#!/usr/bin/env python3
"""Serve self-contained observation commands outside an executor's sandbox via a file spool.

Commands write captures to DEVLYN_OBSERVATION_DIR. Replies retain raw results,
never a verdict; only the controller handles acceptance-look requests.
Each command runs once to completion in the worktree, then the observer ends its
process group and descendants' groups while an ancestor lives. Start, capture and
stop what you need in one call, including anything handed to the OS (open, simulators, launchers).

  observer.py call --spool <dir> [--timeout-sec <seconds>] -- <argv...>
  observer.py run --spool <dir> --worktree <dir> --out <dir> -- <child argv...>
  observer.py --self-test
"""
from __future__ import annotations

import argparse
import contextlib
import datetime
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest
import uuid

PLATFORM = runpy.run_path(str(Path(__file__).with_name("platform-support.py")))


def write_json(path, value):
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def is_link(info):
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_reparse_tag", 0) & 0x20000000)


def inventory(root):
    """Relative regular files and special entries, traversing directories but never links."""
    files, nonregular = [], []
    pending = [root]
    while pending:
        path = pending.pop()
        info = path.lstat()
        if is_link(info):
            nonregular.append(path.relative_to(root).as_posix())
        elif stat.S_ISDIR(info.st_mode):
            pending.extend(path.iterdir())
        elif stat.S_ISREG(info.st_mode):
            files.append(path.relative_to(root).as_posix())
        else:
            nonregular.append(path.relative_to(root).as_posix())
    return sorted(files), sorted(nonregular)


@contextlib.contextmanager
def serving(spool, worktree, out):
    spool = Path(spool)
    spool.mkdir(parents=True, exist_ok=True)
    with PLATFORM["file_lock"](spool / "serving.lock", blocking=True):
        for name in ("requests", "claimed", "replies"):
            directory = spool / name
            if directory.is_symlink() or directory.is_file():
                directory.unlink()
            elif directory.exists():
                shutil.rmtree(directory)
            directory.mkdir()
        try:
            yield
        finally:
            for name in ("requests", "claimed"):
                for request in sorted((spool / name).glob("*.json")):
                    if not (spool / "replies" / request.name).exists():
                        respond(spool, request, worktree, out, stopped=True)


def request_data(path):
    value = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(value, dict) and value.get("kind") == "acceptance-look":
        raise ValueError("acceptance-look is controller-only; observer never executes reviews")
    if not isinstance(value, dict) or set(value) - {"argv", "timeout_sec"}:
        raise ValueError("request must contain only argv and timeout_sec")
    argv = value.get("argv")
    if not isinstance(argv, list) or not argv or not all(isinstance(arg, str) for arg in argv):
        raise ValueError("argv must be a non-empty list of strings")
    seconds = value.get("timeout_sec", 120)
    if type(seconds) is not int or not 1 <= seconds <= 600:
        raise ValueError("timeout_sec must be an integer from 1 to 600")
    return argv, seconds


def respond(spool, request, worktree, out, *, stopped=False):
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    argv, seconds, outcome = [], 120, None
    try:
        argv, seconds = request_data(request)
    except (ValueError, UnicodeError) as exc:
        outcome = {"kind": "refused", "detail": str(exc)}
    if stopped:
        outcome = {"kind": "refused", "detail": "observer stopped"}
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    index = 1 + max((int(p.name) for p in out.iterdir() if p.name.isascii() and p.name.isdecimal()), default=0)
    directory = out / str(index)
    directory.mkdir()  # Exclusive: never overwrite a previous observation.
    result = {"id": request.stem, "index": index, "argv": argv, "started": started}
    with (directory / "stdout.txt").open("w+b") as stdout, (directory / "stderr.txt").open("w+b") as stderr:
        if outcome is None:
            env = os.environ.copy()
            env.update(PYTHONDONTWRITEBYTECODE="1", DEVLYN_OBSERVATION_DIR=str(directory.resolve()))
            try:
                code = PLATFORM["run_process"](PLATFORM["native_argv"](argv, cwd=worktree), subprocess.DEVNULL, seconds,
                                               cwd=worktree, env=env, stdout=stdout, stderr=stderr, raise_timeout=True)
                outcome = {"kind": "exit", "exit_code": code}
            except subprocess.TimeoutExpired:
                outcome = {"kind": "timeout"}
            except PLATFORM["CleanupError"] as exc:
                outcome = {"kind": "cleanup_failed", "detail": str(exc)}
            except (OSError, ValueError) as exc:
                outcome = {"kind": "spawn_error", "detail": str(exc)}
        for name, stream in (("stdout", stdout), ("stderr", stderr)):
            stream.seek(0)
            result[name] = {"path": str(directory / f"{name}.txt"), "sha256": hashlib.file_digest(stream, "sha256").hexdigest(),
                            "bytes": os.fstat(stream.fileno()).st_size}
    files, nonregular = inventory(directory)
    result.update(outcome=outcome, files=sorted(set(files) | {"result.json"}), nonregular=nonregular,
                  finished=datetime.datetime.now(datetime.timezone.utc).isoformat())
    write_json(directory / "result.json", result)
    write_json(spool / "replies" / request.name, result)


