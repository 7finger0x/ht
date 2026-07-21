# Hermes: Policy-Controlled Multi-Agent Trading Infrastructure

**Version:** 1.0.0-draft  
**Last revised:** 2026-07-20  
**Status:** Technical overview of an experimental system; implementation conformance not yet independently verified

## Abstract

Hermes is an experimental software architecture for researching and automating digital-asset trading workflows. It combines reproducible market snapshots, multiple structured analytical agents, deterministic consensus, deterministic risk controls, isolated wallet or exchange authority, venue-specific execution, and continuous reconciliation.

The design addresses a central weakness of model-driven automation: analytical output should not itself possess execution authority. Hermes therefore treats model or agent output as untrusted opinion. A separate consensus function determines whether a sufficiently broad and explicit agreement exists; a deterministic risk engine decides whether an order is permitted; and an isolated signer or exchange credential adapter independently constrains the final venue request.

Hermes does not claim guaranteed profitability, complete decentralization, regulatory compliance by design, atomic shutdown across independent venues, zero-knowledge proof of reasoning, or institutional suitability without deployment-specific evidence and assurance.

## 1. Problem statement

Automated digital-asset trading combines several difficult systems:

- fragmented and time-sensitive market data;
- probabilistic or heuristic analytical models;
- portfolio and liquidity risk;
- irreversible or difficult-to-cancel execution;
- public blockchains and centralized counterparties;
- credentials capable of causing financial loss;
- multi-tenant data and authorization requirements;
- complex reconciliation after timeouts, partial fills, or chain events.

A single model response is not an adequate control plane. Even multiple models can share correlated errors, stale inputs, or common provider dependencies. Agreement must therefore be measured precisely and treated only as one prerequisite for a deterministic authorization process.

## 2. Design thesis

Hermes is built around six separations:

1. **Snapshot from analysis:** every agent evaluates the same immutable, time-bounded evidence.
2. **Assessment from consensus:** agent outputs are schema-valid records; a deterministic function calculates explicit agreement metrics.
3. **Consensus from risk:** agreement does not authorize capital. A rules engine evaluates current portfolio, market, venue, and policy state.
4. **Risk from signing:** application approval does not expose a private key. A signer or credential adapter independently enforces authority limits.
5. **Submission from completion:** acknowledgement or transaction broadcast is not a fill or final settlement. Reconciliation determines terminal state.
6. **Operation from evidence:** every stage records versioned, hash-linked evidence that can be replayed and reviewed.

## 3. Canonical architecture

Hermes supports three deployment modes:

- **Managed multi-tenant:** a hosted control plane with enforced tenant boundaries and explicitly disclosed operator data processing and transaction authority.
- **Dedicated single-tenant:** an isolated stack, preferably with customer-managed identity, signer, and secret infrastructure.
- **Self-hosted:** the customer operates the entire stack and controls its data, credentials, monitoring, and legal obligations.

Deployment mode is separate from signing mode. On-chain execution may be user-in-loop, delegated under a policy, or authorized by a customer-managed HSM/MPC/KMS/signer. CEX execution uses trading-only API credentials with withdrawals disabled under the baseline design.

The architecture is documented in [Architecture](Architecture.md).

## 4. Reproducible analytical pipeline

### 4.1 Snapshot capture

A decision begins with a snapshot containing price, quote, liquidity or order-book data, volatility, portfolio state, source timestamps, sequence numbers or block heights, quality flags, and a canonical digest. Optional macroeconomic or narrative features are referenced by source and time.

Stale, divergent, missing, or ambiguous data makes the snapshot ineligible. A snapshot is immutable; refresh creates a new record.

### 4.2 Structured agents

Technical, macro, narrative, statistical, or other agents return the same schema:

- action: `BUY`, `SELL`, `HOLD`, or `ABSTAIN`;
- confidence and data quality;
- validity interval;
- concise rationale;
- provider, model, prompt, and agent versions;
- input and output digests.

Agents cannot access trading credentials, signers, venue APIs, tenant databases, or internal tools. Invalid or timed-out output becomes `ABSTAIN`.

