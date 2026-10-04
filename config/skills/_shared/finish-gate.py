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
import stat
import subprocess
import sys
import tempfile
import unicodedata

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


def git(work: pathlib.Path, *args: str, text: bool = True) -> subprocess.CompletedProcess:
    # Paths are literal and verbatim from Git's own output: a route such as app/[slug]/page.tsx never
    # glob-matches another file and an NFD name is never precomposed into another. Hooks, replace refs
    # and the commit-graph are worker-writable, so none of them steers what the gate reads or restores.
    # Findings quote Git's errors in the C locale, and a name that is not UTF-8 never stops the gate midway.
    return subprocess.run(
        ["git", "--literal-pathspecs", "-c", "core.precomposeunicode=false", "-c", f"core.hooksPath={os.devnull}",
         "-c", "core.commitGraph=false", *args],
        cwd=str(work),
        capture_output=True,
        env={**os.environ, "GIT_NO_REPLACE_OBJECTS": "1", "LC_ALL": "C"},
        encoding="utf-8" if text else None,
        errors="surrogateescape" if text else None,
    )


def git_detail(proc: subprocess.CompletedProcess) -> str:
    return proc.stderr.strip() or proc.stdout.strip() or f"git exited {proc.returncode}"


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


def contract_drift(work: pathlib.Path, state: dict) -> tuple[str, str] | None:
    """A sibling spec.expected.json that is no longer what bootstrap bound: (path, why).

    It offends wherever PLAN's surface lies, so the next run cannot bind a worker's contract. Its path
    is spelled lexically from state.source.spec_path, nothing resolved: relative when it lies inside
    the worktree, else as given.
    """
    source = state.get("source") if isinstance(state.get("source"), dict) else {}
    if source.get("type") != "spec" or not source.get("spec_path"):
        return None
    spec = pathlib.Path(source["spec_path"])
    why = SPEC_VERIFY.expected_contract_error(source, spec if spec.is_absolute() else work / spec)
    if why is None:
        return None
    sibling = spec.with_name("spec.expected.json")
    if sibling.is_absolute() and work in sibling.parents:
        sibling = sibling.relative_to(work)
    return (sibling.as_posix(), why)


def unsettleable(work: pathlib.Path, path: str) -> str | None:
    """Why the contract's spelled location may not be the entry bootstrap bound, or None.

    A '..', a location outside the worktree or a parent directory that is a symlink (retargetable,
    so it can lead to anyone's file) is never acted on; a missing parent only means the leaf is absent.
    """
    spelled = pathlib.PurePath(path)
    if ".." in spelled.parts:
        return f"its path {path} climbs with '..'"
    if spelled.is_absolute():
        return f"it lies outside the worktree at {path}"
    parent = work
    for part in spelled.parts[:-1]:
        parent = parent / part
        try:
            if stat.S_ISLNK(parent.lstat().st_mode):
                return f"its parent directory {parent.relative_to(work).as_posix()} is a symlink"
        except (FileNotFoundError, NotADirectoryError):
            return None
        except OSError as e:
            return f"its parent directory {parent.relative_to(work).as_posix()} is inaccessible ({e})"
    return None


def is_contract(work: pathlib.Path, path: str, contract: str, fold: bool) -> bool:
    """Whether Git's `path` is the contract's own directory entry: its parent is the same directory and
    its name the same, case-folded only where Git ignores case. A separate hardlink stays an offender."""
    name, contract_name = pathlib.PurePath(path).name, pathlib.PurePath(contract).name
    if name != contract_name and not (fold and name.casefold() == contract_name.casefold()):
        return False
    try:
        return os.path.samefile((work / path).parent, (work / contract).parent)
    except OSError:
        return False  # a missing or inaccessible parent is not the contract's


