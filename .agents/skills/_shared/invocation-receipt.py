#!/usr/bin/env python3
"""Dispatch `codex exec` for codex-monitored.sh: exact argv, an optional sealed prompt file, native process ownership."""
from __future__ import annotations

import runpy

import argparse
import hashlib
import json
import os
import pathlib
import re
import signal
import shutil
import subprocess
import sys
import tempfile
import time


PLATFORM = runpy.run_path(pathlib.Path(__file__).with_name("platform-support.py"))


class TransportError(ValueError):
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


def file_prompt_args(argv):
    """File mode accepts one explicit stdin prompt and no positional competitors."""
    values = {"-C", "--cd", "-s", "--sandbox", "-m", "--model", "-c", "--config",
              "-o", "--output-last-message", "--output-schema", "--color", "--enable",
              "--disable", "--add-dir"}
    flags = {"--json", "--ignore-user-config", "--ignore-rules", "--ephemeral",
             "--skip-git-repo-check", "--full-auto"}
    positional = []
    index = 0
    while index < len(argv):
        token = argv[index]
        if token in values:
            if index + 1 >= len(argv):
                raise TransportError(f"{token} requires a value")
            index += 2
        elif any(token.startswith(key + "=") for key in values) or token in flags:
            index += 1
        elif token == "--":
            positional.extend(argv[index + 1:])
            break
        elif token == "-" or not token.startswith("-"):
            positional.append(token)
            index += 1
        else:
            raise TransportError(f"unsupported Codex file-transport option: {token}")
    if positional != ["-"]:
        raise TransportError("file transport requires the sole prompt argument '-'; competing prompts are forbidden")


def prepare_transport(prompt_path, command, argv, seconds):
    path = pathlib.Path(prompt_path).resolve(strict=True)
    with PLATFORM["open_stdin"](path) as source:
        raw = source.read()
    record = {"schema_version": 1, "transport": "stdin-file",
              "prompt": {"path": str(path), "sha256": sha256(raw), "bytes": len(raw)},
              "command": command, "argv": argv, "timeout_sec": seconds,
              "status": "started", "exit_code": None}
    carrier = path.with_name(path.name + ".transport.json")
    if carrier.exists():
        raise TransportError(f"prompt transport already exists: {carrier}")
    stream = tempfile.TemporaryFile("w+b")
    try:
        stream.write(raw)
        stream.seek(0)
    except BaseException:
        stream.close()
        raise
    return stream, carrier, record


def write_transport(path, record):
    with path.open("xb") as stream:
        stream.write((json.dumps(record, sort_keys=True) + "\n").encode("utf-8"))


def finish_transport(path, exit_code):
    record = read_transport(path)
    if record.get("status") != "started":
        raise TransportError("prompt transport is not open")
    record.update(status="completed", exit_code=exit_code)
    atomic_write(path, record)


def read_transport(path: pathlib.Path) -> dict:
    try:
        value = loads_strict_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise TransportError(f"prompt transport is invalid: {exc}") from exc
    if not isinstance(value, dict):
        raise TransportError("prompt transport must contain an object")
    return value


def monitor_descendant_regression() -> None:
    if os.name == "nt":
        print("SKIP POSIX shell process-group fixture; test-windows-portability.py exercises native Node/Python trees")
        return
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
                key.startswith("DEVLYN_WATCHDOG_TEST_")
                or key.startswith("CODEX_MONITORED_")
                or key in {"CODEX_BLOCKED", "CODEX_REAL_BIN", "DEVLYN_CODEX_PROMPT_FILE"}
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
    if os.name == "nt":
        print("SKIP POSIX executable-shell wrapper fixture; native npm transport is covered by test-windows-portability.py")
        return 0
    with tempfile.TemporaryDirectory() as raw_tmp:
        work = pathlib.Path(raw_tmp)
        fake_codex = work / "fake-codex"
        fake_codex.write_text("#!/usr/bin/env bash\ntouch native-started\n", encoding="utf-8")
        fake_codex.chmod(0o755)
        wrapper = pathlib.Path(__file__).with_name("codex-monitored.sh")
        widened = subprocess.run(
            ["bash", str(wrapper), "-C", str(work), "-s", "danger-full-access", "-m", "gpt-wrapper", "verify the task"],
            cwd=work, env={**os.environ, "CODEX_BIN": str(fake_codex)},
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        assert widened.returncode == 64 and b"forbidden Codex sandbox" in widened.stderr, widened.stderr
        assert widened.stdout == b"" and not (work / "native-started").exists()
    print("PASS monitored-wrapper descendant cleanup and authority-widening refusal")
    return 0


def complete_dispatch(exit_code):
    prompt = os.environ.get("DEVLYN_CODEX_PROMPT_FILE")
    if prompt:
        path = pathlib.Path(prompt).resolve()
        finish_transport(path.with_name(path.name + ".transport.json"), exit_code)


def dispatch_codex(args):
    argv = args.argv[1:] if args.argv[:1] == ["--"] else args.argv
    command = [args.binary, "exec", *argv]
    actual = PLATFORM["native_argv"](command)
    prompt = os.environ.get("DEVLYN_CODEX_PROMPT_FILE")
    if prompt == "":
        raise TransportError("DEVLYN_CODEX_PROMPT_FILE must name a readable prompt file")
    stream, carrier, transport = None, None, None
    try:
        if prompt:
            file_prompt_args(argv)
            stream, carrier, transport = prepare_transport(prompt, command, actual, args.timeout)
        if transport is not None:
            write_transport(carrier, transport)
        if os.name != "nt":
            if stream is not None:
                os.dup2(stream.fileno(), 0)
            os.execvp(actual[0], actual)
        code = PLATFORM["run_process"](actual, stream if stream is not None else subprocess.DEVNULL,
                                       args.timeout, heartbeat=args.heartbeat)
        complete_dispatch(code)
        print(f"[codex-monitored] codex exited: code={code}", file=sys.stderr)
        return code
    finally:
        if stream is not None:
            stream.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    subparsers = parser.add_subparsers(dest="action")
    dispatch = subparsers.add_parser("dispatch")
    dispatch.add_argument("--binary", required=True)
    dispatch.add_argument("--timeout", type=int, required=True)
    dispatch.add_argument("--heartbeat", type=int, required=True)
    dispatch.add_argument("argv", nargs=argparse.REMAINDER)
    completed = subparsers.add_parser("complete-dispatch")
    completed.add_argument("--exit-code", type=int, required=True)
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    try:
        if args.action == "dispatch":
            return dispatch_codex(args)
        elif args.action == "complete-dispatch":
            complete_dispatch(args.exit_code)
        else:
            parser.error("an action is required")
    except (OSError, UnicodeError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    runpy.run_path(str(pathlib.Path(__file__).with_name("platform-support.py")))["configure_utf8"]()
    raise SystemExit(PLATFORM["system_exit_code"](main()))
