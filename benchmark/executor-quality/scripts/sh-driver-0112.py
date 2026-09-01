#!/usr/bin/env python3
"""iter-0112 session-horizon driver — driver-fed resume custody."""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
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
ENOTFOUND_RESULT = "API Error: Unable to connect to API (ENOTFOUND)"
HOST_CONTROL_HOSTNAME = "one.one.one.one"
HOST_CONTROL_FRESHNESS_SECONDS = 60
HOST_CONTROL_SCHEMA = "iter0112-host-origin-dns-v1"
CNET_FIXTURES = (
    ("/Users/aipalm/.local/share/nx01/iter0110/matrix/m6-20260830T001654Z/attempts/s03-b01.a1/claude-opus-4-8.s03-b01-claude-opus-4-8-fwd.r9/t1.EQ3-AF5/cli.stdout", "4dd6e6c176d5bfb18debbd1c6e802d32d7c7392283c7e55afc2f731dc2d42d85"),
    ("/Users/aipalm/.local/share/nx01/iter0110/matrix/m6-20260830T001654Z/attempts/s03-b02.a1/claude-opus-5.s03-b02-claude-opus-5-fwd.r10/t7.EQ3-MI4/cli.stdout", "79653a12cceb8799e8c433cc16b321c8bb72856f110cd5984656773536c9f575"),
    ("/Users/aipalm/.local/share/nx01/iter0110/matrix/m6-20260830T001654Z/attempts/s03-b03.a1/claude-opus-5.s03-b03-claude-opus-5-fwd.r11/t7.EQ3-UA1/cli.stdout", "75c50d066b0c08cb4ffac52f4b67206a68f361bbde3063d12f301319366b4bf6"),
)


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


def iso_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def is_enotfound_envelope(payload):
    return (
        isinstance(payload, dict)
        and payload.get("is_error") is True
        and "api_error_status" in payload
        and payload["api_error_status"] is None
        and payload.get("result") == ENOTFOUND_RESULT
    )


def control_probe(failure_detected_at):
    evidence = {
        "schema": HOST_CONTROL_SCHEMA,
        "mechanism": "socket.getaddrinfo(AF_UNSPEC, SOCK_STREAM)",
        "hostname": HOST_CONTROL_HOSTNAME,
        "failure_detected_at": failure_detected_at,
        "observed_at": iso_now(),
        "result": "probe_unavailable",
        "addresses": [],
        "error": None,
        "raw_result": None,
    }
    try:
        answers = socket.getaddrinfo(HOST_CONTROL_HOSTNAME, 443, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM)
        evidence["raw_result"] = repr(answers)
        evidence["addresses"] = sorted({answer[4][0] for answer in answers})
        evidence["result"] = "control_resolution_succeeded" if evidence["addresses"] else "control_resolution_failed"
    except socket.gaierror as exc:
        evidence["result"] = "control_resolution_failed"
        evidence["error"] = f"{type(exc).__name__}:{exc}"
        evidence["raw_result"] = repr(exc)
    except OSError as exc:
        evidence["error"] = f"{type(exc).__name__}:{exc}"
        evidence["raw_result"] = repr(exc)
    return evidence


def host_origin_attested(evidence, now=None):
    if not isinstance(evidence, dict) or set(evidence) != {"schema", "mechanism", "hostname", "failure_detected_at", "observed_at", "result", "addresses", "error", "raw_result"}:
        return False
    if evidence.get("schema") != HOST_CONTROL_SCHEMA or evidence.get("mechanism") != "socket.getaddrinfo(AF_UNSPEC, SOCK_STREAM)" or evidence.get("hostname") != HOST_CONTROL_HOSTNAME or evidence.get("result") != "control_resolution_failed":
        return False
    try:
        detected = datetime.datetime.fromisoformat(str(evidence["failure_detected_at"]).replace("Z", "+00:00"))
        observed = datetime.datetime.fromisoformat(str(evidence["observed_at"]).replace("Z", "+00:00"))
    except ValueError:
        return False
    if detected.tzinfo is None or observed.tzinfo is None or observed < detected:
        return False
    instant = now or datetime.datetime.now(datetime.timezone.utc)
    return instant.astimezone(datetime.timezone.utc) - detected.astimezone(datetime.timezone.utc) <= datetime.timedelta(seconds=HOST_CONTROL_FRESHNESS_SECONDS)


