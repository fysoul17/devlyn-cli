"""Manifest storage that consumes annotated encoder feeds."""


class ManifestDedup:
    def __init__(self, existing: list[str] | None = None) -> None:
        self._existing = set(existing or [])
        self._manifest_ids = list(existing or [])

    def absorb(self, feed: list[dict]) -> list[dict]:
        scheduled = [
            {
                "id": entry["id"],
                "asset": entry["asset"],
                "priority": entry["priority"],
            }
            for entry in feed
            if not entry["duplicate"] and entry["id"] not in self._existing
        ]
        self._existing.update(entry["id"] for entry in scheduled)
        self._manifest_ids.extend(entry["id"] for entry in scheduled)
        return scheduled

    def manifest_ids(self) -> list[str]:
        return list(self._manifest_ids)
