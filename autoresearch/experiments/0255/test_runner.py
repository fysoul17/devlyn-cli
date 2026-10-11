"""Synthetic integration of sealed receipts with the inherited runner gates."""
from contextlib import ExitStack
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


r = load("runner0255_integration", HERE / "runner.py")
fixture = load("fixtures0254_integration", HERE.parent / "0254/test_audit.py")


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="0255-runner-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        control = self.root / "control"
        for name in ("public", "oracle", "packages"):
            (control / name).mkdir(parents=True)
        r.write(str(control) + ".manifest.json", {"manifests": {
            name: {} for name in ("public", "oracle", "packages")}})
        catalogs = {"skills": [], "plugins": [], "mcp_servers": []}
        runtime = {"tasks_file": str(HERE.parent / "0238/tasks-draft.json"),
                   "image": "sha256:" + "a" * 64, "control": str(control), "phase": "smoke",
                   "output": str(self.root / "output"), "auth": str(self.root / "unused-auth"),
                   "sources": str(self.root), "account": [fixture.ACCOUNT],
                   "boot_catalogs": {"claude": {arm: catalogs for arm in ("A", "B", "S")}}}
        runtime_path = self.root / "runtime.json"
        r.write(runtime_path, runtime)
        self.app = r.Runner(runtime_path)
        self.out = self.root / "evidence"
        self.capture = fixture.Capture(self.out)
        self.capture.files["run/stdout"][0].update(deepcopy(catalogs))
        self.plan = {"config": "claude", "engine": "claude", "model": fixture.MODEL,
                     "effort": "max", "arm": "B", "name": "synthetic"}
        self.capture.files["plan.json"] = self.plan
        self.capture.seal()
        (self.out / "snapshot").mkdir()

    def run_capture(self, *, checked=None, delivered=None, owner=None, seal_errors=None,
                    preflight=None, quota=None, unchanged_error=None, policy_change=None,
                    policy_result=None, legacy_usage=None, legacy_closure=None,
                    after_seal=None, expected_code=None, arm="B", config="claude"):
        """Keep accounting, policy and catalogs real; never invoke a native process."""
        self.plan["arm"] = arm
        self.plan["config"] = self.plan["engine"] = config
        calls = []
        checks = checked if checked is not None else {"product_check_pass": True, "adjudication_needed": False}
        delivery = delivered if delivered is not None else {"passed": True}
        native = {"owner_status": "EXITED_0", "seconds": 1,
                  "identity": {"status": "MATCH"}, "teardown": "CLEAN"}
        if owner:
            native.update(owner)

        def invoke(*_):
            calls.append("native")
            return native

        def seal(*_):
            calls.append("seal")
            digest = self.capture.seal()
            if after_seal:
                after_seal()
            return digest, seal_errors or []

        def oracle(*_):
            calls.append("oracle")
            r.write(self.out / "checks.json", checks)
            return checks

        def deliver(*_):
            calls.append("delivery")
            return delivery

        with ExitStack() as stack:
            mocks = {}
            for label, target, attribute, kwargs in (
                ("validate", self.app, "validate", {"return_value": None}),
                ("preflight", self.app, "preflight", {"return_value": preflight or ({"fixed": True}, None)}),
                ("prepare", self.app, "prepare", {"return_value": self.out}),
                ("native", self.app.frame.cell_run, "run", {"side_effect": invoke}),
                ("seal", self.app.frame, "seal_after_teardown", {"side_effect": seal}),
                ("quota", self.app.frame.quota, "classify", {"return_value": quota or {"execution": []}}),
                ("unchanged", self.app, "unchanged", {"side_effect": unchanged_error}),
                ("locate", self.app.frame.locate, "locate", {"return_value": {"kind": "anchor", "path": "cell/work"}}),
                ("oracle", self.app.frame.check, "check", {"side_effect": oracle}),
                ("delivery", r.delivery, "check", {"side_effect": deliver}),
                ("assess", self.app, "assess", {"side_effect": AssertionError("assessor forbidden")}),
            ):
                mocks[label] = stack.enter_context(patch.object(target, attribute, **kwargs))
            if policy_change:
                original = r.policy.check
                def policy(*args):
                    result = original(*args)
                    result.update(deepcopy(policy_change))
                    return result
                stack.enter_context(patch.object(r.policy, "check", side_effect=policy))
            if policy_result is not None:
                stack.enter_context(patch.object(r.policy, "check", return_value=policy_result))
            if legacy_usage is not None:
                def old_usage(out):
                    r.write(out / "usage.json", legacy_usage)
                    return deepcopy(legacy_usage)
                stack.enter_context(patch.object(self.app.frame.usage, "record", side_effect=old_usage))
            if legacy_closure is not None:
                old_accounting = r.legacy.Runner.run.__globals__["accounting"]
                stack.enter_context(patch.object(old_accounting, "audit", return_value=legacy_closure))
            for attribute in ("run", "check_output", "Popen"):
                stack.enter_context(patch.object(subprocess, attribute,
                    side_effect=AssertionError("external process forbidden")))
            code = self.app.run("synthetic", "S2", arm, config)
        if expected_code is not None:
            self.assertEqual(code, expected_code)
        verdict = Path(self.app.runtime["output"]) / "verdict-synthetic.json"
        record = r.read(verdict) if verdict.exists() else None
        return code, record, calls, mocks

    def assert_stopped_before_grading(self, *, unknown=False, **kwargs):
        _, record, calls, mocks = self.run_capture(expected_code=2, **kwargs)
        self.assertEqual(record["status"], "STOP", record)
        self.assertNotIn("oracle", calls)
        self.assertNotIn("delivery", calls)
        mocks["oracle"].assert_not_called()
        mocks["delivery"].assert_not_called()
        mocks["assess"].assert_not_called()
        self.assertFalse((self.out / "checks.json").exists())
        self.assertNotIn("source_check_pass", record)
        if unknown:
            self.assertEqual(record["usage"], "UNKNOWN")
            self.assertIsNone(record["input_tokens"])
            self.assertIsNone(record["output_tokens"])
        return record

    def add_command(self, command, *, stdout=True, transcript=True):
        block = {"type": "tool_use", "id": "toolu_synthetic_command", "name": "Bash",
                 "input": {"command": command}}
        if transcript:
            self.capture.files[fixture.OWNER][0]["message"]["content"].append(deepcopy(block))
            self.capture.files[self.capture.indexed_file(1, "response")]["content"].append(deepcopy(block))
        if stdout:
            self.capture.files["run/stdout"][1]["message"]["content"].append(deepcopy(block))

    def test_terminal_receipts_pass_existing_gates_and_grade_once(self):
        _, record, calls, mocks = self.run_capture(expected_code=0)
        self.assertEqual((record["status"], record["usage"]), ("CHECKS_PASS", "COMPLETE"), record)
        self.assertEqual((record["input_tokens"], record["output_tokens"]), (63, 139))
        self.assertEqual(record["claude_accounting"]["status"], "MATCH")
        self.assertEqual(record["peer_policy"]["status"], "MATCH")
        self.assertEqual(calls, ["native", "seal", "oracle", "delivery"])
        for name in ("preflight", "native", "seal", "oracle", "delivery", "unchanged"):
            mocks[name].assert_called_once()
        self.assertTrue((self.out / "checked.json").exists())

    def test_nonterminal_anchors_with_exact_bodies_can_grade(self):
        for name in (fixture.OWNER, fixture.CHILD_FILE):
            for row in self.capture.files[name]:
                if row["type"] == "assistant":
                    row["message"]["stop_reason"] = None
                    row["message"]["usage"] = {"output_tokens": 6}
        _, record, calls, _ = self.run_capture(expected_code=0)
        self.assertEqual(record["status"], "CHECKS_PASS", record)
        self.assertEqual((record["input_tokens"], record["output_tokens"]), (63, 139))
        self.assertEqual(calls.count("oracle"), 1)
        self.assertEqual(calls.count("delivery"), 1)

    def test_native_user_string_content_is_normal_input_not_a_scope_error(self):
        self.capture.files[fixture.OWNER].insert(0, {"type": "user", "sessionId": fixture.SESSION,
            "uuid": "30000000-0000-4000-8000-000000000001",
            "message": {"role": "user", "content": "Ordinary synthetic owner prompt."}})
        _, record, calls, _ = self.run_capture(expected_code=0)
        self.assertEqual(record["status"], "CHECKS_PASS", record)
        self.assertEqual(calls.count("oracle"), 1)

    def test_malformed_assistant_content_string_stops_visibly_before_grading(self):
        self.capture.files[fixture.OWNER][0]["message"]["content"] = "malformed assistant content"
        record = self.assert_stopped_before_grading(unknown=True)
        self.assertTrue(record.get("reason"))

    def test_malformed_assistant_content_block_stops_visibly_before_grading(self):
        self.capture.files[fixture.OWNER][0]["message"]["content"] = ["malformed block"]
        record = self.assert_stopped_before_grading(unknown=True)
        self.assertTrue(record.get("reason"))

    def test_missing_terminal_receipt_stops_with_unknown_whole_cost(self):
        del self.capture.files[self.capture.indexed_file(2, "response")]
        self.assert_stopped_before_grading(unknown=True)

    def test_missing_message_anchor_stops_without_aggregate_allocation(self):
        self.capture.files[fixture.CHILD_FILE] = []
        self.assert_stopped_before_grading(unknown=True)

    def test_effective_policy_rejects_incomplete_peer_attempt(self):
        self.capture.files["cell/work/.devlyn/peer/attempt.json"] = {
            "schema": "devlyn-peer-v1", "engine": "claude", "model": fixture.MODEL, "effort": "max",
            "started_ns": 1000000000, "capture": "peer.json", "source_before": {"head": "same"}}
        record = self.assert_stopped_before_grading(unknown=True)
        self.assertNotEqual(record["peer_policy"]["status"], "MATCH")

    def test_direct_helper_without_attempt_is_rejected_by_effective_policy(self):
        self.add_command("python3 /repo/peer.py --engine claude --out missing")
        record = self.assert_stopped_before_grading(unknown=True)
        self.assertTrue(record["peer_policy"]["gaps"])

    def test_helper_only_in_terminal_body_without_attempt_is_unknown(self):
        response = self.capture.files[self.capture.indexed_file(3, "response")]
        response["content"].append({"type": "tool_use", "id": "toolu_body_helper", "name": "Bash",
            "input": {"command": "python3 /installed/_shared/peer.py --engine codex --out missing"}})
        self.assert_stopped_before_grading(unknown=True)

    def test_helper_only_in_child_transcript_without_attempt_is_unknown(self):
        self.capture.files[fixture.CHILD_FILE][0]["message"]["content"].append({
            "type": "tool_use", "id": "toolu_child_helper", "name": "Bash",
            "input": {"command": "python3 /installed/_shared/peer.py --engine codex --out missing"}})
        self.assert_stopped_before_grading(unknown=True)

    def test_quoted_helper_example_does_not_invent_a_dispatch(self):
        self.add_command("echo 'python3 /repo/peer.py --engine claude'")
        _, record, _, _ = self.run_capture(expected_code=0)
        self.assertEqual(record["status"], "CHECKS_PASS", record)

    def test_quoted_helper_only_in_terminal_body_does_not_invent_dispatch(self):
        response = self.capture.files[self.capture.indexed_file(3, "response")]
        response["content"].append({"type": "tool_use", "id": "toolu_body_example", "name": "Bash",
            "input": {"command": "echo 'python3 /installed/_shared/peer.py --engine codex'"}})
        _, record, _, _ = self.run_capture(expected_code=0)
        self.assertEqual(record["status"], "CHECKS_PASS", record)

    def test_independent_cli_command_without_result_in_stdout_is_unknown(self):
        self.add_command("claude -p 'synthetic extra attempt'", transcript=False)
        self.assert_stopped_before_grading(unknown=True)

    def test_independent_cli_command_without_result_in_transcript_is_unknown(self):
        self.add_command("bash /tmp/codex-monitored.sh exec synthetic", stdout=False)
        self.assert_stopped_before_grading(unknown=True)

    def test_independent_cli_command_only_in_terminal_body_is_unknown(self):
        response = self.capture.files[self.capture.indexed_file(3, "response")]
        response["content"].append({"type": "tool_use", "id": "toolu_body_only", "name": "Bash",
            "input": {"command": "claude -p 'unretained terminal-body attempt'"}})
        self.assert_stopped_before_grading(unknown=True)

    def test_independent_cli_command_in_child_transcript_is_unknown(self):
        self.capture.files[fixture.CHILD_FILE][0]["message"]["content"].append({
            "type": "tool_use", "id": "toolu_child_attempt", "name": "Bash",
            "input": {"command": "claude -p 'unretained child attempt'"}})
        self.assert_stopped_before_grading(unknown=True)

    def test_legacy_judge_attempt_without_result_is_unknown(self):
        self.capture.files["cell/work/.devlyn/verify-judge.r1.dispatch.json"] = {
            "roles": {"reviewer": {"decision": "dispatch", "engine": "claude"}}}
        self.assert_stopped_before_grading(unknown=True)

    def test_legacy_worker_attempt_without_result_is_unknown(self):
        self.capture.files["cell/work/.devlyn/job.invocation.1.json"] = {"synthetic": True}
        self.assert_stopped_before_grading(unknown=True)

    def test_extra_codex_native_session_is_unknown(self):
        self.capture.files["home/.codex/sessions/extra.jsonl"] = [
            {"type": "session_meta", "payload": {"id": "extra", "source": "exec"}},
            {"type": "turn_context", "payload": {"model": "gpt-6-astra", "effort": "max"}}]
        self.assert_stopped_before_grading(unknown=True)

    def test_codex_token_carrier_without_session_metadata_is_unknown(self):
        self.capture.files["home/.codex/sessions/extra.jsonl"] = [
            {"type": "event_msg", "payload": {"type": "token_count", "info": {
                "total_token_usage": {"input_tokens": 10, "output_tokens": 2}}}}]
        self.assert_stopped_before_grading(unknown=True)

    def test_corrupt_codex_carrier_is_not_zero_cost(self):
        self.capture.files["home/.codex/sessions/extra.jsonl"] = b"{incomplete\n"
        self.assert_stopped_before_grading(unknown=True)

    def test_sealed_foreign_carrier_removed_after_seal_is_not_forgotten(self):
        name = "home/.codex/sessions/extra.jsonl"
        self.capture.files[name] = [{"type": "event_msg", "payload": {"type": "token_count"}}]
        self.assert_stopped_before_grading(unknown=True, after_seal=lambda: (self.out / name).unlink())

    def test_noncanonical_malformed_trace_carrier_is_unknown(self):
        self.capture.files["cell/trace/partial/trace.jsonl"] = b"{incomplete\n"
        self.assert_stopped_before_grading(unknown=True)

    def test_sealed_trace_carrier_removed_after_seal_is_not_forgotten(self):
        name = "cell/trace/partial/trace.jsonl"
        self.capture.files[name] = b"{incomplete\n"
        self.assert_stopped_before_grading(unknown=True, after_seal=lambda: (self.out / name).unlink())

    def assert_scope_failure_retains_complete_receipts(self, error):
        with patch.object(self.app.frame.cell_run.evidence, "inventory", side_effect=error):
            record = self.assert_stopped_before_grading(unknown=True)
        report = r.read(self.out / "native-receipts.json")
        self.assertEqual(record["claude_accounting"], report)
        self.assertEqual(report["status"], "MATCH")
        self.assertEqual(len(report["messages"]), 3)
        self.assertEqual(report["reported_aggregate"], self.capture.expected)
        self.assertEqual({row["message_id"] for row in report["messages"]},
                         {"msg_synthetic_1", "msg_synthetic_2", "msg_synthetic_3"})

    def test_scope_value_error_retains_receipts_without_claiming_whole_cost(self):
        self.assert_scope_failure_retains_complete_receipts(ValueError("synthetic inventory defect"))

    def test_scope_io_error_retains_receipts_without_claiming_whole_cost(self):
        self.assert_scope_failure_retains_complete_receipts(OSError("synthetic inventory read failure"))

    def test_policy_unverified_is_unknown_before_product_checks(self):
        self.assert_stopped_before_grading(unknown=True, policy_change={"status": "UNVERIFIED", "gaps": ["synthetic missing evidence"]})

    def test_policy_mismatch_is_unknown_before_product_checks(self):
        self.assert_stopped_before_grading(unknown=True, policy_change={"status": "MISMATCH", "violations": ["synthetic route mismatch"]})

    def test_unclean_teardown_cannot_report_frozen_whole_cost(self):
        self.assert_stopped_before_grading(unknown=True, owner={"teardown": "FAILED"})

    def test_seal_failure_cannot_report_frozen_whole_cost(self):
        self.assert_stopped_before_grading(unknown=True, seal_errors=["synthetic missing evidence"])

    def test_identity_failure_stops_grading_but_keeps_complete_receipt_cost(self):
        record = self.assert_stopped_before_grading(owner={"identity": {"status": "MISMATCH"}})
        self.assertEqual((record["input_tokens"], record["output_tokens"]), (63, 139))

    def test_catalog_drift_stops_grading_but_keeps_complete_receipt_cost(self):
        self.capture.files["run/stdout"][0]["skills"] = ["unexpected"]
        record = self.assert_stopped_before_grading()
        self.assertEqual((record["input_tokens"], record["output_tokens"]), (63, 139))

    def test_catalog_missing_is_not_a_valid_empty_catalog(self):
        del self.capture.files["run/stdout"][0]["plugins"]
        self.assert_stopped_before_grading()

    def test_quota_fault_stops_grading_but_keeps_complete_receipt_cost(self):
        record = self.assert_stopped_before_grading(quota={"execution": ["synthetic auth fault"]})
        self.assertEqual((record["input_tokens"], record["output_tokens"]), (63, 139))

    def test_changed_input_stops_grading_but_keeps_complete_receipt_cost(self):
        record = self.assert_stopped_before_grading(unchanged_error=ValueError("synthetic changed input"))
        self.assertEqual((record["input_tokens"], record["output_tokens"]), (63, 139))

    def test_auth_refusal_prevents_preparation_and_native_dispatch(self):
        code, record, calls, mocks = self.run_capture(preflight=(None, "fixed-auth-refused"), expected_code=3)
        self.assertIsNone(record)
        self.assertEqual(calls, [])
        mocks["prepare"].assert_not_called()
        self.assertEqual(r.read(Path(self.app.runtime["output"]) / "not-dispatched-synthetic.json")["reason"], "fixed-auth-refused")

    def test_pair_arms_are_rejected_before_any_execution_gate(self):
        for arm in ("H", "P"):
            with self.subTest(arm=arm), patch.object(self.app, "validate") as validate, \
                    patch.object(self.app, "preflight") as preflight, patch.object(self.app, "prepare") as prepare, \
                    patch.object(self.app.frame.cell_run, "run") as native:
                with self.assertRaises(ValueError):
                    self.app.run("synthetic", "S2", arm, "claude")
                for call in (validate, preflight, prepare, native):
                    call.assert_not_called()

    def test_codex_uses_unchanged_legacy_path_including_pair_arms(self):
        for arm in ("A", "B", "S", "H", "P"):
            with self.subTest(arm=arm), patch.object(r.legacy.Runner, "run", return_value=71) as inherited, \
                    patch.object(self.app, "account", side_effect=AssertionError("Claude audit forbidden")):
                self.assertEqual(self.app.run("synthetic", "S2", arm, "codex"), 71)
                inherited.assert_called_once_with("synthetic", "S2", arm, "codex")

    def test_codex_inherited_orchestration_preserves_usage_and_outcome(self):
        """Exercise routing/orchestration with explicit receipts, not the Codex trace parser."""
        shutil.rmtree(self.out)
        self.out.mkdir()
        (self.out / "snapshot").mkdir()
        self.plan["model"] = "gpt-6-astra"
        self.capture.files = {"plan.json": self.plan, "run/stderr": b"", "run/stdout": [
            {"type": "thread.started", "thread_id": "synthetic-codex-owner"},
            {"type": "turn.completed", "usage": {"input_tokens": 125, "output_tokens": 17}}]}
        self.capture.seal()
        known = {"completeness": "COMPLETE", "gaps": [], "input_tokens": 125, "output_tokens": 17}
        closure = {"status": "MATCH", "gaps": [], "scope": "synthetic inherited closure"}
        pair = {"status": "MATCH", "gaps": [], "violations": [], "protocol_violations": [],
                "codex_roles": {"synthetic-codex-owner": ["owner", "synthetic-codex-owner"]},
                "claude_roles": {}}
        with patch.object(r.accounting, "audit", side_effect=AssertionError("0254 Claude audit forbidden")) as audit, \
                patch.object(self.app, "account", side_effect=AssertionError("new Claude account path forbidden")) as account:
            _, record, calls, _ = self.run_capture(config="codex", legacy_usage=known,
                legacy_closure=closure, policy_result=pair, expected_code=0)
        audit.assert_not_called()
        account.assert_not_called()
        self.assertEqual((record["status"], record["usage"]), ("CHECKS_PASS", "COMPLETE"))
        self.assertEqual((record["input_tokens"], record["output_tokens"]), (125, 17))
        self.assertEqual(record["claude_accounting"], closure)
        self.assertEqual(record["peer_policy"], pair)
        self.assertEqual(r.read(self.out / "usage.json"), known)
        self.assertEqual(r.read(self.out / "claude-accounting.json"), closure)
        self.assertFalse((self.out / "native-receipts.json").exists())
        self.assertEqual(calls, ["native", "seal", "oracle", "delivery"])

    def test_fixed_auth_preflight_and_prelaunch_check_remain_inherited(self):
        auth = r.legacy.legacy.auth
        self.assertIs(self.app.frame.cell_run.run.keywords["check_auth"], auth.preflight)
        with patch.object(auth, "preflight", return_value=(None, "fixed-auth-refused")) as preflight:
            self.assertEqual(self.app.preflight(), (None, "fixed-auth-refused"))
            preflight.assert_called_once_with(self.app.runtime)

    def test_new_runner_and_auditor_are_prospective_inputs(self):
        with patch.object(r.legacy.Runner, "inputs", return_value={"older": "sealed"}):
            inputs = self.app.inputs()
        self.assertEqual(inputs["older"], "sealed")
        for path in (HERE / "runner.py", HERE.parent / "0254/audit.py"):
            self.assertEqual(inputs[str(path)], r.digest(path))

    def test_protocol_violation_preserves_legacy_product_incomplete_classification(self):
        _, record, calls, _ = self.run_capture(policy_change={"protocol_violations": ["synthetic protocol defect"]}, expected_code=0)
        self.assertEqual(record["status"], "PRODUCT_INCOMPLETE")
        self.assertEqual(calls.count("oracle"), 1)
        self.assertEqual(calls.count("delivery"), 1)
        self.assertEqual((record["input_tokens"], record["output_tokens"]), (63, 139))

    def test_source_check_failure_remains_product_incomplete(self):
        _, record, calls, _ = self.run_capture(checked={"product_check_pass": False, "adjudication_needed": False}, expected_code=0)
        self.assertEqual(record["status"], "PRODUCT_INCOMPLETE")
        self.assertEqual(calls.count("delivery"), 1)
        self.assertEqual(record["usage"], "COMPLETE")

    def test_delivery_failure_remains_product_incomplete(self):
        _, record, _, _ = self.run_capture(delivered={"passed": False}, expected_code=0)
        self.assertEqual(record["status"], "PRODUCT_INCOMPLETE")
        self.assertEqual(record["usage"], "COMPLETE")

    def test_adjudication_is_reported_without_automatic_assessor(self):
        _, record, _, mocks = self.run_capture(checked={"product_check_pass": True, "adjudication_needed": True}, expected_code=0)
        self.assertEqual(record["status"], "ADJUDICATE")
        mocks["assess"].assert_not_called()


if __name__ == "__main__":
    unittest.main()
