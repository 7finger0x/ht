from __future__ import annotations

import hashlib
import json
import socket
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator, Literal
from urllib.parse import urlparse

from .auth import AuthContext
from .config import settings


DatabaseBackend = Literal["sqlite", "postgres"]
SQLITE_PREFIX = "sqlite:///"
POSTGRES_PREFIXES = ("postgresql://", "postgres://")


def _database_backend() -> DatabaseBackend:
    if settings.database_url.startswith(SQLITE_PREFIX):
        return "sqlite"
    if settings.database_url.startswith(POSTGRES_PREFIXES):
        return "postgres"
    raise RuntimeError("Unsupported HERMES_DATABASE_URL. Expected sqlite:/// or postgresql:// URL.")


def _sqlite_path() -> Path:
    return Path(settings.database_url.removeprefix(SQLITE_PREFIX)).resolve()


DATABASE_BACKEND = _database_backend()
DB_PATH = _sqlite_path() if DATABASE_BACKEND == "sqlite" else None


def init_db() -> None:
    if DATABASE_BACKEND == "sqlite":
        assert DB_PATH is not None
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(DB_PATH) as conn:
            conn.executescript(
                """
                create table if not exists decisions (
                    tenant_id text,
                    principal_id text,
                    id text primary key,
                    instrument_id text not null,
                    strategy_id text not null,
                    portfolio_id text not null,
                    action text not null,
                    status text not null,
                    support_weight real not null,
                    weighted_confidence real not null,
                    quorum_weight real not null,
                    snapshot_json text not null,
                    assessments_json text not null,
                    created_at text not null,
                    digest text not null
                );
                create index if not exists decisions_tenant_created_idx on decisions (tenant_id, created_at desc);

                create table if not exists executions (
                    tenant_id text,
                    principal_id text,
                    id text primary key,
                    decision_id text not null,
                    venue_id text not null,
                    side text not null,
                    state text not null,
                    requested_notional real not null,
                    approved_notional real not null,
                    order_json text not null,
                    fill_json text not null,
                    risk_json text not null,
                    approval_json text,
                    transitions_json text not null default '[]',
                    created_at text not null,
                    updated_at text not null,
                    intent_digest text not null
                );
                create index if not exists executions_tenant_created_idx on executions (tenant_id, created_at desc);

                create table if not exists audit_events (
                    tenant_id text,
                    principal_id text,
                    id text primary key,
                    occurred_at text not null,
                    action text not null,
                    result text not null,
                    resource_type text not null,
                    resource_id text not null,
                    correlation_id text not null,
                    payload_json text not null
                );
                create index if not exists audit_events_tenant_occurred_idx on audit_events (tenant_id, occurred_at desc);

                create table if not exists idempotency_keys (
                    tenant_id text not null,
                    principal_id text not null,
                    operation text not null,
                    idempotency_key text not null,
                    request_hash text not null,
                    status_code integer not null,
                    response_json text not null,
                    created_at text not null,
                    primary key (tenant_id, operation, idempotency_key)
                );
                create index if not exists idempotency_keys_tenant_created_idx on idempotency_keys (tenant_id, created_at desc);

                create table if not exists circuit_breakers (
                    tenant_id text not null,
                    principal_id text not null,
                    circuit_breaker_id text primary key,
                    scope_type text not null,
                    scope_id text not null,
                    state text not null,
                    reason_code text not null,
                    reason text,
                    activated_by text,
                    activated_at text,
                    reset_by text,
                    reset_at text,
                    updated_at text not null
                );
                create unique index if not exists circuit_breakers_tenant_scope_idx on circuit_breakers (tenant_id, scope_type, scope_id);
                create index if not exists circuit_breakers_tenant_updated_idx on circuit_breakers (tenant_id, updated_at desc);
                """
            )
            _ensure_sqlite_column(conn, "decisions", "tenant_id", "text")
            _ensure_sqlite_column(conn, "decisions", "principal_id", "text")
            _ensure_sqlite_column(conn, "executions", "tenant_id", "text")
            _ensure_sqlite_column(conn, "executions", "principal_id", "text")
            _ensure_sqlite_column(conn, "executions", "approval_json", "text")
            _ensure_sqlite_column(conn, "executions", "transitions_json", "text")
            _ensure_sqlite_column(conn, "audit_events", "tenant_id", "text")
            _ensure_sqlite_column(conn, "audit_events", "principal_id", "text")
        return

    with get_connection() as conn:
        _init_postgres_schema(conn)


