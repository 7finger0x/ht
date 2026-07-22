# Hermes API Reference

**Authoritative contract:** [`openapi/hermes.openapi.yaml`](../openapi/hermes.openapi.yaml)  
**Version:** 1.0.0-draft  
**Last revised:** 2026-07-21

## 1. Contract rules

- OpenAPI 3.1.2 is the source of truth. FastAPI/Pydantic models and generated clients must conform to it or be generated from the same model source.
- All identifiers use UUIDs unless a schema explicitly defines a stable string identifier.
- Timestamps are RFC 3339 UTC values.
- Quantities, prices, money, percentages, and ratios are decimal strings. Clients must not use binary floating-point for financial calculations.
- Unknown fields are rejected on safety-critical request objects.
- The API is asynchronous for decision and execution workflows. `202 Accepted` does not mean consensus, risk approval, venue acknowledgement, or fill.
- Tenant identity is derived from verified authentication and membership. `X-Hermes-Tenant-ID` selects an authorized membership; it is not proof of ownership.
- Internal database tables are not a public API.

## 2. Authentication

Send a short-lived identity-provider access token:

```http
Authorization: Bearer <access-token>
```

The API verifies the signature, issuer, audience/application, expiration, token type, subject, session, and tenant membership. A token for another Hermes environment is rejected.

The browser must not receive a Supabase service-role/secret key, database password, CEX credential, signer key, or AI-provider secret.

### 2.1 Machine-readable authorization contract

Every authenticated tenant operation declares both `x-hermes-allowed-roles` and `x-hermes-required-scopes` in OpenAPI. Authorization requires an active tenant membership, one listed role, every listed scope, resource visibility, and all current policy conditions. A role alone is never sufficient. `/v1/me` instead declares `x-hermes-authorization: authenticated-principal` because it resolves membership rather than acting inside a selected tenant.

| Surface | Allowed roles | Required scope |
|---|---|---|
| Venue, decision, execution, control, and audit reads | Tenant roles listed on the operation | The operation-specific `*:read` scope |
| Create decision evaluation | `operator`, `trader`, `tenant_admin` | `decisions:create` |
| Create execution | `trader`, `tenant_admin` | `executions:create` |
| Record approval decision | `approver` | `executions:approve` |
| Request cancellation | `operator`, `trader`, `tenant_admin`, `security_admin` | `executions:cancel` |
| Activate tenant circuit breaker | `operator`, `tenant_admin`, `security_admin` | `controls:activate` |
| Reset tenant circuit breaker | `tenant_admin`, `security_admin` | `controls:reset` plus step-up authentication |
| Read dependency health | `platform_admin` | `platform:health:read` |

`platform_admin` has no routine authority on tenant endpoints. Temporary support access requires a separately modeled, time-bounded tenant authorization and is not inferred from the platform role.

### 2.2 Health surfaces

`GET /v1/health/live` is a public liveness probe that returns process status plus `service`, `environment`, `version`, and `request_id`. `GET /v1/health/ready` is a public readiness probe that returns aggregate readiness plus `mode`, `live_trading_enabled`, `auth_provider`, `version`, and `time`. Named dependency status is available only through authenticated `GET /v1/health/dependencies` to the platform-health role and scope.

## 3. Tenant selection

A principal with one active tenant may omit the selector. A principal with more than one active membership sends:

```http
X-Hermes-Tenant-ID: 76dd04d5-0c4a-4ea8-9cab-43828a5ab5c1
```

The server verifies that the principal is active in that tenant and builds the authorization context. Request bodies do not contain authoritative `owner_id` or `tenant_id` fields.

## 4. Idempotency

Every mutating endpoint requires:

```http
Idempotency-Key: 01J3WQ3T2R8R6Q5M8M0V4KABCD
```

The key is scoped to tenant, principal, HTTP method, and route.

- Same key and same canonical request: returns the original success or error result and sets `Idempotency-Replayed: true`.
- Same key and different canonical request: returns `409 IDEMPOTENCY_KEY_REUSED`.
- A timeout does not mean the request failed and does not permit a different retry key for the same economic action. Query the resource or replay the same key.

Execution also uses an economic uniqueness constraint and a venue client order ID or transaction-intent digest.

## 5. Correlation and errors

Clients may send `X-Request-ID`; every authenticated success and error response returns a validated request ID. Invalid client values are replaced rather than reflected. Errors use `application/problem+json`. A replayed stored error from a mutating request also returns `Idempotency-Replayed: true`:

```json
{
  "type": "/problems/stale-state",
  "title": "Required market state is stale",
  "status": 422,
  "code": "STALE_MARKET_SNAPSHOT",
  "detail": "The quote exceeded the configured 15-second age limit.",
  "request_id": "req_01J3WQ4DA3A1F75E1R8QW7J0QH",
  "errors": []
}
```

Expected status codes include:

| Status | Meaning |
|---|---|
| `400` | Malformed or semantically invalid request |
| `401` | Missing, invalid, expired, or wrong-environment token |
| `403` | Membership, role, scope, or resource access denied |
| `404` | Resource absent or intentionally hidden from this tenant |
| `409` | Idempotency mismatch, state transition conflict, or duplicate economic action |
| `422` | Valid schema but policy/staleness/precision prevents acceptance |
| `429` | Rate or concurrency limit; honor `Retry-After` |
| `503` | Required dependency or safety state unavailable |

## 6. Primary workflow

