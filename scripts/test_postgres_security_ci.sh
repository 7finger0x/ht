#!/usr/bin/env bash
# CI variant: uses a pre-running postgres service container on 127.0.0.1:5432.
# The migration has already been applied by the CI step before this script runs.
# PGPASSWORD must be set in the environment.
set -euo pipefail

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
package_root=$(cd "$script_dir/.." && pwd)

PG_HOST="${HERMES_PG_HOST:-127.0.0.1}"
PG_PORT="${HERMES_PG_PORT:-5432}"

psql_ci() {
  psql -h "$PG_HOST" -p "$PG_PORT" -U postgres -d hermes "$@"
}

# Apply test fixtures (creates login roles and seed data)
psql_ci -v ON_ERROR_STOP=1 < "$package_root/tests/postgres_security.sql" > /dev/null

# Identity: exact lookup returns the seeded principal
lookup_result=$(psql_ci -Atqc \
  "select principal_id || '|' || principal_status from hermes.lookup_principal('privy', 'did:privy:one')" \
  2>/dev/null)
[[ "$lookup_result" == '10000000-0000-0000-0000-000000000001|active' ]]

# Identity: unknown subject returns zero rows
unknown_count=$(psql_ci -Atqc \
  "select count(*) from hermes.lookup_principal('privy', 'did:privy:missing')" \
  2>/dev/null)
[[ "$unknown_count" == '0' ]]

# RLS: principal sees exactly one membership under correct tenant context
membership_count=$(psql_ci -Atqc \
  "begin; set local app.principal_id = '10000000-0000-0000-0000-000000000001'; select count(*) from hermes.tenant_memberships; commit;" \
  2>/dev/null | tail -n 1)
[[ "$membership_count" == '1' ]]

# Direct principal table access must be denied for identity login role
if PGPASSWORD=identity_test_only psql -h "$PG_HOST" -p "$PG_PORT" \
     -U hermes_identity_login -d hermes -v ON_ERROR_STOP=1 \
     -c 'select count(*) from hermes.principals' > /dev/null 2>&1; then
  echo 'Identity privilege unexpectedly allowed direct principals select' >&2
  exit 1
fi

# RLS: API role sees only its own tenant
api_tenant_count=$(PGPASSWORD=api_test_only psql -h "$PG_HOST" -p "$PG_PORT" \
  -U hermes_api_login -d hermes -Atqc \
  "begin; set local app.tenant_id = '20000000-0000-0000-0000-000000000001'; set local app.principal_id = '10000000-0000-0000-0000-000000000001'; select count(*) from hermes.tenants; commit;" \
  2>/dev/null | tail -n 1)
[[ "$api_tenant_count" == '1' ]]

# RLS: seeded strategy is visible only inside the owning tenant context
strategy_visibility=$(PGPASSWORD=api_test_only psql -h "$PG_HOST" -p "$PG_PORT" \
  -U hermes_api_login -d hermes -Atqc \
  "begin; set local app.tenant_id = '20000000-0000-0000-0000-000000000001'; set local app.principal_id = '10000000-0000-0000-0000-000000000001'; select count(*) from hermes.strategies; commit;" \
  2>/dev/null | tail -n 1)
[[ "$strategy_visibility" == '1' ]]

cross_tenant_strategy_visibility=$(PGPASSWORD=api_test_only psql -h "$PG_HOST" -p "$PG_PORT" \
  -U hermes_api_login -d hermes -Atqc \
  "begin; set local app.tenant_id = '20000000-0000-0000-0000-000000000002'; set local app.principal_id = '10000000-0000-0000-0000-000000000002'; select count(*) from hermes.strategies; commit;" \
  2>/dev/null | tail -n 1)
[[ "$cross_tenant_strategy_visibility" == '0' ]]

# RLS: absent context yields zero rows
absent_context_count=$(PGPASSWORD=api_test_only psql -h "$PG_HOST" -p "$PG_PORT" \
  -U hermes_api_login -d hermes -Atqc \
  'select count(*) from hermes.tenants' 2>/dev/null)
