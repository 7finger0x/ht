# Contract: Baseline Publication Review

## Purpose

This contract defines the evidence required before the baseline Hermes
documentation feature can be treated as publication-ready. It is a review
contract for documentation and release approval, not a runtime API.

## Inputs

- `specs/001-baseline-hermes-docs/spec.md`
- `specs/001-baseline-hermes-docs/plan.md`
- Controlled documentation artifacts listed in the plan
- `TERMS.md`
- `docs/SecurityPolicy.md`
- `VALIDATION_REPORT.md`
- Output from `python scripts/validate_package.py`
- Any optional stronger evidence, such as contract tests or PostgreSQL security
  integration output

## Required Review Results

### R1: Safety Authority Boundary

The review MUST confirm that baseline documentation preserves separation between
analysis, deterministic policy authorization, approval where required, signing
or credential use, venue submission, reconciliation, audit evidence, and live
enablement.

**Pass condition**: No document implies that analytical agents can submit
orders, hold credentials, bypass risk policy, or create signing authority.

### R2: Canonical Artifact Alignment

The review MUST confirm that safety-relevant behavior is represented
consistently across the applicable controlled artifacts.

**Pass condition**: Any discovered drift is either corrected in the same feature
or recorded as a blocking review finding.

### R3: Publication Placeholder Remediation

The review MUST confirm that inherited or introduced publication placeholders in
public-facing operator, legal, security, support, and publication-status text
are resolved before baseline publication readiness is claimed.

**Pass condition**: `python scripts/validate_package.py` reports zero
publication-placeholder warnings, or remaining warnings are explicitly marked as
outside publication-facing scope with reviewer approval.

### R4: Evidence Boundary

The review MUST distinguish static documentation validation from implementation,
deployed-service, legal, independent security, signer, venue, and live-trading
conformance.

**Pass condition**: Validation and release language names what is evidenced,
what is not evidenced, and what remains gated.

### R5: Manual Release Gates

The review MUST preserve manual gates that cannot be satisfied by this
documentation feature.

**Pass condition**: External legal review, independent security assurance,
production deployment, live trading enablement, signer/venue conformance, and
customer-data handling are either out of scope or backed by separately recorded
evidence.

## Output Record

The implementation should leave a review summary in the feature task evidence or
validation report update containing:

- reviewer or agent identity;
- date;
- validator command and result;
- files changed;
- remaining manual gates;
- release claims allowed by the evidence;
- release claims still prohibited.

## Failure Handling

Any blocking failure MUST become an implementation task before the feature is
accepted. Warnings MAY remain only when their scope and release impact are
explicitly documented.
