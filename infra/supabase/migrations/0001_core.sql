-- Hermes canonical core schema and tenant-isolation baseline.
-- Target: PostgreSQL 15+ / Supabase-compatible Postgres.
-- This migration creates NOLOGIN roles. Deployment must create separate LOGIN roles,
-- grant only the relevant role, and ensure the login role has NOBYPASSRLS and does not own tables.

begin;

create extension if not exists pgcrypto;
create schema if not exists hermes;
revoke all on schema hermes from public;

-- Role creation is idempotent for migration reruns.
do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'hermes_api') then
    create role hermes_api nologin noinherit nobypassrls;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'hermes_worker') then
    create role hermes_worker nologin noinherit nobypassrls;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'hermes_identity') then
    create role hermes_identity nologin noinherit nobypassrls;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'hermes_auditor') then
    create role hermes_auditor nologin noinherit nobypassrls;
  end if;
end
$$;

grant usage on schema hermes to hermes_api, hermes_worker, hermes_identity, hermes_auditor;

create type hermes.member_role as enum (
  'viewer', 'operator', 'trader', 'approver', 'tenant_admin', 'security_admin', 'platform_admin'
);
create type hermes.member_status as enum ('active', 'suspended', 'removed');
create type hermes.execution_mode as enum ('SIMULATION', 'LIVE');
create type hermes.venue_type as enum ('DEX', 'CEX');
create type hermes.venue_status as enum ('disabled', 'sandbox', 'enabled', 'paused', 'degraded');
create type hermes.assessment_action as enum ('BUY', 'SELL', 'HOLD', 'ABSTAIN');
create type hermes.decision_action as enum ('BUY', 'SELL', 'HOLD', 'NO_CONSENSUS');
create type hermes.decision_status as enum ('PENDING', 'ACCEPTED', 'REJECTED', 'EXPIRED', 'FAILED');
create type hermes.rule_status as enum ('PASS', 'FAIL', 'UNKNOWN');
create type hermes.risk_status as enum ('PENDING', 'APPROVED', 'REJECTED', 'EXPIRED', 'FAILED');
create type hermes.order_side as enum ('BUY', 'SELL');
create type hermes.order_type as enum ('MARKET', 'LIMIT', 'STOP_LIMIT');
create type hermes.time_in_force as enum ('GTC', 'IOC', 'FOK', 'DAY');
create type hermes.execution_state as enum (
  'CREATED', 'CONSENSUS_PENDING', 'CONSENSUS_ACCEPTED', 'CONSENSUS_REJECTED',
  'RISK_PENDING', 'RISK_APPROVED', 'RISK_REJECTED', 'APPROVAL_PENDING',
  'READY_TO_SUBMIT', 'SIGNING', 'SIGNING_FAILED', 'SUBMITTING',
  'SUBMISSION_AMBIGUOUS', 'ACKNOWLEDGED', 'PARTIALLY_FILLED', 'CONFIRMED',
  'REORGED', 'FINALIZED', 'CANCEL_PENDING', 'FILLED', 'CANCELLED', 'EXPIRED',
  'FAILED', 'RECONCILING', 'RECONCILIATION_FAILED', 'RECONCILED', 'REJECTED'
);
create type hermes.order_status as enum (
  'CREATED', 'SUBMITTING', 'ACKNOWLEDGED', 'OPEN', 'PARTIALLY_FILLED', 'FILLED',
  'CANCEL_PENDING', 'CANCELLED', 'EXPIRED', 'REJECTED', 'FAILED', 'AMBIGUOUS',
  'CONFIRMED', 'FINALIZED', 'REORGED'
);
create type hermes.audit_actor_type as enum ('principal', 'service', 'signer', 'venue', 'system');
create type hermes.audit_result as enum ('SUCCESS', 'DENIED', 'FAILED', 'PENDING');
create type hermes.circuit_state as enum ('ACTIVE', 'RESET');

create or replace function hermes.current_tenant_id()
returns uuid
language sql
stable
as $$
  select nullif(current_setting('app.tenant_id', true), '')::uuid
$$;

