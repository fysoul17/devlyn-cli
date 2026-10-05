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
with config_path.with_name("calls-" + packet["task"]).open("a", encoding="utf-8") as calls:
    calls.write("call\n")
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
PRODUCTS = {
    "greeting": {"greeting.py": "def greet(name):\n    return f\"Hello, {name}!\"\n"},
    "bad-greeting": {"greeting.py": "def greet(name):\n    return f\"Hi {name}\"\n"},
    "app": {"app.py": "import sys\nfrom greeting import greet\nfor name in sys.argv[1:]:\n    print(greet(name))\n"},
    "bad-app": {"app.py": "print('Bye')\n"},
    "notes": {"notes.txt": "notes\n"},
}
GREET_CHECK = {"argv": [sys.executable, "-c", "from greeting import greet; assert greet('Ada') == 'Hello, Ada!'; print('greet ok')"],
               "stdout_contains": ["greet ok"], "contract_refs": ["R1"]}
APP_CHECK = {"argv": [sys.executable, "app.py", "Ada", "Lin"], "stdout_contains": ["Hello, Ada!", "Hello, Lin!"], "contract_refs": ["R1"]}
NOTES_CHECK = {"argv": [sys.executable, "-c", "import pathlib; assert pathlib.Path('notes.txt').read_text() == 'notes\\n'; print('notes ok')"],
               "stdout_contains": ["notes ok"], "contract_refs": ["R1"]}
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

    def drain_argv(self, local=True, unobservable=False):
        self.config.write_text(json.dumps({"behaviors": self.behaviors, "products": PRODUCTS, "hold": HOLD,
                                           "platform_support": str(self.platform),
                                           "queue_lock": str(self.common / "devlyn-loops/queue.lock")}), encoding="utf-8")
        return [sys.executable, *(["-c", UNOBSERVABLE] if unobservable else []), str(self.queue_py), "drain", "--repo", str(self.anchor),
                *(["--local-only"] if local else []), "--", sys.executable, str(self.config.parent / "executor.py"), str(self.config), "{packet}"]

    def drain(self, local=True, code=0, unobservable=False):
        result = subprocess.run(self.drain_argv(local, unobservable), cwd=self.root, env=self.env, capture_output=True, text=True, encoding="utf-8")
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
        # Both executors refuse a piped stdout, as codex-monitored.sh does; the driver gives them files.
        self.plan("inv", CHAIN, {"inv.t1": {"product": "greeting", "refuse_pipe": True}, "inv.t2": {"product": "app", "refuse_pipe": True}})
        result = self.drain()
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
        expected = (self.base_queue.decode("utf-8") + t1_row + "\n" + self.queue["row_line"]("inv.t2", "Greeting app [cli]")).strip()
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

    def test_interruption_after_terminal_commit_attaches_and_delivers_only(self):
        self.plan("inv", CHAIN, {"inv.t1": {"product": "greeting", "hold": True}, "inv.t2": {"product": "app"}})
        driver = self.drain_until("inv.t1: bound", "inv.t1: terminal")
        next(driver)
        receipt_lock = self.hold(self.receipt_path("inv.t1").with_name("lock"))
        self.release_executor_holder()
        next(driver).kill()
        partial = self.receipt("inv.t1")
        terminal = self.g("rev-parse", "refs/heads/devlyn/inv/t1")
        self.assertNotEqual(terminal, partial["source_sha"])
        self.assertNotIn("queue", partial)
        self.assertEqual(self.g("rev-parse", partial["recovery_ref"]), partial["source_sha"])
        receipt_lock.kill()
        receipt_lock.wait()
        result = self.drain()
        self.assertEqual(self.tasks(result)["inv.t1"]["result"], "accepted")
        settled = self.receipt("inv.t1")
        self.assertEqual((settled["queue"]["commit"], settled["delivery"], self.calls("inv.t1")), (terminal, "LOCAL_ONLY", 1))
        self.assertEqual(self.g("rev-parse", settled["recovery_ref"]), terminal)

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
        failed = self.receipt("dd.t1")
        failed_row = self.rows(failed["publish_sha"])["dd.t1"]["line"]
        blocked_row = "- [F] " + self.queue["row_line"]("dd.t3", "Greeting app")[6:] + f" — blocked-prerequisite:dd.t1 (receipt {failed['id']})"
        dd2_inputs = self.queue_at(self.receipt("dd.t2")["acceptance"]["inputs_sha"])
        self.assertEqual(dd2_inputs, "\n".join([self.base_queue.decode("utf-8") + failed_row, self.queue["row_line"]("dd.t2", "Notes"), blocked_row]))
        reports = {loop: (self.common / f"devlyn-loops/{loop}/drain-report.md").read_text(encoding="utf-8") for loop in ("dd", "ee")}
        self.assertIn("Whole-loop acceptance: INCOMPLETE — ee.t2 failed", reports["ee"])
        self.assertIn("blocked-prerequisite:dd.t1", reports["dd"])
        # A hand-written mark that contradicts a receipt stops selection.
        queue_file = self.anchor / "docs/specs/queue.md"
        queue_file.write_bytes(queue_file.read_bytes().replace(b"- [ ] ee.t1", b"- [x] ee.t1").replace(b"- [ ] ee.t2", b"- [x] ee.t2"))
        self.assertIn("conflicting terminal state for ee.t2", self.cli("status", "--repo", self.anchor, code=1)["reason"])

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
    def test_unobservable_post_merge_cleanup_retains_the_workspace_and_drain_continues(self):
        self.remote(pending=False)
        self.plan("inv", [CHAIN[0]], {"inv.t1": {"product": "greeting"}}, delivery="auto")
        self.plan("loc", [("t1", [], "Notes", [NOTES_CHECK])], {"loc.t1": {"product": "notes"}})
        for _ in range(2):
            tasks = self.tasks(self.drain(local=False, unobservable=True))
            self.assertEqual((tasks["inv.t1"]["result"], tasks["inv.t1"]["delivery"], tasks["loc.t1"]["result"]), ("accepted", "COMPLETE", "accepted"))
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
        queue = self.anchor / "docs/specs/queue.md"
        planned = queue.read_bytes()
        queue.write_bytes(planned.replace((self.queue["row_line"]("inv.t2", "Greeting app [cli]") + "\n").encode(), b""))
        self.assertEqual(self.tasks(self.drain(local=False))["inv.t1"]["delivery"], "COMPLETE")
        merge = self.receipt("inv.t1")["merge"]["mergeCommit"]["oid"]
        self.run_ok(["git", "--git-dir", str(bare), "update-ref", "refs/heads/main", self.base])  # The base loses that merge.
        queue.write_bytes(planned)
        for _ in range(2):
            self.assertIn(f"lacks the delivered prerequisite merge {merge}", self.drain(local=False, code=1)["reason"])
            self.assertFalse(self.receipt_path("inv.t2").exists())
        # A receipt allocated on that base by another route is checked again before execution.
        self.run_ok([sys.executable, str(self.helper), "allocate", "--repo", str(self.anchor), "--task", "inv.t2", "--branch", "devlyn/inv/t2",
                     "--repository", "test/project", "--base", "main", "--worktree", str(self.root / "repo.devlyn/inv/t2")])
        self.assertIn(f"lacks the delivered prerequisite merge {merge}", self.drain(local=False, code=1)["reason"])
        self.assertEqual(self.calls("inv.t2"), 0)

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
        self.assertEqual(json.loads(data.read_text())["pr"]["headRefOid"], receipt["publish_sha"])
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
