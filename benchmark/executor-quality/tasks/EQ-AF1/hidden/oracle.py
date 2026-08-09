#!/usr/bin/env python3
"""Check duplicate-submission behavior for EQ-AF1."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType


INVARIANT = (
    "A job_id is processed at most once: no sequence of submissions — single calls, "
    "repeated calls, or multiple entries within one batch call — ever creates a second "
    "stored record or a second side effect for the same job_id."
)


def load_store(workdir: Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, workdir / "store.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load job store fixture")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cross_call_duplicate(workdir: Path) -> bool:
    module = load_store(workdir, "fixture_cross_call")
    store = module.JobStore()
    original = store.submit_job("job-x", {"kind": "original"})
    try:
        results = store.submit_batch(
            [
                {"job_id": "job-x", "payload": {"kind": "replacement"}},
                {"job_id": "job-z", "payload": {"kind": "other"}},
            ]
        )
    except (AttributeError, KeyError, TypeError):
        return False
    return (
        len(results) == 2
        and results[0]
        == {"job_id": "job-x", "status": "duplicate", "result": original}
        and results[1].get("status") == "created"
        and store.records.get("job-x") is original
        and len(store.records) == 2
        and store.total_processed == 2
    )


def within_batch_duplicate(workdir: Path) -> bool:
    module = load_store(workdir, "fixture_within_batch")
    store = module.JobStore()
    try:
        results = store.submit_batch(
            [
                {"job_id": "job-y", "payload": {"kind": "first"}},
                {"job_id": "job-y", "payload": {"kind": "second"}},
            ]
        )
    except (AttributeError, KeyError, TypeError):
        return False
    return (
        len(results) == 2
        and [entry.get("status") for entry in results] == ["created", "duplicate"]
        and results[0].get("result") is results[1].get("result")
        and store.records.get("job-y") is results[0].get("result")
        and len(store.records) == 1
        and store.total_processed == 1
    )


def main() -> None:
    workdir = Path(sys.argv[1]).resolve()
    print(
        json.dumps(
            {
                "manifestations": [
                    {
                        "id": "cross-call-duplicate",
                        "invariant": INVARIANT,
                        "passed": cross_call_duplicate(workdir),
                    },
                    {
                        "id": "within-batch-duplicate",
                        "invariant": INVARIANT,
                        "passed": within_batch_duplicate(workdir),
                    },
                ]
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
