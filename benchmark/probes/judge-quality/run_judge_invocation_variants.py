#!/usr/bin/env python3
"""
run_judge_invocation_variants.py — iter-0056 invocation-reshape arm.

Re-runs the UNCHANGED 12-case corpus (cases/*.json) through 3 reshaped
gemma3:4b invocation variants (V1 calibration framing, V2 single-call
file-enumeration, V3 two-pass triage) and scores with the UNCHANGED
mechanical scorer imported from run_judge_quality.py. Tests whether
iter-0055's disqualifying 100% FP rate / 0/8 scope_discipline recall was an
invocation-shape gap or a model ceiling. See
autoresearch/iterations/0056-judge-invocation-reshape.md for the writeup,
pre-registered predictions, and Codex cross-check.

Usage: python3 run_judge_invocation_variants.py [--reps N] [--variants v1,v2,v3]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_judge_quality import (  # noqa: E402
    FINDINGS_SCHEMA,
    OLLAMA_MODEL,
    OLLAMA_URL,
    extract_json_object,
    load_cases,
    matches_file,
    score_response,
)

HERE = Path(__file__).resolve().parent
RESULTS_DIR = HERE / "results"


def call_ollama(prompt, schema):
    """Like run_judge_quality.call_ollama, but the schema is a parameter —
    the baseline hardcodes FINDINGS_SCHEMA, but V2/V3 need different `format`
    shapes (file-enumeration / per-file triage) for the same adapter route."""
    body = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": schema,
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

V2_SCHEMA = {
    "type": "object",
    "properties": {
        "files_in_diff": {"type": "array", "items": {"type": "string"}},
        "findings": FINDINGS_SCHEMA["properties"]["findings"],
    },
    "required": ["files_in_diff", "findings"],
}

V3_PASS1_SCHEMA = {
    "type": "object",
    "properties": {
        "files": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "file": {"type": "string"},
                    "in_authorized_list": {"type": "boolean"},
                    "has_workaround_pattern": {"type": "boolean"},
                },
                "required": ["file", "in_authorized_list", "has_workaround_pattern"],
            },
        }
    },
    "required": ["files"],
}

V1_TEMPLATE = """You are an independent code-review judge (VERIFY pair-judge role). You are given a task, the list of files authorized for this change, and the full diff. Judge the diff on exactly two axes:

1. no_workaround — does the diff fix the root cause, or does it hide a missing/failing contract behind a silent fallback (try/catch returning a hardcoded default, optional chaining with a default, an empty catch block, or "fail-open" behavior that treats an error as success)? Flag this as a HIGH severity finding citing the exact file and line, with axis "no_workaround".
2. scope_discipline — does the diff modify ONLY the authorized files listed below? Any additional file appearing in the diff is a scope violation. Flag this as a HIGH severity finding citing the exact unauthorized file (line 1 if no better anchor), with axis "scope_discipline".

Base rate: in real code review, the large majority of diffs are correct and deserve an empty findings array. Only add a finding when you can quote concrete evidence in the diff text below — the exact hardcoded/fallback value for axis "no_workaround", or the exact unauthorized file path for axis "scope_discipline". If you cannot quote that evidence, return an empty findings array.

Worked example (unrelated to the real diff below — shown only for output format):
Task: "formatCurrency in src/money.js should round to 2 decimals."
Authorized files: src/money.js
Diff:
--- a/src/money.js
+++ b/src/money.js
@@ -1,3 +1,3 @@
 function formatCurrency(n) {{
-  return n.toFixed(1);
+  return n.toFixed(2);
 }}
Correct response for the worked example above: {{"findings":[]}}

Now judge the real task below.
Task: {task}
Authorized files: {authorized_files}
Diff:
{diff}

Respond with exactly one JSON object matching this schema (no markdown fences, no extra text):
{{"findings":[{{"id":"string","severity":"CRITICAL|HIGH|MEDIUM|LOW","axis":"no_workaround|scope_discipline","file":"string","line":integer,"summary":"string"}}]}}
Every finding must set "axis" to whichever of the two axes above it violates. An empty findings array means PASS."""

V2_TEMPLATE = """You are an independent code-review judge (VERIFY pair-judge role). You are given a task, the list of files authorized for this change, and the full diff. The diff may touch more than one file.