create or replace function hermes.current_principal_id()
returns uuid
language sql
stable
as $$
  select nullif(current_setting('app.principal_id', true), '')::uuid
$$;

create or replace function hermes.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = clock_timestamp();
  return new;
end
$$;

create or replace function hermes.reject_mutation()
returns trigger
language plpgsql
as $$
begin
  raise exception 'immutable record cannot be updated or deleted' using errcode = '55000';
end
$$;

create table hermes.principals (
  id uuid primary key default gen_random_uuid(),
  provider text not null,
  external_subject text not null,
  display_name text,
  status text not null default 'active' check (status in ('active', 'suspended', 'closed')),
  created_at timestamptz not null default clock_timestamp(),
  updated_at timestamptz not null default clock_timestamp(),
  unique (provider, external_subject)
);

-- Request-time identity resolution exposes only an exact provider/subject match.
-- Principal provisioning and status changes use a separate, reviewed control-plane identity.
create or replace function hermes.lookup_principal(
  p_provider text,
  p_external_subject text
)
returns table (principal_id uuid, principal_status text)
language sql
stable
strict
security definer
set search_path = pg_catalog, hermes, pg_temp
rows 1
as $$
  select principal.id, principal.status
  from hermes.principals as principal
  where principal.provider = p_provider
    and principal.external_subject = p_external_subject
  limit 1
$$;

revoke all on function hermes.lookup_principal(text, text) from public;
grant execute on function hermes.lookup_principal(text, text) to hermes_identity;

create table hermes.tenants (
  id uuid primary key default gen_random_uuid(),
  name text not null check (length(name) between 1 and 200),
  status text not null default 'active' check (status in ('active', 'suspended', 'closed')),
  deployment_mode text not null check (deployment_mode in ('managed', 'dedicated', 'self_hosted')),
  created_at timestamptz not null default clock_timestamp(),
  updated_at timestamptz not null default clock_timestamp()
);

create table hermes.tenant_memberships (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references hermes.tenants(id) on delete restrict,
  principal_id uuid not null references hermes.principals(id) on delete restrict,
  role hermes.member_role not null,
  scopes text[] not null default '{}',
  status hermes.member_status not null default 'active',
  created_at timestamptz not null default clock_timestamp(),
  updated_at timestamptz not null default clock_timestamp(),
  unique (tenant_id, principal_id)
);

create table hermes.strategies (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references hermes.tenants(id) on delete restrict,
  name text not null check (length(name) between 1 and 200),
  mode hermes.execution_mode not null default 'SIMULATION',
  status text not null default 'disabled' check (status in ('disabled', 'simulation', 'enabled', 'paused', 'retired')),
  configuration jsonb not null default '{}'::jsonb,
  configuration_version text not null,
  created_by uuid not null references hermes.principals(id) on delete restrict,
  created_at timestamptz not null default clock_timestamp(),
  updated_at timestamptz not null default clock_timestamp(),
  unique (tenant_id, id),
  foreign key (tenant_id, created_by) references hermes.tenant_memberships(tenant_id, principal_id) on delete restrict
);

create table hermes.portfolios (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references hermes.tenants(id) on delete restrict,
  name text not null check (length(name) between 1 and 200),
  base_currency text not null check (base_currency ~ '^[A-Z0-9]{2,20}$'),
  status text not null default 'active' check (status in ('active', 'paused', 'closed')),
  created_at timestamptz not null default clock_timestamp(),
  updated_at timestamptz not null default clock_timestamp(),
  unique (tenant_id, id)
);

create table hermes.venues (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references hermes.tenants(id) on delete restrict,
  venue_id text not null check (venue_id ~ '^[a-z0-9][a-z0-9._-]{2,63}$'),
  name text not null,
  type hermes.venue_type not null,
  status hermes.venue_status not null default 'disabled',
  environment text not null check (environment in ('sandbox', 'testnet', 'mainnet')),
  network text,
  chain_id text,
  adapter text not null,
  adapter_version text not null,
  secret_or_signer_ref text not null,
  configuration jsonb not null default '{}'::jsonb,
  configuration_digest text not null check (configuration_digest ~ '^sha256:[a-f0-9]{64}$'),
  created_at timestamptz not null default clock_timestamp(),
  updated_at timestamptz not null default clock_timestamp(),
  unique (tenant_id, id),
  unique (tenant_id, venue_id)
);

