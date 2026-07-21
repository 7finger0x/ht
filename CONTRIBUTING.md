# Contributing to Hermes

Thanks for contributing to Hermes.

Hermes is a policy-controlled trading project with safety-critical API, tenant, signing, reconciliation, and observability behavior. Contributions are reviewed for correctness, security, operability, data handling, and documentation impact, not only code style.

## Start here

Before opening a pull request, review these project documents:

- [README](README.md)
- [Architecture](docs/Architecture.md)
- [Execution Protocol](docs/ExecutionProtocol.md)
- [Security Policy](docs/SecurityPolicy.md)
- [OpenAPI contract](openapi/hermes.openapi.yaml)
- [Detailed contribution policy](docs/ContributionGuidelines.md)

## Contribution workflow

- Use a short-lived branch for your work.
- Keep changes focused and explain the problem, intended behavior, and risk in your pull request.
- Update docs, schemas, examples, and tests together with code changes.
- Do not commit secrets, private keys, access tokens, exchange credentials, or production data.
- Report vulnerabilities privately through [SECURITY.md](SECURITY.md), not in a public issue.

## Pull request expectations

A good pull request should include:

- what changed and why;
- API, schema, migration, or config impact;
- test evidence;
- rollout and rollback notes for operational changes;
- runbook, alert, or observability updates when behavior changes.

Screenshots alone are not sufficient evidence for behavior changes.

## Local validation

Run the validation steps that match your change.

### Documentation and contract validation

```bash
python -m pip install -r requirements-docs.txt
python scripts/validate_package.py
pytest -q tests/test_contracts.py
```

### Backend MVP validation

```bash
python -m pip install -r services/api/requirements.txt
pytest -q tests/test_mvp_api.py
```

### Frontend MVP validation

```bash
cd apps/web
npm ci
npm run build
```

## Style and safety notes

- Keep examples valid and current.
- Update the OpenAPI contract when API behavior changes.
- Prefer deterministic tests and simulation-safe fixtures.
- Treat browser-exposed `VITE_*` values as public.
- Fail closed on unknown, stale, or ambiguous state.

## Need the full policy?

The repository-level guide is in [docs/ContributionGuidelines.md](docs/ContributionGuidelines.md). That document covers detailed requirements for code review, testing, release controls, and safety-sensitive changes.
