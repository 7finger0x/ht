# Hermes Execution Protocol

**Protocol name:** Antigravity  
**Version:** 1.0.0-draft  
**Last revised:** 2026-07-20  
**Status:** Normative design; implementation conformance not yet verified

## 1. Objective

The protocol converts a reproducible market snapshot into, at most, one authorized economic action. It separates analytical opinion from deterministic authorization and produces evidence sufficient to explain, reconcile, and audit every attempted execution.

The protocol does not treat agreement between agents as proof of accuracy or profitability. It does not permit an LLM to determine final position size, bypass a risk rule, select an unapproved venue, or sign a transaction.

## 2. Normative terminology

- **Snapshot:** Immutable, time-bounded representation of market, portfolio, and enabled contextual data.
- **Assessment:** Schema-valid output from one analytical agent.
- **Consensus:** Deterministic calculation of quorum, support, disagreement, and abstention.
- **Decision:** Accepted or rejected action produced by the consensus engine.
- **Risk evaluation:** Deterministic rule-by-rule authorization using current portfolio and venue state.
- **Order intent:** Immutable economic instruction approved for a specific venue and validity interval.
- **Execution:** Lifecycle that signs/submits the intent, observes venue state, and reconciles the result.
- **Signing envelope:** Complete request presented to an isolated signer.
- **Evidence bundle:** Hash-linked records proving what inputs, policies, code, and actions were used.

## 3. End-to-end pipeline

```text
1. Capture snapshot
2. Collect independent assessments
3. Validate eligibility
4. Compute deterministic consensus
5. Refresh authoritative portfolio and venue state
6. Evaluate deterministic risk policy
7. Create immutable order intent
8. Obtain human approval bound to that intent when required
9. Build and validate venue request
10. Obtain signer or CEX credential authorization
11. Submit exactly once per venue idempotency semantics
12. Monitor acknowledgements, transactions, orders, and fills
13. Reconcile balances and terminal state
14. Seal audit evidence
```

A failure at one stage cannot be treated as a success at a later stage. Missing mandatory evidence prevents progression.

## 4. Immutable market snapshot

A snapshot contains:

- `snapshot_id`, `tenant_id`, `strategy_id`, `instrument_id`;
- capture start/end timestamps and `valid_until`;
- venue quotes, order-book depth or pool liquidity, volume, volatility, and source identifiers;
- sequence numbers or block heights where available;
- portfolio balances, positions, pending orders, allowances, gas balances, and exposure;
- optional macro/news feature identifiers and timestamps;
- source-quality and divergence flags;
- canonical payload digest.

### 4.1 Freshness and source quorum

The policy defines maximum age by data class. A live decision requires all mandatory fields to be within their age limit. For prices and balances, the system should use multiple independent sources where practical.

A snapshot is ineligible when:

- its validity period has expired;
- mandatory source timestamps are missing;
- source divergence exceeds policy;
- an RPC, venue, or portfolio source reports an unresolved sequence gap;
- an instrument, venue, or network is paused;
- decimal, symbol, chain, or token identity is ambiguous.

Snapshots are never edited. A refresh creates a new identifier and digest.

## 5. Agent assessment contract

Each agent returns a structured assessment:

```json
{
  "assessment_id": "0b42b9d6-0d1f-4d90-b38c-e5d7c167604f",
  "snapshot_id": "d769f632-3f3e-462d-b747-a427de1d7a42",
  "agent_id": "technical-momentum",
  "agent_version": "3.2.0",
  "provider": "internal",
  "model": "momentum-rules-v3",
  "prompt_version": null,
  "action": "BUY",
  "confidence": "0.72",
  "data_quality": "0.95",
  "valid_until": "2026-07-20T18:00:30Z",
  "rationale_summary": "Momentum and volume conditions satisfy the configured rule set.",
  "input_digest": "sha256:...",
  "output_digest": "sha256:..."
}
```

### 5.1 Permitted actions

- `BUY`
- `SELL`
- `HOLD`
- `ABSTAIN`

`ABSTAIN` means the agent could not produce a reliable assessment. Invalid or timed-out output is converted to `ABSTAIN`, not imputed as support.

