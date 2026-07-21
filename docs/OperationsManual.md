# Hermes Operations Manual

**Version:** 1.0.0-draft  
**Last revised:** 2026-07-20  
**Owner role:** Operations owner  
**Status:** Design baseline; targets require validation in each deployment

## 1. Operating objective

Operations must preserve three priorities, in order:

1. prevent unauthorized or uncontrolled economic action;
2. establish and reconcile authoritative trading state;
3. restore normal service without weakening controls.

Availability is subordinate to execution safety. During uncertainty, Hermes may continue serving read-only status while new live execution remains paused.

## 2. Service inventory

A production deployment maintains an inventory with owner, environment, region, version, dependency, secret role, recovery tier, and dashboard/runbook link for:

- web application and edge/CDN;
- control API and identity verifier;
- scheduler and queues;
- ingestion and snapshot workers;
- analytical model adapters;
- consensus and risk workers;
- execution orchestrator;
- wallet signer or customer signer integration;
- CEX credential adapters;
- DEX RPC/relayer/venue adapters;
- reconciler;
- Postgres/Supabase, object storage, and audit archive;
- monitoring, paging, support, and notification services.

Unknown ownership is a production blocker.

## 3. Design objectives and recovery tiers

These are baseline objectives, not contractual guarantees. A deployment must measure and approve its own values.

| Capability | Baseline objective | Safety note |
|---|---|---|
| Read/control API | 99.9% monthly availability | Public liveness may remain up while execution is paused |
| Decision evaluation | 99.5% monthly availability | Provider outage produces abstention, not reduced quorum |
| Execution submission | No availability guarantee during unsafe state | Fail closed |
| Reconciliation detection | 99% of expected venue events observed within 60 seconds | REST polling backs up websocket/webhook streams |
| Critical alert delivery | 95% within 2 minutes | Test paging monthly |
| Database RPO | 15 minutes target | Requires configured PITR or equivalent |
| Database RTO | 4 hours target | Restore exercise required quarterly |
| Audit archive RPO | 5 minutes target | Append-only and independent retention preferred |
| Queue recovery | 15 minutes target | At-least-once delivery; idempotent consumers |

An institutional contract may require stricter targets and independent resilience testing.

## 4. Operational states

Hermes exposes independent states rather than one generic “healthy” flag:

- `CONTROL_PLANE`: `READY`, `DEGRADED`, `UNAVAILABLE`;
- `DATA_QUALITY`: `CURRENT`, `DEGRADED`, `STALE`, `DIVERGENT`;
- `ANALYSIS`: `READY`, `QUORUM_AT_RISK`, `UNAVAILABLE`;
- `RISK_ENGINE`: `READY`, `POLICY_ERROR`, `UNAVAILABLE`;
- `SIGNER`: `READY`, `DEGRADED`, `PAUSED`, `UNAVAILABLE`;
- `VENUE`: per-venue `READY`, `DEGRADED`, `PAUSED`, `UNAVAILABLE`;
- `RECONCILIATION`: `CURRENT`, `LAGGING`, `FAILED`;
- `LIVE_EXECUTION`: `DISABLED`, `LIMITED`, `ENABLED`, `PAUSED`.

No service automatically changes `LIVE_EXECUTION` from `DISABLED` or `PAUSED` to `ENABLED` without the configured approval path.

## 5. Monitoring and telemetry

### 5.1 Identity and authorization

Monitor:

- token verification failures by reason;
- wrong issuer/audience/application attempts;
- tenant-selector denials;
- role/scope denials;
- privileged membership and support-access changes;
- RLS denials and missing transaction context;
- step-up authentication failures.

A cross-tenant success, application query using a bypass role, or unexpected service-role key use is SEV-1.

### 5.2 Market data and snapshots

Monitor by source, instrument, and venue:

- fetch/websocket latency;
- last event and snapshot age;
- sequence gaps;
- source divergence;
- null or invalid fields;
- symbol/token/decimal mismatches;
- block height and RPC disagreement;
- snapshot creation rate and failure count.

“Consensus health” is not a single alert threshold. Alert separately on eligible-agent count, quorum weight, abstention, provider errors, assessment latency, and schema failures.

### 5.3 Analysis and consensus

Monitor:

- agent request count, latency, timeout, and error class;
- schema-validation failure and `ABSTAIN` rate;
- provider/model/prompt version distribution;
- input/output size and token usage;
- eligible and excluded weights;
- support, weighted confidence, opposition, and abstention distributions;
- deterministic replay mismatch;
- drift and offline evaluation metrics.

A provider outage must not automatically lower quorum or increase another weight.

### 5.4 Risk and circuit breakers

Monitor:

- rule PASS/FAIL/UNKNOWN by rule ID;
- stale portfolio/quote rejection;
- approved versus requested quantity;
- exposure, leverage, loss, drawdown, liquidity, slippage, impact, and fee headroom;
- active circuit breakers and duration;
- failed or unauthorized reset attempts;
- risk-policy version and configuration-digest changes;
- deterministic replay mismatch.

