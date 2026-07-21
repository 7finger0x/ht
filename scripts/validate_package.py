#!/usr/bin/env python3
"""Validate the Hermes documentation package without contacting external services."""

from __future__ import annotations

import ast
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import unquote

import yaml
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_SCAN_PARTS = {
    ".git",
    "__pycache__",
    "node_modules",
    "dist",
    ".venv",
    ".venv-auth",
    ".venv-mvp",
}


def is_validation_excluded(path: Path) -> bool:
    try:
        relative = path.relative_to(ROOT)
    except ValueError:
        return False
    return any(part in EXCLUDED_SCAN_PARTS for part in relative.parts)


@dataclass
class Finding:
    level: str
    message: str


FINDINGS: list[Finding] = []


def error(message: str) -> None:
    FINDINGS.append(Finding("ERROR", message))


def warning(message: str) -> None:
    FINDINGS.append(Finding("WARN", message))


def info(message: str) -> None:
    FINDINGS.append(Finding("OK", message))


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        error(f"Invalid JSON in {path.relative_to(ROOT)}: {exc}")
        return None


def load_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        error(f"Invalid YAML in {path.relative_to(ROOT)}: {exc}")
        return None


def validate_schema(schema_path: Path, instance_path: Path) -> None:
    schema = load_json(schema_path)
    if schema is None:
        return
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as exc:  # noqa: BLE001
        error(f"Invalid JSON Schema {schema_path.relative_to(ROOT)}: {exc}")
        return

    if instance_path.suffix in {".yaml", ".yml"}:
        instance = load_yaml(instance_path)
    else:
        instance = load_json(instance_path)
    if instance is None:
        return

    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    failures = sorted(validator.iter_errors(instance), key=lambda item: list(item.path))
    if failures:
        for failure in failures:
            location = ".".join(str(part) for part in failure.path) or "<root>"
            error(
                f"{instance_path.relative_to(ROOT)} violates {schema_path.relative_to(ROOT)} "
                f"at {location}: {failure.message}"
            )
    else:
        info(f"Schema validation passed: {instance_path.relative_to(ROOT)}")


def resolve_json_pointer(document: Any, pointer: str) -> Any:
    if pointer == "#":
        return document
    if not pointer.startswith("#/"):
        raise ValueError("only local JSON pointers are supported")
    current = document
    for raw_part in pointer[2:].split("/"):
        part = unquote(raw_part).replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            raise KeyError(part)
    return current


def walk_values(value: Any) -> Iterable[Any]:
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_values(child)


