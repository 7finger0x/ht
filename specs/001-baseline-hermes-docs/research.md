# Research: Baseline Hermes Documentation

## Decision: Treat The Feature As A Documentation-Contract Baseline

**Rationale**: The feature description asks for safety-gated execution,
canonical contracts, validation evidence, and release boundaries. The repository
is a documentation release-candidate package with controlled documents,
machine-readable contracts, validators, schemas, runbook tests, and release
reports. The safest plan is to update documentation and evidence artifacts
rather than introduce application code or runtime integrations.

**Alternatives considered**:

- Build or modify runtime trading services. Rejected because the spec scopes the
  baseline documentation package, not a deployed service.
- Limit the feature to the Spec Kit spec alone. Rejected because the clarified
  scope includes publication-placeholder remediation and baseline publication
  readiness.

## Decision: Include Publication-Placeholder Remediation In This Feature

**Rationale**: Clarification selected inclusion. The current validator reports
remaining bracketed placeholder text in `TERMS.md` and
`docs/SecurityPolicy.md`. These placeholders directly affect publication
readiness and contradict a baseline that claims resolved release boundaries.

**Alternatives considered**:

- Record placeholders only as release blockers. Rejected by clarification.
- Split placeholder remediation into another feature. Rejected by
  clarification; may still be useful later for broader legal/security review.

## Decision: Preserve External Legal And Security Approval As Manual Gates

**Rationale**: Removing placeholder text can make the package structurally
complete, but it does not establish legal advice, jurisdiction-specific
approval, independent security assurance, bounty authorization, or regulatory
fitness. The plan must resolve text while preserving the evidence boundary.

**Alternatives considered**:

- Treat placeholder remediation as legal approval. Rejected because the
  constitution requires honest conformance claims.
- Leave all legal/security language as placeholders. Rejected because the
  feature scope includes remediation before baseline publication readiness.

## Decision: Use Existing Local Validation As Primary Automated Evidence

**Rationale**: `scripts/validate_package.py` already checks required files,
schemas, OpenAPI references, Markdown links, JSON and shell examples, runbook
tests, environment examples, Docker Compose parsing, SQL static consistency,
and publication placeholders. It is deterministic and local.

**Alternatives considered**:

- Require production integration tests for this documentation baseline. Rejected
  because they remain release gates outside the documentation-only feature.
- Use manual review only. Rejected because automated checks are available and
  already aligned with the package contract.

## Decision: Generate A Review Contract Instead Of New Runtime Interfaces

**Rationale**: This feature has no new API, CLI, database, or UI surface. The
meaningful interface is the review/acceptance contract that tasks and reviewers
will use to decide whether baseline publication readiness is evidenced.

**Alternatives considered**:

- Generate OpenAPI or JSON Schema contracts. Rejected because no new runtime
  interface is introduced.
- Skip contracts entirely. Rejected because Spec Kit planning benefits from an
  explicit acceptance contract for publication readiness.
