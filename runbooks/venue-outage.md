# Runbook: Venue, RPC, or Relayer Outage

**Owner role:** Trading-operations on-call  
**Last reviewed:** 2026-07-20  
**Default severity:** SEV-2

## 1. Trigger and severity

Use for exchange maintenance/outage, elevated venue errors, RPC disagreement/unavailability, relayer failure, websocket loss, order lookup failure, or abnormal venue latency.

## 2. Safety objective

Stop new exposure at the affected venue, establish the state of all pending activity, and avoid duplicate or economically different rerouting.

## 3. Preconditions and authority

Trading operations may pause a venue or network. Rerouting to another venue requires a new quote, risk evaluation, and order intent; it is not an outage retry.

## 4. Immediate containment

1. Activate venue/network breaker.
2. Stop new submissions to the affected adapter.
3. Preserve and classify all in-flight requests as not submitted, acknowledged, or ambiguous.
4. Keep reconciliation workers active with bounded polling/backoff.
5. Do not submit the same economic action to another venue until the original state is resolved or explicitly abandoned under policy.
6. Notify the signer/credential adapter not to accept new envelopes for the paused scope.

## 5. Diagnosis

Check provider status, DNS/TLS, credentials, IP restrictions, rate limits, API version, exchange symbol status, RPC block progression, websocket sequence, relayer/mempool status, local egress, and recent deployments. Correlate by client order ID or transaction hash.

## 6. Recovery

1. Confirm provider recovery from more than one signal where practical.
2. Query every pending order/transaction using stable identifiers.
3. Reconcile fills, cancellations, receipts, fees, balances, and finality.
4. Refresh venue metadata and precision.
5. Run sandbox/test query and simulation/paper order if supported.
6. Reset the breaker for limited scope; monitor before full enablement.

## 7. Verification

- no unresolved ambiguous submissions;
- order/fill and chain state reconciled;
- credentials and permissions valid;
- websocket and REST views agree;
- rate limits and clocks are current;
- no silent adapter or API behavior change;
- new quote and risk evaluation required for any reroute.

## 8. Rollback or abort criteria

Keep venue paused if authoritative lookup is unavailable, orders cannot be reconciled, provider behavior changed, credentials are uncertain, or a test request produces ambiguity.

## 9. Evidence to preserve

Provider incident/status references; request/response metadata; client order IDs; transaction hashes; adapter version; timestamps; fills; balances; breaker record; recovery tests; customer communication.

## 10. Escalation and communications

Escalate to SEV-1 for unauthorized effects, material duplicate exposure, or widespread unreconciled state. State that cancellation and an atomic deployment-wide stop are not guaranteed across independent venues.
