#!/usr/bin/env python3
"""Check the hidden behavioral manifestations for EQ-MI1."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


INVARIANT = (
    "Handlers always execute in priority-descending order with ties broken by "
    "registration order, regardless of any additional filtering applied to which handlers run."
)


def load_bus(workdir: Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, workdir / "event_bus.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load event bus fixture")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def recorder(calls: list[str], label: str):
    def handle(_: Any) -> None:
        calls.append(label)

    return handle


def filtered_priority_order(workdir: Path) -> bool:
    bus = load_bus(workdir, "fixture_filtered")
    calls: list[str] = []
    try:
        bus.register("low", 10, recorder(calls, "low"), tags=["ops"])
        bus.register("high", 100, recorder(calls, "high"), tags=["billing"])
        bus.register("noise", 200, recorder(calls, "noise"), tags=["other"])
        bus.dispatch({"kind": "invoice"}, only_tags=["ops", "billing"])
    except (AttributeError, TypeError):
        return False
    return calls == ["high", "low"]


def unfiltered_tie_break(workdir: Path) -> bool:
    bus = load_bus(workdir, "fixture_unfiltered")
    calls: list[str] = []
    try:
        bus.register("one", 50, recorder(calls, "one"), tags=["alpha"])
        bus.register("two", 50, recorder(calls, "two"), tags=["beta"])
        bus.register("three", 50, recorder(calls, "three"), tags=["alpha"])
        bus.dispatch({"kind": "audit"})
    except (AttributeError, TypeError):
        return False
    return calls == ["one", "two", "three"]


def main() -> None:
    workdir = Path(sys.argv[1]).resolve()
    print(
        json.dumps(
            {
                "manifestations": [
                    {
                        "id": "filtered-priority-order",
                        "invariant": INVARIANT,
                        "passed": filtered_priority_order(workdir),
                    },
                    {
                        "id": "unfiltered-tie-break",
                        "invariant": INVARIANT,
                        "passed": unfiltered_tie_break(workdir),
                    },
                ]
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
