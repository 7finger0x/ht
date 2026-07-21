# Hermes Deployment Guide

**Version:** 1.0.0-draft  
**Last revised:** 2026-07-20  
**Status:** Canonical deployment contract; application repository conformance not yet verified

## 1. Select the deployment and authority model

Do not begin production provisioning until these decisions are recorded:

| Decision | Required selection |
|---|---|
| Deployment | Managed multi-tenant, dedicated single-tenant, or self-hosted |
| Environment | Development, staging, or production |
| Execution | Simulation or live; production begins with live disabled |
| On-chain authority | User-in-loop, delegated policy wallet, or customer-managed signer |
| CEX authority | Disabled or trading-only credential with withdrawals disabled |
| Identity | Privy for managed default, or approved OIDC provider |
| Data region and retention | Documented in deployment record and legal documents |
| Support access | Roles, approvals, duration, and audit path |
| Recovery targets | RPO/RTO approved for each data store |

The selected model must match [Architecture](Architecture.md), [Privacy Policy](../PRIVACY.md), [Terms](../TERMS.md), and [Security Policy](SecurityPolicy.md).

## 2. Supported toolchain baseline

The canonical baseline for a new implementation is:

- Node.js **24 LTS** for the Vite/React application;
- Python **3.13** for FastAPI services and workers;
- PostgreSQL 15 or later, using Supabase-compatible features where applicable;
- Redis-compatible queue/cache with persistence configured for job use;
- Docker/OCI images for API, workers, migration jobs, and optional local services;
- GitHub Actions or equivalent CI with protected environments.

Pin exact patch versions in the application repository and update them through a reviewed dependency process. Do not use unsupported Node.js 18 or 20 lines for a new 2026 production deployment.

## 3. Expected repository layout

```text
apps/web/                         Vite/React browser application
services/api/                     FastAPI control API
services/worker/                  ingestion, analysis, execution, reconciliation workers
services/signer/                  isolated signer client/service or adapter
config/                           validated policy and venue configuration
openapi/hermes.openapi.yaml       authoritative HTTP contract
schemas/                          JSON Schemas
infra/supabase/migrations/        database migrations
infra/docker/                     local supporting services
runbooks/                         operational procedures
scripts/validate_package.py       documentation and contract validation
```

The delivered documentation package does not contain the application source. Commands referring to application services are the required interface for the code repository to implement.

## 4. Validate the documentation contract

From the package root:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-docs.txt
python scripts/validate_package.py
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`.

The validator checks JSON/YAML syntax, JSON Schema examples, OpenAPI references, internal links, SQL safety markers, configuration classes, and runbook structure. It is not an integration or security test of a deployed application.

## 5. Local support services

Start Postgres, Redis, and the one-time schema migration:

```bash
docker compose -f infra/docker/compose.yaml up -d postgres redis
docker compose -f infra/docker/compose.yaml run --rm migrate
```

The compose password is development-only and binds services to localhost. Do not reuse it or the compose file as production infrastructure.

Create separate local login roles after migration. Generate real random local passwords rather than copying these placeholders:

```sql
create role hermes_app_login login inherit nobypassrls password 'replace-local-only';
grant hermes_api to hermes_app_login;

create role hermes_worker_login login inherit nobypassrls password 'replace-local-only';
grant hermes_worker to hermes_worker_login;

create role hermes_identity_login login inherit nobypassrls password 'replace-local-only';
grant hermes_identity to hermes_identity_login;
```

The application and worker must start a transaction and set `app.tenant_id` and `app.principal_id` with `SET LOCAL` before accessing tenant tables. Do not connect ordinary requests as `postgres`, table owner, Supabase service role, or any role with `BYPASSRLS`.

Use the identity login only through a separate request-time connection pool. It may execute `hermes.lookup_principal(provider, external_subject)` using claims from a verified token. Before reading memberships, start a transaction and set `app.principal_id` locally to that resolved ID; the identity RLS policy must return only active memberships bound to that principal. A broad table grant without this RLS behavior is insufficient. The identity login has no direct access to the global principal table. Provisioning, suspending, closing, or relinking a principal requires a separate control-plane identity and audited workflow that are not supplied by this baseline.

Reset local data only when it is safe to destroy it:

```bash
docker compose -f infra/docker/compose.yaml down -v
```

## 6. Application dependency installation

The application repository should commit deterministic lock files.

### 6.1 Frontend

```bash
cd apps/web
npm ci
npm run lint
npm run typecheck
npm test
npm run build
```

Only values listed in `config/env/frontend.env.example` may be copied into a frontend environment. Every `VITE_*` value is public and embedded in browser code.

### 6.2 Python services

Use a locked, hash-verified dependency process selected by the repository. A requirements-based example is:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --require-hashes -r requirements.lock
python -m ruff check .
python -m mypy .
python -m pytest
```

