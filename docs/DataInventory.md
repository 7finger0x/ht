# Hermes Data Inventory and Retention Standard

**Version:** 1.0.0-draft  
**Last revised:** 2026-07-20  
**Owner role:** Privacy and data governance owner  
**Applies to:** Managed production unless a dedicated-deployment contract specifies stricter controls

## 1. Purpose

This inventory is the common source for the Architecture, Privacy Policy, Security Policy, Operations Manual, and data-deletion procedures. A production deployment must replace assumptions with its actual data map and publish a current subprocessor register.

Retention periods below are baseline design values, not statements about an unverified existing implementation. Applicable law, litigation hold, accounting requirements, customer contract, or regulatory obligation may require a different period.

## 2. Data-minimization rules

- Store only data required to operate, secure, reconcile, support, or legally administer the service.
- Store secret references rather than secret values in Postgres.
- Do not store raw wallet keys or seed phrases in the browser, general API or worker estate, application database, logs, prompts, source, CI, or ordinary environment files. When the selected authority model requires service-held key material, it may exist only inside the dedicated signer, HSM, MPC service, wallet provider, or equivalent isolated authority boundary.
- Do not store raw AI-provider prompts and responses in managed production by default.
- Do not include authentication tokens, full headers, credentials, private keys, seed phrases, or user-provided secrets in logs.
- Prefer an internal principal ID over repeated storage of email, social profile, wallet address, or external provider attributes.
- Separate tenant business data from platform security and billing data.
- Apply deletion and retention by data class rather than an unrestricted “keep all logs” rule.

## 3. Canonical inventory

| Data class | Representative fields | Source | Purpose | System of record | Sensitivity | Baseline retention |
|---|---|---|---|---|---|---|
| Identity account | Internal principal ID, external provider subject, account status, creation time | Identity provider/API | Authentication and account administration | Postgres | Confidential | External subject/account attributes: account life + 30 days; pseudonymous internal reference: linked-evidence period |
| Contact/profile | Email or phone when supplied by identity provider, display name | Identity provider/user | Login, notices, support | Identity provider; Postgres only when separately justified and mapped | Personal | Account life + 30 days |
| Tenant membership | Tenant ID, principal ID, role, scopes, status | Tenant admin | Authorization | Postgres | Confidential | Membership life + 7 years in audit history |
| Session/security metadata | Session identifier hash, authentication time, IP-derived security signals, user agent, request ID | Browser, edge, API | Fraud prevention, abuse response, incident investigation | Security log system | Personal/confidential | 180 days; up to 1 year after an incident |
| Strategy configuration | Instrument scope, schedule, model selection, limits, simulation/live flag | User/operator | Execute configured workflow | Postgres | Confidential/proprietary | Until deletion + 30 days; policy history 7 years |
| Risk policy | Limits, approvals, circuit breakers, version, approvers | Tenant admin | Deterministic authorization | Versioned configuration and strategy records; dedicated policy store when implemented | Confidential | Active life + 7 years |
| Venue registry | Venue IDs, networks, adapters, contract allowlists, secret references | Tenant admin/operator | Route and constrain execution | Postgres/configuration repository | Confidential | Active life + 7 years |
| Wallet metadata | Public address, network, wallet-provider ID, custody/authority mode, policy ID | User/provider | Signing and reconciliation | Signer/wallet provider and deployment-specific metadata store; not modeled in the core SQL baseline | Public or confidential by context | Account life + 7 years for executed activity |
| CEX account metadata | Exchange, subaccount reference, permission status, credential reference, last rotation | User/operator | Place and reconcile orders | Venue configuration and secret manager; dedicated account metadata is not modeled in the core SQL baseline | Restricted | Account life + 90 days; audit history 7 years |
| Wallet/CEX secret material | Private signing key, authorization key, API secret | Customer, signer, exchange | Authorize transaction or order | Dedicated secret manager, HSM, MPC, or wallet provider | Restricted/critical | Only while active; destroy after revocation and required backup expiry |
| Market snapshot | Price, quote, order book/liquidity, source, timestamp, sequence, quality, hash | Data/RPC/venue providers | Reproducible analysis and risk | Postgres/object store | Generally non-personal | 90 days online; decision-referenced snapshots 7 years |
| Macro/news features | Normalized public indicators, headline identifiers, sentiment features | Data/AI providers | Optional analytical input | Postgres/object store | May include third-party content | 90 days; decision evidence 7 years where licensing permits |
| Agent assessment | Action, confidence, rationale summary, model/provider, prompt version, input/output hash, latency | Analytical agent | Consensus evidence | Postgres | Confidential/proprietary | 1 year online; decision evidence 7 years |
| Raw model payload | Full prompt/provider response | Analytical adapter | Debug only | Disabled by default; isolated encrypted debug store when approved | Restricted | Maximum 7 days, explicit incident/change approval |
| Consensus decision | Eligible agents, weights, support, quorum, result, policy version, digest | Consensus engine | Decision record | Postgres | Confidential | 7 years |
| Portfolio/risk snapshot | Balances, positions, NAV, P&L, exposure, open orders, source times | Venue/reconciler | Pre-trade risk and reporting | `risk_evaluations.portfolio_snapshot` and referenced evidence; no separate core table | Financial/confidential | 7 years |
| Risk evaluation | Rule results, computed limits, approved quantity, reason, policy version, digest | Risk engine | Execution authorization | Postgres | Financial/confidential | 7 years |
| Approval record | Approver ID, decision, timestamp, authentication context, comment | Human approver | Dual control | Postgres/audit store | Confidential | 7 years |
| Order intent | Instrument, side, type, quantity, limit/stop price, venue, client-order ID, digest, expiry | API/orchestrator | Controlled execution | Postgres; execution state and request idempotency are stored separately | Financial/confidential | 7 years |
| Venue order and fill | Client/venue order ID, transaction hash, status, fills, price, fees, timestamps | Venue/blockchain | Reconciliation and reporting | Postgres | Financial; blockchain fields public | 7 years or contract/legal requirement |
| Audit event | Actor, action, resource, result, hashes, previous hash, policy/code versions | All trusted services | Tamper evidence, security, disputes | Append-only Postgres and independent archive | Confidential | 7 years |
| Operational telemetry | Latency, counters, health, error class, correlation ID | Services | Reliability and capacity | Metrics/log platform | Internal | Metrics 13 months; detailed logs 30 days |
| Support record | Contact details, ticket content, diagnostic attachments | User/support | Resolve request | Support system | Personal/confidential | Closure + 2 years; delete secrets immediately |
| Billing/legal record | Entity, invoice, plan, acceptance record, tax fields | Customer/payment provider | Contract and accounting | Billing/legal systems | Personal/confidential | Applicable legal/accounting period |
| Public blockchain data | Wallet address, transaction, token amount, contract interaction | Blockchain | DEX settlement and verification | Public blockchain; indexed copy in Postgres | Public but linkable | Indefinite on chain; local copy per trading retention |

