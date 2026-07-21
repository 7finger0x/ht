# Hermes Terms of Use

**Status:** Draft for legal and commercial review  
**Last revised:** 2026-07-20  
**Proposed effective date:** July 20, 2026  
**Provider:** Hermes Protocol Foundation  
**Contact:** legal@hermes-protocol.org

> **Publication requirement:** These Terms are a structured draft, not jurisdiction-specific legal advice. Replace all bracketed provisions, align them with the actual product and commercial model, and obtain qualified legal review before launch.

## 1. Agreement and scope

These Terms of Use (“Terms”) govern access to the Hermes hosted website, application, APIs, documentation, and related services provided by Hermes Protocol Foundation (“Hermes,” “we,” “us,” or “our”) (the “Hosted Services”). By creating an account, accepting an order form, or using the Hosted Services, you agree to these Terms.

Dedicated deployments, enterprise support, professional services, and service levels may be governed by an order form or separate agreement. If an executed agreement conflicts with these Terms, the executed agreement controls for that subject.

Self-hosted software is governed by its applicable software license and any separate support agreement. No software license was supplied with the source documentation; an approved license must be added before distribution.

## 2. Eligibility and authority

You represent that:

- you are at least 18 years old and legally able to enter these Terms;
- you are not subject to sanctions or restrictions that prohibit the service;
- your use is lawful in every jurisdiction that applies to you;
- when acting for an organization, you have authority to bind it;
- you are permitted to use each wallet, exchange account, credential, asset, network, and venue you connect;
- you will obtain any registration, license, approval, or consent required for your activities.

Hermes may restrict countries, persons, assets, venues, or use cases based on legal, security, commercial, or risk considerations. Services are not available to persons or entities located in, organized under, or resident of sanctioned jurisdictions or OFAC-restricted territories.

## 3. Experimental trading software

Hermes is experimental software for analytical and automated trading workflows. The Hosted Services may be incomplete, unavailable, inaccurate, delayed, or changed. Features may be limited to simulation, testnets, sandboxes, or approved pilots.

Multi-agent agreement is not proof that a trade is correct or profitable. Market data, models, prompts, consensus weights, risk rules, venue adapters, and third-party services can fail or produce correlated errors. No threshold, circuit breaker, stop, or position-sizing method guarantees protection from loss.

## 4. No advice or fiduciary relationship

Hermes provides software and information tools. Unless a separate written agreement expressly states otherwise, we do not provide investment, legal, tax, accounting, custody, brokerage, exchange, or fiduciary services or advice. Outputs such as `BUY`, `SELL`, `HOLD`, confidence, risk, or position-size fields are system outputs, not personalized recommendations.

You are responsible for deciding whether and how to trade, for independently reviewing configuration and output, and for obtaining professional advice.

## 5. Accounts and tenant administration

You must provide accurate information, protect authentication methods, use multi-factor or step-up authentication where offered, and promptly notify us of suspected compromise.

A tenant administrator may invite users, assign roles, configure wallets and venues, approve policies, and access tenant records. You are responsible for your administrators and users and for removing access promptly when it is no longer required.

You must not share accounts, bypass access controls, submit another tenant’s identifier, or attempt to obtain data or authority outside your tenant.

## 6. Deployment and transaction-authority models

Hermes supports different architectures. The selected order form, setup screen, or deployment record identifies the applicable model.

### 6.1 User-in-loop wallet

Hermes may prepare a blockchain transaction, but the user must authorize the exact transaction through the wallet. You are responsible for reviewing network, recipient, contract or program, asset, quantity, minimum received, fees, and transaction data before approval.

### 6.2 Delegated policy wallet

You may grant a Hermes-controlled signer permission to initiate transactions from a wallet within a defined policy. That permission can allow the Hosted Services to cause transactions without an approval prompt for each transaction. The delegation may constrain contracts, recipients, assets, methods, quantities, rates, time periods, and other attributes.

You are responsible for reviewing and revoking delegations. We are responsible for using delegated authority only through the documented service and configured policy. The absence of raw private-key access does not mean that we lack transaction authority while a delegation is active.

### 6.3 Customer-managed signer

A customer signer, HSM, KMS, MPC service, or approval workflow may authorize requests from Hermes. You are responsible for the signer’s availability, policy, key management, and approvals unless a separate agreement assigns those duties to us.

### 6.4 Centralized exchange credentials

When you connect an exchange API credential, the Hosted Services may place, cancel, query, and reconcile orders within its permissions. The baseline configuration requires withdrawal and transfer permissions to be disabled. You must verify permissions at the exchange, use a dedicated subaccount where practical, and apply IP or other restrictions where supported.

We do not control exchange matching, custody, insolvency, maintenance, freezes, compliance decisions, data retention, or withdrawals. An exchange may execute an order even if Hermes times out or a cancellation is pending.

### 6.5 Self-hosted deployments