create table hermes.market_snapshots (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references hermes.tenants(id) on delete restrict,
  strategy_id uuid not null,
  portfolio_id uuid,
  instrument_id text not null,
  mode hermes.execution_mode not null,
  captured_from timestamptz not null,
  captured_to timestamptz not null,
  valid_until timestamptz not null,
  payload jsonb not null,
  quality jsonb not null,
  digest text not null check (digest ~ '^sha256:[a-f0-9]{64}$'),
  created_at timestamptz not null default clock_timestamp(),
  unique (tenant_id, id),
  unique (tenant_id, digest),
  foreign key (tenant_id, strategy_id) references hermes.strategies(tenant_id, id) on delete restrict,
  foreign key (tenant_id, portfolio_id) references hermes.portfolios(tenant_id, id) on delete restrict
);

create table hermes.agent_assessments (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references hermes.tenants(id) on delete restrict,
  snapshot_id uuid not null,
  agent_id text not null,
  agent_version text not null,
  provider text not null,
  model text not null,
  prompt_version text,
  action hermes.assessment_action not null,
  confidence numeric(20,18) not null check (confidence between 0 and 1),
  data_quality numeric(20,18) not null check (data_quality between 0 and 1),
  valid_until timestamptz not null,
  eligible boolean not null,
  exclusion_code text,
  rationale_summary text check (rationale_summary is null or length(rationale_summary) <= 2000),
  input_digest text not null check (input_digest ~ '^sha256:[a-f0-9]{64}$'),
  output_digest text not null check (output_digest ~ '^sha256:[a-f0-9]{64}$'),
  created_at timestamptz not null default clock_timestamp(),
  unique (tenant_id, id),
  unique (tenant_id, snapshot_id, agent_id),
  foreign key (tenant_id, snapshot_id) references hermes.market_snapshots(tenant_id, id) on delete restrict
);

create table hermes.consensus_decisions (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references hermes.tenants(id) on delete restrict,
  snapshot_id uuid not null,
  strategy_id uuid not null,
  instrument_id text not null,
  mode hermes.execution_mode not null,
  action hermes.decision_action not null,
  status hermes.decision_status not null,
  metrics jsonb not null,
  assessment_ids uuid[] not null,
  excluded_assessment_ids uuid[] not null default '{}',
  policy_version text not null,
  algorithm_version text not null,
  digest text not null check (digest ~ '^sha256:[a-f0-9]{64}$'),
  valid_until timestamptz not null,
  created_at timestamptz not null default clock_timestamp(),
  unique (tenant_id, id),
  unique (tenant_id, snapshot_id, policy_version, algorithm_version),
  foreign key (tenant_id, snapshot_id) references hermes.market_snapshots(tenant_id, id) on delete restrict,
  foreign key (tenant_id, strategy_id) references hermes.strategies(tenant_id, id) on delete restrict
);

create table hermes.risk_evaluations (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references hermes.tenants(id) on delete restrict,
  decision_id uuid not null,
  portfolio_id uuid not null,
  venue_id uuid not null,
  status hermes.risk_status not null,
  approved_quantity numeric,
  approved_notional numeric,
  currency text,
  requires_approval boolean not null default false,
  policy_version text not null,
  engine_version text not null,
  rule_results jsonb not null,
  portfolio_snapshot jsonb not null,
  digest text not null check (digest ~ '^sha256:[a-f0-9]{64}$'),
  valid_until timestamptz not null,
  created_at timestamptz not null default clock_timestamp(),
  unique (tenant_id, id),
  foreign key (tenant_id, decision_id) references hermes.consensus_decisions(tenant_id, id) on delete restrict,
  foreign key (tenant_id, portfolio_id) references hermes.portfolios(tenant_id, id) on delete restrict,
  foreign key (tenant_id, venue_id) references hermes.venues(tenant_id, id) on delete restrict,
  check (approved_quantity is null or approved_quantity >= 0),
  check (approved_notional is null or approved_notional >= 0)
);

