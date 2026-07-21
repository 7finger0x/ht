# Runbook: Stale or Divergent Market Data

**Owner role:** Market-data on-call  
**Last reviewed:** 2026-07-20  
**Default severity:** SEV-2 when live execution scope is affected

## 1. Trigger and severity

Trigger on exceeded snapshot/quote age, sequence gaps, RPC block-height disagreement, price-source divergence, invalid decimals/symbol mapping, missing portfolio data, or repeated snapshot-quality rejection.

## 2. Safety objective

Prevent new decisions and executions from using untrustworthy data while preserving reconciliation and avoiding an automatic fallback that changes source assumptions.

## 3. Preconditions and authority

The data or operations on-call may pause affected source, instrument, venue, network, strategy, or tenant scope. The deployment-wide emergency stop is authorized when the affected scope cannot be bounded or may cross tenants.

## 4. Immediate containment

1. Activate a circuit breaker for the smallest verified scope.
2. Mark affected snapshots ineligible; do not extend their validity.
3. Stop new decision evaluations that require the affected source.
4. Allow reconciliation to continue using authoritative venue queries where safe.
5. Record last known good timestamp, sequence/block, source, instrument, and affected execution IDs.
6. Do not reduce source quorum, freshness limits, or mandatory-agent requirements as an incident workaround.

## 5. Diagnosis

Check:

- source status, credentials, quotas, websocket disconnects, and rate limits;
- local clock drift and timestamp parsing;
- sequence, block height, and finality progression;
- symbol normalization, token address/mint, chain ID, and decimals;
- divergence by independent source and whether one source is an outlier;
- queue lag, worker saturation, database latency, and snapshot creation errors;
- whether portfolio/open-order data is stale separately from price data;
- deployments or configuration changes preceding the event.

## 6. Recovery

1. Restore the configured source or approved redundant source without silently changing policy.
2. Backfill only non-authoritative historical data; create new live snapshots.
3. Verify clock, sequence, block, symbol, decimals, and source agreement.
4. Run a simulation decision and deterministic replay.
5. Confirm no accepted decision or risk evaluation remains valid from the stale interval.
6. Reset the breaker with recorded evidence and monitor enhanced freshness/divergence alerts.

## 7. Verification

- mandatory sources are current;
- source divergence is below the policy threshold;
- sequence/block progression is continuous;
- token/instrument identity and decimals match registry;
- new snapshots have correct digest and validity;
- stale decisions and risk evaluations cannot execute;
- simulation results are reproducible;
- reconciliation backlog is current.

## 8. Rollback or abort criteria

Keep scope paused if sources remain divergent, identity/decimal mapping is uncertain, freshness cannot be measured, required portfolio state is stale, or the approved source change has not completed review.

## 9. Evidence to preserve

Source status and responses; timestamps; sequence/block samples; divergence metrics; affected snapshots/decisions/executions; configuration versions; deployment changes; breaker record; simulation and replay output.

## 10. Escalation and communications

Escalate to SEV-1 if untrusted data caused or may have caused a material live order. Notify affected tenants when contract or impact requires it, stating the exact interval and affected instruments/venues.
