# Hermes Contribution Guidelines

**Version:** 1.0.0-draft  
**Last revised:** 2026-07-20

Hermes includes safety-critical trading, identity, tenant, signing, and reconciliation logic. Contributions are evaluated for behavior, security, operability, data impact, and documentation—not only code style.

## 1. Before contributing

- Review [Architecture](Architecture.md), [Execution Protocol](ExecutionProtocol.md), [Security Policy](SecurityPolicy.md), and the [OpenAPI contract](../openapi/hermes.openapi.yaml).
- Do not introduce a second architectural model without an approved architecture decision record.
- Do not add live wallet keys, CEX credentials, production data, access tokens, or personal information to code, tests, fixtures, issues, or pull requests.
- Use simulation, testnet, sandbox, or deterministic fixtures.
- Security vulnerabilities are reported privately through [SECURITY.md](../SECURITY.md), not a public issue.

## 2. Branch and review policy

- `main` is protected and releasable.
- Short-lived branches use `feature/`, `fix/`, `security/`, `docs/`, or `chore/` prefixes.
- Every change requires a pull request, passing CI, and at least one independent approval.
- Changes to identity, RLS, risk, consensus, signer, credentials, venues, migrations, privacy, or Terms require approval from the relevant code owner and security/risk owner.
- No author may solely approve and release a high-risk change.
- Emergency fixes follow incident change control and receive retrospective review.

Commit messages should use conventional prefixes such as `feat:`, `fix:`, `security:`, `docs:`, `test:`, `refactor:`, or `chore:`.

## 3. Coding standards

### Python

- Python 3.13 baseline.
- Full type annotations for production code.
- `ruff` for linting/formatting and `mypy` or an approved strict type checker.
- Pydantic models reject unknown safety-critical fields.
- `Decimal`, integer base units, or venue-native precise types for financial values; no binary floating-point decisions.
- Explicit timeouts, bounded retries, typed error categories, and UTC-aware timestamps.
- No network, database, signer, or venue call hidden inside a model/parser function.

### TypeScript/React

- Node.js 24 LTS baseline and committed lock file.
- Strict TypeScript and ESLint.
- Browser code treats all `VITE_*` variables as public.
- Access tokens are not logged or persisted insecurely.
- UI authorization is not a security boundary; the API enforces every action.
- Transaction and approval screens display exact chain, venue, asset, quantity, recipient/contract, price/minimum received, fees, expiry, and digest where applicable.

### SQL and migrations

- Migrations are versioned, reviewed, and tested forward and through the approved rollback/roll-forward path.
- Every tenant table includes `tenant_id`, indexes used by RLS, enabled and forced RLS, and explicit `USING`/`WITH CHECK` policies.
- Application roles are non-owner and `NOBYPASSRLS`.
- New tables receive no default public grants.
- Cross-tenant foreign keys include tenant identity or an equivalent trigger constraint.
- Immutable evidence cannot be updated or deleted by application roles.

## 4. Required tests

### General

- unit tests;
- integration tests;
- deterministic fixtures;
- negative and failure-path tests;
- regression test for every bug;
- documentation and schema validation.

### Identity and tenancy

Test bad signature, wrong issuer/audience/application, expiry, revoked membership, wrong role, tenant-selector mismatch, absent transaction context, context leakage through pooling, and cross-tenant select/insert/update/delete.

### Consensus and risk

Test deterministic replay, decimal boundaries, stale data, missing fields, excluded agents, quorum, ties, abstention, weight normalization, every risk rule, `UNKNOWN` rejection, rounding down, and property invariants showing hard limits cannot be exceeded.

### Idempotency and state

Test concurrent duplicate requests/jobs, same-key same-body replay, same-key different-body conflict, economic uniqueness, optimistic state transitions, out-of-order venue events, timeout lookup, and terminal-state non-regression.

### Signer and credentials

Test authentication, expiry, replay, wrong chain, contract/program, recipient, method/instruction, asset, quantity, fee, nonce, risk/approval digest, delegation expiry/revocation, and no key export. Verify CEX withdrawals/transfers remain disabled.

### Venue and reconciliation

Test precision, symbol/token identity, min/max notional, partial fills, cancel races, rate limits, websocket gaps, CEX timeout/client-order lookup, DEX dropped/replaced/reverted/reorged transactions, finality, fees, and balance reconciliation.

### Privacy and logging

Test that logs, traces, errors, fixtures, and model payloads do not contain secrets, full tokens, raw private keys, CEX secrets, or unapproved personal data. Test retention and deletion jobs.

## 5. Local validation

For this documentation package:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-docs.txt
python scripts/validate_package.py
```

The application repository should provide one top-level deterministic CI command, for example:

```bash
make ci
```

That target should run frontend and backend lint, type, unit, integration, security, schema, migration, and E2E tests using locked dependencies.

## 6. Pull request content

A pull request states:

- problem and intended behavior;
- architecture and threat-model impact;
- data, privacy, custody, and transaction-authority impact;
- API/schema/migration changes;
- exact tests and evidence;
- operational metrics, alerts, and runbook changes;
- rollout, feature flag, compatibility, and rollback plan;
- whether live execution, limits, venue scope, or signing authority expands.

Screenshots alone are not test evidence for safety-critical behavior.

## 7. Documentation rules

- Use canonical terms from [Glossary](Glossary.md).
- Do not use “institutional-grade,” “verified,” “100% traceable,” “decentralized,” “non-custodial,” “high probability,” or similar claims without precise scope and evidence.
- Update OpenAPI/JSON Schemas before or with implementation changes.
- Keep examples valid JSON/YAML and use decimal strings.
- Add owner, version, last-revised date, and review cadence to controlled documents.
- Repair internal links in the same pull request.

## 8. Release controls

A release requires:

- protected CI and review completion;
- dependency locks, SBOM, vulnerability and secret scans;
- signed/provenance-attested immutable artifacts where supported;
- staging simulation and migration tests;
- venue/signer conformance for affected adapters;
- approved change and rollback plan;
- post-deployment verification;
- release evidence with source commit and image digest.

Live enablement is a separate approved action from software deployment.

## 9. Licensing and contributor terms

No license or contributor agreement was supplied with the original documentation. The project owner must add an approved license and contributor terms before accepting external code or documentation contributions.
