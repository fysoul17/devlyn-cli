"""Read records from storage replicas."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


Reader = Callable[[], object]


class ReplicaUnavailable(RuntimeError):
    """A replica could not be contacted."""


class CorruptReplica(ValueError):
    """A replica returned an unusable record."""


class RecordMissing(LookupError):
    """A replica does not contain the requested record."""


def read_replica(reader: Reader) -> dict[str, Any]:
    """Normalize one replica result or raise its failure category."""
    result = reader()
    if result is None:
        raise RecordMissing("record missing")
    if not isinstance(result, dict) or "value" not in result:
        raise CorruptReplica("invalid record")
    return result
