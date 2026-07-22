from __future__ import annotations

import json
import logging
import sys
import time
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any, Iterator, Mapping

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.propagate import extract
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Span
from opentelemetry.trace.status import Status, StatusCode
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

from .config import settings


_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)
_tenant_id: ContextVar[str | None] = ContextVar("tenant_id", default=None)
_principal_id: ContextVar[str | None] = ContextVar("principal_id", default=None)
_execution_id: ContextVar[str | None] = ContextVar("execution_id", default=None)
_observability_configured = False
_deployment_breaker_synced = False

HTTP_REQUESTS_TOTAL = Counter(
    "hermes_http_requests_total",
    "Total HTTP requests.",
    labelnames=("method", "route", "status_code", "tenant_id"),
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "hermes_http_request_duration_seconds",
    "HTTP request latency.",
    labelnames=("method", "route", "status_code"),
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0),
)
DEPENDENCY_UP = Gauge(
    "hermes_dependency_up",
    "1 if dependency is healthy, 0 if degraded.",
    labelnames=("dependency",),
)
DECISIONS_TOTAL = Counter(
    "hermes_decisions_total",
    "Total consensus decisions reached.",
    labelnames=("tenant_id", "action", "status"),
)
ASSESSMENTS_RECEIVED_TOTAL = Counter(
    "hermes_assessments_received_total",
    "Total agent assessments received.",
    labelnames=("tenant_id", "agent_id", "action"),
)
ASSESSMENTS_ELIGIBLE_RATIO = Gauge(
    "hermes_assessments_eligible_ratio",
    "Ratio of eligible to total assessments per decision.",
    labelnames=("tenant_id", "decision_id"),
)
MARKET_SNAPSHOT_AGE_SECONDS = Gauge(
    "hermes_market_snapshot_age_seconds",
    "Age of the most recent market snapshot from a given source.",
    labelnames=("tenant_id", "source_id", "instrument_id"),
)
MARKET_SNAPSHOT_DIVERGENCE_RATIO = Gauge(
    "hermes_market_snapshot_divergence_ratio",
    "Maximum relative price divergence across sources.",
    labelnames=("tenant_id", "instrument_id"),
)
EXECUTION_CREATED_TOTAL = Counter(
    "hermes_execution_created_total",
    "Total executions created.",
    labelnames=("tenant_id", "mode", "strategy_id"),
)
EXECUTION_AMBIGUOUS_TOTAL = Counter(
    "hermes_execution_ambiguous_total",
    "Total executions entering SUBMISSION_AMBIGUOUS.",
    labelnames=("tenant_id", "venue_id"),
)
EXECUTION_RECONCILIATION_FAILED_TOTAL = Counter(
    "hermes_execution_reconciliation_failed_total",
    "Total executions entering RECONCILIATION_FAILED.",
    labelnames=("tenant_id", "venue_id"),
)
VENUE_ORDERS_SUBMITTED_TOTAL = Counter(
    "hermes_venue_orders_submitted_total",
    "Total orders submitted to venues.",
    labelnames=("tenant_id", "venue_id", "side", "order_type"),
)
VENUE_ORDERS_ACKNOWLEDGED_TOTAL = Counter(
    "hermes_venue_orders_acknowledged_total",
    "Orders acknowledged by venue.",
    labelnames=("tenant_id", "venue_id"),
)
VENUE_ORDERS_REJECTED_TOTAL = Counter(
    "hermes_venue_orders_rejected_total",
    "Orders rejected by venue.",
    labelnames=("tenant_id", "venue_id", "reason_code"),
)
VENUE_ORDERS_AMBIGUOUS_TOTAL = Counter(
    "hermes_venue_orders_ambiguous_total",
    "Orders in ambiguous submission state.",
    labelnames=("tenant_id", "venue_id"),
)
VENUE_SUBMISSION_LATENCY_SECONDS = Histogram(
    "hermes_venue_submission_latency_seconds",
    "Latency from order submission to acknowledgement.",
    labelnames=("tenant_id", "venue_id", "venue_type"),
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0),
)
FILLS_RECEIVED_TOTAL = Counter(
    "hermes_fills_received_total",
    "Total fills received and reconciled.",
    labelnames=("tenant_id", "venue_id", "side"),
)
CIRCUIT_BREAKER_ACTIVATIONS_TOTAL = Counter(
    "hermes_circuit_breaker_activations_total",
    "Total circuit breaker activations.",
    labelnames=("tenant_id", "scope_type", "reason_code"),
)
CIRCUIT_BREAKER_RESETS_TOTAL = Counter(
    "hermes_circuit_breaker_resets_total",
    "Total circuit breaker resets.",
    labelnames=("tenant_id", "scope_type"),
)
CIRCUIT_BREAKER_ACTIVE = Gauge(
    "hermes_circuit_breaker_active",
    "1 if the breaker is ACTIVE, 0 if RESET.",
    labelnames=("tenant_id", "scope_type", "scope_id"),
)
CIRCUIT_BREAKER_CHECK_DURATION_SECONDS = Histogram(
    "hermes_circuit_breaker_check_duration_seconds",
    "Time to evaluate whether a circuit breaker blocks an operation.",
    labelnames=("scope_type",),
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.25, 0.5),
)
EXECUTION_STATE_TRANSITIONS_TOTAL = Counter(
    "hermes_execution_state_transitions_total",
    "Total number of execution state transitions.",
    labelnames=("tenant_id", "from_state", "to_state", "strategy_id", "venue_id", "mode"),
)
EXECUTION_TERMINAL_TOTAL = Counter(
    "hermes_execution_terminal_total",
    "Total executions reaching a terminal state.",
    labelnames=("tenant_id", "final_state", "mode"),
)
EXECUTION_DURATION_SECONDS = Histogram(
    "hermes_execution_duration_seconds",
    "Wall-clock duration from CREATED to a terminal state.",
    labelnames=("tenant_id", "final_state", "mode"),
    buckets=(1.0, 5.0, 15.0, 30.0, 60.0, 120.0, 300.0),
)
RISK_EVALUATIONS_TOTAL = Counter(
    "hermes_risk_evaluations_total",
    "Total risk evaluations completed.",
    labelnames=("tenant_id", "result"),
)
RISK_EVALUATION_DURATION_SECONDS = Histogram(
    "hermes_risk_evaluation_duration_seconds",
    "Time to complete a risk evaluation.",
    labelnames=("tenant_id",),
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0),
)
RISK_RULE_RESULTS_TOTAL = Counter(
    "hermes_risk_rule_results_total",
    "Per-rule evaluation outcomes.",
    labelnames=("tenant_id", "rule_name", "result"),
)
AUDIT_APPEND_LATENCY_SECONDS = Histogram(
    "hermes_audit_append_latency_seconds",
    "Latency of audit append operations.",
    labelnames=("tenant_id",),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5),
)
AUDIT_EVENTS_TOTAL = Counter(
    "hermes_audit_events_total",
    "Total audit events appended.",
    labelnames=("tenant_id", "actor_type", "result"),
)
AUDIT_APPEND_FAILURES_TOTAL = Counter(
    "hermes_audit_append_failures_total",
    "Total failed audit append operations.",
    labelnames=("tenant_id", "error_code"),
)


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        span_context = trace.get_current_span().get_span_context()
        trace_id = None
        span_id = None
        if span_context is not None and span_context.is_valid:
            trace_id = f"{span_context.trace_id:032x}"
            span_id = f"{span_context.span_id:016x}"

        payload = {
            "timestamp": _rfc3339_now(),
            "level": record.levelname,
            "service": settings.service_name,
            "version": settings.release_version,
            "source_commit": settings.source_commit,
            "image_digest": settings.image_digest,
            "trace_id": trace_id,
            "span_id": span_id,
            "tenant_id": getattr(record, "tenant_id", None) or _tenant_id.get(),
            "principal_id": getattr(record, "principal_id", None) or _principal_id.get(),
            "correlation_id": getattr(record, "correlation_id", None) or _correlation_id.get(),
            "request_id": getattr(record, "request_id", None) or _request_id.get(),
            "message": record.getMessage(),
            "error_code": getattr(record, "error_code", None),
            "execution_id": getattr(record, "execution_id", None) or _execution_id.get(),
        }
        return json.dumps(payload, separators=(",", ":"), default=str)