For self-hosted software, you operate the infrastructure, database, signer, credentials, backups, monitoring, security, and legal notices. We do not have access to those systems unless you grant access or send information through support or an enabled external service.

## 7. Configuration and risk responsibility

You are responsible for:

- selecting simulation or live mode;
- configuring instruments, venues, wallets, accounts, models, strategies, and schedules;
- establishing order, exposure, leverage, loss, drawdown, liquidity, slippage, fee, finality, and approval limits;
- confirming data sources, token and contract identities, decimals, symbol mappings, and venue precision;
- monitoring balances, allowances, margin, fees, open orders, pending transactions, and system health;
- responding to alerts and reconciling records independently where appropriate;
- testing changes before live use.

Hermes may enforce hard platform limits or pause execution. Those controls do not transfer your responsibility or guarantee that a loss will be prevented.

## 8. Trading and technology risks

You acknowledge the possibility of losing all assets committed to trading and, when leverage, borrowing, derivatives, fees, or account deficits apply, more than the amount initially committed.

Risks include:

- extreme volatility, gaps, illiquidity, price impact, slippage, adverse selection, and market manipulation;
- incorrect, stale, missing, malicious, or divergent market, macro, news, oracle, RPC, and exchange data;
- model hallucination, prompt injection, correlated agent error, uncalibrated confidence, and software defects;
- rejected, duplicated, delayed, partially filled, unexpectedly filled, or uncancellable orders;
- blockchain congestion, failed or replaced transactions, nonce conflicts, reorganizations, validator behavior, MEV, bridge failure, contract vulnerabilities, token behavior, and irreversible transfers;
- exchange insolvency, compromise, downtime, rate limits, account freezes, credential abuse, delisting, and regulatory action;
- wallet-provider, signer, HSM, MPC, key-recovery, identity-provider, cloud, database, queue, network, and monitoring failure;
- fees, taxes, gas, borrowing costs, funding rates, and currency conversion;
- laws or service restrictions changing without notice.

Circuit breakers coordinate new-order prevention but cannot atomically stop activity already accepted by independent venues. Stop, limit, or trailing orders may not fill at the expected price.

## 9. Third-party services

The Hosted Services depend on third-party identity, wallet, infrastructure, AI, data, blockchain, RPC, DEX, and CEX services. Their terms, fees, availability, privacy practices, and eligibility rules apply separately. We do not endorse or control them and may replace or discontinue an integration.

You authorize us to send the minimum information and instructions required to the services you enable. You must maintain valid accounts and permissions.

## 10. Acceptable use

You must not:

- violate law, sanctions, market-abuse, anti-money-laundering, tax, licensing, or exchange rules;
- manipulate markets, spoof, wash trade, front-run unlawfully, exploit non-public information, or interfere with fair venue operation;
- access another tenant, probe credentials, evade rate limits, disrupt service, introduce malware, or conduct unauthorized security testing;
- use the service to steal, launder, obscure, or transfer unlawfully obtained assets;
- misrepresent audit evidence, performance, custody, compliance, or service capabilities;
- reverse engineer or circumvent controls except to the extent law or an applicable open-source license permits;
- use model or data outputs in a way that violates third-party rights or licenses.

We may investigate, suspend, reject, or report activity when reasonably necessary to enforce these Terms, protect users or systems, or comply with law.

## 11. Fees, gas, and taxes

You will pay fees stated in the applicable order form or plan, plus taxes and third-party charges. Blockchain gas, priority fees, exchange fees, spreads, funding, borrowing, routing, and data-provider costs may apply independently.

Fees and commercial terms are set forth in the applicable order form or service agreement. Billing cycles, taxes, late payments, and fee adjustments are governed by the applicable commercial subscription agreement.

## 12. Data and privacy

Our processing of personal information is described in the [Privacy Policy](PRIVACY.md). You retain rights in your data subject to the license needed for us to operate, secure, support, and improve the Hosted Services.

You represent that you have the right to provide data and configure integrations and that you will give required notices and obtain required consent for users in your tenant.

Public blockchain transactions are generally permanent and visible. Exchange and provider records are controlled by those third parties.

## 13. Intellectual property

As between the parties, we and our licensors own the Hosted Services, documentation, service marks, and related technology, excluding your data and separately licensed components. Subject to these Terms and payment obligations, we grant you a limited, non-exclusive, non-transferable, revocable right to use the Hosted Services for your internal lawful purposes during the subscription term.

You grant us a limited right to host, process, transmit, and display your data only as needed to provide, secure, support, and comply with law regarding the services. The Foundation retains ownership of aggregated, anonymized usage telemetry and performance metrics.

## 14. Confidentiality

Each party may receive non-public business, security, technical, or financial information from the other. The receiving party will use it only for the relationship, protect it using reasonable care, and disclose it only to personnel and providers who need it and are bound by appropriate duties. Standard exclusions apply to information that is public without breach, already lawfully known, independently developed, or lawfully received from another source.