### 5.2 Confidence semantics

`confidence` is the agent’s calibrated confidence in its own classification under its evaluation methodology. It is not a guarantee of return. A provider without a documented calibration process may still report a score, but the consensus policy may cap or ignore it.

### 5.3 Agent eligibility

An assessment is eligible only when:

- schema validation succeeds;
- snapshot ID and digest match;
- the agent is enabled by the policy version;
- the assessment has not expired;
- data quality meets the agent-specific minimum;
- model, prompt, and agent versions are approved;
- the agent did not receive prohibited data or tools;
- the same agent identity has not submitted more than one active assessment.

Excluded assessments remain in evidence with an exclusion code.

## 6. Consensus semantics

Consensus is a deterministic agreement calculation. It is separate from risk approval.

For each eligible agent `i`:

- `w_i` is the approved non-negative agent weight;
- `c_i` is confidence in `[0,1]`;
- `q_i` is data quality in `[0,1]`;
- `a_i` is one of `BUY`, `SELL`, `HOLD`, `ABSTAIN`.

Weights are set by an offline, versioned evaluation and change only through reviewed configuration. Agents do not update their own weights in production.

Let:

```text
W_enabled  = sum of weights for all agents enabled by policy
W_eligible = sum of weights for eligible agents
quorum_weight = W_eligible / W_enabled
```

For candidate action `A` in `{BUY, SELL, HOLD}`:

```text
support_weight(A) = sum(w_i where a_i = A) / W_eligible
weighted_confidence(A) = sum(w_i * c_i * q_i where a_i = A) / W_eligible
opposition_weight(A) = sum(w_i where a_i is a conflicting directional action) / W_eligible
abstain_weight = sum(w_i where a_i = ABSTAIN) / W_enabled
```

For `BUY`, `SELL` is conflicting; for `SELL`, `BUY` is conflicting. `HOLD` is non-support but not directional opposition.

### 6.1 Baseline acceptance policy

The simulation-safe example configuration uses:

- at least 3 eligible agents;
- `quorum_weight >= 0.75`;
- `support_weight(candidate) >= 0.80`;
- `weighted_confidence(candidate) >= 0.60`;
- `opposition_weight(candidate) <= 0.15`;
- `abstain_weight <= 0.25`;
- no mandatory agent missing;
- all assessments and snapshot within policy freshness.

These are configurable control values, not performance claims. A live deployment must justify them through documented evaluation and may require stricter limits.

### 6.2 Candidate selection

1. Calculate support for `BUY`, `SELL`, and `HOLD`.
2. Select the action with greatest support.
3. If two actions tie within the policy epsilon, choose `HOLD`.
4. A directional candidate is accepted only if every threshold passes.
5. Otherwise the result is `NO_CONSENSUS` and no order intent is created.

The engine records raw values before rounding. Decimal arithmetic is used; binary floating-point is not used for threshold decisions.

### 6.3 Decision output

A consensus decision includes:

- candidate and result;
- eligible/excluded assessment IDs;
- weights and metrics;
- threshold results;
- consensus policy version;
- algorithm version;
- snapshot digest;
- canonical decision digest;
- `valid_until`.

The previous term `confidence_score` is replaced by explicit `support_weight`, `weighted_confidence`, `quorum_weight`, and `opposition_weight` fields.

## 7. Deterministic risk controls

The risk engine is a deny-by-default rule engine. It evaluates an immutable policy version against authoritative state captured as close as practical to submission. It does not trust an agent-suggested quantity.

### 7.1 Required control groups

#### System and authorization

- production live-trading flag enabled;
- strategy, tenant, portfolio, venue, signer, and instrument active;
- requesting principal has execution scope;
- required approval path configured;
- no deployment-wide emergency stop or applicable tenant, strategy, venue, network, account, or instrument circuit breaker active.

#### Data quality

- snapshot and quote are fresh;
- portfolio balances and open orders are fresh;
- source quorum and divergence pass;
- token/instrument identity, decimals, chain, venue, and contract are unambiguous;
- time synchronization is within tolerance.

#### Portfolio limits