def validate_openapi(path: Path) -> None:
    error_count_before = sum(finding.level == "ERROR" for finding in FINDINGS)
    document = load_yaml(path)
    if not isinstance(document, dict):
        error("OpenAPI document must be an object")
        return
    if document.get("openapi") != "3.1.2":
        error("OpenAPI contract must use the reviewed OpenAPI 3.1.2 patch release")
    if not isinstance(document.get("paths"), dict) or not document["paths"]:
        error("OpenAPI contract has no paths")
    if "components" not in document:
        error("OpenAPI contract has no components")

    ref_count = 0
    for value in walk_values(document):
        if isinstance(value, dict) and "$ref" in value:
            ref = value["$ref"]
            ref_count += 1
            if not isinstance(ref, str) or not ref.startswith("#/"):
                error(f"Unsupported non-local OpenAPI reference: {ref!r}")
                continue
            try:
                resolve_json_pointer(document, ref)
            except Exception as exc:  # noqa: BLE001
                error(f"Unresolved OpenAPI reference {ref}: {exc}")

    required_paths = {
        "/v1/health/live",
        "/v1/health/ready",
        "/v1/health/dependencies",
        "/v1/me",
        "/v1/decisions",
        "/v1/decision-evaluations",
        "/v1/decisions/{decision_id}",
        "/v1/executions",
        "/v1/executions/{execution_id}",
        "/v1/executions/{execution_id}/approve",
        "/v1/circuit-breakers",
        "/v1/circuit-breakers/{scope_type}/{scope_id}/activate",
        "/v1/circuit-breakers/{scope_type}/{scope_id}/reset",
        "/v1/audit/events",
    }
    missing = sorted(required_paths - set(document.get("paths", {})))
    if missing:
        error(f"OpenAPI contract missing required paths: {', '.join(missing)}")

    operation_ids: dict[str, str] = {}
    operation_count = 0
    http_methods = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}
    public_routes = {"/v1/health/live", "/v1/health/ready"}
    tenant_roles = {"viewer", "operator", "trader", "approver", "tenant_admin", "security_admin"}

    def dereference_parameter(item: Any) -> Any:
        if isinstance(item, dict) and isinstance(item.get("$ref"), str):
            try:
                return resolve_json_pointer(document, item["$ref"])
            except Exception:  # already reported above
                return None
        return item

    def dereference_response(item: Any) -> Any:
        if isinstance(item, dict) and isinstance(item.get("$ref"), str):
            try:
                return resolve_json_pointer(document, item["$ref"])
            except Exception:  # already reported above
                return None
        return item

    for route, path_item in document.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue
        path_parameters = path_item.get("parameters", [])
        route_placeholders = set(re.findall(r"\{([A-Za-z0-9_.-]+)\}", route))

        for method, operation in path_item.items():
            method_lower = method.lower()
            if method_lower not in http_methods or not isinstance(operation, dict):
                continue
            operation_count += 1
            operation_id = operation.get("operationId")
            if not isinstance(operation_id, str) or not operation_id.strip():
                error(f"OpenAPI operation {method.upper()} {route} lacks operationId")
            elif operation_id in operation_ids:
                error(
                    f"Duplicate OpenAPI operationId {operation_id!r}: "
                    f"{operation_ids[operation_id]} and {method.upper()} {route}"
                )
            else:
                operation_ids[operation_id] = f"{method.upper()} {route}"

            label = f"{method.upper()} {route}"
            is_public = operation.get("security", document.get("security")) == []
            if route in public_routes:
                if not is_public:
                    error(f"Public health operation {label} must declare security: []")
                if "x-hermes-allowed-roles" in operation or "x-hermes-required-scopes" in operation:
                    error(f"Public health operation {label} must not declare tenant authorization metadata")
            elif is_public:
                error(f"Authenticated operation {label} unexpectedly disables security")
            elif route == "/v1/me":
                if operation.get("x-hermes-authorization") != "authenticated-principal":
                    error(f"Identity operation {label} lacks authenticated-principal authorization metadata")
            else:
                roles = operation.get("x-hermes-allowed-roles")
                scopes = operation.get("x-hermes-required-scopes")
                if not isinstance(roles, list) or not roles or not all(isinstance(role, str) for role in roles):
                    error(f"Authenticated operation {label} lacks non-empty x-hermes-allowed-roles")
                if not isinstance(scopes, list) or not scopes or not all(isinstance(scope, str) and scope for scope in scopes):
                    error(f"Authenticated operation {label} lacks non-empty x-hermes-required-scopes")
                if route != "/v1/health/dependencies" and isinstance(roles, list):
                    invalid_roles = sorted(set(roles) - tenant_roles)
                    if invalid_roles:
                        error(f"Tenant operation {label} grants non-tenant roles: {', '.join(invalid_roles)}")

            raw_parameters = []
            if isinstance(path_parameters, list):
                raw_parameters.extend(path_parameters)
            operation_parameters = operation.get("parameters", [])
            if isinstance(operation_parameters, list):
                raw_parameters.extend(operation_parameters)

            parameters = [dereference_parameter(item) for item in raw_parameters]
            path_parameter_names: set[str] = set()
            for parameter in parameters:
                if not isinstance(parameter, dict) or parameter.get("in") != "path":
                    continue
                name = parameter.get("name")
                if isinstance(name, str):
                    path_parameter_names.add(name)
                    if parameter.get("required") is not True:
                        error(f"Path parameter {name!r} is not required on {method.upper()} {route}")

            missing_params = sorted(route_placeholders - path_parameter_names)
            extra_params = sorted(path_parameter_names - route_placeholders)
            if missing_params:
                error(
                    f"OpenAPI operation {method.upper()} {route} lacks path parameter definitions: "
                    f"{', '.join(missing_params)}"
                )
            if extra_params:
                error(
                    f"OpenAPI operation {method.upper()} {route} defines unused path parameters: "
                    f"{', '.join(extra_params)}"
                )

            if method_lower in {"post", "put", "patch", "delete"}:
                refs = [item.get("$ref") for item in raw_parameters if isinstance(item, dict)]
                if "#/components/parameters/IdempotencyKey" not in refs:
                    error(f"Mutating endpoint {method.upper()} {route} lacks Idempotency-Key")

            responses = operation.get("responses")
            if not isinstance(responses, dict):
                error(f"OpenAPI operation {label} lacks responses")
                continue

            if not is_public:
                missing_errors = sorted({"401", "429", "503"} - set(responses))
                if missing_errors:
                    error(f"Authenticated operation {label} lacks responses: {', '.join(missing_errors)}")
                success_responses = [
                    dereference_response(response)
                    for status, response in responses.items()
                    if str(status).startswith("2")
                ]
                if not success_responses:
                    error(f"Authenticated operation {label} has no success response")
                for response in success_responses:
                    headers = response.get("headers") if isinstance(response, dict) else None
                    if not isinstance(headers, dict) or "X-Request-ID" not in headers:
                        error(f"Authenticated success response on {label} lacks X-Request-ID")

            if method_lower in {"post", "put", "patch", "delete"}:
                standard_errors = {"400", "401", "403", "409", "422", "429", "503"}
                missing_errors = sorted(standard_errors - set(responses))
                if missing_errors:
                    error(f"Mutating endpoint {label} lacks standard responses: {', '.join(missing_errors)}")
                for status, response in responses.items():
                    if not str(status).startswith("2"):
                        continue
                    resolved = dereference_response(response)
                    headers = resolved.get("headers") if isinstance(resolved, dict) else None
                    if not isinstance(headers, dict) or "Idempotency-Replayed" not in headers:
                        error(f"Mutating success response on {label} lacks Idempotency-Replayed")

    schemas = document.get("components", {}).get("schemas", {})
    if isinstance(schemas, dict):
        for schema_name, schema in schemas.items():
            if not isinstance(schema, dict):
                continue
            required = schema.get("required")
            properties = schema.get("properties")
            if isinstance(required, list) and isinstance(properties, dict):
                missing_properties = [name for name in required if name not in properties]
                if missing_properties:
                    error(
                        f"OpenAPI schema {schema_name} requires undefined properties: "
                        f"{', '.join(str(name) for name in missing_properties)}"
                    )

        binding_requirements = {
            "OrderIntent": {
                "execution_id", "strategy_id", "portfolio_id", "decision_id",
                "risk_evaluation_id", "requires_approval", "intent_digest",
            },
            "ApprovalRecord": {
                "execution_id", "order_intent_id", "risk_evaluation_id", "intent_digest",
            },
        }
        for schema_name, expected in binding_requirements.items():
            schema = schemas.get(schema_name)
            required = set(schema.get("required", [])) if isinstance(schema, dict) else set()
            missing_required = sorted(expected - required)
            if missing_required:
                error(f"OpenAPI schema {schema_name} lacks required bindings: {', '.join(missing_required)}")

        reset_schema = schemas.get("CircuitBreakerResetRequest")
        reset_required = set(reset_schema.get("required", [])) if isinstance(reset_schema, dict) else set()
        evidence_schema = reset_schema.get("properties", {}).get("evidence_refs", {}) if isinstance(reset_schema, dict) else {}
        if "evidence_refs" not in reset_required or evidence_schema.get("minItems", 0) < 1:
            error("OpenAPI circuit-breaker reset must require at least one evidence reference")

    response_components = document.get("components", {}).get("responses", {})
    if isinstance(response_components, dict):
        for response_name, response in response_components.items():
            headers = response.get("headers") if isinstance(response, dict) else None
            if not isinstance(headers, dict) or "X-Request-ID" not in headers:
                error(f"OpenAPI response component {response_name} lacks X-Request-ID")
            if not isinstance(headers, dict) or "Idempotency-Replayed" not in headers:
                error(f"OpenAPI response component {response_name} cannot describe replayed mutation errors")

    error_count_after = sum(finding.level == "ERROR" for finding in FINDINGS)
    if error_count_after == error_count_before:
        info(
            f"OpenAPI parsed with {operation_count} operations, {len(operation_ids)} unique operation IDs, "
            f"and {ref_count} resolved local references"
        )


LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
FENCE_RE = re.compile(r"```([A-Za-z0-9_-]*)\n(.*?)```", re.DOTALL)


def markdown_heading_anchors(path: Path) -> set[str]:
    heading_re = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$", re.MULTILINE)
    anchors: set[str] = set()
    occurrences: dict[str, int] = {}
    for heading in heading_re.findall(path.read_text(encoding="utf-8")):
        normalized = re.sub(r"<[^>]+>", "", heading).strip().lower()
        normalized = re.sub(r"[`*_~]", "", normalized)
        normalized = re.sub(r"[^\w\- ]", "", normalized, flags=re.UNICODE)
        normalized = re.sub(r"\s+", "-", normalized)
        normalized = re.sub(r"-+", "-", normalized).strip("-")
        suffix = occurrences.get(normalized, 0)
        occurrences[normalized] = suffix + 1
        anchors.add(normalized if suffix == 0 else f"{normalized}-{suffix}")
    return anchors


def validate_markdown_links() -> None:
    checked_files = 0
    checked_anchors = 0
    anchor_cache: dict[Path, set[str]] = {}
    for path in ROOT.rglob("*.md"):
        if is_validation_excluded(path):
            continue
        text = path.read_text(encoding="utf-8")
        for target in LINK_RE.findall(text):
            target = target.strip().split(maxsplit=1)[0].strip("<>")
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue

            if "#" in target:
                target_path, fragment = target.split("#", 1)
            else:
                target_path, fragment = target, ""
            target_path = target_path.split("?", 1)[0]

            resolved = path.resolve() if not target_path else (path.parent / unquote(target_path)).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                error(f"Markdown link escapes package in {path.relative_to(ROOT)}: {target}")
                continue

            if target_path:
                checked_files += 1
                if not resolved.exists():
                    error(f"Broken Markdown link in {path.relative_to(ROOT)}: {target}")
                    continue

            if fragment and resolved.suffix.lower() == ".md" and resolved.exists():
                checked_anchors += 1
                anchors = anchor_cache.setdefault(resolved, markdown_heading_anchors(resolved))
                expected = unquote(fragment).lower()
                if expected not in anchors:
                    error(f"Broken Markdown anchor in {path.relative_to(ROOT)}: {target}")

    info(f"Checked {checked_files} internal Markdown file links and {checked_anchors} anchors")


