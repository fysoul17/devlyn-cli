#!/usr/bin/env python3
"""Deterministic PHASE 6 final-diff gate for /devlyn-resolve, and the post-fix checkpoint's repair settlement."""
from __future__ import annotations

import runpy
import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import shutil
import stat
import subprocess
import sys
import tempfile
import unicodedata

sys.dont_write_bytecode = True

FINDINGS_NAME = "finish-gate.findings.jsonl"
SUMMARY_NAME = "finish-gate.summary.json"
PHASE = "finish_gate"
LEAF_MODES = ("100644", "100755", "120000")
SETTLE_CLOSE = ("Do not checkpoint. Complete IMPLEMENT exactly BLOCKED, then run FINAL_REPORT, the finish gate first, "
                "and let it derive the verdict: an offender left behind makes it BLOCKED:finish-gate-unclean; only "
                "if the gate is clean, supply --verdict BLOCKED:repair-unsettled.")


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


def changed_files(work: pathlib.Path, base_sha: str, sparse_absences: frozenset[str], *, staged: bool = False) -> set[str]:
    """Paths changed since base_ref.sha (committed or not, both sides of a rename), observed as MECHANICAL observes;
    `staged` adds those whose index entry alone differs, which a checkpoint would commit."""
    diff = ("diff", "--name-only", "-z", "--no-renames", "--ignore-submodules=none")
    try:
        with SPEC_VERIFY.observed_git(work, sparse_absences) as (observe, _flags):
            raw = observe(*diff, base_sha, "--") + (observe(*diff, "--cached", base_sha, "--") if staged else b"")
    except (OSError, ValueError) as e:
        raise Malformed(f"cannot compute finish-gate changed files: {e}") from e
    return {os.fsdecode(path) for path in raw.split(b"\0") if path}


def checked_paths(work: pathlib.Path, devlyn_dir: pathlib.Path, base_sha: str, ownership, sparse_absences: frozenset[str],
                  *, staged: bool = False) -> list[str]:
    """The run's changes outside .devlyn: paths changed since base_ref.sha, and untracked paths the PHASE 0
    inventory does not cover."""
    changed = changed_files(work, base_sha, sparse_absences, staged=staged)
    untracked, untracked_error = SPEC_VERIFY.current_untracked_files(work, sparse_absences)
    if untracked_error is not None:
        raise Malformed(f"cannot list untracked files: {untracked_error}")
    changed |= {path for path in untracked if not ownership.covers(path)}
    devlyn_prefix = devlyn_relative_prefix(work, devlyn_dir)
    return sorted(path for path in changed if not is_under_prefix(path, devlyn_prefix))


def offends(path: str, surface: list[str], ownership, exact: frozenset[str]) -> bool:
    """Outside PLAN's bound surface, or a path the PHASE 0 inventory covers that no exact surface entry adopts."""
    return not SPEC_VERIFY.path_matches_surface(path, surface) or SPEC_VERIFY.unadopted_user_path(path, ownership, exact)


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