The architecture is provider-neutral. Gemini, Perplexity, or another provider may be configured, but no provider is a protocol requirement.

### 4.3 Deterministic consensus

The Antigravity consensus function reports separate metrics:

- enabled and eligible agent count;
- quorum weight;
- support weight for the candidate action;
- confidence- and quality-weighted support;
- directional opposition;
- abstention.

An illustrative simulation policy requires three eligible agents, 75% eligible weight, 80% support, 60% weighted confidence, no more than 15% directional opposition, and no more than 25% abstention. These are policy settings, not a claim that an accepted trade has an 80% probability of profit.

Weights are versioned and changed through offline evaluation and approval. Agents do not alter their own production weights.

## 5. Deterministic risk authorization

After consensus, the risk engine refreshes authoritative portfolio and venue state. Every mandatory rule returns `PASS`, `FAIL`, or `UNKNOWN`; `FAIL` or `UNKNOWN` denies the order.

Control categories include:

- live-mode and role authorization;
- snapshot, quote, portfolio, and clock freshness;
- venue, asset, chain, router/program, recipient, and order-type allowlists;
- maximum order notional and NAV fraction;
- position, concentration, gross/net exposure, leverage, daily loss, and drawdown;
- liquidity, spread, slippage, price impact, and fee limits;
- precision, lot, tick, and minimum-notional constraints;
- balance, margin, gas, allowance, nonce/sequence, and finality;
- venue health, rate limits, pending orders, and unresolved reconciliation;
- human approval and circuit-breaker state.

The approved quantity is the minimum permitted by all rules and is rounded down to venue precision. Analytical suggestions cannot expand a hard limit.

`StepShield` is the name of the tenant circuit-breaker subsystem. It can prevent new execution at tenant, strategy, portfolio, venue, account, network, or instrument scope. A separate deployment-wide emergency stop blocks new signing/submission across an operated environment. Neither mechanism can atomically cancel activity already accepted by independent blockchains or exchanges.

## 6. Idempotent execution

Every mutating API request has an idempotency key and canonical request digest. Replaying the same request returns the original result; changing the body under the same key returns a conflict.

A separate economic identifier binds tenant, strategy, decision, risk evaluation, venue, and order leg. Database uniqueness prevents two intents for one economic action.

CEX adapters use stable client order IDs and query after a timeout before retrying. DEX adapters bind the economic intent to a signed transaction or user operation and manage nonce/account sequence, replacement, finality, and reorganization explicitly.

The state machine distinguishes accepted, risk-rejected, approval-pending, signing, submitting, ambiguous, acknowledged, partially filled, confirmed, finalized, cancelled, failed, and reconciled states. A timeout is never silently interpreted as a failed submission.

## 7. Isolated transaction authority

A signing envelope contains the exact chain, wallet, contract/program, method/instruction, recipient, assets, quantity, minimum received, fees, nonce, deadline, risk digest, approval digest, and anti-replay value. The signer authenticates the request and enforces an independent policy before producing a signature.

For delegated wallets, the user or customer grants explicit, visible, revocable authority. The operator may be able to cause transactions within that policy even though it never receives the raw private key. This is described as delegated transaction authority rather than simply “self-custody.”

For CEX accounts, the credential adapter has trading and query authority only. Withdrawals and transfers are disabled under the baseline policy. The exchange remains an independent custodian and counterparty.

## 8. Reconciliation and audit evidence

Venue state is authoritative for CEX orders and fills. Canonical chain state is authoritative for DEX settlement and finality. Hermes continuously compares:

- internal intent and state;
- venue acknowledgements and order IDs;
- transactions, replacements, receipts, and confirmations;
- partial and final fills;
- fees;
- positions, balances, nonces, and allowances.

An execution becomes `RECONCILED` only when required authoritative state agrees. Ambiguous or mismatched state activates a scoped breaker.

Audit events record actor, action, result, resource, correlation, code/configuration versions, evidence references, payload digest, and previous-event digest. Independent retention or optional public-chain anchoring can strengthen tamper evidence. A hash chain is not by itself proof of completeness, correctness, or regulatory compliance.