def validate_json_code_fences() -> None:
    count = 0
    for path in ROOT.rglob("*.md"):
        if is_validation_excluded(path):
            continue
        text = path.read_text(encoding="utf-8")
        for language, body in FENCE_RE.findall(text):
            if language.lower() != "json":
                continue
            count += 1
            try:
                json.loads(body)
            except Exception as exc:  # noqa: BLE001
                error(f"Invalid JSON code fence in {path.relative_to(ROOT)}: {exc}")
    info(f"Validated {count} JSON code fences")


def to_bash_path(path: Path) -> str:
    if os.name != "nt":
        return str(path)
    global _IS_WSL_BASH
    if not hasattr(sys.modules[__name__], "_IS_WSL_BASH"):
        try:
            res = subprocess.run(
                ["bash", "-c", "uname"],
                capture_output=True,
                text=True,
                check=False,
            )
            _IS_WSL_BASH = "linux" in res.stdout.lower()
        except Exception:
            _IS_WSL_BASH = False

    posix_path = path.as_posix()
    if _IS_WSL_BASH:
        match = re.match(r"^([a-zA-Z]):/", posix_path)
        if match:
            drive = match.group(1).lower()
            posix_path = f"/mnt/{drive}/{posix_path[3:]}"
    return posix_path


def validate_shell_syntax() -> None:
    """Syntax-check shell fences and scripts in one bash process (avoids per-file spawn cost)."""
    jobs: list[tuple[str, Path]] = []
    temp_paths: list[Path] = []
    fence_count = 0
    script_count = 0

    try:
        for path in ROOT.rglob("*.md"):
            if is_validation_excluded(path):
                continue
            text = path.read_text(encoding="utf-8")
            for language, body in FENCE_RE.findall(text):
                if language.lower() not in {"bash", "sh", "shell"}:
                    continue
                fence_count += 1
                handle = tempfile.NamedTemporaryFile(
                    "w",
                    suffix=".sh",
                    delete=False,
                    encoding="utf-8",
                    newline="\n",
                )
                try:
                    handle.write("set -e\n")
                    handle.write(body)
                finally:
                    handle.close()
                temp_path = Path(handle.name)
                temp_paths.append(temp_path)
                jobs.append((f"fence:{path.relative_to(ROOT).as_posix()}", temp_path))

        for path in ROOT.rglob("*.sh"):
            if is_validation_excluded(path):
                continue
            script_count += 1
            jobs.append((f"script:{path.relative_to(ROOT).as_posix()}", path))

        if jobs:
            driver_lines = [
                "set +e",
                "failures=0",
            ]
            for index, (_label, job_path) in enumerate(jobs):
                quoted = shlex.quote(to_bash_path(job_path))
                driver_lines.append(
                    f'err=$(bash -n {quoted} 2>&1); rc=$?; '
                    f'if [ "$rc" -ne 0 ]; then printf "FAIL|%s|%s\\n" "{index}" "$err"; '
                    f"failures=$((failures+1)); fi"
                )
            driver_lines.append("exit 0")

            with tempfile.NamedTemporaryFile(
                "w",
                suffix=".sh",
                delete=False,
                encoding="utf-8",
                newline="\n",
            ) as driver:
                driver.write("\n".join(driver_lines) + "\n")
                driver_name = driver.name
            temp_paths.append(Path(driver_name))

            result = subprocess.run(
                ["bash", to_bash_path(Path(driver_name))],
                check=False,
                capture_output=True,
                text=True,
            )
            fail_lines = [
                line for line in result.stdout.splitlines() if line.startswith("FAIL|")
            ]
            if result.returncode != 0 and not fail_lines:
                detail = (result.stderr or result.stdout or "unknown driver failure").strip()
                error(f"Shell syntax driver failed: {detail}")
            for line in fail_lines:
                parts = line.split("|", 2)
                if len(parts) != 3:
                    error(f"Unparseable shell syntax failure: {line}")
                    continue
                try:
                    job_index = int(parts[1])
                except ValueError:
                    error(f"Unparseable shell syntax failure index: {line}")
                    continue
                label, _job_path = jobs[job_index]
                kind, relative = label.split(":", 1)
                detail = parts[2].strip()
                if kind == "fence":
                    error(f"Invalid shell syntax in {relative}: {detail}")
                else:
                    error(f"Invalid shell script {relative}: {detail}")
    finally:
        for temp_path in temp_paths:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass

    info(f"Syntax-checked {fence_count} shell code fences and {script_count} shell scripts")


