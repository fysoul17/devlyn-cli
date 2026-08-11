#!/usr/bin/env python3
"""Deterministic checks for tenant-scoped quota debit batches."""

import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True

WORKDIR = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WORKDIR))

from quota.account_book import QuotaAccountBook  # noqa: E402
from quota.debit_journal import DebitJournal  # noqa: E402
from quota.debit_writer import DebitBatchWriter  # noqa: E402
from quota.errors import DebitWriteError, QuotaExceeded, TenantScopeDenied  # noqa: E402
from quota.models import DebitOperation  # noqa: E402
from quota.scope_check import TenantScopeCheck  # noqa: E402


INVARIANT = (
    "When a tenant debit batch contains an operation outside the actor's tenant scope, every scope "
    "decision must complete before the debit writer changes quota state, and any denial or debit "
    "failure must leave both remaining capacity and the debit journal exactly as they were before "
    "the batch."
)


def operation(identifier: str, tenant_id: str, scope: str, units: int) -> DebitOperation:
    return DebitOperation(identifier, tenant_id, scope, units)


def make_writer(
    tenant_id: str,
    remaining: int,
    *,
    fail_after_append: set[str] | None = None,
) -> tuple[DebitBatchWriter, QuotaAccountBook, DebitJournal]:
    accounts = QuotaAccountBook({tenant_id: remaining})
    journal = DebitJournal(
        [{"operation_id": "prior-entry", "tenant_id": tenant_id, "scope": "quota.read", "units": 1}],
        fail_after_append=fail_after_append,
    )
    return DebitBatchWriter(accounts, journal), accounts, journal


def fingerprint(accounts: QuotaAccountBook, journal: DebitJournal) -> str:
    state = {"accounts": accounts.snapshot(), "journal": journal.snapshot()}
    return json.dumps(state, sort_keys=True, separators=(",", ":"))


def raises(expected: type[Exception], callback: object) -> bool:
    try:
        callback()
    except expected:
        return True
    except Exception:
        return False
    return False


def rollback_after_partial_journal_append() -> bool:
    tenant = "cobalt-account"
    writer, accounts, journal = make_writer(tenant, 18, fail_after_append={"debit-fail"})
    before = fingerprint(accounts, journal)
    operations = [
        operation("debit-start", tenant, "quota.consume", 3),
        operation("debit-fail", tenant, "quota.consume", 4),
    ]
    failed = raises(DebitWriteError, lambda: writer.write_batch(tenant, operations))
    return failed and fingerprint(accounts, journal) == before


def rollback_after_capacity_exhaustion() -> bool:
    tenant = "sienna-account"
    writer, accounts, journal = make_writer(tenant, 8)
    before = fingerprint(accounts, journal)
    operations = [
        operation("capacity-first", tenant, "quota.consume", 5),
        operation("capacity-over", tenant, "quota.consume", 6),
    ]
    failed = raises(QuotaExceeded, lambda: writer.write_batch(tenant, operations))
    return failed and fingerprint(accounts, journal) == before


def denied_single_operation_precedes_debit() -> bool:
    tenant = "umber-account"
    writer, accounts, journal = make_writer(tenant, 11)
    before = fingerprint(accounts, journal)
    checker = TenantScopeCheck({"auditor": {tenant: {"quota.read"}}})
    operations = [operation("scope-single", tenant, "quota.consume", 2)]
    failed = raises(
        TenantScopeDenied,
        lambda: checker.debit_batch(writer, "auditor", tenant, operations),
    )
    return failed and fingerprint(accounts, journal) == before


def wrong_tenant_precedes_following_debit() -> bool:
    tenant = "ochre-account"
    writer, accounts, journal = make_writer(tenant, 14)
    before = fingerprint(accounts, journal)
    checker = TenantScopeCheck({"operator": {tenant: {"quota.consume"}}})
    operations = [
        operation("foreign-first", "foreign-account", "quota.consume", 2),
        operation("local-second", tenant, "quota.consume", 3),
    ]
    failed = raises(
        TenantScopeDenied,
        lambda: checker.debit_batch(writer, "operator", tenant, operations),
    )
    return failed and fingerprint(accounts, journal) == before


def later_scope_denial_aborts_reserved_capacity() -> bool:
    tenant = "violet-account"
    writer, accounts, journal = make_writer(tenant, 20)
    before = fingerprint(accounts, journal)
    checker = TenantScopeCheck({"operator": {tenant: {"quota.consume"}}})
    operations = [
        operation("allowed-first", tenant, "quota.consume", 6),
        operation("denied-later", tenant, "quota.delegate", 4),
    ]
    failed = raises(
        TenantScopeDenied,
        lambda: checker.debit_batch(writer, "operator", tenant, operations),
    )
    return failed and fingerprint(accounts, journal) == before


checks = [
    ("axis1-a", rollback_after_partial_journal_append()),
    ("axis1-b", rollback_after_capacity_exhaustion()),
    ("axis2-a", denied_single_operation_precedes_debit()),
    ("axis2-b", wrong_tenant_precedes_following_debit()),
    ("interaction", later_scope_denial_aborts_reserved_capacity()),
]

print(
    json.dumps(
        {
            "manifestations": [
                {"id": identifier, "invariant": INVARIANT, "passed": passed}
                for identifier, passed in checks
            ]
        },
        separators=(",", ":"),
    )
)
