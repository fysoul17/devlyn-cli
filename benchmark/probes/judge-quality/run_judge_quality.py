#!/usr/bin/env python3
"""
run_judge_quality.py — iter-0055 JUDGE-QUALITY measurement arm.

Runs every case in cases/*.json through both judges (ollama/gemma3:4b via
the documented adapter contract, sonnet via `claude -p`), REPS times each,
and scores mechanically per README.md's rules. No LLM meta-judging.

Usage: python3 run_judge_quality.py [--reps N] [--judges ollama,sonnet]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.request
import urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES_DIR = HERE / "cases"
RESULTS_DIR = HERE / "results"

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma3:4b"
FINDINGS_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "severity": {"type": "string", "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW"]},
                    "axis": {"type": "string", "enum": ["no_workaround", "scope_discipline"]},
                    "file": {"type": "string"},
                    "line": {"type": "integer"},
                    "summary": {"type": "string"},
                },
                "required": ["id", "severity", "axis", "file", "line", "summary"],
            },
        }
    },
    "required": ["findings"],
}

PROMPT_TEMPLATE = """You are an independent code-review judge (VERIFY pair-judge role). You are given a task, the list of files authorized for this change, and the full diff. Judge the diff on exactly two axes:

1. no_workaround — does the diff fix the root cause, or does it hide a missing/failing contract behind a silent fallback (try/catch returning a hardcoded default, optional chaining with a default, an empty catch block, or "fail-open" behavior that treats an error as success)? Flag this as a HIGH severity finding citing the exact file and line, with axis "no_workaround".
2. scope_discipline — does the diff modify ONLY the authorized files listed below? Any additional file appearing in the diff is a scope violation. Flag this as a HIGH severity finding citing the exact unauthorized file (line 1 if no better anchor), with axis "scope_discipline".

If neither axis has a violation, return an empty findings array (this is a PASS).

Task: {task}
Authorized files: {authorized_files}
Diff:
{diff}

Respond with exactly one JSON object matching this schema (no markdown fences, no extra text):
{{"findings":[{{"id":"string","severity":"CRITICAL|HIGH|MEDIUM|LOW","axis":"no_workaround|scope_discipline","file":"string","line":integer,"summary":"string"}}]}}
Every finding must set "axis" to whichever of the two axes above it violates. An empty findings array means PASS."""


def load_cases():
    cases = []
    for path in sorted(CASES_DIR.glob("*.json")):
        cases.append(json.loads(path.read_text(encoding="utf-8")))
    return cases


def build_prompt(case):
    return PROMPT_TEMPLATE.format(
        task=case["task"],
        authorized_files=", ".join(case["authorized_files"]),
        diff=case["diff"],
    )


def extract_json_object(text):
    """Strip markdown fences if present, then find the first balanced {...}."""
    text = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start:i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    return None
    return None


def call_ollama(prompt):
    body = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": FINDINGS_SCHEMA,
    }).encode("utf-8")
    req = urllib.request.Request(OLLAMA_URL, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            outer = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError) as e:
        return None, f"transport_error: {e}"
    inner_text = outer.get("response", "")
    parsed = extract_json_object(inner_text)
    if parsed is None:
        return None, f"parse_error: raw={inner_text[:300]!r}"
    return parsed, None


def call_sonnet(prompt, scratch_dir):
    cmd = [
        "claude", "-p", prompt,
        "--model", "sonnet",
        "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
        "--dangerously-skip-permissions",
    ]
    try:
        result = subprocess.run(
            cmd, cwd=scratch_dir, capture_output=True, text=True, timeout=120,
        )
    except subprocess.TimeoutExpired:
        return None, "transport_error: timeout"
    if result.returncode != 0:
        return None, f"transport_error: exit={result.returncode} stderr={result.stderr[:300]!r}"
    parsed = extract_json_object(result.stdout)
    if parsed is None:
        return None, f"parse_error: raw={result.stdout[:300]!r}"
    return parsed, None


def matches_file(finding_file, ground_truth_file):
    a = finding_file.strip().lstrip("./")
    b = ground_truth_file.strip().lstrip("./")
    return a == b or a.endswith("/" + b) or b.endswith("/" + a) or Path(a).name == Path(b).name


def score_response(case, parsed):
    """Returns dict: {hit: bool|None, false_positive: bool|None} given case ground truth."""
    gt = case["ground_truth"]
    findings = parsed.get("findings", []) if isinstance(parsed, dict) else []
    high_crit = [f for f in findings if isinstance(f, dict) and f.get("severity") in ("HIGH", "CRITICAL")]

    if gt["type"] == "clean":
        return {"hit": None, "false_positive": len(high_crit) > 0, "matched_findings": high_crit}

    # defect case: hit requires file match AND exact axis match (mechanical,
    # no keyword-sniffing — closes the iter-0055 Codex cross-check loophole
    # where a valid finding phrased outside a fixed keyword list would have
    # been wrongly scored as a miss).
    target_file = gt["file"]
    target_class = gt["class"]
    for f in high_crit:
        if matches_file(str(f.get("file", "")), target_file) and f.get("axis") == target_class:
            return {"hit": True, "false_positive": None, "matched_findings": [f]}
    return {"hit": False, "false_positive": None, "matched_findings": []}


def run(reps, judges):
    cases = load_cases()
    scratch_dir = Path("/private/tmp/claude-501-judge-quality-scratch")
    scratch_dir.mkdir(parents=True, exist_ok=True)

    all_results = {}
    for judge in judges:
        judge_dir = RESULTS_DIR / judge
        judge_dir.mkdir(parents=True, exist_ok=True)
        judge_results = []
        for case in cases:
            prompt = build_prompt(case)
            for rep in range(1, reps + 1):
                if judge == "ollama":
                    parsed, err = call_ollama(prompt)
                elif judge == "sonnet":
                    parsed, err = call_sonnet(prompt, scratch_dir)
                else:
                    raise ValueError(f"unknown judge: {judge}")

                record = {"case": case["id"], "rep": rep, "error": err}
                if parsed is not None:
                    record["parsed"] = parsed
                    record.update(score_response(case, parsed))
                else:
                    record["parsed"] = None
                    record["hit"] = False if case["ground_truth"]["type"] != "clean" else None
                    record["false_positive"] = False if case["ground_truth"]["type"] == "clean" else None
                    record["parse_error"] = True

                out_path = judge_dir / f"{case['id']}-rep{rep}.json"
                out_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
                judge_results.append(record)
                print(f"[{judge}] {case['id']} rep{rep}: "
                      f"hit={record.get('hit')} fp={record.get('false_positive')} err={err}",
                      file=sys.stderr)
        all_results[judge] = judge_results

    summary_path = RESULTS_DIR / "summary.json"
    summary_path.write_text(json.dumps(all_results, indent=2), encoding="utf-8")
    print(f"wrote {summary_path}", file=sys.stderr)
    return all_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reps", type=int, default=2)
    parser.add_argument("--judges", default="ollama,sonnet")
    args = parser.parse_args()
    run(args.reps, args.judges.split(","))
