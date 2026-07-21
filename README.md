# Hermes

Hermes is an experimental, policy-controlled system for researching and automating digital-asset trading workflows. It combines market-data ingestion, structured analytical agents, deterministic consensus and risk evaluation, isolated signing, venue adapters, and auditable order reconciliation.

Hermes is **not** described as decentralized, autonomous proof of profitability, or institutional-grade by default. Those properties depend on the deployed components, operating controls, and independent assurance. Multi-agent agreement is an input to execution policy; it is not a forecast guarantee.

## Status

**Documentation release candidate — 2026-07-20.**

This package defines the intended architecture and control contract. It does not establish that an existing codebase conforms to the design. Live trading must remain disabled until the implementation gates in [Architecture](docs/Architecture.md#14-implementation-conformance-gates) and [Deployment Guide](docs/DeploymentGuide.md#15-production-release-gates) are satisfied.

## Canonical deployment modes

| Mode | Operator | Tenant isolation | Signing and credentials | Intended use |
|---|---|---|---|---|
| **Managed multi-tenant** | Hermes service operator | Shared control plane and database with enforced tenant boundaries | User-in-loop or explicitly delegated wallet policies; CEX credentials held in a managed secret store | Hosted evaluation and approved live pilots |
| **Dedicated single-tenant** | Hermes operator or customer | Separate application, database, queue, and observability stack | Customer-managed signer/HSM/MPC preferred; isolated CEX credentials | Institutional or regulated environments |
| **Self-hosted** | Customer | Customer-controlled | Customer-controlled signer and secret store | Research, simulation, and customer-operated production |

The supported custody and authority models are defined in [Architecture](docs/Architecture.md#4-custody-and-transaction-authority).

## System flow

```text
market sources -> immutable snapshot -> structured agent assessments
               -> deterministic consensus -> deterministic risk evaluation
               -> optional human approval -> isolated signer/credential adapter
               -> DEX or CEX venue -> fill and chain reconciliation -> audit evidence
```

The reasoning layer cannot submit orders directly. Only a versioned risk policy can authorize an order intent, and the signer independently enforces its own wallet or credential policy.

## Documentation

- [Canonical architecture](docs/Architecture.md)
- [Data inventory and retention](docs/DataInventory.md)
- [Execution protocol](docs/ExecutionProtocol.md)
- [Security policy](docs/SecurityPolicy.md)
- [Privacy policy](PRIVACY.md)
- [Terms of use](TERMS.md)
- [OpenAPI reference](docs/APIReference.md)
- [OpenAPI 3.1 contract](openapi/hermes.openapi.yaml)
- [Deployment guide](docs/DeploymentGuide.md)
- [Operations manual](docs/OperationsManual.md)
- [Operational runbooks](runbooks/README.md)
- [Consolidated whitepaper](docs/Whitepaper.md)
- [Glossary](docs/Glossary.md)
- [Contribution guidelines](docs/ContributionGuidelines.md)
- [Migration notes from the previous documentation](docs/MigrationNotes.md)
- [Observability standards](docs/ObservabilityStandards.md)
- [API mocking examples](docs/api-mocking-collection.md)
- [SDK generation](docs/sdk-generation.md)
- [Validation report](VALIDATION_REPORT.md)

## Repository contract

The package includes machine-readable controls:

- `openapi/hermes.openapi.yaml` — authoritative HTTP API contract.
- `schemas/*.schema.json` — JSON Schemas for risk policy, venue registry, and audit events.
- `config/*.example.yaml` — simulation-safe example configuration.
- `infra/supabase/migrations/0001_core.sql` — canonical data model and tenant-isolation policies.
- `infra/docker/compose.yaml` — local supporting services for development and contract testing.
- `scripts/validate_package.py` — link, schema, configuration, OpenAPI reference, SQL, and runbook checks.
- `runbooks/runbook-tests.yaml` — executable static control/evidence tests for each operational runbook.

Run the documentation and contract checks with:

```bash
python -m pip install -r requirements-docs.txt
python scripts/validate_package.py
```

With Docker available, run the disposable PostgreSQL role, RLS, tenant-binding, and audit-chain integration gate:

```bash
bash scripts/test_postgres_security.sh
```

These checks validate structure and examples. They do not substitute for integration testing against a deployed API, database, signer, blockchain, or exchange sandbox.

## Safety defaults

- Live execution is disabled by default.
- No wallet private key belongs in a frontend build, repository, generic `.env` file, database row, log, or model prompt.
- CEX API keys must have withdrawals disabled and the minimum trading permissions required.
- Raw LLM responses are not retained in managed production by default.
- Every mutating API request requires an idempotency key.
- Unknown, stale, ambiguous, or unreconciled state fails closed.

## Publication blockers

Before public release, confirm that operator, legal, security, and support text remains current; obtain jurisdiction-specific legal review; add a license; publish a current subprocessor register; and verify code conformance to this documentation.

## License

No software license was supplied with the source documentation. Add an approved `LICENSE` file before distributing code or accepting external contributions.
