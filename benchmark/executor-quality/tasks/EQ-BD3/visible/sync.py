"""Catalog synchronization that depends on transport classification."""

from transport import InvalidPayload, UpstreamUnavailable, classify_response


class CatalogSync:
    def __init__(self, items: list[dict] | None = None, cursor: int = 0):
        self.items = list(items or [])
        self.cursor = cursor
        self.retry_count = 0
        self.quarantine_count = 0

    def ingest(self, status: int, body: str) -> dict:
        try:
            items = classify_response(status, body)
        except InvalidPayload:
            self.quarantine_count += 1
            return {"status": "quarantined", "cursor": self.cursor}
        except UpstreamUnavailable:
            self.retry_count += 1
            return {"status": "retry", "cursor": self.cursor}

        self.items = items
        self.cursor += 1
        return {"status": "applied", "cursor": self.cursor}

    def snapshot(self) -> dict:
        return {
            "items": list(self.items),
            "cursor": self.cursor,
            "retry_count": self.retry_count,
            "quarantine_count": self.quarantine_count,
        }