Do not use ambiguous instructions such as `requirements.txt or similar`, `python main.py`, or `npm install --save-dev` without named dependencies.

## 7. Environment variable and secret classification

### 7.1 Frontend/public

Permitted examples:

- API origin;
- public identity-provider application ID;
- release version;
- non-secret feature flags;
- support URL.

Anything prefixed with `VITE_` is public. A build-time secret cannot be made safe by hiding it in the Vercel dashboard.

### 7.2 Backend/application secrets

Examples:

- database login URL;
- Redis/queue credential;
- identity verification key or secret reference;
- AI, market-data, FRED, RPC, monitoring, and webhook credentials.

Store these in a runtime secret manager or inject them through workload identity. Scope them by environment and service.

### 7.3 Trading authority

Examples:

- delegated signer authorization key;
- HSM/MPC/KMS credentials;
- CEX API secret.

These secrets belong only in the isolated signer or credential adapter. They must not be available to the web app, general API, analysis worker, database, model adapters, or support tooling.

### 7.4 Prohibited

Never place wallet private keys or seed phrases in Vercel, a Vite variable, repository, ordinary `.env` file, CI variable, Postgres row, application log, trace, or prompt. A generic environment variable is not a wallet vault.

### 7.5 Deployment-wide emergency stop

`HERMES_LIVE_TRADING_ENABLED=false` and `HERMES_SIGNER_LIVE_ENABLED=false` are boot-time fail-safe defaults, not a complete runtime incident control. A production deployment must provide a strongly authenticated deployment control that:

- is readable by execution workers and independently by the signer/CEX credential boundary;
- causes both layers to reject new live submissions when active, unavailable, expired, malformed, or unverifiable;
- is not mutable through tenant APIs;
- requires an authorized incident or security role to activate and step-up/dual approval to reset;
- has a bounded cache lifetime and a defined fail-closed behavior during control-store outage;
- emits immutable activation, observation, and reset evidence.

Tenant circuit breakers remain in Postgres and the tenant API. The deployment stop applies across the operated environment and is intentionally a separate trust boundary.

## 8. Identity deployment

For the managed Privy configuration:

1. Create separate Privy applications or equivalent environment separation for development, staging, and production.
2. Configure only approved login methods and origins.
3. Configure the backend verification mechanism and pin the expected app/audience/issuer values.
4. Verify tokens server-side and test wrong environment, wrong app, expired token, bad signature, missing subject, revoked/disabled membership, and clock-skew cases.
5. Map the provider subject to an internal principal; do not use email or wallet address as the primary authorization key.
6. Require step-up authentication for live enablement, delegation changes, CEX credential changes, risk-limit changes, privileged roles, and circuit-breaker reset.

A dedicated deployment may replace Privy with OIDC, but must preserve the same internal principal and tenant authorization contract.

## 9. Database and Supabase deployment

### 9.1 Project separation

Use separate Supabase projects or Postgres clusters for each environment. Dedicated tenants use a separate project/cluster. Configure network restrictions, TLS, connection pooling, backups, point-in-time recovery where required, and database monitoring.

### 9.2 Migrations

Apply migrations through a controlled migration identity in CI or an approved change window:

```bash
psql "$MIGRATION_DATABASE_URL" \
  -v ON_ERROR_STOP=1 \
  -f infra/supabase/migrations/0001_core.sql
```

Never run schema migrations from an application startup path in production.

Before applying:

- create a tested backup/restore point;
- review lock and rewrite behavior;
- test forward migration and rollback/roll-forward in staging;
- verify RLS and grants after migration;
- record migration commit and operator.

