# Hermes Security Policy and Control Standard

**Version:** 1.0.0-draft  
**Last revised:** 2026-07-20  
**Owner role:** Security owner  
**Review cadence:** Quarterly, after a material incident, and before any custody or live-execution change

## 1. Scope and posture

This policy defines the baseline security controls for managed, dedicated, and self-hosted Hermes deployments. It covers identity, tenant isolation, secrets, signing, exchange credentials, execution safety, software supply chain, monitoring, incident response, backup, and recovery.

Hermes is experimental trading software. Compliance with this document reduces risk but does not establish that the service is secure, compliant, audited, or suitable for a particular institution. Those claims require implementation evidence and, where represented, independent assurance.

## 2. Security principles

- **Deny by default:** no access, execution, or secret use without explicit authorization.
- **Separate duties:** analysis, risk authorization, approval, signing, venue submission, and reconciliation are distinct functions.
- **Least privilege and least authority:** identities, services, wallets, and exchange credentials receive only required permissions.
- **Tenant identity from trusted context:** client-supplied ownership fields are ignored for authorization.
- **No raw secrets in application data paths:** keys remain in a signer or secret manager.
- **Defense in depth:** API authorization and forced database RLS both apply.
- **Immutable evidence:** security and execution events are append-only to ordinary application roles and independently retained.
- **Fail closed:** missing, stale, ambiguous, or compromised state pauses affected execution.
- **Production isolation:** production identities, data, secrets, wallets, accounts, and telemetry are separated from non-production.

## 3. Security responsibility by deployment mode

| Control area | Managed multi-tenant | Dedicated single-tenant | Self-hosted |
|---|---|---|---|
| Application and infrastructure | Hermes operator | Allocated by contract | Customer/operator |
| Identity configuration | Hermes operator | Hermes or customer | Customer/operator |
| Tenant authorization and RLS | Hermes operator | Stack operator | Customer/operator |
| Signer/key management | As selected: provider policy, customer signer, or managed signer | Customer signer preferred; contract governs | Customer/operator |
| CEX credential storage | Hermes managed secret store | Dedicated/customer store | Customer/operator |
| Backups and recovery | Hermes operator | Contract-defined | Customer/operator |
| Monitoring and incident response | Hermes operator | Shared or customer-led by contract | Customer/operator |
| Privacy/legal notices | Hermes operator for Hosted Services | Contract-defined | Customer/operator |

A responsibility matrix must be completed during onboarding. Unassigned controls block production release.

## 4. Threat model

Hermes treats the following as material threats:

- account takeover, token theft, session replay, and privilege escalation;
- cross-tenant access through API, database, cache, queue, realtime stream, logs, exports, or support tooling;
- exposure or misuse of wallet keys, delegated signer authority, authorization keys, or CEX credentials;
- malicious or compromised application, worker, dependency, model provider, data source, RPC, venue, or operator;
- prompt injection, malformed model output, data exfiltration, and correlated model error;
- stale/manipulated market data, symbol or decimal confusion, and wrong-chain or wrong-contract execution;
- duplicate orders, ambiguous timeouts, partial fills, chain reorganizations, nonce conflict, and failed reconciliation;
- supply-chain compromise, vulnerable dependencies, CI secret exposure, and unauthorized release;
- denial of service during volatile markets;
- insufficient backups, unrecoverable storage, and untested restore procedures;
- inaccurate privacy, custody, compliance, or audit claims.