def is_aup_refusal(payload, engine):
    """The frozen m6 refusal envelope is scoreable, not provider-void."""
    return (
        isinstance(payload, dict)
        and isinstance(engine, str)
        and payload.get("is_error") is True
        and payload.get("subtype") == "success"
        and payload.get("terminal_reason") == "api_error"
        and payload.get("stop_reason") == "refusal"
        and "api_error_status" in payload
        and payload["api_error_status"] is None
        and isinstance(payload.get("modelUsage"), dict)
        and set(payload["modelUsage"]) == {engine}
    )


def classify_cli_result(engine, returncode, payload, stderr, host_evidence=None):
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
    aup_refusal = is_aup_refusal(payload, engine)
    catastrophic = (cli_failed or not usage_models) and not aup_refusal
    incomplete = not cli_failed and payload_failure
    if usage_models and usage_models != [engine]:
        return catastrophic, incomplete, False, engine_attested
    infra_invalid = failure and (
        api_error_status in {429, 529}
        or (api_error_status is None and INFRA_FAILURE.search(stderr) is not None)
        or (is_enotfound_envelope(payload) and host_origin_attested(host_evidence))
    )
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


def write_immutable_bytes(path, value):
    path.write_bytes(value)
    path.chmod(0o444)


def raw_attestation(path):
    payload = path.read_bytes()
    return {"bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def finalize_raw_row(row, stdout_path, stderr_path):
    for stream, path in (("stdout", stdout_path), ("stderr", stderr_path)):
        payload = path.read_bytes()
        write_immutable_bytes(path, payload)
        for field, value in raw_attestation(path).items():
            row[f"cli_{stream}_{field}"] = value


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
        "cli_returncode": None,
        "cli_stdout_bytes": 0,
        "cli_stdout_sha256": hashlib.sha256(b"").hexdigest(),
        "cli_stderr_bytes": 0,
        "cli_stderr_sha256": hashlib.sha256(b"").hexdigest(),
        "cli_argv": None,
        "host_origin_attestation": None,
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
    cli_invocations = []
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
            finalize_raw_row(row, stdout_path, stderr_path)
            cli_invocations.append({"position_index": position_index, "task": task_id, "argv": None, "returncode": None, "stdout": raw_attestation(stdout_path), "stderr": raw_attestation(stderr_path)})
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
            failed_row(row, task_dir, stderr_path, f"attempt setup failure: {exc}", False)
            custody["links"].append(
                {"position_index": position_index, "launched_resume_id": resume_id, "reported_session_id": None}
            )
            custody["broken"] = True
            custody["break_position"] = position_index
            write_json(session_dir / "custody.json", custody)
            broken = True
            finalize_raw_row(row, stdout_path, stderr_path)
            cli_invocations.append({"position_index": position_index, "task": task_id, "argv": None, "returncode": None, "stdout": raw_attestation(stdout_path), "stderr": raw_attestation(stderr_path)})
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
        row["cli_argv"] = cmd
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
            row["cli_returncode"] = proc.returncode
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
            detected_at = iso_now()
            host_evidence = control_probe(detected_at) if is_enotfound_envelope(payload) else None
            if host_evidence is not None:
                write_json(att_dir / "host-origin.json", host_evidence)
                (att_dir / "host-origin.json").chmod(0o444)
            catastrophic, incomplete, infra_invalid, engine_attested = classify_cli_result(
                engine, proc.returncode, payload, failure_text.decode("utf-8", errors="replace"), host_evidence,
            )
            row["catastrophic"] = catastrophic
            row["incomplete"] = incomplete
            row["infra_invalid"] = infra_invalid
            row["engine_attested"] = engine_attested
            row["host_origin_attestation"] = host_evidence
        else:
            row["catastrophic"] = True
            row["infra_invalid"] = False
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
            and (proc.returncode == 0 or is_aup_refusal(payload, engine))
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
            failed_row(row, task_dir, stderr_path, stderr_path.read_text(encoding="utf-8").strip(), False)
        finalize_raw_row(row, stdout_path, stderr_path)
        cli_invocations.append({"position_index": position_index, "task": task_id, "argv": row["cli_argv"], "returncode": row["cli_returncode"], "stdout": raw_attestation(stdout_path), "stderr": raw_attestation(stderr_path)})
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
    write_json(session_dir / "cli-attestation.json", {"schema": "iter0112-cli-attestation-v1", "cli_version": "2.1.226", "cli_path": str(PIN), "cli_sha256": PIN_SHA256, "strict_whole_envelope_json": True, "strict_mcp_config": True, "invocations": cli_invocations})
    return session_dir


def self_test():
    cases = (
        ("success", 0, {"subtype": "success", "modelUsage": {"claude-opus-5": {"input_tokens": 1}}}, "", (False, False, False)),
        ("mid-run-429", 1, {"is_error": True, "subtype": "error", "api_error_status": 429, "modelUsage": {"claude-opus-5": {"input_tokens": 1}}}, "", (True, False, True)),
        ("zero-turn-limit-text", 1, {"is_error": True, "subtype": "error", "api_error_status": None, "modelUsage": {}}, "session limit", (True, False, True)),
        ("zero-turn-without-limit-text", 1, {"is_error": True, "subtype": "error", "api_error_status": None, "modelUsage": {}}, "refused", (True, False, False)),
        ("engine-refusal-after-turn", 1, {"is_error": True, "subtype": "error", "modelUsage": {"claude-opus-5": {"input_tokens": 1}}}, "refused", (True, False, False)),
        ("sonnet-success", 0, {"subtype": "success", "modelUsage": {"claude-sonnet-5": {"input_tokens": 1}}}, "", (False, False, False)),
    )
    for label, returncode, payload, stderr, expected in cases:
        actual = classify_cli_result("claude-sonnet-5" if label == "sonnet-success" else "claude-opus-5", returncode, payload, stderr)[:3]
        assert actual == expected, (label, actual)
    for path, digest in CNET_FIXTURES:
        receipt = pathlib.Path(path)
        assert sha256(receipt) == digest
        assert is_enotfound_envelope(json.loads(receipt.read_bytes()))
    envelope = {"is_error": True, "api_error_status": None, "result": ENOTFOUND_RESULT, "modelUsage": {"claude-opus-5": {"outputTokens": 0}}}
    assert is_enotfound_envelope(envelope)
    assert classify_cli_result("claude-opus-5", 1, envelope, "")[:3] == (True, False, False)
    attested = {"schema": HOST_CONTROL_SCHEMA, "mechanism": "socket.getaddrinfo(AF_UNSPEC, SOCK_STREAM)", "hostname": HOST_CONTROL_HOSTNAME, "failure_detected_at": iso_now(), "observed_at": iso_now(), "result": "control_resolution_failed", "addresses": [], "error": "gaierror:test", "raw_result": "gaierror('test')"}
    assert classify_cli_result("claude-opus-5", 1, envelope, "", attested)[:3] == (True, False, True)
    aup = {"is_error": True, "subtype": "success", "terminal_reason": "api_error", "stop_reason": "refusal", "api_error_status": None, "modelUsage": {"claude-opus-5": {}}}
    assert is_aup_refusal(aup, "claude-opus-5")
    assert classify_cli_result("claude-opus-5", 1, aup, "")[:3] == (False, False, False)
    assert not is_aup_refusal({**aup, "stop_reason": "end_turn"}, "claude-opus-5")
    assert not is_aup_refusal({key: value for key, value in aup.items() if key != "api_error_status"}, "claude-opus-5")
    assert not is_aup_refusal({**aup, "modelUsage": ["claude-opus-5"]}, "claude-opus-5")
    negatives = (
        {**envelope, "is_error": False},
        {**envelope, "api_error_status": 0},
        {key: value for key, value in envelope.items() if key != "api_error_status"},
        {**envelope, "result": ENOTFOUND_RESULT + "!"},
    )
    assert not any(is_enotfound_envelope(item) for item in negatives)
    assert (position_class(1, 4), position_class(2, 4), position_class(3, 4), position_class(4, 4)) == ("EARLY", "EARLY", "LATE", "LATE")
    row = mark_custody_broken({"custody_ok": True, "custody_broken": False})
    assert row == {"custody_ok": False, "custody_broken": True}
    assert project_slug(pathlib.Path("/private/tmp/nx-0023ab893188/ws")) == "-private-tmp-nx-0023ab893188-ws"
    with tempfile.TemporaryDirectory(prefix="iter0112-driver-") as temporary:
        root = pathlib.Path(temporary)
        tasks_root = root / "tasks"
        for task_id in ("A", "B"):
            task = tasks_root / task_id
            task.joinpath("visible").mkdir(parents=True)
            task.joinpath("hidden").mkdir()
            task.joinpath("task.json").write_text(json.dumps({"goal": "reply"}), encoding="utf-8")
            task.joinpath("hidden/manifests.json").write_text(json.dumps({"manifestations": [{"id": task_id}]}), encoding="utf-8")
        aup_stdout = json.dumps({"is_error": True, "subtype": "success", "terminal_reason": "api_error", "stop_reason": "refusal", "api_error_status": None, "modelUsage": {"claude-opus-5": {}}, "session_id": "scoreable-aup"}).encode()

        class FakeProc:
            returncode = 1
            stdout = aup_stdout
            stderr = b""

        original_tasks_root, original_run, original_oracle, original_append = SMOKE_TASKS_ROOT, subprocess.run, run_oracle, append_row
        globals()["SMOKE_TASKS_ROOT"] = tasks_root
        globals()["run_oracle"] = lambda _task, _workdir, _output: (1, 1, True)
        globals()["subprocess"].run = lambda *_args, **_kwargs: FakeProc()
        def quiet_append(paths, row):
            encoded = json.dumps(row, sort_keys=True)
            for path in paths:
                with path.open("a", encoding="utf-8") as handle:
                    handle.write(encoded + "\n")
        globals()["append_row"] = quiet_append
        try:
            session_dir = run_session("claude-opus-5", "aup-reachability", ["A", "B"], 1, root / "out", "self-test", True)
            executed = [json.loads(line) for line in (session_dir / "rows.jsonl").read_text().splitlines()]
            assert all(row["catastrophic"] is False and row["infra_invalid"] is False and row["custody_ok"] is True and row["manifestations_failed"] == row["manifestations_total"] == 1 for row in executed)
            setup_dir = run_session("claude-opus-5", "setup-reachability", ["MISSING", "B"], 1, root / "out", "self-test", True)
            setup_rows = [json.loads(line) for line in (setup_dir / "rows.jsonl").read_text().splitlines()]
            assert setup_rows[0]["infra_invalid"] is False and setup_rows[0]["cli_argv"] is None and setup_rows[0]["catastrophic"] is True
            def raise_oserror(*_args, **_kwargs):
                raise OSError("self-test runner failure")
            globals()["subprocess"].run = raise_oserror
            runner_dir = run_session("claude-opus-5", "runner-reachability", ["A", "B"], 1, root / "out", "self-test", True)
            runner_rows = [json.loads(line) for line in (runner_dir / "rows.jsonl").read_text().splitlines()]
            assert runner_rows[0]["infra_invalid"] is False and runner_rows[0]["cli_argv"] is not None and runner_rows[0]["catastrophic"] is True
        finally:
            globals()["SMOKE_TASKS_ROOT"] = original_tasks_root
            globals()["subprocess"].run = original_run
            globals()["run_oracle"] = original_oracle
            globals()["append_row"] = original_append
            for session in ("aup-reachability", "setup-reachability", "runner-reachability"):
                custody_path = root / "out" / f"claude-opus-5.{session}.r1" / "custody.json"
                if custody_path.exists():
                    workspace = pathlib.Path(json.loads(custody_path.read_text())["cwd"]).parent
                    if workspace.exists():
                        shutil.rmtree(workspace)
    print("PASS sh-driver-0112 self-test: registered void classification, strict ENOTFOUND two-leg fixtures, scoreable AUP refusal, setup/runner no-void reachability, position, custody")


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
