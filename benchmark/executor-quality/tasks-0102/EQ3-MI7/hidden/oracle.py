#!/usr/bin/env python3
"""Evaluate the pass fixture without writing to the supplied worktree."""

import copy
import json
import pathlib
import sys


def load(root, relative):
    namespace = {}
    exec((root / relative).read_text(encoding="utf-8"), namespace)
    return namespace


def prepare(issuer, scanner, pass_id, price, scheduled_windows):
    pass_record = issuer["issue_pass"](pass_id, price, scheduled_windows)
    for window in ("morning", "afternoon"):
        if not scanner["scan_pass"](pass_record, window):
            raise RuntimeError("fixture scan was refused")
    duplicate_tap = scanner["scan_pass"](pass_record, "morning")
    return pass_record, duplicate_tap


def evaluate(root):
    issuer = load(root, "issuer/pass_issuer.py")
    scanner = load(root, "gates/gate_scanner.py")
    weather = load(root, "checks/weather_refund_test.py")

    local_pass = issuer["issue_pass"]("local-7", 240, 4)
    local_result = issuer["close_pass"](local_pass)

    remote_pass, remote_duplicate_tap = prepare(issuer, scanner, "ridge-9", 360, 5)
    remote_before_uses = copy.deepcopy(remote_pass["uses"])
    remote_price = remote_pass["price"]
    remote_scheduled_windows = copy.deepcopy(remote_pass["scheduled_windows"])
    remote_expected_windows = copy.deepcopy(scanner["scanned_windows"](remote_pass))
    remote_result = issuer["close_pass"](remote_pass)

    restored_pass, restored_duplicate_tap = prepare(issuer, scanner, "summit-77", 500, 5)
    restored_before_uses = copy.deepcopy(restored_pass["uses"])
    restored_price = restored_pass["price"]
    restored_scheduled_windows = copy.deepcopy(restored_pass["scheduled_windows"])
    restored_windows = copy.deepcopy(scanner["scanned_windows"](restored_pass))
    restored_expected = weather["expected_credit"](
        restored_price, restored_scheduled_windows, restored_windows
    )
    invalidations = "invalidation" + "s"
    first = issuer["close_pass"](restored_pass)
    second = issuer["close_pass"](restored_pass)
    denied_after_close = scanner["scan_pass"](restored_pass, "evening")

    local_a = local_result["closed"] and not local_pass["active"]
    local_b = (
        local_result["pass_id"] == "local-7"
        and local_result["amount"] == local_pass["price"]
        and len(local_pass["refunds"]) == 1
    )
    remote_a = (
        not remote_duplicate_tap and scanner["single_use_windows"](remote_pass)
        and remote_pass["uses"] == remote_before_uses
        and remote_result.get("used_windows") == remote_expected_windows
    )
    remote_b = weather["matching_credit"](
        remote_result,
        remote_price,
        remote_scheduled_windows,
        remote_expected_windows,
    )
    expected_refund = {
        "pass_id": "summit-77",
        "amount": restored_expected,
        "used_windows": restored_windows,
    }
    restore = (
        first["amount"] == restored_expected
        and second["amount"] == restored_expected
        and restored_pass["refunds"] == [expected_refund]
        and restored_pass[invalidations] == [{"pass_id": "summit-77"}]
        and restored_pass["uses"] == restored_before_uses
        and not restored_pass["active"]
        and not denied_after_close
        and not restored_duplicate_tap
        and scanner["single_use_windows"](restored_pass)
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
