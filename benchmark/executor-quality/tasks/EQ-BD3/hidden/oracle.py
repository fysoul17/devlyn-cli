#!/usr/bin/env python3
"""Offline checks for synchronization behavior that depends on response classification."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path


INVARIANT = (
    "Catalog synchronization quarantines invalid response bodies without advancing "
    "its cursor or scheduling a retry, even when the response status is unavailable."
)


def load_sync(workdir: Path):
    sys.path.insert(0, str(workdir))
    try:
        sys.modules.pop("sync", None)
        sys.modules.pop("transport", None)
        return importlib.import_module("sync")
    finally:
        sys.path.pop(0)


def run_case(module, status: int, body: str) -> bool:
    catalog = module.CatalogSync([{"sku": "seed"}], cursor=7)
    before_items = list(catalog.items)
    try:
        result = catalog.ingest(status, body)
    except Exception:
        return False
    return (
        result == {"status": "quarantined", "cursor": 7}
        and catalog.items == before_items
        and catalog.cursor == 7
        and catalog.retry_count == 0
        and catalog.quarantine_count == 1
    )


def main() -> None:
    workdir = Path(sys.argv[1])
    module = load_sync(workdir)
    bad_json_success = run_case(module, 200, "{broken")
    bad_shape_unavailable = run_case(module, 503, '{"items": "not-a-list"}')
    print(
        json.dumps(
            {
                "manifestations": [
                    {
                        "id": "sync_bad_json_success",
                        "invariant": INVARIANT,
                        "passed": bad_json_success,
                    },
                    {
                        "id": "sync_bad_shape_unavailable",
                        "invariant": INVARIANT,
                        "passed": bad_shape_unavailable,
                    },
                ]
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
