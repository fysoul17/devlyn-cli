"""Dependent transcode queue built from the encoder feed."""

from encoder_feed import prepare_feed
from manifest_dedup import ManifestDedup


def run_queue(submissions: list[dict], existing: list[str] | None = None) -> dict:
    registry = ManifestDedup(existing)
    scheduled = registry.absorb(prepare_feed(submissions))
    return {
        "scheduled": [entry["id"] for entry in scheduled],
        "priorities": [entry["priority"] for entry in scheduled],
        "records": registry.manifest_ids(),
    }
