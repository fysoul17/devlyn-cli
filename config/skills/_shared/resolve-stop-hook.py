#!/usr/bin/env python3
"""Block a Claude Stop only for same-session incomplete devlyn state."""

from __future__ import annotations

import fnmatch
import hashlib
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time
from types import ModuleType
from typing import Any


RECEIPT_PATTERN = "resolve-stop-hook.*.json"


def load_module(path: pathlib.Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"module cannot be loaded: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def allow(reason: str) -> int:
    print(f"devlyn resolve Stop allowed: {reason}", file=sys.stderr)
    return 0


def parse_hook_input(raw: bytes) -> dict[str, Any]:
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("hook input must be a JSON object")
    if value.get("hook_event_name") != "Stop":
        raise ValueError("hook_event_name must be Stop")
    if not isinstance(value.get("stop_hook_active"), bool):
        raise ValueError("stop_hook_active must be boolean")
    return value


def canonical_root(hook_input: dict[str, Any]) -> pathlib.Path | None:
    cwd = hook_input.get("cwd")
    if not isinstance(cwd, str) or not cwd:
        return None
    try:
        root = pathlib.Path(cwd).resolve(strict=True)
    except OSError:
        return None
    return root if root.is_dir() else None


def hook_session_id(hook_input: dict[str, Any]) -> object | None:
    stdin_session = hook_input.get("session_id")
    if stdin_session is not None:
        return stdin_session
    return os.environ.get("CLAUDE_CODE_SESSION_ID")


def write_block_receipt(
    root: pathlib.Path,
    classification: object,
    hook_input: dict[str, Any],
    session_id: object,
) -> pathlib.Path:
    run_id = getattr(classification, "run_id")
    observed_ns = time.monotonic_ns()
    receipt = root / ".devlyn" / (
        f"resolve-stop-hook.{run_id}.{os.getpid()}.{observed_ns}.json"
    )
    record = {
        "classifier_status": getattr(classification, "status"),
        "hook_event_name": "Stop",
        "observed_ns": observed_ns,
        "run_id": run_id,
        "session_id": session_id,
        "stop_hook_active": hook_input["stop_hook_active"],
    }
    data = json.dumps(record, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    temporary = tempfile.NamedTemporaryFile(
        mode="wb", prefix=".resolve-stop-hook.", dir=receipt.parent, delete=False
    )
    temp_path = pathlib.Path(temporary.name)
    try:
        with temporary as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, receipt)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
    return receipt


def run_hook() -> int:
    try:
        hook_input = parse_hook_input(sys.stdin.buffer.read())
    except (OSError, UnicodeError, ValueError) as exc:
        return allow(f"hook input unavailable ({type(exc).__name__})")

    root = canonical_root(hook_input)
    if root is None:
        return allow("canonical project root unavailable")

    state_path = root / ".devlyn" / "pipeline.state.json"
    try:
        state_bytes = state_path.read_bytes()
    except FileNotFoundError:
        return allow("active pipeline state absent")
    except OSError as exc:
        return allow(f"active pipeline state unreadable ({type(exc).__name__})")

    try:
        classifier = load_module(
            pathlib.Path(__file__).with_name("terminal-claim-check.py"),
            "devlyn_terminal_claim_check",
        )
        classification, state = classifier.classify_active_state(root, state_bytes)
    except (AttributeError, ImportError, OSError, RuntimeError, SyntaxError, TypeError, ValueError) as exc:
        return allow(f"classifier unavailable ({type(exc).__name__})")

    if classification.status == "MALFORMED" or state is None:
        return allow(f"active pipeline state {classification.status}")
    if not classification.status.startswith("INCOMPLETE:"):
        return allow(f"active pipeline state {classification.status}")

    session_id = hook_session_id(hook_input)
    state_session_id = state.get("session_id")
    if state_session_id is None:
        return allow("active pipeline state has no session owner")
    if session_id is None:
        return allow("hook session id unavailable")
    if state_session_id != session_id:
        return allow("active pipeline state belongs to another session")

    try:
        write_block_receipt(root, classification, hook_input, session_id)
    except (OSError, TypeError, ValueError) as exc:
        return allow(f"block receipt unavailable ({type(exc).__name__})")

    shared = pathlib.Path(__file__).resolve().parent
    print(
        f"devlyn resolve Stop blocked: {classification.status}. Repair path: complete "
        f"the open phase via {shared / 'state-phase-write.py'}; if completion is "
        f"impossible, record an honest BLOCKED terminal via {shared / 'state-phase-write.py'} "
        f"and archive via {shared / 'archive_run.py'}.",
        file=sys.stderr,
    )
    return 2


def tree_snapshot(root: pathlib.Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            snapshot[f"L:{relative}"] = os.readlink(path)
        elif path.is_dir():
            snapshot[f"D:{relative}"] = ""
        else:
            snapshot[f"F:{relative}"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return snapshot


def self_test() -> int:
    repo = pathlib.Path(__file__).resolve().parents[3]
    k2a_source = repo / (
        "benchmark/ceiling/results/iter0077-probe-a/"
        "DR-auth-signature-f12-webhook/A1/devlyn-snapshot/pipeline.state.json"
    )
    clean_source = repo / (
        "benchmark/ceiling/results/nodeg-20260719g/"
        "DR-atomic-state-f11-batch-import/A1/devlyn-snapshot/runs/"
        "rs-20260719T121412Z-6408dc3d43c8/pipeline.state.json"
    )
    archive_module = load_module(
        pathlib.Path(__file__).with_name("archive_run.py"), "devlyn_archive_run"
    )
    assert k2a_source.is_file() and clean_source.is_file()
    scratch = pathlib.Path(tempfile.mkdtemp(prefix="devlyn-0078-stop-hook-"))
    session = "session-0078"

    def state_from(source: pathlib.Path, owner: object) -> tuple[bytes, str]:
        state = json.loads(source.read_bytes())
        state["session_id"] = owner
        return json.dumps(state, indent=2, sort_keys=True).encode() + b"\n", state["run_id"]

    def stage_active(root: pathlib.Path, source: pathlib.Path, owner: object) -> pathlib.Path:
        raw, _ = state_from(source, owner)
        state_path = root / ".devlyn" / "pipeline.state.json"
        state_path.parent.mkdir(parents=True)
        state_path.write_bytes(raw)
        return state_path

    def stage_archive(root: pathlib.Path, source: pathlib.Path, owner: object) -> None:
        raw, run_id = state_from(source, owner)
        target = root / ".devlyn" / "runs" / run_id / "pipeline.state.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)

    def invoke(
        root: pathlib.Path,
        *,
        stdin_session: object = session,
        env_session: str | None = None,
        raw_input: bytes | None = None,
        active: bool = False,
    ) -> subprocess.CompletedProcess[bytes]:
        payload = {
            "cwd": str(root),
            "hook_event_name": "Stop",
            "session_id": stdin_session,
            "stop_hook_active": active,
        }
        env = os.environ.copy()
        env.pop("CLAUDE_CODE_SESSION_ID", None)
        if env_session is not None:
            env["CLAUDE_CODE_SESSION_ID"] = env_session
        return subprocess.run(
            [sys.executable, str(pathlib.Path(__file__).resolve())],
            input=json.dumps(payload).encode() if raw_input is None else raw_input,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            check=False,
        )

    block = scratch / "block-k2a"
    block.mkdir()
    block_state = stage_active(block, k2a_source, session)
    before_sha = hashlib.sha256(block_state.read_bytes()).hexdigest()
    blocked = invoke(block, active=True)
    receipts = list((block / ".devlyn").glob(RECEIPT_PATTERN))
    assert blocked.returncode == 2 and b"state-phase-write.py" in blocked.stderr
    assert b"archive_run.py" in blocked.stderr
    assert hashlib.sha256(block_state.read_bytes()).hexdigest() == before_sha
    assert len(receipts) == 1
    assert any(fnmatch.fnmatch(receipts[0].name, pattern) for pattern in archive_module.PER_RUN_PATTERNS)
    assert json.loads(receipts[0].read_text())["stop_hook_active"] is True

    absent = scratch / "control-a-absent"
    absent.mkdir()
    archived_clean = scratch / "control-b-archived-clean"
    archived_clean.mkdir()
    stage_archive(archived_clean, clean_source, session)
    foreign = scratch / "control-c-foreign-active"
    foreign.mkdir()
    stage_active(foreign, k2a_source, "foreign-session")
    archive_only = scratch / "control-d-archive-only-foreign"
    archive_only.mkdir()
    stage_active(archive_only, clean_source, session)
    stage_archive(archive_only, clean_source, session)
    stage_archive(archive_only, k2a_source, "foreign-session")
    for root in (absent, archived_clean, foreign, archive_only):
        before = tree_snapshot(root)
        result = invoke(root)
        assert result.returncode == 0 and tree_snapshot(root) == before
        assert not list(root.rglob(RECEIPT_PATTERN))
    assert not (absent / ".devlyn").exists()

    null_owner = scratch / "null-owner"
    null_owner.mkdir()
    stage_active(null_owner, k2a_source, None)
    before = tree_snapshot(null_owner)
    assert invoke(null_owner).returncode == 0 and tree_snapshot(null_owner) == before

    malformed = scratch / "malformed"
    malformed.mkdir()
    malformed_state = malformed / ".devlyn" / "pipeline.state.json"
    malformed_state.parent.mkdir()
    malformed_state.write_bytes(k2a_source.read_bytes()[:-1])
    before = tree_snapshot(malformed)
    assert invoke(malformed).returncode == 0 and tree_snapshot(malformed) == before

    bad_stdin = scratch / "unparsable-stdin"
    bad_stdin.mkdir()
    stage_active(bad_stdin, k2a_source, session)
    before = tree_snapshot(bad_stdin)
    assert invoke(bad_stdin, raw_input=b"{").returncode == 0
    assert tree_snapshot(bad_stdin) == before

    env_fallback = scratch / "env-fallback"
    env_fallback.mkdir()
    stage_active(env_fallback, k2a_source, session)
    assert invoke(env_fallback, stdin_session=None, env_session=session).returncode == 2
    stdin_preferred = scratch / "stdin-preferred"
    stdin_preferred.mkdir()
    stage_active(stdin_preferred, k2a_source, session)
    before = tree_snapshot(stdin_preferred)
    assert invoke(
        stdin_preferred, stdin_session="foreign-session", env_session=session
    ).returncode == 0
    assert tree_snapshot(stdin_preferred) == before

    print(f"resolve-stop-hook self-test: PASS (real receipts; scratch={scratch})")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args == ["--self-test"]:
        return self_test()
    if args:
        return allow("unexpected hook arguments")
    try:
        return run_hook()
    except Exception as exc:
        return allow(f"hook internal error ({type(exc).__name__})")


if __name__ == "__main__":
    raise SystemExit(main())