@contextmanager
def get_connection(auth_context: AuthContext | None = None) -> Iterator[Any]:
    if DATABASE_BACKEND == "sqlite":
        assert DB_PATH is not None
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return

    psycopg, dict_row = _load_psycopg()
    conn = psycopg.connect(settings.database_url, row_factory=dict_row)
    try:
        if auth_context is not None:
            conn.execute("select set_config('app.tenant_id', %s, true)", (auth_context.tenant_id,))
            conn.execute("select set_config('app.principal_id', %s, true)", (auth_context.principal_id,))
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def insert_decision(record: dict, auth_context: AuthContext) -> None:
    context = _require_auth_context(auth_context)
    snapshot_json = json.dumps(record["snapshot"])
    assessments_json = json.dumps(record["assessments"])
    if DATABASE_BACKEND == "sqlite":
        with get_connection(context) as conn:
            conn.execute(
                """
                insert into decisions (
                    tenant_id, principal_id, id, instrument_id, strategy_id, portfolio_id,
                    action, status, support_weight, weighted_confidence, quorum_weight,
                    snapshot_json, assessments_json, created_at, digest
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    context.tenant_id,
                    context.principal_id,
                    record["id"],
                    record["instrument_id"],
                    record["strategy_id"],
                    record["portfolio_id"],
                    record["action"],
                    record["status"],
                    record["support_weight"],
                    record["weighted_confidence"],
                    record["quorum_weight"],
                    snapshot_json,
                    assessments_json,
                    record["created_at"],
                    record["digest"],
                ),
            )
        return

    with get_connection(context) as conn:
        conn.execute(
            """
            insert into hermes_mvp.decisions (
                tenant_id, principal_id, id, instrument_id, strategy_id, portfolio_id,
                action, status, support_weight, weighted_confidence, quorum_weight,
                snapshot_json, assessments_json, created_at, digest
            ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s)
            """,
            (
                context.tenant_id,
                context.principal_id,
                record["id"],
                record["instrument_id"],
                record["strategy_id"],
                record["portfolio_id"],
                record["action"],
                record["status"],
                record["support_weight"],
                record["weighted_confidence"],
                record["quorum_weight"],
                snapshot_json,
                assessments_json,
                record["created_at"],
                record["digest"],
            ),
        )


def list_decisions(auth_context: AuthContext) -> list[dict]:
    context = _require_auth_context(auth_context)
    if DATABASE_BACKEND == "sqlite":
        with get_connection(context) as conn:
            rows = conn.execute(
                "select * from decisions where tenant_id = ? order by created_at desc",
                (context.tenant_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    with get_connection(context) as conn:
        rows = conn.execute("select * from hermes_mvp.decisions order by created_at desc").fetchall()
    return [dict(row) for row in rows]


def get_decision(decision_id: str, auth_context: AuthContext) -> dict | None:
    context = _require_auth_context(auth_context)
    if DATABASE_BACKEND == "sqlite":
        with get_connection(context) as conn:
            row = conn.execute(
                "select * from decisions where id = ? and tenant_id = ?",
                (decision_id, context.tenant_id),
            ).fetchone()
        return dict(row) if row else None

    with get_connection(context) as conn:
        row = conn.execute(
            "select * from hermes_mvp.decisions where id = %s",
            (decision_id,),
        ).fetchone()
    return dict(row) if row else None


def insert_execution(record: dict, auth_context: AuthContext) -> None:
    context = _require_auth_context(auth_context)
    order_json = json.dumps(record["order"])
    fill_json = json.dumps(record["fill"])
    risk_json = json.dumps(record["risk_evaluation"])
    approval_json = json.dumps(record["approval"]) if record.get("approval") is not None else None
    transitions_json = json.dumps(record.get("transitions", []))
    if DATABASE_BACKEND == "sqlite":
        with get_connection(context) as conn:
            conn.execute(
                """
                insert into executions (
                    tenant_id, principal_id, id, decision_id, venue_id, side, state,
                    requested_notional, approved_notional, order_json, fill_json,
                    risk_json, approval_json, transitions_json, created_at, updated_at, intent_digest
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    context.tenant_id,
                    context.principal_id,
                    record["id"],
                    record["decision_id"],
                    record["venue_id"],
                    record["side"],
                    record["state"],
                    record["requested_notional"],
                    record["approved_notional"],
                    order_json,
                    fill_json,
                    risk_json,
                    approval_json,
                    transitions_json,
                    record["created_at"],
                    record["updated_at"],
                    record["intent_digest"],
                ),
            )
        return

    with get_connection(context) as conn:
        conn.execute(
            """
            insert into hermes_mvp.executions (
                tenant_id, principal_id, id, decision_id, venue_id, side, state,
                requested_notional, approved_notional, order_json, fill_json,
                risk_json, approval_json, transitions_json, created_at, updated_at, intent_digest
            ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s, %s)
            """,
            (
                context.tenant_id,
                context.principal_id,
                record["id"],
                record["decision_id"],
                record["venue_id"],
                record["side"],
                record["state"],
                record["requested_notional"],
                record["approved_notional"],
                order_json,
                fill_json,
                risk_json,
                approval_json,
                transitions_json,
                record["created_at"],
                record["updated_at"],
                record["intent_digest"],
            ),
        )


