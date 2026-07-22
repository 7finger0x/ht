from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]


def test_documentation_package_validator() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/validate_package.py")],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr


def test_audit_event_requires_explicit_chain_predecessor() -> None:
    schema = json.loads((ROOT / "schemas/audit-event.schema.json").read_text(encoding="utf-8"))
    event = json.loads((ROOT / "config/audit-event.example.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())

    assert not list(validator.iter_errors(event))
    event.pop("previous_event_digest")
    failures = list(validator.iter_errors(event))
    assert any(failure.validator == "required" for failure in failures)


def test_circuit_breaker_reset_requires_nonempty_evidence() -> None:
    document = yaml.safe_load((ROOT / "openapi/hermes.openapi.yaml").read_text(encoding="utf-8"))
    schema = document["components"]["schemas"]["CircuitBreakerResetRequest"]
    validator = Draft202012Validator(schema)

    valid = {"reason_code": "INCIDENT_CLOSED", "reason": "Evidence reviewed.", "evidence_refs": ["incident:INC-42"]}
    assert not list(validator.iter_errors(valid))

    for invalid in (
        {"reason_code": "INCIDENT_CLOSED", "reason": "Evidence reviewed."},
        {"reason_code": "INCIDENT_CLOSED", "reason": "Evidence reviewed.", "evidence_refs": []},
    ):
        assert list(validator.iter_errors(invalid))


def test_approval_artifacts_require_cross_record_bindings() -> None:
    document = yaml.safe_load((ROOT / "openapi/hermes.openapi.yaml").read_text(encoding="utf-8"))
    schemas = document["components"]["schemas"]

    assert {
        "execution_id", "strategy_id", "portfolio_id", "decision_id",
        "risk_evaluation_id", "requires_approval", "intent_digest",
    } <= set(schemas["OrderIntent"]["required"])
    assert {
        "execution_id", "order_intent_id", "risk_evaluation_id", "intent_digest",
    } <= set(schemas["ApprovalRecord"]["required"])
