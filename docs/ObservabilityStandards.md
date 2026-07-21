# Hermes Observability Standards

**Status:** Normative reference  
**Last revised:** 2026-07-20  
**Applies to:** All Hermes service components

This document defines the canonical OpenTelemetry metric names, trace span conventions, and structured log fields for the Hermes execution pipeline. Implementations MUST emit these signals to be considered conformant.

## 1. Metric Naming Conventions

All Hermes metrics use the `hermes_` prefix, follow [OpenMetrics](https://openmetrics.io/) naming, and are exported in Prometheus exposition format. Metric names are lowercase with underscores.

### 1.1 Execution Pipeline Metrics

| Metric name | Type | Labels | Description |
|---|---|---|---|
| `hermes_execution_state_transitions_total` | Counter | `tenant_id`, `from_state`, `to_state`, `strategy_id`, `venue_id`, `mode` | Total number of execution state transitions. Increment on every valid transition. |
| `hermes_execution_duration_seconds` | Histogram | `tenant_id`, `final_state`, `mode` | Wall-clock duration from `CREATED` to a terminal state. Buckets: 1s, 5s, 15s, 30s, 60s, 120s, 300s. |
| `hermes_execution_created_total` | Counter | `tenant_id`, `mode`, `strategy_id` | Total executions created. |
| `hermes_execution_terminal_total` | Counter | `tenant_id`, `final_state`, `mode` | Total executions reaching a terminal state (`RECONCILED`, `FAILED`, `CANCELLED`, `EXPIRED`, `REJECTED`, etc.). |
| `hermes_execution_ambiguous_total` | Counter | `tenant_id`, `venue_id` | Total executions entering `SUBMISSION_AMBIGUOUS`. MUST trigger an alert. |
| `hermes_execution_reconciliation_failed_total` | Counter | `tenant_id`, `venue_id` | Total executions entering `RECONCILIATION_FAILED`. |

### 1.2 Risk Evaluation Metrics

| Metric name | Type | Labels | Description |
|---|---|---|---|
| `hermes_risk_evaluations_total` | Counter | `tenant_id`, `result` (`APPROVED`\|`REJECTED`\|`EXPIRED`\|`FAILED`) | Total risk evaluations completed. |
| `hermes_risk_evaluation_duration_seconds` | Histogram | `tenant_id` | Time to complete a risk evaluation. Buckets: 10ms, 50ms, 100ms, 250ms, 500ms, 1s, 2s. |
| `hermes_risk_rule_results_total` | Counter | `tenant_id`, `rule_name`, `result` (`PASS`\|`FAIL`\|`UNKNOWN`) | Per-rule evaluation outcomes. |

### 1.3 Consensus & Decision Metrics

| Metric name | Type | Labels | Description |
|---|---|---|---|
| `hermes_decisions_total` | Counter | `tenant_id`, `action` (`BUY`\|`SELL`\|`HOLD`\|`NO_CONSENSUS`), `status` | Total consensus decisions reached. |
| `hermes_assessments_received_total` | Counter | `tenant_id`, `agent_id`, `action` | Total agent assessments received. |
| `hermes_assessments_eligible_ratio` | Gauge | `tenant_id`, `decision_id` | Ratio of eligible to total assessments per decision. |
| `hermes_market_snapshot_age_seconds` | Gauge | `tenant_id`, `source_id`, `instrument_id` | Age of the most recent market snapshot from a given source. MUST alert above the freshness threshold. |
| `hermes_market_snapshot_divergence_ratio` | Gauge | `tenant_id`, `instrument_id` | Maximum relative price divergence across sources. |

### 1.4 Venue & Order Metrics

| Metric name | Type | Labels | Description |
|---|---|---|---|
| `hermes_venue_orders_submitted_total` | Counter | `tenant_id`, `venue_id`, `side`, `order_type` | Total orders submitted to venues. |
| `hermes_venue_orders_acknowledged_total` | Counter | `tenant_id`, `venue_id` | Orders acknowledged by venue. |
| `hermes_venue_orders_rejected_total` | Counter | `tenant_id`, `venue_id`, `reason_code` | Orders rejected by venue. |
| `hermes_venue_orders_ambiguous_total` | Counter | `tenant_id`, `venue_id` | Orders in ambiguous submission state. |
| `hermes_venue_submission_latency_seconds` | Histogram | `tenant_id`, `venue_id`, `venue_type` | Latency from order submission to acknowledgement. Buckets: 100ms, 500ms, 1s, 2s, 5s, 10s. |
| `hermes_fills_received_total` | Counter | `tenant_id`, `venue_id`, `side` | Total fills received and reconciled. |

### 1.5 Circuit Breaker Metrics

| Metric name | Type | Labels | Description |
|---|---|---|---|
| `hermes_circuit_breaker_activations_total` | Counter | `tenant_id`, `scope_type`, `reason_code` | Total circuit breaker activations. |
| `hermes_circuit_breaker_resets_total` | Counter | `tenant_id`, `scope_type` | Total circuit breaker resets. |
| `hermes_circuit_breaker_active` | Gauge | `tenant_id`, `scope_type`, `scope_id` | 1 if the breaker is ACTIVE, 0 if RESET. |

### 1.6 Audit Chain Metrics

| Metric name | Type | Labels | Description |
|---|---|---|---|
| `hermes_audit_append_latency_seconds` | Histogram | `tenant_id` | Latency of `hermes.append_audit_event()` including advisory lock wait. Buckets: 5ms, 10ms, 25ms, 50ms, 100ms, 250ms, 500ms. |
| `hermes_audit_events_total` | Counter | `tenant_id`, `actor_type`, `result` | Total audit events appended. |
| `hermes_audit_append_failures_total` | Counter | `tenant_id`, `error_code` | Total failed `append_audit_event()` calls. |

### 1.7 Service Health Metrics

| Metric name | Type | Labels | Description |
|---|---|---|---|
| `hermes_http_requests_total` | Counter | `method`, `route`, `status_code`, `tenant_id` | Total HTTP requests. |
| `hermes_http_request_duration_seconds` | Histogram | `method`, `route`, `status_code` | HTTP request latency. Buckets: 10ms, 50ms, 100ms, 250ms, 500ms, 1s, 2s, 5s. |
| `hermes_dependency_up` | Gauge | `dependency` (`postgres`\|`redis`\|`queue`\|`identity_provider`) | 1 if dependency is healthy, 0 if degraded. |
| `hermes_circuit_breaker_check_duration_seconds` | Histogram | `scope_type` | Time to evaluate whether a circuit breaker blocks an operation. |

## 2. OpenTelemetry Trace Span Conventions

All service operations that cross a network boundary or take more than 1 ms MUST be wrapped in an OpenTelemetry span. Spans MUST propagate W3C TraceContext headers.

### 2.1 Required Span Attributes

Every span emitted by a Hermes service MUST include:

| Attribute | Type | Description |
|---|---|---|
| `hermes.tenant_id` | string (UUID) | The resolved tenant identifier. |
| `hermes.correlation_id` | string (UUID) | The request correlation ID. |
| `hermes.principal_id` | string (UUID) | The authenticated principal identifier. |
| `hermes.request_id` | string (UUID) | The `X-Request-ID` header value. |
| `service.name` | string | Hermes service name (e.g., `hermes-api`, `hermes-worker`). |
| `service.version` | string | Deployed application version. |

### 2.2 Execution Pipeline Span Names

| Span name | Description |
|---|---|
| `hermes.execution.create` | Create and persist a new execution record. |
| `hermes.consensus.evaluate` | Run multi-agent consensus and produce a decision. |
| `hermes.risk.evaluate` | Run the deterministic risk policy engine. |
| `hermes.approval.wait` | Wait for an authorized approver action. |
| `hermes.signing.request` | Request a signing envelope from the signer. |
| `hermes.venue.submit` | Submit an order or transaction to the venue adapter. |
| `hermes.venue.observe` | Poll or stream acknowledgement and fill events. |
| `hermes.reconciliation.run` | Reconcile fills, fees, receipts, and balances. |
| `hermes.audit.append` | Append an event to the tenant audit chain. |

### 2.3 Span Status and Error Handling

- Set span status to `ERROR` and record the exception on all unhandled errors.
- Add `hermes.error_code` as a span attribute on all application-level rejections.
- Do NOT record raw private keys, secret values, bearer tokens, or PII in span attributes or events.

## 3. Structured Log Fields

All log records MUST be emitted as JSON and include the following fields:

```json
{
  "timestamp": "<RFC 3339 with nanoseconds>",
  "level": "INFO | WARN | ERROR | DEBUG",
  "service": "hermes-api",
  "version": "<semver>",
  "trace_id": "<W3C trace ID>",
  "span_id": "<W3C span ID>",
  "tenant_id": "<uuid>",
  "principal_id": "<uuid>",
  "correlation_id": "<uuid>",
  "request_id": "<uuid>",
  "message": "<human-readable summary>",
  "error_code": "<application error code, if applicable>",
  "execution_id": "<uuid, if applicable>"
}
```

Do NOT log raw signing envelopes, bearer tokens, private keys, seed phrases, CEX secrets, or unredacted personal information.
