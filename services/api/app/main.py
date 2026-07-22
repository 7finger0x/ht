from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from time import perf_counter
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response as FastAPIResponse

from .auth import AuthContext, mint_development_token, require_authenticated_principal, require_scopes
from .config import settings
from .db import (
    append_audit_event,
    check_database_health,
    check_redis_health,
    get_active_circuit_breakers,
    get_circuit_breaker,
    get_decision,
    get_execution,
    get_idempotency_record,
    hash_request_payload,
    init_db,
    insert_decision,
    insert_execution,
    list_audit_events,
    list_circuit_breakers,
    list_decisions,
    list_executions,
    store_idempotency_record,
    update_execution,
    upsert_circuit_breaker,
)
from .models import (
    AcceptedResponse,
    ApprovalRequest,
    AuditEvent,
    CircuitBreakerChangeRequest,
    CircuitBreakerRecord,
    CircuitBreakerResetRequest,
    CircuitScopeType,
    DecisionEvaluationRequest,
    DecisionRecord,
    ExecutionRecord,
    ExecutionRequest,
    PrincipalResponse,
)
from .observability import (
    clear_request_context,
    configure_observability,
    extract_trace_context,
    metrics_content_type,
    record_audit_append_failure,
    record_audit_append_success,
    record_circuit_breaker_check,
    record_circuit_breaker_state_change,
    record_decision_metrics,
    record_execution_metrics,
    record_http_server_metrics,
    record_market_snapshot_metrics,
    record_risk_evaluation_metrics,
    record_venue_order_metrics,
    render_metrics,
    set_dependency_state,
    set_execution_context,
    set_request_context,
    start_hermes_span,
)
from .worker import (
    build_execution,
    complete_execution_after_approval,
    evaluate_consensus,
    evaluate_risk,
    make_audit_event,
    reject_execution_after_approval,
)


AuthenticatedPrincipal = Annotated[AuthContext, Depends(require_authenticated_principal)]
DecisionWriter = Annotated[AuthContext, Depends(require_scopes("decisions:create"))]
ExecutionWriter = Annotated[AuthContext, Depends(require_scopes("executions:create"))]
ExecutionApprover = Annotated[AuthContext, Depends(require_scopes("executions:approve"))]
AuditReader = Annotated[AuthContext, Depends(require_scopes("audit:read"))]
DecisionReader = Annotated[AuthContext, Depends(require_scopes("decisions:read"))]
ExecutionReader = Annotated[AuthContext, Depends(require_scopes("executions:read"))]
DependencyHealthReader = Annotated[AuthContext, Depends(require_scopes("platform:health:read"))]
ControlReader = Annotated[AuthContext, Depends(require_scopes("controls:read"))]
ControlActivator = Annotated[AuthContext, Depends(require_scopes("controls:activate"))]
ControlResetter = Annotated[AuthContext, Depends(require_scopes("controls:reset"))]
logger = logging.getLogger("hermes.api")


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_observability()
    init_db()
    yield