### 3.1 Baseline implementation boundary

The delivered core SQL models principals, tenants, memberships, strategies, portfolios, venues, market snapshots, agent assessments, consensus decisions, risk evaluations, executions, order intents, approvals, venue orders, fills, circuit breakers, idempotency records, and audit events.

It does **not** model dedicated wallet or CEX-account records, contact attributes beyond an optional display name, raw-payload debug storage, security-log indexes, support or billing systems, object/archive storage, provider-side copies, retention jobs, deletion tombstones, or legal holds. Those are deployment requirements, not implemented capabilities of the documentation package. Managed production conformance requires an approved data map that assigns every inventory row to an exact table, field, bucket, log index, secret path, provider system, and backup set.

Each mapped data class must have a versioned retention rule containing its trigger, active-store action, archive action, backup-expiry behavior, legal-hold override, responsible owner, and verification evidence. A narrative period in this table is not evidence that deletion or retention is enforced.

## 4. Data flows and recipients

### 4.1 Identity provider

The browser and backend exchange authentication data with the configured identity provider. Hermes receives the minimum claims needed to identify the principal and verify the session. The exact provider, claims, and retention belong in the subprocessor register and deployment record.

### 4.2 Infrastructure providers

Managed deployments process application and operational data through hosting, database, queue, storage, monitoring, email/notification, and support providers. Production must maintain a provider inventory containing service, purpose, region, data categories, contract owner, security review date, and deletion mechanism.

### 4.3 AI and data providers

Only a minimized market context is sent to configured analytical providers. It must exclude user identity, access tokens, wallet keys, exchange credentials, support records, and unrelated tenant data. Provider prompts are treated as potentially retained by the provider unless the applicable contract and configuration state otherwise.

