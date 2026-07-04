#!/usr/bin/env python3
"""Deterministic spawn/complete writer for phases.<name> in pipeline.state.json.

Usage:
    python3 state-phase-write.py --devlyn-dir .devlyn --phase implement spawn \
        --round 1 --triggered-by verify [--pre-sha <sha>] [--engine claude] [--model <id>]
    python3 state-phase-write.py --devlyn-dir .devlyn --phase implement complete \
        --verdict PASS [--findings-file <path>] [--log-file <path>] [--engine claude] [--model <id>]

references/state-schema.md#write-protocol is the contract this implements.
iter-0042 (autoresearch/iterations/0042-compliance-drift-probes.md) found a
hand-edited fix-loop respawn left `started_at` at its original round's value
while `completed_at`/`duration_ms`/`round`/`triggered_by` advanced to the new
round, producing an internally inconsistent phase timeline. `spawn` always
resets `started_at` fresh and nulls the completion fields; `complete` derives
`duration_ms` from the phase's own recorded `started_at`, so the two can never
drift apart again.
"""
from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import sys
import tempfile

VALID_VERDICTS = {"PASS", "PASS_WITH_ISSUES", "FAIL", "NEEDS_WORK", "BLOCKED"}
VALID_TRIGGERS = {"build_gate", "verify"}
PHASE_NAMES = {"plan", "probe_derive", "implement", "build_gate", "cleanup", "verify", "final_report"}


def reject_json_constant(token: str) -> None:
    raise ValueError(f"invalid JSON numeric constant: {token}")


def loads_strict_json(text: str):
    return json.loads(text, parse_constant=reject_json_constant)