A party may disclose information when legally required after providing notice where permitted.

## 15. Service changes, availability, and beta features

We may modify the Hosted Services, providers, limits, or documentation. We may suspend an integration or live execution due to security, legal, venue, market, or reliability risk. Beta or experimental features may be changed or discontinued and may not receive service commitments.

Hosted API endpoints aim for 99.9% availability, excluding scheduled maintenance windows announced at least 48 hours in advance. Support commitments and deprecation schedules are specified in your applicable service order.

## 16. Suspension and termination

You may stop using the Hosted Services and terminate as provided in the applicable plan or order form. We may suspend or terminate access for material breach, non-payment, legal requirement, security risk, prohibited use, or risk to systems or others.

On termination, live execution is disabled, open activity is reconciled where feasible, delegations and credentials should be revoked, and data is handled under the Privacy Policy and contract. You remain responsible for orders, transactions, fees, taxes, and obligations incurred before termination.

## 17. Disclaimers

TO THE MAXIMUM EXTENT PERMITTED BY LAW, THE HOSTED SERVICES, OUTPUTS, DOCUMENTATION, AND BETA FEATURES ARE PROVIDED “AS IS” AND “AS AVAILABLE.” HERMES PROTOCOL FOUNDATION DISCLAIMS IMPLIED WARRANTIES, INCLUDING MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, TITLE, NON-INFRINGEMENT, ACCURACY, QUIET ENJOYMENT, AND WARRANTIES ARISING FROM COURSE OF DEALING OR USAGE.

WE DO NOT WARRANT THAT THE SERVICES WILL BE UNINTERRUPTED, SECURE, ERROR-FREE, PROFITABLE, COMPLIANT FOR YOUR USE, OR COMPATIBLE WITH EVERY WALLET, ASSET, NETWORK, EXCHANGE, OR JURISDICTION. WE DO NOT WARRANT THAT A CONSENSUS, RISK RULE, CIRCUIT BREAKER, STOP, APPROVAL, OR RECONCILIATION PROCESS WILL PREVENT LOSS.

Some jurisdictions do not allow certain disclaimers, so some may not apply.

## 18. Limitation of liability

TO THE MAXIMUM EXTENT PERMITTED BY LAW, NEITHER PARTY WILL BE LIABLE FOR INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, PUNITIVE, OR CONSEQUENTIAL DAMAGES, OR FOR LOST PROFITS, REVENUE, GOODWILL, DATA, OR TRADING OPPORTUNITY, EVEN IF ADVISED OF THE POSSIBILITY.

EXCEPT FOR EXCLUDED CLAIMS IDENTIFIED BELOW, EACH PARTY’S AGGREGATE LIABILITY ARISING OUT OF OR RELATING TO THE HOSTED SERVICES WILL NOT EXCEED THE GREATER OF US$100 OR THE FEES PAID OR PAYABLE FOR THE HOSTED SERVICES DURING THE 12 MONTHS BEFORE THE EVENT GIVING RISE TO LIABILITY.

The liability cap does not limit liability for fraud, willful misconduct, breach of confidentiality, violation of data-protection obligations, intellectual-property infringement, indemnification obligations, payment obligations, or any liability that cannot lawfully be excluded or limited. These exclusions remain subject to qualified legal review for the applicable customer, jurisdiction, and commercial model.

The allocation of risk in this section is an essential basis of the agreement. Jurisdictional restrictions may apply.

## 19. Indemnification

Each party agrees to defend, indemnify, and hold harmless the other from and against third-party claims, losses, and damages arising out of material breach of these Terms, unlawful conduct, or willful misconduct.

## 20. Governing law and disputes

These Terms are governed by the laws of the Cayman Islands, excluding conflict-of-law rules. Courts located in the Cayman Islands will have exclusive jurisdiction, and any disputes shall be resolved through binding arbitration in accordance with standard Cayman Islands arbitration rules.

This section must be customized for the operator and user population.

## 21. General terms

Neither party may assign these Terms except with prior written consent, provided that either party may assign these Terms to an affiliate or in connection with a corporate reorganization or sale of assets. Notices may be delivered electronically to the account contact. Failure to enforce a provision is not a waiver. If a provision is unenforceable, it will be modified to the minimum extent necessary and the remainder will continue. Headings are for convenience. These Terms, the Privacy Policy, applicable order form, and incorporated documents form the agreement concerning the Hosted Services.

Provisions that by nature should survive termination do survive, including payment, risk allocation, confidentiality, intellectual property, disclaimers, liability, disputes, and retained-data provisions.

## 22. Changes

We may update these Terms. We will identify the revision date and provide notice required by law or contract. Material changes to delegated transaction authority require a separate authorization process and are not established merely by posting revised Terms.

## 23. Contact

Hermes Protocol Foundation  
P.O. Box 309, Ugland House, Grand Cayman, KY1-1104, Cayman Islands  
legal@hermes-protocol.org  
https://hermes-protocol.org/support
