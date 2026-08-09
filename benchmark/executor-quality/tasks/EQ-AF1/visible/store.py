"""In-memory storage for submitted jobs."""

from __future__ import annotations

from typing import Any


class JobStore:
    """Record job results and suppress repeat processing."""

    def __init__(self) -> None:
        self.records: dict[str, dict[str, Any]] = {}
        self.total_processed = 0

    def submit_job(self, job_id: str, payload: Any) -> dict[str, Any]:
        """Return the existing result or create one record for ``job_id``."""
        if job_id in self.records:
            return self.records[job_id]

        result = {"sequence": self.total_processed + 1, "payload": payload}
        self.records[job_id] = result
        self.total_processed += 1
        return result