def unsettleable(work: pathlib.Path, path: str, fold: bool = False) -> str | None:
    """Why a spelled location may not be the entry it names, or None.

    A '..', a location outside the worktree or a parent directory that is a symlink (retargetable,
    so it can lead to anyone's file) is never acted on; a missing parent only means the leaf is absent.
    Where Git ignores case (`fold`), neither is a component spelled in another case than its directory
    entry: Git's index and trees and the PHASE 0 inventory hold the entry's own spelling.
    """
    spelled = pathlib.PurePath(path)
    if ".." in spelled.parts:
        return f"its path {path} climbs with '..'"
    if spelled.is_absolute():
        return f"it lies outside the worktree at {path}"
    parent = work
    for depth, part in enumerate(spelled.parts, 1):
        if fold:
            try:
                names = os.listdir(parent)
            except (FileNotFoundError, NotADirectoryError):
                return None
            except OSError as e:
                return f"its directory {'/'.join(spelled.parts[:depth - 1]) or '.'} cannot be listed ({e})"
            if part not in names and (alias := [name for name in names if name.casefold() == part.casefold()]):
                return f"its spelling {'/'.join(spelled.parts[:depth])} differs in case from the directory entry {alias[0]}"
        if depth == len(spelled.parts):
            return None
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
    its name the same, case-folded only where Git ignores case; with no parent to compare (missing or
    inaccessible), the same spelling is. A separate hardlink stays an offender."""
    name, contract_name = pathlib.PurePath(path).name, pathlib.PurePath(contract).name
    if name != contract_name and not (fold and name.casefold() == contract_name.casefold()):
        return False
    try:
        return os.path.samefile((work / path).parent, (work / contract).parent)
    except OSError:
        return path == contract or (fold and path.casefold() == contract.casefold())


def directory_occupies(work: pathlib.Path, path: str) -> str | None:
    """Why base's file must not be checked out at `path`: a real directory there, which checkout would delete
    with its contents although each has a disposition of its own, or one that cannot be inspected."""
    try:
        return ("a directory occupies it; restoring would delete its contents"
                if stat.S_ISDIR((work / path).lstat().st_mode) else None)
    except (FileNotFoundError, NotADirectoryError):
        return None
    except OSError as e:
        return f"inspecting it failed ({e})"


def settle_contract(work: pathlib.Path, base_sha: str, bound: str | None, ownership, sparse_absences: frozenset[str],
                    path: str, fold: bool) -> tuple[bool, str, str | None]:
    """Return the drifted contract to its binding, acting only on the entry spelled from spec_path.

    Bound absence means no directory entry, so the run's entry is removed with its index entry; a
    sparse absence (base tracks the path) gets base's index entry back instead, skip-worktree again
    where PHASE 0 recorded the absence, and an entry the PHASE 0 inventory covers is the user's, so it
    is only reported. A bound digest is restored from base_ref.sha only when base holds exactly those
    bytes and no directory occupies the path. Returns (settled, outcome, error detail).
    """
    why = unsettleable(work, path, fold)
    if why is not None:
        return (False, f"reported only because {why}", None)
    if bound is not None:
        blob = git(work, "cat-file", "blob", f"{base_sha}:{path}", text=False)
        if blob.returncode != 0 or hashlib.sha256(blob.stdout).hexdigest() != bound:
            return (False, "reported only because base_ref.sha does not hold the bytes bootstrap bound",
                    blob.stderr.decode("utf-8", "surrogateescape").strip() or None)
        occupied = directory_occupies(work, path)
        if occupied is not None:
            return (False, f"left in place because {occupied}", None)
        proc = git(work, "checkout", "--no-recurse-submodules", base_sha, "--", path)
        if proc.returncode != 0:
            return (False, "left in place because restoring it failed", git_detail(proc))
        return (True, "restored to the bytes bootstrap bound", None)
    entry, error = base_entry(work, base_sha, path)
    if error is not None:
        return (False, "left in place because looking it up at base_ref.sha failed", error)
    if entry is not None:
        # A sparse absence: base tracks the path, so its index entry returns and only the leaf goes.
        steps = [(("reset", "-q", base_sha, "--", path), "restoring base_ref.sha's index entry")]
        if path in sparse_absences:
            steps.append((("update-index", "--skip-worktree", "--", path), "marking it skip-worktree"))
    elif ownership.covers(path):
        return (False, "reported only because the PHASE 0 inventory covers it as the user's", None)
    else:
        steps = [(("rm", "-q", "--cached", "--ignore-unmatch", "--", path), "removing its index entry")]
    for args, step in steps:
        proc = git(work, *args)
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

    The lookup never needs the entry's object: a gitlink's commit lives in the submodule, not here. A
    trailing "/" (how Git lists a nested repository) still names the entry itself, never a tree's contents.
    """
    proc = git(work, "ls-tree", "-z", base_sha, "--", path.rstrip("/"))
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
    its change is the run's, unless a directory now occupies a base file's path. A gitlink gets back
    only base's pointer in the index; its nested checkout is never moved. Any other path keeps its
    worktree bytes, losing only an index entry: the gate never deletes, since a deletion decision
    needs the verified PHASE 0 inventory the repair settlement checks. Returns (status, outcome,
    detail): "reverted", "retained" or "revert-failed", what actually happened, and Git's error.
    """
    entry, error = base_entry(work, base_sha, path)
    if error is not None:
        return ("revert-failed", "left in place because looking it up at base_ref.sha failed", error)
    if entry is not None:
        occupied = directory_occupies(work, path) if entry[0] in LEAF_MODES else None
        if occupied is not None:
            return ("revert-failed", f"left in place because {occupied}", None)
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
        ownership, sparse_absences, baseline_error = SPEC_VERIFY.load_untracked_baseline(devlyn_dir)
        if baseline_error is not None:
            raise Malformed(baseline_error, ".devlyn/untracked.baseline")
        checked = checked_paths(work, devlyn_dir, base_sha, ownership, sparse_absences)
        drift = contract_drift(work, state)
    except Malformed as e:
        findings_path.unlink(missing_ok=True)
        write_findings(devlyn_dir, [malformed_finding(e)])
        write_summary(devlyn_dir, {"exit": 1, "malformed": str(e)})
        return 1

    contract = drift[0] if drift is not None else None
    fold = contract is not None and git(work, "config", "--bool", "core.ignorecase").stdout.strip() == "true"
    exact = frozenset(entry.rstrip("/") for entry in surface)
    offenders = [path for path in checked
                 if not (contract and is_contract(work, path, contract, fold)) and offends(path, surface, ownership, exact)]
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
        ok, outcome, detail = settle_contract(work, base_sha, state["source"]["expected_sha256"], ownership,
                                              sparse_absences, contract, fold)
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


def settle_gitlink(work: pathlib.Path, base_sha: str, path: str, oid: str) -> tuple[bool, str, str]:
    """Give a gitlink back base's pointer in the index only and read that entry back: devlyn never moves or fetches a
    nested checkout, so it settles only when the checkout is already at that commit with nothing visible beyond it
    (its own index flags and ignore rules trusted)."""
    proc = git(work, "restore", "--staged", "--no-recurse-submodules", f"--source={base_sha}", "--", path)
    if proc.returncode != 0:
        return (False, "restore-failed", f"restoring base_ref.sha's pointer {oid} in the index failed ({git_detail(proc)})")
    readback = git(work, "ls-files", "-s", "-z", "--", path)
    if readback.returncode != 0 or [record.split("\t", 1)[0].split() for record in readback.stdout.split("\0")
                                    if record] != [["160000", oid, "0"]]:
        found = git_detail(readback) if readback.returncode != 0 else readback.stdout.strip("\0") or "no entry"
        return (False, "pointer-unverified", f"reading back its index entry did not show base_ref.sha's pointer {oid} ({found})")
    restored = f"base_ref.sha's pointer {oid} was restored in the index only, but the nested checkout {path}"
    child = work / path
    try:
        if not stat.S_ISDIR(child.lstat().st_mode):
            return (False, "pointer-restored", f"{restored} is no longer a directory")
        if not SPEC_VERIFY._present(child / ".git"):
            return (False, "pointer-restored", f"{restored} is not initialized (it has no .git), so its commit is unknown")
        head = SPEC_VERIFY._child_git(child, "rev-parse", "--verify", "-q", "HEAD").decode("utf-8", "surrogateescape").strip()
        residue = SPEC_VERIFY._child_git(child, "status", "--porcelain=v1", "-z", "--untracked-files=all",
                                         "--ignore-submodules=none") if head == oid else b""
    except (OSError, ValueError) as e:
        return (False, "pointer-restored", f"{restored} could not be read ({e})")
    if head != oid:
        return (False, "pointer-restored", f"{restored} is at {head}; devlyn does not move nested checkouts")
    if residue:
        entries, error = SPEC_VERIFY.parse_status(residue)
        return (False, "pointer-restored", f"{restored} at that commit holds content the commit lacks: "
                + (", ".join(f"{path}/{name}" for _status, name in entries) or str(error)))
    return (True, "pointer-restored",
            f"restored to base_ref.sha's pointer {oid}; its nested checkout is at that commit and clean")


def covered_inside(work: pathlib.Path, directory: pathlib.Path, ownership) -> str | None:
    """Why an uncovered directory may not be deleted whole: a path inside it the PHASE 0 inventory covers, or a part
    that cannot be read, walking without following symlinks; None when nothing inside is the user's."""
    def refuse(error: OSError) -> None:
        raise error

    try:
        for top, dirs, files in os.walk(directory, onerror=refuse):
            for name in sorted(dirs + files):
                inner = pathlib.Path(top, name).relative_to(work).as_posix()
                if ownership.covers(inner):
                    return f"{inner} inside it is the user's"
    except OSError as e:
        return f"part of it cannot be read ({e})"
    return None


def settle_added(work: pathlib.Path, path: str, ownership) -> tuple[bool, str, str]:
    """A path base lacks loses any index entry, never by force; then the PHASE 0 inventory decides: a covered path is
    the user's and kept, an uncovered one this run created and is deleted (a directory only when nothing in it is
    covered)."""
    proc = git(work, "rm", "-q", "--cached", "--ignore-unmatch", "--", path)
    if proc.returncode != 0:
        return (False, "unstage-failed", f"left in place because removing its index entry failed ({git_detail(proc)})")
    if ownership.covers(path):
        return (True, "kept", "kept in place with no index entry: the PHASE 0 inventory covers it as the user's")
    target = work / path
    try:
        if not SPEC_VERIFY._present(target):
            return (True, "deleted", "no index entry remains, and it was already gone")
        if stat.S_ISDIR(target.lstat().st_mode):
            refusal = covered_inside(work, target, ownership)
            if refusal is not None:
                return (False, "kept", f"no index entry remains, but it was kept whole because {refusal}")
            shutil.rmtree(target)
        else:
            target.unlink()
    except OSError as e:
        return (False, "delete-failed", f"no index entry remains, but deleting it failed ({e})")
    return (True, "deleted", "deleted: the PHASE 0 inventory does not cover it, so this run created it")


def settle_path(work: pathlib.Path, base_sha: str, path: str, ownership) -> tuple[bool, str, str]:
    """Settle one offender a VERIFY repair round left: (settled, action, detail), settled meaning the state left behind.

    A path base holds gets base's entry back (a gitlink its pointer in the index only); a path base lacks loses its
    index entry and is kept or deleted as the PHASE 0 inventory decides. A failed lookup is never absence, a tree is
    never restored whole, and nothing is acted on through '..' or a symlinked parent.
    """
    why = unsettleable(work, path)
    if why is not None:
        return (False, "none", f"left in place because {why}")
    entry, error = base_entry(work, base_sha, path)
    if error is not None:
        return (False, "none", f"left in place because looking it up at base_ref.sha failed ({error})")
    key = path.rstrip("/")
    if entry is None:
        return settle_added(work, key, ownership)
    if entry[0] == "160000":
        return settle_gitlink(work, base_sha, key, entry[1])
    if entry[0] not in LEAF_MODES:
        return (False, "none", f"left in place because base_ref.sha holds a tree ({entry[0]}) there, never restored whole")
    occupied = directory_occupies(work, key)
    if occupied is not None:
        return (False, "none", f"left in place because {occupied}")
    proc = git(work, "checkout", "--no-recurse-submodules", base_sha, "--", key)
    if proc.returncode != 0:
        return (False, "restore-failed", f"left in place because restoring it failed ({git_detail(proc)})")
    return (True, "restored", "restored to base_ref.sha")


