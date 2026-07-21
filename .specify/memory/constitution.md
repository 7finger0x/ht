<!--
Sync Impact Report
Version change: template -> 1.0.0
Modified principles:
- principle slot 1 -> I. Safety Authority Fails Closed
- principle slot 2 -> II. Canonical Contracts Stay Aligned
- principle slot 3 -> III. Tenant, Secret, and Custody Boundaries
- principle slot 4 -> IV. Evidence-First Validation
- principle slot 5 -> V. Honest Release and Conformance Claims
Added sections:
- Safety-Critical Development Constraints
- Spec Kit Workflow and Quality Gates
Removed sections:
- None
Templates requiring updates:
- .specify/templates/plan-template.md - updated
- .specify/templates/spec-template.md - updated
- .specify/templates/tasks-template.md - updated
- .specify/templates/commands/*.md - not present in this installation
Follow-up TODOs:
- None
-->
# Hermes Constitution

## Core Principles

### I. Safety Authority Fails Closed

Hermes features MUST preserve the separation between analytical reasoning,
deterministic policy authorization, human approval where required, and isolated
signing or venue submission. Analytical agents MUST NOT receive credentials,
call venues, submit orders, bypass risk policy, or create signing authority.
Unknown, stale, ambiguous, unreconciled, or policy-incomplete state MUST fail
closed. Live execution remains disabled until the documented release gates are
evidenced and an authorized operator explicitly enables the approved scope.

Rationale: Hermes can create economic effects. A feature is unacceptable if it
allows model output, UI state, retry behavior, or missing evidence to become an
implicit trading authorization.

### II. Canonical Contracts Stay Aligned

OpenAPI, JSON Schemas, SQL migrations, runbook tests, controlled documents, and
normative execution-state definitions MUST remain aligned in the same change.
Any feature that changes API shape, enums, risk policy, audit events, tenancy,
state transitions, evidence bundles, or configuration MUST update the canonical
machine-readable artifact first or in the same pull request. Contradictions
between normative artifacts are release-blocking specification defects.

Rationale: Hermes relies on deterministic replay, idempotency, and auditability.
Drift between contracts is operational risk, not documentation cleanup.

### III. Tenant, Secret, and Custody Boundaries

Tenant identity MUST be derived from verified server-side authorization context,
never from client-supplied owner or tenant fields. Secrets, wallet keys, seed
phrases, CEX credentials, bearer tokens, production personal data, and live
customer data MUST NOT be committed, logged, placed in prompts, or stored in
frontend builds. Browser and UI authorization are never security boundaries.
Custody, signing, and delegated authority MUST be explicit, scoped, expiring,
revocable, audited, and independently enforced.

Rationale: The project combines identity, trading authority, credentials, and
tenant isolation. Boundary mistakes can expose accounts or assets.

### IV. Evidence-First Validation

Every safety-relevant change MUST include reproducible validation evidence
appropriate to its risk: unit tests, integration tests, negative tests,
deterministic fixtures, schema checks, migration/RLS checks, idempotency and
concurrency tests, signer/venue conformance tests, runbook tests, or documented
manual gates. Tests that assert new behavior MUST be written or updated before
implementation when practical and MUST fail for the missing behavior before
being used as acceptance evidence. Static checks alone MUST NOT be represented
as live-service, legal, security, financial, or production conformance.

Rationale: Hermes documentation and code are only as trustworthy as the evidence
that proves the claimed behavior at the correct boundary.

### V. Honest Release and Conformance Claims

Project text, UI copy, examples, release notes, specs, and plans MUST avoid
claims such as autonomous profit, institutional-grade, verified, audited,
secure, decentralized, non-custodial, or production-ready unless the claim is
scoped and backed by current evidence. Documentation MUST distinguish design
intent, static package validation, implementation conformance, deployed service
evidence, and live trading approval.

Rationale: Overstated claims create user, operator, legal, and safety risk. The
system must describe what is evidenced, what is configured but unverified, and
what remains gated.

## Safety-Critical Development Constraints

- Financial quantities, limits, thresholds, fees, and monetary comparisons MUST
  use deterministic decimal, integer base-unit, or venue-native precise types.
  Binary floating point MUST NOT decide an economic limit.
- Mutating API behavior MUST use scoped idempotency and conflict semantics that
  prevent duplicate economic effects.
- Execution and order state transitions MUST validate the expected prior state
  and MUST NOT regress terminal states.
- Audit evidence MUST be append-only to application roles, tenant-scoped,
  hash-linked where applicable, and sufficient to reproduce the decision,
  authorization, signing, submission, fill, and reconciliation path.
- Changes to identity, RLS, consensus, risk, signer, credentials, venues,
  migrations, privacy, or Terms require explicit security/risk ownership review
  before release.
- Examples, fixtures, and local configuration MUST be simulation-safe by
  default. Live defaults MUST fail closed.

## Spec Kit Workflow and Quality Gates

Specs MUST identify affected safety boundaries, canonical contracts, tenant and
credential impact, evidence requirements, and release gates before planning.
Plans MUST pass the Constitution Check before Phase 0 research and again after
Phase 1 design. Tasks MUST include explicit validation, documentation, and
contract-alignment work for each affected user story or safety boundary.

Implementation MAY proceed incrementally by independently testable user story,
but each increment MUST preserve the core principles. A checkpoint is not
complete until its evidence is recorded and any remaining manual gate is named.

## Governance

This constitution supersedes informal practices for Spec Kit-driven work in the
Hermes package. Amendments require a pull request or equivalent reviewed change
that explains the reason, affected principles, migration impact, dependent
template updates, and validation evidence.

Versioning follows semantic versioning:

- MAJOR: removes, relaxes, or redefines a core principle or governance gate in a
  backward-incompatible way.
- MINOR: adds a principle, mandatory section, safety boundary, or materially
  expands required evidence.
- PATCH: clarifies wording, fixes errors, or updates examples without changing
  obligations.

Every `/speckit-plan`, `/speckit-tasks`, `/speckit-implement`, and
`/speckit-converge` run MUST check active work against this constitution.
Non-compliance MUST be corrected or explicitly documented in Complexity
Tracking with owner-approved justification before implementation continues.

**Version**: 1.0.0 | **Ratified**: 2026-07-21 | **Last Amended**: 2026-07-21
