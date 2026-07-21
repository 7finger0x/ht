# Quickstart: Validate Baseline Hermes Documentation

## Prerequisites

- Work from the Spec Kit project root: `hermes-documentation-rewrite`.
- Python dependencies for the documentation validator are installed.
- Optional: Docker/PostgreSQL is available if running the database security
  integration gate.

## 1. Confirm Active Feature

```bash
.specify/scripts/bash/check-prerequisites.sh --json --paths-only
```

Expected result:

- `FEATURE_DIR` points to `specs/001-baseline-hermes-docs`.
- `FEATURE_SPEC` points to `specs/001-baseline-hermes-docs/spec.md`.
- `IMPL_PLAN` points to `specs/001-baseline-hermes-docs/plan.md`.

## 2. Review Publication Placeholders

```bash
python scripts/validate_package.py
```

Expected result after implementation:

- `0 error(s)`.
- `0 warning(s)` for publication placeholders.
- If warnings remain, the implementation is not baseline publication-ready
  unless the warning is explicitly approved as outside publication-facing scope.

## 3. Optional Contract Tests

```bash
pytest -q tests/test_contracts.py
```

Expected result:

- Contract tests pass.
- Any failure becomes a blocking task because the baseline spec depends on
  canonical artifact consistency.

## 4. Optional PostgreSQL Security Integration Gate

```bash
bash scripts/test_postgres_security.sh
```

Expected result:

- Migration and security integration checks pass in the disposable target.
- If Docker/PostgreSQL is unavailable, record the gate as not run rather than
  claiming deployed-service or database conformance.

## 5. Manual Review Checklist

Confirm:

- Safety-gated execution language does not grant analytical agents trading,
  signing, credential, or live-execution authority.
- Canonical artifacts affected by the feature are updated in the same change.
- `TERMS.md` and `docs/SecurityPolicy.md` no longer contain unresolved
  publication placeholders.
- `VALIDATION_REPORT.md`, README, and release-status language do not claim
  production, legal, security, signer, venue, or live-trading conformance from
  static documentation checks.
- Remaining legal, security, operational, signer, venue, and live enablement
  gates are named as manual gates.

## Completion Signal

The feature is ready for task execution review when the plan artifacts are
present, the requirements checklist remains passing, and tasks can be generated
from the spec, plan, research, data model, review contract, and quickstart.
