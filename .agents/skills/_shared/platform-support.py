#!/usr/bin/env python3
"""Native lock, argv, process and UTF-8 boundaries shared by harness callers."""
from __future__ import annotations

import contextlib
import errno
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import stat
import subprocess
import sys
import time


def managed_node():
    """The Node that runs devlyn-cli's own scripts: the app's override is authoritative, and an invalid one never
    falls back to PATH. Project and engine commands keep the session's own Node."""
    value = os.environ.get("DEVLYN_NODE")
    if value is None:
        return None
    node = Path(value)
    if not node.is_absolute() or not node.is_file() or not os.access(node, os.X_OK):
        raise OSError("DEVLYN_NODE must be an absolute path to an executable file")
    return value


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


SHIM_NODE = re.compile(r'IF EXIST "%(?:~dp0|dp0%)\\node\.exe"')
SHIM_RUN = re.compile(r'(?:"%_prog%"|"%~dp0\\node\.exe"|\bnode)\s+"%(?:~dp0|dp0%)\\([^"\r\n]+)"\s+%\*')
SHIM_SET = re.compile(r'(?im)^[ \t]*@?SET[ \t]+"?([^=" \t]+)=')
NPM_CLI = re.compile(r'SET "(NP[MX]_CLI_JS)=%~dp0\\([^"\r\n]+)"')


def native_argv(argv, cwd=None):
    """Resolve argv as Windows does, for a command that will run in cwd; a Node command shim runs its Node and script
    directly, never cmd /c; on macOS avoid kernel #! exec, whose process tree keeps kernel memory for each later
    #! exec until restart."""
    if sys.platform == "darwin":
        try:
            prefix = darwin_script_argv(argv[0], cwd or os.getcwd())
            return [*prefix, *argv[1:]] if prefix else list(argv)
        except (OSError, ValueError, TypeError, NotImplementedError, IndexError):
            return list(argv)  # Preserve CPython's PATH search and errors without a shell fallback.
    if os.name != "nt":
        return list(argv)
    binary = shutil.which(argv[0])
    if binary is None:
        raise FileNotFoundError(f"executable unavailable: {argv[0]}")
    shim = Path(binary)
    if shim.suffix.lower() not in {".cmd", ".bat"}:
        return [binary, *argv[1:]]
    node = shim.parent / "node.exe"
    node = str(node) if node.is_file() else shutil.which("node.exe")
    script = shim_script(shim, shim.read_text(encoding="utf-8", errors="replace"), node, cwd)
    if script is None:
        raise OSError(f"unsupported native command shim: {shim}; use argv with an explicit interpreter, such as node and the script")
    if node is None:
        raise FileNotFoundError(f"node.exe unavailable for {shim}")
    return [node, str(script.resolve(strict=True)), *argv[1:]]


