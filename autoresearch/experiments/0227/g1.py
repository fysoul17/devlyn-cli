#!/usr/bin/env python3
"""0227 gate G1 (model-free): the fix commit's structured-output path against 0226's Claude outputs.

Usage: python3 -B g1.py <checkout of the fix commit F>
Reads 0226's sealed rounds read-only. Exit 0 = every G1 expectation holds.
"""
import json
from pathlib import Path
import runpy
import sys

sys.dont_write_bytecode = True
F = Path(sys.argv[1]).resolve() / "config/skills/_shared"
ROUNDS = Path("/Users/Shared/devlyn-vr/rounds")
EVIDENCE = runpy.run_path(str(F / "judge-role-evidence.py"))
PARSER = runpy.run_path(str(F / "judge-output-parser.py"))
ENVELOPE = {"type": "result", "subtype": "success", "is_error": False, "stop_reason": "end_turn",
            "session_id": "g1", "modelUsage": {"claude-opus-5-5": {}}}
failures = []


def render(judgment):
    raw = json.dumps({**ENVELOPE, "structured_output": judgment}).encode()
    return EVIDENCE["claude_result"](raw, 0)[0]


def parse(text, source):
    return PARSER["judge_findings"](*PARSER["collect_text"](text, source))


accepted = rejected = 0
for path in sorted(ROUNDS.glob("*/work/.devlyn/claude-judge.r0.stdout")):
    text = path.read_text(encoding="utf-8")
    try:
        found, summary = parse(text, path)
    except SystemExit:
        rejected += 1  # stays rejected on the text path: F leaves the parser untouched
        continue
    accepted += 1
    judgment = {"findings": found, "verdict": summary["verdict"]}
    try:
        again, summary_again = parse(render(judgment).decode(), path)
    except (ValueError, SystemExit) as exc:
        failures.append(f"{path.parent.parent.parent.name}: does not validate or render: {exc}")
        continue
    if again != found or summary_again["verdict"] != summary["verdict"]:
        failures.append(f"{path.parent.parent.parent.name}: round trip changed findings or verdict")

if (accepted, rejected) != (61, 3):
    failures.append(f"expected 61 accepted and 3 rejected 0226 Claude outputs, found {accepted} and {rejected}")

message = "quotes `code`, a \\ backslash before `x`, \"quotes\", a newline\nand non-ASCII é 漢 😀 \u0085 \u2028 \u2029"
finding = {"id": "F1", "rule_id": "r", "severity": "LOW", "file": "a.md", "line": 3, "message": message,
           "criterion_ref": "spec", "confidence": "high"}
fixture, _ = parse(render({"findings": [finding], "verdict": "PASS_WITH_ISSUES"}).decode(), Path("fixture"))
if fixture[0]["message"] != message:
    failures.append("fixture strings did not come back byte-exact")

negatives = [
    ("session_id", ""), ("type", "assistant"),
    ("subtype", "error_max_structured_output_retries"), ("subtype", "error_during_execution"), ("is_error", True),
    ("structured_output", None), ("structured_output", "PASS"), ("structured_output", {"verdict": "PASS"}),
    ("structured_output", {"findings": [], "verdict": "MAYBE"}),
    ("structured_output", {"findings": [{"severity": "HIGH"}], "verdict": "NEEDS_WORK"}),
]
for field, value in negatives:
    try:
        EVIDENCE["claude_result"](json.dumps({**ENVELOPE, "structured_output": {"findings": [], "verdict": "PASS"},
                                              field: value}).encode(), 0)
    except ValueError:
        continue
    failures.append(f"envelope negative accepted: {field}={value!r}")
for raw in (b'{"type": "result", "subtype": "success"', b'{"type": "result", "type": "result"}'):
    try:
        EVIDENCE["claude_result"](raw, 0)
    except ValueError:
        continue
    failures.append(f"truncated or duplicate-key envelope accepted: {raw!r}")
binding = {**finding, "severity": "MEDIUM", "verdict_binding": True}
try:
    parse(render({"findings": [binding], "verdict": "PASS"}).decode(), Path("binding-pass"))
except SystemExit:
    pass
else:
    failures.append("a verdict-binding finding with PASS was accepted")

print(json.dumps({"accepted_round_trips": accepted, "rejected_stay_rejected": rejected,
                  "failures": failures}, indent=1))
sys.exit(1 if failures else 0)