app = FastAPI(title=settings.app_name, version=settings.release_version, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def attach_request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", "").strip() or str(uuid4())
    request.state.request_id = request_id
    set_request_context(request_id=request_id, correlation_id=request_id)
    started_at = perf_counter()
    route = request.scope.get("path", request.url.path)
    parent_context = extract_trace_context(dict(request.headers))

    try:
        with start_hermes_span(
            "hermes.http.request",
            parent_context=parent_context,
            attributes={
                "http.method": request.method,
                "http.route": route,
                "hermes.correlation_id": request_id,
                "hermes.request_id": request_id,
            },
        ) as span:
            response = await call_next(request)
            span.set_attribute("http.status_code", response.status_code)
    except Exception as exc:
        duration_seconds = max(perf_counter() - started_at, 0.0)
        record_http_server_metrics(request.method, route, 500, None, duration_seconds)
        logger.exception(
            "Unhandled request failure",
            extra={"request_id": request_id, "correlation_id": request_id, "error_code": exc.__class__.__name__},
        )
        clear_request_context()
        raise

    response.headers["X-Request-ID"] = request_id
    if "Idempotency-Replayed" not in response.headers:
        response.headers["Idempotency-Replayed"] = "false"

    duration_seconds = max(perf_counter() - started_at, 0.0)
    auth_context = getattr(request.state, "auth_context", None)
    tenant_id = getattr(auth_context, "tenant_id", None)
    record_http_server_metrics(request.method, route, response.status_code, tenant_id, duration_seconds)
    logger.info(
        "%s %s -> %s",
        request.method,
        route,
        response.status_code,
        extra={"request_id": request_id, "correlation_id": request_id, "tenant_id": tenant_id},
    )
    clear_request_context()
    return response


@app.get("/metrics", include_in_schema=False)
def get_metrics() -> FastAPIResponse:
    if not settings.metrics_enabled:
        raise HTTPException(status_code=404, detail="Metrics endpoint is disabled")
    return FastAPIResponse(content=render_metrics(), media_type=metrics_content_type())


@app.get("/v1/health/live")
def get_liveness(request: Request) -> dict:
    return {
        "status": "live",
        "service": settings.service_name,
        "environment": settings.environment,
        "version": settings.release_version,
        "source_commit": settings.source_commit,
        "image_digest": settings.image_digest,
        "request_id": request.state.request_id,
    }


@app.get("/v1/health/ready")
def get_readiness() -> dict:
    now = datetime.now(UTC).isoformat()
    return {
        "status": "ready",
        "mode": "simulation-only",
        "live_trading_enabled": settings.live_trading_enabled,
        "auth_provider": settings.auth_provider,
        "version": settings.release_version,
        "source_commit": settings.source_commit,
        "image_digest": settings.image_digest,
        "time": now,
    }


@app.get("/v1/health/dependencies")
def get_dependency_health(_: DependencyHealthReader) -> dict:
    dependencies = [check_database_health(), check_redis_health()]
    for item in dependencies:
        dependency_name = "postgres" if item["name"] == "database" else item["name"]
        set_dependency_state(dependency_name, item["status"])
    statuses = {item["status"] for item in dependencies}
    overall_status = "ready"
    if "down" in statuses:
        overall_status = "degraded"
    return {
        "status": overall_status,
        "checked_at": datetime.now(UTC).isoformat(),
        "dependencies": dependencies,
    }


@app.post("/v1/dev/token", status_code=201)
def issue_dev_token(payload: dict) -> dict:
    try:
        return mint_development_token(
            principal_id=str(payload["principal_id"]),
            tenant_id=str(payload["tenant_id"]),
            subject=str(payload["subject"]),
            roles=tuple(str(item) for item in payload.get("roles", [])),
            scopes=tuple(str(item) for item in payload.get("scopes", [])),
            lifetime_seconds=int(payload.get("lifetime_seconds", 3600)),
        )
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"Missing field: {exc.args[0]}") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/v1/me", response_model=PrincipalResponse)
def get_current_principal(context: AuthenticatedPrincipal) -> PrincipalResponse:
    return PrincipalResponse(
        principal_id=context.principal_id,
        tenant_id=context.tenant_id,
        roles=list(context.roles),
        scopes=list(context.scopes),
    )


@app.get("/v1/decisions", response_model=list[DecisionRecord])
def get_decisions(context: DecisionReader) -> list[DecisionRecord]:
    records = []
    for row in list_decisions(context):
        row["snapshot"] = json.loads(row.pop("snapshot_json"))
        row["assessments"] = json.loads(row.pop("assessments_json"))
        records.append(DecisionRecord.model_validate(row))
    return records


