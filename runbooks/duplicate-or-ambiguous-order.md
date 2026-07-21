# Runbook: Duplicate or Ambiguous Order

**Owner role:** Execution and reconciliation on-call  
**Last reviewed:** 2026-07-20  
**Default severity:** SEV-2; SEV-1 for material duplicate exposure

## 1. Trigger and severity

Use when submission times out, a client order ID conflicts, duplicate queue delivery is suspected, two venue IDs appear for one intent, a transaction hash is uncertain, or internal and authoritative order state differ.

## 2. Safety objective

Prevent additional economic effect, determine whether any order or transaction exists, reconcile all fills, and correct state without deleting evidence.

## 3. Preconditions and authority

The execution/reconciliation on-call may pause account, wallet, instrument, strategy, and venue scope. Manual hedging or offsetting requires a new approved emergency intent and is not an ordinary retry.

## 4. Immediate containment

1. Activate account/wallet and instrument breaker.
2. Mark execution `SUBMISSION_AMBIGUOUS` if venue effect is possible.
3. Stop retries with new idempotency keys or client order IDs.
4. Preserve original request digest, idempotency record, queue attempts, signer output, client order ID, nonce, and transaction bytes/hash.
5. Query by every stable identifier and account time window.
6. Monitor fills and balances continuously until bounded.

## 5. Diagnosis

Determine:

- whether HTTP timeout occurred before or after venue receipt;
- whether idempotency reservation and economic uniqueness constraints succeeded;
- whether concurrent workers processed the same job;
- CEX client-order-ID rules and lookup results;
- DEX nonce/account sequence, signed transaction hash, mempool/relayer state, replacement, and chain receipts;
- partial fills, cancellation races, or delayed webhooks;
- internal state-transition version conflicts;
- exact net position and cash/token balance effect.

## 6. Recovery

1. If no authoritative order/transaction exists and the intent remains valid, retry only through the same idempotent economic path.
2. If one exists, attach its authoritative identifier and continue monitoring/reconciliation.
3. If multiple exist, cancel remaining open quantities where possible and calculate net exposure.
4. Any corrective hedge uses a separate emergency risk evaluation, approval, and intent.
5. Insert correction and audit events; never overwrite or delete original records.
6. Repair idempotency, queue, or adapter defect and run concurrency regression tests.
7. Reset breaker only after balances and all venue states reconcile.

## 7. Verification

- exactly identified set of venue orders/transactions;
- fills, fees, cancellations, receipts, positions, and balances reconcile;
- no pending worker can resubmit the old intent;
- same idempotency key replays the original response;
- same key with changed payload returns conflict;
- concurrent duplicate test produces one economic effect;
- affected code/configuration fix is deployed and monitored.

## 8. Rollback or abort criteria

Do not resume if lookup remains unavailable, position/balance is uncertain, nonce/order sequence can conflict, or a duplicate-processing defect remains reproducible.

## 9. Evidence to preserve

Idempotency row; request/body digests; job IDs/attempts; worker logs; signer envelope/signature ID; venue request metadata; client/venue order IDs; transaction bytes/hash; fills; balances; state-transition history; breaker and correction approvals.

## 10. Escalation and communications

Escalate for material exposure, customer impact, or evidence of malicious replay. Communications state gross and net effects separately and distinguish submitted, acknowledged, filled, cancelled, confirmed, and reconciled states.
