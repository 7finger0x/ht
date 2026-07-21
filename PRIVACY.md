# Hermes Privacy Policy

**Status:** Draft for legal and operational review  
**Last revised:** 2026-07-20  
**Proposed effective date:** July 20, 2026  
**Operator:** Hermes Protocol Foundation  
**Contact:** privacy@hermes-protocol.org  
**Address:** P.O. Box 309, Ugland House, Grand Cayman, KY1-1104, Cayman Islands

> **Publication requirement:** Verify every provider and retention period against the production deployment, publish a subprocessor register, and obtain jurisdiction-specific legal review before relying on this policy.

## 1. Scope

This Privacy Policy explains how Hermes Protocol Foundation (“Hermes,” “we,” “us,” or “our”) processes information when it operates the Hermes hosted service, website, application programming interface, and related support services (the “Hosted Services”).

Hermes may also be deployed as dedicated or self-hosted software:

- In a **dedicated deployment**, the customer contract identifies which party controls each category of information. The customer will generally control trading and user data when the system runs in its environment.
- In a **self-hosted deployment**, the person or organization operating the system determines the data processing. We do not receive self-hosted deployment data unless the operator enables a service that sends data to us or asks us for support.

This Policy does not govern independent processing by exchanges, wallet providers, blockchains, RPC providers, identity providers, market-data providers, AI providers, or other third parties. Their own terms and privacy notices apply.

## 2. Architecture and transaction authority

Hermes is not a single local-only application. The Hosted Services process account, configuration, market, trading, security, and operational data in managed infrastructure.

Supported transaction-authority models include:

- **User-in-loop wallet:** the user authorizes each transaction.
- **Delegated policy wallet:** a user or customer authorizes a Hermes-controlled signer to initiate transactions within a defined, revocable policy. We do not need to receive the raw private key to exercise that delegated authority.
- **Customer-managed signer:** a customer-controlled HSM, KMS, MPC service, or signer approves requests from Hermes.
- **CEX API credential:** Hermes may place and cancel orders in a linked exchange account using a trading-enabled API credential. Under the baseline configuration, withdrawals must be disabled.

