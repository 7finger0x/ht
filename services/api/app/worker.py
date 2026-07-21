from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from uuid import uuid4

from .models import Assessment, AuditEvent, DecisionEvaluationRequest, ExecutionRequest, FillRecord, OrderRecord, RiskEvaluation, RuleResult, Snapshot


def _hash_digest(payload: dict) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _agent_action(bias: float, volatility: float, mode: str) -> str:
    if mode == "momentum":
        if bias >= 0.2:
            return "BUY"
        if bias <= -0.2:
            return "SELL"
        return "HOLD"
    if mode == "mean-reversion":
        if bias >= 0.7:
            return "SELL"
        if bias <= -0.7:
            return "BUY"
        return "HOLD"
    if volatility >= 0.85:
        return "ABSTAIN"
    return "BUY" if bias >= 0 else "SELL"


def build_snapshot(request: DecisionEvaluationRequest) -> Snapshot:
    digest_seed = int(hashlib.sha256(request.instrument_id.encode("utf-8")).hexdigest()[:8], 16)
    price = round(25 + (digest_seed % 1000) / 10 + request.market_bias * 5, 2)
    divergence_scale = max(0.0025, min(0.05, request.volatility * 0.04 + abs(request.market_bias) * 0.01))
    source_prices = {
        "synthetic-primary": round(price * (1 - divergence_scale), 4),
        "synthetic-consensus": round(price, 4),
        "synthetic-secondary": round(price * (1 + divergence_scale), 4),
    }
    return Snapshot(
        instrument_id=request.instrument_id.upper(),
        price=price,
        market_bias=request.market_bias,
        volatility=request.volatility,
        source_prices=source_prices,
    )


def build_assessments(snapshot: Snapshot) -> list[Assessment]:
    bias = snapshot.market_bias
    volatility = snapshot.volatility
    return [
        Assessment(
            agent_id="technical-momentum",
            action=_agent_action(bias, volatility, "momentum"),
            confidence=min(0.95, 0.6 + abs(bias) * 0.3),
            data_quality=max(0.7, 1 - volatility * 0.2),
            rationale_summary="Tracks directional bias over the latest simulated snapshots.",
        ),
        Assessment(
            agent_id="mean-reversion",
            action=_agent_action(bias, volatility, "mean-reversion"),
            confidence=0.62,
            data_quality=max(0.72, 1 - volatility * 0.25),
            rationale_summary="Pushes back only when the market bias is extremely stretched.",
        ),
        Assessment(
            agent_id="risk-sentiment",
            action=_agent_action(bias, volatility, "sentiment"),
            confidence=max(0.55, 0.85 - volatility * 0.25),
            data_quality=max(0.7, 1 - volatility * 0.15),
            rationale_summary="Prefers lower volatility environments and abstains on stress spikes.",
        ),
    ]


def evaluate_consensus(request: DecisionEvaluationRequest) -> dict:
    snapshot = build_snapshot(request)
    assessments = build_assessments(snapshot)
    eligible = [item for item in assessments if item.eligible]
    enabled_weight = float(len(assessments))
    eligible_weight = float(len(eligible))
    quorum_weight = eligible_weight / enabled_weight

    support = {"BUY": 0.0, "SELL": 0.0, "HOLD": 0.0}
    weighted_confidence = {"BUY": 0.0, "SELL": 0.0, "HOLD": 0.0}
    abstain_weight = 0.0
    for item in eligible:
        if item.action == "ABSTAIN":
            abstain_weight += 1 / enabled_weight
            continue
        support[item.action] += 1 / eligible_weight
        weighted_confidence[item.action] += (item.confidence * item.data_quality) / eligible_weight

    candidate = max(support, key=support.get)
    opposition = support["SELL"] if candidate == "BUY" else support["BUY"] if candidate == "SELL" else 0.0
    accepted = (
        candidate in {"BUY", "SELL"}
        and len(eligible) >= 3
        and quorum_weight >= 0.75
        and support[candidate] >= 0.5
        and weighted_confidence[candidate] >= 0.45
        and opposition <= 0.4
        and abstain_weight <= 0.34
    )

    payload = {
        "instrument_id": snapshot.instrument_id,
        "market_bias": request.market_bias,
        "volatility": request.volatility,
        "candidate": candidate,
        "support_weight": round(support[candidate], 4),
        "weighted_confidence": round(weighted_confidence[candidate], 4),
        "quorum_weight": round(quorum_weight, 4),
    }
    return {
        "id": str(uuid4()),
        "instrument_id": snapshot.instrument_id,
        "strategy_id": request.strategy_id,
        "portfolio_id": request.portfolio_id,
        "action": candidate if accepted else "NO_CONSENSUS",
        "status": "ACCEPTED" if accepted else "REJECTED",
        "support_weight": round(support[candidate], 4),
        "weighted_confidence": round(weighted_confidence[candidate], 4),
        "quorum_weight": round(quorum_weight, 4),
        "snapshot": snapshot.model_dump(mode="json"),
        "assessments": [item.model_dump(mode="json") for item in assessments],
        "created_at": datetime.now(UTC).isoformat(),
        "digest": _hash_digest(payload),
    }


