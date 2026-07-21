# Hermes Operational Runbooks

Each runbook is an executable operational procedure, not general troubleshooting prose. Before production use, replace bracketed contacts and deployment-specific commands, exercise the procedure in staging or a venue sandbox, and attach the exercise record.

## Required structure

Every runbook contains:

1. Trigger and severity
2. Safety objective
3. Preconditions and authority
4. Immediate containment
5. Diagnosis
6. Recovery
7. Verification
8. Rollback or abort criteria
9. Evidence to preserve
10. Escalation and communications

## Index

| Runbook | Primary condition | Default breaker scope |
|---|---|---|
| [Security incident](incident-security.md) | Credential, tenant, identity, or unauthorized action concern | Deployment-wide stop until scope is known |
| [Stale or divergent market data](stale-market-data.md) | Data freshness, sequence, or source disagreement | Source/instrument/venue |
| [Venue outage](venue-outage.md) | CEX, DEX, RPC, relayer, or provider unavailable | Venue/network |
| [Duplicate or ambiguous order](duplicate-or-ambiguous-order.md) | Timeout, duplicate client ID, uncertain economic effect | Account/instrument |
| [Blockchain transaction failure](blockchain-transaction.md) | Stuck, dropped, replaced, reverted, or reorged transaction | Wallet/network/instrument |
| [Backup and restore](backup-restore.md) | Data loss, corruption, or recovery exercise | Deployment-wide live execution disabled |
| [Model or prompt change](model-change.md) | Analytical provider/model/prompt/weight update | Simulation until approved |

## Exercise cadence

- Security incident and ambiguous order: at least quarterly.
- Backup/restore: at least quarterly.
- Stale data and venue outage: at least semiannually and after adapter changes.
- Blockchain transaction: before each mainnet adapter release and at least semiannually.
- Model change: for every material change.

Use UTC timestamps and never place secrets in the exercise report.

## Automated contract tests

[`runbook-tests.yaml`](runbook-tests.yaml) defines one machine-readable failure scenario for each runbook. The package validator checks the suite against [`../schemas/runbook-test.schema.json`](../schemas/runbook-test.schema.json), verifies one-to-one runbook coverage, and confirms required containment and evidence anchors are present.

These automated checks are not a substitute for operator-led tabletop exercises, sandbox drills, or timed restoration tests. Attach live exercise evidence before production enablement.