The [Architecture](Architecture.md#8-trust-boundaries-and-threats) documents trust boundaries, and the [Execution Protocol](ExecutionProtocol.md) defines fail-closed behavior.

## 5. Identity and session security

### 5.1 Token verification

The managed service uses Privy access tokens by default. Dedicated and self-hosted systems may use an approved OIDC provider. The backend, not the browser, is the security boundary.

For every request, the API MUST:

- accept tokens only over TLS;
- permit only the configured signature algorithm;
- verify the signature with a pinned or securely refreshed provider key set;
- verify issuer and intended audience or application identifier;
- verify expiration and not-before claims with a bounded clock-skew allowance;
- verify the token type and required subject/session claims;
- reject tokens for another environment or application;
- map the external subject to an internal immutable principal;
- check account, session, tenant membership, role, and scope status;
- apply step-up authentication for sensitive actions where configured;
- avoid logging the token or full authorization header.

Key-set refresh must fail safely. An unknown key ID triggers one bounded refresh; it does not disable signature verification.

### 5.2 Browser session handling

Bearer access tokens should be kept in memory where practical and sent only to the configured API origin. If cookies are used, they must be `Secure`, `HttpOnly`, appropriately `SameSite`, narrowly scoped, and protected against CSRF. The application must define content-security policy, frame restrictions, referrer policy, and an approved cross-origin policy.

No secret or privileged database key may be delivered to the browser. Public Vite variables are treated as public source code.

### 5.3 Roles and privileged access

Roles are defined in [Architecture](Architecture.md#62-authorization-roles). Privileged platform and tenant actions use least privilege, explicit scopes, and audit logging. High-risk actions require step-up authentication and, where configured, dual approval:

- enabling live trading;
- creating or expanding wallet delegation;
- adding or rotating CEX credentials;
- changing risk limits or circuit breakers;
- granting tenant-admin, approver, security-admin, or platform-admin role;
- accessing a tenant for support;
- exporting sensitive evidence;
- changing retention or diagnostic logging;
- break-glass database or signer access.

Platform support access is just-in-time, time-limited, approved, and recorded. Routine platform roles do not have wallet or exchange transaction authority.

## 6. Tenant isolation and database security

### 6.1 Access path

The browser does not directly access internal trading tables. It uses the Hermes API and authorized event stream. PostgREST, anonymous keys, and ordinary authenticated Supabase roles are not part of the trading-data path unless a separately reviewed tenant-scoped API schema is implemented.

### 6.2 Application database role

The production application connects with a dedicated role that:

- does not own schemas or tables;
- does not have `SUPERUSER` or `BYPASSRLS`;
- cannot assume migration, service-role, or platform-admin roles;
- has only explicit CRUD grants required by its service;
- is separate from migration, backup, analytics, and support roles.

The Supabase service-role or secret key bypasses RLS and MUST NOT be used by ordinary API or worker requests. It MUST NOT be present in the frontend.

The grants in the canonical migration are a tenant-isolation baseline, not evidence of service-level least privilege. Each production service identity must have a reviewed effective-grant matrix, must be unable to inherit or assume a broader role, and must be tested for denied operations. Split worker identities by responsibility where snapshot, analysis, risk, execution, and reconciliation duties can be isolated.

### 6.3 Transaction-local context

After authorization and before querying tenant data, the API starts a database transaction and sets:

```sql
SET LOCAL app.tenant_id = '<authorized-tenant-uuid>';
SET LOCAL app.principal_id = '<authorized-principal-uuid>';
```

The values come from the server authorization context. Connection-pool release ends the transaction and clears the settings. Queries outside a transaction are prohibited in the data-access layer.

### 6.4 Forced RLS

Every tenant-owned table has RLS enabled and forced. Policies include both `USING` and `WITH CHECK` where writes are allowed. Normalized workflow relationships use composite `(tenant_id, id)` foreign keys, and principal-attribution columns bind the principal to a membership in the same tenant. Application roles cannot update a row’s tenant identifier or delete/update audit records.

Identifiers embedded in arrays or JSON are not protected by relational foreign keys. Tables containing authorization- or execution-relevant denormalized references must deny direct application inserts and updates and route writes through a database-enforced function or trigger that validates tenant, resource type, and immutable parent relationship. Every permitted writer requires negative integration tests. Until that enforcement exists for every such field, the canonical migration is only a tenant-isolation baseline and production release remains blocked. RLS and a trusted application write path alone do not establish relationship integrity.

Tests MUST cover:

- select, insert, update, and delete for owner and non-owner tenants;
- attempts to change `tenant_id` or reference another tenant’s resource;
- absent or malformed transaction context;
- connection-pool context leakage;
- API, job queue, cache, event stream, export, storage, and logs;
- privileged maintenance paths and break-glass access.

The canonical migration is `infra/supabase/migrations/0001_core.sql`.

### 6.5 Identity lookup boundary

The request-time identity connection uses a credential and pool separate from the tenant API connection. After token verification, it may execute only the exact-match `hermes.lookup_principal(provider, external_subject)` resolver and then read that principal’s active memberships under transaction-local context. The resolver is `SECURITY DEFINER` with a fixed trusted `search_path`; public execution is revoked. The request-time identity role has no direct `SELECT`, `INSERT`, `UPDATE`, or `DELETE` privilege on the global `principals` table, owns no application object, and has no membership in or inheritance path to a broader role.

The provider and subject passed to the resolver come only from the verified token profile, never from a request body or tenant selector. Principal creation, display-name changes, suspension, closure, and relinking are control-plane operations using a separate identity, authorization policy, and audit trail; just-in-time provisioning is not granted to the request-time resolver by this baseline.

## 7. Secrets and key management

### 7.1 Secret classes

| Class | Examples | Approved storage | Browser exposure |
|---|---|---|---|
| Public configuration | API origin, Privy app ID, release version | Frontend environment/build config | Allowed |
| Application secret | Database password, provider API key, webhook secret | Managed secret manager or workload identity | Prohibited |
| Trading credential | CEX API secret, delegated signer authorization key | Isolated secret manager or signer boundary | Prohibited |
| Wallet key material | Private key, seed phrase, HSM/MPC share | Wallet provider, HSM, MPC, or customer signer | Prohibited |
| Recovery/break-glass | Backup decryption key, emergency credential | Separate controlled vault with dual access | Prohibited |

### 7.2 Requirements

- Secrets are not committed, embedded in images, copied into tickets, or exposed in CI logs.
- Production uses workload identity or runtime secret injection; plaintext files are not a production secret store.
- Secret references in Postgres are opaque and non-sensitive without secret-manager access.
- Access is service-specific, environment-specific, and tenant-specific where appropriate.
- Rotation occurs on compromise, personnel/role change, provider recommendation, and a documented schedule based on secret capability. A fixed 90-day rule is not a substitute for automated or event-driven rotation.
- Secret reads, policy changes, and rotations are logged without recording secret values.
- Secret scanning runs pre-commit and in CI; release artifacts and frontend bundles are scanned.
- Backups containing encrypted secret-store state follow a separate key and destruction policy.

## 8. Wallet and signer security

### 8.1 User-in-loop wallets

The UI displays decoded transaction details. Authorization is bound to the exact digest and expires. The backend cannot substitute chain, contract/program, recipient, asset, quantity, minimum received, fee policy, or calldata after approval.

### 8.2 Delegated wallets

Delegation is explicit, scoped, revocable, and visible. The policy should constrain:

- wallet and network;
- permitted contracts/programs and recipients;
- methods, instructions, or calldata parameters;
- assets and quantities;
- per-transaction, period, and aggregate limits;
- time window and expiration;
- signer identity and anti-replay requirements;
- whether the server can update owners, signers, policies, or export capability.

The most restrictive practical ownership model is preferred. The product and legal terms must accurately disclose any server ability to update policy or cause transactions.

### 8.3 Customer-managed and institutional signers

Dedicated deployments should use an external signer, HSM, KMS, MPC service, or quorum approval. The signer validates the complete signing envelope independently and returns only a signature or operation identifier.

Signer policy and application risk policy are separate controls. Compromise of one should not automatically bypass the other.

### 8.4 CEX credentials

CEX credentials MUST:

- be dedicated to one tenant, environment, and account/subaccount;
- have withdrawal and transfer permissions disabled;
- use only required spot/derivatives permissions;
- use IP allowlisting or equivalent restrictions where supported;
- be stored in a secret manager and accessed only by the CEX adapter;
- be rotated and revoked through a tested procedure;
- be reconciled against exchange permission status;
- never be sent to AI providers or logs.

## 9. Execution security

The controls in [Execution Protocol](ExecutionProtocol.md) are security controls. In particular:

- analytical agents have no venue or signer permission;
- every assessment is schema-validated and tied to an immutable snapshot;
- consensus is deterministic and cannot authorize capital;
- the risk engine rejects unknown or stale mandatory inputs;
- every mutating call and economic action is idempotent;
- the signer independently validates an expiring anti-replay envelope;
- CEX timeouts trigger lookup by client order ID before retry;
- DEX nonce, replacement, finality, and reorganization are reconciled;
- an ambiguous submission activates a scoped circuit breaker;
- a deployment-wide emergency stop cannot be represented as atomic cancellation across independent venues.

## 10. External data and AI security

### 10.1 Data sources

Market, macro, news, exchange, and RPC providers are allowlisted and versioned. The snapshot service validates freshness, sequence, instrument identity, decimals, and divergence. Source failures do not silently lower required quorum.

### 10.2 Model providers

Model adapters receive minimized context and no secrets or direct user identifiers. They have no network tools beyond the explicitly configured provider request and no internal API, signer, database, or venue access.

All output is treated as untrusted. Structured validation, length limits, timeouts, content redaction, and action allowlists apply. Prompt injection contained in news or market text cannot instruct the system to call tools, reveal secrets, change policy, or submit an order.

Raw model payload logging is disabled by default. Diagnostic capture follows the seven-day isolated process in [Data Inventory](DataInventory.md#6-logging-and-model-evidence-policy).

## 11. Network and infrastructure controls

- TLS is required for browser, API, database, queue, signer, secret-manager, and provider communications.
- Internal services use workload identity or mutually authenticated channels where supported.
- Database, queue, and signer endpoints are private or network-restricted in production.
- Administrative interfaces use SSO, MFA, least privilege, and IP/device controls where appropriate.
- Development, staging, and production use separate projects, networks, secrets, identities, wallets, and exchange accounts.
- Container images are minimal, non-root where practical, read-only where practical, and pinned by digest for production.
- Runtime egress is restricted by service role where infrastructure permits.
- Edge/serverless functions do not host long-running trading workers or signing keys.
- Infrastructure changes are reviewed, versioned, and applied through approved CI/CD or documented emergency procedure.

## 12. Application and supply-chain security

Required controls include:

- branch protection and reviewed pull requests;
- mandatory CI for tests, linting, type checking, dependency and secret scanning;
- signed or provenance-attested release artifacts where available;
- dependency lock files and automated update review;
- software bill of materials for production releases;
- static analysis and infrastructure/configuration scanning;
- security regression tests for RLS, authorization, idempotency, risk, signer, and venue adapters;
- isolated untrusted-provider parsing;
- production change approval and rollback;
- documented vulnerability remediation targets.

Baseline remediation targets, measured from validated severity assignment:

| Severity | Mitigation or patch target |
|---|---|
| Critical with credible exploitation | Immediate containment; target permanent remediation within 72 hours |
| High | 14 calendar days |
| Medium | 60 calendar days |
| Low | 120 calendar days or accepted risk |

Exceptions require owner, rationale, compensating controls, expiry, and approval.

## 13. Logging, monitoring, and detection

### 13.1 Prohibited log content

Logs, traces, metrics, and audit payloads MUST NOT contain:

- private keys, seed phrases, authorization keys, CEX secrets;
- bearer tokens, refresh tokens, full cookies, or full authorization headers;
- database passwords or service-role keys;
- unredacted raw model prompts/responses in routine production;
- unnecessary personal or support data.

### 13.2 Required detection

Alerting covers:

- repeated authentication or authorization failures;
- cross-tenant policy denials;
- privileged role, risk-policy, delegation, credential, or circuit-breaker changes;
- unusual secret reads or signer requests;
- signer policy rejection or replay detection;
- abnormal order rate, notional, slippage, price impact, fee, or loss;
- data staleness/divergence;
- ambiguous submission or reconciliation mismatch;
- database/queue latency and resource saturation;
- backup failure and retention-job failure;
- dependency or image vulnerabilities;
- clock drift and audit-chain verification failure.

Alerts identify scope and correlation IDs but not secret values.

### 13.3 Audit-chain integrity

The SQL baseline enforces one root per tenant, a same-tenant existing predecessor for every non-root event, one successor per predecessor, and rejection of self-links. These constraints prevent simple roots, gaps, and forks from being inserted, but they do not validate the digest calculation or prove that every required event reached the database or independent archive.

Application roles have no direct `INSERT` privilege on `audit_events`. Every application event must pass through `hermes.append_audit_event`, or an equivalently reviewed database-enforced boundary, which verifies transaction-local tenant context, serializes the current tenant head, and rejects a stale predecessor. The trusted caller must calculate the canonical event digest and commit the append with the protected state change. Effective-grant tests must prove there is no alternate application write path. An independent verifier must recalculate digests and detect database/archive omissions. `event_sequence` is a global database-ingestion sequence and may be non-contiguous within one tenant; chain verification follows predecessor digests rather than assuming a contiguous per-tenant sequence.

## 14. Incident response

### 14.1 Severity

- **SEV-1:** confirmed or likely key/credential compromise, unauthorized transaction/order, cross-tenant exposure, material data breach, or uncontrolled live execution.
- **SEV-2:** significant degradation or control failure with contained exposure; signer/venue ambiguity affecting multiple executions; backup/recovery impairment.
- **SEV-3:** limited security event or operational defect without known material exposure.
- **SEV-4:** low-risk event, observation, or policy exception.

### 14.2 Immediate actions

For a suspected SEV-1 or SEV-2:

1. Activate the narrowest effective tenant circuit breaker; invoke the deployment-wide emergency stop when scope is unknown or multiple tenants may be affected.
2. Prevent new signing and CEX submissions.
3. Preserve audit, identity, signer, venue, database, and infrastructure evidence.
4. Revoke or suspend affected delegations, authorization keys, CEX keys, sessions, and service credentials.
5. Reconcile open orders, pending transactions, balances, and fills before recovery.
6. Isolate affected services and rotate secrets in dependency order.
7. Notify incident command, legal/privacy, affected customer contacts, and providers according to the response plan.
8. Do not destroy evidence or promise that already-submitted venue activity has stopped.

### 14.3 Recovery

Recovery requires root-cause or bounded-cause understanding, credential and integrity verification, reconciled economic state, validated fix, regression testing, authorized circuit-breaker reset, and enhanced monitoring. A post-incident review records timeline, impact, control gaps, remediation owner, due dates, and communication decisions.

Detailed procedures are in `runbooks/incident-security.md` and related runbooks.

## 15. Vulnerability reporting

Report suspected vulnerabilities through the private channel published in the repository-level [Security Notice](../SECURITY.md). Do not include live private keys, seed phrases, exchange secrets, or personal data in the initial report. Provide a description, affected component, reproduction steps, impact, and safe evidence.

Hermes acknowledges vulnerability reports within two business days and provides an initial severity and remediation target after validation. Reporters may request the current PGP key through `security@hermes-protocol.org`; do not send secret values if an encryption key is not available. Good-faith research is authorized when it stays within test accounts or owned tenants, avoids data access beyond what is necessary to prove impact, does not move assets, avoids persistence or service disruption, and gives Hermes a reasonable remediation window before disclosure. Hermes does not offer a paid bug bounty unless a separate written bounty program is published for the affected scope.

## 16. Backup, recovery, and data integrity

- Define approved RPO and RTO per deployment and data store.
- Back up database roles, schema, data, object storage, configuration, and required audit archives separately.
- Encrypt backups and isolate backup credentials from production runtime credentials.
- Test restoration at least quarterly and after material storage changes.
- Verify row counts, hashes, tenant isolation, audit-chain continuity, deletion tombstones, and ability to reconcile trading state.
- Database backups alone are not assumed to contain object-storage files.
- Restore exercises use non-production credentials and do not submit live orders.

The baseline targets in [Operations Manual](OperationsManual.md) are design objectives until a deployment has measured evidence.

## 17. Security release gates

Live production enablement requires:

- [ ] completed threat model and responsibility matrix;
- [ ] token verification and authorization tests;
- [ ] request-time identity resolver and principal-table denial tests, with separate provisioning-path evidence;
- [ ] RLS and cross-tenant test evidence;
- [ ] effective database-grant matrix and denied-operation tests for API, worker, identity, auditor, migration, backup, and break-glass identities;
- [ ] database-enforced normalized and denormalized cross-resource tenant binding, plus denied-direct-write and every-writer negative tests;
- [ ] frontend secret scan and configuration classification;
- [ ] signer/delegation review and independent policy test;
- [ ] CEX permission verification and withdrawal-disabled evidence;
- [ ] consensus/risk/idempotency regression and property tests;
- [ ] venue sandbox/testnet and reconciliation tests;
- [ ] incident and circuit-breaker game day;
- [ ] backup/restore evidence;
- [ ] direct audit-insert denial, sole append-function access, concurrent append, root/fork/gap/self-link, digest, and independent-export completeness tests;
- [ ] dependency, container, and infrastructure scan review;
- [ ] privacy, terms, retention, and subprocessor alignment;
- [ ] security owner approval and any required independent assessment.

## 18. Exceptions

A security exception must identify the control, risk, affected deployment, compensating controls, owner, approval, creation date, and expiry. Exceptions cannot waive legal obligations or permit undisclosed custody, secret exposure, cross-tenant access, or unbounded live execution.

## 19. Primary implementation references

Provider behavior must be revalidated during each release review. References revalidated on 2026-07-20:

- [Privy access-token verification](https://docs.privy.io/authentication/user-authentication/access-tokens)
- [Supabase data security](https://supabase.com/docs/guides/database/secure-data)
- [PostgreSQL row security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [PostgreSQL secure `SECURITY DEFINER` functions](https://www.postgresql.org/docs/current/sql-createfunction.html#SQL-CREATEFUNCTION-SECURITY)