def update_execution(record: dict, auth_context: AuthContext) -> None:
    context = _require_auth_context(auth_context)
    order_json = json.dumps(record["order"])
    fill_json = json.dumps(record["fill"])
    risk_json = json.dumps(record["risk_evaluation"])
    approval_json = json.dumps(record["approval"]) if record.get("approval") is not None else None
    transitions_json = json.dumps(record.get("transitions", []))
    if DATABASE_BACKEND == "sqlite":
        with get_connection(context) as conn:
            conn.execute(
                """
                update executions
                set principal_id = ?,
                    decision_id = ?,
                    venue_id = ?,
                    side = ?,
                    state = ?,
                    requested_notional = ?,
                    approved_notional = ?,
                    order_json = ?,
                    fill_json = ?,
                    risk_json = ?,
                    approval_json = ?,
                    transitions_json = ?,
                    updated_at = ?,
                    intent_digest = ?
                where id = ? and tenant_id = ?
                """,
                (
                    context.principal_id,
                    record["decision_id"],
                    record["venue_id"],
                    record["side"],
                    record["state"],
                    record["requested_notional"],
                    record["approved_notional"],
                    order_json,
                    fill_json,
                    risk_json,
                    approval_json,
                    transitions_json,
                    record["updated_at"],
                    record["intent_digest"],
                    record["id"],
                    context.tenant_id,
                ),
            )
        return

    with get_connection(context) as conn:
        conn.execute(
            """
            update hermes_mvp.executions
            set principal_id = %s,
                decision_id = %s,
                venue_id = %s,
                side = %s,
                state = %s,
                requested_notional = %s,
                approved_notional = %s,
                order_json = %s::jsonb,
                fill_json = %s::jsonb,
                risk_json = %s::jsonb,
                approval_json = %s::jsonb,
                transitions_json = %s::jsonb,
                updated_at = %s,
                intent_digest = %s
            where id = %s
            """,
            (
                context.principal_id,
                record["decision_id"],
                record["venue_id"],
                record["side"],
                record["state"],
                record["requested_notional"],
                record["approved_notional"],
                order_json,
                fill_json,
                risk_json,
                approval_json,
                transitions_json,
                record["updated_at"],
                record["intent_digest"],
                record["id"],
            ),
        )


