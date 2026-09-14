import base64
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


def controller():
    spec = importlib.util.spec_from_file_location(
        "comparison_controller", Path(__file__).with_name("comparison-controller.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BOUNDS = dict(native_seconds=1800, wrapper_seconds=1810,
              post_return_quiet_seconds=15, term_seconds=10,
              kill_reap_seconds=5, overall_seconds=1830)


class ControllerTests(unittest.TestCase):
    def simulate(self, mode):
        module = controller()
        elapsed = [0.0]
        attempts, signals = [], []
        killed_at = [None]

        class Process:
            pid = 999001
            returncode = None

            def poll(self):
                if mode in ("recover", "nonzero") and elapsed[0] >= 4:
                    self.returncode = 7 if mode == "nonzero" else 0
                return self.returncode

            def wait(self, timeout):
                if self.poll() is None:
                    raise subprocess.TimeoutExpired("owned-task", timeout)
                return self.returncode

        process = Process()

        def table(timeout):
            attempts.append(timeout)
            if mode == "blind" or (mode == "recover" and len(attempts) == 1):
                elapsed[0] += timeout
                raise subprocess.TimeoutExpired("ps", timeout, b"\xffpartial", b"slow")
            if mode == "reuse":
                if len(attempts) == 2:
                    raise OSError("census unavailable")
                if len(attempts) >= 4:
                    process.returncode = 0
                    return {process.pid: dict(pid=process.pid, ppid=1,
                            pgid=process.pid, state="S", identity="replacement")}
            dying = killed_at[0] is not None and elapsed[0] - killed_at[0] < .5
            if process.poll() is not None and not dying:
                return {}
            return {process.pid: dict(pid=process.pid, ppid=os.getpid(),
                    pgid=process.pid, state="S", identity="original")}

        def kill(pid, number):
            signals.append((pid, number))
            if number == signal.SIGKILL:
                process.returncode = -number
                killed_at[0] = elapsed[0]

        def sleep(seconds):
            elapsed[0] += seconds

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(module.time, "monotonic", lambda: elapsed[0]), \
                    patch.object(module.time, "sleep", sleep), \
                    patch.object(module.subprocess, "Popen", return_value=process) as spawn, \
                    patch.object(module, "process_table", table), \
                    patch.object(module.os, "kill", kill):
                result = module.execute(dict(bounds=BOUNDS, argv=["task"], work=str(root)), root)
            events = [json.loads(line) for line in (root / "owned-processes.jsonl").read_text().splitlines()]
        self.assertEqual(spawn.call_count, 1)
        self.assertLessEqual(elapsed[0], BOUNDS["overall_seconds"])
        return result, events, signals, attempts

    def test_one_timeout_recovers_without_restarting_or_signalling_task(self):
        result, events, signals, _ = self.simulate("recover")
        self.assertIsNone(result["error"])
        self.assertTrue(result["owned_writers_quiescent"])
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["observation_timeouts"], 1)
        self.assertEqual(base64.b64decode(events[0]["stdout_base64"]), b"\xffpartial")
        self.assertEqual(signals, [])

    def test_persistent_blindness_fails_without_stale_pid_signals(self):
        result, _, signals, attempts = self.simulate("blind")
        self.assertIsNotNone(result["error"])
        self.assertIsNone(result["owned_writers_quiescent"])
        self.assertIsNone(result["wrapper_return_seconds"])
        self.assertEqual(signals, [])
        self.assertEqual(result["controller_seconds"], 30)
        self.assertTrue(all(0 < timeout <= 2 for timeout in attempts))

    def test_task_failure_is_not_hidden_by_quiescence(self):
        result, _, signals, _ = self.simulate("nonzero")
        self.assertEqual(result["exit_code"], 7)
        self.assertTrue(result["owned_writers_quiescent"])
        self.assertEqual(signals, [])

    def test_pid_reuse_between_observation_and_signal_is_not_killed(self):
        result, _, signals, _ = self.simulate("reuse")
        self.assertIsNotNone(result["error"])
        self.assertEqual(signals, [])

    def test_term_ignorer_gets_kill_and_post_kill_quiet_observation(self):
        result, _, signals, _ = self.simulate("ignore-term")
        self.assertEqual([number for _, number in signals], [signal.SIGTERM, signal.SIGKILL])
        self.assertTrue(result["owned_writers_quiescent"])
        self.assertIsNotNone(result["error"])
        self.assertEqual(result["exit_code"], -signal.SIGKILL)

    @unittest.skipUnless(Path("/bin/ps").exists(), "native POSIX census")
    def test_real_subprocess_survives_slow_census(self):
        module = controller()
        original_run = subprocess.run
        delayed = []

        def run(argv, **kwargs):
            if argv[0] == "/bin/ps" and not delayed:
                delayed.append(True)
                return original_run([sys.executable, "-c", "import time; time.sleep(2.1)"], **kwargs)
            return original_run(argv, **kwargs)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(module.subprocess, "run", run):
                result = module.execute(dict(bounds=BOUNDS, work=str(root), argv=[
                    sys.executable, "-c", "import time; print('started', flush=True); time.sleep(4); print('finished')"
                ]), root)
            self.assertEqual((root / "stdout").read_text(), "started\nfinished\n")
        self.assertIsNone(result["error"])
        self.assertTrue(result["owned_writers_quiescent"])
        self.assertEqual(result["observation_timeouts"], 1)

    def test_parent_committed_test_needs_no_worker_index_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            def git(*args, check=True):
                return subprocess.run(["git", *args], cwd=root, check=check, capture_output=True)
            git("init", "-q")
            (root / "test_regression.py").write_text("def test_regression(): assert True\n")
            git("add", "test_regression.py")
            git("-c", "user.name=test", "-c", "user.email=test@example.invalid",
                "-c", "commit.gpgsign=false", "commit", "-qm", "parent checkpoint")
            before = (root / ".git/index").read_bytes()
            (root / ".git/index.lock").touch()
            self.assertEqual(git("ls-files", "--error-unmatch", "test_regression.py").stdout,
                             b"test_regression.py\n")
            self.assertEqual(git("add", "test_regression.py", check=False).returncode, 128)
            self.assertEqual((root / ".git/index").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
