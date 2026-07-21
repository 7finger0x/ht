# Data Model: Baseline Hermes Documentation

## Controlled Documentation Artifact

Represents a repository file that defines or supports the Hermes baseline.

**Fields**:

- `path`: project-relative file path.
- `artifact_type`: one of `overview`, `normative_protocol`, `policy`,
  `legal_terms`, `security_notice`, `api_contract`, `schema`, `migration`,
  `runbook`, `validation_report`, `contribution_guidance`, `spec_artifact`.
- `owner_context`: accountable review area, such as documentation, legal,
  security, risk, operations, or release.
- `publication_required`: whether unresolved placeholders in this artifact
  block baseline publication readiness.
- `validation_path`: automated or manual evidence used to review the artifact.

**Relationships**:

- May define one or more `Execution Boundary` records.
- May require one or more `Validation Evidence` records.
- May contain zero or more `Publication Placeholder` records.

## Execution Boundary

Represents a documented safety transition or authority separation.

**Fields**:

- `name`: canonical boundary name.
- `source_stage`: starting responsibility or state.
- `target_stage`: receiving responsibility or state.
- `authorized_by`: actor, policy, approval, or control allowed to advance it.
- `fail_closed_conditions`: conditions that must block or pause progress.
- `evidence_required`: evidence needed to show the boundary is preserved.

**Validation rules**:

- Analytical assessment must not directly authorize signing, venue submission,
  or live enablement.
- Ambiguous, stale, unreconciled, unknown, or policy-incomplete state must have
  a documented fail-closed outcome.

## Canonical Artifact Alignment

Represents a same-change consistency obligation between controlled artifacts.

**Fields**:

- `topic`: behavior or claim that must stay aligned.
- `primary_artifact`: source artifact that defines the behavior.
- `dependent_artifacts`: other artifacts that must be checked in the same
  change.
- `drift_risk`: safety, release, tenant, custody, evidence, or claims risk.
- `acceptance_check`: how reviewers verify alignment.

**Validation rules**:

- Safety-relevant changes to API behavior, schemas, migrations, runbook tests,
  controlled documents, release claims, or execution-state definitions must list
  dependent artifacts.

## Publication Placeholder

Represents bracketed or draft text that must be resolved before baseline
publication readiness can be claimed.

**Fields**:

- `path`: file containing the placeholder.
- `location`: heading or line context.
- `placeholder_text`: the unresolved bracketed text or equivalent draft marker.
- `required_resolution`: concrete text or document change needed.
- `manual_gate`: approval or evidence still needed after text remediation.

**Validation rules**:

- No unresolved bracketed placeholder may remain in public-facing operator,
  legal, security, support, or publication-status text before the baseline is
  represented as publication-ready.
- Resolving text does not by itself satisfy external legal, security, or
  regulatory approval.

## Validation Evidence

Represents automated or manual proof used to support completion.

**Fields**:

- `evidence_type`: automated check, manual review, external approval, runtime
  gate, or release gate.
- `command_or_source`: command, file, checklist, or review source.
- `expected_result`: pass condition or required finding.
- `evidence_boundary`: what the evidence proves and what it does not prove.
- `blocking`: whether failure blocks feature acceptance.

**Validation rules**:

- Static documentation checks cannot be represented as deployed-service,
  legal, security, financial, signer, venue, or live-trading conformance.
- Any remaining manual gate must be named with release impact.

## Release Gate

Represents a condition that blocks a release or live enablement claim.

**Fields**:

- `gate_name`: short name.
- `scope`: publication, production deployment, live execution, legal,
  security, signer, venue, or operational readiness.
- `required_evidence`: evidence needed to satisfy the gate.
- `current_status`: `satisfied`, `blocked`, `not_applicable`, or
  `outside_feature_scope`.
- `claim_restriction`: claims prohibited until the gate is satisfied.

**Validation rules**:

- Live execution, production credentials, signer integration, venue
  integration, external legal review, independent security assurance, and
  customer-data handling remain separate from baseline publication readiness
  unless separately authorized and evidenced.

## Review Finding

Represents a discrepancy discovered while validating baseline readiness.

**Fields**:

- `finding_id`: stable identifier for tracking.
- `source`: check, reviewer, or artifact that found the issue.
- `severity`: blocking, warning, advisory.
- `affected_requirement`: linked FR, SAE, or SC from the spec.
- `resolution`: planned correction or accepted residual gate.

**Relationships**:

- May refer to a `Publication Placeholder`, `Canonical Artifact Alignment`, or
  `Validation Evidence` record.
