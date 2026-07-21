# Runbook: Analytical Model, Prompt, Agent, or Weight Change

**Owner role:** Model-risk owner  
**Last reviewed:** 2026-07-20  
**Default severity:** Planned high-risk change; incident severity if unapproved change is detected

## 1. Trigger and severity

Use for model-provider/version change, prompt-template change, agent code or feature change, confidence calibration change, consensus weight/threshold change, or enabling a new analytical source.

## 2. Safety objective

Ensure analytical changes are versioned, reproducible, evaluated, and incapable of bypassing deterministic risk or signer controls.

## 3. Preconditions and authority

Changes require model owner, trading/risk owner, and production change approver. Lowering quorum, increasing an agent’s influence, adding tools/data, or enabling live use requires security/privacy review as applicable.

## 4. Immediate containment

For an unapproved or unexplained production change:

1. pause affected strategies;
2. pin the last approved model/prompt/weight configuration;
3. preserve provider metadata, request/response digests, release/configuration history, and affected decisions;
4. verify no model received secrets or unauthorized tenant data;
5. reconcile any live executions influenced by the change.

For a planned change, keep it simulation-only through evaluation.

## 5. Diagnosis or evaluation

Evaluate on a fixed, versioned dataset and time split:

- schema validity, timeout, abstention, and provider-error rate;
- action distribution and confidence calibration;
- disagreement and correlation with other agents;
- deterministic consensus result changes;
- downstream risk rejection/approval and quantity changes;
- prompt-injection and adversarial content behavior;
- data-minimization and provider-retention implications;
- latency, cost, rate limits, and outage behavior;
- performance net of fees/slippage only when methodology is documented, with no guarantee claims.

Do not select solely on in-sample returns.

## 6. Recovery or release

1. assign new agent/model/prompt/policy versions;
2. update approved-version allowlist and weights through reviewed configuration;
3. run unit, replay, adversarial, integration, and failure-mode tests;
4. deploy to staging and simulation canary;
5. compare against the current version with predeclared acceptance and rollback criteria;
6. approve limited production scope without increasing hard risk limits;
7. monitor enhanced metrics and retain replay evidence;
8. roll back by version pin if criteria fail.

## 7. Verification

- exact provider/model/prompt/agent versions are visible in every assessment;
- deterministic replay matches stored consensus;
- no raw output can call tools, signer, venue, database, or secret manager;
- invalid output becomes `ABSTAIN`;
- quorum does not decrease during provider failure;
- risk and signer controls remain unchanged unless separately approved;
- privacy/data inventory and subprocessor register are current;
- marketing does not convert evaluation results into unsupported profitability claims.

## 8. Rollback or abort criteria

Abort or roll back for schema regression, increased unbounded output, data leakage, poor calibration, excessive correlated error, unexplained decision drift, latency beyond decision validity, provider contract/privacy mismatch, or deterministic replay failure.

## 9. Evidence to preserve

Candidate and baseline versions; dataset/version and split; prompts/configuration; request/output digests; metrics and statistical methodology; adversarial cases; consensus/risk diffs; approvals; deployment/canary results; rollback decision.

## 10. Escalation and communications

Treat an unauthorized production model/prompt/weight change as a security and change-control incident. Notify affected tenants when decision behavior materially changed contrary to contract or published controls.
