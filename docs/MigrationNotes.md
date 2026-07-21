# Documentation Migration Notes

**Last revised:** 2026-07-20

This package replaces the prior draft documentation with one canonical architecture and vocabulary.

## 1. Canonical file mapping

| Previous file | Canonical replacement | Disposition |
|---|---|---|
| `README(1).md` | `README.md` | Rewritten; links repaired and implementation status added |
| `Architecture(1).md` | `docs/Architecture.md` | Rewritten around deployment, identity, custody, data, and trust boundaries |
| `APIReference.md` | `openapi/hermes.openapi.yaml` and `docs/APIReference.md` | Replaced with OpenAPI-backed contract |
| `DeploymentGuide.md` | `docs/DeploymentGuide.md` | Rewritten with secret classes, exact roles, release gates, and rollback |
| `OperationsManual.md` | `docs/OperationsManual.md` and `runbooks/` | Rewritten with SLO/RPO/RTO objectives, alerts, reconciliation, and runbooks |
| `SecurityPolicy.md` | `docs/SecurityPolicy.md` and `SECURITY.md` | Rewritten with threat model, token verification, RLS, signing, and incident controls |
| `PRIVACY.md` | `PRIVACY.md` | Rewritten for managed, dedicated, and self-hosted processing |
| `TERMS.md` | `TERMS.md` | Rewritten for transaction authority and third-party/market risks; legal placeholders retained |
| `InstitutionalWhitepaper.md` and `WHITEPAPER.md` | `docs/Whitepaper.md` | Consolidated; unsupported claims and expired roadmap removed |
| `Glossary.md` | `docs/Glossary.md` | Corrected and expanded; retired ambiguous marketing terms |
| `ContributionGuidelines.md` | `docs/ContributionGuidelines.md` | Rewritten with safety-critical tests and release controls |

## 2. Architectural changes

- The system is no longer described simultaneously as local-only, managed multi-tenant, and decentralized. It has three explicit deployment modes.
- Wallet ownership is separated from transaction authority.
- The browser no longer directly accesses internal trading tables.
- Privy or OIDC identity is verified by the backend and mapped to an internal principal and tenant membership.
- Application database roles are non-owner, `NOBYPASSRLS`, and subject to forced RLS.
- Service-role/secret database credentials are excluded from ordinary request paths.
- Raw private keys are prohibited from generic `.env` files and application services.
- CEX activity is correctly distinguished from public on-chain execution.
- Bitcoin/BRC-20 execution is removed from baseline scope pending an implemented and reviewed adapter.

## 3. Protocol terminology changes

| Retired or ambiguous term | Canonical term |
|---|---|
| Single `confidence_score` | Quorum weight, support weight, weighted confidence, opposition weight, abstain weight |
| Consensus “proof” as score hash | Decision digest and evidence manifest; optional independent anchoring |
| `Vibe Flow` | Audit event stream or operational telemetry |
| “Atomic” global kill switch | Deployment-wide emergency stop plus tenant-scoped circuit breakers; submitted activity reconciled separately |
| `Sentinel Guard` | Retired umbrella term; use deterministic risk engine and StepShield circuit breakers |
| “All trades are on-chain” | DEX transactions are public; CEX orders/fills remain in exchange systems |
| “Self-custodial” alone | Key ownership plus user-in-loop/delegated/customer-managed transaction authority |
| “Institutional-grade” | Deployment-specific controls and assurance evidence |

## 4. Roadmap correction

The previous 2024 Q3, 2024 Q4, and 2025 Q1 milestones lacked evidence in the supplied documents. They are not marked completed. The consolidated whitepaper uses evidence-gated phases with no invented dates.

## 5. Implementation work still required

The documentation package establishes the target contract but does not prove that application code implements it. Engineering must map each service and database migration to the design, generate or validate FastAPI/Pydantic models against OpenAPI, implement the signer and venue adapters, run integration tests, and produce release evidence.

The legal documents also retain placeholders for operator identity, jurisdiction, contacts, billing, liability, dispute terms, and subprocessor register. They are not ready for publication until completed and reviewed.