## 9. Privacy and tenant isolation

The hosted service processes identity, tenant, configuration, security, trading, and operational data. It does not claim to be local-only or to avoid all IP processing.

The browser accesses trading data through the authenticated API. The API maps an identity-provider subject to an internal principal and active tenant membership. Database transactions set server-derived tenant and principal context. Tenant tables use forced RLS, and application roles cannot bypass it or own the tables.

The database stores secret references, not secret values. Raw model prompts/responses are not retained in managed production by default. DEX transaction data is public and generally permanent; CEX order activity is private to the exchange/account and is not necessarily on-chain.

Detailed disclosures are in [Privacy Policy](../PRIVACY.md) and [Data Inventory](DataInventory.md).

## 10. Security and operational assurance

The security baseline covers token verification, least privilege, database isolation, secret management, wallet delegation, CEX permissions, software supply chain, logging, monitoring, incident response, and backup/restore.

Operational runbooks address security incidents, stale data, venue outages, ambiguous orders, blockchain failures, recovery, and model changes. Live execution is a gated production capability rather than the default state.

A deployment should not be represented as institutional-grade, verified, audited, compliant, or secure without current evidence such as code conformance, venue tests, restore exercises, security assessment, control operation, and contract/legal review.

## 11. Evaluation methodology

Any performance report should publish at least:

- strategy and instrument scope;
- dataset sources, timestamps, quality exclusions, and survivorship treatment;
- training, validation, and out-of-sample periods;
- model, prompt, agent, consensus, and risk versions;
- fees, spread, slippage, price impact, gas, funding, borrow, and taxes considered;
- latency and venue-capacity assumptions;
- rejected and abstained decisions;
- maximum drawdown, volatility, turnover, exposure, and tail behavior;
- comparison baseline;
- statistical uncertainty and multiple-testing controls;
- live versus simulated results;
- conflicts and limitations.

Backtests and paper trading do not guarantee live performance. Marketing should not describe an action as “high probability” without a defined, calibrated probability and supporting evidence.

## 12. Current status and roadmap

The earlier roadmap listed 2024 Q3, 2024 Q4, and 2025 Q1 milestones without implementation evidence in the supplied documentation. Those dates are retired rather than presented as completed.

| Phase | Status as of 2026-07-20 | Exit evidence |
|---|---|---|
| Canonical architecture and documentation | **Design complete in this package; code conformance unverified** | Approved architecture, legal/security review, source mapping |
| Simulation and deterministic replay | **Implementation evidence required** | OpenAPI/schema conformance, historical replay, property tests, paper venue reconciliation |
| Security and recovery readiness | **Implementation evidence required** | RLS tests, signer controls, incident game day, backup restore, vulnerability review |
| Limited live pilot | **Not approved by documentation alone** | Low-notional scope, sandbox/mainnet adapter review, approvals, monitored reconciliation |
| Dedicated institutional deployment | **Future capability subject to contract and assurance** | Isolated stack, customer signer, SLO/DR evidence, external assessment |
| Cryptographic proof research | **Research backlog** | Formal statement, implemented proof system, verifier, threat model, independent review |

Targets should be assigned only after engineering owners, dependencies, and test capacity are confirmed.

## 13. Limitations

Hermes cannot eliminate:

- market loss, adverse selection, venue insolvency, or regulatory change;
- correlated model error or data-provider compromise;
- chain congestion, MEV, reorganization, contract or token risk;
- exchange cancellation and fill races;
- all credential or operator compromise;
- the permanence and linkability of public-chain data;
- the need for deployment-specific legal, tax, security, and operational review.

## 14. Conclusion

Hermes is best understood as a control architecture for model-assisted trading, not as an autonomous oracle. Its central claim is architectural: analytical systems should produce bounded, reproducible evidence, while deterministic policy and isolated authority decide whether and how an order can be executed. Whether a deployment is safe, effective, or suitable depends on implementation, configuration, testing, operation, and independent review.