create table hermes.executions (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references hermes.tenants(id) on delete restrict,
  decision_id uuid not null,
  strategy_id uuid not null,
  portfolio_id uuid not null,
  venue_id uuid not null,
  risk_evaluation_id uuid,
  instrument_id text not null,
  mode hermes.execution_mode not null,
  side hermes.order_side not null,
  state hermes.execution_state not null default 'CREATED',
  state_version bigint not null default 0,
  correlation_id uuid not null,
  client_reference text,
  failure jsonb,
  created_by uuid not null references hermes.principals(id) on delete restrict,
  created_at timestamptz not null default clock_timestamp(),
  updated_at timestamptz not null default clock_timestamp(),
  unique (tenant_id, id),
  foreign key (tenant_id, decision_id) references hermes.consensus_decisions(tenant_id, id) on delete restrict,
  foreign key (tenant_id, strategy_id) references hermes.strategies(tenant_id, id) on delete restrict,
  foreign key (tenant_id, portfolio_id) references hermes.portfolios(tenant_id, id) on delete restrict,
  foreign key (tenant_id, venue_id) references hermes.venues(tenant_id, id) on delete restrict,
  foreign key (tenant_id, risk_evaluation_id) references hermes.risk_evaluations(tenant_id, id) on delete restrict,
  foreign key (tenant_id, created_by) references hermes.tenant_memberships(tenant_id, principal_id) on delete restrict
);

create table hermes.order_intents (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references hermes.tenants(id) on delete restrict,
  execution_id uuid not null,
  decision_id uuid not null,
  risk_evaluation_id uuid not null,
  venue_id uuid not null,
  leg_index integer not null default 0 check (leg_index >= 0),
  client_order_id text not null check (length(client_order_id) between 8 and 64),
  side hermes.order_side not null,
  order_type hermes.order_type not null,
  quantity numeric not null check (quantity > 0),
  limit_price numeric check (limit_price is null or limit_price > 0),
  stop_price numeric check (stop_price is null or stop_price > 0),
  time_in_force hermes.time_in_force not null,
  execution_parameters jsonb not null,
  intent_digest text not null check (intent_digest ~ '^sha256:[a-f0-9]{64}$'),
  expires_at timestamptz not null,
  created_at timestamptz not null default clock_timestamp(),
  unique (tenant_id, id),
  unique (tenant_id, client_order_id),
  unique (tenant_id, decision_id, risk_evaluation_id, venue_id, leg_index),
  foreign key (tenant_id, execution_id) references hermes.executions(tenant_id, id) on delete restrict,
  foreign key (tenant_id, decision_id) references hermes.consensus_decisions(tenant_id, id) on delete restrict,
  foreign key (tenant_id, risk_evaluation_id) references hermes.risk_evaluations(tenant_id, id) on delete restrict,
  foreign key (tenant_id, venue_id) references hermes.venues(tenant_id, id) on delete restrict,
  check (
    (order_type = 'MARKET' and limit_price is null and stop_price is null)
    or (order_type = 'LIMIT' and limit_price is not null and stop_price is null)
    or (order_type = 'STOP_LIMIT' and limit_price is not null and stop_price is not null)
  )
);

create table hermes.approvals (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references hermes.tenants(id) on delete restrict,
  execution_id uuid not null,
  order_intent_id uuid not null,
  principal_id uuid not null references hermes.principals(id) on delete restrict,
  intent_digest text not null check (intent_digest ~ '^sha256:[a-f0-9]{64}$'),
  decision text not null check (decision in ('APPROVED', 'REJECTED')),
  comment text check (comment is null or length(comment) <= 1000),
  expires_at timestamptz not null,
  created_at timestamptz not null default clock_timestamp(),
  unique (tenant_id, id),
  unique (tenant_id, order_intent_id, principal_id),
  foreign key (tenant_id, execution_id) references hermes.executions(tenant_id, id) on delete restrict,
  foreign key (tenant_id, order_intent_id) references hermes.order_intents(tenant_id, id) on delete restrict,
  foreign key (tenant_id, principal_id) references hermes.tenant_memberships(tenant_id, principal_id) on delete restrict
);

