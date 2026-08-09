"""Tentative and committed state for seats."""


class SeatMap:
    def __init__(self, seats: list[str]) -> None:
        self._available = set(seats)
        self._held: dict[str, list[str]] = {}
        self._assigned: dict[str, list[str]] = {}

    def hold(self, request_id: str, seat: str) -> bool:
        if seat not in self._available:
            return False
        self._available.remove(seat)
        self._held.setdefault(request_id, []).append(seat)
        return True

    def release(self, request_id: str) -> None:
        self._available.update(self._held.pop(request_id, []))

    def commit(self, request_id: str) -> None:
        self._assigned[request_id] = self._held.pop(request_id, [])

    def assignments(self) -> dict[str, list[str]]:
        return {key: list(value) for key, value in sorted(self._assigned.items())}

    def available(self) -> list[str]:
        return sorted(self._available)
