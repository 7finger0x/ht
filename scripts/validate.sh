#!/usr/bin/env bash
set -euo pipefail

echo "Validating repository..."

required_files=(
  "README.md"
  "azure-pipelines.yml"
  "SPEC.md"
)

for file in "${required_files[@]}"; do
  if [[ ! -f "$file" ]]; then
    echo "Missing required file: $file"
    exit 1
  fi
done

python - <<'PY'
from pathlib import Path
import sys

errors = []

for path in Path(".").rglob("*.yml"):
    if path.is_file() and path.stat().st_size == 0:
        errors.append(f"Empty YAML file: {path}")

for path in Path(".").rglob("*.yaml"):
    if path.is_file() and path.stat().st_size == 0:
        errors.append(f"Empty YAML file: {path}")

if errors:
    print("\n".join(errors))
    sys.exit(1)

print("Validation passed.")
PY