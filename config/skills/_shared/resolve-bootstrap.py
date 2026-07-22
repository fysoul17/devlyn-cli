#!/usr/bin/env python3
"""Deterministic PHASE-0 bootstrap for /devlyn:resolve."""
from __future__ import annotations

import datetime
import hashlib
import importlib.util
import json
import os
import pathlib
import secrets
import stat
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True


VALUE_FLAGS = {
    "--max-rounds", "--engine", "--spec", "--verify-only", "--goal-file", "--bypass",
}
BOOL_FLAGS = {"--pair-verify", "--no-pair", "--risk-probes", "--no-risk-probes", "--perf"}
SINGLE_VALUE_FLAGS = VALUE_FLAGS - {"--bypass"}
VALID_BYPASSES = {"build-gate", "cleanup"}
PHASE_NAMES = (
    "plan", "probe_derive", "implement", "surface_close",
    "build_gate", "cleanup", "verify", "final_report",
)


class BootstrapBlocked(Exception):
    def __init__(self, reason: str, detail: str):
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


def block(reason: str, detail: str) -> None:
    raise BootstrapBlocked(reason, detail)


def reject_json_constant(token: str) -> None:
    raise ValueError(f"invalid JSON numeric constant: {token}")


def strict_json(text: str):
    return json.loads(text, parse_constant=reject_json_constant)


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
    values: dict[str, str | list[str]] = {"--bypass": []}
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
            if token in SINGLE_VALUE_FLAGS and token in seen_single:
                block("BLOCKED:invalid-flags", f"{token} may be passed only once")
            if i + 1 >= len(argv) or argv[i + 1].startswith("--"):
                block("BLOCKED:invalid-flags", f"{token} requires a value")
            value = argv[i + 1]
            if token == "--bypass":
                assert isinstance(values[token], list)
                values[token].append(value)
            else:
                values[token] = value
                seen_single.add(token)
            i += 2
            continue
        if token.startswith("-"):
            block("BLOCKED:invalid-flags", f"unknown flag: {token}")
        positional.append(token)
        i += 1

    if "--pair-verify" in switches and "--no-pair" in switches:
        block("BLOCKED:invalid-flags", "--pair-verify and --no-pair are mutually exclusive")
    if "--goal-file" in values and any(flag in values for flag in ("--spec", "--verify-only")):
        block("BLOCKED:invalid-flags", "--goal-file is mutually exclusive with --spec/--verify-only")
    if "--goal-file" in values and positional:
        block("BLOCKED:invalid-flags", "--goal-file is mutually exclusive with an inline goal")
    if "--verify-only" in values and "--spec" not in values:
        block("BLOCKED:invalid-flags", "--verify-only requires --spec")
    if "--spec" in values and positional:
        block("BLOCKED:invalid-flags", "--spec is mutually exclusive with an inline goal")

    max_rounds_raw = values.get("--max-rounds", "4")
    try:
        max_rounds = int(str(max_rounds_raw))
    except ValueError:
        block("BLOCKED:invalid-flags", "--max-rounds must be a positive integer")
    if max_rounds < 1:
        block("BLOCKED:invalid-flags", "--max-rounds must be a positive integer")

    bypasses: list[str] = []
    for group in values["--bypass"]:
        for phase in group.split(","):
            if phase not in VALID_BYPASSES:
                block("BLOCKED:invalid-flags", f"invalid --bypass phase: {phase or '<empty>'}")
            if phase not in bypasses:
                bypasses.append(phase)

    mode = "verify-only" if "--verify-only" in values else "spec" if "--spec" in values else "free-form"
    return {
        "mode": mode,
        "max_rounds": max_rounds,
        "engine": values.get("--engine"),
        "spec": values.get("--spec"),
        "verify_ref": values.get("--verify-only"),
        "goal_file": values.get("--goal-file"),
        "inline_goal": " ".join(positional),
        "pair_verify": "--pair-verify" in switches,
        "bypasses": bypasses,
    }


def validate_shared_dir(shared_dir: pathlib.Path) -> None:
    required = shared_dir / "spec-verify-check.py"
    if not required.is_file():
        block("BLOCKED:shared-dir-unresolved", str(required))


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
    proc = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
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
    cwd: pathlib.Path, staging_dir: pathlib.Path, shared_dir: pathlib.Path, raw_path: str,
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
    if expected.is_file():
        run_checked([sys.executable, str(helper), "--check-expected", str(expected)], cwd)
    else:
        run_checked([sys.executable, str(helper), "--check", str(path)], cwd)
    module = load_spec_helper(shared_dir)
    if expected.is_file():
        found, _staged, error, _expected_path, _data = module.stage_from_expected(path, staging_dir)
        if not found or error:
            block("BLOCKED:invalid-flags", error or f"expected contract not found: {expected}")
    else:
        _staged, error = module.stage_from_source(path, staging_dir)
        if error:
            block("BLOCKED:invalid-flags", error)
    staged_path = staging_dir / "spec-verify.json"
    return ({
        "type": "spec",
        "spec_path": raw_path,
        "spec_sha256": sha256(raw),
        "criteria_path": None,
        "criteria_sha256": None,
    }, staged_path.read_bytes() if staged_path.is_file() else None)