def validate_python_syntax() -> None:
    script_count = 0
    roots = [ROOT / "scripts", ROOT / "tests"]
    for base in roots:
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            script_count += 1
            try:
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except (OSError, SyntaxError) as exc:
                error(f"Invalid Python syntax in {path.relative_to(ROOT)}: {exc}")
    info(f"Syntax-checked {script_count} Python files")


def validate_runbooks() -> None:
    required_headings = [
        "## 1. Trigger and severity",
        "## 2. Safety objective",
        "## 3. Preconditions and authority",
        "## 4. Immediate containment",
        "## 5.",
        "## 6.",
        "## 7. Verification",
        "## 8. Rollback or abort criteria",
        "## 9. Evidence to preserve",
        "## 10. Escalation and communications",
    ]
    runbooks = sorted(path for path in (ROOT / "runbooks").glob("*.md") if path.name != "README.md")
    if len(runbooks) < 5:
        error("At least five operational runbooks are required")
    for path in runbooks:
        text = path.read_text(encoding="utf-8")
        for heading in required_headings:
            if heading not in text:
                error(f"Runbook {path.relative_to(ROOT)} missing required heading prefix: {heading}")
    info(f"Validated required structure for {len(runbooks)} runbooks")


def validate_runbook_contract_tests() -> None:
    error_count_before = sum(finding.level == "ERROR" for finding in FINDINGS)
    path = ROOT / "runbooks/runbook-tests.yaml"
    suite = load_yaml(path)
    if not isinstance(suite, dict):
        error("Runbook test suite must be an object")
        return

    cases = suite.get("cases")
    if not isinstance(cases, list):
        error("Runbook test suite has no cases")
        return

    tested_paths: set[str] = set()
    for case in cases:
        if not isinstance(case, dict):
            error("Runbook test case must be an object")
            continue
        case_id = str(case.get("id", "<unknown>"))
        relative = case.get("runbook")
        if not isinstance(relative, str):
            error(f"Runbook test {case_id} has no runbook path")
            continue
        runbook_path = (ROOT / relative).resolve()
        try:
            runbook_path.relative_to(ROOT.resolve())
        except ValueError:
            error(f"Runbook test {case_id} escapes the package: {relative}")
            continue
        if not runbook_path.exists():
            error(f"Runbook test {case_id} references missing file: {relative}")
            continue
        tested_paths.add(relative)
        runbook_text = runbook_path.read_text(encoding="utf-8").lower()
        for field in ("required_controls", "required_evidence"):
            anchors = case.get(field, [])
            if not isinstance(anchors, list):
                error(f"Runbook test {case_id} field {field} must be a list")
                continue
            for anchor in anchors:
                if not isinstance(anchor, str) or anchor.lower() not in runbook_text:
                    error(f"Runbook test {case_id} missing {field} anchor in {relative}: {anchor!r}")

    actual_paths = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "runbooks").glob("*.md")
        if path.name != "README.md"
    }
    missing_tests = sorted(actual_paths - tested_paths)
    duplicate_count = len(cases) - len(tested_paths)
    if missing_tests:
        error(f"Runbooks without contract tests: {', '.join(missing_tests)}")
    if duplicate_count:
        error(f"Runbook test suite contains {duplicate_count} duplicate runbook path(s)")
    error_count_after = sum(finding.level == "ERROR" for finding in FINDINGS)
    if not missing_tests and not duplicate_count and error_count_after == error_count_before:
        info(f"Passed {len(cases)} automated runbook contract tests")


def parse_env_names(path: Path) -> list[str]:
    names: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            error(f"Invalid environment line in {path.relative_to(ROOT)}: {line}")
            continue
        names.append(stripped.split("=", 1)[0])
    return names


def parse_env_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            error(f"Invalid environment line in {path.relative_to(ROOT)}: {line}")
            continue
        name, value = stripped.split("=", 1)
        if name in values:
            error(f"Duplicate environment variable in {path.relative_to(ROOT)}: {name}")
        values[name] = value
    return values