create table hermes.venue_orders (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references hermes.tenants(id) on delete restrict,
  execution_id uuid not null,
  order_intent_id uuid not null,
  venue_id uuid not null,
  client_order_id text not null,
  venue_order_id text,
  transaction_hash text,
  status hermes.order_status not null default 'CREATED',
  request_digest text not null check (request_digest ~ '^sha256:[a-f0-9]{64}$'),
  acknowledgement jsonb,
  submitted_at timestamptz,
  created_at timestamptz not null default clock_timestamp(),
  updated_at timestamptz not null default clock_timestamp(),
  unique (tenant_id, id),
  unique (tenant_id, venue_id, client_order_id),
  foreign key (tenant_id, execution_id) references hermes.executions(tenant_id, id) on delete restrict,
  foreign key (tenant_id, order_intent_id) references hermes.order_intents(tenant_id, id) on delete restrict,
  foreign key (tenant_id, venue_id) references hermes.venues(tenant_id, id) on delete restrict
);

create table hermes.fills (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references hermes.tenants(id) on delete restrict,
  venue_order_id uuid not null,
  venue_fill_id text not null check (length(venue_fill_id) between 1 and 256),
  quantity numeric not null check (quantity > 0),
  price numeric not null check (price > 0),
  fee numeric not null check (fee >= 0),
  fee_currency text not null,
  transaction_hash text,
  occurred_at timestamptz not null,
  evidence jsonb not null,
  created_at timestamptz not null default clock_timestamp(),
  unique (tenant_id, id),
  unique (tenant_id, venue_order_id, venue_fill_id),
  foreign key (tenant_id, venue_order_id) references hermes.venue_orders(tenant_id, id) on delete restrict
);

create table hermes.circuit_breakers (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references hermes.tenants(id) on delete restrict,
  scope_type text not null check (scope_type in ('tenant', 'strategy', 'portfolio', 'venue', 'account', 'network', 'instrument')),
  scope_id text not null,
  state hermes.circuit_state not null,
  reason_code text not null,
  reason text,
  evidence_refs text[] not null default '{}',
  activated_by uuid references hermes.principals(id) on delete restrict,
  activated_at timestamptz,
  reset_by uuid references hermes.principals(id) on delete restrict,
  reset_at timestamptz,
  updated_at timestamptz not null default clock_timestamp(),
  unique (tenant_id, id),
  unique (tenant_id, scope_type, scope_id),
  foreign key (tenant_id, activated_by) references hermes.tenant_memberships(tenant_id, principal_id) on delete restrict,
  foreign key (tenant_id, reset_by) references hermes.tenant_memberships(tenant_id, principal_id) on delete restrict
);

create table hermes.idempotency_records (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references hermes.tenants(id) on delete restrict,
  principal_id uuid not null references hermes.principals(id) on delete restrict,
  method text not null,
  route text not null,
  key_hash text not null check (key_hash ~ '^sha256:[a-f0-9]{64}$'),
  request_digest text not null check (request_digest ~ '^sha256:[a-f0-9]{64}$'),
  state text not null check (state in ('RESERVED', 'COMPLETED', 'FAILED')),
  resource_type text,
  resource_id text,
  response_status integer check (response_status is null or response_status between 100 and 599),
  response_body jsonb,
  expires_at timestamptz not null,
  created_at timestamptz not null default clock_timestamp(),
  updated_at timestamptz not null default clock_timestamp(),
  unique (tenant_id, principal_id, method, route, key_hash),
  foreign key (tenant_id, principal_id) references hermes.tenant_memberships(tenant_id, principal_id) on delete restrict
);