def git_text(cwd: pathlib.Path, *args: str, allow_empty: bool = False) -> str:
    proc = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    text = proc.stdout.strip()
    if proc.returncode != 0 or (not allow_empty and not text):
        detail = (proc.stderr or proc.stdout).strip() or "git command failed"
        block("BLOCKED:invalid-flags", detail)
    return text


def capture_external_diff(cwd: pathlib.Path, ref: str) -> bytes:
    supplied = pathlib.Path(ref)
    source = supplied if supplied.is_absolute() else cwd / supplied
    if source.is_file():
        raw = source.read_bytes()
    else:
        proc = subprocess.run(["git", "diff", "--binary", ref], cwd=cwd, capture_output=True)
        if proc.returncode != 0:
            block("BLOCKED:invalid-flags", os.fsdecode(proc.stderr or proc.stdout).strip())
        raw = proc.stdout
    return raw


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
    devlyn = cwd / ".devlyn"
    outputs: dict[pathlib.Path, bytes | None] = {}
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
            "goal_path": ".devlyn/goal.raw.txt",
            "goal_sha256": sha256(raw_goal),
            "criteria_path": ".devlyn/criteria.generated.md",
            "criteria_sha256": None,
        }
    else:
        with tempfile.TemporaryDirectory() as tmp:
            source, staged_spec = init_spec_source(
                cwd, pathlib.Path(tmp), shared_dir, parsed["spec"],
            )
        outputs[devlyn / "spec-verify.json"] = staged_spec
        if parsed["mode"] == "verify-only":
            outputs[devlyn / "external-diff.patch"] = capture_external_diff(cwd, parsed["verify_ref"])

    engine = parsed["engine"] or default_engine
    engine_source = "flag" if parsed["engine"] is not None else "default"
    now = datetime.datetime.now(datetime.timezone.utc)
    started_at = now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"
    run_id = now.strftime("rs-%Y%m%dT%H%M%SZ-") + secrets.token_hex(6)
    state = {
        "version": "3.0",
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
            "risk_probes_enabled": False,
            "risk_probes_explicit": False,
            "pair_default_enabled": True,
        },
        "risk_probes_digest": None,
        "base_ref": {
            "branch": git_text(cwd, "symbolic-ref", "--short", "-q", "HEAD", allow_empty=True) or "HEAD",
            "sha": git_text(cwd, "rev-parse", "HEAD"),
        },
        "rounds": {"max_rounds": parsed["max_rounds"], "global": 0},
        "bypasses": parsed["bypasses"],
        "implement_passed_sha": None,
        "source": source,
        "criteria": [],
        "phases": {name: None for name in PHASE_NAMES},
        "verify": {"coverage_failed": False, "pair_trigger": None},
    }
    state_raw = json_bytes(state)
    outputs[devlyn / "pipeline.state.json"] = state_raw
    atomic_write_batch(outputs, writer)
    return {
        "ok": True,
        "run_id": run_id,
        "mode": parsed["mode"],
        "source": source,
        "state_path": ".devlyn/pipeline.state.json",
        "state_sha256": sha256(state_raw),
    }


