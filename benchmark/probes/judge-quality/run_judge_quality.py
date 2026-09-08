#!/usr/bin/env python3
"""
run_judge_quality.py — iter-0055 JUDGE-QUALITY measurement arm.

Runs every case in cases/*.json through the selected judges (ollama/gemma3:4b
via the documented adapter contract, Claude models via `claude -p`), REPS times each,
and scores mechanically per README.md's rules. No LLM meta-judging.

Usage: python3 run_judge_quality.py [--reps N] [--judges ollama,sonnet,opus,codex]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import runpy
import shlex
import signal
import subprocess
import sys
import urllib.request
import urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES_DIR = HERE / "cases"
RESULTS_DIR = HERE / "results"
sys.dont_write_bytecode = True
NATIVE = runpy.run_path(HERE.parents[2] / "config/skills/_shared/judge-role-evidence.py")
IDENTITY_BASIS = "native-Codex-configuration-header"

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma3:4b"
CLAUDE_JUDGE_RE = re.compile(r"^claude-[A-Za-z0-9.-]+$")
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


def is_claude_judge(judge):
    return judge in {"sonnet", "opus"} or CLAUDE_JUDGE_RE.fullmatch(judge) is not None


def call_claude(prompt, scratch_dir, model):
    cmd = [
        "claude", "-p", prompt,
        "--model", model,
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


def terminate_process_group(pid):
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except PermissionError:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            return


def artifact(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"not a regular artifact: {path.name}")
    raw = path.read_bytes()
    return {"path": path.name, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def read_artifact(directory, binding, expected_name):
    if not isinstance(binding, dict) or binding.get("path") != expected_name or Path(expected_name).name != expected_name:
        raise ValueError("artifact name differs from associated attempt/record")
    path = directory / expected_name
    if artifact(path) != binding:
        raise ValueError(f"artifact changed: {expected_name}")
    return path.read_bytes()


def inspect_codex_attempt(directory, attempt, requested_model, stem):
    """Recompute public identity and parse outcome from the exact retained attempt."""
    native = None
    identity_error = None
    stdout = ""
    stderr = ""
    try:
        argv = json.loads(read_artifact(directory, attempt["argv"], stem + ".argv.json"))
        stdout = read_artifact(directory, attempt["stdout"], stem + ".stdout.txt").decode("utf-8", errors="replace")
        stderr = read_artifact(directory, attempt["stderr"], stem + ".stderr.txt").decode("utf-8", errors="replace")
        require, option = NATIVE["require"], NATIVE["option"]
        require(isinstance(argv, list) and all(isinstance(arg, str) for arg in argv), "invalid argv")
        require(option(argv, "-m", "--model") == requested_model, "requested model differs from argv")
        cwd = Path(attempt["cwd"])
        require(cwd.is_absolute() and option(argv, "-C", "--cd") == str(cwd), "attempt cwd differs from argv")
        require(option(argv, "-s", "--sandbox") == "read-only", "argv sandbox differs")
        configs = [argv[i + 1] for i, arg in enumerate(argv[:-1]) if arg in ("-c", "--config")]
        require([item for item in configs if item.startswith("model_reasoning_effort=")] == ["model_reasoning_effort=xhigh"], "argv effort differs")
        native = NATIVE["codex_header"](stderr)
        diagnostics = stderr.partition("\nuser\n")[0]
        require(not re.search(r"(?im)^.*(?:model|effort).*\b(?:ignor\w*|clamp\w*|unsupported|not supported)\b", diagnostics), "native rejected an option")
        require(requested_model is None or native["model"] == requested_model, "native model differs from request")
        require(Path(native["workdir"]).is_absolute() and Path(native["workdir"]).resolve() == cwd.resolve(), "native cwd differs")
        require(native["sandbox"] == "read-only" and native["reasoning effort"] == "xhigh", "native sandbox/effort differs")
        require(type(attempt["exit_code"]) is int and attempt["exit_code"] == 0 and attempt["transport_error"] is None, "native execution did not succeed")
    except (OSError, ValueError, TypeError, KeyError) as exc:
        identity_error = str(exc)
    if attempt.get("transport_error"):
        error = attempt["transport_error"]
    elif attempt.get("exit_code") != 0:
        error = f"transport_error: exit={attempt.get('exit_code')} stderr={stderr[:300]!r}"
    elif identity_error:
        error = f"identity_error: {identity_error}"
    else:
        parsed = extract_json_object(stdout)
        error = None if parsed is not None else f"parse_error: raw={stdout[:300]!r}"
        return parsed, error, native, identity_error
    return None, error, native, identity_error


def observed_codex_identity(directory, records, identity):
    """Validate every record/attempt; legacy declarations are not native evidence."""
    if identity.get("schema") != 1 or identity.get("identity_basis") != IDENTITY_BASIS:
        raise ValueError("missing native identity contract")
    requested = identity["model_requested"]
    if requested is not None and (not isinstance(requested, str) or not requested.strip()):
        raise ValueError("invalid requested model")
    bindings = identity["records"]
    names = [f"{record['case']}-rep{record['rep']}.json" for record in records]
    if not records or len(names) != len(set(names)) or len(bindings) != len(records):
        raise ValueError("missing or duplicate record association")
    by_name = {binding["path"]: binding for binding in bindings}
    actual_records = {path.name for path in directory.glob("*-rep*.json") if not path.name.endswith(".argv.json")}
    if set(by_name) != set(names) or actual_records != set(names):
        raise ValueError("record inventory differs")
    observed = set()
    artifacts = set()
    for name, record in zip(names, records):
        if json.loads(read_artifact(directory, by_name[name], name)) != record:
            raise ValueError("record bytes differ")
        attempts = record["attempts"]
        if not isinstance(attempts, list) or len(attempts) not in (1, 2):
            raise ValueError("missing or invalid attempt count")
        for index, attempt in enumerate(attempts, 1):
            previous_error = attempts[index - 2].get("error") if index > 1 else None
            if attempt["attempt"] != index or (index > 1 and not (isinstance(previous_error, str) and previous_error.startswith("parse_error:"))):
                raise ValueError("attempt order/retry differs")
            stem = name[:-5] + f"-attempt{index}"
            parsed, error, native, identity_error = inspect_codex_attempt(directory, attempt, requested, stem)
            if identity_error or (attempt.get("native"), attempt.get("identity_error"), attempt["error"]) != (native, identity_error, error):
                raise ValueError(identity_error or "attempt observations differ from raw")
            observed.add((native["cli_version"], native["model"]))
            artifacts.update(stem + suffix for suffix in (".argv.json", ".stdout.txt", ".stderr.txt"))
        if record["parsed"] != parsed or record["error"] != error:
            raise ValueError("final record differs from its terminal attempt")
    actual = {path.name for suffix in ("argv.json", "stdout.txt", "stderr.txt") for path in directory.glob(f"*-attempt*.{suffix}")}
    if actual != artifacts or len(observed) != 1:
        raise ValueError("unassociated attempt artifacts or inconsistent native version/model")
    return next(iter(observed))


def call_codex(prompt, scratch_dir, codex_command, stdout_path, stderr_path, model_requested=None):
    cmd = [
        *codex_command,
        "exec",
        "--ignore-user-config",
        "--ignore-rules",
        "--ephemeral",
        "--skip-git-repo-check",
        "--disable", "codex_hooks",
        "--disable", "hooks",
        "-C", str(scratch_dir),
        "-s", "read-only",
        "-c", "model_reasoning_effort=xhigh",
        *(["-m", model_requested] if model_requested is not None else []),
        prompt,
    ]
    argv_path = stdout_path.with_name(stdout_path.name.removesuffix(".stdout.txt") + ".argv.json")
    argv_path.write_text(json.dumps(cmd, ensure_ascii=False) + "\n", encoding="utf-8")
    returncode = None
    transport_error = None
    try:
        with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open("w", encoding="utf-8") as stderr:
            proc = subprocess.Popen(
                cmd,
                cwd=scratch_dir,
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                text=True,
                start_new_session=True,
            )
            try:
                returncode = proc.wait(timeout=300)
            except subprocess.TimeoutExpired:
                terminate_process_group(proc.pid)
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except OSError:
                        pass
                    proc.wait()
                returncode = proc.returncode
                transport_error = "transport_error: timeout"
    except FileNotFoundError:
        transport_error = f"transport_error: command_not_found {codex_command[0]}"
    attempt = {"cwd": str(scratch_dir), "exit_code": returncode, "transport_error": transport_error,
               "argv": artifact(argv_path), "stdout": artifact(stdout_path), "stderr": artifact(stderr_path)}
    parsed, error, native, identity_error = inspect_codex_attempt(stdout_path.parent, attempt, model_requested, argv_path.name.removesuffix(".argv.json"))
    attempt.update(native=native, identity_error=identity_error)
    return parsed, error, attempt


def call_judge_with_retry(judge, prompt, scratch_dir, *, codex_command, judge_dir, artifact_stem, model_requested=None):
    attempts = []
    parsed = None
    err = None
    for attempt in (1, 2):
        evidence = {}
        if judge == "ollama":
            parsed, err = call_ollama(prompt)
        elif is_claude_judge(judge):
            parsed, err = call_claude(prompt, scratch_dir, judge)
        elif judge == "codex":
            stdout_path = judge_dir / f"{artifact_stem}-attempt{attempt}.stdout.txt"
            stderr_path = judge_dir / f"{artifact_stem}-attempt{attempt}.stderr.txt"
            parsed, err, evidence = call_codex(prompt, scratch_dir, codex_command, stdout_path, stderr_path, model_requested)
        else:
            raise ValueError(f"unknown judge: {judge}")
        attempts.append({"attempt": attempt, "error": err, **evidence})
        if parsed is not None or not (err or "").startswith("parse_error:"):
            break
    return parsed, err, attempts


def probe_version(command, args):
    try:
        result = subprocess.run(
            [*command, *args],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    text = (result.stdout or result.stderr or "").strip()
    return text.splitlines()[0] if text else None


def write_identity(judge, judge_dir, run_id, *, records=None, model_requested=None):
    if judge == "ollama":
        cli_version = probe_version(["ollama"], ["--version"])
        model = OLLAMA_MODEL
    elif is_claude_judge(judge):
        cli_version = probe_version(["claude"], ["--version"])
        model = judge
    elif judge == "codex":
        identity = {"schema": 1, "identity_basis": IDENTITY_BASIS, "model_requested": model_requested,
                    "recorded_at_run_id": run_id, "cli_version": None, "model_id_or_alias": None,
                    "identity_validated": False,
                    "records": [artifact(judge_dir / f"{record['case']}-rep{record['rep']}.json") for record in records]}
        try:
            identity["cli_version"], identity["model_id_or_alias"] = observed_codex_identity(judge_dir, records, identity)
            identity["identity_validated"] = True
            identity["identity_error"] = None
        except (OSError, ValueError, TypeError, KeyError) as exc:
            identity["identity_error"] = str(exc)
        (judge_dir / "identity.json").write_text(json.dumps(identity, indent=2) + "\n", encoding="utf-8")
        return
    else:
        raise ValueError(f"unknown judge: {judge}")
    identity = {
        "cli_version": cli_version,
        "model_id_or_alias": model,
        "recorded_at_run_id": run_id,
    }
    (judge_dir / "identity.json").write_text(json.dumps(identity, indent=2) + "\n", encoding="utf-8")


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


def run(reps, judges, *, run_id, results_dir, codex_command):
    model_requested = os.environ.get("CODEX_MODEL") or os.environ.get("OPENAI_MODEL")
    if "codex" in judges:
        if model_requested is not None and not model_requested.strip():
            raise ValueError("explicit whitespace-only Codex model request")
        codex_results = results_dir / "codex"
        if codex_results.exists() and any(codex_results.iterdir()):
            raise ValueError("Codex measurement requires a fresh results directory; historical artifacts are not overwritten")
    cases = load_cases()
    scratch_dir = Path("/private/tmp/claude-501-judge-quality-scratch")
    scratch_dir.mkdir(parents=True, exist_ok=True)
    codex_scratch_dir = Path("/private/tmp/codex-501-judge-quality-scratch")
    codex_scratch_dir.mkdir(parents=True, exist_ok=True)

    all_results = {}
    for judge in judges:
        judge_dir = results_dir / judge
        judge_dir.mkdir(parents=True, exist_ok=True)
        if judge != "codex":
            write_identity(judge, judge_dir, run_id)
        judge_results = []
        for case in cases:
            prompt = build_prompt(case)
            for rep in range(1, reps + 1):
                parsed, err, attempts = call_judge_with_retry(
                    judge,
                    prompt,
                    codex_scratch_dir if judge == "codex" else scratch_dir,
                    codex_command=codex_command,
                    judge_dir=judge_dir,
                    artifact_stem=f"{case['id']}-rep{rep}",
                    model_requested=model_requested,
                )

                record = {"case": case["id"], "rep": rep, "error": err}
                if judge == "codex" or len(attempts) > 1 or err is not None:
                    record["attempts"] = attempts
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
        if judge == "codex":
            write_identity(judge, judge_dir, run_id, records=judge_results, model_requested=model_requested)
        all_results[judge] = judge_results

    summary_path = results_dir / "summary.json"
    summary_path.write_text(json.dumps(all_results, indent=2), encoding="utf-8")
    print(f"wrote {summary_path}", file=sys.stderr)
    return all_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reps", type=int, default=2)
    parser.add_argument("--judges", default="ollama,sonnet")
    parser.add_argument("--run-id", default=f"manual-{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}")
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument(
        "--codex-command",
        default=os.environ.get("JUDGE_QUALITY_CODEX_CMD", "codex"),
        help="command used for codex judge route; shell-split, then 'exec ...' is appended",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    judges = [judge for judge in args.judges.split(",") if judge]
    invalid_judges = [judge for judge in judges if judge not in {"ollama", "codex"} and not is_claude_judge(judge)]
    if invalid_judges:
        parser.error(f"unsupported judge: {invalid_judges[0]}")
    codex_command = shlex.split(args.codex_command)
    if not codex_command:
        parser.error("--codex-command must not be empty")
    if args.dry_run:
        print(json.dumps({
            "run_id": args.run_id,
            "judges": judges,
            "results_dir": str(args.results_dir),
            "codex_command": codex_command,
        }, indent=2))
        raise SystemExit(0)
    run(args.reps, judges, run_id=args.run_id, results_dir=args.results_dir, codex_command=codex_command)
