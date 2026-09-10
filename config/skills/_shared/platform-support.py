#!/usr/bin/env python3
"""Native lock, argv, process and UTF-8 boundaries shared by harness callers."""
from __future__ import annotations

import contextlib
import errno
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time


def configure_utf8():
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="strict")


@contextlib.contextmanager
def file_lock(path, *, blocking=False):
    with Path(path).open("a+b") as handle:
        if os.name == "nt":
            import msvcrt
            if os.fstat(handle.fileno()).st_size == 0:
                handle.write(b"\0")
                handle.flush()
            while True:
                handle.seek(0)
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError as exc:
                    # CRT maps ERROR_LOCK_VIOLATION to EACCES (winerror may be absent).
                    contended = exc.errno == errno.EACCES and getattr(exc, "winerror", None) in (None, 33)
                    if not contended:
                        raise
                    if not blocking:
                        raise BlockingIOError(errno.EAGAIN, "lock occupied", str(path)) from exc
                    time.sleep(0.05)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def native_argv(argv):
    """Resolve supported npm engine shims to their package's Node bin, never cmd /c."""
    if os.name != "nt":
        return list(argv)
    binary = shutil.which(argv[0])
    if binary is None:
        raise FileNotFoundError(f"executable unavailable: {argv[0]}")
    shim = Path(binary)
    if shim.suffix.lower() not in {".cmd", ".bat"}:
        return [binary, *argv[1:]]
    packages = {"codex": "@openai/codex", "claude": "@anthropic-ai/claude-code"}
    package = packages.get(shim.stem.lower())
    if shim.suffix.lower() != ".cmd" or package is None:
        raise OSError(f"unsupported native command shim: {shim}")
    root = (shim.parent.parent if shim.parent.name == ".bin" else shim.parent / "node_modules") / package
    try:
        manifest = json.loads((root / "package.json").read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise OSError(f"invalid npm engine manifest: {shim}") from exc
    if not isinstance(manifest, dict):
        raise OSError(f"invalid npm engine manifest: {shim}")
    entry = manifest.get("bin")
    entry = entry.get(shim.stem.lower()) if isinstance(entry, dict) else entry
    if manifest.get("name") != package or not isinstance(entry, str):
        raise OSError(f"invalid npm engine bin: {shim}")
    target = (root / entry).resolve(strict=True)
    if not target.is_relative_to(root.resolve()) or target.suffix not in {".js", ".cjs", ".mjs"}:
        raise OSError(f"unsupported npm engine bin: {target}")
    raw = shim.read_text(encoding="utf-8")
    matches = re.findall(r'"%_prog%"\s+"%dp0%\\([^"\r\n]+)"\s+%\*', raw)
    if len(matches) != 1 or (shim.parent / matches[0]).resolve() != target:
        raise OSError(f"unrecognized npm engine shim: {shim}")
    node = shim.parent / "node.exe"
    binary = str(node) if node.is_file() else shutil.which("node.exe")
    if binary is None:
        raise FileNotFoundError(f"node.exe unavailable for {shim}")
    return [binary, str(target), *argv[1:]]


def terminate_tree(child):
    if os.name == "nt":
        if child.poll() is not None:
            return
        # child.pid is a native PID, including when this interpreter runs under Git Bash.
        killed = subprocess.run(["taskkill.exe", "/PID", str(child.pid), "/T", "/F"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if killed.returncode:
            raise OSError(f"taskkill failed for native PID {child.pid}: {killed.stderr!r}")
        child.wait(timeout=5)
        return
    try:
        os.killpg(child.pid, signal.SIGTERM)
    except ProcessLookupError:
        child.wait()
        return
    # Reap the leader and retain the grace period for its surviving descendants.
    deadline = time.monotonic() + 5
    try:
        child.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass  # The leader also needs the final group KILL below.
    time.sleep(max(0, deadline - time.monotonic()))
    try:
        os.killpg(child.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass  # Every member already exited during the grace period.
    child.wait()


def run_process(argv, stdin, seconds, *, heartbeat=0):
    child = subprocess.Popen(argv, stdin=stdin, start_new_session=os.name != "nt")
    started = time.monotonic()
    next_heartbeat = started + heartbeat
    previous = {}

    def interrupted(signum, _frame):
        raise SystemExit(128 + signum)

    try:
        for sig in (signal.SIGTERM, signal.SIGINT):
            previous[sig] = signal.signal(sig, interrupted)
        if heartbeat:
            print(f"[codex-monitored] codex pid={child.pid}", file=sys.stderr, flush=True)
        while True:
            try:
                return child.wait(timeout=0.1)
            except subprocess.TimeoutExpired:
                now = time.monotonic()
                if seconds and now - started >= seconds:
                    if heartbeat:
                        print(f"[codex-monitored] timeout: elapsed={int(now-started)}s limit={seconds}s", file=sys.stderr, flush=True)
                    return 124
                if heartbeat and now >= next_heartbeat:
                    print(f"[codex-monitored] heartbeat: elapsed={int(now-started)}s", file=sys.stderr, flush=True)
                    next_heartbeat = now + heartbeat
    finally:
        try:
            terminate_tree(child)
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)
