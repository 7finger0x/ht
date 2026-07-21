# Hermes API Mocking Collection

**Status:** Reference  
**Last revised:** 2026-07-20

This document provides OpenAPI-aligned example API requests for local development and analytical agent testing. Prefer [Prism](https://stoplight.io/open-source/prism) against `openapi/hermes.openapi.yaml`. A Bruno/Postman collection directory is not shipped in this package; copy examples from this document or from [APIReference](APIReference.md).

## Example Request Payloads

### POST /v1/decision-evaluations — Submit Decision Evaluation

```json
{
  "strategy_id": "6252e7a4-0eb9-4ead-bade-ad1c9acb9313",
  "instrument_id": "BTC-USDT",
  "mode": "SIMULATION",
  "venue_ids": ["paper-cex"],
  "client_reference": "research-run-2026-07-20"
}
```

Required headers:
```
Authorization: Bearer <token>
Idempotency-Key: <uuid-v4>
X-Request-ID: <uuid-v4>
```

The server captures the snapshot. Clients do not post assessments or snapshot IDs on this endpoint.

### POST /v1/executions — Submit an Execution

```json
{
  "decision_id": "585da6d7-7520-484c-a79c-e1cd1f23c909",
  "portfolio_id": "312228de-856b-4f0f-91b4-6dde638a0e5e",
  "venue_id": "paper-cex",
  "constraints": {
    "max_quantity": "0.05000000",
    "max_notional": "5000.00",
    "limit_price": null,
    "stop_price": null,
    "order_type_preference": "MARKET",
    "time_in_force": "IOC",
    "client_reference": "allocation-17"
  }
}
```

Required headers:
```
Authorization: Bearer <token>
Idempotency-Key: <uuid-v4>
X-Request-ID: <uuid-v4>
```

### GET /v1/executions/{execution_id} — Retrieve an Execution

```
GET /v1/executions/66000000-0000-0000-0000-000000000001
Authorization: Bearer <token>
X-Request-ID: <uuid-v4>
```

### POST /v1/executions/{execution_id}/approve — Approve an Execution

```json
{
  "intent_digest": "sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "decision": "APPROVED",
  "comment": "Approved under change ticket CHG-2041."
}
```

Required headers:
```
Authorization: Bearer <token>
Idempotency-Key: <uuid-v4>
X-Request-ID: <uuid-v4>
```

### POST /v1/circuit-breakers/{scope_type}/{scope_id}/activate — Activate a Circuit Breaker

```json
{
  "reason_code": "VENUE_DEGRADED",
  "reason": "Elevated order acknowledgement latency exceeding 5s SLA."
}
```

Example path: `POST /v1/circuit-breakers/venue/paper-cex/activate`

### GET /v1/audit/events — Query Audit Events

```
GET /v1/audit/events?correlation_id=550e8400-e29b-41d4-a716-446655440000&limit=50
Authorization: Bearer <token>
X-Request-ID: <uuid-v4>
```

## Local Mock Server

For fully offline development, use Prism to serve the OpenAPI spec:

```bash
npm install -g @stoplight/prism-cli

# Start mock server on port 4010
prism mock openapi/hermes.openapi.yaml --port 4010

# All 20 endpoints will respond with spec-conformant example responses
curl -s http://localhost:4010/v1/health/live | jq .
```

Prism uses the `examples` defined in the OpenAPI spec to generate realistic responses. No backend, database, or authentication infrastructure is required.

## Testing Analytical Agents Against the Mock

Set the agent's API base URL to `http://localhost:4010` and provide any string as the Bearer token. The mock server does not validate authentication. This allows:

- validation of request/response shape against the OpenAPI contract;
- CI pipeline tests that do not require live credentials or a running Hermes service.
