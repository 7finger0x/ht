#!/usr/bin/env bash
# Generate typed TypeScript and Python client SDKs from the Hermes OpenAPI spec.
#
# Prerequisites:
#   TypeScript: npm install -g @hey-api/openapi-ts   (or npx is used automatically)
#   Python:     pip install openapi-python-client
#
# Usage:
#   bash scripts/generate_sdks.sh [--ts-only | --py-only]
#
# Output:
#   sdks/typescript/   - TypeScript client with full type safety
#   sdks/python/       - Python client (dataclasses, httpx)
set -euo pipefail

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
root=$(cd "$script_dir/.." && pwd)
spec="$root/openapi/hermes.openapi.yaml"

TS_OUT="$root/sdks/typescript"
PY_OUT="$root/sdks/python"

generate_ts=true
generate_py=true

for arg in "$@"; do
  case "$arg" in
    --ts-only) generate_py=false ;;
    --py-only) generate_ts=false ;;
    *) echo "Unknown argument: $arg" >&2; exit 1 ;;
  esac
done

# ---------------------------------------------------------------------------
# TypeScript SDK via @hey-api/openapi-ts
# ---------------------------------------------------------------------------
if [[ "$generate_ts" == true ]]; then
  echo '==> Generating TypeScript SDK...'
  mkdir -p "$TS_OUT"
  npx --yes @hey-api/openapi-ts \
    --input "$spec" \
    --output "$TS_OUT" \
    --client @hey-api/client-fetch \
    --schemas \
    --types \
    --services
  echo "TypeScript SDK written to $TS_OUT"
fi

# ---------------------------------------------------------------------------
# Python SDK via openapi-python-client
# ---------------------------------------------------------------------------
if [[ "$generate_py" == true ]]; then
  echo '==> Generating Python SDK...'
  # openapi-python-client requires the config file; use --overwrite if the dir exists
  if [[ -d "$PY_OUT" ]]; then
    openapi-python-client update \
      --path "$spec" \
      --config "$root/scripts/openapi_python_client_config.yaml"
  else
    openapi-python-client generate \
      --path "$spec" \
      --output-path "$PY_OUT" \
      --config "$root/scripts/openapi_python_client_config.yaml"
  fi
  echo "Python SDK written to $PY_OUT"
fi

echo '==> SDK generation complete.'