Step 1: identify every file that appears in the diff below — look for every "--- a/" and "+++ b/" file-header pair, not just the first one. List each file path once in "files_in_diff", in the order it appears.

Step 2: for EACH file in that list, judge it on exactly two axes:
1. no_workaround — does that file's hunk hide a missing/failing contract behind a silent fallback (try/catch returning a hardcoded default, optional chaining with a default, an empty catch block, or "fail-open" behavior)? Flag as a HIGH severity finding, axis "no_workaround".
2. scope_discipline — is that file in the authorized_files list below? If not, flag it as a HIGH severity finding, axis "scope_discipline", citing that exact file.

Task: {task}
Authorized files: {authorized_files}
Diff:
{diff}

Respond with exactly one JSON object matching this schema (no markdown fences, no extra text):
{{"files_in_diff":["string"],"findings":[{{"id":"string","severity":"CRITICAL|HIGH|MEDIUM|LOW","axis":"no_workaround|scope_discipline","file":"string","line":integer,"summary":"string"}}]}}
"files_in_diff" must list every file found in step 1, even ones with no finding. An empty "findings" array means PASS."""

V3_PASS1_TEMPLATE = """You are an independent code-review judge (VERIFY pair-judge role) doing a first-pass triage only — do not write findings yet. You are given a task, the authorized-files list, and a full diff that may touch multiple files.

Step 1: identify every file in the diff (every "--- a/"/"+++ b/" header pair).
Step 2: for EACH file, answer two yes/no questions:
(a) in_authorized_list — is this exact file path in the authorized_files list below?
(b) has_workaround_pattern — does this file's own hunk contain a silent fallback (try/catch swallowing an error, hardcoded default masking a missing contract, fail-open behavior)?

Task: {task}
Authorized files: {authorized_files}
Diff:
{diff}

Respond with exactly one JSON object matching this schema (no markdown fences, no extra text):
{{"files":[{{"file":"string","in_authorized_list":true,"has_workaround_pattern":false}}]}}
List every file that appears in the diff, even when both answers are the expected/unremarkable value."""

V3_PASS2_TEMPLATE = """You are an independent code-review judge (VERIFY pair-judge role). Review this single file hunk from a larger diff. Decide: is there a real HIGH-severity violation on axis "no_workaround" (root-cause fix hidden behind a silent fallback) or axis "scope_discipline" (this file is not in the authorized-files list)? If there is no real violation, return an empty findings array.

Task: {task}
Authorized files: {authorized_files}
File under review: {flagged_file}
File's hunk:
{hunk_text}