### 9.3 Application role

Create login roles outside the source migration using a secret generated by the platform. The role must be a member only of the required `hermes_*` NOLOGIN role, have `NOBYPASSRLS`, and not own tables.

Do not use a Supabase service-role or secret key for ordinary API/worker queries. Those credentials bypass RLS and are reserved for narrowly controlled administrative tasks.

### 9.4 Data API and realtime

Do not expose the private `hermes` schema through a browser-facing Data API. The UI uses the Hermes API. If a future readonly or realtime schema is added, it requires separate grants, RLS, token mapping, storage/realtime policy tests, and security approval.

## 10. Frontend deployment on Vercel

Vercel may host the static/SSR web application. It does not host live trading workers or wallet keys.

1. Configure the root directory as `apps/web`.
2. Use `npm ci` and `npm run build`.
3. Set only the approved public variables from `config/env/frontend.env.example`.
4. Use separate Vercel projects for staging and production.
5. Restrict production environment changes and deployments through protected roles.
6. Configure TLS, canonical domains, security headers, origin allowlists, and preview-environment isolation.
7. Disable optional analytics until the privacy notice and consent configuration are approved.
8. Scan the built assets for secret patterns and unapproved endpoints.

## 11. API and worker deployment

Deploy API and workers as separate containers or workloads.

### 11.1 API

- stateless request handling;
- autoscaling bounded by database and queue capacity;
- readiness excludes live-execution readiness so the API can report incidents while trading is paused;
- authenticated health details are separate from public liveness;
- strict timeouts, body limits, CORS allowlist, and rate/concurrency limits;
- no direct signer key or CEX secret access.

### 11.2 Workers

Use separate identities and queues for:

- ingestion/snapshot;
- analysis/consensus;
- risk/execution orchestration;
- CEX credential adapter;
- reconciliation;
- retention/audit archive.

The most privileged execution and credential workloads run with the narrowest egress and secret permissions. At-least-once queue delivery requires idempotent consumers.

### 11.3 Observability wiring

Every API and worker deployment must:

- expose Prometheus-format metrics on `/metrics` with authenticated network access controls;
- configure `HERMES_OTEL_EXPORTER_OTLP_ENDPOINT` to an OTLP/HTTP collector reachable from the workload;
- scrape `/metrics` from the platform collector or Prometheus-compatible scraper;
- label dashboards and alerts with the deployed `service.name`, environment, and release version;
- verify the boot-time deployment live-execution stop is visible through circuit-breaker metrics.

The local compose stack should mirror this with a collector and a Prometheus scrape target so telemetry wiring is tested before deployment.

### 11.4 Signer

The signer is a separate trust boundary. Prefer a customer signer, HSM, MPC, KMS, or wallet-provider policy. It must authenticate the orchestrator, validate the complete signing envelope, enforce independent policy, reject replay/expiry, and return no raw key material.

## 12. CEX onboarding

For each exchange account:

1. Use a dedicated subaccount where available.
2. Create an API credential with only required trading/read permissions.
3. Disable withdrawal, transfer, address management, and API-key management.
4. Apply IP allowlisting or equivalent restrictions where supported.
5. Store the secret only in the CEX credential adapter namespace.
6. Register venue precision, order types, time-in-force, client-order-ID, rate-limit, and reconciliation behavior.
7. Verify permissions automatically and manually.
8. Run sandbox/paper tests for partial fills, timeout lookup, cancel race, and reconciliation.
9. Record owner, rotation date, revocation runbook, and evidence.

## 13. DEX onboarding

For each chain and router/program:

1. Confirm chain ID, RPC quorum, token identity, decimals, and contract/program addresses.
2. Review and allowlist methods/instructions and decoded parameters.
3. Define quote age, route expiry, minimum received, price impact, slippage, fee/gas ceiling, nonce/sequence, allowance, finality, and reorganization rules.
4. Deploy a testnet or forked-environment signer policy.
5. Test wrong-chain, wrong-contract, replay, expired quote, fee spike, dropped/replaced transaction, reorg, and balance reconciliation.
6. Obtain security approval before mainnet enablement.