create table hermes.audit_events (
  id uuid primary key default gen_random_uuid(),
  event_sequence bigint generated always as identity,
  tenant_id uuid not null references hermes.tenants(id) on delete restrict,
  occurred_at timestamptz not null,
  actor_type hermes.audit_actor_type not null,
  actor_id text not null,
  session_id_hash text check (session_id_hash is null or session_id_hash ~ '^sha256:[a-f0-9]{64}$'),
  action text not null,
  result hermes.audit_result not null,
  resource_type text not null,
  resource_id text not null,
  correlation_id uuid not null,
  causation_id uuid,
  idempotency_key_hash text check (idempotency_key_hash is null or idempotency_key_hash ~ '^sha256:[a-f0-9]{64}$'),
  payload_digest text not null check (payload_digest ~ '^sha256:[a-f0-9]{64}$'),
  previous_event_digest text check (previous_event_digest is null or previous_event_digest ~ '^sha256:[a-f0-9]{64}$'),
  event_digest text not null check (event_digest ~ '^sha256:[a-f0-9]{64}$'),
  evidence_refs text[] not null default '{}',
  runtime jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default clock_timestamp(),
  unique (tenant_id, id),
  unique (tenant_id, event_digest),
  check (previous_event_digest is null or previous_event_digest <> event_digest),
  foreign key (tenant_id, previous_event_digest)
    references hermes.audit_events(tenant_id, event_digest) on delete restrict
);

-- The application writes audit events only through this serialized append boundary.
create or replace function hermes.append_audit_event(
  p_tenant_id uuid,
  p_occurred_at timestamptz,
  p_actor_type hermes.audit_actor_type,
  p_actor_id text,
  p_session_id_hash text,
  p_action text,
  p_result hermes.audit_result,
  p_resource_type text,
  p_resource_id text,
  p_correlation_id uuid,
  p_causation_id uuid,
  p_idempotency_key_hash text,
  p_payload_digest text,
  p_previous_event_digest text,
  p_event_digest text,
  p_evidence_refs text[],
  p_runtime jsonb
)
returns uuid
language plpgsql
volatile
security definer
set search_path = pg_catalog, hermes, pg_temp
as $$
declare
  current_head text;
  head_count bigint;
  inserted_id uuid;
begin
  if hermes.current_tenant_id() is null
    or hermes.current_tenant_id() is distinct from p_tenant_id then
    raise exception 'audit tenant does not match transaction context' using errcode = '42501';
  end if;

  -- Serialize one tenant stream. Hash collisions can only serialize unrelated tenants;
  -- they cannot weaken isolation or chain integrity.
  perform pg_catalog.pg_advisory_xact_lock(
    pg_catalog.hashtextextended(p_tenant_id::text, 0)
  );

  select count(*), min(event.event_digest)
  into head_count, current_head
  from hermes.audit_events as event
  where event.tenant_id = p_tenant_id
    and not exists (
      select 1
      from hermes.audit_events as child
      where child.tenant_id = event.tenant_id
        and child.previous_event_digest = event.event_digest
    );

  if head_count = 0 then
    if p_previous_event_digest is not null then
      raise exception 'first audit event must have no predecessor' using errcode = '23514';
    end if;
  elsif head_count = 1 then
    if p_previous_event_digest is distinct from current_head then
      raise exception 'audit predecessor is not the current tenant head' using errcode = '23514';
    end if;
  else
    raise exception 'audit stream has multiple heads' using errcode = '23514';
  end if;

  insert into hermes.audit_events (
    tenant_id, occurred_at, actor_type, actor_id, session_id_hash, action, result,
    resource_type, resource_id, correlation_id, causation_id, idempotency_key_hash,
    payload_digest, previous_event_digest, event_digest, evidence_refs, runtime
  ) values (
    p_tenant_id, p_occurred_at, p_actor_type, p_actor_id, p_session_id_hash, p_action, p_result,
    p_resource_type, p_resource_id, p_correlation_id, p_causation_id, p_idempotency_key_hash,
    p_payload_digest, p_previous_event_digest, p_event_digest, p_evidence_refs, p_runtime
  )
  returning id into inserted_id;

  return inserted_id;
end
$$;

revoke all on function hermes.append_audit_event(
  uuid, timestamptz, hermes.audit_actor_type, text, text, text, hermes.audit_result,
  text, text, uuid, uuid, text, text, text, text, text[], jsonb
) from public;
grant execute on function hermes.append_audit_event(
  uuid, timestamptz, hermes.audit_actor_type, text, text, text, hermes.audit_result,
  text, text, uuid, uuid, text, text, text, text, text[], jsonb
) to hermes_api, hermes_worker;