The active model is displayed or documented during setup. Additional details are in [Canonical Architecture](docs/Architecture.md#4-custody-and-transaction-authority).

## 3. Information we process

### 3.1 Account and identity information

We may process an internal user identifier, identity-provider identifier, email address, phone number, wallet address, display name, tenant membership, role, account status, and authentication timestamps. The exact claims depend on the configured identity provider and login method.

### 3.2 Configuration and business information

We process tenant details, team memberships, strategies, instruments, venue configuration, risk policies, approval rules, wallet metadata, public addresses, exchange/account references, and support preferences.

### 3.3 Trading and financial activity

We process market snapshots, balances, positions, exposure, net asset value inputs, open orders, consensus decisions, risk evaluations, approvals, order intents, exchange order identifiers, blockchain transaction hashes, fills, prices, fees, and reconciliation records.

Hermes does not treat CEX order execution as public blockchain activity. CEX orders and fills generally remain in the exchange’s systems. DEX transactions are submitted to public networks and become publicly visible.

### 3.4 Wallet and exchange credentials

Hermes application databases store references and metadata for credentials, not raw secret values. Depending on the deployment, secret material is held by a wallet provider, HSM/MPC/KMS, customer signer, or dedicated secret manager.

The Hosted Services may use a delegated signer or CEX credential to cause transactions or orders within the configured authority. Raw wallet private keys and seed phrases must not be stored in ordinary application environment files, databases, logs, prompts, or browser code.

### 3.5 Analytical and AI data

We may send minimized market, macroeconomic, technical, or news context to analytical providers selected for the deployment. Requests are designed to exclude access tokens, private keys, exchange secrets, support records, and direct account identifiers.

Public news or narrative content may contain personal information about people discussed in that content and is not necessarily anonymous. In managed production, Hermes does not retain full AI prompts and responses by default. It normally retains structured assessments, redacted rationale summaries, provider/model identifiers, prompt versions, latency/usage metrics, and content digests. Approved diagnostic capture may retain raw payloads for up to seven days in an isolated store.

### 3.6 Device, network, and usage information

When a person uses the Hosted Services, we and our infrastructure providers necessarily process connection and request information such as IP address, user agent, timestamps, request identifiers, page or API activity, performance metrics, error data, and security signals. We use this information for service delivery, authentication, abuse prevention, rate limiting, reliability, and incident investigation.

We do not claim that the Hosted Services avoid all IP-address processing. We seek to minimize routine storage and may use truncated addresses, keyed hashes, or provider-generated risk signals where sufficient.

### 3.7 Support, legal, and billing information

We process information submitted in support requests, diagnostic attachments, contract and acceptance records, billing contacts, invoice data, and records needed to administer our relationship or comply with law.

## 4. How we use information

We use information to:

- authenticate users and enforce tenant roles;
- provide dashboards, strategies, decisions, execution, reconciliation, and audit exports;
- operate wallet delegation, customer signers, and exchange integrations;
- apply deterministic consensus, risk, approval, and circuit-breaker rules;
- secure the service, detect abuse, investigate incidents, and prevent duplicate orders;
- monitor reliability, diagnose errors, restore service, and test changes;
- respond to support requests and communicate material service or security notices;
- administer contracts, billing, taxes, and legal obligations;
- improve the service using aggregated or de-identified operational information where permitted.

We do not use raw private keys or exchange secrets to train analytical models. We do not sell personal information for money. The Foundation does not sell or share personal data for targeted advertising or third-party marketing.

## 5. Legal bases

Where a legal basis is required, we process information as necessary to perform a contract, take requested pre-contract steps, protect legitimate interests in operating and securing the service, comply with legal obligations, protect rights and safety, or obtain consent where required.

The applicable basis depends on the data, purpose, deployment, and jurisdiction. Customers are responsible for identifying their own basis when they control information in a dedicated or self-hosted deployment.

## 6. How we disclose information

We disclose information only as needed to:

- hosting, database, storage, queue, monitoring, email, support, and security providers;
- identity and wallet providers;
- configured AI, market-data, news, macroeconomic-data, and RPC providers;
- blockchains, DEX protocols, routers, relays, and validators when a transaction is submitted;
- centralized exchanges when an order or account request is submitted;
- professional advisers, auditors, insurers, acquirers, and financing parties subject to appropriate protections;
- authorities or other parties when required by law or reasonably necessary to protect rights, safety, or service integrity;
- a customer organization that administers the user’s tenant.

A current production subprocessor register must identify the providers actually used, their purposes, and available location information: https://hermes-protocol.org/subprocessors.

## 7. Public blockchain information

Public blockchains are transparent and generally immutable. A transaction may reveal wallet addresses, contracts or programs, token types and amounts, fees, timing, and transaction data. Other parties may associate this data with a person or organization using information outside Hermes.

We cannot delete, correct, or control data confirmed on a public blockchain. Requests concerning our indexed copies do not remove the underlying public record.

## 8. Retention

Baseline managed-service retention is described in [Data Inventory](docs/DataInventory.md). Unless a different contract, legal hold, or law applies:

| Category | Baseline retention |
|---|---|
| Account and active configuration | Account or contract life plus 30 days |
| Session and routine security metadata | 180 days; up to one year after an incident |
| Detailed operational logs | 30 days |
| Operational metrics | Up to 13 months |
| Raw AI diagnostic payloads | Disabled by default; maximum seven days when approved |
| Market snapshots not tied to a decision | 90 days |
| Decisions, risk results, approvals, orders, fills, reconciliation, and audit records | Seven years |
| Support records | Two years after closure unless deletion or longer retention is appropriate |
| Secret material | Only while active, then destroyed subject to encrypted backup expiry |

We retain data longer when required for a legal obligation, dispute, fraud/security investigation, or documented legal hold. Encrypted backups expire under their rotation schedule and are not routinely edited; deletion controls are replayed after a restore.

## 9. Security

We use administrative, technical, and physical measures intended to protect information, including role-based access, environment separation, forced tenant policies in the database, encryption in transit, managed secret storage, isolated signing, audit logging, vulnerability management, backup testing, and incident procedures.

No system is completely secure. Users and customers must protect their accounts, devices, wallets, identity-provider sessions, exchange credentials, and recovery methods and must promptly report suspected compromise.

## 10. International processing

Our providers and customers may process information in countries other than the user’s location. Where required, we use contractual or other recognized transfer mechanisms and provide additional information through the applicable contract or subprocessor register.

## 11. Choices and rights

Depending on location and applicable law, a person may have rights to access, correct, delete, restrict, object to, or receive a portable copy of personal information, or withdraw consent. A person may also have the right to complain to a data-protection authority.

Submit requests to privacy@hermes-protocol.org. We may verify identity and authority before responding. A tenant administrator may be the appropriate contact when an organization controls the account. We may retain information where permitted or required, including transaction, security, accounting, dispute, and audit records. Public blockchain data cannot be deleted by Hermes.

Users can also:

- revoke wallet delegations through the documented wallet controls;
- revoke exchange credentials through the exchange and Hermes configuration;
- disable optional analytics or diagnostic capture where the deployment provides that control;
- close an account, subject to reconciliation and retention obligations.

## 12. Cookies and analytics

The production operator must publish an accurate cookie and analytics notice. Strictly necessary storage may be used for authentication, security, preferences, and load balancing. Optional analytics, advertising, or cross-site tracking must not be enabled without the notice and consent required by applicable law.

The mere presence of Vercel or another hosting provider does not determine the final disclosure; the enabled product configuration does.

## 13. Children

The Hosted Services are not directed to children and are intended only for persons legally able to enter the Terms and use the relevant trading services. We do not knowingly offer the Hosted Services to anyone below the minimum age specified in the Terms or applicable law.

## 14. Changes

We may update this Policy to reflect changes in the service, providers, law, or practices. We will update the revision date and provide additional notice when required. Material changes do not retroactively expand wallet or exchange authority; changes to transaction authority require the authorization process documented in the product.

## 15. Contact

Hermes Protocol Foundation  
P.O. Box 309, Ugland House, Grand Cayman, KY1-1104, Cayman Islands  
privacy@hermes-protocol.org  
Data Protection Officer: dpo@hermes-protocol.org
