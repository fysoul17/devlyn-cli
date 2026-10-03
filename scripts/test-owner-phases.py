#!/usr/bin/env python3
"""Exercise the owner PLAN and VERIFY MECHANICAL boundaries through the real CLI and Git."""
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import time
import unittest

SHARED = Path(__file__).resolve().parents[1] / "config/skills/_shared"
ENV = {k: v for k, v in os.environ.items() if not k.startswith("DEVLYN_INVOCATION_")}
ENV["PYTHONDONTWRITEBYTECODE"] = "1"
ENV.pop("BENCH_WORKDIR", None)


class OwnerPhases(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name).resolve()
        self.devlyn = self.work / ".devlyn"
        self.devlyn.mkdir()
        self.state_path = self.devlyn / "pipeline.state.json"
        (self.devlyn / "untracked.baseline").write_text("")
        self.git("init", "-q")
        self.git("config", "user.name", "Owner phase test")
        self.git("config", "user.email", "owner@example.invalid")
        (self.work / ".gitignore").write_text(".devlyn/\n")
        (self.work / "source.txt").write_text("original\n")
        self.git("add", ".")
        self.git("commit", "-qm", "fixture")
        self.head = self.git("rev-parse", "HEAD")
        self.save({"version": "3.0", "run_id": "rs-owner-test", "engine": "codex", "mode": "spec",
                   "base_ref": {"sha": self.head}, "untracked_baseline_sha256": None,
                   "rounds": {"global": 0, "max_rounds": 4}, "phases": {}})

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.work, text=True).strip()

    def state(self):
        return json.loads(self.state_path.read_text())

    def save(self, value):
        self.state_path.write_text(json.dumps(value))

    def cli(self, phase, *args, error=None):
        before = self.state_path.read_bytes()
        result = subprocess.run(
            [sys.executable, str(SHARED / "state-phase-write.py"), "--devlyn-dir", ".devlyn",
             "--phase", phase, *args], cwd=self.work, env=ENV, capture_output=True, text=True,
        )
        if error:
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn(error, result.stderr)
            self.assertEqual(self.state_path.read_bytes(), before)
        else:
            self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def checker(self, *args):
        return subprocess.run([sys.executable, str(SHARED / "spec-verify-check.py"), *args],
                              cwd=self.work, env=ENV, capture_output=True, text=True)

    def assert_owner(self, phase):
        entry = self.state()["phases"][phase]
        self.assertEqual(entry["execution_kind"], "orchestrator_context")
        for name in ("engine", "model_requested", "model_effective"):
            self.assertIsNone(entry[name])
        self.assertFalse({"prompt_sha256", "invocation_receipt", "role_argv"} & entry.keys())
        return entry

    def plan(self):
        self.cli("plan", "spawn", "--round", "0")
        self.assert_owner("plan")
        (self.devlyn / "plan.md").write_text(
            '<!-- devlyn:authorized-surface -->\n# Files\n```json\n'
            '{"authorized_surface":["source.txt"]}\n```\n# Acceptance\nPreserve scope.\n')

    def implemented(self):
        """PLAN → IMPLEMENT with a committed change → VERIFY round 0."""
        self.plan()
        self.cli("plan", "transition", "--verdict", "PASS", "--next-phase", "implement",
                 "--next-round", "0", "--next-engine", "claude")
        (self.work / "source.txt").write_text("implemented\n")
        self.git("commit", "-qam", "chore(pipeline): implement")
        self.cli("implement", "transition", "--verdict", "PASS", "--next-phase", "verify",
                 "--next-round", "0", "--next-engine", "claude")
        return self.git("rev-parse", "HEAD")

    def needs_work(self):
        """Stand in for the merge: VERIFY round closes NEEDS_WORK with merged findings."""
        (self.devlyn / "verify-merged.findings.jsonl").write_text('{"id": "VERIFY-0001", "severity": "HIGH"}\n')
        state = self.state()
        state["phases"]["verify"].update(verdict="NEEDS_WORK", merged={"verdict": "NEEDS_WORK"})
        self.save(state)

    def test_plan_digest_and_atomic_handoff(self):
        self.plan()
        self.cli("plan", "transition", "--verdict", "PASS", "--next-phase", "implement",
                 "--next-round", "0", "--next-engine", "claude")
        entry = self.assert_owner("plan")
        self.assertEqual(entry["output_sha256"],
                         hashlib.sha256((self.devlyn / "plan.md").read_bytes()).hexdigest())
        self.assertEqual(self.state()["untracked_baseline_sha256"], hashlib.sha256(b"").hexdigest())
        self.cli("plan", "spawn", "--round", "1", "--triggered-by", "plan",
                 error="plan-already-in-use")
        (self.devlyn / "plan.md").write_text("widened scope")
        self.cli("implement", "complete", "--verdict", "PASS", error="plan-integrity-mismatch")

    def test_owner_identity_and_current_round_artifacts(self):
        self.cli("plan", "spawn", "--round", "0")
        opened = self.state()
        for flag in ("--engine", "--model", "--engine-session-log"):
            self.cli("plan", "complete", "--verdict", "BLOCKED", flag, "false-worker",
                     error="cannot claim worker")
        for suffix in ("prompt.0", "worker-session.0.jsonl", "invocation.0.json", "argv.0.json"):
            proof = self.devlyn / f"plan.{suffix}"
            proof.symlink_to(self.devlyn / "missing")
            self.cli("plan", "complete", "--verdict", "BLOCKED", error="worker evidence")
            proof.unlink()
        for key, value in (("engine", "codex"), ("prompt_sha256", None),
                           ("execution_kind", False), ("execution_kind", {})):
            bad = json.loads(json.dumps(opened))
            bad["phases"]["plan"][key] = value
            self.save(bad)
            self.cli("plan", "complete", "--verdict", "BLOCKED", error="error:")
        self.save(opened)

    def test_owner_plan_history_is_bound_and_round_limited(self):
        self.plan()
        self.cli("plan", "complete", "--verdict", "NEEDS_WORK")
        old = self.assert_owner("plan")
        self.cli("plan", "spawn", "--round", "1", "--triggered-by", "plan")
        self.assertEqual(self.state()["phases"]["plan"]["history"][0]["output_sha256"], old["output_sha256"])
        self.cli("plan", "complete", "--verdict", "BLOCKED")
        self.cli("plan", "spawn", "--round", "2", "--triggered-by", "plan", error="plan-respawn-exhausted")

    def test_mechanical_seals_only_the_unchanged_clean_tree(self):
        head = self.implemented()
        self.assertEqual(self.state()["phases"]["verify"]["pre_sha"], head)

        def staged():
            (self.work / "source.txt").write_text("staged\n")
            self.git("add", "source.txt")

        for mutate, restore in (
            (lambda: (self.work / "source.txt").write_text("unverified change\n"),
             lambda: self.git("checkout", "--", "source.txt")),
            (staged, lambda: self.git("reset", "-q", "--hard", head)),
            (lambda: (self.work / "outside-plan.txt").write_text("leak"),
             lambda: (self.work / "outside-plan.txt").unlink()),
        ):
            self.assertEqual(self.checker().returncode, 0)
            mutate()
            refused = self.checker("--seal")
            self.assertEqual(refused.returncode, 1, refused.stderr)
            self.assertIsNone(json.loads((self.devlyn / "source-seal.json").read_text())["seal"])
            self.assertIn("scope.unsealed-source", (self.devlyn / "verify-mechanical.findings.jsonl").read_text())
            restore()
        self.assertEqual(self.checker().returncode, 0)
        (self.work / "coverage.out").write_text("run artifact removed before sealing\n")
        (self.work / "coverage.out").unlink()
        sealed = self.checker("--seal")
        self.assertEqual(sealed.returncode, 0, sealed.stderr)
        self.assertEqual(json.loads((self.devlyn / "source-seal.json").read_text())["seal"]["head"], head)

    def test_preexisting_untracked_files_survive_and_residue_cannot_seal(self):
        (self.work / "user-existing.txt").write_text("preserve")
        (self.devlyn / "untracked.baseline").write_text("user-existing.txt\n")
        self.implemented()
        (self.work / "outside-plan.txt").write_text("created before MECHANICAL")
        self.checker()
        self.assertEqual(self.checker("--seal").returncode, 1)
        (self.work / "outside-plan.txt").unlink()
        self.assertEqual(self.checker().returncode, 0)
        self.assertEqual(self.checker("--seal").returncode, 0)
        self.assertEqual((self.work / "user-existing.txt").read_text(), "preserve")

    def test_verify_repair_reenters_with_checkpoint(self):
        self.implemented()
        self.needs_work()
        self.cli("verify", "transition", "--next-phase", "implement", "--next-round", "1",
                 "--next-triggered-by", "verify", "--next-engine", "claude")
        self.assertEqual(self.state()["rounds"]["global"], 1)
        self.cli("implement", "transition", "--verdict", "PASS", "--next-phase", "verify",
                 "--next-round", "1", "--next-triggered-by", "verify", error="repair-checkpoint")
        (self.work / "source.txt").write_text("fixed\n")
        self.cli("implement", "durability-enforce", "--round", "1", error="not clean")
        self.git("commit", "-qam", "chore(pipeline): implement fix round 1")
        self.cli("implement", "durability-enforce", "--round", "1")
        fixed = self.git("rev-parse", "HEAD")
        self.cli("implement", "transition", "--verdict", "PASS", "--next-phase", "verify",
                 "--next-round", "1", "--next-triggered-by", "verify", "--next-engine", "claude")
        verify = self.state()["phases"]["verify"]
        self.assertEqual((verify["round"], verify["pre_sha"]), (1, fixed))
        self.assertFalse((self.devlyn / "source-seal.json").exists())

    def test_repair_admission_lock_serializes_contenders(self):
        self.implemented()
        self.needs_work()
        self.cli("verify", "complete")
        lock = runpy.run_path(str(SHARED / "platform-support.py"))["file_lock"]
        command = [sys.executable, str(SHARED / "state-phase-write.py"), "--devlyn-dir", ".devlyn",
                   "--phase", "implement", "spawn", "--round", "1", "--triggered-by", "verify",
                   "--engine", "claude"]
        with lock(self.devlyn / "pipeline.state.lock", blocking=True):
            first = subprocess.Popen(command, cwd=self.work, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            second = subprocess.Popen(command, cwd=self.work, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            time.sleep(0.1)
            self.assertIsNone(first.poll())
            self.assertIsNone(second.poll())
        results = [(process.returncode, stderr) for process in (first, second)
                   for _stdout, stderr in [process.communicate(timeout=10)]]
        self.assertEqual(sorted(code for code, _ in results), [0, 1], results)
        self.assertEqual(self.state()["rounds"]["global"], 1)
        self.assertEqual(self.state()["phases"]["implement"]["round"], 1)

    def test_refused_repair_closes_and_archives_terminal_report(self):
        self.implemented()
        self.needs_work()
        state = self.state()
        state["rounds"] = {"global": 1, "max_rounds": 1}
        self.save(state)
        self.cli("verify", "transition", "--next-phase", "implement", "--next-round", "1",
                 "--next-triggered-by", "verify", "--next-engine", "claude",
                 error="BLOCKED:repair-budget-exhausted")
        self.cli("verify", "complete")
        self.cli("final_report", "spawn", "--round", "0")
        (self.devlyn / "final-report.md").write_text(
            "<!-- devlyn:final-report run_id=rs-owner-test -->\n# Repair budget exhausted\n")
        self.cli("final_report", "complete", "--verdict", "NEEDS_WORK",
                 "--log-file", ".devlyn/final-report.md")
        archived = subprocess.run([sys.executable, str(SHARED / "archive_run.py"), "--devlyn-dir", ".devlyn"],
                                  cwd=self.work, env=ENV, capture_output=True, text=True)
        self.assertEqual(archived.returncode, 0, archived.stderr)
        checked = subprocess.run([sys.executable, str(SHARED / "terminal-claim-check.py")],
                                 cwd=self.work, env=ENV, capture_output=True, text=True)
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)

    def test_owner_plan_does_not_replace_selected_worker(self):
        helper = runpy.run_path(str(SHARED / "state-phase-write.py"))
        (self.devlyn / "engines.json").write_text(json.dumps({"roles": {
            "worker": {"engine": "codex", "model": "gpt-6-astra", "effort": "high"}}}))
        state = self.state()
        frozen = helper["freeze_roles"](state, self.work, "codex")
        self.save(state)
        self.cli("plan", "spawn", "--round", "0")
        self.assert_owner("plan")
        self.assertEqual(self.state()["role_resolution"], frozen)
        self.cli("implement", "spawn", "--round", "0", "--engine", "claude",
                 error="role-selection-mismatch")


if __name__ == "__main__":
    unittest.main(verbosity=2)