def settle_contract(work: pathlib.Path, base_sha: str, bound: str | None, baseline: set[str],
                    path: str) -> tuple[bool, str, str | None]:
    """Return the drifted contract to its binding, acting only on the entry spelled from spec_path.

    Bound absence means no directory entry, so the run's entry is removed with its index entry; a
    sparse absence (base tracks the path) gets base's index entry back instead, and an entry the
    PHASE 0 baseline lists is the user's, so it is only reported. A bound digest is restored from
    base_ref.sha only when base holds exactly those bytes. Returns (settled, outcome, error detail).
    """
    why = unsettleable(work, path)
    if why is not None:
        return (False, f"reported only because {why}", None)
    if bound is not None:
        blob = git(work, "cat-file", "blob", f"{base_sha}:{path}", text=False)
        if blob.returncode != 0 or hashlib.sha256(blob.stdout).hexdigest() != bound:
            return (False, "reported only because base_ref.sha does not hold the bytes bootstrap bound",
                    blob.stderr.decode("utf-8", "surrogateescape").strip() or None)
        proc = git(work, "checkout", "--no-recurse-submodules", base_sha, "--", path)
        if proc.returncode != 0:
            return (False, "left in place because restoring it failed", git_detail(proc))
        return (True, "restored to the bytes bootstrap bound", None)
    entry, error = base_entry(work, base_sha, path)
    if error is not None:
        return (False, "left in place because looking it up at base_ref.sha failed", error)
    if entry is not None:
        # A sparse absence: base tracks the path, so its index entry returns and only the leaf goes.
        proc, step = git(work, "reset", "-q", base_sha, "--", path), "restoring base_ref.sha's index entry"
    elif path in {item.rstrip("/") for item in baseline}:
        return (False, "reported only because the PHASE 0 baseline lists it as the user's", None)
    else:
        proc, step = git(work, "rm", "-q", "--cached", "--ignore-unmatch", "--", path), "removing its index entry"
    if proc.returncode != 0:
        return (False, f"left in place because {step} failed", git_detail(proc))
    try:
        remove_worktree_path(work / path)
    except OSError as e:
        return (False, "left in place because removing it failed", str(e))
    return (True, "removed, as bootstrap bound its absence" + (", with base_ref.sha's index entry restored" if entry else ""),
            None)


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


def base_entry(work: pathlib.Path, base_sha: str, path: str) -> tuple[tuple[str, str] | None, str | None]:
    """`path`'s tree entry at base_ref.sha as (mode, oid), or None when base has none; and a failed lookup's error.

    The lookup never needs the entry's object: a gitlink's commit lives in the submodule, not here.
    """
    proc = git(work, "ls-tree", "-z", base_sha, "--", path)
    if proc.returncode != 0:
        return (None, git_detail(proc))
    if not proc.stdout:
        return (None, None)
    mode, _type, oid = proc.stdout.split("\t", 1)[0].split(" ")
    return ((mode, oid), None)


def remove_worktree_path(path: pathlib.Path) -> None:
    # One directory entry, a symlink itself, never recursively: an entry inside a directory has its own finding.
    if stat.S_ISDIR(path.lstat().st_mode):
        path.rmdir()
    else:
        path.unlink()


def revert_offender(work: pathlib.Path, base_sha: str, path: str) -> tuple[str, str, str | None]:
    """Undo an out-of-surface change without destroying bytes the run cannot prove it made.

    A path present at base_ref.sha is restored: bootstrap required a clean tracked baseline, so
    its change is the run's. A gitlink gets back only base's pointer in the index; its nested
    checkout is never moved. Any other path keeps its worktree bytes, losing only an index entry:
    absence from the PHASE 0 baseline does not prove the run created it (an ignore change can
    reveal a user's file). Returns (status, outcome, detail): "reverted", "retained" or
    "revert-failed", what actually happened, and Git's error.
    """
    entry, error = base_entry(work, base_sha, path)
    if error is not None:
        return ("revert-failed", "left in place because looking it up at base_ref.sha failed", error)
    if entry is not None:
        proc = git(work, "checkout", "--no-recurse-submodules", base_sha, "--", path)
        if proc.returncode != 0:
            return ("revert-failed", "left in place because restoring it failed", git_detail(proc))
        if entry[0] == "160000":
            return ("reverted", "restored to base_ref.sha's pointer in the index only; its nested checkout "
                                "was left at its current commit", None)
        return ("reverted", "restored to base_ref.sha", None)
    proc = git(work, "rm", "-q", "--cached", "--ignore-unmatch", "--", path)
    if proc.returncode != 0:
        return ("revert-failed", "left in place because removing its index entry failed", git_detail(proc))
    return ("retained", "kept in place (only an index entry removed): nothing proves this run created it", None)


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
    fold = contract is not None and git(work, "config", "--bool", "core.ignorecase").stdout.strip() == "true"
    offenders = sorted(path for path in checked if not (contract and is_contract(work, path, contract, fold)) and (
        not SPEC_VERIFY.path_matches_surface(path, surface) or SPEC_VERIFY.unadopted_user_path(path, baseline, surface)))
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
        ok, outcome, detail = settle_contract(work, base_sha, state["source"]["expected_sha256"], baseline, contract)
        counts["reverted" if ok else "revert-failed"] += 1
        findings.append(make_finding(
            1, "scope.finish-contract-drift",
            f"The run's verification contract is no longer what bootstrap bound: {drift[1]} The contract was {outcome}"
            + (f" ({detail})" if detail else "") + ".",
            contract, status="reverted" if ok else "revert-failed",
            criterion_ref="pipeline.state.json/source.expected_sha256",
            fix_hint=f"The contract was {outcome}; a run never verifies against a contract it changed.",
        ))
    for path in offenders:
        status, outcome, detail = revert_offender(work, base_sha, path)
        counts[status] += 1
        message = f"Final diff touched an unaudited file outside authorized_surface: {path}; it was {outcome}"
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


