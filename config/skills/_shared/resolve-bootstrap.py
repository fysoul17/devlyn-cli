#!/usr/bin/env python3
"""Deterministic PHASE-0 bootstrap for /devlyn-resolve."""
from __future__ import annotations

import contextlib
import datetime
import hashlib
import importlib.util
import json
import os
import pathlib
import runpy
import secrets
import stat
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True


VALUE_FLAGS = {
    "--max-rounds", "--engine", "--spec", "--verify-only", "--goal-file", "--role-config",
}
BOOL_FLAGS = {"--pair-verify", "--no-pair", "--risk-probes", "--no-risk-probes"}
PHASE_NAMES = ("plan", "probe_derive", "implement", "verify", "final_report")


class BootstrapBlocked(Exception):
    def __init__(self, reason: str, detail: str):
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


def block(reason: str, detail: str) -> None:
    raise BootstrapBlocked(reason, detail)


def reject_json_constant(token: str) -> None:
    raise ValueError(f"invalid JSON numeric constant: {token}")


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def strict_json(text: str):
    return json.loads(
        text,
        parse_constant=reject_json_constant,
        object_pairs_hook=reject_duplicate_keys,
    )


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def atomic_write(path: pathlib.Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".tmp.")
    try:
        with open(fd, "wb") as handle:
            handle.write(raw)
        pathlib.Path(name).replace(path)
    except BaseException:
        pathlib.Path(name).unlink(missing_ok=True)
        raise


def atomic_write_batch(
    outputs: dict[pathlib.Path, bytes | None],
    writer=atomic_write,
) -> None:
    originals = {
        path: (path.exists(), path.read_bytes() if path.exists() else None)
        for path in outputs
    }
    parent_existed = {path.parent: path.parent.exists() for path in outputs}
    try:
        for path, raw in outputs.items():
            if raw is None:
                path.unlink(missing_ok=True)
            else:
                writer(path, raw)
    except BaseException:
        for path, (existed, raw) in reversed(originals.items()):
            if existed:
                assert raw is not None
                atomic_write(path, raw)
            else:
                path.unlink(missing_ok=True)
        for parent, existed in parent_existed.items():
            if not existed and parent.exists():
                parent.rmdir()
        raise


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def parse_flags(argv: list[str]) -> dict:
    values: dict[str, str] = {}
    switches: set[str] = set()
    positional: list[str] = []
    seen_single: set[str] = set()
    i = 0
    positional_only = False
    while i < len(argv):
        token = argv[i]
        if positional_only:
            positional.append(token)
            i += 1
            continue
        if token == "--":
            positional_only = True
            i += 1
            continue
        if token in BOOL_FLAGS:
            switches.add(token)
            i += 1
            continue
        if token in VALUE_FLAGS:
            if token in seen_single:
                block("BLOCKED:invalid-flags", f"{token} may be passed only once")
            if i + 1 >= len(argv) or argv[i + 1].startswith("--"):
                block("BLOCKED:invalid-flags", f"{token} requires a value")
            values[token] = argv[i + 1]
            seen_single.add(token)
            i += 2
            continue
        if token.startswith("-"):
            block("BLOCKED:invalid-flags", f"unknown flag: {token}")
        positional.append(token)
        i += 1

    if "--pair-verify" in switches and "--no-pair" in switches:
        block("BLOCKED:invalid-flags", "--pair-verify and --no-pair are mutually exclusive")
    if "--risk-probes" in switches and "--no-risk-probes" in switches:
        block("BLOCKED:invalid-flags", "--risk-probes and --no-risk-probes are mutually exclusive")
    if "--goal-file" in values and any(flag in values for flag in ("--spec", "--verify-only")):
        block("BLOCKED:invalid-flags", "--goal-file is mutually exclusive with --spec/--verify-only")
    if "--goal-file" in values and positional:
        block("BLOCKED:invalid-flags", "--goal-file is mutually exclusive with an inline goal")
    if "--verify-only" in values and "--spec" not in values:
        block("BLOCKED:invalid-flags", "--verify-only requires --spec")
    if "--verify-only" in values and "--risk-probes" in switches:
        block("BLOCKED:invalid-flags", "--risk-probes needs PHASE 1.5, which --verify-only skips")
    if "--spec" in values and positional:
        block("BLOCKED:invalid-flags", "--spec is mutually exclusive with an inline goal")

    max_rounds_raw = values.get("--max-rounds", "4")
    try:
        max_rounds = int(str(max_rounds_raw))
    except ValueError:
        block("BLOCKED:invalid-flags", "--max-rounds must be a positive integer")
    if max_rounds < 1:
        block("BLOCKED:invalid-flags", "--max-rounds must be a positive integer")

    mode = "verify-only" if "--verify-only" in values else "spec" if "--spec" in values else "free-form"
    return {
        "mode": mode,
        "max_rounds": max_rounds,
        "engine": values.get("--engine"),
        "spec": values.get("--spec"),
        "verify_ref": values.get("--verify-only"),
        "goal_file": values.get("--goal-file"),
        "role_config": values.get("--role-config"),
        "no_pair": "--no-pair" in switches,
        "risk_probes": "--risk-probes" in switches,
        "no_risk_probes": "--no-risk-probes" in switches,
        "inline_goal": " ".join(positional),
        "pair_verify": "--pair-verify" in switches,
    }


def validate_shared_dir(shared_dir: pathlib.Path) -> None:
    for name in ("spec-verify-check.py", "archive_run.py", "process-evidence.py"):
        required = shared_dir / name
        if not required.is_file():
            block("BLOCKED:shared-dir-unresolved", str(required))


def archive_prior_run(devlyn: pathlib.Path, shared_dir: pathlib.Path) -> None:
    archive = runpy.run_path(shared_dir / "archive_run.py")
    if not archive["has_owned_artifacts"](devlyn):
        return
    try:
        state = archive["read_state"](devlyn)
    except (archive["ArchiveError"], OSError, UnicodeError, ValueError) as exc:
        block("BLOCKED:prior-run-ownership-unverified", str(exc))
    run_id = state["run_id"]
    if not archive["is_completed"](state) or archive["has_bootstrap_residue"](devlyn):
        block(
            "BLOCKED:prior-run-unfinished",
            f"Run {run_id} at {devlyn.parent} is unfinished or indeterminate. "
            "Continue through its owning session or start in a distinct worktree.",
        )
    try:
        archive["move_artifacts"](devlyn, devlyn / "runs" / run_id)
        archive["prune"](devlyn / "runs", keep=10)
    except (archive["ArchiveError"], OSError, UnicodeError, ValueError) as exc:
        block("BLOCKED:prior-run-archive-failed", str(exc))


def safe_goal_file(cwd: pathlib.Path, raw_path: str) -> bytes:
    supplied = pathlib.Path(raw_path)
    if supplied.is_absolute() or ".." in supplied.parts:
        block("BLOCKED:goal-file-invalid-path", raw_path)
    target = cwd / supplied
    try:
        resolved = target.resolve(strict=True)
        resolved.relative_to(cwd.resolve())
    except (OSError, ValueError):
        if target.exists():
            block("BLOCKED:goal-file-invalid-path", raw_path)
        block("BLOCKED:goal-file-unreadable", raw_path)
    try:
        metadata = resolved.stat()
    except OSError:
        block("BLOCKED:goal-file-unreadable", raw_path)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_mode & 0o444 == 0:
        block("BLOCKED:goal-file-unreadable", raw_path)
    try:
        raw = resolved.read_bytes()
        text = raw.decode("utf-8")
    except (OSError, UnicodeError):
        block("BLOCKED:goal-file-unreadable", raw_path)
    if not text.strip():
        block("BLOCKED:goal-file-empty", raw_path)
    return raw