- maximum order notional;
- maximum order notional as a fraction of NAV;
- maximum position and concentration by asset, issuer, venue, chain, and correlated group;
- maximum gross and net exposure;
- maximum leverage and borrow utilization;
- available balance and margin;
- reserved exposure for pending orders;
- maximum daily loss and drawdown;
- counterparty and bridge exposure where applicable.

#### Market and execution limits

- maximum quote age;
- maximum spread, slippage, and estimated price impact;
- minimum liquidity multiple relative to order size;
- order-size, price-tick, lot-size, and minimum-notional precision;
- maximum gas, priority fee, or venue fee;
- permitted order type and time in force;
- permitted route, router, contract, program, recipient, and calldata/instruction;
- transaction deadline and minimum received amount;
- venue rate limit and health.

#### Chain and account limits

- supported chain ID and RPC quorum;
- sufficient native gas balance;
- nonce/account sequence consistency;
- allowance within policy;
- required finality depth;
- no unresolved reorganization, stuck transaction, or ambiguous submission;
- CEX credential has expected permissions and withdrawals disabled.

### 7.2 Rule result

Each rule returns:

```json
{
  "rule_id": "portfolio.max_order_nav_fraction",
  "version": "1.0.0",
  "status": "PASS",
  "observed": "0.0142",
  "limit": "0.0200",
  "unit": "NAV_FRACTION",
  "reason_code": "WITHIN_LIMIT",
  "evidence_refs": ["portfolio_snapshot:...", "risk_policy:..."]
}
```

Statuses are `PASS`, `FAIL`, or `UNKNOWN`. A mandatory `FAIL` or `UNKNOWN` rejects the order.

### 7.3 Quantity calculation

The approved quantity is the minimum quantity permitted by every applicable rule and venue precision. The baseline algorithm is:

```text
q_allowed = min(
  q_requested,
  q_notional_cap,
  q_nav_fraction_cap,
  q_position_cap,
  q_exposure_cap,
  q_liquidity_cap,
  q_balance_or_margin_cap,
  q_loss_budget_cap,
  q_signer_or_venue_policy_cap
)
```

Then round **down** to the venue lot size. If the result is below minimum notional or zero, reject.

Fractional Kelly or volatility scaling may produce a proposed cap, but cannot increase any hard limit. Such models require documented inputs, payoff assumptions, sample size, uncertainty adjustment, out-of-sample evaluation, and an absolute upper bound.

### 7.4 Approval threshold

Policy may require a human approver based on notional, asset risk, venue, strategy state, custody mode, or policy change. Approval:

- references the exact risk evaluation and order-intent digest;
- is accepted only while the execution is `APPROVAL_PENDING` and the supplied digest matches the current immutable intent;
- expires no later than the earliest expiry of the decision, risk evaluation, order intent, quote, or applicable policy;
- is invalidated by any economic change;
- uses a principal distinct from the requester when dual control is required;
- is recorded in the audit ledger.

The order intent is created before approval so the approver can review and bind to its exact digest. Approval is a separate immutable record and is never an input to the intent digest it approves.

The approval surface MUST display the current intent's venue, instrument, account/wallet reference, side, order type, quantity, limit/stop price, time in force, slippage and price-impact caps, fee cap and currency, deadline, finality policy, policy versions, software version, expiry, and digest. A digest presented without its human-readable bound fields is not sufficient approval evidence.

## 8. Order intent

An order intent is immutable and includes:

- tenant, strategy, portfolio, decision, risk evaluation, venue, account/wallet, and instrument IDs;
- side, order type, quantity, limit/stop price, time in force;
- slippage, price-impact, fee, deadline, and finality parameters;
- approval requirement; any approval record is stored separately and references the intent digest;
- policy and software versions;
- `client_order_id` or transaction-intent identifier;
- canonical digest and expiration.

Intent construction is deterministic from the approved risk evaluation, selected venue, normalized execution parameters, and versioned policies. Any economic change creates a new order intent, requires a new risk evaluation, and invalidates prior approval. Administrative metadata such as a reconciliation note may be appended without changing the intent.

