#!/usr/bin/env python3
"""Classify one pud-1 good/bad pair by its structural defect signature."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import runpy
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
NONCODING_ROOT = HERE.parent
SCHEMA = runpy.run_path(str(HERE / "packet-schema.py"))
PacketError = SCHEMA["PacketError"]
load_packet = SCHEMA["load_packet"]
validate_packet = SCHEMA["validate_packet"]


def task_constraint_projection(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "objective": task["objective"],
        "scope": {
            "may_change": task["scope"]["may_change"],
            "must_preserve": task["scope"]["must_preserve"],
        },
        "acceptance": [entry["observable"] for entry in task["acceptance"]],
    }


def structural_hash(task: dict[str, Any]) -> str:
    encoded = json.dumps(
        task_constraint_projection(task), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def align_tasks(
    good: dict[str, Any], bad: dict[str, Any]
) -> tuple[dict[str, str] | None, str | None]:
    good_tasks = good["tasks"]
    bad_tasks = bad["tasks"]
    good_ids = {task["id"] for task in good_tasks}
    bad_ids = {task["id"] for task in bad_tasks}
    if good_ids == bad_ids:
        return {task_id: task_id for task_id in bad_ids}, None

    good_by_hash: dict[str, list[str]] = {}
    bad_by_hash: dict[str, list[str]] = {}
    for task in good_tasks:
        good_by_hash.setdefault(structural_hash(task), []).append(task["id"])
    for task in bad_tasks:
        bad_by_hash.setdefault(structural_hash(task), []).append(task["id"])
    if set(good_by_hash) != set(bad_by_hash):
        return None, "non-edge structural hashes differ"
    if any(len(ids) != 1 for ids in (*good_by_hash.values(), *bad_by_hash.values())):
        return None, "non-edge structural hashes are not unique"
    return {
        bad_by_hash[digest][0]: good_by_hash[digest][0]
        for digest in sorted(good_by_hash)
    }, None


def ordering_signature(packet: dict[str, Any], identity: dict[str, str]) -> dict[str, Any]:
    order = [identity[task["id"]] for task in packet["tasks"]]
    dependencies = {
        identity[task["id"]]: [identity[dependency] for dependency in task["depends_on"]]
        for task in packet["tasks"]
    }
    return {"task_order": order, "depends_on": dependencies}


def constraint_signature(packet: dict[str, Any], identity: dict[str, str]) -> dict[str, Any]:
    return {
        "tasks": {
            identity[task["id"]]: task_constraint_projection(task)
            for task in packet["tasks"]
        },
        "project_acceptance": [entry["observable"] for entry in packet["project_acceptance"]],
    }


def classify(good: dict[str, Any], bad: dict[str, Any]) -> dict[str, str]:
    alignment, alignment_error = align_tasks(good, bad)
    if alignment is None:
        return {"family": "INELIGIBLE", "reason": f"task alignment failed: {alignment_error}"}
    good_identity = {task["id"]: task["id"] for task in good["tasks"]}
    ordering_changed = ordering_signature(good, good_identity) != ordering_signature(bad, alignment)
    constraints_changed = constraint_signature(good, good_identity) != constraint_signature(bad, alignment)
    if ordering_changed and not constraints_changed:
        return {"family": "ORDERING_MUTATION", "reason": "only the ordering signature changed"}
    if constraints_changed and not ordering_changed:
        return {
            "family": "CONTENT_CONSTRAINT_MUTATION",
            "reason": "only the content-constraint signature changed",
        }
    if ordering_changed:
        return {
            "family": "INELIGIBLE",
            "reason": "ordering and content-constraint signatures both changed",
        }
    return {"family": "INELIGIBLE", "reason": "neither structural signature changed"}


def packet_path(fixture_dir: Path, name: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name):
        raise PacketError(f"packet name must be a basename, got {name!r}")
    filename = name if name.endswith(".json") else f"{name}.json"
    return fixture_dir.resolve() / "packets" / filename


def classify_paths(fixture_dir: Path, good_name: str, bad_name: str) -> dict[str, str]:
    good = load_packet(packet_path(fixture_dir, good_name))
    bad = load_packet(packet_path(fixture_dir, bad_name))
    return classify(good, bad)


def synthetic_packet() -> dict[str, Any]:
    return {
        "schema_version": "pud-1",
        "project_acceptance": [{"id": "project", "observable": "Project behavior is visible."}],
        "tasks": [
            {
                "id": "first",
                "objective": "Make the first structural edit.",
                "depends_on": [],
                "context_refs": [
                    {"path": "src/a.py", "line_start": 1, "line_end": 1, "claim": "Narrative A."}
                ],
                "scope": {"may_change": ["src/a.py"], "must_preserve": ["public API"]},
                "acceptance": [{"id": "first-check", "observable": "The first edit is observable."}],
                "handoff": "Continue to the second task.",
            },
            {
                "id": "second",
                "objective": "Make the second structural edit.",
                "depends_on": ["first"],
                "context_refs": [
                    {"path": "src/b.py", "line_start": 1, "line_end": 1, "claim": "Narrative B."}
                ],
                "scope": {"may_change": ["src/b.py"], "must_preserve": ["file format"]},
                "acceptance": [{"id": "second-check", "observable": "The second edit is observable."}],
                "handoff": "Run the checks.",
            },
        ],
        "open_questions": [],
        "assumptions": [{"statement": "The structure is sufficient.", "evidence_refs": ["src/a.py:1"]}],
    }


def self_test() -> int:
    base = validate_packet(synthetic_packet())
    edge = copy.deepcopy(base)
    edge["tasks"] = [edge["tasks"][1], edge["tasks"][0]]
    edge["tasks"][0]["depends_on"] = []
    edge["tasks"][1]["depends_on"] = ["second"]

    content = copy.deepcopy(base)
    content["tasks"][1]["objective"] = "Make a materially different second edit."

    mixed = copy.deepcopy(edge)
    mixed["tasks"][0]["objective"] = "Make a materially different second edit."

    renamed = copy.deepcopy(edge)
    renamed["tasks"][0]["id"] = "renamed-second"
    renamed["tasks"][1]["id"] = "renamed-first"
    renamed["tasks"][1]["depends_on"] = ["renamed-second"]

    unalignable = copy.deepcopy(base)
    unalignable["tasks"][0]["id"] = "unknown-first"
    unalignable["tasks"][1]["id"] = "unknown-second"
    unalignable["tasks"][1]["depends_on"] = ["unknown-first"]
    unalignable["tasks"][1]["objective"] = "A changed task cannot be fallback-aligned."

    microcases = (
        ("edge-only swap", edge, "ORDERING_MUTATION"),
        ("content-only value", content, "CONTENT_CONSTRAINT_MUTATION"),
        ("mixed", mixed, "INELIGIBLE"),
        ("id-rename fallback", renamed, "ORDERING_MUTATION"),
        ("unalignable", unalignable, "INELIGIBLE"),
    )
    for name, candidate, expected in microcases:
        validate_packet(candidate)
        observed = classify(base, candidate)["family"]
        if observed != expected:
            raise AssertionError(f"{name}: expected {expected}, observed {observed}")

    canonical = (
        ("catalog-source-order", "good-a", "bad-dependency", "ORDERING_MUTATION"),
        ("catalog-source-order", "good-b", "bad-constraint", "CONTENT_CONSTRAINT_MUTATION"),
        ("credential-redaction", "good-b", "bad-constraint", "CONTENT_CONSTRAINT_MUTATION"),
        ("credential-redaction", "good-a", "bad-dependency", "INELIGIBLE"),
    )
    for fixture, good, bad, expected in canonical:
        observed = classify_paths(NONCODING_ROOT / "calibration" / fixture, good, bad)["family"]
        print(f"{fixture} {good}<->{bad}: {observed}")
        if observed != expected:
            raise AssertionError(f"{fixture} {good}<->{bad}: expected {expected}, observed {observed}")
    print("defect-family classifier self-test: PASS (5 microcases, 4 dev pairs)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-dir", type=Path)
    parser.add_argument("--good")
    parser.add_argument("--bad")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        if args.fixture_dir is not None or args.good is not None or args.bad is not None:
            parser.error("--self-test does not accept fixture arguments")
        try:
            return self_test()
        except (AssertionError, OSError, PacketError) as exc:
            print(f"SELF_TEST_MISMATCH: {exc}", file=sys.stderr)
            return 1
    if args.fixture_dir is None or args.good is None or args.bad is None:
        parser.error("--fixture-dir, --good, and --bad are required")
    try:
        result = classify_paths(args.fixture_dir, args.good, args.bad)
    except (OSError, PacketError) as exc:
        print(f"CLASSIFIER_ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
