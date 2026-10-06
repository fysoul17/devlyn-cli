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
import subprocess
import sys
import tempfile
import threading
import time
import unittest

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
source = commit(config["products"][behavior["product"]], "implement " + packet["task"])
submission = {"schema_version": 1, "task": packet["task"], "source_sha": source, "summary": "done (informational)",
              "assumptions": ["fixture assumption for " + packet["task"]]}
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
# the removal of one.
CRASH = ("import os, pathlib, runpy, sys\n"
         "step, name = sys.argv[1:3]\n"
         "sys.argv = sys.argv[3:]\n"
         "def crashing(real):\n"
         "    def call(path, *args, **kwargs):\n"
         "        if pathlib.Path(args[0] if step == 'replace' else path).name == name:\n"
         "            os._exit(9)\n"
         "        return real(path, *args, **kwargs)\n"
         "    return call\n"
         "if step == 'replace':\n    os.replace = crashing(os.replace)\n"
         "else:\n    pathlib.Path.unlink = crashing(pathlib.Path.unlink)\n"
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
        self.queue_py = self.skills / "devlyn-ideate/scripts/queue.py"
        self.helper = self.skills / "_shared/task-complete.py"
        self.platform = self.skills / "_shared/platform-support.py"
        self.queue = runpy.run_path(str(self.queue_py))
        self.env = {key: value for key, value in os.environ.items() if key not in {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR"}}
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

        # Conflicting terminal receipts for one identity stop selection with both receipts named.
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
        blocked = self.cli("status", "--repo", self.anchor, code=1)
        self.assertIn("conflicting receipts for inv.t1", blocked["reason"])
        self.assertIn(allocated["receipt"], blocked["reason"])
        result = self.drain(code=1)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("conflicting receipts for inv.t1", result["reason"])

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
        blocked = self.cli("drain", "--repo", self.anchor, "--local-only", "--", str(self.root / "no executor"), "{packet}", code=1)
        self.assertIn("executor could not start", blocked["reason"])
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
        return [Path(entry["path"]).name for entry in json.loads(self.receipt_path(identity).with_name("packet.json").read_text(encoding="utf-8"))["methodology"]]

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
        meta = self.queue["write_package"](self.anchor, "au", [CHAIN[0]], delivery="auto", base=self.base,
                                           intent="User asked: unrelated legacy intent.")
        self.behaviors.update({"au.t1": {"product": "greeting"}})
        self.cli("add", meta, "--materialize", 4)
        self.plan("lo", [("t1", [], "Notes", [NOTES_CHECK])], {"lo.t1": {"product": "notes"}})
        result = self.drain()
        tasks = self.tasks(result)
        self.assertEqual([(identity, task["result"], task["delivery"]) for identity, task in tasks.items()],
                         [("au.t1", "accepted", "LOCAL_ONLY"), ("lo.t1", "accepted", "LOCAL_ONLY")])
        self.assertEqual((result["status"], self.receipt("au.t1")["baseline"]), ("DRAINED", self.base))
        self.assertIn("- Bring into main: git merge --ff devlyn/au/t1\n", self.report("au"))

    def test_frontier_is_the_latest_accepted_source(self):
        tasks = [CHAIN[0], ("t2", [], "Notes", [NOTES_CHECK]), ("t3", ["t1"], "Greeting app", [APP_CHECK]), ("t4", ["t2", "t3"], "Notes again", [NOTES_CHECK])]
        self.plan("fr", tasks, {"fr.t1": {"product": "greeting"}, "fr.t2": {"product": "notes"}, "fr.t3": {"product": "app"}, "fr.t4": {"product": "notes"}})
        self.drain()
        t1, t2, t3, t4 = (self.receipt(f"fr.{task}") for task in ("t1", "t2", "t3", "t4"))
        # Each later task starts from the latest accepted source, not the first.
        self.assertEqual((t2["baseline"], t3["baseline"], t4["baseline"]), (t1["source_sha"], t2["source_sha"], t3["source_sha"]))
        # A receipt whose attached terminal commit lacks its result's mark stops selection.
        receipt = self.receipt_path("fr.t1")
        receipt.write_text(json.dumps(dict(json.loads(receipt.read_text(encoding="utf-8")), product="FAILED")), encoding="utf-8")
        self.assertIn(f"fr.t1: terminal commit {t1['publish_sha']} does not carry its failed mark", self.cli("status", "--repo", self.anchor, code=1)["reason"])

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
        resumed = next(self.drain_until("a.t1: waiting"))
        self.config.with_name("release").write_text("go", encoding="utf-8")
        out, _ = resumed.communicate(timeout=120)
        self.assertEqual((self.tasks(json.loads(out))["a.t1"]["result"], self.calls("a.t1")), ("accepted", 1))

    def test_captured_contracts_stay_immutable(self):
        # Prediction (C, read captured bytes): with a.t1 left active with committed inputs and a packet, edited copies of the
        # loop's package in the checkout and a deleted one change nothing: status names no inputs change, the drain runs a.t1
        # and a.t2 from the capture to acceptance with their packets binding the captured bytes, and it reports the edited
        # copies as kept. Before: an edited or deleted checkout copy failed the active task as inputs-changed and blocked
        # its dependent.
        self.plan("a", CHAIN, {"a.t1": {"product": "greeting"}, "a.t2": {"product": "app"}})
        blocked = self.cli("drain", "--repo", self.anchor, "--local-only", "--", str(self.root / "no executor"), "{packet}", code=1)
        self.assertIn("executor could not start", blocked["reason"])
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

    def test_devlyn_ignore_is_checked_before_allocation(self):
        (self.anchor / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
        self.g("commit", "-qam", "base without the .devlyn/ rule")
        self.plan("ig", [("t1", [], "Notes", [NOTES_CHECK])], {"ig.t1": {"product": "notes"}}, base=self.g("rev-parse", "HEAD"))
        blocked = self.drain(code=1)
        self.assertIn(".devlyn/ is not ignored", blocked["reason"])
        self.assertIn(".gitignore", blocked["reason"])
        self.assertIn("info", blocked["reason"])
        self.assertIn("exclude", blocked["reason"])
        self.assertFalse(self.receipt_path("ig.t1").exists())
        (self.common / "info").mkdir(exist_ok=True)
        with (self.common / "info" / "exclude").open("a", encoding="utf-8") as exclude:
            exclude.write(".devlyn/\n")
        self.assertEqual(self.tasks(self.drain())["ig.t1"]["result"], "accepted")

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
        blocked = self.cli("drain", "--repo", self.anchor, "--local-only", "--", str(self.root / "no executor"), "{packet}", code=1)
        self.assertIn("executor could not start", blocked["reason"])
        (self.anchor / "CLAUDE.md").write_bytes(b"# Installed v3\n")
        self.g("commit", "-qam", "install v3")
        self.plan("bb", [("t1", [], "Greeting", [GREET_CHECK])], {"bb.t1": {"product": "greeting"}})
        tasks = self.tasks(self.drain())
        start = self.receipt("aa.t1")["source_sha"]
        reason = (f"the installed instructions (CLAUDE.md) in this checkout differ from those in its start commit {start}, so it would run "
                  "without them; restore them to their bytes at that commit, or plan the remaining work as a new loop")
        self.assertEqual((tasks["aa.t1"]["result"], tasks["aa.t2"].get("reason"), self.calls("aa.t2"), tasks["bb.t1"]["result"]), ("accepted", reason, 0, "accepted"))
        methodology = json.loads(self.receipt_path("aa.t1").with_name("packet.json").read_text(encoding="utf-8"))["methodology"]
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
        for _ in range(2):
            self.assertIn(f"lacks the delivered prerequisite merge {merge}", self.drain(local=False, code=1)["reason"])
            self.assertFalse(self.receipt_path("inv.t2").exists())
        # A receipt allocated on that base by another route is checked again before execution.
        self.run_ok([sys.executable, str(self.helper), "allocate", "--repo", str(self.anchor), "--task", "inv.t2", "--branch", "devlyn/inv/t2",
                     "--repository", "test/project", "--base", "main", "--worktree", str(self.root / "repo.devlyn/inv/t2")])
        self.assertIn(f"lacks the delivered prerequisite merge {merge}", self.drain(local=False, code=1)["reason"])
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

    def pull(self, bare):
        return subprocess.run(["git", "-C", str(self.anchor), "pull", "--ff-only", str(bare), "main"], env=self.env, capture_output=True,
                              text=True, encoding="utf-8")

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
        # inputs commit; a pull fast-forwards the anchor with a clean tree; the legacy queue stays as it was, CRLF line
        # endings and the duplicate row above the replaced one included. Before the drain, before the pull, after it and in
        # a fresh clone of the remote, status shows the duplicate pending and the loop's rows in the replaced row's place,
        # and materializing that line again is refused, so the intent never runs twice. Before: the plan rewrote the legacy
        # queue, and once the drain had synced the anchor its record stopped replacing the row until the pull.
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
        pulled = self.pull(bare)
        self.assertEqual(pulled.returncode, 0, pulled.stdout + pulled.stderr)
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
        merged = self.bring_in("inv", bare)
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
        # so `git pull --ff-only` fast-forwards the anchor to the remote base with a clean tree and both rows [x]. Before:
        # add's commit stayed on the anchor and no squash merge descends from it, so the pull could not fast-forward.
        bare, data = self.remote(pending=False, squash=True)
        self.plan("sq", CHAIN, {"sq.t1": {"product": "greeting"}, "sq.t2": {"product": "app"}}, delivery="auto")
        tasks = self.tasks(self.drain(local=False))
        self.assertEqual({identity: task["delivery"] for identity, task in tasks.items()}, {"sq.t1": "COMPLETE", "sq.t2": "COMPLETE"})
        main = self.run_ok(["git", "--git-dir", str(bare), "rev-parse", "main"])
        self.assertEqual(self.run_ok(["git", "--git-dir", str(bare), "rev-list", "--parents", "-n", "1", main]).split()[1:],
                         [self.receipt("sq.t1")["merge"]["mergeCommit"]["oid"]])  # a squash: one parent
        pulled = self.pull(bare)
        self.assertEqual(pulled.returncode, 0, pulled.stdout + pulled.stderr)
        self.assertEqual((self.g("rev-parse", "HEAD"), self.g("status", "--porcelain", "--untracked-files=all")), (main, ""))
        self.assertEqual({identity: row["mark"] for identity, row in self.rows("HEAD").items()}, {"sq.t1": "x", "sq.t2": "x"})
        report = (self.common / "devlyn-loops/sq/drain-report.md").read_text(encoding="utf-8")
        self.assertIn("- Bring into main: git merge --ff origin/main\n", report)

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

    def bring_in(self, loop, bare=None):
        """Run the loop's drain report `Bring into` command in the anchor, origin's URL resolving to the bare remote."""
        command = shlex.split(next(line for line in self.report(loop).splitlines() if line.startswith("- Bring into ")).split(": ", 1)[1].split(" (")[0])
        self.assertEqual(command[0], "git")
        return subprocess.run(["git", *(["-c", f"url.{bare}.insteadOf=https://github.com/test/project.git"] if bare else []), "-C", str(self.anchor),
                               *command[1:]], env=self.env, capture_output=True, text=True, encoding="utf-8")

    def apply_one_drains_reports(self, order):
        # Prediction (B): one drain delivers an auto loop and accepts a local loop, and both reports are written before
        # either command runs; the auto report's `git merge --ff origin/main` and the local report's `git merge --ff`
        # then apply in either order with every row [x] and a clean tree. Before: the auto report was chosen when it was
        # written, `git pull --ff-only origin main`, which aborts once the local merge has moved main.
        bare, _ = self.remote(pending=False)
        self.plan("au", [CHAIN[0]], {"au.t1": {"product": "greeting"}}, delivery="auto")
        self.plan("lo", [("t1", [], "Notes", [NOTES_CHECK])], {"lo.t1": {"product": "notes"}})
        tasks = self.tasks(self.drain(local=False))
        self.assertEqual({identity: task["delivery"] for identity, task in tasks.items()}, {"au.t1": "COMPLETE", "lo.t1": "LOCAL_ONLY"})
        self.assertIn("- Bring into main: git merge --ff origin/main\n", self.report("au"))
        for loop in order:
            merged = self.bring_in(loop, bare if loop == "au" else None)
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
                pulled = self.bring_in("lt", bare)
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
        bare, data = self.remote(pending=True)
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
        merged = self.bring_in("aw", bare)
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
        stopped = self.cli("drain", "--repo", self.anchor, "--", str(self.root / "no executor"), "{packet}", code=1)
        self.assertIn("executor could not start", stopped["reason"])
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
        stopped = self.cli("drain", "--repo", self.anchor, "--", str(self.root / "no executor"), "{packet}", code=1)
        self.assertIn("executor could not start", stopped["reason"])
        linked = self.root / "linked"
        self.g("worktree", "add", "-q", "-b", "side", str(linked))
        self.assertEqual((self.tasks(self.drain(local=False, repo=linked))["au.t1"]["delivery"], self.calls("au.t1")), ("COMPLETE", 1))

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
        # Prediction (H1): a delivery task-complete refuses leaves its task waiting with the refusal and its resume command,
        # and the drain goes on: dv.t1, whose base_ref is not the repository's default branch, is accepted, then waits "base/
        # default branch changed" while the local loop lo is accepted, and the drain ends WAITING; once a person closes
        # pm.t1's PR, the next drain leaves pm.t1 waiting "PR is closed without merge" and accepts the local loop lp; no task
        # runs twice. Before: each refusal ended the whole drain BLOCKED, and since unsettled receipts resume first, every
        # later drain stopped at the same receipt before any independent loop ran.
        bare, data = self.remote(pending=True)
        self.run_ok(["git", "-C", str(self.anchor), "push", "-q", str(bare), "main:develop"])
        self.plan("pm", [CHAIN[0]], {"pm.t1": {"product": "greeting"}}, delivery="pr")
        meta = self.queue["write_package"](self.anchor, "dv", [("t1", [], "Todo", [TODO_CHECK])], delivery="auto", base=self.base)
        meta.write_text(meta.read_text(encoding="utf-8").replace('"base_ref": "main"', '"base_ref": "develop"'), encoding="utf-8")
        self.behaviors["dv.t1"] = {"product": "todo"}
        self.cli("add", meta)
        self.plan("lo", [("t1", [], "Notes", [NOTES_CHECK])], {"lo.t1": {"product": "notes"}})
        refused = "delivery blocked: task-complete complete: "
        result = self.drain(local=False)
        tasks = self.tasks(result)
        self.assertEqual((result["status"], {identity: (task["result"], task.get("delivery"), task.get("reason")) for identity, task in tasks.items()}),
                         ("WAITING", {"pm.t1": ("accepted", "PR", None), "lo.t1": ("accepted", "LOCAL_ONLY", None),
                                      "dv.t1": ("accepted", None, refused + "base/default branch changed; retain resources")}))
        self.assertIn("task-complete.py complete --receipt", tasks["dv.t1"]["resume"])
        server = json.loads(data.read_text(encoding="utf-8"))
        server["prs"][0]["state"] = "CLOSED"
        data.write_text(json.dumps(server), encoding="utf-8")
        self.plan("lp", [("t1", [], "Greeting", [GREET_CHECK])], {"lp.t1": {"product": "greeting"}})
        tasks = self.tasks(self.drain(local=False))
        self.assertEqual({identity: (task["result"], task.get("reason")) for identity, task in tasks.items()}, {
            "pm.t1": ("accepted", refused + "PR is closed without merge; retain task"), "lo.t1": ("accepted", None),
            "dv.t1": ("accepted", refused + "base/default branch changed; retain resources"), "lp.t1": ("accepted", None)})
        self.assertEqual([self.calls(identity) for identity in ("pm.t1", "dv.t1", "lo.t1", "lp.t1")], [1, 1, 1, 1])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-root", type=Path, default=PACKAGE_ROOT)
    args, rest = parser.parse_known_args()
    LoopFixture.skills = args.package_root.resolve() / "config" / "skills"
    result = unittest.main(argv=[sys.argv[0], *rest], exit=False, verbosity=2).result
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
