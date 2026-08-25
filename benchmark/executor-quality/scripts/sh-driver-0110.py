#!/usr/bin/env python3
"""iter-0110 session-horizon driver — driver-fed resume custody."""
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
CORPUS_TASKS_ROOT = REPO / "benchmark/executor-quality/tasks-0102"
SMOKE_TASKS_ROOT = REPO / "benchmark/executor-quality/tasks-0110-smoke"
HERE = pathlib.Path(__file__).resolve().parent
PIN = pathlib.Path.home() / ".local/share/nx01/pins/claude-2.1.226-iter0100/claude"
PIN_SHA256 = "013a1cf17df5ff1dcc189d5d6fd3fdd5f097ddc3cd41aa9992e99805574febbe"
RUN_BOUNDED = REPO / "config/skills/_shared/run-bounded.py"
RUN_BOUNDED_SHA256 = "db9ed3832e444449263a5ca3bdeccba41d91722ef2070115107b6caf82424ca5"
CORPUS_MANIFEST = pathlib.Path("/Users/aipalm/.local/share/nx01/iter0102/freeze/candidate-manifest.json")
CORPUS_MANIFEST_SHA256 = "80f0a12ddb6df006c4137ecbc96c557742f8bbe74b0cacf65466c3af6dcd8887"
TREE_SHA256 = "294eeadea37889e99f8dee1dc6021d353ac1f835fda46d6b1827480cc9a0fe5b"
ALLOWED_ENGINES = frozenset({"claude-opus-5", "claude-opus-4-8", "claude-sonnet-5"})
BOUND_SEC = 1800
EFFORT = "high"
TOOLS = "Read,Grep,Glob,Edit,Write,Bash"
PROMPT_TEMPLATE = "Work only inside ./t{n}/ (relative to the current directory).\n\n"
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
    task_dir = CORPUS_TASKS_ROOT / task_id
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


def position_class(position_index, k):
    if k < 2 or k % 2:
        raise ValueError("k must be even and at least 2")
    if not 1 <= position_index <= k:
        raise ValueError("position index is outside the session")
    return "EARLY" if position_index <= k // 2 else "LATE"


def project_slug(workdir):
    return str(workdir).replace("/", "-")


def snapshot_transcripts(transcript_dir):
    try:
        return {
            path.name: path.stat().st_size
            for path in transcript_dir.glob("*.jsonl")
            if path.is_file()
        }
    except OSError:
        return {}


def mark_custody_broken(row):
    row["custody_ok"] = False
    row["custody_broken"] = True
    return row


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_oracle(task_dir, workdir, output_path):
    try:
        oracle = subprocess.run(
            [sys.executable, str(task_dir / "hidden/oracle.py"), str(workdir)],
            capture_output=True,
            timeout=60,
        )
        output_path.write_bytes(oracle.stdout)
        if oracle.returncode != 0:
            raise RuntimeError(f"oracle exit {oracle.returncode}")
        manifestations = json.loads(oracle.stdout)["manifestations"]
        return len(manifestations), sum(1 for item in manifestations if not item["passed"]), True
    except (
        OSError,
        subprocess.TimeoutExpired,
        RuntimeError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
    ):
        total = manifestation_count(task_dir)
        return total, total, False


def append_row(paths, row):
    encoded = json.dumps(row, sort_keys=True)
    for path in paths:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(encoded + "\n")
    print(encoded, flush=True)


def base_row(engine, task_id, replicate, cohort_run_id, session_label, k, position_index):
    prompt_bytes = b""
    return {
        "run_id": f"{cohort_run_id}:{engine}:{session_label}:r{replicate}:t{position_index}",
        "task": task_id,
        "replicate": replicate,
        "engine_requested": engine,
        "engine_attested": None,
        "manifestations_total": 0,
        "manifestations_failed": 0,
        "catastrophic": False,
        "incomplete": False,
        "infra_invalid": False,
        "wall_ms": 0,
        "prompt_sha256": hashlib.sha256(prompt_bytes).hexdigest(),
        "session_label": session_label,
        "k": k,
        "position_index": position_index,
        "position_class": position_class(position_index, k),
        "launched_resume_id": None,
        "reported_session_id": None,
        "custody_ok": False,
        "custody_broken": False,
    }


def validate_launch(engine, tasks, smoke):
    if engine not in ALLOWED_ENGINES:
        raise ValueError(f"engine must be one of {sorted(ALLOWED_ENGINES)}")
    if len(tasks) < 2 or len(tasks) % 2:
        raise ValueError("--tasks must contain an even number of at least two task ids")
    if not runner_is_frozen():
        raise RuntimeError("runner integrity mismatch")
    if not smoke and not all(corpus_task_is_sealed(task_id) for task_id in tasks):
        raise RuntimeError("corpus task integrity mismatch")