def pump(spool, worktree, out):
    spool = Path(spool)
    for request in sorted((spool / "requests").glob("*.json")):
        claimed = spool / "claimed" / request.name
        request.rename(claimed)
        respond(spool, claimed, worktree, out)
        break


def call(spool, argv, seconds, kind=None):
    spool = Path(spool)

    def unavailable(detail):
        print(f"observer unavailable at {spool}: {detail}", file=sys.stderr)
        return 3

    lock = spool / "serving.lock"
    if not lock.exists():
        return unavailable("no observer has served this spool")
    identity = uuid.uuid4().hex
    write_json(spool / "requests" / f"{identity}.json", {"kind": kind} if kind else {"argv": argv, "timeout_sec": seconds})
    print(identity, flush=True)
    reply = spool / "replies" / f"{identity}.json"
    while not reply.exists():
        try:
            with PLATFORM["file_lock"](lock, blocking=False):
                pass
        except BlockingIOError:
            time.sleep(0.1)
        else:
            if reply.exists():  # Shutdown publishes replies before releasing the lock.
                break
            return unavailable("observer stopped without a reply")
    result = json.loads(reply.read_text(encoding="utf-8"))
    print(json.dumps(result, ensure_ascii=False), flush=True)
    if kind and "verdict" in result:
        return 0 if result["verdict"] == "ship" else 2
    outcome = result["outcome"]
    return outcome["exit_code"] if outcome["kind"] == "exit" else {"timeout": 124, "cleanup_failed": 125, "spawn_error": 127, "refused": 3}[outcome["kind"]]


def run(spool, worktree, out, argv):
    with serving(spool, worktree, out):
        child = subprocess.Popen(PLATFORM["native_argv"](argv, cwd=worktree), cwd=worktree)
        while True:
            try:
                return child.wait(timeout=0.1)
            except subprocess.TimeoutExpired:
                pump(spool, worktree, out)


class ObserverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="devlyn-observer ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.spool, self.work, self.out = (self.root / name for name in ("spool", "work tree", "captures"))
        self.work.mkdir()

    def request(self, value, name="test"):
        path = self.spool / "requests" / f"{name}.json"
        write_json(path, value)
        pump(self.spool, self.work, self.out)
        result = json.loads((self.spool / "replies" / path.name).read_text(encoding="utf-8"))
        self.assertEqual(result, json.loads((self.out / str(result["index"]) / "result.json").read_text(encoding="utf-8")))
        self.assertNotIn("verdict", result)
        return result

    def test_refuses_controller_review_kind(self):
        with serving(self.spool, self.work, self.out):
            for value in ({"kind": "acceptance-look"}, {"kind": "acceptance-look", "argv": ["false"]}):
                result = self.request(value)
                self.assertEqual(result["outcome"]["kind"], "refused")
                self.assertIn("controller-only", result["outcome"]["detail"])

    def test_refuses_malformed_requests_without_running(self):
        command = [sys.executable, "-c", "from pathlib import Path; Path('ran').touch()"]
        with serving(self.spool, self.work, self.out):
            for value in ([], {}, {"argv": []}, {"argv": [3]}, {"argv": command, "extra": True},
                          *({"argv": command, "timeout_sec": seconds} for seconds in (True, 0, 601, "1"))):
                with self.subTest(value=value):
                    self.assertEqual(self.request(value)["outcome"]["kind"], "refused")
            (self.spool / "requests/broken.json").write_text("{", encoding="utf-8")
            pump(self.spool, self.work, self.out)
            self.assertEqual(json.loads((self.spool / "replies/broken.json").read_text())["outcome"]["kind"], "refused")
        self.assertFalse((self.work / "ran").exists())

    def test_environment_streams_numbering_and_inventory(self):
        from unittest import mock
        (self.out / "7").mkdir(parents=True)
        script = ("import json, os, pathlib, sys; p = pathlib.Path(os.environ['DEVLYN_OBSERVATION_DIR']); "
                  "(p / 'nested').mkdir(); (p / 'nested/capture.txt').write_text('capture'); "
                  "print(json.dumps([os.getcwd(), sys.stdin.read(), dict(os.environ)])); print('stderr', file=sys.stderr)")
        with mock.patch.dict(os.environ, {"OBSERVER_KEY": "key", "OBSERVER_SECRET": "secret", "OBSERVER_TOKEN": "token", "OBSERVER_KEEP": "keep"}):
            with serving(self.spool, self.work, self.out):
                result = self.request({"argv": [sys.executable, "-c", script]})
        self.assertEqual((result["index"], result["outcome"]), (8, {"kind": "exit", "exit_code": 0}))
        cwd, stdin, env = json.loads(Path(result["stdout"]["path"]).read_text())
        self.assertEqual((Path(cwd), stdin, env["DEVLYN_OBSERVATION_DIR"], env["PYTHONDONTWRITEBYTECODE"], env["OBSERVER_KEEP"]),
                         (self.work, "", str(self.out / "8"), "1", "keep"))
        self.assertEqual([env[key] for key in ("OBSERVER_KEY", "OBSERVER_SECRET", "OBSERVER_TOKEN")],
                         ["key", "secret", "token"])
        self.assertEqual(result["files"], ["nested/capture.txt", "result.json", "stderr.txt", "stdout.txt"])
        for name in ("stdout", "stderr"):
            raw = Path(result[name]["path"]).read_bytes()
            self.assertEqual((result[name]["sha256"], result[name]["bytes"]), (hashlib.sha256(raw).hexdigest(), len(raw)))

    def test_nonregular_entries_are_reported_without_following(self):
        script = ("import os, pathlib, subprocess; p = pathlib.Path(os.environ['DEVLYN_OBSERVATION_DIR']); " +
                  ("subprocess.run(['cmd', '/d', '/c', 'mklink', '/J', str(p / 'link'), str(p.parent)], check=True)" if os.name == "nt" else
                   "(p / 'link').symlink_to(p.parent, target_is_directory=True); os.mkfifo(p / 'fifo')"))
        with serving(self.spool, self.work, self.out):
            result = self.request({"argv": [sys.executable, "-c", script]})
        self.assertEqual(result["outcome"], {"kind": "exit", "exit_code": 0})
        self.assertEqual(result["nonregular"], ["link"] if os.name == "nt" else ["fifo", "link"])

    def test_timeout_and_normal_exit_end_background_children(self):
        # A child holds a native lock for its whole lifetime; reacquiring it proves it stopped.
        sleeper = ("import pathlib, runpy, sys, time\n"
                   "with runpy.run_path(sys.argv[1])['file_lock'](pathlib.Path(sys.argv[2])):\n"
                   " pathlib.Path(sys.argv[3]).touch()\n time.sleep(60)\n")
        script = ("import os, pathlib, subprocess, sys, time\n"
                  "p = pathlib.Path(os.environ['DEVLYN_OBSERVATION_DIR'])\n"
                  "child = subprocess.Popen([sys.executable, '-c', sys.argv[1], sys.argv[2], str(p / 'lock'), str(p / 'ready')])\n"
                  "while not (p / 'ready').exists():\n time.sleep(0.01)\n"
                  "(p / 'pid').write_text(str(child.pid))\n"
                  "time.sleep(int(sys.argv[3]))\n")
        with serving(self.spool, self.work, self.out):
            for delay, kind in ((60, "timeout"), (0, "exit")):
                result = self.request({"argv": [sys.executable, "-c", script, sleeper, str(Path(__file__).with_name("platform-support.py")), str(delay)],
                                       "timeout_sec": 2}, name=kind)
                self.assertEqual(result["outcome"]["kind"], kind)
                directory = self.out / str(result["index"])
                self.assertTrue((directory / "pid").is_file())
                with PLATFORM["file_lock"](directory / "lock"):
                    pass

    @unittest.skipIf(os.name == "nt", "POSIX detached process groups")
    def test_normal_exit_and_timeout_end_detached_grandchildren(self):
        sleeper = ("import os, pathlib, runpy, sys, time\n"
                   "with runpy.run_path(sys.argv[1])['file_lock'](pathlib.Path(sys.argv[2])):\n"
                   " pathlib.Path(sys.argv[3]).write_text(str(os.getpid()))\n time.sleep(60)\n")
        parent = ("import subprocess, sys, time\n"
                  "subprocess.Popen([sys.executable, '-c', *sys.argv[1:]], start_new_session=True)\n"
                  "time.sleep(60)\n")
        script = ("import os, pathlib, subprocess, sys, time\n"
                  "p = pathlib.Path(os.environ['DEVLYN_OBSERVATION_DIR'])\n"
                  "subprocess.Popen([sys.executable, '-c', sys.argv[1], sys.argv[2], sys.argv[3], str(p / 'lock'), str(p / 'ready')])\n"
                  "while not (p / 'ready').exists(): time.sleep(.01)\n"
                  "time.sleep(int(sys.argv[4]))\n")
        with serving(self.spool, self.work, self.out):
            for index, (delay, kind) in enumerate(((0, "exit"), (60, "timeout")), 1):
                with self.subTest(kind=kind):
                    def cleanup_descendant(index):
                        import signal
                        ready = self.out / str(index) / "ready"
                        if ready.exists():
                            try:
                                os.killpg(int(ready.read_text()), signal.SIGKILL)
                            except ProcessLookupError:
                                pass  # Successful cleanup already ended this fixture's group.

                    self.addCleanup(cleanup_descendant, index)
                    result = self.request({"argv": [sys.executable, "-c", script, parent, sleeper,
                                                   str(Path(__file__).with_name("platform-support.py")), str(delay)],
                                           "timeout_sec": 2}, name=kind)
                    self.assertEqual(result["outcome"]["kind"], kind)
                    directory = self.out / str(result["index"])
                    self.assertTrue((directory / "ready").exists())
                    with PLATFORM["file_lock"](directory / "lock"):
                        pass

    def test_prompt_background_exit_does_not_wait_out_grace(self):
        script = ("import os, pathlib, subprocess, sys, time\n"
                  "p = pathlib.Path(os.environ['DEVLYN_OBSERVATION_DIR'])\n"
                  "subprocess.Popen([sys.executable, '-c', "
                  "\"import pathlib, sys, time; pathlib.Path(sys.argv[1]).touch(); time.sleep(60)\", str(p / 'ready')])\n"
                  "while not (p / 'ready').exists(): time.sleep(.01)\n")
        with serving(self.spool, self.work, self.out):
            started = time.monotonic()
            result = self.request({"argv": [sys.executable, "-c", script]})
            elapsed = time.monotonic() - started
        self.assertEqual(result["outcome"], {"kind": "exit", "exit_code": 0})
        self.assertTrue((self.out / str(result["index"]) / "ready").exists())
        self.assertLess(elapsed, 4)

    @unittest.skipIf(os.name == "nt", "POSIX process groups")
    def test_escalation_verifies_group_identity(self):
        import signal
        from unittest import mock
        platform_globals = PLATFORM["terminate_tree"].__globals__
        discovery = {101: (1, 101, "leader"), 202: (101, 202, "T1"), 203: (202, 202, "member")}
        # Include a reused pid, and an original member whose group leader has exited.
        for current, verified in (({303: (1, 202, "T2")}, False),
                                  ({202: (1, 202, "T2")}, False),
                                  ({203: (1, 202, "member")}, True)):
            with self.subTest(current=current):
                child = mock.Mock(pid=101, returncode=None)
                child.poll.return_value = 0
                signals = []

                def signal_group(group, sig):
                    signals.append((group, sig))
                    if group == 101:
                        raise ProcessLookupError

                with mock.patch.dict(platform_globals, {"_process_snapshot": mock.Mock(side_effect=[discovery, current])}), \
                        mock.patch.object(os, "killpg", side_effect=signal_group), \
                        mock.patch.object(time, "monotonic", side_effect=[0, 6, 6, 12]):
                    with self.assertRaises(PLATFORM["CleanupError"]) as raised:
                        PLATFORM["terminate_tree"](child)
                self.assertIn((202, signal.SIGTERM), signals)
                self.assertIn((202, 0), signals)
                self.assertEqual((202, signal.SIGKILL) in signals, verified)
                self.assertIn("surviving groups [202]", str(raised.exception))
                self.assertIn(f"unverified groups {[] if verified else [202]}", str(raised.exception))

    @unittest.skipIf(os.name == "nt", "POSIX process groups")
    def test_missing_identity_only_escalates_unreaped_leader(self):
        import io
        import signal
        from unittest import mock
        platform_globals = PLATFORM["terminate_tree"].__globals__
        discovery = {101: (1, 101, "leader"), 202: (101, 202, "T1")}
        for discovery_failed in (False, True):
            for reaped in (False, True):
                with self.subTest(discovery_failed=discovery_failed, reaped=reaped):
                    child = mock.Mock(pid=101, returncode=None)
                    child.poll.return_value = 0 if reaped else None
                    snapshots = mock.Mock(side_effect=[OSError("ps unavailable") if discovery_failed else discovery,
                                                       OSError("ps unavailable")])
                    stderr = io.StringIO()
                    with mock.patch.dict(platform_globals, {"_process_snapshot": snapshots}), \
                            mock.patch.object(os, "killpg") as killpg, \
                            mock.patch.object(time, "monotonic", side_effect=[0, 6, 6, 12]), \
                            contextlib.redirect_stderr(stderr):
                        with self.assertRaises(PLATFORM["CleanupError"]) as raised:
                            PLATFORM["terminate_tree"](child)
                    self.assertEqual(snapshots.call_count, 2)
                    self.assertEqual(mock.call(101, signal.SIGKILL) in killpg.call_args_list, not reaped)
                    self.assertNotIn(mock.call(202, signal.SIGKILL), killpg.call_args_list)
                    unverified = ([101] if reaped else []) + ([] if discovery_failed else [202])
                    self.assertIn(f"unverified groups {unverified}", str(raised.exception))
                    self.assertEqual(len(stderr.getvalue().splitlines()), 1)

    @unittest.skipIf(os.name == "nt", "POSIX process groups")
    def test_ps_unavailable_kills_unreaped_leader(self):
        import io
        import signal
        import threading
        from unittest import mock
        ready = self.work / "leader.pid"
        script = ("import os, pathlib, signal, sys, time\n"
                  "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
                  "pathlib.Path(sys.argv[1]).write_text(str(os.getpid()))\n"
                  "time.sleep(60)\n")
        real_run, real_killpg = subprocess.run, os.killpg
        signals, snapshots = [], []

        def run(*args, **kwargs):
            if args[0][0] == "ps":
                snapshots.append(args[0])
                raise OSError("fixture denies ps")
            return real_run(*args, **kwargs)

        def signal_group(group, sig):
            signals.append((group, sig))
            return real_killpg(group, sig)

        expired = threading.Event()

        def stop_fixture():
            if ready.exists():
                try:
                    real_killpg(int(ready.read_text()), signal.SIGKILL)
                except ProcessLookupError:
                    pass  # The fixture has already been cleaned up.

        def watchdog():
            expired.set()
            stop_fixture()

        timer = threading.Timer(12, watchdog)
        timer.start()
        try:
            stderr = io.StringIO()
            with mock.patch.object(subprocess, "run", side_effect=run), \
                    mock.patch.object(os, "killpg", side_effect=signal_group), contextlib.redirect_stderr(stderr):
                with serving(self.spool, self.work, self.out):
                    result = self.request({"argv": [sys.executable, "-c", script, str(ready)], "timeout_sec": 1})
            self.assertFalse(expired.is_set(), "cleanup exceeded the watchdog deadline")
            self.assertTrue(ready.exists(), "leader never installed its SIGTERM handler")
            self.assertIn((int(ready.read_text()), signal.SIGKILL), signals)
            self.assertEqual(len(snapshots), 2)
            self.assertEqual(len(stderr.getvalue().splitlines()), 1)
            self.assertEqual(result["outcome"]["kind"], "timeout")
        finally:
            timer.cancel()
            timer.join()
            stop_fixture()

    @unittest.skipIf(os.name == "nt", "POSIX process groups")
    def test_unkillable_leader_reports_bounded_cleanup_failure(self):
        self.check_cleanup_failure(detached=False)

    @unittest.skipIf(os.name == "nt", "POSIX detached process groups")
    def test_detached_survivor_reports_cleanup_failure(self):
        self.check_cleanup_failure(detached=True)

    def check_cleanup_failure(self, *, detached):
        import signal
        import threading
        from unittest import mock
        ready = self.work / "survivor.pid"
        sleeper = ("import os, pathlib, signal, sys, time\n"
                   "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
                   "pathlib.Path(sys.argv[1]).write_text(str(os.getpid()))\n"
                   "print('stdout', flush=True); print('stderr', file=sys.stderr, flush=True)\n"
                   "time.sleep(60)\n")
        command = [sys.executable, "-c", sleeper, str(ready)]
        if detached:
            parent = ("import subprocess, sys, time\n"
                      "subprocess.Popen(sys.argv[1:], start_new_session=True)\n"
                      "time.sleep(60)\n")
            command = [sys.executable, "-c", parent, *command]
        platform_globals = PLATFORM["terminate_tree"].__globals__
        real_killpg, real_popen = os.killpg, subprocess.Popen
        leaders, blocked = [], []

        def start(*args, **kwargs):
            child = real_popen(*args, **kwargs)
            if kwargs.get("start_new_session"):
                leaders.append(child)
            return child

        def signal_group(group, sig):
            if sig == signal.SIGKILL and ready.exists() and group == int(ready.read_text()):
                blocked.append(group)
                if not detached:
                    raise PermissionError("fixture denies SIGKILL")
                return  # The detached group survives a successful-looking SIGKILL.
            return real_killpg(group, sig)

        def kill_fixtures():
            groups = {child.pid for child in leaders}
            if ready.exists():
                groups.add(int(ready.read_text()))
            for group in groups:
                try:
                    real_killpg(group, signal.SIGKILL)
                except ProcessLookupError:
                    pass  # Cleanup may already have ended the leader's group.

        # A regression to unbounded wait must fail the test rather than hang the suite.
        expired = threading.Event()

        def watchdog():
            expired.set()
            kill_fixtures()

        timer = threading.Timer(12, watchdog)
        timer.start()
        try:
            with mock.patch.object(platform_globals["os"], "killpg", side_effect=signal_group), \
                    mock.patch.object(platform_globals["subprocess"], "Popen", side_effect=start):
                with serving(self.spool, self.work, self.out):
                    started = time.monotonic()
                    result = self.request({"argv": command, "timeout_sec": 1})
                    elapsed = time.monotonic() - started
            self.assertFalse(expired.is_set(), "cleanup exceeded the watchdog deadline")
            self.assertLess(elapsed, 12)
            self.assertTrue(blocked, "fixture group was not discovered and sent SIGKILL")
            self.assertEqual(result["outcome"]["kind"], "cleanup_failed")
            self.assertIn(str(blocked[0]), result["outcome"]["detail"])
            self.assertIn(f"still lives: {not detached}", result["outcome"]["detail"])
            self.assertEqual(result["files"], ["result.json", "stderr.txt", "stdout.txt"])
            for name in ("stdout", "stderr"):
                raw = Path(result[name]["path"]).read_bytes()
                self.assertEqual(raw, f"{name}\n".encode())
                self.assertEqual((result[name]["sha256"], result[name]["bytes"]), (hashlib.sha256(raw).hexdigest(), len(raw)))
            with PLATFORM["file_lock"](self.spool / "serving.lock"):
                pass
        finally:
            timer.cancel()
            timer.join()
            kill_fixtures()
            for child in leaders:
                child.wait(timeout=5)

    def test_client_maps_cleanup_failure_to_125(self):
        import io
        from unittest import mock
        with serving(self.spool, self.work, self.out):
            write_json(self.spool / "replies/cleanup.json", {"outcome": {"kind": "cleanup_failed", "detail": "surviving group"}})
            with mock.patch.object(uuid, "uuid4") as identity, contextlib.redirect_stdout(io.StringIO()):
                identity.return_value.hex = "cleanup"
                self.assertEqual(call(self.spool, [sys.executable, "-c", "pass"], 1), 125)

    def test_shutdown_replies_and_stale_spool_cleanup(self):
        with serving(self.spool, self.work, self.out):
            for name in ("requests", "claimed"):
                write_json(self.spool / name / f"{name}.json", {"argv": [sys.executable, "-c", "raise SystemExit(99)"]})
        self.assertTrue((self.spool / "serving.lock").exists())
        with PLATFORM["file_lock"](self.spool / "serving.lock"):
            pass
        for name in ("requests", "claimed"):
            reply = json.loads((self.spool / "replies" / f"{name}.json").read_text())
            self.assertEqual(reply["outcome"], {"kind": "refused", "detail": "observer stopped"})
        with serving(self.spool, self.work, self.out):
            self.assertTrue((self.spool / "serving.lock").exists())
            for name in ("requests", "claimed", "replies"):
                self.assertEqual(list((self.spool / name).iterdir()), [])
        self.assertTrue((self.spool / "serving.lock").exists())
        with PLATFORM["file_lock"](self.spool / "serving.lock"):
            pass

    def wait_for(self, predicate):
        deadline = time.monotonic() + 5
        while not predicate():
            self.assertLess(time.monotonic(), deadline, "fixture did not become ready")
            time.sleep(0.01)

    def start_python(self, script, *args):
        child = subprocess.Popen([sys.executable, "-c", script, *map(str, args)])

        def stop():
            if child.poll() is None:
                child.kill()
            child.wait(timeout=5)

        self.addCleanup(stop)
        return child

    def client_argv(self):
        return [sys.executable, str(Path(__file__).resolve()), "call", "--spool", str(self.spool),
                "--", sys.executable, "-c", "pass"]

    def test_client_unavailable_without_lock_or_live_server(self):
        absent = subprocess.run(self.client_argv(), capture_output=True, text=True, timeout=5)
        self.assertEqual((absent.returncode, len(absent.stderr.splitlines())), (3, 1))
        self.assertIn("no observer has served this spool", absent.stderr)
        with serving(self.spool, self.work, self.out):
            pass
        stopped = subprocess.run(self.client_argv(), capture_output=True, text=True, timeout=5)
        self.assertEqual(stopped.returncode, 3)
        self.assertEqual(len(stopped.stdout.splitlines()), 1)
        self.assertIn("observer stopped without a reply", stopped.stderr)

    def test_killed_server_releases_claimed_client(self):
        script = ("import pathlib, runpy, sys, time\n"
                  "observer = runpy.run_path(sys.argv[1])\n"
                  "spool, work, out = map(pathlib.Path, sys.argv[2:])\n"
                  "with observer['serving'](spool, work, out):\n"
                  " (spool / 'ready').touch()\n"
                  " while not list((spool / 'requests').glob('*.json')): time.sleep(.01)\n"
                  " request = next((spool / 'requests').glob('*.json'))\n"
                  " request.rename(spool / 'claimed' / request.name)\n"
                  " time.sleep(60)\n")
        server = self.start_python(script, Path(__file__).resolve(), self.spool, self.work, self.out)
        self.wait_for(lambda: (self.spool / "ready").exists())
        with subprocess.Popen(self.client_argv(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as client:
            try:
                self.wait_for(lambda: bool(list((self.spool / "claimed").glob("*.json"))))
                started = time.monotonic()
                server.kill()  # SIGKILL on POSIX, TerminateProcess on Windows.
                server.wait(timeout=5)
                stdout, stderr = client.communicate(timeout=3)
                self.assertLess(time.monotonic() - started, 3)
                self.assertEqual(client.returncode, 3)
                self.assertEqual(len(stdout.splitlines()), 1)
                self.assertIn("observer stopped without a reply", stderr)
            finally:
                if client.poll() is None:
                    client.kill()

    def test_client_waits_behind_request_longer_than_ten_seconds(self):
        script = ("import pathlib, runpy, sys, time\n"
                  "observer = runpy.run_path(sys.argv[1])\n"
                  "spool, work, out = map(pathlib.Path, sys.argv[2:])\n"
                  "with observer['serving'](spool, work, out):\n"
                  " observer['write_json'](spool / 'requests/000.json', "
                  "{'argv': [sys.executable, '-c', 'import time; time.sleep(11)'], 'timeout_sec': 20})\n"
                  " (spool / 'ready').touch()\n"
                  " while len(list((spool / 'replies').glob('*.json'))) < 2:\n"
                  "  observer['pump'](spool, work, out)\n time.sleep(.01)\n")
        server = self.start_python(script, Path(__file__).resolve(), self.spool, self.work, self.out)
        self.wait_for(lambda: (self.spool / "claimed/000.json").exists())
        started = time.monotonic()
        result = subprocess.run(self.client_argv(), capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertGreater(time.monotonic() - started, 10)
        self.assertEqual(json.loads(result.stdout.splitlines()[1])["outcome"], {"kind": "exit", "exit_code": 0})
        self.assertEqual(json.loads((self.spool / "replies/000.json").read_text())["outcome"],
                         {"kind": "exit", "exit_code": 0})
        self.assertEqual(server.wait(timeout=5), 0)

    def test_pump_answers_only_oldest_request(self):
        with serving(self.spool, self.work, self.out):
            for name in ("002", "001"):
                write_json(self.spool / "requests" / f"{name}.json", {"argv": [sys.executable, "-c", "pass"]})
            pump(self.spool, self.work, self.out)
            self.assertEqual([p.name for p in (self.spool / "replies").iterdir()], ["001.json"])
            self.assertEqual([p.name for p in (self.spool / "requests").iterdir()], ["002.json"])
        self.assertEqual(json.loads((self.spool / "replies/002.json").read_text())["outcome"],
                         {"kind": "refused", "detail": "observer stopped"})

    def test_run_stops_queued_requests_when_child_exits(self):
        script = ("import pathlib, runpy, sys, time\n"
                  "observer = runpy.run_path(sys.argv[1]); spool = pathlib.Path(sys.argv[2])\n"
                  "observer['write_json'](spool / 'requests/001.json', {'argv': [sys.executable, '-c', "
                  "\"import pathlib, time; time.sleep(.5); pathlib.Path('first').touch()\"]})\n"
                  "observer['write_json'](spool / 'requests/002.json', {'argv': [sys.executable, '-c', "
                  "\"import pathlib; pathlib.Path('second').touch()\"]})\n"
                  "while not (spool / 'claimed/001.json').exists(): time.sleep(.01)\n")
        observer = str(Path(__file__).resolve())
        result = subprocess.run([sys.executable, observer, "run", "--spool", str(self.spool),
                                 "--worktree", str(self.work), "--out", str(self.out), "--",
                                 sys.executable, "-c", script, observer, str(self.spool)],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.work / "first").exists())
        self.assertFalse((self.work / "second").exists())
        self.assertEqual(json.loads((self.spool / "replies/002.json").read_text())["outcome"],
                         {"kind": "refused", "detail": "observer stopped"})

    def test_direct_run_and_client_exit_codes(self):
        observer = str(Path(__file__).resolve())
        client = [sys.executable, observer, "call", "--spool", str(self.spool), "--timeout-sec", "1", "--"]
        driver = [sys.executable, observer, "run", "--spool", str(self.spool), "--worktree", str(self.work), "--out", str(self.out), "--"]
        for command, code, kind in (([sys.executable, "-c", "raise SystemExit(7)"], 7, "exit"),
                                    ([sys.executable, "-c", "raise SystemExit(124)"], 124, "exit"),
                                    ([sys.executable, "-c", "import time; time.sleep(60)"], 124, "timeout"),
                                    ([str(self.root / "missing")], 127, "spawn_error")):
            with self.subTest(kind=kind):
                result = subprocess.run(driver + client + command, capture_output=True, text=True, encoding="utf-8", timeout=15)
                self.assertEqual(result.returncode, code, result.stderr)
                identity, raw = result.stdout.splitlines()
                reply = json.loads(raw)
                self.assertEqual((reply["id"], reply["outcome"]["kind"]), (identity, kind))
                self.assertTrue((self.spool / "serving.lock").exists())
                with PLATFORM["file_lock"](self.spool / "serving.lock"):
                    pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    actions = parser.add_subparsers(dest="action")
    client = actions.add_parser("call")
    client.add_argument("--spool", type=Path, required=True)
    client.add_argument("--timeout-sec", type=int, default=120)
    client.add_argument("--kind", choices=("acceptance-look",))
    client.add_argument("argv", nargs=argparse.REMAINDER)
    server = actions.add_parser("run")
    for name in ("spool", "worktree", "out"):
        server.add_argument(f"--{name}", type=Path, required=True)
    server.add_argument("argv", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.self_test:
        return 0 if unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ObserverTests)).wasSuccessful() else 1
    if args.action is None:
        parser.error("choose call or run")
    argv = args.argv[1:] if args.argv[:1] == ["--"] else args.argv
    kind = getattr(args, "kind", None)
    if kind and argv:
        parser.error("acceptance-look carries no argv or prompt")
    if not argv and not kind:
        parser.error("a command is required after --")
    try:
        if args.action == "call":
            return call(args.spool, argv, args.timeout_sec, kind)
        return run(args.spool.resolve(), args.worktree.resolve(), args.out.resolve(), argv)
    except (OSError, ValueError) as exc:
        print(f"observer: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    PLATFORM["configure_utf8"]()
    raise SystemExit(PLATFORM["system_exit_code"](main()))