An `UNKNOWN` mandatory rule that permits an order is SEV-1.

### 5.5 Signer and credentials

Monitor:

- signing requests, approvals, refusals, latency, and expiry;
- policy mismatches by field;
- replay detection;
- authorization-key use and secret reads;
- active wallet delegations and approaching expiry;
- CEX credential permission verification, rotation age, and failed authentication;
- unexpected withdrawal/transfer permission;
- signer/credential adapter egress destinations.

Never log raw signatures when unnecessary, private keys, authorization keys, or CEX secrets.

### 5.6 Orders and reconciliation

Monitor:

- order intents, submission attempts, acknowledgements, and venue IDs;
- ambiguous submissions and lookup duration;
- duplicate client-order-ID conflicts;
- partial-fill duration and cancel races;
- DEX pending, replaced, dropped, confirmed, finalized, and reorged transactions;
- expected versus actual quantity, price, fee, and balance change;
- websocket/webhook lag versus REST reconciliation;
- unreconciled count, value, age, and affected scope.

Any unreconciled economic difference above the deployment threshold activates a scoped breaker.

### 5.7 Infrastructure

Monitor:

- API latency/error/saturation;
- queue depth, oldest-job age, retries, dead letters, and duplicate delivery;
- database connection use, transaction age, locks, replication/PITR lag, storage, and slow queries;
- cache memory/eviction and persistence;
- container restarts, CPU, memory, disk, and network;
- time synchronization;
- backup, archive, retention, and audit-chain verification jobs;
- certificate and credential expiry.

## 6. Alert matrix

| Condition | Initial severity | Automated action | Operator action |
|---|---|---|---|
| Cross-tenant access or bypass-role use | SEV-1 | Deployment-wide emergency stop; block affected identity/service | Invoke security incident runbook |
| Unauthorized signer/CEX action | SEV-1 | Pause signer/credential adapter; revoke if possible | Reconcile and preserve evidence |
| Ambiguous order/transaction submission | SEV-2, SEV-1 if material | Pause account/instrument scope | Run duplicate/ambiguous order procedure |
| Reconciliation mismatch | SEV-2 | Pause affected scope | Compare venue, chain, and balances |
| Market data stale/divergent | SEV-2 if live scope | Prevent new decisions/execution | Run stale-data procedure |
| Risk engine unavailable or `UNKNOWN` rule | SEV-2 | Reject new execution | Restore without bypass |
| Signer unavailable | SEV-2 if live orders pending | Stop new submission | Determine signed/submitted state |
| CEX/DEX venue outage | SEV-2 | Pause venue | Reconcile, do not reroute silently |
| Database unavailable | SEV-2 | Stop state-changing requests | Restore; verify tenant context and state |
| Backup or audit archive failure | SEV-3; escalate by duration | Alert and preserve primary data | Repair and perform catch-up copy |
| AI provider outage | SEV-3 | Agent abstains; maintain quorum requirements | Restore provider or keep decisions blocked |

Severity may increase with notional, duration, data sensitivity, tenant count, or evidence of exploitation.

## 7. Logging standard

Use structured logs containing:

- timestamp, service, environment, region, version, source commit;
- tenant ID where permitted, principal/service actor ID, correlation and causation IDs;
- action, result, error category/code, duration;
- resource identifiers and safe evidence digests.

Do not log secrets, full tokens/cookies/headers, private keys, seed phrases, CEX secrets, database passwords, or routine raw model payloads. Rationale text and provider content require redaction and length limits.

Detailed application logs are retained 30 days by baseline. Metrics are retained up to 13 months. Audit and trading evidence follow the seven-year baseline in [Data Inventory](DataInventory.md).

## 8. Routine operating procedures

### Daily

- review active breakers, unresolved incidents, ambiguous submissions, and reconciliation failures;
- verify venue and signer health;
- verify last successful database backup, audit archive, and retention job;
- review high-severity security, credential, RLS, and risk alerts;
- verify clock synchronization;
- reconcile a sampled set of orders, fills, fees, and balances.

### Weekly

- review queue retry/dead-letter trends and oldest jobs;
- review model/provider schema failures and abstention;
- review CEX permissions and signer policy changes;
- review privileged access and support sessions;
- test one non-disruptive circuit breaker in staging;
- review dependency and image findings.

### Monthly

- test paging and incident contacts;
- restore a representative backup in an isolated environment;
- verify audit hash chain and archive retrieval;
- review retention/deletion evidence;
- review capacity under volatility assumptions;
- review venue allowlists, token identities, decimals, and account ownership;
- review outstanding security exceptions and remediation SLAs.

### Quarterly

- full disaster-recovery exercise;
- incident game day covering an ambiguous order or credential compromise;
- RLS and cross-tenant penetration test or equivalent review;
- signer/delegation and CEX permission review;
- model/consensus/risk performance and calibration review;
- privacy/data-inventory/subprocessor review;
- architecture and documentation conformance review.

## 9. Reconciliation procedure