def evaluate_risk(decision: dict, request: ExecutionRequest) -> RiskEvaluation:
    snapshot = decision["snapshot"]
    volatility = float(snapshot["volatility"])
    rules = [
        RuleResult(
            rule_id="system.live_mode_disabled",
            status="PASS",
            observed="simulation",
            limit="simulation-only",
            reason_code="SIMULATION_ALLOWED",
        ),
        RuleResult(
            rule_id="market.max_volatility",
            status="PASS" if volatility <= 0.9 else "FAIL",
            observed=f"{volatility:.4f}",
            limit="0.9000",
            reason_code="WITHIN_LIMIT" if volatility <= 0.9 else "VOLATILITY_TOO_HIGH",
        ),
        RuleResult(
            rule_id="portfolio.max_requested_notional",
            status="PASS" if request.requested_notional <= 100000 else "FAIL",
            observed=f"{request.requested_notional:.2f}",
            limit="100000.00",
            reason_code="WITHIN_LIMIT" if request.requested_notional <= 100000 else "LIMIT_EXCEEDED",
        ),
    ]
    if any(rule.status != "PASS" for rule in rules):
        return RiskEvaluation(
            status="REJECTED",
            approved_notional=0,
            requires_approval=False,
            rules=rules,
            digest=_hash_digest(
                {
                    "decision_id": decision["id"],
                    "status": "REJECTED",
                    "approved_notional": 0,
                    "rules": [rule.model_dump(mode="json") for rule in rules],
                }
            ),
        )

    headroom = max(0.15, 1 - volatility * 0.7)
    approved = round(min(request.requested_notional, 25000 * headroom), 2)
    if approved <= 0:
        return RiskEvaluation(
            status="REJECTED",
            approved_notional=0,
            requires_approval=False,
            rules=rules,
            digest=_hash_digest(
                {
                    "decision_id": decision["id"],
                    "status": "REJECTED",
                    "approved_notional": 0,
                    "rules": [rule.model_dump(mode="json") for rule in rules],
                }
            ),
        )
    return RiskEvaluation(
        status="APPROVED",
        approved_notional=approved,
        requires_approval=True,
        rules=rules,
        digest=_hash_digest(
            {
                "decision_id": decision["id"],
                "status": "APPROVED",
                "approved_notional": approved,
                "rules": [rule.model_dump(mode="json") for rule in rules],
            }
        ),
    )


