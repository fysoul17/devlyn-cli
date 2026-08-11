"""Published conflict threads for meeting slot requests."""

from __future__ import annotations

from models import Conflict, ConflictReport


class ConflictReporter:
    def __init__(self) -> None:
        self._threads: dict[str, list[tuple[int, ConflictReport]]] = {}
        self._notification_count = 0

    def find(self, request_id: str, calendar_revision: int) -> ConflictReport | None:
        """Find a report published against this calendar snapshot."""

        for revision, report in self._threads.get(request_id, ()):
            if revision == calendar_revision:
                return report
        return None

    def publish(
        self,
        request_id: str,
        calendar_revision: int,
        conflict: Conflict,
    ) -> ConflictReport:
        report = ConflictReport(
            request_id,
            conflict.reason,
            conflict.source_index,
            calendar_revision,
        )
        self._threads.setdefault(request_id, []).append((calendar_revision, report))
        self._notification_count += 1
        return report

    def reports(self, request_id: str) -> tuple[ConflictReport, ...]:
        return tuple(report for _, report in self._threads.get(request_id, ()))

    @property
    def notification_count(self) -> int:
        return self._notification_count