def sole_finding(devlyn: pathlib.Path, status: str, text: str) -> dict:
    finding, = read_findings(devlyn)
    assert finding["status"] == status and text in finding["message"], finding
    return finding


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
        # A refused index removal is reported as what happened: the file stays, and so does its index entry.
        work, devlyn, _base = make_fixture(root, "added-file-edited")
        write_text(work / "runtime.txt", "v1\n")
        git_check(work, "add", "runtime.txt")
        write_text(work / "runtime.txt", "v2\n")
        assert checked_run_gate(work, devlyn) == 2
        sole_finding(devlyn, "revert-failed", "it was left in place because removing its index entry failed "
                                              "(error: the following file has staged content")
        assert "runtime.txt" in git_check(work, "ls-files").splitlines()
        assert (work / "runtime.txt").read_text(encoding="utf-8") == "v2\n"
        assert_summary(devlyn, {"offenders": 1, "retained": 0, "revert_failed": 1, "exit": 2})

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

        # Repository hooks are worker code: none runs inside the gate to re-dirty what it restored.
        for hook in ("post-checkout", "post-index-change"):
            work, devlyn, _base = make_fixture(root, f"hook-{hook}")
            write_text(work / ".git" / "hooks" / hook, '#!/bin/sh\n[ -n "$DEVLYN_HOOKED" ] && exit 0\nexport DEVLYN_HOOKED=1\n'
                                                       "printf 'polluted again by a hook\\n' > notes.txt\n")
            (work / ".git" / "hooks" / hook).chmod(0o755)
            write_text(work / "notes.txt", "polluted\n")
            assert checked_run_gate(work, devlyn) == 2
            assert (work / "notes.txt").read_text(encoding="utf-8") == "base notes\n", hook

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

        # A user's pre-run file committed through a glob surface offends; its bytes stay.
        work, devlyn, _base = make_fixture(root, "user-file-swept")
        write_text(devlyn / "plan.md", "# PLAN\n\n<!-- devlyn:authorized-surface -->\n## Files to touch\n\n```json\n"
                                       '{"authorized_surface": ["src/**"]}\n```\n')
        write_text(work / "src" / "user.txt", "the user's\n")
        write_text(devlyn / "untracked.baseline", json.dumps({"untracked": ["src/user.txt"], "sparse_absences": []}) + "\n")
        git_check(work, "add", "src/user.txt")
        git_check(work, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "swept")
        assert checked_run_gate(work, devlyn) == 2
        assert (work / "src" / "user.txt").read_text(encoding="utf-8") == "the user's\n"
        assert [(f["file"], f["status"]) for f in read_findings(devlyn)] == [("src/user.txt", "retained")]

        # The same holds for a user's nested repository committed as a gitlink (baseline spelling `dir/`).
        work, devlyn, _base = make_fixture(root, "user-repo-swept")
        write_text(devlyn / "plan.md", "# PLAN\n\n<!-- devlyn:authorized-surface -->\n## Files to touch\n\n```json\n"
                                       '{"authorized_surface": ["src/**"]}\n```\n')
        vendor = work / "src" / "vendor"
        vendor.mkdir(parents=True)
        git_check(vendor, "init", "-q")
        git_check(vendor, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "vendor")
        write_text(devlyn / "untracked.baseline", json.dumps({"untracked": ["src/vendor/"], "sparse_absences": []}) + "\n")
        git_check(work, "add", "src/vendor")
        git_check(work, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "gitlink")
        assert checked_run_gate(work, devlyn) == 2
        assert (vendor / ".git").exists()
        assert [(f["file"], f["status"]) for f in read_findings(devlyn)] == [("src/vendor", "retained")]
        # An exact entry, either spelling, adopts it.
        for index, spelling in enumerate(("src/vendor", "src/vendor/")):
            work, devlyn, _base = make_fixture(root, f"user-repo-adopted-{index}")
            write_text(devlyn / "plan.md", "# PLAN\n\n<!-- devlyn:authorized-surface -->\n## Files to touch\n\n```json\n"
                                           + json.dumps({"authorized_surface": [spelling]}) + "\n```\n")
            vendor = work / "src" / "vendor"
            vendor.mkdir(parents=True)
            git_check(vendor, "init", "-q")
            git_check(vendor, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "vendor")
            write_text(devlyn / "untracked.baseline", json.dumps({"untracked": ["src/vendor/"], "sparse_absences": []}) + "\n")
            git_check(work, "add", "src/vendor")
            git_check(work, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "gitlink")
            assert checked_run_gate(work, devlyn) == 0, read_findings(devlyn)

        # An out-of-surface submodule bump, even one a committed `ignore = all` hides from plain diff, gets back
        # base's pointer in the index only: the child's commit is not in this object store, and the child's
        # checkout (HEAD, tracked and untracked bytes) and .gitmodules are never touched, whatever submodule.recurse says.
        writer = runpy.run_path(str(pathlib.Path(__file__).with_name("state-phase-write.py")))

        def rendered(work: pathlib.Path, devlyn: pathlib.Path) -> str:
            return writer["render_final_report"](read_state(devlyn / "pipeline.state.json"), devlyn, work,
                                                 "BLOCKED:finish-gate-unclean", None)

        def bumped_submodule(name: str, bump: str) -> tuple[pathlib.Path, pathlib.Path, pathlib.Path, str]:
            work, devlyn, _base = make_fixture(root, name)
            child = root / f"{name}-child"
            write_text(child / "lib.txt", "lib v1\n")
            git_check(child, "init", "-q")
            git_check(child, "add", "lib.txt")
            git_check(child, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "v1")
            git_check(work, "-c", "protocol.file.allow=always", "submodule", "add", "-q", str(child), "sub")
            git_check(work, "config", "-f", ".gitmodules", "submodule.sub.ignore", "all")
            git_check(work, "add", ".gitmodules")
            git_check(work, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "submodule")
            base = git_check(work, "rev-parse", "HEAD")
            write_state(devlyn, {"mode": "full", "base_ref": {"sha": base},
                                 "phases": {"plan": {"started_at": "t", "completed_at": "t", "verdict": "PASS"}}})
            sub = work / "sub"
            write_text(sub / "lib.txt", "lib v2\n")
            git_check(sub, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-am", "v2")
            write_text(sub / "scratch.txt", "the child's untracked bytes\n")
            if bump != "unstaged":
                git_check(work, "add", "sub")
            if bump == "committed":
                git_check(work, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "bump")
            return work, devlyn, sub, git_check(work, "ls-tree", base, "--", "sub").split()[2]

        for bump, recurse in (("committed", False), ("staged", True), ("unstaged", True)):
            work, devlyn, sub, pointer = bumped_submodule(f"submodule-{bump}", bump)
            if recurse:
                git_check(work, "config", "submodule.recurse", "true")
            assert git(work, "cat-file", "-e", pointer).returncode != 0
            head, gitmodules = git_check(sub, "rev-parse", "HEAD"), (work / ".gitmodules").read_bytes()
            assert checked_run_gate(work, devlyn) == 2
            finding, = read_findings(devlyn)
            assert (finding["file"], finding["status"]) == ("sub", "reverted"), finding
            assert finding["message"].endswith("sub; it was restored to base_ref.sha's pointer in the index only; "
                                               "its nested checkout was left at its current commit"), finding
            assert git_check(work, "ls-files", "-s", "--", "sub").split()[:2] == ["160000", pointer]
            assert git_check(sub, "rev-parse", "HEAD") == head and (work / ".gitmodules").read_bytes() == gitmodules
            assert (sub / "lib.txt").read_text(encoding="utf-8") == "lib v2\n"
            assert (sub / "scratch.txt").read_text(encoding="utf-8") == "the child's untracked bytes\n"
        assert finding["message"] in rendered(work, devlyn)

        # A failed base lookup is never taken for absence: the gitlink keeps its staged pointer, the failure is
        # what the finding shows, and the offenders after it are still settled and recorded.
        work, devlyn, sub, pointer = bumped_submodule("submodule-lookup-failure", "staged")
        write_text(work / "tmp.txt", "a later offender\n")
        staged = git_check(work, "ls-files", "-s", "--", "sub")
        real_git = git

        def failing_lookup(where: pathlib.Path, *args: str, **kwargs) -> subprocess.CompletedProcess:
            if args[:2] == ("ls-tree", "-z") and args[-1] == "sub":
                return subprocess.CompletedProcess(args, 128, "", "fatal: simulated lookup failure\n")
            return real_git(where, *args, **kwargs)

        globals()["git"] = failing_lookup
        try:
            assert checked_run_gate(work, devlyn) == 2
        finally:
            globals()["git"] = real_git
        assert [(f["file"], f["status"]) for f in read_findings(devlyn)] == [("sub", "revert-failed"), ("tmp.txt", "retained")]
        assert git_check(work, "ls-files", "-s", "--", "sub") == staged
        assert_summary(devlyn, {"offenders": 2, "reverted": 0, "retained": 1, "revert_failed": 1})
        report = rendered(work, devlyn)
        assert "sub; it was left in place because looking it up at base_ref.sha failed (fatal: simulated lookup failure)" \
            in report
        assert "tmp.txt; it was kept in place (only an index entry removed)" in report

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

        # Paths are Git's own spelling, used verbatim: an NFD name committed without precomposition is restored
        # when edited or deleted, never precomposed away from base's entry (PHASE 0 lists macOS's NFC phantom).
        nfd = unicodedata.normalize("NFD", "문서.txt")
        for change in ("edited", "deleted"):
            work, devlyn, _base = make_fixture(root, f"nfd-{change}")
            write_text(work / nfd, "base doc\n")
            git_check(work, "-c", "core.precomposeunicode=false", "add", "--", nfd)
            git_check(work, "-c", "core.precomposeunicode=false", "-c", "user.email=t@t", "-c", "user.name=t",
                      "commit", "-q", "-m", "nfd")
            write_state(devlyn, {"mode": "full", "base_ref": {"sha": git_check(work, "rev-parse", "HEAD")},
                                 "phases": {"plan": {"started_at": "t", "completed_at": "t", "verdict": "PASS"}}})
            assert SPEC_VERIFY.run_write_untracked_baseline(work, devlyn) == 0
            if change == "edited":
                write_text(work / nfd, "run edit\n")
            else:
                (work / nfd).unlink()
            assert checked_run_gate(work, devlyn) == 2
            assert [(f["file"], f["status"]) for f in read_findings(devlyn)] == [(nfd, "reverted")], change
            assert (work / nfd).read_text(encoding="utf-8") == "base doc\n"

        # A non-UTF-8 name never stops the gate midway: every finding and the summary are written, and a rerun
        # returns that first result. APFS cannot hold such names, so the untracked one is injected into the
        # listing and the tracked one exists only in base and the index.
        work, devlyn, _base = make_fixture(root, "non-utf8-names")
        tracked, untracked = os.fsdecode(b"y-caf\xe9.txt"), os.fsdecode(b"z-caf\xe9.txt")
        git_check(work, "update-index", "--add", "--cacheinfo",
                  f"100644,{git_check(work, 'rev-parse', 'HEAD:notes.txt')},{tracked}")
        git_check(work, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "tracked")
        write_state(devlyn, {"mode": "full", "base_ref": {"sha": git_check(work, "rev-parse", "HEAD")},
                             "phases": {"plan": {"started_at": "t", "completed_at": "t", "verdict": "PASS"}}})
        write_text(work / "notes.txt", "polluted\n")
        listed = SPEC_VERIFY.current_untracked_files
        SPEC_VERIFY.current_untracked_files = lambda *args: (listed(*args)[0] | {untracked}, None)
        try:
            assert checked_run_gate(work, devlyn) == 2
        finally:
            SPEC_VERIFY.current_untracked_files = listed
        findings = read_findings(devlyn)
        assert [(f["file"], f["status"]) for f in findings] == [
            ("notes.txt", "reverted"), (tracked, "reverted" if os.path.lexists(work / tracked) else "revert-failed"),
            (untracked, "retained")], findings
        first_summary = (devlyn / SUMMARY_NAME).read_bytes()
        assert_summary(devlyn, {"checked": 3, "offenders": 3, "exit": 2})
        assert checked_run_gate(work, devlyn) == 2
        assert (devlyn / SUMMARY_NAME).read_bytes() == first_summary and read_findings(devlyn) == findings

        # The run's verification contract must still be what bootstrap bound, wherever PLAN's surface lies.
        def contract_fixture(name: str, committed: bytes | None, bound: bytes | None,
                             spec_path: str = "docs/spec.md") -> tuple[pathlib.Path, pathlib.Path]:
            work, devlyn, base = make_fixture(root, name)
            write_text(work / "docs" / "spec.md", "# Spec\n")
            if committed is not None:
                (work / "docs" / "spec.expected.json").write_bytes(committed)
            git_check(work, "add", "-A")
            git_check(work, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "spec")
            base = git_check(work, "rev-parse", "HEAD")
            write_state(devlyn, {"mode": "spec", "base_ref": {"sha": base},
                                 "source": {"type": "spec", "spec_path": spec_path,
                                            "expected_sha256": None if bound is None else hashlib.sha256(bound).hexdigest()},
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

        # A rename never hides its source: moving an out-of-surface file to a new path inside the surface offends.
        work, devlyn, _base = make_fixture(root, "rename-into-surface")
        write_text(devlyn / "plan.md", "# PLAN\n\n<!-- devlyn:authorized-surface -->\n## Files to touch\n\n```json\n"
                                       '{"authorized_surface": ["src/app.txt", "src/moved.txt"]}\n```\n')
        git_check(work, "mv", "notes.txt", "src/moved.txt")
        git_check(work, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "rename")
        assert checked_run_gate(work, devlyn) == 2
        assert [(f["file"], f["status"]) for f in read_findings(devlyn)] == [("notes.txt", "reverted")]
        assert (work / "notes.txt").read_text(encoding="utf-8") == "base notes\n"

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
        # A contract bound absent while base tracks it (a sparse absence) gets back base's index entry, mode and
        # object alike, and loses only the copy the run materialized.
        work, devlyn = contract_fixture("contract-sparse-absent", b'{"a": 1}\n', None)
        git_check(work, "update-index", "--skip-worktree", "docs/spec.expected.json")
        (work / "docs" / "spec.expected.json").unlink()
        assert SPEC_VERIFY.run_write_untracked_baseline(work, devlyn) == 0
        git_check(work, "update-index", "--no-skip-worktree", "docs/spec.expected.json")
        (work / "docs" / "spec.expected.json").write_bytes(b'{"a": 2}\n')
        (work / "docs" / "spec.expected.json").chmod(0o755)
        git_check(work, "add", "docs/spec.expected.json")
        assert checked_run_gate(work, devlyn) == 2
        assert [(f["file"], f["status"]) for f in read_findings(devlyn)] == [("docs/spec.expected.json", "reverted")]
        mode, _kind, oid = git_check(work, "ls-tree", "HEAD", "--", "docs/spec.expected.json").split()[:3]
        assert git_check(work, "ls-files", "-s", "--", "docs/spec.expected.json").split()[:2] == [mode, oid]
        assert not os.path.lexists(work / "docs" / "spec.expected.json")

        # Bound absence means no directory entry: a planted dangling symlink is drift and goes itself (nothing
        # appears at its target), and a planted directory is drift left in place, its contents keeping their own finding.
        work, devlyn = contract_fixture("contract-dangling-symlink", None, None)
        (work / "docs" / "spec.expected.json").symlink_to("missing.json")
        assert checked_run_gate(work, devlyn) == 2
        assert [(f["rule_id"], f["status"]) for f in read_findings(devlyn)] == [("scope.finish-contract-drift", "reverted")]
        assert not os.path.lexists(work / "docs" / "spec.expected.json") and not os.path.lexists(work / "docs" / "missing.json")
        work, devlyn = contract_fixture("contract-directory", None, None)
        write_text(work / "docs" / "spec.expected.json" / "inner.json", "{}\n")
        assert checked_run_gate(work, devlyn) == 2
        findings = read_findings(devlyn)
        assert [(f["file"], f["status"]) for f in findings] == [
            ("docs/spec.expected.json", "revert-failed"), ("docs/spec.expected.json/inner.json", "retained")], findings
        assert "The contract was left in place because removing it failed" in findings[0]["message"]
        assert (work / "docs" / "spec.expected.json" / "inner.json").read_text(encoding="utf-8") == "{}\n"

        # Only the entry spelled from spec_path is settled: through '..' or a parent directory that is a symlink
        # (retargeted since bootstrap, here at the user's draft), the drift is reported and nothing is touched.
        work, devlyn = contract_fixture("contract-dotdot", None, None, "src/../docs/spec.md")
        write_text(work / "docs" / "spec.expected.json", '{"draft": 1}\n')
        assert checked_run_gate(work, devlyn) == 2
        sole_finding(devlyn, "revert-failed", "The contract was reported only because its path "
                                              "src/../docs/spec.expected.json climbs with '..'.")
        assert (work / "docs" / "spec.expected.json").read_text(encoding="utf-8") == '{"draft": 1}\n'
        work, devlyn = contract_fixture("contract-symlinked-parent", None, None, "current/spec.md")
        write_text(work / "drafts" / "spec.expected.json", "the user's draft\n")
        (work / "current").symlink_to("drafts")
        write_text(devlyn / "untracked.baseline",
                   json.dumps({"untracked": ["current", "drafts/spec.expected.json"], "sparse_absences": []}) + "\n")
        assert checked_run_gate(work, devlyn) == 2
        assert sole_finding(devlyn, "revert-failed", "reported only because its parent directory current is a symlink"
                            )["file"] == "current/spec.expected.json"
        assert (work / "drafts" / "spec.expected.json").read_text(encoding="utf-8") == "the user's draft\n"
        # An entry the PHASE 0 baseline lists is the user's whatever bootstrap bound: reported, never removed.
        work, devlyn = contract_fixture("contract-baseline-listed", None, None)
        write_text(work / "docs" / "spec.expected.json", "the user's draft\n")
        write_text(devlyn / "untracked.baseline",
                   json.dumps({"untracked": ["docs/spec.expected.json"], "sparse_absences": []}) + "\n")
        assert checked_run_gate(work, devlyn) == 2
        sole_finding(devlyn, "revert-failed", "reported only because the PHASE 0 baseline lists it as the user's")
        assert (work / "docs" / "spec.expected.json").read_text(encoding="utf-8") == "the user's draft\n"
        # An entry that cannot be inspected is never taken for absence: drift, reported with the error.
        work, devlyn = contract_fixture("contract-uninspectable", None, None, "x" * 300 + "/spec.md")
        assert checked_run_gate(work, devlyn) == 2
        message = sole_finding(devlyn, "revert-failed", "whose absence bootstrap bound:")["message"]
        assert "is inaccessible (" in message and "File name too long" in message, message

        # Identity is the directory entry: a case alias of the spelling is one disposition, while a separate
        # hardlink stays an offender of its own.
        work, devlyn = contract_fixture("contract-case-alias", None, None, "Docs/spec.md")
        if not (work / "DOCS").exists():
            print("SKIP case-alias contract fixture: this filesystem is case-sensitive")
        else:
            write_text(work / "docs" / "Spec.Expected.json", "{}\n")
            assert checked_run_gate(work, devlyn) == 2
            assert [(f["file"], f["status"]) for f in read_findings(devlyn)] == [("Docs/spec.expected.json", "reverted")]
            assert not os.path.lexists(work / "docs" / "Spec.Expected.json")
        work, devlyn = contract_fixture("contract-hardlink", None, None)
        write_text(work / "docs" / "spec.expected.json", "{}\n")
        os.link(work / "docs" / "spec.expected.json", work / "docs" / "linked.json")
        assert checked_run_gate(work, devlyn) == 2
        assert [(f["file"], f["status"]) for f in read_findings(devlyn)] == [
            ("docs/spec.expected.json", "reverted"), ("docs/linked.json", "retained")]
        assert (work / "docs" / "linked.json").read_text(encoding="utf-8") == "{}\n"

        # A missing leaf is still the contract's entry (one disposition); with its parent directory missing too,
        # Git's path is no entry of the contract's, so it is settled on its own as well.
        work, devlyn = contract_fixture("contract-missing-leaf", b'{"a": 1}\n', b'{"a": 1}\n')
        (work / "docs" / "spec.expected.json").unlink()
        assert checked_run_gate(work, devlyn) == 2
        assert [(f["file"], f["status"]) for f in read_findings(devlyn)] == [("docs/spec.expected.json", "reverted")]
        assert (work / "docs" / "spec.expected.json").read_bytes() == b'{"a": 1}\n'
        work, devlyn = contract_fixture("contract-missing-parent", b'{"a": 1}\n', b'{"a": 1}\n')
        for name in ("spec.expected.json", "spec.md"):
            (work / "docs" / name).unlink()
        (work / "docs").rmdir()
        assert checked_run_gate(work, devlyn) == 2
        assert [(f["rule_id"], f["file"], f["status"]) for f in read_findings(devlyn)] == [
            ("scope.finish-contract-drift", "docs/spec.expected.json", "reverted"),
            ("scope.finish-unaudited-file", "docs/spec.expected.json", "reverted"),
            ("scope.finish-unaudited-file", "docs/spec.md", "reverted")]
        assert (work / "docs" / "spec.expected.json").read_bytes() == b'{"a": 1}\n'

        # A failed settle is reported as what happened, never as the settle it tried.
        work, devlyn = contract_fixture("contract-staged-edited", None, None)
        write_text(work / "docs" / "spec.expected.json", '{"a": 1}\n')
        git_check(work, "add", "docs/spec.expected.json")
        write_text(work / "docs" / "spec.expected.json", '{"a": 2}\n')
        assert checked_run_gate(work, devlyn) == 2
        finding = sole_finding(devlyn, "revert-failed", "The contract was left in place because removing its index entry "
                                                        "failed (error:")
        assert finding["fix_hint"].startswith("The contract was left in place because removing its index entry failed;")
        assert (work / "docs" / "spec.expected.json").read_text(encoding="utf-8") == '{"a": 2}\n'
        assert "docs/spec.expected.json" in git_check(work, "ls-files", "docs").splitlines()
        assert_summary(devlyn, {"offenders": 1, "reverted": 0, "revert_failed": 1})
        if os.geteuid() == 0:
            print("SKIP read-only-parent contract fixture: permissions do not bind root")
        else:
            work, devlyn = contract_fixture("contract-read-only-parent", None, None)
            write_text(work / "docs" / "spec.expected.json", "{}\n")
            (work / "docs").chmod(0o555)
            try:
                assert checked_run_gate(work, devlyn) == 2
            finally:
                (work / "docs").chmod(0o755)
            sole_finding(devlyn, "revert-failed", "The contract was left in place because removing it failed ([Errno 13]")
            assert (work / "docs" / "spec.expected.json").read_text(encoding="utf-8") == "{}\n"
            assert_summary(devlyn, {"offenders": 1, "reverted": 0, "revert_failed": 1})
        work, devlyn = contract_fixture("contract-restore-locked", b'{"a": 1}\n', b'{"a": 1}\n')
        (work / "docs" / "spec.expected.json").write_bytes(b'{"a": 2}\n')
        (work / ".git" / "index.lock").write_bytes(b"")
        try:
            assert checked_run_gate(work, devlyn) == 2
        finally:
            (work / ".git" / "index.lock").unlink()
        sole_finding(devlyn, "revert-failed", "The contract was left in place because restoring it failed "
                                              "(fatal: Unable to create")
        assert (work / "docs" / "spec.expected.json").read_bytes() == b'{"a": 2}\n'
        assert_summary(devlyn, {"offenders": 1, "reverted": 0, "revert_failed": 1})
        # A failed read of base's copy is not empty bytes, even when bootstrap bound an empty contract.
        work, devlyn = contract_fixture("contract-empty-bound", None, b"")
        write_text(work / "docs" / "spec.expected.json", "{}\n")
        assert checked_run_gate(work, devlyn) == 2
        sole_finding(devlyn, "revert-failed", "reported only because base_ref.sha does not hold the bytes bootstrap bound "
                                              "(fatal:")

        # The gate reads and restores genuine objects: a worker's replace refs never choose the bytes it restores.
        work, devlyn = contract_fixture("replaced-objects", b'{"a": 1}\n', b'{"a": 1}\n')
        write_text(root / "forged.txt", "forged\n")
        forged = git_check(work, "hash-object", "-w", str(root / "forged.txt"))
        for path in ("notes.txt", "docs/spec.expected.json"):
            git_check(work, "replace", git_check(work, "rev-parse", f"HEAD:{path}"), forged)
            write_text(work / path, "the run's\n")
        assert checked_run_gate(work, devlyn) == 2
        assert (work / "notes.txt").read_text(encoding="utf-8") == "base notes\n"
        assert (work / "docs" / "spec.expected.json").read_bytes() == b'{"a": 1}\n'

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
