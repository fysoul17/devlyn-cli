"""Tentative and committed parking-slot state."""


class SlotAllocator:
    def __init__(self, slots: list[str]) -> None:
        self._available = set(slots)
        self._tentative: dict[str, list[str]] = {}

    def claim(self, request_id: str, slot: str) -> bool:
        if slot not in self._available:
            return False
        self._available.remove(slot)
        self._tentative.setdefault(request_id, []).append(slot)
        return True

    def abort(self, request_id: str) -> list[str]:
        return self._tentative.pop(request_id, [])

    def restore(self, slots: list[str]) -> None:
        self._available.update(slots)

    def commit(self, request_id: str) -> None:
        self._tentative.pop(request_id, None)

    def available(self) -> list[str]:
        return sorted(self._available)
