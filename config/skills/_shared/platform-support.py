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
import stat
import subprocess
import sys
import time


def configure_utf8():
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="strict")


def open_stdin(path):
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NONBLOCK", 0))
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        raise ValueError(f"stdin file is not a regular file: {path}")
    return os.fdopen(fd, "rb")


@contextlib.contextmanager
def file_lock(path, *, blocking=False):
    with Path(path).open("a+b") as handle:
        if os.name == "nt":
            import msvcrt
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


def system_exit_code(code):
    # CPython SystemExit uses signed C long (32 bits on Windows), unlike DWORD.
    return code - 0x100000000 if os.name == "nt" and code >= 0x80000000 else code


if os.name == "nt":
    import ctypes
    from ctypes import wintypes
    import msvcrt

    class _BasicLimits(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong),
                    ("PerJobUserTimeLimit", ctypes.c_longlong),
                    ("LimitFlags", wintypes.DWORD),
                    ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t),
                    ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t),
                    ("PriorityClass", wintypes.DWORD),
                    ("SchedulingClass", wintypes.DWORD)]

    class _ExtendedLimits(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", _BasicLimits),
                    ("IoInfo", ctypes.c_ulonglong * 6),
                    ("ProcessMemoryLimit", ctypes.c_size_t),
                    ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t),
                    ("PeakJobMemoryUsed", ctypes.c_size_t)]

    class _JobAccounting(ctypes.Structure):
        _fields_ = [("TotalUserTime", ctypes.c_longlong),
                    ("TotalKernelTime", ctypes.c_longlong),
                    ("ThisPeriodTotalUserTime", ctypes.c_longlong),
                    ("ThisPeriodTotalKernelTime", ctypes.c_longlong),
                    ("TotalPageFaultCount", wintypes.DWORD),
                    ("TotalProcesses", wintypes.DWORD),
                    ("ActiveProcesses", wintypes.DWORD),
                    ("TotalTerminatedProcesses", wintypes.DWORD)]

    def _checked(result, function, _args):
        if not result:
            error = ctypes.get_last_error()
            raise ctypes.WinError(error, f"{function.__name__}: {ctypes.FormatError(error)}")
        return result

    _kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    for _name, _args, _result in (
        ("CreateJobObjectW", [ctypes.c_void_p, wintypes.LPCWSTR], wintypes.HANDLE),
        ("SetInformationJobObject", [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD], wintypes.BOOL),
        ("QueryInformationJobObject", [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p], wintypes.BOOL),
        ("AssignProcessToJobObject", [wintypes.HANDLE, wintypes.HANDLE], wintypes.BOOL),
        ("TerminateJobObject", [wintypes.HANDLE, wintypes.UINT], wintypes.BOOL),
        ("GetCurrentProcess", [], wintypes.HANDLE),
        ("DuplicateHandle", [wintypes.HANDLE, wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.HANDLE), wintypes.DWORD, wintypes.BOOL, wintypes.DWORD], wintypes.BOOL),
        ("CloseHandle", [wintypes.HANDLE], wintypes.BOOL),
        ("PeekNamedPipe", [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p], wintypes.BOOL),
    ):
        _function = getattr(_kernel, _name)
        _function.argtypes, _function.restype, _function.errcheck = _args, _result, _checked

    def _read_control(fd, count):
        deadline = time.monotonic() + 10
        data = b""
        while len(data) < count:
            available = wintypes.DWORD()
            _kernel.PeekNamedPipe(msvcrt.get_osfhandle(fd), None, 0, None, ctypes.byref(available), None)
            if available.value:
                data += os.read(fd, min(count - len(data), available.value))
            elif time.monotonic() >= deadline:
                raise OSError("Windows job launch handshake timed out")
            else:
                time.sleep(0.01)
        return data

    class _WindowsJob:
        def __init__(self):
            self.handle = None
            self.child = None
            self.creating = False
            self.interrupted_signal = None

        def start(self, argv, stdin):
            self.handle = _kernel.CreateJobObjectW(None, None)
            limits = _ExtendedLimits()
            limits.BasicLimitInformation.LimitFlags = 0x2000  # KILL_ON_JOB_CLOSE; no breakaway.
            _kernel.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits))
            with contextlib.ExitStack() as controls, contextlib.ExitStack() as inherited_handles:
                inherited_job = wintypes.HANDLE()
                current = _kernel.GetCurrentProcess()
                _kernel.DuplicateHandle(current, self.handle, current, ctypes.byref(inherited_job), 0, True, 2)
                inherited_handles.callback(_kernel.CloseHandle, inherited_job)
                ready_read, ready_write = os.pipe()
                controls.callback(os.close, ready_read); inherited_handles.callback(os.close, ready_write)
                allow_read, allow_write = os.pipe()
                inherited_handles.callback(os.close, allow_read); controls.callback(os.close, allow_write)
                inherited = [inherited_job.value, msvcrt.get_osfhandle(ready_write), msvcrt.get_osfhandle(allow_read)]
                for handle in inherited[1:]:
                    os.set_handle_inheritable(handle, True)
                startup = subprocess.STARTUPINFO()
                startup.lpAttributeList = {"handle_list": inherited}
                command = [sys.executable, "-I", "-S", str(Path(__file__).resolve()), "--job-bootstrap",
                           str(inherited[0]), str(inherited[2]), str(inherited[1]), *argv]
                # Retain the Popen object even if __init__ raises after native creation.
                self.child = subprocess.Popen.__new__(subprocess.Popen)
                self.creating = True
                try:
                    self.child.__init__(command, stdin=stdin, startupinfo=startup, close_fds=True)
                finally:
                    self.creating = False
                if self.interrupted_signal is not None:
                    raise SystemExit(128 + self.interrupted_signal)
                inherited_handles.close()
                if _read_control(ready_read, 1) != b"R":
                    raise OSError("Windows job enrollment did not report ready")
                os.write(allow_write, b"G")
                self.target_pid = int.from_bytes(_read_control(ready_read, 4), "little")
            return self.child

        def terminate(self):
            try:
                # Stop startup first so no new enrollment/dispatch can race job quiescence.
                if self.child is not None and getattr(self.child, "_child_created", False):
                    try:
                        if self.child.poll() is None:
                            self.child.kill()
                        self.child.wait(timeout=5)
                    finally:
                        self.child._handle.Close()
            finally:
                if self.handle is not None:
                    try:
                        _kernel.TerminateJobObject(self.handle, 1)
                        deadline = time.monotonic() + 5
                        accounting = _JobAccounting()
                        while True:
                            _kernel.QueryInformationJobObject(self.handle, 1, ctypes.byref(accounting), ctypes.sizeof(accounting), None)
                            if accounting.ActiveProcesses == 0:
                                break
                            if time.monotonic() >= deadline:
                                raise OSError("Windows job teardown did not reach quiescence")
                            time.sleep(0.01)
                    finally:
                        _kernel.CloseHandle(self.handle)

    def _job_bootstrap(argv):
        job, allow, ready = map(int, argv[:3])
        with contextlib.ExitStack() as handles:
            allow_fd = msvcrt.open_osfhandle(allow, os.O_RDONLY | os.O_BINARY)
            handles.callback(os.close, allow_fd)
            ready_fd = msvcrt.open_osfhandle(ready, os.O_WRONLY | os.O_BINARY)
            handles.callback(os.close, ready_fd)
            try:
                _kernel.AssignProcessToJobObject(job, _kernel.GetCurrentProcess())
            finally:
                _kernel.CloseHandle(job)
            os.write(ready_fd, b"R")
            if _read_control(allow_fd, 1) != b"G":
                raise OSError("Windows job launch was not authorized")
            with subprocess.Popen(argv[3:], stdin=sys.stdin.buffer, close_fds=True) as target:
                os.write(ready_fd, target.pid.to_bytes(4, "little"))
                return target.wait()


def terminate_tree(child, job=None):
    if job is not None:
        job.terminate()
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
    child = None
    job = _WindowsJob() if os.name == "nt" else None
    previous = {}

    def interrupted(signum, _frame):
        # CPython stores the native handle only after CreateProcess's finally block.
        if job is not None and job.creating:
            job.interrupted_signal = signum
            return
        raise SystemExit(128 + signum)

    try:
        for sig in (signal.SIGTERM, signal.SIGINT):
            previous[sig] = signal.signal(sig, interrupted)
        child = job.start(argv, stdin) if job is not None else subprocess.Popen(argv, stdin=stdin, start_new_session=True)
        started = time.monotonic()
        next_heartbeat = started + heartbeat
        if heartbeat:
            print(f"[codex-monitored] codex pid={job.target_pid if job is not None else child.pid}", file=sys.stderr, flush=True)
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
            if job is not None or child is not None:
                terminate_tree(child, job)
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)


if __name__ == "__main__" and os.name == "nt":
    configure_utf8()
    try:
        if sys.argv[1:2] != ["--job-bootstrap"]:
            raise ValueError("expected internal Windows job bootstrap")
        code = _job_bootstrap(sys.argv[2:])
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        code = 2
    raise SystemExit(system_exit_code(code))
