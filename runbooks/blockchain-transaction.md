# Runbook: Blockchain Transaction Failure or Reorganization

**Owner role:** Blockchain-operations on-call  
**Last reviewed:** 2026-07-20  
**Default severity:** SEV-2

## 1. Trigger and severity

Use for stuck, dropped, replaced, reverted, wrong-fee, nonce-conflicting, unexpectedly executed, or reorged transactions; RPC disagreement; or balance/event mismatch after a receipt.

## 2. Safety objective

Prevent conflicting transactions, establish canonical chain state, preserve signer intent, and reconcile token/native balances before further execution.

## 3. Preconditions and authority

Blockchain operations may pause a wallet, network, venue, and instrument. A replacement transaction may change only policy-approved fee fields unless a new risk evaluation authorizes an economic change.

## 4. Immediate containment

1. Activate wallet/network/instrument breaker.
2. Stop new transactions using the affected nonce/account sequence.
3. Record signed transaction hash, raw transaction digest, nonce/sequence, block references, route, deadline, and minimum received.
4. Query multiple approved RPCs and any relayer/mempool service.
5. Continue monitoring until dropped, replaced, confirmed/finalized, reverted, or expired under policy.

## 5. Diagnosis

Check chain ID, nonce/account sequence, signer wallet, gas/native balance, base/priority fee, transaction propagation, replacement rules, contract/program allowlist, deadline, minimum received, allowance, simulation/revert reason, block inclusion, confirmation depth, reorg evidence, emitted events, and actual balance deltas.

A successful receipt is insufficient when token behavior or route semantics require balance verification.

## 6. Recovery

- **Underpriced/stuck:** create a policy-permitted fee replacement with identical economic calldata and the same nonce; retain both hashes.
- **Dropped and expired:** confirm absence across approved sources before creating a new intent and risk evaluation.
- **Reverted:** record revert evidence; do not retry until cause is corrected and a new evaluation approves it.
- **Reorged:** move state to `REORGED`, monitor canonical chain, and do not assume previous fills/balances remain.
- **Wrong or duplicate economic effect:** keep scope paused, calculate net effect, and use separately approved corrective action if necessary.

## 7. Verification

- canonical chain and finality policy agree across approved sources;
- nonce/account sequence is known;
- transaction replacement relationship is documented;
- decoded calldata/instructions match approved intent;
- token and native balance changes, fees, and events reconcile;
- no stale signed transaction can be replayed outside policy;
- breaker reset is authorized.

## 8. Rollback or abort criteria

Keep scope paused during RPC disagreement, unresolved reorg, unknown nonce, insufficient balance evidence, or signer/intent mismatch.

## 9. Evidence to preserve

Signing envelope and digest; signer operation ID; raw signed-transaction digest; transaction hashes; RPC responses; simulation/revert data; block headers; receipts/events; balances; replacement relationship; finality time; breaker record.

## 10. Escalation and communications

Escalate to SEV-1 for unauthorized destination/asset/amount, signer-policy bypass, or material duplicate effect. Do not describe a transaction as final until the configured finality policy passes.
