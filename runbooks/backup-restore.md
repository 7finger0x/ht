# Runbook: Backup and Restore

**Owner role:** Database and recovery on-call  
**Last reviewed:** 2026-07-20  
**Default severity:** SEV-2 for production recovery; planned exercise otherwise

## 1. Trigger and severity

Use for database loss/corruption, region failure, accidental change, audit/archive loss, or scheduled restore exercise.

## 2. Safety objective

Restore an internally consistent control plane without permitting live execution until tenant isolation, audit continuity, deletion controls, and authoritative venue state are verified.

## 3. Preconditions and authority

Recovery requires an approved restore point, isolated target, recovery lead, security/operations approval, and access to database, object-storage, configuration, and audit backups. The deployment-wide live-execution control remains disabled.

## 4. Immediate containment

1. Invoke the deployment-wide emergency stop and stop state-changing API/execution workers.
2. Keep evidence and reconciliation access where safe.
3. Record incident/exercise time, suspected corruption interval, last known good backup, and all data stores.
4. Protect current primary data from overwrite until evidence is captured.
5. Select target recovery point based on RPO, integrity, and venue state—not convenience.

## 5. Diagnosis

Determine affected stores and whether the issue involves schema, roles/grants/RLS, rows, object files, audit archive, queue, configuration, or secrets. Verify backup encryption, checksums, timestamps, provider status, and whether public-chain/CEX activity continued after the recovery point.

## 6. Recovery

1. Restore into an isolated environment with non-production signer and venue credentials.
2. Restore roles/grants, schema, data, object storage, audit archive, and configuration using store-specific procedures.
3. Apply required migrations through the approved path.
4. Recreate application login roles as NOBYPASSRLS non-owners.
5. Replay deletion tombstones and retention actions.
6. Verify audit-chain continuity; record any expected recovery gap.
7. Reconcile every account/wallet/order from before the recovery point through current authoritative venue/chain state.
8. Run identity, RLS, idempotency, simulation, signer-policy, and evidence tests.
9. Promote or redirect only after approval; keep live execution disabled until final reconciliation.

## 7. Verification

- row counts and checksums by tenant/data class;
- RLS enabled and forced on all tenant tables;
- application roles cannot bypass RLS or own tables;
- cross-tenant tests fail safely;
- object files and metadata agree;
- audit hashes and archives verify;
- retention/deletion state reapplied;
- queue contains no stale executable job;
- orders, fills, fees, positions, balances, nonces, and allowances reconcile;
- RPO and RTO measured and recorded.

## 8. Rollback or abort criteria

Abort promotion if tenant isolation fails, backup integrity is uncertain, object/audit data is missing beyond approved tolerance, stale jobs can execute, or venue state is unreconciled. Preserve both source and restore environments for investigation.

## 9. Evidence to preserve

Backup identifiers/checksums; encryption/key references; restore commands and logs; target environment; schema/migration versions; row/hash comparison; RLS test output; audit verification; reconciliation report; measured RPO/RTO; approvals.

## 10. Escalation and communications

Escalate to security/privacy/legal when loss, corruption, or unauthorized access may affect personal or tenant data. Customer notices state recovered interval, unavailable or reconstructed data, and execution impact.
