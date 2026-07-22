# Hermes SDK Generation Guide

**Status:** Reference  
**Last revised:** 2026-07-21

This guide explains how to generate strictly typed client SDKs for TypeScript and Python directly from the [Hermes OpenAPI 3.1.2 specification](../openapi/hermes.openapi.yaml).

## Prerequisites

| SDK | Toolchain | Install |
|---|---|---|
| TypeScript | Node.js ≥ 18, `@hey-api/openapi-ts` | `npx @hey-api/openapi-ts` (auto-installed) |
| Python | Python ≥ 3.11, `openapi-python-client` | `pip install openapi-python-client` |

## Generating SDKs

```bash
# Both SDKs
bash scripts/generate_sdks.sh

# TypeScript only
bash scripts/generate_sdks.sh --ts-only

# Python only
bash scripts/generate_sdks.sh --py-only
```

Output is written to:

- `sdks/typescript/` — TypeScript client using `@hey-api/client-fetch`
- `sdks/python/` — Python async client using `httpx`

## TypeScript SDK Usage

```typescript
import { createClient } from '@hey-api/client-fetch';
import { getExecutions, createExecution } from './sdks/typescript';

const client = createClient({
  baseUrl: 'https://api.hermes-protocol.org',
  headers: { Authorization: `Bearer ${token}` },
});

// List executions
const { data, error } = await getExecutions({ client });

// Submit execution
const { data: exec } = await createExecution({
  client,
  headers: { 'Idempotency-Key': crypto.randomUUID() },
  body: {
    decision_id: '<decision-id>',
    requested_notional: 5000,
    side: 'BUY',
    venue_id: 'paper-venue-001',
  },
});
```

## Python SDK Usage

```python
import asyncio
from hermes_client import AuthenticatedClient
from hermes_client.api.executions import list_executions

async def main() -> None:
    async with AuthenticatedClient(
        base_url="https://api.hermes-protocol.org",
        token="<bearer-token>",
    ) as client:
        response = await list_executions.asyncio_detailed(client=client)
        print(response.parsed)

asyncio.run(main())
```

## Regeneration Policy

- Re-run `bash scripts/generate_sdks.sh` after every change to `openapi/hermes.openapi.yaml`.
- Commit generated SDKs in `sdks/` if your consumers depend on them from source control.
- Add a CI step that runs `generate_sdks.sh` and fails on a diff to detect spec-SDK drift.

## Decimal and Monetary Fields

All quantity and price fields in the Hermes API are encoded as **strings** to preserve deterministic decimal arithmetic. Do not coerce these fields to `float` or `number` in consuming code; use a decimal library instead (e.g., Python `decimal.Decimal`, JS `big.js`).
