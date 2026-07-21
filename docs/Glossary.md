# Hermes Glossary

**Version:** 1.0.0-draft  
**Last revised:** 2026-07-20

## A

**Abstention** — An agent result indicating that it cannot produce an eligible assessment. Abstention is not counted as support and does not automatically transfer weight to another agent.

**Agent** — A deterministic rule, statistical model, LLM adapter, or other analytical component that produces a schema-valid assessment. Agents have no signer or venue authority.

**Agent assessment** — Versioned analytical record containing action, confidence, data quality, validity, rationale summary, and evidence digests.

**Antigravity Protocol** — The Hermes execution specification covering snapshots, assessments, consensus, risk, idempotency, signing, venue execution, reconciliation, and audit evidence.

**Approval digest** — Hash binding a human approval to one exact order intent. Economic changes invalidate the approval.

**Assets under management (AUM)** — Assets managed or administered for an account or portfolio. Hermes uses the more precise term **NAV** for risk ratios when the calculation is based on net portfolio value.

**ATR (Average True Range)** — A historical volatility indicator based on trading ranges. ATR may inform a proposed volatility cap but cannot override hard risk limits.

**Audit event** — Append-only record of actor, action, result, resource, correlation, evidence, and hash linkage.

## C

**Canonicalization** — Deterministic serialization rules that make equivalent evidence produce the same digest.

**CEX (Centralized Exchange)** — An exchange that maintains account, order, fill, and custody records in its own systems. CEX trades are not necessarily public blockchain transactions.

**Circuit breaker** — Tenant control that prevents new execution within a tenant, strategy, portfolio, venue, account, network, or instrument scope. It does not guarantee cancellation of already-submitted activity.

**Deployment-wide emergency stop** — Out-of-band operator control that prevents new live signing and venue submission across one deployed Hermes environment. It is distinct from tenant circuit-breaker API records and cannot cancel activity already accepted by a venue.

**Client order ID** — Stable identifier sent to a venue to correlate and deduplicate an order.

**Consensus** — Deterministic calculation of quorum, support, weighted confidence, opposition, and abstention across eligible agents.

**Consensus policy** — Versioned thresholds and agent weights used by the consensus engine.

**Correlation ID** — Identifier linking API, job, decision, execution, venue, and audit activity for one workflow.

**Custody** — Control or possession of assets or keys. Hermes separately documents key ownership and transaction authority because a delegated signer may have authority without receiving a raw private key.

## D

**Data quality** — Agent- or snapshot-level measure of completeness, freshness, consistency, and source reliability under a documented method.

**Decision** — Accepted or rejected consensus result tied to a snapshot and policy version.

**Dedicated deployment** — Single-tenant application, data, queue, secret, and observability stack.

**Delegated policy wallet** — User- or customer-owned wallet that grants a signer limited, revocable authority under a policy.

**DEX (Decentralized Exchange)** — On-chain protocol or router that executes through smart contracts or chain programs.

**Drawdown** — Decline from a prior portfolio peak, measured under a specified valuation and time method.

## E

**Economic idempotency** — Guarantee that one accepted analytical/risk action creates no more than one intended economic effect, despite retries or duplicate jobs.

**Evidence bundle** — Manifest of snapshot, assessment, consensus, risk, approval, signer, venue, fill, reconciliation, code, and policy evidence for an execution.

**Execution** — Lifecycle from risk request through order intent, signing, submission, fill/finality, and reconciliation.

**Execution authority** — Ability to cause an order or transaction. This may exist through a wallet delegation or CEX API key even without raw-key access.

## F

**Fail closed** — Rejecting or pausing execution when required data, policy, identity, signer, or venue state is missing, stale, ambiguous, or unavailable.

**Fill** — Venue-confirmed executed quantity and price, including fee and time evidence.

**Finality** — Policy threshold at which on-chain state is treated as sufficiently irreversible. Confirmation is not always finality.

**Fractional Kelly** — Position-size heuristic derived from an estimated edge and payoff distribution, multiplied by a fraction. It requires uncertainty controls and cannot expand hard exposure limits.

## H

**HSM (Hardware Security Module)** — Hardware or managed service designed to protect cryptographic keys and perform constrained operations without exporting key material.

## I

**Idempotency key** — Client-supplied identifier for a mutating API request. Reuse with the same canonical request replays the original result; reuse with a different request conflicts.

**Immutable snapshot** — Time-bounded data record that is never edited after capture. A refresh creates a new identifier.

**Instrument** — Canonical traded pair or contract, distinct from a venue-specific symbol.

