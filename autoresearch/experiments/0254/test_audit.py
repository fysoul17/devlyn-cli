"""Black-box receipt checks using synthetic, sealed native-0253-shaped evidence."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("receipt_audit_0254", HERE / "audit.py")
AUDIT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDIT
SPEC.loader.exec_module(AUDIT)
MODEL = "claude-opus-5-5"
SESSION = "00000000-0000-4000-8000-000000000001"
CHILD = "a000000000000001"
TOOL = "toolu_synthetic_foreground"
ACCOUNT_UUID = "synthetic-account-uuid-never-publish"
ACCOUNT = hashlib.sha256(ACCOUNT_UUID.encode()).hexdigest()[:12]
PRIVATE_TEXT = "SYNTHETIC_PRIVATE_PROMPT_DO_NOT_PUBLISH"
BODY = "home/.claude/api-bodies"
OWNER = f"home/.claude/projects/-cell-work/{SESSION}.jsonl"
CHILD_FILE = f"home/.claude/projects/-cell-work/{SESSION}/subagents/agent-{CHILD}.jsonl"
META = CHILD_FILE.removesuffix(".jsonl") + ".meta.json"
KEYS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens",
        "output_tokens", "thinking_tokens")


def usage(noncache, created, read, output, thinking):
    return {"input_tokens": noncache, "cache_creation_input_tokens": created,
            "cache_read_input_tokens": read, "output_tokens": output,
            "output_tokens_details": {"thinking_tokens": thinking},
            "server_tool_use": {"web_search_requests": 0, "web_fetch_requests": 0}}


class Capture:
    """Only evidence is synthesized; no auditor internals are used."""

    def __init__(self, out):
        self.out = out
        self.files = {}
        self.owner_usage = usage(4, 40, 7, 80, 20)
        self.child_usage = usage(2, 10, 0, 59, 44)
        self.total_usage = usage(6, 50, 7, 139, 64)
        self.expected = dict(zip(KEYS, (6, 50, 7, 139, 64)))
        tool = {"type": "tool_use", "id": TOOL, "name": "Agent", "input": {
            "subagent_type": "general-purpose", "run_in_background": False,
            "description": "Synthetic child", "prompt": PRIVATE_TEXT}}
        owner1 = self.message(1, usage(2, 30, 0, 65, 20), "tool_use", [tool])
        child = self.message(2, self.child_usage, "end_turn", [{"type": "text", "text": PRIVATE_TEXT}])
        owner2 = self.message(3, usage(2, 10, 7, 15, 0), "end_turn", [{"type": "text", "text": PRIVATE_TEXT}])
        records = [self.anchor(owner1, 1), self.anchor(child, 2, CHILD), self.anchor(owner2, 3)]
        self.files[OWNER] = [records[0], {"type": "user", "sessionId": SESSION,
            "uuid": "00000000-0000-4000-8000-000000000099",
            "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": TOOL,
                                                        "content": PRIVATE_TEXT}]},
            "toolUseResult": {"status": "completed", "agentId": CHILD, "agentType": "general-purpose",
                "resolvedModel": MODEL, "totalToolUseCount": 0, "totalTokens": 71,
                "usage": deepcopy(self.child_usage)}}, records[2]]
        self.files[CHILD_FILE] = [records[1]]
        self.files[META] = {"agentType": "general-purpose", "toolUseId": TOOL, "spawnDepth": 1,
                            "requestShape": "foreground", "requestNonInteractive": True}
        stdout = [{"type": "system", "subtype": "init", "session_id": SESSION, "model": MODEL}]
        stdout.append(self.stream(records[0]))
        stdout.extend([
            {"type": "system", "subtype": "task_started", "session_id": SESSION,
             "task_id": CHILD, "tool_use_id": TOOL, "is_backgrounded": False},
            {"type": "system", "subtype": "task_updated", "session_id": SESSION,
             "task_id": CHILD, "patch": {"status": "completed", "end_time": 1}},
            {"type": "system", "subtype": "task_notification", "session_id": SESSION,
             "task_id": CHILD, "tool_use_id": TOOL, "status": "completed"},
            self.stream(records[2]),
            {"type": "result", "subtype": "success", "session_id": SESSION, "is_error": False,
             "result": PRIVATE_TEXT, "usage": deepcopy(self.owner_usage), "modelUsage": {MODEL: {
                 "inputTokens": 6, "cacheCreationInputTokens": 50, "cacheReadInputTokens": 7,
                 "outputTokens": 139, "thinkingTokens": 64, "webSearchRequests": 0,
                 "canonicalModel": MODEL, "provider": "firstParty", "costBasis": "list"}}}])
        self.files["run/stdout"] = stdout
        self.files["run/stderr"] = b""
        self.files[f"{BODY}/index.jsonl"] = []
        for number, record in enumerate(records, 1):
            request_file = f"00000000-0000-4000-8000-{number:012d}.request.json"
            response_file = f"req_synthetic_{number}.response.json"
            self.files[f"{BODY}/{request_file}"] = {"model": MODEL,
                "metadata": {"user_id": json.dumps({"session_id": SESSION, "account_uuid": ACCOUNT_UUID})},
                "output_config": {"effort": "max"}, "thinking": {"type": "adaptive"},
                "messages": [{"role": "user", "content": PRIVATE_TEXT}]}
            self.files[f"{BODY}/{response_file}"] = deepcopy(record["message"])
            self.files[f"{BODY}/index.jsonl"].append({"timestamp": "2026-10-11T00:00:00Z",
                "session_id": SESSION, "query_source": "agent:builtin:general-purpose" if number == 2 else "sdk",
                "model": MODEL, "request_id": record["requestId"], "message_id": record["message"]["id"],
                "message_uuid": record["uuid"], "request_file": request_file, "response_file": response_file})

    @staticmethod
    def message(number, counts, stop, content):
        return {"id": f"msg_synthetic_{number}", "type": "message", "role": "assistant",
                "model": MODEL, "stop_reason": stop, "content": content, "usage": deepcopy(counts)}

    @staticmethod
    def anchor(message, number, agent=None):
        row = {"type": "assistant", "sessionId": SESSION,
               "uuid": f"10000000-0000-4000-8000-{number:012d}",
               "requestId": f"req_synthetic_{number}", "message": message}
        if agent:
            row["agentId"] = agent
        return row

    @staticmethod
    def stream(record):
        result = {"type": "assistant", "session_id": SESSION, "uuid": record["uuid"],
                  "request_id": record["requestId"],
                  "parent_tool_use_id": None, "message": deepcopy(record["message"])}
        result["message"]["stop_reason"] = None
        result["message"]["usage"]["output_tokens"] = 6
        result["message"]["usage"]["output_tokens_details"]["thinking_tokens"] = 0
        return result

    def indexed_file(self, number, kind):
        row = self.files[f"{BODY}/index.jsonl"][number - 1]
        return f"{BODY}/{row[kind + '_file']}"

    def result(self):
        return self.files["run/stdout"][-1]

    def seal(self):
        for name, value in self.files.items():
            path = self.out / name
            path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(value, bytes):
                raw = value
            elif name.endswith(".jsonl") or name == "run/stdout":
                raw = ("".join(json.dumps(row) + "\n" for row in value)).encode()
            else:
                raw = (json.dumps(value) + "\n").encode()
            path.write_bytes(raw)
        manifest = {"failures": [], "files": {
            name: hashlib.sha256((self.out / name).read_bytes()).hexdigest() for name in self.files}}
        path = self.out / "evidence.manifest.json"
        path.write_text(json.dumps(manifest) + "\n")
        return hashlib.sha256(path.read_bytes()).hexdigest()


class ReceiptAuditTests(unittest.TestCase):
    def exercise(self, change=None, after_seal=None, expected="UNKNOWN", expectation=None):
        with tempfile.TemporaryDirectory(prefix="0254-receipt-") as directory:
            fixture = Capture(Path(directory))
            if change:
                change(fixture)
            digest = fixture.seal()
            if after_seal:
                after_seal(fixture)
            args = dict(manifest_sha256=digest, model=MODEL, effort="max", account=ACCOUNT)
            if expectation:
                args.update(expectation)
            report = AUDIT.audit(fixture.out, **args)
            self.assertEqual(report["status"], expected, report)
            self.assertIsInstance(report["gaps"], list)
            self.assertIsInstance(report["messages"], list)
            serialized = json.dumps(report)
            self.assertNotIn(PRIVATE_TEXT, serialized)
            self.assertNotIn(ACCOUNT_UUID, serialized)
            if expected == "MATCH":
                self.assertEqual(report["gaps"], [])
                self.assertEqual({key: report["totals"][key] for key in KEYS}, fixture.expected)
                self.assertEqual(len(report["messages"]), 3)
            else:
                self.assertTrue(report["gaps"], report)
                self.assertIsNone(report["totals"], report)
                self.assertIsNone(report.get("input_tokens"), report)
                self.assertIsNone(report.get("output_tokens"), report)
            return report

    def test_healthy_owner_and_foreground_child(self):
        self.exercise(expected="MATCH")

    def test_nonterminal_anchors_use_exact_terminal_bodies(self):
        def change(f):
            for name in (OWNER, CHILD_FILE):
                for row in f.files[name]:
                    if row["type"] == "assistant":
                        row["message"]["stop_reason"] = None
                        row["message"]["usage"]["output_tokens"] = 6
                        row["message"]["usage"]["output_tokens_details"]["thinking_tokens"] = 0
        self.exercise(change, expected="MATCH")

    def test_nonterminal_missing_optional_counters_are_not_zero_fills(self):
        def change(f):
            row = f.files[CHILD_FILE][0]
            row["message"]["stop_reason"] = None
            row["message"]["usage"] = {}
        self.exercise(change, expected="MATCH")

    def test_repeated_blocks_and_distinct_block_uuids_count_once(self):
        def change(f):
            original = f.files[CHILD_FILE][0]
            earlier = deepcopy(original)
            earlier["uuid"] = "20000000-0000-4000-8000-000000000002"
            f.files[CHILD_FILE] = [earlier, original, deepcopy(original)]
        self.exercise(change, expected="MATCH")

    def test_missing_each_receipt_carrier(self):
        for kind in ("request", "response", "index", "anchor"):
            with self.subTest(kind=kind):
                def change(f, kind=kind):
                    if kind in ("request", "response"):
                        del f.files[f.indexed_file(2, kind)]
                    elif kind == "index":
                        f.files[f"{BODY}/index.jsonl"].pop(1)
                    else:
                        f.files[CHILD_FILE] = []
                self.exercise(change)

    def test_orphan_attempt_and_response(self):
        for kind in ("request", "response"):
            with self.subTest(kind=kind):
                self.exercise(lambda f: f.files.update({f"{BODY}/orphan.{kind}.json":
                                                       deepcopy(f.files[f.indexed_file(2, kind)])}))

    def test_duplicate_index_binding(self):
        self.exercise(lambda f: f.files[f"{BODY}/index.jsonl"].append(
            deepcopy(f.files[f"{BODY}/index.jsonl"][1])))

    def test_reused_index_identity_components(self):
        for key in ("request_id", "message_id", "message_uuid", "request_file", "response_file"):
            with self.subTest(key=key):
                def change(f, key=key):
                    rows = f.files[f"{BODY}/index.jsonl"]
                    rows[1][key] = rows[0][key]
                self.exercise(change)

    def test_wrong_index_uuid_or_query_source(self):
        for key, value in (("message_uuid", "wrong-uuid"), ("query_source", "sdk")):
            with self.subTest(key=key):
                self.exercise(lambda f: f.files[f"{BODY}/index.jsonl"][1].update({key: value}))

    def test_wrong_session_in_each_carrier(self):
        for carrier in ("anchor", "index", "request", "init", "result", "lifecycle"):
            with self.subTest(carrier=carrier):
                def change(f, carrier=carrier):
                    if carrier == "anchor": f.files[CHILD_FILE][0]["sessionId"] = "other"
                    elif carrier == "index": f.files[f"{BODY}/index.jsonl"][1]["session_id"] = "other"
                    elif carrier == "request":
                        req = f.files[f.indexed_file(2, "request")]
                        req["metadata"]["user_id"] = json.dumps({"session_id": "other", "account_uuid": ACCOUNT_UUID})
                    elif carrier == "init": f.files["run/stdout"][0]["session_id"] = "other"
                    elif carrier == "result": f.result()["session_id"] = "other"
                    else: f.files["run/stdout"][2]["session_id"] = "other"
                self.exercise(change)

    def test_wrong_model_in_each_carrier(self):
        for carrier in ("anchor", "index", "request", "response", "init"):
            with self.subTest(carrier=carrier):
                def change(f, carrier=carrier):
                    if carrier == "anchor": f.files[CHILD_FILE][0]["message"]["model"] = "other"
                    elif carrier == "index": f.files[f"{BODY}/index.jsonl"][1]["model"] = "other"
                    elif carrier == "init": f.files["run/stdout"][0]["model"] = "other"
                    else: f.files[f.indexed_file(2, carrier)]["model"] = "other"
                self.exercise(change)

    def test_wrong_effort_and_account(self):
        self.exercise(lambda f: f.files[f.indexed_file(2, "request")]["output_config"].update(effort="high"))
        self.exercise(expectation={"account": "0" * 12})
        self.exercise(expectation={"effort": "high"})

    def test_unsealed_or_changed_evidence(self):
        self.exercise(after_seal=lambda f: (f.out / "run/stdout").write_text("{}\n"))
        self.exercise(after_seal=lambda f: (f.out / f"{BODY}/orphan.request.json").write_text("{}\n"))
        self.exercise(expectation={"manifest_sha256": "0" * 64})

    def test_sealed_unindexed_attempt_removed_after_seal_is_not_forgotten(self):
        orphan = f"{BODY}/orphan.request.json"
        self.exercise(lambda f: f.files.update({orphan: deepcopy(f.files[f.indexed_file(2, "request")])}),
                      after_seal=lambda f: (f.out / orphan).unlink())

    def test_sealed_transcript_or_metadata_removed_after_seal(self):
        for name in (CHILD_FILE.replace(CHILD, "sealed-other"), META.replace(CHILD, "sealed-other")):
            with self.subTest(name=name):
                self.exercise(lambda f: f.files.update({name: deepcopy(f.files[CHILD_FILE if name.endswith(".jsonl") else META])}),
                              after_seal=lambda f: (f.out / name).unlink())
        self.exercise(after_seal=lambda f: (f.out / CHILD_FILE).unlink())
        self.exercise(after_seal=lambda f: (f.out / META).unlink())

    def test_orphan_metadata_prevents_closed_child_inventory(self):
        self.exercise(lambda f: f.files.update({META.replace(CHILD, "orphan-child"): deepcopy(f.files[META])}))

    def test_parent_body_directory_symlink_is_unknown(self):
        def change(f):
            body = f.out / BODY
            relocated = f.out / "relocated-api-bodies"
            body.rename(relocated)
            body.symlink_to(relocated, target_is_directory=True)
        self.exercise(after_seal=change)

    def test_terminal_conflict_cannot_be_overridden_by_later_good_copy(self):
        for defect in ("counter", "stop", "missing", "model"):
            with self.subTest(defect=defect):
                def change(f, defect=defect):
                    bad = deepcopy(f.files[CHILD_FILE][0])
                    if defect == "counter": bad["message"]["usage"]["output_tokens"] += 1
                    elif defect == "stop": bad["message"]["stop_reason"] = "max_tokens"
                    elif defect == "missing": del bad["message"]["usage"]["input_tokens"]
                    else: bad["message"]["model"] = "other"
                    f.files[CHILD_FILE].insert(0, bad)
                self.exercise(change)

    def test_malformed_terminal_and_body_counters(self):
        for carrier in ("anchor", "response"):
            for value in (-1, True, "59", 59.0, None):
                with self.subTest(carrier=carrier, value=value):
                    def change(f, carrier=carrier, value=value):
                        msg = f.files[CHILD_FILE][0]["message"] if carrier == "anchor" else f.files[f.indexed_file(2, "response")]
                        msg["usage"]["output_tokens"] = value
                    self.exercise(change)

    def test_thinking_must_fit_output(self):
        self.exercise(lambda f: f.files[f.indexed_file(2, "response")]["usage"]["output_tokens_details"].update(thinking_tokens=60))

    def test_malformed_present_progress_is_not_ignored(self):
        for value in (-1, True, "6", 6.0):
            with self.subTest(value=value):
                def change(f, value=value):
                    f.files[CHILD_FILE][0]["message"]["stop_reason"] = None
                    f.files[CHILD_FILE][0]["message"]["usage"]["output_tokens"] = value
                self.exercise(change)

    def test_terminal_response_required(self):
        self.exercise(lambda f: f.files[f.indexed_file(2, "response")].update(stop_reason=None))

    def test_unobserved_pause_turn_is_outside_successful_path_contract(self):
        def change(f):
            f.files[CHILD_FILE][0]["message"]["stop_reason"] = "pause_turn"
            f.files[f.indexed_file(2, "response")]["stop_reason"] = "pause_turn"
        self.exercise(change)

    def test_corrupt_json_and_duplicate_keys_are_unknown(self):
        for carrier in ("request", "response", "metadata", "index", "transcript", "stdout"):
            for raw in (b"{broken}\n", b'{"type":"assistant","type":"assistant"}\n'):
                with self.subTest(carrier=carrier, raw=raw):
                    def change(f, carrier=carrier, raw=raw):
                        name = f.indexed_file(2, carrier) if carrier in ("request", "response") else {
                            "metadata": META, "index": f"{BODY}/index.jsonl", "transcript": CHILD_FILE,
                            "stdout": "run/stdout"}[carrier]
                        f.files[name] = raw
                    self.exercise(change)

    def test_duplicate_nested_account_metadata_keys(self):
        self.exercise(lambda f: f.files[f.indexed_file(2, "request")]["metadata"].update(
            user_id='{"account_uuid":"synthetic-account-uuid-never-publish","account_uuid":"other","session_id":"' + SESSION + '"}'))

    def test_partial_jsonl_is_unknown_even_when_valid_json(self):
        for name in ("run/stdout", OWNER, CHILD_FILE, f"{BODY}/index.jsonl"):
            with self.subTest(name=name):
                def change(f, name=name):
                    f.files[name] = "\n".join(json.dumps(row) for row in f.files[name]).encode()
                self.exercise(change)

    def test_child_mapping_is_proven_not_labelled(self):
        for defect in ("agent", "meta_tool", "meta_type", "tool_id", "tool_name", "background",
                       "override", "spawn_depth", "request_shape", "missing_meta", "missing_tool"):
            with self.subTest(defect=defect):
                def change(f, defect=defect):
                    tool = f.files[OWNER][0]["message"]["content"][0]
                    if defect == "agent": f.files[CHILD_FILE][0]["agentId"] = "other"
                    elif defect == "meta_tool": f.files[META]["toolUseId"] = "other"
                    elif defect == "meta_type": f.files[META]["agentType"] = "other"
                    elif defect == "tool_id": tool["id"] = "other"
                    elif defect == "tool_name": tool["name"] = "Task"
                    elif defect == "background": tool["input"]["run_in_background"] = True
                    elif defect == "override": tool["input"]["model"] = "other"
                    elif defect == "spawn_depth": f.files[META]["spawnDepth"] = 2
                    elif defect == "request_shape": f.files[META]["requestShape"] = "background"
                    elif defect == "missing_meta": del f.files[META]
                    else: tool["name"] = "Read"
                self.exercise(change)

    def test_incomplete_or_wrong_child_lifecycle(self):
        for defect in ("start_missing", "start_background", "start_task", "start_tool", "notification_missing",
                       "notification_failed", "update_failed", "result_missing", "result_agent", "result_model",
                       "result_status", "result_usage", "result_total"):
            with self.subTest(defect=defect):
                def change(f, defect=defect):
                    events = f.files["run/stdout"]
                    result = f.files[OWNER][1]["toolUseResult"]
                    if defect == "start_missing": events.pop(2)
                    elif defect == "start_background": events[2]["is_backgrounded"] = True
                    elif defect == "start_task": events[2]["task_id"] = "other"
                    elif defect == "start_tool": events[2]["tool_use_id"] = "other"
                    elif defect == "notification_missing": events.pop(4)
                    elif defect == "notification_failed": events[4]["status"] = "failed"
                    elif defect == "update_failed": events[3]["patch"]["status"] = "failed"
                    elif defect == "result_missing": del f.files[OWNER][1]["toolUseResult"]
                    elif defect == "result_agent": result["agentId"] = "other"
                    elif defect == "result_model": result["resolvedModel"] = "other"
                    elif defect == "result_status": result["status"] = "killed"
                    elif defect == "result_usage": result["usage"]["output_tokens"] += 1
                    else: result["totalTokens"] += 1
                self.exercise(change)

    def test_extra_owner_or_child_transcript_is_unknown(self):
        self.exercise(lambda f: f.files.update({OWNER.replace(SESSION, "extra-owner"): deepcopy(f.files[OWNER])}))
        self.exercise(lambda f: f.files.update({CHILD_FILE.replace(CHILD, "extra-child"): deepcopy(f.files[CHILD_FILE])}))

    def test_extra_result_or_init_is_unknown(self):
        for index in (0, -1):
            with self.subTest(index=index):
                self.exercise(lambda f: f.files["run/stdout"].append(deepcopy(f.files["run/stdout"][index])))

    def test_retry_error_and_cancel_events_are_unknown(self):
        events = [{"type": "system", "subtype": "api_retry"},
                  {"type": "system", "subtype": "api_error"},
                  {"type": "error"},
                  {"type": "assistant", "isApiErrorMessage": True},
                  {"type": "user", "message": {"role": "user", "content": [
                      {"type": "text", "text": "[Request interrupted by user]"}]}}]
        for event in events:
            for carrier in ("run/stdout", OWNER, CHILD_FILE):
                with self.subTest(event=event, carrier=carrier):
                    self.exercise(lambda f: f.files[carrier].insert(1, deepcopy(event)))

    def test_native_result_error_is_unknown(self):
        self.exercise(lambda f: f.result().update(is_error=True))
        self.exercise(lambda f: f.result().update(subtype="error_during_execution"))

    def test_whole_aggregate_and_owner_scope_are_distinct(self):
        self.exercise(lambda f: f.result()["modelUsage"][MODEL].update(outputTokens=80))
        self.exercise(lambda f: f.result().update(usage=deepcopy(f.total_usage)))
        self.exercise(lambda f: f.result()["modelUsage"].update(other=deepcopy(f.result()["modelUsage"][MODEL])))

    def test_unknown_retains_separately_labelled_complete_receipts_and_native_reports(self):
        report = self.exercise(lambda f: f.result()["modelUsage"][MODEL].update(outputTokens=140))
        self.assertEqual(len(report["messages"]), 3)
        self.assertEqual(report["reported_aggregate"], dict(zip(KEYS, (6, 50, 7, 140, 64))))
        self.assertEqual(report["reported_owner_usage"], dict(zip(KEYS, (4, 40, 7, 80, 20))))
        self.assertEqual({row["message_id"] for row in report["messages"]},
                         {"msg_synthetic_1", "msg_synthetic_2", "msg_synthetic_3"})
        for row in report["messages"]:
            self.assertEqual(set(row["usage"]), set(KEYS))

    def test_aggregate_agreement_does_not_replace_absent_anchor(self):
        self.exercise(lambda f: f.files.update({CHILD_FILE: []}))

    def test_stdout_conflicting_terminal_is_not_ignored(self):
        def change(f):
            event = f.files["run/stdout"][1]
            event["message"]["stop_reason"] = "tool_use"
            event["message"]["usage"] = usage(2, 30, 0, 66, 20)
        self.exercise(change)

    def test_stdout_identity_conflicts_are_not_ignored(self):
        for key, value in (("request_id", "req_wrong"), ("uuid", "wrong-uuid"),
                           ("parent_tool_use_id", "toolu_wrong"), ("agent_id", "wrong-agent")):
            with self.subTest(key=key):
                self.exercise(lambda f: f.files["run/stdout"][1].update({key: value}))

    def test_stdout_requires_request_and_block_identity(self):
        for key in ("request_id", "uuid"):
            with self.subTest(key=key):
                self.exercise(lambda f: f.files["run/stdout"][1].pop(key))


if __name__ == "__main__":
    unittest.main()