def list_executions(auth_context: AuthContext) -> list[dict]:
    context = _require_auth_context(auth_context)
    if DATABASE_BACKEND == "sqlite":
        with get_connection(context) as conn:
            rows = conn.execute(
                "select * from executions where tenant_id = ? order by created_at desc",
                (context.tenant_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    with get_connection(context) as conn:
        rows = conn.execute("select * from hermes_mvp.executions order by created_at desc").fetchall()
    return [dict(row) for row in rows]


def get_execution(execution_id: str, auth_context: AuthContext) -> dict | None:
    context = _require_auth_context(auth_context)
    if DATABASE_BACKEND == "sqlite":
        with get_connection(context) as conn:
            row = conn.execute(
                "select * from executions where id = ? and tenant_id = ?",
                (execution_id, context.tenant_id),
            ).fetchone()
        return dict(row) if row else None

    with get_connection(context) as conn:
        row = conn.execute(
            "select * from hermes_mvp.executions where id = %s",
            (execution_id,),
        ).fetchone()
    return dict(row) if row else None


def get_circuit_breaker(scope_type: str, scope_id: str, auth_context: AuthContext) -> dict | None:
    context = _require_auth_context(auth_context)
    if DATABASE_BACKEND == "sqlite":
        with get_connection(context) as conn:
            row = conn.execute(
                "select * from circuit_breakers where tenant_id = ? and scope_type = ? and scope_id = ?",
                (context.tenant_id, scope_type, scope_id),
            ).fetchone()
        return dict(row) if row else None

    with get_connection(context) as conn:
        row = conn.execute(
            "select * from hermes_mvp.circuit_breakers where scope_type = %s and scope_id = %s",
            (scope_type, scope_id),
        ).fetchone()
    return dict(row) if row else None


def list_circuit_breakers(auth_context: AuthContext) -> list[dict]:
    context = _require_auth_context(auth_context)
    if DATABASE_BACKEND == "sqlite":
        with get_connection(context) as conn:
            rows = conn.execute(
                "select * from circuit_breakers where tenant_id = ? order by updated_at desc",
                (context.tenant_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    with get_connection(context) as conn:
        rows = conn.execute("select * from hermes_mvp.circuit_breakers order by updated_at desc").fetchall()
    return [dict(row) for row in rows]


def get_active_circuit_breakers(scope_keys: list[tuple[str, str]], auth_context: AuthContext) -> list[dict]:
    if not scope_keys:
        return []
    key_set = {(scope_type, scope_id) for scope_type, scope_id in scope_keys}
    return [
        row
        for row in list_circuit_breakers(auth_context)
        if row.get("state") == "ACTIVE" and (row.get("scope_type"), row.get("scope_id")) in key_set
    ]


def upsert_circuit_breaker(record: dict, auth_context: AuthContext) -> None:
    context = _require_auth_context(auth_context)
    if DATABASE_BACKEND == "sqlite":
        with get_connection(context) as conn:
            conn.execute(
                """
                insert into circuit_breakers (
                    tenant_id, principal_id, circuit_breaker_id, scope_type, scope_id,
                    state, reason_code, reason, activated_by, activated_at,
                    reset_by, reset_at, updated_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(tenant_id, scope_type, scope_id)
                do update set
                    principal_id = excluded.principal_id,
                    state = excluded.state,
                    reason_code = excluded.reason_code,
                    reason = excluded.reason,
                    activated_by = excluded.activated_by,
                    activated_at = excluded.activated_at,
                    reset_by = excluded.reset_by,
                    reset_at = excluded.reset_at,
                    updated_at = excluded.updated_at
                """,
                (
                    context.tenant_id,
                    context.principal_id,
                    record["circuit_breaker_id"],
                    record["scope_type"],
                    record["scope_id"],
                    record["state"],
                    record["reason_code"],
                    record.get("reason"),
                    record.get("activated_by"),
                    record.get("activated_at"),
                    record.get("reset_by"),
                    record.get("reset_at"),
                    record["updated_at"],
                ),
            )
        return

    with get_connection(context) as conn:
        conn.execute(
            """
            insert into hermes_mvp.circuit_breakers (
                tenant_id, principal_id, circuit_breaker_id, scope_type, scope_id,
                state, reason_code, reason, activated_by, activated_at,
                reset_by, reset_at, updated_at
            ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            on conflict (tenant_id, scope_type, scope_id)
            do update set
                principal_id = excluded.principal_id,
                state = excluded.state,
                reason_code = excluded.reason_code,
                reason = excluded.reason,
                activated_by = excluded.activated_by,
                activated_at = excluded.activated_at,
                reset_by = excluded.reset_by,
                reset_at = excluded.reset_at,
                updated_at = excluded.updated_at
            """,
            (
                context.tenant_id,
                context.principal_id,
                record["circuit_breaker_id"],
                record["scope_type"],
                record["scope_id"],
                record["state"],
                record["reason_code"],
                record.get("reason"),
                record.get("activated_by"),
                record.get("activated_at"),
                record.get("reset_by"),
                record.get("reset_at"),
                record["updated_at"],
            ),
        )


def append_audit_event(event: dict, auth_context: AuthContext) -> None:
    context = _require_auth_context(auth_context)
    payload_json = json.dumps(event["payload"])
    if DATABASE_BACKEND == "sqlite":
        with get_connection(context) as conn:
            conn.execute(
                """
                insert into audit_events (
                    tenant_id, principal_id, id, occurred_at, action, result,
                    resource_type, resource_id, correlation_id, payload_json
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    context.tenant_id,
                    context.principal_id,
                    event["id"],
                    event["occurred_at"],
                    event["action"],
                    event["result"],
                    event["resource_type"],
                    event["resource_id"],
                    event["correlation_id"],
                    payload_json,
                ),
            )
        return

    with get_connection(context) as conn:
        conn.execute(
            """
            insert into hermes_mvp.audit_events (
                tenant_id, principal_id, id, occurred_at, action, result,
                resource_type, resource_id, correlation_id, payload_json
            ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
            """,
            (
                context.tenant_id,
                context.principal_id,
                event["id"],
                event["occurred_at"],
                event["action"],
                event["result"],
                event["resource_type"],
                event["resource_id"],
                event["correlation_id"],
                payload_json,
            ),
        )


def list_audit_events(auth_context: AuthContext) -> list[dict]:
    context = _require_auth_context(auth_context)
    if DATABASE_BACKEND == "sqlite":
        with get_connection(context) as conn:
            rows = conn.execute(
                "select * from audit_events where tenant_id = ? order by occurred_at desc",
                (context.tenant_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    with get_connection(context) as conn:
        rows = conn.execute("select * from hermes_mvp.audit_events order by occurred_at desc").fetchall()
    return [dict(row) for row in rows]


def get_idempotency_record(idempotency_key: str, operation: str, auth_context: AuthContext) -> dict | None:
    context = _require_auth_context(auth_context)
    if DATABASE_BACKEND == "sqlite":
        with get_connection(context) as conn:
            row = conn.execute(
                "select * from idempotency_keys where tenant_id = ? and operation = ? and idempotency_key = ?",
                (context.tenant_id, operation, idempotency_key),
            ).fetchone()
        record = dict(row) if row else None
    else:
        with get_connection(context) as conn:
            row = conn.execute(
                "select * from hermes_mvp.idempotency_keys where operation = %s and idempotency_key = %s",
                (operation, idempotency_key),
            ).fetchone()
        record = dict(row) if row else None

    if record and isinstance(record.get("response_json"), str):
        record["response_json"] = json.loads(record["response_json"])
    return record


def store_idempotency_record(
    idempotency_key: str,
    operation: str,
    request_hash: str,
    status_code: int,
    response_payload: dict,
    auth_context: AuthContext,
) -> None:
    context = _require_auth_context(auth_context)
    response_json = json.dumps(response_payload)
    created_at = datetime.now(UTC).isoformat()
    if DATABASE_BACKEND == "sqlite":
        with get_connection(context) as conn:
            conn.execute(
                """
                insert or replace into idempotency_keys (
                    tenant_id, principal_id, operation, idempotency_key,
                    request_hash, status_code, response_json, created_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    context.tenant_id,
                    context.principal_id,
                    operation,
                    idempotency_key,
                    request_hash,
                    status_code,
                    response_json,
                    created_at,
                ),
            )
        return

    with get_connection(context) as conn:
        conn.execute(
            """
            insert into hermes_mvp.idempotency_keys (
                tenant_id, principal_id, operation, idempotency_key,
                request_hash, status_code, response_json, created_at
            ) values (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
            on conflict (tenant_id, operation, idempotency_key)
            do update set
                principal_id = excluded.principal_id,
                request_hash = excluded.request_hash,
                status_code = excluded.status_code,
                response_json = excluded.response_json,
                created_at = excluded.created_at
            """,
            (
                context.tenant_id,
                context.principal_id,
                operation,
                idempotency_key,
                request_hash,
                status_code,
                response_json,
                created_at,
            ),
        )


def hash_request_payload(payload: dict) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def check_database_health() -> dict[str, str]:
    try:
        with get_connection() as conn:
            conn.execute("select 1")
        return {"name": "database", "status": "ready", "detail": DATABASE_BACKEND}
    except Exception as exc:
        return {"name": "database", "status": "down", "detail": str(exc)}


def check_redis_health() -> dict[str, str]:
    if not settings.redis_url:
        return {"name": "redis", "status": "not_configured", "detail": "HERMES_REDIS_URL is unset"}

    parsed = urlparse(settings.redis_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 6379
    try:
        with socket.create_connection((host, port), timeout=2):
            return {"name": "redis", "status": "ready", "detail": f"tcp://{host}:{port}"}
    except OSError as exc:
        return {"name": "redis", "status": "down", "detail": str(exc)}


def _ensure_sqlite_column(conn: sqlite3.Connection, table_name: str, column_name: str, column_type: str) -> None:
    columns = {row[1] for row in conn.execute(f"pragma table_info({table_name})").fetchall()}
    if column_name not in columns:
        conn.execute(f"alter table {table_name} add column {column_name} {column_type}")


def _load_psycopg() -> tuple[Any, Any]:
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise RuntimeError("psycopg is required for postgresql database URLs. Install backend dependencies first.") from exc
    return psycopg, dict_row


def _init_postgres_schema(conn: Any) -> None:
    statements = [
        "create schema if not exists hermes_mvp",
        """
        create table if not exists hermes_mvp.decisions (
            tenant_id text not null,
            principal_id text not null,
            id text primary key,
            instrument_id text not null,
            strategy_id text not null,
            portfolio_id text not null,
            action text not null,
            status text not null,
            support_weight double precision not null,
            weighted_confidence double precision not null,
            quorum_weight double precision not null,
            snapshot_json jsonb not null,
            assessments_json jsonb not null,
            created_at timestamptz not null,
            digest text not null
        )
        """,
        "create index if not exists decisions_tenant_created_idx on hermes_mvp.decisions (tenant_id, created_at desc)",
        """
        create table if not exists hermes_mvp.executions (
            tenant_id text not null,
            principal_id text not null,
            id text primary key,
            decision_id text not null,
            venue_id text not null,
            side text not null,
            state text not null,
            requested_notional double precision not null,
            approved_notional double precision not null,
            order_json jsonb not null,
            fill_json jsonb not null,
            risk_json jsonb not null,
            approval_json jsonb,
            transitions_json jsonb not null default '[]'::jsonb,
            created_at timestamptz not null,
            updated_at timestamptz not null,
            intent_digest text not null
        )
        """,
        "alter table hermes_mvp.executions add column if not exists approval_json jsonb",
        "alter table hermes_mvp.executions add column if not exists transitions_json jsonb not null default '[]'::jsonb",
        "create index if not exists executions_tenant_created_idx on hermes_mvp.executions (tenant_id, created_at desc)",
        """
        create table if not exists hermes_mvp.audit_events (
            tenant_id text not null,
            principal_id text not null,
            id text primary key,
            occurred_at timestamptz not null,
            action text not null,
            result text not null,
            resource_type text not null,
            resource_id text not null,
            correlation_id text not null,
            payload_json jsonb not null
        )
        """,
        "create index if not exists audit_events_tenant_occurred_idx on hermes_mvp.audit_events (tenant_id, occurred_at desc)",
        """
        create table if not exists hermes_mvp.idempotency_keys (
            tenant_id text not null,
            principal_id text not null,
            operation text not null,
            idempotency_key text not null,
            request_hash text not null,
            status_code integer not null,
            response_json jsonb not null,
            created_at timestamptz not null,
            primary key (tenant_id, operation, idempotency_key)
        )
        """,
        "create index if not exists idempotency_keys_tenant_created_idx on hermes_mvp.idempotency_keys (tenant_id, created_at desc)",
        """
        create table if not exists hermes_mvp.circuit_breakers (
            tenant_id text not null,
            principal_id text not null,
            circuit_breaker_id text primary key,
            scope_type text not null,
            scope_id text not null,
            state text not null,
            reason_code text not null,
            reason text,
            activated_by text,
            activated_at timestamptz,
            reset_by text,
            reset_at timestamptz,
            updated_at timestamptz not null
        )
        """,
        "create unique index if not exists circuit_breakers_tenant_scope_idx on hermes_mvp.circuit_breakers (tenant_id, scope_type, scope_id)",
        "create index if not exists circuit_breakers_tenant_updated_idx on hermes_mvp.circuit_breakers (tenant_id, updated_at desc)",
        """
        do $$
        declare
            table_name text;
            policy_name text;
        begin
            foreach table_name in array array['decisions', 'executions', 'audit_events', 'idempotency_keys', 'circuit_breakers']
            loop
                execute format('alter table hermes_mvp.%I enable row level security', table_name);
                execute format('alter table hermes_mvp.%I force row level security', table_name);
                policy_name := 'tenant_isolation_' || table_name;
                if not exists (
                    select 1
                    from pg_policies
                    where schemaname = 'hermes_mvp'
                      and tablename = table_name
                      and policyname = policy_name
                ) then
                    execute format(
                        'create policy %I on hermes_mvp.%I for all using (tenant_id = current_setting(''app.tenant_id'', true)) with check (tenant_id = current_setting(''app.tenant_id'', true))',
                        policy_name,
                        table_name
                    );
                end if;
            end loop;
        end
        $$
        """,
    ]
    for statement in statements:
        conn.execute(statement)


def _require_auth_context(auth_context: AuthContext | None) -> AuthContext:
    if auth_context is None:
        raise RuntimeError("Authenticated request context is required for data access.")
    return auth_context
