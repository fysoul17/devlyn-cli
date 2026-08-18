#!/usr/bin/env python3
"""iter-0103 matrix driver — 0100 arm-driver lineage, opus-5 vs opus-4-8.

Per attempt: opaque workdir, visible-fixture copy, goal-only prompt, pinned CLI
under run-bounded 1800s, offline oracle scoring, ledger row emission.
Usage: mx-driver.py --engine <exact-model-id> --tasks EQ3-UA1,... --rep N \
       --out <dir> --run-id <id>
"""
import argparse
import hashlib
import json
import os
import pathlib
import re
import secrets
import shutil
import subprocess
import sys
import time

REPO = pathlib.Path("/Users/aipalm/Documents/GitHub/devlyn-cli")
TASKS_ROOT = REPO / "benchmark/executor-quality/tasks-0102"
HERE = pathlib.Path(__file__).resolve().parent
PIN = pathlib.Path.home() / ".local/share/nx01/pins/claude-2.1.226-iter0100/claude"
PIN_SHA256 = "013a1cf17df5ff1dcc189d5d6fd3fdd5f097ddc3cd41aa9992e99805574febbe"
RUN_BOUNDED = HERE / "run-bounded.py"
RUN_BOUNDED_SHA256 = "db9ed3832e444449263a5ca3bdeccba41d91722ef2070115107b6caf82424ca5"
CORPUS_MANIFEST = pathlib.Path("/Users/aipalm/.local/share/nx01/iter0102/freeze/candidate-manifest.json")
CORPUS_MANIFEST_SHA256 = "80f0a12ddb6df006c4137ecbc96c557742f8bbe74b0cacf65466c3af6dcd8887"
TREE_SHA256 = "294eeadea37889e99f8dee1dc6021d353ac1f835fda46d6b1827480cc9a0fe5b"
ALLOWED_ENGINES = frozenset({"claude-opus-5", "claude-opus-4-8"})
BOUND_SEC = 1800
EFFORT = "high"
TOOLS = "Read,Grep,Glob,Edit,Write,Bash"
INFRA_FAILURE = re.compile(r"http\s*429|http\s*529|rate[ -]?limit|session[ -]?limit|usage[ -]?limit|overloaded", re.IGNORECASE)


def scrubbed_env():
    keep = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("CLAUDE", "CODEX", "MCP", "ANTHROPIC_MODEL"))
    }
    keep["TERM"] = "dumb"
    return keep


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def runner_is_frozen():
    try:
        return (
            sha256(RUN_BOUNDED) == RUN_BOUNDED_SHA256
            and sha256(PIN) == PIN_SHA256
            and sha256(CORPUS_MANIFEST) == CORPUS_MANIFEST_SHA256
        )
    except OSError:
        return False


