\set ON_ERROR_STOP on

create role hermes_identity_login login inherit nobypassrls password 'identity_test_only';
grant hermes_identity to hermes_identity_login;
create role hermes_api_login login inherit nobypassrls password 'api_test_only';
grant hermes_api to hermes_api_login;

insert into hermes.principals (id, provider, external_subject, display_name)
values
  ('10000000-0000-0000-0000-000000000001', 'privy', 'did:privy:one', 'One'),
  ('10000000-0000-0000-0000-000000000002', 'privy', 'did:privy:two', 'Two');

insert into hermes.tenants (id, name, deployment_mode)
values
  ('20000000-0000-0000-0000-000000000001', 'Tenant One', 'managed'),
  ('20000000-0000-0000-0000-000000000002', 'Tenant Two', 'managed');

insert into hermes.tenant_memberships (tenant_id, principal_id, role)
values
  ('20000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', 'trader'),
  ('20000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000002', 'trader');

insert into hermes.strategies (tenant_id, name, configuration_version, created_by)
values (
  '20000000-0000-0000-0000-000000000001',
  'Valid strategy',
  '1',
  '10000000-0000-0000-0000-000000000001'
);

do $$
declare
  rejected boolean := false;
begin
  begin
    insert into hermes.strategies (tenant_id, name, configuration_version, created_by)
    values (
      '20000000-0000-0000-0000-000000000001',
      'Cross-tenant actor',
      '1',
      '10000000-0000-0000-0000-000000000002'
    );
  exception when foreign_key_violation then
    rejected := true;
  end;
  if not rejected then
    raise exception 'cross-tenant principal attribution was accepted';
  end if;
end
$$;

do $$
declare
  root_digest text := 'sha256:' || repeat('a', 64);
  child_digest text := 'sha256:' || repeat('b', 64);
  rejected boolean;
begin
  insert into hermes.audit_events (
    tenant_id, occurred_at, actor_type, actor_id, action, result,
    resource_type, resource_id, correlation_id, payload_digest, event_digest
  ) values (
    '20000000-0000-0000-0000-000000000001', clock_timestamp(), 'system', 'test',
    'test.root', 'SUCCESS', 'test', 'root', gen_random_uuid(),
    'sha256:' || repeat('1', 64), root_digest
  );

  rejected := false;
  begin
    insert into hermes.audit_events (
      tenant_id, occurred_at, actor_type, actor_id, action, result,
      resource_type, resource_id, correlation_id, payload_digest, event_digest
    ) values (
      '20000000-0000-0000-0000-000000000001', clock_timestamp(), 'system', 'test',
      'test.second_root', 'SUCCESS', 'test', 'second-root', gen_random_uuid(),
      'sha256:' || repeat('2', 64), 'sha256:' || repeat('c', 64)
    );
  exception when unique_violation then
    rejected := true;
  end;
  if not rejected then
    raise exception 'second audit root was accepted';
  end if;

  insert into hermes.audit_events (
    tenant_id, occurred_at, actor_type, actor_id, action, result,
    resource_type, resource_id, correlation_id, payload_digest,
    previous_event_digest, event_digest
  ) values (
    '20000000-0000-0000-0000-000000000001', clock_timestamp(), 'system', 'test',
    'test.child', 'SUCCESS', 'test', 'child', gen_random_uuid(),
    'sha256:' || repeat('3', 64), root_digest, child_digest
  );

  rejected := false;
  begin
    insert into hermes.audit_events (
      tenant_id, occurred_at, actor_type, actor_id, action, result,
      resource_type, resource_id, correlation_id, payload_digest,
      previous_event_digest, event_digest
    ) values (
      '20000000-0000-0000-0000-000000000001', clock_timestamp(), 'system', 'test',
      'test.fork', 'SUCCESS', 'test', 'fork', gen_random_uuid(),
      'sha256:' || repeat('4', 64), root_digest, 'sha256:' || repeat('d', 64)
    );
  exception when unique_violation then
    rejected := true;
  end;
  if not rejected then
    raise exception 'audit fork was accepted';
  end if;

  rejected := false;
  begin
    insert into hermes.audit_events (
      tenant_id, occurred_at, actor_type, actor_id, action, result,
      resource_type, resource_id, correlation_id, payload_digest,
      previous_event_digest, event_digest
    ) values (
      '20000000-0000-0000-0000-000000000001', clock_timestamp(), 'system', 'test',
      'test.gap', 'SUCCESS', 'test', 'gap', gen_random_uuid(),
      'sha256:' || repeat('5', 64),
      'sha256:' || repeat('e', 64),
      'sha256:' || repeat('f', 64)
    );
  exception when foreign_key_violation then
    rejected := true;
  end;
  if not rejected then
    raise exception 'missing audit predecessor was accepted';
  end if;

  rejected := false;
  begin
    insert into hermes.audit_events (
      tenant_id, occurred_at, actor_type, actor_id, action, result,
      resource_type, resource_id, correlation_id, payload_digest,
      previous_event_digest, event_digest
    ) values (
      '20000000-0000-0000-0000-000000000001', clock_timestamp(), 'system', 'test',
      'test.self', 'SUCCESS', 'test', 'self', gen_random_uuid(),
      'sha256:' || repeat('6', 64),
      'sha256:' || repeat('7', 64),
      'sha256:' || repeat('7', 64)
    );
  exception when check_violation then
    rejected := true;
  end;
  if not rejected then
    raise exception 'audit self-link was accepted';
  end if;
end
$$;

select case
  when (select count(*) from hermes.strategies) = 1
    and (select count(*) from hermes.audit_events) = 2
  then 'postgres structural security assertions: PASS'
  else 'postgres structural security assertions: FAIL'
end as result;