Brand names in documentation are examples, not production enablement.

## 14. CI/CD minimum pipeline

A protected production pipeline runs:

1. dependency lock verification;
2. secret scanning;
3. frontend lint/type/unit/E2E tests;
4. Python lint/format/type/unit/integration/property tests;
5. OpenAPI and JSON Schema validation;
6. migration lint and RLS/cross-tenant integration tests;
7. consensus, risk, idempotency, signer, and venue conformance tests;
8. container and dependency vulnerability scans;
9. SBOM and provenance generation;
10. staging deployment, smoke tests, and simulation replay;
11. manual production approval by an authorized role;
12. post-deployment health, migration, and circuit-breaker checks.

Production images are immutable and referenced by digest. Rollback uses the previous approved artifact; database changes use an approved backward-compatible roll-forward or tested rollback.

## 15. Production release gates

Live trading remains disabled until all items are evidenced:

- [ ] Architecture conformance checklist complete.
- [ ] Legal entity, jurisdiction, contact, subprocessor, and commercial placeholders resolved.
- [ ] Security review and threat model approved.
- [ ] Frontend bundle verified free of secrets.
- [ ] Token and role tests pass.
- [ ] The request-time identity role cannot enumerate or mutate principals; the separate provisioning path is authorized and audited.
- [ ] Forced RLS and cross-tenant tests pass for API, database, queue, stream, cache, export, and logs.
- [ ] Effective grants deny out-of-scope operations for API, worker, identity, auditor, migration, backup, and break-glass identities.
- [ ] Risk/consensus deterministic replay and property tests pass.
- [ ] Idempotency concurrency tests pass.
- [ ] Signer/delegation policy tests pass.
- [ ] CEX withdrawal-disabled or DEX allowlist evidence recorded.
- [ ] Venue sandbox/testnet conformance and reconciliation tests pass.
- [ ] Backup/restore meets approved RPO/RTO.
- [ ] Incident and five critical runbooks have been exercised.
- [ ] Monitoring and paging routes are verified.
- [ ] Audit-chain concurrency, root/fork/gap/self-link, digest, and independent-export tests pass.
- [ ] A limited notional, limited-venue live pilot is approved.

## 16. Deployment procedure

1. Freeze and identify the release commit and images.
2. Confirm the deployment-wide live-execution control is disabled and all relevant tenant circuit breakers are active.
3. Back up and test the release restore point.
4. Apply backward-compatible migrations.
5. Deploy API, workers, and signer integration with new execution still paused.
6. Deploy frontend.
7. Run health, identity, RLS, queue, snapshot, simulation, evidence, and reconciliation smoke tests.
8. Compare metrics and error rates with staging and previous release.
9. Enable only the approved tenant/strategy/venue scope after change approval.
10. Monitor enhanced alerts and reconcile the first executions.
11. Record release evidence and close the change.

## 17. Rollback and emergency change

Rollback is triggered by authorization failure, cross-tenant anomaly, signer-policy mismatch, duplicate/ambiguous execution, unreconciled balance, abnormal slippage/fees, data corruption, or material reliability regression.

1. Activate the narrowest affected tenant circuit breaker; invoke the deployment-wide emergency stop when scope is unknown or multiple tenants may be affected.
2. Stop new execution workers while keeping reconciliation and read APIs available.
3. Preserve evidence.
4. Reconcile pending venue state.
5. Roll back application images or apply the approved database roll-forward/rollback.
6. Rotate or revoke credentials if compromise is possible.
7. Validate security, simulation, and reconciliation before reset.

An emergency change still requires an incident record, reviewer as soon as feasible, and retrospective testing.

## 18. Post-deployment verification

Verify:

- liveness and readiness;
- identity token and tenant selection;
- cross-tenant negative query;
- queue enqueue/dequeue and duplicate delivery;
- snapshot freshness and source divergence;
- simulation consensus and risk replay;
- audit hash continuity;
- secret-read and signer-policy logs;
- circuit-breaker activation/reset permissions;
- CEX/DEX sandbox lookup and reconciliation;
- backup job and retention job status;
- dashboards and paging routes.

Record evidence with release commit, environment, time, operator, and result.
