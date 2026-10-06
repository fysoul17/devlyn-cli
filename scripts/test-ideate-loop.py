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
# Runs the driver as from a terminal, where Ctrl-C raises KeyboardInterrupt: a runner started in the background passes
# SIGINT on ignored, and Python then installs no handler.
INTERRUPTIBLE = ("import runpy, signal, sys\n"
                 "signal.signal(signal.SIGINT, signal.default_int_handler)\n"
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

    def queue_at(self, rev):
        return self.run_ok(["git", "-C", str(self.anchor), "show", f"{rev}:docs/specs/queue.md"])

    def rows(self, rev):
        return {row["identity"]: row for row in self.queue["parse_queue"](self.queue_at(rev).encode("utf-8")) if row["identity"]}

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
        expected = (self.base_queue.decode("utf-8") + "\n" + t1_row + "\n\n" + self.queue["row_line"]("inv.t2", "Greeting app [cli]") + "\n\n"
                    + self.queue["TRAILER"].decode("utf-8"))
        self.assertEqual(self.queue_at(inputs), expected)
        self.assertEqual(self.run_ok([sys.executable, "app.py", "Ada"], cwd=second["worktree"]), "Hello, Ada!")
        report = (self.common / "devlyn-loops/inv/drain-report.md").read_text(encoding="utf-8")
        self.assertIn("Whole-loop acceptance: ACCEPTED", report)
        self.assertIn("fixture assumption for inv.t2", report)
        status = self.cli("status", "--repo", self.anchor)
        self.assertEqual((status["counts"]["accepted"], status["counts"]["legacy_pending"], status["next"]), (2, 1, None))
        self.assertIn("legacy row 4 needs planning: unrelated legacy intent", status["blockers"])
        self.assertEqual((self.anchor / "docs/specs/queue.md").read_bytes().count(b"- [ ] inv.t"), 2)

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

    def merge_ff(self, rev):
        return subprocess.run(["git", "-C", str(self.anchor), "merge", "--ff-only", rev], env=self.env, capture_output=True,
                              text=True, encoding="utf-8")

    def added(self, loop):
        return json.loads((self.common / f"devlyn-loops/{loop}/added.json").read_text(encoding="utf-8"))

    def test_local_loop_fast_forwards_the_anchor_branch(self):
        # The loop starts from add's commit, so the final frontier fast-forwards the branch it was added on (e2e D1).
        self.plan("inv", CHAIN, {"inv.t1": {"product": "greeting"}, "inv.t2": {"product": "app"}})
        self.drain()
        first, final = self.receipt("inv.t1"), self.receipt("inv.t2")
        merged = self.merge_ff(final["branch"])
        self.assertEqual(merged.returncode, 0, merged.stdout + merged.stderr)
        self.assertEqual((self.g("rev-parse", "HEAD"), self.g("status", "--porcelain", "--untracked-files=all")), (final["publish_sha"], ""))
        self.assertEqual({identity: row["mark"] for identity, row in self.rows("HEAD").items()}, {"inv.t1": "x", "inv.t2": "x"})
        # Scoped inputs are what a base lacks: nothing for the first task, the predecessor's [x] row for its dependent.
        added = self.added("inv")["commit"]
        self.assertEqual((first["baseline"], first["acceptance"]["inputs_sha"]), (added, added))
        self.assertEqual(self.g("diff", "--name-only", final["baseline"], final["acceptance"]["inputs_sha"]), "docs/specs/queue.md")
        report = (self.common / "devlyn-loops/inv/drain-report.md").read_text(encoding="utf-8")
        self.assertIn(f"- Bring into main: git merge --ff-only {final['branch']} (a fast-forward)", report)

    def test_two_local_loops_bring_in_as_reported(self):
        # Prediction: add commits a blank line between the rows it appends and the trailer line, so a second local loop's
        # rows follow an unchanged line; following both reports, the later loop fast-forwards and the earlier one merges
        # without a conflict, every row [x]. Before: the second add's rows touched the first loop's last row, so the
        # reported merge conflicted in docs/specs/queue.md.
        self.plan("aa", [CHAIN[0]], {"aa.t1": {"product": "greeting"}})
        self.plan("bb", [("t1", [], "Notes", [NOTES_CHECK])], {"bb.t1": {"product": "notes"}})
        self.drain()
        for loop, command in (("bb", "merge --ff-only devlyn/bb/t1"), ("aa", "merge devlyn/aa/t1")):
            self.assertIn(f"- Bring into main: git {command} (", (self.common / f"devlyn-loops/{loop}/drain-report.md").read_text(encoding="utf-8"))
            self.g(*command.split())
        self.assertEqual({identity: row["mark"] for identity, row in self.rows("HEAD").items()}, {"aa.t1": "x", "bb.t1": "x"})

    @unittest.skipIf(os.name == "nt", "the commit hook, fake gh and transport wrappers are POSIX shell scripts")
    def test_newline_hooks_accept_every_queue_the_loop_writes(self):
        # Prediction (R1): a pre-commit hook running end-of-file-fixer's check (no file ending in more than one newline)
        # and a no-two-consecutive-blank-lines check accepts the queue of a local add and of a local --materialize, so both
        # commit, and the checks also accept a carrier's inputs queue; each queue ends with the trailer line and one
        # newline. Before: the hook refused the first add, whose queue ended in a blank line.
        self.remote(pending=False)
        checks = self.root / "newline hooks.py"
        checks.write_text(NEWLINE_HOOKS, encoding="utf-8")
        hook = self.common / "hooks" / "pre-commit"
        hook.parent.mkdir(exist_ok=True)
        hook.write_text("#!/bin/sh\ntest -n \"$(git diff --cached --name-only -- docs/specs/queue.md)\" || exit 0\n"
                        f"git show :docs/specs/queue.md | \"{sys.executable}\" \"{checks}\"\n", encoding="utf-8")
        hook.chmod(0o755)
        self.plan("aa", [("t1", [], "Notes", [NOTES_CHECK])], {"aa.t1": {"product": "notes"}})
        meta = self.queue["write_package"](self.anchor, "bb", [("t1", [], "Todo", [TODO_CHECK])], base=self.base,
                                           intent="User asked: unrelated legacy intent.")
        self.behaviors.update({"bb.t1": {"product": "todo"}})
        self.cli("add", meta, "--materialize", 4)
        self.plan("cc", [CHAIN[0]], {"cc.t1": {"product": "greeting"}}, delivery="auto")
        tasks = self.tasks(self.drain(local=False))
        self.assertEqual({identity: task["result"] for identity, task in tasks.items()}, {"aa.t1": "accepted", "bb.t1": "accepted", "cc.t1": "accepted"})
        for name, rev in (("add", "HEAD~1"), ("materialize", "HEAD"), ("carrier", self.receipt("cc.t1")["acceptance"]["inputs_sha"])):
            data = subprocess.run(["git", "-C", str(self.anchor), "cat-file", "blob", rev + ":docs/specs/queue.md"], env=self.env,
                                  capture_output=True, check=True).stdout
            checked = subprocess.run([sys.executable, str(checks)], input=data, capture_output=True)
            self.assertEqual((name, checked.returncode, data.endswith(b"\n" + self.queue["TRAILER"] + b"\n")), (name, 0, True), checked.stderr)

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
        # CLAUDE.md committed with CRLF line endings under core.autocrlf=true lets add commit a loop whose task is accepted
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

    def test_add_commits_only_the_package_and_queue(self):
        # add commits exactly the package and the queue; unrelated staged and unstaged changes stay as they were.
        (self.anchor / "staged.txt").write_text("staged\n", encoding="utf-8")
        self.g("add", "staged.txt")
        with (self.anchor / ".gitignore").open("a", encoding="utf-8") as ignore:
            ignore.write("# unstaged edit\n")
        self.plan("inv", CHAIN, {})
        self.assertEqual(self.g("log", "-1", "--format=%s"), "devlyn loop: add inv")
        self.assertEqual(self.g("rev-parse", "HEAD^"), self.base)
        package = ["docs/specs/inv/meta.md"] + [f"docs/specs/inv/{task}/{name}" for task in ("t1", "t2") for name in ("spec.expected.json", "spec.md")]
        self.assertEqual(self.g("diff", "--name-only", self.base, "HEAD").splitlines(), package + ["docs/specs/queue.md"])
        self.assertEqual((self.g("diff", "--cached", "--name-only"), self.g("diff", "--name-only")), ("staged.txt", ".gitignore"))
        self.assertEqual(self.added("inv"), {"schema_version": 1, "loop_id": "inv", "branch": "main", "commit": self.g("rev-parse", "HEAD")})

    def hooked_add(self, meta, event, script):
        """Run add in its own process group with a commit hook whose script signals that group."""
        hook = self.common / "hooks" / event
        hook.parent.mkdir(exist_ok=True)
        hook.write_text("#!/bin/sh\n" + script + "\n", encoding="utf-8")
        hook.chmod(0o755)
        try:
            return subprocess.run([sys.executable, "-c", INTERRUPTIBLE, str(self.queue_py), "add", str(meta)], cwd=self.root, env=self.env,
                                  capture_output=True, text=True, encoding="utf-8", start_new_session=True)
        finally:
            hook.unlink()

    @unittest.skipIf(os.name == "nt", "a commit hook signals the add's process group")
    def test_add_interrupted_inside_its_commit_restores_the_queue_and_index_entries(self):
        # Prediction (L1): Ctrl-C reaching add's process group while its pre-commit hook runs leaves HEAD, the queue bytes
        # and the exact index entries of the package and queue paths, a partly staged package file included, as they were,
        # with no intent or add record left; a retried add then commits the package. Before: the interrupt skipped the
        # rollback, so the rows stayed appended and the package staged.
        meta = self.queue["write_package"](self.anchor, "inv", CHAIN)
        spec = self.anchor / "docs/specs/inv/t1/spec.md"
        final = spec.read_bytes()
        spec.write_bytes(final.replace(b"Fixture.", b"Draft."))
        self.g("add", "docs/specs/inv/t1/spec.md")
        spec.write_bytes(final)
        paths = ["docs/specs/inv", "docs/specs/queue.md"]

        def state():
            return (self.g("rev-parse", "HEAD"), (self.anchor / "docs/specs/queue.md").read_bytes(), self.g("ls-files", "-s", "--", *paths),
                    sorted(path.name for path in (self.common / "devlyn-loops").glob("*/*.json")))
        before = state()
        interrupted = self.hooked_add(meta, "pre-commit", "kill -INT 0\nexit 1")
        self.assertIn("KeyboardInterrupt", interrupted.stderr, f"exit {interrupted.returncode}: {interrupted.stdout}")
        self.assertEqual(state(), before)
        self.assertIn("Draft.", self.g("show", ":docs/specs/inv/t1/spec.md"))
        self.cli("add", meta)
        self.assertEqual((self.g("log", "-1", "--format=%s"), self.g("show", "HEAD:docs/specs/inv/t1/spec.md")),
                         ("devlyn loop: add inv", final.decode("utf-8").strip()))

    @unittest.skipIf(os.name == "nt", "a commit hook signals the add's process group")
    def test_add_killed_after_its_commit_is_completed_by_the_next_status(self):
        # Prediction (L2): add killed after its commit lands, before added.json, leaves its intent record; the next status
        # records that add commit and removes the intent record, and the drain then runs the loop to acceptance from it.
        # Before: no intent record existed, so the drain blocked on the missing add record.
        meta = self.queue["write_package"](self.anchor, "inv", CHAIN)
        self.behaviors.update({"inv.t1": {"product": "greeting"}, "inv.t2": {"product": "app"}})
        crashed = self.hooked_add(meta, "post-commit", "kill -KILL 0")
        self.assertEqual(crashed.returncode, -signal.SIGKILL)
        commit = self.g("rev-parse", "HEAD")
        self.assertEqual(self.g("log", "-1", "--format=%s"), "devlyn loop: add inv")
        records = self.common / "devlyn-loops/inv"
        self.assertEqual(sorted(path.name for path in records.glob("*.json")), ["adding.json"])
        self.assertEqual(self.cli("status", "--repo", self.anchor)["next"], "inv.t1")
        self.assertEqual((self.added("inv")["commit"], (records / "adding.json").exists()), (commit, False))
        tasks = self.tasks(self.drain())
        self.assertEqual({identity: task["result"] for identity, task in tasks.items()}, {"inv.t1": "accepted", "inv.t2": "accepted"})
        self.assertEqual(self.receipt("inv.t1")["baseline"], commit)

    @unittest.skipIf(os.name == "nt", "a commit hook signals the add's process group")
    def test_a_retried_add_reports_the_commit_a_crash_or_interrupt_left(self):
        # Prediction: add killed, or interrupted by Ctrl-C, after its commit landed is retried; the retry reports that
        # commit as ADDED, with the add recorded and nothing left uncommitted. Before: the retry was refused as "task
        # identity already queued", telling the host to plan the same loop again under new IDs.
        for loop, script, stopped in (("ka", "kill -KILL 0", lambda r: r.returncode == -signal.SIGKILL),
                                      ("ki", "kill -INT 0; sleep 1", lambda r: "KeyboardInterrupt" in r.stderr)):
            with self.subTest(loop=loop):
                meta = self.queue["write_package"](self.anchor, loop, [CHAIN[0]])
                result = self.hooked_add(meta, "post-commit", script)
                self.assertTrue(stopped(result), f"exit {result.returncode}: {result.stdout}{result.stderr}")
                commit = self.g("rev-parse", "HEAD")
                self.assertEqual(self.g("log", "-1", "--format=%s"), f"devlyn loop: add {loop}")
                retried = self.cli("add", meta)
                self.assertEqual((retried["status"], retried["commit"], retried["tasks"]), ("ADDED", commit, [f"{loop}.t1"]))
                self.assertEqual((self.added(loop)["commit"], self.g("status", "--porcelain", "--untracked-files=all")), (commit, ""))

    @unittest.skipIf(os.name == "nt" or not shutil.which("ssh-keygen"), "a commit hook signals the add's process group; ssh-keygen signs")
    def test_recovery_completes_a_signed_add_commit(self):
        # Prediction: with SSH-signed commits and log.showSignature, add killed, or interrupted by Ctrl-C, after its commit
        # landed is completed: status records that commit, and the index, queue and package stay as committed. Before:
        # `git show` printed the signature ahead of the parent, tree and subject, so recovery rolled the add back while its
        # exact commit stayed on the branch (package staged as deleted, rows removed) and recorded no add.
        key = self.root / "signing key"
        self.run_ok(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "fixture", "-f", str(key)])
        signers = self.root / "allowed signers"
        signers.write_text("fixture@example.invalid " + key.with_name(key.name + ".pub").read_text(encoding="utf-8"), encoding="utf-8")
        for name, value in (("user.signingKey", key), ("gpg.format", "ssh"), ("gpg.ssh.allowedSignersFile", signers),
                            ("commit.gpgSign", "true"), ("log.showSignature", "true")):
            self.g("config", name, str(value))
        for loop, script in (("sk", "kill -KILL 0"), ("si", "kill -INT 0; sleep 1")):
            with self.subTest(loop=loop):
                meta = self.queue["write_package"](self.anchor, loop, [CHAIN[0]])
                self.hooked_add(meta, "post-commit", script)
                commit = self.g("rev-parse", "HEAD")
                self.assertEqual(self.g("log", "-1", "--no-show-signature", "--format=%s"), f"devlyn loop: add {loop}")
                self.assertIn('Good "git" signature', self.g("show", "-s", "--format=%s", commit))
                self.cli("status", "--repo", self.anchor)
                self.assertEqual((self.added(loop)["commit"], self.g("status", "--porcelain", "--untracked-files=all")), (commit, ""))

    def test_a_local_only_drain_waits_the_auto_loop_it_cannot_start(self):
        # Prediction (R4): an auto loop queued ahead of a local loop (it materializes the legacy row above the local loop's
        # rows) and drained with --local-only waits with its reason and no executor call, while the local loop is accepted
        # and the drain ends WAITING. Before: allocating the auto loop's first task raised, so the drain ended BLOCKED and the
        # local loop never ran.
        meta = self.queue["write_package"](self.anchor, "au", [CHAIN[0]], delivery="auto", base=self.base,
                                           intent="User asked: unrelated legacy intent.")
        self.cli("add", meta, "--materialize", 4)
        self.plan("lo", [("t1", [], "Notes", [NOTES_CHECK])], {"lo.t1": {"product": "notes"}})
        result = self.drain()
        tasks = self.tasks(result)
        self.assertEqual(list(tasks), ["au.t1", "lo.t1"])
        self.assertEqual((result["status"], tasks["lo.t1"]["result"], tasks["au.t1"]["result"], self.calls("au.t1")), ("WAITING", "accepted", "pending", 0))
        self.assertEqual(tasks["au.t1"]["reason"], "au was added for auto delivery, so no add commit carries its package for a local drain; "
                         "drain it without --local-only")

    def test_frontier_is_the_latest_accepted_source_and_divergence_is_refused(self):
        tasks = [CHAIN[0], ("t2", [], "Notes", [NOTES_CHECK]), ("t3", ["t1"], "Greeting app", [APP_CHECK]), ("t4", ["t2", "t3"], "Notes again", [NOTES_CHECK])]
        self.plan("fr", tasks, {"fr.t1": {"product": "greeting"}, "fr.t2": {"product": "notes"}, "fr.t3": {"product": "app"}, "fr.t4": {"product": "notes"}})
        rows = {task: self.queue["row_line"](f"fr.{task}", title) for task, _, title, _ in tasks}
        queue = self.anchor / "docs/specs/queue.md"
        queue.write_bytes(queue.read_bytes().replace((rows["t4"] + "\n").encode(), b""))
        self.drain()
        t1, t2, t3 = (self.receipt(f"fr.{task}") for task in ("t1", "t2", "t3"))
        # Each later task starts from the latest accepted source, not the first.
        self.assertEqual((t2["baseline"], t3["baseline"]), (t1["source_sha"], t2["source_sha"]))
        # Reordered rows put the frontier at fr.t2, which lacks fr.t3's source: a divergent prerequisite is refused.
        queue.write_bytes(self.base_queue + "".join(rows[task] + "\n" for task in ("t3", "t1", "t2", "t4")).encode())
        blocked = self.drain(code=1)
        self.assertIn(f"fr.t4: prerequisite source {t3['source_sha']} is not in the accepted frontier {t2['source_sha']}; plan an integration task",
                      blocked["reason"])
        self.assertEqual(self.calls("fr.t4"), 0)
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
        self.assertEqual(self.queue_at(dd2["acceptance"]["inputs_sha"]), self.queue_at(dd2["baseline"]).replace(
            self.queue["row_line"]("dd.t1", "Greeting interface 인사"), failed_row).replace(self.queue["row_line"]("dd.t3", "Greeting app"), blocked_row))
        reports = {loop: (self.common / f"devlyn-loops/{loop}/drain-report.md").read_text(encoding="utf-8") for loop in ("dd", "ee")}
        self.assertIn("Whole-loop acceptance: INCOMPLETE — ee.t2 failed", reports["ee"])
        self.assertIn("blocked-prerequisite:dd.t1", reports["dd"])
        # A hand-written mark that contradicts a receipt stops selection.
        queue_file = self.anchor / "docs/specs/queue.md"
        queue_file.write_bytes(queue_file.read_bytes().replace(b"- [ ] ee.t1", b"- [x] ee.t1").replace(b"- [ ] ee.t2", b"- [x] ee.t2"))
        self.assertIn("conflicting terminal state for ee.t2", self.cli("status", "--repo", self.anchor, code=1)["reason"])

    def test_a_detached_submission_fails_settles_and_the_drain_continues(self):
        self.plan("a", [CHAIN[0]], {"a.t1": {"product": "greeting", "detach": True}})
        self.plan("b", [("t1", [], "Notes", [NOTES_CHECK])], {"b.t1": {"product": "notes"}})
        tasks = self.tasks(self.drain())
        self.assertEqual({identity: task["result"] for identity, task in tasks.items()}, {"a.t1": "failed", "b.t1": "accepted"})
        self.assertIn("HEAD detached", tasks["a.t1"]["reason"])
        receipt = self.receipt("a.t1")
        self.assertEqual((receipt["delivery"], receipt["queue"]["commit"], self.calls("a.t1")), ("FAILED", receipt["publish_sha"], 1))
        self.assertEqual(self.rows(receipt["publish_sha"])["a.t1"]["mark"], "F")

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

    def test_changed_contract_of_an_active_task_fails_only_that_task(self):
        self.plan("a", CHAIN, {"a.t1": {"product": "greeting"}, "a.t2": {"product": "app"}})
        self.plan("b", [("t1", [], "Notes", [NOTES_CHECK])], {"b.t1": {"product": "notes"}})
        # An executor that cannot start leaves a.t1 active with committed inputs and a packet.
        blocked = self.cli("drain", "--repo", self.anchor, "--local-only", "--", str(self.root / "no executor"), "{packet}", code=1)
        self.assertIn("executor could not start", blocked["reason"])
        spec = self.anchor / "docs/specs/a/t1/spec.md"
        spec.write_text(spec.read_text(encoding="utf-8").replace(" works.", " works for every caller."), encoding="utf-8")
        self.assertIn("a.t1: inputs-changed", " ".join(self.cli("status", "--repo", self.anchor)["blockers"]))
        tasks = self.tasks(self.drain())
        self.assertEqual({identity: task["result"] for identity, task in tasks.items()}, {"a.t1": "failed", "a.t2": "blocked", "b.t1": "accepted"})
        self.assertTrue(tasks["a.t1"]["reason"].startswith("inputs-changed: docs/specs/a/t1/spec.md changed"))
        self.assertEqual((self.calls("a.t1"), self.calls("a.t2"), self.calls("b.t1")), (0, 0, 1))
        receipt = self.receipt("a.t1")
        self.assertTrue(Path(receipt["worktree"]).is_dir())
        self.assertIn("— inputs-changed:", self.rows(receipt["publish_sha"])["a.t1"]["rest"])

    def assert_invalid_inputs_stop_only_their_tasks(self, active, pending):
        """active(loop root) breaks active a.t1's committed contract and returns its path; pending(loop root) breaks
        loop c, queued while a.t1 is active, and returns the reasons c.t1 and c.t2 must report."""
        self.plan("a", CHAIN, {"a.t1": {"product": "greeting"}, "a.t2": {"product": "app"}})
        self.plan("b", [("t1", [], "Notes", [NOTES_CHECK])], {"b.t1": {"product": "notes"}})
        blocked = self.cli("drain", "--repo", self.anchor, "--local-only", "--", str(self.root / "no executor"), "{packet}", code=1)
        self.assertIn("executor could not start", blocked["reason"])  # a.t1 stays active with committed inputs.
        self.plan("c", CHAIN, {"c.t1": {"product": "greeting"}, "c.t2": {"product": "app"}})
        changed, reasons = active(self.anchor / "docs/specs/a"), pending(self.anchor / "docs/specs/c")
        self.assertIn(f"a.t1: inputs-changed: {changed} changed", " ".join(self.cli("status", "--repo", self.anchor)["blockers"]))
        tasks = self.tasks(self.drain())
        self.assertEqual({identity: task["result"] for identity, task in tasks.items()},
                         {"a.t1": "failed", "a.t2": "blocked", "b.t1": "accepted", "c.t1": "pending", "c.t2": "pending"})
        self.assertTrue(tasks["a.t1"]["reason"].startswith(f"inputs-changed: {changed} changed"))
        for identity, reason in reasons.items():  # validation errors name the file by its native path
            self.assertIn(reason.replace("/", os.sep), tasks[identity]["reason"])
        self.assertEqual([self.calls(identity) for identity in ("a.t1", "a.t2", "b.t1", "c.t1", "c.t2")], [0, 0, 1, 0, 0])
        self.assertIn("— inputs-changed:", self.rows(self.receipt("a.t1")["publish_sha"])["a.t1"]["rest"])

    def test_a_deleted_active_contract_and_a_malformed_pending_meta_stop_only_their_tasks(self):
        def active(root):
            (root / "t1/spec.md").unlink()
            return "docs/specs/a/t1/spec.md"

        def pending(root):
            (root / "meta.md").write_text("# Loop c\n", encoding="utf-8")
            return {"c.t1": "docs/specs/c/meta.md: missing or empty section(s)", "c.t2": "docs/specs/c/meta.md: missing or empty section(s)"}
        self.assert_invalid_inputs_stop_only_their_tasks(active, pending)

    def test_malformed_active_and_pending_acceptance_stop_only_their_tasks(self):
        def malform(root):
            (root / "t1/spec.expected.json").write_text("{", encoding="utf-8")
            return f"docs/specs/{root.name}/t1/spec.expected.json"
        self.assert_invalid_inputs_stop_only_their_tasks(
            malform, lambda root: {"c.t1": malform(root), "c.t2": "waiting for c.t1 (pending)"})

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
        bare, _ = self.remote(pending=False)
        (self.anchor / "AGENTS.md").write_text("# Installed instructions\n", encoding="utf-8")
        self.g("add", "AGENTS.md")
        self.g("commit", "-qm", "install instructions")
        self.plan("ai", [CHAIN[0]], {"ai.t1": {"product": "greeting"}}, delivery="auto")
        self.assertEqual(self.drain(local=False, code=1)["reason"], f"ai.t1: the installed instructions (AGENTS.md) in this checkout differ from "
                         f"those in its start commit {self.base}, so it would run without them; commit them and push them to origin/main")
        self.assertFalse(self.receipt_path("ai.t1").exists())
        self.run_ok(["git", "-C", str(self.anchor), "push", "-q", str(bare), "main"])
        self.assertEqual((self.tasks(self.drain(local=False))["ai.t1"]["delivery"], self.methodology("ai.t1")), ("COMPLETE", ["AGENTS.md"]))

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_unobservable_post_merge_cleanup_retains_the_workspace_and_drain_continues(self):
        self.remote(pending=False)
        self.plan("inv", [CHAIN[0]], {"inv.t1": {"product": "greeting"}}, delivery="auto")
        self.plan("loc", [("t1", [], "Notes", [NOTES_CHECK])], {"loc.t1": {"product": "notes"}})
        tasks = self.tasks(self.drain(local=False, unobservable=True))
        self.assertEqual((tasks["inv.t1"]["result"], tasks["inv.t1"]["delivery"], tasks["loc.t1"]["result"]), ("accepted", "COMPLETE", "accepted"))
        # The drain synced the anchor, so until a pull brings inv's rows the next drain lists only loc, and reruns nothing.
        self.assertEqual({identity: task["result"] for identity, task in self.tasks(self.drain(local=False, unobservable=True)).items()},
                         {"loc.t1": "accepted"})
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
        bare, _ = self.remote(pending=False)
        self.plan("inv", CHAIN, {"inv.t1": {"product": "greeting"}, "inv.t2": {"product": "app"}}, delivery="auto")
        held = self.anchor / "docs/specs/inv/t2/spec.expected.json"  # inv.t2 waits on its missing file while inv.t1 delivers.
        saved = held.read_bytes()
        held.unlink()
        self.assertEqual(self.tasks(self.drain(local=False))["inv.t1"]["delivery"], "COMPLETE")
        merge = self.receipt("inv.t1")["merge"]["mergeCommit"]["oid"]
        self.run_ok(["git", "--git-dir", str(bare), "update-ref", "refs/heads/main", self.base])  # The base loses that merge.
        held.write_bytes(saved)
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
        bare, data = self.remote(pending=False)
        self.plan("inv", CHAIN, {"inv.t1": {"product": "greeting"}, "inv.t2": {"product": "app"}}, delivery="auto")
        held = self.anchor / "docs/specs/inv/t2/spec.expected.json"  # inv.t2 waits on its missing file while inv.t1 delivers.
        saved = held.read_bytes()
        held.unlink()
        self.assertEqual(self.tasks(self.drain(local=False))["inv.t1"]["delivery"], "COMPLETE")
        held.write_bytes(saved)
        # A checkout of the refreshed base whose queue lacks T2's row: whole-loop acceptance reads the manifest.
        refreshed = self.root / "refreshed"
        self.g("fetch", "-q", str(bare), "main")
        self.g("worktree", "add", "-q", "--detach", str(refreshed), "FETCH_HEAD")
        stale = refreshed / "docs/specs/queue.md"
        stale.write_bytes(stale.read_bytes().replace((self.queue["row_line"]("inv.t2", "Greeting app [cli]") + "\n").encode(), b""))
        self.drain(local=False, repo=refreshed)
        report = self.common / "devlyn-loops/inv/drain-report.md"
        self.assertIn("- Whole-loop acceptance: INCOMPLETE — inv.t2 not yet run", report.read_text(encoding="utf-8"))
        # The original checkout runs T2, the integration task.
        self.assertEqual(self.tasks(self.drain(local=False))["inv.t2"]["result"], "accepted")
        self.assertIn("- Whole-loop acceptance: ACCEPTED", report.read_text(encoding="utf-8"))

    def pull(self, bare):
        return subprocess.run(["git", "-C", str(self.anchor), "pull", "--ff-only", str(bare), "main"], env=self.env, capture_output=True,
                              text=True, encoding="utf-8")

    def remote_rows(self, bare):
        queue = self.run_ok(["git", "--git-dir", str(bare), "show", "main:docs/specs/queue.md"]).encode("utf-8")
        return {row["identity"]: row["mark"] for row in self.queue["parse_queue"](queue) if row["identity"]}

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
    def test_auto_delivery_fast_forwards_the_anchor_on_pull(self):
        # add commits nothing for an auto loop. The first task carries the plan, in place of the legacy row it materializes;
        # the dependent starts from the merged plan with no inputs commit; once the loop settles the drain removes the
        # anchor's plan copies, so a pull fast-forwards the anchor with a clean tree (e2e D1, decision A).
        bare, data = self.remote(pending=False)
        meta = self.queue["write_package"](self.anchor, "inv", CHAIN, delivery="auto", base=self.base,
                                           intent="User asked: unrelated legacy intent.")
        self.behaviors.update({"inv.t1": {"product": "greeting"}, "inv.t2": {"product": "app"}})
        self.cli("add", meta, "--materialize", 4)
        self.assertEqual((self.g("rev-parse", "HEAD"), (self.common / "devlyn-loops/inv/adding.json").exists()), (self.base, False))
        tasks = self.tasks(self.drain(local=False))
        self.assertEqual({identity: task["delivery"] for identity, task in tasks.items()}, {"inv.t1": "COMPLETE", "inv.t2": "COMPLETE"})
        pulled = self.pull(bare)
        self.assertEqual(pulled.returncode, 0, pulled.stdout + pulled.stderr)
        self.assertEqual((self.g("rev-parse", "HEAD"), self.g("status", "--porcelain", "--untracked-files=all")),
                         (self.run_ok(["git", "--git-dir", str(bare), "rev-parse", "main"]), ""))
        accepted = ["- [x] " + self.queue["row_line"](identity, title)[6:] for identity, title in
                    (("inv.t1", "Greeting interface 인사"), ("inv.t2", "Greeting app [cli]"))]
        self.assertEqual(self.queue_at("HEAD"), "# Intent Queue\n\n- [x] earlier legacy work\n\n" + "\n\n".join(accepted) + "\n\n"
                         + self.queue["TRAILER"].decode("utf-8"))
        first, second = self.receipt("inv.t1"), self.receipt("inv.t2")
        self.assertEqual((first["baseline"], second["baseline"], second["acceptance"]["inputs_sha"]),
                         (self.base, first["merge"]["mergeCommit"]["oid"], first["merge"]["mergeCommit"]["oid"]))
        report = (self.common / "devlyn-loops/inv/drain-report.md").read_text(encoding="utf-8")
        self.assertIn("- Bring into main: git pull --ff-only origin main", report)

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_no_task_pr_carries_an_unpushed_anchor_commit(self):
        # Prediction (A1): with an unpushed commit U on the anchor branch, every auto task starts from the refreshed remote
        # base, so no delivered PR head descends from U. Before: the first task started from add's commit atop U, and its
        # PR carried U. Prediction (R5): main has U, which origin/main lacks, so the report prints `git merge origin/main`
        # with the reason, and running it brings the delivered work in beside U. Before R5: it printed
        # `git pull --ff-only origin main`, which cannot fast-forward the diverged branch.
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
        self.assertIn("- Bring into main: git merge origin/main (main has commits origin/main lacks, so this merges instead of fast-forwarding)",
                      (self.common / "devlyn-loops/inv/drain-report.md").read_text(encoding="utf-8"))

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_independent_pending_prs_merge_one_after_the_other(self):
        # Prediction (A2): once the carrier's PR landed the plan, two independent tasks' PRs pending at once each change
        # only their own row, one blank line from the next, so they merge one after the other without conflict and the
        # remote queue shows both rows [x]. Before: the rows were adjacent, so the second merge conflicted in the queue.
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
    def test_a_carrier_and_another_loops_pending_last_row_pr_both_merge(self):
        # Prediction: a carrier's plan leaves a blank line between the loop's last row and the trailer line, so the next
        # loop's carrier inserts after an unchanged line; with that last row's PR and the next carrier's PR pending
        # together, the two heads merge with each other (so in either order), they merge one after the other, and the next
        # drain completes both. Before: the next carrier's rows touched that last row, so the second merge conflicted and
        # the carrier stayed in flight.
        bare, data = self.remote(pending=True)
        self.plan("la", [("t1", [], "Notes", [NOTES_CHECK]), ("t2", ["t1"], "Todo", [TODO_CHECK])],
                  {"la.t1": {"product": "notes"}, "la.t2": {"product": "todo"}}, delivery="auto")
        self.drain(local=False)
        self.assertEqual(self.merge_pr(data, 1).returncode, 0)
        self.plan("lb", [("t1", [], "Greeting", [GREET_CHECK])], {"lb.t1": {"product": "greeting"}}, delivery="auto")
        self.drain(local=False)
        prs = json.loads(data.read_text(encoding="utf-8"))["prs"]
        self.assertEqual([pr["headRefName"] for pr in prs if pr["state"] == "OPEN"], ["devlyn/la/t2", "devlyn/lb/t1"])
        self.run_ok(["git", "--git-dir", str(bare), "merge-tree", "--write-tree", prs[1]["headRefOid"], prs[2]["headRefOid"]])
        for number in (2, 3):
            merged = self.merge_pr(data, number)
            self.assertEqual(merged.returncode, 0, merged.stderr)
        tasks = self.tasks(self.drain(local=False))
        self.assertEqual({identity: task["delivery"] for identity, task in tasks.items()}, {"la.t1": "COMPLETE", "la.t2": "COMPLETE", "lb.t1": "COMPLETE"})

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_one_carrier_is_in_flight_across_the_queue(self):
        # Prediction (R2): while the first auto loop's carrier PR is pending, the second auto loop's first task waits with
        # that carrier named and no executor call; once that PR merges, the second loop's carrier runs, its PR merges without
        # conflict, and both rows on the remote base end [x]. Before: the second carrier ran at once, so two carriers
        # inserted rows above the same trailer and the second PR could not merge.
        bare, data = self.remote(pending=True)
        self.plan("la", [("t1", [], "Notes", [NOTES_CHECK])], {"la.t1": {"product": "notes"}}, delivery="auto")
        self.plan("lb", [("t1", [], "Todo", [TODO_CHECK])], {"lb.t1": {"product": "todo"}}, delivery="auto")
        tasks = self.tasks(self.drain(local=False))
        self.assertEqual((tasks["la.t1"]["delivery"], tasks["lb.t1"]["result"], tasks["lb.t1"].get("reason"), self.calls("lb.t1")),
                         ("PENDING", "pending", "awaiting delivery of la.t1, whose PR carries its loop's plan", 0))
        self.assertEqual(self.merge_pr(data, 1).returncode, 0)
        tasks = self.tasks(self.drain(local=False))
        self.assertEqual((tasks["la.t1"]["delivery"], tasks["lb.t1"]["delivery"]), ("COMPLETE", "PENDING"))
        merged = self.merge_pr(data, 2)
        self.assertEqual(merged.returncode, 0, merged.stderr)
        self.assertEqual(self.tasks(self.drain(local=False))["lb.t1"]["delivery"], "COMPLETE")
        self.assertEqual(self.remote_rows(bare), {"la.t1": "x", "lb.t1": "x"})

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_squash_delivery_leaves_the_anchor_pull_ready(self):
        # Prediction (A3): the fake squash-merges every PR; the anchor holds no loop commit and the drain removes its plan
        # copies once the loop settled, so `git pull --ff-only` fast-forwards the anchor to the remote base with a clean
        # tree and both rows [x]. Before: add's commit stayed on the anchor and no squash merge descends from it, so the
        # pull could not fast-forward.
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
        self.assertIn("- Bring into main: git pull --ff-only origin main", report)

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_a_failed_carrier_hands_the_plan_to_the_next_task(self):
        # Prediction (A4): the carrier fails and is never published; the next task then starts from the same remote base,
        # its inputs commit carries the whole package and every row of the loop, the failed carrier's receipt-proven [F]
        # row included, its PR merges, and the loop settles. Before: both tasks started from add's local commit.
        bare, data = self.remote(pending=False)
        tasks = [CHAIN[0], ("t2", [], "Notes", [NOTES_CHECK]), ("t3", ["t1", "t2"], "Greeting app", [APP_CHECK])]
        self.plan("cf", tasks, {"cf.t1": {"product": "bad-greeting"}, "cf.t2": {"product": "notes"}, "cf.t3": {"product": "app"}},
                  delivery="auto")
        tasks = self.tasks(self.drain(local=False))
        self.assertEqual({identity: task["result"] for identity, task in tasks.items()}, {"cf.t1": "failed", "cf.t2": "accepted", "cf.t3": "blocked"})
        failed, carrier = self.receipt("cf.t1"), self.receipt("cf.t2")
        self.assertEqual((failed["baseline"], carrier["baseline"], carrier["delivery"], self.calls("cf.t3")), (self.base, self.base, "COMPLETE", 0))
        self.assertEqual([pr["headRefName"] for pr in json.loads(data.read_text(encoding="utf-8"))["prs"]], ["devlyn/cf/t2"])
        package = ["docs/specs/cf/meta.md"] + [f"docs/specs/cf/{task}/{name}" for task in ("t1", "t2", "t3") for name in ("spec.expected.json", "spec.md")]
        self.assertEqual(self.g("diff", "--name-only", self.base, carrier["acceptance"]["inputs_sha"]).splitlines(), package + ["docs/specs/queue.md"])
        self.assertEqual(self.remote_rows(bare), {"cf.t1": "F", "cf.t2": "x", "cf.t3": "F"})

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_a_pending_task_missing_a_file_waits_alone_while_the_carrier_lands_the_plan(self):
        # Prediction: with a pending task's spec.expected.json deleted, the carrier commits every row and the package less
        # that task, so it and an independent loop are delivered while that task waits with the error; once the file is
        # back, the task commits its own files and the loop is accepted. Before: the carrier read every task's files after
        # its allocation, so each drain blocked on the missing file and no executor ran.
        self.remote(pending=False)
        self.plan("mv", [("t1", [], "Notes", [NOTES_CHECK]), ("t2", ["t1"], "Todo", [TODO_CHECK])],
                  {"mv.t1": {"product": "notes"}, "mv.t2": {"product": "todo"}}, delivery="auto")
        self.plan("ot", [("t1", [], "Greeting", [GREET_CHECK])], {"ot.t1": {"product": "greeting"}}, delivery="auto")
        missing = self.anchor / "docs/specs/mv/t2/spec.expected.json"
        saved = missing.read_bytes()
        missing.unlink()
        tasks = self.tasks(self.drain(local=False))
        self.assertEqual({identity: (task["result"], task.get("delivery")) for identity, task in tasks.items()},
                         {"mv.t1": ("accepted", "COMPLETE"), "mv.t2": ("pending", None), "ot.t1": ("accepted", "COMPLETE")})
        self.assertIn("spec.expected.json", tasks["mv.t2"]["reason"])
        carrier = self.receipt("mv.t1")
        self.assertEqual(self.g("diff", "--name-only", carrier["baseline"], carrier["acceptance"]["inputs_sha"]).splitlines(),
                         ["docs/specs/mv/meta.md", "docs/specs/mv/t1/spec.expected.json", "docs/specs/mv/t1/spec.md", "docs/specs/queue.md"])
        missing.write_bytes(saved)
        tasks = self.tasks(self.drain(local=False))
        self.assertEqual((tasks["mv.t2"]["delivery"], self.calls("mv.t2")), ("COMPLETE", 1))
        second = self.receipt("mv.t2")
        self.assertEqual(self.g("diff", "--name-only", second["baseline"], second["acceptance"]["inputs_sha"]).splitlines(),
                         ["docs/specs/mv/t2/spec.expected.json", "docs/specs/mv/t2/spec.md"])
        self.assertIn("- Whole-loop acceptance: ACCEPTED", (self.common / "devlyn-loops/mv/drain-report.md").read_text(encoding="utf-8"))

    def bring_in(self, loop, bare):
        """Run the loop's drain report `Bring into` command in the anchor, origin's URL resolving to the bare remote."""
        report = (self.common / f"devlyn-loops/{loop}/drain-report.md").read_text(encoding="utf-8")
        command = shlex.split(next(line for line in report.splitlines() if line.startswith("- Bring into ")).split(": ", 1)[1].split(" (")[0])
        self.assertEqual(command[0], "git")
        return subprocess.run(["git", "-c", f"url.{bare}.insteadOf=https://github.com/test/project.git", "-C", str(self.anchor), *command[1:]],
                              env=self.env, capture_output=True, text=True, encoding="utf-8")

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_a_plan_that_never_lands_leaves_the_tracked_queue_unchanged(self):
        # Prediction (R3a): an auto add leaves docs/specs/queue.md unchanged, so after a chain auto loop's first task fails,
        # the anchor's tracked files stay unchanged through its drains and a later auto loop's, status still reports the
        # failed and the blocked row, and the later loop's delivered work comes in with the report's command, a fast-forward
        # pull. Before: add wrote the rows into the anchor's queue and only a landed plan removed them, so the queue stayed
        # modified and the pull refused it.
        bare, _ = self.remote(pending=False)
        self.plan("cf", CHAIN, {"cf.t1": {"product": "bad-greeting"}, "cf.t2": {"product": "app"}}, delivery="auto")
        for _ in range(2):
            tasks = self.tasks(self.drain(local=False))
            self.assertEqual({identity: task["result"] for identity, task in tasks.items()}, {"cf.t1": "failed", "cf.t2": "blocked"})
            self.assertEqual(self.g("status", "--porcelain", "--untracked-files=no"), "")
        self.plan("lt", [("t1", [], "Notes", [NOTES_CHECK])], {"lt.t1": {"product": "notes"}}, delivery="auto")
        self.assertEqual(self.tasks(self.drain(local=False))["lt.t1"]["delivery"], "COMPLETE")
        self.assertEqual(self.g("status", "--porcelain", "--untracked-files=no"), "")
        pulled = self.bring_in("lt", bare)
        self.assertEqual(pulled.returncode, 0, pulled.stdout + pulled.stderr)
        self.assertEqual(self.g("rev-parse", "HEAD"), self.run_ok(["git", "--git-dir", str(bare), "rev-parse", "main"]))
        self.assertEqual({identity: row["mark"] for identity, row in self.rows("HEAD").items()}, {"lt.t1": "x"})
        status = self.cli("status", "--repo", self.anchor)
        self.assertEqual((status["counts"]["failed"], status["counts"]["blocked"]), (1, 1))
        self.assertIn("cf.t2: blocked-prerequisite:cf.t1", status["blockers"])

    def test_commit_all_after_an_auto_add_commits_nothing_of_the_loop(self):
        # Prediction (R3b): an auto add leaves docs/specs/queue.md unchanged, so `git commit -am` right after it commits only
        # the user's own tracked edit, while status shows the loop's task. Before: add wrote the rows into the anchor's
        # queue, and the commit swept them up.
        self.plan("ca", [CHAIN[0]], {}, delivery="auto")
        with (self.anchor / ".gitignore").open("a", encoding="utf-8") as ignore:
            ignore.write("# own edit\n")
        self.g("commit", "-qam", "own edit")
        self.assertEqual(self.g("show", "--name-only", "--format=", "HEAD"), ".gitignore")
        self.assertEqual(self.cli("status", "--repo", self.anchor)["next"], "ca.t1")

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_a_local_loop_added_after_an_auto_loop_fast_forwards_while_its_pr_waits(self):
        # Prediction (R3c, d): auto adds leave docs/specs/queue.md unchanged, so a local loop added after an auto loop
        # commits only its own row, and with that auto loop's PR pending and another auto loop added since, the local loop's
        # reported fast-forward applies and leaves the tracked files clean. Before: the local add's commit swept up the
        # first auto loop's rows, and the second auto loop's uncommitted rows made the fast-forward refuse the queue.
        bare, _ = self.remote(pending=True)
        self.plan("au", [CHAIN[0]], {"au.t1": {"product": "greeting"}}, delivery="auto")
        self.plan("lo", [("t1", [], "Notes", [NOTES_CHECK])], {"lo.t1": {"product": "notes"}})
        self.assertEqual(list(self.rows("HEAD")), ["lo.t1"])
        self.plan("aw", [("t1", [], "Todo", [TODO_CHECK])], {"aw.t1": {"product": "todo"}}, delivery="auto")
        tasks = self.tasks(self.drain(local=False))
        self.assertEqual((tasks["au.t1"]["delivery"], tasks["lo.t1"]["delivery"]), ("PENDING", "LOCAL_ONLY"))
        merged = self.bring_in("lo", bare)
        self.assertEqual(merged.returncode, 0, merged.stdout + merged.stderr)
        self.assertEqual((self.g("rev-parse", "HEAD"), self.g("status", "--porcelain", "--untracked-files=no")),
                         (self.receipt("lo.t1")["publish_sha"], ""))

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_a_used_loop_id_is_refused_before_and_after_the_sync(self):
        # Prediction (R3e): add refuses a loop id that already has an add record, so a different package under a used auto
        # loop id is refused while the loop is queued and again after the drain synced the anchor, which would otherwise
        # take the old loop's receipts for the new one. Before: both re-adds were accepted, their task ids clashing with no
        # queued row.
        bare, _ = self.remote(pending=False)
        self.plan("ru", [CHAIN[0]], {"ru.t1": {"product": "greeting"}}, delivery="auto")
        package = self.anchor / "docs/specs/ru"
        saved = {path: path.read_bytes() for path in package.rglob("*") if path.is_file()}

        def readd():
            meta = self.queue["write_package"](self.anchor, "ru", [("t9", [], "Other", [NOTES_CHECK])], delivery="auto", base=self.base)
            return self.cli("add", meta, code=1)["reason"]
        self.assertIn("loop id ru was already added", readd())
        shutil.rmtree(package)
        for path, body in saved.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
        self.assertEqual(self.tasks(self.drain(local=False))["ru.t1"]["delivery"], "COMPLETE")
        self.assertEqual((package.exists(), self.added("ru")["synced"]), (False, True))
        self.assertIn("loop id ru was already added", readd())

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
        # A later --local-only drain cannot rewrite the delivery of a task whose PR is already pushed.
        server = json.loads(data.read_text())
        blocked = self.drain(code=1)
        self.assertIn("inv.t1 already has a pushed PR", blocked["reason"])
        self.assertEqual((self.receipt("inv.t1")["delivery"], self.receipt("inv.t1").get("local_only"), self.calls("inv.t2")), ("PENDING", None, 0))
        self.assertEqual(json.loads(data.read_text()), server)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-root", type=Path, default=PACKAGE_ROOT)
    args, rest = parser.parse_known_args()
    LoopFixture.skills = args.package_root.resolve() / "config" / "skills"
    result = unittest.main(argv=[sys.argv[0], *rest], exit=False, verbosity=2).result
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
