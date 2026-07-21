# Antigravity Execution Specification

**Version:** 1.0.0-draft  
**Last revised:** 2026-07-20  
**Status:** Normative design; implementation conformance not yet verified

This specification defines the safety-critical behavior of the Hermes execution pipeline. The detailed protocol is in [docs/ExecutionProtocol.md](docs/ExecutionProtocol.md), and the authoritative HTTP schema is in [openapi/hermes.openapi.yaml](openapi/hermes.openapi.yaml).

The key words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** describe normative requirements.

## 1. Invariants

1. An analytical agent MUST NOT call a venue or signer directly.
2. Every decision MUST reference an immutable, time-bounded market snapshot.
3. Consensus MUST be computed from schema-valid, eligible assessments by a deterministic function and a versioned policy.
4. Consensus scores MUST be labeled as agreement metrics, not probabilities of profit.
5. A deterministic risk engine MUST independently approve every order intent.
6. Live execution MUST fail closed on stale data, missing balances, ambiguous venue state, unavailable risk state, or an active circuit breaker.
7. Every mutating operation MUST be idempotent within its documented scope.
8. A signing request MUST contain a complete, immutable signing envelope and MUST expire.
9. The signer MUST enforce a policy independent of the reasoning service.
10. Venue acknowledgements, fills, chain receipts, and account balances MUST be reconciled before an execution is treated as complete.
11. Audit records MUST be append-only to application roles and linked through deterministic hashes. Each tenant stream MUST have exactly one root, every non-root predecessor MUST exist in the same tenant stream, and each predecessor MUST have at most one successor. Digest correctness and collection completeness MUST be independently verified.
12. Tenant identity MUST be derived from verified server-side authorization context, never from a client-supplied owner or tenant field.
13. Decimal quantities and monetary values MUST use deterministic decimal arithmetic and canonical serialization; binary floating-point MUST NOT decide a limit or threshold.
14. An ambiguous submission MUST be reconciled before any retry that could create a second economic effect.
15. Live execution MUST remain disabled until the release gates are evidenced and an authorized operator explicitly enables the approved scope.

## 2. Canonical processing and state binding

The processing order is:

```text
capture snapshot
  -> collect and validate assessments
  -> compute deterministic consensus
  -> refresh authoritative portfolio and venue state
  -> evaluate deterministic risk policy
  -> create an immutable order intent
  -> obtain any required approval bound to that intent
  -> authorize, submit, observe, and reconcile
  -> seal the evidence bundle
```

This sequence describes processing responsibilities; its labels are not persisted execution states. The canonical execution-state names are the `ExecutionState` enum in [OpenAPI](openapi/hermes.openapi.yaml), and the only permitted transitions are those in [Execution Protocol](docs/ExecutionProtocol.md#11-order-and-execution-state-machine). The database enum, API enum, implementation, and protocol transition table MUST remain aligned to the same protocol version.

Every transition MUST validate the expected prior state using row locking or optimistic concurrency. Unknown, duplicate, stale, or out-of-order events MAY be retained as evidence but MUST NOT create an invalid transition or regress a terminal state. A state or transition mismatch between normative artifacts is a release-blocking specification defect; implementations MUST fail closed rather than infer a transition.

Only `RECONCILED` represents successful execution completion. `CONSENSUS_REJECTED`, `RISK_REJECTED`, and `REJECTED` are terminal non-execution outcomes and MUST NOT be presented as successful execution. `CANCELLED` MUST proceed to reconciliation; `EXPIRED` and `FAILED` MUST do so whenever venue activity may have occurred.

## 3. Canonical evidence bundle

A completed execution MUST be reproducible from:

- tenant, strategy, portfolio, instrument, and venue identifiers;
- market snapshot and source digests;
- eligible and excluded agent assessments;
- consensus policy and result;
- risk policy, portfolio state, rule outcomes, and result;
- approval evidence where required;
- signing envelope, signer policy reference, and signature or credential-operation digest;
- venue request, acknowledgement, transaction hash or client order identifier;
- fills, fees, receipts, finality state, and reconciliation result;
- application version, source commit, configuration versions, timestamps, actor identities, and correlation identifiers.

The bundle hash is tamper-evidence only. It is not a zero-knowledge proof, an independent audit, or proof that a trade was profitable.

## 4. Conformance

A deployment is conformant only when all mandatory controls in the architecture, execution, security, API, deployment, and operations documents are implemented and tested, their versioned state and enum contracts agree, and the required evidence is retained. Marketing language MUST NOT imply conformance before the evidence is available.