## J

**JWT (JSON Web Token)** — Signed token used to convey authentication claims. The backend verifies signature, issuer, intended audience/application, expiry, and required claims.

## K

**KMS (Key Management Service)** — Managed system for creating, protecting, and using cryptographic keys under policy.

## L

**LLM (Large Language Model)** — Probabilistic model that may be used by an analytical agent. LLM output is untrusted and has no direct execution authority.

**Liquidity multiple** — Available relevant liquidity divided by proposed order size under a defined methodology.

## M

**Managed multi-tenant deployment** — Hosted stack serving multiple tenants with server-derived authorization and enforced tenant boundaries.

**MEV (Maximal Extractable Value)** — Value extracted through transaction ordering, insertion, or censorship by block producers or searchers.

**MPC (Multi-Party Computation)** — Cryptographic technique in which parties jointly perform a signing operation without reconstructing one complete key in a single party.

## N

**NAV (Net Asset Value)** — Portfolio assets minus liabilities under a defined valuation method and timestamp.

**nATR (Normalized Average True Range)** — ATR divided by a reference price, producing a relative volatility measure. It is not a standalone protection guarantee.

**Nonce/account sequence** — Monotonic value used by a blockchain account to order or prevent replay of transactions.

## O

**OHLCV** — Open, high, low, close, and volume market data for a period.

**Opposition weight** — Eligible agent weight assigned to the directional action conflicting with the consensus candidate.

**Order intent** — Immutable, risk-approved economic instruction for one venue and validity interval.

## P

**Position limit** — Maximum permitted exposure to an asset, instrument, issuer, venue, chain, or correlated group.

**Price impact** — Estimated change in executable price caused by the order itself, distinct from general slippage.

**Principal** — Internal immutable identity mapped from an external authentication subject.

**Prompt version** — Identifier for the exact prompt template and configuration used by an LLM-based agent.

## Q

**Quorum weight** — Eligible agent weight divided by all enabled agent weight. It measures participation, not directional agreement.

## R

**Reconciliation** — Comparison of internal state with authoritative venue, chain, fill, fee, balance, position, nonce, and allowance records.

**Reorganization (reorg)** — Replacement of previously observed blockchain history by another canonical chain branch.

**RLS (Row Level Security)** — Postgres policy mechanism that restricts which rows a role may access. Hermes uses forced RLS as defense in depth and does not use bypass roles for ordinary requests.

**RPC provider** — Service exposing blockchain node methods. Production policies may require agreement among multiple RPC providers.

## S

**Secret reference** — Opaque identifier used to retrieve a secret from an authorized secret manager. It is not the secret value.

**Self-hosted deployment** — Stack operated by the customer or user, including data, credentials, signer, monitoring, and legal obligations.

**Signer** — Isolated system that validates a complete signing envelope against independent policy and returns a signature or operation identifier without returning a private key.

**Signing envelope** — Expiring, anti-replay request containing exact transaction semantics, policy/evidence digests, and authorization context.

**Slippage** — Difference between a reference or expected price and actual execution price under a defined measurement. It is distinct from price impact and spread.

**Snapshot** — Immutable record of market, portfolio, source-quality, and contextual data used for a decision.

**StepShield** — Product name for the Hermes circuit-breaker subsystem. It is not a predictive model and cannot atomically halt independent venues.

**Support weight** — Fraction of eligible agent weight assigned to the candidate action.

## T

**Tenant** — Customer or organizational security boundary. Tenant identity is established by server-side membership, not a client ownership field.

**Transaction authority** — Permission to cause a blockchain transaction or exchange order, whether through user approval, delegation, signer policy, or API credential.

**Trust boundary** — Interface where data or authority moves between components with different security assumptions.

## V

**Venue adapter** — Versioned integration that normalizes one exchange, DEX/router, blockchain, or paper venue and implements its precision, idempotency, lifecycle, and reconciliation behavior.

**Venue registry** — Validated configuration of approved venues, environments, instruments, contracts/programs, credentials/signers, limits, and finality.

**Vibe Flow** — Retired marketing term. Use **audit event stream** or **operational telemetry**, depending on meaning.

**VIX** — Cboe Volatility Index. It may be one contextual macro input but is not a universal or atomic execution kill switch.

## W

**Weighted confidence** — Sum of supporting agent weight multiplied by confidence and data quality, divided by eligible weight. It is not a probability of profit unless separately calibrated and documented.

**WORM storage** — Storage configured to prevent modification or deletion for a defined retention period.