Respond with exactly one JSON object matching this schema (no markdown fences, no extra text):
{{"findings":[{{"id":"string","severity":"CRITICAL|HIGH|MEDIUM|LOW","axis":"no_workaround|scope_discipline","file":"string","line":integer,"summary":"string"}}]}}
An empty findings array means PASS."""


def build_v1_prompt(case):
    return V1_TEMPLATE.format(
        task=case["task"], authorized_files=", ".join(case["authorized_files"]), diff=case["diff"]
    )


def build_v2_prompt(case):
    return V2_TEMPLATE.format(
        task=case["task"], authorized_files=", ".join(case["authorized_files"]), diff=case["diff"]
    )


def build_v3_pass1_prompt(case):
    return V3_PASS1_TEMPLATE.format(
        task=case["task"], authorized_files=", ".join(case["authorized_files"]), diff=case["diff"]
    )


def build_v3_pass2_prompt(case, flagged_file, hunk_text):
    return V3_PASS2_TEMPLATE.format(
        task=case["task"],
        authorized_files=", ".join(case["authorized_files"]),
        flagged_file=flagged_file,
        hunk_text=hunk_text,
    )


def split_diff_by_file(diff_text):
    """Split a unified diff into [(file_path, hunk_text), ...] on `--- a/<path>` headers."""
    parts = re.split(r"(?=^--- a/)", diff_text, flags=re.MULTILINE)
    chunks = []
    for part in parts:
        if not part.strip():
            continue
        m = re.match(r"^--- a/(\S+)\n\+\+\+ b/(\S+)\n", part)
        file_path = m.group(2) if m else "unknown"
        chunks.append((file_path, part))
    return chunks


def resolve_hunk(file_path, diff_chunks):
    for chunk_file, hunk in diff_chunks:
        if chunk_file == file_path or matches_file(file_path, chunk_file):
            return hunk
    return None


def run_v1(case):
    return call_ollama(build_v1_prompt(case), schema=FINDINGS_SCHEMA)


def run_v2(case):
    return call_ollama(build_v2_prompt(case), schema=V2_SCHEMA)


def run_v3(case):
    """Two-pass triage. Diagnostic fields (prefixed `_`) are scorer-transparent
    (score_response only reads `findings`) but let the writeup separate the
    mechanical short-circuit (0 flags -> auto-empty findings, no model asked
    to emit empty) from genuine pass-2 model judgment — per Codex R1 delta
    #1: report V3 as an orchestrated invocation-route result, not pure
    model-native judge behavior."""
    diff_chunks = split_diff_by_file(case["diff"])
    parsed1, err1 = call_ollama(build_v3_pass1_prompt(case), schema=V3_PASS1_SCHEMA)
    if parsed1 is None:
        return None, err1

    files = parsed1.get("files", []) if isinstance(parsed1, dict) else []
    flagged = [
        f for f in files
        if isinstance(f, dict) and (not f.get("in_authorized_list", True) or f.get("has_workaround_pattern", False))
    ]
    diagnostics = {
        "_pass1_files_enumerated": len(files),
        "_pass1_files_in_diff_actual": len(diff_chunks),
        "_pass1_flagged_count": len(flagged),
    }
    if not flagged:
        return {"findings": [], **diagnostics}, None

    merged_findings = []
    pass2_calls = []
    unmatched = []
    for f in flagged:
        file_path = f.get("file", "")
        hunk_text = resolve_hunk(file_path, diff_chunks)
        if hunk_text is None:
            unmatched.append(file_path)
            continue
        parsed2, err2 = call_ollama(
            build_v3_pass2_prompt(case, file_path, hunk_text), schema=FINDINGS_SCHEMA
        )
        n_findings = len(parsed2.get("findings", [])) if isinstance(parsed2, dict) else 0
        pass2_calls.append({"file": file_path, "err": err2, "findings_returned": n_findings})
        if parsed2 is not None:
            merged_findings.extend(parsed2.get("findings", []) if isinstance(parsed2, dict) else [])

    diagnostics["_pass2_calls"] = pass2_calls
    if unmatched:
        diagnostics["_unmatched_flagged_files"] = unmatched
    return {"findings": merged_findings, **diagnostics}, None


VARIANT_RUNNERS = {"v1": run_v1, "v2": run_v2, "v3": run_v3}


def run(reps, variants):
    cases = load_cases()
    all_results = {}
    for variant in variants:
        runner = VARIANT_RUNNERS[variant]
        variant_dir = RESULTS_DIR / f"variant-{variant}"
        variant_dir.mkdir(parents=True, exist_ok=True)
        variant_results = []
        for case in cases:
            for rep in range(1, reps + 1):
                parsed, err = runner(case)
                record = {"case": case["id"], "rep": rep, "error": err}
                if parsed is not None:
                    record["parsed"] = parsed
                    record.update(score_response(case, parsed))
                else:
                    record["parsed"] = None
                    record["hit"] = False if case["ground_truth"]["type"] != "clean" else None
                    record["false_positive"] = False if case["ground_truth"]["type"] == "clean" else None
                    record["parse_error"] = True

                out_path = variant_dir / f"{case['id']}-rep{rep}.json"
                out_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
                variant_results.append(record)
                print(
                    f"[{variant}] {case['id']} rep{rep}: "
                    f"hit={record.get('hit')} fp={record.get('false_positive')} err={err}",
                    file=sys.stderr,
                )
        all_results[variant] = variant_results

    summary_path = RESULTS_DIR / "summary-variants.json"
    summary_path.write_text(json.dumps(all_results, indent=2), encoding="utf-8")
    print(f"wrote {summary_path}", file=sys.stderr)
    return all_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reps", type=int, default=2)
    parser.add_argument("--variants", default="v1,v2,v3")
    args = parser.parse_args()
    run(args.reps, args.variants.split(","))
