#!/usr/bin/env python3
"""Exercise the candidate's owner phases through the real CLI and Git boundary."""
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest

SHARED = Path(__file__).resolve().parents[1] / "config/skills/_shared"
ENV = {k: v for k, v in os.environ.items() if not k.startswith("DEVLYN_INVOCATION_")}
ENV["PYTHONDONTWRITEBYTECODE"] = "1"


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
        self.save({"version": "3.0", "run_id": "rs-owner-test", "engine": "codex",
                   "phases": {}})

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

    def assert_owner(self, phase):
        entry = self.state()["phases"][phase]
        self.assertEqual(entry["execution_kind"],
                         "orchestrator_context" if phase == "plan" else "orchestrator_commands")
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

    def test_plan_digest_and_atomic_handoff(self):
        self.plan()
        self.cli("plan", "transition", "--verdict", "PASS", "--next-phase", "implement",
                 "--next-round", "0", "--next-engine", "claude")
        entry = self.assert_owner("plan")
        self.assertEqual(entry["output_sha256"],
                         hashlib.sha256((self.devlyn / "plan.md").read_bytes()).hexdigest())
        self.cli("plan", "spawn", "--round", "1", "--triggered-by", "plan",
                 error="plan-already-in-use")
        (self.devlyn / "plan.md").write_text("widened scope")
        self.cli("implement", "complete", "--verdict", "PASS", error="plan-integrity-mismatch")

    def test_owner_identity_and_current_round_artifacts(self):
        for phase in ("plan", "cleanup"):
            self.save({"version": "3.0", "run_id": "rs-owner-test", "engine": "codex", "phases": {}})
            spawn = ("spawn", "--round", "0") + (("--pre-sha", self.head) if phase == "cleanup" else ())
            self.cli(phase, *spawn)
            opened = self.state()
            for flag in ("--engine", "--model", "--engine-session-log"):
                self.cli(phase, "complete", "--verdict", "BLOCKED", flag, "false-worker",
                         error="cannot claim worker")
            for suffix in ("prompt.0", "worker-session.0.jsonl", "invocation.0.json", "argv.0.json"):
                proof = self.devlyn / f"{phase}.{suffix}"
                proof.symlink_to(self.devlyn / "missing")
                self.cli(phase, "complete", "--verdict", "BLOCKED", error="worker evidence")
                proof.unlink()
            for key, value in (("engine", "codex"), ("prompt_sha256", None),
                               ("execution_kind", False), ("execution_kind", {})):
                bad = json.loads(json.dumps(opened))
                bad["phases"][phase][key] = value
                self.save(bad)
                self.cli(phase, "complete", "--verdict", "BLOCKED", error="error:")
            self.save(opened)

    def test_owner_plan_history_is_bound_and_round_limited(self):
        self.plan()
        self.cli("plan", "complete", "--verdict", "NEEDS_WORK")
        old = self.assert_owner("plan")
        self.cli("plan", "spawn", "--round", "1", "--triggered-by", "plan")
        self.assertEqual(self.state()["phases"]["plan"]["history"][0]["output_sha256"], old["output_sha256"])
        self.cli("plan", "complete", "--verdict", "BLOCKED")
        self.cli("plan", "spawn", "--round", "2", "--triggered-by", "plan", error="plan-respawn-exhausted")

    def test_cleanup_checks_source_and_preserves_atomicity(self):
        self.cli("cleanup", "spawn", "--round", "0", "--pre-sha", self.head)
        self.assert_owner("cleanup")
        args = ("transition", "--verdict", "PASS", "--post-sha", self.head,
                "--next-phase", "verify", "--next-round", "0", "--next-engine", "claude")
        (self.work / "source.txt").write_text("unverified change\n")
        self.cli("cleanup", *args, error="owner-cleanup-source-changed")
        self.git("add", "source.txt")
        self.cli("cleanup", *args, error="owner-cleanup-source-changed")
        (self.work / "source.txt").write_text("original\n")
        self.cli("cleanup", *args, error="owner-cleanup-source-changed")
        (self.work / "source.txt").write_text("unverified change\n")
        self.git("commit", "-qm", "unverified")
        self.cli("cleanup", *args, error="owner-cleanup-source-changed")
        # All mutations are in this disposable test fixture.
        self.git("reset", "--hard", self.head)
        self.cli("cleanup", *args)
        self.assertIsNotNone(self.state()["phases"]["verify"]["started_at"])

    def test_cleanup_repair_reenters_build_with_durability(self):
        self.cli("cleanup", "spawn", "--round", "0", "--pre-sha", self.head)
        (self.devlyn / "cleanup.findings.jsonl").write_text("")
        self.cli("cleanup", "transition", "--verdict", "FAIL", "--post-sha", self.head,
                 "--next-phase", "implement", "--next-round", "1", "--next-triggered-by", "cleanup",
                 "--next-engine", "claude")
        self.cli("implement", "transition", "--verdict", "PASS", "--next-phase", "build_gate",
                 "--next-round", "1", error="closure-durability")
        self.git("commit", "--allow-empty", "-qm", "chore(pipeline): implement fix round 1")
        self.cli("implement", "durability-enforce", "--round", "1", "--origin-phase", "cleanup")
        for phase in ("cleanup", "verify"):
            self.cli("implement", "transition", "--verdict", "PASS", "--next-phase", phase,
                     "--next-round", "1", error="owner-cleanup-repair-route")
        self.cli("implement", "transition", "--verdict", "PASS", "--next-phase", "build_gate", "--next-round", "1")
        self.assert_owner("build_gate")
        fixed_head = self.git("rev-parse", "HEAD")
        (self.devlyn / "spec-verify.results.json").write_text(
            json.dumps({"commands": [], "process_evidence": None}))
        self.cli("build_gate", "transition", "--verdict", "PASS", "--next-phase", "cleanup",
                 "--next-round", "1", "--next-pre-sha", fixed_head)
        (self.devlyn / "cleanup.findings.jsonl").write_text("\n")
        self.cli("cleanup", "transition", "--verdict", "PASS", "--post-sha", fixed_head,
                 "--next-phase", "verify", "--next-round", "1", "--next-engine", "claude")

    def test_cleanup_repair_bypass_still_requires_durability(self):
        self.cli("cleanup", "spawn", "--round", "0", "--pre-sha", self.head)
        (self.devlyn / "cleanup.findings.jsonl").write_text("")
        self.cli("cleanup", "transition", "--verdict", "FAIL", "--post-sha", self.head,
                 "--next-phase", "implement", "--next-round", "1", "--next-triggered-by", "cleanup",
                 "--next-engine", "claude")
        self.git("commit", "--allow-empty", "-qm", "chore(pipeline): implement fix round 1")
        pending = self.state()
        for bypasses, phase in (([], "build_gate"), (["cleanup"], "build_gate"),
                                (["build-gate"], "cleanup"), (["build-gate", "cleanup"], "verify")):
            with self.subTest(bypasses=bypasses):
                (self.devlyn / "closure-durability.round-1.json").unlink(missing_ok=True)
                self.save(dict(pending, bypasses=bypasses))
                for wrong_round in ("0", "2"):
                    self.cli("implement", "transition", "--verdict", "PASS", "--next-phase", phase,
                             "--next-round", wrong_round, error="owner-cleanup-repair-route")
                args = ("transition", "--verdict", "PASS", "--next-phase", phase,
                        "--next-round", "1", "--next-pre-sha", self.git("rev-parse", "HEAD"))
                self.cli("implement", *args, error="closure-durability")
                self.cli("implement", "durability-enforce", "--round", "1", "--origin-phase", "cleanup")
                self.cli("implement", *args)

    def test_historical_cleanup_cannot_take_owner_repair_edge(self):
        self.cli("cleanup", "spawn", "--round", "0", "--engine", "claude", "--pre-sha", self.head)
        for verdict in ("PASS", "FAIL"):
            self.cli("cleanup", "transition", "--verdict", verdict,
                     "--next-phase", "implement", "--next-round", "1", "--next-triggered-by", "cleanup",
                     "--next-engine", "claude", error="owner-cleanup-failed")
        self.cli("cleanup", "transition", "--verdict", "PASS", "--post-sha", self.head,
                 "--next-phase", "verify", "--next-round", "0", "--next-engine", "claude")

    def test_dirty_cleanup_can_fail_honestly_but_cannot_verify(self):
        self.cli("cleanup", "spawn", "--round", "0", "--pre-sha", self.head)
        opened = self.state_path.read_bytes()
        (self.work / "source.txt").write_text("BUILD left a tracked change\n")
        self.cli("cleanup", "transition", "--verdict", "FAIL", "--post-sha", self.head,
                 "--next-phase", "verify", "--next-round", "0", error="repair before VERIFY")
        self.cli("cleanup", "complete", "--verdict", "BLOCKED", "--post-sha", self.head)
        self.assertEqual(self.state()["phases"]["cleanup"]["verdict"], "BLOCKED")
        self.state_path.write_bytes(opened)
        self.cli("cleanup", "transition", "--verdict", "FAIL", "--post-sha", self.head,
                 "--next-phase", "implement", "--next-round", "1", "--next-triggered-by", "cleanup",
                 "--next-engine", "claude")
        self.assertEqual((self.work / "source.txt").read_text(), "BUILD left a tracked change\n")

    def test_final_untracked_delta_cannot_bypass_scope(self):
        (self.work / "user-existing.txt").write_text("preserve")
        (self.devlyn / "untracked.baseline").write_text("user-existing.txt\n")
        self.cli("cleanup", "spawn", "--round", "0", "--pre-sha", self.head)
        (self.work / "outside-plan.txt").write_text("leak")
        self.cli("cleanup", "complete", "--verdict", "PASS", "--post-sha", self.head,
                 error="owner-cleanup-untracked")
        (self.work / "outside-plan.txt").unlink()
        (self.devlyn / "untracked.baseline").unlink()
        self.cli("cleanup", "complete", "--verdict", "PASS", "--post-sha", self.head,
                 error="owner-cleanup-untracked")
        (self.devlyn / "untracked.baseline").write_text("user-existing.txt\n")
        self.cli("cleanup", "complete", "--verdict", "PASS", "--post-sha", self.head)
        self.assertEqual((self.work / "user-existing.txt").read_text(), "preserve")

    def test_owner_cleanup_does_not_replace_selected_worker(self):
        helper = runpy.run_path(str(SHARED / "state-phase-write.py"))
        (self.devlyn / "engines.json").write_text(json.dumps({"roles": {
            "worker": {"engine": "codex", "model": "gpt-6-astra", "effort": "high"}}}))
        state = self.state()
        frozen = helper["freeze_roles"](state, self.work, "codex")
        self.save(state)
        self.cli("cleanup", "spawn", "--round", "0", "--pre-sha", self.head)
        self.assert_owner("cleanup")
        self.assertEqual(self.state()["role_resolution"], frozen)
        self.cli("implement", "spawn", "--round", "0", "--engine", "claude",
                 error="role-selection-mismatch")


if __name__ == "__main__":
    unittest.main(verbosity=2)
