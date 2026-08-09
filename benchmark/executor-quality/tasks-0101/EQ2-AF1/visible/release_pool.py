"""Returned slots awaiting reuse by the allocator."""


class ReleasePool:
    def __init__(self) -> None:
        self._entries: list[tuple[int, list[str]]] = []

    def deposit(self, failed_arrival: int, slots: list[str]) -> None:
        self._entries.append((failed_arrival, list(slots)))

    def collect_before(self, arrival: int) -> list[str]:
        ready = [slots for failed, slots in self._entries if failed < arrival]
        self._entries = [entry for entry in self._entries if entry[0] >= arrival]
        return [slot for slots in ready for slot in slots]

    def collect_all(self) -> list[str]:
        slots = [slot for _, returned in self._entries for slot in returned]
        self._entries.clear()
        return slots