def self_test() -> int:
    script_shared = pathlib.Path(__file__).resolve().parent

    def init_repo(path: pathlib.Path) -> None:
        path.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=path, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
        (path / "app.py").write_text("print('base')\n")
        subprocess.run(["git", "add", "app.py"], cwd=path, check=True)
        subprocess.run(["git", "commit", "-qm", "base"], cwd=path, check=True)

    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        work = root / "repo"
        init_repo(work)
        session_key = "CLAUDE_CODE_SESSION_ID"
        session_present = session_key in os.environ
        prior_session = os.environ.pop(session_key, None)
        result = bootstrap(["fix", "app.py", "failing", "test"], work, script_shared)
        state_path = work / ".devlyn" / "pipeline.state.json"
        state = strict_json(state_path.read_text())
        expected = {
            "version": "3.0",
            "run_id": state["run_id"],
            "started_at": state["started_at"],
            "session_id": None,
            "engine": "claude",
            "engine_source": "default",
            "mode": "free-form",
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
            "base_ref": {
                "branch": git_text(work, "symbolic-ref", "--short", "-q", "HEAD"),
                "sha": git_text(work, "rev-parse", "HEAD"),
            },
            "rounds": {"max_rounds": 4, "global": 0},
            "bypasses": [],
            "implement_passed_sha": None,
            "source": {
                "type": "generated",
                "spec_path": None,
                "spec_sha256": None,
                "goal_path": ".devlyn/goal.raw.txt",
                "goal_sha256": sha256(b"fix app.py failing test"),
                "criteria_path": ".devlyn/criteria.generated.md",
                "criteria_sha256": None,
            },
            "criteria": [],
            "phases": {name: None for name in PHASE_NAMES},
            "verify": {"coverage_failed": False, "pair_trigger": None},
        }
        schema = (script_shared.parent / "devlyn:resolve" / "references" / "state-schema.md").read_text()
        assert '"version": "3.0"' in schema and all(f'"{name}"' in schema for name in PHASE_NAMES)
        assert state_path.read_bytes() == json_bytes(expected)
        assert result["state_sha256"] == sha256(json_bytes(expected))
        assert (work / ".devlyn" / "goal.raw.txt").read_bytes() == b"fix app.py failing test"
        assert not (work / ".devlyn" / "untracked.baseline").exists()
        assert set(result) == {"ok", "run_id", "mode", "source", "state_path", "state_sha256"}
        print("PASS bootstrap self-test state-init byte contract: schema v3.0 exact, slim result")

        os.environ[session_key] = "session-self-test"
        bootstrap(["--engine", "raw-engine", "--pair-verify", "fix", "app.py"], work, script_shared)
        stamped = strict_json(state_path.read_text())
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
            ["--bypass", "plan", "fix", "app.py"],
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
        )
        assert cli_blocked.returncode == 1 and cli_blocked.stderr == ""
        assert strict_json(cli_blocked.stdout)["blocked"] == "BLOCKED:invalid-flags"
        assert not (blocked_work / ".devlyn").exists()
        print("PASS bootstrap self-test failure receipt: machine-only JSON, zero partial state")

        goal_file = blocked_work / "goal.txt"
        goal_file.write_text(" \n")
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
            "## Verification\n\n```json\n{\"verification_commands\":[{\"cmd\":\"printf ok\",\"stdout_contains\":[\"ok\"]}]}\n```\n"
        )
        spec_raw = spec_path.read_bytes()
        spec_result = bootstrap(["--spec", str(spec_path.relative_to(work))], work, script_shared)
        staged = strict_json((work / ".devlyn" / "spec-verify.json").read_text())
        assert staged["verification_commands"][0]["cmd"] == "printf ok"
        assert spec_result["source"]["spec_sha256"] == sha256(spec_raw)
        (spec_dir / "spec.expected.json").write_text(json.dumps({
            "verification_commands": [{"cmd": "printf expected", "stdout_contains": ["expected"]}],
        }) + "\n")
        bootstrap(["--spec", str(spec_path.relative_to(work))], work, script_shared)
        staged = strict_json((work / ".devlyn" / "spec-verify.json").read_text())
        assert staged["verification_commands"][0]["cmd"] == "printf expected"
        patch_raw = b"diff --git a/app.py b/app.py\nexact external bytes\x00\n"
        (work / "external.patch").write_bytes(patch_raw)
        verify_result = bootstrap([
            "--verify-only", "external.patch", "--spec", str(spec_path.relative_to(work)),
        ], work, script_shared)
        assert verify_result["mode"] == "verify-only"
        assert (work / ".devlyn" / "external-diff.patch").read_bytes() == patch_raw
        print("PASS bootstrap self-test spec staging + verify-only capture: exact source/diff bytes")

        malformed_work = root / "malformed-spec-repo"
        init_repo(malformed_work)
        bad_spec = malformed_work / "spec.md"
        bad_spec.write_text(
            "# Spec\n\n<!-- devlyn:verification -->\n## Verification\n\n```json\n{broken\n```\n"
        )
        try:
            bootstrap(["--spec", "spec.md"], malformed_work, script_shared)
        except BootstrapBlocked as exc:
            assert exc.reason == "BLOCKED:invalid-flags"
        else:
            raise AssertionError("malformed spec accepted")
        assert not (malformed_work / ".devlyn").exists()
        print("PASS bootstrap self-test spec validation failure: zero partial filesystem state")

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
    raise SystemExit(main())