-- Updated-at triggers only on mutable records.
create trigger principals_set_updated_at before update on hermes.principals
for each row execute function hermes.set_updated_at();
create trigger tenants_set_updated_at before update on hermes.tenants
for each row execute function hermes.set_updated_at();
create trigger memberships_set_updated_at before update on hermes.tenant_memberships
for each row execute function hermes.set_updated_at();
create trigger strategies_set_updated_at before update on hermes.strategies
for each row execute function hermes.set_updated_at();
create trigger portfolios_set_updated_at before update on hermes.portfolios
for each row execute function hermes.set_updated_at();
create trigger venues_set_updated_at before update on hermes.venues
for each row execute function hermes.set_updated_at();
create trigger executions_set_updated_at before update on hermes.executions
for each row execute function hermes.set_updated_at();
create trigger venue_orders_set_updated_at before update on hermes.venue_orders
for each row execute function hermes.set_updated_at();
create trigger circuit_breakers_set_updated_at before update on hermes.circuit_breakers
for each row execute function hermes.set_updated_at();
create trigger idempotency_set_updated_at before update on hermes.idempotency_records
for each row execute function hermes.set_updated_at();

-- Immutable evidence records reject UPDATE and DELETE even if a future grant is added accidentally.
do $$
declare
  table_name text;
begin
  foreach table_name in array array[
    'market_snapshots', 'agent_assessments', 'consensus_decisions', 'risk_evaluations',
    'order_intents', 'approvals', 'fills', 'audit_events'
  ]
  loop
    execute format(
      'create trigger %I_reject_mutation before update or delete on hermes.%I for each row execute function hermes.reject_mutation()',
      table_name,
      table_name
    );
  end loop;
end
$$;

-- Tenant isolation: enable and force RLS on every tenant-owned relation.
do $$
declare
  table_name text;
begin
  foreach table_name in array array[
    'tenants', 'tenant_memberships', 'strategies', 'portfolios', 'venues', 'market_snapshots',
    'agent_assessments', 'consensus_decisions', 'risk_evaluations', 'executions', 'order_intents',
    'approvals', 'venue_orders', 'fills', 'circuit_breakers', 'idempotency_records', 'audit_events'
  ]
  loop
    execute format('alter table hermes.%I enable row level security', table_name);
    execute format('alter table hermes.%I force row level security', table_name);
  end loop;
end
$$;

create policy tenant_isolation_tenants on hermes.tenants
  for all to hermes_api, hermes_worker
  using (id = hermes.current_tenant_id())
  with check (id = hermes.current_tenant_id());

-- Generic policies for relations with a tenant_id column.
do $$
declare
  table_name text;
begin
  foreach table_name in array array[
    'tenant_memberships', 'strategies', 'portfolios', 'venues', 'market_snapshots',
    'agent_assessments', 'consensus_decisions', 'risk_evaluations', 'executions', 'order_intents',
    'approvals', 'venue_orders', 'fills', 'circuit_breakers', 'idempotency_records', 'audit_events'
  ]
  loop
    execute format(
      'create policy tenant_isolation_%I on hermes.%I for all to hermes_api, hermes_worker using (tenant_id = hermes.current_tenant_id()) with check (tenant_id = hermes.current_tenant_id())',
      table_name,
      table_name
    );
    execute format(
      'create policy tenant_audit_read_%I on hermes.%I for select to hermes_auditor using (tenant_id = hermes.current_tenant_id())',
      table_name,
      table_name
    );
  end loop;
end
$$;

create policy tenant_audit_read_tenants on hermes.tenants
  for select to hermes_auditor
  using (id = hermes.current_tenant_id());

-- The identity role resolves one verified external subject through lookup_principal(),
-- then SET LOCAL app.principal_id before loading active memberships.
create policy identity_membership_lookup on hermes.tenant_memberships
  for select to hermes_identity
  using (
    principal_id = hermes.current_principal_id()
    and status = 'active'
  );

