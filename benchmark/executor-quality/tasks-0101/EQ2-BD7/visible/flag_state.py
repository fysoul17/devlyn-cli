from __future__ import annotations

from collections.abc import Iterable

from errors import UnknownFlagError
from models import FlagMutationRequest, FlagRevision, MutationOutcome


class FlagRevisionChain:
    def __init__(self, flags: Iterable[tuple[str, str, bool]]) -> None:
        self._flags = {
            (environment, flag_key): {"enabled": enabled, "revision": 0}
            for flag_key, environment, enabled in flags
        }
        self._revisions: list[FlagRevision] = []

    def recorded(self, operation_key: str) -> MutationOutcome | None:
        for entry in reversed(self._revisions):
            if entry.operation_key == operation_key:
                return self._outcome(entry)
        return None

    def append(self, request: FlagMutationRequest) -> MutationOutcome:
        key = (request.environment, request.flag_key)
        current = self._flags.get(key)
        if current is None:
            raise UnknownFlagError(request.flag_key, request.environment)

        revision = int(current["revision"]) + 1
        current["revision"] = revision
        current["enabled"] = request.enabled
        entry = FlagRevision(
            operation_key=request.operation_key,
            flag_key=request.flag_key,
            environment=request.environment,
            actor_id=request.actor_id,
            revision=revision,
            enabled=request.enabled,
        )
        self._revisions.append(entry)
        return self._outcome(entry)

    def snapshot(self) -> dict[str, object]:
        flags = tuple(
            (environment, flag_key, int(value["revision"]), bool(value["enabled"]))
            for (environment, flag_key), value in sorted(self._flags.items())
        )
        return {"flags": flags, "revisions": tuple(self._revisions)}

    @staticmethod
    def _outcome(entry: FlagRevision) -> MutationOutcome:
        return MutationOutcome(
            status="changed",
            operation_key=entry.operation_key,
            flag_key=entry.flag_key,
            environment=entry.environment,
            revision=entry.revision,
            enabled=entry.enabled,
        )