def validate_environment_files() -> None:
    frontend = ROOT / "config/env/frontend.env.example"
    names = parse_env_names(frontend)
    bad = [name for name in names if not name.startswith("VITE_")]
    if bad:
        error(f"Frontend environment contains non-public variable names: {', '.join(bad)}")
    prohibited_fragments = {
        "SECRET",
        "PRIVATE_KEY",
        "SEED",
        "DATABASE",
        "SERVICE_ROLE",
        "CEX",
        "WALLET_KEY",
        "API_SECRET",
    }
    suspicious = [name for name in names if any(fragment in name for fragment in prohibited_fragments)]
    if suspicious:
        error(f"Frontend environment contains suspicious secret-like variables: {', '.join(suspicious)}")

    environment_files = sorted((ROOT / "config/env").glob("*.env.example"))
    raw_secret_names = ("PRIVATE_KEY", "SEED_PHRASE", "MNEMONIC", "WALLET_KEY", "CEX_API_SECRET")
    for path in environment_files:
        values = parse_env_values(path)
        prohibited = [name for name in values if any(fragment in name for fragment in raw_secret_names)]
        if prohibited:
            error(f"Environment example exposes raw signing/credential variable names in {path.relative_to(ROOT)}: {', '.join(prohibited)}")
        for name, value in values.items():
            if name.endswith("_KEY_REF") and not value.startswith("secret://"):
                error(f"Secret reference {name} in {path.relative_to(ROOT)} must use secret://")

    required_false = {
        "config/env/backend.env.example": "HERMES_LIVE_TRADING_ENABLED",
        "config/env/worker.env.example": "HERMES_LIVE_TRADING_ENABLED",
        "config/env/signer.env.example": "HERMES_SIGNER_LIVE_ENABLED",
    }
    for relative, variable in required_false.items():
        values = parse_env_values(ROOT / relative)
        if values.get(variable) != "false":
            error(f"{relative} must set {variable}=false")

    info(
        f"Environment examples checked across {len(environment_files)} service boundaries; "
        f"frontend classifies {len(names)} variables as public and all live defaults fail closed"
    )


def validate_infrastructure_config() -> None:
    path = ROOT / "infra/docker/compose.yaml"
    compose = load_yaml(path)
    if not isinstance(compose, dict):
        error("Docker Compose configuration must be an object")
        return
    services = compose.get("services")
    if not isinstance(services, dict):
        error("Docker Compose configuration has no services map")
        return
    required_services = {"postgres", "redis", "migrate"}
    missing = sorted(required_services - set(services))
    if missing:
        error(f"Docker Compose configuration missing services: {', '.join(missing)}")
    for service_name, service in services.items():
        if not isinstance(service, dict):
            error(f"Docker Compose service {service_name} must be an object")
            continue
        image = service.get("image")
        if isinstance(image, str) and (":" not in image or image.endswith(":latest")):
            error(f"Docker Compose service {service_name} must use an explicit non-latest image tag")
        ports = service.get("ports", [])
        if isinstance(ports, list):
            for port in ports:
                if isinstance(port, str) and not port.startswith("127.0.0.1:"):
                    error(f"Local Docker Compose port must bind to loopback: {service_name} {port}")
    migrate = services.get("migrate")
    command_text = json.dumps(migrate.get("command")) if isinstance(migrate, dict) else ""
    if "0001_core.sql" not in command_text or "ON_ERROR_STOP=1" not in command_text:
        error("Docker Compose migrate service must apply 0001_core.sql with ON_ERROR_STOP=1")
    info(f"Parsed Docker Compose configuration with {len(services)} pinned local-support services")


