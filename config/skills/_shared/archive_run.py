#!/usr/bin/env python3
"""Archive devlyn:resolve run artifacts per references/pipeline-state.md#archive-contract.

Usage:
    python3 scripts/archive_run.py [--devlyn-dir .devlyn]

Reads run_id from .devlyn/pipeline.state.json, moves per-run artifacts into
.devlyn/runs/<run_id>/, then best-effort prunes to last 10 completed runs
(in-flight runs — phases.final_report.verdict == null — are never deleted).

The contract lives in pipeline-state.md. This script implements it so that
archive behavior is identical across every invocation.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import runpy
import shutil
import subprocess
import sys
import tempfile


PER_RUN_PATTERNS = (
    "pipeline.state.json",
    "untracked.baseline",
    "external-diff.patch",
    "plan.task-context",
    "plan.prompt",
    "probe-derive.stdout",
    "probe-derive.stderr",
    "*.findings.jsonl",
    "*.log.md",
    "fix-batch.round-*.json",
    "closure-durability.round-*.json",
    "resolve-stop-hook.*.json",
    "criteria.generated.md",
    "goal.raw.txt",
    "surface-close.input.patch",
    "surface-close.prompt",
    "surface-close.output.json",
    "surface-close.stdout",
    # Mutation workers retain the exact session JSONL identified by their
    # dispatch receipt. Round-scoped root files avoid engine-global scans.
    "implement.worker-session.*.jsonl",
    "surface-close.worker-session.*.jsonl",
    "cleanup.worker-session.*.jsonl",
    "risk-probes.jsonl",
    # Probe scripts referenced by risk-probes.jsonl preserve probes/<file>
    # layout through the common preflight/move plan below.
    # iter-0019.8: spec-verify carrier artifacts get archived alongside
    # other per-run state. Killed mid-run cleanup is enforced separately
    # by spec-verify-check.py main() — when source markdown has no json
    # block AND BENCH_WORKDIR is unset (real-user mode), the script drops
    # any pre-existing .devlyn/spec-verify.json so a stale orphan from a
    # killed prior run cannot poison this run's gate.
    "spec-verify.json",
    "spec-verify.results.json",
    "spec-verify-findings.jsonl",
    "verify-merge.summary.json",
    "verify.pair.timeout.json",
    "finish-gate.summary.json",
    # iter-0033a/2026-04-30 archive-fix iter: NEW /devlyn:resolve emits
    # plan.md (PLAN output) + final-report.md (PHASE 6 render) +
    # cumulative.patch (cumulative diff). Smoke 2's archive listing
    # captured all three; archive_run.py was missing them because the
    # patterns predated the new skill's artifact set. Added explicitly
    # so the move is deterministic.
    "plan.md",
    "final-report.md",
    "cumulative.patch",
    # iter-0033c (Codex R-final-smoke Q2): pair-mode VERIFY emits per-judge
    # deliberation transcripts (verify-judge-claude.md / verify-judge-codex.md
    # — and any future-engine analogue via wildcard). Smoke 1a (F2 l2_forced)
    # surfaced the gap: the orchestrator wrote them and listed them as
    # artifacts, but archive_run.py left them in .devlyn/. Gate 8
    # ("pair_judge findings archive distinguishable") would false-fail on
    # every paired fixture without this glob.
    "verify-judge-*.md",
    # *-judge.*: every engine's pair-judge stdout/stderr capture
    # (codex-judge.*, claude-judge.* — adapters/claude.md ## Invocation).
    "*-judge.*",
    # Phase-owned prompt, context, raw-stream, event, and retry carriers use
    # a phase prefix. Keep the ownership surface here so bootstrap and final
    # archive cannot drift onto separate cleanup lists.
)
PER_RUN_PATTERNS += tuple(
    f"{phase}.{suffix}"
    for phase in (
        "plan", "probe-derive", "implement", "surface-close", "build_gate",
        "build-gate", "cleanup", "verify", "final-report", "finish-gate",
    )
    for suffix in (
        "task-context", "prompt", "stdout", "stderr", "events.jsonl",
        "event-stream.jsonl", "retry.*",
    )
)

SAFE_RUN_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


class ArchiveError(Exception):
    pass


def process_evidence_module():
    return runpy.run_path(pathlib.Path(__file__).with_name("process-evidence.py"))


def reject_json_constant(token: str) -> None:
    raise ValueError(f"invalid JSON numeric constant: {token}")


def loads_strict_json(text: str):
    return json.loads(text, parse_constant=reject_json_constant)


def read_state(devlyn: pathlib.Path) -> dict:
    state_path = devlyn / "pipeline.state.json"
    if not state_path.is_file():
        raise ArchiveError(f"{state_path} not found")
    try:
        state = loads_strict_json(state_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ArchiveError(f"{state_path} is not valid JSON: {exc}") from exc
    if not isinstance(state, dict):
        raise ArchiveError(f"{state_path} must contain a JSON object")
    run_id = state.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        raise ArchiveError(f"{state_path} has no run_id")
    if not SAFE_RUN_ID_RE.fullmatch(run_id):
        raise ArchiveError(f"{state_path} run_id must match [A-Za-z0-9_.-]+")
    return state


def read_run_id(devlyn: pathlib.Path) -> str:
    try:
        return read_state(devlyn)["run_id"]
    except ArchiveError as exc:
        raise SystemExit(f"error: {exc}") from exc


def static_artifacts(devlyn: pathlib.Path) -> list[pathlib.Path]:
    found: dict[pathlib.Path, None] = {}
    for pattern in PER_RUN_PATTERNS:
        for path in devlyn.glob(pattern):
            if path.is_file():
                found[path] = None
    probes = devlyn / "probes"
    if probes.is_dir():
        for path in probes.rglob("*"):
            if path.is_file():
                found[path] = None
    return sorted(found)


def has_owned_artifacts(devlyn: pathlib.Path) -> bool:
    if not devlyn.is_dir():
        return False
    if static_artifacts(devlyn):
        return True
    evidence = devlyn / "process-evidence"
    return evidence.is_dir() and any(path.is_file() for path in evidence.rglob("*"))


def dynamic_evidence_artifacts(devlyn: pathlib.Path, state: dict) -> list[pathlib.Path]:
    carriers = state.get("process_evidence")
    evidence_root = devlyn / "process-evidence"
    if carriers is None:
        if evidence_root.is_dir() and any(path.is_file() for path in evidence_root.rglob("*")):
            raise ArchiveError("process-evidence files exist without state bindings")
        return []
    if not isinstance(carriers, list):
        raise ArchiveError("state.process_evidence must be null or an array")

    runner = process_evidence_module()
    work = devlyn.parent.resolve()
    run_id = state["run_id"]
    expected_root = pathlib.PurePosixPath(".devlyn") / "process-evidence" / run_id
    found: dict[pathlib.Path, None] = {}
    for carrier in carriers:
        try:
            runner["validate_bound_carrier"](work, carrier)
        except (runner["EvidenceError"], OSError, UnicodeError, ValueError) as exc:
            raise ArchiveError(f"invalid bound process evidence: {exc}") from exc
        manifest = carrier["manifest"]
        paths = [manifest["path"]]
        for stream in carrier["streams"]:
            paths.extend((stream["stdout"]["path"], stream["stderr"]["path"]))
        for relative_text in paths:
            relative = pathlib.PurePosixPath(relative_text)
            try:
                relative.relative_to(expected_root)
            except ValueError as exc:
                raise ArchiveError(
                    f"process evidence is not owned by state.run_id {run_id}: {relative_text}"
                ) from exc
            source = work.joinpath(*relative.parts)
            if source in found:
                raise ArchiveError(f"duplicate state-bound process-evidence path: {relative_text}")
            found[source] = None

    actual = {
        path.resolve()
        for path in evidence_root.rglob("*")
        if path.is_file()
    } if evidence_root.is_dir() else set()
    bound = {path.resolve() for path in found}
    unbound = []
    for path in actual - bound:
        try:
            unbound.append(path.relative_to(work).as_posix())
        except ValueError as exc:
            raise ArchiveError(f"process-evidence file escapes the worktree: {path}") from exc
    unbound.sort()
    if unbound:
        raise ArchiveError("unbound process-evidence file(s): " + ",".join(unbound))
    return sorted(found)


def archive_plan(devlyn: pathlib.Path, dest: pathlib.Path, state: dict) -> list[tuple[pathlib.Path, pathlib.Path]]:
    moves: list[tuple[pathlib.Path, pathlib.Path]] = []
    sources: set[pathlib.Path] = set()
    targets: set[pathlib.Path] = set()

    def add(source: pathlib.Path, target: pathlib.Path) -> None:
        if source in sources:
            return
        if target in targets:
            raise ArchiveError(f"archive destination is ambiguous: {target}")
        if target.exists():
            raise ArchiveError(f"archive destination collision: {target}")
        parent = target.parent
        while parent != dest.parent:
            if parent.exists() and not parent.is_dir():
                raise ArchiveError(f"archive destination parent is not a directory: {parent}")
            if parent == dest:
                break
            parent = parent.parent
        sources.add(source)
        targets.add(target)
        moves.append((source, target))

    for source in static_artifacts(devlyn):
        relative = source.relative_to(devlyn)
        target = dest / relative if relative.parts[0] == "probes" else dest / source.name
        add(source, target)
    for source in dynamic_evidence_artifacts(devlyn, state):
        add(source, dest / source.relative_to(devlyn))
    return moves


def move_artifacts(devlyn: pathlib.Path, dest: pathlib.Path) -> int:
    devlyn = devlyn.resolve()
    dest = dest.resolve()
    state = read_state(devlyn)
    if dest.name != state["run_id"] or dest.parent != devlyn / "runs":
        raise ArchiveError("archive destination does not match authenticated state.run_id")
    moves = archive_plan(devlyn, dest, state)
    completed: list[tuple[pathlib.Path, pathlib.Path]] = []
    try:
        for source, target in moves:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(target))
            completed.append((source, target))
    except BaseException:
        for source, target in reversed(completed):
            source.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(target), str(source))
        raise
    for root in (devlyn / "probes", devlyn / "process-evidence" / state["run_id"]):
        if root.is_dir():
            for directory in sorted(
                (path for path in root.rglob("*") if path.is_dir()),
                key=lambda path: len(path.parts), reverse=True,
            ):
                directory.rmdir()
            root.rmdir()
    return len(completed)


def prune(runs_dir: pathlib.Path, keep: int = 10) -> int:
    """Delete oldest completed runs beyond `keep`. In-flight runs never removed."""
    candidates = []
    for d in sorted(runs_dir.glob("*/"), key=lambda p: p.name):
        state_file = d / "pipeline.state.json"
        if not state_file.is_file():
            continue
        try:
            s = loads_strict_json(state_file.read_text(encoding="utf-8"))
        except ValueError:
            # Can't decide flight-state safely; skip (never prune)
            continue
        phases = s.get("phases") if isinstance(s, dict) else None
        final_report = phases.get("final_report") if isinstance(phases, dict) else None
        if not isinstance(final_report, dict) or final_report.get("verdict") is None:
            continue  # in-flight
        candidates.append(d)
    over = len(candidates) - keep
    if over <= 0:
        return 0
    pruned = 0
    for d in candidates[:over]:  # oldest first (lex sort = chronological)
        shutil.rmtree(d, ignore_errors=False)
        pruned += 1
    return pruned


def self_test() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        work = pathlib.Path(tmp)
        devlyn = pathlib.Path(tmp) / ".devlyn"
        devlyn.mkdir()
        state = {
            "run_id": "run-1",
            "phases": {
                "verify": {"round": 2},
                "final_report": {"verdict": "PASS"},
            },
            "process_evidence": None,
        }
        runner = process_evidence_module()
        obligation = runner["normalize_obligation"]({
            "id": "mechanical-0",
            "phase": "verify",
            "argv": [sys.executable, "-c", "import sys;sys.stdout.buffer.write(b'raw\\x00out')"],
        })
        manifest_rel = runner["manifest_relative_path"](state, "verify")
        runner["capture_process"](
            work, work / manifest_rel, state["run_id"], "verify", 2, obligation,
        )
        state["process_evidence"] = [runner["validate_manifest"](
            work, manifest_rel, state["run_id"], "verify", 2,
            [obligation], require_expectations=False,
        )]
        (devlyn / "pipeline.state.json").write_text(
            json.dumps(state) + "\n", encoding="utf-8",
        )
        for name in (
            "risk-probes.jsonl",
            "goal.raw.txt",
            "surface-close.input.patch",
            "surface-close.prompt",
            "surface-close.output.json",
            "surface-close.stdout",
            "implement.worker-session.0.jsonl",
            "surface-close.worker-session.0.jsonl",
            "cleanup.worker-session.1.jsonl",
            "resolve-stop-hook.run-1.123.456.json",
            "verify.pair.findings.jsonl",
            "verify-merge.summary.json",
            "untracked.baseline",
            "external-diff.patch",
            "plan.task-context",
            "plan.prompt",
            "probe-derive.stdout",
            "probe-derive.stderr",
            "verify.pair.timeout.json",
            "codex-judge.stdout",
            "codex-judge.summary.json",
            "claude-judge.stdout",
            "claude-judge.stderr",
            "implement.task-context",
            "implement.prompt",
            "implement.stdout",
            "implement.stderr",
            "implement.events.jsonl",
            "implement.retry.1.stdout",
        ):
            (devlyn / name).write_text("{}\n", encoding="utf-8")
        (devlyn / "probes").mkdir()
        (devlyn / "probes" / "P1.py").write_text("print('probe')\n", encoding="utf-8")
        global_rollout = devlyn / "engine-sessions" / "rollout-global.jsonl"
        global_rollout.parent.mkdir()
        global_rollout.write_text("{}\n", encoding="utf-8")
        run_id = read_run_id(devlyn)
        assert run_id == "run-1", run_id
        moved = move_artifacts(devlyn, devlyn / "runs" / run_id)
        assert moved >= 12, moved
        for name in (
            "pipeline.state.json",
            "risk-probes.jsonl",
            "goal.raw.txt",
            "surface-close.input.patch",
            "surface-close.prompt",
            "surface-close.output.json",
            "surface-close.stdout",
            "implement.worker-session.0.jsonl",
            "surface-close.worker-session.0.jsonl",
            "cleanup.worker-session.1.jsonl",
            "probes/P1.py",
            "verify.pair.findings.jsonl",
            "verify-merge.summary.json",
            "untracked.baseline",
            "external-diff.patch",
            "plan.task-context",
            "plan.prompt",
            "probe-derive.stdout",
            "probe-derive.stderr",
            "verify.pair.timeout.json",
            "codex-judge.stdout",
            "codex-judge.summary.json",
            "claude-judge.stdout",
            "claude-judge.stderr",
            "implement.task-context",
            "implement.prompt",
            "implement.stdout",
            "implement.stderr",
            "implement.events.jsonl",
            "implement.retry.1.stdout",
            f"process-evidence/{run_id}/verify/round-2/manifest.json",
            f"process-evidence/{run_id}/verify/round-2/mechanical-0.stdout",
            f"process-evidence/{run_id}/verify/round-2/mechanical-0.stderr",
        ):
            assert (devlyn / "runs" / run_id / name).is_file(), name
            assert not (devlyn / name).exists(), name
        assert global_rollout.is_file(), "engine-global session files must stay untouched"
        assert not (devlyn / "runs" / run_id / global_rollout.name).exists()
        assert not (devlyn / "process-evidence" / run_id).exists()

        for label in ("digest", "missing", "unsafe", "unbound", "collision"):
            isolated_work = pathlib.Path(tmp) / f"{label}-work"
            isolated_devlyn = isolated_work / ".devlyn"
            isolated_devlyn.mkdir(parents=True)
            isolated_state = {
                "run_id": f"run-{label}",
                "phases": {"verify": {"round": 0}},
                "process_evidence": None,
            }
            isolated_manifest_rel = runner["manifest_relative_path"](isolated_state, "verify")
            runner["capture_process"](
                isolated_work,
                isolated_work / isolated_manifest_rel,
                isolated_state["run_id"],
                "verify",
                0,
                obligation,
            )
            isolated_state["process_evidence"] = [runner["validate_manifest"](
                isolated_work,
                isolated_manifest_rel,
                isolated_state["run_id"],
                "verify",
                0,
                [obligation],
                require_expectations=False,
            )]
            (isolated_devlyn / "pipeline.state.json").write_text(
                json.dumps(isolated_state) + "\n", encoding="utf-8",
            )
            target = isolated_devlyn / "runs" / isolated_state["run_id"]
            if label == "digest":
                stream = isolated_work / isolated_state["process_evidence"][0]["streams"][0]["stdout"]["path"]
                stream.write_bytes(stream.read_bytes() + b"altered")
            elif label == "missing":
                stream = isolated_work / isolated_state["process_evidence"][0]["streams"][0]["stderr"]["path"]
                stream.unlink()
            elif label == "unsafe":
                isolated_state["process_evidence"][0]["manifest"]["path"] = "../escape/manifest.json"
                (isolated_devlyn / "pipeline.state.json").write_text(
                    json.dumps(isolated_state) + "\n", encoding="utf-8",
                )
            elif label == "unbound":
                extra = isolated_devlyn / "process-evidence" / isolated_state["run_id"] / "verify" / "round-0" / "extra.stdout"
                extra.write_text("not state-bound\n", encoding="utf-8")
            else:
                collision = target / pathlib.PurePosixPath(isolated_manifest_rel).relative_to(".devlyn")
                collision.parent.mkdir(parents=True)
                collision.write_text("occupied\n", encoding="utf-8")
            before = {
                str(path.relative_to(isolated_devlyn)): path.read_bytes()
                for path in isolated_devlyn.rglob("*") if path.is_file()
            }
            try:
                move_artifacts(isolated_devlyn, target)
            except ArchiveError:
                pass
            else:
                raise AssertionError(f"{label} archive violation was accepted")
            after = {
                str(path.relative_to(isolated_devlyn)): path.read_bytes()
                for path in isolated_devlyn.rglob("*") if path.is_file()
            }
            assert after == before, label

        null_states = {
            "run-0-final-report-null": {"phases": {"final_report": None}},
            "run-0-phases-null": {"phases": None},
            "run-0-root-null": None,
        }
        for name, state in null_states.items():
            null_run = devlyn / "runs" / name
            null_run.mkdir()
            (null_run / "pipeline.state.json").write_text(
                json.dumps(state) + "\n",
                encoding="utf-8",
            )
        newest_run = devlyn / "runs" / "run-2"
        newest_run.mkdir()
        (newest_run / "pipeline.state.json").write_text(
            json.dumps({"phases": {"final_report": {"verdict": "PASS"}}}) + "\n",
            encoding="utf-8",
        )
        assert prune(devlyn / "runs", keep=1) == 1
        assert all((devlyn / "runs" / name).is_dir() for name in null_states)
        assert not (devlyn / "runs" / run_id).exists(), "oldest completed archive must be pruned"
        assert newest_run.is_dir(), "newest completed archive must remain"

        bad = pathlib.Path(tmp) / "bad"
        bad.mkdir()
        (bad / "pipeline.state.json").write_text('{"run_id": "../escape"}\n', encoding="utf-8")
        try:
            read_run_id(bad)
        except SystemExit as exc:
            assert "run_id must match" in str(exc)
        else:
            raise AssertionError("unsafe archive run_id was accepted")
        blocked_cli = subprocess.run(
            [sys.executable, str(pathlib.Path(__file__).resolve()), "--devlyn-dir", str(bad)],
            capture_output=True,
            text=True,
        )
        assert blocked_cli.returncode == 1
        assert "error: archive blocked:" in blocked_cli.stderr
        assert "Traceback" not in blocked_cli.stderr

        nan = pathlib.Path(tmp) / "nan"
        nan.mkdir()
        (nan / "pipeline.state.json").write_text('{"run_id": NaN}\n', encoding="utf-8")
        try:
            read_run_id(nan)
        except SystemExit as exc:
            assert "invalid JSON numeric constant: NaN" in str(exc)
        else:
            raise AssertionError("NaN archive run_id was accepted")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--devlyn-dir", default=".devlyn")
    ap.add_argument("--keep", type=int, default=10, help="keep N most recent completed runs")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()

    devlyn = pathlib.Path(args.devlyn_dir)
    if not devlyn.is_dir():
        sys.stderr.write(f"error: {devlyn} is not a directory\n")
        return 1

    try:
        state = read_state(devlyn)
        run_id = state["run_id"]
        dest = devlyn / "runs" / run_id
        moved = move_artifacts(devlyn, dest)
        pruned = prune(devlyn / "runs", keep=args.keep)
    except (ArchiveError, OSError, UnicodeError, ValueError) as exc:
        sys.stderr.write(f"error: archive blocked: {exc}\n")
        return 1

    sys.stdout.write(f"archived run_id={run_id} files={moved} pruned={pruned}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
