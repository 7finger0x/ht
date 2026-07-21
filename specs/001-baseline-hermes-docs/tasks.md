# Tasks: Baseline Hermes Documentation

**Input**: Design documents from `/specs/001-baseline-hermes-docs/`

**Prerequisites**: plan.md (required), spec.md (required for user stories),
research.md, data-model.md, contracts/publication-review-contract.md,
quickstart.md

**Tests**: This documentation-contract feature requires validation tasks because
it affects Hermes release claims, publication placeholders, controlled
documents, and safety-boundary evidence.

**Organization**: Tasks are grouped by user story to enable independent
implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Context)

**Purpose**: Confirm active feature state and capture the current publication
warning baseline before editing controlled documents.

- [x] T001 Verify active feature paths with `.specify/scripts/bash/check-prerequisites.sh --json --paths-only`
- [x] T002 [P] Review feature requirements in `specs/001-baseline-hermes-docs/spec.md`
- [x] T003 [P] Review constitution gates in `.specify/memory/constitution.md`
- [x] T004 Run `python scripts/validate_package.py` and record the current publication-placeholder warning in `specs/001-baseline-hermes-docs/tasks.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Identify the exact controlled-document edits needed before any
user-story completion can be claimed.

**Checkpoint**: No user story work can be accepted until the two known
publication placeholders and affected release-boundary artifacts are mapped.

- [x] T005 Identify the liability-exclusions placeholder and surrounding release impact in `TERMS.md`
- [x] T006 Identify the coordinated-disclosure placeholder and surrounding release impact in `docs/SecurityPolicy.md`
- [x] T007 [P] Review release-status and validation-boundary language in `VALIDATION_REPORT.md`
- [x] T008 [P] Review safety-boundary summary language in `README.md`
- [x] T009 Map affected requirements FR-001 through FR-010 and SAE-001 through SAE-005 from `specs/001-baseline-hermes-docs/spec.md` to the files identified in T005-T008

---

## Phase 3: User Story 1 - Understand Safe Execution Boundaries (Priority: P1)

**Goal**: Operators, reviewers, and implementers can identify execution
authority boundaries, fail-closed behavior, and live-enablement gates without
implementation source code.

**Independent Test**: Reviewers can trace market snapshot through
reconciliation across the baseline docs and confirm that analytical agents do
not gain trading, signing, credential, or live-execution authority.

### Tests and Evidence for User Story 1

- [x] T010 [P] [US1] Verify no controlled document grants analytical agents trading, signing, credential, or live-execution authority in `README.md`, `SPEC.md`, `docs/Architecture.md`, `docs/ExecutionProtocol.md`, and `docs/SecurityPolicy.md`
- [x] T011 [P] [US1] Verify stale, ambiguous, unreconciled, unknown, and policy-incomplete states fail closed in `SPEC.md` and `docs/ExecutionProtocol.md`

### Implementation for User Story 1

- [x] T012 [US1] Update safety-boundary wording in `README.md`, `SPEC.md`, `docs/Architecture.md`, `docs/ExecutionProtocol.md`, or `docs/SecurityPolicy.md` only if T010 or T011 finds drift
- [x] T013 [US1] Record US1 evidence against R1 in `specs/001-baseline-hermes-docs/contracts/publication-review-contract.md` or the task evidence notes in `specs/001-baseline-hermes-docs/tasks.md`

**Checkpoint**: US1 is complete when authority boundaries and fail-closed
conditions are clear and no live-execution expansion is implied.

---

## Phase 4: User Story 2 - Verify Canonical Contract Alignment (Priority: P2)

**Goal**: Contributors can identify canonical artifacts and companion updates
required for safety-relevant changes.

**Independent Test**: Reviewers can compare the repository contract with
normative docs and machine-readable artifacts and confirm each affected artifact
has a validation or review path.

### Tests and Evidence for User Story 2

- [x] T014 [P] [US2] Verify repository contract references and validation paths in `README.md`, `VALIDATION_REPORT.md`, `openapi/hermes.openapi.yaml`, `schemas/runbook-test.schema.json`, `runbooks/runbook-tests.yaml`, and `scripts/validate_package.py`
- [x] T015 [P] [US2] Verify contributor same-change review expectations in `docs/ContributionGuidelines.md`

### Implementation for User Story 2

- [x] T016 [US2] Update canonical artifact alignment language in `README.md`, `VALIDATION_REPORT.md`, or `docs/ContributionGuidelines.md` only if T014 or T015 finds drift
- [x] T017 [US2] Record US2 evidence against R2 in `specs/001-baseline-hermes-docs/contracts/publication-review-contract.md` or the task evidence notes in `specs/001-baseline-hermes-docs/tasks.md`

**Checkpoint**: US2 is complete when canonical artifact roles and same-change
review expectations are clear and validation paths are identified.

---

## Phase 5: User Story 3 - Distinguish Evidence From Release Claims (Priority: P3)

**Goal**: Publication reviewers can distinguish static validation from
implementation conformance, deployed-service evidence, external approval, and
live trading approval.

**Independent Test**: `python scripts/validate_package.py` reports zero
publication-placeholder warnings, and release language does not claim legal,
security, signer, venue, deployed-service, or live-trading conformance from
static documentation checks.

### Tests and Evidence for User Story 3

- [x] T018 [P] [US3] Verify the limitation-of-liability placeholder is the only unresolved publication text in `TERMS.md` before editing
- [x] T019 [P] [US3] Verify the coordinated-disclosure placeholder is the only unresolved publication text in `docs/SecurityPolicy.md` before editing
- [x] T020 [US3] Run `python scripts/validate_package.py` and preserve the pre-remediation warning output for comparison

### Implementation for User Story 3

- [x] T021 [US3] Replace the bracketed liability-exclusions placeholder with scoped draft exclusions and legal-review boundary language in `TERMS.md`
- [x] T022 [US3] Replace the bracketed coordinated-disclosure placeholder with concrete private-reporting, response-target, safe-harbor, encryption-key, and bounty-status language in `docs/SecurityPolicy.md`
- [x] T023 [US3] Update `VALIDATION_REPORT.md` with final validator output counts, publication-placeholder status, and release-boundary language after T021-T022
- [x] T024 [US3] Verify examples, configs, docs, fixtures, logs/model-payload language, and frontend-public variable guidance do not expose secrets or unapproved personal data in `README.md`, `docs/SecurityPolicy.md`, `docs/ContributionGuidelines.md`, `config/`, and `docs/`
- [x] T025 [US3] Run `python scripts/validate_package.py` and confirm zero publication-placeholder warnings for `TERMS.md` and `docs/SecurityPolicy.md`

**Checkpoint**: US3 is complete when publication placeholders are resolved,
manual external gates remain explicit, and static validation is not overstated.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final consistency, quickstart validation, and handoff evidence.

- [x] T026 [P] Run `pytest -q tests/test_contracts.py` if local test dependencies are available
- [x] T027 [P] Run `bash scripts/test_postgres_security.sh` if Docker/PostgreSQL is available, otherwise record it as not run in `specs/001-baseline-hermes-docs/tasks.md`
- [x] T028 Validate quickstart steps in `specs/001-baseline-hermes-docs/quickstart.md`
- [x] T029 Update task evidence notes in `specs/001-baseline-hermes-docs/tasks.md` with validator results, optional gates run or skipped, remaining manual gates, and release claims still prohibited

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup completion and blocks story acceptance.
- **US1 (Phase 3)**: Depends on Foundational mapping.
- **US2 (Phase 4)**: Depends on Foundational mapping; can run after US1 evidence checks or in parallel if file edits do not overlap.
- **US3 (Phase 5)**: Depends on Foundational mapping; can run independently of US1/US2 once release-boundary files are identified.
- **Polish (Phase 6)**: Depends on desired user stories being complete.

### User Story Dependencies

- **US1**: Independent safety-boundary evidence slice.
- **US2**: Independent canonical-alignment evidence slice.
- **US3**: Independent publication-readiness evidence slice; required for zero-warning validation.

### Within Each User Story

- Evidence tasks precede document edits.
- Document edits precede final validator runs.
- Any drift discovered by evidence tasks must be corrected before the story checkpoint is complete.

---

## Parallel Opportunities

- T002 and T003 can run in parallel.
- T007 and T008 can run in parallel.
- T010 and T011 can run in parallel.
- T014 and T015 can run in parallel.
- T018 and T019 can run in parallel.
- T026 and T027 can run in parallel after US3 is complete, subject to local dependencies.

---

## Parallel Example: User Story 3

```bash
Task: "Verify the limitation-of-liability placeholder is the only unresolved publication text in TERMS.md before editing"
Task: "Verify the coordinated-disclosure placeholder is the only unresolved publication text in docs/SecurityPolicy.md before editing"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2.
2. Complete US1 authority-boundary verification and any required corrections.
3. Stop and validate that safety-gated execution remains clear and fail-closed.