def darwin_script_argv(program, cwd):
    """The argv prefix macOS would build for a safely resolved script with a native interpreter, else None.

    Search with CPython's os.get_exec_path(), including os.defpath when PATH is unset. A CPU-compatible
    interpreter with an otherwise damaged image fails against the interpreter instead of retrying PATH.
    The interpreter path is executed as it is at exec time: replacing it requires write access that
    already lets the writer run code as the user. A set-id replacement owned by another user cannot
    raise privilege; only root can create root-owned set-id files. Quarantined scripts are declined;
    other exec-only MAC policies that permit reading but deny executing the script are not consulted.
    """
    cpu = {"arm64": 0x0100000c, "x86_64": 0x01000007}.get(platform.machine())
    if cpu is None:
        return None
    subtypes = (0, 1, 2) if cpu == 0x0100000c else (3,)
    entries = [None] if "/" in program else os.get_exec_path()
    with contextlib.ExitStack() as handles:
        try:
            cwd_fd = os.open(cwd, os.O_RDONLY | os.O_DIRECTORY)
            handles.callback(os.close, cwd_fd)
            for entry in entries:
                if entry is not None and len(os.fsencode(entry)) + len(os.fsencode(program)) + 2 > 1024:
                    return None
                candidate = program if entry is None else os.path.join(entry, program)
                try:
                    mode = os.stat(candidate, dir_fd=cwd_fd).st_mode
                except (FileNotFoundError, NotADirectoryError):
                    continue
                if not stat.S_ISREG(mode) or not os.access(candidate, os.X_OK, dir_fd=cwd_fd, effective_ids=True):
                    continue
                with os.fdopen(os.open(candidate, os.O_RDONLY | os.O_NONBLOCK, dir_fd=cwd_fd), "rb") as stream:
                    mode = os.fstat(stream.fileno()).st_mode
                    if not stat.S_ISREG(mode) or mode & (stat.S_ISUID | stat.S_ISGID):
                        return None
                    try:
                        if hasattr(os, "getxattr"):
                            os.getxattr(stream.fileno(), "com.apple.quarantine")
                        else:
                            # CPython exposes os.getxattr on Linux, but macOS needs its native fd API.
                            import ctypes
                            getxattr = ctypes.CDLL(None, use_errno=True).fgetxattr
                            getxattr.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_void_p, ctypes.c_size_t,
                                                ctypes.c_uint32, ctypes.c_int]
                            getxattr.restype = ctypes.c_ssize_t
                            if getxattr(stream.fileno(), b"com.apple.quarantine", None, 0, 0, 0) < 0:
                                error = ctypes.get_errno()
                                raise OSError(error, os.strerror(error))
                    except OSError as exc:
                        if exc.errno != getattr(errno, "ENOATTR", None):
                            return None
                    else:
                        return None
                    header = stream.read(512)
                if not header.startswith(b"#!"):
                    return None
                line = re.split(b"[#\n]", header[2:], maxsplit=1)
                if len(line) != 2:
                    return None
                words = re.split(b"[ \t]+", line[0].strip(b" \t"))
                if b"\0" in line[0] or not words[0].startswith(b"/"):
                    return None
                interpreter = os.fsdecode(words[0])
                mode = os.stat(interpreter).st_mode
                if (not stat.S_ISREG(mode) or mode & (stat.S_ISUID | stat.S_ISGID)
                        or not os.access(interpreter, os.X_OK, effective_ids=True)):
                    return None
                with open_stdin(interpreter) as stream:
                    image = stream.read(512)
                magic = int.from_bytes(image[:4], "big")
                if magic not in (0xfeedface, 0xfeedfacf, 0xcefaedfe, 0xcffaedfe,
                                 0xcafebabe, 0xbebafeca, 0xcafebabf, 0xbfbafeca):
                    return None
                order = "little" if magic in (0xcefaedfe, 0xcffaedfe, 0xbebafeca, 0xbfbafeca) else "big"
                if magic in (0xfeedface, 0xfeedfacf, 0xcefaedfe, 0xcffaedfe):
                    size = 32 if magic in (0xfeedfacf, 0xcffaedfe) else 28
                    if (len(image) < size or int.from_bytes(image[4:8], order) != cpu
                            or int.from_bytes(image[8:12], order) & ~0xff000000 not in subtypes):
                        return None
                else:
                    count = int.from_bytes(image[4:8], order)
                    size = 32 if magic in (0xcafebabf, 0xbfbafeca) else 20
                    if len(image) < 8 or count > (len(image) - 8) // size:
                        return None
                    if not any(int.from_bytes(image[8 + i * size:12 + i * size], order) == cpu
                               and int.from_bytes(image[12 + i * size:16 + i * size], order) & ~0xff000000 in subtypes
                               for i in range(count)):
                        return None
                return [*map(os.fsdecode, words), candidate]
        except (OSError, ValueError, TypeError, NotImplementedError):
            # Preserve the original exec, including PATH retries, whenever inspection is uncertain.
            return None
    return None


def shim_script(shim, raw, node, cwd=None):
    """The script a Node command shim runs, as cmd.exe would resolve it, else None: the one target of an npm, pnpm
    or corepack cmd-shim that sets no environment, or for Node.js's own npm.cmd and npx.cmd the global prefix's
    npm when installed there, else the bundled one."""
    targets = set(SHIM_RUN.findall(raw))
    if SHIM_NODE.search(raw) and len(targets) == 1 and set(SHIM_SET.findall(raw)) <= {"dp0", "_prog", "PATHEXT"}:
        return shim.parent / targets.pop().replace("\\", "/")
    cli = NPM_CLI.search(raw)
    if not cli or f'"%NODE_EXE%" "%{cli[1]}%" %*' not in raw:
        return None
    prefix_js = re.search(r'SET "NPM_PREFIX_JS=%~dp0\\([^"\r\n]+)"', raw)
    global_cli = re.search(rf'SET "NPM_PREFIX_{cli[1]}=%%F\\([^"\r\n]+)"', raw)
    if prefix_js and global_cli and node:
        # As the shim's FOR /F does: the last nonempty line npm-prefix.js prints names the global prefix.
        output = subprocess.run([node, str(shim.parent / prefix_js[1].replace("\\", "/"))], cwd=cwd, capture_output=True,
                                text=True, encoding="utf-8").stdout
        prefix = [line for line in output.splitlines() if line]
        if prefix and (installed := Path(prefix[-1]) / global_cli[1].replace("\\", "/")).is_file():
            return installed
    return shim.parent / cli[2].replace("\\", "/")


def system_exit_code(code):
    # CPython SystemExit uses signed C long (32 bits on Windows), unlike DWORD.
    return code - 0x100000000 if os.name == "nt" and code >= 0x80000000 else code


def mark_not_content_indexed(path):
    """Disable Windows content indexing for a directory and children created afterwards."""
    if os.name != "nt":
        return
    attrs = _kernel.GetFileAttributesW(str(path))
    _checked(attrs != 0xFFFFFFFF, _kernel.GetFileAttributesW, (str(path),))  # INVALID_FILE_ATTRIBUTES.
    _kernel.SetFileAttributesW(str(path), attrs | stat.FILE_ATTRIBUTE_NOT_CONTENT_INDEXED)