def run_checked(command: list[str], cwd: pathlib.Path) -> None:
    proc = subprocess.run(command, cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip() or "command failed"
        block("BLOCKED:invalid-flags", detail)


def load_spec_helper(shared_dir: pathlib.Path):
    path = shared_dir / "spec-verify-check.py"
    spec = importlib.util.spec_from_file_location("devlyn_spec_verify_check", path)
    if spec is None or spec.loader is None:
        block("BLOCKED:shared-dir-unresolved", str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def init_spec_source(
    cwd: pathlib.Path, staging_dir: pathlib.Path, shared_dir: pathlib.Path, raw_path: str, risk_probes: bool = False,
) -> tuple[dict, bytes | None]:
    path = pathlib.Path(raw_path)
    path = path if path.is_absolute() else cwd / path
    if not path.is_file():
        block("BLOCKED:invalid-flags", f"spec not found: {raw_path}")
    try:
        raw = path.read_bytes()
        raw.decode("utf-8")
    except (OSError, UnicodeError) as exc:
        block("BLOCKED:invalid-flags", f"spec unreadable: {raw_path}: {exc}")
    helper = shared_dir / "spec-verify-check.py"
    expected = path.with_name("spec.expected.json")
    module = load_spec_helper(shared_dir)
    if risk_probes and not module.extract_verification_text(path.read_text(encoding="utf-8")):
        block("BLOCKED:invalid-flags", "--risk-probes needs the spec's <!-- devlyn:verification --> section, "
              "which PROBE_DERIVE derives every probe from")
    # A bound None means no directory entry existed, so any entry there is a regular file or refused.
    try:
        present = module._present(expected)
    except OSError as exc:
        block("BLOCKED:invalid-flags", f"cannot inspect {expected}: {exc}")
    if present and not expected.is_file():
        block("BLOCKED:invalid-flags", f"spec.expected.json exists but is not a regular file: {expected}")
    if present:
        found, _staged, error, _expected_path, _data = module.stage_from_expected(path, staging_dir)
        if not found or error:
            block("BLOCKED:invalid-flags", error or f"expected contract not found: {expected}")
    else:
        run_checked([sys.executable, str(helper), "--check", str(path)], cwd)
        _found, _staged, error = module.stage_from_source(path, staging_dir)
        if error:
            block("BLOCKED:invalid-flags", error)
    staged_path = staging_dir / "spec-verify.json"
    return ({
        "type": "spec",
        "spec_path": raw_path,
        "spec_sha256": sha256(raw),
        "expected_sha256": sha256(expected.read_bytes()) if present else None,
        "criteria_path": None,
        "criteria_sha256": None,
    }, staged_path.read_bytes() if staged_path.is_file() else None)


def git_text(cwd: pathlib.Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=cwd, capture_output=True)
    text = os.fsdecode(proc.stdout.removesuffix(b"\n"))
    if proc.returncode != 0 or not text:
        detail = os.fsdecode(proc.stderr or proc.stdout).strip() or "git command failed"
        block("BLOCKED:invalid-flags", detail)
    return text


def base_branch(cwd: pathlib.Path) -> str | None:
    proc = subprocess.run(
        ["git", "symbolic-ref", "--short", "-q", "HEAD"],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if proc.returncode == 1 and not proc.stdout.strip() and not proc.stderr.strip():
        return None
    if proc.returncode != 0 or not proc.stdout.strip():
        detail = (proc.stderr or proc.stdout).strip() or "git symbolic-ref failed"
        block("BLOCKED:invalid-flags", detail)
    return proc.stdout.strip()


def capture_external_diff(cwd: pathlib.Path, ref: str) -> tuple[bytes, str | None]:
    """The verify-only patch and the commit it is diffed from: a ref resolves once; a patch file asserts none."""
    supplied = pathlib.Path(ref)
    source = supplied if supplied.is_absolute() else cwd / supplied
    if source.is_file():
        return source.read_bytes(), None
    resolved = subprocess.run(["git", "rev-parse", "--verify", "--quiet", "--end-of-options", ref + "^{commit}"],
                              cwd=cwd, capture_output=True)
    if resolved.returncode != 0:
        block("BLOCKED:invalid-flags", f"--verify-only {ref} is neither a patch file nor a commit")
    oid = os.fsdecode(resolved.stdout).strip()
    proc = subprocess.run(["git", "diff", "--binary", "--no-ext-diff", "--src-prefix=a/", "--dst-prefix=b/", oid], cwd=cwd, capture_output=True)
    if proc.returncode != 0:
        block("BLOCKED:invalid-flags", os.fsdecode(proc.stderr or proc.stdout).strip())
    return proc.stdout, oid


def require_clean_tracked_baseline(cwd: pathlib.Path, shared_dir: pathlib.Path) -> None:
    """Refuse tracked changes, including ones index flags hide; a sparse checkout's absences are not changes."""
    helper = load_spec_helper(shared_dir)
    changed: list[str] = []
    try:
        with helper.observed_git(cwd, helper.sparse_absent_entries(cwd)) as (git, flags):
            for args in (("diff",), ("diff", "--cached")):
                changed += [os.fsdecode(path) for path in git(*args, "--no-renames", "--name-only", "-z",
                                                              "--ignore-submodules=none").split(b"\0") if path]
            dirty = sorted({path for path in changed if path != ".devlyn" and not path.startswith(".devlyn/")})
            index = git("ls-files", "-s", "-z").split(b"\0") if dirty else []
    except (OSError, ValueError) as exc:
        block("BLOCKED:invalid-flags", str(exc))
    if dirty:
        hidden = [f"{path} ({flags[path]})" for path in dirty if path in flags]
        gitlinks = {os.fsdecode(entry.partition(b"\t")[2]) for entry in index if entry.startswith(b"160000 ")}
        submodules = [path for path in dirty if path in gitlinks]
        block(
            "BLOCKED:worktree-dirty",
            f"Commit or stash tracked changes outside .devlyn before starting a full resolve: {', '.join(dirty)}."
            + (f" Content inside a submodule ({', '.join(submodules)}) must be committed or cleaned inside it, or"
               " ignored by that repository's own ignore rules; the submodule.<name>.ignore setting is not honored."
               if submodules else "")
            + (f" Index flags hid these: {', '.join(hidden)}." if hidden else ""),
        )


@contextlib.contextmanager
def admission_lock(cwd: pathlib.Path):
    lock_path = pathlib.Path(git_text(cwd, "rev-parse", "--absolute-git-dir")) / "devlyn-bootstrap.lock"
    with contextlib.ExitStack() as stack:
        try:
            stack.enter_context(runpy.run_path(pathlib.Path(__file__).with_name("platform-support.py"))["file_lock"](lock_path))
        except BlockingIOError:
            block(
                "BLOCKED:bootstrap-contended",
                f"Bootstrap admission is occupied at {cwd}. Retry from this root after admission finishes.",
            )
        except (ImportError, OSError, AttributeError) as exc:
            block("BLOCKED:bootstrap-lock-unavailable", f"{cwd}: {lock_path}: {exc}")
        for path in (cwd / ".devlyn", cwd / ".devlyn" / "runs"):
            if path.is_symlink() or path.resolve() != path or (path.exists() and not path.is_dir()):
                block("BLOCKED:devlyn-path-redirect", f"{cwd}: require an unredirected directory at {path}")
        yield


def bootstrap(
    argv: list[str],
    cwd: pathlib.Path,
    shared_dir: pathlib.Path,
    *,
    default_engine: str = "claude",
    writer=atomic_write,
) -> dict:
    cwd = cwd.resolve()
    validate_shared_dir(shared_dir)
    parsed = parse_flags(argv)
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"):
        if name in os.environ:
            block("BLOCKED:git-env-redirect", f"{cwd}: inherited {name} redirects Git; unset it before retrying.")
    root = pathlib.Path(git_text(cwd, "rev-parse", "--show-toplevel")).resolve()
    if cwd != root:
        block("BLOCKED:worktree-root-required", f"{cwd} is not the worktree root {root}. Retry from {root}.")
    if parsed["mode"] != "verify-only":
        require_clean_tracked_baseline(cwd, shared_dir)
    with admission_lock(cwd):
        devlyn = cwd / ".devlyn"
        outputs: dict[pathlib.Path, bytes | None] = {devlyn / "external-diff.patch": None}
        if parsed["mode"] == "free-form":
            raw_goal = (
                safe_goal_file(cwd, parsed["goal_file"])
                if parsed["goal_file"] is not None
                else parsed["inline_goal"].encode("utf-8")
            )
            outputs[devlyn / "goal.raw.txt"] = raw_goal
            source = {
                "type": "generated",
                "spec_path": None,
                "spec_sha256": None,
                "expected_sha256": None,
                "goal_path": ".devlyn/goal.raw.txt",
                "goal_sha256": sha256(raw_goal),
                "criteria_path": ".devlyn/criteria.generated.md",
                "criteria_sha256": None,
            }
        else:
            with tempfile.TemporaryDirectory() as tmp:
                source, staged_spec = init_spec_source(
                    cwd, pathlib.Path(tmp), shared_dir, parsed["spec"], parsed["risk_probes"],
                )
            outputs[devlyn / "spec-verify.json"] = staged_spec
            if parsed["mode"] == "verify-only":
                outputs[devlyn / "external-diff.patch"], source["diff_base_sha"] = capture_external_diff(cwd, parsed["verify_ref"])

        role_input = None
        if parsed["role_config"] is not None:
            role_module = runpy.run_path(pathlib.Path(__file__).with_name("role-config.py"))
            requested_path = pathlib.Path(parsed["role_config"])
            if not requested_path.is_absolute():
                requested_path = cwd / requested_path
            try:
                value, pin = role_module["read_config"](requested_path, run=True)
            except ValueError as exc:
                block("BLOCKED:invalid-engine-config", str(exc))
            role_input = {**pin, "value": value}

        engine = parsed["engine"] or default_engine
        engine_source = "flag" if parsed["engine"] is not None else "default"
        now = datetime.datetime.now(datetime.timezone.utc)
        started_at = now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"
        run_id = now.strftime("rs-%Y%m%dT%H%M%SZ-") + secrets.token_hex(6)
        state = {
            "version": "3.0",
            "role_config_input": role_input,
            "run_id": run_id,
            "started_at": started_at,
            "session_id": os.environ.get("CLAUDE_CODE_SESSION_ID"),
            "engine": engine,
            "engine_source": engine_source,
            "mode": parsed["mode"],
            "pair_verify": parsed["pair_verify"],
            "complexity": None,
            "risk_profile": {
                "high_risk": False,
                "reasons": [],
                "risk_probes_enabled": parsed["risk_probes"],
                "risk_probes_explicit": parsed["risk_probes"] or parsed["no_risk_probes"],
                "pair_default_enabled": not parsed["no_pair"],
            },
            "risk_probes_digest": None,
            "process_evidence": None,
            "base_ref": {
                "branch": base_branch(cwd),
                "sha": git_text(cwd, "rev-parse", "HEAD"),
            },
            "rounds": {"max_rounds": parsed["max_rounds"], "global": 0},
            "untracked_baseline_sha256": None,
            "source": source,
            "phases": {name: None for name in PHASE_NAMES},
            "verify": {"coverage_failed": False, "pair_trigger": None},
        }
        state_raw = json_bytes(state)
        outputs[devlyn / "pipeline.state.json"] = state_raw
        archive_prior_run(devlyn, shared_dir)
        atomic_write_batch(outputs, writer)
        return {
            "ok": True,
            "run_id": run_id,
            "mode": parsed["mode"],
            "source": source,
            "state_path": ".devlyn/pipeline.state.json",
            "state_sha256": sha256(state_raw),
        }



def pathname_self_test() -> None:
    script = pathlib.Path(__file__).resolve()
    env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
    with tempfile.TemporaryDirectory() as tmp:
        for name in ("plain", "trailing ", "trailing\t", "trailing\n", "trailing\r\n"):
            if os.name == "nt" and name != "plain":
                print(f"SKIP POSIX-only pathname {name!r}: native Windows rejects/normalizes this name")
                continue
            repo = pathlib.Path(tmp).resolve() / name
            repo.mkdir()

            def git(*args):
                return subprocess.run(["git", *args], cwd=repo, env=env,
                                      check=True, capture_output=True).stdout

            git("init", "-q")
            git("-c", "user.name=Test", "-c", "user.email=test@example.com",
                "commit", "--allow-empty", "-qm", "base")
            for option, path in (("--show-toplevel", repo), ("--absolute-git-dir", repo / ".git")):
                raw = git("rev-parse", option)
                print(f"pathname {name!r} {option}: {raw!r}", flush=True)
                assert raw == os.fsencode(path.as_posix() if os.name == "nt" else path) + b"\n", raw
            command = [sys.executable, str(script), "pathname", "probe"]
            proc = subprocess.run(command, cwd=repo, env=env, capture_output=True, timeout=15)
            result = strict_json(proc.stdout)
            assert proc.returncode == 0 and result["ok"] and not proc.stderr, (name, proc, result)
            for option, path in (("--show-toplevel", repo), ("--absolute-git-dir", repo / ".git")):
                assert git_text(repo, "rev-parse", option) == (path.as_posix() if os.name == "nt" else str(path))
            lock = repo / ".git" / "devlyn-bootstrap.lock"
            inode = lock.stat().st_ino
            devlyn = repo / ".devlyn"
            before = {p.relative_to(devlyn): p.read_bytes() for p in devlyn.rglob("*") if p.is_file()}
            assert (devlyn / "goal.raw.txt").read_bytes() == b"pathname probe"
            proc = subprocess.run(command, cwd=repo, env=env, capture_output=True, timeout=15)
            refused = strict_json(proc.stdout)
            assert proc.returncode == 1 and not proc.stderr, (name, proc)
            assert refused["blocked"] == "BLOCKED:prior-run-unfinished", refused
            assert str(repo) in refused["detail"] and result["run_id"] in refused["detail"]
            assert {p.relative_to(devlyn): p.read_bytes() for p in devlyn.rglob("*") if p.is_file()} == before
            assert not (devlyn / "runs").exists() and lock.stat().st_ino == inode
            print(f"PASS admission pathname {name!r}: exact root/Gitdir, stable lock, unfinished refusal")


def admission_self_test() -> None:
    import time
    from unittest.mock import patch

    shared = pathlib.Path(__file__).resolve().parent
    script = shared / "resolve-bootstrap.py"
    archive = runpy.run_path(shared / "archive_run.py")
    env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1",
               CLAUDE_CODE_SESSION_ID="same-admission-session")
    spec_raw = (
        '# Spec\n\n<!-- devlyn:verification -->\n## Verification\n\n```json\n'
        '{"verification_commands":[{"cmd":"printf ok","stdout_contains":["ok"]}]}\n```\n'
    ).encode()
    modes = (["goal", "A"], ["--spec", "spec.md"],
             ["--verify-only", "external.patch", "--spec", "spec.md"])

    def git(repo, *args):
        return subprocess.run(["git", *args], cwd=repo, env=env, check=True, capture_output=True).stdout

    def inputs(repo):
        (repo / "spec.md").write_bytes(spec_raw)
        (repo / "external.patch").write_bytes(b"external patch A\x00\n")

    def init(repo):
        repo.mkdir()
        git(repo, "init", "-q")
        git(repo, "config", "user.email", "test@example.com")
        git(repo, "config", "user.name", "Test")
        (repo / "app.py").write_text("print('base')\n", encoding="utf-8")
        git(repo, "add", "app.py")
        git(repo, "commit", "-qm", "base")
        inputs(repo)

    def snapshot(path):
        try:
            pending = [(path, path.lstat())]
        except FileNotFoundError:
            return {}
        result = {}
        while pending:
            p, metadata = pending.pop()
            key = str(p.relative_to(path))
            if stat.S_ISLNK(metadata.st_mode) or (
                os.name == "nt" and metadata.st_reparse_tag == stat.IO_REPARSE_TAG_MOUNT_POINT
            ):
                result[key] = str(p.readlink())
            elif stat.S_ISDIR(metadata.st_mode):
                result[key] = None
                pending.extend((child, child.lstat()) for child in p.iterdir())
            else:
                result[key] = p.read_bytes()
        return result

    def cli(repo, argv, extra_env=None):
        proc = subprocess.run([sys.executable, str(script), *argv], cwd=repo,
                              env=extra_env or env, capture_output=True, text=True, timeout=15, encoding="utf-8")
        assert proc.stderr == "", (proc.returncode, proc.stdout, proc.stderr)
        result = strict_json(proc.stdout)
        assert proc.returncode == (0 if result["ok"] else 1), result
        return result

    def refusal(repo, argv, reason, extra_env=None):
        before = snapshot(repo / ".devlyn")
        result = cli(repo, argv, extra_env)
        assert result.get("blocked") == reason, result
        assert snapshot(repo / ".devlyn") == before, result
        return result

    def wait_for(predicate):
        deadline = time.monotonic() + 15
        while not predicate():
            assert time.monotonic() < deadline, "admission child synchronization timed out"
            time.sleep(0.01)

    # Test-only seam around the real bootstrap and atomic writer. Both children
    # reach the pipe barrier before flock; only the winner reaches the writer.
    child = r"""
import json, os, pathlib, runpy, sys, time
script, repo, signals, action, barrier, argv = sys.argv[1:]
m = runpy.run_path(script)
signals = pathlib.Path(signals)
def hold():
    signals.with_suffix('.inside').touch()
    deadline = time.monotonic() + 20
    while not signals.with_suffix('.release').exists():
        if time.monotonic() > deadline:
            raise TimeoutError('held admission was not released')
        time.sleep(0.01)
def writer(path, raw):
    if action in ('hold', 'before'):
        hold()
    m['atomic_write'](path, raw)
    if action == 'canonical':
        hold()
if action.startswith('temp:'):
    replace = pathlib.Path.replace
    def held_replace(path, target):
        if path.name.startswith(action[5:] + '.tmp.'):
            hold()
        return replace(path, target)
    pathlib.Path.replace = held_replace
signals.with_suffix('.ready').touch()
if barrier.startswith('file:'):
    deadline = time.monotonic() + 20
    while not pathlib.Path(barrier[5:]).exists():
        if time.monotonic() > deadline:
            raise TimeoutError('native admission barrier was not released')
        time.sleep(0.01)
elif int(barrier) >= 0:
    os.read(int(barrier), 1)
    os.close(int(barrier))
try:
    result = m['bootstrap'](json.loads(argv), pathlib.Path(repo), pathlib.Path(script).parent, writer=writer)
except m['BootstrapBlocked'] as exc:
    print(json.dumps({'ok': False, 'blocked': exc.reason, 'detail': exc.detail}))
    sys.exit(1)
print(json.dumps(result))
"""

    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp).resolve()
        repo = root / "state"
        init(repo)
        first = cli(repo, modes[0])
        devlyn = repo / ".devlyn"
        state_path = devlyn / "pipeline.state.json"
        initial = strict_json(state_path.read_text(encoding="utf-8"))
        (devlyn / "engines.json").write_bytes(b'{"executor":"codex"}\n')
        (devlyn / "config.json").write_bytes(b'{"setting":true}\n')
        (devlyn / "unrelated.data").write_bytes(b"keep\n")
        old_archive = devlyn / "runs" / "unfinished-old" / "pipeline.state.json"
        old_archive.parent.mkdir(parents=True)
        old_archive.write_bytes(b'{"run_id":"unfinished-old","phases":{}}\n')
        for argv in modes:
            result = refusal(repo, argv, "BLOCKED:prior-run-unfinished")
            assert first["run_id"] in result["detail"] and str(repo) in result["detail"]
        invalid = [None, [], "PASS", {}, {"verdict": "PASS"},
                   {"completed_at": "2026-09-06T00:00:00Z"}]
        invalid += [{"verdict": v, "completed_at": "2026-09-06T00:00:00Z"}
                    for v in (None, [], {}, "UNKNOWN", "FAIL")]
        invalid += [{"verdict": "PASS", "completed_at": t} for t in (
            None, [], "", "2026-09-06T00:00:00", "2026-02-29T00:00:00Z",
            "2026-09-06T24:00:00Z", "2026-09-06T00:00:00.1Z",
            "2026-09-06T00:00:00+00:00",
        )]
        for final in invalid:
            state = dict(initial, phases={"final_report": final, "verify": {"verdict": "PASS"}})
            state_path.write_bytes(json_bytes(state))
            refusal(repo, modes[0], "BLOCKED:prior-run-unfinished")
        for verdict in ("PASS", "PASS_WITH_ISSUES", "NEEDS_WORK", "BLOCKED"):
            for timestamp in ("2024-02-29T23:59:59Z", "2024-02-29T23:59:59.123Z"):
                state = strict_json(state_path.read_text(encoding="utf-8"))
                state["phases"]["final_report"] = {"verdict": verdict, "completed_at": timestamp}
                state_path.write_bytes(json_bytes(state))
                raw = state_path.read_bytes()
                goal = (devlyn / "goal.raw.txt").read_bytes()
                assert cli(repo, modes[0])["ok"]
                archived = devlyn / "runs" / state["run_id"]
                assert (archived / "pipeline.state.json").read_bytes() == raw
                assert (archived / "goal.raw.txt").read_bytes() == goal
        assert (devlyn / "engines.json").read_bytes() == b'{"executor":"codex"}\n'
        assert (devlyn / "config.json").read_bytes() == b'{"setting":true}\n'
        assert (devlyn / "unrelated.data").read_bytes() == b"keep\n"
        assert old_archive.read_bytes() == b'{"run_id":"unfinished-old","phases":{}}\n'
        for raw in (None, b"{", b"null", b'{"run_id":[]}', b'{"run_id":"../escape"}'):
            if raw is None:
                state_path.unlink()
            else:
                state_path.write_bytes(raw)
            refusal(repo, modes[0], "BLOCKED:prior-run-ownership-unverified")
        # Residue also blocks when the canonical report otherwise looks completed.
        for pattern in archive["BOOTSTRAP_TEMP_PATTERNS"]:
            state = dict(initial, phases={"final_report": {
                "verdict": "PASS", "completed_at": "2026-09-06T00:00:00Z",
            }})
            state_path.write_bytes(json_bytes(state))
            residue = devlyn / pattern.replace("*", "interrupted")
            residue.write_bytes(b"partial")
            for argv in modes:
                refusal(repo, argv, "BLOCKED:prior-run-unfinished")
            residue.unlink()
        print("PASS admission state: same-session/all-mode byte stability, 8 completed forms, ownership/residue refusal")

        identity = root / "identity"
        init(identity)
        alias = root / "alias"
        def directory_link(link, target):
            if os.name == "nt":
                subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
                               check=True, capture_output=True)
            else:
                link.symlink_to(target, target_is_directory=True)
        directory_link(alias, identity)
        sub = identity / "sub"
        sub.mkdir()
        detail = refusal(sub, ["--goal-file", "relative.txt"], "BLOCKED:worktree-root-required")["detail"]
        assert str(identity) in detail and "Retry" in detail
        assert not (identity / ".devlyn").exists()
        external = root / "external"
        init(external)
        external_before = snapshot(external)
        for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"):
            for value in ("", str(external / ".git")):
                for argv in modes:
                    result = refusal(identity, argv, "BLOCKED:git-env-redirect", dict(env, **{key: value}))
                    assert key in result["detail"] and str(identity) in result["detail"]
        assert snapshot(external) == external_before
        # Even a non-repository location must reject Git redirection before Git.
        assert cli(root, modes[0], dict(env, GIT_DIR=""))["blocked"] == "BLOCKED:git-env-redirect"
        for relative in (".devlyn", ".devlyn/runs"):
            for dangling in (False, True):
                target = root / ("missing-target" if dangling else "redirect-target")
                if not dangling:
                    target.mkdir(exist_ok=True)
                    (target / "keep").write_bytes(b"untouched")
                link = identity / relative
                link.parent.mkdir(exist_ok=True)
                directory_link(link, target)
                before = snapshot(target)
                assert before == ({} if dangling else {".": None, "keep": b"untouched"})
                expected = {".": str(link.readlink())} if relative == ".devlyn" else {
                    ".": None, "runs": str(link.readlink()),
                }
                assert snapshot(identity / ".devlyn") == expected
                result = refusal(identity, modes[0], "BLOCKED:devlyn-path-redirect")
                assert str(link) in result["detail"] and link.resolve() == target and (os.name == "nt" or link.is_symlink())
                assert snapshot(target) == before
                link.rmdir() if os.name == "nt" else link.unlink()
        print("PASS admission identity: physical-root guidance, Git redirects including empty, live/dangling directory links")

        def launch(repo, signals, action, argv, barrier=-1):
            return subprocess.Popen(
                [sys.executable, "-c", child, str(script), str(repo), str(signals),
                 action, str(barrier), json.dumps(argv)],
                cwd=repo, env=env, **({} if os.name == "nt" else {"pass_fds": (() if barrier < 0 else (barrier,))}),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                encoding="utf-8",
            )

        def receipt(proc):
            stdout, stderr = proc.communicate(timeout=15)
            assert stderr == "", (proc.returncode, stdout, stderr)
            result = strict_json(stdout)
            assert proc.returncode == (0 if result["ok"] else 1), result
            return result

        for i, argv in enumerate(modes):
            race = root / f"race-{i}"
            init(race)
            (race / "spec-b.md").write_bytes(spec_raw.replace(b"# Spec", b"# Other spec"))
            (race / "external-b.patch").write_bytes(b"external patch B\n")
            other = ["goal", "B"] if i == 0 else [s.replace("spec.md", "spec-b.md").replace(
                "external.patch", "external-b.patch") for s in argv]
            signals = [root / f"race-{i}-{label}" for label in ("A", "B")]
            if os.name == "nt":
                barrier_file = root / f"race-{i}.barrier"
                rfd = "file:" + str(barrier_file)
            else:
                rfd, wfd = os.pipe()
            procs = []
            try:
                procs = [launch(race, signal, "hold", args, rfd)
                         for signal, args in zip(signals, (argv, other))]
                if os.name != "nt":
                    os.close(rfd)
                wait_for(lambda: all(s.with_suffix(".ready").exists() for s in signals))
                if os.name == "nt":
                    barrier_file.touch()
                else:
                    os.close(wfd)
                wait_for(lambda: any(s.with_suffix(".inside").exists() for s in signals)
                         and any(p.poll() is not None for p in procs))
                holders = [j for j, s in enumerate(signals) if s.with_suffix(".inside").exists()]
                assert len(holders) == 1, holders
                winner = holders[0]
                loser = receipt(procs[1 - winner])
                assert loser.get("blocked") == "BLOCKED:bootstrap-contended", loser
                assert str(race) in loser["detail"] and "run_id" not in loser
                assert snapshot(race / ".devlyn") == {}, "loser mutated owned/archive state"
                signals[winner].with_suffix(".release").touch()
                won = receipt(procs[winner])
                assert won["ok"]
            finally:
                for proc in procs:
                    if proc.poll() is None:
                        proc.kill()
                        proc.communicate()
            state_raw = (race / ".devlyn/pipeline.state.json").read_bytes()
            state = strict_json(state_raw.decode())
            assert state["run_id"] == won["run_id"] and sha256(state_raw) == won["state_sha256"]
            expected_files = {"pipeline.state.json"}
            if i == 0:
                goal = (race / ".devlyn/goal.raw.txt").read_bytes()
                assert goal == (b"goal A" if winner == 0 else b"goal B")
                assert sha256(goal) == state["source"]["goal_sha256"]
                expected_files.add("goal.raw.txt")
            else:
                source_path = "spec.md" if winner == 0 else "spec-b.md"
                assert state["source"]["spec_path"] == source_path
                assert state["source"]["spec_sha256"] == sha256((race / source_path).read_bytes())
                expected_files.add("spec-verify.json")
                if i == 2:
                    patch_path = "external.patch" if winner == 0 else "external-b.patch"
                    assert (race / ".devlyn/external-diff.patch").read_bytes() == (race / patch_path).read_bytes()
                    expected_files.add("external-diff.patch")
            assert {p.name for p in (race / ".devlyn").iterdir()} == expected_files
            for attempt in modes:
                refusal(race, attempt, "BLOCKED:prior-run-unfinished")
        print("PASS admission processes: pre-lock synchronized pair in all 3 modes, one winner, zero loser delta, unmixed outputs")

        linked = root / "linked"
        git(identity, "worktree", "add", "-qb", "independent", str(linked))
        inputs(linked)
        lock_path = pathlib.Path(git(identity, "rev-parse", "--absolute-git-dir").decode().strip()) / "devlyn-bootstrap.lock"
        with admission_lock(identity):
            inode = lock_path.stat().st_ino
            assert cli(linked, modes[0])["ok"]
            refusal(alias, modes[0], "BLOCKED:bootstrap-contended")
        assert cli(alias, modes[0])["ok"]
        assert lock_path.stat().st_ino == inode
        assert pathlib.Path(git(linked, "rev-parse", "--absolute-git-dir").decode().strip()) != lock_path.parent
        collision = subprocess.run(["git", "worktree", "add", str(root / "collision"), "independent"],
                                   cwd=identity, env=env, capture_output=True)
        assert collision.returncode != 0 and b"already" in collision.stderr
        assert not (root / "collision").exists()
        print("PASS admission worktrees: linked root initializes under other's lock; aliases exclude; branch collision retained")

        failure = root / "failure"
        init(failure)
        def fail_writer(path, raw):
            raise OSError("before-first-write")
        try:
            bootstrap(modes[0], failure, shared, writer=fail_writer)
        except OSError as exc:
            assert str(exc) == "before-first-write"
        else:
            raise AssertionError("writer exception was hidden")
        assert not (failure / ".devlyn").exists()
        failure_lock = failure / ".git/devlyn-bootstrap.lock"
        failure_inode = failure_lock.stat().st_ino
        module = __import__("msvcrt" if os.name == "nt" else "fcntl")
        operation = "locking" if os.name == "nt" else "flock"
        for replacement in (patch.dict(sys.modules, {module.__name__: None}),
                            patch.object(module, operation, side_effect=OSError("unsupported locking"))):
            with replacement:
                try:
                    bootstrap(modes[0], failure, shared)
                except BootstrapBlocked as exc:
                    assert exc.reason == "BLOCKED:bootstrap-lock-unavailable" and str(failure) in exc.detail
                else:
                    raise AssertionError("unavailable locking was accepted")
            assert not (failure / ".devlyn").exists()
            assert failure_lock.stat().st_ino == failure_inode
        denied = root / "lock-open-failure"
        init(denied)
        (denied / ".git/devlyn-bootstrap.lock").mkdir()
        refusal(denied, modes[0], "BLOCKED:bootstrap-lock-unavailable")
        assert cli(failure, modes[0])["ok"] and failure_lock.stat().st_ino == failure_inode
        print("PASS admission failures: before-write exception/retry; explicit import/open/acquisition refusal; persistent inode")

        deaths = [("before", modes[0], None), ("canonical", modes[0], "goal.raw.txt")]
        deaths += [("temp:" + name, modes[mode], name + ".tmp.*") for name, mode in (
            ("goal.raw.txt", 0), ("spec-verify.json", 1), ("external-diff.patch", 2), ("pipeline.state.json", 0),
        )]
        for i, (action, argv, family) in enumerate(deaths):
            dead = root / f"death-{i}"
            init(dead)
            signal = root / f"death-{i}"
            proc = launch(dead, signal, action, argv)
            try:
                wait_for(lambda: signal.with_suffix(".inside").exists() or proc.poll() is not None)
                assert signal.with_suffix(".inside").exists(), proc.communicate()
                inode = (dead / ".git/devlyn-bootstrap.lock").stat().st_ino
                proc.kill()
                stdout, stderr = proc.communicate(timeout=15)
                assert proc.returncode == (1 if os.name == "nt" else -9) and stdout == "" and stderr == "", (proc.returncode, stdout, stderr)
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.communicate()
            if family is None:
                assert not (dead / ".devlyn").exists()
                assert cli(dead, modes[1])["ok"]
            else:
                assert len(list((dead / ".devlyn").glob(family))) == 1
                for attempt in modes:
                    refusal(dead, attempt, "BLOCKED:prior-run-ownership-unverified")
            assert (dead / ".git/devlyn-bootstrap.lock").stat().st_ino == inode
        print("PASS admission death: SIGKILL before write retries; canonical and all 4 real atomic temp families preserved across modes")


