from __future__ import annotations

import os
import sys
from pathlib import Path

import jwt
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "services/api/test_mvp.db"
PRIMARY_TENANT_ID = "11111111-1111-1111-1111-111111111111"
PRIMARY_PRINCIPAL_ID = "22222222-2222-2222-2222-222222222222"
SECONDARY_TENANT_ID = "33333333-3333-3333-3333-333333333333"
SECONDARY_PRINCIPAL_ID = "44444444-4444-4444-4444-444444444444"
os.environ["HERMES_DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["HERMES_ALLOWED_ORIGINS"] = "http://localhost:5173"
os.environ["HERMES_AUTH_PROVIDER"] = "test-jwt"
os.environ["HERMES_AUTH_JWT_ALGORITHM"] = "HS256"
os.environ["HERMES_AUTH_JWT_SECRET"] = "unit-test-secret"
os.environ["HERMES_AUTH_ISSUER"] = "https://auth.test.hermes"
os.environ["HERMES_AUTH_AUDIENCE"] = "hermes-test-audience"
os.environ["HERMES_ENABLE_DEV_AUTH_BOOTSTRAP"] = "true"
os.environ["HERMES_RELEASE_VERSION"] = "test-build"

sys.path.insert(0, str(ROOT / "services/api"))

from app.db import init_db  # noqa: E402
from app.main import app  # noqa: E402


client = TestClient(app)


def auth_headers(
    *,
    scopes: str = "decisions:create decisions:read executions:create executions:read executions:approve audit:read controls:read controls:activate controls:reset",
    tenant_id: str = PRIMARY_TENANT_ID,
    principal_id: str = PRIMARY_PRINCIPAL_ID,
    subject: str = "privy-user-001",
    extra_headers: dict[str, str] | None = None,
) -> dict[str, str]:
    token = jwt.encode(
        {
            "sub": subject,
            "principal_id": principal_id,
            "tenant_id": tenant_id,
            "roles": ["tenant_admin", "trader"],
            "scope": scopes,
            "iss": "https://auth.test.hermes",
            "aud": "hermes-test-audience",
        },
        "unit-test-secret",
        algorithm="HS256",
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Hermes-Tenant-ID": tenant_id,
    }
    if extra_headers:
        headers.update(extra_headers)
    return headers


def setup_function() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    init_db()


def test_health_and_identity_endpoints() -> None:
    live = client.get("/v1/health/live")
    ready = client.get("/v1/health/ready")
    principal = client.get("/v1/me", headers=auth_headers())

    assert live.status_code == 200
    assert ready.status_code == 200
    assert principal.status_code == 200
    assert live.json()["status"] == "live"
    assert live.json()["version"] == "test-build"
    assert "time" in ready.json()
    assert live.headers["x-request-id"]
    assert ready.headers["x-request-id"]
    assert principal.json()["tenant_id"] == PRIMARY_TENANT_ID
    assert principal.json()["principal_id"] == PRIMARY_PRINCIPAL_ID


def test_request_id_header_is_propagated() -> None:
    response = client.get("/v1/health/live", headers={"X-Request-ID": "req-observability-001"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "req-observability-001"
    assert response.json()["request_id"] == "req-observability-001"


def test_decision_to_execution_flow() -> None:
    decision_response = client.post(
        "/v1/decision-evaluations",
        headers=auth_headers(extra_headers={"Idempotency-Key": "decision-001"}),
        json={
            "instrument_id": "BTC-USD",
            "strategy_id": "strategy-paper-001",
            "portfolio_id": "portfolio-paper-001",
            "market_bias": 0.55,
            "volatility": 0.22,
        },
    )
    assert decision_response.status_code == 202
    assert decision_response.headers["idempotency-replayed"] == "false"

    decision_id = decision_response.json()["data"]["decision_id"]
    decision_record = client.get(f"/v1/decisions/{decision_id}", headers=auth_headers())
    assert decision_record.status_code == 200
    assert decision_record.json()["status"] == "ACCEPTED"

    execution_response = client.post(
        "/v1/executions",
        headers=auth_headers(extra_headers={"Idempotency-Key": "execution-001"}),
        json={
            "decision_id": decision_id,
            "requested_notional": 5000,
            "venue_id": "paper-venue-001",
        },
    )
    assert execution_response.status_code == 202
    assert execution_response.headers["idempotency-replayed"] == "false"
    assert execution_response.json()["data"]["state"] == "APPROVAL_PENDING"

    execution_id = execution_response.json()["data"]["execution_id"]
    execution_record = client.get(f"/v1/executions/{execution_id}", headers=auth_headers())

    assert execution_record.status_code == 200
    assert execution_record.json()["state"] == "APPROVAL_PENDING"
    assert execution_record.json()["approval"] is None
    assert execution_record.json()["order"]["status"] == "PENDING_APPROVAL"

    approval_response = client.post(
        f"/v1/executions/{execution_id}/approve",
        headers=auth_headers(extra_headers={"Idempotency-Key": "approval-001"}),
        json={
            "intent_digest": execution_record.json()["intent_digest"],
            "decision": "APPROVED",
            "comment": "Approved for simulated submission.",
        },
    )
    assert approval_response.status_code == 200
    assert approval_response.headers["idempotency-replayed"] == "false"
    assert approval_response.json()["state"] == "RECONCILED"
    assert approval_response.json()["approval"]["decision"] == "APPROVED"
    assert approval_response.json()["order"]["status"] == "FILLED"
    assert approval_response.json()["fill"]["status"] == "FILLED"

    audit_events = client.get("/v1/audit/events", headers=auth_headers())

    assert audit_events.status_code == 200
    assert len(audit_events.json()) == 3
    assert {event["action"] for event in audit_events.json()} == {
        "decision.evaluate",
        "execution.created",
        "execution.approved",
    }
    assert {event["result"] for event in audit_events.json()} == {"SUCCESS", "PENDING"}
    assert all(event["payload"]["tenant_id"] == PRIMARY_TENANT_ID for event in audit_events.json())
    assert {
        event["correlation_id"] for event in audit_events.json()
    } == {
        decision_response.headers["x-request-id"],
        execution_response.headers["x-request-id"],
        approval_response.headers["x-request-id"],
    }


def test_idempotency_replay_returns_same_response() -> None:
    headers = auth_headers(extra_headers={"Idempotency-Key": "decision-replay-001"})
    payload = {
        "instrument_id": "BTC-USD",
        "strategy_id": "strategy-paper-001",
        "portfolio_id": "portfolio-paper-001",
        "market_bias": 0.55,
        "volatility": 0.22,
    }

    first_response = client.post("/v1/decision-evaluations", headers=headers, json=payload)
    replay_response = client.post("/v1/decision-evaluations", headers=headers, json=payload)

    assert first_response.status_code == 202
    assert replay_response.status_code == 202
    assert replay_response.headers["idempotency-replayed"] == "true"
    assert first_response.json() == replay_response.json()


def test_execution_rejects_non_executable_decision() -> None:
    rejected_decision = client.post(
        "/v1/decision-evaluations",
        headers=auth_headers(extra_headers={"Idempotency-Key": "decision-reject-001"}),
        json={
            "instrument_id": "ETH-USD",
            "strategy_id": "strategy-paper-001",
            "portfolio_id": "portfolio-paper-001",
            "market_bias": 0.0,
            "volatility": 0.95,
        },
    )
    assert rejected_decision.status_code == 202

    decision_id = rejected_decision.json()["data"]["decision_id"]
    execution_response = client.post(
        "/v1/executions",
        headers=auth_headers(extra_headers={"Idempotency-Key": "execution-reject-001"}),
        json={
            "decision_id": decision_id,
            "requested_notional": 5000,
        },
    )

    assert execution_response.status_code == 409
    assert "not executable" in execution_response.text


def test_tenant_isolation_filters_records() -> None:
    decision_response = client.post(
        "/v1/decision-evaluations",
        headers=auth_headers(extra_headers={"Idempotency-Key": "decision-tenant-001"}),
        json={
            "instrument_id": "SOL-USD",
            "strategy_id": "strategy-paper-001",
            "portfolio_id": "portfolio-paper-001",
            "market_bias": 0.51,
            "volatility": 0.25,
        },
    )
    assert decision_response.status_code == 202

    decision_id = decision_response.json()["data"]["decision_id"]
    secondary_headers = auth_headers(
        tenant_id=SECONDARY_TENANT_ID,
        principal_id=SECONDARY_PRINCIPAL_ID,
        subject="privy-user-002",
    )

    tenant_scoped_list = client.get("/v1/decisions", headers=secondary_headers)
    tenant_scoped_get = client.get(f"/v1/decisions/{decision_id}", headers=secondary_headers)
    tenant_scoped_audit = client.get("/v1/audit/events", headers=secondary_headers)

    assert tenant_scoped_list.status_code == 200
    assert tenant_scoped_list.json() == []
    assert tenant_scoped_get.status_code == 404
    assert tenant_scoped_audit.status_code == 200
    assert tenant_scoped_audit.json() == []


def test_mismatched_tenant_header_is_rejected() -> None:
    response = client.get(
        "/v1/me",
        headers=auth_headers(extra_headers={"X-Hermes-Tenant-ID": SECONDARY_TENANT_ID}),
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "unauthorized_tenant_selection"


def test_dependency_readiness_endpoint() -> None:
    response = client.get(
        "/v1/health/dependencies",
        headers=auth_headers(scopes="platform:health:read"),
    )

    assert response.status_code == 200
    assert response.json()["status"] in {"ready", "degraded"}
    assert any(item["name"] == "database" for item in response.json()["dependencies"])


def test_metrics_endpoint_exposes_http_and_dependency_metrics() -> None:
    decision_response = client.post(
        "/v1/decision-evaluations",
        headers=auth_headers(extra_headers={"Idempotency-Key": "metrics-decision-001"}),
        json={
            "instrument_id": "BTC-USD",
            "strategy_id": "strategy-paper-001",
            "portfolio_id": "portfolio-paper-001",
            "market_bias": 0.55,
            "volatility": 0.22,
        },
    )
    decision_id = decision_response.json()["data"]["decision_id"]
    execution_response = client.post(
        "/v1/executions",
        headers=auth_headers(extra_headers={"Idempotency-Key": "metrics-execution-001"}),
        json={
            "decision_id": decision_id,
            "requested_notional": 5000,
            "venue_id": "paper-venue-001",
        },
    )
    execution_id = execution_response.json()["data"]["execution_id"]
    pending_execution = client.get(f"/v1/executions/{execution_id}", headers=auth_headers())
    client.post(
        f"/v1/executions/{execution_id}/approve",
        headers=auth_headers(extra_headers={"Idempotency-Key": "metrics-approval-001"}),
        json={
            "intent_digest": pending_execution.json()["intent_digest"],
            "decision": "APPROVED",
            "comment": "Metrics coverage approval.",
        },
    )
    client.post(
        "/v1/circuit-breakers/tenant/global/activate",
        headers=auth_headers(extra_headers={"Idempotency-Key": "metrics-breaker-001"}),
        json={
            "reason_code": "MANUAL_STOP",
            "reason": "Metrics coverage breaker activation.",
            "evidence_refs": ["metrics-case-001"],
        },
    )
    client.get("/v1/health/live", headers={"X-Request-ID": "metrics-live-001"})
    client.get(
        "/v1/health/dependencies",
        headers=auth_headers(scopes="platform:health:read", extra_headers={"X-Request-ID": "metrics-deps-001"}),
    )

    metrics_response = client.get("/metrics")

    assert metrics_response.status_code == 200
    assert "text/plain" in metrics_response.headers["content-type"]
    body = metrics_response.text
    assert "hermes_http_requests_total" in body
    assert "hermes_http_request_duration_seconds" in body
    assert "hermes_dependency_up" in body
    assert "hermes_execution_state_transitions_total" in body
    assert "hermes_market_snapshot_age_seconds" in body
    assert "hermes_market_snapshot_divergence_ratio" in body
    assert "hermes_venue_orders_submitted_total" in body
    assert "hermes_venue_orders_acknowledged_total" in body
    assert "hermes_fills_received_total" in body
    assert "hermes_circuit_breaker_active" in body
    assert "hermes_circuit_breaker_activations_total" in body
    assert "hermes_circuit_breaker_check_duration_seconds" in body
    assert 'route="/v1/health/live"' in body
    assert 'dependency="postgres"' in body
    assert 'from_state="CREATED"' in body
    assert 'to_state="APPROVAL_PENDING"' in body
    assert 'to_state="RECONCILED"' in body
    assert 'source_id="synthetic-primary"' in body
    assert 'source_id="synthetic-secondary"' in body
    assert 'instrument_id="BTC-USD"' in body
    assert 'scope_type="deployment"' in body
    assert 'scope_type="tenant"' in body
    assert 'reason_code="MANUAL_STOP"' in body
    assert 'order_type="MARKET"' in body


def test_approval_rejection_flow() -> None:
    decision_response = client.post(
        "/v1/decision-evaluations",
        headers=auth_headers(extra_headers={"Idempotency-Key": "decision-reject-flow-001"}),
        json={
            "instrument_id": "ETH-USD",
            "strategy_id": "strategy-paper-001",
            "portfolio_id": "portfolio-paper-001",
            "market_bias": 0.44,
            "volatility": 0.18,
        },
    )
    assert decision_response.status_code == 202

    decision_id = decision_response.json()["data"]["decision_id"]
    execution_response = client.post(
        "/v1/executions",
        headers=auth_headers(extra_headers={"Idempotency-Key": "execution-reject-flow-001"}),
        json={
            "decision_id": decision_id,
            "requested_notional": 4000,
            "venue_id": "paper-venue-001",
        },
    )
    assert execution_response.status_code == 202

    execution_id = execution_response.json()["data"]["execution_id"]
    pending_execution = client.get(f"/v1/executions/{execution_id}", headers=auth_headers())
    assert pending_execution.status_code == 200
    assert pending_execution.json()["state"] == "APPROVAL_PENDING"

    rejection_response = client.post(
        f"/v1/executions/{execution_id}/approve",
        headers=auth_headers(extra_headers={"Idempotency-Key": "approval-reject-001"}),
        json={
            "intent_digest": pending_execution.json()["intent_digest"],
            "decision": "REJECTED",
            "comment": "Risk desk rejected the simulated order.",
        },
    )

    assert rejection_response.status_code == 200
    assert rejection_response.json()["state"] == "REJECTED"
    assert rejection_response.json()["approval"]["decision"] == "REJECTED"
    assert rejection_response.json()["order"]["status"] == "REJECTED"
    assert rejection_response.json()["fill"]["status"] == "PENDING"



def test_circuit_breaker_lifecycle_and_enforcement() -> None:
    activate_response = client.post(
        f"/v1/circuit-breakers/tenant/{PRIMARY_TENANT_ID}/activate",
        headers=auth_headers(extra_headers={"Idempotency-Key": "breaker-activate-001"}),
        json={
            "reason_code": "MANUAL_STOP",
            "reason": "Operator paused trading for verification.",
            "evidence_refs": ["ticket-123"],
        },
    )

    assert activate_response.status_code == 200
    assert activate_response.json()["scope_type"] == "tenant"
    assert activate_response.json()["scope_id"] == PRIMARY_TENANT_ID
    assert activate_response.json()["state"] == "ACTIVE"
    assert activate_response.json()["reason_code"] == "MANUAL_STOP"

    list_response = client.get("/v1/circuit-breakers", headers=auth_headers())

    assert list_response.status_code == 200
    assert list_response.json()["accepted"] is True
    assert list_response.json()["data"] == [activate_response.json()]

    decision_response = client.post(
        "/v1/decision-evaluations",
        headers=auth_headers(extra_headers={"Idempotency-Key": "decision-breaker-001"}),
        json={
            "instrument_id": "BTC-USD",
            "strategy_id": "strategy-paper-001",
            "portfolio_id": "portfolio-paper-001",
            "market_bias": 0.55,
            "volatility": 0.22,
        },
    )
    decision_id = decision_response.json()["data"]["decision_id"]
    blocked_execution = client.post(
        "/v1/executions",
        headers=auth_headers(extra_headers={"Idempotency-Key": "execution-breaker-001"}),
        json={
            "decision_id": decision_id,
            "requested_notional": 5000,
            "venue_id": "paper-venue-001",
        },
    )

    assert blocked_execution.status_code == 409
    assert blocked_execution.json()["detail"]["code"] == "circuit_breaker_active"
    assert blocked_execution.json()["detail"]["scope_type"] == "tenant"
    assert blocked_execution.json()["detail"]["scope_id"] == PRIMARY_TENANT_ID
    assert blocked_execution.json()["detail"]["reason_code"] == "MANUAL_STOP"

    reset_response = client.post(
        f"/v1/circuit-breakers/tenant/{PRIMARY_TENANT_ID}/reset",
        headers=auth_headers(extra_headers={"Idempotency-Key": "breaker-reset-001"}),
        json={
            "reason_code": "CLEARED",
            "reason": "Verification complete.",
            "evidence_refs": ["ticket-123"],
        },
    )

    assert reset_response.status_code == 200
    assert reset_response.json()["state"] == "RESET"
    assert reset_response.json()["reset_by"] == PRIMARY_PRINCIPAL_ID
    assert reset_response.json()["reason_code"] == "CLEARED"



def test_dev_token_bootstrap_issues_valid_token() -> None:
    token_response = client.post(
        "/v1/dev/token",
        json={
            "principal_id": PRIMARY_PRINCIPAL_ID,
            "tenant_id": PRIMARY_TENANT_ID,
            "subject": "bootstrap-user",
            "roles": ["tenant_admin", "trader"],
            "scopes": ["decisions:read"],
            "lifetime_seconds": 600,
        },
    )

    assert token_response.status_code == 201
    token = token_response.json()["access_token"]
    me_response = client.get(
        "/v1/me",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Hermes-Tenant-ID": PRIMARY_TENANT_ID,
        },
    )
    assert me_response.status_code == 200
    assert me_response.json()["principal_id"] == PRIMARY_PRINCIPAL_ID


def test_missing_token_is_rejected() -> None:
    response = client.get("/v1/me")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "missing_bearer_token"


def test_missing_scope_is_rejected() -> None:
    audit_response = client.get("/v1/audit/events", headers=auth_headers(scopes="decisions:read"))

    assert audit_response.status_code == 403
    assert audit_response.json()["detail"]["code"] == "insufficient_scope"
    assert audit_response.json()["detail"]["required_scopes"] == ["audit:read"]

    decision_response = client.post(
        "/v1/decision-evaluations",
        headers=auth_headers(
            scopes="decisions:create decisions:read executions:create executions:read",
            extra_headers={"Idempotency-Key": "scope-decision-001"},
        ),
        json={
            "instrument_id": "BTC-USD",
            "strategy_id": "strategy-paper-001",
            "portfolio_id": "portfolio-paper-001",
            "market_bias": 0.55,
            "volatility": 0.22,
        },
    )
    assert decision_response.status_code == 202

    decision_id = decision_response.json()["data"]["decision_id"]
    execution_response = client.post(
        "/v1/executions",
        headers=auth_headers(
            scopes="decisions:create decisions:read executions:create executions:read",
            extra_headers={"Idempotency-Key": "scope-execution-001"},
        ),
        json={
            "decision_id": decision_id,
            "requested_notional": 5000,
            "venue_id": "paper-venue-001",
        },
    )
    assert execution_response.status_code == 202

    execution_id = execution_response.json()["data"]["execution_id"]
    pending_execution = client.get(
        f"/v1/executions/{execution_id}",
        headers=auth_headers(scopes="executions:read"),
    )
    assert pending_execution.status_code == 200

    approval_response = client.post(
        f"/v1/executions/{execution_id}/approve",
        headers=auth_headers(
            scopes="decisions:create decisions:read executions:create executions:read",
            extra_headers={"Idempotency-Key": "scope-approval-001"},
        ),
        json={
            "intent_digest": pending_execution.json()["intent_digest"],
            "decision": "APPROVED",
        },
    )
    assert approval_response.status_code == 403
    assert approval_response.json()["detail"]["required_scopes"] == ["executions:approve"]

    breaker_read_response = client.get(
        "/v1/circuit-breakers",
        headers=auth_headers(scopes="executions:read"),
    )
    assert breaker_read_response.status_code == 403
    assert breaker_read_response.json()["detail"]["required_scopes"] == ["controls:read"]

    breaker_activate_response = client.post(
        f"/v1/circuit-breakers/tenant/{PRIMARY_TENANT_ID}/activate",
        headers=auth_headers(
            scopes="controls:read",
            extra_headers={"Idempotency-Key": "scope-breaker-activate-001"},
        ),
        json={
            "reason_code": "MANUAL_STOP",
            "reason": "Missing activate scope coverage.",
            "evidence_refs": ["scope-case-001"],
        },
    )
    assert breaker_activate_response.status_code == 403
    assert breaker_activate_response.json()["detail"]["required_scopes"] == ["controls:activate"]

    client.post(
        f"/v1/circuit-breakers/tenant/{PRIMARY_TENANT_ID}/activate",
        headers=auth_headers(extra_headers={"Idempotency-Key": "scope-breaker-activate-002"}),
        json={
            "reason_code": "MANUAL_STOP",
            "reason": "Prepare reset scope check.",
            "evidence_refs": ["scope-case-002"],
        },
    )
    breaker_reset_response = client.post(
        f"/v1/circuit-breakers/tenant/{PRIMARY_TENANT_ID}/reset",
        headers=auth_headers(
            scopes="controls:read controls:activate",
            extra_headers={"Idempotency-Key": "scope-breaker-reset-001"},
        ),
        json={
            "reason_code": "CLEARED",
            "reason": "Missing reset scope coverage.",
            "evidence_refs": ["scope-case-002"],
        },
    )
    assert breaker_reset_response.status_code == 403
    assert breaker_reset_response.json()["detail"]["required_scopes"] == ["controls:reset"]
