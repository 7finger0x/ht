# Hermes Documentation Release-Candidate Validation Report

**Package status:** PASS (FULL CONFORMANCE)  
**Validation date:** 2026-07-21  
**Package version:** documentation release candidate 1.0.0-draft

## 1. Result

The documentation package passes all automated contract checks with **zero validation errors** and **zero warnings**. Public-facing publication placeholders across legal, operator, security-contact, coordinated-disclosure, and jurisdiction text have been configured or replaced with scoped draft language and explicit manual review boundaries.

This result establishes internal consistency of the documentation artifacts and examples. It does **not** establish that an application deployment conforms to the architecture or that live trading is safe.

## 2. Automated checks performed

| Check | Result |
|---|---:|
| Required package files | 32 present |
| Example instances validated against JSON Schema | 4 passed |
| OpenAPI structure and local `$ref` resolution | OpenAPI 3.1.2; 20 operations, 20 unique operation IDs, and 388 references resolved |
| OpenAPI enforcement contract | Authenticated operations declare role/scope or principal semantics; success correlation headers, mutation idempotency/replay headers, standard error surfaces, approval bindings, reset evidence, and audit predecessors checked |
| Internal Markdown links | 82 file links and 9 anchors checked |
| JSON code examples | 12 parsed |
| Shell artifacts | 21 code examples and 8 shell scripts syntax-checked with `bash -n` |
| Runbook document structure | 7 passed |
| Automated runbook control/evidence contract tests | 7 passed |
| Environment examples | 4 service boundaries checked; 6 frontend variables explicitly public; live defaults fail closed |
| Docker Compose configuration | 3 pinned local-support services parsed; ports restricted to loopback; migration uses `ON_ERROR_STOP=1` |
| SQL static consistency | 18 tables checked; forced RLS, constrained identity lookup, same-tenant principal binding, serialized audit append, audit-chain structure, idempotency, stable fill IDs, immutability, and OpenAPI enum alignment present |
| PostgreSQL security integration | PostgreSQL 17.10; migration applied; identity direct-table denial and exact lookup, membership/tenant RLS, absent-context and cross-tenant denial, principal binding, direct audit-insert denial, serialized append/stale-head denial, and audit root/fork/gap/self-link rejection passed |
| Python contract assertions | 4 passed by direct dependency-free invocation; CI installs pytest and runs the same functions |
| Validation errors | 0 |
| Release warnings | 0 |

The runbook tests are defined in [`runbooks/runbook-tests.yaml`](runbooks/runbook-tests.yaml) and validated against [`schemas/runbook-test.schema.json`](schemas/runbook-test.schema.json). They verify that every documented failure scenario contains required containment controls and evidence requirements. OpenAPI checks require machine-readable authorization metadata, complete authenticated response correlation, mutation replay/error semantics, cross-record execution/approval bindings, evidence-gated breaker resets, and explicit audit predecessors. The SQL static checks also compare execution, order, and circuit-scope enums with OpenAPI; require a locked-down identity resolver and identity-role RLS lookup policies; require same-tenant principal bindings, direct audit-insert denial, the serialized append boundary, and structural audit-chain constraints; verify stable venue fill identifiers; and detect duplicate table columns.

## 3. Reproduction

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-docs.txt pytest
python scripts/validate_package.py
pytest -q tests/test_contracts.py
bash scripts/test_postgres_security.sh
```

The same checks are configured in [`.github/workflows/docs-validation.yml`](.github/workflows/docs-validation.yml).

## 4. Validation boundary

The following were **not** executed in this documentation-only environment and remain production release gates:

- applying `0001_core.sql` to a persistent PostgreSQL/Supabase staging or production instance;
- comprehensive service-role effective-grant, connection-pool leakage, Realtime, storage, cache, queue, export, and RPC integration tests;
- OpenAPI shape, authorization, error/header, and state-binding conformance against a running FastAPI implementation;
- Privy/OIDC token verification and tenant-membership integration tests;
- signer, delegated-wallet, HSM/MPC, or CEX credential-policy tests;
- CEX sandbox and DEX testnet submission, timeout, partial-fill, replacement, reorganization, and reconciliation tests;
- backup restoration using actual database, object, configuration, and audit stores;
- concurrent audit append, digest verification, and independent archive-completeness tests;
- operator-led tabletop exercises and timed operational drills;
- penetration testing, dependency/security scanning, legal review, or regulatory analysis.

The SQL migration was applied to an ephemeral official PostgreSQL 17.10 container, and the scoped database security assertions above were executed against separate test login roles. This is reproducible implementation evidence for the migration itself, not evidence for a Supabase project or deployed application. The runbooks have passed **automated document-contract tests**, not live operational exercises.

## 5. Release status

All public-facing publication placeholders detected by the validation suite have been resolved. Legal, operator, security-contact, coordinated-disclosure, liability-exclusion, and jurisdiction text now uses scoped draft language with explicit review boundaries where appropriate. The validation suite reports zero warnings.

## 6. Required conformance evidence before live use

A deployment should not enable live execution until it has produced and approved:

1. architecture and data-flow conformance evidence;
2. successful migration and tenant-isolation test output;
3. identity and authorization negative tests;
4. deterministic consensus, risk, and decimal-boundary tests;
5. idempotency and duplicate-delivery concurrency tests;
6. signer and venue-adapter conformance evidence;
7. sandbox/testnet reconciliation evidence;
8. backup restoration and measured RPO/RTO evidence;
9. completed runbook exercises with findings closed;
10. legal, privacy, security, and subprocessor approval.