def build_execution(decision: dict, request: ExecutionRequest, risk: RiskEvaluation) -> dict:
    side = request.side or ("BUY" if decision["action"] == "BUY" else "SELL")
    now = datetime.now(UTC).isoformat()
    execution_id = str(uuid4())
    if risk.status != "APPROVED":
        empty_order = OrderRecord(
            id=str(uuid4()),
            execution_id=execution_id,
            venue_id=request.venue_id,
            side=side,
            requested_notional=request.requested_notional,
            approved_notional=0,
            status="REJECTED",
        )
        empty_fill = FillRecord(
            id=str(uuid4()),
            execution_id=execution_id,
            venue_id=request.venue_id,
            side=side,
            notional=0,
            price=0,
            quantity=0,
            status="PENDING",
        )
        return {
            "id": execution_id,
            "decision_id": request.decision_id,
            "venue_id": request.venue_id,
            "side": side,
            "state": "FAILED",
            "requested_notional": request.requested_notional,
            "approved_notional": 0,
            "order": empty_order.model_dump(mode="json"),
            "fill": empty_fill.model_dump(mode="json"),
            "risk_evaluation": risk.model_dump(mode="json"),
            "approval": None,
            "created_at": now,
            "updated_at": now,
            "intent_digest": _hash_digest({"decision": request.decision_id, "approved_notional": 0}),
            "transitions": ["CREATED", "RISK_REJECTED", "FAILED"],
        }

    pending_order = OrderRecord(
        id=str(uuid4()),
        execution_id=execution_id,
        venue_id=request.venue_id,
        side=side,
        requested_notional=request.requested_notional,
        approved_notional=risk.approved_notional,
        status="PENDING_APPROVAL",
    )
    pending_fill = FillRecord(
        id=str(uuid4()),
        execution_id=execution_id,
        venue_id=request.venue_id,
        side=side,
        notional=0,
        price=0,
        quantity=0,
        status="PENDING",
    )
    return {
        "id": execution_id,
        "decision_id": request.decision_id,
        "venue_id": request.venue_id,
        "side": side,
        "state": "APPROVAL_PENDING",
        "requested_notional": request.requested_notional,
        "approved_notional": risk.approved_notional,
        "order": pending_order.model_dump(mode="json"),
        "fill": pending_fill.model_dump(mode="json"),
        "risk_evaluation": risk.model_dump(mode="json"),
        "approval": None,
        "created_at": now,
        "updated_at": now,
        "intent_digest": _hash_digest({"decision": request.decision_id, "approved_notional": risk.approved_notional}),
        "transitions": ["CREATED", "RISK_APPROVED", "APPROVAL_PENDING"],
    }


def complete_execution_after_approval(execution: dict, decision: dict, approval: dict) -> dict:
    now = datetime.now(UTC).isoformat()
    price = float(decision["snapshot"]["price"])
    approved_notional = float(execution["approved_notional"])
    quantity = round(approved_notional / price, 6) if approved_notional > 0 and price > 0 else 0.0
    order = {
        **execution["order"],
        "status": "FILLED",
        "approved_notional": approved_notional,
    }
    fill = {
        **execution["fill"],
        "status": "FILLED",
        "notional": approved_notional,
        "price": price,
        "quantity": quantity,
    }
    return {
        **execution,
        "state": "RECONCILED",
        "order": order,
        "fill": fill,
        "approval": approval,
        "updated_at": now,
        "transitions": execution.get("transitions", [])
        + ["READY_TO_SUBMIT", "SIGNING", "SUBMITTING", "ACKNOWLEDGED", "FILLED", "RECONCILED"],
    }


def reject_execution_after_approval(execution: dict, approval: dict) -> dict:
    now = datetime.now(UTC).isoformat()
    order = {
        **execution["order"],
        "status": "REJECTED",
    }
    return {
        **execution,
        "state": "REJECTED",
        "order": order,
        "approval": approval,
        "updated_at": now,
        "transitions": execution.get("transitions", []) + ["REJECTED"],
    }


def simulate_execution(decision: dict, request: ExecutionRequest) -> dict:
    risk = evaluate_risk(decision, request)
    execution = build_execution(decision, request, risk)
    if execution["state"] != "APPROVAL_PENDING":
        return execution
    approval = {
        "approval_id": str(uuid4()),
        "execution_id": execution["id"],
        "order_intent_id": execution["order"]["id"],
        "risk_evaluation_id": execution["risk_evaluation"]["risk_evaluation_id"],
        "principal_id": "simulation",
        "intent_digest": execution["intent_digest"],
        "decision": "APPROVED",
        "comment": "Simulated approval path.",
        "created_at": datetime.now(UTC).isoformat(),
        "expires_at": execution["risk_evaluation"]["valid_until"],
    }
    return complete_execution_after_approval(execution, decision, approval)


def make_audit_event(
    action: str,
    resource_type: str,
    resource_id: str,
    payload: dict,
    result: str = "SUCCESS",
    correlation_id: str | None = None,
) -> AuditEvent:
    return AuditEvent(
        id=str(uuid4()),
        occurred_at=datetime.now(UTC),
        action=action,
        result=result,
        resource_type=resource_type,
        resource_id=resource_id,
        correlation_id=correlation_id or str(uuid4()),
        payload=payload,
    )