### 6.1 Request a decision evaluation

```http
POST /v1/decision-evaluations
Authorization: Bearer <access-token>
X-Hermes-Tenant-ID: 76dd04d5-0c4a-4ea8-9cab-43828a5ab5c1
Idempotency-Key: 01J3WQ3T2R8R6Q5M8M0V4KABCD
Content-Type: application/json
```

```json
{
  "instrument_id": "BTC-USDT",
  "strategy_id": "strategy-paper-001",
  "portfolio_id": "portfolio-paper-001",
  "market_bias": 0.3,
  "volatility": 0.3
}
```

The server captures the snapshot. Clients do not post RSI, ATR, headlines, or other mutable values as authoritative execution inputs.

### 6.2 Read the decision

The current MVP exposes both `GET /v1/decisions` and `GET /v1/decisions/{decision_id}`. Both surfaces return the live `DecisionRecord` shape with `snapshot`, `assessments`, consensus weights, and the persisted decision digest.

### 6.3 Request execution

```http
POST /v1/executions
Idempotency-Key: 01J3WQA0E2Y0FRZE4H8EQYJ7SV
Content-Type: application/json
```

```json
{
  "decision_id": "585da6d7-7520-484c-a79c-e1cd1f23c909",
  "requested_notional": 5000,
  "side": "BUY",
  "venue_id": "paper-venue-001"
}
```

The server accepts the requested notional, uses the provided side when present, and defaults `venue_id` when omitted. Deterministic risk evaluation is returned as the workflow advances.

### 6.4 Approve an execution

An approval binds to the exact current intent digest:

```json
{
  "intent_digest": "sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "decision": "APPROVED",
  "comment": "Approved under change ticket CHG-2041."
}
```

Before posting approval, retrieve the current execution and use its current `intent_digest`. The server accepts a decision only in `APPROVAL_PENDING` and only when the supplied digest matches the current immutable intent. The resulting approval record repeats the execution, order-intent, and risk-evaluation identifiers so the binding is independently inspectable.

### 6.5 Executions and circuit breakers

`GET /v1/executions` returns an array of execution records. `GET /v1/executions/{execution_id}` and `POST /v1/executions/{execution_id}/approve` return a single execution record.

Circuit-breaker endpoints manage tenant-local scopes only: tenant, strategy, portfolio, venue, account, network, and instrument. Activate requires `reason_code` and `reason`, with optional `evidence_refs`. Reset requires `reason_code`, `reason`, and at least one `evidence_refs` item. `GET /v1/circuit-breakers` returns an `AcceptedResponse` wrapper whose `data` array contains `CircuitBreakerRecord` items. The deployment-wide emergency stop is an out-of-band operator control and is intentionally absent from the tenant API and cannot be reset through it.

## 7. Execution states

The exact enum is in OpenAPI. The current MVP execution states are:

- `CREATED`;
- `RISK_APPROVED`;
- `RISK_REJECTED`;
- `APPROVAL_PENDING`;
- `READY_TO_SUBMIT`;
- `SIGNING`;
- `SIGNING_FAILED`;
- `SUBMITTING`;
- `SUBMISSION_AMBIGUOUS`;
- `ACKNOWLEDGED`;
- `FILLED`;
- `RECONCILING`;
- `RECONCILIATION_FAILED`;
- `RECONCILED`;
- `REJECTED`;
- `FAILED`.

## 8. Collection responses

The current MVP list endpoints return JSON arrays directly:

```http
GET /v1/decisions
GET /v1/executions
GET /v1/audit/events
```

`GET /v1/circuit-breakers` is the exception: it returns an `AcceptedResponse` object whose `data` field contains the array of circuit-breaker records.

## 9. Rate and concurrency limits

Limits are deployment- and endpoint-specific. The server may constrain:

- requests per principal, tenant, IP security signal, route, venue, strategy, and account;
- concurrent decision evaluations and executions;
- provider and venue quotas;
- maximum pending or ambiguous executions.

A `429` response includes `Retry-After`. Trading clients must still respect decision, quote, approval, and intent expiry; retrying after expiry requires a new evaluation.

## 10. Audit read model

`GET /v1/audit/events` is tenant-filtered and read-only. It returns an array of `AuditEvent` objects with `id`, `occurred_at`, `action`, `result`, `resource_type`, `resource_id`, `correlation_id`, and an opaque `payload` object. Application roles cannot insert, update, or delete audit rows directly; audited services append through the serialized database function described in the data and security contracts.

The live MVP surface does not currently expose sequence counters or digest-chain fields on the API response, so consumers should treat `payload` as the detailed event envelope and use server-side evidence workflows for deeper chain verification.

## 12. Compatibility policy

- Breaking changes use a new major path such as `/v2` or a negotiated contract version.
- Adding an optional response field is non-breaking, but generated clients should tolerate it only where the schema permits.
- Enum additions are treated as potentially breaking for trading clients and require notice.
- Safety-rule, precision, venue, and state-machine changes follow controlled release procedures even when the HTTP shape does not change.
- Deprecated behavior receives a documented migration and end date before removal, except urgent security measures.

## 13. External standard

The contract was revalidated on 2026-07-20 against the [OpenAPI Specification 3.1.2](https://spec.openapis.org/oas/v3.1.2.html). Hermes uses `x-hermes-*` specification extensions for machine-readable authorization requirements while retaining standard OpenAPI security schemes for bearer authentication.