def mark_hidden(path):
    """Hide a newly created directory on Windows, preserving its other attributes."""
    if os.name != "nt":
        return
    attrs = _kernel.GetFileAttributesW(str(path))
    _checked(attrs != 0xFFFFFFFF, _kernel.GetFileAttributesW, (str(path),))
    _kernel.SetFileAttributesW(str(path), attrs | stat.FILE_ATTRIBUTE_HIDDEN)


if os.name == "nt":
    import _winapi
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

    class _JobProcessIds(ctypes.Structure):
        _fields_ = [("NumberOfAssignedProcesses", wintypes.DWORD),
                    ("NumberOfProcessIdsInList", wintypes.DWORD),
                    ("ProcessIdList", ctypes.c_size_t * 1)]

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
        ("OpenProcess", [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD], wintypes.HANDLE),
        ("IsProcessInJob", [wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL)], wintypes.BOOL),
        ("GetCurrentProcess", [], wintypes.HANDLE),
        ("DuplicateHandle", [wintypes.HANDLE, wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.HANDLE), wintypes.DWORD, wintypes.BOOL, wintypes.DWORD], wintypes.BOOL),
        ("CloseHandle", [wintypes.HANDLE], wintypes.BOOL),
        ("PeekNamedPipe", [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p], wintypes.BOOL),
        ("SetFileAttributesW", [wintypes.LPCWSTR, wintypes.DWORD], wintypes.BOOL),
    ):
        _function = getattr(_kernel, _name)
        _function.argtypes, _function.restype, _function.errcheck = _args, _result, _checked

    _kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    _kernel.WaitForSingleObject.restype = wintypes.DWORD  # WAIT_OBJECT_0 is successful zero, not BOOL.

    _kernel.GetFileAttributesW.argtypes = [wintypes.LPCWSTR]
    _kernel.GetFileAttributesW.restype = wintypes.DWORD  # Failure is INVALID_FILE_ATTRIBUTES, not zero.

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
                        # kill() can cache an exit code before the native handle is signaled.
                        if _winapi.WaitForSingleObject(self.child._handle, 5000) == _winapi.WAIT_TIMEOUT:
                            raise subprocess.TimeoutExpired(self.child.args, 5)
                    finally:
                        self.child._handle.Close()
            finally:
                if self.handle is not None:
                    with contextlib.ExitStack() as handles:
                        handles.callback(_kernel.CloseHandle, self.handle)
                        limits = _ExtendedLimits()  # Zero ActiveProcessLimit: no freed slot admits a new child.
                        limits.BasicLimitInformation.LimitFlags = 0x2008  # KILL_ON_JOB_CLOSE | ACTIVE_PROCESS.
                        _kernel.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits))
                        capacity = 1
                        while True:
                            buffer = ctypes.create_string_buffer(_JobProcessIds.ProcessIdList.offset + capacity * ctypes.sizeof(ctypes.c_size_t))
                            ids = _JobProcessIds.from_buffer(buffer)
                            try:
                                _kernel.QueryInformationJobObject(self.handle, 3, buffer, len(buffer), None)
                                break
                            except OSError as exc:
                                if exc.winerror != 234:  # ERROR_MORE_DATA: never accept a partial list.
                                    raise
                                capacity = max(capacity * 2, ids.NumberOfAssignedProcesses)
                        members = []
                        pids = (ctypes.c_size_t * ids.NumberOfProcessIdsInList).from_buffer(buffer, _JobProcessIds.ProcessIdList.offset)
                        for pid in pids:
                            try:
                                process = _kernel.OpenProcess(0x101000, False, pid)  # SYNCHRONIZE | QUERY_LIMITED_INFORMATION.
                            except OSError as exc:
                                if exc.winerror == 87:  # Already gone; other open failures remain visible.
                                    continue
                                raise
                            handles.callback(_kernel.CloseHandle, process)
                            member = wintypes.BOOL()
                            _kernel.IsProcessInJob(process, self.handle, ctypes.byref(member))
                            if member.value:  # A reused PID in another job is not our process identity.
                                members.append((pid, process))
                        # Natural exits before capture do not prove pending I/O or historical object finalization.
                        _kernel.TerminateJobObject(self.handle, 1)
                        deadline = time.monotonic() + 5
                        for pid, process in members:
                            remaining = max(0, int((deadline - time.monotonic()) * 1000))
                            result = _kernel.WaitForSingleObject(process, remaining)
                            if result == 258:  # WAIT_TIMEOUT.
                                raise OSError(f"Windows job teardown timed out waiting for process {pid}")
                            if result == 0xFFFFFFFF:  # WAIT_FAILED.
                                error = ctypes.get_last_error()
                                raise ctypes.WinError(error, f"WaitForSingleObject: {ctypes.FormatError(error)}")
                            if result != 0:
                                raise OSError(f"WaitForSingleObject: unexpected result {result} for process {pid}")

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