def corpus_task_is_sealed(task_id):
    try:
        manifest = json.loads(CORPUS_MANIFEST.read_bytes())
        tasks = manifest["tasks"]
        tree = hashlib.sha256(
            json.dumps(tasks, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        expected = tasks[task_id]
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return False
    if tree != TREE_SHA256 or not isinstance(expected, dict) or not expected:
        return False
    task_dir = TASKS_ROOT / task_id
    try:
        entries = list(task_dir.rglob("*"))
    except OSError:
        return False
    if any(path.is_symlink() for path in entries):
        return False
    actual = {
        path.relative_to(task_dir).as_posix(): path for path in entries if path.is_file()
    }
    if set(actual) != set(expected):
        return False
    try:
        return all(sha256(actual[relative]) == digest for relative, digest in expected.items())
    except OSError:
        return False


def manifestation_count(task_dir):
    try:
        payload = json.loads((task_dir / "hidden/manifests.json").read_bytes())
        manifestations = payload["manifestations"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return 0
    return len(manifestations) if isinstance(manifestations, list) else 0


def failed_row(row, task_dir, stderr_path, message, infra_invalid):
    total = manifestation_count(task_dir)
    row.update(
        {
            "manifestations_total": total,
            "manifestations_failed": total,
            "catastrophic": True,
            "infra_invalid": infra_invalid,
        }
    )
    stderr_path.write_text(message + "\n", encoding="utf-8")
    return row


def classify_cli_result(engine, returncode, payload, stderr):
    """Keep engine outcome taxonomy separate from provider-invalid receipts."""
    cli_failed = payload is None or returncode != 0
    payload_failure = False
    usage_models = []
    api_error_status = None
    if isinstance(payload, dict):
        payload_failure = payload.get("is_error") is True or payload.get("subtype") != "success"
        model_usage = payload.get("modelUsage")
        usage_models = sorted(model_usage) if isinstance(model_usage, dict) else []
        api_error_status = payload.get("api_error_status")
    failure = cli_failed or payload_failure
    engine_attested = (
        usage_models[0] if usage_models == [engine] else ",".join(usage_models) or None
    )
    catastrophic = cli_failed or not usage_models
    incomplete = not cli_failed and payload_failure
    if usage_models and usage_models != [engine]:
        return catastrophic, incomplete, True, engine_attested
    zero_turn = not usage_models
    infra_signal = api_error_status in {429, 529} or (
        api_error_status is None and bool(INFRA_FAILURE.search(stderr))
    )
    infra_invalid = failure and (zero_turn or infra_signal)
    return catastrophic, incomplete, infra_invalid, engine_attested


def run_attempt(engine, task_id, rep, out_dir, cohort_run_id):
    task_dir = TASKS_ROOT / task_id
    ws_root = pathlib.Path("/private/tmp") / f"nx-{secrets.token_hex(6)}"
    workdir = ws_root / "ws"
    att_dir = out_dir / f"{engine}.{task_id}.r{rep}"
    att_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = att_dir / "prompt.txt"
    stdout_path = att_dir / "cli.stdout"
    stderr_path = att_dir / "cli.stderr"
    oracle_path = att_dir / "oracle.json"
    prompt_bytes = b""
    row = {
        "run_id": f"{cohort_run_id}:{engine}:{task_id}:r{rep}",
        "task": task_id,
        "rep": rep,
        "engine_requested": engine,
        "engine_attested": None,
        "manifestations_total": 0,
        "manifestations_failed": 0,
        "catastrophic": False,
        "incomplete": False,
        "infra_invalid": False,
        "wall_ms": 0,
        "prompt_sha256": hashlib.sha256(prompt_bytes).hexdigest(),
    }
    prompt_path.write_bytes(prompt_bytes)
    stdout_path.write_bytes(b"")
    stderr_path.write_bytes(b"")
    oracle_path.write_bytes(b"")
    if not runner_is_frozen():
        return failed_row(row, task_dir, stderr_path, "runner integrity mismatch", True)
    if not corpus_task_is_sealed(task_id):
        return failed_row(row, task_dir, stderr_path, "corpus task integrity mismatch", True)
    try:
        goal = json.loads((task_dir / "task.json").read_bytes())["goal"]
        if not isinstance(goal, str):
            raise TypeError("goal must be a string")
        prompt_bytes = goal.encode("utf-8")
        prompt_path.write_bytes(prompt_bytes)
        row["prompt_sha256"] = hashlib.sha256(prompt_bytes).hexdigest()
        shutil.copytree(task_dir / "visible", workdir)
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        return failed_row(row, task_dir, stderr_path, f"attempt setup failure: {exc}", True)

    t0 = time.time()
    cmd = [
        sys.executable,
        str(RUN_BOUNDED),
        str(BOUND_SEC),
        "--",
        str(PIN),
        "-p",
        goal,
        "--model",
        engine,
        "--effort",
        EFFORT,
        "--output-format",
        "json",
        "--dangerously-skip-permissions",
        "--strict-mcp-config",
        "--mcp-config",
        '{"mcpServers":{}}',
        "--allowedTools",
        TOOLS,
    ]
    try:
        proc = subprocess.run(
            cmd,
            cwd=workdir,
            env=scrubbed_env(),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=BOUND_SEC + 60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        row["wall_ms"] = int((time.time() - t0) * 1000)
        shutil.rmtree(ws_root, ignore_errors=True)
        return failed_row(row, task_dir, stderr_path, f"runner failure: {exc}", True)
    row["wall_ms"] = int((time.time() - t0) * 1000)
    stdout_path.write_bytes(proc.stdout)
    stderr_path.write_bytes(proc.stderr)

    payload = None
    try:
        decoded = json.loads(proc.stdout)
        if isinstance(decoded, dict):
            payload = decoded
    except json.JSONDecodeError:
        pass
    failure_text = (proc.stdout + b"\n" + proc.stderr).decode("utf-8", errors="replace")
    catastrophic, incomplete, infra_invalid, engine_attested = classify_cli_result(
        engine, proc.returncode, payload, failure_text,
    )
    row["catastrophic"] = catastrophic
    row["incomplete"] = incomplete
    row["infra_invalid"] = infra_invalid
    row["engine_attested"] = engine_attested
    if row["catastrophic"] or row["infra_invalid"]:
        total = manifestation_count(task_dir)
        row["manifestations_total"] = total
        row["manifestations_failed"] = total
        shutil.rmtree(ws_root, ignore_errors=True)
        return row

    try:
        oracle = subprocess.run(
            [sys.executable, str(task_dir / "hidden/oracle.py"), str(workdir)],
            capture_output=True,
            timeout=60,
        )
        oracle_path.write_bytes(oracle.stdout)
        if oracle.returncode != 0:
            raise RuntimeError(f"oracle exit {oracle.returncode}")
        manifestations = json.loads(oracle.stdout)["manifestations"]
        row["manifestations_total"] = len(manifestations)
        row["manifestations_failed"] = sum(1 for item in manifestations if not item["passed"])
    except (
        OSError,
        subprocess.TimeoutExpired,
        RuntimeError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
    ):
        total = manifestation_count(task_dir)
        row["manifestations_total"] = total
        row["manifestations_failed"] = total
        row["catastrophic"] = True
    shutil.rmtree(ws_root, ignore_errors=True)
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--engine")
    parser.add_argument("--tasks")
    parser.add_argument("--rep", type=int, default=1)
    parser.add_argument("--out")
    parser.add_argument("--run-id")
    args = parser.parse_args()
    if args.self_test:
        cases = (
            ("success", 0, {"subtype": "success", "modelUsage": {"claude-opus-5": {"input_tokens": 1}}}, "", (False, False, False)),
            ("mid-run-429", 1, {"is_error": True, "subtype": "error", "api_error_status": 429, "modelUsage": {"claude-opus-5": {"input_tokens": 1}}}, "", (True, False, True)),
            ("mid-run-529", 1, {"is_error": True, "subtype": "error", "api_error_status": 529, "modelUsage": {"claude-opus-5": {"input_tokens": 1}}}, "", (True, False, True)),
            ("zero-turn-session-limit", 1, {"is_error": True, "subtype": "error", "modelUsage": {}}, "session limit", (True, False, True)),
            ("text-usage-limit", 1, {"is_error": True, "subtype": "error", "modelUsage": {"claude-opus-5": {"input_tokens": 1}}}, "usage limit", (True, False, True)),
            ("engine-refusal-after-turn", 1, {"is_error": True, "subtype": "error", "modelUsage": {"claude-opus-5": {"input_tokens": 1}}}, "refused", (True, False, False)),
            ("exit-0-non-success", 0, {"is_error": True, "subtype": "error_max_turns", "modelUsage": {"claude-opus-5": {"input_tokens": 1}}}, "", (False, True, False)),
        )
        for label, returncode, payload, stderr, expected in cases:
            catastrophic, incomplete, infra_invalid, _attested = classify_cli_result(
                "claude-opus-5", returncode, payload, stderr,
            )
            assert (catastrophic, incomplete, infra_invalid) == expected, (label, catastrophic, incomplete, infra_invalid)
        print("PASS mx-driver self-test structural infra classification: 7 fixtures")
        return 0
    if not all((args.engine, args.tasks, args.out, args.run_id)):
        parser.error("--engine, --tasks, --out, and --run-id are required unless --self-test is used")
    if args.engine not in ALLOWED_ENGINES:
        parser.error(f"engine must be one of {sorted(ALLOWED_ENGINES)}")
    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    ledger = out_dir / "ledger.jsonl"
    for task_id in args.tasks.split(","):
        row = run_attempt(args.engine, task_id, args.rep, out_dir, args.run_id)
        with ledger.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        print(json.dumps(row, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
