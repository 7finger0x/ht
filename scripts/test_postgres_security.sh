#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
package_root=$(cd "$script_dir/.." && pwd)
container_name="hermes-postgres-security-$$"
postgres_image="postgres:17-alpine@sha256:742f40ea20b9ff2ff31db5458d127452988a2164df9e17441e191f3b72252193"

if [[ -n "${HERMES_DOCKER_BIN:-}" ]]; then
  docker_bin=$HERMES_DOCKER_BIN
elif docker version >/dev/null 2>&1; then
  docker_bin=docker
elif [[ -x '/mnt/c/Program Files/Docker/Docker/resources/bin/docker.exe' ]] \
  && '/mnt/c/Program Files/Docker/Docker/resources/bin/docker.exe' version >/dev/null 2>&1; then
  docker_bin='/mnt/c/Program Files/Docker/Docker/resources/bin/docker.exe'
else
  echo 'Docker is required for the PostgreSQL security integration test.' >&2
  exit 1
fi

cleanup() {
  "$docker_bin" rm -f "$container_name" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

"$docker_bin" run --rm -d \
  --name "$container_name" \
  -e POSTGRES_DB=hermes \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=hermes_test_only \
  "$postgres_image" >/dev/null

ready=0
for _ in $(seq 1 30); do
  if "$docker_bin" exec "$container_name" pg_isready -U postgres -d hermes >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done
if [[ "$ready" -ne 1 ]]; then
  "$docker_bin" logs "$container_name" >&2
  exit 1
fi

"$docker_bin" exec -i -e PGPASSWORD=hermes_test_only "$container_name" \
  psql -U postgres -d hermes -v ON_ERROR_STOP=1 \
  < "$package_root/infra/supabase/migrations/0001_core.sql" >/dev/null

"$docker_bin" exec -i -e PGPASSWORD=hermes_test_only "$container_name" \
  psql -U postgres -d hermes -v ON_ERROR_STOP=1 \
  < "$package_root/tests/postgres_security.sql" >/dev/null

lookup_result=$("$docker_bin" exec -e PGPASSWORD=identity_test_only "$container_name" \
  psql -h 127.0.0.1 -U hermes_identity_login -d hermes -Atqc \
  "select principal_id || '|' || principal_status from hermes.lookup_principal('privy', 'did:privy:one')")
[[ "$lookup_result" == '10000000-0000-0000-0000-000000000001|active' ]]

unknown_count=$("$docker_bin" exec -e PGPASSWORD=identity_test_only "$container_name" \
  psql -h 127.0.0.1 -U hermes_identity_login -d hermes -Atqc \
  "select count(*) from hermes.lookup_principal('privy', 'did:privy:missing')")
[[ "$unknown_count" == '0' ]]

membership_count=$("$docker_bin" exec -e PGPASSWORD=identity_test_only "$container_name" \
  psql -h 127.0.0.1 -U hermes_identity_login -d hermes -Atqc \
  "begin; set local app.principal_id = '10000000-0000-0000-0000-000000000001'; select count(*) from hermes.tenant_memberships; commit;" \
  | tail -n 1)
[[ "$membership_count" == '1' ]]

for forbidden_sql in \
  'select count(*) from hermes.principals' \
  "insert into hermes.principals (provider, external_subject) values ('privy', 'did:privy:blocked')" \
  "update hermes.principals set status = 'suspended'"; do
  if "$docker_bin" exec -e PGPASSWORD=identity_test_only "$container_name" \
    psql -h 127.0.0.1 -U hermes_identity_login -d hermes -v ON_ERROR_STOP=1 \
    -c "$forbidden_sql" >/dev/null 2>&1; then
    echo "Identity privilege unexpectedly allowed: $forbidden_sql" >&2
    exit 1
  fi
done

api_tenant_count=$("$docker_bin" exec -e PGPASSWORD=api_test_only "$container_name" \
  psql -h 127.0.0.1 -U hermes_api_login -d hermes -Atqc \
  "begin; set local app.tenant_id = '20000000-0000-0000-0000-000000000001'; set local app.principal_id = '10000000-0000-0000-0000-000000000001'; select count(*) from hermes.tenants; commit;" \
  | tail -n 1)
[[ "$api_tenant_count" == '1' ]]

absent_context_count=$("$docker_bin" exec -e PGPASSWORD=api_test_only "$container_name" \
  psql -h 127.0.0.1 -U hermes_api_login -d hermes -Atqc \
  'select count(*) from hermes.tenants')
[[ "$absent_context_count" == '0' ]]

if "$docker_bin" exec -e PGPASSWORD=api_test_only "$container_name" \
  psql -h 127.0.0.1 -U hermes_api_login -d hermes -v ON_ERROR_STOP=1 -c \
  "begin; set local app.tenant_id = '20000000-0000-0000-0000-000000000001'; set local app.principal_id = '10000000-0000-0000-0000-000000000001'; insert into hermes.portfolios (tenant_id, name, base_currency) values ('20000000-0000-0000-0000-000000000002', 'Blocked', 'USD'); commit;" \
  >/dev/null 2>&1; then
  echo 'Cross-tenant API insert unexpectedly succeeded.' >&2
  exit 1
fi

if "$docker_bin" exec -e PGPASSWORD=api_test_only "$container_name" \
  psql -h 127.0.0.1 -U hermes_api_login -d hermes -v ON_ERROR_STOP=1 \
  -c 'select count(*) from hermes.principals' >/dev/null 2>&1; then
  echo 'API principal-table access unexpectedly succeeded.' >&2
  exit 1
fi

if "$docker_bin" exec -e PGPASSWORD=api_test_only "$container_name" \
  psql -h 127.0.0.1 -U hermes_api_login -d hermes -v ON_ERROR_STOP=1 -c \
  "begin; set local app.tenant_id = '20000000-0000-0000-0000-000000000002'; insert into hermes.audit_events (tenant_id, occurred_at, actor_type, actor_id, action, result, resource_type, resource_id, correlation_id, payload_digest, event_digest) values ('20000000-0000-0000-0000-000000000002', clock_timestamp(), 'system', 'test', 'test.direct', 'SUCCESS', 'test', 'direct', gen_random_uuid(), 'sha256:' || repeat('8', 64), 'sha256:' || repeat('9', 64)); commit;" \
  >/dev/null 2>&1; then
  echo 'Direct application audit insert unexpectedly succeeded.' >&2
  exit 1
fi

append_result=$("$docker_bin" exec -e PGPASSWORD=api_test_only "$container_name" \
  psql -h 127.0.0.1 -U hermes_api_login -d hermes -Atqc \
  "begin; set local app.tenant_id = '20000000-0000-0000-0000-000000000002'; select hermes.append_audit_event('20000000-0000-0000-0000-000000000002'::uuid, clock_timestamp(), 'system'::hermes.audit_actor_type, 'api-test', null::text, 'test.append', 'SUCCESS'::hermes.audit_result, 'test', 'append', gen_random_uuid(), null::uuid, null::text, 'sha256:' || repeat('a', 64), null::text, 'sha256:' || repeat('b', 64), '{}'::text[], '{}'::jsonb); commit;" \
  | tail -n 1)
[[ "$append_result" =~ ^[0-9a-f-]{36}$ ]]

if "$docker_bin" exec -e PGPASSWORD=api_test_only "$container_name" \
  psql -h 127.0.0.1 -U hermes_api_login -d hermes -v ON_ERROR_STOP=1 -c \
  "begin; set local app.tenant_id = '20000000-0000-0000-0000-000000000002'; select hermes.append_audit_event('20000000-0000-0000-0000-000000000002'::uuid, clock_timestamp(), 'system'::hermes.audit_actor_type, 'api-test', null::text, 'test.stale', 'SUCCESS'::hermes.audit_result, 'test', 'stale', gen_random_uuid(), null::uuid, null::text, 'sha256:' || repeat('c', 64), null::text, 'sha256:' || repeat('d', 64), '{}'::text[], '{}'::jsonb); commit;" \
  >/dev/null 2>&1; then
  echo 'Audit append with a stale predecessor unexpectedly succeeded.' >&2
  exit 1
fi

server_version=$("$docker_bin" exec -e PGPASSWORD=hermes_test_only "$container_name" \
  psql -U postgres -d hermes -Atqc 'show server_version;')
echo "PostgreSQL $server_version security integration: PASS"
echo 'Identity resolver, direct-table denial, membership RLS: PASS'
echo 'Tenant RLS, cross-tenant attribution, audit direct-write denial: PASS'
echo 'Serialized audit append, stale-head denial, chain structure: PASS'
