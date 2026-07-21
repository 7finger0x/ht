# Implementation Plan: Baseline Hermes Documentation

**Branch**: `001-baseline-hermes-docs` | **Date**: 2026-07-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-baseline-hermes-docs/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Establish a baseline documentation contract for Hermes that makes safety-gated
execution, canonical artifact alignment, validation evidence, publication
placeholder remediation, and release boundaries explicit and testable. The
implementation approach is documentation-first: update controlled docs and
validation evidence, then prove the package with the existing documentation
validator and the feature quickstart.

## Technical Context

**Language/Version**: Markdown, OpenAPI 3.1.2 YAML, JSON Schema draft 2020-12,
SQL migration text, Python 3.13 validation scripts

**Primary Dependencies**: Existing documentation package, `scripts/validate_package.py`,
`jsonschema`, `PyYAML`, OpenAPI contract, JSON Schemas, runbook-test schema,
and static SQL consistency checks

**Storage**: Repository files only; no database or external service writes

**Testing**: `python scripts/validate_package.py`; optional
`pytest -q tests/test_contracts.py`; optional PostgreSQL security integration
gate when Docker/PostgreSQL is available

**Target Platform**: Documentation release-candidate package for reviewers,
operators, implementers, and release approvers

**Project Type**: Documentation and contract package

**Performance Goals**: Validation should remain deterministic and local; no
network calls are required for the baseline documentation checks

**Constraints**: Preserve live-execution disabled-by-default posture; do not
claim deployed-service, legal, security, financial, signer, venue, or live
trading conformance from static documentation evidence; resolve publication
placeholders before representing baseline publication readiness

**Scale/Scope**: One baseline feature covering the current Hermes documentation
package, its controlled contracts, validation report, publication blockers, and
manual release gates

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Safety authority**: PASS. The feature is documentation-only and preserves
  separation between analytical agents, policy authorization, human approval,
  signer/venue submission, reconciliation, and live enablement. No live service,
  credential, signer, venue, or approval state is changed.
- **Canonical contracts**: PASS. Affected artifacts are identified as controlled
  docs, OpenAPI references, JSON Schema references, SQL/migration references,
  runbook-test references, validation report language, and publication blockers.
- **Tenant, secret, and custody boundaries**: PASS. The feature reinforces
  tenant-derived authorization, secret-handling prohibitions, custody/delegation
  disclosure, and logging limits without introducing secrets or live data.
- **Evidence-first validation**: PASS. Acceptance evidence is
  `python scripts/validate_package.py`, requirements checklist review, optional
  contract tests, optional PostgreSQL security integration when available, and
  explicit manual gates for legal/security/release approval.
- **Honest claims**: PASS. The plan distinguishes documentation baseline,
  static validation, implementation conformance, deployed-service evidence,
  external legal/security review, and live trading approval.

## Project Structure

### Documentation (this feature)

```text
specs/001-baseline-hermes-docs/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── publication-review-contract.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
README.md
SPEC.md
TERMS.md
PRIVACY.md
SECURITY.md
VALIDATION_REPORT.md
docs/
├── Architecture.md
├── ExecutionProtocol.md
├── SecurityPolicy.md
├── DeploymentGuide.md
├── ContributionGuidelines.md
└── ...
openapi/
└── hermes.openapi.yaml
schemas/
├── audit-event.schema.json
├── risk-policy.schema.json
├── runbook-test.schema.json
└── venue-registry.schema.json
infra/supabase/migrations/
└── 0001_core.sql
runbooks/
└── runbook-tests.yaml
scripts/
└── validate_package.py
tests/
└── test_contracts.py
```

**Structure Decision**: Use the existing documentation package layout. This
feature does not add application source directories, services, migrations, or
runtime storage. Planning artifacts remain under
`specs/001-baseline-hermes-docs/`.

## Phase 0: Research

Research completed in [research.md](research.md). Key decisions:

- Treat the baseline as a documentation-contract feature, not application
  implementation.
- Resolve publication placeholders as part of the feature while keeping
  external legal/security approval as a manual release gate.
- Use existing local validation as acceptance evidence, with optional stronger
  gates documented when their runtime dependencies are available.
- Keep canonical artifact alignment review explicit rather than generating new
  runtime contracts.

## Phase 1: Design And Contracts

Design artifacts generated:

- [data-model.md](data-model.md) defines controlled documentation artifacts,
  execution boundaries, validation evidence, publication placeholders, release
  gates, and review findings.
- [contracts/publication-review-contract.md](contracts/publication-review-contract.md)
  defines the review contract for publication readiness and release-boundary
  evidence.
- [quickstart.md](quickstart.md) provides the runnable validation path and
  expected outcomes.

## Post-Design Constitution Check

- **Safety authority**: PASS. Design artifacts only define documentation review
  and validation work. No runtime authority is expanded.
- **Canonical contracts**: PASS. The data model and review contract require
  same-change review for affected controlled artifacts.
- **Tenant, secret, and custody boundaries**: PASS. Secret/custody language is
  represented as documentation requirements and review fields, with no secrets
  or live data introduced.
- **Evidence-first validation**: PASS. Quickstart and contract require evidence
  capture and explicit handling of remaining manual gates.
- **Honest claims**: PASS. Publication readiness is blocked until placeholders
  are resolved, while live/deployed conformance remains separate.

## Complexity Tracking

No constitution violations or complexity exceptions are required.
