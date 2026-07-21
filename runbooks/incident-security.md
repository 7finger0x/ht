# Runbook: Security Incident

**Owner role:** Security on-call  
**Last reviewed:** 2026-07-20  
**Default severity:** SEV-1 for unauthorized transaction, key/credential concern, or cross-tenant exposure

## 1. Trigger and severity

Use this runbook for suspected account takeover, token compromise, cross-tenant access, unauthorized signer/CEX action, leaked secret, malicious release, or material personal-data exposure. Start at SEV-1 when economic authority or tenant isolation may be affected; downgrade only after evidence bounds the impact.

## 2. Safety objective

Stop new unauthorized effects, preserve authoritative evidence, determine whether economic or data impact occurred, and restore only after credentials, integrity, tenancy, and venue state are verified.

## 3. Preconditions and authority

The incident commander or security on-call may invoke the deployment-wide emergency stop and suspend signing without prior business approval. Credential revocation and customer communication follow the incident authority matrix. Maintain two-person control for recovery where feasible.

## 4. Immediate containment

1. Record UTC start time, detector, affected environment, and initial indicators.
2. Invoke the deployment-wide emergency stop when scope is unknown or multiple tenants may be affected; otherwise activate the narrowest proven tenant scope.
3. Disable new signer and CEX credential-adapter requests while keeping reconciliation available.
4. Preserve identity, API, database, queue, signer, venue, cloud, and audit logs. Export immutable snapshots where available.
5. Revoke or suspend affected sessions, identity applications, delegated signers, authorization keys, CEX credentials, database users, and workload identities in dependency order.
6. Isolate suspected workloads or releases. Do not delete containers, logs, or database rows before evidence capture.
7. Begin venue and wallet reconciliation from the earliest possible compromise time.
8. Notify incident command, security, operations, trading/reconciliation, legal/privacy, and affected customer contacts according to the matrix.

## 5. Diagnosis

Determine:

- first and last known indicators;
- affected principals, tenants, services, wallets, accounts, venues, and regions;
- whether token verification, RLS, support access, or privileged roles were bypassed;
- every secret read, signer operation, order, transaction, fill, transfer, policy change, and circuit-breaker change;
- source release/image/configuration and whether provenance matches;
- whether audit-chain continuity or log collection was impaired;
- personal-data categories, recipients, and jurisdictional notification implications;
- whether compromise persists in backups, CI, developer machines, or provider consoles.

Use correlation IDs and authoritative venue IDs. Treat absence of an application log as inconclusive until provider and database evidence agree.

## 6. Recovery

1. Patch or remove the compromised path.
2. Rotate credentials from highest-level roots downward. Do not rotate a child into a still-compromised parent environment.
3. Rebuild affected workloads from trusted source and immutable artifacts.
4. Verify database grants, forced RLS, tenant context, identity configuration, signer policy, CEX permissions, and frontend bundle contents.
5. Reconcile orders, transactions, fills, fees, positions, balances, nonces, and allowances.
6. Run security regression, cross-tenant, idempotency, signer, and venue tests.
7. Restore read-only service first.
8. Reset breakers only with incident-commander and security/trading approval; re-enable limited scope before broader execution.
9. Increase monitoring and preserve the incident hold.

## 7. Verification

- no unapproved active sessions, roles, delegations, credentials, or workloads;
- cross-tenant negative tests pass;
- application roles cannot bypass RLS;
- signer refuses an out-of-policy and replayed envelope;
- CEX credentials show withdrawals/transfers disabled;
- authoritative venue and blockchain state is reconciled;
- audit chain verifies from before the incident through recovery;
- backup and retention implications are addressed;
- legal/privacy and customer notifications are decided and recorded.

## 8. Rollback or abort criteria

Abort recovery and keep execution paused if cause is unbounded, evidence is incomplete, any credential or release remains untrusted, tenant isolation fails, signer policy cannot be verified, or economic state is unreconciled.

## 9. Evidence to preserve

Incident timeline; alert; affected identifiers; access and provider logs; database audit and query logs; queue messages/metadata; image digests/SBOM/provenance; identity and role changes; secret-read logs; signer requests; venue orders/fills; transaction receipts; breaker records; communications; legal decisions; and hashes of exported evidence.

Do not include raw keys, seed phrases, CEX secrets, or full bearer tokens in the incident record.

## 10. Escalation and communications

Use the deployment's approved incident contact matrix. External statements distinguish confirmed from suspected impact, specify time in UTC, and avoid claiming that already-submitted orders or transactions were stopped until reconciliation proves it. Follow contractual and legal notification deadlines.