### Incremental Delivery

1. Complete Setup and Foundational mapping.
2. Deliver US1 safety-boundary clarity.
3. Deliver US2 canonical artifact alignment.
4. Deliver US3 publication-placeholder remediation, secret-exposure review, and zero-warning validation.
5. Complete Polish validation and evidence notes.

### Acceptance Target

The full baseline feature is accepted when all selected story checkpoints pass,
`python scripts/validate_package.py` reports zero errors and zero
publication-placeholder warnings, and remaining external legal, security,
deployment, signer, venue, and live-trading gates are explicitly preserved.

## Evidence Notes

- T001: Active feature resolved to `specs/001-baseline-hermes-docs`.
- T004/T020: Pre-remediation validation reported `0 error(s), 1 warning(s)`,
  with two publication placeholders in `TERMS.md` and `docs/SecurityPolicy.md`.
- T010-T013: Safety-boundary review found existing docs already state that
  analytical agents cannot call venues/signers directly and ambiguous, stale, or
  unreconciled state fails closed; no safety-boundary rewrite was required.
- T014-T017: Canonical artifact review found repository contract and
  same-change review language present; `VALIDATION_REPORT.md` was updated for
  final validation counts and publication-placeholder status.
- T021-T025: `TERMS.md` and `docs/SecurityPolicy.md` placeholders were replaced
  with scoped draft language while preserving legal/security review gates.
- T024: Secret and unapproved-personal-data guidance was verified across
  `README.md`, `docs/SecurityPolicy.md`, `docs/ContributionGuidelines.md`,
  `config/`, and `docs/`; no additional exposure-remediation edit was needed.
- T025/T028: Final `python scripts/validate_package.py` result was
  `0 error(s), 0 warning(s)`.
- T026: `pytest` was not installed (`pytest` not found; `python -m pytest`
  reported `No module named pytest`), so the optional contract-test gate was not
  run.
- T027: `bash scripts/test_postgres_security.sh` reported Docker is required,
  so the optional PostgreSQL security integration gate was not run in this WSL
  environment.
- Remaining manual gates: external legal review, independent security
  assessment where represented, production deployment evidence, signer/venue
  conformance, customer-data handling validation, and live-trading approval.
- Claims still prohibited: deployed-service conformance, legal approval,
  independent security assurance, signer/venue conformance, production
  readiness, and live-trading approval.
