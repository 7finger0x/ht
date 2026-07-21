#!/usr/bin/env python3
"""
Hermes Audit Chain Verifier
===========================
Standalone CLI for external auditors and operators to independently verify the
cryptographic predecessor-digest chain stored in hermes.audit_events.

The verifier checks:
  1. Every tenant stream has exactly one root event (predecessor_event_digest IS NULL).
  2. Every non-root event's declared predecessor_event_digest exists in the same tenant stream.
  3. The chain is a strict linear sequence with no forks (no event has more than one successor).
  4. There are no gaps (the chain is fully connected from root to head).
  5. Each event_digest uses the required sha256:<64 lowercase hex characters> format.

This tool does not recompute event digests from payload fields. Cryptographic
payload verification requires a separately versioned canonicalization contract.

Usage
-----
  # From a live PostgreSQL database (requires psycopg2)
  python scripts/verify_audit_chain.py \
      --dsn "postgresql://auditor@host/hermes" \
      --tenant-id <uuid>

  # From a CSV export (no database required)
  python scripts/verify_audit_chain.py \
      --csv audit_events_export.csv \
      --tenant-id <uuid>

  # Verify all tenants in a CSV
  python scripts/verify_audit_chain.py --csv audit_events_export.csv --all-tenants

Exit codes
----------
  0  All checks passed.
  1  One or more chain integrity violations found.
  2  Usage or I/O error.

Output
------
  Human-readable findings to stdout. Machine-readable JSON summary with
  --output-json path/to/report.json.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

_DIGEST_PATTERN = re.compile(r'^sha256:[a-f0-9]{64}$')


@dataclass
class AuditEvent:
    tenant_id: str
    event_id: str
    event_digest: str
    previous_event_digest: Optional[str]

    def is_root(self) -> bool:
        return self.previous_event_digest is None or self.previous_event_digest == ''


@dataclass
class ChainFinding:
    level: str  # 'ERROR' | 'WARN' | 'INFO'
    tenant_id: str
    message: str


@dataclass
class TenantReport:
    tenant_id: str
    total_events: int = 0
    roots: list[str] = field(default_factory=list)
    missing_predecessors: list[str] = field(default_factory=list)  # event_digests whose predecessor is absent
    fork_sources: list[str] = field(default_factory=list)          # event_digests that have >1 successor
    unreachable: list[str] = field(default_factory=list)           # event_ids not reachable from root
    invalid_digest_format: list[str] = field(default_factory=list) # event_ids with malformed digest
    passed: bool = False


# ---------------------------------------------------------------------------
# Chain verification
# ---------------------------------------------------------------------------

def verify_tenant_chain(events: list[AuditEvent]) -> TenantReport:
    tenant_id = events[0].tenant_id if events else 'unknown'
    report = TenantReport(tenant_id=tenant_id, total_events=len(events))

    if not events:
        report.passed = True
        return report

    # Build lookup structures
    by_digest: dict[str, AuditEvent] = {}
    for ev in events:
        # Validate digest format
        if not _DIGEST_PATTERN.match(ev.event_digest):
            report.invalid_digest_format.append(ev.event_id)
        if ev.event_digest in by_digest:
            # Duplicate digest — this is a fork violation
            report.fork_sources.append(ev.event_digest)
        else:
            by_digest[ev.event_digest] = ev

    # Count successors per digest to detect forks
    successor_count: dict[str, int] = defaultdict(int)
    for ev in events:
        if not ev.is_root():
            successor_count[ev.previous_event_digest] += 1  # type: ignore[index]

    # Roots
    roots = [ev for ev in events if ev.is_root()]
    report.roots = [ev.event_digest for ev in roots]

    # Missing predecessors
    for ev in events:
        if not ev.is_root():
            pred = ev.previous_event_digest
            if pred not in by_digest:
                report.missing_predecessors.append(ev.event_digest)

    # Forks: any digest that has more than one successor
    for digest, count in successor_count.items():
        if count > 1:
            report.fork_sources.append(digest)

    # Reachability: walk the chain from each root
    reachable: set[str] = set()
    if len(roots) == 1:
        current = roots[0].event_digest
        visited: set[str] = set()
        successors: dict[str, str] = {}  # predecessor_digest -> event_digest
        for ev in events:
            if not ev.is_root() and ev.previous_event_digest:
                successors[ev.previous_event_digest] = ev.event_digest
        node: Optional[str] = current
        while node and node not in visited:
            reachable.add(node)
            visited.add(node)
            node = successors.get(node)

    all_digests = {ev.event_digest for ev in events}
    report.unreachable = list(all_digests - reachable) if roots else list(all_digests)

    # Remove items that are already flagged as missing-predecessor or fork from unreachable
    # so the report surfaces the root cause rather than cascading effects.
    contaminated = set(report.missing_predecessors) | set(report.fork_sources)
    report.unreachable = [d for d in report.unreachable if d not in contaminated]

    report.passed = (
        len(report.roots) == 1
        and not report.missing_predecessors
        and not report.fork_sources
        and not report.invalid_digest_format
        and not report.unreachable
    )
    return report


# ---------------------------------------------------------------------------
# Data sources
# ---------------------------------------------------------------------------

def load_from_csv(path: Path, tenant_id: Optional[str]) -> dict[str, list[AuditEvent]]:
    """Load audit events from a CSV export.

    Expected columns (others are ignored):
      tenant_id, id, event_digest, previous_event_digest
    """
    by_tenant: dict[str, list[AuditEvent]] = defaultdict(list)
    with path.open(encoding='utf-8', newline='') as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            tid = row.get('tenant_id', '').strip()
            if not tid:
                continue
            if tenant_id and tid != tenant_id:
                continue
            prev = row.get('previous_event_digest', '').strip() or None
            by_tenant[tid].append(AuditEvent(
                tenant_id=tid,
                event_id=row.get('id', '').strip(),
                event_digest=row.get('event_digest', '').strip(),
                previous_event_digest=prev,
            ))
    return dict(by_tenant)


def load_from_db(dsn: str, tenant_id: Optional[str]) -> dict[str, list[AuditEvent]]:
    """Load audit events from PostgreSQL using psycopg2."""
    try:
        import psycopg2  # type: ignore
        import psycopg2.extras  # type: ignore
    except ImportError:
        print('ERROR: psycopg2 is required for --dsn mode.', file=sys.stderr)
        print('Install with: pip install psycopg2-binary', file=sys.stderr)
        sys.exit(2)

    query = """
        SELECT tenant_id::text, id::text, event_digest, previous_event_digest
        FROM hermes.audit_events
        {where}
        ORDER BY tenant_id, event_sequence
    """
    where = "WHERE tenant_id = %s" if tenant_id else ''
    params = (tenant_id,) if tenant_id else ()

    conn = psycopg2.connect(dsn)
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(query.format(where=where), params)
            rows = cur.fetchall()
    finally:
        conn.close()

    by_tenant: dict[str, list[AuditEvent]] = defaultdict(list)
    for row in rows:
        prev = row['previous_event_digest'] or None
        by_tenant[row['tenant_id']].append(AuditEvent(
            tenant_id=row['tenant_id'],
            event_id=row['id'],
            event_digest=row['event_digest'],
            previous_event_digest=prev,
        ))
    return dict(by_tenant)


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_report(report: TenantReport) -> None:
    status = 'PASS' if report.passed else 'FAIL'
    print(f"\nTenant {report.tenant_id}: {status}  ({report.total_events} events)")
    if report.passed:
        print('  Chain integrity: OK — single root, no gaps, no forks, no malformed digests.')
        return

    if len(report.roots) == 0:
        print('  ERROR: No root event found (all events have a predecessor).')
    elif len(report.roots) > 1:
        print(f'  ERROR: {len(report.roots)} root events found (expected exactly 1):')
        for r in report.roots[:5]:
            print(f'    {r}')

    if report.missing_predecessors:
        print(f'  ERROR: {len(report.missing_predecessors)} event(s) reference a missing predecessor:')
        for d in report.missing_predecessors[:5]:
            print(f'    {d}')

    if report.fork_sources:
        print(f'  ERROR: {len(report.fork_sources)} fork(s) detected (digest has multiple successors):')
        for d in report.fork_sources[:5]:
            print(f'    {d}')

    if report.invalid_digest_format:
        print(f'  ERROR: {len(report.invalid_digest_format)} event(s) have malformed digest format:')
        for eid in report.invalid_digest_format[:5]:
            print(f'    event id={eid}')

    if report.unreachable:
        print(f'  ERROR: {len(report.unreachable)} event(s) unreachable from root (gap detected):')
        for d in report.unreachable[:5]:
            print(f'    {d}')


def build_json_summary(reports: list[TenantReport]) -> dict[str, Any]:
    return {
        'summary': {
            'tenants_verified': len(reports),
            'tenants_passed': sum(1 for r in reports if r.passed),
            'tenants_failed': sum(1 for r in reports if not r.passed),
        },
        'tenants': [
            {
                'tenant_id': r.tenant_id,
                'passed': r.passed,
                'total_events': r.total_events,
                'root_count': len(r.roots),
                'missing_predecessor_count': len(r.missing_predecessors),
                'fork_count': len(r.fork_sources),
                'unreachable_count': len(r.unreachable),
                'invalid_digest_format_count': len(r.invalid_digest_format),
            }
            for r in reports
        ],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog='verify_audit_chain',
        description='Verify Hermes audit-chain structure and digest format for one or all tenants.',
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--dsn', metavar='DSN',
                        help='PostgreSQL connection string (requires psycopg2)')
    source.add_argument('--csv', metavar='FILE', type=Path,
                        help='Path to CSV export of hermes.audit_events')

    tenant = parser.add_mutually_exclusive_group(required=True)
    tenant.add_argument('--tenant-id', metavar='UUID',
                        help='Verify a single tenant stream')
    tenant.add_argument('--all-tenants', action='store_true',
                        help='Verify all tenant streams found in the data source')

    parser.add_argument('--output-json', metavar='FILE', type=Path,
                        help='Write machine-readable JSON summary to this file')
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    tenant_id: Optional[str] = None if args.all_tenants else args.tenant_id

    # Load data
    try:
        if args.csv:
            by_tenant = load_from_csv(args.csv, tenant_id)
        else:
            by_tenant = load_from_db(args.dsn, tenant_id)
    except (OSError, ValueError) as exc:
        print(f'ERROR: Failed to load audit events: {exc}', file=sys.stderr)
        return 2

    if not by_tenant:
        print('No audit events found for the specified tenant(s).')
        return 0

    reports: list[TenantReport] = []
    for tid, events in sorted(by_tenant.items()):
        report = verify_tenant_chain(events)
        reports.append(report)
        print_report(report)

    # JSON output
    if args.output_json:
        summary = build_json_summary(reports)
        args.output_json.write_text(json.dumps(summary, indent=2), encoding='utf-8')
        print(f'\nJSON summary written to {args.output_json}')

    # Final summary
    failed = [r for r in reports if not r.passed]
    total = len(reports)
    print(f'\n{total - len(failed)}/{total} tenant stream(s) passed chain verification.')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