Reconciliation is continuous and mandatory after restart, deployment, timeout, provider disconnect, or breaker activation.

For each execution:

1. Read internal intent and last known state.
2. Query authoritative venue state by stable client order ID, venue order ID, transaction hash, wallet/account, and time window.
3. Collect fills, fees, receipts, confirmations/finality, cancellations, and replacements.
4. Compare expected and actual balance/position changes, including gas and venue fees.
5. Deduplicate fills first by stable `venue_fill_id` and venue order; use economic attributes only as secondary anomaly evidence.
6. Update mutable execution/order state using expected previous state.
7. Insert immutable fill and audit records.
8. Mark `RECONCILED` only when all required quantities and balances agree within documented precision.
9. Otherwise mark `RECONCILIATION_FAILED`, maintain the scoped breaker, and escalate.

Never resolve a mismatch by deleting evidence or manually forcing `RECONCILED` without a documented correction event and approval.

## 10. Backup and restore

### 10.1 Backup scope

Back up separately:

- database roles and grants;
- schema/migrations;
- database data;
- object-storage evidence and model diagnostics where enabled;
- policy and venue configuration;
- audit archive and hash roots;
- identity, signer, and secret-manager configuration metadata, excluding export of non-exportable key material;
- infrastructure definitions.

A database backup is not assumed to include object-storage files.

### 10.2 Baseline schedule

- managed database backup or PITR consistent with 15-minute target RPO;
- daily independent logical export of critical configuration and evidence metadata;
- audit archive replication at least every five minutes where supported;
- monthly retained recovery point according to contract and legal policy;
- quarterly isolated restore test.

Actual schedule depends on the provider plan and contract.

### 10.3 Restore verification

After restore:

- confirm schema and migration version;
- verify roles, grants, RLS enabled/forced, and application NOBYPASSRLS role;
- verify tenant row counts and cross-tenant denial;
- verify audit-chain continuity and archive availability;
- replay deletion tombstones and retention tasks;
- reconcile all venue accounts from a safe timestamp;
- keep live execution disabled until state is reconciled and approved.

See `runbooks/backup-restore.md`.

## 11. Change management

Every production change records:

- owner, reviewer, ticket, purpose, risk, affected tenants/venues;
- source commit, image digests, configuration/policy versions;
- test evidence, security/privacy impact, migration plan;
- release steps, monitoring, rollback trigger and procedure;
- post-change result.

### 11.1 Model, prompt, and agent changes

A provider/model/prompt/weight change is a trading-logic change, not routine tuning. It requires:

1. versioned candidate configuration;
2. fixed historical replay and out-of-sample evaluation;
3. schema, timeout, prompt-injection, and failure-mode tests;
4. consensus and risk regression comparison;
5. simulation/canary deployment;
6. approval and rollback criteria;
7. no online self-modification of production weights.

See `runbooks/model-change.md`.

### 11.2 Risk-policy changes

Increasing any limit, enabling live mode, changing mandatory agents, reducing quorum, adding a venue, or expanding signer authority is high risk and requires dual approval and staging evidence. Emergency risk reductions may be applied immediately but still require an audit record and retrospective review.

## 12. Incident command

A SEV-1/SEV-2 incident assigns:

- incident commander;
- operations lead;
- security lead;
- trading/reconciliation lead;
- communications/legal/privacy lead as appropriate;
- scribe/timeline owner.

The incident channel and record are access-controlled. Use UTC timestamps. Preserve evidence. Do not paste secrets into chat. External communications state confirmed facts, scope, actions, and uncertainty; they do not claim all venue activity is stopped until reconciled.

## 13. Capacity and scaling

Scale by workload class, not one undifferentiated worker pool:

- API replicas for control traffic;
- partitioned queues by analysis, execution, and reconciliation;
- per-tenant and per-venue concurrency limits;
- dedicated credential/signer workers;
- database indexes and partition/retention strategy for high-volume audit and telemetry;
- bounded model-provider concurrency and budgets;
- backpressure that stops new decisions before critical reconciliation work is starved.

Execution and reconciliation receive priority over new analysis during volatility. Edge functions are not used for long-running reasoning, credential handling, or trade lifecycle management.

## 14. Runbooks and exercise evidence

Operational procedures are in [`runbooks/`](../runbooks/README.md). Each runbook contains trigger, immediate containment, diagnosis, recovery, verification, rollback, evidence, and escalation sections.

The package validator checks runbook structure and command syntax where safe. Production operators must also exercise runbooks against staging or sandbox systems and record:

- date, participants, scenario, environment;
- steps completed and deviations;
- measured detection/recovery times;
- evidence collected;
- control gaps, owner, and due date.

Static validation is not an operational exercise.

## 15. Required operational records

Retain:

- release and change records;
- incident timelines and post-incident reviews;
- breaker activation/reset evidence;
- backup and restore reports;
- access and role reviews;
- credential/delegation reviews;
- runbook exercise reports;
- security exception register;
- model/consensus/risk evaluation reports;
- venue onboarding and conformance results;
- privacy/data-retention review evidence.