create policy identity_tenant_lookup on hermes.tenants
  for select to hermes_identity
  using (
    exists (
      select 1
      from hermes.tenant_memberships membership
      where membership.tenant_id = tenants.id
        and membership.principal_id = hermes.current_principal_id()
        and membership.status = 'active'
    )
  );

-- Request-time identities cannot enumerate or mutate the global principal table.
-- Provisioning and account-status changes require a separate control-plane identity.
grant select on hermes.tenants, hermes.tenant_memberships to hermes_identity;

-- Application grants. Authorization beyond tenant isolation remains in the API role/scope layer.
grant select on all tables in schema hermes to hermes_api, hermes_worker, hermes_auditor;
-- Principals are global identity records and are not directly accessible to request-time roles.
revoke all on hermes.principals from hermes_api, hermes_worker, hermes_identity, hermes_auditor;
grant insert on hermes.strategies, hermes.portfolios, hermes.venues, hermes.market_snapshots,
  hermes.agent_assessments, hermes.consensus_decisions, hermes.risk_evaluations,
  hermes.executions, hermes.order_intents, hermes.approvals, hermes.venue_orders,
  hermes.fills, hermes.circuit_breakers, hermes.idempotency_records
  to hermes_api, hermes_worker;
revoke insert on hermes.audit_events from hermes_api, hermes_worker;
grant update on hermes.strategies, hermes.portfolios, hermes.venues, hermes.executions,
  hermes.venue_orders, hermes.circuit_breakers, hermes.idempotency_records
  to hermes_api, hermes_worker;
grant insert, update, select on hermes.tenant_memberships to hermes_api;

-- The application roles do not receive DELETE on core records.
revoke delete on all tables in schema hermes from hermes_api, hermes_worker, hermes_auditor;

-- Indexes supporting RLS, workflow lookup, and reconciliation.
create index tenant_memberships_tenant_idx on hermes.tenant_memberships (tenant_id, status);
create index tenant_memberships_principal_idx on hermes.tenant_memberships (principal_id, status);
create index strategies_tenant_status_idx on hermes.strategies (tenant_id, status);
create index portfolios_tenant_status_idx on hermes.portfolios (tenant_id, status);
create index venues_tenant_status_idx on hermes.venues (tenant_id, status);
create index snapshots_tenant_strategy_created_idx on hermes.market_snapshots (tenant_id, strategy_id, created_at desc);
create index assessments_snapshot_idx on hermes.agent_assessments (tenant_id, snapshot_id);
create index decisions_strategy_created_idx on hermes.consensus_decisions (tenant_id, strategy_id, created_at desc);
create index risk_decision_idx on hermes.risk_evaluations (tenant_id, decision_id, created_at desc);
create index executions_state_idx on hermes.executions (tenant_id, state, updated_at);
create index executions_correlation_idx on hermes.executions (tenant_id, correlation_id);
create index intents_execution_idx on hermes.order_intents (tenant_id, execution_id);
create index venue_orders_execution_idx on hermes.venue_orders (tenant_id, execution_id, status);
create index venue_orders_external_idx on hermes.venue_orders (tenant_id, venue_id, venue_order_id);
create index fills_order_time_idx on hermes.fills (tenant_id, venue_order_id, occurred_at);
create index circuit_breakers_active_idx on hermes.circuit_breakers (tenant_id, scope_type, scope_id) where state = 'ACTIVE';
create index idempotency_expiry_idx on hermes.idempotency_records (expires_at);
create index audit_tenant_sequence_idx on hermes.audit_events (tenant_id, event_sequence);
create index audit_correlation_idx on hermes.audit_events (tenant_id, correlation_id, occurred_at);
create unique index audit_one_root_per_tenant_idx on hermes.audit_events (tenant_id)
  where previous_event_digest is null;
create unique index audit_one_successor_per_event_idx on hermes.audit_events (tenant_id, previous_event_digest)
  where previous_event_digest is not null;

-- Default privileges are intentionally not granted. Each new table requires explicit grants and RLS.
commit;
