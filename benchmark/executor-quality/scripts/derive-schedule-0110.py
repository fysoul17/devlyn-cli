#!/usr/bin/env python3
"""Derive and mechanically verify the iter-0110 block-crossover schedule."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import random
import sys
from collections import Counter, defaultdict


REPO = pathlib.Path(__file__).resolve().parents[3]
MANIFEST = pathlib.Path.home() / ".local/share/nx01/iter0102/freeze/candidate-manifest.json"
MANIFEST_SHA256 = "80f0a12ddb6df006c4137ecbc96c557742f8bbe74b0cacf65466c3af6dcd8887"
SEED = 20260825
K = 8
DEFAULT_SWEEPS = 2
MATRIX_ENGINES = ("claude-opus-5", "claude-opus-4-8")
SONNET = "claude-sonnet-5"
ENGINES = (*MATRIX_ENGINES, SONNET)
DEFAULT_OUT = REPO / "docs/specs/iter0110/schedule.json"


class ScheduleViolation(ValueError):
    """A named failure of a frozen schedule invariant."""


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sealed_task_ids() -> list[str]:
    if sha256(MANIFEST) != MANIFEST_SHA256:
        raise ScheduleViolation("manifest-digest-mismatch")
    try:
        payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
        tasks = payload["tasks"]
    except (OSError, TypeError, ValueError, KeyError) as exc:
        raise ScheduleViolation(f"manifest-unreadable:{exc}") from exc
    if not isinstance(tasks, dict) or len(tasks) != 32 or not all(
        isinstance(task_id, str) and task_id for task_id in tasks
    ):
        raise ScheduleViolation("manifest-task-ids-invalid")
    return sorted(tasks)


def task_entries(task_ids: list[str]) -> list[dict[str, object]]:
    if len(task_ids) != K:
        raise ScheduleViolation("session-k-mismatch")
    return [
        {
            "slot": f"t{position}",
            "task_id": task_id,
            "position_index": position,
            "position_class": "EARLY" if position <= K // 2 else "LATE",
        }
        for position, task_id in enumerate(task_ids, start=1)
    ]


def build_schedule(sweeps: int = DEFAULT_SWEEPS) -> dict[str, object]:
    if not isinstance(sweeps, int) or isinstance(sweeps, bool) or sweeps < 1:
        raise ScheduleViolation("sweeps-must-be-positive-integer")
    task_ids = sealed_task_ids()
    rng = random.Random(SEED)
    blocks: list[dict[str, object]] = []
    sessions: list[dict[str, object]] = []
    replicate_index = 0
    for sweep_id in range(1, sweeps + 1):
        shuffled = task_ids[:]
        rng.shuffle(shuffled)
        for block_id, start in enumerate(range(0, len(shuffled), K), start=1):
            block = shuffled[start : start + K]
            replicate_index += 1
            replicate_id = f"s{sweep_id:02d}-b{block_id:02d}"
            blocks.append(
                {
                    "sweep_id": sweep_id,
                    "block_id": block_id,
                    "replicate_id": replicate_id,
                    "replicate_index": replicate_index,
                    "task_ids": block,
                }
            )
            first_half, second_half = block[: K // 2], block[K // 2 :]
            shapes = {
                "forward": first_half + second_half,
                "swapped_halves": second_half + first_half,
            }
            # Filtering this full session sequence to the matrix engines is ABBA.
            for engine, shape in (
                (MATRIX_ENGINES[0], "forward"),
                (MATRIX_ENGINES[1], "forward"),
                (SONNET, "forward"),
                (MATRIX_ENGINES[1], "swapped_halves"),
                (MATRIX_ENGINES[0], "swapped_halves"),
                (SONNET, "swapped_halves"),
            ):
                short_shape = "fwd" if shape == "forward" else "swap"
                sessions.append(
                    {
                        "engine": engine,
                        "session_label": f"{replicate_id}-{engine}-{short_shape}",
                        "replicate_id": replicate_id,
                        "replicate_index": replicate_index,
                        "sweep_id": sweep_id,
                        "block_id": block_id,
                        "crossover_shape": shape,
                        "tasks": task_entries(shapes[shape]),
                    }
                )
    block_digest = hashlib.sha256(canonical_bytes(blocks)).hexdigest()
    return {
        "schema": "iter0110-session-horizon-schedule-v1",
        "seed": SEED,
        "k": K,
        "sweeps": sweeps,
        "engines": list(ENGINES),
        "matrix_engines": list(MATRIX_ENGINES),
        "block_assignments_sha256": block_digest,
        "blocks": blocks,
        "sessions": sessions,
    }


def require(condition: bool, name: str) -> None:
    if not condition:
        raise ScheduleViolation(name)


def check_schedule(schedule: object) -> None:
    if not isinstance(schedule, dict):
        raise ScheduleViolation("schedule-not-object")
    require(schedule.get("schema") == "iter0110-session-horizon-schedule-v1", "schema-mismatch")
    require(schedule.get("seed") == SEED, "schedule-seed-mismatch")
    require(schedule.get("k") == K, "schedule-k-mismatch")
    sweeps = schedule.get("sweeps")
    require(isinstance(sweeps, int) and not isinstance(sweeps, bool) and sweeps >= 1, "schedule-sweeps-invalid")
    require(schedule.get("engines") == list(ENGINES), "engine-list-mismatch")
    blocks = schedule.get("blocks")
    sessions = schedule.get("sessions")
    require(isinstance(blocks, list), "blocks-not-list")
    require(isinstance(sessions, list), "sessions-not-list")
    require(
        schedule.get("block_assignments_sha256") == hashlib.sha256(canonical_bytes(blocks)).hexdigest(),
        "block-assignment-digest-mismatch",
    )
    sealed = set(sealed_task_ids())
    require(len(blocks) == sweeps * len(sealed) // K, "block-count-invalid")

    block_by_replicate: dict[str, dict[str, object]] = {}
    blocks_by_sweep: dict[int, list[dict[str, object]]] = defaultdict(list)
    for block in blocks:
        require(isinstance(block, dict), "block-not-object")
        replicate_id = block.get("replicate_id")
        sweep_id = block.get("sweep_id")
        task_ids = block.get("task_ids")
        require(isinstance(replicate_id, str) and replicate_id, "block-replicate-id-invalid")
        require(isinstance(sweep_id, int), "block-sweep-id-invalid")
        require(isinstance(task_ids, list) and len(task_ids) == K, "block-task-count-invalid")
        require(set(task_ids) <= sealed and len(set(task_ids)) == K, "block-task-id-invalid")
        require(replicate_id not in block_by_replicate, "replicate-id-duplicate")
        block_by_replicate[replicate_id] = block
        blocks_by_sweep[sweep_id].append(block)
    require(set(blocks_by_sweep) == set(range(1, sweeps + 1)), "sweep-set-invalid")
    for sweep_id, group in blocks_by_sweep.items():
        flat = [task for block in group for task in block["task_ids"]]
        require(len(group) == len(sealed) // K, f"block-count-sweep-{sweep_id}")
        require(set(flat) == sealed and len(flat) == len(sealed), f"block-partition-invalid-sweep-{sweep_id}")

    sessions_by_replicate_engine: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    session_labels: set[str] = set()
    session_sequence_by_replicate: dict[str, list[dict[str, object]]] = defaultdict(list)
    for session in sessions:
        require(isinstance(session, dict), "session-not-object")
        engine = session.get("engine")
        replicate_id = session.get("replicate_id")
        label = session.get("session_label")
        tasks = session.get("tasks")
        require(engine in ENGINES, "session-engine-invalid")
        require(isinstance(replicate_id, str) and replicate_id in block_by_replicate, "session-replicate-invalid")
        require(isinstance(label, str) and label and label not in session_labels, "session-label-invalid-or-duplicate")
        session_labels.add(label)
        require(session.get("sweep_id") == block_by_replicate[replicate_id]["sweep_id"], "session-sweep-mismatch")
        require(session.get("block_id") == block_by_replicate[replicate_id]["block_id"], "session-block-mismatch")
        require(session.get("crossover_shape") in {"forward", "swapped_halves"}, "session-crossover-shape-invalid")
        require(isinstance(tasks, list) and len(tasks) == K, "session-task-count-invalid")
        ordered_task_ids: list[str] = []
        classes: list[str] = []
        for position, item in enumerate(tasks, start=1):
            require(isinstance(item, dict), "session-task-not-object")
            require(item.get("slot") == f"t{position}", "session-slot-invalid")
            require(item.get("position_index") == position, "session-position-index-invalid")
            expected_class = "EARLY" if position <= K // 2 else "LATE"
            require(item.get("position_class") == expected_class, "session-position-class-invalid")
            task_id = item.get("task_id")
            require(isinstance(task_id, str), "session-task-id-invalid")
            ordered_task_ids.append(task_id)
            classes.append(expected_class)
        block_tasks = block_by_replicate[replicate_id]["task_ids"]
        require(set(ordered_task_ids) == set(block_tasks) and len(set(ordered_task_ids)) == K, "session-block-membership-invalid")
        require(classes.count("EARLY") == K // 2 and classes.count("LATE") == K // 2, "session-position-balance-invalid")
        sessions_by_replicate_engine[(replicate_id, engine)].append(session)
        session_sequence_by_replicate[replicate_id].append(session)

    require(len(sessions) == len(blocks) * len(ENGINES) * 2, "session-count-invalid")
    for replicate_id, block in block_by_replicate.items():
        block_tasks = set(block["task_ids"])
        for engine in ENGINES:
            pair = sessions_by_replicate_engine[(replicate_id, engine)]
            require(len(pair) == 2, f"crossover-session-count-{replicate_id}-{engine}")
            require({session["crossover_shape"] for session in pair} == {"forward", "swapped_halves"}, f"crossover-shape-pair-{replicate_id}-{engine}")
            placements: dict[str, Counter[str]] = defaultdict(Counter)
            for session in pair:
                for item in session["tasks"]:
                    placements[item["task_id"]][item["position_class"]] += 1
            require(set(placements) == block_tasks, f"crossover-task-set-{replicate_id}-{engine}")
            require(all(counts == Counter({"EARLY": 1, "LATE": 1}) for counts in placements.values()), f"crossover-law-violation-{replicate_id}-{engine}")
        matrix_sequence = [
            session["engine"]
            for session in session_sequence_by_replicate[replicate_id]
            if session["engine"] in MATRIX_ENGINES
        ]
        require(matrix_sequence == [MATRIX_ENGINES[0], MATRIX_ENGINES[1], MATRIX_ENGINES[1], MATRIX_ENGINES[0]], f"abba-violation-{replicate_id}")
        sonnet_sessions = sessions_by_replicate_engine[(replicate_id, SONNET)]
        require(len(sonnet_sessions) == 2, f"sonnet-coverage-violation-{replicate_id}")


def read_schedule(path: pathlib.Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ScheduleViolation(f"schedule-unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise ScheduleViolation("schedule-not-object")
    return value


def self_test() -> None:
    schedule = build_schedule(2)
    check_schedule(schedule)
    violating = json.loads(json.dumps(schedule))
    session = next(
        value
        for value in violating["sessions"]
        if value["engine"] == MATRIX_ENGINES[0] and value["crossover_shape"] == "swapped_halves"
    )
    session["tasks"][0]["task_id"] = session["tasks"][1]["task_id"]
    try:
        check_schedule(violating)
    except ScheduleViolation as exc:
        if not str(exc).startswith(("session-block-membership-invalid", "crossover-law-violation")):
            raise AssertionError(f"unexpected fixture violation: {exc}") from exc
    else:
        raise AssertionError("violating crossover fixture passed")
    print("PASS derive-schedule-0110 self-test: deterministic partition, crossover, ABBA, violating fixture")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    parser.add_argument("--sweeps", type=int, default=DEFAULT_SWEEPS)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            self_test()
            return 0
        if args.check:
            schedule = read_schedule(args.out)
            check_schedule(schedule)
            expected = build_schedule(schedule["sweeps"])
            require(canonical_bytes(schedule) == canonical_bytes(expected), "schedule-not-deterministic-derivation")
            print(json.dumps({"check": "PASS", "schedule": str(args.out), "sweeps": schedule["sweeps"]}, sort_keys=True))
            return 0
        schedule = build_schedule(args.sweeps)
        check_schedule(schedule)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(schedule, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"schedule": str(args.out), "sessions": len(schedule["sessions"]), "sweeps": args.sweeps}, sort_keys=True))
        return 0
    except ScheduleViolation as exc:
        print(f"FAIL derive-schedule-0110: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