def parse_sql_enum(sql: str, enum_name: str) -> list[str] | None:
    pattern = re.compile(
        rf"create\s+type\s+hermes\.{re.escape(enum_name)}\s+as\s+enum\s*\((.*?)\)\s*;",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(sql)
    if not match:
        return None
    return re.findall(r"'([^']+)'", match.group(1))


def split_sql_top_level(value: str) -> list[str]:
    parts: list[str] = []
    start = 0
    depth = 0
    in_single = False
    in_double = False
    index = 0
    while index < len(value):
        char = value[index]
        next_char = value[index + 1] if index + 1 < len(value) else ""
        if in_single:
            if char == "'" and next_char == "'":
                index += 2
                continue
            if char == "'":
                in_single = False
        elif in_double:
            if char == '"' and next_char == '"':
                index += 2
                continue
            if char == '"':
                in_double = False
        elif char == "'":
            in_single = True
        elif char == '"':
            in_double = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        elif char == "," and depth == 0:
            parts.append(value[start:index].strip())
            start = index + 1
        index += 1
    tail = value[start:].strip()
    if tail:
        parts.append(tail)
    return parts


def validate_sql_baseline() -> None:
    path = ROOT / "infra/supabase/migrations/0001_core.sql"
    raw_text = path.read_text(encoding="utf-8")
    text = raw_text.lower()
    required = [
        "enable row level security",
        "force row level security",
        "nobypassrls",
        "with check",
        "idempotency_records",
        "audit_events",
        "reject_mutation",
        "current_setting('app.tenant_id'",
        "identity_membership_lookup",
        "identity_tenant_lookup",
        "lookup_principal(",
        "security definer",
        "set search_path = pg_catalog, hermes, pg_temp",
        "revoke all on function hermes.lookup_principal(text, text) from public",
        "grant execute on function hermes.lookup_principal(text, text) to hermes_identity",
        "references hermes.audit_events(tenant_id, event_digest)",
        "audit_one_root_per_tenant_idx",
        "audit_one_successor_per_event_idx",
        "previous_event_digest <> event_digest",
        "append_audit_event(",
        "pg_advisory_xact_lock",
        "revoke insert on hermes.audit_events from hermes_api, hermes_worker",
        "venue_fill_id text not null",
        "unique (tenant_id, venue_order_id, venue_fill_id)",
    ]
    for marker in required:
        if marker not in text:
            error(f"SQL migration missing security or integrity marker: {marker}")
    prohibited = [
        "grant all on schema hermes to public",
        "grant all on all tables in schema hermes",
        "grant select, insert, update on hermes.principals to hermes_identity",
        "service_role",
        "external_fill_id",
    ]
    for marker in prohibited:
        if marker in text:
            error(f"SQL migration contains prohibited marker: {marker}")
    if text.count("begin;") != text.count("commit;"):
        warning("SQL transaction marker count differs; review migration manually")
    membership_binding = "references hermes.tenant_memberships(tenant_id, principal_id)"
    if text.count(membership_binding) < 6:
        error("SQL migration must bind principal-attribution columns to same-tenant memberships")
    application_insert_grant = re.search(
        r"grant\s+insert\s+on\s+(.*?)\s+to\s+hermes_api\s*,\s*hermes_worker\s*;",
        text,
        re.DOTALL,
    )
    if not application_insert_grant:
        error("SQL application INSERT grant block not found")
    elif "hermes.audit_events" in application_insert_grant.group(1):
        error("Application roles must not receive direct INSERT on hermes.audit_events")

    table_pattern = re.compile(
        r"create\s+table\s+hermes\.([a-z_][a-z0-9_]*)\s*\((.*?)\n\);",
        re.IGNORECASE | re.DOTALL,
    )
    table_count = 0
    for table_name, body in table_pattern.findall(raw_text):
        table_count += 1
        columns: list[str] = []
        for item in split_sql_top_level(body):
            normalized = item.lstrip().lower()
            if normalized.startswith(("constraint ", "unique ", "foreign key", "primary key", "check ", "exclude ")):
                continue
            match = re.match(r'(?:("[^"]+")|([a-z_][a-z0-9_]*))\s+', item, re.IGNORECASE)
            if match:
                columns.append((match.group(1) or match.group(2)).strip('"').lower())
        duplicates = sorted({name for name in columns if columns.count(name) > 1})
        if duplicates:
            error(f"SQL table hermes.{table_name} defines duplicate columns: {', '.join(duplicates)}")

    openapi = load_yaml(ROOT / "openapi/hermes.openapi.yaml")
    if isinstance(openapi, dict):
        schemas = openapi.get("components", {}).get("schemas", {})
        enum_pairs = {
            "execution_state": "ExecutionState",
            "order_status": "OrderStatus",
        }
        for sql_name, schema_name in enum_pairs.items():
            sql_values = parse_sql_enum(raw_text, sql_name)
            schema = schemas.get(schema_name) if isinstance(schemas, dict) else None
            api_values = schema.get("enum") if isinstance(schema, dict) else None
            if sql_values is None:
                error(f"SQL enum hermes.{sql_name} not found")
            elif not isinstance(api_values, list):
                error(f"OpenAPI enum {schema_name} not found")
            else:
                missing_values = [value for value in api_values if value not in sql_values]
                if missing_values:
                    error(
                        f"SQL/OpenAPI enum mismatch for {sql_name}/{schema_name}: "
                        f"missing from SQL={missing_values!r}, SQL={sql_values!r}, OpenAPI={api_values!r}"
                    )

        circuit_schema = schemas.get("CircuitScopeType") if isinstance(schemas, dict) else None
        api_scopes = circuit_schema.get("enum") if isinstance(circuit_schema, dict) else None
        scope_match = re.search(
            r"scope_type\s+text\s+not\s+null\s+check\s*\(scope_type\s+in\s*\((.*?)\)\)",
            raw_text,
            re.IGNORECASE | re.DOTALL,
        )
        sql_scopes = re.findall(r"'([^']+)'", scope_match.group(1)) if scope_match else None
        if sql_scopes is None:
            error("SQL circuit-breaker scope constraint not found")
        elif not isinstance(api_scopes, list):
            error("OpenAPI CircuitScopeType enum not found")
        elif sql_scopes != api_scopes:
            error(f"SQL/OpenAPI circuit scope mismatch: SQL={sql_scopes!r}, OpenAPI={api_scopes!r}")
        if isinstance(api_scopes, list) and "global" in api_scopes:
            error("Tenant circuit-breaker API must not expose deployment-wide global scope")

        fill_schema = schemas.get("Fill") if isinstance(schemas, dict) else None
        fill_required = fill_schema.get("required", []) if isinstance(fill_schema, dict) else []
        if "venue_fill_id" not in fill_required:
            error("OpenAPI Fill must require venue_fill_id for external-event deduplication")

    info(
        f"SQL baseline statically checked across {table_count} tables with forced RLS, constrained identity lookup, "
        "same-tenant principal binding, serialized audit append, audit-chain structure, idempotency, stable fill IDs, immutability, "
        "and OpenAPI enum consistency"
    )


def validate_required_files() -> None:
    required = [
        "README.md",
        "SPEC.md",
        "PRIVACY.md",
        "TERMS.md",
        "SECURITY.md",
        "VALIDATION_REPORT.md",
        "docs/Architecture.md",
        "docs/DataInventory.md",
        "docs/ExecutionProtocol.md",
        "docs/SecurityPolicy.md",
        "docs/APIReference.md",
        "docs/DeploymentGuide.md",
        "docs/OperationsManual.md",
        "docs/Whitepaper.md",
        "docs/Glossary.md",
        "docs/ContributionGuidelines.md",
        "docs/ObservabilityStandards.md",
        "docs/api-mocking-collection.md",
        "docs/sdk-generation.md",
        "openapi/hermes.openapi.yaml",
        "schemas/risk-policy.schema.json",
        "schemas/venue-registry.schema.json",
        "schemas/audit-event.schema.json",
        "schemas/runbook-test.schema.json",
        "runbooks/runbook-tests.yaml",
        "infra/supabase/migrations/0001_core.sql",
        "infra/docker/compose.yaml",
        "scripts/test_postgres_security.sh",
        "scripts/test_postgres_security_ci.sh",
        "scripts/generate_sdks.sh",
        "scripts/verify_audit_chain.py",
        "tests/postgres_security.sql",
    ]
    for relative in required:
        if not (ROOT / relative).exists():
            error(f"Missing required file: {relative}")
    info(f"Checked {len(required)} required files")


def report_placeholders() -> None:
    pattern = re.compile(
        r"\[(?:(?:counsel|publish|insert|replace|configure|provide|define|tbd|todo)\b)[^\]\n]*\]",
        re.IGNORECASE,
    )
    matches: list[str] = []
    for path in ROOT.rglob("*.md"):
        if is_validation_excluded(path):
            continue
        for match in sorted(set(pattern.findall(path.read_text(encoding="utf-8")))):
            matches.append(f"{path.relative_to(ROOT)}: {match}")
    if matches:
        warning(
            f"Publication placeholders remain ({len(matches)} unique occurrences): "
            + "; ".join(matches)
        )


def main() -> int:
    validate_required_files()
    validate_schema(
        ROOT / "schemas/risk-policy.schema.json",
        ROOT / "config/risk-policy.example.yaml",
    )
    validate_schema(
        ROOT / "schemas/venue-registry.schema.json",
        ROOT / "config/venues.example.yaml",
    )
    validate_schema(
        ROOT / "schemas/audit-event.schema.json",
        ROOT / "config/audit-event.example.json",
    )
    validate_schema(
        ROOT / "schemas/runbook-test.schema.json",
        ROOT / "runbooks/runbook-tests.yaml",
    )
    validate_openapi(ROOT / "openapi/hermes.openapi.yaml")
    validate_markdown_links()
    validate_json_code_fences()
    validate_shell_syntax()
    validate_python_syntax()
    validate_runbooks()
    validate_runbook_contract_tests()
    validate_environment_files()
    validate_infrastructure_config()
    validate_sql_baseline()
    report_placeholders()

    for finding in FINDINGS:
        print(f"[{finding.level}] {finding.message}")

    error_count = sum(finding.level == "ERROR" for finding in FINDINGS)
    warning_count = sum(finding.level == "WARN" for finding in FINDINGS)
    print(f"\nValidation complete: {error_count} error(s), {warning_count} warning(s).")
    return 1 if error_count else 0


if __name__ == "__main__":
    sys.exit(main())
