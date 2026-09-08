#!/usr/bin/env python3
"""Create and validate run-owned Codex invocation receipts."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import signal
import shutil
import subprocess
import tempfile
import time


SCHEMA_VERSION = "2.0"
PHASES = {"plan", "implement", "build_gate", "cleanup"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
DANGEROUS_FLAGS = {"--dangerously-bypass-approvals-and-sandbox", "--yolo"}
NETWORK_ACCESS_CONFIG = "sandbox_workspace_write.network_access"


class ReceiptError(ValueError):
    pass


def reject_constant(token: str) -> None:
    raise ValueError(f"invalid JSON numeric constant: {token}")


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def loads_strict_json(text: str):
    return json.loads(
        text,
        parse_constant=reject_constant,
        object_pairs_hook=reject_duplicate_keys,
    )


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def atomic_write(path: pathlib.Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".tmp.")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
        pathlib.Path(temporary).replace(path)
    except BaseException:
        pathlib.Path(temporary).unlink(missing_ok=True)
        raise


def relative_file(work: pathlib.Path, raw_path: str, label: str, *, require: bool) -> tuple[pathlib.Path, str]:
    path = pathlib.Path(raw_path)
    candidate = path if path.is_absolute() else work / path
    try:
        if require and candidate.is_symlink():
            raise ReceiptError(f"{label} must not be a symlink: {raw_path}")
        resolved = candidate.resolve(strict=require)
        relative = resolved.relative_to(work.resolve()).as_posix()
    except (OSError, ValueError) as exc:
        raise ReceiptError(f"{label} is missing or escapes the worktree: {raw_path}") from exc
    if require and not resolved.is_file():
        raise ReceiptError(f"{label} is not a regular file: {raw_path}")
    return resolved, relative


def option_values(argv: list[str], short: str, long: str) -> list[str]:
    values = []
    index = 0
    while index < len(argv):
        token = argv[index]
        if token in {short, long}:
            if index + 1 >= len(argv):
                raise ReceiptError(f"{token} requires a value")
            values.append(argv[index + 1])
            index += 2
            continue
        if token.startswith(long + "="):
            values.append(token.split("=", 1)[1])
        elif token.startswith(short + "="):
            values.append(token.split("=", 1)[1])
        index += 1
    return values


def option_value(argv: list[str], short: str, long: str) -> str | None:
    values = option_values(argv, short, long)
    if len(values) > 1:
        raise ReceiptError(f"duplicate {long} option")
    return values[0] if values else None


def sandbox_network_access(argv: list[str], phase: str) -> bool:
    enabled = phase == "build_gate"
    expected = f"{NETWORK_ACCESS_CONFIG}={'true' if enabled else 'false'}"
    related = [
        raw for raw in option_values(argv, "-c", "--config")
        if "sandbox_workspace_write" in raw or "network_access" in raw
    ]
    if related != [expected]:
        raise ReceiptError(
            f"Codex {phase} requires exactly one -c {expected}; "
            "alternate, table, missing, and duplicate network overrides are forbidden"
        )
    return enabled


def start_receipt(
    work: pathlib.Path,
    receipt_path: pathlib.Path,
    run_id: str,
    phase: str,
    round_: int,
    prompt_path: str,
    session_path: str,
    argv: list[str],
) -> None:
    if receipt_path.exists():
        raise ReceiptError(f"invocation receipt already exists: {receipt_path}")
    if SAFE_ID_RE.fullmatch(run_id) is None:
        raise ReceiptError("run id is invalid")
    if phase not in PHASES:
        raise ReceiptError(f"unsupported invocation phase: {phase}")
    if round_ < 0:
        raise ReceiptError("round must be non-negative")
    evidence_manifest = (
        work / ".devlyn" / "process-evidence" / run_id / phase
        / f"round-{round_}" / "manifest.json"
    )
    if evidence_manifest.is_file():
        manifest = loads_strict_json(evidence_manifest.read_text(encoding="utf-8"))
        entries = manifest.get("entries") if isinstance(manifest, dict) else None
        if not isinstance(entries, list):
            raise ReceiptError("existing process-evidence manifest is malformed")
        if any(
            isinstance(entry, dict)
            and isinstance(entry.get("classification"), dict)
            and entry["classification"].get("kind") == "capability_denied"
            for entry in entries
        ):
            raise ReceiptError(
                "capability-denied phase/round cannot launch another Codex invocation"
            )
    forbidden = sorted(DANGEROUS_FLAGS.intersection(argv))
    if forbidden:
        raise ReceiptError(f"forbidden Codex bypass flag: {forbidden[0]}")
    if "--json" not in argv[:-1]:
        raise ReceiptError("receipt-bound Codex invocation requires --json before the prompt")
    model = option_value(argv, "-m", "--model")
    sandbox = option_value(argv, "-s", "--sandbox")
    invocation_workdir = option_value(argv, "-C", "--cd")
    if not model:
        raise ReceiptError("Codex invocation requires an explicit model")
    if not sandbox:
        raise ReceiptError("Codex invocation requires an explicit sandbox")
    if sandbox != "workspace-write":
        raise ReceiptError(
            f"Codex {phase} sandbox must remain workspace-write, got {sandbox}"
        )
    network_access = sandbox_network_access(argv, phase)
    if not invocation_workdir:
        raise ReceiptError("Codex invocation requires an explicit workdir")
    try:
        if pathlib.Path(invocation_workdir).resolve(strict=True) != work.resolve():
            raise ReceiptError("Codex invocation workdir does not match receipt workdir")
    except OSError as exc:
        raise ReceiptError("Codex invocation workdir is missing") from exc

    prompt_file, prompt_relative = relative_file(work, prompt_path, "invocation prompt", require=True)
    session_file, session_relative = relative_file(work, session_path, "worker session", require=False)
    receipt_file, receipt_relative = relative_file(work, str(receipt_path), "invocation receipt", require=False)
    expected_receipt = f".devlyn/{phase}.invocation.{round_}.json"
    expected_session = f".devlyn/{phase}.worker-session.{round_}.jsonl"
    expected_prompt = f".devlyn/{phase}.prompt.{round_}"
    if receipt_relative != expected_receipt:
        raise ReceiptError(
            f"invocation receipt path expected {expected_receipt}, got {receipt_relative}"
        )
    if session_relative != expected_session:
        raise ReceiptError(
            f"worker session path expected {expected_session}, got {session_relative}"
        )
    if prompt_relative != expected_prompt:
        raise ReceiptError(
            f"invocation prompt path expected {expected_prompt}, got {prompt_relative}"
        )
    prompt_raw = prompt_file.read_bytes()
    try:
        prompt_argument = prompt_raw.decode("utf-8").rstrip("\n")
    except UnicodeError as exc:
        raise ReceiptError("invocation prompt is not UTF-8") from exc
    if not argv or argv[-1] != prompt_argument:
        raise ReceiptError("Codex prompt argument does not match the canonical prompt file")

    atomic_write(receipt_file, {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "phase": phase,
        "round": round_,
        "engine": "codex",
        "model": model,
        "sandbox": sandbox,
        "sandbox_network_access": network_access,
        "prompt": {"path": prompt_relative, "sha256": sha256(prompt_raw)},
        "session": {"path": session_relative, "sha256": None, "bytes": None},
        "argv_sha256": sha256(json.dumps(argv, separators=(",", ":")).encode("utf-8")),
        "status": "started",
        "exit_code": None,
    })


def read_receipt(path: pathlib.Path) -> dict:
    try:
        value = loads_strict_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ReceiptError(f"invocation receipt is invalid: {exc}") from exc
    if not isinstance(value, dict):
        raise ReceiptError("invocation receipt must contain an object")
    return value


def finish_receipt(work: pathlib.Path, receipt_path: pathlib.Path, exit_code: int) -> None:
    receipt = read_receipt(receipt_path)
    if receipt.get("status") != "started" or receipt.get("exit_code") is not None:
        raise ReceiptError("invocation receipt is not open")
    session = receipt.get("session")
    session_path = session.get("path") if isinstance(session, dict) else None
    if not isinstance(session_path, str):
        raise ReceiptError("invocation receipt session path is invalid")
    session_file, _ = relative_file(work, session_path, "worker session", require=True)
    raw = session_file.read_bytes()
    receipt["session"] = {
        "path": session_path,
        "sha256": sha256(raw),
        "bytes": len(raw),
    }
    receipt["status"] = "completed"
    receipt["exit_code"] = exit_code
    atomic_write(receipt_path, receipt)


def validate_receipt_artifacts(
    work: pathlib.Path,
    receipt_path: pathlib.Path,
    *,
    run_id: str,
    phase: str,
) -> tuple[dict, pathlib.Path, pathlib.Path, pathlib.Path]:
    """Validate self-contained receipt identity and every referenced byte carrier."""
    receipt_file, receipt_relative = relative_file(
        work, str(receipt_path), "invocation receipt", require=True,
    )
    receipt = read_receipt(receipt_file)
    if set(receipt) != {
        "schema_version", "run_id", "phase", "round", "engine", "model",
        "sandbox", "sandbox_network_access", "prompt", "session", "argv_sha256",
        "status", "exit_code",
    }:
        raise ReceiptError("invocation receipt has an invalid shape")
    round_ = receipt.get("round")
    if isinstance(round_, bool) or not isinstance(round_, int) or round_ < 0:
        raise ReceiptError("invocation receipt round is invalid")
    expected_path = f".devlyn/{phase}.invocation.{round_}.json"
    if receipt_relative != expected_path:
        raise ReceiptError(f"invocation receipt path expected {expected_path}")
    expected_identity = (SCHEMA_VERSION, run_id, phase, round_, "codex", "completed")
    actual_identity = (
        receipt["schema_version"], receipt["run_id"], receipt["phase"], receipt["round"],
        receipt["engine"], receipt["status"],
    )
    if actual_identity != expected_identity:
        raise ReceiptError("invocation receipt identity/status mismatch")
    if not isinstance(receipt["model"], str) or not receipt["model"]:
        raise ReceiptError("invocation receipt model is invalid")
    if receipt["sandbox"] != "workspace-write":
        raise ReceiptError("invocation receipt sandbox must be workspace-write")
    expected_network_access = phase == "build_gate"
    if receipt["sandbox_network_access"] is not expected_network_access:
        raise ReceiptError("invocation receipt sandbox network-access capability mismatch")
    if not isinstance(receipt["exit_code"], int) or isinstance(receipt["exit_code"], bool):
        raise ReceiptError("invocation receipt exit_code is invalid")
    if not isinstance(receipt["argv_sha256"], str) or SHA256_RE.fullmatch(receipt["argv_sha256"]) is None:
        raise ReceiptError("invocation receipt argv digest is invalid")
    prompt = receipt["prompt"]
    if not isinstance(prompt, dict) or set(prompt) != {"path", "sha256"}:
        raise ReceiptError("invocation receipt prompt binding is invalid")
    prompt_file, _ = relative_file(work, prompt["path"], "invocation prompt", require=True)
    if prompt["path"] != f".devlyn/{phase}.prompt.{round_}":
        raise ReceiptError("invocation receipt prompt path mismatch")
    if (
        not isinstance(prompt["sha256"], str)
        or SHA256_RE.fullmatch(prompt["sha256"]) is None
        or sha256(prompt_file.read_bytes()) != prompt["sha256"]
    ):
        raise ReceiptError("invocation prompt digest mismatch")
    session = receipt["session"]
    if not isinstance(session, dict) or set(session) != {"path", "sha256", "bytes"}:
        raise ReceiptError("invocation receipt session binding is invalid")
    if not isinstance(session["path"], str):
        raise ReceiptError("invocation receipt session path is invalid")
    session_file, relative_session = relative_file(
        work, session["path"], "worker session", require=True,
    )
    if relative_session != f".devlyn/{phase}.worker-session.{round_}.jsonl":
        raise ReceiptError("invocation receipt session path mismatch")
    raw = session_file.read_bytes()
    if (
        not isinstance(session["sha256"], str)
        or SHA256_RE.fullmatch(session["sha256"]) is None
        or isinstance(session["bytes"], bool)
        or not isinstance(session["bytes"], int)
        or session["bytes"] < 0
        or session["sha256"] != sha256(raw)
        or session["bytes"] != len(raw)
    ):
        raise ReceiptError("invocation worker-session digest mismatch")
    return receipt, receipt_file, prompt_file, session_file


def validate_receipt(
    work: pathlib.Path,
    receipt_path: pathlib.Path,
    *,
    run_id: str,
    phase: str,
    round_: int,
    model: str,
    prompt_sha256: str,
    session_path: pathlib.Path,
) -> dict:
    receipt, receipt_file, _prompt_file, receipt_session = validate_receipt_artifacts(
        work, receipt_path, run_id=run_id, phase=phase,
    )
    if receipt["round"] != round_ or receipt["model"] != model:
        raise ReceiptError("invocation receipt round/model mismatch")
    if receipt["prompt"]["sha256"] != prompt_sha256:
        raise ReceiptError("invocation prompt digest mismatch")
    supplied_session, _ = relative_file(
        work, str(session_path), "worker session", require=True,
    )
    if supplied_session != receipt_session:
        raise ReceiptError("invocation receipt session path mismatch")
    raw = receipt_session.read_bytes()
    if sha256(raw) != receipt["session"]["sha256"]:
        raise ReceiptError("invocation worker-session digest mismatch")
    for number, line in enumerate(raw.decode("utf-8").split("\n"), start=1):
        if not line.strip():
            continue
        try:
            event = loads_strict_json(line)
        except ValueError as exc:
            raise ReceiptError(f"invalid worker-session JSONL at line {number}: {exc}") from exc
        if not isinstance(event, dict):
            raise ReceiptError(f"worker-session event at line {number} must be an object")
        item = event.get("item")
        if (event.get("type") == "item.completed" and isinstance(item, dict)
                and item.get("type") == "error" and isinstance(item.get("message"), str)
                and item["message"].startswith("model rerouted: ")):
            raise ReceiptError(
                f"Codex reported model reroute at worker-session line {number}; "
                "requested model was not preserved; inspect the retained session"
            )
    return {
        "path": receipt_file.relative_to(work.resolve()).as_posix(),
        "sha256": sha256(receipt_file.read_bytes()),
        "sandbox": receipt["sandbox"],
        "sandbox_network_access": receipt["sandbox_network_access"],
        "argv_sha256": receipt["argv_sha256"],
        "exit_code": receipt["exit_code"],
    }


def monitor_descendant_regression() -> None:
    with tempfile.TemporaryDirectory() as raw_tmp:
        work = pathlib.Path(raw_tmp)
        fixture_bin = work / "bin"
        fixture_bin.mkdir()
        release_marker = work / "release"
        codex_pid_marker = work / "codex.pid"
        sleep_marker = work / "sleep.tsv"
        real_bash = shutil.which("bash")
        real_sleep = shutil.which("sleep")
        if real_bash is None or real_sleep is None:
            raise AssertionError("monitor regression requires bash and sleep")
        real_bash = str(pathlib.Path(real_bash).resolve(strict=True))
        real_sleep = str(pathlib.Path(real_sleep).resolve(strict=True))

        fake_codex = work / "fake-codex"
        fake_codex.write_text(
            f"#!{real_bash}\n"
            "printf '%s\\n' \"$$\" > \"$DEVLYN_WATCHDOG_TEST_CODEX_PID\"\n"
            "while [ ! -e \"$DEVLYN_WATCHDOG_TEST_RELEASE\" ]; do\n"
            "  \"$DEVLYN_WATCHDOG_TEST_REAL_SLEEP\" 0.01\n"
            "done\n",
            encoding="utf-8",
        )
        fake_codex.chmod(0o755)
        sleep_shim = fixture_bin / "sleep"
        sleep_shim.write_text(
            f"#!{real_bash}\n"
            "printf '%s\\t%s\\n' \"$$\" \"${1-}\" >> "
            "\"$DEVLYN_WATCHDOG_TEST_SLEEP_MARKER\"\n"
            "exec \"$DEVLYN_WATCHDOG_TEST_REAL_SLEEP\" \"$@\"\n",
            encoding="utf-8",
        )
        sleep_shim.chmod(0o755)

        wrapper = pathlib.Path(__file__).resolve().with_name("codex-monitored.sh")
        env = os.environ.copy()
        for key in tuple(env):
            if (
                key.startswith("DEVLYN_INVOCATION_")
                or key.startswith("DEVLYN_WATCHDOG_TEST_")
                or key.startswith("CODEX_MONITORED_")
                or key in {"CODEX_BLOCKED", "CODEX_REAL_BIN"}
            ):
                env.pop(key)
        env.update({
            "CODEX_BIN": str(fake_codex),
            "CODEX_MONITORED_HEARTBEAT": "1",
            "CODEX_MONITORED_TIMEOUT_SEC": "30",
            "DEVLYN_WATCHDOG_TEST_CODEX_PID": str(codex_pid_marker),
            "DEVLYN_WATCHDOG_TEST_RELEASE": str(release_marker),
            "DEVLYN_WATCHDOG_TEST_SLEEP_MARKER": str(sleep_marker),
            "DEVLYN_WATCHDOG_TEST_REAL_SLEEP": real_sleep,
            "PATH": str(fixture_bin) + os.pathsep + env.get("PATH", ""),
        })

        wrapped: subprocess.Popen | None = None
        fixture_groups: dict[int, set[int]] = {}
        wrapper_pgid: int | None = None

        def record_owned_process(pid: int, session_id: int) -> int | None:
            try:
                process_session = os.getsid(pid)
                process_group = os.getpgid(pid)
            except ProcessLookupError:
                return None
            except PermissionError as exc:
                raise AssertionError(f"cannot inspect fixture pid {pid}: {exc}") from exc
            if process_session != session_id:
                raise AssertionError(
                    f"fixture pid {pid} escaped session {session_id}: {process_session}"
                )
            fixture_groups.setdefault(process_group, set()).update({pid, process_group})
            return process_group

        def read_announced_groups(session_id: int) -> tuple[
            tuple[int, int] | None, dict[str, tuple[int, int]]
        ]:
            codex_info = None
            if codex_pid_marker.is_file():
                raw_pid = codex_pid_marker.read_text(encoding="utf-8")
                if raw_pid.endswith("\n") and re.fullmatch(r"[1-9][0-9]*\n", raw_pid):
                    codex_pid = int(raw_pid.strip())
                    codex_pgid = record_owned_process(codex_pid, session_id)
                    if codex_pgid is not None:
                        codex_info = (codex_pid, codex_pgid)
                elif raw_pid.endswith("\n"):
                    raise AssertionError(f"invalid fake Codex PID marker: {raw_pid!r}")

            sleeps: dict[str, tuple[int, int]] = {}
            if sleep_marker.is_file():
                raw_sleeps = sleep_marker.read_text(encoding="utf-8")
                complete = raw_sleeps if raw_sleeps.endswith("\n") else raw_sleeps.rsplit("\n", 1)[0]
                for line in complete.splitlines():
                    match = re.fullmatch(r"([1-9][0-9]*)\t([^\t]+)", line)
                    if match is None:
                        raise AssertionError(f"invalid monitor sleep marker: {line!r}")
                    sleep_pid = int(match.group(1))
                    sleep_pgid = record_owned_process(sleep_pid, session_id)
                    if sleep_pgid is not None:
                        sleeps[match.group(2)] = (sleep_pid, sleep_pgid)
            return codex_info, sleeps

        def owned_group_alive(pgid: int, session_id: int) -> bool:
            for pid in fixture_groups.get(pgid, ()):
                try:
                    if os.getsid(pid) == session_id and os.getpgid(pid) == pgid:
                        return True
                except ProcessLookupError:
                    continue
                except PermissionError as exc:
                    raise AssertionError(
                        f"cannot inspect fixture process group {pgid}: {exc}"
                    ) from exc
            return False

        def cleanup_fixture(session_id: int) -> list[str]:
            failures: list[str] = []
            if wrapped is None:
                return failures
            try:
                read_announced_groups(session_id)
            except (OSError, UnicodeError, AssertionError) as exc:
                failures.append(f"announcement discovery failed: {exc}")

            def live_groups() -> list[int]:
                result = []
                for pgid in sorted(fixture_groups):
                    if pgid == os.getpgrp():
                        failures.append(f"refused to signal current process group {pgid}")
                        continue
                    try:
                        if owned_group_alive(pgid, session_id):
                            result.append(pgid)
                    except AssertionError as exc:
                        failures.append(str(exc))
                return result

            for pgid in live_groups():
                try:
                    os.killpg(pgid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                except PermissionError as exc:
                    failures.append(f"TERM fixture process group {pgid} failed: {exc}")

            term_deadline = time.monotonic() + 1.0
            survivors = live_groups()
            while survivors and time.monotonic() < term_deadline:
                time.sleep(0.01)
                survivors = live_groups()
            for pgid in survivors:
                try:
                    os.killpg(pgid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                except PermissionError as exc:
                    failures.append(f"KILL fixture process group {pgid} failed: {exc}")

            kill_deadline = time.monotonic() + 1.0
            survivors = live_groups()
            while survivors and time.monotonic() < kill_deadline:
                time.sleep(0.01)
                survivors = live_groups()
            if survivors:
                failures.append(f"fixture process groups survived cleanup: {survivors}")

            try:
                wrapped.wait(timeout=1)
            except subprocess.TimeoutExpired:
                failures.append("wrapper wait exceeded cleanup deadline")
                try:
                    wrapped.kill()
                except ProcessLookupError:
                    pass
                except PermissionError as exc:
                    failures.append(f"direct wrapper KILL failed: {exc}")
                try:
                    wrapped.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    failures.append("wrapper remained alive after direct KILL")

            try:
                wrapped.communicate(timeout=1)
            except subprocess.TimeoutExpired:
                failures.append("captured stderr did not reach EOF during cleanup")
                if wrapped.stderr is not None:
                    wrapped.stderr.close()
            return failures

        try:
            wrapped = subprocess.Popen(
                [
                    real_bash, str(wrapper), "-C", str(work), "-s", "workspace-write",
                    "-m", "gpt-wrapper", "verify monitor cleanup",
                ],
                cwd=work,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
            session_id = wrapped.pid
            wrapper_pgid = record_owned_process(wrapped.pid, session_id)
            if wrapper_pgid != wrapped.pid:
                raise AssertionError(
                    f"wrapper did not own its fixture session/process group: {wrapper_pgid}"
                )

            setup_deadline = time.monotonic() + 5.0
            ready = None
            while time.monotonic() < setup_deadline:
                codex_info, sleeps = read_announced_groups(session_id)
                heartbeat = sleeps.get("1")
                watchdog = sleeps.get("30")
                if codex_info is not None and heartbeat is not None and watchdog is not None:
                    groups = {
                        wrapper_pgid,
                        codex_info[1],
                        heartbeat[1],
                        watchdog[1],
                    }
                    if len(groups) != 4:
                        raise AssertionError(
                            "wrapper, Codex, heartbeat, and watchdog did not own distinct groups: "
                            f"{sorted(groups)}"
                        )
                    if all(owned_group_alive(pgid, session_id) for pgid in groups):
                        ready = (codex_info, heartbeat, watchdog)
                        break
                if wrapped.poll() is not None:
                    raise AssertionError(
                        f"wrapper exited during monitor setup with code {wrapped.returncode}"
                    )
                time.sleep(0.01)
            if ready is None:
                sleep_detail = sleep_marker.read_text(encoding="utf-8") if sleep_marker.exists() else ""
                raise AssertionError(
                    "monitor setup did not announce live Codex/heartbeat=1/watchdog=30 "
                    f"within 5 seconds: {sleep_detail!r}"
                )

            release_marker.write_bytes(b"release\n")
            try:
                _stdout, stderr = wrapped.communicate(timeout=5)
            except subprocess.TimeoutExpired as exc:
                raise AssertionError(
                    "wrapper completion or captured stderr EOF exceeded 5 seconds "
                    f"after release (returncode={wrapped.poll()})"
                ) from exc
            if wrapped.returncode != 0:
                raise AssertionError(stderr.decode("utf-8", errors="replace"))
            read_announced_groups(session_id)
            survivors = [
                pgid
                for pgid in sorted(fixture_groups)
                if owned_group_alive(pgid, session_id)
            ]
            if survivors:
                raise AssertionError(
                    f"wrapper returned while fixture process groups remained alive: {survivors}"
                )
        except BaseException as exc:
            session_id = wrapped.pid if wrapped is not None else -1
            cleanup_failures = cleanup_fixture(session_id)
            if cleanup_failures:
                raise AssertionError(
                    f"monitor regression failed ({exc}); cleanup failed: "
                    + "; ".join(cleanup_failures)
                ) from exc
            raise


def self_test() -> int:
    monitor_descendant_regression()
    with tempfile.TemporaryDirectory() as raw_tmp:
        work = pathlib.Path(raw_tmp)
        devlyn = work / ".devlyn"
        devlyn.mkdir()
        prompt = devlyn / "implement.prompt.0"
        prompt.write_text("do the task\n", encoding="utf-8")
        session = devlyn / "implement.worker-session.0.jsonl"
        session.write_text('{"type":"thread.started"}\n', encoding="utf-8")
        receipt = devlyn / "implement.invocation.0.json"
        argv = [
            "--json", "-C", str(work), "-s", "workspace-write", "-m", "gpt-test",
            "-c", "sandbox_workspace_write.network_access=false", "do the task",
        ]
        start_receipt(work, receipt, "rs-receipt", "implement", 0, str(prompt), str(session), argv)
        finish_receipt(work, receipt, 0)
        bound = validate_receipt(
            work, receipt, run_id="rs-receipt", phase="implement", round_=0,
            model="gpt-test", prompt_sha256=sha256(prompt.read_bytes()), session_path=session,
        )
        assert bound["sandbox"] == "workspace-write" and bound["exit_code"] == 0
        original_session = session.read_bytes()
        original_receipt = receipt.read_bytes()
        reroute = "model rerouted: gpt-test -> another-model (Policy)"
        cases = [
            ({"type": "item.completed", "item": {"type": "error", "message": reroute}}, True),
            ({"type": "item.completed", "item": {"type": "agent_message", "text": reroute}}, False),
            ({"type": "item.completed", "item": {"type": "command_execution", "aggregated_output": reroute}}, False),
            ({"type": "item.completed", "item": {"type": "error", "message": "recoverable tool error"}}, False),
        ]
        cases.append(({"type": "item.completed", "item": {
            "type": "agent_message", "text": "ordinary \u2028 \u2029 \u0085 message",
        }}, False))
        for event, blocked in cases:
            raw = original_session + (json.dumps(event, ensure_ascii=False) + '\n{"type":"turn.completed"}\n').encode()
            session.write_bytes(raw)
            receipt.unlink()
            start_receipt(work, receipt, "rs-receipt", "implement", 0, str(prompt), str(session), argv)
            finish_receipt(work, receipt, 0)
            sealed = receipt.read_bytes()
            try:
                validate_receipt(work, receipt, run_id="rs-receipt", phase="implement", round_=0,
                                 model="gpt-test", prompt_sha256=sha256(prompt.read_bytes()), session_path=session)
            except ReceiptError as exc:
                assert blocked and "reported model reroute" in str(exc), str(exc)
            else:
                assert not blocked, "native reroute followed by success was accepted"
            validate_receipt_artifacts(work, receipt, run_id="rs-receipt", phase="implement")
            assert receipt.read_bytes() == sealed and session.read_bytes() == raw
        for malformed in (b'{broken\n', b'null\n', b'{"type":"item.completed","type":"ignored"}\n'):
            session.write_bytes(malformed)
            receipt.unlink()
            start_receipt(work, receipt, "rs-receipt", "implement", 0, str(prompt), str(session), argv)
            finish_receipt(work, receipt, 0)
            try:
                validate_receipt(work, receipt, run_id="rs-receipt", phase="implement", round_=0,
                                 model="gpt-test", prompt_sha256=sha256(prompt.read_bytes()), session_path=session)
            except ReceiptError:
                pass
            else:
                raise AssertionError("malformed worker event was accepted")
            validate_receipt_artifacts(work, receipt, run_id="rs-receipt", phase="implement")
        session.write_bytes(original_session)
        receipt.write_bytes(original_receipt)
        plan_prompt = devlyn / "plan.prompt.0"
        plan_prompt.write_text("plan exactly\n", encoding="utf-8")
        plan_session = devlyn / "plan.worker-session.0.jsonl"
        plan_session.write_text('{"type":"thread.started"}\n', encoding="utf-8")
        plan_receipt = devlyn / "plan.invocation.0.json"
        plan_argv = [
            "--json", "-C", str(work), "-s", "workspace-write",
            "-m", "gpt-plan", "-c",
            "sandbox_workspace_write.network_access=false", "plan exactly",
        ]
        start_receipt(
            work, plan_receipt, "rs-receipt", "plan", 0,
            str(plan_prompt), str(plan_session), plan_argv,
        )
        finish_receipt(work, plan_receipt, 0)
        plan_bound = validate_receipt(
            work, plan_receipt, run_id="rs-receipt", phase="plan", round_=0,
            model="gpt-plan", prompt_sha256=sha256(plan_prompt.read_bytes()),
            session_path=plan_session,
        )
        assert plan_bound["sandbox"] == "workspace-write"
        try:
            loads_strict_json('{"run_id":"a","run_id":"b"}')
        except ValueError as exc:
            assert "duplicate JSON key" in str(exc)
        else:
            raise AssertionError("duplicate invocation receipt key was accepted")
        try:
            start_receipt(
                work, devlyn / "cleanup.invocation.0.json", "rs-receipt", "cleanup", 0,
                str(prompt), str(devlyn / "cleanup.worker-session.0.jsonl"),
                ["--json", "--dangerously-bypass-approvals-and-sandbox", "-s", "danger-full-access",
                 "-m", "gpt-test", "do the task"],
            )
        except ReceiptError as exc:
            assert "forbidden Codex bypass flag" in str(exc)
        else:
            raise AssertionError("Codex bypass flag was accepted")
        cleanup_prompt = devlyn / "cleanup.prompt.0"
        cleanup_prompt.write_text("do the task\n", encoding="utf-8")
        try:
            start_receipt(
                work, devlyn / "cleanup.invocation.0.json", "rs-receipt", "cleanup", 0,
                str(cleanup_prompt), str(devlyn / "cleanup.worker-session.0.jsonl"),
                ["--json", "-C", str(work), "-s", "workspace-write", "-m", "gpt-test",
                 "do the task"],
            )
        except ReceiptError as exc:
            assert "requires exactly one -c sandbox_workspace_write.network_access=false" in str(exc)
        else:
            raise AssertionError("Codex cleanup accepted implicit network capability")
        try:
            start_receipt(
                work, devlyn / "cleanup.invocation.0.json", "rs-receipt", "cleanup", 0,
                str(cleanup_prompt), str(devlyn / "cleanup.worker-session.0.jsonl"),
                ["--json", "-C", str(work), "-s", "workspace-write", "-m", "gpt-test",
                 "-c", "sandbox_workspace_write.network_access=true", "do the task"],
            )
        except ReceiptError as exc:
            assert "requires exactly one -c sandbox_workspace_write.network_access=false" in str(exc)
        else:
            raise AssertionError("Codex cleanup accepted enabled network capability")
        try:
            start_receipt(
                work, devlyn / "cleanup.invocation.0.json", "rs-receipt", "cleanup", 0,
                str(cleanup_prompt), str(devlyn / "cleanup.worker-session.0.jsonl"),
                ["--json", "-s", "danger-full-access", "-m", "gpt-test", "do the task"],
            )
        except ReceiptError as exc:
            assert "must remain workspace-write" in str(exc)
        else:
            raise AssertionError("widened Codex sandbox was accepted")
        try:
            start_receipt(
                work, devlyn / "cleanup.invocation.0.json", "rs-receipt", "cleanup", 0,
                str(cleanup_prompt), str(devlyn / "cleanup.worker-session.0.jsonl"),
                ["--json", "-C", str(devlyn), "-s", "workspace-write", "-m", "gpt-test",
                 "-c", "sandbox_workspace_write.network_access=false", "do the task"],
            )
        except ReceiptError as exc:
            assert "workdir does not match" in str(exc)
        else:
            raise AssertionError("Codex invocation accepted a different working directory")
        session.write_text('{"type":"thread.started","mutated":true}\n', encoding="utf-8")
        try:
            validate_receipt(
                work, receipt, run_id="rs-receipt", phase="implement", round_=0,
                model="gpt-test", prompt_sha256=sha256(prompt.read_bytes()), session_path=session,
            )
        except ReceiptError as exc:
            assert "worker-session digest mismatch" in str(exc)
        else:
            raise AssertionError("mutated worker session was accepted")

        build_prompt = devlyn / "build_gate.prompt.0"
        build_prompt.write_text("verify the task\n", encoding="utf-8")
        build_session = devlyn / "build_gate.worker-session.0.jsonl"
        build_receipt = devlyn / "build_gate.invocation.0.json"
        try:
            start_receipt(
                work, build_receipt, "rs-wrapper", "build_gate", 0,
                str(build_prompt), str(build_session),
                ["--json", "-C", str(work), "-s", "workspace-write", "-m", "gpt-wrapper",
                 "verify the task"],
            )
        except ReceiptError as exc:
            assert "requires exactly one -c sandbox_workspace_write.network_access=true" in str(exc)
        else:
            raise AssertionError("Codex build_gate accepted missing network capability")
        try:
            start_receipt(
                work, build_receipt, "rs-wrapper", "build_gate", 0,
                str(build_prompt), str(build_session),
                ["--json", "-C", str(work), "-s", "workspace-write", "-m", "gpt-wrapper",
                 "-c", "sandbox_workspace_write.network_access=true",
                 "-c", "sandbox_workspace_write.network_access=false",
                 "verify the task"],
            )
        except ReceiptError as exc:
            assert "duplicate network overrides are forbidden" in str(exc)
        else:
            raise AssertionError("Codex build_gate accepted duplicate network capabilities")
        for alternate in (
            "sandbox_workspace_write={network_access=true}",
            '"sandbox_workspace_write".network_access=true',
        ):
            try:
                start_receipt(
                    work, build_receipt, "rs-wrapper", "build_gate", 0,
                    str(build_prompt), str(build_session),
                    ["--json", "-C", str(work), "-s", "workspace-write", "-m", "gpt-wrapper",
                     "-c", "sandbox_workspace_write.network_access=true",
                     "--config=" + alternate, "verify the task"],
                )
            except ReceiptError as exc:
                assert "alternate, table, missing, and duplicate" in str(exc)
            else:
                raise AssertionError(f"Codex build_gate accepted alternate override: {alternate}")
        glued_prompt = devlyn / "build_gate.prompt.1"
        glued_prompt.write_text("verify glued config\n", encoding="utf-8")
        glued_session = devlyn / "build_gate.worker-session.1.jsonl"
        glued_session.write_text('{"type":"thread.started"}\n', encoding="utf-8")
        glued_receipt = devlyn / "build_gate.invocation.1.json"
        start_receipt(
            work, glued_receipt, "rs-glued", "build_gate", 1,
            str(glued_prompt), str(glued_session),
            ["--json", "-C", str(work), "-s", "workspace-write", "-m", "gpt-wrapper",
             "-c=sandbox_workspace_write.network_access=true", "verify glued config"],
        )
        finish_receipt(work, glued_receipt, 0)
        assert validate_receipt(
            work, glued_receipt, run_id="rs-glued", phase="build_gate", round_=1,
            model="gpt-wrapper", prompt_sha256=sha256(glued_prompt.read_bytes()),
            session_path=glued_session,
        )["sandbox_network_access"] is True
        fake_codex = work / "fake-codex"
        fake_codex.write_text(
            "#!/usr/bin/env bash\n"
            "touch native-started\n"
            "printf '%s\\n' '{\"type\":\"thread.started\"}'\n",
            encoding="utf-8",
        )
        fake_codex.chmod(0o755)
        wrapper = pathlib.Path(__file__).with_name("codex-monitored.sh")
        widened = subprocess.run(
            [
                "bash", str(wrapper), "-C", str(work), "-s", "danger-full-access",
                "-m", "gpt-wrapper", "verify the task",
            ],
            cwd=work,
            env={**os.environ, "CODEX_BIN": str(fake_codex)},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        assert widened.returncode == 64
        assert b"forbidden Codex sandbox" in widened.stderr
        assert widened.stdout == b""
        env = os.environ.copy()
        env.update({
            "CODEX_BIN": str(fake_codex),
            "CODEX_MONITORED_HEARTBEAT": "1",
            "DEVLYN_INVOCATION_RUN_ID": "rs-wrapper",
            "DEVLYN_INVOCATION_PHASE": "build_gate",
            "DEVLYN_INVOCATION_ROUND": "0",
            "DEVLYN_INVOCATION_WORKDIR": str(work),
            "DEVLYN_INVOCATION_PROMPT_FILE": str(build_prompt),
            "DEVLYN_INVOCATION_SESSION_FILE": str(build_session),
            "DEVLYN_INVOCATION_RECEIPT": str(build_receipt),
        })
        with build_session.open("wb") as stdout:
            missing_json = subprocess.run(
                ["bash", str(wrapper), "-C", str(work), "-s", "workspace-write",
                 "-m", "gpt-wrapper", "-c",
                 "sandbox_workspace_write.network_access=true", "verify the task"],
                cwd=work, env=env, stdout=stdout, stderr=subprocess.PIPE,
                check=False,
            )
        assert missing_json.returncode == 64 and b"requires --json" in missing_json.stderr, missing_json.stderr
        assert build_session.read_bytes() == b"" and not (work / "native-started").exists()
        assert not build_receipt.exists()
        with build_session.open("wb") as stdout:
            wrapped = subprocess.run(
                [
                    "bash", str(wrapper), "--json", "-C", str(work), "-s", "workspace-write",
                    "-m", "gpt-wrapper", "-c",
                    "sandbox_workspace_write.network_access=true", "verify the task",
                ],
                cwd=work,
                env=env,
                stdout=stdout,
                stderr=subprocess.PIPE,
                check=False,
            )
        assert wrapped.returncode == 0, wrapped.stderr.decode("utf-8", errors="replace")
        wrapper_bound = validate_receipt(
            work, build_receipt, run_id="rs-wrapper", phase="build_gate", round_=0,
            model="gpt-wrapper", prompt_sha256=sha256(build_prompt.read_bytes()),
            session_path=build_session,
        )
        assert wrapper_bound["exit_code"] == 0
        assert wrapper_bound["sandbox_network_access"] is True

        wrapped_plan_prompt = devlyn / "plan.prompt.1"
        wrapped_plan_prompt.write_text("plan through wrapper\n", encoding="utf-8")
        wrapped_plan_session = devlyn / "plan.worker-session.1.jsonl"
        wrapped_plan_receipt = devlyn / "plan.invocation.1.json"
        plan_env = os.environ.copy()
        plan_env.update({
            "CODEX_BIN": str(fake_codex),
            "CODEX_MONITORED_HEARTBEAT": "1",
            "DEVLYN_INVOCATION_RUN_ID": "rs-plan-wrapper",
            "DEVLYN_INVOCATION_PHASE": "plan",
            "DEVLYN_INVOCATION_ROUND": "1",
            "DEVLYN_INVOCATION_WORKDIR": str(work),
            "DEVLYN_INVOCATION_PROMPT_FILE": str(wrapped_plan_prompt),
            "DEVLYN_INVOCATION_SESSION_FILE": str(wrapped_plan_session),
            "DEVLYN_INVOCATION_RECEIPT": str(wrapped_plan_receipt),
        })
        with wrapped_plan_session.open("wb") as stdout:
            wrapped_plan = subprocess.run(
                [
                    "bash", str(wrapper), "--json", "-C", str(work),
                    "-s", "workspace-write", "-m", "gpt-plan-wrapper",
                    "-c", "sandbox_workspace_write.network_access=false",
                    "plan through wrapper",
                ],
                cwd=work,
                env=plan_env,
                stdout=stdout,
                stderr=subprocess.PIPE,
                check=False,
            )
        assert wrapped_plan.returncode == 0, wrapped_plan.stderr.decode(
            "utf-8", errors="replace",
        )
        plan_wrapper_bound = validate_receipt(
            work, wrapped_plan_receipt, run_id="rs-plan-wrapper", phase="plan",
            round_=1, model="gpt-plan-wrapper",
            prompt_sha256=sha256(wrapped_plan_prompt.read_bytes()),
            session_path=wrapped_plan_session,
        )
        assert plan_wrapper_bound["exit_code"] == 0
        print(
            "PASS invocation receipt identity, prompt/session digest, bypass guard, "
            "phase-scoped BUILD_GATE network capability, and monitored-wrapper "
            "integration including PLAN"
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    subparsers = parser.add_subparsers(dest="action")
    start = subparsers.add_parser("start")
    start.add_argument("--workdir", required=True)
    start.add_argument("--receipt", required=True)
    start.add_argument("--run-id", required=True)
    start.add_argument("--phase", choices=sorted(PHASES), required=True)
    start.add_argument("--round", type=int, required=True)
    start.add_argument("--prompt-file", required=True)
    start.add_argument("--session-file", required=True)
    start.add_argument("argv", nargs=argparse.REMAINDER)
    finish = subparsers.add_parser("finish")
    finish.add_argument("--workdir", required=True)
    finish.add_argument("--receipt", required=True)
    finish.add_argument("--exit-code", type=int, required=True)
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    try:
        if args.action == "start":
            argv = args.argv[1:] if args.argv[:1] == ["--"] else args.argv
            start_receipt(
                pathlib.Path(args.workdir).resolve(), pathlib.Path(args.receipt), args.run_id,
                args.phase, args.round, args.prompt_file, args.session_file, argv,
            )
        elif args.action == "finish":
            work = pathlib.Path(args.workdir).resolve()
            receipt_path = pathlib.Path(args.receipt)
            if not receipt_path.is_absolute():
                receipt_path = work / receipt_path
            finish_receipt(
                work, receipt_path, args.exit_code,
            )
        else:
            parser.error("an action is required")
    except (OSError, UnicodeError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
