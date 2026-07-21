from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


Action = Literal["BUY", "SELL", "HOLD", "ABSTAIN", "NO_CONSENSUS"]
DecisionStatus = Literal["ACCEPTED", "REJECTED"]
RiskStatus = Literal["APPROVED", "REJECTED"]
ExecutionState = Literal[
    "CREATED",
    "RISK_APPROVED",
    "RISK_REJECTED",
    "APPROVAL_PENDING",
    "READY_TO_SUBMIT",
    "SIGNING",
    "SIGNING_FAILED",
    "SUBMITTING",
    "SUBMISSION_AMBIGUOUS",
    "ACKNOWLEDGED",
    "FILLED",
    "RECONCILING",
    "RECONCILIATION_FAILED",
    "RECONCILED",
    "REJECTED",
    "FAILED",
]
CircuitScopeType = Literal["tenant", "strategy", "portfolio", "venue", "account", "network", "instrument"]


class DecisionEvaluationRequest(BaseModel):
    instrument_id: str = Field(min_length=2, max_length=64)
    strategy_id: str = Field(default="strategy-paper-001", min_length=2, max_length=64)
    portfolio_id: str = Field(default="portfolio-paper-001", min_length=2, max_length=64)
    market_bias: float = Field(default=0.3, ge=-1.0, le=1.0)
    volatility: float = Field(default=0.3, ge=0.0, le=1.0)


class ExecutionRequest(BaseModel):
    decision_id: str
    requested_notional: float = Field(gt=0, le=100000)
    side: Literal["BUY", "SELL"] | None = None
    venue_id: str = Field(default="paper-venue-001", min_length=2, max_length=64)


class ApprovalRequest(BaseModel):
    intent_digest: str = Field(min_length=8, max_length=256)
    decision: Literal["APPROVED", "REJECTED"]
    comment: str | None = Field(default=None, max_length=1000)


class CircuitBreakerChangeRequest(BaseModel):
    reason_code: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=1, max_length=1000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=100)


class CircuitBreakerResetRequest(BaseModel):
    reason_code: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=1, max_length=1000)
    evidence_refs: list[str] = Field(min_length=1, max_length=100)


class Assessment(BaseModel):
    assessment_id: str = Field(default_factory=lambda: str(uuid4()))
    agent_id: str
    action: Action
    confidence: float = Field(ge=0.0, le=1.0)
    data_quality: float = Field(ge=0.0, le=1.0)
    rationale_summary: str
    eligible: bool = True


class Snapshot(BaseModel):
    snapshot_id: str = Field(default_factory=lambda: str(uuid4()))
    instrument_id: str
    price: float
    market_bias: float
    volatility: float
    captured_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source_prices: dict[str, float] = Field(default_factory=dict)


class DecisionRecord(BaseModel):
    id: str
    instrument_id: str
    strategy_id: str
    portfolio_id: str
    action: Action
    status: DecisionStatus
    support_weight: float
    weighted_confidence: float
    quorum_weight: float
    snapshot: Snapshot
    assessments: list[Assessment]
    created_at: datetime
    digest: str


class RuleResult(BaseModel):
    rule_id: str
    status: Literal["PASS", "FAIL", "UNKNOWN"]
    observed: str
    limit: str
    reason_code: str


class RiskEvaluation(BaseModel):
    risk_evaluation_id: str = Field(default_factory=lambda: str(uuid4()))
    status: RiskStatus
    approved_notional: float
    requires_approval: bool = False
    policy_version: str = "mvp-risk-policy-v1"
    engine_version: str = "mvp-risk-engine-v1"
    digest: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    valid_until: datetime = Field(default_factory=lambda: datetime.now(UTC) + timedelta(minutes=15))
    rules: list[RuleResult]


class OrderRecord(BaseModel):
    id: str
    execution_id: str
    venue_id: str
    side: Literal["BUY", "SELL"]
    requested_notional: float
    approved_notional: float
    status: Literal["PENDING_APPROVAL", "SUBMITTED", "ACKNOWLEDGED", "FILLED", "REJECTED", "AMBIGUOUS"]


class FillRecord(BaseModel):
    id: str
    execution_id: str
    venue_id: str
    side: Literal["BUY", "SELL"]
    notional: float
    price: float
    quantity: float
    status: Literal["PENDING", "FILLED"] = "FILLED"


class ApprovalRecord(BaseModel):
    approval_id: str
    execution_id: str
    order_intent_id: str
    risk_evaluation_id: str
    principal_id: str
    intent_digest: str
    decision: Literal["APPROVED", "REJECTED"]
    comment: str | None = None
    created_at: datetime
    expires_at: datetime


class CircuitBreakerRecord(BaseModel):
    circuit_breaker_id: str
    scope_type: CircuitScopeType
    scope_id: str
    state: Literal["ACTIVE", "RESET"]
    reason_code: str
    reason: str | None = None
    activated_by: str | None = None
    activated_at: datetime | None = None
    reset_by: str | None = None
    reset_at: datetime | None = None
    updated_at: datetime


class ExecutionRecord(BaseModel):
    id: str
    decision_id: str
    venue_id: str
    side: Literal["BUY", "SELL"]
    state: ExecutionState
    requested_notional: float
    approved_notional: float
    order: OrderRecord
    fill: FillRecord
    risk_evaluation: RiskEvaluation
    approval: ApprovalRecord | None = None
    created_at: datetime
    updated_at: datetime
    intent_digest: str


class AuditEvent(BaseModel):
    id: str
    occurred_at: datetime
    action: str
    result: Literal["SUCCESS", "DENIED", "FAILED", "PENDING"]
    resource_type: str
    resource_id: str
    correlation_id: str
    payload: dict


class PrincipalResponse(BaseModel):
    principal_id: str
    tenant_id: str
    roles: list[str]
    scopes: list[str]


class AcceptedResponse(BaseModel):
    accepted: bool = True
    data: dict | list[dict]
