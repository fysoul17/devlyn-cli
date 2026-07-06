#!/usr/bin/env python3
"""Deterministic PHASE 6 final-diff gate for /devlyn:resolve."""
from __future__ import annotations

import argparse
import importlib.util
import json
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
    return subprocess.run(
        ["git", *args],
        cwd=str(work),
        capture_output=True,
        text=True,
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


def cleanup_window(work: pathlib.Path, state: dict) -> set[str]:
    if "cleanup" in (state.get("bypasses") or []):
        return set()
    phases = state.get("phases") or {}
    cleanup = phases.get("cleanup") if isinstance(phases, dict) else None
    if cleanup is None:
        return set()
    if not isinstance(cleanup, dict):
        raise Malformed("phases.cleanup must be an object or null")
    if cleanup.get("verdict") is None:
        return set()
    pre_sha = (cleanup.get("pre_sha") or "").strip()
    post_sha = (cleanup.get("post_sha") or "").strip()
    if not pre_sha or not post_sha:
        raise Malformed("phases.cleanup with a verdict must include both pre_sha and post_sha")
    ensure_commit(work, pre_sha, "phases.cleanup.pre_sha")
    ensure_commit(work, post_sha, "phases.cleanup.post_sha")
    proc = git(work, "diff", "--name-only", pre_sha, post_sha)
    if proc.returncode != 0:
        raise Malformed(f"cannot compute cleanup window: {proc.stderr.strip()}")
    return {line.strip() for line in proc.stdout.splitlines() if line.strip()}


def changed_files(work: pathlib.Path, base_sha: str) -> set[str]:
    proc = git(work, "diff", "--name-only", base_sha, "--")
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or "git diff --name-only failed"
        raise Malformed(f"cannot compute finish-gate changed files: {detail}")
    return {line.strip() for line in proc.stdout.splitlines() if line.strip()}


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


def revert_offender(work: pathlib.Path, base_sha: str, path: str) -> tuple[bool, str | None, bool]:
    existed_at_base = path_exists_at_base(work, base_sha, path)
    if existed_at_base:
        proc = git(work, "checkout", base_sha, "--", path)
        if proc.returncode != 0:
            return (False, proc.stderr.strip() or proc.stdout.strip(), True)
        return (True, None, True)

    proc = git(work, "rm", "-f", "--ignore-unmatch", "--", path)
    target = work / path
    try:
        if target.exists() or target.is_symlink():
            remove_worktree_path(target)
    except OSError as e:
        return (False, str(e), False)
    if proc.returncode != 0:
        cached = git(work, "rm", "-f", "--cached", "--ignore-unmatch", "--", path)
        if cached.returncode != 0:
            detail = proc.stderr.strip() or cached.stderr.strip() or proc.stdout.strip()
            return (False, detail, False)
    return (True, None, False)


def run_gate(work: pathlib.Path, devlyn_dir: pathlib.Path) -> int:
    state_path = devlyn_dir / "pipeline.state.json"
    findings_path = devlyn_dir / FINDINGS_NAME
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
        surface = load_authorized_surface(devlyn_dir)
        cleanup_paths = cleanup_window(work, state)
        changed = changed_files(work, base_sha)
        devlyn_prefix = devlyn_relative_prefix(work, devlyn_dir)
        checked = sorted(path for path in changed if not is_under_prefix(path, devlyn_prefix))
    except Malformed as e:
        findings_path.unlink(missing_ok=True)
        write_findings(devlyn_dir, [malformed_finding(e)])
        write_summary(devlyn_dir, {"exit": 1, "malformed": str(e)})
        return 1

    offenders = sorted(
        path for path in checked
        if (
            not SPEC_VERIFY.path_matches_surface(path, surface)
            and path not in cleanup_paths
        )
    )
    if not offenders:
        findings_path.unlink(missing_ok=True)
        write_summary(devlyn_dir, {
            "mode": state.get("mode"),
            "checked": len(checked),
            "offenders": 0,
            "exit": 0,
        })
        return 0

    findings: list[dict] = []
    failed = False
    reverted = 0
    revert_failed = 0
    for seq, path in enumerate(offenders, start=1):
        ok, detail, existed_at_base = revert_offender(work, base_sha, path)
        status = "reverted" if ok else "revert-failed"
        failed = failed or not ok
        if ok:
            reverted += 1
        else:
            revert_failed += 1
        action = "restored to base_ref.sha" if existed_at_base else "removed because it did not exist at base_ref.sha"
        message = f"Final diff touched an unaudited file outside authorized_surface and cleanup window: {path}"
        if detail:
            message = f"{message} ({detail})"
        findings.append(make_finding(
            seq,
            "scope.finish-unaudited-file",
            message,
            path,
            status=status,
            criterion_ref="plan.md/authorized_surface",
            fix_hint=(
                "This file was outside authorized_surface plus the cleanup window "
                f"and was {action}; do not ship unlicensed final-diff changes."
            ),
        ))
    write_findings(devlyn_dir, findings)
    exit_code = 2 if failed else 0
    write_summary(devlyn_dir, {
        "mode": state.get("mode"),
        "checked": len(checked),
        "offenders": len(offenders),
        "reverted": reverted,
        "revert_failed": revert_failed,
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
    return [SPEC_VERIFY.loads_strict_json(line) for line in path.read_text().splitlines() if line.strip()]


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
        "phases": {"cleanup": None},
    })
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
        assert checked_run_gate(work, devlyn) == 0
        assert (work / "notes.txt").read_text(encoding="utf-8") == "base notes\n"
        findings = read_findings(devlyn)
        assert findings[0]["rule_id"] == "scope.finish-unaudited-file"
        assert findings[0]["status"] == "reverted"
        assert_summary(devlyn, {
            "mode": "full", "checked": 1, "offenders": 1,
            "reverted": 1, "revert_failed": 0, "exit": 0,
        })

        work, devlyn, _base = make_fixture(root, "added-file")
        write_text(work / "runtime.txt", "late\n")
        git_check(work, "add", "runtime.txt")
        assert checked_run_gate(work, devlyn) == 0
        assert not (work / "runtime.txt").exists()
        assert "runtime.txt" not in git_check(work, "diff", "--name-only", _base).splitlines()
        assert_summary(devlyn, {
            "mode": "full", "checked": 1, "offenders": 1,
            "reverted": 1, "revert_failed": 0, "exit": 0,
        })

        work, devlyn, _base = make_fixture(root, "devlyn-owned-tracked-mutation")
        archived = devlyn / "runs" / "prior" / "pipeline.state.json"
        write_text(archived, "tracked devlyn state\n")
        git_check(work, "add", archived.relative_to(work).as_posix())
        git_check(work, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "track devlyn state")
        write_text(archived, "mutated devlyn state\n")
        write_text(work / "notes.txt", "polluted\n")
        assert checked_run_gate(work, devlyn) == 0
        assert archived.read_text(encoding="utf-8") == "mutated devlyn state\n"
        assert (work / "notes.txt").read_text(encoding="utf-8") == "base notes\n"
        findings = read_findings(devlyn)
        assert [finding["file"] for finding in findings] == ["notes.txt"]
        assert findings[0]["status"] == "reverted"
        assert_summary(devlyn, {
            "mode": "full", "checked": 1, "offenders": 1,
            "reverted": 1, "revert_failed": 0, "exit": 0,
        })

        work, devlyn, base = make_fixture(root, "cleanup-window")
        write_text(work / "cleanable.txt", "cleanup changed\n")
        git_check(work, "add", "cleanable.txt")
        git_check(work, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "cleanup")
        post_sha = git_check(work, "rev-parse", "HEAD")
        write_state(devlyn, {
            "mode": "full",
            "base_ref": {"sha": base},
            "phases": {"cleanup": {"verdict": "PASS", "pre_sha": base, "post_sha": post_sha}},
        })
        assert checked_run_gate(work, devlyn) == 0
        assert not (devlyn / FINDINGS_NAME).exists()
        assert_summary(devlyn, {"mode": "full", "checked": 1, "offenders": 0, "exit": 0})

        work, devlyn, base = make_fixture(root, "cleanup-malformed")
        write_state(devlyn, {
            "mode": "full",
            "base_ref": {"sha": base},
            "phases": {"cleanup": {"verdict": "PASS", "pre_sha": base}},
        })
        assert checked_run_gate(work, devlyn) == 1
        assert read_findings(devlyn)[0]["rule_id"] == "scope.finish-gate-malformed"
        summary = read_summary(devlyn)
        assert summary["exit"] == 1, summary
        assert "phases.cleanup with a verdict" in summary["malformed"], summary

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
        assert checked_run_gate(work, devlyn) == 0
        assert (work / "notes.txt").read_text(encoding="utf-8") == "base notes\n"
        assert read_findings(devlyn)[0]["status"] == "reverted"
        assert_summary(devlyn, {
            "mode": "full", "checked": 1, "offenders": 1,
            "reverted": 1, "revert_failed": 0, "exit": 0,
        })

        work, devlyn, _base = make_fixture(root, "git-diff-failure")
        original_git = globals()["git"]

        def failing_git(work_arg: pathlib.Path, *args: str) -> subprocess.CompletedProcess[str]:
            if args[:2] == ("diff", "--name-only"):
                return subprocess.CompletedProcess(["git", *args], 128, "", "simulated diff failure")
            return original_git(work_arg, *args)

        globals()["git"] = failing_git
        try:
            assert checked_run_gate(work, devlyn) == 1
            finding = read_findings(devlyn)[0]
            assert finding["rule_id"] == "scope.finish-gate-malformed"
            assert "cannot compute finish-gate changed files" in finding["message"]
            summary = read_summary(devlyn)
            assert summary["exit"] == 1, summary
            assert "cannot compute finish-gate changed files" in summary["malformed"], summary
        finally:
            globals()["git"] = original_git

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
    raise SystemExit(main())