def run_session(engine, session_label, tasks, replicate, out_dir, cohort_run_id, smoke):
    task_root = SMOKE_TASKS_ROOT if smoke else CORPUS_TASKS_ROOT
    session_dir = out_dir / f"{engine}.{session_label}.r{replicate}"
    if session_dir.exists():
        raise RuntimeError(f"session output already exists: {session_dir}")
    session_dir.mkdir(parents=True)
    ws_root = pathlib.Path("/private/tmp") / f"nx0110-{secrets.token_hex(6)}"
    workdir = ws_root / "ws"
    workdir.mkdir(parents=True)
    transcript_dir = pathlib.Path.home() / ".claude/projects" / project_slug(workdir)
    custody = {
        "cwd": str(workdir),
        "project_slug": project_slug(workdir),
        "links": [],
        "broken": False,
        "break_position": None,
    }
    boundaries = []
    ledger_paths = (out_dir / "ledger.jsonl", session_dir / "rows.jsonl")
    resume_id = None
    broken = False
    exposed = []

    for position_index, task_id in enumerate(tasks, start=1):
        task_dir = task_root / task_id
        row = base_row(
            engine, task_id, replicate, cohort_run_id, session_label, len(tasks), position_index,
        )
        att_dir = session_dir / f"t{position_index}.{task_id}"
        att_dir.mkdir()
        prompt_path = att_dir / "prompt.txt"
        stdout_path = att_dir / "cli.stdout"
        stderr_path = att_dir / "cli.stderr"
        oracle_path = att_dir / "oracle.json"
        prompt_path.write_bytes(b"")
        stdout_path.write_bytes(b"")
        stderr_path.write_bytes(b"")
        oracle_path.write_bytes(b"")
        if broken:
            mark_custody_broken(row)
            failed_row(row, task_dir, stderr_path, "custody broken by earlier invocation", False)
            append_row(ledger_paths, row)
            continue

        try:
            goal = json.loads((task_dir / "task.json").read_bytes())["goal"]
            if not isinstance(goal, str):
                raise TypeError("goal must be a string")
            prompt_bytes = (PROMPT_TEMPLATE.format(n=position_index) + goal).encode("utf-8")
            prompt_path.write_bytes(prompt_bytes)
            row["prompt_sha256"] = hashlib.sha256(prompt_bytes).hexdigest()
            task_workdir = workdir / f"t{position_index}"
            shutil.copytree(task_dir / "visible", task_workdir)
            exposed.append((position_index, task_id, task_dir, task_workdir))
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
            mark_custody_broken(row)
            failed_row(row, task_dir, stderr_path, f"attempt setup failure: {exc}", True)
            custody["links"].append(
                {"position_index": position_index, "launched_resume_id": resume_id, "reported_session_id": None}
            )
            custody["broken"] = True
            custody["break_position"] = position_index
            write_json(session_dir / "custody.json", custody)
            broken = True
            append_row(ledger_paths, row)
            continue

        row["launched_resume_id"] = resume_id
        before = snapshot_transcripts(transcript_dir)
        boundary = {
            "position_index": position_index,
            "task": task_id,
            "launched_resume_id": resume_id,
            "transcript_dir": str(transcript_dir),
            "before": before,
        }
        cmd = [
            sys.executable,
            str(RUN_BOUNDED),
            str(BOUND_SEC),
            "--",
            str(PIN),
            "-p",
            prompt_bytes.decode("utf-8"),
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
        if resume_id is not None:
            cmd.extend(("--resume", resume_id))
        t0 = time.time()
        try:
            proc = subprocess.run(
                cmd,
                cwd=workdir,
                env=scrubbed_env(),
                stdin=subprocess.DEVNULL,
                capture_output=True,
                timeout=BOUND_SEC + 60,
            )
            row["wall_ms"] = int((time.time() - t0) * 1000)
            stdout_path.write_bytes(proc.stdout)
            stderr_path.write_bytes(proc.stderr)
        except (OSError, subprocess.TimeoutExpired) as exc:
            row["wall_ms"] = int((time.time() - t0) * 1000)
            stderr_path.write_text(f"runner failure: {exc}\n", encoding="utf-8")
            proc = None
        after = snapshot_transcripts(transcript_dir)
        boundary["after"] = after
        boundaries.append(boundary)
        write_json(session_dir / "boundaries.json", boundaries)

        payload = None
        if proc is not None:
            try:
                decoded = json.loads(proc.stdout)
                if isinstance(decoded, dict):
                    payload = decoded
            except json.JSONDecodeError:
                pass
        failure_text = b""
        if proc is not None:
            failure_text = proc.stdout + b"\n" + proc.stderr
            catastrophic, incomplete, infra_invalid, engine_attested = classify_cli_result(
                engine, proc.returncode, payload, failure_text.decode("utf-8", errors="replace"),
            )
            row["catastrophic"] = catastrophic
            row["incomplete"] = incomplete
            row["infra_invalid"] = infra_invalid
            row["engine_attested"] = engine_attested
        else:
            row["catastrophic"] = True
            row["infra_invalid"] = True
        reported_id = payload.get("session_id") if isinstance(payload, dict) else None
        row["reported_session_id"] = reported_id if isinstance(reported_id, str) else None
        custody["links"].append(
            {
                "position_index": position_index,
                "launched_resume_id": resume_id,
                "reported_session_id": row["reported_session_id"],
            }
        )
        accepted = (
            proc is not None
            and proc.returncode == 0
            and isinstance(reported_id, str)
            and bool(reported_id)
            and not row["catastrophic"]
            and not row["infra_invalid"]
        )
        if accepted:
            row["custody_ok"] = True
            resume_id = reported_id
        else:
            mark_custody_broken(row)
            custody["broken"] = True
            custody["break_position"] = position_index
            broken = True
        write_json(session_dir / "custody.json", custody)

        if proc is not None and not (row["catastrophic"] or row["infra_invalid"]):
            total, failed, oracle_ok = run_oracle(task_dir, task_workdir, oracle_path)
            row["manifestations_total"] = total
            row["manifestations_failed"] = failed
            if not oracle_ok:
                row["catastrophic"] = True
        elif proc is not None:
            total = manifestation_count(task_dir)
            row["manifestations_total"] = total
            row["manifestations_failed"] = total
        else:
            failed_row(row, task_dir, stderr_path, stderr_path.read_text(encoding="utf-8").strip(), True)
        append_row(ledger_paths, row)

    reoracle = []
    for position_index, task_id, task_dir, task_workdir in exposed:
        output_path = session_dir / f"t{position_index}.{task_id}" / "end_of_session_reoracle.json"
        total, failed, oracle_ok = run_oracle(task_dir, task_workdir, output_path)
        reoracle.append(
            {
                "position_index": position_index,
                "task": task_id,
                "manifestations_total": total,
                "manifestations_failed": failed,
                "oracle_ok": oracle_ok,
            }
        )
    write_json(session_dir / "end_of_session_reoracle.json", reoracle)
    return session_dir


def self_test():
    cases = (
        ("success", 0, {"subtype": "success", "modelUsage": {"claude-opus-5": {"input_tokens": 1}}}, "", (False, False, False)),
        ("mid-run-429", 1, {"is_error": True, "subtype": "error", "api_error_status": 429, "modelUsage": {"claude-opus-5": {"input_tokens": 1}}}, "", (True, False, True)),
        ("zero-turn-session-limit", 1, {"is_error": True, "subtype": "error", "modelUsage": {}}, "session limit", (True, False, True)),
        ("engine-refusal-after-turn", 1, {"is_error": True, "subtype": "error", "modelUsage": {"claude-opus-5": {"input_tokens": 1}}}, "refused", (True, False, False)),
        ("sonnet-success", 0, {"subtype": "success", "modelUsage": {"claude-sonnet-5": {"input_tokens": 1}}}, "", (False, False, False)),
    )
    for label, returncode, payload, stderr, expected in cases:
        actual = classify_cli_result("claude-sonnet-5" if label == "sonnet-success" else "claude-opus-5", returncode, payload, stderr)[:3]
        assert actual == expected, (label, actual)
    assert (position_class(1, 4), position_class(2, 4), position_class(3, 4), position_class(4, 4)) == ("EARLY", "EARLY", "LATE", "LATE")
    row = mark_custody_broken({"custody_ok": True, "custody_broken": False})
    assert row == {"custody_ok": False, "custody_broken": True}
    assert project_slug(pathlib.Path("/private/tmp/nx-0023ab893188/ws")) == "-private-tmp-nx-0023ab893188-ws"
    print("PASS sh-driver-0110 self-test: classification, position, custody")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--engine")
    parser.add_argument("--session-label")
    parser.add_argument("--tasks")
    parser.add_argument("--replicate", type=int)
    parser.add_argument("--out")
    parser.add_argument("--run-id")
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not all((args.engine, args.session_label, args.tasks, args.replicate, args.out, args.run_id)):
        parser.error("--engine, --session-label, --tasks, --replicate, --out, and --run-id are required unless --self-test is used")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.session_label):
        parser.error("--session-label must contain only letters, digits, dot, underscore, and dash")
    tasks = args.tasks.split(",")
    try:
        validate_launch(args.engine, tasks, args.smoke)
        session_dir = run_session(args.engine, args.session_label, tasks, args.replicate, pathlib.Path(args.out), args.run_id, args.smoke)
    except (RuntimeError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps({"session_dir": str(session_dir)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