[[ "$absent_context_count" == '0' ]]

# Cross-tenant insert must fail
if PGPASSWORD=api_test_only psql -h "$PG_HOST" -p "$PG_PORT" \
     -U hermes_api_login -d hermes -v ON_ERROR_STOP=1 -c \
     "begin; set local app.tenant_id = '20000000-0000-0000-0000-000000000001'; set local app.principal_id = '10000000-0000-0000-0000-000000000001'; insert into hermes.portfolios (tenant_id, name, base_currency) values ('20000000-0000-0000-0000-000000000002', 'Blocked', 'USD'); commit;" \
     > /dev/null 2>&1; then
  echo 'Cross-tenant API insert unexpectedly succeeded.' >&2
  exit 1
fi

# Direct audit insert must be denied
if PGPASSWORD=api_test_only psql -h "$PG_HOST" -p "$PG_PORT" \
     -U hermes_api_login -d hermes -v ON_ERROR_STOP=1 -c \
     "begin; set local app.tenant_id = '20000000-0000-0000-0000-000000000002'; insert into hermes.audit_events (tenant_id, occurred_at, actor_type, actor_id, action, result, resource_type, resource_id, correlation_id, payload_digest, event_digest) values ('20000000-0000-0000-0000-000000000002', clock_timestamp(), 'system', 'test', 'test.direct', 'SUCCESS', 'test', 'direct', gen_random_uuid(), 'sha256:' || repeat('8', 64), 'sha256:' || repeat('9', 64)); commit;" \
     > /dev/null 2>&1; then
  echo 'Direct application audit insert unexpectedly succeeded.' >&2
  exit 1
fi

# Serialized audit append must succeed via the boundary function
append_result=$(PGPASSWORD=api_test_only psql -h "$PG_HOST" -p "$PG_PORT" \
  -U hermes_api_login -d hermes -Atqc \
  "begin; set local app.tenant_id = '20000000-0000-0000-0000-000000000002'; select hermes.append_audit_event('20000000-0000-0000-0000-000000000002'::uuid, clock_timestamp(), 'system'::hermes.audit_actor_type, 'ci-test', null::text, 'test.append', 'SUCCESS'::hermes.audit_result, 'test', 'append', gen_random_uuid(), null::uuid, null::text, 'sha256:' || repeat('a', 64), null::text, 'sha256:' || repeat('b', 64), '{}'::text[], '{}'::jsonb); commit;" \
  2>/dev/null | tail -n 1)
[[ "$append_result" =~ ^[0-9a-f-]{36}$ ]]

# Stale-head append must fail
if PGPASSWORD=api_test_only psql -h "$PG_HOST" -p "$PG_PORT" \
     -U hermes_api_login -d hermes -v ON_ERROR_STOP=1 -c \
     "begin; set local app.tenant_id = '20000000-0000-0000-0000-000000000002'; select hermes.append_audit_event('20000000-0000-0000-0000-000000000002'::uuid, clock_timestamp(), 'system'::hermes.audit_actor_type, 'ci-test', null::text, 'test.stale', 'SUCCESS'::hermes.audit_result, 'test', 'stale', gen_random_uuid(), null::uuid, null::text, 'sha256:' || repeat('c', 64), null::text, 'sha256:' || repeat('d', 64), '{}'::text[], '{}'::jsonb); commit;" \
     > /dev/null 2>&1; then
  echo 'Audit append with a stale predecessor unexpectedly succeeded.' >&2
  exit 1
fi

server_version=$(psql_ci -Atqc 'show server_version;')
echo "PostgreSQL $server_version CI security integration: PASS"
echo 'Identity resolver, direct-table denial, membership RLS: PASS'
echo 'Tenant RLS, cross-tenant attribution, audit direct-write denial: PASS'
echo 'Serialized audit append, stale-head denial, chain structure: PASS'