def now_ms() -> datetime.datetime:
    # Truncate to millisecond precision at capture time — now_iso()'s string
    # representation is millisecond-precise, so any duration_ms computed from
    # a not-yet-truncated `now` can be off by a sub-millisecond rounding
    # remainder from what re-parsing the stored completed_at would give.
    dt = datetime.datetime.now(datetime.timezone.utc)
    return dt.replace(microsecond=(dt.microsecond // 1000) * 1000)


def now_iso(dt: datetime.datetime | None = None) -> str:
    dt = dt or now_ms()
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def parse_iso(value: str) -> datetime.datetime:
    text = value[:-1] if value.endswith("Z") else value
    if "." in text:
        head, frac = text.split(".", 1)
        text = f"{head}.{(frac + '000000')[:6]}"
    return datetime.datetime.fromisoformat(text).replace(tzinfo=datetime.timezone.utc)


def read_state(state_path: pathlib.Path) -> dict:
    if not state_path.is_file():
        raise SystemExit(f"error: {state_path} not found")
    try:
        return loads_strict_json(state_path.read_text(encoding="utf-8"))
    except ValueError as e:
        raise SystemExit(f"error: {state_path} is not valid JSON: {e}")


def write_state(state_path: pathlib.Path, state: dict) -> None:
    fd, tmp_name = tempfile.mkstemp(dir=str(state_path.parent), prefix=state_path.name + ".tmp.")
    try:
        with open(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(state, indent=2, sort_keys=True) + "\n")
        pathlib.Path(tmp_name).replace(state_path)
    except BaseException:
        pathlib.Path(tmp_name).unlink(missing_ok=True)
        raise


def clear_verify_round_artifacts(devlyn: pathlib.Path) -> None:
    # The per-round reset contract covers files, not just JSON fields: a
    # VERIFY fix-loop respawn reuses the same .devlyn, so a prior round's
    # findings/stdout would otherwise read as current-round spawn evidence in
    # verify-merge-findings.py (iter-0060 R0 finding).
    # verify*.jsonl (not just *.findings.jsonl): judge-specific files like
    # verify.findings.judge-codex.jsonl end in .judge-<engine>.jsonl.
    # *-judge.* covers every engine's stdout/stderr capture (codex-judge.*,
    # claude-judge.* — adapters/claude.md ## Invocation).
    for pattern in ("verify*.jsonl", "*-judge.*"):
        for path in devlyn.glob(pattern):
            path.unlink()
    (devlyn / "verify-merge.summary.json").unlink(missing_ok=True)


def do_spawn(state: dict, phase: str, round_: int, triggered_by: str | None,
             pre_sha: str | None, engine: str | None, model: str | None) -> None:
    # Merge, don't replace: a phase-gated large run's `exec` progress (or any
    # other field this script doesn't own) survives a fix-loop respawn.
    phases = state.setdefault("phases", {})
    entry = phases.get(phase)
    if not isinstance(entry, dict):
        entry = {}
        phases[phase] = entry
    entry["started_at"] = now_iso()
    entry["completed_at"] = None
    entry["duration_ms"] = None
    entry["round"] = round_
    entry["triggered_by"] = triggered_by
    entry["verdict"] = None
    entry["artifacts"] = {"findings_file": None, "log_file": None}
    entry["sub_verdicts"] = None
    if engine is not None:
        entry["engine"] = engine
    if model is not None:
        entry["model"] = model
    if pre_sha is not None:
        entry["pre_sha"] = pre_sha


def do_complete(state: dict, phase: str, verdict: str | None,
                 findings_file: str | None, log_file: str | None,
                 engine: str | None, model: str | None) -> None:
    phases = state.setdefault("phases", {})
    entry = phases.get(phase)
    if not isinstance(entry, dict) or not entry.get("started_at"):
        raise SystemExit(f"error: phases.{phase} was never spawned (no started_at) — cannot complete")
    started = parse_iso(entry["started_at"])
    now = now_ms()
    entry["completed_at"] = now_iso(now)
    entry["duration_ms"] = max(0, round((now - started).total_seconds() * 1000))
    if phase == "verify":
        if verdict is not None:
            raise SystemExit(
                "error: phases.verify.verdict is owned by verify-merge-findings.py "
                "--write-state; do not pass --verdict to complete for this phase"
            )
        if entry.get("verdict") is None:
            raise SystemExit(
                "error: phases.verify.verdict is still null — run "
                "verify-merge-findings.py --write-state before complete"
            )
    elif verdict is not None:
        entry["verdict"] = verdict
    else:
        raise SystemExit(f"error: --verdict is required to complete phases.{phase}")
    if findings_file is not None or log_file is not None:
        artifacts = entry.setdefault("artifacts", {"findings_file": None, "log_file": None})
        if findings_file is not None:
            artifacts["findings_file"] = findings_file
        if log_file is not None:
            artifacts["log_file"] = log_file
    if engine is not None:
        entry["engine"] = engine
    if model is not None:
        entry["model"] = model


def self_test() -> int:
    import time

    with tempfile.TemporaryDirectory() as tmp:
        devlyn = pathlib.Path(tmp)
        state_path = devlyn / "pipeline.state.json"
        write_state(state_path, {"phases": {}})

        # Round 0: spawn -> complete.
        state = read_state(state_path)
        do_spawn(state, "implement", 0, None, None, "claude", None)
        write_state(state_path, state)
        round0_started = read_state(state_path)["phases"]["implement"]["started_at"]

        time.sleep(0.05)
        state = read_state(state_path)
        do_complete(state, "implement", "NEEDS_WORK", None, None, None, "test-model-id")
        write_state(state_path, state)
        entry = read_state(state_path)["phases"]["implement"]
        assert entry["completed_at"] is not None
        assert entry["duration_ms"] >= 0
        assert parse_iso(entry["completed_at"]) >= parse_iso(entry["started_at"])
        expected_ms = round((parse_iso(entry["completed_at"]) - parse_iso(entry["started_at"])).total_seconds() * 1000)
        assert entry["duration_ms"] == expected_ms, (entry["duration_ms"], expected_ms)

        # Round 1: fix-loop respawn — this is the literal iter-0042 regression.
        time.sleep(0.05)
        state = read_state(state_path)
        do_spawn(state, "implement", 1, "verify", None, None, None)
        write_state(state_path, state)
        respawned = read_state(state_path)["phases"]["implement"]
        assert respawned["started_at"] != round0_started, "started_at must refresh on respawn"
        assert respawned["completed_at"] is None, "respawn must null stale completed_at"
        assert respawned["duration_ms"] is None, "respawn must null stale duration_ms"
        assert respawned["verdict"] is None, "respawn must null stale verdict"
        assert respawned["engine"] == "claude", "engine preserved when not re-supplied"
        assert respawned["round"] == 1
        assert respawned["triggered_by"] == "verify"

        time.sleep(0.05)
        state = read_state(state_path)
        do_complete(state, "implement", "PASS", ".devlyn/x.jsonl", None, None, None)
        write_state(state_path, state)
        final = read_state(state_path)["phases"]["implement"]
        assert final["verdict"] == "PASS"
        assert parse_iso(final["started_at"]) == parse_iso(respawned["started_at"])
        assert parse_iso(final["completed_at"]) >= parse_iso(final["started_at"])
        assert final["artifacts"]["findings_file"] == ".devlyn/x.jsonl"

        # complete() before spawn() must fail loudly, not silently invent data.
        write_state(state_path, {"phases": {}})
        state = read_state(state_path)
        try:
            do_complete(state, "build_gate", "PASS", None, None, None, None)
        except SystemExit as e:
            assert "never spawned" in str(e)
        else:
            raise AssertionError("complete() without a prior spawn() must raise")

        # VERIFY flow: verify-merge-findings.py already wrote verdict; complete()
        # must preserve it when --verdict is omitted.
        write_state(state_path, {"phases": {}})
        state = read_state(state_path)
        do_spawn(state, "verify", 0, None, None, "claude", None)
        state["phases"]["verify"]["verdict"] = "PASS"
        state["phases"]["verify"]["sub_verdicts"] = {"mechanical": "PASS", "judge": "PASS"}
        write_state(state_path, state)
        state = read_state(state_path)
        do_complete(state, "verify", None, None, None, None, None)
        write_state(state_path, state)
        verify_entry = read_state(state_path)["phases"]["verify"]
        assert verify_entry["verdict"] == "PASS", "complete() must preserve pre-set verdict when omitted"
        assert verify_entry["sub_verdicts"] == {"mechanical": "PASS", "judge": "PASS"}
        assert verify_entry["completed_at"] is not None

        # An explicit --verdict for VERIFY must be rejected — its verdict is
        # owned exclusively by verify-merge-findings.py --write-state.
        state = read_state(state_path)
        try:
            do_complete(state, "verify", "PASS", None, None, None, None)
        except SystemExit as e:
            assert "owned by verify-merge-findings.py" in str(e)
        else:
            raise AssertionError("complete() must reject an explicit --verdict for VERIFY")

        # Non-VERIFY phases require --verdict explicitly; complete() must not
        # silently accept an unset verdict the way VERIFY's omit-to-preserve
        # flow does.
        write_state(state_path, {"phases": {}})
        state = read_state(state_path)
        do_spawn(state, "plan", 0, None, None, None, None)
        write_state(state_path, state)
        state = read_state(state_path)
        try:
            do_complete(state, "plan", None, None, None, None, None)
        except SystemExit as e:
            assert "is required" in str(e)
        else:
            raise AssertionError("complete() with no --verdict on a non-VERIFY phase must raise")

        # VERIFY complete() before verify-merge-findings.py wrote a verdict
        # must also fail loudly, not silently pass with a null verdict.
        write_state(state_path, {"phases": {}})
        state = read_state(state_path)
        do_spawn(state, "verify", 0, None, None, None, None)
        write_state(state_path, state)
        state = read_state(state_path)
        try:
            do_complete(state, "verify", None, None, None, None, None)
        except SystemExit as e:
            assert "still null" in str(e)
        else:
            raise AssertionError("VERIFY complete() with no verdict anywhere must raise")

        # VERIFY respawn must clear the prior round's on-disk artifacts too —
        # a stale round-0 pair findings file would otherwise read as
        # current-round spawn evidence in verify-merge-findings.py
        # (iter-0060 R0 finding: current-round spawn evidence).
        for name in (
            "verify.findings.jsonl",
            "verify.pair.findings.jsonl",
            "verify.findings.judge-codex.jsonl",
            "verify-merged.findings.jsonl",
            "verify-merge.summary.json",
            "codex-judge.stdout",
            "claude-judge.stdout",
        ):
            (devlyn / name).write_text("stale\n", encoding="utf-8")
        (devlyn / "spec-verify.json").write_text("{}", encoding="utf-8")
        clear_verify_round_artifacts(devlyn)
        for name in (
            "verify.findings.jsonl",
            "verify.pair.findings.jsonl",
            "verify.findings.judge-codex.jsonl",
            "verify-merged.findings.jsonl",
            "verify-merge.summary.json",
            "codex-judge.stdout",
            "claude-judge.stdout",
        ):
            assert not (devlyn / name).exists(), f"{name} must be cleared on VERIFY spawn"
        assert (devlyn / "spec-verify.json").exists(), "non-VERIFY-round files must survive"

        # Fix-loop respawn of phase-gated IMPLEMENT must preserve `exec`
        # (routing truth for large runs, state-schema.md line 55) — spawn
        # merges into the existing entry rather than replacing it wholesale.
        write_state(state_path, {"phases": {}})
        state = read_state(state_path)
        do_spawn(state, "implement", 0, None, None, "claude", None)
        state["phases"]["implement"]["exec"] = {
            "total": 3, "current": 3, "statuses": ["PASS", "PASS", "PASS"], "commits": ["a", "b", "c"],
        }
        write_state(state_path, state)
        state = read_state(state_path)
        do_complete(state, "implement", "PASS", None, None, None, None)
        write_state(state_path, state)
        state = read_state(state_path)
        do_spawn(state, "implement", 1, "verify", None, None, None)
        write_state(state_path, state)
        respawned_exec = read_state(state_path)["phases"]["implement"]
        assert respawned_exec["exec"]["current"] == 3, "spawn must not clobber unowned fields like exec"
        assert respawned_exec["verdict"] is None, "respawn still nulls owned fields even with exec present"

    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--devlyn-dir", default=".devlyn")
    ap.add_argument("--phase", choices=sorted(PHASE_NAMES))
    ap.add_argument("--self-test", action="store_true")
    sub = ap.add_subparsers(dest="event")

    spawn_p = sub.add_parser("spawn")
    spawn_p.add_argument("--round", type=int, required=True)
    spawn_p.add_argument("--triggered-by", choices=sorted(VALID_TRIGGERS), default=None)
    spawn_p.add_argument("--pre-sha", default=None)
    spawn_p.add_argument("--engine", default=None)
    spawn_p.add_argument("--model", default=None)

    complete_p = sub.add_parser("complete")
    complete_p.add_argument("--verdict", choices=sorted(VALID_VERDICTS), default=None)
    complete_p.add_argument("--findings-file", default=None)
    complete_p.add_argument("--log-file", default=None)
    complete_p.add_argument("--engine", default=None)
    complete_p.add_argument("--model", default=None)

    args = ap.parse_args()
    if args.self_test:
        return self_test()

    if not args.phase or args.event not in {"spawn", "complete"}:
        ap.error("--phase and one of {spawn,complete} are required unless --self-test")

    devlyn = pathlib.Path(args.devlyn_dir)
    if not devlyn.is_dir():
        sys.stderr.write(f"error: {devlyn} is not a directory\n")
        return 1
    state_path = devlyn / "pipeline.state.json"
    state = read_state(state_path)

    if args.event == "spawn":
        if args.phase == "verify":
            clear_verify_round_artifacts(devlyn)
        do_spawn(state, args.phase, args.round, args.triggered_by, args.pre_sha, args.engine, args.model)
    else:
        do_complete(state, args.phase, args.verdict, args.findings_file, args.log_file, args.engine, args.model)

    write_state(state_path, state)
    sys.stdout.write(f"ok: phases.{args.phase}.{args.event}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
