#!/usr/bin/env python3
"""Deterministic PHASE 6 final-diff gate for /devlyn-resolve."""
from __future__ import annotations

import runpy
import argparse
import hashlib
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

FINDINGS_NAME = "finish-gate.findings.jsonl"
SUMMARY_NAME = "finish-gate.summary.json"
PHASE = "finish_gate"


class Malformed(Exception):
    def __init__(self, message: str, file_ref: str = ".devlyn/pipeline.state.json"):
        super().__init__(message)
        self.file_ref = file_ref


def load_spec_verify():
    helper = pathlib.Path(__file__).with_name("spec-verify-check.py")
    spec = importlib.util.spec_from_file_location("devlyn_spec_verify_check", helper)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {helper}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SPEC_VERIFY = load_spec_verify()


def git(work: pathlib.Path, *args: str) -> subprocess.CompletedProcess[str]:
    # Paths are literal: a route such as app/[slug]/page.tsx must never glob-match another file.
    return subprocess.run(
        ["git", "--literal-pathspecs", *args],
        cwd=str(work),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def git_check(work: pathlib.Path, *args: str) -> str:
    proc = git(work, *args)
    if proc.returncode != 0:
        raise AssertionError(proc.stderr or proc.stdout or f"git {' '.join(args)} failed")
    return proc.stdout.strip()


def read_state(path: pathlib.Path) -> dict:
    if not path.is_file():
        raise Malformed(f"{path} is missing")
    try:
        data = SPEC_VERIFY.loads_strict_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise Malformed(f"{path} is not valid JSON: {e}") from e
    if not isinstance(data, dict):
        raise Malformed(f"{path} must contain a JSON object")
    return data


def ensure_commit(work: pathlib.Path, sha: str, label: str) -> None:
    proc = git(work, "rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}")
    if proc.returncode != 0:
        raise Malformed(f"{label} is not a valid commit: {sha!r}")


def write_findings(devlyn_dir: pathlib.Path, findings: list[dict]) -> None:
    devlyn_dir.mkdir(parents=True, exist_ok=True)
    with (devlyn_dir / FINDINGS_NAME).open("w", encoding="utf-8") as handle:
        for finding in findings:
            handle.write(json.dumps(finding) + "\n")


def write_summary(devlyn_dir: pathlib.Path, summary: dict) -> None:
    devlyn_dir.mkdir(parents=True, exist_ok=True)
    (devlyn_dir / SUMMARY_NAME).write_text(json.dumps(summary, sort_keys=True) + "\n", encoding="utf-8")


def make_finding(
    seq: int,
    rule_id: str,
    message: str,
    file_ref: str,
    *,
    status: str,
    fix_hint: str,
    criterion_ref: str,
) -> dict:
    return {
        "id": f"FINISH-{seq:04d}",
        "rule_id": rule_id,
        "level": "error",
        "severity": "CRITICAL",
        "confidence": 1.0,
        "message": message,
        "file": file_ref,
        "line": 1,
        "phase": PHASE,
        "criterion_ref": criterion_ref,
        "fix_hint": fix_hint,
        "blocking": True,
        "status": status,
    }


def malformed_finding(error: Malformed) -> dict:
    return make_finding(
        1,
        "scope.finish-gate-malformed",
        str(error),
        error.file_ref,
        status="open",
        criterion_ref="finish_gate/state",
        fix_hint=(
            "Restore a valid pipeline state and plan authorized_surface block "
            "before final reporting can continue."
        ),
    )


def load_authorized_surface(devlyn_dir: pathlib.Path) -> list[str]:
    plan_path = devlyn_dir / "plan.md"
    if not plan_path.is_file():
        raise Malformed(
            "PHASE 6 finish gate requires .devlyn/plan.md with authorized_surface; the file is missing.",
            ".devlyn/plan.md",
        )
    try:
        plan_text = plan_path.read_text(encoding="utf-8")
    except OSError as e:
        raise Malformed(f"Cannot read {plan_path}: {e}", ".devlyn/plan.md") from e

    _found, block = SPEC_VERIFY.extract_authorized_surface_block(plan_text)
    data = None
    if block is None:
        parse_error = (
            "plan.md must include a `<!-- devlyn:authorized-surface -->` "
            "section with a fenced ```json``` authorized_surface block."
        )
    else:
        try:
            data = SPEC_VERIFY.loads_strict_json(block)
            parse_error = SPEC_VERIFY.validate_authorized_surface_shape(data)
        except ValueError as e:
            parse_error = f"authorized_surface json block is invalid JSON: {e}"
    if parse_error:
        raise Malformed(f"plan.md authorized_surface is malformed: {parse_error}", ".devlyn/plan.md")
    return list(data["authorized_surface"])


def changed_files(work: pathlib.Path, base_sha: str, sparse_absences: frozenset[str]) -> set[str]:
    """Paths changed since base_ref.sha (committed or not, both sides of a rename), observed as MECHANICAL observes."""
    try:
        with SPEC_VERIFY.observed_git(work, sparse_absences) as (observe, _flags):
            raw = observe("diff", "--name-only", "-z", "--no-renames", "--ignore-submodules=none", base_sha, "--")
    except (OSError, ValueError) as e:
        raise Malformed(f"cannot compute finish-gate changed files: {e}") from e
    return {os.fsdecode(path) for path in raw.split(b"\0") if path}


def contract_drift(work: pathlib.Path, state: dict) -> tuple[str, str, str] | None:
    """A sibling spec.expected.json that is no longer what bootstrap bound: (path, why, action).

    It offends wherever PLAN's surface lies, so the next run cannot bind a worker's contract, and
    only its binding decides the action: "remove" when bootstrap bound its absence, "restore" from
    base_ref.sha when base holds exactly the bound bytes, otherwise "report". The sibling's own
    path is the offender (a planted symlink is removed, never followed), and a contract outside the
    worktree is only reported.
    """
    source = state.get("source") if isinstance(state.get("source"), dict) else {}
    if source.get("type") != "spec" or not source.get("spec_path"):
        return None
    spec = pathlib.Path(source["spec_path"])
    spec = spec if spec.is_absolute() else work / spec
    why = SPEC_VERIFY.expected_contract_error(source, spec)
    if why is None:
        return None
    sibling = spec.with_name("spec.expected.json")
    try:
        path = (sibling.parent.resolve() / sibling.name).relative_to(work.resolve()).as_posix()
    except ValueError:
        return (str(sibling), why, "report")
    bound = source["expected_sha256"]
    if bound is None:
        return (path, why, "remove")
    base_blob = git(work, "rev-parse", "--verify", "--quiet", f"{state['base_ref']['sha']}:{path}")
    restorable = base_blob.returncode == 0 and hashlib.sha256(
        subprocess.run(["git", "cat-file", "blob", base_blob.stdout.strip()], cwd=work, capture_output=True).stdout
    ).hexdigest() == bound
    return (path, why, "restore" if restorable else "report")


def settle_contract(work: pathlib.Path, base_sha: str, path: str, action: str) -> tuple[bool, str | None]:
    """Return the drifted contract to its binding: absent, or the bound bytes from base."""
    if action == "report":
        return (False, "no bytes bootstrap bound exist to restore it")
    if action == "restore":
        proc = git(work, "checkout", base_sha, "--", path)
        return (proc.returncode == 0, proc.stderr.strip() or proc.stdout.strip() or None)
    # Bootstrap bound the contract's absence, so the run created this one: remove it, index entry
    # included unless base tracks the path (a sparse absence keeps its index entry).
    if not path_exists_at_base(work, base_sha, path):
        proc = git(work, "rm", "-q", "--cached", "--ignore-unmatch", "--", path)
        if proc.returncode != 0:
            return (False, proc.stderr.strip() or proc.stdout.strip())
    try:
        remove_worktree_path(work / path)
    except OSError as e:
        return (False, str(e))
    return (True, None)


def devlyn_relative_prefix(work: pathlib.Path, devlyn_dir: pathlib.Path) -> str:
    try:
        relative = devlyn_dir.resolve().relative_to(work.resolve()).as_posix().strip("/")
    except ValueError as e:
        raise Malformed(f"--devlyn-dir must be inside the work tree: {devlyn_dir}") from e
    if not relative or relative == ".":
        raise Malformed("--devlyn-dir must not be the work tree root")
    return relative


def is_under_prefix(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(f"{prefix}/")


def path_exists_at_base(work: pathlib.Path, base_sha: str, path: str) -> bool:
    return git(work, "cat-file", "-e", f"{base_sha}:{path}").returncode == 0


def remove_worktree_path(path: pathlib.Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def revert_offender(work: pathlib.Path, base_sha: str, path: str) -> tuple[str, str | None]:
    """Undo an out-of-surface change without destroying bytes the run cannot prove it made.

    A path present at base_ref.sha is restored: bootstrap required a clean tracked baseline, so
    its change is the run's. Any other path keeps its worktree bytes, losing only an index entry:
    absence from the PHASE 0 baseline does not prove the run created it (an ignore change can
    reveal a user's file). Returns (status, detail): "reverted", "retained" or "revert-failed".
    """
    if path_exists_at_base(work, base_sha, path):
        proc = git(work, "checkout", base_sha, "--", path)
        return ("reverted", None) if proc.returncode == 0 else ("revert-failed", proc.stderr.strip() or proc.stdout.strip())
    proc = git(work, "rm", "-q", "--cached", "--ignore-unmatch", "--", path)
    return ("retained", None) if proc.returncode == 0 else ("revert-failed", proc.stderr.strip() or proc.stdout.strip())


def run_gate(work: pathlib.Path, devlyn_dir: pathlib.Path) -> int:
    state_path = devlyn_dir / "pipeline.state.json"
    findings_path = devlyn_dir / FINDINGS_NAME
    summary_path = devlyn_dir / SUMMARY_NAME
    if summary_path.exists() or summary_path.is_symlink():
        # The first result stands for the run: a rerun after its automatic reverts would report clean.
        try:
            recorded = json.loads(summary_path.read_text(encoding="utf-8")).get("exit")
        except (OSError, ValueError, AttributeError):
            recorded = None
        sys.stderr.write("finish-gate: this run already has a result; it stands\n")
        return recorded if recorded in (0, 1, 2) else 1
    try:
        state = read_state(state_path)
        findings_path.unlink(missing_ok=True)
        if state.get("mode") == "verify-only":
            write_summary(devlyn_dir, {"mode": "verify-only", "skipped": True, "exit": 0})
            return 0

        base_sha = ((state.get("base_ref") or {}).get("sha") or "").strip()
        if not base_sha:
            raise Malformed("pipeline.state.json must include non-empty base_ref.sha")
        ensure_commit(work, base_sha, "base_ref.sha")
        # Revert only against the surface PLAN bound: a changed plan.md must never decide what to undo.
        writer = runpy.run_path(str(pathlib.Path(__file__).with_name("state-phase-write.py")))
        plan_error = writer["plan_output_error"](state, devlyn_dir, "final_report")
        if plan_error is not None:
            raise Malformed(f"bound PLAN no longer verifies: {plan_error}", ".devlyn/plan.md")
        # Before PLAN opens (a PHASE 0 halt) the run owns no product surface: any change offends.
        plan_opened = isinstance((state.get("phases") or {}).get("plan"), dict)
        surface = load_authorized_surface(devlyn_dir) if plan_opened else []
        baseline, sparse_absences, baseline_error = SPEC_VERIFY.load_untracked_baseline(devlyn_dir)
        if baseline_error is not None:
            raise Malformed(baseline_error, ".devlyn/untracked.baseline")
        changed = changed_files(work, base_sha, sparse_absences)
        untracked, untracked_error = SPEC_VERIFY.current_untracked_files(work, sparse_absences)
        if untracked_error is not None:
            raise Malformed(f"cannot list untracked files: {untracked_error}")
        changed |= untracked - baseline
        devlyn_prefix = devlyn_relative_prefix(work, devlyn_dir)
        checked = sorted(path for path in changed if not is_under_prefix(path, devlyn_prefix))
        drift = contract_drift(work, state)
    except Malformed as e:
        findings_path.unlink(missing_ok=True)
        write_findings(devlyn_dir, [malformed_finding(e)])
        write_summary(devlyn_dir, {"exit": 1, "malformed": str(e)})
        return 1

    contract = drift[0] if drift is not None else None
    offenders = sorted(path for path in checked if path != contract and not SPEC_VERIFY.path_matches_surface(path, surface))
    if not offenders and drift is None:
        findings_path.unlink(missing_ok=True)
        write_summary(devlyn_dir, {
            "mode": state.get("mode"),
            "checked": len(checked),
            "offenders": 0,
            "exit": 0,
        })
        return 0

    findings: list[dict] = []
    counts = {"reverted": 0, "retained": 0, "revert-failed": 0}
    if drift is not None:
        ok, detail = settle_contract(work, base_sha, *drift[::2])
        counts["reverted" if ok else "revert-failed"] += 1
        outcome = {"remove": "removed, as bootstrap bound its absence", "restore": "restored to the bytes bootstrap bound",
                   "report": "left in place"}[drift[2]]
        findings.append(make_finding(
            1, "scope.finish-contract-drift",
            f"The run's verification contract is no longer what bootstrap bound: {drift[1]}" + (f" ({detail})" if detail else ""),
            contract, status="reverted" if ok else "revert-failed",
            criterion_ref="pipeline.state.json/source.expected_sha256",
            fix_hint=f"The contract was {outcome}; a run never verifies against a contract it changed.",
        ))
    for path in offenders:
        status, detail = revert_offender(work, base_sha, path)
        counts[status] += 1
        outcome = {"reverted": "restored to base_ref.sha",
                   "retained": "kept in place (only an index entry removed): nothing proves this run created it",
                   "revert-failed": "left as is because restoring it failed"}[status]
        message = f"Final diff touched an unaudited file outside authorized_surface: {path}"
        if detail:
            message = f"{message} ({detail})"
        findings.append(make_finding(
            len(findings) + 1, "scope.finish-unaudited-file", message, path, status=status,
            criterion_ref="plan.md/authorized_surface",
            fix_hint=f"This file was outside authorized_surface and was {outcome}; do not ship unlicensed final-diff changes."))
    write_findings(devlyn_dir, findings)
    # Exit 0 let a real run treat reverted orchestrator commits as a clean pass.
    # Any offender is therefore unclean even when every automatic revert succeeds;
    # the caller maps exit 1/2 to BLOCKED:finish-gate-unclean.
    exit_code = 2
    write_summary(devlyn_dir, {
        "mode": state.get("mode"),
        "checked": len(checked),
        "offenders": len(findings),
        "reverted": counts["reverted"],
        "retained": counts["retained"],
        "revert_failed": counts["revert-failed"],
        "exit": exit_code,
    })
    return exit_code


def write_text(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_state(devlyn: pathlib.Path, state: dict) -> None:
    write_text(devlyn / "pipeline.state.json", json.dumps(state, indent=2) + "\n")


def read_findings(devlyn: pathlib.Path) -> list[dict]:
    path = devlyn / FINDINGS_NAME
    return [SPEC_VERIFY.loads_strict_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_summary(devlyn: pathlib.Path) -> dict:
    return SPEC_VERIFY.loads_strict_json((devlyn / SUMMARY_NAME).read_text(encoding="utf-8"))


def assert_summary(devlyn: pathlib.Path, expected: dict) -> None:
    summary = read_summary(devlyn)
    for key, value in expected.items():
        assert summary.get(key) == value, summary


def make_fixture(root: pathlib.Path, name: str, *, mode: str = "full") -> tuple[pathlib.Path, pathlib.Path, str]:
    work = root / name
    work.mkdir()
    git_check(work, "init", "-q")
    write_text(work / "src" / "app.txt", "base app\n")
    write_text(work / "notes.txt", "base notes\n")
    write_text(work / "cleanable.txt", "base cleanable\n")
    git_check(work, "add", "-A")
    git_check(work, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "base")
    base_sha = git_check(work, "rev-parse", "HEAD")
    devlyn = work / ".devlyn"
    write_text(
        devlyn / "plan.md",
        "# PLAN\n\n<!-- devlyn:authorized-surface -->\n## Files to touch\n\n"
        "- `src/app.txt` (edit): implement the requested change.\n\n"
        "```json\n"
        '{"authorized_surface": ["src/app.txt"]}\n'
        "```\n",
    )
    write_state(devlyn, {
        "mode": mode,
        "base_ref": {"sha": base_sha},
        "phases": {"plan": {"started_at": "t", "completed_at": "t", "verdict": "PASS"}},
    })
    write_text(devlyn / "untracked.baseline", json.dumps({"untracked": [], "sparse_absences": []}) + "\n")
    return (work, devlyn, base_sha)


def checked_run_gate(work: pathlib.Path, devlyn: pathlib.Path) -> int:
    rc = run_gate(work, devlyn)
    assert not any(path.name == "__pycache__" for path in work.rglob("__pycache__"))
    return rc


def self_test() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)

        work, devlyn, _base = make_fixture(root, "conforming")
        write_text(work / "src" / "app.txt", "changed app\n")
        assert checked_run_gate(work, devlyn) == 0
        assert not (devlyn / FINDINGS_NAME).exists()
        assert_summary(devlyn, {"mode": "full", "checked": 1, "offenders": 0, "exit": 0})

        work, devlyn, _base = make_fixture(root, "tracked-mutation")
        write_text(work / "notes.txt", "polluted\n")
        assert checked_run_gate(work, devlyn) == 2
        assert (work / "notes.txt").read_text(encoding="utf-8") == "base notes\n"
        findings = read_findings(devlyn)
        assert findings[0]["rule_id"] == "scope.finish-unaudited-file"
        assert findings[0]["status"] == "reverted"
        assert_summary(devlyn, {
            "mode": "full", "checked": 1, "offenders": 1,
            "reverted": 1, "revert_failed": 0, "exit": 2,
        })

        # A rerun keeps the first result; the reverted tree must not launder into a clean pass.
        first_summary = (devlyn / SUMMARY_NAME).read_bytes()
        assert checked_run_gate(work, devlyn) == 2
        assert (devlyn / SUMMARY_NAME).read_bytes() == first_summary and read_findings(devlyn) == findings

        # A PLAN narrowed after binding is malformed for the gate: nothing is reverted.
        work, devlyn, _base = make_fixture(root, "narrowed-plan")
        write_text(work / "src" / "app.txt", "changed app\n")
        bound = (devlyn / "plan.md").read_bytes()
        write_state(devlyn, {"version": "3.0", "mode": "full", "base_ref": {"sha": _base}, "phases": {"plan": {
            "started_at": "t", "completed_at": "t", "verdict": "PASS",
            "output_sha256": hashlib.sha256(bound).hexdigest()}}})
        (devlyn / "plan.md").write_bytes(bound.replace(b'"src/app.txt"]', b'"notes.txt"]', 1))
        assert checked_run_gate(work, devlyn) == 1
        assert (work / "src" / "app.txt").read_text(encoding="utf-8") == "changed app\n"
        assert "bound PLAN no longer verifies" in read_summary(devlyn)["malformed"]

        # A path absent at base keeps its bytes: staging proves nothing about who created it.
        work, devlyn, _base = make_fixture(root, "added-file")
        write_text(work / "runtime.txt", "late\n")
        git_check(work, "add", "runtime.txt")
        assert checked_run_gate(work, devlyn) == 2
        assert (work / "runtime.txt").read_text(encoding="utf-8") == "late\n"
        assert "runtime.txt" not in git_check(work, "ls-files").splitlines()
        assert read_findings(devlyn)[0]["status"] == "retained"
        assert_summary(devlyn, {
            "mode": "full", "checked": 1, "offenders": 1,
            "reverted": 0, "retained": 1, "revert_failed": 0, "exit": 2,
        })

        work, devlyn, _base = make_fixture(root, "devlyn-owned-tracked-mutation")
        archived = devlyn / "runs" / "prior" / "pipeline.state.json"
        write_text(archived, "tracked devlyn state\n")
        git_check(work, "add", archived.relative_to(work).as_posix())
        git_check(work, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "track devlyn state")
        write_text(archived, "mutated devlyn state\n")
        write_text(work / "notes.txt", "polluted\n")
        assert checked_run_gate(work, devlyn) == 2
        assert archived.read_text(encoding="utf-8") == "mutated devlyn state\n"
        assert (work / "notes.txt").read_text(encoding="utf-8") == "base notes\n"
        findings = read_findings(devlyn)
        assert [finding["file"] for finding in findings] == ["notes.txt"]
        assert findings[0]["status"] == "reverted"
        assert_summary(devlyn, {
            "mode": "full", "checked": 1, "offenders": 1,
            "reverted": 1, "revert_failed": 0, "exit": 2,
        })

        work, devlyn, _base = make_fixture(root, "verify-only", mode="verify-only")
        (devlyn / "plan.md").unlink()
        write_findings(devlyn, [make_finding(
            1,
            "scope.finish-unaudited-file",
            "stale",
            "stale.txt",
            status="reverted",
            criterion_ref="plan.md/authorized_surface",
            fix_hint="stale",
        )])
        write_state(devlyn, {"mode": "verify-only", "phases": {}})
        assert checked_run_gate(work, devlyn) == 0
        assert not (devlyn / FINDINGS_NAME).exists()
        assert read_summary(devlyn) == {"exit": 0, "mode": "verify-only", "skipped": True}

        work, devlyn, _base = make_fixture(root, "deleted-file")
        (work / "notes.txt").unlink()
        assert checked_run_gate(work, devlyn) == 2
        assert (work / "notes.txt").read_text(encoding="utf-8") == "base notes\n"
        assert read_findings(devlyn)[0]["status"] == "reverted"
        assert_summary(devlyn, {
            "mode": "full", "checked": 1, "offenders": 1,
            "reverted": 1, "revert_failed": 0, "exit": 2,
        })

        work, devlyn, _base = make_fixture(root, "git-diff-failure")
        original_observer = SPEC_VERIFY.observed_git

        def failing_observer(*_args, **_kwargs):
            raise ValueError("simulated diff failure")

        SPEC_VERIFY.observed_git = failing_observer
        try:
            assert checked_run_gate(work, devlyn) == 1
            finding = read_findings(devlyn)[0]
            assert finding["rule_id"] == "scope.finish-gate-malformed"
            assert "cannot compute finish-gate changed files" in finding["message"]
            summary = read_summary(devlyn)
            assert summary["exit"] == 1, summary
            assert "cannot compute finish-gate changed files" in summary["malformed"], summary
        finally:
            SPEC_VERIFY.observed_git = original_observer

        # A PHASE 0 halt owns no product surface: a clean tree passes and any change offends.
        work, devlyn, _base = make_fixture(root, "phase0-clean")
        write_state(devlyn, {"mode": "full", "base_ref": {"sha": _base}, "phases": {}})
        (devlyn / "plan.md").unlink()
        assert checked_run_gate(work, devlyn) == 0 and not (devlyn / FINDINGS_NAME).exists()
        work, devlyn, _base = make_fixture(root, "phase0-change")
        write_state(devlyn, {"mode": "full", "base_ref": {"sha": _base}, "phases": {}})
        write_text(work / "src" / "app.txt", "changed before any PLAN\n")
        assert checked_run_gate(work, devlyn) == 2
        assert (work / "src" / "app.txt").read_text(encoding="utf-8") == "base app\n"

        # Untracked files the run created are offenders too; the user's baseline files are kept.
        work, devlyn, _base = make_fixture(root, "untracked-residue")
        write_text(work / "keep.txt", "the user's\n")
        write_text(devlyn / "untracked.baseline", json.dumps({"untracked": ["keep.txt"], "sparse_absences": []}) + "\n")
        write_text(work / "stray.txt", "outside the baseline\n")
        assert checked_run_gate(work, devlyn) == 2
        assert (work / "stray.txt").is_file() and (work / "keep.txt").is_file()
        assert [(f["file"], f["status"]) for f in read_findings(devlyn)] == [("stray.txt", "retained")]

        # Paths are literal: an offender under app/[slug]/ never touches app/s/.
        work, devlyn, _base = make_fixture(root, "literal-paths")
        write_text(work / "app" / "s" / "page.tsx", "tracked route\n")
        git_check(work, "add", "app/s/page.tsx")
        git_check(work, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "route")
        write_state(devlyn, {"mode": "full", "base_ref": {"sha": git_check(work, "rev-parse", "HEAD")},
                             "phases": {"plan": {"started_at": "t", "completed_at": "t", "verdict": "PASS"}}})
        write_text(work / "app" / "[slug]" / "page.tsx", "new route\n")
        git_check(work, "add", "app/[slug]/page.tsx")
        assert checked_run_gate(work, devlyn) == 2
        assert "app/s/page.tsx" in git_check(work, "ls-files").splitlines()
        assert (work / "app" / "s" / "page.tsx").read_text(encoding="utf-8") == "tracked route\n"
        assert (work / "app" / "[slug]" / "page.tsx").is_file()
        work, devlyn, _base = make_fixture(root, "missing-baseline")
        (devlyn / "untracked.baseline").unlink()
        assert checked_run_gate(work, devlyn) == 1 and "untracked.baseline" in read_summary(devlyn)["malformed"]

        # The run's verification contract must still be what bootstrap bound, wherever PLAN's surface lies.
        def contract_fixture(name: str, committed: bytes | None, bound: bytes | None) -> tuple[pathlib.Path, pathlib.Path]:
            work, devlyn, base = make_fixture(root, name)
            write_text(work / "docs" / "spec.md", "# Spec\n")
            if committed is not None:
                (work / "docs" / "spec.expected.json").write_bytes(committed)
            git_check(work, "add", "-A")
            git_check(work, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "spec")
            base = git_check(work, "rev-parse", "HEAD")
            write_state(devlyn, {"mode": "spec", "base_ref": {"sha": base},
                                 "source": {"type": "spec", "spec_path": "docs/spec.md",
                                            "expected_sha256": hashlib.sha256(bound).hexdigest() if bound else None},
                                 "phases": {"plan": {"started_at": "t", "completed_at": "t", "verdict": "PASS"}}})
            return work, devlyn

        work, devlyn = contract_fixture("contract-appeared", None, None)
        write_text(work / "docs" / "spec.expected.json", '{"verification_commands": []}\n')
        assert checked_run_gate(work, devlyn) == 2 and not (work / "docs" / "spec.expected.json").exists()
        assert read_findings(devlyn)[0]["rule_id"] == "scope.finish-contract-drift"
        work, devlyn = contract_fixture("contract-restored", b'{"a": 1}\n', b'{"a": 1}\n')
        (work / "docs" / "spec.expected.json").write_bytes(b'{"a": 2}\n')
        assert checked_run_gate(work, devlyn) == 2
        assert (work / "docs" / "spec.expected.json").read_bytes() == b'{"a": 1}\n'
        work, devlyn = contract_fixture("contract-unrestorable", b'{"a": 0}\n', b'{"a": 1}\n')
        assert checked_run_gate(work, devlyn) == 2
        finding = read_findings(devlyn)[0]
        assert (finding["rule_id"], finding["status"]) == ("scope.finish-contract-drift", "revert-failed"), finding
        assert (work / "docs" / "spec.expected.json").read_bytes() == b'{"a": 0}\n'

        # A drifted contract offends even inside the authorized surface.
        work, devlyn = contract_fixture("contract-in-surface", None, None)
        (devlyn / "plan.md").write_text(
            "# PLAN\n\n<!-- devlyn:authorized-surface -->\n## Files to touch\n\n```json\n"
            '{"authorized_surface": ["src/app.txt", "docs/**"]}\n```\n', encoding="utf-8")
        write_text(work / "docs" / "spec.expected.json", '{"verification_commands": []}\n')
        assert checked_run_gate(work, devlyn) == 2 and not (work / "docs" / "spec.expected.json").exists()

        # A rename never hides its source: moving an out-of-surface file into the surface offends.
        work, devlyn, _base = make_fixture(root, "rename-into-surface")
        git_check(work, "rm", "-q", "src/app.txt")
        (work / "src").mkdir(exist_ok=True)
        git_check(work, "mv", "notes.txt", "src/app.txt")
        git_check(work, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "rename")
        assert checked_run_gate(work, devlyn) == 2
        assert "notes.txt" in [finding["file"] for finding in read_findings(devlyn)]

        # A planted symlink is removed itself; its target is never touched.
        work, devlyn = contract_fixture("contract-symlink", None, None)
        write_text(work / "docs" / "real.json", '{"verification_commands": []}\n')
        git_check(work, "add", "docs/real.json")
        git_check(work, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "real")
        state = json.loads((devlyn / "pipeline.state.json").read_text(encoding="utf-8"))
        state["base_ref"]["sha"] = git_check(work, "rev-parse", "HEAD")
        write_state(devlyn, state)
        (work / "docs" / "spec.expected.json").symlink_to("real.json")
        assert checked_run_gate(work, devlyn) == 2
        assert not os.path.lexists(work / "docs" / "spec.expected.json")
        assert (work / "docs" / "real.json").read_text(encoding="utf-8") == '{"verification_commands": []}\n'
        # Only the binding decides: an unrestorable contract is reported, even when it is out of surface and staged.
        work, devlyn = contract_fixture("contract-staged-unrestorable", None, b'{"a": 1}\n')
        write_text(work / "docs" / "spec.expected.json", '{"a": 2}\n')
        git_check(work, "add", "docs/spec.expected.json")
        assert checked_run_gate(work, devlyn) == 2
        assert [(f["rule_id"], f["status"]) for f in read_findings(devlyn)] == [("scope.finish-contract-drift", "revert-failed")]
        assert (work / "docs" / "spec.expected.json").read_text(encoding="utf-8") == '{"a": 2}\n'
        # A contract bound absent while base tracks it (a sparse absence) loses only its worktree copy.
        work, devlyn = contract_fixture("contract-sparse-absent", b'{"a": 1}\n', None)
        assert checked_run_gate(work, devlyn) == 2
        assert not (work / "docs" / "spec.expected.json").exists()
        assert "docs/spec.expected.json" in git_check(work, "ls-files", "docs")

    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--devlyn-dir", default=".devlyn")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    devlyn_dir = pathlib.Path(args.devlyn_dir)
    if not devlyn_dir.is_absolute():
        devlyn_dir = (pathlib.Path.cwd() / devlyn_dir).resolve()
    return run_gate(devlyn_dir.parent, devlyn_dir)


if __name__ == "__main__":
    runpy.run_path(str(pathlib.Path(__file__).with_name("platform-support.py")))["configure_utf8"]()
    raise SystemExit(main())