@app.post("/v1/decision-evaluations", response_model=AcceptedResponse, status_code=202)
def create_decision_evaluation(
    request: DecisionEvaluationRequest,
    response: Response,
    http_request: Request,
    context: DecisionWriter,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> AcceptedResponse:
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key header is required")

    request_payload = request.model_dump(mode="json")
    request_hash = hash_request_payload(request_payload)
    replay = get_idempotency_record(idempotency_key, "decision-evaluations", context)
    if replay:
        if replay["request_hash"] != request_hash:
            raise HTTPException(status_code=409, detail="Idempotency-Key already used with a different payload")
        response.headers["Idempotency-Replayed"] = "true"
        return AcceptedResponse.model_validate(replay["response_json"])

    with start_hermes_span(
        "hermes.consensus.evaluate",
        attributes={
            "hermes.tenant_id": context.tenant_id,
            "hermes.principal_id": context.principal_id,
        },
    ):
        decision = evaluate_consensus(request)
        with start_hermes_span(
            "hermes.decision.persist",
            attributes={
                "hermes.tenant_id": context.tenant_id,
                "decision_id": decision["id"],
            },
        ):
            insert_decision(decision, context)
        record_decision_metrics(decision, context.tenant_id)
        record_market_snapshot_metrics(decision.get("snapshot", {}), context.tenant_id)

    audit = make_audit_event(
        action="decision.evaluate",
        resource_type="decision",
        resource_id=decision["id"],
        payload={
            "instrument_id": decision["instrument_id"],
            "action": decision["action"],
            "status": decision["status"],
            "tenant_id": context.tenant_id,
            "principal_id": context.principal_id,
        },
        correlation_id=http_request.state.request_id,
    )
    _append_audit_event(audit.model_dump(mode="json"), context)
    response_payload = AcceptedResponse(data={"decision_id": decision["id"], "status": decision["status"]}).model_dump(mode="json")
    store_idempotency_record(idempotency_key, "decision-evaluations", request_hash, 202, response_payload, context)
    return AcceptedResponse.model_validate(response_payload)


@app.get("/v1/decisions/{decision_id}", response_model=DecisionRecord)
def get_decision_by_id(decision_id: str, context: DecisionReader) -> DecisionRecord:
    row = get_decision(decision_id, context)
    if not row:
        raise HTTPException(status_code=404, detail="Decision not found")
    row["snapshot"] = json.loads(row.pop("snapshot_json"))
    row["assessments"] = json.loads(row.pop("assessments_json"))
    return DecisionRecord.model_validate(row)


@app.get("/v1/executions", response_model=list[ExecutionRecord])
def get_all_executions(context: ExecutionReader) -> list[ExecutionRecord]:
    records = []
    for row in list_executions(context):
        records.append(ExecutionRecord.model_validate(_hydrate_execution_row(row)))
    return records


@app.post("/v1/executions", response_model=AcceptedResponse, status_code=202)
def create_execution(
    request: ExecutionRequest,
    response: Response,
    http_request: Request,
    context: ExecutionWriter,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> AcceptedResponse:
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key header is required")

    request_payload = request.model_dump(mode="json")
    request_hash = hash_request_payload(request_payload)
    replay = get_idempotency_record(idempotency_key, "executions", context)
    if replay:
        if replay["request_hash"] != request_hash:
            raise HTTPException(status_code=409, detail="Idempotency-Key already used with a different payload")
        response.headers["Idempotency-Replayed"] = "true"
        return AcceptedResponse.model_validate(replay["response_json"])

    with start_hermes_span(
        "hermes.decision.load",
        attributes={
            "hermes.tenant_id": context.tenant_id,
            "decision_id": request.decision_id,
        },
    ):
        decision = get_decision(request.decision_id, context)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    decision["snapshot"] = json.loads(decision.pop("snapshot_json"))
    decision["assessments"] = json.loads(decision.pop("assessments_json"))
    if decision["status"] != "ACCEPTED":
        raise HTTPException(status_code=409, detail="Decision is not executable")
    if decision["action"] not in {"BUY", "SELL"}:
        raise HTTPException(status_code=409, detail="Decision has no executable side")

    with start_hermes_span(
        "hermes.execution.create",
        attributes={
            "hermes.tenant_id": context.tenant_id,
            "hermes.principal_id": context.principal_id,
            "decision_id": request.decision_id,
            "venue_id": request.venue_id,
            "deployment.live_trading_enabled": settings.live_trading_enabled,
        },
    ):
        breaker_started = perf_counter()
        record_circuit_breaker_check("deployment", max(perf_counter() - breaker_started, 0.0))
        _enforce_runtime_circuit_breakers(context, decision, request)

        risk_started = perf_counter()
        with start_hermes_span(
            "hermes.risk.evaluate",
            attributes={
                "hermes.tenant_id": context.tenant_id,
                "hermes.principal_id": context.principal_id,
                "decision_id": request.decision_id,
            },
        ):
            risk_evaluation = evaluate_risk(decision, request)
        risk_duration = max(perf_counter() - risk_started, 0.0)
        record_risk_evaluation_metrics(risk_evaluation, context.tenant_id, risk_duration)
        execution = build_execution(decision, request, risk_evaluation)

        with start_hermes_span(
            "hermes.execution.persist",
            attributes={
                "hermes.tenant_id": context.tenant_id,
                "execution_id": execution["id"],
            },
        ):
            insert_execution(execution, context)
        set_execution_context(execution["id"])
        record_execution_metrics(execution, context.tenant_id, decision["strategy_id"], mode="simulation")

    _append_audit_event(
        make_audit_event(
            action="execution.created",
            resource_type="execution",
            resource_id=execution["id"],
            payload={
                "decision_id": request.decision_id,
                "state": execution["state"],
                "approved_notional": execution["approved_notional"],
                "tenant_id": context.tenant_id,
                "principal_id": context.principal_id,
            },
            result="PENDING" if execution["state"] == "APPROVAL_PENDING" else "FAILED",
            correlation_id=http_request.state.request_id,
        ).model_dump(mode="json"),
        context,
    )
    response_payload = AcceptedResponse(data={"execution_id": execution["id"], "state": execution["state"]}).model_dump(mode="json")
    store_idempotency_record(idempotency_key, "executions", request_hash, 202, response_payload, context)
    return AcceptedResponse.model_validate(response_payload)


@app.get("/v1/executions/{execution_id}", response_model=ExecutionRecord)
def get_execution_by_id(execution_id: str, context: ExecutionReader) -> ExecutionRecord:
    row = get_execution(execution_id, context)
    if not row:
        raise HTTPException(status_code=404, detail="Execution not found")
    return ExecutionRecord.model_validate(_hydrate_execution_row(row))


@app.post("/v1/executions/{execution_id}/approve", response_model=ExecutionRecord)
def approve_execution(
    execution_id: str,
    request: ApprovalRequest,
    response: Response,
    http_request: Request,
    context: ExecutionApprover,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> ExecutionRecord:
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key header is required")

    operation = f"execution-approvals:{execution_id}"
    request_payload = request.model_dump(mode="json")
    request_hash = hash_request_payload(request_payload)
    replay = get_idempotency_record(idempotency_key, operation, context)
    if replay:
        if replay["request_hash"] != request_hash:
            raise HTTPException(status_code=409, detail="Idempotency-Key already used with a different payload")
        response.headers["Idempotency-Replayed"] = "true"
        return ExecutionRecord.model_validate(replay["response_json"])

    execution = get_execution(execution_id, context)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    execution = _hydrate_execution_row(execution)
    if execution["state"] != "APPROVAL_PENDING":
        raise HTTPException(status_code=409, detail="Execution is not awaiting approval")
    if request.intent_digest != execution["intent_digest"]:
        raise HTTPException(status_code=409, detail="Execution intent digest does not match current state")

    decision = get_decision(execution["decision_id"], context)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    decision["snapshot"] = json.loads(decision.pop("snapshot_json"))
    decision["assessments"] = json.loads(decision.pop("assessments_json"))

    approval = {
        "approval_id": str(uuid4()),
        "execution_id": execution_id,
        "order_intent_id": execution["order"]["id"],
        "risk_evaluation_id": execution["risk_evaluation"]["risk_evaluation_id"],
        "principal_id": context.principal_id,
        "intent_digest": request.intent_digest,
        "decision": request.decision,
        "comment": request.comment,
        "created_at": datetime.now(UTC).isoformat(),
        "expires_at": execution["risk_evaluation"]["valid_until"],
    }

    with start_hermes_span(
        "hermes.execution.approval",
        attributes={
            "hermes.tenant_id": context.tenant_id,
            "hermes.principal_id": context.principal_id,
            "execution_id": execution_id,
            "approval.decision": request.decision,
        },
    ):
        if request.decision == "APPROVED":
            updated_execution = complete_execution_after_approval(execution, decision, approval)
            record_venue_order_metrics(
                updated_execution,
                context.tenant_id,
                submission_latency_seconds=0.0,
                venue_type="simulated",
            )
            audit_action = "execution.approved"
            audit_result = "SUCCESS"
        else:
            updated_execution = reject_execution_after_approval(execution, approval)
            audit_action = "execution.rejected"
            audit_result = "DENIED"

        with start_hermes_span(
            "hermes.execution.persist",
            attributes={
                "hermes.tenant_id": context.tenant_id,
                "execution_id": execution_id,
            },
        ):
            update_execution(updated_execution, context)
        set_execution_context(updated_execution["id"])
        record_execution_metrics(
            updated_execution,
            context.tenant_id,
            decision["strategy_id"],
            mode="simulation",
            previous_transitions=execution.get("transitions", []),
        )

    _append_audit_event(
        make_audit_event(
            action=audit_action,
            resource_type="execution",
            resource_id=execution_id,
            payload={
                "decision_id": execution["decision_id"],
                "state": updated_execution["state"],
                "tenant_id": context.tenant_id,
                "principal_id": context.principal_id,
                "approval_decision": request.decision,
            },
            result=audit_result,
            correlation_id=http_request.state.request_id,
        ).model_dump(mode="json"),
        context,
    )

    response_model = ExecutionRecord.model_validate(updated_execution)
    store_idempotency_record(idempotency_key, operation, request_hash, 200, response_model.model_dump(mode="json"), context)
    return response_model


@app.get("/v1/circuit-breakers", response_model=AcceptedResponse)
def get_circuit_breakers(context: ControlReader) -> AcceptedResponse:
    records = [CircuitBreakerRecord.model_validate(row).model_dump(mode="json") for row in list_circuit_breakers(context)]
    return AcceptedResponse(data=records)


@app.post("/v1/circuit-breakers/{scope_type}/{scope_id}/activate", response_model=CircuitBreakerRecord)
def activate_circuit_breaker(
    scope_type: CircuitScopeType,
    scope_id: str,
    request: CircuitBreakerChangeRequest,
    response: Response,
    http_request: Request,
    context: ControlActivator,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> CircuitBreakerRecord:
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key header is required")

    operation = f"circuit-breaker-activate:{scope_type}:{scope_id}"
    request_hash = hash_request_payload(request.model_dump(mode="json"))
    replay = get_idempotency_record(idempotency_key, operation, context)
    if replay:
        if replay["request_hash"] != request_hash:
            raise HTTPException(status_code=409, detail="Idempotency-Key already used with a different payload")
        response.headers["Idempotency-Replayed"] = "true"
        return CircuitBreakerRecord.model_validate(replay["response_json"])

    existing = get_circuit_breaker(scope_type, scope_id, context)
    record = _build_circuit_breaker_record(
        existing=existing,
        scope_type=scope_type,
        scope_id=scope_id,
        state="ACTIVE",
        reason_code=request.reason_code,
        reason=request.reason,
        principal_id=context.principal_id,
    )
    upsert_circuit_breaker(record, context)
    record_circuit_breaker_state_change(record, context.tenant_id)
    _append_audit_event(
        make_audit_event(
            action="circuit_breaker.activate",
            resource_type="circuit_breaker",
            resource_id=record["circuit_breaker_id"],
            payload={
                "tenant_id": context.tenant_id,
                "principal_id": context.principal_id,
                "scope_type": scope_type,
                "scope_id": scope_id,
                "reason_code": request.reason_code,
                "evidence_refs": request.evidence_refs,
            },
            correlation_id=http_request.state.request_id,
        ).model_dump(mode="json"),
        context,
    )
    response_model = CircuitBreakerRecord.model_validate(record)
    store_idempotency_record(idempotency_key, operation, request_hash, 200, response_model.model_dump(mode="json"), context)
    return response_model


@app.post("/v1/circuit-breakers/{scope_type}/{scope_id}/reset", response_model=CircuitBreakerRecord)
def reset_circuit_breaker(
    scope_type: CircuitScopeType,
    scope_id: str,
    request: CircuitBreakerResetRequest,
    response: Response,
    http_request: Request,
    context: ControlResetter,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> CircuitBreakerRecord:
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key header is required")

    operation = f"circuit-breaker-reset:{scope_type}:{scope_id}"
    request_hash = hash_request_payload(request.model_dump(mode="json"))
    replay = get_idempotency_record(idempotency_key, operation, context)
    if replay:
        if replay["request_hash"] != request_hash:
            raise HTTPException(status_code=409, detail="Idempotency-Key already used with a different payload")
        response.headers["Idempotency-Replayed"] = "true"
        return CircuitBreakerRecord.model_validate(replay["response_json"])

    existing = get_circuit_breaker(scope_type, scope_id, context)
    if not existing or existing.get("state") != "ACTIVE":
        raise HTTPException(status_code=409, detail="Circuit breaker is not active")

    record = _build_circuit_breaker_record(
        existing=existing,
        scope_type=scope_type,
        scope_id=scope_id,
        state="RESET",
        reason_code=request.reason_code,
        reason=request.reason,
        principal_id=context.principal_id,
    )
    upsert_circuit_breaker(record, context)
    record_circuit_breaker_state_change(record, context.tenant_id)
    _append_audit_event(
        make_audit_event(
            action="circuit_breaker.reset",
            resource_type="circuit_breaker",
            resource_id=record["circuit_breaker_id"],
            payload={
                "tenant_id": context.tenant_id,
                "principal_id": context.principal_id,
                "scope_type": scope_type,
                "scope_id": scope_id,
                "reason_code": request.reason_code,
                "evidence_refs": request.evidence_refs,
            },
            correlation_id=http_request.state.request_id,
        ).model_dump(mode="json"),
        context,
    )
    response_model = CircuitBreakerRecord.model_validate(record)
    store_idempotency_record(idempotency_key, operation, request_hash, 200, response_model.model_dump(mode="json"), context)
    return response_model


@app.get("/v1/audit/events", response_model=list[AuditEvent])
def get_audit_events(context: AuditReader) -> list[AuditEvent]:
    records = []
    for row in list_audit_events(context):
        row["payload"] = json.loads(row.pop("payload_json"))
        records.append(AuditEvent.model_validate(row))
    return records


def _append_audit_event(event: dict, context: AuthContext) -> None:
    started_at = perf_counter()
    try:
        with start_hermes_span(
            "hermes.audit.append",
            attributes={
                "hermes.tenant_id": context.tenant_id,
                "hermes.principal_id": context.principal_id,
                "audit.action": event.get("action"),
                "audit.result": event.get("result"),
            },
        ):
            append_audit_event(event, context)
    except Exception as exc:
        record_audit_append_failure(context.tenant_id, exc.__class__.__name__, max(perf_counter() - started_at, 0.0))
        raise
    record_audit_append_success(
        context.tenant_id,
        actor_type="principal",
        result=str(event.get("result", "UNKNOWN")),
        duration_seconds=max(perf_counter() - started_at, 0.0),
    )


def _hydrate_execution_row(row: dict) -> dict:
    row["order"] = json.loads(row.pop("order_json"))
    row["fill"] = json.loads(row.pop("fill_json"))
    row["risk_evaluation"] = json.loads(row.pop("risk_json"))
    approval_json = row.pop("approval_json", None)
    row["approval"] = json.loads(approval_json) if approval_json else None
    row["transitions"] = json.loads(row.pop("transitions_json", "[]"))
    return row


def _scope_id_for(scope_type: str, *, context: AuthContext, decision: dict | None = None, request: ExecutionRequest | None = None) -> str:
    if scope_type == "tenant":
        return context.tenant_id
    if decision is None or request is None:
        raise ValueError(f"Decision and request are required for scope type {scope_type}")
    mapping = {
        "strategy": decision["strategy_id"],
        "portfolio": decision["portfolio_id"],
        "venue": request.venue_id,
        "instrument": decision["instrument_id"],
    }
    return mapping[scope_type]


def _runtime_breaker_scope_keys(context: AuthContext, decision: dict, request: ExecutionRequest) -> list[tuple[str, str]]:
    scope_types = ["tenant", "strategy", "portfolio", "venue", "instrument"]
    return [
        (scope_type, _scope_id_for(scope_type, context=context, decision=decision, request=request))
        for scope_type in scope_types
    ]


def _enforce_runtime_circuit_breakers(context: AuthContext, decision: dict, request: ExecutionRequest) -> None:
    breaker_started = perf_counter()
    active_breakers = get_active_circuit_breakers(_runtime_breaker_scope_keys(context, decision, request), context)
    record_circuit_breaker_check("runtime", max(perf_counter() - breaker_started, 0.0))
    if active_breakers:
        blocker = active_breakers[0]
        raise HTTPException(
            status_code=409,
            detail={
                "code": "circuit_breaker_active",
                "scope_type": blocker["scope_type"],
                "scope_id": blocker["scope_id"],
                "reason_code": blocker["reason_code"],
            },
        )


def _build_circuit_breaker_record(
    *,
    existing: dict | None,
    scope_type: str,
    scope_id: str,
    state: str,
    reason_code: str,
    reason: str,
    principal_id: str,
) -> dict:
    now = datetime.now(UTC).isoformat()
    record = {
        "circuit_breaker_id": existing["circuit_breaker_id"] if existing else str(uuid4()),
        "scope_type": scope_type,
        "scope_id": scope_id,
        "state": state,
        "reason_code": reason_code,
        "reason": reason,
        "activated_by": existing.get("activated_by") if existing else None,
        "activated_at": existing.get("activated_at") if existing else None,
        "reset_by": existing.get("reset_by") if existing else None,
        "reset_at": existing.get("reset_at") if existing else None,
        "updated_at": now,
    }
    if state == "ACTIVE":
        record["activated_by"] = principal_id
        record["activated_at"] = now
        record["reset_by"] = None
        record["reset_at"] = None
    else:
        record["activated_by"] = existing.get("activated_by") if existing else None
        record["activated_at"] = existing.get("activated_at") if existing else None
        record["reset_by"] = principal_id
        record["reset_at"] = now
    return record