def self_test() -> int:
    from unittest.mock import patch

    script_shared = pathlib.Path(__file__).resolve().parent
    try:
        strict_json('{"run_id":"a","run_id":"b"}')
    except ValueError as exc:
        assert "duplicate JSON key" in str(exc)
    else:
        raise AssertionError("duplicate bootstrap state key was accepted")

    def init_repo(path: pathlib.Path) -> None:
        path.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=path, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
        (path / "app.py").write_text("print('base')\n", encoding="utf-8")
        subprocess.run(["git", "add", "app.py"], cwd=path, check=True)
        subprocess.run(["git", "commit", "-qm", "base"], cwd=path, check=True)

    def git(path: pathlib.Path, *args: str) -> bytes:
        return subprocess.run(["git", *args], cwd=path, check=True, capture_output=True).stdout

    def snapshot(path: pathlib.Path) -> dict[str, bytes]:
        return {
            str(file.relative_to(path)): file.read_bytes()
            for file in path.rglob("*")
            if file.is_file()
        }

    def complete_prior(path: pathlib.Path) -> None:
        state_path = path / ".devlyn" / "pipeline.state.json"
        state = strict_json(state_path.read_text(encoding="utf-8"))
        state["phases"]["final_report"] = {
            "verdict": "PASS", "completed_at": "2026-09-06T00:00:00Z",
        }
        state_path.write_bytes(json_bytes(state))

    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        role_work = root / "role-repo"
        init_repo(role_work)
        role_file = root / "roles.json"
        for raw in (b"{", b'{"executor":"codex"}', b'{"roles":null}'):
            role_file.write_bytes(raw)
            try:
                bootstrap(["--role-config", str(role_file), "fix app.py"], role_work, script_shared)
            except BootstrapBlocked as exc:
                assert exc.reason == "BLOCKED:invalid-engine-config"
            else:
                raise AssertionError("invalid per-run roles admitted")
            assert not (role_work / ".devlyn/pipeline.state.json").exists()
        role_raw = b'{"roles":{"worker":{"engine":"codex","model":"gpt-6-astra"}}}'
        role_file.write_bytes(role_raw)
        bootstrap(["--role-config", str(role_file), "--no-pair", "fix app.py"], role_work, script_shared)
        staged_role = strict_json((role_work / ".devlyn/pipeline.state.json").read_text(encoding="utf-8"))
        role_file.write_text("{}", encoding="utf-8")
        assert staged_role["role_config_input"]["sha256"] == sha256(role_raw)
        assert staged_role["role_config_input"]["value"] == strict_json(role_raw.decode())
        assert staged_role["risk_profile"]["pair_default_enabled"] is False
        for flags, enabled, explicit in ((["--risk-probes"], True, True), (["--no-risk-probes"], False, True)):
            flag_work = root / ("flags" + flags[0])
            init_repo(flag_work)
            bootstrap([*flags, "fix app.py"], flag_work, script_shared)
            flagged = strict_json((flag_work / ".devlyn/pipeline.state.json").read_text(encoding="utf-8"))["risk_profile"]
            assert (flagged["risk_probes_enabled"], flagged["risk_probes_explicit"]) == (enabled, explicit), flagged
        work = root / "repo"
        init_repo(work)
        session_key = "CLAUDE_CODE_SESSION_ID"
        session_present = session_key in os.environ
        prior_session = os.environ.pop(session_key, None)
        result = bootstrap(["fix", "app.py", "failing", "test"], work, script_shared)
        state_path = work / ".devlyn" / "pipeline.state.json"
        state = strict_json(state_path.read_text(encoding="utf-8"))
        expected = {
            "version": "3.0",
            "run_id": state["run_id"],
            "started_at": state["started_at"],
            "session_id": None,
            "engine": "claude",
            "engine_source": "default",
            "mode": "free-form",
            "role_config_input": None,
            "pair_verify": False,
            "complexity": None,
            "risk_profile": {
                "high_risk": False,
                "reasons": [],
                "risk_probes_enabled": False,
                "risk_probes_explicit": False,
                "pair_default_enabled": True,
            },
            "risk_probes_digest": None,
            "process_evidence": None,
            "base_ref": {
                "branch": base_branch(work),
                "sha": git_text(work, "rev-parse", "HEAD"),
            },
            "rounds": {"max_rounds": 4, "global": 0},
            "untracked_baseline_sha256": None,
            "source": {
                "type": "generated",
                "spec_path": None,
                "spec_sha256": None,
                "expected_sha256": None,
                "goal_path": ".devlyn/goal.raw.txt",
                "goal_sha256": sha256(b"fix app.py failing test"),
                "criteria_path": ".devlyn/criteria.generated.md",
                "criteria_sha256": None,
            },
            "phases": {name: None for name in PHASE_NAMES},
            "verify": {"coverage_failed": False, "pair_trigger": None},
        }
        schema_dirs = [script_shared.parent / name for name in ("devlyn-resolve",)
                       if (script_shared.parent / name).is_dir()]
        assert len(schema_dirs) == 1, schema_dirs
        schema = (schema_dirs[0] / "references" / "state-schema.md").read_text(encoding="utf-8")
        # Two-way parity: the documented skeleton has exactly the keys bootstrap writes.
        shape = schema.split("## Top-level shape", 1)[1].split("```json\n", 1)[1].split("\n```", 1)[0]
        documented = strict_json(shape)
        assert set(documented) == set(expected), set(documented) ^ set(expected)
        for field in ("risk_profile", "base_ref", "rounds", "phases", "verify"):
            assert set(documented[field]) == set(expected[field]), (field, set(documented[field]) ^ set(expected[field]))
        assert set(documented["source"]) | {"goal_path", "goal_sha256"} == set(expected["source"])
        assert state_path.read_bytes() == json_bytes(expected)
        assert result["state_sha256"] == sha256(json_bytes(expected))
        assert (work / ".devlyn" / "goal.raw.txt").read_bytes() == b"fix app.py failing test"
        assert not (work / ".devlyn" / "untracked.baseline").exists()
        assert set(result) == {"ok", "run_id", "mode", "source", "state_path", "state_sha256"}
        print("PASS bootstrap self-test state-init byte contract: schema v3.0 exact, slim result")

        detached = root / "detached-repo"
        init_repo(detached)
        subprocess.run(["git", "checkout", "--detach", "-q"], cwd=detached, check=True)
        detached_result = bootstrap(["fix", "app.py"], detached, script_shared)
        detached_state = strict_json((detached / ".devlyn" / "pipeline.state.json").read_text(encoding="utf-8"))
        assert detached_result["ok"] is True
        assert detached_state["base_ref"]["branch"] is None
        assert detached_state["base_ref"]["sha"] == git_text(detached, "rev-parse", "HEAD")
        print("PASS bootstrap self-test detached HEAD: branch null with exact HEAD sha")

        complete_prior(work)
        os.environ[session_key] = "session-self-test"
        bootstrap(["--engine", "raw-engine", "--pair-verify", "fix", "app.py"], work, script_shared)
        stamped = strict_json(state_path.read_text(encoding="utf-8"))
        assert stamped["session_id"] == "session-self-test"
        assert stamped["engine"] == "raw-engine" and stamped["engine_source"] == "flag"
        assert stamped["pair_verify"] is True
        if session_present:
            assert prior_session is not None
            os.environ[session_key] = prior_session
        else:
            os.environ.pop(session_key)
        print("PASS bootstrap self-test session stamp: null-safe and env-present; engine flag passthrough")

        invalid_flag_cases = [
            ["--role-config"],
            ["--role-config", "a", "--role-config", "b", "fix app.py"],
            ["--pair-verify", "--no-pair", "fix", "app.py"],
            ["--goal-file", "goal.txt", "--spec", "spec.md"],
            ["--goal-file", "goal.txt", "--verify-only", "patch", "--spec", "spec.md"],
            ["--goal-file", "goal.txt", "fix", "app.py"],
            ["--goal-file"],
            ["--goal-file", "a", "--goal-file", "b"],
            ["--verify-only", "patch"],
            ["--spec", "spec.md", "fix", "app.py"],
            ["--spec", "a", "--spec", "b"],
            ["--verify-only", "a", "--spec", "s", "--verify-only", "b"],
            ["--engine"],
            ["--engine", "claude", "--engine", "codex"],
            ["--max-rounds", "0", "fix", "app.py"],
            ["--max-rounds", "x", "fix", "app.py"],
            ["--max-rounds"],
            ["--bypass", "build-gate,cleanup", "fix", "app.py"],
            ["--perf", "fix", "app.py"],
            ["--risk-probes", "--verify-only", "patch", "--spec", "spec.md"],
            ["--risk-probes", "--no-risk-probes", "fix", "app.py"],
            ["--bypass"],
            ["--unknown", "fix", "app.py"],
        ]
        for case in invalid_flag_cases:
            try:
                parse_flags(case)
            except BootstrapBlocked as exc:
                assert exc.reason == "BLOCKED:invalid-flags", (case, exc.reason)
            else:
                raise AssertionError(f"invalid flag combination accepted: {case}")
        print(f"PASS bootstrap self-test BLOCKED:invalid-flags: {len(invalid_flag_cases)} combinations")

        blocked_work = root / "blocked-repo"
        init_repo(blocked_work)
        cli_blocked = subprocess.run(
            [sys.executable, str(pathlib.Path(__file__).resolve()), "--pair-verify", "--no-pair"],
            cwd=blocked_work, capture_output=True, text=True,
            encoding="utf-8",
        )
        assert cli_blocked.returncode == 1 and cli_blocked.stderr == ""
        assert strict_json(cli_blocked.stdout)["blocked"] == "BLOCKED:invalid-flags"
        assert not (blocked_work / ".devlyn").exists()
        print("PASS bootstrap self-test failure receipt: machine-only JSON, zero partial state")

        goal_file = blocked_work / "goal.txt"
        goal_file.write_text(" \n", encoding="utf-8")
        try:
            bootstrap(["--goal-file", "goal.txt"], blocked_work, script_shared)
        except BootstrapBlocked as exc:
            assert exc.reason == "BLOCKED:goal-file-empty"
        else:
            raise AssertionError("empty goal file accepted")
        try:
            bootstrap(["--goal-file", "missing.txt"], blocked_work, script_shared)
        except BootstrapBlocked as exc:
            assert exc.reason == "BLOCKED:goal-file-unreadable"
        else:
            raise AssertionError("missing goal file accepted")
        try:
            bootstrap(["--goal-file", "../outside.txt"], blocked_work, script_shared)
        except BootstrapBlocked as exc:
            assert exc.reason == "BLOCKED:goal-file-invalid-path"
        else:
            raise AssertionError("escaping goal path accepted")
        assert not (blocked_work / ".devlyn").exists()
        print("PASS bootstrap self-test goal-file BLOCKED paths: empty/unreadable/invalid-path, zero partial state")

        goal_raw = "fix app.py\r\npreserve café bytes\n".encode()
        (work / "goal.txt").write_bytes(goal_raw)
        complete_prior(work)
        goal_result = bootstrap(["--goal-file", "goal.txt"], work, script_shared)
        assert goal_result["source"]["goal_sha256"] == sha256(goal_raw)
        assert (work / ".devlyn" / "goal.raw.txt").read_bytes() == goal_raw
        print("PASS bootstrap self-test goal source: exact bytes and sha256")

        atomic_work = root / "atomic-repo"
        init_repo(atomic_work)
        write_count = 0

        def fail_second_write(path: pathlib.Path, raw: bytes) -> None:
            nonlocal write_count
            write_count += 1
            if write_count == 2:
                raise OSError("forced second-write failure")
            atomic_write(path, raw)

        try:
            bootstrap(["fix", "app.py"], atomic_work, script_shared, writer=fail_second_write)
        except OSError as exc:
            assert str(exc) == "forced second-write failure"
        else:
            raise AssertionError("forced atomic batch failure did not fail")
        assert not (atomic_work / ".devlyn").exists()
        print("PASS bootstrap self-test atomic batch rollback: zero partial filesystem state")

        previous_state = state_path.read_bytes()
        try:
            bootstrap(["fix", "app.py"], work, root / "missing-shared")
        except BootstrapBlocked as exc:
            assert exc.reason == "BLOCKED:shared-dir-unresolved"
        else:
            raise AssertionError("missing shared directory accepted")
        assert state_path.read_bytes() == previous_state
        print("PASS bootstrap self-test BLOCKED:shared-dir-unresolved: existing state byte-stable")

        spec_dir = work / "docs" / "specs" / "sample"
        spec_dir.mkdir(parents=True)
        spec_path = spec_dir / "spec.md"
        spec_path.write_text(
            "---\ncomplexity: medium\n---\n# Spec\n\n<!-- devlyn:verification -->\n"
            "## Verification\n\n```json\n{\"verification_commands\":[{\"cmd\":\"printf ok\",\"stdout_contains\":[\"ok\"]}]}\n```\n",
            encoding="utf-8",
        )
        spec_raw = spec_path.read_bytes()
        external_patch = work / ".devlyn" / "external-diff.patch"
        external_patch.write_bytes(b"stale spec patch\n")
        complete_prior(work)
        spec_result = bootstrap(["--spec", str(spec_path.relative_to(work))], work, script_shared)
        assert not external_patch.exists()
        staged = strict_json((work / ".devlyn" / "spec-verify.json").read_text(encoding="utf-8"))
        assert staged["verification_commands"][0]["cmd"] == "printf ok"
        assert spec_result["source"]["spec_sha256"] == sha256(spec_raw)
        assert "diff_base_sha" not in spec_result["source"]
        pure_spec = spec_dir / "design.md"
        pure_spec.write_text(
            "# Design\n\n<!-- devlyn:verification -->\n## Verification\n\n"
            '```json\n{"pure_design":true,"verification_commands":[]}\n```\n',
            encoding="utf-8",
        )
        complete_prior(work)
        pure_result = bootstrap(["--spec", str(pure_spec.relative_to(work))], work, script_shared)
        assert pure_result["source"]["spec_sha256"] == sha256(pure_spec.read_bytes())
        assert not (work / ".devlyn/spec-verify.json").exists()
        crlf_spec = spec_dir / "crlf.md"
        crlf_spec.write_bytes(b"# CRLF\r\n\r\n<!-- devlyn:verification -->\r\n## Verification\r\n\r\n- prints ok\r\n\r\n"
                              b"```json\r\n{\"verification_commands\":[{\"cmd\":\"printf ok\",\"stdout_contains\":[\"ok\"]}]}\r\n```\r\n")
        complete_prior(work)
        bootstrap(["--risk-probes", "--spec", str(crlf_spec.relative_to(work))], work, script_shared)
        bare_spec = spec_dir / "bare.md"
        bare_spec.write_text("# Bare\n\n- no verification section\n", encoding="utf-8")
        complete_prior(work)
        try:
            bootstrap(["--risk-probes", "--spec", str(bare_spec.relative_to(work))], work, script_shared)
        except BootstrapBlocked as exc:
            assert exc.reason == "BLOCKED:invalid-flags" and "verification --> section" in str(exc), exc
        else:
            raise AssertionError("--risk-probes accepted for a spec PROBE_DERIVE cannot derive from")
        external_patch.write_bytes(b"stale free-form patch\n")
        complete_prior(work)
        bootstrap(["fresh", "goal"], work, script_shared)
        assert not external_patch.exists()
        (spec_dir / "spec.expected.json").write_text(json.dumps({
            "verification_commands": [{"cmd": "printf expected", "stdout_contains": ["expected"]}],
        }) + "\n", encoding="utf-8")
        complete_prior(work)
        bootstrap(["--spec", str(spec_path.relative_to(work))], work, script_shared)
        staged = strict_json((work / ".devlyn" / "spec-verify.json").read_text(encoding="utf-8"))
        assert staged["verification_commands"][0]["cmd"] == "printf expected"
        patch_raw = b"diff --git a/app.py b/app.py\nexact external bytes\x00\n"
        (work / "external.patch").write_bytes(patch_raw)
        (work / "app.py").write_text("print('dirty verify-only input')\n", encoding="utf-8")
        complete_prior(work)
        verify_result = bootstrap([
            "--verify-only", "external.patch", "--spec", str(spec_path.relative_to(work)),
        ], work, script_shared)
        assert verify_result["mode"] == "verify-only"
        assert external_patch.read_bytes() == patch_raw
        assert verify_result["source"]["diff_base_sha"] is None
        subprocess.run(["git", "restore", "app.py"], cwd=work, check=True)
        # Ambient no-prefix config must not change the reader's a/b contract.
        (work / "app.py").write_text("print('prefix control')\n", encoding="utf-8")
        settings = ["diff.noprefix"] + (["diff.external"] if os.name != "nt" else [])
        for setting in settings:
            subprocess.run(["git", "config", setting, "true"], cwd=work, check=True)
            try:
                assert b"diff --git a/app.py b/app.py\n" in capture_external_diff(work, "HEAD")[0]
            finally:
                subprocess.run(["git", "config", "--unset", setting], cwd=work, check=True)
        subprocess.run(["git", "restore", "app.py"], cwd=work, check=True)
        # A supplied ref binds its own commit, never a merge-base, and the patch is diffed from that commit.
        diverged = root / "diverged-repo"
        init_repo(diverged)
        git(diverged, "checkout", "-qb", "trunk")
        (diverged / "trunk.txt").write_text("trunk\n", encoding="utf-8")
        git(diverged, "add", "trunk.txt")
        git(diverged, "commit", "-qm", "trunk")
        git(diverged, "checkout", "-q", "-")
        (diverged / "app.py").write_text("print('feature')\n", encoding="utf-8")
        git(diverged, "commit", "-qam", "feature")
        (diverged / "spec.md").write_bytes(spec_raw)
        trunk = git_text(diverged, "rev-parse", "trunk")
        assert git_text(diverged, "merge-base", "trunk", "HEAD") != trunk
        ref_result = bootstrap(["--verify-only", "trunk", "--spec", "spec.md"], diverged, script_shared)
        assert ref_result["source"]["diff_base_sha"] == trunk
        assert (diverged / ".devlyn/external-diff.patch").read_bytes() == git(
            diverged, "diff", "--binary", "--no-ext-diff", "--src-prefix=a/", "--dst-prefix=b/", trunk)
        diverged_state = strict_json((diverged / ".devlyn/pipeline.state.json").read_text(encoding="utf-8"))
        assert diverged_state["base_ref"]["sha"] == git_text(diverged, "rev-parse", "HEAD")
        print("PASS bootstrap self-test patch lifecycle: full-mode removal + dirty verify-only exact capture;"
              " diff base is the supplied ref's own commit, null for a patch file")

        for valid_named in (True, False):
            named_work = root / f"named-spec-{valid_named}"
            init_repo(named_work)
            named_spec = named_work / "X.md"
            named_spec.write_text(
                "---\ncomplexity: " + ("medium" if valid_named else "hihg") + "\n---\n# Named spec\n",
                encoding="utf-8",
            )
            (named_work / "spec.md").write_text(
                "---\ncomplexity: " + ("hihg" if valid_named else "medium") + "\n---\n# Unrelated spec\n",
                encoding="utf-8",
            )
            (named_work / "spec.expected.json").write_text(json.dumps({
                "verification_commands": [{"cmd": "printf named-contract"}],
            }), encoding="utf-8")
            try:
                result = bootstrap(["--spec", "X.md"], named_work, script_shared)
            except BootstrapBlocked as exc:
                assert not valid_named and exc.reason == "BLOCKED:invalid-flags", exc
                assert "frontmatter complexity" in exc.detail, exc.detail
                assert not (named_work / ".devlyn").exists()
            else:
                assert valid_named, "invalid named spec was accepted via unrelated spec.md"
                assert result["source"]["spec_path"] == "X.md"
                assert result["source"]["spec_sha256"] == sha256(named_spec.read_bytes())
                staged = strict_json((named_work / ".devlyn/spec-verify.json").read_text(encoding="utf-8"))
                assert staged["verification_commands"] == [{"cmd": "printf named-contract"}]

        # Only a missing sibling binds absence; a nonregular entry or an inspection error refuses admission.
        entry_work = root / "contract-entry-repo"
        init_repo(entry_work)
        (entry_work / "spec.md").write_bytes(spec_raw)
        sibling = entry_work.resolve() / "spec.expected.json"
        real_lstat = pathlib.Path.lstat

        def denied_lstat(path: pathlib.Path):
            if path == sibling:
                raise PermissionError("injected access error")
            return real_lstat(path)

        def refused_contract(label: str, detail: str) -> None:
            try:
                bootstrap(["--spec", "spec.md"], entry_work, script_shared)
            except BootstrapBlocked as exc:
                assert exc.reason == "BLOCKED:invalid-flags" and exc.detail == detail, (label, exc.detail)
            else:
                raise AssertionError(f"{label} spec.expected.json was bound as absent")
            assert not (entry_work / ".devlyn").exists()

        nonregular = f"spec.expected.json exists but is not a regular file: {sibling}"
        sibling.mkdir()
        refused_contract("a directory", nonregular)
        sibling.rmdir()
        if os.name == "nt":
            print("SKIP dangling spec.expected.json symlink: symlink creation requires native Windows privileges")
        else:
            sibling.symlink_to("absent.json")
            refused_contract("a dangling symlink", nonregular)
            sibling.unlink()
        with patch.object(pathlib.Path, "lstat", denied_lstat):
            refused_contract("an uninspectable", f"cannot inspect {sibling}: injected access error")
        print("PASS bootstrap self-test contract absence: directory, dangling symlink and access error refused")

        dirty_work = root / "dirty-repo"
        init_repo(dirty_work)
        bootstrap(["clean", "baseline"], dirty_work, script_shared)
        before_dirty = snapshot(dirty_work / ".devlyn")
        (dirty_work / "app.py").write_text("print('unstaged')\n", encoding="utf-8")
        for label in ("unstaged", "staged"):
            if label == "staged":
                subprocess.run(["git", "add", "app.py"], cwd=dirty_work, check=True)
            try:
                bootstrap(["blocked", label], dirty_work, script_shared)
            except BootstrapBlocked as exc:
                assert exc.reason == "BLOCKED:worktree-dirty"
                assert exc.detail == "Commit or stash tracked changes outside .devlyn before starting a full resolve: app.py.", exc.detail
            else:
                raise AssertionError(f"{label} tracked owner change accepted")
            assert snapshot(dirty_work / ".devlyn") == before_dirty
        subprocess.run(["git", "restore", "--staged", "app.py"], cwd=dirty_work, check=True)
        subprocess.run(["git", "restore", "app.py"], cwd=dirty_work, check=True)
        # Index flags never hide a tracked change from the clean baseline; a sparse absence is no change.
        subprocess.run(["git", "update-index", "--assume-unchanged", "app.py"], cwd=dirty_work, check=True)
        require_clean_tracked_baseline(dirty_work, script_shared)
        (dirty_work / "app.py").write_text("print('hidden')\n", encoding="utf-8")
        try:
            require_clean_tracked_baseline(dirty_work, script_shared)
        except BootstrapBlocked as exc:
            assert exc.reason == "BLOCKED:worktree-dirty" and "app.py (h)" in exc.detail, exc.detail
        else:
            raise AssertionError("a change hidden by assume-unchanged was accepted")
        subprocess.run(["git", "update-index", "--no-assume-unchanged", "app.py"], cwd=dirty_work, check=True)
        subprocess.run(["git", "restore", "app.py"], cwd=dirty_work, check=True)
        subprocess.run(["git", "update-index", "--skip-worktree", "app.py"], cwd=dirty_work, check=True)
        (dirty_work / "app.py").unlink()
        require_clean_tracked_baseline(dirty_work, script_shared)
        subprocess.run(["git", "update-index", "--no-skip-worktree", "app.py"], cwd=dirty_work, check=True)
        subprocess.run(["git", "restore", "app.py"], cwd=dirty_work, check=True)
        # A submodule.<name>.ignore setting hides nothing: a moved checkout or untracked content inside is dirty.
        sub_work = root / "submodule-repo"
        init_repo(sub_work)
        init_repo(sub_work / "sub")
        git(sub_work, "add", "sub")
        (sub_work / ".gitmodules").write_text('[submodule "sub"]\n\tpath = sub\n\turl = ./sub\n', encoding="utf-8")
        git(sub_work, "add", ".gitmodules")
        git(sub_work, "commit", "-qm", "register sub")
        recorded = git_text(sub_work / "sub", "rev-parse", "HEAD")

        def refused_submodule() -> None:
            assert git(sub_work, "status", "--porcelain") == b""  # the ignore setting hides it from plain Git
            try:
                require_clean_tracked_baseline(sub_work, script_shared)
            except BootstrapBlocked as exc:
                assert exc.reason == "BLOCKED:worktree-dirty" and exc.detail == (
                    "Commit or stash tracked changes outside .devlyn before starting a full resolve: sub. Content inside"
                    " a submodule (sub) must be committed or cleaned inside it, or ignored by that repository's own"
                    " ignore rules; the submodule.<name>.ignore setting is not honored."), exc.detail
            else:
                raise AssertionError("submodule dirt hidden by submodule.sub.ignore was accepted")

        git(sub_work, "config", "submodule.sub.ignore", "all")
        git(sub_work / "sub", "commit", "--allow-empty", "-qm", "moved")
        refused_submodule()
        git(sub_work, "config", "--unset", "submodule.sub.ignore")
        git(sub_work, "config", "-f", ".gitmodules", "submodule.sub.ignore", "all")
        git(sub_work, "commit", "-qm", "ignore sub", ".gitmodules")
        refused_submodule()
        git(sub_work / "sub", "checkout", "-q", recorded)
        require_clean_tracked_baseline(sub_work, script_shared)
        (sub_work / "sub" / "scratch.tmp").write_text("untracked\n", encoding="utf-8")
        refused_submodule()

        devlyn_work = root / "devlyn-dirty-repo"
        init_repo(devlyn_work)
        (devlyn_work / ".devlyn").mkdir()
        owner_file = devlyn_work / ".devlyn" / "owner.txt"
        owner_file.write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "add", ".devlyn/owner.txt"], cwd=devlyn_work, check=True)
        subprocess.run(["git", "commit", "-qm", "track devlyn owner"], cwd=devlyn_work, check=True)
        owner_file.write_text("dirty allowed\n", encoding="utf-8")
        assert bootstrap(["devlyn", "allowed"], devlyn_work, script_shared)["ok"] is True
        assert owner_file.read_text(encoding="utf-8") == "dirty allowed\n"

        untracked_work = root / "untracked-repo"
        init_repo(untracked_work)
        (untracked_work / "untracked.txt").write_text("allowed\n", encoding="utf-8")
        assert bootstrap(["untracked", "allowed"], untracked_work, script_shared)["ok"] is True
        print("PASS bootstrap self-test honest baseline: dirty owner blocked and named, submodule dirt despite its"
              " ignore setting; .devlyn/untracked allowed")

        prior_work = root / "prior-run-repo"
        init_repo(prior_work)
        prior = bootstrap(["prior", "run"], prior_work, script_shared)
        prior_devlyn = prior_work / ".devlyn"
        for name in (
            "implement.task-context",
            "implement.prompt",
            "implement.stdout",
            "implement.stderr",
            "implement.events.jsonl",
            "implement.retry.1.stdout",
            "verify-judge.r0.dispatch.json",
        ):
            (prior_devlyn / name).write_text(f"prior {name}\n", encoding="utf-8")
        (prior_devlyn / "engines.json").write_text('{"executor":"codex"}\n', encoding="utf-8")
        (prior_devlyn / "unrelated.data").write_text("preserve\n", encoding="utf-8")
        before = snapshot(prior_devlyn)
        try:
            bootstrap(["replacement", "run"], prior_work, script_shared)
        except BootstrapBlocked as exc:
            assert exc.reason == "BLOCKED:prior-run-unfinished"
            assert prior["run_id"] in exc.detail and str(prior_work.resolve()) in exc.detail
        else:
            raise AssertionError("unfinished prior run was replaced")
        assert snapshot(prior_devlyn) == before
        complete_prior(prior_work)
        replacement = bootstrap(["replacement", "run"], prior_work, script_shared)
        prior_archive = prior_devlyn / "runs" / prior["run_id"]
        assert replacement["run_id"] != prior["run_id"]
        for name in (
            "pipeline.state.json",
            "goal.raw.txt",
            "implement.task-context",
            "implement.prompt",
            "implement.stdout",
            "implement.stderr",
            "implement.events.jsonl",
            "implement.retry.1.stdout",
            "verify-judge.r0.dispatch.json",
        ):
            assert (prior_archive / name).is_file(), name
            if name not in {"pipeline.state.json", "goal.raw.txt"}:
                assert not (prior_devlyn / name).exists(), name
        assert strict_json((prior_devlyn / "pipeline.state.json").read_text(encoding="utf-8"))["run_id"] == replacement["run_id"]
        assert (prior_archive / "goal.raw.txt").read_bytes() == b"prior run"
        assert (prior_devlyn / "goal.raw.txt").read_bytes() == b"replacement run"
        assert (prior_devlyn / "engines.json").read_text(encoding="utf-8") == '{"executor":"codex"}\n'
        assert (prior_devlyn / "unrelated.data").read_text(encoding="utf-8") == "preserve\n"

        for label, state_raw in (("missing", None), ("malformed", b"{\n")):
            unauthenticated = root / f"unauthenticated-{label}"
            init_repo(unauthenticated)
            unauthenticated_devlyn = unauthenticated / ".devlyn"
            unauthenticated_devlyn.mkdir()
            (unauthenticated_devlyn / "implement.stdout").write_bytes(b"owned bytes\n")
            if state_raw is not None:
                (unauthenticated_devlyn / "pipeline.state.json").write_bytes(state_raw)
            before = snapshot(unauthenticated_devlyn)
            try:
                bootstrap(["must", "block"], unauthenticated, script_shared)
            except BootstrapBlocked as exc:
                assert exc.reason == "BLOCKED:prior-run-ownership-unverified", exc.reason
            else:
                raise AssertionError(f"{label} prior-run ownership was accepted")
            assert snapshot(unauthenticated_devlyn) == before
        print("PASS bootstrap self-test prior-run ownership: unfinished refused, completed archived; unauthenticated bytes stable")

        malformed_work = root / "malformed-spec-repo"
        init_repo(malformed_work)
        bad_spec = malformed_work / "spec.md"
        bad_spec.write_text(
            "# Spec\n\n<!-- devlyn:verification -->\n## Verification\n\n```json\n{broken\n```\n",
            encoding="utf-8",
        )
        try:
            bootstrap(["--spec", "spec.md"], malformed_work, script_shared)
        except BootstrapBlocked as exc:
            assert exc.reason == "BLOCKED:invalid-flags"
        else:
            raise AssertionError("malformed spec accepted")
        assert not (malformed_work / ".devlyn").exists()
        print("PASS bootstrap self-test spec validation failure: zero partial filesystem state")

    pathname_self_test()
    admission_self_test()
    return 0


def main() -> int:
    if sys.argv[1:] == ["--self-test"]:
        return self_test()
    try:
        result = bootstrap(
            sys.argv[1:], pathlib.Path.cwd(), pathlib.Path(__file__).resolve().parent,
            default_engine=os.environ.get("DEVLYN_DEFAULT_ENGINE", "claude"),
        )
    except BootstrapBlocked as exc:
        sys.stdout.write(json.dumps({
            "ok": False,
            "blocked": exc.reason,
            "detail": exc.detail,
        }, sort_keys=True) + "\n")
        return 1
    except Exception as exc:
        sys.stdout.write(json.dumps({
            "ok": False,
            "blocked": "BLOCKED:init-failed",
            "detail": str(exc) or type(exc).__name__,
        }, sort_keys=True) + "\n")
        return 1
    sys.stdout.write(json.dumps(result, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    runpy.run_path(str(pathlib.Path(__file__).with_name("platform-support.py")))["configure_utf8"]()
    raise SystemExit(main())