def configure_observability() -> None:
    global _observability_configured
    if _observability_configured:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter())
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        handlers=[handler],
        force=True,
    )

    resource = Resource.create(
        {
            "service.name": settings.service_name,
            "service.version": settings.release_version,
            "deployment.environment": settings.environment,
            "hermes.source_commit": settings.source_commit,
            "hermes.image_digest": settings.image_digest,
        }
    )
    provider = TracerProvider(resource=resource)
    if settings.otlp_endpoint:
        exporter = OTLPSpanExporter(endpoint=settings.otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _sync_deployment_circuit_breaker_state()
    _observability_configured = True


def extract_trace_context(headers: Mapping[str, str]) -> Any:
    return extract(headers)


@contextmanager
def start_hermes_span(
    name: str,
    *,
    parent_context: Any | None = None,
    attributes: Mapping[str, Any] | None = None,
) -> Iterator[Span]:
    tracer = trace.get_tracer(settings.service_name, settings.release_version)
    with tracer.start_as_current_span(name, context=parent_context) as span:
        _apply_standard_span_attributes(span)
        if attributes:
            for key, value in attributes.items():
                if value is not None:
                    span.set_attribute(key, value)
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_attribute("hermes.error_code", exc.__class__.__name__)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise


def set_request_context(*, request_id: str, correlation_id: str) -> None:
    _request_id.set(request_id)
    _correlation_id.set(correlation_id)


def clear_request_context() -> None:
    _request_id.set(None)
    _correlation_id.set(None)
    _tenant_id.set(None)
    _principal_id.set(None)
    _execution_id.set(None)


def bind_authenticated_context(principal_id: str, tenant_id: str) -> None:
    _principal_id.set(principal_id)
    _tenant_id.set(tenant_id)
    span = trace.get_current_span()
    if span is not None:
        _apply_standard_span_attributes(span)


def set_execution_context(execution_id: str | None) -> None:
    _execution_id.set(execution_id)
    span = trace.get_current_span()
    if span is not None and execution_id:
        span.set_attribute("execution_id", execution_id)


def current_tenant_id() -> str | None:
    return _tenant_id.get()


def record_http_server_metrics(method: str, route: str, status_code: int, tenant_id: str | None, duration_seconds: float) -> None:
    tenant_label = _label_value(tenant_id, "anonymous")
    status_label = str(status_code)
    route_label = route or "unknown"
    HTTP_REQUESTS_TOTAL.labels(method=method, route=route_label, status_code=status_label, tenant_id=tenant_label).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(method=method, route=route_label, status_code=status_label).observe(duration_seconds)


def set_dependency_state(dependency: str, status: str) -> None:
    DEPENDENCY_UP.labels(dependency=dependency).set(1 if status == "ready" else 0)


def record_decision_metrics(decision: dict[str, Any], tenant_id: str) -> None:
    tenant_label = _label_value(tenant_id)
    DECISIONS_TOTAL.labels(
        tenant_id=tenant_label,
        action=_label_value(decision.get("action")),
        status=_label_value(decision.get("status")),
    ).inc()
    assessments = decision.get("assessments", [])
    for assessment in assessments:
        ASSESSMENTS_RECEIVED_TOTAL.labels(
            tenant_id=tenant_label,
            agent_id=_label_value(assessment.get("agent_id")),
            action=_label_value(assessment.get("action")),
        ).inc()
    eligible_count = sum(1 for item in assessments if item.get("eligible", True))
    eligible_ratio = 0.0 if not assessments else eligible_count / len(assessments)
    ASSESSMENTS_ELIGIBLE_RATIO.labels(
        tenant_id=tenant_label,
        decision_id=_label_value(decision.get("id")),
    ).set(eligible_ratio)


def record_market_snapshot_metrics(snapshot: Any, tenant_id: str | None) -> None:
    tenant_label = _label_value(tenant_id, "anonymous")
    instrument_id = None
    captured_at = None
    source_prices = None
    if isinstance(snapshot, dict):
        instrument_id = snapshot.get("instrument_id")
        captured_at = snapshot.get("captured_at")
        source_prices = snapshot.get("source_prices")
    else:
        instrument_id = getattr(snapshot, "instrument_id", None)
        captured_at = getattr(snapshot, "captured_at", None)
        source_prices = getattr(snapshot, "source_prices", None)

    instrument_label = _label_value(instrument_id)
    observed_at = _coerce_datetime(captured_at)
    if observed_at is None:
        age_seconds = 0.0
    else:
        age_seconds = max((datetime.now(UTC) - observed_at).total_seconds(), 0.0)

    normalized_prices = {
        _label_value(source_id): float(price)
        for source_id, price in (source_prices or {}).items()
        if price is not None
    }
    if not normalized_prices:
        normalized_prices = {"synthetic-consensus": 0.0}

    for source_id in normalized_prices:
        MARKET_SNAPSHOT_AGE_SECONDS.labels(
            tenant_id=tenant_label,
            source_id=source_id,
            instrument_id=instrument_label,
        ).set(age_seconds)

    positive_prices = [price for price in normalized_prices.values() if price > 0]
    divergence_ratio = 0.0
    if positive_prices:
        baseline = sum(positive_prices) / len(positive_prices)
        if baseline > 0:
            divergence_ratio = max(positive_prices) - min(positive_prices)
            divergence_ratio /= baseline
    MARKET_SNAPSHOT_DIVERGENCE_RATIO.labels(
        tenant_id=tenant_label,
        instrument_id=instrument_label,
    ).set(divergence_ratio)


def record_venue_order_metrics(
    execution: dict[str, Any],
    tenant_id: str | None,
    *,
    submission_latency_seconds: float,
    venue_type: str,
) -> None:
    tenant_label = _label_value(tenant_id, "anonymous")
    venue_id = _label_value(execution.get("venue_id"))
    side = _label_value(execution.get("side"))
    order = execution.get("order") or {}
    fill = execution.get("fill") or {}
    transitions = {_label_value(state) for state in execution.get("transitions", []) if state}
    order_status = _label_value(order.get("status"))

    if "SUBMITTING" in transitions or order_status in {"SUBMITTED", "ACKNOWLEDGED", "FILLED", "AMBIGUOUS"}:
        VENUE_ORDERS_SUBMITTED_TOTAL.labels(
            tenant_id=tenant_label,
            venue_id=venue_id,
            side=side,
            order_type="MARKET",
        ).inc()
        VENUE_SUBMISSION_LATENCY_SECONDS.labels(
            tenant_id=tenant_label,
            venue_id=venue_id,
            venue_type=_label_value(venue_type),
        ).observe(submission_latency_seconds)
    if "ACKNOWLEDGED" in transitions or order_status in {"ACKNOWLEDGED", "FILLED"}:
        VENUE_ORDERS_ACKNOWLEDGED_TOTAL.labels(tenant_id=tenant_label, venue_id=venue_id).inc()
    if execution.get("state") == "SUBMISSION_AMBIGUOUS" or order_status == "AMBIGUOUS":
        VENUE_ORDERS_AMBIGUOUS_TOTAL.labels(tenant_id=tenant_label, venue_id=venue_id).inc()
    if order_status == "REJECTED" and execution.get("state") not in {"FAILED"}:
        VENUE_ORDERS_REJECTED_TOTAL.labels(
            tenant_id=tenant_label,
            venue_id=venue_id,
            reason_code="VENUE_REJECTED",
        ).inc()
    if _label_value(fill.get("status")) == "FILLED" and float(fill.get("notional", 0) or 0) > 0:
        FILLS_RECEIVED_TOTAL.labels(tenant_id=tenant_label, venue_id=venue_id, side=side).inc()


def record_circuit_breaker_check(scope_type: str, duration_seconds: float) -> None:
    CIRCUIT_BREAKER_CHECK_DURATION_SECONDS.labels(scope_type=_label_value(scope_type)).observe(duration_seconds)


def record_circuit_breaker_state_change(record: dict[str, Any], tenant_id: str | None) -> None:
    tenant_label = _label_value(tenant_id, "anonymous")
    scope_type = _label_value(record.get("scope_type"))
    scope_id = _label_value(record.get("scope_id"))
    state = _label_value(record.get("state"))

    CIRCUIT_BREAKER_ACTIVE.labels(
        tenant_id=tenant_label,
        scope_type=scope_type,
        scope_id=scope_id,
    ).set(1 if state == "ACTIVE" else 0)

    if state == "ACTIVE":
        CIRCUIT_BREAKER_ACTIVATIONS_TOTAL.labels(
            tenant_id=tenant_label,
            scope_type=scope_type,
            reason_code=_label_value(record.get("reason_code")),
        ).inc()
    else:
        CIRCUIT_BREAKER_RESETS_TOTAL.labels(
            tenant_id=tenant_label,
            scope_type=scope_type,
        ).inc()


def record_execution_metrics(
    execution: dict[str, Any],
    tenant_id: str,
    strategy_id: str,
    *,
    mode: str,
    previous_transitions: list[str] | None = None,
) -> None:
    tenant_label = _label_value(tenant_id)
    mode_label = _label_value(mode)
    venue_id = _label_value(execution.get("venue_id"))
    strategy_label = _label_value(strategy_id)
    transitions = [_label_value(state) for state in execution.get("transitions", []) if state]
    if not transitions:
        transitions = ["CREATED", _label_value(execution.get("state"))]

    prior = [_label_value(state) for state in (previous_transitions or []) if state]
    if prior and transitions[: len(prior)] == prior:
        transition_pairs = list(zip(transitions[len(prior) - 1 :], transitions[len(prior) :]))
    else:
        prior = []
        transition_pairs = list(zip(transitions, transitions[1:]))

    if not prior:
        EXECUTION_CREATED_TOTAL.labels(
            tenant_id=tenant_label,
            mode=mode_label,
            strategy_id=strategy_label,
        ).inc()

    for from_state, to_state in transition_pairs:
        EXECUTION_STATE_TRANSITIONS_TOTAL.labels(
            tenant_id=tenant_label,
            from_state=from_state,
            to_state=to_state,
            strategy_id=strategy_label,
            venue_id=venue_id,
            mode=mode_label,
        ).inc()

    terminal_states = {"RECONCILED", "RECONCILIATION_FAILED", "SUBMISSION_AMBIGUOUS", "REJECTED", "FAILED"}
    final_state = transitions[-1]
    previous_final_state = prior[-1] if prior else None
    newly_terminal = final_state in terminal_states and final_state != previous_final_state
    if newly_terminal:
        EXECUTION_TERMINAL_TOTAL.labels(
            tenant_id=tenant_label,
            final_state=final_state,
            mode=mode_label,
        ).inc()
    if final_state == "SUBMISSION_AMBIGUOUS" and final_state != previous_final_state:
        EXECUTION_AMBIGUOUS_TOTAL.labels(tenant_id=tenant_label, venue_id=venue_id).inc()
    if final_state == "RECONCILIATION_FAILED" and final_state != previous_final_state:
        EXECUTION_RECONCILIATION_FAILED_TOTAL.labels(tenant_id=tenant_label, venue_id=venue_id).inc()

    if newly_terminal:
        created_at = execution.get("created_at")
        updated_at = execution.get("updated_at")
        if isinstance(created_at, str) and isinstance(updated_at, str):
            try:
                started = datetime.fromisoformat(created_at)
                finished = datetime.fromisoformat(updated_at)
                EXECUTION_DURATION_SECONDS.labels(
                    tenant_id=tenant_label,
                    final_state=final_state,
                    mode=mode_label,
                ).observe(max(0.0, (finished - started).total_seconds()))
            except ValueError:
                pass


def record_risk_evaluation_metrics(risk_evaluation: Any, tenant_id: str | None, duration_seconds: float) -> None:
    tenant_label = _label_value(tenant_id, "anonymous")
    status = getattr(risk_evaluation, "status", None)
    rules = getattr(risk_evaluation, "rules", None)
    if status is None and isinstance(risk_evaluation, dict):
        status = risk_evaluation.get("status")
        rules = risk_evaluation.get("rules", [])
    RISK_EVALUATIONS_TOTAL.labels(tenant_id=tenant_label, result=_label_value(status)).inc()
    RISK_EVALUATION_DURATION_SECONDS.labels(tenant_id=tenant_label).observe(duration_seconds)
    for rule in rules or []:
        rule_name = getattr(rule, "rule_id", None)
        result = getattr(rule, "status", None)
        if isinstance(rule, dict):
            rule_name = rule.get("rule_id")
            result = rule.get("status")
        RISK_RULE_RESULTS_TOTAL.labels(
            tenant_id=tenant_label,
            rule_name=_label_value(rule_name),
            result=_label_value(result),
        ).inc()


def record_audit_append_success(tenant_id: str | None, actor_type: str, result: str, duration_seconds: float) -> None:
    tenant_label = _label_value(tenant_id, "anonymous")
    AUDIT_APPEND_LATENCY_SECONDS.labels(tenant_id=tenant_label).observe(duration_seconds)
    AUDIT_EVENTS_TOTAL.labels(
        tenant_id=tenant_label,
        actor_type=_label_value(actor_type),
        result=_label_value(result),
    ).inc()


def record_audit_append_failure(tenant_id: str | None, error_code: str, duration_seconds: float) -> None:
    tenant_label = _label_value(tenant_id, "anonymous")
    AUDIT_APPEND_LATENCY_SECONDS.labels(tenant_id=tenant_label).observe(duration_seconds)
    AUDIT_APPEND_FAILURES_TOTAL.labels(
        tenant_id=tenant_label,
        error_code=_label_value(error_code),
    ).inc()


def render_metrics() -> bytes:
    if not _observability_configured:
        configure_observability()
    return generate_latest()


def metrics_content_type() -> str:
    return CONTENT_TYPE_LATEST


def _apply_standard_span_attributes(span: Span) -> None:
    span.set_attribute("service.name", settings.service_name)
    span.set_attribute("service.version", settings.release_version)
    span.set_attribute("hermes.source_commit", settings.source_commit)
    span.set_attribute("hermes.image_digest", settings.image_digest)
    if _tenant_id.get():
        span.set_attribute("hermes.tenant_id", _tenant_id.get())
    if _correlation_id.get():
        span.set_attribute("hermes.correlation_id", _correlation_id.get())
    if _principal_id.get():
        span.set_attribute("hermes.principal_id", _principal_id.get())
    if _request_id.get():
        span.set_attribute("hermes.request_id", _request_id.get())
    if _execution_id.get():
        span.set_attribute("execution_id", _execution_id.get())


def _rfc3339_now() -> str:
    now_ns = time.time_ns()
    seconds, nanos = divmod(now_ns, 1_000_000_000)
    base = datetime.fromtimestamp(seconds, UTC).strftime("%Y-%m-%dT%H:%M:%S")
    return f"{base}.{nanos:09d}Z"


def _coerce_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
    return None


def _sync_deployment_circuit_breaker_state() -> None:
    global _deployment_breaker_synced
    if _deployment_breaker_synced:
        return
    tenant_label = "anonymous"
    scope_type = "deployment"
    scope_id = f"{settings.environment}:{settings.service_name}:live-execution"
    active = not settings.live_trading_enabled
    CIRCUIT_BREAKER_ACTIVE.labels(
        tenant_id=tenant_label,
        scope_type=scope_type,
        scope_id=scope_id,
    ).set(1 if active else 0)
    if active:
        CIRCUIT_BREAKER_ACTIVATIONS_TOTAL.labels(
            tenant_id=tenant_label,
            scope_type=scope_type,
            reason_code="LIVE_TRADING_DISABLED",
        ).inc()
    else:
        CIRCUIT_BREAKER_RESETS_TOTAL.labels(
            tenant_id=tenant_label,
            scope_type=scope_type,
        ).inc()
    _deployment_breaker_synced = True


def _label_value(value: Any, default: str = "unknown") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default
