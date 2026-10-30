#!/usr/bin/env python3
"""Deterministic loop fixture: the production queue driver over temporary Git repositories.

Fake executors and fake delivery stand in for models and GitHub; nothing uses the
network. Interruptions are real: a native lock holds the driver at a durable
checkpoint and the driver process is killed there (D6 §6).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
HOLD = ("import pathlib, runpy, sys, time\n"
        "with runpy.run_path(sys.argv[1])['file_lock'](pathlib.Path(sys.argv[2]), blocking=True):\n"
        "    pathlib.Path(sys.argv[3]).write_text('held')\n"
        "    while True:\n        time.sleep(1)\n")
EXECUTOR = r'''
import json, os, pathlib, stat, subprocess, sys, time
config_path, packet = pathlib.Path(sys.argv[1]), json.loads(pathlib.Path(sys.argv[2]).read_text(encoding="utf-8"))
config = json.loads(config_path.read_text(encoding="utf-8"))
behavior = config["behaviors"][packet["task"]]
if behavior.get("refuse_pipe") and stat.S_ISFIFO(os.fstat(1).st_mode):
    print("stdout is a pipe", file=sys.stderr)  # codex-monitored.sh refuses this shape with exit 64
    sys.exit(64)
if behavior.get("stdin_eof") and sys.stdin.read():
    sys.exit("stdin carries the driver's input")
with config_path.with_name("calls-" + packet["task"]).open("a", encoding="utf-8") as calls:
    calls.write(json.dumps(sys.argv[2:]) + "\n")
if "exit_now" in behavior:  # an engine that stops at once, as on a usage limit
    print("API Error: 429 usage limit reached", file=sys.stderr)
    sys.exit(behavior["exit_now"])
if behavior.get("hang"):
    config_path.with_name("hang.pid").write_text(str(os.getpid()))
    while not config_path.with_name("release").exists():
        time.sleep(0.1)
    config_path.with_name("hang.pid").unlink()
work = pathlib.Path(packet["worktree"])
def git(*args):
    return subprocess.run(["git", "-C", str(work), *args], check=True, capture_output=True, text=True, encoding="utf-8").stdout.strip()
def commit(files, message):
    for rel, body in files.items():
        (work / rel).write_text(body, encoding="utf-8")
    git("add", *files)
    git("commit", "-q", "-m", message)
    return git("rev-parse", "HEAD")
source = (packet["inputs_sha"] if behavior.get("check_only")
          else commit(config["products"][behavior["product"]], "implement " + packet["task"]))
submission = {"schema_version": 1, "task": packet["task"], "source_sha": source, "summary": "done (informational)",
              "assumptions": behavior.get("assumptions", ["fixture assumption for " + packet["task"]]), "blockers": behavior.get("blockers", [])}
if behavior.get("runner", True):
    checked = subprocess.run(packet["runner"], check=True, capture_output=True, text=True, encoding="utf-8")
    submission["runner_results"] = [json.loads(checked.stdout)["result"]]
if behavior.get("review", True):
    review = work / ".devlyn" / "reviews" / (packet["task"] + ".json")
    review.parent.mkdir(parents=True, exist_ok=True)
    review.write_text(json.dumps({"schema_version": 1, "kind": "devlyn-review", "task": packet["task"], "engine": "fake-engine",
        "model": "fake-model", "source_sha": source, "contract_sha256": packet["contract"]["sha256"],
        "expected_sha256": packet["expected"]["sha256"], "findings": [],
        "requirements": [{"id": r} for r in packet["review_requirements"]] if behavior.get("malformed_review") else packet["review_requirements"]}),
        encoding="utf-8")
    submission["reviews"] = [str(review)]
if behavior.get("change_after_review"):
    submission["source_sha"] = commit({"late.txt": "late change\n"}, "change after checks and review")
if behavior.get("detach"):
    git("checkout", "-q", "--detach")
if behavior.get("hold"):
    flag = config_path.with_name("held")
    detach = {"creationflags": subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    holder = subprocess.Popen([sys.executable, "-c", config["hold"], config["platform_support"], config["queue_lock"], str(flag)],
                              stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **detach)
    while not flag.exists():
        time.sleep(0.05)
    config_path.with_name("holder.pid").write_text(str(holder.pid))
pathlib.Path(packet["submission"]).write_text(json.dumps(submission), encoding="utf-8")
'''
# Runs the driver where task-complete cannot observe writers, as on native Windows (a no-op there).
UNOBSERVABLE = ("import runpy, sys\n"
                "queue = runpy.run_path(sys.argv[1])\n"
                "queue['shared']('task-complete')\n"
                "sys.platform = 'win32'\n"
                "sys.argv = sys.argv[1:]\n"
                "queue['shared']('platform-support')['configure_utf8']()\n"
                "sys.exit(queue['main']())\n")
# Runs the driver until its next matching durable step, then exits at once, as a crash there would: no handler, finally
# block or later write runs. `replace <name>` stops before the atomic write of a file of that name, `unlink <name>` before
# the removal of one. The `-after` suffix stops after that operation; `rename-after <name>` matches the source name.
# `attach-after receipt.json` stops once the terminal attachment is saved.
CRASH = ("import json, os, pathlib, runpy, sys\n"
         "step, name = sys.argv[1:3]\n"
         "after = step.endswith('-after')\n"
         "step = step.removesuffix('-after')\n"
         "sys.argv = sys.argv[3:]\n"
         "def crashing(real):\n"
         "    def call(path, *args, **kwargs):\n"
         "        matched = pathlib.Path(args[0] if step in {'replace', 'attach'} else path).name == name\n"
         "        if matched and step == 'attach':\n"
         "            matched = 'queue' in json.loads(pathlib.Path(path).read_text(encoding='utf-8'))\n"
         "        if matched and not after:\n"
         "            os._exit(9)\n"
         "        result = real(path, *args, **kwargs)\n"
         "        if matched:\n"
         "            os._exit(9)\n"
         "        return result\n"
         "    return call\n"
         "if step in {'replace', 'attach'}:\n    os.replace = crashing(os.replace)\n"
         "elif step == 'rename':\n    pathlib.Path.rename = crashing(pathlib.Path.rename)\n"
         "else:\n    pathlib.Path.unlink = crashing(pathlib.Path.unlink)\n"
         "runpy.run_path(sys.argv[0], run_name='__main__')\n")
# Leave acceptance copied and the next custody file truncated, without running cleanup handlers.
CRASH_CUSTODY = ("import os, pathlib, runpy, shutil, sys\n"
                 "real_copy, copied = shutil.copyfileobj, 0\n"
                 "def copy(source, target, *args, **kwargs):\n"
                 "    global copied\n"
                 "    if any(p == 'custody' or p.startswith('.custody-') for p in pathlib.Path(target.name).parts):\n"
                 "        copied += 1\n"
                 "        if copied == 2:\n"
                 "            target.write(source.read(1))\n"
                 "            target.flush()\n"
                 "            os.fsync(target.fileno())\n"
                 "            os._exit(9)\n"
                 "    return real_copy(source, target, *args, **kwargs)\n"
                 "shutil.copyfileobj = copy\n"
                 "sys.argv = sys.argv[1:]\n"
                 "runpy.run_path(sys.argv[0], run_name='__main__')\n")
# Two common formatter hooks over a queue on stdin: pre-commit's end-of-file-fixer and a no-double-blank-line check.
NEWLINE_HOOKS = ("import sys\n"
                 "data = sys.stdin.buffer.read()\n"
                 "if data.endswith(b'\\n\\n'):\n    sys.exit('end-of-file-fixer: the queue ends in more than one newline')\n"
                 "if b'\\n\\n\\n' in data:\n    sys.exit('the queue has two consecutive blank lines')\n")
PRODUCTS = {
    "greeting": {"greeting.py": "def greet(name):\n    return f\"Hello, {name}!\"\n"},
    "bad-greeting": {"greeting.py": "def greet(name):\n    return f\"Hi {name}\"\n"},
    "app": {"app.py": "import sys\nfrom greeting import greet\nfor name in sys.argv[1:]:\n    print(greet(name))\n"},
    "bad-app": {"app.py": "print('Bye')\n"},
    "notes": {"notes.txt": "notes\n"},
    "todo": {"todo.txt": "todo\n"},
}
GREET_CHECK = {"argv": [sys.executable, "-c", "from greeting import greet; assert greet('Ada') == 'Hello, Ada!'; print('greet ok')"],
               "stdout_contains": ["greet ok"], "contract_refs": ["R1"]}
APP_CHECK = {"argv": [sys.executable, "app.py", "Ada", "Lin"], "stdout_contains": ["Hello, Ada!", "Hello, Lin!"], "contract_refs": ["R1"]}
NOTES_CHECK = {"argv": [sys.executable, "-c", "import pathlib; assert pathlib.Path('notes.txt').read_text() == 'notes\\n'; print('notes ok')"],
               "stdout_contains": ["notes ok"], "contract_refs": ["R1"]}
TODO_CHECK = {"argv": [sys.executable, "-c", "import pathlib; assert pathlib.Path('todo.txt').read_text() == 'todo\\n'; print('todo ok')"],
              "stdout_contains": ["todo ok"], "contract_refs": ["R1"]}
CHAIN = [("t1", [], "Greeting interface 인사", [GREET_CHECK]), ("t2", ["t1"], "Greeting app [cli]", [APP_CHECK])]


class LoopFixture(unittest.TestCase):
    skills = PACKAGE_ROOT / "config" / "skills"

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="devlyn loop ✓ 한글 ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / "sitecustomize.py").write_text(
            "import importlib.machinery, importlib.util, pathlib, sys\n"
            "spec = importlib.machinery.PathFinder.find_spec('sitecustomize', [p for p in sys.path if pathlib.Path(p or '.').resolve() != pathlib.Path(__file__).resolve().parent])\n"
            "if spec is not None and spec.loader is not None:\n"
            "    spec.loader.exec_module(importlib.util.module_from_spec(spec))\n"
            "import shutil\nfrom types import SimpleNamespace\n"
            "shutil.disk_usage = lambda path: SimpleNamespace(total=100 * 1024**3, free=100 * 1024**3)\n",
            encoding="utf-8")
        self.queue_py = self.skills / "devlyn-ideate/scripts/queue.py"
        self.helper = self.skills / "_shared/task-complete.py"
        self.platform = self.skills / "_shared/platform-support.py"
        self.queue = runpy.run_path(str(self.queue_py))
        self.env = {key: value for key, value in os.environ.items() if key not in {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR"}}
        self.env["PYTHONPATH"] = str(self.root) + os.pathsep + self.env.get("PYTHONPATH", "")
        self.env["PYTHONDONTWRITEBYTECODE"] = "1"
        self.env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=str(self.root / "gitconfig"), GIT_CONFIG_COUNT="0",
                        GIT_AUTHOR_NAME="Fixture", GIT_AUTHOR_EMAIL="fixture@example.invalid",
                        GIT_COMMITTER_NAME="Fixture", GIT_COMMITTER_EMAIL="fixture@example.invalid")
        self.anchor = self.root / "repo"
        self.run_ok(["git", "init", "-q", "--initial-branch=main", str(self.anchor)])
        (self.anchor / ".gitignore").write_text(".devlyn/\n__pycache__/\n", encoding="utf-8")
        (self.anchor / "docs/specs").mkdir(parents=True)
        self.base_queue = b"# Intent Queue\n\n- [x] earlier legacy work\n- [ ] unrelated legacy intent\n"
        (self.anchor / "docs/specs/queue.md").write_bytes(self.base_queue)
        self.g("add", ".")
        self.g("commit", "-qm", "base")
        self.base = self.g("rev-parse", "HEAD")  # No remote: local loops neither need nor touch one.
        self.common = Path(self.g("rev-parse", "--path-format=absolute", "--git-common-dir"))
        self.config = self.root / "executor" / "behaviors.json"
        self.config.parent.mkdir()
        (self.config.parent / "executor.py").write_text(EXECUTOR, encoding="utf-8")
        self.behaviors = {}
        self.addCleanup(self.release_executor_holder)
        self.addCleanup(self.kill_hung_executor)

    def run_ok(self, argv, cwd=None):
        result = subprocess.run(argv, cwd=cwd or self.root, env=self.env, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout.strip()

    def g(self, *args, work=None):
        return self.run_ok(["git", "-C", str(work or self.anchor), *args])

    def plan(self, loop, tasks, behaviors, delivery="local-only", base=None):
        meta = self.queue["write_package"](self.anchor, loop, tasks, delivery=delivery, base=base or self.base)
        self.behaviors.update(behaviors)
        self.cli("add", meta)

    def cli(self, *args, code=0):
        result = subprocess.run([sys.executable, str(self.queue_py), *map(str, args)], cwd=self.root, env=self.env,
                                capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def drain_argv(self, local=True, unobservable=False, repo=None):
        self.config.write_text(json.dumps({"behaviors": self.behaviors, "products": PRODUCTS, "hold": HOLD,
                                           "platform_support": str(self.platform),
                                           "queue_lock": str(self.common / "devlyn-loops/queue.lock")}), encoding="utf-8")
        return [sys.executable, *(["-c", UNOBSERVABLE] if unobservable else []), str(self.queue_py), "drain", "--repo", str(repo or self.anchor),
                *(["--local-only"] if local else []), "--", sys.executable, str(self.config.parent / "executor.py"), str(self.config), "{packet}"]

    def drain(self, local=True, code=0, unobservable=False, repo=None, stdin=None):
        result = subprocess.run(self.drain_argv(local, unobservable, repo), cwd=self.root, env=self.env, capture_output=True, text=True,
                                encoding="utf-8", input=stdin)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def drain_until(self, *markers):
        """Start the driver and return it once each marker line appears on its progress stream, in order."""
        proc = subprocess.Popen(self.drain_argv(), cwd=self.root, env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, encoding="utf-8")
        watchdog = threading.Timer(300, proc.kill)
        watchdog.start()
        self.addCleanup(watchdog.cancel)
        self.addCleanup(lambda: (proc.kill(), proc.wait(), proc.stdout.close(), proc.stderr.close()))
        seen = []
        for marker in markers:
            for line in proc.stderr:
                seen.append(line)
                if marker in line:
                    break
            else:
                self.fail(f"driver ended before {marker!r}:\n{''.join(seen)}")
            yield proc

    def hold(self, path):
        flag = self.root / f"held-{hashlib.sha256(str(path).encode()).hexdigest()[:8]}"
        holder = subprocess.Popen([sys.executable, "-c", HOLD, str(self.platform), str(path), str(flag)],
                                  stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.addCleanup(lambda: (holder.kill(), holder.wait()))
        while not flag.exists():
            self.assertIsNone(holder.poll())
            time.sleep(0.05)
        return holder

    def release_executor_holder(self):
        pid_file = self.config.with_name("holder.pid")
        if pid_file.exists():
            pid = int(pid_file.read_text())
            pid_file.unlink()
            os.kill(pid, signal.SIGTERM)

    def kill_hung_executor(self):
        pid_file = self.config.with_name("hang.pid")
        if pid_file.exists():
            os.kill(int(pid_file.read_text()), signal.SIGTERM)
            pid_file.unlink()

    def calls(self, identity):
        path = self.config.with_name("calls-" + identity)
        return len(path.read_text(encoding="utf-8").splitlines()) if path.exists() else 0

    def receipt_path(self, identity):
        return self.common / "devlyn-completion" / hashlib.sha256(("devlyn/" + identity.replace(".", "/")).encode()).hexdigest()[:24] / "receipt.json"

    def receipt(self, identity):
        return json.loads(self.receipt_path(identity).read_text(encoding="utf-8"))

    def queue_at(self, rev, loop, git_dir=None):
        """The loop's queue file at `rev`, without its final newline."""
        return self.run_ok(["git", *(["--git-dir", str(git_dir)] if git_dir else ["-C", str(self.anchor)]), "show", f"{rev}:docs/specs/{loop}/queue.md"])

    def rows(self, rev, git_dir=None):
        """Every loop's rows at `rev`, by identity."""
        files = self.run_ok(["git", *(["--git-dir", str(git_dir)] if git_dir else ["-C", str(self.anchor)]), "ls-tree", "-r", "--name-only", rev, "--", "docs/specs"])
        return {row["identity"]: row for rel in files.splitlines() if re.fullmatch(r"docs/specs/[^/]+/queue\.md", rel)
                for row in self.queue["parse_queue"](self.queue_at(rev, rel.split("/")[2], git_dir).encode("utf-8")) if row["identity"]}

    def tasks(self, result):
        return {task["identity"]: task for task in result["tasks"]}

    def fault_drain(self, injection, *, local=True, code=0, root=None, status=False):
        """Inject an operational fault in the controller; executors and Git still run normally."""
        argv = self.drain_argv(local)
        if status:
            argv[2] = "status"
            del argv[argv.index("--"):]
        if root is not None:
            argv[argv.index("--"):argv.index("--")] = ["--worktree-root", str(root)]
        wrapper = ("import json, os, pathlib, runpy, subprocess, sys\n"
                   "q = runpy.run_path(sys.argv[1])\n"
                   "g = q['drain'].__globals__\n"
                   "h = q['shared']('task-complete')\n" + injection +
                   "\nsys.argv = sys.argv[1:]\n"
                   "q['shared']('platform-support')['configure_utf8']()\n"
                   "sys.exit(q['main']())\n")
        result = subprocess.run([sys.executable, "-c", wrapper, *argv[1:]], cwd=self.root, env=self.env,
                                capture_output=True, text=True, encoding="utf-8", timeout=120)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def independent(self, loop="bb"):
        self.plan(loop, [("t1", [], "Notes", [NOTES_CHECK])], {f"{loop}.t1": {"product": "notes"}})

    def assert_independent(self, result, loop="bb"):
        self.assertEqual(result["status"], "WAITING")
        self.assertEqual((self.tasks(result)[f"{loop}.t1"]["result"], self.calls(f"{loop}.t1")), ("accepted", 1))

    def pause_after_binding(self):
        """Leave t1 bound while holding every later task until the fixture corrupts the receipt."""
        return self.fault_drain(
            "def settle(*args):\n    raise g['Waiting']('fixture pause after binding')\ng['settle'] = settle\n"
            "real_advance = g['advance']\ndef advance(v, row, opts):\n"
            "    return real_advance(v, row, opts) if row['task'] == 't1' else 'fixture hold dependent'\n"
            "g['advance'] = advance\n")

    def skill_copy(self, root, version):
        shutil.copytree(self.skills, root)
        (root / ".devlyn-install.json").write_text(json.dumps({"version": version}), encoding="utf-8")
        self.queue_py = root / "devlyn-ideate/scripts/queue.py"
        return {"root": str(root), "version": version}

    def test_skill_version_mismatch_warns_without_blocking(self):
        # Prediction: each host's different project version adds exactly one warning, without changing status or
        # preventing execution; WAITING and DRAINED carry the same warning as their Markdown reports.
        skill = self.skill_copy(self.root / "running skills", "1.0.0")
        self.independent()
        for host in (".claude", ".agents"):
            with self.subTest(host=host):
                before = self.cli("status", "--repo", self.anchor)
                marker = self.anchor / host / "skills/.devlyn-install.json"
                marker.parent.mkdir(parents=True)
                marker.write_text('{"version": "2.0.0"}', encoding="utf-8")
                status = self.cli("status", "--repo", self.anchor / "docs")
                self.assertEqual(status["status"], "OK")
                self.assertEqual(status["skill"], skill)
                self.assertEqual({k: v for k, v in status.items() if k != "warnings"},
                                 {k: v for k, v in before.items() if k != "warnings"})
                warning, = status["warnings"]
                for text in (skill["root"], "1.0.0", str(marker), "2.0.0", "npx devlyn-cli@latest update"):
                    self.assertIn(text, warning)
                result = self.drain()
                self.assertEqual((result["status"], result["skill"], result["warnings"]), ("WAITING", skill, [warning]))
                self.assertEqual((self.tasks(result)["bb.t1"]["result"], self.calls("bb.t1")), ("accepted", 1))
                report, = result["reports"]
                self.assertIn("## Warnings\n\n- " + warning, Path(report).read_text(encoding="utf-8"))
                marker.unlink()
        (self.anchor / "docs/specs/queue.md").write_text("# Intent Queue\n", encoding="utf-8")
        marker.write_text('{"version": "2.0.0"}', encoding="utf-8")
        result = self.drain()
        self.assertEqual((result["status"], result["skill"], result["warnings"]), ("DRAINED", skill, [warning]))
        self.assertIn(warning, Path(result["reports"][0]).read_text(encoding="utf-8"))
        self.assertEqual(self.calls("bb.t1"), 1)

    def test_skill_matching_or_absent_markers_are_quiet(self):
        # Prediction: the fixture's actual running SKILLS root is reported (null without an install marker), and
        # absent or matching project markers leave warnings empty and add no Markdown warnings section.
        root = self.queue["SKILLS"]
        installed = root / ".devlyn-install.json"
        version = json.loads(installed.read_text(encoding="utf-8")).get("version") if installed.exists() else None
        skill = {"root": str(root), "version": version}
        self.independent()
        for host in (None, ".claude", ".agents"):
            with self.subTest(host=host):
                if host:
                    marker = self.anchor / host / "skills/.devlyn-install.json"
                    marker.parent.mkdir(parents=True)
                    marker.write_text(json.dumps({"version": version}), encoding="utf-8")
                for result in (self.cli("status", "--repo", self.anchor), self.drain()):
                    self.assertEqual((result["skill"], result["warnings"]), (skill, []))
                    for report in result.get("reports", []):
                        self.assertNotIn("## Warnings", Path(report).read_text(encoding="utf-8"))
        self.assertEqual(self.calls("bb.t1"), 1)

    def test_skill_running_project_copy_matches_its_marker(self):
        # Prediction: running the repository's own installed copy reports its version without warning about itself.
        skill = self.skill_copy(self.anchor / ".agents/skills", "3.0.0")
        for result in (self.cli("status", "--repo", self.anchor), self.drain()):
            self.assertEqual((result["skill"], result["warnings"]), (skill, []))

    def test_skill_unreadable_markers_warn_without_crashing(self):
        # Prediction: invalid or deeply nested JSON, shape, UTF-8 and an OSError are diagnostics, never controller failures; the
        # executor still runs once, and reports contain the exact warning returned by status and drain.
        self.independent()
        root = str(self.queue["SKILLS"])
        for host in (".claude", ".agents"):
            marker = self.anchor / host / "skills/.devlyn-install.json"
            marker.parent.mkdir(parents=True)
            for data in (b"{", b"[]", b"\xff", b"[" * 2000 + b"]" * 2000, None):
                with self.subTest(host=host, data=data[:20] if data else data):
                    if data is None:
                        marker.mkdir()
                    else:
                        marker.write_bytes(data)
                    status = self.cli("status", "--repo", self.anchor)
                    warning, = status["warnings"]
                    for text in (root, str(marker), "unreadable", "npx devlyn-cli@latest update"):
                        self.assertIn(text, warning)
                    result = self.drain()
                    self.assertEqual((status["status"], result["status"], result["warnings"]), ("OK", "WAITING", [warning]))
                    self.assertEqual((self.tasks(result)["bb.t1"]["result"], self.calls("bb.t1")), ("accepted", 1))
                    self.assertIn(warning, Path(result["reports"][0]).read_text(encoding="utf-8"))
                    marker.rmdir() if data is None else marker.unlink()

    def test_skill_unreadable_running_marker_skips_version_comparisons(self):
        # Prediction: an unreadable running marker warns once, with no comparisons against its unknown version;
        # unreadable repository markers still warn, including in status/drain's BLOCKED fallback.
        skill = self.skill_copy(self.root / "running skills", "1.0.0")
        skill["version"] = None
        running = Path(skill["root"]) / ".devlyn-install.json"
        # Python 3.14's C scanner accepts this depth; use the stdlib recursive scanner to exercise RecursionError.
        wrapper = self.root / "recursive-json-queue.py"
        wrapper.write_text("import json, json.scanner, runpy\n"
                           "json._default_decoder.scan_once = json.scanner.py_make_scanner(json._default_decoder)\n"
                           f"runpy.run_path({str(self.queue_py)!r}, run_name='__main__')\n", encoding="utf-8")
        self.queue_py = wrapper
        markers = [self.anchor / host / "skills/.devlyn-install.json" for host in (".claude", ".agents")]
        for data in (b"{", b"[" * 2000 + b"]" * 2000):
            with self.subTest(data=data[:20]):
                running.write_bytes(data)
                for marker in markers:
                    marker.parent.mkdir(parents=True, exist_ok=True)
                    marker.write_text('{"version": "2.0.0"}', encoding="utf-8")
                status = self.cli("status", "--repo", self.anchor)
                warning, = status["warnings"]
                self.assertIn(str(running), warning)
                self.assertIn("unreadable", warning)
                result = self.drain()
                self.assertEqual((status["status"], status["skill"]), ("OK", skill))
                self.assertEqual((result["status"], result["skill"], result["warnings"]), ("WAITING", skill, [warning]))
                markers[0].write_bytes(b"{")
                status = self.cli("status", "--repo", self.anchor)
                own_warning, repo_warning = status["warnings"]
                self.assertEqual(own_warning, warning)
                self.assertIn(str(markers[0]), repo_warning)
                self.assertIn("unreadable", repo_warning)
                (self.anchor / "docs/specs/queue.md").write_bytes(b"\xff")
                for result in (self.cli("status", "--repo", self.anchor, code=1), self.drain(code=1)):
                    self.assertEqual((result["status"], result["skill"], result["warnings"]),
                                     ("BLOCKED", skill, status["warnings"]))
                (self.anchor / "docs/specs/queue.md").write_bytes(self.base_queue)

    def test_skill_absent_running_marker_still_compares_repository_versions(self):
        # Prediction: an absent running marker keeps the null-version comparison with readable repository markers.
        skill = self.skill_copy(self.root / "running skills", "1.0.0")
        (Path(skill["root"]) / ".devlyn-install.json").unlink()
        skill["version"] = None
        marker = self.anchor / ".agents/skills/.devlyn-install.json"
        marker.parent.mkdir(parents=True)
        marker.write_text('{"version": "2.0.0"}', encoding="utf-8")
        for result in (self.cli("status", "--repo", self.anchor), self.drain()):
            self.assertEqual(result["skill"], skill)
            warning, = result["warnings"]
            self.assertIn(str(marker), warning)
            self.assertIn('version "2.0.0"', warning)
            self.assertNotIn("unreadable", warning)

    def test_skill_details_survive_repository_lookup_failure(self):
        # Prediction: repository() failing before it returns an anchor still prints BLOCKED JSON with diagnostics,
        # without a traceback, for both status and drain.
        skill = self.skill_copy(self.root / "running skills", "1.0.0")
        for action in ("status", "drain"):
            with self.subTest(action=action):
                argv = [sys.executable, str(self.queue_py), action, "--repo", str(self.root)]
                if action == "drain":
                    argv += ["--", sys.executable, "-c", "pass", "{packet}"]
                result = subprocess.run(argv, cwd=self.root, env=self.env, capture_output=True, text=True, encoding="utf-8")
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertNotIn("Traceback", result.stdout + result.stderr)
                payload = json.loads(result.stdout)
                self.assertEqual((payload["status"], payload["skill"], payload["warnings"]), ("BLOCKED", skill, []))
                self.assertIn("not a git repository", payload["reason"])

    def test_skill_details_survive_blocked_outcomes(self):
        # Prediction: preflight, lock and authoritative-queue failures keep BLOCKED and their existing reason,
        # but still name the running copy and version mismatch, including when --repo names a subdirectory.
        skill = self.skill_copy(self.root / "running skills", "1.0.0")
        marker = self.anchor / ".claude/skills/.devlyn-install.json"
        marker.parent.mkdir(parents=True)
        marker.write_text('{"version": "2.0.0"}', encoding="utf-8")
        expected = self.cli("status", "--repo", self.anchor)["warnings"]
        invalid = self.cli("drain", "--repo", self.anchor / "docs", "--", sys.executable, "-c", "pass", code=1)
        self.assertIn("executor argv must contain {packet}", invalid["reason"])
        holder = self.hold(self.common / "devlyn-loops/drain.lock")
        locked = self.drain(code=1)
        self.assertIn("another drain is active", locked["reason"])
        holder.kill()
        holder.wait()
        (self.anchor / "docs/specs/queue.md").write_bytes(b"\xff")
        for result in (invalid, locked, self.cli("status", "--repo", self.anchor / "docs", code=1), self.drain(code=1)):
            self.assertEqual((result["status"], result["skill"], result["warnings"]), ("BLOCKED", skill, expected))

    def test_review_01_failed_verdict_without_product(self):
        # Prediction: the bound verdict remains failed without the redundant product field, before and after attachment;
        # no dependent executes and an independent loop completes. Older valid ACCEPTED receipts omit product too.
        self.plan("aa", CHAIN, {"aa.t1": {"product": "bad-greeting"}, "aa.t2": {"product": "app"}})
        self.pause_after_binding()
        path = self.receipt_path("aa.t1")
        receipt = self.receipt("aa.t1")
        self.assertEqual((receipt["acceptance"]["verdict"], receipt.pop("product")), ("FAILED", "FAILED"))
        path.write_text(json.dumps(receipt), encoding="utf-8")
        self.assertEqual(self.cli("status", "--repo", self.anchor)["counts"]["failed"], 1)
        self.independent()
        result = self.drain()
        self.assert_independent(result)
        task = self.tasks(result)["aa.t1"]
        self.assertEqual((task["result"], task["delivery"], self.calls("aa.t2")), ("failed", "FAILED", 0))
        self.assertEqual(self.rows(self.receipt("aa.t1")["publish_sha"])["aa.t1"]["mark"], "F")
        self.assertNotIn("product", self.receipt("bb.t1"))

    def test_review_01_inconsistent_verdict_product(self):
        # Prediction: either contradictory verdict/product pair invalidates only its task and preserves its artifacts.
        originals = {}
        for loop, product, contradictory in (("aa", "greeting", "FAILED"), ("cc", "bad-greeting", "ACCEPTED")):
            self.plan(loop, CHAIN, {f"{loop}.t1": {"product": product}, f"{loop}.t2": {"product": "app"}})
            self.pause_after_binding()
            path = self.receipt_path(f"{loop}.t1")
            receipt = self.receipt(f"{loop}.t1")
            receipt["product"] = contradictory
            path.write_text(json.dumps(receipt), encoding="utf-8")
            originals[path] = path.read_bytes()
        self.independent()
        result = self.drain()
        self.assert_independent(result)
        for loop in ("aa", "cc"):
            self.assertIn("verdict/product", self.tasks(result)[f"{loop}.t1"]["reason"])
            self.assertEqual((self.calls(f"{loop}.t1"), self.calls(f"{loop}.t2")), (1, 0))
        self.assertEqual({path: path.read_bytes() for path in originals}, originals)

    def test_review_02_unrelated_tracked_queues(self):
        # Prediction: tracked queues with no row of their directory's loop are ignored by status and drain.
        for loop, body in (("unrelated", "- [ ] ordinary documentation task\n"), ("empty", "")):
            path = self.anchor / f"docs/specs/{loop}/queue.md"
            path.parent.mkdir()
            path.write_text(body, encoding="utf-8")
        self.g("add", "docs/specs")
        self.g("commit", "-qm", "unrelated queues")
        self.independent()
        status = self.cli("status", "--repo", self.anchor)
        self.assertEqual(status["next"], "bb.t1")
        result = self.drain()
        self.assert_independent(result)
        self.assertEqual(set(self.tasks(result)), {"bb.t1"})

    def test_review_02_damaged_proven_queue(self):
        # Prediction: a tracked loop proven by HEAD remains authoritative even when its checkout queue loses every row.
        path = self.anchor / "docs/specs/known/queue.md"
        path.parent.mkdir()
        path.write_text(self.queue["row_line"]("known.t1", "Known") + "\n", encoding="utf-8")
        self.g("add", "docs/specs")
        self.g("commit", "-qm", "known loop")
        self.independent()
        for body in (None, "", "- [ ] unrelated replacement\n"):
            with self.subTest(body=body):
                if body is None:
                    path.unlink()
                else:
                    path.write_text(body, encoding="utf-8")
                result = self.drain(code=1)
                self.assertEqual((result["status"], self.calls("bb.t1")), ("BLOCKED", 0))

    def test_review_02_staged_deletion_of_proven_queue(self):
        # Prediction: removing a known loop queue from both checkout and index still blocks status and drain;
        # HEAD remains proof of that loop, so independent execution cannot silently bypass its missing queue.
        path = self.anchor / "docs/specs/known/queue.md"
        path.parent.mkdir()
        path.write_text(self.queue["row_line"]("known.t1", "Known") + "\n", encoding="utf-8")
        self.g("add", "docs/specs")
        self.g("commit", "-qm", "known loop")
        self.g("rm", str(path))
        self.independent()
        self.assertEqual(self.cli("status", "--repo", self.anchor, code=1)["status"], "BLOCKED")
        result = self.drain(code=1)
        self.assertEqual((result["status"], self.calls("bb.t1")), ("BLOCKED", 0))

    @unittest.skipIf(os.name == "nt", "fake remote uses POSIX wrappers")
    def test_review_03_drain_allocation_reconciles_direct_receipt(self):
        # Prediction: a queue allocation still sweeps an older direct PR merged manually; it cleans owned resources.
        _, data = self.remote(pending=True)
        work = self.root / "direct"
        allocated = json.loads(self.run_ok([sys.executable, str(self.helper), "allocate", "--repo", str(self.anchor),
                                           "--task", "direct", "--branch", "direct-task", "--worktree", str(work),
                                           "--repository", "test/project", "--remote", "origin", "--base", "main"]))
        (work / "direct.txt").write_text("direct\n", encoding="utf-8")
        self.g("add", "direct.txt", work=work)
        self.g("commit", "-qm", "direct source", work=work)
        (work / ".devlyn").mkdir()
        (work / ".devlyn/check.log").write_text("checked\n", encoding="utf-8")
        acceptance = work / ".devlyn/acceptance.json"
        acceptance.write_text(json.dumps({"kind": "direct", "task": "direct", "source_sha": self.g("rev-parse", "HEAD", work=work),
                                          "checks": [{"command": "manual", "evidence": ".devlyn/check.log"}]}), encoding="utf-8")
        self.run_ok([sys.executable, str(self.helper), "complete", "--receipt", allocated["receipt"], "--acceptance", str(acceptance),
                     "--mode", "pr", "--writers-stopped"])
        self.assertEqual(self.merge_pr(data, 1).returncode, 0)
        self.plan("bb", [("t1", [], "Notes", [NOTES_CHECK])], {"bb.t1": {"product": "notes"}}, delivery="auto")
        result = self.drain(local=False)
        self.assert_independent(result)
        receipt = json.loads(Path(allocated["receipt"]).read_text(encoding="utf-8"))
        self.assertEqual((receipt.get("delivery"), receipt.get("status")), ("COMPLETE", "COMPLETE"))
        self.assertFalse(work.exists())
        self.assertEqual(self.g("branch", "--list", "direct-task"), "")

    @unittest.skipIf(os.name == "nt", "fake remote uses POSIX wrappers")
    def test_review_03_complete_receipt_retries_retained_cleanup(self):
        # Prediction: a later queue allocation retries retained scratch cleanup on an already COMPLETE receipt.
        self.remote(pending=False)
        self.plan("aa", [CHAIN[0]], {"aa.t1": {"product": "greeting"}}, delivery="auto")
        self.fault_drain("real_clean = h['clean_scratch']\n"
                         "def clean(receipt, *args):\n    if receipt['task'] == 'aa.t1':\n"
                         "        raise h['CompletionError']('fixture retained scratch')\n    return real_clean(receipt, *args)\n"
                         "h['completion_result'].__globals__['clean_scratch'] = clean\n", local=False)
        self.assertEqual((self.receipt("aa.t1")["status"], self.receipt("aa.t1")["scratch_cleanup"]["status"]), ("COMPLETE", "RETAINED"))
        self.plan("bb", [("t1", [], "Notes", [NOTES_CHECK])], {"bb.t1": {"product": "notes"}}, delivery="auto")
        result = self.drain(local=False)
        self.assert_independent(result)
        self.assertEqual(self.receipt("aa.t1")["scratch_cleanup"]["status"], "CLEAN")
        self.assertEqual(self.calls("aa.t1"), 1)

    def assert_invalid_bound_field(self, field, value):
        self.plan("aa", CHAIN, {"aa.t1": {"product": "greeting"}, "aa.t2": {"product": "app"}})
        self.pause_after_binding()
        path = self.receipt_path("aa.t1")
        receipt = self.receipt("aa.t1")
        receipt[field] = value
        path.write_text(json.dumps(receipt), encoding="utf-8")
        original = path.read_bytes()
        self.independent()
        result = self.drain()
        self.assert_independent(result)
        self.assertIn("recovery conflict:", self.tasks(result)["aa.t1"]["reason"])
        self.assertEqual((self.calls("aa.t1"), self.calls("aa.t2"), path.read_bytes()), (1, 0, original))

    def test_review_04_nul_terminal_path(self):
        # Prediction: a NUL terminal path invalidates only its owner, without rewriting it or running a dependent.
        self.assert_invalid_bound_field("queue", {"file": "bad\0path", "commit": self.base})

    def test_review_04_list_bound_files(self):
        # Prediction: list-valued bound files invalidate only their owner, without entering helper custody validation.
        self.assert_invalid_bound_field("files", [])

    def test_review_04_non_utf8_execution_log(self):
        # Prediction: undecodable execution history waits at its read, preserves the bytes and prevents a second spawn.
        self.plan("aa", CHAIN, {"aa.t1": {"product": "greeting", "exit_now": 1}, "aa.t2": {"product": "app"}})
        self.drain()
        log = self.receipt_path("aa.t1").with_name("executions.log")
        log.write_bytes(b"\xff interrupted start\n")
        self.independent()
        result = self.drain()
        self.assert_independent(result)
        self.assertIn("executions.log is not UTF-8", self.tasks(result)["aa.t1"]["reason"])
        self.assertEqual((self.calls("aa.t1"), self.calls("aa.t2"), log.read_bytes()), (1, 0, b"\xff interrupted start\n"))

    def test_review_05_origin_stat_probe(self):
        # Prediction: an origin is_dir failure is a package-cleanup diagnostic.
        from unittest import mock
        with mock.patch.object(Path, "is_dir", side_effect=PermissionError("origin stat denied")):
            notes = self.queue["clean"](self.common, {"aa": {"origin": str(self.anchor)}})
        self.assertIn("origin stat denied", " ".join(notes))

    def test_review_05_summary_stat_probe(self):
        # Prediction: a summary existence failure remains diagnostic and preserves both successful task results.
        self.plan("aa", [CHAIN[0]], {"aa.t1": {"product": "greeting"}})
        self.independent()
        result = self.fault_drain(
            "real_summary = g['summary']\nreal_exists = pathlib.Path.exists\ninspecting = False\n"
            "def exists(path, *args, **kwargs):\n    if inspecting and path.name == 't1':\n"
            "        raise PermissionError('workspace stat denied')\n    return real_exists(path, *args, **kwargs)\n"
            "def summary(*args):\n    global inspecting\n    inspecting = True\n"
            "    try:\n        return real_summary(*args)\n    finally:\n        inspecting = False\n"
            "pathlib.Path.exists = exists\ng['summary'] = summary\n")
        self.assert_independent(result)
        self.assertEqual(self.tasks(result)["aa.t1"]["result"], "accepted")
        self.assertIn("workspace stat denied", " ".join(result["cleanup"]))

    def test_review_05_prune_stat_probe(self):
        # Prediction: a pruning existence failure is a cleanup diagnostic instead of escaping the final drain result.
        from unittest import mock
        root = self.root / "prune"
        v = {"states": {"aa.t1": {"receipt": {"delivery": "COMPLETE", "linked": True, "worktree": str(root / "aa/t1")}}},
             "cleanup": [], "anchor": self.anchor}
        with mock.patch.object(Path, "exists", side_effect=PermissionError("prune stat denied")):
            self.queue["prune_parents"](v, root)
        self.assertIn("prune stat denied", " ".join(v["cleanup"]))

    def test_review_06_canonical_registered_parent(self):
        # Prediction: pruning uses the helper's canonical registrations even when Git spells the path differently
        # (Windows C:/ vs C:\\). Missing registered siblings also retain their empty parent, on every test host.
        from unittest import mock
        root = self.root / "prune"
        parent = root / "aa"
        parent.mkdir(parents=True)
        work = parent / "t1"
        receipt = {"delivery": "COMPLETE", "linked": True, "worktree": str(work), "common_gitdir": str(self.common)}
        helper = self.queue["shared"]("task-complete")
        for registered in (work, parent / "missing-sibling"):
            with self.subTest(registered=registered):
                parent.mkdir(parents=True, exist_ok=True)
                v = {"states": {"aa.t1": {"receipt": receipt}}, "cleanup": [], "anchor": self.anchor}
                spelling = str(registered).replace("\\", "/") if os.name == "nt" else str(registered).replace("/", "\\")
                with mock.patch.dict(helper["prune_empty_parents"].__globals__, registrations=mock.Mock(return_value={str(registered): {"worktree": spelling}})), \
                        mock.patch.dict(self.queue["prune_parents"].__globals__, git=mock.Mock(return_value="worktree " + spelling + "\0\0")):
                    self.queue["prune_parents"](v, root)
                self.assertTrue(parent.is_dir(), "registered worktree's parent was pruned")
                self.assertIn("registered", " ".join(v["cleanup"]))

    def test_require_merged_on_base_receipt(self):
        # Prediction: settled publish_sha permits dependents only when present in their base.
        self.g("commit", "--allow-empty", "-qm", "delivered outside helper")
        published = self.g("rev-parse", "HEAD")
        receipt = {"delivery": "COMPLETE", "publish_sha": published}
        row = {"loop": "inv", "task": "t2", "identity": "inv.t2"}
        v = {"anchor": self.anchor, "packages": {"inv": {"tasks": {"t2": {"depends_on": ["t1"]}}}},
             "states": {"inv.t1": {"receipt": receipt}}, "manifests": {"inv": {"base_ref": "main"}}}
        for allocated in (False, True):
            with self.subTest(allocated=allocated):
                self.queue["require_merged"](v, row, published, allocated=allocated)
                with self.assertRaises(self.queue["LoopError"]) as error:
                    self.queue["require_merged"](v, row, self.base, allocated=allocated)
                self.assertIn(f"delivered commit {published}", str(error.exception))
                if not allocated:
                    self.assertIn("restore that commit on origin/main", str(error.exception))
        receipt["delivery"] = "PR"
        with self.assertRaises(self.queue["LoopError"]):
            self.queue["require_merged"](v, row, published)
        receipt.update(delivery="COMPLETE", merge={"mergeCommit": {"oid": published}})
        receipt["publish_sha"] = self.base
        with self.assertRaisesRegex(self.queue["LoopError"], f"delivered merge {published}"):
            self.queue["require_merged"](v, row, self.base)
        self.queue["require_merged"](v, row, published)

    def test_review_07_helper_exception_contract_documented(self):
        # Prediction: the inherited helper wrapper still contains all three errors; docs describe that exact exception.
        from unittest import mock
        helper = self.queue["shared"]("task-complete")
        for error in (TypeError, KeyError, ValueError):
            with self.subTest(error=error), mock.patch.dict(helper, allocate=mock.Mock(side_effect=error("helper defect"))):
                with self.assertRaisesRegex(self.queue["LoopError"], "helper defect"):
                    self.queue["task_complete"]("allocate")
        text = (self.skills / "devlyn-ideate/references/loop.md").read_text(encoding="utf-8")
        self.assertFalse("Programming errors are not converted to waits." in text, "blanket programming-error guarantee remains")
        for error in ("TypeError", "KeyError", "ValueError"):
            self.assertIn(error, text)

    @unittest.skipIf(os.name == "nt", "fake remote uses POSIX wrappers")
    def test_robust_01_base_refresh(self):
        # Prediction: a failed targeted fetch leaves aa unallocated, its dependent waiting, and bb accepted; repair retries once.
        self.remote(pending=False)
        self.plan("aa", CHAIN, {"aa.t1": {"product": "greeting"}, "aa.t2": {"product": "app"}}, delivery="auto")
        self.independent()
        for failure in ("fetch exit", "PermissionError"):
            with self.subTest(failure=failure):
                injection = ("real = subprocess.run\ndef run(argv, **kw):\n"
                             "    if argv[0] == 'git' and 'fetch' in argv:\n" +
                             ("        raise PermissionError('fetch denied')\n" if failure == "PermissionError" else
                              "        return subprocess.CompletedProcess(argv, 1, stdout='', stderr='fetch denied')\n") +
                             "    return real(argv, **kw)\nsubprocess.run = run\n")
                result = self.fault_drain(injection, local=False)
                self.assert_independent(result)
                self.assertIn("restore remote access or the base ref", self.tasks(result)["aa.t1"]["reason"])
                self.assertFalse(self.receipt_path("aa.t1").exists())
                self.assertEqual((self.calls("aa.t1"), self.calls("aa.t2")), (0, 0))
        self.assertEqual(self.tasks(self.drain(local=False))["aa.t2"]["result"], "accepted")
        self.assertEqual((self.calls("aa.t1"), self.calls("aa.t2"), self.calls("bb.t1")), (1, 1, 1))

    def test_robust_02_executor_start(self):
        # Prediction: either spawn error preserves start/not-started, permits bb, and retries aa only on a later drain.
        self.plan("aa", CHAIN, {"aa.t1": {"product": "greeting"}, "aa.t2": {"product": "app"}})
        self.independent()
        for failure in ("FileNotFoundError", "PermissionError"):
            with self.subTest(failure=failure):
                result = self.fault_drain(
                    "real = subprocess.Popen\ndef spawn(argv, **kw):\n"
                    "    if pathlib.Path(kw.get('cwd') or '.').parts[-2:] == ('aa', 't1') and 'executor.py' in str(argv):\n"
                    f"        raise {failure}('executor unavailable')\n"
                    "    return real(argv, **kw)\nsubprocess.Popen = spawn\n")
                self.assert_independent(result)
                task = self.tasks(result)["aa.t1"]
                self.assertIn("executor blocked: executor could not start", task["reason"])
                self.assertIsNone(task["terminal"])
                log = self.receipt_path("aa.t1").with_name("executions.log").read_text(encoding="utf-8")
                self.assertTrue(log.splitlines()[-2].endswith(" start"))
                self.assertIn("not started:", log.splitlines()[-1])
                self.assertEqual((self.calls("aa.t1"), self.calls("aa.t2")), (0, 0))
        self.assertEqual(self.tasks(self.drain())["aa.t2"]["result"], "accepted")
        self.assertEqual((self.calls("aa.t1"), self.calls("aa.t2")), (1, 1))

    def test_robust_05_missing_receipt(self):
        # Prediction: the occupied receipt directory is invalid on every read; nothing is removed/adopted and bb completes.
        self.plan("aa", CHAIN, {"aa.t1": {"product": "greeting"}, "aa.t2": {"product": "app"}})
        self.independent()
        directory = self.receipt_path("aa.t1").parent
        (directory / "scratch").mkdir(parents=True)
        sentinel = directory / "sentinel"
        sentinel.write_text("keep", encoding="utf-8")
        for _ in range(2):
            result = self.drain()
            self.assert_independent(result)
            reason = self.tasks(result)["aa.t1"]["reason"]
            self.assertIn("receipt missing at", reason)
            self.assertIn("remove only confirmed interrupted-allocation artifacts", reason)
            self.assertIn(reason, " ".join(self.cli("status", "--repo", self.anchor)["blockers"]))
            self.assertEqual((sentinel.read_text(encoding="utf-8"), self.calls("aa.t1"), self.calls("aa.t2")), ("keep", 0, 0))
        shutil.rmtree(directory)  # Explicit verified fixture recovery, never driver recovery.
        self.assertEqual(self.tasks(self.drain())["aa.t2"]["result"], "accepted")
        self.assertEqual((self.calls("aa.t1"), self.calls("aa.t2")), (1, 1))

    def test_robust_07_first_receipt_write(self):
        # Prediction: allocation's first receipt write can fail after mkdir; bb completes now and aa waits invalid next drain.
        self.plan("aa", CHAIN, {"aa.t1": {"product": "greeting"}, "aa.t2": {"product": "app"}})
        self.independent()
        result = self.fault_drain(
            "hg = h['allocate'].__globals__\nreal = hg['atomic_json']\n"
            "def write(path, value):\n"
            "    if value.get('task') == 'aa.t1':\n        raise PermissionError('first receipt denied')\n"
            "    return real(path, value)\nhg['atomic_json'] = write\n")
        self.assert_independent(result)
        self.assertIn("first receipt denied", self.tasks(result)["aa.t1"]["reason"])
        self.assertFalse(self.receipt_path("aa.t1").exists())
        self.assertTrue(self.receipt_path("aa.t1").parent.is_dir())
        self.assertIn("receipt missing", self.tasks(self.drain())["aa.t1"]["reason"])
        self.assertEqual((self.calls("aa.t1"), self.calls("aa.t2")), (0, 0))

    @unittest.skipIf(os.name == "nt", "fake delivery and symlinks require POSIX")
    def test_robust_06_parent_cleanup_boundaries(self):
        # Prediction: parent pruning retries after permission failure; nonempty, registered, symlink and outside-root paths
        # remain untouched. Custom roots survive, custody stays reachable, and completed tasks never execute twice.
        self.remote(pending=False)
        self.plan("aa", [CHAIN[0]], {"aa.t1": {"product": "greeting"}}, delivery="auto")
        root = self.root / "custom"
        result = self.fault_drain(
            "real = pathlib.Path.rmdir\ndef remove(path):\n"
            "    if path.name == 'aa' and path.parent.name == 'custom':\n        raise PermissionError('parent denied')\n"
            "    return real(path)\npathlib.Path.rmdir = remove\n", local=False, root=root)
        self.assertEqual(self.tasks(result)["aa.t1"]["delivery"], "COMPLETE")
        self.assertIn("parent cleanup retained:", " ".join(result["cleanup"]))
        parent = root / "aa"
        self.assertTrue(parent.is_dir())
        self.assertFalse((parent / "t1").exists())
        sentinel = parent / "keep"
        sentinel.write_text("keep", encoding="utf-8")
        self.fault_drain("", local=False, root=root)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")
        sentinel.unlink()
        # Another registered sibling worktree holds its parent even if the task's own workspace is gone.
        self.g("worktree", "add", "-q", "-b", "sibling", str(parent / "sibling"))
        self.fault_drain("", local=False, root=root)
        self.assertTrue((parent / "sibling").is_dir())
        self.g("worktree", "remove", str(parent / "sibling"))
        # A different drain root cannot prune the original allocation.
        self.drain(local=False)
        self.assertTrue(parent.exists())
        parent.rmdir()
        outside = self.root / "outside"
        outside.mkdir()
        parent.symlink_to(outside, target_is_directory=True)
        self.fault_drain("", local=False, root=root)
        self.assertTrue(parent.is_symlink() and outside.is_dir())
        parent.unlink()
        parent.mkdir()
        self.fault_drain("", local=False, root=root)
        self.assertFalse(parent.exists())
        self.assertTrue(root.is_dir())
        completed = json.loads(self.run_ok([sys.executable, str(self.helper), "complete", "--receipt",
                                           str(self.receipt_path("aa.t1"))]))
        self.assertEqual(completed["status"], "COMPLETE")
        self.assertTrue(root.is_dir(), "completion must retain a custom root outside every named root")
        receipt = self.receipt("aa.t1")
        self.assertEqual(self.g("rev-parse", receipt["recovery_ref"]), receipt["publish_sha"])
        self.assertTrue(self.receipt_path("aa.t1").with_name("custody").is_dir())
        self.assertEqual(self.calls("aa.t1"), 1)

    def test_robust_08_recovery_conflicts(self):
        # Prediction: malformed packets, duplicate/foreign claims and damaged recovery refs invalidate only implicated tasks;
        # aa's sibling remains behind its writer barrier, bb completes, and invalid evidence never supplies a frontier.
        self.plan_checker("aa", [GREET_CHECK, NOTES_CHECK], {"aa.t1": {"product": "greeting", "exit_now": 1},
                                                            "aa.t2": {"product": "notes"}, "aa.t3": {"check_only": True}})
        self.drain()
        packet = self.receipt_path("aa.t1").with_name("packet.json")
        original = packet.read_bytes()
        for index, malformed in enumerate(("null", "{}", '{"contract":{"path":"outside"},"worktree":"/other"}')):
            with self.subTest(packet=malformed):
                packet.write_text(malformed, encoding="utf-8")
                self.independent(f"bb{index}")
                result = self.drain()
                self.assert_independent(result, f"bb{index}")
                self.assertIn("recovery conflict:", self.tasks(result)["aa.t1"]["reason"])
                self.assertEqual((self.calls("aa.t1"), self.calls("aa.t2"), packet.read_text(encoding="utf-8")), (1, 0, malformed))
        packet.write_bytes(original)
        self.behaviors["aa.t1"] = {"product": "greeting"}
        self.drain()
        receipt = self.receipt("aa.t1")
        self.g("update-ref", "-d", receipt["recovery_ref"])
        self.independent("cc")
        result = self.drain()
        self.assert_independent(result, "cc")
        self.assertEqual(self.tasks(result)["aa.t1"]["result"], "pending")
        self.assertIn("recovery conflict:", self.tasks(result)["aa.t1"]["reason"])
        self.assertNotIn("Whole-loop acceptance: ACCEPTED", self.report("aa"))

    def test_robust_09_missing_prerequisite(self):
        # Prediction: a missing authoritative prerequisite row invalidates the dependent, leaving an unrelated loop runnable.
        meta = self.queue["write_package"](self.anchor, "aa", CHAIN, base=self.base)
        (meta.parent / "queue.md").write_text(self.queue["row_line"]("aa.t2", CHAIN[1][2]) + "\n", encoding="utf-8")
        self.g("add", "docs/specs/aa")
        self.g("commit", "-qm", "legacy queue missing prerequisite")
        self.independent()
        result = self.drain()
        self.assert_independent(result)
        self.assertIn("aa.t1, which is not queued", self.tasks(result)["aa.t2"]["reason"])
        self.assertIn("new loop", self.tasks(result)["aa.t2"]["reason"])
        self.assertEqual(self.calls("aa.t2"), 0)

    def test_robust_10_task_phases(self):
        # Prediction: each operational phase failure lets independent work finish; resumption reuses submission/bound result.
        for index, (phase, target) in enumerate((("inputs", "inputs"), ("acceptance", "acceptance"),
                                               ("custody binding", "accept"), ("terminal transition", "attach"))):
            with self.subTest(phase=phase):
                loop = f"aa{index}"
                self.plan(loop, [CHAIN[0]], {f"{loop}.t1": {"product": "greeting"}})
                self.independent(f"bb{index}")
                if target == "inputs":
                    injection = ("real = g['ensure_packet']\ndef call(v, row, *args):\n"
                                 f"    if row['identity'] == '{loop}.t1':\n        raise g['LoopError']('inputs unavailable; restore package')\n"
                                 "    return real(v, row, *args)\ng['ensure_packet'] = call\n")
                elif target == "acceptance":
                    injection = ("a = q['acceptance']()\nreal = a['accept']\ndef call(packet, *args):\n"
                                 f"    if json.loads(packet.read_text(encoding='utf-8'))['task'] == '{loop}.t1':\n        raise a['AcceptanceError']('checks unavailable')\n"
                                 "    return real(packet, *args)\na['accept'] = call\n")
                else:
                    injection = ("real = g['task_complete']\ndef call(action, **kw):\n"
                                 f"    if action == '{target}' and json.loads(pathlib.Path(kw['receipt']).read_text(encoding='utf-8'))['task'] == '{loop}.t1':\n"
                                 "        raise g['LoopError']('injected durable step failure')\n"
                                 "    return real(action, **kw)\ng['task_complete'] = call\n")
                result = self.fault_drain(injection)
                self.assert_independent(result, f"bb{index}")
                self.assertIn(phase + " blocked:", self.tasks(result)[f"{loop}.t1"]["reason"])
                self.assertEqual(self.calls(f"{loop}.t1"), 0 if target == "inputs" else 1)
                bound = self.receipt(loop + ".t1")
                self.assertEqual(self.tasks(self.drain())[f"{loop}.t1"]["result"], "accepted")
                self.assertEqual(self.calls(f"{loop}.t1"), 1)
                if target == "attach":
                    self.assertEqual(self.receipt(loop + ".t1")["source_sha"], bound["source_sha"])

    def test_robust_11_observe_once(self):
        # Prediction: one live-writer observation returns WAITING, never sleeps/adopts/respawns, and bb finishes.
        self.plan("aa", CHAIN, {"aa.t1": {"product": "greeting", "exit_now": 1}, "aa.t2": {"product": "app"}})
        self.drain()
        log = self.receipt_path("aa.t1").with_name("executions.log")
        log.write_text("interrupted start\n", encoding="utf-8")
        self.independent()
        result = self.fault_drain(
            "checks = 0\ndef observe(work):\n    global checks\n    checks += 1\n"
            "    if checks > 1:\n        raise AssertionError('writer observed twice in one drain')\n"
            "    raise h['WriterActive']('writer 4242 active')\nh['stopped_writers'] = observe\n")
        self.assert_independent(result)
        self.assertIn("interrupted execution still active", self.tasks(result)["aa.t1"]["reason"])
        self.assertEqual((self.calls("aa.t1"), self.calls("aa.t2"), log.read_text(encoding="utf-8")), (1, 0, "interrupted start\n"))

    def test_robust_12_ancillary_failures(self):
        # Prediction: inaccessible package origins and report-write errors stay visible; accepted products are never replayed.
        self.plan("aa", [CHAIN[0]], {"aa.t1": {"product": "greeting"}})
        record = self.common / "devlyn-loops/aa/added.json"
        value = json.loads(record.read_text(encoding="utf-8"))
        former = self.root / "former"
        (former / "docs/specs/aa").mkdir(parents=True)
        (former / "docs/specs/aa/sentinel").write_text("keep", encoding="utf-8")
        value["origin"] = str(former)  # Intact authoritative capture; former checkout is no longer a repository.
        record.write_text(json.dumps(value), encoding="utf-8")
        self.independent()
        result = self.fault_drain(
            "a = q['acceptance']()\nreal = a['atomic_write']\ndef write(path, data):\n"
            "    if path.name == 'drain-report.md' and path.parent.name == 'aa':\n"
            "        raise PermissionError('report denied')\n    return real(path, data)\na['atomic_write'] = write\n")
        self.assert_independent(result)
        self.assertEqual(self.tasks(result)["aa.t1"]["result"], "accepted")
        self.assertIn("package cleanup retained:", " ".join(result["cleanup"]))
        self.assertIn("report unavailable:", " ".join(result["cleanup"]))
        self.assertTrue((former / "docs/specs/aa/sentinel").exists())
        self.drain()
        self.assertEqual((self.calls("aa.t1"), self.calls("bb.t1")), (1, 1))

    def test_robust_13_authoritative_queue(self):
        # Prediction: unreadable bytes, duplicate identities, missing/malformed queue files and bad add records remain BLOCKED;
        # unlike task-local damage, none permits even the independent executor to start.
        self.plan("aa", [CHAIN[0]], {"aa.t1": {"product": "greeting"}})
        self.independent()
        for fault in ("bytes", "duplicate", "missing", "malformed", "record"):
            with self.subTest(fault=fault):
                if fault == "bytes":
                    injection = "(pathlib.Path(sys.argv[sys.argv.index('--repo') + 1]) / 'docs/specs/queue.md').write_bytes(b'\\xff')\n"
                elif fault == "record":
                    injection = ("real = g['records']\ndef records(common):\n"
                                 "    (common / 'devlyn-loops/aa/added.json').write_text('{}', encoding='utf-8')\n"
                                 "    return real(common)\ng['records'] = records\n")
                else:
                    data = {"duplicate": "(q['row_line']('aa.t1', 'One') + '\\n') .encode() * 2",
                            "missing": "None", "malformed": "b'- [ ] foreign legacy row\\n'"}[fault]
                    injection = ("real = g['show']\ndef show(cwd, rev, path):\n"
                                 f"    if path == 'docs/specs/aa/queue.md':\n        return {data}\n"
                                 "    return real(cwd, rev, path)\ng['show'] = show\n")
                path = self.common / "devlyn-loops/aa/added.json"
                saved = path.read_bytes()
                result = self.fault_drain(injection, code=1)
                self.assertEqual(result["status"], "BLOCKED")
                self.assertEqual((self.calls("aa.t1"), self.calls("bb.t1")), (0, 0))
                path.write_bytes(saved)
                (self.anchor / "docs/specs/queue.md").write_bytes(self.base_queue)

    def test_robust_13_unreadable_unrelated_queue(self):
        # Prediction: an unreadable tracked file without a proving row in HEAD (including no HEAD copy) is ignored, and a
        # recorded loop's tracked queue is never read (its capture is); status selects aa.t1 and drain accepts both aa.t1
        # and bb.t1, each with one executor call.
        path = self.anchor / "docs/specs/notes/queue.md"
        path.parent.mkdir()
        path.write_text("- [ ] ordinary documentation task\n", encoding="utf-8")
        self.plan("aa", [CHAIN[0]], {"aa.t1": {"product": "greeting"}})
        self.g("checkout", "refs/devlyn/captures/aa", "--", "docs/specs/aa")
        self.g("commit", "-qm", "tracked loop package")
        self.g("add", str(path))
        self.independent()
        denied = [str(path), str(self.anchor / "docs/specs/aa/queue.md")]
        injection = ("real_read = pathlib.Path.read_bytes\ndef read(path):\n"
                     f"    if str(path) in {denied!r}:\n        raise PermissionError('queue read denied')\n"
                     "    return real_read(path)\npathlib.Path.read_bytes = read\n")
        for committed in (False, True):
            with self.subTest(committed=committed):
                if committed:
                    self.g("commit", "-qm", "unrelated queue")
                status = self.fault_drain(injection, status=True)
                self.assertEqual((status["status"], status["next"]), ("OK", "aa.t1"))
        result = self.fault_drain(injection)
        self.assert_independent(result)
        self.assertEqual({identity: task["result"] for identity, task in self.tasks(result).items()},
                         {"aa.t1": "accepted", "bb.t1": "accepted"})
        self.assertEqual((self.calls("aa.t1"), self.calls("bb.t1")), (1, 1))

    def test_robust_13_unreadable_proven_queue(self):
        # Prediction: HEAD's proving row makes an unreadable unrecorded loop queue BLOCKED in status and drain,
        # naming its path before either independent executor runs.
        path = self.anchor / "docs/specs/known/queue.md"
        path.parent.mkdir()
        path.write_text(self.queue["row_line"]("known.t1", "Known") + "\n", encoding="utf-8")
        self.g("add", str(path))
        self.g("commit", "-qm", "known loop")
        self.plan("aa", [CHAIN[0]], {"aa.t1": {"product": "greeting"}})
        self.independent()
        injection = ("real_read = pathlib.Path.read_bytes\ndef read(path):\n"
                     f"    if path == pathlib.Path({str(path)!r}):\n        raise PermissionError('queue read denied')\n"
                     "    return real_read(path)\npathlib.Path.read_bytes = read\n")
        for status in (True, False):
            with self.subTest(status=status):
                result = self.fault_drain(injection, status=status, code=1)
                self.assertEqual(result["status"], "BLOCKED")
                self.assertIn(str(path), result["reason"])
                self.assertIn("queue read denied", result["reason"])
                self.assertEqual((self.calls("aa.t1"), self.calls("bb.t1"), self.calls("known.t1")), (0, 0, 0))

    def test_robust_selection_io_and_programming_errors(self):
        # Prediction: a task-local eligibility read failure waits before selection and cannot abort annotation/reporting;
        # programming errors in advance remain visible exceptions rather than operational waits.
        self.plan("aa", [CHAIN[0]], {"aa.t1": {"product": "greeting"}})
        self.independent()
        result = self.fault_drain(
            "real = g['local_start']\ndef start(v, loop):\n"
            "    if loop == 'aa':\n        raise OSError('cannot read aa baseline')\n"
            "    return real(v, loop)\ng['local_start'] = start\n")
        self.assert_independent(result)
        self.assertIn("cannot read aa baseline", self.tasks(result)["aa.t1"]["reason"])
        self.assertEqual(self.calls("aa.t1"), 0)
        from unittest import mock
        opts = argparse.Namespace(repo=str(self.anchor), local_only=True, worktree_root=None, executor=["unused", "{packet}"])
        with mock.patch.dict(self.queue["drain"].__globals__, advance=mock.Mock(side_effect=TypeError("programming defect"))):
            with self.assertRaisesRegex(TypeError, "programming defect"):
                self.queue["drain"](opts)

    def test_robust_malformed_allocation_and_packet_paths_hold_barrier(self):
        # Prediction: a lost allocation checkpoint cannot prove no writer ran; malformed packet paths are invalid data,
        # not programming exceptions. Both retain aa's sibling barrier while an unrelated loop completes.
        self.plan_checker("aa", [GREET_CHECK, NOTES_CHECK], {"aa.t1": {"product": "greeting", "exit_now": 1},
                                                            "aa.t2": {"product": "notes"}, "aa.t3": {"check_only": True}})
        self.drain()
        path = self.receipt_path("aa.t1")
        original = path.read_bytes()
        receipt = json.loads(original)
        del receipt["allocation"]
        path.write_text(json.dumps(receipt), encoding="utf-8")
        self.independent()
        result = self.drain()
        self.assert_independent(result)
        self.assertEqual(self.calls("aa.t2"), 0)
        self.assertIn("recovery conflict:", self.tasks(result)["aa.t1"]["reason"])
        path.write_bytes(original)
        packet_path = path.with_name("packet.json")
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        packet["submission"] = []
        packet_path.write_text(json.dumps(packet), encoding="utf-8")
        self.independent("cc")
        result = self.drain()
        self.assert_independent(result, "cc")
        self.assertIn("recovery conflict:", self.tasks(result)["aa.t1"]["reason"])
        self.assertEqual((self.calls("aa.t1"), self.calls("aa.t2")), (1, 0))

    def test_robust_final_summary_io(self):
        # Prediction: an ancillary branch-inspection failure after acceptance stays a visible cleanup diagnostic;
        # the final JSON preserves both accepted products rather than falling back to BLOCKED.
        self.plan("aa", [CHAIN[0]], {"aa.t1": {"product": "greeting"}})
        self.independent()
        result = self.fault_drain(
            "real_summary = g['summary']\nreal_ref = g['ref_value']\ninspecting = False\n"
            "def ref(cwd, name):\n"
            "    if inspecting and name == 'refs/heads/devlyn/aa/t1':\n        raise PermissionError('aa ref unreadable')\n"
            "    return real_ref(cwd, name)\n"
            "def summary(v, row):\n    global inspecting\n    inspecting = True\n"
            "    try:\n        return real_summary(v, row)\n    finally:\n        inspecting = False\n"
            "g['ref_value'] = ref\ng['summary'] = summary\n")
        self.assert_independent(result)
        self.assertEqual(self.tasks(result)["aa.t1"]["result"], "accepted")
        self.assertIn("aa ref unreadable", " ".join(result["cleanup"]))
        self.assertEqual(self.calls("aa.t1"), 1)

    def test_robust_partial_receipt_identity(self):
        # Prediction: every usable identity implicates its task even when another identity field is malformed;
        # the suspect artifact is preserved, aa never executes, and bb completes. Astra's original probe ran aa once.
        self.plan("aa", [CHAIN[0]], {"aa.t1": {"product": "greeting"}})
        self.independent()
        path = self.common / "devlyn-completion/foreign/receipt.json"
        path.parent.mkdir(parents=True)
        original = json.dumps({"task": "aa.t1", "branch": None, "allocation": "owned", "worktree": "/unknown"})
        path.write_text(original, encoding="utf-8")
        result = self.drain()
        self.assert_independent(result)
        self.assertIn("recovery conflict:", self.tasks(result)["aa.t1"]["reason"])
        self.assertEqual((self.calls("aa.t1"), path.read_text(encoding="utf-8")), (0, original))

    def direct_allocate(self, name, work):
        helper = self.queue["shared"]("task-complete")
        args = argparse.Namespace(repo=self.anchor, task=name, branch="task/" + name, worktree=str(work),
                                  repository=None, base=None, remote="origin", local_base=self.base,
                                  from_receipt=None, start=None)
        with mock.patch.dict(os.environ, self.env), mock.patch.object(helper["shutil"], "disk_usage",
                return_value=argparse.Namespace(total=100 * 1024**3, free=100 * 1024**3)):
            return helper["allocate"](args)

    def test_direct_cleanup_prunes_exact_roots_after_removal_or_deregistration(self):
        # Prediction: real Git removal prunes each named root, retains the shared container, and refuses a missing
        # registered tree until deregistration. An arbitrary suffix-lookalike root has no named-root ownership.
        helper = self.queue["shared"]("task-complete")
        roots = helper["worktree_roots"]({"anchor": str(self.anchor)})
        for index, root in enumerate((*roots, self.root / "foreign.devlyn.noindex")):
            with self.subTest(root=root):
                work = root / "loop/task"
                allocation = self.direct_allocate("cleanup" + str(index), work)
                path = Path(allocation["receipt"])
                receipt = json.loads(path.read_text(encoding="utf-8"))
                receipt.update(publish_sha=self.base, source_sha=self.base, writers_released=True, files={}, remote_url={})
                self.g("update-ref", receipt["recovery_ref"], self.base)
                pr = {"state": "MERGED", "mergedAt": "fixture", "mergeCommit": {"oid": self.base}}
                with mock.patch.dict(helper["cleanup"].__globals__,
                                     verify_files=mock.Mock(), read_json=mock.Mock(return_value={}),
                                     removable=mock.Mock(), records_manifest=mock.Mock(return_value={}),
                                     repo_policy=mock.Mock(), remote_base=mock.Mock(return_value=self.base),
                                     remote_url=mock.Mock(return_value={}), remote_head=mock.Mock(return_value=None)), \
                        mock.patch.dict(os.environ, self.env):
                    if index == 1:
                        shutil.rmtree(work)
                        with self.assertRaisesRegex(helper["CompletionError"], "missing worktree is still registered"):
                            helper["cleanup"](receipt, path, pr)
                        self.assertTrue(root.is_dir())
                        self.g("worktree", "prune")
                    if index == 2:
                        rmdir = Path.rmdir

                        def denied(parent):
                            if parent == work.parent:
                                raise PermissionError("fixture parent denied")
                            return rmdir(parent)

                        warnings = []
                        with mock.patch.object(Path, "rmdir", denied):
                            helper["cleanup"](receipt, path, pr, warnings=warnings)
                        self.assertFalse(work.exists())
                        self.assertEqual(receipt["status"], "COMPLETE")
                        self.assertEqual(warnings, [f"parent cleanup retained: {work.parent}: fixture parent denied; continuing"])
                    helper["cleanup"](receipt, path, pr)
                self.assertFalse(work.exists())
                self.assertEqual(root.exists(), index == 3)
                self.assertTrue((self.anchor.parent / ".devlyn-worktrees").is_dir())

    def test_named_pruning_keeps_siblings_ds_store_and_registered_missing(self):
        # Prediction: siblings and .DS_Store stop rmdir; a real registered-but-missing sibling also prevents pruning.
        helper = self.queue["shared"]("task-complete")
        root = helper["worktree_roots"]({"anchor": str(self.anchor)})[0]
        parent = root / "loop"
        receipt = {"anchor": str(self.anchor), "common_gitdir": str(self.common), "worktree": str(parent / "task")}
        parent.mkdir(parents=True)
        for name in ("sibling", ".DS_Store"):
            retained = parent / name
            retained.write_text("keep", encoding="utf-8")
            helper["prune_named_parents"](receipt)
            self.assertEqual(retained.read_text(encoding="utf-8"), "keep")
            retained.unlink()
        sibling = parent / "missing"
        self.g("worktree", "add", "-q", "-b", "missing", str(sibling))
        shutil.rmtree(sibling)
        helper["prune_named_parents"](receipt)
        self.assertTrue(parent.is_dir())
        self.g("worktree", "prune")
        helper["prune_named_parents"](receipt)
        self.assertFalse(root.exists())
        self.assertTrue(root.parent.is_dir())

    def test_pruning_rejects_redirected_ancestors(self):
        # Prediction: a symlink (or Windows junction) above the task cannot redirect either named or custom pruning.
        helper = self.queue["shared"]("task-complete")
        root = helper["worktree_roots"]({"anchor": str(self.anchor)})[0]
        outside = self.root / "outside"
        (outside / "loop").mkdir(parents=True)
        root.parent.mkdir()
        if os.name == "nt":
            self.run_ok(["cmd.exe", "/d", "/c", "mklink", "/J", str(root), str(outside)])
        else:
            root.symlink_to(outside, target_is_directory=True)
        receipt = {"anchor": str(self.anchor), "common_gitdir": str(self.common), "worktree": str(root / "loop/task")}
        try:
            with self.assertRaisesRegex(helper["CompletionError"], "unredirected"):
                helper["prune_named_parents"](receipt)
            with self.assertRaisesRegex(helper["CompletionError"], "symlink or junction"):
                helper["prune_empty_parents"](receipt, root / "loop", root)
            self.assertTrue((outside / "loop").is_dir())
        finally:
            root.rmdir() if os.name == "nt" else root.unlink()

    def test_allocate_sweeps_only_empty_exact_legacy_roots(self):
        # Prediction: allocate removes only the anchor's empty legacy roots; occupied, redirected and foreign roots stay.
        helper = self.queue["shared"]("task-complete")
        roots = helper["worktree_roots"]({"anchor": str(self.anchor)})[1:]
        foreign = self.root / "other.devlyn.noindex"
        foreign.mkdir()
        for root in roots:
            root.mkdir()
        self.direct_allocate("sweep", self.root / "task1")
        self.assertEqual([root.exists() for root in roots], [False, False])
        self.assertTrue(foreign.is_dir())
        roots[0].mkdir()
        (roots[0] / ".DS_Store").touch()
        self.g("worktree", "add", "-q", "-b", "missing", str(roots[1] / "missing"))
        shutil.rmtree(roots[1] / "missing")
        result = self.direct_allocate("sweep2", self.root / "task2")
        self.assertTrue(all(root.is_dir() for root in roots))
        self.assertEqual(result["warnings"], [])
        self.g("worktree", "prune")
        with mock.patch.object(Path, "rmdir", side_effect=PermissionError("fixture prune denied")):
            result = self.direct_allocate("sweep3", self.root / "task3")
        self.assertEqual(len(result["warnings"]), 2)
        self.assertTrue(all("fixture prune denied" in warning for warning in result["warnings"]))

    def test_legacy_sweep_refuses_symlinks_and_junctions(self):
        # Prediction: an exact legacy name redirected to an empty foreign directory is retained with a warning.
        root = self.anchor.parent / (self.anchor.name + ".devlyn.noindex")
        outside = self.root / "outside"
        outside.mkdir()
        if os.name == "nt":
            self.run_ok(["cmd.exe", "/d", "/c", "mklink", "/J", str(root), str(outside)])
        else:
            root.symlink_to(outside, target_is_directory=True)
        try:
            result = self.direct_allocate("redirect", self.root / "task")
            self.assertIn("symlink or junction", " ".join(result["warnings"]))
            self.assertTrue(root.is_dir() and outside.is_dir())
        finally:
            root.rmdir() if os.name == "nt" else root.unlink()

    @unittest.skipIf(os.name == "nt", "POSIX permissions and fake delivery require POSIX")
    def test_nested_custom_root_keeps_permissions_after_completion_and_drain(self):
        # Prediction: completion and drain remove only descendants of an explicit custom root, preserving its 0700 mode.
        self.remote(pending=False)
        self.plan("private", [CHAIN[0]], {"private.t1": {"product": "greeting"}}, delivery="auto")
        named = self.anchor.parent / ".devlyn-worktrees" / self.anchor.name
        root = named / "private-root"
        root.mkdir(parents=True, mode=0o700)
        result = self.fault_drain("", local=False, root=root)
        self.assertEqual(self.tasks(result)["private.t1"]["delivery"], "COMPLETE")
        self.assertTrue(root.is_dir())
        self.assertEqual(stat.S_IMODE(root.stat().st_mode), 0o700)
        self.assertFalse((root / "private").exists())
        self.assertEqual(self.receipt("private.t1")["keep_root"], str(root))
        # Repeated completion and a later drain both respect the recorded boundary.
        completed = json.loads(self.run_ok([sys.executable, str(self.helper), "complete", "--receipt",
                                           str(self.receipt_path("private.t1"))]))
        self.assertEqual(completed["status"], "COMPLETE")
        self.assertTrue(root.is_dir())
        self.assertEqual(stat.S_IMODE(root.stat().st_mode), 0o700)
        (root / "private").mkdir()
        self.fault_drain("", local=False, root=root)
        self.assertFalse((root / "private").exists())
        self.assertTrue(root.is_dir() and named.is_dir())
        self.assertEqual(stat.S_IMODE(root.stat().st_mode), 0o700)
        self.assertEqual(self.calls("private.t1"), 1)

    @unittest.skipIf(os.name == "nt", "fake delivery requires POSIX")
    def test_pruning_resolve_runtime_error_warns_without_blocking_completion(self):
        # Prediction: Python 3.12's resolve RuntimeError becomes a path-naming pruning warning on completed receipts.
        self.remote(pending=False)
        self.plan("cycle", [CHAIN[0]], {"cycle.t1": {"product": "greeting"}}, delivery="auto")
        self.drain(local=False)
        receipt = self.receipt("cycle.t1")
        self.assertNotIn("keep_root", receipt)
        work = Path(receipt["worktree"])
        work.parent.mkdir(parents=True)
        helper = self.queue["shared"]("task-complete")
        resolve = Path.resolve
        for failing in (work, work.parent):
            with self.subTest(path=failing):
                def cyclic(path, *args, **kwargs):
                    if path == failing:
                        raise RuntimeError("fixture symlink loop")
                    return resolve(path, *args, **kwargs)

                with mock.patch.object(Path, "resolve", cyclic), mock.patch.dict(os.environ, self.env):
                    completed = helper["complete"](argparse.Namespace(receipt=str(self.receipt_path("cycle.t1")),
                        acceptance=None, local_only=False, writers_stopped=False, mode=None))
                    view = {"states": {"cycle.t1": {"receipt": receipt}}, "cleanup": []}
                    self.queue["prune_parents"](view, work.parent.parent)
                self.assertEqual(completed["status"], "COMPLETE")
                warning, = completed["warnings"]
                self.assertIn("parent cleanup retained:", warning)
                self.assertIn(str(failing), warning)
                self.assertIn("fixture symlink loop", warning)
                self.assertTrue(warning.endswith("; continuing"))
                retained, = view["cleanup"]
                self.assertIn("parent cleanup retained:", retained)
                self.assertIn(str(failing), retained)
                self.assertIn("fixture symlink loop", retained)
                self.assertTrue(work.parent.is_dir())

    def test_allocation_retries_disappearing_parent_and_refuses_competing_creator(self):
        # Prediction: removal immediately before the final mkdir retries; a competing final directory is never adopted.
        helper = self.queue["shared"]("task-complete")
        mkdir = Path.mkdir
        root = helper["worktree_roots"]({"anchor": str(self.anchor)})[0]
        target = root / "loop/task"
        attempts = []

        def disappearing(path, *args, **kwargs):
            if path == target:
                attempts.append(path)
                if len(attempts) == 1:
                    path.parent.rmdir()
            return mkdir(path, *args, **kwargs)

        with mock.patch.object(Path, "mkdir", disappearing):
            self.assertEqual(self.direct_allocate("retry", target)["status"], "ALLOCATED")
        self.assertEqual(len(attempts), 2)
        target = root / "loop/raced"

        def competing(path, *args, **kwargs):
            if path == target:
                mkdir(path)
                (path / "foreign").write_text("keep", encoding="utf-8")
            return mkdir(path, *args, **kwargs)

        with mock.patch.object(Path, "mkdir", competing):
            with self.assertRaises(helper["CompletionError"]) as raised:
                self.direct_allocate("raced", target)
        directory = self.common / "devlyn-completion" / hashlib.sha256(b"task/raced").hexdigest()[:24]
        self.assertIn(f"not devlyn's; leave it; choose another --worktree path, delete receipt directory {directory}, then allocate again", str(raised.exception))
        self.assertEqual((target / "foreign").read_text(encoding="utf-8"), "keep")
        self.assertEqual(json.loads((directory / "receipt.json").read_text(encoding="utf-8"))["allocation"], "allocating")
        self.assertEqual(self.g("branch", "--list", "task/raced"), "")

    def test_allocation_parent_retry_is_bounded(self):
        # Prediction: an ancestor lost on every final mkdir stops after three attempts and keeps the allocation intent.
        target = self.root / "parent/task"
        mkdir, attempts = Path.mkdir, []

        def disappearing(path, *args, **kwargs):
            if path == target:
                attempts.append(path)
                path.parent.rmdir()
            return mkdir(path, *args, **kwargs)

        with mock.patch.object(Path, "mkdir", disappearing):
            with self.assertRaises(FileNotFoundError):
                self.direct_allocate("bounded", target)
        self.assertEqual(len(attempts), 3)
        self.assertFalse(target.exists())
        self.assertEqual(self.g("branch", "--list", "task/bounded"), "")

    def test_allocation_retries_ancestor_creation_and_container_enoent(self):
        # Prediction: losing an ancestor during recursive mkdir, or ENOENT at container mkdir, retries allocation.
        helper = self.queue["shared"]("task-complete")
        mkdir = Path.mkdir
        target = self.root / "outer/parent/task"
        attempts = []
        removed = []

        def disappearing(path, *args, **kwargs):
            if path == target.parent:
                if kwargs.get("parents"):
                    attempts.append(path)
                elif not removed:
                    path.parent.rmdir()
                    removed.append(path.parent)
            return mkdir(path, *args, **kwargs)

        with mock.patch.object(Path, "mkdir", disappearing):
            self.assertEqual(self.direct_allocate("ancestor", target)["status"], "ALLOCATED")
        self.assertEqual((len(attempts), removed), (2, [target.parent.parent]))
        container = helper["worktree_roots"]({"anchor": str(self.anchor)})[0].parent
        attempts = []

        def missing_container(path, *args, **kwargs):
            if path == container:
                attempts.append(path)
                if len(attempts) == 1:
                    raise FileNotFoundError("fixture container ancestor disappeared")
            return mkdir(path, *args, **kwargs)

        with mock.patch.object(Path, "mkdir", missing_container):
            result = self.direct_allocate("container", container / self.anchor.name / "task")
        self.assertEqual((result["status"], len(attempts)), ("ALLOCATED", 2))

    def test_marking_warning_survives_checkout_failure_in_drain_reports(self):
        # Prediction: a marking warning reaches drain JSON and reports even when checkout then fails.
        self.plan("warn", [CHAIN[0]], {})
        result = self.fault_drain(
            "def indexing(path):\n    raise OSError('fixture indexing denied')\n"
            "h['shared']('platform-support')['mark_not_content_indexed'] = indexing\n"
            "hg = h['allocate'].__globals__\nreal = hg['gref']\n"
            "def checkout(receipt, *args):\n"
            "    if args[:2] == ('worktree', 'add'):\n        raise h['CompletionError']('fixture checkout denied')\n"
            "    return real(receipt, *args)\nhg['gref'] = checkout\n")
        warning = f"content indexing unchanged: {self.receipt('warn.t1')['worktree']}: could not set FILE_ATTRIBUTE_NOT_CONTENT_INDEXED: fixture indexing denied; continuing"
        self.assertEqual((result["status"], result["warnings"]), ("WAITING", [warning]))
        self.assertIn("fixture checkout denied", self.tasks(result)["warn.t1"]["reason"])
        self.assertEqual(self.calls("warn.t1"), 0)
        self.assertTrue(result["reports"])
        for report in result["reports"]:
            self.assertIn(warning, Path(report).read_text(encoding="utf-8"))

    @unittest.skipIf(os.name == "nt", "fake delivery and symlinks require POSIX")
    def test_symlinked_named_root_warns_without_blocking_cleanup_or_completion(self):
        # Prediction: redirecting the empty root after removal retains it, deletes task refs and completes;
        # repeated completion still succeeds and both command results and drain reports contain its stderr warning.
        bare, _ = self.remote(pending=False)
        self.plan("redirect", [CHAIN[0]], {"redirect.t1": {"product": "greeting"}}, delivery="auto")
        root = self.anchor.parent / ".devlyn-worktrees" / self.anchor.name
        outside = self.root / "outside"
        outside.mkdir()
        result = self.fault_drain(
            "hg = h['cleanup'].__globals__\nreal = hg['prune_named_parents']\n"
            "def redirect(receipt):\n"
            "    root = h['worktree_roots'](receipt)[0]\n"
            "    if not root.is_symlink():\n"
            "        pathlib.Path(receipt['worktree']).parent.rmdir()\n"
            "        root.rmdir()\n"
            "        root.symlink_to(root.parent.parent / 'outside', target_is_directory=True)\n"
            "    return real(receipt)\nhg['prune_named_parents'] = redirect\n", local=False)
        self.assertEqual(self.tasks(result)["redirect.t1"]["delivery"], "COMPLETE")
        warning, = result["warnings"]
        self.assertIn("parent cleanup retained:", warning)
        self.assertIn("unredirected worktree", warning)
        self.assertTrue(warning.endswith("; continuing"))
        self.assertTrue(root.is_symlink() and outside.is_dir())
        self.assertEqual(self.g("branch", "--list", "devlyn/redirect/t1"), "")
        self.assertEqual(self.run_ok(["git", "--git-dir", str(bare), "branch", "--list", "devlyn/redirect/t1"]), "")
        for report in result["reports"]:
            self.assertIn(warning, Path(report).read_text(encoding="utf-8"))
        for _ in range(2):
            completed = subprocess.run([sys.executable, str(self.helper), "complete", "--receipt",
                                        str(self.receipt_path("redirect.t1"))], env=self.env,
                                       capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
            self.assertEqual((json.loads(completed.stdout)["status"], json.loads(completed.stdout)["warnings"]),
                             ("COMPLETE", [warning]))
            self.assertIn(warning, completed.stderr)

    def test_attribute_failures_warn_in_direct_output_and_drain_reports(self):
        # Prediction: hidden and indexing failures are printed and returned directly, then reach every drain report.
        from io import StringIO
        import contextlib
        helper = self.queue["shared"]("task-complete")
        container = self.anchor.parent / ".devlyn-worktrees"
        stderr = StringIO()
        with mock.patch.dict(helper["shared"]("platform-support"),
                             mark_hidden=mock.Mock(side_effect=OSError("fixture hidden denied")),
                             mark_not_content_indexed=mock.Mock(side_effect=OSError("fixture indexing denied"))), \
                contextlib.redirect_stderr(stderr):
            result = self.direct_allocate("hidden", container / self.anchor.name / "direct")
        warning = f"visibility unchanged: {container}: could not set FILE_ATTRIBUTE_HIDDEN: fixture hidden denied; continuing"
        indexing = f"content indexing unchanged: {result['worktree']}: could not set FILE_ATTRIBUTE_NOT_CONTENT_INDEXED: fixture indexing denied; continuing"
        self.assertEqual(result["warnings"], [warning, indexing])
        self.assertEqual(stderr.getvalue(), warning + "\n" + indexing + "\n")
        self.g("worktree", "remove", result["worktree"])
        helper["prune_named_parents"](json.loads(Path(result["receipt"]).read_text(encoding="utf-8")))
        container.rmdir()  # Fixture reset so this drain is the exclusive creator again.
        self.plan("hidden", [CHAIN[0]], {"hidden.t1": {"product": "greeting"}})
        result = self.fault_drain("def hidden(path):\n    raise OSError('fixture hidden denied')\n"
                                  "def indexing(path):\n    raise OSError('fixture indexing denied')\n"
                                  "h['shared']('platform-support')['mark_hidden'] = hidden\n"
                                  "h['shared']('platform-support')['mark_not_content_indexed'] = indexing\n")
        self.assertIn(warning, result["warnings"])
        indexing = f"content indexing unchanged: {self.receipt('hidden.t1')['worktree']}: could not set FILE_ATTRIBUTE_NOT_CONTENT_INDEXED: fixture indexing denied; continuing"
        self.assertIn(indexing, result["warnings"])
        for report in result["reports"]:
            text = Path(report).read_text(encoding="utf-8")
            self.assertIn(warning, text)
            self.assertIn(indexing, text)
        self.assertEqual(self.tasks(result)["hidden.t1"]["result"], "accepted")

    def test_default_drain_allocates_hidden_worktree_outside_anchor(self):
        # Prediction: a default drain passes the real allocation's absent/disjoint check and accepts a task in
        # <anchor parent>/.devlyn-worktrees/<anchor name>/<loop>/<task>, outside the anchor on every OS.
        self.plan("nx", [CHAIN[0]], {"nx.t1": {"product": "greeting"}})
        task = self.tasks(self.drain())["nx.t1"]
        receipt = self.receipt("nx.t1")
        work = Path(receipt["worktree"])
        self.assertEqual(work, self.anchor.parent / ".devlyn-worktrees" / self.anchor.name / "nx" / "t1")
        self.assertFalse(work.is_relative_to(self.anchor))
        self.assertFalse(self.anchor.is_relative_to(work))
        self.assertEqual(receipt["allocation"], "owned")
        self.assertEqual(Path(self.g("rev-parse", "--show-toplevel", work=work)), work)
        self.assertEqual((task["result"], task["delivery"], self.calls("nx.t1")), ("accepted", "LOCAL_ONLY", 1))

    def test_disk_refusal_stops_drain_and_retries_pending_task(self):
        # Prediction: disk refusal stops before an independent task starts, preserves pending rows, reports the reason,
        # and a later drain without the fault starts both tasks.
        self.plan("aa", [CHAIN[0]], {"aa.t1": {"product": "greeting"}})
        self.independent()
        result = self.fault_drain(
            "import types\n"
            "h['shutil'].disk_usage = lambda path: types.SimpleNamespace(total=100 * 1024**3, free=9 * 1024**3)\n",
            code=1)
        tasks = self.tasks(result)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("BLOCKED:disk", result["reason"])
        self.assertIn("BLOCKED:disk", tasks["aa.t1"]["reason"])
        self.assertEqual((tasks["aa.t1"]["result"], tasks["bb.t1"]["result"]), ("pending", "pending"))
        self.assertEqual((result["counts"]["failed"], self.calls("aa.t1"), self.calls("bb.t1")), (0, 0, 0))
        self.assertFalse(self.receipt_path("aa.t1").exists())
        self.assertFalse(self.receipt_path("bb.t1").exists())
        self.assertEqual(self.g("branch", "--list", "devlyn/aa/t1"), "")
        self.assertTrue(any("BLOCKED:disk" in Path(path).read_text(encoding="utf-8") for path in result["reports"]))
        retried = self.tasks(self.drain())
        self.assertEqual((retried["aa.t1"]["result"], retried["bb.t1"]["result"]), ("accepted", "accepted"))
        self.assertEqual((self.calls("aa.t1"), self.calls("bb.t1")), (1, 1))

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_disk_refusal_reports_delivery_reconciled_during_allocation(self):
        # Prediction: allocation may settle an earlier merged PR before refusing for disk; the final view reflects it.
        _, data = self.remote(pending=True)
        self.plan("aa", [CHAIN[0]], {"aa.t1": {"product": "greeting"}}, delivery="auto")
        self.assertEqual(self.tasks(self.drain(local=False))["aa.t1"]["delivery"], "PENDING")
        self.assertEqual(self.merge_pr(data, 1).returncode, 0)
        self.plan("bb", [("t1", [], "Notes", [NOTES_CHECK])], {"bb.t1": {"product": "notes"}}, delivery="auto")
        result = self.fault_drain(
            "import types\n"
            "real_next = g['next_task']\n"
            "g['next_task'] = lambda v, attempted: real_next(v, attempted | {'aa.t1'})\n"
            "h['shutil'].disk_usage = lambda path: types.SimpleNamespace(total=100 * 1024**3, free=9 * 1024**3)\n",
            local=False, code=1)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("BLOCKED:disk", result["reason"])
        self.assertEqual(self.tasks(result)["aa.t1"]["delivery"], "COMPLETE")
        self.assertEqual(self.tasks(result)["bb.t1"]["result"], "pending")
        self.assertEqual(self.receipt("aa.t1")["status"], "COMPLETE")
        self.assertFalse(self.receipt_path("bb.t1").exists())

    def allow_content_indexing(self, path):
        # Fixture control: a Windows temp ancestor may already have the not-content-indexed bit.
        self.queue["shared"]("platform-support")["_kernel"].SetFileAttributesW(
            str(path), path.stat().st_file_attributes & ~stat.FILE_ATTRIBUTE_NOT_CONTENT_INDEXED)
        self.assertFalse(path.stat().st_file_attributes & stat.FILE_ATTRIBUTE_NOT_CONTENT_INDEXED)

    @unittest.skipIf(os.name != "nt", "Windows file attributes")
    def test_windows_default_drain_disables_content_indexing_with_inheritance(self):
        # Prediction: marking the task before checkout covers nested files, .git and later files; its parents stay unmarked.
        self.allow_content_indexing(self.root)
        self.plan("nx", [CHAIN[0]], {"nx.t1": {"product": "greeting"}})
        task = self.tasks(self.drain())["nx.t1"]
        work = Path(self.receipt("nx.t1")["worktree"])
        (work / "later.txt").write_text("later", encoding="utf-8")
        for path in (work, work / "docs/specs/queue.md", work / ".git", work / "later.txt"):
            with self.subTest(path=path):
                self.assertTrue(path.stat().st_file_attributes & stat.FILE_ATTRIBUTE_NOT_CONTENT_INDEXED)
        for path in (work.parent.parent, work.parent):
            self.assertFalse(path.stat().st_file_attributes & stat.FILE_ATTRIBUTE_NOT_CONTENT_INDEXED)
        self.assertTrue(work.parents[2].stat().st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN)
        self.assertEqual((task["result"], task["delivery"], self.calls("nx.t1")), ("accepted", "LOCAL_ONLY", 1))

    @unittest.skipIf(os.name != "nt", "Windows file attributes")
    def test_windows_existing_default_root_keeps_content_indexing(self):
        # Prediction: the existing default root keeps its attributes while the new task is marked.
        root = self.anchor.parent / ".devlyn-worktrees" / self.anchor.name
        root.mkdir(parents=True)
        self.allow_content_indexing(root)
        platform = self.queue["shared"]("platform-support")
        platform["_kernel"].SetFileAttributesW(str(root.parent), root.parent.stat().st_file_attributes & ~stat.FILE_ATTRIBUTE_HIDDEN)
        container_before = root.parent.stat().st_file_attributes
        before = root.stat().st_file_attributes
        self.plan("nx", [CHAIN[0]], {"nx.t1": {"product": "greeting"}})
        self.assertEqual(self.tasks(self.drain())["nx.t1"]["result"], "accepted")
        self.assertEqual(root.stat().st_file_attributes, before)
        self.assertEqual(root.parent.stat().st_file_attributes, container_before)
        self.assertTrue(Path(self.receipt("nx.t1")["worktree"]).stat().st_file_attributes & stat.FILE_ATTRIBUTE_NOT_CONTENT_INDEXED)

    @unittest.skipIf(os.name != "nt", "Windows file attributes")
    def test_windows_explicit_worktree_root_keeps_content_indexing(self):
        # Prediction: explicit roots keep their attributes, including an explicit default path; every task is marked.
        self.allow_content_indexing(self.root)
        for loop, root in (("ex", self.root / "custom"), ("nx", self.anchor.parent / ".devlyn-worktrees" / self.anchor.name)):
            with self.subTest(root=root):
                root.mkdir(parents=True)
                before = root.stat().st_file_attributes
                self.plan(loop, [CHAIN[0]], {f"{loop}.t1": {"product": "greeting"}})
                self.assertEqual(self.tasks(self.fault_drain("", root=root))[f"{loop}.t1"]["result"], "accepted")
                self.assertEqual(root.stat().st_file_attributes, before)
                self.assertTrue(Path(self.receipt(f"{loop}.t1")["worktree"]).stat().st_file_attributes & stat.FILE_ATTRIBUTE_NOT_CONTENT_INDEXED)

    @unittest.skipIf(os.name != "nt", "Windows file attributes")
    def test_windows_direct_allocation_marks_worktree_under_unmarked_custom_parent(self):
        # Prediction: direct allocate marks the explicit worktree before Git populates it, without changing its parent.
        parent = self.root / "custom"
        parent.mkdir()
        self.allow_content_indexing(parent)
        before = parent.stat().st_file_attributes
        work = parent / "direct"
        result = json.loads(self.run_ok([sys.executable, str(self.helper), "allocate", "--repo", str(self.anchor),
                                        "--task", "direct", "--branch", "task/direct", "--worktree", str(work),
                                        "--local-base", self.base]))
        self.assertEqual((result["status"], result["warnings"]), ("ALLOCATED", []))
        self.assertEqual(parent.stat().st_file_attributes, before)
        for path in (work, work / "docs/specs/queue.md", work / ".git"):
            self.assertTrue(path.stat().st_file_attributes & stat.FILE_ATTRIBUTE_NOT_CONTENT_INDEXED)

    @unittest.skipIf(os.name != "nt", "Windows file attributes")
    def test_windows_content_indexing_failure_is_diagnostic_and_tasks_run(self):
        # Prediction: each failed attribute call survives later queue views in warnings and reports; both tasks run.
        self.allow_content_indexing(self.root)
        self.plan("nx", CHAIN, {"nx.t1": {"product": "greeting"}, "nx.t2": {"product": "app"}})
        result = self.fault_drain("def mark(path):\n    raise OSError('fixture attribute denied')\n"
                                  "h['shared']('platform-support')['mark_not_content_indexed'] = mark\n")
        root = self.anchor.parent / ".devlyn-worktrees" / self.anchor.name
        warnings = [f"content indexing unchanged: {root / 'nx' / task}: could not set FILE_ATTRIBUTE_NOT_CONTENT_INDEXED: fixture attribute denied; continuing"
                    for task in ("t1", "t2")]
        self.assertEqual([warning for warning in result["warnings"] if "content indexing unchanged:" in warning], warnings)
        for path in (root, root / "nx/t1", root / "nx/t2"):
            self.assertFalse(path.stat().st_file_attributes & stat.FILE_ATTRIBUTE_NOT_CONTENT_INDEXED)
        for path in result["reports"]:
            report = Path(path).read_text(encoding="utf-8")
            for warning in warnings:
                self.assertIn(warning, report)
        self.assertEqual({identity: (task["result"], task["delivery"], self.calls(identity))
                          for identity, task in self.tasks(result).items()},
                         {"nx.t1": ("accepted", "LOCAL_ONLY", 1), "nx.t2": ("accepted", "LOCAL_ONLY", 1)})

    @unittest.skipIf(os.name != "nt", "Windows file attributes")
    def test_mark_not_content_indexed_preserves_attributes_and_reports_read_failure(self):
        # Prediction: marking preserves an unrelated hidden bit, and an unreadable attribute call raises OSError.
        path = self.root / "attributes"
        path.mkdir()
        self.allow_content_indexing(path)
        platform = self.queue["shared"]("platform-support")
        platform["_kernel"].SetFileAttributesW(str(path), path.stat().st_file_attributes | stat.FILE_ATTRIBUTE_HIDDEN)
        before = path.stat().st_file_attributes
        platform["mark_not_content_indexed"](path)
        self.assertEqual(path.stat().st_file_attributes, before | stat.FILE_ATTRIBUTE_NOT_CONTENT_INDEXED)
        with self.assertRaises(OSError):
            platform["mark_not_content_indexed"](self.root / "missing")

    @unittest.skipIf(os.name != "nt", "Windows file attributes")
    def test_mark_hidden_preserves_attributes_and_marks_only_exclusive_container_creator(self):
        # Prediction: the helper preserves indexing bits; allocation marks the container once and leaves existing dirs.
        platform = self.queue["shared"]("platform-support")
        path = self.root / "attributes"
        path.mkdir()
        platform["mark_not_content_indexed"](path)
        before = path.stat().st_file_attributes
        platform["mark_hidden"](path)
        self.assertEqual(path.stat().st_file_attributes, before | stat.FILE_ATTRIBUTE_HIDDEN)
        with self.assertRaises(OSError):
            platform["mark_hidden"](self.root / "missing")
        container = self.anchor.parent / ".devlyn-worktrees"
        mark = platform["mark_hidden"]
        recorded = []

        def hidden(path):
            self.assertEqual(path, container)
            attrs = path.stat().st_file_attributes
            mark(path)
            self.assertEqual(path.stat().st_file_attributes, attrs | stat.FILE_ATTRIBUTE_HIDDEN)
            recorded.append(path)

        helper = self.queue["shared"]("task-complete")
        with mock.patch.dict(helper["shared"]("platform-support"), mark_hidden=hidden):
            self.direct_allocate("first", container / self.anchor.name / "first")
            attrs = container.stat().st_file_attributes
            self.direct_allocate("second", container / self.anchor.name / "second")
        self.assertEqual(recorded, [container])
        self.assertEqual(container.stat().st_file_attributes, attrs)

    @unittest.skipIf(os.name == "nt", "POSIX no-op")
    def test_mark_not_content_indexed_is_noop_on_posix(self):
        # Prediction: on POSIX the helper does nothing, even for a nonexistent path.
        self.assertIsNone(self.queue["shared"]("platform-support")["mark_not_content_indexed"](self.root / "missing"))
        self.assertIsNone(self.queue["shared"]("platform-support")["mark_hidden"](self.root / "missing"))

    def test_default_drain_creates_no_root_without_fresh_allocation(self):
        # Prediction: no runnable task, allocation preflight refusal and resuming an old-root receipt each leave the
        # default root absent; only a fresh allocation that passed queue preflight needs it.
        root = self.anchor.parent / ".devlyn-worktrees" / self.anchor.name
        self.assertEqual(self.drain()["tasks"], [])
        self.assertFalse(root.exists())
        self.plan("nx", [CHAIN[0]], {"nx.t1": {"product": "greeting"}})
        result = self.fault_drain("g['instruction_drift'] = lambda *args, **kwargs: 'AGENTS.md'\n")
        self.assertIn("installed instructions (AGENTS.md)", self.tasks(result)["nx.t1"]["reason"])
        self.assertEqual(self.calls("nx.t1"), 0)
        self.assertFalse(root.exists())
        self.behaviors["nx.t1"] = {"exit_now": 1}
        old_root = self.anchor.parent / f"{self.anchor.name}.devlyn.noindex"
        self.assertEqual(self.tasks(self.fault_drain("", root=old_root))["nx.t1"]["result"], "active")
        self.behaviors["nx.t1"] = {"product": "greeting"}
        self.assertEqual(self.tasks(self.drain())["nx.t1"]["result"], "accepted")
        self.assertEqual(Path(self.receipt("nx.t1")["worktree"]), old_root / "nx" / "t1")
        self.assertFalse(root.exists())

    def test_default_drain_resumes_old_root_receipt_and_allocates_new_task_hidden(self):
        # Prediction: interruption after an owned allocation under the old .devlyn root resumes at its recorded path;
        # the same default drain allocates the fresh dependent under .devlyn-worktrees/<repo>, without duplicating the old tree.
        self.plan("nx", CHAIN, {"nx.t1": {"product": "greeting"}, "nx.t2": {"product": "app"}})
        old_root = self.anchor.parent / f"{self.anchor.name}.devlyn"
        new_root = self.anchor.parent / ".devlyn-worktrees" / self.anchor.name
        argv = self.drain_argv()
        argv[argv.index("--"):argv.index("--")] = ["--worktree-root", str(old_root)]
        crashed = subprocess.run([sys.executable, "-c", CRASH, "replace", "packet.json", *argv[1:]], cwd=self.root,
                                 env=self.env, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(crashed.returncode, 9, crashed.stdout + crashed.stderr)
        original = self.receipt("nx.t1")
        self.assertEqual((original["allocation"], Path(original["worktree"])), ("owned", old_root / "nx" / "t1"))
        self.assertTrue(Path(original["worktree"]).is_dir())
        self.assertFalse(self.receipt_path("nx.t1").with_name("packet.json").exists())
        self.assertFalse(self.receipt_path("nx.t2").exists())
        self.assertFalse(new_root.exists())
        self.assertEqual((self.calls("nx.t1"), self.calls("nx.t2")), (0, 0))

        tasks = self.tasks(self.drain())
        resumed = self.receipt("nx.t1")
        self.assertEqual(resumed["worktree"], original["worktree"])
        self.assertEqual(resumed["worktree_identity"], original["worktree_identity"])
        self.assertEqual(Path(self.receipt("nx.t2")["worktree"]), new_root / "nx" / "t2")
        self.assertFalse((new_root / "nx" / "t1").exists())
        self.assertFalse((old_root / "nx" / "t2").exists())
        self.assertEqual({identity: (task["result"], task["delivery"]) for identity, task in tasks.items()},
                         {"nx.t1": ("accepted", "LOCAL_ONLY"), "nx.t2": ("accepted", "LOCAL_ONLY")})
        self.assertEqual((self.calls("nx.t1"), self.calls("nx.t2")), (1, 1))

    def test_robust_07_existing_allocations_are_never_adopted(self):
        # Prediction: existing branches or workspaces refuse only their allocation, preserve their bytes and let bb run.
        self.plan("aa", [CHAIN[0]], {"aa.t1": {"product": "greeting"}})
        self.g("branch", "devlyn/aa/t1", self.base)
        self.independent()
        result = self.drain()
        self.assert_independent(result)
        self.assertIn("existing branch cannot be adopted", self.tasks(result)["aa.t1"]["reason"])
        self.assertEqual(self.g("rev-parse", "devlyn/aa/t1"), self.base)
        self.g("branch", "-D", "devlyn/aa/t1")  # Explicit fixture recovery.
        work = self.root / ".devlyn-worktrees/repo/aa/t1"
        work.mkdir(parents=True)
        (work / "sentinel").write_text("keep", encoding="utf-8")
        self.independent("cc")
        result = self.drain()
        self.assert_independent(result, "cc")
        self.assertIn("linked worktree must be an absent path", self.tasks(result)["aa.t1"]["reason"])
        self.assertEqual((self.calls("aa.t1"), (work / "sentinel").read_text(encoding="utf-8")), (0, "keep"))
        self.assertFalse(self.receipt_path("aa.t1").exists())

    def test_robust_09_legacy_fork_refuses_integration(self):
        # Prediction: a legacy fork cannot supply both prerequisites to an integration task; it waits unchanged while bb runs.
        self.plan_checker("aa", [GREET_CHECK, NOTES_CHECK], {"aa.t1": {"product": "greeting"},
                                                            "aa.t2": {"product": "notes"}, "aa.t3": {"check_only": True}})
        # Reproduce the older driver's fork: the second sibling starts from the first allocation's base,
        # then holds the integration task until the unmodified driver can inspect the actual divergent receipts.
        self.fault_drain(
            "real_frontier = g['frontier']\nreal_allocate = g['allocate']\n"
            "def frontier(v, loop):\n    return None if loop == 'aa' else real_frontier(v, loop)\n"
            "def allocate(v, row, opts):\n"
            "    if row['identity'] == 'aa.t3':\n        return 'legacy fixture pause'\n"
            "    return real_allocate(v, row, opts)\ng['frontier'] = frontier\ng['allocate'] = allocate\n")
        self.independent()
        result = self.drain()
        self.assert_independent(result)
        reason = self.tasks(result)["aa.t3"]["reason"]
        self.assertIn("prerequisite source", reason)
        self.assertIn("plan an integration task", reason)
        self.assertEqual([self.calls(f"aa.t{i}") for i in (1, 2, 3)], [1, 1, 0])

    @unittest.skipIf(os.name == "nt", "fake remote uses POSIX wrappers")
    def test_robust_08_remote_allocation_preserves_conflicted_carrier(self):
        # Prediction: an independent remote allocation must not invoke the direct helper's repository-wide cleanup
        # on a queue-invalid carrier, even after its PR merged. Its receipt, packet, branch and workspace stay untouched.
        _, data = self.remote(pending=True)
        self.plan_checker("aa", [GREET_CHECK, NOTES_CHECK], {"aa.t1": {"product": "greeting"},
                                                            "aa.t2": {"product": "notes"}, "aa.t3": {"check_only": True}}, delivery="auto")
        self.drain(local=False)
        receipt_path = self.receipt_path("aa.t1")
        receipt_bytes = receipt_path.read_bytes()
        receipt = json.loads(receipt_bytes)
        packet = receipt_path.with_name("packet.json")
        damaged = json.loads(packet.read_text(encoding="utf-8"))
        damaged["submission"] = []
        packet.write_text(json.dumps(damaged), encoding="utf-8")
        self.assertEqual(self.merge_pr(data, 1).returncode, 0)
        self.plan("bb", [("t1", [], "Notes", [NOTES_CHECK])], {"bb.t1": {"product": "notes"}}, delivery="auto")
        result = self.drain(local=False)
        self.assert_independent(result)
        self.assertEqual((self.calls("aa.t1"), self.calls("aa.t2")), (1, 0))
        self.assertEqual(receipt_path.read_bytes(), receipt_bytes)
        self.assertEqual(json.loads(packet.read_text(encoding="utf-8")), damaged)
        self.assertTrue(Path(receipt["worktree"]).is_dir())
        self.assertEqual(self.g("rev-parse", receipt["branch"]), receipt["publish_sha"])

    def test_successful_local_chain_keeps_custody_and_transfers_metadata(self):
        # Both executors refuse a piped stdout, as codex-monitored.sh does, and the driver's stdin; the driver gives them
        # files and the null device.
        behavior = {"refuse_pipe": True, "stdin_eof": True}
        self.plan("inv", CHAIN, {"inv.t1": {"product": "greeting", **behavior}, "inv.t2": {"product": "app", **behavior}})
        result = self.drain(stdin="driver input\n")
        tasks = self.tasks(result)
        self.assertEqual((result["status"], tasks["inv.t1"]["result"], tasks["inv.t2"]["result"]), ("WAITING", "accepted", "accepted"))
        self.assertEqual((self.calls("inv.t1"), self.calls("inv.t2")), (1, 1))
        first, second = self.receipt("inv.t1"), self.receipt("inv.t2")
        self.assertNotEqual(first["worktree"], second["worktree"])
        self.assertTrue(all((Path(r["worktree"]) / ".devlyn/loop" / name).is_file() for r in (first, second)
                            for name in ("executor.stdout", "executor.stderr")))
        self.assertTrue(Path(first["worktree"]).is_dir() and Path(second["worktree"]).is_dir())
        self.assertEqual((second["baseline"], second["allocated_from"]["source_sha"]), (first["source_sha"], first["source_sha"]))
        self.assertNotEqual(second["baseline"], first["publish_sha"])
        self.assertEqual(first["queue"]["commit"], first["publish_sha"])
        for receipt in (first, second):
            # Local-only: source, custody and recovery ref exist although nothing was delivered remotely.
            self.assertEqual((receipt["local_only"], receipt["delivery"]), (True, "LOCAL_ONLY"))
            self.assertEqual(self.g("rev-parse", receipt["recovery_ref"]), receipt["publish_sha"])
            self.assertEqual(self.g("rev-parse", receipt["publish_sha"] + "^"), receipt["source_sha"])
            custody = Path(receipt["common_gitdir"]) / "devlyn-completion" / receipt["id"] / "custody"
            self.assertTrue((custody / ".devlyn/loop/acceptance.json").is_file())
            self.assertTrue(all((custody / path).is_file() for path in receipt["acceptance"]["evidence"]))
        t1_row = self.rows(first["publish_sha"])["inv.t1"]["line"]
        self.assertTrue(t1_row.startswith("- [x] inv.t1 [Greeting interface 인사]"))
        inputs = second["acceptance"]["inputs_sha"]
        self.assertEqual(self.queue_at(inputs, "inv"), t1_row + "\n\n" + self.queue["row_line"]("inv.t2", "Greeting app [cli]"))
        self.assertEqual(self.run_ok([sys.executable, "app.py", "Ada"], cwd=second["worktree"]), "Hello, Ada!")
        report = (self.common / "devlyn-loops/inv/drain-report.md").read_text(encoding="utf-8")
        self.assertIn("Whole-loop acceptance: ACCEPTED", report)
        self.assertIn("fixture assumption for inv.t2", report)
        status = self.cli("status", "--repo", self.anchor)
        self.assertEqual((status["counts"]["accepted"], status["counts"]["legacy_pending"], status["next"]), (2, 1, None))
        self.assertIn("legacy row 4 needs planning: unrelated legacy intent", status["blockers"])
        self.assertEqual(((self.anchor / "docs/specs/queue.md").read_bytes(), (self.anchor / "docs/specs/inv").exists()), (self.base_queue, False))

        # Conflicting terminal receipts invalidate the implicated task, naming both receipts, while independent work continues.
        foreign = self.root / "foreign"
        allocated = json.loads(self.run_ok([sys.executable, str(self.helper), "allocate", "--repo", str(self.anchor), "--task", "inv.t1",
                                            "--branch", "foreign/t1", "--repository", "test/project", "--base", "main",
                                            "--worktree", str(foreign), "--local-base", self.base]))
        (foreign / "greeting.py").write_text("def greet(name):\n    return name\n", encoding="utf-8")
        self.g("add", "greeting.py", work=foreign)
        self.g("commit", "-qm", "foreign", work=foreign)
        (foreign / ".devlyn").mkdir()
        (foreign / ".devlyn/check.log").write_text("manual\n", encoding="utf-8")
        (foreign / ".devlyn/acceptance.json").write_text(json.dumps({
            "kind": "direct", "task": "inv.t1", "source_sha": self.g("rev-parse", "HEAD", work=foreign),
            "checks": [{"command": "manual", "evidence": ".devlyn/check.log"}]}), encoding="utf-8")
        self.run_ok([sys.executable, str(self.helper), "accept", "--receipt", allocated["receipt"], "--acceptance", str(foreign / ".devlyn/acceptance.json")])
        blocked = " ".join(self.cli("status", "--repo", self.anchor)["blockers"])
        self.assertIn("conflicting receipts for inv.t1", blocked)
        self.assertIn(allocated["receipt"], blocked)
        self.independent()
        result = self.drain()
        self.assert_independent(result)
        self.assertIn("conflicting receipts for inv.t1", self.tasks(result)["inv.t1"]["reason"])
        self.assertEqual((self.calls("inv.t1"), self.calls("inv.t2")), (1, 1))

    def test_the_drain_fills_the_task_worktree_git_dir(self):
        # Prediction (E1): {worktree_git_dir} in the executor argv arrives as the task worktree's
        # `git rev-parse --path-format=absolute --git-dir`, the directory a Codex sandbox must list for the executor to
        # commit there, and {packet} still arrives as the packet path. Before: the literal placeholder arrived.
        self.plan("inv", [CHAIN[0]], {"inv.t1": {"product": "greeting"}})
        drained = subprocess.run(self.drain_argv() + ["{worktree_git_dir}"], cwd=self.root, env=self.env, capture_output=True,
                                 text=True, encoding="utf-8")
        self.assertEqual(drained.returncode, 0, drained.stdout + drained.stderr)
        worktree = Path(self.receipt("inv.t1")["worktree"])
        self.assertEqual(json.loads(self.config.with_name("calls-inv.t1").read_text(encoding="utf-8")),
                         [str(self.receipt_path("inv.t1").with_name("packet.json")),
                          self.g("rev-parse", "--path-format=absolute", "--git-dir", work=worktree)])

    def added(self, loop):
        return json.loads((self.common / f"devlyn-loops/{loop}/added.json").read_text(encoding="utf-8"))

    def report(self, loop):
        return (self.common / f"devlyn-loops/{loop}/drain-report.md").read_text(encoding="utf-8")

    def package(self, loop, tasks=("t1",)):
        return sorted([f"docs/specs/{loop}/meta.md", f"docs/specs/{loop}/queue.md"]
                      + [f"docs/specs/{loop}/{task}/{name}" for task in tasks for name in ("spec.expected.json", "spec.md")])

    def test_local_loop_fast_forwards_the_anchor_branch(self):
        # Prediction (L, B): the first task starts from the HEAD of the branch the loop was added on, so its inputs commit
        # adds the captured package directory with the loop's queue file, the dependent's adds only the predecessor's [x]
        # row, and the report's `git merge --ff <final frontier branch>` fast-forwards that branch with a clean tree. Before:
        # the first task started from add's commit and the report printed `git merge --ff-only`.
        self.plan("inv", CHAIN, {"inv.t1": {"product": "greeting"}, "inv.t2": {"product": "app"}})
        self.drain()
        first, final = self.receipt("inv.t1"), self.receipt("inv.t2")
        self.assertIn(f"- Bring into main: git merge --ff {final['branch']}\n", self.report("inv"))
        merged = self.bring_in("inv")
        self.assertEqual(merged.returncode, 0, merged.stdout + merged.stderr)
        self.assertEqual((self.g("rev-parse", "HEAD"), self.g("status", "--porcelain", "--untracked-files=all")), (final["publish_sha"], ""))
        self.assertEqual({identity: row["mark"] for identity, row in self.rows("HEAD").items()}, {"inv.t1": "x", "inv.t2": "x"})
        self.assertEqual((first["baseline"], self.g("diff", "--name-only", first["baseline"], first["acceptance"]["inputs_sha"]).splitlines()),
                         (self.base, self.package("inv", ("t1", "t2"))))
        self.assertEqual(self.g("diff", "--name-only", final["baseline"], final["acceptance"]["inputs_sha"]), "docs/specs/inv/queue.md")

    def test_the_report_carries_the_captured_package_decisions_once(self):
        # Prediction (rp-d3 policy 1): the drain report carries the package's decisions once, read from its capture. With the
        # manifest after the decisions inside `## Decisions and assumptions`, as a real plan wrote it, each decision appears
        # exactly once and no manifest JSON does, although dc.t1's executor submits no assumptions, and dc.t2's executor
        # assumption stays in its own section. With the checkout copy of meta.md absent, then differing, the report keeps the
        # captured decisions and never shows the checkout's. Before: the report carried executor assumptions only.
        meta = self.queue["write_package"](self.anchor, "dc", CHAIN, base=self.base)
        text = meta.read_text(encoding="utf-8")
        manifest = self.queue["JSON_FENCE_RE"].search(text).group(0)
        decisions = ["- D1: Names print in argument order, as the request lists them.", "- D2: Output is UTF-8, the project convention."]
        meta.write_text(text.replace(manifest + "\n\n", "").replace("None beyond the task contracts.", "\n".join(decisions) + "\n\n" + manifest),
                        encoding="utf-8")
        self.behaviors.update({"dc.t1": {"product": "greeting", "assumptions": []}, "dc.t2": {"product": "app"}})
        self.cli("add", meta)
        captured = self.g("show", "refs/devlyn/captures/dc:docs/specs/dc/meta.md")
        self.assertFalse(meta.exists())
        for copy in (None, captured.replace(decisions[0], "- D9: A checkout-only decision.")):
            if copy:
                meta.parent.mkdir(parents=True)
                meta.write_text(copy, encoding="utf-8")
            self.assertEqual({identity: task["result"] for identity, task in self.tasks(self.drain()).items()}, {"dc.t1": "accepted", "dc.t2": "accepted"})
            report = self.report("dc")
            self.assertEqual([report.count(part) for part in ("## Package decisions and assumptions\n", *decisions, "D9", '"integration_task_id"',
                                                              "fixture assumption for dc.t1", "- Assumptions: fixture assumption for dc.t2\n")],
                             [1, 1, 1, 0, 0, 0, 1])
        self.assertEqual((self.calls("dc.t1"), self.calls("dc.t2")), (1, 1))

    def test_an_unreadable_package_reports_its_decisions_unavailable(self):
        # Prediction (rp-d3 policy 1): a loop without an add record, read as in a fresh clone from its tracked queue file,
        # whose meta.md is gone, still gets its full report: nr.t1 pending with the missing file as its reason, whole-loop
        # acceptance INCOMPLETE naming the unreadable manifest, and "Unavailable: <reason>" as its package decisions. Before:
        # the report said nothing about the package decisions.
        queue = self.anchor / "docs/specs/nr/queue.md"
        queue.parent.mkdir()
        queue.write_text(self.queue["row_line"]("nr.t1", "Notes") + "\n", encoding="utf-8")
        self.g("add", str(queue))
        self.g("commit", "-qm", "a loop's queue file without its package")
        missing = f"{queue.with_name('meta.md')}: no such file"
        self.assertEqual(self.tasks(self.drain())["nr.t1"]["reason"], missing)
        report = self.report("nr")
        for part in (f"- Whole-loop acceptance: INCOMPLETE — manifest unreadable: {missing}\n",
                     f"## Package decisions and assumptions\n\nUnavailable: {missing}\n", f"## nr.t1\n\n- Product: pending\n- Reason: {missing}\n"):
            self.assertIn(part, report)

    def test_a_package_without_decisions_reports_none_recorded(self):
        # Prediction (rp-d3 policy 1): when the package's `## Decisions and assumptions` holds only the manifest, the report's
        # package decisions read "None recorded.". Before: that section of the report was empty.
        meta = self.queue["write_package"](self.anchor, "nd", [CHAIN[0]], base=self.base)
        text = meta.read_text(encoding="utf-8")
        manifest = self.queue["JSON_FENCE_RE"].search(text).group(0)
        meta.write_text(text.replace(manifest + "\n\n", "").replace("None beyond the task contracts.", manifest), encoding="utf-8")
        self.behaviors["nd.t1"] = {"product": "greeting"}
        self.cli("add", meta)
        self.drain()
        self.assertIn("## Package decisions and assumptions\n\nNone recorded.\n\n## nd.t1\n", self.report("nd"))

    def test_a_local_loop_starts_from_the_branch_it_was_added_on(self):
        # Prediction (L): with the checkout switched to another branch, a local loop's first task starts from the HEAD of
        # the branch it was added on, and the report brings it into that branch; while that HEAD does not descend from the
        # manifest base_sha, or the checkout's instructions differ from it, the task waits naming the reason and its remedy,
        # with no executor call, then runs once the branch holds base_sha or the instructions are committed. Before: a
        # branch moved behind base_sha was not checked at allocation, and the instruction wait named only the remedies of
        # a fixed start.
        self.plan("aa", [CHAIN[0]], {"aa.t1": {"product": "greeting"}})
        self.g("commit", "-q", "--allow-empty", "-m", "moves main")
        moved = self.g("rev-parse", "HEAD")
        self.plan("bb", [("t1", [], "Notes", [NOTES_CHECK])], {"bb.t1": {"product": "notes"}}, base=moved)
        self.g("checkout", "-q", "-b", "side")
        self.g("commit", "-q", "--allow-empty", "-m", "side work")
        self.g("branch", "-f", "main", self.base)
        tasks = self.tasks(self.drain())
        self.assertEqual((tasks["aa.t1"]["result"], self.receipt("aa.t1")["baseline"], tasks["bb.t1"].get("reason"), self.calls("bb.t1")),
                         ("accepted", self.base, f"main, the branch bb was added on, is at {self.base}, which does not descend from the manifest "
                          f"base_sha {moved}; bring {moved} into main, or plan the work as a new loop", 0))
        self.assertIn("- Bring into main: git merge --ff devlyn/aa/t1\n", self.report("aa"))
        self.g("branch", "-f", "main", moved)
        self.assertEqual((self.tasks(self.drain())["bb.t1"]["result"], self.receipt("bb.t1")["baseline"]), ("accepted", moved))
        self.plan("cc", [("t1", [], "Todo", [TODO_CHECK])], {"cc.t1": {"product": "todo"}}, base=moved)
        (self.anchor / "CLAUDE.md").write_text("# Installed instructions\n", encoding="utf-8")
        side = self.g("rev-parse", "HEAD")
        self.assertEqual(self.tasks(self.drain())["cc.t1"].get("reason"), f"the installed instructions (CLAUDE.md) in this checkout differ from "
                         f"those in its start commit {side}, so it would run without them; commit them on side, or restore them to their bytes at that commit")
        self.g("add", "CLAUDE.md")
        self.g("commit", "-qm", "install instructions")
        self.assertEqual((self.tasks(self.drain())["cc.t1"]["result"], self.methodology("cc.t1")), ("accepted", ["CLAUDE.md"]))

    def test_a_local_loop_keeps_the_start_its_first_allocation_fixed(self):
        # Prediction (L): once its first allocation fixed a local loop's start, a later independent task starts from that
        # same commit after the first task failed, though the branch has moved since. Before (95fbccef): it started from
        # the moved branch HEAD.
        tasks = [CHAIN[0], ("t2", [], "Notes", [NOTES_CHECK]), ("t3", ["t1", "t2"], "Greeting app", [APP_CHECK])]
        self.plan("cc", tasks, {"cc.t1": {"product": "bad-greeting"}, "cc.t2": {"product": "notes"}, "cc.t3": {"product": "app"}})
        blocked = self.cli("drain", "--repo", self.anchor, "--local-only", "--", str(self.root / "no executor"), "{packet}")
        self.assertIn("executor could not start", " ".join(task.get("reason", "") for task in blocked["tasks"]))
        self.g("commit", "-q", "--allow-empty", "-m", "moves main")
        tasks = self.tasks(self.drain())
        self.assertEqual({identity: task["result"] for identity, task in tasks.items()}, {"cc.t1": "failed", "cc.t2": "accepted", "cc.t3": "blocked"})
        self.assertEqual((self.receipt("cc.t1")["baseline"], self.receipt("cc.t2")["baseline"]), (self.base, self.base))

    def test_a_loop_id_another_clone_brought_in_makes_the_first_task_wait(self):
        # Prediction (C, L): clone B adds a local loop dup, then pulls clone A's loop dup, so the branch B added it on holds
        # another docs/specs/dup/. B's dup.t1 waits, naming the files that differ from B's capture and the remedies, with no
        # executor call, status names that wait, and a loop zz added after it is accepted in the same drain. Before: dup.t1
        # bound A's contract and was accepted on A's product, then the drain ended BLOCKED "dup.t1 has no pending queue row".
        bare, clone = self.root / "remote.git", self.root / "clone b"
        self.run_ok(["git", "init", "-q", "--bare", "--initial-branch=main", str(bare)])
        self.run_ok(["git", "-C", str(self.anchor), "push", "-q", str(bare), "main"])
        self.run_ok(["git", "clone", "-q", str(bare), str(clone)])
        self.plan("dup", [("t1", [], "Notes", [NOTES_CHECK])], {"dup.t1": {"product": "notes"}})
        self.drain()
        self.assertEqual(self.bring_in("dup").returncode, 0)
        self.run_ok(["git", "-C", str(self.anchor), "push", "-q", str(bare), "main"])
        self.cli("add", self.queue["write_package"](clone, "dup", [("t1", [], "Todo", [TODO_CHECK])], base=self.base))
        self.run_ok(["git", "-C", str(clone), "pull", "-q", "--ff-only", "origin", "main"])
        self.cli("add", self.queue["write_package"](clone, "zz", [("t1", [], "Greeting", [GREET_CHECK])]))
        self.behaviors.update({"dup.t1": {"product": "bad-app"}, "zz.t1": {"product": "greeting"}})
        tasks = self.tasks(self.drain(repo=clone))
        reason = ("main holds another version of loop dup's package (differing from refs/devlyn/captures/dup: docs/specs/dup/t1/spec.expected.json, "
                  "docs/specs/dup/t1/spec.md), so its tasks cannot run their captured contracts there; plan the work as a new loop, or restore "
                  "those files on main to the captured bytes")
        self.assertEqual(({identity: (task["result"], task.get("reason")) for identity, task in tasks.items()}, self.calls("dup.t1")),
                         ({"dup.t1": ("pending", reason), "zz.t1": ("accepted", None)}, 1))  # the one call is A's
        self.assertIn(f"dup.t1: {reason}", self.cli("status", "--repo", clone)["blockers"])

    def test_two_local_loops_bring_in_in_either_order(self):
        # Prediction (Q, B): two local loops added before draining keep their rows in their own queue files, so each
        # report's `git merge --ff <frontier branch>` applies after the other in either order without a conflict, every row
        # [x]. Before: the reports promised a fast-forward for one loop and a merge for the other, so the other order failed.
        self.plan("aa", [CHAIN[0]], {"aa.t1": {"product": "greeting"}})
        self.plan("bb", [("t1", [], "Notes", [NOTES_CHECK])], {"bb.t1": {"product": "notes"}})
        self.drain()
        for order in (("aa", "bb"), ("bb", "aa")):
            self.g("reset", "-q", "--hard", self.base)
            for loop in order:
                self.assertIn(f"- Bring into main: git merge --ff devlyn/{loop}/t1\n", self.report(loop))
                merged = self.bring_in(loop)
                self.assertEqual(merged.returncode, 0, merged.stdout + merged.stderr)
            self.assertEqual({identity: row["mark"] for identity, row in self.rows("HEAD").items()}, {"aa.t1": "x", "bb.t1": "x"})

    def test_every_queue_file_the_loop_writes_passes_newline_hooks(self):
        # Prediction (R1, Q): pre-commit's end-of-file-fixer check (no file ending in more than one newline) and a check for
        # two consecutive blank lines accept each queue file the loop writes: a capture, a --materialize capture with its
        # replaced-row line, and a terminal commit's. Before R1: the queue a local add committed ended in a blank line.
        checks = self.root / "newline hooks.py"
        checks.write_text(NEWLINE_HOOKS, encoding="utf-8")
        self.plan("aa", [("t1", [], "Notes", [NOTES_CHECK])], {"aa.t1": {"product": "notes"}})
        meta = self.queue["write_package"](self.anchor, "bb", [("t1", [], "Todo", [TODO_CHECK])], base=self.base,
                                           intent="User asked: unrelated legacy intent.")
        self.behaviors.update({"bb.t1": {"product": "todo"}})
        self.cli("add", meta, "--materialize", 4)
        self.assertEqual({identity: task["result"] for identity, task in self.tasks(self.drain()).items()}, {"bb.t1": "accepted", "aa.t1": "accepted"})
        for loop, rev in (("aa", "refs/devlyn/captures/aa"), ("bb", "refs/devlyn/captures/bb"), ("bb", self.receipt("bb.t1")["publish_sha"])):
            data = subprocess.run(["git", "-C", str(self.anchor), "cat-file", "blob", f"{rev}:docs/specs/{loop}/queue.md"], env=self.env,
                                  capture_output=True, check=True).stdout
            checked = subprocess.run([sys.executable, str(checks)], input=data, capture_output=True)
            self.assertEqual((rev, checked.returncode, data.endswith(b")\n")), (rev, 0, True), checked.stderr)

    def methodology(self, identity):
        return [Path(entry["path"]).name for entry in json.loads(self.receipt_path(identity).with_name("packet.json").read_text(encoding="utf-8"))["methodology"]["projectInstructions"]]

    def test_add_refuses_a_head_without_the_checkouts_instructions(self):
        # Prediction (E3): a checkout with neither CLAUDE.md nor AGENTS.md drains normally, its packet listing no
        # methodology; an uncommitted CLAUDE.md makes add refuse, naming the file, HEAD and the remedy, with no queue, index,
        # ref or record change; once CLAUDE.md is committed, add succeeds and the task's packet lists it. Before: add
        # committed the loop from a HEAD without CLAUDE.md, and its task ran without the installed instructions.
        self.plan("nf", [("t1", [], "Notes", [NOTES_CHECK])], {"nf.t1": {"product": "notes"}})
        self.assertEqual((self.tasks(self.drain())["nf.t1"]["result"], self.methodology("nf.t1")), ("accepted", []))
        (self.anchor / "CLAUDE.md").write_text("# Installed instructions\n", encoding="utf-8")
        meta = self.queue["write_package"](self.anchor, "ci", [("t1", [], "Todo", [TODO_CHECK])], base=self.base)
        self.behaviors.update({"ci.t1": {"product": "todo"}})

        def state():
            return (self.g("for-each-ref"), self.g("ls-files", "-s"), (self.anchor / "docs/specs/queue.md").read_bytes(),
                    (self.common / "devlyn-loops/ci").exists())
        before, head = state(), self.g("rev-parse", "HEAD")
        self.assertEqual(self.cli("add", meta, code=1)["reason"], f"the installed instructions (CLAUDE.md) in this checkout differ from those "
                         f"in HEAD {head}, so the loop's tasks would run without them; commit them, then add the loop")
        self.assertEqual(state(), before)
        self.g("add", "CLAUDE.md")
        self.g("commit", "-qm", "install instructions")
        self.cli("add", meta)
        self.assertEqual((self.tasks(self.drain())["ci.t1"]["result"], self.methodology("ci.t1")), ("accepted", ["CLAUDE.md"]))

    @unittest.skipIf(os.name == "nt", "a symbolic link needs a privilege on Windows")
    def test_instructions_git_reports_unchanged_are_the_checkouts(self):
        # Prediction: instruction files `git status` reports unchanged are the checkout's, so each of the installer's
        # layouts, AGENTS.md committed as a link to CLAUDE.md (-y --claude) and CLAUDE.md as a link to AGENTS.md (-y), and a
        # CLAUDE.md committed with CRLF line endings under core.autocrlf=true lets add capture a loop whose task is accepted
        # with the files in its methodology. Before: each blob was compared with `git hash-object` of the file, which
        # follows a link and, reading no index, normalizes a CRLF blob, so add refused although nothing was left to commit.
        def install(loop, message, links=(), crlf=False):
            for name in ("CLAUDE.md", "AGENTS.md"):
                (self.anchor / name).unlink(missing_ok=True)
            (self.anchor / "CLAUDE.md").write_bytes(b"# Installed\r\nUse tabs.\r\n" if crlf else b"# Installed\n")
            for name, target in links:
                (self.anchor / name).unlink(missing_ok=True)
                (self.anchor / target).write_bytes(b"# Installed\n")
                os.symlink(target, self.anchor / name)
            self.g("-c", "core.autocrlf=false", "add", "-A", "--", "CLAUDE.md", "AGENTS.md")
            self.g("commit", "-qm", message)
            if crlf:
                self.g("config", "core.autocrlf", "true")
            self.assertEqual(self.g("status", "--porcelain", "--", "CLAUDE.md", "AGENTS.md"), "")
            self.plan(loop, [("t1", [], "Notes", [NOTES_CHECK])], {f"{loop}.t1": {"product": "notes"}})
            return self.tasks(self.drain())[f"{loop}.t1"]["result"], self.methodology(f"{loop}.t1")
        self.assertEqual(install("la", "AGENTS.md links to CLAUDE.md", [("AGENTS.md", "CLAUDE.md")]), ("accepted", ["CLAUDE.md", "AGENTS.md"]))
        self.assertEqual(install("lb", "CLAUDE.md links to AGENTS.md", [("CLAUDE.md", "AGENTS.md")]), ("accepted", ["CLAUDE.md", "AGENTS.md"]))
        self.assertEqual(install("lc", "CLAUDE.md with CRLF line endings", crlf=True), ("accepted", ["CLAUDE.md"]))

    def test_add_leaves_the_branch_index_and_worktree_as_they_were(self):
        # Prediction (C): add commits nothing; HEAD, unrelated staged and unstaged changes and the legacy queue stay as they
        # were, and only the package originals, now held by the capture, leave the checkout, so `git commit -am` right after
        # add commits only the user's own changes while status shows the loop's next task. Before: add committed the package
        # and the queue on the current branch.
        (self.anchor / "staged.txt").write_text("staged\n", encoding="utf-8")
        self.g("add", "staged.txt")
        with (self.anchor / ".gitignore").open("a", encoding="utf-8") as ignore:
            ignore.write("# unstaged edit\n")
        self.plan("inv", CHAIN, {})
        self.assertEqual((self.g("rev-parse", "HEAD"), self.g("diff", "--cached", "--name-only"), self.g("diff", "--name-only"),
                          self.g("ls-files", "--others"), (self.anchor / "docs/specs/queue.md").read_bytes()), (self.base, "staged.txt", ".gitignore", "", self.base_queue))
        capture = self.g("rev-parse", "refs/devlyn/captures/inv")
        self.assertEqual(self.g("ls-tree", "-r", "--name-only", capture).splitlines(), self.package("inv", ("t1", "t2")))
        self.assertEqual(self.added("inv"), {"schema_version": 1, "loop_id": "inv", "delivery": "local-only", "capture": "refs/devlyn/captures/inv",
                                             "commit": capture, "tree": self.g("rev-parse", capture + "^{tree}"), "origin": str(self.anchor),
                                             "branch": "main", "sequence": 1})
        self.g("commit", "-qam", "own changes")
        self.assertEqual((self.g("show", "--name-only", "--format=", "HEAD"), self.cli("status", "--repo", self.anchor)["next"]),
                         (".gitignore\nstaged.txt", "inv.t1"))

    def crashed_add(self, meta, step, name):
        crashed = subprocess.run([sys.executable, "-c", CRASH, step, name, str(self.queue_py), "add", str(meta)], cwd=self.root, env=self.env,
                                 capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(crashed.returncode, 9, crashed.stdout + crashed.stderr)

    def test_an_interrupted_add_is_recovered_at_each_capture_step(self):
        # Prediction (C): add stopped after creating its capture ref, before the record, leaves the originals in place and no
        # record, and its retry captures the same package again, under the same commit; stopped after the record, before any
        # cleanup, it leaves every original, and the next status removes them; stopped during cleanup, its retry reports the
        # same capture and removes the rest. The drain then accepts each loop. Before: add committed on the branch and an
        # intent record rolled the commit back or recorded it.
        for loop, step, name in (("rf", "replace", "added.json"), ("ul", "unlink", "meta.md"), ("us", "unlink", "spec.md")):
            with self.subTest(loop=loop):
                meta = self.queue["write_package"](self.anchor, loop, [CHAIN[0]], base=self.base)
                self.behaviors[f"{loop}.t1"] = {"product": "greeting"}
                self.crashed_add(meta, step, name)
                capture, package = self.g("rev-parse", f"refs/devlyn/captures/{loop}"), self.anchor / "docs/specs" / loop
                self.assertEqual(((self.common / f"devlyn-loops/{loop}/added.json").exists(), sorted(path.name for path in package.rglob("*.*"))),
                                 {"rf": (False, ["meta.md", "spec.expected.json", "spec.md"]), "ul": (True, ["meta.md", "spec.expected.json", "spec.md"]),
                                  "us": (True, ["spec.md"])}[loop])
                if loop == "ul":
                    self.cli("status", "--repo", self.anchor)
                else:
                    self.assertEqual(self.cli("add", meta)["commit"], capture)
                self.assertEqual((self.added(loop)["commit"], package.exists(), self.g("status", "--porcelain", "--untracked-files=all")), (capture, False, ""))
        self.assertEqual({identity: task["result"] for identity, task in self.tasks(self.drain()).items()},
                         {"rf.t1": "accepted", "ul.t1": "accepted", "us.t1": "accepted"})

    def test_the_capture_ref_keeps_the_package_through_garbage_collection(self):
        # Prediction (C): once add removed the originals no commit or file holds the package, yet `git gc --prune=now` keeps
        # the captured commit, its tree and blobs, which refs/devlyn/captures/gc reaches, so `git show` still prints the
        # package and the drain accepts the loop from it. Before: no capture ref existed.
        self.plan("gc", [CHAIN[0]], {"gc.t1": {"product": "greeting"}})
        meta = self.g("show", "refs/devlyn/captures/gc:docs/specs/gc/meta.md")
        self.g("gc", "-q", "--prune=now")
        self.assertEqual(self.g("show", "refs/devlyn/captures/gc:docs/specs/gc/meta.md"), meta)
        self.assertEqual(self.tasks(self.drain())["gc.t1"]["result"], "accepted")

    def test_a_local_only_drain_runs_an_unpublished_auto_loop_locally(self):
        # Prediction (A): an auto loop whose tasks have not published, drained with --local-only, runs as a local loop from
        # its capture and the branch it was added on: its task, in the place of the legacy row it materializes, is accepted
        # LOCAL_ONLY beside a local loop's, no remote is needed, and its report brings it into main with `git merge --ff`.
        # Before (b3774008): it waited, "au was added for auto delivery, so no add commit carries its package".
        # Prediction (H5): first, drained without --local-only, au.t1 waits with no receipt or executor call, its reason
        # naming the origin forms auto delivery takes and both remedies, while lo.t1 is accepted; an origin URL holding a
        # token, a GitLab or a GitHub one, reaches neither the drain's output nor its report. Before: allocation raised, so
        # the drain ended BLOCKED with "git config --get: " or the URL check's error, never naming --local-only, and lo.t1
        # never ran; then (da682f47) the reason quoted origin, token included, and told a GitHub origin to add one.
        meta = self.queue["write_package"](self.anchor, "au", [CHAIN[0]], delivery="auto", base=self.base,
                                           intent="User asked: unrelated legacy intent.")
        self.behaviors.update({"au.t1": {"product": "greeting"}})
        self.cli("add", meta, "--materialize", 4)
        self.plan("lo", [("t1", [], "Notes", [NOTES_CHECK])], {"lo.t1": {"product": "notes"}})
        needs = ("auto delivery needs an origin remote of the form https://github.com/<owner>/<repo>, git@github.com:<owner>/<repo> "
                 "or ssh://git@github.com/<owner>/<repo>; set one, or drain with --local-only")
        self.g("remote", "add", "origin", "https://oauth2:glpat-SECRET@gitlab.com/team/project.git")
        result = self.drain(local=False)
        self.assertEqual({identity: (task["result"], task.get("reason")) for identity, task in self.tasks(result).items()},
                         {"au.t1": ("pending", needs), "lo.t1": ("accepted", None)})
        seen = json.dumps(result) + self.report("au")
        self.g("remote", "set-url", "origin", "https://x-access-token:ghp_SECRET@github.com/test/project.git")
        result = self.drain(local=False)
        seen += json.dumps(result) + self.report("au")
        self.g("remote", "remove", "origin")
        self.assertEqual([self.tasks(drained)["au.t1"].get("reason") for drained in (result, self.drain(local=False))], [needs, needs])
        self.assertNotIn("SECRET", seen)
        self.assertEqual((self.receipt_path("au.t1").exists(), self.calls("au.t1")), (False, 0))
        result = self.drain()
        tasks = self.tasks(result)
        self.assertEqual([(identity, task["result"], task["delivery"]) for identity, task in tasks.items()],
                         [("au.t1", "accepted", "LOCAL_ONLY"), ("lo.t1", "accepted", "LOCAL_ONLY")])
        self.assertEqual((result["status"], self.receipt("au.t1")["baseline"]), ("DRAINED", self.base))
        self.assertIn("- Bring into main: git merge --ff devlyn/au/t1\n", self.report("au"))

    def test_frontier_is_the_latest_accepted_source(self):
        tasks = [CHAIN[0], ("t2", [], "Notes", [NOTES_CHECK]), ("t3", ["t1"], "Greeting app", [APP_CHECK]), ("t4", ["t2", "t3"], "Notes again", [NOTES_CHECK])]
        self.plan("fr", tasks, {"fr.t1": {"product": "greeting"}, "fr.t2": {"product": "notes"}, "fr.t3": {"product": "app"}, "fr.t4": {"check_only": True}})
        result = self.drain()
        t1, t2, t3, t4 = (self.receipt(f"fr.{task}") for task in ("t1", "t2", "t3", "t4"))
        # Each later task starts from the latest accepted source, not the first.
        self.assertEqual((t2["baseline"], t3["baseline"], t4["baseline"]), (t1["source_sha"], t2["source_sha"], t3["source_sha"]))
        # Prediction (rp-d3 policy 2): the check-only fr.t4 submits its committed inputs unchanged and is accepted, so the loop
        # is ACCEPTED. Before: its executor committed notes.txt unchanged, which git refused, so fr.t4 never submitted.
        self.assertEqual(self.tasks(result)["fr.t4"]["result"], "accepted")
        self.assertEqual(t4["source_sha"], t4["acceptance"]["inputs_sha"])
        self.assertIn("- Whole-loop acceptance: ACCEPTED\n", self.report("fr"))
        # A consistent failed result whose attached terminal commit still carries [x] stops selection.
        receipt = self.receipt_path("fr.t1")
        value = json.loads(receipt.read_text(encoding="utf-8"))
        value["product"] = "FAILED"
        value["acceptance"].update(verdict="FAILED", reasons=["failed: fixture terminal mismatch"])
        receipt.write_text(json.dumps(value), encoding="utf-8")
        self.assertIn(f"fr.t1: terminal commit {t1['publish_sha']} does not carry its failed mark", " ".join(self.cli("status", "--repo", self.anchor)["blockers"]))

    def plan_checker(self, loop, checks, behaviors, delivery="local-only"):
        """Add a loop of independent t1 and t2, then t3, a check-only task depending on both whose diff guard refuses any
        source change (rp-d3 policy 2)."""
        tasks = [CHAIN[0], ("t2", [], "Notes", [NOTES_CHECK]), ("t3", ["t1", "t2"], "Assembled product", checks)]
        meta = self.queue["write_package"](self.anchor, loop, tasks, delivery=delivery, base=self.base)
        (meta.parent / "t3/spec.expected.json").write_text(json.dumps({"verification_commands": checks, "forbidden_patterns": [
            {"pattern": ".", "description": "No source changes", "severity": "disqualifier"}]}), encoding="utf-8")
        self.behaviors.update(behaviors)
        self.cli("add", meta)

    def test_a_check_only_task_accepts_its_unchanged_candidate(self):
        # Prediction (rp-d3 policy 2): with the independent ck.t1 and ck.t2 accepted, the check-only ck.t3, which depends on
        # both, submits its committed inputs unchanged (source_sha == inputs_sha, no empty commit); both its checks pass, so
        # they observe both products, its diff guard passes, and it is accepted and delivered LOCAL_ONLY, so the loop is
        # ACCEPTED. Before: the fixture executor committed a product for every task, so none could submit its inputs.
        self.plan_checker("ck", [GREET_CHECK, NOTES_CHECK], {"ck.t1": {"product": "greeting"}, "ck.t2": {"product": "notes"}, "ck.t3": {"check_only": True}})
        tasks = self.tasks(self.drain())
        self.assertEqual({identity: (task["result"], task["delivery"]) for identity, task in tasks.items()},
                         {f"ck.{task}": ("accepted", "LOCAL_ONLY") for task in ("t1", "t2", "t3")})
        checker = self.receipt("ck.t3")["acceptance"]
        self.assertEqual((checker["source_sha"], [command["passed"] for command in checker["commands"]],
                          [guard["passed"] for guard in checker["guards"] if guard["rule"] == "forbidden_patterns/0"]), (checker["inputs_sha"], [True, True], [True]))
        self.assertIn("- Whole-loop acceptance: ACCEPTED\n", self.report("ck"))

    def test_a_failed_substantive_task_blocks_only_the_check_only_task(self):
        # Prediction (rp-d3 policy 2): when t1 fails its check (fa) or stops as needs-review (rv), the independent t2 is still
        # accepted, the check-only t3 becomes blocked-prerequisite without executing, and whole-loop acceptance stays
        # INCOMPLETE. The runtime is unchanged; this guards the independent progress the policy relies on.
        question = "Should greet() accept an empty name?"
        self.plan_checker("fa", [GREET_CHECK, NOTES_CHECK], {"fa.t1": {"product": "bad-greeting"}, "fa.t2": {"product": "notes"}, "fa.t3": {"check_only": True}})
        self.plan_checker("rv", [GREET_CHECK, NOTES_CHECK], {"rv.t1": {"product": "greeting", "blockers": [{"kind": "needs-review", "detail": question}]},
                                                             "rv.t2": {"product": "notes"}, "rv.t3": {"check_only": True}})
        tasks = self.tasks(self.drain())
        self.assertEqual({identity: (task["result"], task.get("reason")) for identity, task in tasks.items()}, {
            "fa.t1": ("failed", "failed: command 0 (R1) exit 1, expected 0"), "fa.t2": ("accepted", None), "fa.t3": ("blocked", "blocked-prerequisite:fa.t1"),
            "rv.t1": ("failed", f"needs-review: {question}"), "rv.t2": ("accepted", None), "rv.t3": ("blocked", "blocked-prerequisite:rv.t1")})
        self.assertEqual((tasks["rv.t1"]["questions"], self.calls("fa.t3"), self.calls("rv.t3")), ([question], 0, 0))
        for loop in ("fa", "rv"):
            self.assertIn(f"- Whole-loop acceptance: INCOMPLETE — {loop}.t1 failed, {loop}.t3 blocked\n", self.report(loop))

    def test_a_check_only_task_fails_on_its_assembled_product_or_a_source_change(self):
        # Prediction (rp-d3 policy 2): with both substantive tasks accepted, the check-only task fails, and whole-loop
        # acceptance stays INCOMPLETE, when the assembled product fails its check (ca.t3: no app.py) and when its executor
        # commits a product edit, which its full-diff guard refuses (ce.t3). The runtime is unchanged; this guards that a
        # checker neither passes on a broken assembly nor changes product source.
        self.plan_checker("ca", [APP_CHECK], {"ca.t1": {"product": "greeting"}, "ca.t2": {"product": "notes"}, "ca.t3": {"check_only": True}})
        self.plan_checker("ce", [GREET_CHECK, NOTES_CHECK], {"ce.t1": {"product": "greeting"}, "ce.t2": {"product": "notes"}, "ce.t3": {"product": "todo"}})
        tasks = self.tasks(self.drain())
        self.assertEqual({identity: (task["result"], task.get("reason")) for identity, task in tasks.items()}, {
            "ca.t1": ("accepted", None), "ca.t2": ("accepted", None), "ca.t3": ("failed", "failed: command 0 (R1) exit 2, expected 0"),
            "ce.t1": ("accepted", None), "ce.t2": ("accepted", None), "ce.t3": ("failed", "failed: guard forbidden_patterns/0 No source changes")})
        for loop in ("ca", "ce"):
            self.assertIn(f"- Whole-loop acceptance: INCOMPLETE — {loop}.t3 failed\n", self.report(loop))

    def test_a_local_loop_runs_one_task_at_a_time(self):
        # Prediction (rp-d3 policy 2): rt.t1's executor exits without a submission, as on a usage limit, so rt.t1 stays active
        # and the independent rt.t2 waits for it with no executor call. Once rt.t1 is accepted, rt.t2 starts from its source
        # and the check-only rt.t3 from rt.t2's, so the loop is ACCEPTED, its `Bring into` names rt.t3's branch, and a loop
        # added between the drains is accepted too. Before: rt.t2 started from rt.t1's start, their accepted sources diverged,
        # and every later drain ended BLOCKED "prerequisite source ... is not in the accepted frontier", so nw.t1 never ran.
        self.plan_checker("rt", [GREET_CHECK, NOTES_CHECK], {"rt.t1": {"product": "greeting", "exit_now": 1}, "rt.t2": {"product": "notes"},
                                                             "rt.t3": {"check_only": True}})
        tasks = self.tasks(self.drain())
        self.assertEqual({identity: (task["result"], task.get("reason")) for identity, task in tasks.items() if identity != "rt.t1"}, {
            "rt.t2": ("pending", "waiting for rt.t1 (active), since a local loop runs one task at a time"),
            "rt.t3": ("pending", "waiting for rt.t1 (active)")})
        self.assertEqual((tasks["rt.t1"]["result"], self.calls("rt.t2")), ("active", 0))
        self.behaviors["rt.t1"] = {"product": "greeting"}
        self.plan("nw", [("t1", [], "Todo", [TODO_CHECK])], {"nw.t1": {"product": "todo"}})
        tasks = self.tasks(self.drain())
        self.assertEqual({identity: task["result"] for identity, task in tasks.items()},
                         {"rt.t1": "accepted", "rt.t2": "accepted", "rt.t3": "accepted", "nw.t1": "accepted"})
        t1, t2, t3 = (self.receipt(f"rt.{task}") for task in ("t1", "t2", "t3"))
        self.assertEqual((t2["baseline"], t3["baseline"], t3["source_sha"]), (t1["source_sha"], t2["source_sha"], t3["acceptance"]["inputs_sha"]))
        self.assertEqual([self.calls(f"rt.{task}") for task in ("t1", "t2", "t3")], [2, 1, 1])
        for line in ("- Whole-loop acceptance: ACCEPTED\n", f"- Bring into main: git merge --ff {t3['branch']}\n"):
            self.assertIn(line, self.report("rt"))

    @unittest.skipIf(os.name == "nt", "the failing allocation uses a POSIX shell hook")
    def test_the_frontier_is_the_accepted_source_containing_the_others(self):
        # Prediction (L, B): oo.t1's allocation fails on a post-checkout hook and the independent oo.t2 is accepted; once that
        # allocation is removed, oo.t1 starts from oo.t2's source, so the loop's one history runs out of row order. The frontier
        # is then oo.t1, whose source contains oo.t2's: the check-only oo.t3 starts from oo.t1's source, and while it is active
        # (its first executor exits without a submission) `Bring into` names oo.t1's branch; once oo.t3 is accepted the loop is
        # ACCEPTED. Before: the frontier was the last accepted row, oo.t2, so the drain after the removal and every later one
        # ended BLOCKED "oo.t3: prerequisite source ... is not in the accepted frontier ...; plan an integration task", and
        # `Bring into` named oo.t2's branch, which lacks oo.t1.
        self.plan_checker("oo", [GREET_CHECK, NOTES_CHECK], {"oo.t1": {"product": "greeting"}, "oo.t2": {"product": "notes"},
                                                             "oo.t3": {"check_only": True, "exit_now": 1}})
        hook = self.common / "hooks" / "post-checkout"
        hook.write_text("#!/bin/sh\ncase \"$PWD\" in */t1) echo 'post-checkout: setup failed' >&2; exit 1;; esac\n", encoding="utf-8")
        hook.chmod(0o755)
        self.assertIn("post-checkout: setup failed", " ".join(task.get("reason", "") for task in self.drain()["tasks"]))
        hook.unlink()
        self.assertEqual(self.tasks(self.drain())["oo.t2"]["result"], "accepted")
        path, receipt = self.receipt_path("oo.t1"), self.receipt("oo.t1")
        self.g("worktree", "remove", "--force", receipt["worktree"])
        self.g("branch", "-D", receipt["branch"])
        shutil.rmtree(path.parent)
        tasks = self.tasks(self.drain())
        self.assertEqual(({identity: task["result"] for identity, task in tasks.items()}, self.receipt("oo.t1")["baseline"]),
                         ({"oo.t1": "accepted", "oo.t2": "accepted", "oo.t3": "active"}, self.receipt("oo.t2")["source_sha"]))
        self.assertIn("- Bring into main: git merge --ff devlyn/oo/t1\n", self.report("oo"))
        self.behaviors["oo.t3"] = {"check_only": True}
        self.assertEqual((self.tasks(self.drain())["oo.t3"]["result"], self.receipt("oo.t3")["baseline"]),
                         ("accepted", self.receipt("oo.t1")["source_sha"]))
        self.assertIn("- Whole-loop acceptance: ACCEPTED\n", self.report("oo"))

    def assert_interrupted_custody_resumes(self, product, runner, verdict, published=False, crash_after=None):
        # A partially copied result must not bind custody or obstruct the next acceptance run.
        self.plan("inv", [CHAIN[0]], {"inv.t1": {"product": product, "runner": runner}})
        argv = self.drain_argv()
        crash = [CRASH, "replace", "manifest.json"] if published else [CRASH_CUSTODY]
        crashed = subprocess.run([sys.executable, "-c", *crash, *argv[1:]], cwd=self.root,
                                 env=self.env, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(crashed.returncode, 9, crashed.stdout + crashed.stderr)
        path = self.receipt_path("inv.t1")
        receipt = self.receipt("inv.t1")
        self.assertNotIn("acceptance", receipt)
        acceptance_file = Path(receipt["worktree"]) / ".devlyn/loop/acceptance.json"
        previous = acceptance_file.read_bytes()
        helper = self.queue["shared"]("task-complete")
        unbound = path.parent / "custody" if published else next(path.parent.glob(".custody-*"))
        copies = [helper["snapshot_files"](unbound, [".devlyn"])]
        if crash_after:
            crashed = subprocess.run([sys.executable, "-c", CRASH, *crash_after, *argv[1:]], cwd=self.root,
                                     env=self.env, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(crashed.returncode, 9, crashed.stdout + crashed.stderr)
            self.assertNotIn("acceptance", self.receipt("inv.t1"))
            self.assertNotEqual(acceptance_file.read_bytes(), previous)
            previous = acceptance_file.read_bytes()
            retained, = path.parent.glob(".custody-*")
            helper["verify_files"](retained, copies[0])
            if crash_after[0] == "rename-after":
                self.assertFalse((path.parent / "custody").exists())
                self.assertFalse(path.with_name("manifest.json").exists())
            else:
                copies.append(helper["snapshot_files"](path.parent / "custody", [".devlyn"]))
                self.assertEqual(json.loads(path.with_name("manifest.json").read_text(encoding="utf-8")), copies[-1])
        resumed = subprocess.run(argv, cwd=self.root, env=self.env, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(resumed.returncode, 0, resumed.stdout + resumed.stderr)
        self.assertEqual(resumed.stderr.count("devlyn-loop: inv.t1: bound\n"), 1)
        result = json.loads(resumed.stdout)
        self.assertEqual(self.tasks(result)["inv.t1"]["result"], verdict)
        self.assertNotEqual(acceptance_file.read_bytes(), previous)  # The checks really ran again.
        bound = self.receipt("inv.t1")
        helper["verify_files"](path.parent / "custody", bound["files"])
        self.assertEqual(json.loads(path.with_name("manifest.json").read_text(encoding="utf-8")), bound["files"])
        self.assertEqual(self.g("rev-parse", bound["recovery_ref"]), bound["publish_sha"])
        self.assertEqual(bound["delivery"], "FAILED" if verdict == "failed" else "LOCAL_ONLY")
        # A hard crash leaves its private staging directory behind; later runs never consume it.
        retained = list(path.parent.glob(".custody-*"))
        self.assertCountEqual([helper["snapshot_files"](root, [".devlyn"]) for root in retained], copies)
        self.assertEqual(self.tasks(self.drain())["inv.t1"]["result"], verdict)
        self.assertEqual(self.receipt("inv.t1"), bound)
        helper["verify_files"](Path(bound["worktree"]), bound["files"])
        self.assertEqual(self.calls("inv.t1"), 1)

    def test_interrupted_custody_resumes_failed_checks(self):
        self.assert_interrupted_custody_resumes("bad-greeting", True, "failed")

    def test_interrupted_custody_resumes_rerun_checks(self):
        self.assert_interrupted_custody_resumes("greeting", False, "accepted")

    def test_published_custody_resumes_failed_checks(self):
        self.assert_interrupted_custody_resumes("bad-greeting", True, "failed", published=True)

    def test_published_custody_resumes_rerun_checks(self):
        self.assert_interrupted_custody_resumes("greeting", False, "accepted", published=True)

    def test_unbound_custody_rename_crash_resumes(self):
        # Prediction: crashing just after custody is renamed aside leaves no acceptance binding or new custody;
        # fresh acceptance binds once, retains the earlier copy and finishes LOCAL_ONLY without rerunning the executor.
        self.assert_interrupted_custody_resumes("greeting", False, "accepted", published=True,
                                               crash_after=("rename-after", "custody"))

    def test_custody_manifest_written_crash_resumes(self):
        # Prediction: crashing after manifest.json is written leaves a complete but unbound copy; fresh acceptance
        # binds once, retains both earlier copies and finishes FAILED without rerunning the executor.
        self.assert_interrupted_custody_resumes("bad-greeting", True, "failed", published=True,
                                               crash_after=("replace-after", "manifest.json"))

    def test_published_unbound_custody_cannot_override_changed_inputs(self):
        # A legacy tracked package has no immutable capture: its anchor inputs must still be reconciled.
        self.plan("inv", [CHAIN[0]], {"inv.t1": {"product": "greeting"}})
        argv = self.drain_argv()
        crashed = subprocess.run([sys.executable, "-c", CRASH, "replace", "manifest.json", *argv[1:]],
                                 cwd=self.root, env=self.env, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(crashed.returncode, 9, crashed.stdout + crashed.stderr)
        path = self.receipt_path("inv.t1")
        self.assertNotIn("acceptance", self.receipt("inv.t1"))
        previous = (path.parent / "custody/.devlyn/loop/acceptance.json").read_bytes()
        self.assertEqual(json.loads(previous)["verdict"], "ACCEPTED")
        self.g("checkout", "refs/devlyn/captures/inv", "--", "docs/specs/inv")
        self.g("commit", "-qm", "tracked loop package")
        (self.common / "devlyn-loops/inv/added.json").unlink()
        contract = self.anchor / "docs/specs/inv/t1/spec.md"
        contract.write_text(contract.read_text(encoding="utf-8") + "\nChanged requirement.\n", encoding="utf-8")
        task = self.tasks(self.drain())["inv.t1"]
        self.assertEqual((task["result"], task["delivery"]), ("failed", "FAILED"))
        self.assertIn("inputs-changed:", task["reason"])
        bound = self.receipt("inv.t1")
        self.assertEqual(bound["acceptance"]["verdict"], "FAILED")
        self.assertEqual(self.rows(bound["publish_sha"])["inv.t1"]["mark"], "F")
        self.assertNotIn("pushed", bound)
        retained = list(path.parent.glob(".custody-*"))
        self.assertEqual(len(retained), 1)
        self.assertEqual((retained[0] / ".devlyn/loop/acceptance.json").read_bytes(), previous)
        self.assertEqual(self.calls("inv.t1"), 1)

    def test_legacy_partial_unbound_custody_resumes(self):
        self.plan("inv", [CHAIN[0]], {"inv.t1": {"product": "greeting", "runner": False}})
        argv = self.drain_argv()
        crashed = subprocess.run([sys.executable, "-c", CRASH_CUSTODY, *argv[1:]], cwd=self.root,
                                 env=self.env, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(crashed.returncode, 9, crashed.stdout + crashed.stderr)
        path = self.receipt_path("inv.t1")
        self.assertNotIn("acceptance", self.receipt("inv.t1"))
        # 4.2.3 copied directly into custody, including a truncated second file.
        staging, = path.parent.glob(".custody-*")
        staging.rename(path.parent / "custody")
        (path.parent / "custody/.devlyn/loop/acceptance.json").write_bytes(b"{")
        helper = self.queue["shared"]("task-complete")
        partial = helper["snapshot_files"](path.parent / "custody", [".devlyn"])
        task = self.tasks(self.drain())["inv.t1"]
        self.assertEqual((task["result"], task["delivery"]), ("accepted", "LOCAL_ONLY"))
        retained, = path.parent.glob(".custody-*")
        helper["verify_files"](retained, partial)
        helper["verify_files"](path.parent / "custody", self.receipt("inv.t1")["files"])
        self.assertEqual(self.tasks(self.drain())["inv.t1"]["result"], "accepted")
        self.assertEqual(self.calls("inv.t1"), 1)

    def test_interruption_after_acceptance_writes_only_the_missing_transition(self):
        self.plan("inv", CHAIN, {"inv.t1": {"product": "greeting", "hold": True}, "inv.t2": {"product": "app"}})
        driver = self.drain_until("inv.t1: bound")
        next(driver).kill()
        bound = self.receipt("inv.t1")
        self.assertTrue(bound["acceptance"] and "queue" not in bound)
        self.assertEqual(self.g("rev-parse", "refs/heads/devlyn/inv/t1"), bound["source_sha"])
        self.release_executor_holder()
        # Until the terminal commit is attached the resume is another drain, never task-complete delivery.
        resume = {t["identity"]: t["resume"] for t in self.cli("status", "--repo", self.anchor)["delivery"]}["inv.t1"]
        self.assertNotIn("task-complete", resume)
        self.assertIn("drain again", resume)
        result = self.drain()
        self.assertEqual({identity: task["result"] for identity, task in self.tasks(result).items()}, {"inv.t1": "accepted", "inv.t2": "accepted"})
        self.assertEqual((self.calls("inv.t1"), self.calls("inv.t2")), (1, 1))
        settled = self.receipt("inv.t1")
        self.assertEqual((settled["source_sha"], settled["acceptance_digest"]), (bound["source_sha"], bound["acceptance_digest"]))
        self.assertEqual(self.rows(settled["publish_sha"])["inv.t1"]["mark"], "x")

    def kill_before_attachment(self):
        """Kill the driver after inv.t1's terminal commit, while attachment waits for the receipt lock."""
        self.plan("inv", CHAIN, {"inv.t1": {"product": "greeting", "hold": True}, "inv.t2": {"product": "app"}})
        driver = self.drain_until("inv.t1: bound", "inv.t1: terminal")
        next(driver)
        receipt_lock = self.hold(self.receipt_path("inv.t1").with_name("lock"))
        self.release_executor_holder()
        next(driver).kill()
        receipt_lock.kill()
        receipt_lock.wait()
        partial = self.receipt("inv.t1")
        terminal = self.g("rev-parse", "refs/heads/devlyn/inv/t1")
        self.assertNotEqual(terminal, partial["source_sha"])
        self.assertNotIn("queue", partial)
        self.assertEqual(self.g("rev-parse", partial["recovery_ref"]), partial["source_sha"])
        return partial, terminal

    def assert_attached_once(self, result, terminal):
        self.assertEqual(self.tasks(result)["inv.t1"]["result"], "accepted")
        settled = self.receipt("inv.t1")
        self.assertEqual((settled["queue"]["commit"], settled["delivery"], self.calls("inv.t1")), (terminal, "LOCAL_ONLY", 1))
        self.assertEqual(self.g("rev-parse", settled["recovery_ref"]), terminal)

    def test_interruption_after_terminal_commit_attaches_and_delivers_only(self):
        _, terminal = self.kill_before_attachment()
        self.assert_attached_once(self.drain(), terminal)

    def test_interrupted_attachment_is_completed_on_resume(self):
        partial, terminal = self.kill_before_attachment()
        # Attachment's first write moves the recovery ref; a crash before its receipt save leaves this state.
        self.g("update-ref", partial["recovery_ref"], terminal, partial["source_sha"])
        resume = {t["identity"]: t["resume"] for t in self.cli("status", "--repo", self.anchor)["delivery"]}["inv.t1"]
        self.assertIn("drain again", resume)
        self.assert_attached_once(self.drain(), terminal)

    def test_failures_never_reach_accepted(self):
        self.g("remote", "add", "origin", "https://gitlab.com/team/project.git")  # Local loops need no GitHub remote.
        greeting, notes = CHAIN[0], ("t2", [], "Notes", [NOTES_CHECK])
        self.plan("aa", CHAIN, {"aa.t1": {"product": "bad-greeting", "runner": False, "review": False}, "aa.t2": {"product": "app"}})
        self.plan("bb", CHAIN, {"bb.t1": {"product": "greeting", "change_after_review": True}, "bb.t2": {"product": "app"}})
        self.plan("cc", CHAIN, {"cc.t1": {"product": "greeting", "review": False}, "cc.t2": {"product": "app"}})
        self.plan("dd", [greeting, notes, ("t3", ["t1", "t2"], "Greeting app", [APP_CHECK])],
                  {"dd.t1": {"product": "bad-greeting"}, "dd.t2": {"product": "notes"}, "dd.t3": {"product": "app"}})
        self.plan("ee", CHAIN, {"ee.t1": {"product": "greeting"}, "ee.t2": {"product": "bad-app"}})
        self.plan("ff", CHAIN, {"ff.t1": {"product": "greeting", "malformed_review": True}, "ff.t2": {"product": "app"}})
        result = self.drain()
        tasks = self.tasks(result)
        self.assertEqual({identity: task["result"] for identity, task in tasks.items()}, {
            "aa.t1": "failed", "aa.t2": "blocked", "bb.t1": "failed", "bb.t2": "blocked", "cc.t1": "failed", "cc.t2": "blocked",
            "dd.t1": "failed", "dd.t2": "accepted", "dd.t3": "blocked", "ee.t1": "accepted", "ee.t2": "failed",
            "ff.t1": "failed", "ff.t2": "blocked"})
        self.assertEqual([self.calls(identity) for identity in ("aa.t2", "bb.t2", "cc.t2", "dd.t3", "ff.t2")], [0, 0, 0, 0, 0])
        # A malformed executor record fails its task with a named reason; it never crashes the driver.
        self.assertIn("malformed review record", tasks["ff.t1"]["reason"])
        self.assertIn("failed: command 0 (R1) exit 1", tasks["aa.t1"]["reason"])
        self.assertEqual(tasks["aa.t2"]["reason"], "blocked-prerequisite:aa.t1")
        for identity in ("bb.t1", "cc.t1"):
            self.assertIn("required review coverage missing for R2", tasks[identity]["reason"])
        stale = self.receipt("bb.t1")["acceptance"]
        self.assertNotIn("reused_from", stale["commands"][0])
        self.assertIn("is bound to source", stale["ignored_reviews"][0]["reason"])
        for identity in ("aa.t1", "bb.t1", "cc.t1", "dd.t1", "ee.t2"):
            receipt = self.receipt(identity)
            row = self.rows(receipt["publish_sha"])[identity]
            self.assertEqual((receipt["product"], receipt["delivery"], row["mark"]), ("FAILED", "FAILED", "F"))
            self.assertIn(f"(receipt {receipt['id']})", row["rest"])
            self.assertEqual(self.g("rev-parse", receipt["recovery_ref"]), receipt["publish_sha"])
        # Receipt-proven failed and prerequisite-blocked marks enter the next checkout of the same loop,
        # in queue order, with unrelated rows byte-identical.
        failed, dd2 = self.receipt("dd.t1"), self.receipt("dd.t2")
        failed_row = self.rows(failed["publish_sha"])["dd.t1"]["line"]
        blocked_row = "- [F] " + self.queue["row_line"]("dd.t3", "Greeting app")[6:] + f" — blocked-prerequisite:dd.t1 (receipt {failed['id']})"
        self.assertEqual(self.queue_at(dd2["acceptance"]["inputs_sha"], "dd"), self.queue_at("refs/devlyn/captures/dd", "dd").replace(
            self.queue["row_line"]("dd.t1", "Greeting interface 인사"), failed_row).replace(self.queue["row_line"]("dd.t3", "Greeting app"), blocked_row))
        self.assertIn("Whole-loop acceptance: INCOMPLETE — ee.t2 failed", self.report("ee"))
        self.assertIn("blocked-prerequisite:dd.t1", self.report("dd"))

    def test_a_detached_submission_fails_settles_and_the_drain_continues(self):
        self.plan("a", [CHAIN[0]], {"a.t1": {"product": "greeting", "detach": True}})
        self.plan("b", [("t1", [], "Notes", [NOTES_CHECK])], {"b.t1": {"product": "notes"}})
        tasks = self.tasks(self.drain())
        self.assertEqual({identity: task["result"] for identity, task in tasks.items()}, {"a.t1": "failed", "b.t1": "accepted"})
        self.assertIn("HEAD detached", tasks["a.t1"]["reason"])
        receipt = self.receipt("a.t1")
        self.assertEqual((receipt["delivery"], receipt["queue"]["commit"], self.calls("a.t1")), ("FAILED", receipt["publish_sha"], 1))
        self.assertEqual(self.rows(receipt["publish_sha"])["a.t1"]["mark"], "F")

    def test_an_executor_that_exits_without_a_submission_leaves_its_task_waiting(self):
        # Prediction (H2): an executor that exits 1 without a submission, as on a usage limit, leaves aa.t1 active, waiting
        # with "executor exited 1 without a submission (see <evidence_dir>/executor.stderr); the next drain runs it again",
        # with no terminal commit and its dependent pending, while the independent loop bb is accepted; once the executor
        # works, the next drain runs aa.t1 again and accepts the loop. Before: the drain wrote a stand-in submission, so aa.t1
        # became [F] blocked-infrastructure, aa.t2 blocked-prerequisite, and no drain ran either again.
        self.plan("aa", CHAIN, {"aa.t1": {"product": "greeting", "exit_now": 1}, "aa.t2": {"product": "app"}})
        self.plan("bb", [("t1", [], "Notes", [NOTES_CHECK])], {"bb.t1": {"product": "notes"}})
        tasks = self.tasks(self.drain())
        stderr = Path(self.receipt("aa.t1")["worktree"]) / ".devlyn/loop/executor.stderr"
        self.assertEqual({identity: (task["result"], task.get("reason")) for identity, task in tasks.items()}, {
            "aa.t1": ("active", f"executor exited 1 without a submission (see {stderr}); the next drain runs it again"),
            "aa.t2": ("pending", "waiting for aa.t1 (active)"), "bb.t1": ("accepted", None)})
        self.assertEqual((tasks["aa.t1"].get("terminal"), "429 usage limit" in stderr.read_text(encoding="utf-8")), (None, True))
        self.behaviors["aa.t1"] = {"product": "greeting"}
        tasks = self.tasks(self.drain())
        self.assertEqual({identity: task["result"] for identity, task in tasks.items()}, {"aa.t1": "accepted", "aa.t2": "accepted", "bb.t1": "accepted"})
        self.assertEqual((self.calls("aa.t1"), self.calls("aa.t2"), self.calls("bb.t1")), (2, 1, 1))

    def test_unobservable_interrupted_execution_fails_only_that_task(self):
        self.plan("a", CHAIN, {"a.t1": {"product": "greeting", "hang": True}, "a.t2": {"product": "app"}})
        self.plan("b", [("t1", [], "Notes", [NOTES_CHECK])], {"b.t1": {"product": "notes"}})
        driver = next(self.drain_until("a.t1: executing"))
        while not self.config.with_name("hang.pid").exists():
            time.sleep(0.05)
        driver.kill()
        driver.wait()
        self.kill_hung_executor()
        tasks = self.tasks(self.drain(unobservable=True))
        self.assertEqual({identity: task["result"] for identity, task in tasks.items()}, {"a.t1": "failed", "a.t2": "blocked", "b.t1": "accepted"})
        self.assertTrue(tasks["a.t1"]["reason"].startswith("interrupted-unobservable: "))
        self.assertEqual((self.calls("a.t1"), self.calls("a.t2"), self.calls("b.t1")), (1, 0, 1))
        receipt = self.receipt("a.t1")
        self.assertTrue(Path(receipt["worktree"]).is_dir())
        self.assertIn("— interrupted-unobservable: ", self.rows(receipt["publish_sha"])["a.t1"]["rest"])

    @unittest.skipIf(os.name == "nt", "writer observation requires POSIX")
    def test_interrupted_execution_waits_for_the_live_executor_and_adopts_its_submission(self):
        self.plan("a", [CHAIN[0]], {"a.t1": {"product": "greeting", "hang": True}})
        driver = next(self.drain_until("a.t1: executing"))
        while not self.config.with_name("hang.pid").exists():
            time.sleep(0.05)
        driver.kill()  # The controller dies after the spawn; its executor lives on.
        driver.wait()
        self.independent()
        resumed = self.drain()
        self.assert_independent(resumed)
        self.assertIn("interrupted execution still active", self.tasks(resumed)["a.t1"]["reason"])
        self.assertEqual(self.calls("a.t1"), 1)
        self.config.with_name("release").write_text("go", encoding="utf-8")
        deadline = time.monotonic() + 60
        while not self.receipt_path("a.t1").with_name("submission.json").exists():
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.05)
        # The submission precedes process exit; retry writer observation without ever starting another executor.
        while True:
            result = self.drain()
            if self.tasks(result)["a.t1"]["result"] == "accepted":
                break
            self.assertLess(time.monotonic(), deadline)
        self.assertEqual((self.calls("a.t1"), self.calls("bb.t1")), (1, 1))

    def test_captured_contracts_stay_immutable(self):
        # Prediction (C, read captured bytes): with a.t1 left active with committed inputs and a packet, edited copies of the
        # loop's package in the checkout and a deleted one change nothing: status names no inputs change, the drain runs a.t1
        # and a.t2 from the capture to acceptance with their packets binding the captured bytes, and it reports the edited
        # copies as kept. Before: an edited or deleted checkout copy failed the active task as inputs-changed and blocked
        # its dependent.
        self.plan("a", CHAIN, {"a.t1": {"product": "greeting"}, "a.t2": {"product": "app"}})
        blocked = self.cli("drain", "--repo", self.anchor, "--local-only", "--", str(self.root / "no executor"), "{packet}")
        self.assertIn("executor could not start", " ".join(task.get("reason", "") for task in blocked["tasks"]))
        self.queue["write_package"](self.anchor, "a", [(CHAIN[0][0], [], "Changed title", [NOTES_CHECK]), CHAIN[1]], base=self.base)
        (self.anchor / "docs/specs/a/t2/spec.expected.json").unlink()
        self.assertNotIn("inputs-changed", " ".join(self.cli("status", "--repo", self.anchor)["blockers"]))
        result = self.drain()
        self.assertEqual({identity: task["result"] for identity, task in self.tasks(result).items()}, {"a.t1": "accepted", "a.t2": "accepted"})
        self.assertEqual((self.calls("a.t1"), self.calls("a.t2")), (1, 1))
        packet = json.loads(self.receipt_path("a.t1").with_name("packet.json").read_text(encoding="utf-8"))
        captured = subprocess.run(["git", "-C", str(self.anchor), "cat-file", "blob", "refs/devlyn/captures/a:docs/specs/a/t1/spec.md"],
                                  env=self.env, capture_output=True, check=True).stdout
        self.assertEqual(packet["contract"]["sha256"], hashlib.sha256(captured).hexdigest())
        self.assertIn(f"{self.anchor / 'docs/specs/a/t1/spec.md'}: kept, it differs from the captured package refs/devlyn/captures/a", result["cleanup"])

    def test_unignored_start_is_accepted_in_one_drain(self):
        # Prediction: an unignored start and an independent loop both complete in one drain without changing the
        # anchor's .gitignore or info/exclude, or adding .gitignore/.devlyn changes to either accepted source.
        self.g("branch", "ignored-base")
        (self.anchor / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
        self.g("commit", "-qam", "base without the .devlyn/ rule")
        self.plan("ig", [("t1", [], "Notes", [NOTES_CHECK])], {"ig.t1": {"product": "notes"}}, base=self.g("rev-parse", "HEAD"))
        self.g("checkout", "-q", "ignored-base")
        self.independent()
        ignore, exclude = self.anchor / ".gitignore", self.common / "info/exclude"
        before = (ignore.read_bytes(), exclude.read_bytes())
        result = self.drain()
        self.assert_independent(result)
        for identity in ("ig.t1", "bb.t1"):
            self.assertEqual(self.tasks(result)[identity]["result"], "accepted")
            receipt = self.receipt(identity)
            self.assertEqual(self.g("diff", "--name-only", receipt["baseline"], receipt["source_sha"], "--", ".gitignore", ".devlyn"), "")
        self.assertEqual((ignore.read_bytes(), exclude.read_bytes()), before)
        self.assertEqual((self.calls("ig.t1"), self.calls("bb.t1")), (1, 1))

    @unittest.skipIf(os.name == "nt", "the failing allocation uses a POSIX shell hook")
    def test_an_unfinished_allocation_waits_naming_its_recovery(self):
        # Prediction (H3): a post-checkout hook that fails while hk.t1's worktree is added leaves its receipt short of
        # `allocation: owned`, and that drain returns WAITING with the hook's error while lo completes. Once the hook is gone, the next drain never
        # adopts hk.t1: it waits, naming the recovery (remove its worktree and branch if present, delete the receipt
        # directory, drain again), status lists that wait without repeating the identity, and the local loop lo is accepted;
        # after that recovery, the next drain accepts hk.t1. Before: every later status and drain ended BLOCKED "allocation
        # was interrupted (...); uncertain ownership blocks adoption, inspect it", naming no recovery, and lo never ran.
        self.plan("hk", [CHAIN[0]], {"hk.t1": {"product": "greeting"}})
        self.plan("lo", [("t1", [], "Notes", [NOTES_CHECK])], {"lo.t1": {"product": "notes"}})
        hook = self.common / "hooks" / "post-checkout"
        hook.write_text("#!/bin/sh\ncase \"$PWD\" in */hk/t1) echo 'post-checkout: setup failed' >&2; exit 1;; esac\n", encoding="utf-8")
        hook.chmod(0o755)
        self.assertIn("post-checkout: setup failed", " ".join(task.get("reason", "") for task in self.drain()["tasks"]))
        self.assertEqual((self.calls("hk.t1"), self.calls("lo.t1")), (0, 1))
        hook.unlink()
        path, receipt = self.receipt_path("hk.t1"), self.receipt("hk.t1")
        reason = (f"allocation did not finish ({path}); remove its worktree {receipt['worktree']} and branch {receipt['branch']} if present, "
                  f"delete {path.parent}, then drain again")
        tasks = self.tasks(self.drain())
        self.assertEqual({identity: (task["result"], task.get("reason")) for identity, task in tasks.items()},
                         {"hk.t1": ("pending", reason), "lo.t1": ("accepted", None)})
        self.assertIn(f"hk.t1: {reason}", self.cli("status", "--repo", self.anchor)["blockers"])
        self.g("worktree", "remove", "--force", receipt["worktree"])
        self.g("branch", "-D", receipt["branch"])
        shutil.rmtree(path.parent)
        self.assertEqual((self.tasks(self.drain())["hk.t1"]["result"], self.calls("hk.t1")), ("accepted", 1))

    def remote(self, **server):
        """GitHub stand-in: task-complete's fake gh and transport wrappers over a local bare repository."""
        helper = runpy.run_path(str(self.helper))
        bare = self.root / "remote.git"
        self.run_ok(["git", "init", "-q", "--bare", "--initial-branch=main", str(bare)])
        self.run_ok(["git", "-C", str(self.anchor), "push", "-q", str(bare), "main"])
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        for name, body in (("gh", helper["FAKE_GH"]), ("git.py", helper["GIT_WRAPPER"]), ("git", helper["GIT_DISPATCH"])):
            (bin_dir / name).write_text(body, encoding="utf-8")
            (bin_dir / name).chmod(0o755)
        data = self.root / "gh.json"
        data.write_text(json.dumps({"bare": str(bare), **server}), encoding="utf-8")
        self.env.update(PATH=str(bin_dir) + os.pathsep + self.env["PATH"], FIXTURE_GH=str(data), REAL_GIT=shutil.which("git"))
        self.g("remote", "add", "origin", "https://github.com/test/project.git")
        return bare, data

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_an_auto_task_is_refused_until_the_instructions_are_pushed(self):
        # Prediction (E3): with AGENTS.md committed but not pushed, an auto loop's add passes, but its task is refused at
        # allocation, naming AGENTS.md, the refreshed base and the push remedy, with no receipt; after the push the drain
        # delivers it and its packet lists AGENTS.md. Before: the task ran from the refreshed base without AGENTS.md.
        # Prediction: the refused task, queued ahead of a local loop, waits with that reason while the local loop is
        # accepted in the same drain. Before: allocation raised, so the drain ended BLOCKED and the local loop never ran.
        bare, _ = self.remote(pending=False)
        (self.anchor / "AGENTS.md").write_text("# Installed instructions\n", encoding="utf-8")
        self.g("add", "AGENTS.md")
        self.g("commit", "-qm", "install instructions")
        installed = self.g("rev-parse", "HEAD")
        meta = self.queue["write_package"](self.anchor, "ai", [CHAIN[0]], delivery="auto", base=self.base,
                                           intent="User asked: unrelated legacy intent.")
        self.behaviors.update({"ai.t1": {"product": "greeting"}})
        self.cli("add", meta, "--materialize", 4)
        self.plan("lo", [("t1", [], "Notes", [NOTES_CHECK])], {"lo.t1": {"product": "notes"}})
        tasks = self.tasks(self.drain(local=False))
        self.assertEqual([(identity, task["result"], task.get("reason")) for identity, task in tasks.items()], [
            ("ai.t1", "pending", f"the installed instructions (AGENTS.md) in this checkout differ from those in its start commit {self.base}, "
                                 "so it would run without them; commit them and push them to origin/main"), ("lo.t1", "accepted", None)])
        self.assertFalse(self.receipt_path("ai.t1").exists())
        self.run_ok(["git", "-C", str(self.anchor), "push", "-q", str(bare), f"{installed}:main"])
        self.assertEqual((self.tasks(self.drain(local=False))["ai.t1"]["delivery"], self.methodology("ai.t1")), ("COMPLETE", ["AGENTS.md"]))

    def test_a_local_task_whose_start_lacks_the_checkouts_instructions_waits_while_other_loops_run(self):
        # Prediction (E3, L): a CLAUDE.md v2 committed after add but before the loop's first allocation is used: aa.t1 starts
        # from the branch HEAD holding it. Once that allocation fixed the start, a v3 commit makes the dependent aa.t2 wait,
        # naming the file, its start commit and both remedies, with no executor call, while a loop added under v3 is
        # accepted in the same drain; status names that wait and offers no next task; with v2 restored aa.t2 is accepted.
        # Before: the start was add's commit under v1, so the v2 commit made before the first allocation stranded the loop.
        (self.anchor / "CLAUDE.md").write_bytes(b"# Installed v1\n")
        self.g("add", "CLAUDE.md")
        self.g("commit", "-qm", "install v1")
        self.plan("aa", [("t1", [], "Notes", [NOTES_CHECK]), ("t2", ["t1"], "Todo", [TODO_CHECK])], {"aa.t1": {"product": "notes"}, "aa.t2": {"product": "todo"}})
        (self.anchor / "CLAUDE.md").write_bytes(b"# Installed v2\n")
        self.g("commit", "-qam", "install v2")
        # aa.t1 is allocated, then its executor cannot start: the loop's start is now fixed.
        blocked = self.cli("drain", "--repo", self.anchor, "--local-only", "--", str(self.root / "no executor"), "{packet}")
        self.assertIn("executor could not start", " ".join(task.get("reason", "") for task in blocked["tasks"]))
        (self.anchor / "CLAUDE.md").write_bytes(b"# Installed v3\n")
        self.g("commit", "-qam", "install v3")
        self.plan("bb", [("t1", [], "Greeting", [GREET_CHECK])], {"bb.t1": {"product": "greeting"}})
        tasks = self.tasks(self.drain())
        start = self.receipt("aa.t1")["source_sha"]
        reason = (f"the installed instructions (CLAUDE.md) in this checkout differ from those in its start commit {start}, so it would run "
                  "without them; restore them to their bytes at that commit, or plan the remaining work as a new loop")
        self.assertEqual((tasks["aa.t1"]["result"], tasks["aa.t2"].get("reason"), self.calls("aa.t2"), tasks["bb.t1"]["result"]), ("accepted", reason, 0, "accepted"))
        methodology = json.loads(self.receipt_path("aa.t1").with_name("packet.json").read_text(encoding="utf-8"))["methodology"]["projectInstructions"]
        self.assertEqual([entry["sha256"] for entry in methodology], [hashlib.sha256(b"# Installed v2\n").hexdigest()])
        status = self.cli("status", "--repo", self.anchor)
        self.assertEqual((status["next"], f"aa.t2: {reason}" in status["blockers"]), (None, True))
        (self.anchor / "CLAUDE.md").write_bytes(b"# Installed v2\n")
        self.assertEqual(self.tasks(self.drain())["aa.t2"]["result"], "accepted")

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_unobservable_post_merge_cleanup_retains_the_workspace_and_drain_continues(self):
        self.remote(pending=False)
        self.plan("inv", [CHAIN[0]], {"inv.t1": {"product": "greeting"}}, delivery="auto")
        self.plan("loc", [("t1", [], "Notes", [NOTES_CHECK])], {"loc.t1": {"product": "notes"}})
        tasks = self.tasks(self.drain(local=False, unobservable=True))
        self.assertEqual((tasks["inv.t1"]["result"], tasks["inv.t1"]["delivery"], tasks["loc.t1"]["result"]), ("accepted", "COMPLETE", "accepted"))
        # The next drain reruns nothing.
        self.assertEqual({identity: task["result"] for identity, task in self.tasks(self.drain(local=False, unobservable=True)).items()},
                         {"inv.t1": "accepted", "loc.t1": "accepted"})
        self.assertEqual((self.calls("inv.t1"), self.calls("loc.t1")), (1, 1))
        receipt = self.receipt("inv.t1")
        # Retained, never reported as cleaned: the worktree, task ref and receipt stay, and the report says why.
        self.assertTrue(receipt["merge"] and Path(receipt["worktree"]).is_dir())
        self.assertNotIn("status", receipt)
        self.assertEqual(self.g("rev-parse", "refs/heads/devlyn/inv/t1"), receipt["publish_sha"])
        report = (self.common / "devlyn-loops/inv/drain-report.md").read_text(encoding="utf-8")
        self.assertIn("- Workspace cleanup: RETAINED — writer observation unsupported on this platform; retain workspace", report)

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_prerequisite_merge_is_checked_before_allocation_and_execution(self):
        # Prediction (3): both merge checks wait while unrelated work completes; an allocated baseline is never replaced.
        bare, data = self.remote(pending=True)
        self.plan("inv", CHAIN, {"inv.t1": {"product": "greeting"}, "inv.t2": {"product": "app"}}, delivery="auto")
        self.drain(local=False)
        held = self.anchor / "AGENTS.md"  # An uncommitted instruction file holds inv.t2 back while inv.t1 delivers.
        held.write_text("# Installed instructions\n", encoding="utf-8")
        self.assertEqual(self.merge_pr(data, 1).returncode, 0)
        self.assertEqual(self.tasks(self.drain(local=False))["inv.t1"]["delivery"], "COMPLETE")
        self.assertFalse(self.receipt_path("inv.t2").exists())
        merge = self.receipt("inv.t1")["merge"]["mergeCommit"]["oid"]
        self.run_ok(["git", "--git-dir", str(bare), "update-ref", "refs/heads/main", self.base])  # The base loses that merge.
        held.unlink()
        self.independent()
        for _ in range(2):
            result = self.drain(local=False)
            self.assert_independent(result)
            self.assertIn(f"lacks prerequisite inv.t1's delivered merge {merge}", self.tasks(result)["inv.t2"]["reason"])
            self.assertFalse(self.receipt_path("inv.t2").exists())
        # A receipt allocated on that base by another route is checked again before execution.
        self.run_ok([sys.executable, str(self.helper), "allocate", "--repo", str(self.anchor), "--task", "inv.t2", "--branch", "devlyn/inv/t2",
                     "--repository", "test/project", "--base", "main", "--worktree", str(self.root / "repo.devlyn/inv/t2")])
        self.independent("cc")
        allocated = self.receipt_path("inv.t2").read_bytes()
        result = self.drain(local=False)
        self.assert_independent(result, "cc")
        reason = self.tasks(result)["inv.t2"]["reason"]
        self.assertIn(f"lacks prerequisite inv.t1's delivered merge {merge}", reason)
        self.assertIn("allocated baseline", reason)
        self.assertIn("new loop", reason)
        self.run_ok(["git", "--git-dir", str(bare), "update-ref", "refs/heads/main", merge])
        self.assertIn("allocated baseline", self.tasks(self.drain(local=False))["inv.t2"]["reason"])
        self.assertEqual(self.receipt_path("inv.t2").read_bytes(), allocated)
        self.assertEqual(self.calls("inv.t2"), 0)

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_whole_loop_acceptance_waits_for_every_manifest_task(self):
        bare, data = self.remote(pending=True)
        self.plan("inv", CHAIN, {"inv.t1": {"product": "greeting"}, "inv.t2": {"product": "app"}}, delivery="auto")
        self.assertEqual(self.tasks(self.drain(local=False))["inv.t1"]["delivery"], "PENDING")
        self.assertIn("- Whole-loop acceptance: INCOMPLETE — inv.t2 pending", self.report("inv"))
        self.assertEqual(self.merge_pr(data, 1).returncode, 0)
        # T2, the integration task, runs once T1 is delivered.
        self.assertEqual(self.tasks(self.drain(local=False))["inv.t2"]["result"], "accepted")
        self.assertIn("- Whole-loop acceptance: ACCEPTED", self.report("inv"))

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_a_settled_loop_keeps_its_decisions_after_its_workspaces_are_cleaned(self):
        # Prediction (6): confirmed removals also prune the empty loop parent, preserving the root and durable receipts;
        # a later drain finishes interrupted parent pruning without invoking either executor again.
        # Prediction (rp-d3 policy 1): once both tasks of an auto loop are delivered, their worktrees are cleaned, and a
        # further drain, which loads no package for the settled loop, rewrites the report with the captured decision once.
        # Before: no report carried the package decisions.
        self.remote(pending=False)
        meta = self.queue["write_package"](self.anchor, "sd", CHAIN, delivery="auto", base=self.base)
        decision = "- D1: Greetings stay in English, the project convention."
        meta.write_text(meta.read_text(encoding="utf-8").replace("None beyond the task contracts.", decision), encoding="utf-8")
        self.behaviors.update({"sd.t1": {"product": "greeting"}, "sd.t2": {"product": "app"}})
        self.cli("add", meta)
        tasks = self.tasks(self.drain(local=False))
        self.assertEqual({identity: task["delivery"] for identity, task in tasks.items()}, {"sd.t1": "COMPLETE", "sd.t2": "COMPLETE"})
        self.assertEqual([Path(self.receipt(identity)["worktree"]).exists() for identity in tasks], [False, False])
        parent = self.root / ".devlyn-worktrees/repo/sd"
        self.assertFalse(parent.exists())
        self.assertFalse(parent.parent.exists())
        self.assertTrue(parent.parent.parent.is_dir())
        parent.mkdir(parents=True)  # Model interruption between worktree removal and empty-parent pruning.
        report = self.common / "devlyn-loops/sd/drain-report.md"
        report.unlink()
        self.drain(local=False)
        self.assertFalse(parent.exists())
        self.assertEqual((self.calls("sd.t1"), self.calls("sd.t2")), (1, 1))
        self.assertEqual(report.read_text(encoding="utf-8").count(decision), 1)

    def remote_rows(self, bare):
        return {identity: row["mark"] for identity, row in self.rows("main", git_dir=bare).items()}

    def merge_pr(self, data, number):
        """GitHub completing PR `number`'s pending auto-merge: the fake merges it into the remote main."""
        server = json.loads(data.read_text(encoding="utf-8"))
        data.write_text(json.dumps(dict(server, pending=False)), encoding="utf-8")
        try:
            return subprocess.run(["gh", "pr", "merge", str(number), "--auto", "--merge", "--match-head-commit",
                                   server["prs"][number - 1]["headRefOid"], "--repo", "github.com/test/project"],
                                  env=self.env, capture_output=True, text=True, encoding="utf-8")
        finally:
            data.write_text(json.dumps(dict(json.loads(data.read_text(encoding="utf-8")), pending=server.get("pending", False))), encoding="utf-8")

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_auto_delivery_fast_forwards_the_anchor_and_a_materialized_row_stays_replaced(self):
        # Prediction (Q, A): add commits nothing; the first task's PR carries the captured package and the loop's queue file,
        # which records the replaced legacy row's text and occurrence; the dependent starts from the merged package with no
        # inputs commit; the report's `Bring into` command fast-forwards the anchor with a clean tree; the legacy queue stays
        # as it was, CRLF line endings and the duplicate row above the replaced one included. Before the drain, before that
        # command, after it and in a fresh clone of the remote, status shows the duplicate pending and the loop's rows in the
        # replaced row's place, and materializing that line again is refused, so the intent never runs twice. Before: the plan
        # rewrote the legacy queue, and once the drain had synced the anchor its record stopped replacing the row until the pull.
        bare, data = self.remote(pending=False)
        legacy = b"# Intent Queue\r\n\r\n- [ ] unrelated legacy intent\r\n- [x] earlier legacy work\r\n- [ ] unrelated legacy intent\r\n"
        (self.anchor / "docs/specs/queue.md").write_bytes(legacy)
        self.g("commit", "-qam", "a legacy queue with CRLF line endings and a duplicate row")
        self.run_ok(["git", "-C", str(self.anchor), "push", "-q", str(bare), "main"])
        base = self.g("rev-parse", "HEAD")
        meta = self.queue["write_package"](self.anchor, "inv", CHAIN, delivery="auto", base=base, intent="User asked: unrelated legacy intent.")
        self.behaviors.update({"inv.t1": {"product": "greeting"}, "inv.t2": {"product": "app"}})
        self.cli("add", meta, "--materialize", 5)
        self.assertEqual((self.g("rev-parse", "HEAD"), self.g("status", "--porcelain", "--untracked-files=all")), (base, ""))

        def replaced(repo):
            status = self.cli("status", "--repo", repo)
            again = self.queue["write_package"](repo, "re", [CHAIN[0]], delivery="auto", base=base, intent="User asked: unrelated legacy intent.")
            refused = self.cli("add", again, "--materialize", 5, code=1)["reason"]
            shutil.rmtree(repo / "docs/specs/re")
            return [line for line in status["blockers"] if line.startswith("legacy")], status["counts"]["legacy_pending"], refused
        expected = (["legacy row 3 needs planning: unrelated legacy intent"], 1, "docs/specs/queue.md line 5 is not a pending legacy row")
        self.assertEqual(replaced(self.anchor), expected)
        tasks = self.tasks(self.drain(local=False))
        self.assertEqual({identity: task["delivery"] for identity, task in tasks.items()}, {"inv.t1": "COMPLETE", "inv.t2": "COMPLETE"})
        self.assertEqual(replaced(self.anchor), expected)
        merged = self.bring_in("inv")
        self.assertEqual(merged.returncode, 0, merged.stdout + merged.stderr)
        self.assertEqual((self.g("rev-parse", "HEAD"), self.g("status", "--porcelain", "--untracked-files=all")),
                         (self.run_ok(["git", "--git-dir", str(bare), "rev-parse", "main"]), ""))
        self.assertEqual(replaced(self.anchor), expected)
        accepted = ["- [x] " + self.queue["row_line"](identity, title)[6:] for identity, title in
                    (("inv.t1", "Greeting interface 인사"), ("inv.t2", "Greeting app [cli]"))]
        self.assertEqual(self.queue_at("HEAD", "inv"), "\n\n".join(
            ["<!-- replaces docs/specs/queue.md row (occurrence 2): - [ ] unrelated legacy intent -->", *accepted]))
        self.assertEqual(subprocess.run(["git", "-C", str(self.anchor), "cat-file", "blob", "HEAD:docs/specs/queue.md"], env=self.env,
                                        capture_output=True, check=True).stdout, legacy)
        clone = self.root / "fresh clone"
        self.run_ok(["git", "clone", "-q", str(bare), str(clone)])
        self.assertEqual(replaced(clone), expected)
        first, second = self.receipt("inv.t1"), self.receipt("inv.t2")
        self.assertEqual((first["baseline"], second["baseline"], second["acceptance"]["inputs_sha"]),
                         (base, first["merge"]["mergeCommit"]["oid"], first["merge"]["mergeCommit"]["oid"]))
        self.assertIn("- Bring into main: git merge --ff origin/main\n", self.report("inv"))

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_no_task_pr_carries_an_unpushed_anchor_commit(self):
        # Prediction (A1): with an unpushed commit U on the anchor branch, every auto task starts from the refreshed remote
        # base, so no delivered PR head descends from U. Before: the first task started from add's commit atop U, and its
        # PR carried U. Prediction (B): the report prints `git merge --ff origin/main`, and running it merges the delivered
        # work in beside U. Before R5: it printed `git pull --ff-only origin main`, which cannot fast-forward the diverged
        # branch.
        bare, data = self.remote(pending=False)
        (self.anchor / "unrelated.txt").write_text("unpushed\n", encoding="utf-8")
        self.g("add", "unrelated.txt")
        self.g("commit", "-qm", "unpushed unrelated work")
        unpushed = self.g("rev-parse", "HEAD")
        self.plan("inv", CHAIN, {"inv.t1": {"product": "greeting"}, "inv.t2": {"product": "app"}}, delivery="auto")
        tasks = self.tasks(self.drain(local=False))
        self.assertEqual({identity: task["delivery"] for identity, task in tasks.items()}, {"inv.t1": "COMPLETE", "inv.t2": "COMPLETE"})
        heads = [pr["headRefOid"] for pr in json.loads(data.read_text(encoding="utf-8"))["prs"]]
        self.assertEqual(len(heads), 2)
        main = self.run_ok(["git", "--git-dir", str(bare), "rev-parse", "main"])
        for head in [*heads, main]:
            self.assertEqual(subprocess.run(["git", "-C", str(self.anchor), "merge-base", "--is-ancestor", unpushed, head],
                                            env=self.env).returncode, 1, head)
        merged = self.bring_in("inv")
        self.assertEqual(merged.returncode, 0, merged.stdout + merged.stderr)
        self.assertEqual((self.g("rev-list", "--parents", "-n", "1", "HEAD").split()[1:], self.g("status", "--porcelain", "--untracked-files=all")),
                         ([unpushed, main], ""))
        self.assertEqual(self.run_ok([sys.executable, "app.py", "Ada"], cwd=self.anchor), "Hello, Ada!")
        self.assertIn("- Bring into main: git merge --ff origin/main\n", (self.common / "devlyn-loops/inv/drain-report.md").read_text(encoding="utf-8"))

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_independent_pending_prs_merge_one_after_the_other(self):
        # Prediction (A2): once the carrier's PR landed the package, two independent tasks' PRs pending at once each change
        # only their own row of the loop's queue file, one blank line from the next, so they merge one after the other
        # without conflict and the remote rows show both [x]. Before: the rows were adjacent, so the second merge conflicted.
        bare, data = self.remote(pending=True)
        tasks = [CHAIN[0], ("t2", [], "Notes", [NOTES_CHECK]), ("t3", [], "Todo", [TODO_CHECK]),
                 ("t4", ["t1", "t2", "t3"], "Greeting app", [APP_CHECK])]
        self.plan("par", tasks, {"par.t1": {"product": "greeting"}, "par.t2": {"product": "notes"}, "par.t3": {"product": "todo"},
                                 "par.t4": {"product": "app"}}, delivery="auto")
        self.drain(local=False)
        self.assertEqual(self.merge_pr(data, 1).returncode, 0)
        self.drain(local=False)
        pending = [pr for pr in json.loads(data.read_text(encoding="utf-8"))["prs"] if pr["state"] == "OPEN" and pr["autoMergeRequest"]]
        self.assertEqual([pr["headRefName"] for pr in pending], ["devlyn/par/t2", "devlyn/par/t3"])
        for pr in pending:
            merged = self.merge_pr(data, pr["number"])
            self.assertEqual(merged.returncode, 0, merged.stderr)
        rows = self.remote_rows(bare)
        self.assertEqual((rows["par.t2"], rows["par.t3"]), ("x", "x"))

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_carriers_of_two_loops_are_in_flight_at_once(self):
        # Prediction (Q): each loop's package and rows land in its own directory, so while the first auto loop's carrier PR
        # is pending, its independent second task waits for it (the same-loop carrier rule), but the second loop's carrier
        # runs; the two PR heads merge with each other, so in either order, they merge last-first, and the remote base holds
        # every row [x]. Before (R2): the second loop's carrier waited too, since both carriers inserted rows above one
        # trailer line of docs/specs/queue.md.
        bare, data = self.remote(pending=True)
        self.plan("la", [("t1", [], "Notes", [NOTES_CHECK]), ("t2", [], "Todo", [TODO_CHECK]), ("t3", ["t1", "t2"], "Greeting app", [APP_CHECK])],
                  {"la.t1": {"product": "notes"}, "la.t2": {"product": "todo"}, "la.t3": {"product": "app"}}, delivery="auto")
        self.plan("lb", [CHAIN[0]], {"lb.t1": {"product": "greeting"}}, delivery="auto")
        tasks = self.tasks(self.drain(local=False))
        self.assertEqual([(identity, task.get("delivery"), task.get("reason")) for identity, task in tasks.items()], [
            ("la.t1", "PENDING", None), ("la.t2", None, "awaiting delivery of la.t1, whose PR carries its loop's package"),
            ("la.t3", None, "awaiting delivery of la.t1"), ("lb.t1", "PENDING", None)])
        prs = json.loads(data.read_text(encoding="utf-8"))["prs"]
        self.run_ok(["git", "--git-dir", str(bare), "merge-tree", "--write-tree", prs[0]["headRefOid"], prs[1]["headRefOid"]])
        for number in (2, 1):
            merged = self.merge_pr(data, number)
            self.assertEqual(merged.returncode, 0, merged.stderr)
        data.write_text(json.dumps(dict(json.loads(data.read_text(encoding="utf-8")), pending=False)), encoding="utf-8")
        tasks = self.tasks(self.drain(local=False))
        self.assertEqual({identity: task["delivery"] for identity, task in tasks.items()},
                         {"la.t1": "COMPLETE", "la.t2": "COMPLETE", "la.t3": "COMPLETE", "lb.t1": "COMPLETE"})
        self.assertEqual(self.remote_rows(bare), {"la.t1": "x", "la.t2": "x", "la.t3": "x", "lb.t1": "x"})

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_squash_delivery_leaves_the_anchor_pull_ready(self):
        # Prediction (A3): the fake squash-merges every PR; the anchor holds no loop commit and, after add, no package copy,
        # so the report's `git merge --ff origin/main` fast-forwards the anchor to the remote base with a clean tree and both
        # rows [x]. Before: add's commit stayed on the anchor and no squash merge descends from it, so the pull could not
        # fast-forward.
        bare, data = self.remote(pending=False, squash=True)
        self.plan("sq", CHAIN, {"sq.t1": {"product": "greeting"}, "sq.t2": {"product": "app"}}, delivery="auto")
        tasks = self.tasks(self.drain(local=False))
        self.assertEqual({identity: task["delivery"] for identity, task in tasks.items()}, {"sq.t1": "COMPLETE", "sq.t2": "COMPLETE"})
        main = self.run_ok(["git", "--git-dir", str(bare), "rev-parse", "main"])
        self.assertEqual(self.run_ok(["git", "--git-dir", str(bare), "rev-list", "--parents", "-n", "1", main]).split()[1:],
                         [self.receipt("sq.t1")["merge"]["mergeCommit"]["oid"]])  # a squash: one parent
        merged = self.bring_in("sq")
        self.assertEqual(merged.returncode, 0, merged.stdout + merged.stderr)
        self.assertEqual((self.g("rev-parse", "HEAD"), self.g("status", "--porcelain", "--untracked-files=all")), (main, ""))
        self.assertEqual({identity: row["mark"] for identity, row in self.rows("HEAD").items()}, {"sq.t1": "x", "sq.t2": "x"})
        report = (self.common / "devlyn-loops/sq/drain-report.md").read_text(encoding="utf-8")
        self.assertIn("- Bring into main: git merge --ff origin/main\n", report)

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_a_check_only_task_delivers_after_its_squash_merged_prerequisites(self):
        # Prediction (rp-d3 policy 2): in an auto loop whose PRs squash-merge, the check-only sc.t3 starts from a remote base
        # holding both prerequisites' squash merges, commits nothing (source_sha == inputs_sha == that base), and its row-only
        # PR merges, so every remote row is [x]. The runtime is unchanged; this guards the remote path of the policy.
        bare, _ = self.remote(pending=False, squash=True)
        self.plan_checker("sc", [GREET_CHECK, NOTES_CHECK], {"sc.t1": {"product": "greeting"}, "sc.t2": {"product": "notes"}, "sc.t3": {"check_only": True}},
                          delivery="auto")
        tasks = self.tasks(self.drain(local=False))
        self.assertEqual({identity: task["delivery"] for identity, task in tasks.items()}, {"sc.t1": "COMPLETE", "sc.t2": "COMPLETE", "sc.t3": "COMPLETE"})
        checker = self.receipt("sc.t3")
        self.assertEqual((checker["source_sha"], checker["acceptance"]["inputs_sha"]), (checker["baseline"], checker["baseline"]))
        for task in ("t1", "t2"):
            self.g("merge-base", "--is-ancestor", self.receipt(f"sc.{task}")["merge"]["mergeCommit"]["oid"], checker["baseline"])
        self.assertEqual(self.remote_rows(bare), {"sc.t1": "x", "sc.t2": "x", "sc.t3": "x"})

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_a_failed_carrier_hands_the_plan_to_the_next_task(self):
        # Prediction (A4): the carrier fails and is never published; the next task then starts from the same remote base,
        # its inputs commit carries the captured package directory with the loop's queue file, the failed carrier's
        # receipt-proven [F] row included, its PR merges, and the loop settles. Before: both tasks started from add's local commit.
        bare, data = self.remote(pending=False)
        tasks = [CHAIN[0], ("t2", [], "Notes", [NOTES_CHECK]), ("t3", ["t1", "t2"], "Greeting app", [APP_CHECK])]
        self.plan("cf", tasks, {"cf.t1": {"product": "bad-greeting"}, "cf.t2": {"product": "notes"}, "cf.t3": {"product": "app"}},
                  delivery="auto")
        tasks = self.tasks(self.drain(local=False))
        self.assertEqual({identity: task["result"] for identity, task in tasks.items()}, {"cf.t1": "failed", "cf.t2": "accepted", "cf.t3": "blocked"})
        failed, carrier = self.receipt("cf.t1"), self.receipt("cf.t2")
        self.assertEqual((failed["baseline"], carrier["baseline"], carrier["delivery"], self.calls("cf.t3")), (self.base, self.base, "COMPLETE", 0))
        self.assertEqual([pr["headRefName"] for pr in json.loads(data.read_text(encoding="utf-8"))["prs"]], ["devlyn/cf/t2"])
        self.assertEqual(self.g("diff", "--name-only", self.base, carrier["acceptance"]["inputs_sha"]).splitlines(), self.package("cf", ("t1", "t2", "t3")))
        self.assertEqual(self.remote_rows(bare), {"cf.t1": "F", "cf.t2": "x", "cf.t3": "F"})

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_a_task_waits_while_its_base_holds_another_version_of_its_package(self):
        # Prediction (C, A): after the carrier landed docs/specs/ed/, a commit on the remote base that weakens ed.t2's
        # spec.expected.json makes ed.t2 wait, naming that file and the remedies, with no receipt or executor call; once the base
        # holds the captured bytes again, ed.t2 runs its captured APP_CHECK, which its broken product fails. Before: ed.t2's
        # packet and acceptance bound the weakened check, and its broken product was accepted.
        bare, data = self.remote(pending=True)
        self.plan("ed", CHAIN, {"ed.t1": {"product": "greeting"}, "ed.t2": {"product": "bad-app"}}, delivery="auto")
        self.drain(local=False)
        self.assertEqual(self.merge_pr(data, 1).returncode, 0)
        editor = self.root / "editor"
        self.run_ok(["git", "clone", "-q", str(bare), str(editor)])
        expected = editor / "docs/specs/ed/t2/spec.expected.json"
        captured = expected.read_bytes()
        weak = {"argv": [sys.executable, "-c", "print('ok')"], "stdout_contains": ["ok"], "contract_refs": ["R1"]}
        expected.write_text(json.dumps({"verification_commands": [weak]}), encoding="utf-8")
        self.g("commit", "-qam", "weaken ed.t2's check on main", work=editor)
        self.run_ok(["git", "-C", str(editor), "push", "-q", "origin", "main"])
        task = self.tasks(self.drain(local=False))["ed.t2"]
        self.assertEqual((task["result"], task.get("reason"), self.receipt_path("ed.t2").exists(), self.calls("ed.t2")), (
            "pending", "origin/main holds another version of loop ed's package (differing from refs/devlyn/captures/ed: "
            "docs/specs/ed/t2/spec.expected.json), so its tasks cannot run their captured contracts there; plan the work as a new loop, "
            "or restore those files on origin/main to the captured bytes", False, 0))
        expected.write_bytes(captured)
        self.g("commit", "-qam", "restore ed.t2's check", work=editor)
        self.run_ok(["git", "-C", str(editor), "push", "-q", "origin", "main"])
        task = self.tasks(self.drain(local=False))["ed.t2"]
        self.assertEqual((task["result"], "output lacks ['Hello, Ada!', 'Hello, Lin!']" in task["reason"]), ("failed", True))

    def bring_in(self, loop):
        """Run the loop's drain report `Bring into` command in the anchor."""
        command = shlex.split(next(line for line in self.report(loop).splitlines() if line.startswith("- Bring into ")).split(": ", 1)[1])
        self.assertEqual(command[0], "git")
        return subprocess.run(["git", "-C", str(self.anchor), *command[1:]], env=self.env, capture_output=True, text=True, encoding="utf-8")

    def apply_one_drains_reports(self, order):
        # Prediction (B): one drain delivers an auto loop and accepts a local loop, and both reports are written before
        # either command runs; the auto report's `git merge --ff origin/main` and the local report's `git merge --ff`
        # then apply in either order with every row [x] and a clean tree. Before: the auto report was chosen when it was
        # written, `git pull --ff-only origin main`, which aborts once the local merge has moved main.
        self.remote(pending=False)
        self.plan("au", [CHAIN[0]], {"au.t1": {"product": "greeting"}}, delivery="auto")
        self.plan("lo", [("t1", [], "Notes", [NOTES_CHECK])], {"lo.t1": {"product": "notes"}})
        tasks = self.tasks(self.drain(local=False))
        self.assertEqual({identity: task["delivery"] for identity, task in tasks.items()}, {"au.t1": "COMPLETE", "lo.t1": "LOCAL_ONLY"})
        self.assertIn("- Bring into main: git merge --ff origin/main\n", self.report("au"))
        for loop in order:
            merged = self.bring_in(loop)
            self.assertEqual(merged.returncode, 0, (loop, merged.stdout + merged.stderr))
        self.assertEqual(({identity: row["mark"] for identity, row in self.rows("HEAD").items()},
                          self.g("status", "--porcelain", "--untracked-files=all")), ({"au.t1": "x", "lo.t1": "x"}, ""))

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_one_drains_reports_apply_local_first(self):
        self.apply_one_drains_reports(("lo", "au"))

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_one_drains_reports_apply_auto_first(self):
        self.apply_one_drains_reports(("au", "lo"))

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_a_plan_that_never_lands_leaves_the_tracked_queue_unchanged(self):
        # Prediction (R3a, Q): no add, drain or carrier writes the anchor, so after a chain auto loop's first task fails, the
        # anchor's tracked files stay unchanged through its drains and a later auto loop's, the later loop's delivered work
        # comes in with the report's command, a fast-forward pull, and status reports the failed and the blocked row before
        # and after that pull. Before: add wrote the rows into the anchor's queue and only a landed plan removed them, so the
        # queue stayed modified and the pull refused it.
        bare, _ = self.remote(pending=False)
        self.plan("cf", CHAIN, {"cf.t1": {"product": "bad-greeting"}, "cf.t2": {"product": "app"}}, delivery="auto")
        for _ in range(2):
            tasks = self.tasks(self.drain(local=False))
            self.assertEqual({identity: task["result"] for identity, task in tasks.items()}, {"cf.t1": "failed", "cf.t2": "blocked"})
            self.assertEqual(self.g("status", "--porcelain", "--untracked-files=no"), "")
        self.plan("lt", [("t1", [], "Notes", [NOTES_CHECK])], {"lt.t1": {"product": "notes"}}, delivery="auto")
        self.assertEqual(self.tasks(self.drain(local=False))["lt.t1"]["delivery"], "COMPLETE")
        self.assertEqual(self.g("status", "--porcelain", "--untracked-files=no"), "")
        for pull in (False, True):
            if pull:
                pulled = self.bring_in("lt")
                self.assertEqual(pulled.returncode, 0, pulled.stdout + pulled.stderr)
                self.assertEqual(self.g("rev-parse", "HEAD"), self.run_ok(["git", "--git-dir", str(bare), "rev-parse", "main"]))
                self.assertEqual({identity: row["mark"] for identity, row in self.rows("HEAD").items()}, {"lt.t1": "x"})
            status = self.cli("status", "--repo", self.anchor)
            self.assertEqual((status["counts"]["failed"], status["counts"]["blocked"]), (1, 1))
            self.assertIn("cf.t2: blocked-prerequisite:cf.t1", status["blockers"])

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_a_local_loop_and_auto_loops_bring_in_without_conflict(self):
        # Prediction (Q, B): a local loop added between two auto loops runs while their carrier PRs are pending; its
        # report's `git merge --ff` fast-forwards main, and once both PRs merged, the auto report's `git merge --ff origin/main`
        # (main now has the local loop's commits) brings them in beside it with no conflict, every row [x] and a clean tree.
        # Before: the local add commit and the carriers inserted rows at one point of docs/specs/queue.md, so that merge
        # conflicted.
        _, data = self.remote(pending=True)
        self.plan("au", [CHAIN[0]], {"au.t1": {"product": "greeting"}}, delivery="auto")
        self.plan("lo", [("t1", [], "Notes", [NOTES_CHECK])], {"lo.t1": {"product": "notes"}})
        self.plan("aw", [("t1", [], "Todo", [TODO_CHECK])], {"aw.t1": {"product": "todo"}}, delivery="auto")
        tasks = self.tasks(self.drain(local=False))
        self.assertEqual({identity: task["delivery"] for identity, task in tasks.items()}, {"au.t1": "PENDING", "lo.t1": "LOCAL_ONLY", "aw.t1": "PENDING"})
        merged = self.bring_in("lo")
        self.assertEqual(merged.returncode, 0, merged.stdout + merged.stderr)
        self.assertEqual((self.g("rev-parse", "HEAD"), self.g("status", "--porcelain", "--untracked-files=all")), (self.receipt("lo.t1")["publish_sha"], ""))
        for number in (1, 2):
            self.assertEqual(self.merge_pr(data, number).returncode, 0)
        self.drain(local=False)
        self.assertIn("- Bring into main: git merge --ff origin/main\n", self.report("aw"))
        merged = self.bring_in("aw")
        self.assertEqual(merged.returncode, 0, merged.stdout + merged.stderr)
        self.assertEqual({identity: row["mark"] for identity, row in self.rows("HEAD").items()}, {"au.t1": "x", "aw.t1": "x", "lo.t1": "x"})
        self.assertEqual(self.g("status", "--porcelain", "--untracked-files=all"), "")

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_a_used_loop_id_is_refused_before_and_after_the_drain(self):
        # Prediction (R3e, C): add refuses a different package under a loop id that already has an add record, while the
        # loop is queued and again after its delivery, which would otherwise take the old loop's receipts for the new one.
        bare, _ = self.remote(pending=False)
        self.plan("ru", [CHAIN[0]], {"ru.t1": {"product": "greeting"}}, delivery="auto")

        def readd():
            meta = self.queue["write_package"](self.anchor, "ru", [("t9", [], "Other", [NOTES_CHECK])], delivery="auto", base=self.base)
            return self.cli("add", meta, code=1)["reason"]
        self.assertIn("loop id ru was already added with another package", readd())
        self.assertEqual(self.tasks(self.drain(local=False))["ru.t1"]["delivery"], "COMPLETE")
        self.assertIn("loop id ru was already added with another package", readd())

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_an_auto_loop_resumed_local_only_is_reported(self):
        # Prediction: an auto loop whose first task an auto drain left active and unpushed, resumed with --local-only, drains
        # both tasks to LOCAL_ONLY, and this drain and the next each end with the loop's report. Before: the report read the
        # loop's auto add record as a local one, so every drain ended BLOCKED "malformed add record" without a report.
        self.remote(pending=False)
        self.plan("ri", CHAIN, {"ri.t1": {"product": "greeting"}, "ri.t2": {"product": "app"}}, delivery="auto")
        stopped = self.cli("drain", "--repo", self.anchor, "--", str(self.root / "no executor"), "{packet}")
        self.assertIn("executor could not start", " ".join(task.get("reason", "") for task in stopped["tasks"]))
        report = self.common / "devlyn-loops/ri/drain-report.md"
        for _ in range(2):
            report.unlink()
            tasks = self.tasks(self.drain())
            self.assertEqual({identity: (task["result"], task["delivery"]) for identity, task in tasks.items()},
                             {"ri.t1": ("accepted", "LOCAL_ONLY"), "ri.t2": ("accepted", "LOCAL_ONLY")})
            self.assertIn("- Whole-loop acceptance: ACCEPTED", report.read_text(encoding="utf-8"))

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_an_auto_loop_resumes_from_another_worktree(self):
        # Prediction (C): every worktree of the repository reads the loop's capture, so with au.t1 left active by an executor
        # that could not start, a drain from a linked worktree on another branch resumes it from its committed inputs and
        # delivers it with one executor call, naming no inputs change. Before: only the checkout that added the loop saw its
        # rows, so the linked worktree's drain listed none of them.
        self.remote(pending=False)
        self.plan("au", [CHAIN[0]], {"au.t1": {"product": "greeting"}}, delivery="auto")
        stopped = self.cli("drain", "--repo", self.anchor, "--", str(self.root / "no executor"), "{packet}")
        self.assertIn("executor could not start", " ".join(task.get("reason", "") for task in stopped["tasks"]))
        linked = self.root / "linked"
        self.g("worktree", "add", "-q", "-b", "side", str(linked))
        self.assertEqual((self.tasks(self.drain(local=False, repo=linked))["au.t1"]["delivery"], self.calls("au.t1")), ("COMPLETE", 1))

    def test_retained_scratch_reports_its_reason_and_resume(self):
        self.plan("inv", [CHAIN[0]], {"inv.t1": {"product": "greeting"}})
        result = self.drain(unobservable=True)
        scratch = self.receipt("inv.t1")["scratch_cleanup"]
        self.assertEqual(scratch["status"], "RETAINED")
        expected = f"RETAINED — {scratch['reason']}; resume: {scratch['resume']}"
        self.assertEqual(self.tasks(result)["inv.t1"]["scratch"], expected)
        self.assertIn(f"- Scratch cleanup: {expected}\n", self.report("inv"))

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_merge_refused_reports_why_a_person_must_merge(self):
        self.remote(merge_allowed=False)
        self.plan("inv", [CHAIN[0]], {"inv.t1": {"product": "greeting"}}, delivery="auto")
        for _ in range(2):
            result = self.drain(local=False)
            task = self.tasks(result)["inv.t1"]
            self.assertEqual((result["status"], task["result"], task["delivery"]), ("WAITING", "accepted", "PR"))
            reason = "merge refused: repository disallows merge commits; a person merges the PR"
            self.assertEqual(task.get("reason"), reason)
            self.assertIn(f"- Reason: {reason}\n", self.report("inv"))
            self.assertIn(f"- PR: {task['pr']}\n", self.report("inv"))
        self.assertEqual(self.calls("inv.t1"), 1)

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_report_omits_the_branch_only_after_cleanup_deletes_it(self):
        _, data = self.remote(pending=True)
        self.plan("inv", [CHAIN[0]], {"inv.t1": {"product": "greeting"}}, delivery="auto")
        task = self.tasks(self.drain(local=False))["inv.t1"]
        branch = self.receipt("inv.t1")["branch"]
        self.assertEqual(task["branch"], branch)
        self.assertIn(f"- Branch: {branch}\n", self.report("inv"))
        self.g("show-ref", "--verify", "refs/heads/" + branch)
        self.assertEqual(self.merge_pr(data, 1).returncode, 0)
        task = self.tasks(self.drain(local=False))["inv.t1"]
        self.assertEqual(task["delivery"], "COMPLETE")
        self.assertEqual(self.g("branch", "--list", branch), "")
        self.assertFalse(Path(self.receipt("inv.t1")["worktree"]).exists())
        self.assertIsNone(task.get("branch"))
        self.assertNotIn("- Branch:", self.report("inv"))

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_delivery_pending_keeps_acceptance_resources_and_resume(self):
        bare, data = self.remote(pending=True)
        self.plan("inv", CHAIN, {"inv.t1": {"product": "greeting"}, "inv.t2": {"product": "app"}}, delivery="auto")
        result = self.drain(local=False)
        tasks = self.tasks(result)
        self.assertEqual((result["status"], tasks["inv.t1"]["result"], tasks["inv.t1"]["delivery"]), ("WAITING", "accepted", "PENDING"))
        self.assertEqual((tasks["inv.t2"]["result"], tasks["inv.t2"]["reason"]), ("pending", "awaiting delivery of inv.t1"))
        self.assertEqual(self.calls("inv.t2"), 0)
        receipt = self.receipt("inv.t1")
        self.assertTrue(Path(receipt["worktree"]).is_dir())
        self.assertEqual(json.loads(data.read_text())["prs"][0]["headRefOid"], receipt["publish_sha"])
        self.assertIn("task-complete.py complete --receipt", tasks["inv.t1"]["resume"])
        report = (self.common / "devlyn-loops/inv/drain-report.md").read_text(encoding="utf-8")
        self.assertIn("Delivery: PENDING", report)
        self.assertIn("Resume: ", report)
        # Prediction (A): a later --local-only drain never rewrites the delivery of a task whose PR is already pushed, nor runs
        # the rest of its loop locally on that unmerged source: inv.t1 and its dependent inv.t2 wait naming the PR, with no
        # executor call, and nothing reaches the remote. Before: inv.t2 ran locally on inv.t1's pushed source (one call).
        server = json.loads(data.read_text())
        result = self.drain()
        reason = f"inv.t1 already has a pushed PR {receipt['pr_url']}, so --local-only never runs loop inv; drain without --local-only"
        self.assertEqual((result["status"], [(task["identity"], task["result"], task.get("reason")) for task in result["tasks"]]),
                         ("WAITING", [("inv.t1", "accepted", reason), ("inv.t2", "pending", reason)]))
        self.assertEqual((self.receipt("inv.t1")["delivery"], self.receipt("inv.t1").get("local_only"), self.calls("inv.t2")), ("PENDING", None, 0))
        self.assertEqual(json.loads(data.read_text()), server)

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_a_local_only_drain_leaves_a_published_auto_loop_waiting(self):
        # Prediction (A): once a task of an auto loop is published, --local-only never runs that loop: with pr.t1 squash-merged
        # and pr.t2's PR pending, pr.t2 and the integration task pr.t3 wait naming pr.t1's PR, with no executor call, while a
        # local loop added later is accepted, and the drain ends WAITING. Before: pr.t3 was allocated locally on pr.t2's
        # source, which lacks pr.t1's pre-squash source, so every such drain ended BLOCKED "plan an integration task" and
        # lo.t1 never ran.
        bare, data = self.remote(pending=True, squash=True)
        tasks = [CHAIN[0], ("t2", [], "Notes", [NOTES_CHECK]), ("t3", ["t1", "t2"], "Greeting app", [APP_CHECK])]
        self.plan("pr", tasks, {"pr.t1": {"product": "greeting"}, "pr.t2": {"product": "notes"}, "pr.t3": {"product": "app"}}, delivery="auto")
        self.drain(local=False)
        self.assertEqual(self.merge_pr(data, 1).returncode, 0)
        self.assertEqual(self.tasks(self.drain(local=False))["pr.t2"]["delivery"], "PENDING")
        self.plan("lo", [("t1", [], "Todo", [TODO_CHECK])], {"lo.t1": {"product": "todo"}})
        result = self.drain()
        reason = f"pr.t1 already has a pushed PR {self.receipt('pr.t1')['pr_url']}, so --local-only never runs loop pr; drain without --local-only"
        self.assertEqual((result["status"], {task["identity"]: (task["result"], task.get("reason")) for task in result["tasks"]}), ("WAITING", {
            "pr.t1": ("accepted", None), "pr.t2": ("accepted", reason), "pr.t3": ("pending", reason), "lo.t1": ("accepted", None)}))
        self.assertEqual((self.calls("pr.t3"), self.calls("lo.t1")), (0, 1))

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_a_refused_delivery_waits_while_independent_loops_run(self):
        # A non-default base waits before allocation; independent loops and later closed-PR refusals still proceed.
        bare, data = self.remote(pending=True)
        self.run_ok(["git", "-C", str(self.anchor), "push", "-q", str(bare), "main:develop"])
        self.plan("pm", [CHAIN[0]], {"pm.t1": {"product": "greeting"}}, delivery="pr")
        meta = self.queue["write_package"](self.anchor, "dv", [("t1", [], "Todo", [TODO_CHECK])], delivery="auto", base=self.base)
        meta.write_text(meta.read_text(encoding="utf-8").replace('"base_ref": "main"', '"base_ref": "develop"'), encoding="utf-8")
        self.behaviors["dv.t1"] = {"product": "todo"}
        self.cli("add", meta)
        self.plan("lo", [("t1", [], "Notes", [NOTES_CHECK])], {"lo.t1": {"product": "notes"}})
        refused = "delivery blocked: task-complete complete: "
        base_reason = "auto delivery base develop is not the repository's default branch main; plan the loop on main, or drain with --local-only"
        result = self.drain(local=False)
        tasks = self.tasks(result)
        self.assertEqual(self.calls("dv.t1"), 0)
        self.assertFalse(self.receipt_path("dv.t1").exists())
        self.assertEqual((result["status"], {identity: (task["result"], task.get("delivery"), task.get("reason")) for identity, task in tasks.items()}),
                         ("WAITING", {"pm.t1": ("accepted", "PR", None), "lo.t1": ("accepted", "LOCAL_ONLY", None),
                                      "dv.t1": ("pending", None, base_reason)}))
        server = json.loads(data.read_text(encoding="utf-8"))
        server["prs"][0]["state"] = "CLOSED"
        data.write_text(json.dumps(server), encoding="utf-8")
        self.plan("lp", [("t1", [], "Greeting", [GREET_CHECK])], {"lp.t1": {"product": "greeting"}})
        tasks = self.tasks(self.drain(local=False))
        self.assertEqual({identity: (task["result"], task.get("reason")) for identity, task in tasks.items()}, {
            "pm.t1": ("accepted", refused + "PR is closed without merge; retain task"), "lo.t1": ("accepted", None),
            "dv.t1": ("pending", base_reason), "lp.t1": ("accepted", None)})
        self.assertEqual([self.calls(identity) for identity in ("pm.t1", "dv.t1", "lo.t1", "lp.t1")], [1, 0, 1, 1])

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_repository_lookup_failure_waits_while_local_loops_run(self):
        self.remote()
        (self.root / "bin/gh").write_text("#!/bin/sh\necho 'repo lookup unavailable' >&2\nexit 1\n", encoding="utf-8")
        self.plan("au", [CHAIN[0]], {"au.t1": {"product": "greeting"}}, delivery="auto")
        self.plan("lo", [CHAIN[0]], {"lo.t1": {"product": "greeting"}})
        result = self.drain(local=False)
        tasks = self.tasks(result)
        self.assertEqual(result["status"], "WAITING")
        self.assertEqual((tasks["au.t1"]["result"], self.calls("au.t1")), ("pending", 0))
        self.assertIn("cannot check delivery repository", tasks["au.t1"]["reason"])
        self.assertIn("repo lookup unavailable", tasks["au.t1"]["reason"])
        self.assertFalse(self.receipt_path("au.t1").exists())
        self.assertEqual((tasks["lo.t1"]["delivery"], self.calls("lo.t1")), ("LOCAL_ONLY", 1))

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_repository_lookup_errors_wait_while_local_loops_run(self):
        self.remote()
        self.plan("au", [CHAIN[0]], {"au.t1": {"product": "greeting"}}, delivery="auto")
        # Inject only gh's spawn/output failures; Git, allocation and the local executor remain real.
        wrapper = (
            "import runpy, subprocess, sys\n"
            "failure = sys.argv.pop(1)\n"
            "real = subprocess.run\n"
            "def run(argv, **kwargs):\n"
            "    if argv[0] == 'gh':\n"
            "        if failure == 'missing':\n"
            "            raise FileNotFoundError('gh unavailable')\n"
            "        return subprocess.CompletedProcess(argv, 0, stdout=failure, stderr='')\n"
            "    return real(argv, **kwargs)\n"
            "subprocess.run = run\n"
            "sys.argv = sys.argv[1:]\n"
            "runpy.run_path(sys.argv[0], run_name='__main__')\n")
        for index, failure in enumerate(("missing", "invalid JSON", "{}", "null")):
            with self.subTest(failure=failure):
                loop = f"lo{index}"
                self.plan(loop, [CHAIN[0]], {f"{loop}.t1": {"product": "greeting"}})
                result = json.loads(self.run_ok([sys.executable, "-c", wrapper, failure, *self.drain_argv(local=False)[1:]]))
                tasks = self.tasks(result)
                self.assertEqual(result["status"], "WAITING")
                self.assertEqual((tasks["au.t1"]["result"], self.calls("au.t1")), ("pending", 0))
                self.assertIn("cannot check delivery repository", tasks["au.t1"]["reason"])
                self.assertFalse(self.receipt_path("au.t1").exists())
                self.assertEqual((tasks[f"{loop}.t1"]["delivery"], self.calls(f"{loop}.t1")), ("LOCAL_ONLY", 1))

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_nondefault_bases_wait_before_allocation_but_local_delivery_runs(self):
        # GitHub's default is release even though the fixture's Git HEAD is main.
        bare, _ = self.remote(default_branch="release", pending=True)
        self.run_ok(["git", "-C", str(self.anchor), "push", "-q", str(bare), "main:release"])
        for loop, delivery, base in (("au", "auto", "main"), ("pr", "pr", "main"),
                                     ("ok", "pr", "release"), ("lo", "local-only", "main")):
            meta = self.queue["write_package"](self.anchor, loop, [CHAIN[0]], delivery=delivery, base=self.base)
            meta.write_text(meta.read_text(encoding="utf-8").replace('"base_ref": "main"', f'"base_ref": "{base}"'), encoding="utf-8")
            self.behaviors[f"{loop}.t1"] = {"product": "greeting"}
            self.cli("add", meta)
        result = self.drain(local=False)
        tasks = self.tasks(result)
        for loop, mode in (("au", "auto"), ("pr", "pr")):
            with self.subTest(delivery=mode):
                identity = f"{loop}.t1"
                self.assertEqual(self.calls(identity), 0)
                self.assertFalse(self.receipt_path(identity).exists())
                self.assertFalse((self.anchor.parent / ".devlyn-worktrees" / self.anchor.name / loop / "t1").exists())
                self.assertEqual(tasks[identity]["result"], "pending")
                self.assertEqual(tasks[identity]["reason"], f"{mode} delivery base main is not the repository's default branch release; "
                                 "plan the loop on release, or drain with --local-only")
        self.assertEqual(result["status"], "WAITING")
        self.assertEqual((tasks["ok.t1"]["delivery"], tasks["lo.t1"]["delivery"]), ("PR", "LOCAL_ONLY"))
        tasks = self.tasks(self.drain())
        for loop in ("au", "pr"):
            self.assertEqual((tasks[f"{loop}.t1"]["delivery"], self.calls(f"{loop}.t1")), ("LOCAL_ONLY", 1))

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_resume_before_first_delivery_preserves_the_plan_mode(self):
        # Prediction: after terminal attachment but before the first complete call, a pr plan's exact printed resume
        # leaves an open PR even under auto policy, without releasing writers or rerunning the executor. Before: it merged.
        _, data = self.remote()
        self.run_ok(["git", "--git-dir", str(self.common), "config", "--local", "devlyn.completionMode", "auto"])
        self.plan("pr", [CHAIN[0]], {"pr.t1": {"product": "greeting"}}, delivery="pr")
        argv = self.drain_argv(local=False)
        crashed = subprocess.run([sys.executable, "-c", CRASH, "attach-after", "receipt.json", *argv[1:]], cwd=self.root,
                                 env=self.env, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(crashed.returncode, 9, crashed.stdout + crashed.stderr)
        receipt = self.receipt("pr.t1")
        self.assertEqual(receipt["acceptance"]["verdict"], "ACCEPTED")
        self.assertEqual(receipt["queue"]["commit"], receipt["publish_sha"])
        for key in ("delivery", "mode_override", "local_only", "writers_released"):
            self.assertNotIn(key, receipt)
        pending, = self.cli("status", "--repo", self.anchor)["delivery"]
        self.assertEqual(pending["identity"], "pr.t1")
        resume = shlex.split(pending["resume"])
        self.assertNotIn("--writers-stopped", resume)
        self.assertEqual(json.loads(data.read_text(encoding="utf-8")).get("prs", []), [])
        # Prediction: a missing packet leaves status available, with a diagnostic instead of an unsafe resume.
        with self.subTest("missing packet before mode is recorded"):
            packet = self.receipt_path("pr.t1").with_name("packet.json")
            saved = packet.read_bytes()
            packet.unlink()
            try:
                status = self.cli("status", "--repo", self.anchor)
                self.assertEqual(status["counts"]["accepted"], 1)
                self.assertEqual(status["delivery"], [])
                self.assertTrue(any("task summary unavailable: pr.t1" in note and "packet.json" in note for note in status["cleanup"]))
            finally:
                packet.write_bytes(saved)
        resumed = json.loads(self.run_ok(resume, cwd=self.root))
        self.assertEqual((resumed["status"], resumed["delivery_status"]), ("PR", "PR"))
        receipt = self.receipt("pr.t1")
        self.assertEqual(receipt["mode_override"], "pr")
        self.assertNotIn("writers_released", receipt)
        server = json.loads(data.read_text(encoding="utf-8"))
        pr, = server["prs"]
        self.assertEqual((pr["state"], server.get("merges", 0), self.calls("pr.t1")), ("OPEN", 0, 1))
        pending, = self.cli("status", "--repo", self.anchor)["delivery"]
        self.assertNotIn("--mode", shlex.split(pending["resume"]))

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_a_per_task_mode_survives_later_drains(self):
        # Prediction (H6): the plan's mode seeds an auto task's first delivery call (auto-merge requested, PENDING); after the
        # user's `task-complete.py complete --mode pr`, which cancels that request, the next drain keeps the receipt's pr:
        # delivery PR, no new merge request and mode_override pr. Before: every drain passed the manifest's mode again, so the
        # drain re-requested auto-merge and reset mode_override to auto, merging what the user held back.
        _, data = self.remote(pending=True)
        self.plan("inv", [CHAIN[0]], {"inv.t1": {"product": "greeting"}}, delivery="auto")
        self.assertEqual(self.tasks(self.drain(local=False))["inv.t1"]["delivery"], "PENDING")
        held = json.loads(self.run_ok([sys.executable, str(self.helper), "complete", "--receipt", str(self.receipt_path("inv.t1")), "--mode", "pr"]))
        self.assertEqual((held["status"], json.loads(data.read_text(encoding="utf-8"))["prs"][0]["autoMergeRequest"]), ("PR", None))
        self.assertEqual(self.tasks(self.drain(local=False))["inv.t1"]["delivery"], "PR")
        server = json.loads(data.read_text(encoding="utf-8"))
        self.assertEqual((server["merges"], server["prs"][0]["autoMergeRequest"], self.receipt("inv.t1")["mode_override"]), (1, None, "pr"))


    def harness_release(self, fresh=True):
        """Build once, copy only the release inventory; no source-checkout manifest or model calls."""
        cls = type(self)
        if not hasattr(cls, "release_fixture"):
            temp = tempfile.TemporaryDirectory(prefix="devlyn-cli2-release-")
            cls.addClassCleanup(temp.cleanup)
            build = Path(temp.name) / "build"
            build.mkdir()
            source = self.skills.parents[1]
            for name in ("bin", "config", "optional-skills", "node_modules"):
                shutil.copytree(source / name, build / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".bin"))
            for name in ("package.json", "CLAUDE.md", "AGENTS.md"):
                shutil.copy2(source / name, build / name)
            self.run_ok(["node", "-e", "require(process.argv[1]).buildRelease()", str(build / "bin/release.js")])
            cls.release_fixture = Path(temp.name) / "release"
            manifest = json.loads((build / "release.json").read_bytes())
            for name in ["release.json", *(entry["path"] for entry in manifest["files"])]:
                target = cls.release_fixture / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(build / name, target)
        release = self.root / "release"
        if not release.exists():
            shutil.copytree(cls.release_fixture, release)
        if fresh:
            (self.anchor / "docs/specs/queue.md").write_text("# Intent Queue\n", encoding="utf-8")
            self.g("add", "docs/specs/queue.md")
            self.g("commit", "-qm", "empty legacy queue")
            self.base = self.g("rev-parse", "HEAD")
        self.queue_py = release / "config/skills/devlyn-ideate/scripts/queue.py"
        self.queue = runpy.run_path(str(self.queue_py))
        return release

    def tree_snapshot(self, root):
        return {str(p.relative_to(root)): (p.lstat().st_mode, p.lstat().st_mtime_ns,
                os.readlink(p) if p.is_symlink() else hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None)
                for p in root.rglob("*")}

    def test_harness_binding_packet_and_settlement(self):
        # Prediction: capture through a linked checkout binds its common Gitdir; dispatch sends unchanged argv and v2
        # release defaults; successful local delivery releases the binding without changing release files.
        release = self.harness_release()
        before = self.tree_snapshot(release)
        if os.name != "nt":
            link = self.root / "invoked-skill"
            link.symlink_to(release / "config/skills/devlyn-ideate", target_is_directory=True)
            self.queue_py = link / "scripts/queue.py"
        linked = self.root / "linked"
        self.g("worktree", "add", "-qb", "linked", str(linked))
        meta = self.queue["write_package"](linked, "bound", CHAIN[:1], base=self.base)
        self.cli("add", meta)
        binding_path = self.common / "devlyn-loops/harness.json"
        binding = json.loads(binding_path.read_bytes())
        self.assertEqual(binding["release"]["root"], str(release))
        self.assertFalse((linked / "harness.json").exists())
        self.behaviors = {"bound.t1": {"product": "greeting"}}
        self.assertEqual(self.tasks(self.drain(repo=linked))["bound.t1"]["delivery"], "LOCAL_ONLY")
        packet = json.loads(self.receipt_path("bound.t1").with_name("packet.json").read_bytes())
        self.assertEqual((packet["schema_version"], packet["harness"]), (2, binding["release"]))
        self.assertEqual(packet["methodology"], {"defaults": {"source": "release", **binding["defaults"]}, "projectInstructions": []})
        for resource in (binding["defaults"], packet["workerPrompt"]):
            self.assertTrue(Path(resource["path"]).is_absolute())
            self.assertEqual(hashlib.sha256(Path(resource["path"]).read_bytes()).hexdigest(), resource["sha256"])
        self.assertFalse(binding_path.exists())
        self.assertEqual(before, self.tree_snapshot(release))

    def test_harness_concurrent_first_capture(self):
        # Prediction: two first adds serialize the binding and capture; both records retain the same release.
        self.harness_release()
        metas = [self.queue["write_package"](self.anchor, loop, CHAIN[:1], base=self.base) for loop in ("one", "two")]
        processes = [subprocess.Popen([sys.executable, str(self.queue_py), "add", str(meta)], env=self.env,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE) for meta in metas]
        for proc in processes:
            out, err = proc.communicate(timeout=60)
            self.assertEqual(proc.returncode, 0, (out, err))
        binding = json.loads((self.common / "devlyn-loops/harness.json").read_bytes())
        self.assertEqual(binding["release"]["root"], str(self.root / "release"))
        self.assertEqual(self.cli("inspect", "--repo", self.anchor, "--json")["counts"]["pending"], 2)

    def test_harness_interrupted_binding(self):
        # Prediction: crashes before/after atomic binding publish no capture; retry retains exactly the published identity.
        self.harness_release()
        meta = self.queue["write_package"](self.anchor, "crash", CHAIN[:1], base=self.base)
        binding_path = self.common / "devlyn-loops/harness.json"
        for step in ("replace", "replace-after"):
            with self.subTest(step=step):
                result = subprocess.run([sys.executable, "-c", CRASH, step, "harness.json", str(self.queue_py), "add", str(meta)],
                                        env=self.env, capture_output=True)
                self.assertEqual(result.returncode, 9, result.stderr)
                self.assertEqual(binding_path.exists(), step.endswith("after"))
                self.assertEqual(self.g("for-each-ref", "--format=%(refname)", "refs/devlyn/captures"), "")
        binding = binding_path.read_bytes()
        self.cli("status", "--repo", self.anchor)
        self.assertEqual(binding_path.read_bytes(), binding)
        self.cli("add", meta)
        self.assertEqual(binding_path.read_bytes(), binding)

    def test_harness_mismatch_exact_recovery(self):
        # Prediction: another verified release cannot even clean the queue; its refusal carries an exact original argv.
        release = self.harness_release()
        self.plan("bound", CHAIN[:1], {})
        other = self.root / "other release"
        shutil.copytree(release, other)
        package = json.loads((other / "package.json").read_bytes())
        package["version"] = "0.0.0-cli2-mismatch"
        (other / "package.json").write_text(json.dumps(package), encoding="utf-8")
        self.run_ok(["node", "-e", "require(process.argv[1]).buildRelease()", str(other / "bin/release.js")])
        self.queue_py = other / "config/skills/devlyn-ideate/scripts/queue.py"
        args = ["drain", "--repo", str(self.anchor), "--local-only", "--", sys.executable, "-c", "pass", "{packet}"]
        before = self.tree_snapshot(self.anchor)
        result = self.cli(*args, code=1)
        recovery = json.loads(result["reason"].split("recovery argv: ", 1)[1])
        self.assertEqual(recovery, [sys.executable, str(release / "config/skills/devlyn-ideate/scripts/queue.py"), *args])
        self.assertEqual(before, self.tree_snapshot(self.anchor))
        inspected = self.cli("inspect", "--repo", self.anchor, "--json")
        self.assertFalse(inspected["compatibility"]["compatible"])
        self.assertEqual(inspected["compatibility"]["recoveryArgv"][1], recovery[1])

    def test_harness_legacy_unbound_and_v1(self):
        # Prediction: an existing unfinished unbound queue is not rebound, even from a release; v1 resumes byte-for-byte.
        self.plan("legacy", CHAIN[:1], {"legacy.t1": {"product": "greeting"}})
        self.cli("drain", "--repo", self.anchor, "--local-only", "--", str(self.root / "absent"), "{packet}")
        path = self.receipt_path("legacy.t1").with_name("packet.json")
        packet = json.loads(path.read_bytes())
        packet["schema_version"] = 1
        packet["methodology"] = packet["methodology"]["projectInstructions"]
        packet.pop("harness")
        packet.pop("workerPrompt")
        path.write_text(json.dumps(packet), encoding="utf-8")
        original = path.read_bytes()
        self.harness_release(fresh=False)
        inspected = self.cli("inspect", "--repo", self.anchor, "--json")
        self.assertIsNone(inspected["binding"])
        self.assertTrue(inspected["compatibility"]["legacy"])
        self.assertEqual(self.tasks(self.drain())["legacy.t1"]["result"], "accepted")
        self.assertEqual(path.read_bytes(), original)
        self.assertFalse((self.common / "devlyn-loops/harness.json").exists())

    def test_harness_unbound_packet_names_its_own_defaults(self):
        # Prediction: an unbound queue's packet names the running installation's own runtime-principles.md (source
        # "skill"), so a global-only install no longer drains its tasks without principles. Before: defaults were null
        # and a checkout without CLAUDE.md/AGENTS.md ran its executor with no principles at all.
        self.plan("own", CHAIN[:1], {"own.t1": {"product": "greeting"}})
        self.cli("drain", "--repo", self.anchor, "--local-only", "--", str(self.root / "absent"), "{packet}")
        packet = json.loads(self.receipt_path("own.t1").with_name("packet.json").read_bytes())
        own = self.skills / "_shared/runtime-principles.md"
        self.assertIsNone(packet["harness"])
        self.assertEqual(packet["methodology"]["defaults"],
                         {"source": "skill", "path": str(own), "sha256": hashlib.sha256(own.read_bytes()).hexdigest()})
        self.assertEqual(self.tasks(self.drain())["own.t1"]["result"], "accepted")

    def test_harness_task_without_any_principles_waits(self):
        # Prediction: with no committed CLAUDE.md/AGENTS.md and an installation that lost runtime-principles.md, the task
        # waits naming the gap before its executor starts, and drains once the file is back.
        copy = Path(self.skill_copy(self.root / "skills-copy", "4.3.0")["root"])
        own = copy / "_shared/runtime-principles.md"
        original = own.read_bytes()
        own.unlink()
        self.plan("bare", CHAIN[:1], {"bare.t1": {"product": "greeting"}})
        result = self.drain()
        self.assertIn("no principles reach its executor", self.tasks(result)["bare.t1"]["reason"])
        self.assertEqual(self.calls("bare.t1"), 0)
        own.write_bytes(original)
        self.assertEqual(self.tasks(self.drain())["bare.t1"]["result"], "accepted")

    def other_release(self, release, version):
        other = self.root / f"release {version}"
        shutil.copytree(release, other)
        package = json.loads((other / "package.json").read_bytes())
        package["version"] = version
        (other / "package.json").write_text(json.dumps(package), encoding="utf-8")
        self.run_ok(["node", "-e", "require(process.argv[1]).buildRelease()", str(other / "bin/release.js")])
        return other

    def test_harness_blocked_dependent_releases_binding(self):
        # Prediction: t1 fails and t2 is blocked behind it for good; the drain ends DRAINED and settles the binding.
        # Before: a blocked task counted as unfinished, so every later release refused this repository.
        self.harness_release()
        self.plan("cf", CHAIN, {"cf.t1": {"product": "bad-greeting"}, "cf.t2": {"product": "app"}})
        result = self.drain()
        self.assertEqual((result["status"], self.tasks(result)["cf.t1"]["result"], self.tasks(result)["cf.t2"]["result"]),
                         ("DRAINED", "failed", "blocked"))
        self.assertFalse((self.common / "devlyn-loops/harness.json").exists())

    def test_harness_settled_queue_yields_to_another_release(self):
        # Prediction: a binding left on a settled queue (its last delivery finished outside queue.py) or by a first add
        # interrupted before its capture is dropped by another release, which then binds its own; an unfinished queue
        # still refuses (test_harness_mismatch_exact_recovery).
        release = self.harness_release()
        binding_path = self.common / "devlyn-loops/harness.json"
        self.plan("done", CHAIN[:1], {"done.t1": {"product": "greeting"}})
        self.drain()
        self.assertFalse(binding_path.exists())
        for leftover in ("settled", "interrupted"):
            with self.subTest(leftover=leftover):
                self.queue_py = release / "config/skills/devlyn-ideate/scripts/queue.py"
                binding_path.write_text(json.dumps({"schemaVersion": 1, "release": json.loads(
                    self.run_ok(["node", str(release / "bin/devlyn.js"), "release", "--verify", "--root", str(release), "--json"]))["data"]["release"],
                    "defaults": {"path": str(release / "config/skills/_shared/runtime-principles.md"),
                                 "sha256": hashlib.sha256((release / "config/skills/_shared/runtime-principles.md").read_bytes()).hexdigest()}}),
                    encoding="utf-8")
                other = self.other_release(release, f"0.0.0-cli2-{leftover}")
                self.queue_py = other / "config/skills/devlyn-ideate/scripts/queue.py"
                self.cli("status", "--repo", self.anchor)
                self.assertFalse(binding_path.exists())

    def test_harness_unbound_defaults_change_does_not_strand_a_task(self):
        # Prediction: a normal update rewrites an unbound installation's runtime-principles.md while its task's packet
        # names the old bytes; the task still runs and is accepted. Only a missing file makes it wait, before a spawn.
        copy = Path(self.skill_copy(self.root / "skills-copy", "4.3.0")["root"])
        own = copy / "_shared/runtime-principles.md"
        self.plan("upd", CHAIN[:1], {"upd.t1": {"product": "greeting"}})
        self.cli("drain", "--repo", self.anchor, "--local-only", "--", str(self.root / "absent"), "{packet}")
        original = own.read_bytes()
        own.unlink()
        result = self.drain()
        self.assertIn("principles file", self.tasks(result)["upd.t1"]["reason"])
        self.assertEqual(self.calls("upd.t1"), 0)
        own.write_bytes(original + b"\nA later release's wording.\n")
        self.assertEqual(self.tasks(self.drain())["upd.t1"]["result"], "accepted")

    def test_harness_defaults_missing_or_changed_refuse_recovery(self):
        # Prediction: missing/modified defaults refuse before spawn and preserve the packet, binding and invocation count.
        release = self.harness_release()
        self.plan("recover", CHAIN[:1], {"recover.t1": {"product": "greeting"}})
        self.cli("drain", "--repo", self.anchor, "--local-only", "--", str(self.root / "absent"), "{packet}")
        path = self.receipt_path("recover.t1").with_name("packet.json")
        packet = path.read_bytes()
        defaults = release / "config/skills/_shared/runtime-principles.md"
        original = defaults.read_bytes()
        for changed in (None, b"changed defaults\n"):
            with self.subTest(changed=changed):
                if changed is None:
                    defaults.unlink()
                else:
                    defaults.write_bytes(changed)
                result = self.drain(code=1)
                self.assertIn("release verification failed", result["reason"])
                self.assertEqual(path.read_bytes(), packet)
                self.assertEqual(self.calls("recover.t1"), 0)
                defaults.write_bytes(original)
        # A packet cannot drop its defaults or masquerade as legacy while its queue is bound.
        for legacy in (False, True):
            damaged = json.loads(packet)
            damaged["methodology"]["defaults"] = None
            if legacy:
                damaged.update(harness=None, workerPrompt=None)
            path.write_text(json.dumps(damaged), encoding="utf-8")
            result = self.drain()
            self.assertEqual(self.calls("recover.t1"), 0)
            self.assertIn("defaults source", self.tasks(result)["recover.t1"]["reason"])
        path.write_bytes(packet)
        self.assertEqual(self.tasks(self.drain())["recover.t1"]["result"], "accepted")

    def test_harness_no_defaults_source_refuses_capture(self):
        # Prediction: a release missing its defaults cannot turn itself into a silent legacy install or capture work.
        release = self.harness_release()
        (release / "config/skills/_shared/runtime-principles.md").unlink()
        meta = self.queue["write_package"](self.anchor, "invalid", CHAIN[:1], base=self.base)
        result = self.cli("add", meta, code=1)
        self.assertIn("release verification failed", result["reason"])
        self.assertFalse((self.common / "devlyn-loops").exists())

    def test_harness_inspect_purity_and_incompatible_packet(self):
        # Prediction: inspect creates no lock/state, leaves captured originals intact and exposes incompatible packet versions.
        self.harness_release()
        before = self.tree_snapshot(self.root)
        self.cli("inspect", "--repo", self.anchor, "--json")
        self.assertEqual(before, self.tree_snapshot(self.root))
        instructions = self.anchor / "CLAUDE.md"
        instructions.write_text("Project instructions\n", encoding="utf-8")
        self.g("add", "CLAUDE.md")
        self.g("commit", "-qm", "project instructions")
        self.base = self.g("rev-parse", "HEAD")
        meta = self.queue["write_package"](self.anchor, "pure", CHAIN[:1], base=self.base)
        original = meta.read_bytes()
        self.cli("add", meta)
        meta.parent.mkdir(parents=True, exist_ok=True)
        meta.write_bytes(original)
        # git diff's automatic index refresh must also be disabled by the pure CLI reader.
        os.utime(instructions, ns=(instructions.stat().st_atime_ns, instructions.stat().st_mtime_ns + 10_000_000_000))
        before = self.tree_snapshot(self.root)
        self.cli("inspect", "--repo", self.anchor, "--json")
        self.assertEqual(before, self.tree_snapshot(self.root))
        self.cli("drain", "--repo", self.anchor, "--local-only", "--", str(self.root / "absent"), "{packet}")
        meta.parent.mkdir(parents=True, exist_ok=True)
        meta.write_bytes(original)
        packet = self.receipt_path("pure.t1").with_name("packet.json")
        data = json.loads(packet.read_bytes())
        data["schema_version"] = 99
        packet.write_text(json.dumps(data), encoding="utf-8")
        before = self.tree_snapshot(self.root)
        result = self.cli("inspect", "--repo", self.anchor, "--json")
        self.assertEqual(before, self.tree_snapshot(self.root))
        self.assertFalse(result["compatibility"]["compatible"])
        self.assertIn("incompatible task packet", result["compatibility"]["reasons"][0])

    def test_harness_projection_and_changed_worker_prompt(self):
        # Prediction: an exact marked Codex projection resolves to its release; altered prompt bytes refuse redispatch.
        release = self.harness_release()
        projection = self.root / "codex-cache"
        shutil.copytree(release / "native/codex/plugins/devlyn", projection)
        manifest = json.loads((release / "release.json").read_bytes())
        ref = {"package": "devlyn-cli", "version": manifest["version"], "digest": manifest["digest"]["value"], "root": str(release)}
        (projection / ".devlyn-harness-projection.json").write_text(json.dumps(
            {"schemaVersion": 1, "release": ref, "source": "native/codex/plugins/devlyn"}), encoding="utf-8")
        self.queue_py = projection / "skills/devlyn-ideate/scripts/queue.py"
        # An unreadable unexpected directory must not disappear from the projection inventory.
        hidden = projection / "unreadable"
        hidden.mkdir()
        (hidden / "unlisted").write_text("unverified", encoding="utf-8")
        original_scandir = os.scandir

        def scandir(path):
            if Path(path) == hidden:
                raise PermissionError("fixture unreadable projection directory")
            return original_scandir(path)

        with mock.patch("os.scandir", scandir):
            with self.assertRaisesRegex(OSError, "unreadable projection"):
                self.queue["shared"]("harness-store")["resolve"](projection / "skills")
        shutil.rmtree(hidden)
        self.plan("projected", CHAIN[:1], {"projected.t1": {"product": "greeting"}})
        self.cli("drain", "--repo", self.anchor, "--local-only", "--", str(self.root / "absent"), "{packet}")
        prompt = self.receipt_path("projected.t1").with_name("worker-prompt.md")
        original = prompt.read_bytes()
        prompt.write_text("changed", encoding="utf-8")
        result = self.drain()
        self.assertIn("worker prompt changed", self.tasks(result)["projected.t1"]["reason"])
        self.assertEqual(self.calls("projected.t1"), 0)
        prompt.write_bytes(original)
        (projection / "skills/devlyn-ideate/SKILL.md").write_text("changed", encoding="utf-8")
        self.assertIn("projection resource changed", self.drain(code=1)["reason"])


    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_harness_binding_retained_for_pending_delivery(self):
        # Prediction: accepted work with a pending PR retains the binding; merging and resuming settles without replay.
        self.harness_release()
        _, data = self.remote(pending=True)
        self.plan("deliver", CHAIN[:1], {"deliver.t1": {"product": "greeting"}}, delivery="auto")
        path = self.common / "devlyn-loops/harness.json"
        binding = path.read_bytes()
        self.assertEqual(self.tasks(self.drain(local=False))["deliver.t1"]["delivery"], "PENDING")
        self.cli("status", "--repo", self.anchor)
        self.assertEqual(path.read_bytes(), binding)
        self.assertEqual(self.merge_pr(data, 1).returncode, 0)
        self.assertEqual(self.tasks(self.drain(local=False))["deliver.t1"]["delivery"], "COMPLETE")
        self.assertEqual(self.calls("deliver.t1"), 1)
        self.assertFalse(path.exists())

    def test_harness_incompatible_binding_stays_inspectable(self):
        # Prediction: unknown binding versions stay visible, inspect remains pure and mutation refuses without dispatch.
        self.harness_release()
        self.plan("unknown", CHAIN[:1], {})
        path = self.common / "devlyn-loops/harness.json"
        binding = json.loads(path.read_bytes())
        binding["schemaVersion"] = 9
        path.write_text(json.dumps(binding), encoding="utf-8")
        before = self.tree_snapshot(self.root)
        result = self.cli("inspect", "--repo", self.anchor, "--json")
        self.assertEqual(result["binding"], binding)
        self.assertFalse(result["compatibility"]["compatible"])
        self.assertEqual(before, self.tree_snapshot(self.root))
        self.assertIn("incompatible queue binding", self.drain(code=1)["reason"])


    def test_harness_standalone_ignores_unrelated_release_manifest(self):
        # Prediction: a generic ancestor release.json does not turn a vendored skill into a release entry point.
        self.skill_copy(self.root / "standalone-skills", "fixture")
        (self.root / "release.json").write_text('{"package":"another-tool"}', encoding="utf-8")
        self.plan("standalone", CHAIN[:1], {})
        result = self.cli("inspect", "--repo", self.anchor, "--json")
        self.assertIsNone(result["binding"])
        self.assertTrue(result["compatibility"]["compatible"])
        self.assertTrue(result["compatibility"]["legacy"])
        self.assertEqual(result["counts"]["pending"], 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-root", type=Path, default=PACKAGE_ROOT)
    args, rest = parser.parse_known_args()
    LoopFixture.skills = args.package_root.resolve() / "config" / "skills"
    result = unittest.main(argv=[sys.argv[0], *rest], exit=False, verbosity=2).result
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
