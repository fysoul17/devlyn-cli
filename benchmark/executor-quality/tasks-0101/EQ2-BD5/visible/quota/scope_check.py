"""Tenant-scope checks that depend on the debit writer contract."""

from collections.abc import Iterable, Iterator

from .debit_writer import DebitBatchWriter
from .errors import TenantScopeDenied
from .models import DebitOperation


class TenantScopeCheck:
    def __init__(self, grants: dict[str, dict[str, set[str]]]) -> None:
        self._grants = grants

    def checked_operations(
        self,
        actor_id: str,
        tenant_id: str,
        operations: Iterable[DebitOperation],
    ) -> Iterator[DebitOperation]:
        allowed = self._grants.get(actor_id, {}).get(tenant_id, set())
        for operation in operations:
            if operation.tenant_id != tenant_id or operation.scope not in allowed:
                raise TenantScopeDenied(operation.operation_id)
            yield operation

    def debit_batch(
        self,
        writer: DebitBatchWriter,
        actor_id: str,
        tenant_id: str,
        operations: Iterable[DebitOperation],
    ) -> list[str]:
        guarded = self.checked_operations(actor_id, tenant_id, operations)
        return writer.write_batch(tenant_id, guarded)
