#!/usr/bin/env python3
"""Check aggregate replica failure precedence for EQ-AF3."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType


INVARIANT = (
    "When all replica reads fail, aggregate failure follows a fixed precedence: "
    "ReplicaUnavailable outranks CorruptReplica, which outranks RecordMissing, "
    "independent of reader order."
)


def load_replicas(workdir: Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, workdir / "replicas.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load replica fixture")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def outcome(module: ModuleType, readers: list[object]) -> str:
    if not hasattr(module, "read_from_replicas"):
        return "absent"
    try:
        module.read_from_replicas(readers)
    except module.ReplicaUnavailable:
        return "offline"
    except module.CorruptReplica:
        return "corrupt"
    except module.RecordMissing:
        return "missing"
    return "record"


def outage_first(workdir: Path) -> bool:
    module = load_replicas(workdir, "fixture_af3_first")

    def unavailable() -> object:
        raise module.ReplicaUnavailable("down")

    def missing() -> object:
        return None

    return outcome(module, [unavailable, missing]) == "offline"


def outage_late(workdir: Path) -> bool:
    module = load_replicas(workdir, "fixture_af3_late")

    def missing() -> object:
        return None

    def corrupt() -> object:
        return {"version": 9}

    def unavailable() -> object:
        raise module.ReplicaUnavailable("down")

    return outcome(module, [missing, corrupt, unavailable]) == "offline"


def main() -> None:
    workdir = Path(sys.argv[1]).resolve()
    print(
        json.dumps(
            {
                "manifestations": [
                    {
                        "id": "af3-outage-first",
                        "invariant": INVARIANT,
                        "passed": outage_first(workdir),
                    },
                    {
                        "id": "af3-outage-late",
                        "invariant": INVARIANT,
                        "passed": outage_late(workdir),
                    },
                ]
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