Price fields are canonical by order type: `MARKET` requires both limit and stop price to be null; `LIMIT` requires a positive limit price and a null stop price; `STOP_LIMIT` requires both prices to be positive. Unsupported or inconsistent combinations are rejected before intent creation.

## 9. Idempotency and duplicate prevention

### 9.1 HTTP idempotency

Every mutating external API request requires an `Idempotency-Key` header:

- 16–128 visible ASCII characters;
- scoped to tenant, authenticated principal, HTTP method, and route;
- retained for at least 24 hours; execution keys are retained for the execution-record retention period;
- stored with a canonical request-body hash, status, resource ID, and response.

Behavior:

- first valid request reserves the key atomically;
- same key and identical canonical request returns the original status/resource/response;
- same key and different request returns `409 IDEMPOTENCY_KEY_REUSED`;
- concurrent duplicates wait for or receive the result of the first request;
- a server timeout does not free the key.

### 9.2 Economic idempotency

The orchestrator derives a stable economic identifier from:

```text
tenant_id + strategy_id + decision_id + risk_evaluation_id + venue_id + leg_index
```

A uniqueness constraint prevents multiple order intents for the same economic action.

For CEX execution, the adapter uses a stable venue-supported client order identifier and queries by that identifier after any timeout before retrying.

For DEX execution, the signed transaction or user operation has one intent digest. A replacement transaction may alter only policy-approved fee fields unless a new risk evaluation authorizes economic changes. Nonce or account-sequence reservation prevents conflicting submissions.

## 10. Signer behavior

### 10.1 Signing envelope

The orchestrator sends the signer a complete envelope containing:

- envelope ID and expiry;
- tenant, execution, order-intent, wallet/account, network, and chain IDs;
- exact unsigned transaction, typed data, or user operation;
- decoded economic summary;
- approved contracts/programs, methods/instructions, recipient, assets, quantities, minimum received, deadline, fees, nonce/sequence;
- risk-evaluation and approval digests;
- required signer-policy version;
- anti-replay nonce;
- orchestrator signature or mutually authenticated workload identity.

### 10.2 Independent signer checks

The signer independently verifies:

- request authentication and anti-replay value;
- envelope expiry and one-time use;
- network, wallet, contract/program, method/instruction, recipient, asset, quantity, fee, deadline, and calldata constraints;
- risk and approval digest binding;
- active delegation and signer policy;
- amount/time/rate limits;
- circuit-breaker state available to the signer.

The signer returns a signature, signed transaction, or provider operation ID. It never returns raw private key material.

### 10.3 User-in-loop signing

The UI displays the decoded transaction and policy-relevant fields. User approval is bound to the exact digest. A changed route, recipient, quantity, minimum received, chain, or calldata requires a new approval.

### 10.4 Delegated signing

Delegation is created through an explicit user/admin action and includes scope, limits, expiration, and revocation. The server signer receives only the authority required by that policy. Policy changes are separately authenticated and audited. The service UI must show active delegations and provide immediate revocation.

### 10.5 CEX request signing

The credential adapter retrieves an exchange secret only for the request, signs the venue API call, and clears it from process memory where feasible. The adapter refuses withdrawal, transfer, API-key-management, or account-management operations under the baseline role.

## 11. Order and execution state machine

### 11.1 Canonical states