def emit(message: str) -> None:
    # As bytes: a path that is not UTF-8 is named as Git holds it.
    sys.stderr.buffer.write(message.encode("utf-8", "surrogateescape"))


def run_settle(work: pathlib.Path, devlyn_dir: pathlib.Path, round_: int) -> int:
    """The post-fix checkpoint's settlement, after a budget-admitted VERIFY repair IMPLEMENT round and before its commit.

    Every current offender, by the gate's own predicate over the worktree and the index the checkpoint commits, is
    settled path by path; the merged scope findings only record which they named. Bindings come first and refuse
    before any change: IMPLEMENT open at `round_` triggered by VERIFY, that VERIFY closed NEEDS_WORK with merged
    findings, the bound PLAN, and the complete PHASE 0 inventory at its bound digest. Writes
    .devlyn/repair-settle.r<round_>.json, never the gate's own result. Exit 0 settled, 2 unsettled, 1 refused.
    """
    try:
        state = read_state(devlyn_dir / "pipeline.state.json")
        phases = state.get("phases") or {}
        implement, verify = phases.get("implement"), phases.get("verify")
        if not (isinstance(implement, dict) and implement.get("started_at") and implement.get("completed_at") is None
                and implement.get("round") == round_ and implement.get("triggered_by") == "verify"):
            raise Malformed(f"IMPLEMENT is not open at round {round_} triggered by VERIFY")
        merged = verify.get("merged") if isinstance(verify, dict) else None
        if not (isinstance(merged, dict) and verify.get("completed_at") and verify.get("round") == round_ - 1
                and verify.get("verdict") == merged.get("verdict") == "NEEDS_WORK"):
            raise Malformed(f"VERIFY round {round_ - 1} did not complete NEEDS_WORK with merged findings")
        try:
            raw = (devlyn_dir / "verify-merged.findings.jsonl").read_bytes()
            findings = [SPEC_VERIFY.loads_strict_json(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
        except (OSError, ValueError) as e:
            raise Malformed(f"cannot read .devlyn/verify-merged.findings.jsonl: {e}") from e
        writer = runpy.run_path(str(pathlib.Path(__file__).with_name("state-phase-write.py")))
        plan_error = writer["plan_output_error"](state, devlyn_dir, "implement")
        if plan_error is not None:
            raise Malformed(f"bound PLAN no longer verifies: {plan_error}")
        ownership, sparse_absences, baseline_error = SPEC_VERIFY.load_untracked_baseline(devlyn_dir)
        baseline_error = baseline_error or SPEC_VERIFY.baseline_digest_error(devlyn_dir, state)
        if baseline_error is not None:
            raise Malformed(baseline_error)
        base_sha = ((state.get("base_ref") or {}).get("sha") or "").strip()
        ensure_commit(work, base_sha, "base_ref.sha")
        surface = load_authorized_surface(devlyn_dir)
        exact = frozenset(entry.rstrip("/") for entry in surface)
        candidates = [path for path in checked_paths(work, devlyn_dir, base_sha, ownership, sparse_absences, staged=True)
                      if offends(path, surface, ownership, exact)]
    except Malformed as e:
        emit(f"finish-gate --settle-repair: refused before changing anything: {e}\n{SETTLE_CLOSE}\n")
        return 1
    named = {item["file"] for item in findings if isinstance(item, dict)
             and item.get("rule_id") == "scope.out-of-scope-file" and isinstance(item.get("file"), str)}
    outcomes = []
    for path in candidates:
        settled, action, detail = settle_path(work, base_sha, path, ownership)
        outcomes.append({"path": path, "named_by_finding": path in named, "action": action,
                         "outcome": "settled" if settled else "unsettled", "detail": detail})
    unsettled = [item for item in outcomes if item["outcome"] == "unsettled"]
    (devlyn_dir / f"repair-settle.r{round_}.json").write_text(json.dumps({
        "run_id": state.get("run_id"), "verify_round": verify["round"], "implement_round": round_,
        "merged_findings_sha256": hashlib.sha256(raw).hexdigest(),
        "untracked_baseline_sha256": state["untracked_baseline_sha256"],
        "paths": outcomes, "exit": 2 if unsettled else 0}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if unsettled:
        emit("finish-gate --settle-repair: this repair round cannot be checkpointed:\n"
             + "".join(f"- {item['path']}: {item['detail']}\n" for item in unsettled) + SETTLE_CLOSE + "\n")
        return 2
    sys.stdout.write(f"ok: settled {len(outcomes)} path(s); see .devlyn/repair-settle.r{round_}.json\n")
    return 0


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
    write_text(devlyn / "untracked.baseline", json.dumps({"untracked": [], "ignored": [], "sparse_absences": []}) + "\n")
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
        write_text(devlyn / "untracked.baseline",
                   json.dumps({"untracked": ["keep.txt"], "ignored": [], "sparse_absences": []}) + "\n")
        write_text(work / "stray.txt", "outside the baseline\n")
        assert checked_run_gate(work, devlyn) == 2
        assert (work / "stray.txt").is_file() and (work / "keep.txt").is_file()
        assert [(f["file"], f["status"]) for f in read_findings(devlyn)] == [("stray.txt", "retained")]
        # So are the files an ignore rule hid at PHASE 0 when the run reveals them, a whole ignored directory's
        # descendants included: the inventory covers them.
        work, devlyn, _base = make_fixture(root, "revealed-ignored")
        write_text(devlyn / "untracked.baseline",
                   json.dumps({"untracked": [], "ignored": ["cache/", "config.local"], "sparse_absences": []}) + "\n")
        for name in ("config.local", "cache/old.bin", "cache/later.bin"):
            write_text(work / name, "the user's\n")
        write_text(work / "src" / "app.txt", "changed app\n")
        assert checked_run_gate(work, devlyn) == 0, read_findings(devlyn)

        # A user's pre-run file committed through a glob surface offends; its bytes stay.
        work, devlyn, _base = make_fixture(root, "user-file-swept")
        write_text(devlyn / "plan.md", "# PLAN\n\n<!-- devlyn:authorized-surface -->\n## Files to touch\n\n```json\n"
                                       '{"authorized_surface": ["src/**"]}\n```\n')
        write_text(work / "src" / "user.txt", "the user's\n")
        write_text(devlyn / "untracked.baseline",
                   json.dumps({"untracked": ["src/user.txt"], "ignored": [], "sparse_absences": []}) + "\n")
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
        write_text(devlyn / "untracked.baseline",
                   json.dumps({"untracked": ["src/vendor/"], "ignored": [], "sparse_absences": []}) + "\n")
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
            write_text(devlyn / "untracked.baseline",
                       json.dumps({"untracked": ["src/vendor/"], "ignored": [], "sparse_absences": []}) + "\n")
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
        # object alike, with skip-worktree again so Git shows the sparse absence, and loses only the copy the run
        # materialized.
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
        assert git_check(work, "ls-files", "-v", "--", "docs/spec.expected.json") == "S docs/spec.expected.json"
        assert git_check(work, "status", "--porcelain", "--", "docs") == ""

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
        # Nor is base's file checked out over a directory the run put at its path, the contract's or an offender's:
        # checkout would delete the contents, which keep their own finding.
        bound_contract = contract_fixture("contract-directory-bound", b'{"a": 1}\n', b'{"a": 1}\n')
        for (where, gate_devlyn), path in ((bound_contract, "docs/spec.expected.json"),
                                           (make_fixture(root, "directory-at-base-file")[:2], "notes.txt")):
            (where / path).unlink()
            write_text(where / path / "inner.json", "{}\n")
            assert checked_run_gate(where, gate_devlyn) == 2
            findings = read_findings(gate_devlyn)
            assert [(f["file"], f["status"]) for f in findings] == [
                (path, "revert-failed"), (f"{path}/inner.json", "retained")], findings
            assert "left in place because a directory occupies it; restoring would delete its contents" in findings[0]["message"]
            assert (where / path / "inner.json").read_text(encoding="utf-8") == "{}\n"

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
                   json.dumps({"untracked": ["current", "drafts/spec.expected.json"], "ignored": [],
                               "sparse_absences": []}) + "\n")
        assert checked_run_gate(work, devlyn) == 2
        assert sole_finding(devlyn, "revert-failed", "reported only because its parent directory current is a symlink"
                            )["file"] == "current/spec.expected.json"
        assert (work / "drafts" / "spec.expected.json").read_text(encoding="utf-8") == "the user's draft\n"
        # An entry the PHASE 0 inventory covers, untracked or ignored then, is the user's whatever bootstrap bound:
        # reported, never removed.
        for listed in ("untracked", "ignored"):
            work, devlyn = contract_fixture(f"contract-{listed}-listed", None, None)
            write_text(work / "docs" / "spec.expected.json", "the user's draft\n")
            write_text(devlyn / "untracked.baseline", json.dumps(
                {"untracked": [], "ignored": [], "sparse_absences": [], listed: ["docs/spec.expected.json"]}) + "\n")
            assert checked_run_gate(work, devlyn) == 2
            sole_finding(devlyn, "revert-failed", "reported only because the PHASE 0 inventory covers it as the user's")
            assert (work / "docs" / "spec.expected.json").read_text(encoding="utf-8") == "the user's draft\n"
        # An entry that cannot be inspected is never taken for absence: drift, reported with the error.
        work, devlyn = contract_fixture("contract-uninspectable", None, None, "x" * 300 + "/spec.md")
        assert checked_run_gate(work, devlyn) == 2
        message = sole_finding(devlyn, "revert-failed", "whose absence bootstrap bound:")["message"]
        assert "is inaccessible (" in message and "File name too long" in message, message

        # Identity is the directory entry: a case alias of the spelling is one disposition, while a separate
        # hardlink stays an offender of its own. Names differing only in case are one entry exactly where Git
        # ignores case, on any filesystem.
        (root / "case-rule" / "docs").mkdir(parents=True)
        assert [is_contract(root / "case-rule", "docs/Spec.Expected.json", "docs/spec.expected.json", fold)
                for fold in (False, True)] == [False, True]
        # Settling acts on Git's spelling, which an alias does not share (Git's index and trees and the inventory are
        # case-sensitive): a user's listed entry, a staged worker contract and a contract base holds are reported only.
        work, devlyn = contract_fixture("contract-case-alias", None, None, "Docs/spec.md")
        if not (work / "DOCS").exists():
            print("SKIP case-alias contract fixtures: this filesystem is case-sensitive")
        else:
            write_text(work / "docs" / "Spec.Expected.json", "{}\n")
            assert checked_run_gate(work, devlyn) == 2
            sole_finding(devlyn, "revert-failed", "reported only because its spelling Docs differs in case from the "
                                                  "directory entry docs")
            assert (work / "docs" / "Spec.Expected.json").read_text(encoding="utf-8") == "{}\n"
            for name, committed, bound in (("listed", None, None), ("staged", None, None),
                                           ("base-held", b'{"a": 1}\n', b'{"a": 1}\n')):
                work, devlyn = contract_fixture(f"contract-case-alias-{name}", committed, bound, "Docs/spec.md")
                contract = work / "docs" / "spec.expected.json"
                if name == "listed":
                    (work / "userdir").mkdir()
                    contract.symlink_to("../userdir")
                    write_text(devlyn / "untracked.baseline", json.dumps(
                        {"untracked": ["docs/spec.expected.json"], "ignored": [], "sparse_absences": []}) + "\n")
                else:
                    contract.write_bytes(b'{"a": 2}\n')
                if name == "staged":
                    git_check(work, "add", "docs/spec.expected.json")
                before = (git_check(work, "ls-files", "-s"), os.readlink(contract) if contract.is_symlink()
                          else contract.read_bytes())
                assert checked_run_gate(work, devlyn) == 2, name
                sole_finding(devlyn, "revert-failed", "reported only because its spelling Docs differs in case")
                assert (git_check(work, "ls-files", "-s"), os.readlink(contract) if contract.is_symlink()
                        else contract.read_bytes()) == before, name
            # With the parent directory gone, Git's path spelled the same but for case is still the contract's.
            work, devlyn = contract_fixture("contract-case-alias-missing-parent", b'{"a": 1}\n', b'{"a": 1}\n', "Docs/spec.md")
            shutil.rmtree(work / "docs")
            assert checked_run_gate(work, devlyn) == 2
            assert [(f["rule_id"], f["file"], f["status"]) for f in read_findings(devlyn)] == [
                ("scope.finish-contract-drift", "Docs/spec.expected.json", "revert-failed"),
                ("scope.finish-unaudited-file", "docs/spec.md", "reverted")], read_findings(devlyn)
        work, devlyn = contract_fixture("contract-hardlink", None, None)
        write_text(work / "docs" / "spec.expected.json", "{}\n")
        os.link(work / "docs" / "spec.expected.json", work / "docs" / "linked.json")
        assert checked_run_gate(work, devlyn) == 2
        assert [(f["file"], f["status"]) for f in read_findings(devlyn)] == [
            ("docs/spec.expected.json", "reverted"), ("docs/linked.json", "retained")]
        assert (work / "docs" / "linked.json").read_text(encoding="utf-8") == "{}\n"

        # A missing leaf is still the contract's entry (one disposition), and so is Git's path spelled the same with
        # its parent directory missing too.
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

        # Nor does a forged commit-graph (as binding_self_test forges one): with base's root tree forged to the run's, a
        # graph-trusting diff sees no change, yet the gate finds the out-of-surface edit and restores genuine bytes.
        def forge_graph(work: pathlib.Path, commit: str, tree: str) -> None:
            """Overwrite `commit`'s root-tree OID in a freshly written commit-graph."""
            git_check(work, "-c", "core.commitGraph=true", "commit-graph", "write", "--reachable")
            graph = work / ".git" / "objects" / "info" / "commit-graph"
            data = bytearray(graph.read_bytes())
            chunks = {bytes(data[8 + 12 * i:12 + 12 * i]): int.from_bytes(data[12 + 12 * i:20 + 12 * i], "big")
                      for i in range(data[6])}
            count = int.from_bytes(data[chunks[b"OIDF"] + 1020:chunks[b"OIDF"] + 1024], "big")
            oids = [bytes(data[chunks[b"OIDL"] + 20 * i:chunks[b"OIDL"] + 20 * i + 20]) for i in range(count)]
            at = chunks[b"CDAT"] + 36 * oids.index(bytes.fromhex(commit))
            data[at:at + 20] = bytes.fromhex(tree)
            graph.chmod(0o644)
            graph.write_bytes(data)

        work, devlyn, base = make_fixture(root, "forged-commit-graph")
        write_text(work / "notes.txt", "the run's\n")
        git_check(work, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-am", "worker")
        forge_graph(work, base, git_check(work, "rev-parse", "HEAD^{tree}"))
        assert git_check(work, "-c", "core.commitGraph=true", "diff", "--name-only", base) == ""
        assert checked_run_gate(work, devlyn) == 2
        assert (work / "notes.txt").read_text(encoding="utf-8") == "base notes\n"

        # --settle-repair, the post-fix checkpoint's settlement of what a VERIFY repair round left outside the surface.
        def open_repair(devlyn: pathlib.Path, base: str, named: tuple[str, ...] = ()) -> None:
            """IMPLEMENT round 1 open after VERIFY round 0 closed NEEDS_WORK, its merged scope findings naming `named`,
            with the PHASE 0 baseline as it stands now bound."""
            write_text(devlyn / "verify-merged.findings.jsonl", "".join(
                json.dumps({"rule_id": "scope.out-of-scope-file", "file": path}) + "\n" for path in named))
            write_state(devlyn, {
                "run_id": "rs-settle", "mode": "full", "base_ref": {"sha": base},
                "untracked_baseline_sha256": hashlib.sha256((devlyn / "untracked.baseline").read_bytes()).hexdigest(),
                "phases": {"plan": {"started_at": "t", "completed_at": "t", "verdict": "PASS"},
                           "verify": {"started_at": "t", "completed_at": "t", "round": 0, "verdict": "NEEDS_WORK",
                                      "merged": {"verdict": "NEEDS_WORK"}},
                           "implement": {"started_at": "t", "completed_at": None, "round": 1, "triggered_by": "verify"}}})

        def settle(work: pathlib.Path, devlyn: pathlib.Path, round_: int = 1) -> tuple[int, str, dict | None]:
            captured = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
            with contextlib.redirect_stderr(captured), contextlib.redirect_stdout(io.StringIO()):
                rc = run_settle(work, devlyn, round_)
            record = devlyn / f"repair-settle.r{round_}.json"
            return rc, captured.buffer.getvalue().decode("utf-8", "surrogateescape"), (
                SPEC_VERIFY.loads_strict_json(record.read_text(encoding="utf-8")) if record.exists() else None)

        def outcomes(record: dict) -> list[tuple]:
            return [(item["path"], item["named_by_finding"], item["action"], item["outcome"]) for item in record["paths"]]

        def commit(work: pathlib.Path, message: str) -> str:
            git_check(work, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", message)
            return git_check(work, "rev-parse", "HEAD")

        # Every current offender is settled, the merged scope findings only recording which they named: a base file
        # gets base's bytes back, committed or not; a path the PHASE 0 inventory covers keeps its bytes and loses only
        # its unauthorized index entry; one it does not cover is the run's and goes after a non-forced index removal,
        # committed or untracked, named or created later by a command. Covered untracked files and the surface stay.
        work, devlyn, base = make_fixture(root, "settle-paths")
        write_text(devlyn / "untracked.baseline", json.dumps(
            {"untracked": ["keep.txt"], "ignored": ["cache/", "config.local"], "sparse_absences": []}) + "\n")
        for name in ("keep.txt", "config.local", "cache/old.bin"):
            write_text(work / name, "the user's\n")
        write_text(work / "cleanable.txt", "committed by the run\n")
        write_text(work / "committed.txt", "created and committed by the run\n")
        git_check(work, "add", "cleanable.txt", "committed.txt")
        commit(work, "chore(pipeline): implement")
        git_check(work, "add", "config.local")
        for name, text in (("src/app.txt", "changed app\n"), ("notes.txt", "the run's\n"), ("scratch.txt", "the run's\n"),
                           ("coverage.out", "written by a verification command\n")):
            write_text(work / name, text)
        open_repair(devlyn, base, ("cleanable.txt", "committed.txt", "config.local", "notes.txt", "scratch.txt"))
        rc, message, record = settle(work, devlyn)
        assert rc == 0 and message == "", message
        assert outcomes(record) == [
            ("cleanable.txt", True, "restored", "settled"), ("committed.txt", True, "deleted", "settled"),
            ("config.local", True, "kept", "settled"), ("coverage.out", False, "deleted", "settled"),
            ("notes.txt", True, "restored", "settled"), ("scratch.txt", True, "deleted", "settled")], record
        assert {key: record[key] for key in ("run_id", "verify_round", "implement_round", "exit")} == {
            "run_id": "rs-settle", "verify_round": 0, "implement_round": 1, "exit": 0}
        assert [record["merged_findings_sha256"], record["untracked_baseline_sha256"]] == [
            hashlib.sha256((devlyn / name).read_bytes()).hexdigest()
            for name in ("verify-merged.findings.jsonl", "untracked.baseline")]
        assert git_check(work, "ls-files").splitlines() == ["cleanable.txt", "notes.txt", "src/app.txt"]
        for name, text in (("cleanable.txt", "base cleanable\n"), ("notes.txt", "base notes\n"),
                           ("src/app.txt", "changed app\n"), ("keep.txt", "the user's\n"), ("config.local", "the user's\n"),
                           ("cache/old.bin", "the user's\n")):
            assert (work / name).read_text(encoding="utf-8") == text, name
        assert not any(os.path.lexists(work / name) for name in ("committed.txt", "scratch.txt", "coverage.out"))
        assert not (devlyn / FINDINGS_NAME).exists() and not (devlyn / SUMMARY_NAME).exists()

        # Every binding is checked before any change; a refusal changes and records nothing. A tampered, missing or
        # legacy inventory never licenses a deletion (here the tampered one drops the user's keep.txt), nor does another
        # round, an unready VERIFY, missing merged findings or a changed PLAN.
        for case, reason in (("round", "IMPLEMENT is not open at round 2 triggered by VERIFY"),
                             ("verify", "VERIFY round 0 did not complete NEEDS_WORK with merged findings"),
                             ("merged", "cannot read .devlyn/verify-merged.findings.jsonl"),
                             ("plan", "bound PLAN no longer verifies: BLOCKED:plan-integrity-mismatch"),
                             ("tampered", ".devlyn/untracked.baseline differs from its bound digest"),
                             ("missing", "requires .devlyn/untracked.baseline from PHASE 0; the file is missing"),
                             ("legacy", "lacks the PHASE 0 ignored inventory; restart from PHASE 0")):
            work, devlyn, base = make_fixture(root, f"settle-refused-{case}")
            write_text(devlyn / "untracked.baseline",
                       json.dumps({"untracked": ["keep.txt"], "ignored": [], "sparse_absences": []}) + "\n")
            for name in ("keep.txt", "stray.txt", "notes.txt"):
                write_text(work / name, "before settling\n")
            open_repair(devlyn, base, ("stray.txt", "notes.txt"))
            state = read_state(devlyn / "pipeline.state.json")
            if case == "verify":
                state["phases"]["verify"]["merged"]["verdict"] = "PASS"
            elif case == "merged":
                (devlyn / "verify-merged.findings.jsonl").unlink()
            elif case == "plan":
                state["version"] = "3.0"
                state["phases"]["plan"]["output_sha256"] = hashlib.sha256((devlyn / "plan.md").read_bytes()).hexdigest()
                write_text(devlyn / "plan.md", (devlyn / "plan.md").read_text(encoding="utf-8").replace(
                    '["src/app.txt"]', '["src/app.txt", "notes.txt"]'))
            elif case == "tampered":
                write_text(devlyn / "untracked.baseline", SPEC_VERIFY.EMPTY_BASELINE)
            elif case == "missing":
                (devlyn / "untracked.baseline").unlink()
            elif case == "legacy":
                write_text(devlyn / "untracked.baseline", '{"untracked": ["keep.txt"], "sparse_absences": []}\n')
                state["untracked_baseline_sha256"] = hashlib.sha256((devlyn / "untracked.baseline").read_bytes()).hexdigest()
            write_state(devlyn, state)

            def tree() -> tuple[str, str]:
                return git_check(work, "ls-files", "-s"), git_check(work, "status", "--porcelain", "--untracked-files=all")

            before = tree()
            rc, message, record = settle(work, devlyn, 2 if case == "round" else 1)
            assert rc == 1 and record is None and message.startswith(
                "finish-gate --settle-repair: refused before changing anything: ") and message.endswith(
                f"\n{SETTLE_CLOSE}\n") and reason in message, (case, message)
            assert tree() == before, case
            assert all((work / name).read_text(encoding="utf-8") == "before settling\n"
                       for name in ("keep.txt", "stray.txt", "notes.txt")), case

        # A directory goes whole only when nothing in it is covered: a run-created nested repository is deleted, while
        # one made over the user's file (PHASE 0 listed cache/keep.txt; Git now reports cache/ whole) is kept.
        work, devlyn, base = make_fixture(root, "settle-ancestor")
        write_text(devlyn / "untracked.baseline",
                   json.dumps({"untracked": ["cache/keep.txt"], "ignored": [], "sparse_absences": []}) + "\n")
        write_text(work / "cache" / "keep.txt", "the user's\n")
        for name in ("cache", "vendor"):
            write_text(work / name / "made.txt", "the run's\n")
            git_check(work / name, "init", "-q")
        open_repair(devlyn, base)
        rc, message, record = settle(work, devlyn)
        assert rc == 2 and outcomes(record) == [("cache/", False, "kept", "unsettled"),
                                                ("vendor/", False, "deleted", "settled")], record
        assert ("- cache/: no index entry remains, but it was kept whole because cache/keep.txt inside it is the user's\n"
                in message and message.endswith(SETTLE_CLOSE + "\n")), message
        assert (work / "cache" / "keep.txt").read_text(encoding="utf-8") == "the user's\n"
        assert (work / "cache" / ".git").is_dir() and not os.path.lexists(work / "vendor")
        # Nor does one go with a part the walk cannot read, whatever that part holds.
        if os.geteuid() == 0:
            print("SKIP unreadable-directory settlement fixture: permissions do not bind root")
        else:
            work, devlyn, base = make_fixture(root, "settle-unreadable")
            write_text(work / "vendor" / "locked" / "inner.txt", "unknown\n")
            write_text(work / "vendor" / "made.txt", "the run's\n")
            git_check(work / "vendor", "init", "-q")
            open_repair(devlyn, base)
            (work / "vendor" / "locked").chmod(0)
            try:
                rc, message, record = settle(work, devlyn)
            finally:
                (work / "vendor" / "locked").chmod(0o755)
            assert rc == 2 and outcomes(record) == [("vendor/", False, "kept", "unsettled")], record
            assert "kept whole because part of it cannot be read ([Errno 13]" in record["paths"][0]["detail"], record
            assert (work / "vendor" / "made.txt").is_file() and (work / "vendor" / "locked" / "inner.txt").is_file()

        # Nothing is acted on that is not one provable entry: a tree base holds is never restored whole (looked up as the
        # entry itself when Git lists it as a nested repository, pkg/), nothing is restored through a symlinked parent,
        # and base's file is never checked out over a directory the run made.
        work, devlyn, base = make_fixture(root, "settle-refusals")
        write_text(work / "lib" / "a.txt", "base lib\n")
        write_text(work / "pkg" / "x.txt", "base pkg\n")
        git_check(work, "add", "lib", "pkg")
        base = commit(work, "lib and pkg")
        elsewhere = root / "settle-refusals-elsewhere"
        write_text(elsewhere / "a.txt", "outside the repository\n")
        shutil.rmtree(work / "lib")
        (work / "lib").symlink_to(elsewhere)
        (work / "notes.txt").unlink()
        write_text(work / "notes.txt" / "inner.txt", "the run's\n")
        git_check(work / "pkg", "init", "-q")
        git_check(work, "rm", "-q", "--cached", "pkg/x.txt")
        open_repair(devlyn, base)
        rc, message, record = settle(work, devlyn)
        tree_refused = "left in place because base_ref.sha holds a tree (040000) there, never restored whole"
        assert rc == 2 and [(item["path"], item["action"], item["outcome"], item["detail"]) for item in record["paths"]] == [
            ("lib", "none", "unsettled", tree_refused),
            ("lib/a.txt", "none", "unsettled", "left in place because its parent directory lib is a symlink"),
            ("notes.txt", "none", "unsettled",
             "left in place because a directory occupies it; restoring would delete its contents"),
            ("notes.txt/inner.txt", "deleted", "settled",
             "deleted: the PHASE 0 inventory does not cover it, so this run created it"),
            ("pkg/", "none", "unsettled", tree_refused),
            ("pkg/x.txt", "restored", "settled", "restored to base_ref.sha")], record
        assert os.readlink(work / "lib") == str(elsewhere) and (work / "notes.txt").is_dir()
        assert (elsewhere / "a.txt").read_text(encoding="utf-8") == "outside the repository\n"
        assert (work / "pkg" / ".git").is_dir() and (work / "pkg" / "x.txt").read_text(encoding="utf-8") == "base pkg\n"

        # Restore, index-removal and deletion failures are recorded apart, each with what did happen: a deletion that
        # fails after its index entry went says so, and success is only what the tree shows afterwards.
        if os.geteuid() == 0:
            print("SKIP failing-settlement fixture: permissions do not bind root")
        else:
            work, devlyn, base = make_fixture(root, "settle-failures")
            write_text(work / "ro" / "base.txt", "base ro\n")
            git_check(work, "add", "ro")
            base = commit(work, "ro")
            write_text(work / "ro" / "committed.txt", "the run's\n")
            git_check(work, "add", "ro/committed.txt")
            commit(work, "chore(pipeline): implement")
            write_text(work / "ro" / "base.txt", "the run's\n")
            write_text(work / "edited.txt", "v1\n")
            git_check(work, "add", "edited.txt")
            write_text(work / "edited.txt", "v2\n")
            open_repair(devlyn, base)
            (work / "ro").chmod(0o555)
            try:
                rc, message, record = settle(work, devlyn)
            finally:
                (work / "ro").chmod(0o755)
            assert rc == 2 and [(item["path"], item["action"], item["outcome"]) for item in record["paths"]] == [
                ("edited.txt", "unstage-failed", "unsettled"), ("ro/base.txt", "restore-failed", "unsettled"),
                ("ro/committed.txt", "delete-failed", "unsettled")], record
            details = [item["detail"] for item in record["paths"]]
            assert details[0].startswith("left in place because removing its index entry failed (error: the following "
                                         "file has staged content"), details
            assert details[1].startswith("left in place because restoring it failed (error: unable to unlink old "), details
            assert details[2].startswith("no index entry remains, but deleting it failed ([Errno 13]"), details
            assert git_check(work, "ls-files", "edited.txt", "ro").splitlines() == ["edited.txt", "ro/base.txt"]
            for name, text in (("edited.txt", "v2\n"), ("ro/base.txt", "the run's\n"), ("ro/committed.txt", "the run's\n")):
                assert (work / name).read_text(encoding="utf-8") == text, name

        # A gitlink gets back base's pointer in the index only, read back exactly. devlyn never moves or fetches a
        # nested checkout, so a moved one is unsettled, named with both commits, and stays exactly as it was (HEAD,
        # refs, index flags, configuration and bytes: flag-hidden edits, ignored files, an untracked file where base's
        # commit tracks one), staged, unstaged or committed, whatever submodule.recurse says. The superproject never
        # holds the child's commits, which is no failed lookup.
        def repair_submodule(name: str, bump: str) -> tuple[pathlib.Path, pathlib.Path, pathlib.Path, str]:
            work, devlyn, sub, pointer = bumped_submodule(name, bump)
            open_repair(devlyn, read_state(devlyn / "pipeline.state.json")["base_ref"]["sha"], ("sub",))
            return work, devlyn, sub, pointer

        def child_state(work: pathlib.Path, sub: pathlib.Path) -> tuple:
            config = pathlib.Path(git_check(sub, "rev-parse", "--path-format=absolute", "--git-path", "config"))
            return (git_check(sub, "rev-parse", "HEAD"), git_check(sub, "for-each-ref"), git_check(sub, "ls-files", "-v"),
                    config.read_bytes(), (work / ".gitmodules").read_bytes(), git_check(work, "config", "--list", "--local"),
                    {path.relative_to(sub).as_posix(): path.read_bytes() for path in sorted(sub.rglob("*"))
                     if path.is_file() and ".git" not in path.relative_to(sub).parts})

        for bump in ("staged", "unstaged", "committed"):
            work, devlyn, sub, pointer = repair_submodule(f"settle-sub-{bump}", bump)
            git_check(work, "config", "submodule.recurse", "true")
            if bump == "committed":
                write_text(sub / "kept.txt", "tracked by the child's own commit\n")
                git_check(sub, "add", "kept.txt")
                git_check(sub, "rm", "-q", "lib.txt")
                commit(sub, "drops lib.txt")
                write_text(sub / "lib.txt", "untracked where base's commit tracks lib.txt\n")
                write_text(sub / "kept.txt", "a flag-hidden edit\n")
                git_check(sub, "update-index", "--assume-unchanged", "kept.txt")
                write_text(pathlib.Path(git_check(sub, "rev-parse", "--path-format=absolute", "--git-path", "info/exclude")),
                           "*.log\n")
                write_text(sub / "build.log", "ignored by the child\n")
            assert git(work, "cat-file", "-e", pointer).returncode != 0
            moved, before = git_check(sub, "rev-parse", "HEAD"), child_state(work, sub)
            rc, message, record = settle(work, devlyn)
            assert rc == 2 and outcomes(record) == [("sub", True, "pointer-restored", "unsettled")], record
            assert record["paths"][0]["detail"] == (f"base_ref.sha's pointer {pointer} was restored in the index only, but "
                                                    f"the nested checkout sub is at {moved}; devlyn does not move nested "
                                                    "checkouts"), record
            assert git_check(work, "ls-files", "-s", "--", "sub").split()[:3] == ["160000", pointer, "0"]
            assert child_state(work, sub) == before, bump

        # At base's commit, the checkout still settles only when nothing is visible beyond it: its residue is named.
        work, devlyn, sub, pointer = repair_submodule("settle-sub-residue", "staged")
        git_check(sub, "checkout", "-q", pointer)
        rc, message, record = settle(work, devlyn)
        assert rc == 2 and record["paths"][0]["detail"] == (
            f"base_ref.sha's pointer {pointer} was restored in the index only, but the nested checkout sub at that commit "
            "holds content the commit lacks: sub/scratch.txt"), record
        assert (sub / "scratch.txt").read_text(encoding="utf-8") == "the child's untracked bytes\n"
        # A path that is no longer a directory is no checkout, and is left as it is.
        work, devlyn, sub, pointer = repair_submodule("settle-sub-kind", "staged")
        sub.rename(root / "settle-sub-kind-away")
        write_text(sub, "a file where the checkout was\n")
        rc, message, record = settle(work, devlyn)
        assert rc == 2 and record["paths"][0]["detail"] == (
            f"base_ref.sha's pointer {pointer} was restored in the index only, but the nested checkout sub is no longer "
            "a directory"), record
        assert sub.read_text(encoding="utf-8") == "a file where the checkout was\n"
        # A failed lookup and a failed readback are outcomes of their own, never absence or a restored pointer.
        real_git = git
        for failure, expected in (
                ("lookup", ("none", "left in place because looking it up at base_ref.sha failed (fatal: simulated failure)")),
                ("readback", ("pointer-unverified", "reading back its index entry did not show base_ref.sha's pointer "
                                                    "{pointer} (fatal: simulated failure)"))):
            work, devlyn, sub, pointer = repair_submodule(f"settle-sub-{failure}-failure", "staged")
            before = child_state(work, sub)

            def failing(where: pathlib.Path, *args: str, **kwargs) -> subprocess.CompletedProcess:
                if args[:2] == {"lookup": ("ls-tree", "-z"), "readback": ("ls-files", "-s")}[failure] and args[-1] == "sub":
                    return subprocess.CompletedProcess(args, 128, "", "fatal: simulated failure\n")
                return real_git(where, *args, **kwargs)

            globals()["git"] = failing
            try:
                rc, message, record = settle(work, devlyn)
            finally:
                globals()["git"] = real_git
            assert rc == 2 and [(item["action"], item["detail"]) for item in record["paths"]] == [
                (expected[0], expected[1].format(pointer=pointer))], record
            assert child_state(work, sub) == before and (sub / ".git").exists()
        # A name that is not UTF-8 is reported as Git holds it (APFS cannot hold one, so the listing carries it).
        work, devlyn, base = make_fixture(root, "settle-non-utf8")
        odd = os.fsdecode(b"caf\xe9.txt")
        open_repair(devlyn, base)
        listed = SPEC_VERIFY.current_untracked_files

        def odd_lookup_fails(where: pathlib.Path, *args: str, **kwargs) -> subprocess.CompletedProcess:
            if args[:2] == ("ls-tree", "-z") and args[-1] == odd:
                return subprocess.CompletedProcess(args, 128, "", "fatal: simulated failure\n")
            return real_git(where, *args, **kwargs)

        SPEC_VERIFY.current_untracked_files = lambda *args: (listed(*args)[0] | {odd}, None)
        globals()["git"] = odd_lookup_fails
        try:
            rc, message, record = settle(work, devlyn)
        finally:
            SPEC_VERIFY.current_untracked_files, globals()["git"] = listed, real_git
        assert rc == 2 and outcomes(record) == [(odd, False, "none", "unsettled")], record
        assert f"- {odd}: left in place because looking it up at base_ref.sha failed" in message, message

        # Undone in the worktree only (the child back at base's commit and clean, a committed edit reverted, a committed
        # run file deleted), the index still holds what the checkpoint would commit, so it settles too: the documented
        # checkpoint then commits base's state, and durability-enforce, whose status here sees submodule changes, accepts it.
        work, devlyn, sub, pointer = repair_submodule("settle-sub-repaired", "committed")
        base = read_state(devlyn / "pipeline.state.json")["base_ref"]["sha"]
        write_text(work / "notes.txt", "the run's\n")
        write_text(work / "made.txt", "the run's\n")
        git_check(work, "add", "notes.txt", "made.txt")
        commit(work, "chore(pipeline): implement")
        write_text(work / "notes.txt", "base notes\n")
        (work / "made.txt").unlink()
        git_check(work, "config", "submodule.sub.ignore", "none")
        (sub / "scratch.txt").unlink()
        git_check(sub, "checkout", "-q", pointer)
        rc, message, record = settle(work, devlyn)
        assert rc == 0 and outcomes(record) == [
            ("made.txt", False, "deleted", "settled"), ("notes.txt", False, "restored", "settled"),
            ("sub", True, "pointer-restored", "settled")], (message, record)
        shared = pathlib.Path(__file__).resolve().parent
        env = {**{key: value for key, value in os.environ.items()
                  if not key.startswith("DEVLYN_INVOCATION_") and key != "BENCH_WORKDIR"},
               "DEVLYN_SHARED_DIR": str(shared), "PYTHONDONTWRITEBYTECODE": "1"}
        env.update({f"GIT_{role}_{field}": value for role in ("AUTHOR", "COMMITTER")
                    for field, value in (("NAME", "t"), ("EMAIL", "t@t"))})
        checkpoint = subprocess.run(["bash", "-c", "bash -o pipefail -c 'python3 \"$DEVLYN_SHARED_DIR/spec-verify-check.py\" "
                                     "--print-authorized-surface | git --literal-pathspecs add --pathspec-from-file=- "
                                     "--pathspec-file-nul' && git commit -q --allow-empty -m \"chore(pipeline): implement fix "
                                     "round 1\""], cwd=work, env=env, capture_output=True, text=True)
        assert checkpoint.returncode == 0, checkpoint.stderr

        def cli(work: pathlib.Path, script: str, *args: str) -> subprocess.CompletedProcess:
            return subprocess.run([sys.executable, str(shared / script), *args], cwd=work, env=env, capture_output=True,
                                  text=True)

        enforced = cli(work, "state-phase-write.py", "--devlyn-dir", ".devlyn", "--phase", "implement",
                       "durability-enforce", "--round", "1")
        assert enforced.returncode == 0 and enforced.stdout == "ok: phases.implement.durability.round-1\n", enforced.stderr
        assert git_check(work, "rev-parse", "HEAD^{tree}") == git_check(work, "rev-parse", f"{base}^{{tree}}")

        # A refusal closes the run without a checkpoint or a contradiction: IMPLEMENT completes exactly BLOCKED, and
        # FINAL_REPORT, the finish gate first, derives the verdict (the gitlink the moved child leaves behind offends;
        # only a clean gate, here over an uninitialized child, takes BLOCKED:repair-unsettled); archive and
        # terminal-claim-check then witness a complete run.
        for name, verdict in (("settle-close-offender", "BLOCKED:finish-gate-unclean"),
                              ("settle-close-uninitialized", "BLOCKED:repair-unsettled")):
            uninitialized = verdict == "BLOCKED:repair-unsettled"
            work, devlyn, sub, pointer = bumped_submodule(name, "staged" if uninitialized else "committed")
            plan = (devlyn / "plan.md").read_bytes()
            (devlyn / "plan.md").unlink()
            write_state(devlyn, {"version": "3.0", "run_id": f"rs-{name}", "engine": "claude", "mode": "spec",
                                 "base_ref": read_state(devlyn / "pipeline.state.json")["base_ref"],
                                 "untracked_baseline_sha256": None, "rounds": {"global": 0, "max_rounds": 4}, "phases": {}})

            def phase(*args: str, error: str = "") -> None:
                proc = cli(work, "state-phase-write.py", "--devlyn-dir", ".devlyn", "--phase", *args)
                assert proc.returncode == (1 if error else 0) and error in proc.stderr, proc.stderr

            phase("plan", "spawn", "--round", "0")
            (devlyn / "plan.md").write_bytes(plan)
            phase("plan", "complete", "--verdict", "PASS")
            phase("implement", "spawn", "--round", "0", "--engine", "claude")
            phase("implement", "transition", "--verdict", "PASS", "--next-phase", "verify", "--next-round", "0",
                  "--next-engine", "claude")
            write_text(devlyn / "verify-merged.findings.jsonl",
                       json.dumps({"rule_id": "scope.out-of-scope-file", "file": "sub"}) + "\n")
            state = read_state(devlyn / "pipeline.state.json")
            state["phases"]["verify"].update(verdict="NEEDS_WORK", merged={
                "verdict": "NEEDS_WORK", "findings_file": ".devlyn/verify-merged.findings.jsonl"})
            write_state(devlyn, state)
            phase("verify", "complete")
            phase("implement", "spawn", "--round", "1", "--triggered-by", "verify", "--engine", "claude")
            if uninitialized:
                git_check(work, "submodule", "deinit", "-q", "-f", "sub")
            settled = cli(work, "finish-gate.py", "--devlyn-dir", ".devlyn", "--settle-repair", "--round", "1")
            record = SPEC_VERIFY.loads_strict_json((devlyn / "repair-settle.r1.json").read_text(encoding="utf-8"))
            detail = record["paths"][0]["detail"]
            assert settled.returncode == 2 and settled.stderr == (
                f"finish-gate --settle-repair: this repair round cannot be checkpointed:\n- sub: {detail}\n{SETTLE_CLOSE}\n"
            ), settled.stderr
            assert detail.endswith("is not initialized (it has no .git), so its commit is unknown" if uninitialized
                                   else "devlyn does not move nested checkouts"), detail
            phase("implement", "complete", "--verdict", "BLOCKED")
            phase("final_report", "spawn", "--round", "0")
            assert cli(work, "finish-gate.py").returncode == (0 if uninitialized else 2)
            if not uninitialized:
                phase("final_report", "complete", "--verdict", "BLOCKED:repair-unsettled", error="contradicts")
            phase("final_report", "complete", *(("--verdict", verdict) if uninitialized else ()))
            assert read_state(devlyn / "pipeline.state.json")["phases"]["final_report"]["verdict"] == verdict
            assert cli(work, "archive_run.py", "--devlyn-dir", ".devlyn").returncode == 0
            claimed = cli(work, "terminal-claim-check.py")
            assert claimed.returncode == 0, claimed.stdout + claimed.stderr

    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--devlyn-dir", default=".devlyn")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--settle-repair", action="store_true")
    ap.add_argument("--round", type=int)
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if args.settle_repair and args.round is None:
        ap.error("--settle-repair requires --round <the repair IMPLEMENT round>")
    devlyn_dir = pathlib.Path(args.devlyn_dir)
    if not devlyn_dir.is_absolute():
        devlyn_dir = (pathlib.Path.cwd() / devlyn_dir).resolve()
    if args.settle_repair:
        return run_settle(devlyn_dir.parent, devlyn_dir, args.round)
    return run_gate(devlyn_dir.parent, devlyn_dir)


if __name__ == "__main__":
    runpy.run_path(str(pathlib.Path(__file__).with_name("platform-support.py")))["configure_utf8"]()
    raise SystemExit(main())
