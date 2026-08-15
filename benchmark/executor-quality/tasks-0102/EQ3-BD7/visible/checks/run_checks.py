#!/usr/bin/env python3
"""Run the visible reinspection checks from the task root."""

import pathlib


def load(path):
    namespace = {}
    exec(path.read_text(encoding="utf-8"), namespace)
    return namespace


def main():
    root = pathlib.Path(__file__).resolve().parents[1]
    recorder = load(root / "recorder" / "finding_recorder.py")
    helpers = load(root / "checks" / "fixture_helpers.py")
    local = load(root / "checks" / "local_clearance_test.py")
    closure = recorder["open_closure"]()
    receipt = recorder["clear_finding"](
        closure, "vent-drift", "samira", helpers["no_change"], helpers["no_change"]
    )
    assert local["local_receipt_is_clear"](receipt, closure, "vent-drift")


if __name__ == "__main__":
    main()
