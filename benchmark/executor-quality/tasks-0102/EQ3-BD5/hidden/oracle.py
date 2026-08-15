#!/usr/bin/env python3
"""Evaluate the checkout fixture without writing to the supplied worktree."""

import json
import pathlib
import sys


def load(root, relative):
    namespace = {}
    exec((root / relative).read_text(encoding="utf-8"), namespace)
    return namespace


def evaluate(root):
    desk = load(root, "checkout/checkout_desk.py")
    scheduler = load(root, "scheduler/scene_change_scheduler.py")
    checks = load(root, "checks/damaged_prop_test.py")
    main, understudy, scene = "clock-main", "clock-understudy", "act-2"

    local_show = desk["open_show"]()
    local_result = desk["report_damage"](local_show, main, scene)

    remote_show = desk["open_show"]()
    remote_result = desk["report_damage"](remote_show, main, scene)
    try:
        sequence = scheduler["scene_sequence"](remote_show, scene)
        sequence_ready = scheduler["sequence_ready"](remote_show, scene)
    except (KeyError, TypeError):
        sequence = []
        sequence_ready = False

    repeated_show = desk["open_show"]()
    first = desk["report_damage"](repeated_show, main, scene)
    try:
        before_repeat = scheduler["scene_sequence"](repeated_show, scene)
    except (KeyError, TypeError):
        before_repeat = []
    second = desk["report_damage"](repeated_show, main, scene)
    try:
        after_repeat = scheduler["scene_sequence"](repeated_show, scene)
    except (KeyError, TypeError):
        after_repeat = []

    local_a = local_result["swapped"] and local_result["replacement"] == understudy
    props_for_scene = desk["checked_" + "out_props"]
    local_b = local_result["scene"] == scene and props_for_scene(local_show, scene) == [understudy, "book-red"]
    remote_a = remote_result["swapped"] and sequence == [understudy, "book-red"] and sequence_ready
    remote_b = (
        checks["damage_event_details"](remote_show, main, understudy, scene)
        and sequence == [understudy, "book-red"]
    )
    restore = (
        first["swapped"] and second["swapped"] and before_repeat == [understudy, "book-red"]
        and after_repeat == before_repeat
        and checks["damage_event_once"](repeated_show, main, understudy, scene)
    )
    return {
        "local-a": local_a,
        "local-b": local_b,
        "remote-a": remote_a,
        "remote-b": remote_b,
        "restore": restore,
    }


def main():
    values = evaluate(pathlib.Path(sys.argv[1]))
    print(json.dumps({"manifestations": [
        {"id": role, "passed": values[role]}
        for role in ("local-a", "local-b", "remote-a", "remote-b", "restore")
    ]}, separators=(",", ":")))


if __name__ == "__main__":
    main()