News headlines are not necessarily anonymous. They may contain names or other personal information from public reporting. The Privacy Policy therefore describes the content accurately rather than labeling all requests “anonymized.”

### 4.4 Execution venues and blockchain networks

A DEX transaction exposes the sender address, recipient/contracts, token amounts, fees, calldata/instructions, and transaction timing to the public network and infrastructure providers. This information is generally permanent and may be linked to an individual or organization through other data.

A CEX receives credentials, account identifiers, order instructions, network information, and any identity or compliance data already held for the account. CEX order and fill records are generally not written to a public blockchain.

## 5. IP addresses and device data

Managed services necessarily process network addresses to establish connections, deliver content, prevent abuse, rate-limit, and investigate incidents. The baseline design:

- avoids storing full IP addresses in application business tables;
- permits edge, security, and infrastructure providers to process them;
- stores a truncated address, keyed hash, or provider-generated risk signal when sufficient;
- limits routine security-log retention to 180 days;
- restricts access to security and operations roles;
- discloses analytics or cookies actually enabled by the deployment.

The service MUST NOT claim that it does not process IP addresses when using network hosting, rate limiting, or security logging.

## 6. Logging and model-evidence policy

Permitted model evidence:

- canonical snapshot ID and digest;
- agent provider and model identifier;
- prompt-template version and system configuration version;
- structured action, confidence, quality, and expiry;
- redacted rationale summary;
- token usage, latency, and validation result;
- raw-input and raw-output digests.

Raw prompts or responses may be captured only for a time-bounded debugging session approved by security and privacy owners. The capture destination must be isolated, encrypted, access-logged, and automatically deleted within seven days. Secret scanning runs before persistence.

## 7. Deletion and account closure

For managed deployments:

1. Disable new live execution and revoke delegated authority.
2. Cancel open orders where supported and reconcile all accounts.
3. Revoke or delete CEX credentials and secret references.
4. Export records requested or contractually required.
5. After the approved recovery period, remove or de-identify non-retained profile/contact attributes, disable active strategies, and delete only unreferenced configuration that an approved retention policy permits.
6. Preserve the internal principal and tenant references required by retained order, fill, risk, approval, security, and audit records; mark them closed and restrict access. Do not break evidence foreign keys or rewrite immutable records to simulate erasure.
7. Delete or de-identify support and telemetry data according to their schedules.
8. Record the request, scope, actions, exceptions, verification result, and completion time in a deletion tombstone and the audit ledger.

Data on public blockchains, in a customer-controlled self-hosted system, in exchange records, or legally retained cannot be deleted by the Hermes operator.

The core SQL baseline intentionally withholds DELETE from application roles and uses restrictive foreign keys and immutable-record triggers. A production retention service therefore requires a separate, narrowly authorized maintenance identity and reviewed procedures. That identity MUST NOT update or delete immutable execution evidence and must fail closed when a record is referenced by an active legal hold or retained evidence.

## 8. Backup and deletion interaction

Deletion propagates to active systems first. Encrypted backups expire on their normal rotation schedule and are not restored except for disaster recovery. When a backup is restored, deletion tombstones and retention jobs must be replayed before ordinary processing resumes.

Database backups do not necessarily include object-storage payloads. The backup plan must explicitly cover each data store and validate restoration.

The core SQL baseline does not implement deletion tombstones, retention schedules, or legal-hold records. These controls and restore-time replay tests are release gates for managed production, not capabilities established by this package.

## 9. Legal holds and preservation

A documented legal-hold process may suspend deletion for specifically identified records. Holds require an authorized requester, scope, reason, start date, review date, and release approval. A hold does not justify indefinite retention of unrelated data.

## 10. Review checklist

A release review must confirm:

- [ ] actual fields and systems match this inventory;
- [ ] every inventory row maps to an exact store, provider copy, backup set, and versioned retention rule;
- [ ] provider/subprocessor register is current;
- [ ] retention jobs exist and are tested;
- [ ] deletion tombstones and legal holds are implemented, access-controlled, and replayed in restore tests;
- [ ] the retention identity cannot mutate immutable evidence or bypass a hold;
- [ ] raw model payload logging is disabled by default;
- [ ] logs and traces redact prohibited values;
- [ ] secret values are absent from the application database and its backups; signer/secret-manager backups follow the separately approved key-destruction policy;
- [ ] account deletion, credential revocation, and blockchain limitations are accurately disclosed;
- [ ] dedicated and self-hosted responsibility allocations are documented by contract.