| State | Meaning | Permitted next states |
|---|---|---|
| `CREATED` | Request accepted and idempotency reserved | `CONSENSUS_PENDING`, `REJECTED` |
| `CONSENSUS_PENDING` | Assessments are being collected/validated | `CONSENSUS_ACCEPTED`, `CONSENSUS_REJECTED`, `EXPIRED`, `FAILED` |
| `CONSENSUS_ACCEPTED` | Directional decision passed consensus | `RISK_PENDING`, `EXPIRED` |
| `CONSENSUS_REJECTED` | No eligible action | Terminal |
| `RISK_PENDING` | Authoritative state and rules are evaluated | `RISK_APPROVED`, `RISK_REJECTED`, `FAILED` |
| `RISK_APPROVED` | Risk authorizes creation of one immutable order intent | `APPROVAL_PENDING`, `READY_TO_SUBMIT`, `EXPIRED` |
| `RISK_REJECTED` | One or more mandatory controls failed/unknown | Terminal |
| `APPROVAL_PENDING` | Exact immutable intent awaits human approval | `READY_TO_SUBMIT`, `REJECTED`, `EXPIRED` |
| `READY_TO_SUBMIT` | Intent is complete, current, and approved when required | `SIGNING`, `SUBMITTING`, `CANCELLED`, `EXPIRED` |
| `SIGNING` | Wallet authorization in progress | `SUBMITTING`, `SIGNING_FAILED`, `EXPIRED` |
| `SIGNING_FAILED` | Signer refused or failed | `READY_TO_SUBMIT` only after classified retry; otherwise terminal |
| `SUBMITTING` | Venue call or broadcast in progress | `ACKNOWLEDGED`, `SUBMISSION_AMBIGUOUS`, `FAILED` |
| `SUBMISSION_AMBIGUOUS` | Timeout or uncertain venue state | `ACKNOWLEDGED`, `FAILED`, `CANCELLED`; blocks conflicting retry |
| `ACKNOWLEDGED` | Venue accepted order/transaction | `PARTIALLY_FILLED`, `FILLED`, `CONFIRMED`, `CANCEL_PENDING`, `EXPIRED`, `FAILED` |
| `PARTIALLY_FILLED` | Some quantity filled | `PARTIALLY_FILLED`, `FILLED`, `CANCEL_PENDING`, `CANCELLED`, `EXPIRED` |
| `CONFIRMED` | On-chain inclusion meets confirmation threshold | `FINALIZED`, `REORGED`, `FAILED` |
| `REORGED` | Previously observed chain state was removed | `ACKNOWLEDGED`, `FAILED` |
| `FINALIZED` | On-chain finality policy satisfied | `RECONCILING` |
| `CANCEL_PENDING` | Cancellation requested | `CANCELLED`, `PARTIALLY_FILLED`, `FILLED`, `FAILED` |
| `FILLED` | Venue reports full fill | `RECONCILING` |
| `CANCELLED` | Venue confirms no further fill expected | `RECONCILING` |
| `EXPIRED` | Intent/order expired | `RECONCILING` when venue activity may exist; otherwise terminal |
| `FAILED` | Classified failure | `RECONCILING` when economic effect is possible; otherwise terminal |
| `RECONCILING` | Orders, fills, receipts, fees, and balances are compared | `RECONCILED`, `RECONCILIATION_FAILED` |
| `RECONCILIATION_FAILED` | State mismatch remains | `RECONCILING`; affected scope paused |
| `RECONCILED` | Internal and authoritative state agree | Terminal |
| `REJECTED` | Request or required approval was rejected before submission | Terminal |

State changes use optimistic concurrency or row locking and an expected previous state. Duplicate or out-of-order events are recorded but cannot regress a terminal state.

### 11.2 Cancellation

Cancellation is best effort. It cannot guarantee prevention of a fill or on-chain inclusion. A cancel request is itself idempotent, and the reconciler continues until the venue establishes terminal state.

## 12. Venue-specific behavior

### 12.1 DEX

Before signing, the adapter obtains a fresh quote and validates route, contracts/programs, token identities, quantity, minimum received, price impact, deadline, and fees. If the quote changes beyond policy, it creates a new risk evaluation and intent.

After broadcast, the adapter tracks transaction hash, mempool status where available, replacement, inclusion, confirmations, finality, token balance changes, and emitted events. A receipt with status success is not by itself sufficient when token behavior or route semantics require balance verification.

### 12.2 CEX

Before submission, the adapter validates instrument status, tick/lot precision, min/max notional, account balance/margin, open-order reservation, and rate limits. It records the exact normalized venue payload.

After submission, REST acknowledgement is correlated with the client order ID, then reconciled against websocket and REST order/fill streams. Missing acknowledgement after a timeout triggers lookup, not immediate duplicate submission. Every fill receives a stable `venue_fill_id`: the exchange fill/trade identifier for CEX activity, or a deterministic transaction-hash plus event/instruction index for DEX activity. That identifier is unique per venue order and is the primary external-event deduplication key.

## 13. Circuit breakers and deployment stop

Hermes has two control layers:

- a **deployment-wide emergency stop**, controlled by the deployment operator outside the tenant API and enforced at both the execution worker and signer/credential boundary; and
- **tenant circuit breakers** at tenant, strategy, portfolio, venue, account/wallet, network, and instrument scopes.

Triggers include:

- data staleness or source divergence;
- daily loss or drawdown limit;
- repeated risk, signing, or venue failures;
- ambiguous submission or reconciliation mismatch;
- abnormal slippage, price impact, spread, fee, or fill behavior;
- signer or credential anomaly;
- chain reorganization or RPC disagreement;
- security incident or operator action.

Activation prevents new order intents within the applicable scope. The deployment stop prevents new live signing/submission across the deployment. Neither control claims to atomically stop orders already accepted by independent venues. Recovery requires a documented reason, evidence, authorized actor, reconciliation, and explicit reset.

`StepShield` is the product name for the circuit-breaker subsystem. It is not a separate probabilistic model.

## 14. Audit evidence

### 14.1 Event structure

Every trusted stage emits an event conforming to `schemas/audit-event.schema.json` with:

- event, tenant, actor, resource, correlation, causation, and idempotency identifiers;
- service, software commit, environment, and region;
- action and result;
- UTC timestamp and clock source status;
- canonical payload hash and evidence references;
- previous event hash for the tenant stream;
- current event hash.

### 14.2 Canonicalization and hashing

The implementation uses one documented canonical JSON algorithm and SHA-256 or a stronger approved digest. Timestamps, decimals, property ordering, and omitted/null values have fixed serialization rules. The same evidence must produce the same digest across services.

### 14.3 Evidence bundle and anchoring

The final evidence bundle includes all records listed in [SPEC.md](../SPEC.md). It is exported to an access-controlled archive with retention lock where available. A periodic root may be anchored on-chain, but the documentation must distinguish:

- application hash chain;
- independent immutable retention;
- optional public-chain anchoring;
- external audit or assurance.

None should be called a zero-knowledge proof unless an actual ZK system and verification specification are implemented.

## 15. Error model and retries

Errors are classified as:

- `VALIDATION`: request or provider payload invalid; no retry without correction;
- `AUTHENTICATION` or `AUTHORIZATION`: deny; no automatic retry;
- `STALE_STATE`: refresh and create new evaluation;
- `POLICY_REJECTION`: terminal for the intent;
- `TRANSIENT_DEPENDENCY`: bounded exponential backoff with jitter and deadline;
- `RATE_LIMIT`: respect provider retry metadata and deadline;
- `AMBIGUOUS_SUBMISSION`: reconcile before any retry;
- `PERMANENT_VENUE`: terminal and alert;
- `SECURITY`: pause affected scope and invoke incident response.

Retries never extend an expired decision, risk evaluation, approval, quote, or signing envelope.

## 16. Versioning and change control

Every evidence record references:

- protocol version;
- application release and source commit;
- snapshot schema version;
- agent/model/prompt version;
- consensus algorithm and policy version;
- risk engine and policy version;
- venue adapter and registry version;
- signer policy version.

A material change to consensus, risk, signer policy, precision, routing, or venue semantics requires simulation regression, sandbox/testnet test, change approval, rollback plan, and updated documentation. Online model or weight changes without versioned approval are prohibited.

## 17. Required test classes

- deterministic replay of consensus and risk results;
- decimal boundary and rounding-down tests;
- market, limit, and stop-limit price-field combination tests;
- property tests showing hard limits cannot be exceeded;
- concurrent idempotency and duplicate-job tests;
- wrong-tenant and wrong-role negative tests;
- stale/divergent data and missing-field tests;
- user approval and delegation-expiry tests;
- approval-before-intent, missing review-field, stale/mismatched-digest, mutated-field, and approval-expiry tests;
- signer policy rejection and anti-replay tests;
- CEX timeout/client-order-ID reconciliation tests;
- DEX nonce, replacement, dropped transaction, reorg, and finality tests;
- partial fill, cancel race, fee, and balance reconciliation tests;
- circuit-breaker activation and recovery game days;
- audit-chain verification and evidence export tests.
