#!/usr/bin/env python3
"""Frozen iter-0113 L0/L1/L2 layer-lift runner.

Real run modes deliberately fail while PARAMS_PIN_SHA256 is TBD-FREEZE.  The
registration owner replaces that value only after independently freezing the
apparatus.  --derive-panel and --self-test never invoke a model.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import contextlib
import datetime as dt
import hashlib
import io
import json
import os
import pathlib
import re
import runpy
import secrets
import signal
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from fractions import Fraction
from typing import Any, Callable, Iterable
from zoneinfo import ZoneInfo


REPO = pathlib.Path("/Users/aipalm/Documents/GitHub/devlyn-cli")
HERE = REPO / "benchmark/layer-lift"
PAIR_COLLECTOR = runpy.run_path(REPO / "config/skills/_shared/collect-codex-findings.py")
TASKS_ROOT = REPO / "benchmark/executor-quality/tasks-0102"
PARAMS_PATH = HERE / "registered-params.json"
PANEL_PATH = HERE / "panel-quick.json"
SCRIPTS_PATH = HERE / "scripts.sha256"
CLAUDE_ISOLATION = REPO / "benchmark/ceiling/scripts/claude-isolation.py"
PARAMS_PIN_SHA256 = "38e0761882a9e2f4d3aab32e6d2d238ffe5dcca342f00b45d6e6dd8bb2cc425b"
MODEL_RE = re.compile(r"^claude-[A-Za-z0-9][A-Za-z0-9.-]*$")
INFRA_FAILURE = re.compile(r"http\s*429|http\s*529|rate[ -]?limit|session[ -]?limit|usage[ -]?limit|overloaded", re.IGNORECASE)
CLASS_RE = re.compile(r"^EQ3-(AF|BD|MI|UA)[1-8]$")
ARMS = ("L0", "L1", "L2")
BASE_REPS = {"L0": 4, "L1": 1, "L2": 1}
APPARATUS_FILES = (
    "benchmark/ceiling/scripts/claude-isolation.py",
    "benchmark/layer-lift/README.md",
    "benchmark/layer-lift/panel-quick.json",
    "benchmark/layer-lift/run-lift-panel.py",
    "benchmark/layer-lift/score-lift.py",
)
PARAMS_PIN_FILES = {
    "benchmark/layer-lift/run-lift-panel.py",
    "benchmark/layer-lift/score-lift.py",
}
PARAMS_PIN_LINE = re.compile(rb'(?m)^PARAMS_PIN_SHA256 = "[^"\r\n]*"\r?\n')
SETTINGS_BYTES = b'{"hooks":{"Stop":[{"hooks":[{"type":"command","command":"python3 \\"$CLAUDE_PROJECT_DIR/.claude/skills/_shared/resolve-stop-hook.py\\"","timeout":30}]}]}}\n'
ENGINES_BYTES = b'{"executor":"claude"}\n'
ROW_LOCK = threading.Lock()


class Refusal(RuntimeError):
    pass
class CellInterrupted(RuntimeError):
    pass
class WindowInterrupted(RuntimeError):
    pass
class InterruptionController:
    def __init__(self) -> None:
        self.event = threading.Event()
        self.lock = threading.RLock()
        self.groups: set[int] = set()

    @property
    def interrupted(self) -> bool:
        return self.event.is_set()

    def begin_cell(self) -> bool:
        with self.lock:
            return not self.event.is_set()

    def register_process_group(self, pid: int) -> None:
        with self.lock:
            self.groups.add(pid)
            interrupted = self.event.is_set()
        if interrupted:
            self._signal_group(pid, signal.SIGTERM)

    def unregister_process_group(self, pid: int) -> None:
        with self.lock:
            self.groups.discard(pid)

    @staticmethod
    def _signal_group(pid: int, signum: int) -> None:
        try:
            os.killpg(pid, signum)
        except ProcessLookupError:
            pass

    def request_interrupt(self) -> None:
        with self.lock:
            if self.event.is_set():
                return
            self.event.set()
            process_groups = tuple(self.groups)
        for pid in process_groups:
            self._signal_group(pid, signal.SIGTERM)

    def handle_sigterm(self, _signum: int, _frame: object) -> None:
        self.request_interrupt()

    def refuse_if_interrupted(self) -> None:
        if self.event.is_set():
            raise CellInterrupted("window-boundary interruption")
def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    return sha256_bytes(path.read_bytes())


def normalized_apparatus_sha256(root: pathlib.Path = REPO) -> str:
    digest = hashlib.sha256()
    for relative in sorted(APPARATUS_FILES):
        data = (root / relative).read_bytes()
        if relative in PARAMS_PIN_FILES:
            data, count = PARAMS_PIN_LINE.subn(b'PARAMS_PIN_SHA256 = "TBD-FREEZE"\n', data)
            if count != 1:
                raise Refusal(f"apparatus params-pin line count differs: {relative}")
        digest.update(relative.encode("utf-8") + b"\0")
        digest.update(sha256_bytes(data).encode("ascii") + b"\n")
    return digest.hexdigest()


def validate_apparatus(params: dict[str, Any], root: pathlib.Path = REPO) -> None:
    if normalized_apparatus_sha256(root) != params.get("apparatus_sha256"):
        raise Refusal("normalized apparatus digest mismatch")
    if params.get("base_reps") != BASE_REPS:
        raise Refusal("runner BASE_REPS differs from registered base_reps")


def reject_constant(token: str) -> None:
    raise ValueError(f"invalid JSON numeric constant: {token}")


def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def strict_json_bytes(raw: bytes) -> object:
    return json.loads(
        raw,
        parse_constant=reject_constant,
        object_pairs_hook=reject_duplicates,
    )


def read_object(path: pathlib.Path) -> dict[str, Any]:
    value = strict_json_bytes(path.read_bytes())
    if not isinstance(value, dict):
        raise Refusal(f"JSON object required: {path}")
    return value


def canonical_json(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def fraction_text(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def task_class(task: str) -> str:
    match = CLASS_RE.fullmatch(task)
    if match is None:
        raise Refusal(f"invalid task id: {task}")
    return match.group(1)


def derive_panel(calibrator: pathlib.Path) -> dict[str, Any]:
    payload = read_object(calibrator)
    if payload.get("engine") != "claude-sonnet-5":
        raise Refusal("calibrator engine is not claude-sonnet-5")
    q_cal = payload.get("q_cal")
    if not isinstance(q_cal, dict) or len(q_cal) != 32:
        raise Refusal("calibrator q_cal must contain 32 tasks")
    ranked: dict[str, list[tuple[Fraction, str]]] = {name: [] for name in ("AF", "BD", "MI", "UA")}
    for task, value in q_cal.items():
        if not isinstance(task, str) or not isinstance(value, str):
            raise Refusal("calibrator q_cal entries must be string fractions")
        cls = task_class(task)
        try:
            distance = abs(Fraction(value) - Fraction(1, 2))
        except (ValueError, ZeroDivisionError) as exc:
            raise Refusal(f"invalid q_cal fraction for {task}") from exc
        ranked[cls].append((distance, task))
    if any(len(items) != 8 for items in ranked.values()):
        raise Refusal("calibrator must contain 8 tasks per class")
    tasks = {cls: [task for _, task in sorted(ranked[cls])[:3]] for cls in sorted(ranked)}
    return {
        "calibrator_sha256": sha256_file(calibrator),
        "rule": "per class, 3 ids minimizing exact Fraction abs(q_cal - 1/2); ties lexical id",
        "tasks": tasks,
    }


def write_derived_panel(params_path: pathlib.Path = PARAMS_PATH, panel_path: pathlib.Path = PANEL_PATH) -> dict[str, Any]:
    params = read_object(params_path)
    panel = derive_panel(pathlib.Path(params["calibrator"]["path"]))
    panel_path.parent.mkdir(parents=True, exist_ok=True)
    panel_path.write_bytes(canonical_json(panel))
    return panel


def selected_tasks(params: dict[str, Any], panel_name: str, panel_path: pathlib.Path = PANEL_PATH) -> list[str]:
    derived = derive_panel(pathlib.Path(params["calibrator"]["path"]))
    committed = read_object(panel_path)
    if committed != derived:
        raise Refusal("panel-quick.json does not match exact re-derivation")
    if panel_name == "quick":
        return [task for cls in sorted(derived["tasks"]) for task in derived["tasks"][cls]]
    manifest = read_object(pathlib.Path(params["corpus"]["manifest_path"]))
    tasks = manifest.get("tasks")
    if not isinstance(tasks, dict) or len(tasks) != 32:
        raise Refusal("full panel manifest does not contain 32 tasks")
    return sorted(tasks)


def intervention_digest(entries: Iterable[tuple[str, bytes]]) -> str:
    digest = hashlib.sha256()
    for relative, data in sorted(entries):
        digest.update(relative.encode() + b"\0")
        digest.update(sha256_bytes(data).encode("ascii") + b"\0")
        digest.update(str(len(data)).encode("ascii") + b"\n")
    return digest.hexdigest()


def source_intervention_sha256() -> str:
    entries = [
        (f".claude/skills/{path.relative_to(REPO / 'config/skills').as_posix()}", path.read_bytes())
        for path in (REPO / "config/skills").rglob("*")
        if path.is_file()
    ]
    for name in ("CLAUDE.md", "AGENTS.md"):
        entries.append((name, (REPO / name).read_bytes()))
    entries.extend((
        (".claude/settings.json", SETTINGS_BYTES),
        (".devlyn/engines.json", ENGINES_BYTES),
    ))
    return intervention_digest(entries)


def staged_intervention_sha256(work: pathlib.Path) -> str:
    skills = work / ".claude/skills"
    required = [work / "CLAUDE.md", work / "AGENTS.md", work / ".claude/settings.json", work / ".devlyn/engines.json"]
    if not skills.is_dir() or any(not path.is_file() for path in required):
        raise Refusal("staged intervention is incomplete")
    files = [path for path in skills.rglob("*") if path.is_file()] + required
    return intervention_digest(
        (path.relative_to(work).as_posix(), path.read_bytes()) for path in files
    )


def validate_staged_intervention(work: pathlib.Path, params: dict[str, Any]) -> str:
    digest = staged_intervention_sha256(work)
    if digest != params["harness"]["staged_intervention_sha256"]:
        raise Refusal("staged intervention digest mismatch")
    return digest


def validate_script_manifest(path: pathlib.Path = SCRIPTS_PATH) -> list[str]:
    errors: list[str] = []
    expected_targets = {
        target.resolve()
        for target in HERE.iterdir()
        if target.is_file() and target != SCRIPTS_PATH and target.name != "drain-quick.py"
    } | {
        CLAUDE_ISOLATION.resolve(),
        pathlib.Path("/Users/aipalm/.local/share/nx01/iter0102/freeze/candidate-manifest.json").resolve(),
    }
    seen: set[pathlib.Path] = set()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [f"scripts manifest unreadable: {exc}"]
    if not lines:
        return ["scripts manifest is empty"]
    for number, line in enumerate(lines, 1):
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if match is None:
            errors.append(f"scripts manifest line {number} malformed")
            continue
        expected, name = match.groups()
        target = pathlib.Path(name)
        if not target.is_absolute():
            target = REPO / target
        target = target.resolve()
        if target in seen:
            errors.append(f"scripts manifest duplicate target: {name}")
        seen.add(target)
        try:
            actual = sha256_file(target)
        except OSError as exc:
            errors.append(f"scripts manifest target unreadable: {name}: {exc}")
            continue
        if actual != expected:
            errors.append(f"scripts manifest digest mismatch: {name}")
    missing = expected_targets - seen
    extra = seen - expected_targets
    if missing or extra:
        errors.append(
            "scripts manifest target set mismatch: "
            f"missing={[str(item) for item in sorted(missing)]}, "
            f"extra={[str(item) for item in sorted(extra)]}"
        )
    return errors


def registered_binary(name: str, binary_path: str, expected_sha256: str) -> tuple[pathlib.Path, str]:
    binary = pathlib.Path(binary_path)
    if not binary.is_file():
        raise Refusal(f"registered {name} binary is missing: {binary}")
    if not os.access(binary, os.X_OK):
        raise Refusal(f"registered {name} binary is not executable: {binary}")
    try:
        digest = sha256_file(binary)
    except OSError as exc:
        raise Refusal(f"registered {name} binary is unreadable: {binary}: {exc}") from exc
    if digest != expected_sha256:
        raise Refusal(f"registered {name} binary digest mismatch: {binary}")
    return binary, digest


def corpus_task_is_sealed(
    task: str,
    params: dict[str, Any],
    tasks_root: pathlib.Path = TASKS_ROOT,
) -> bool:
    try:
        manifest = read_object(pathlib.Path(params["corpus"]["manifest_path"]))
        tasks = manifest["tasks"]
        tree = sha256_bytes(json.dumps(tasks, sort_keys=True, separators=(",", ":")).encode())
        expected = tasks[task]
        if tree != params["corpus"]["tree_sha256"] or not isinstance(expected, dict) or not expected:
            return False
        task_dir = tasks_root / task
        entries = list(task_dir.rglob("*"))
        if any(path.is_symlink() for path in entries):
            return False
        actual = {path.relative_to(task_dir).as_posix(): path for path in entries if path.is_file()}
        return set(actual) == set(expected) and all(sha256_file(actual[name]) == digest for name, digest in expected.items())
    except (OSError, KeyError, TypeError, Refusal):
        return False


def real_writer_check(
    repo: pathlib.Path,
    process_probe: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> tuple[bool, str]:
    try:
        proc = process_probe(
            ["/bin/ps", "ax", "-o", "pid=,command="],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"writer check unavailable: {exc}"
    if proc.returncode != 0:
        return False, f"writer check failed: {proc.stderr.strip()}"
    own = os.getpid()
    active = []
    for line in proc.stdout.splitlines():
        fields = line.strip().split(maxsplit=1)
        if len(fields) != 2 or not fields[0].isdigit() or int(fields[0]) == own:
            continue
        command = fields[1]
        if re.search(r"(?:claude\s+-p|codex\s+exec|grok\s+-p)", command):
            active.append(line.strip())
    state_path = repo / ".devlyn/pipeline.state.json"
    state_in_flight = False
    if state_path.is_file():
        final_report = read_object(state_path).get("phases", {}).get("final_report")
        state_in_flight = final_report is None or final_report.get("verdict") is None
    if active or state_in_flight:
        return False, "live writer/state found: " + "; ".join(active + ([str(state_path)] if state_in_flight else []))
    return True, "quiet"


def in_quiet_window(now: dt.datetime, params: dict[str, Any]) -> bool:
    local = now.astimezone(ZoneInfo("Asia/Seoul"))
    start = int(str(params["quiet_window_kst"]["start"]).split(":")[0])
    end = int(str(params["quiet_window_kst"]["end"]).split(":")[0])
    return local.hour >= start or local.hour < end


def preflight(
    params_path: pathlib.Path = PARAMS_PATH,
    *,
    writer_probe: Callable[[pathlib.Path], tuple[bool, str]] = real_writer_check,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    if PARAMS_PIN_SHA256 == "TBD-FREEZE":
        errors.append("registered-params pin is TBD-FREEZE; fable must freeze the instrument")
    elif sha256_file(params_path) != PARAMS_PIN_SHA256:
        errors.append("registered-params.json pin mismatch")
    params = read_object(params_path)
    try:
        validate_apparatus(params)
    except (OSError, Refusal) as exc:
        errors.append(str(exc))
    errors.extend(validate_script_manifest())
    checks = (
        (pathlib.Path(params["corpus"]["manifest_path"]), params["corpus"]["manifest_sha256"], "corpus manifest"),
        (pathlib.Path(params["calibrator"]["path"]), params["calibrator"]["sha256"], "calibrator"),
    )
    for path, expected, label in checks:
        try:
            if sha256_file(path) != expected:
                errors.append(f"{label} digest mismatch")
        except OSError as exc:
            errors.append(f"{label} unreadable: {exc}")
    for name, path, expected in (
        ("Claude", params["claude"]["binary_path"], params["claude"]["binary_sha256"]),
        ("Codex", params["pair"]["codex_binary_path"], params["pair"]["codex_binary_sha256"]),
    ):
        try:
            registered_binary(name, path, expected)
        except Refusal as exc:
            errors.append(str(exc))
    try:
        if source_intervention_sha256() != params["harness"]["staged_intervention_sha256"]:
            errors.append("staged intervention source digest mismatch")
    except OSError as exc:
        errors.append(f"staged intervention source unreadable: {exc}")
    selected_tasks(params, "quick")
    okay, detail = writer_probe(REPO)
    if not okay:
        errors.append(detail)
    instant = now or dt.datetime.now(dt.timezone.utc)
    if in_quiet_window(instant, params):
        errors.append("23:00-01:00 KST quiet-window exclusion is active")
    if errors:
        raise Refusal("; ".join(errors))
    return params


def run_command(command: list[str], *, cwd: pathlib.Path, env: dict[str, str] | None = None, timeout: int = 60) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def run_cell_command(
    command: list[str],
    *,
    cwd: pathlib.Path,
    env: dict[str, str] | None = None,
    timeout: int,
    interruption: InterruptionController | None,
) -> subprocess.CompletedProcess[bytes]:
    """Run one cell child in its own group so driver SIGTERM reaches descendants."""
    if interruption is not None:
        interruption.refuse_if_interrupted()
    proc = subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    if interruption is not None:
        interruption.register_process_group(proc.pid)
    try:
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                InterruptionController._signal_group(proc.pid, signal.SIGKILL)
                stdout, stderr = proc.communicate()
                raise subprocess.TimeoutExpired(command, timeout, output=stdout, stderr=stderr)
            try:
                stdout, stderr = proc.communicate(timeout=min(remaining, 0.25))
                break
            except subprocess.TimeoutExpired:
                if interruption is not None and interruption.interrupted:
                    raise CellInterrupted("window-boundary interruption")
        if interruption is not None:
            interruption.refuse_if_interrupted()
        return subprocess.CompletedProcess(command, proc.returncode, stdout, stderr)
    finally:
        if interruption is not None:
            if interruption.interrupted:
                InterruptionController._signal_group(proc.pid, signal.SIGKILL)
                proc.communicate()
            interruption.unregister_process_group(proc.pid)


def invoke_launcher(
    command: list[str],
    cwd: pathlib.Path,
    timeout: int,
    injected: Callable[[list[str], pathlib.Path, int, dict[str, str] | None], subprocess.CompletedProcess[bytes]] | None = None,
    interruption: InterruptionController | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    """One injection seam keeps self-tests off real Claude/Keychain/network."""
    if injected is not None:
        return injected(command, cwd, timeout, env)
    return run_cell_command(
        command,
        cwd=cwd,
        env=env,
        timeout=timeout,
        interruption=interruption,
    )


def git(work: pathlib.Path, *args: str, timeout: int = 60) -> subprocess.CompletedProcess[bytes]:
    return run_command(["git", "-C", str(work), *args], cwd=work, timeout=timeout)


def stage_harness(work: pathlib.Path, goal: bytes, params: dict[str, Any]) -> str:
    for command in (
        ["git", "init", "-q"],
        ["git", "config", "user.name", "devlyn-meter"],
        ["git", "config", "user.email", "meter@local"],
        ["git", "add", "-A"],
        ["git", "commit", "-qm", "baseline"],
        ["git", "-c", "tag.gpgsign=false", "tag", "baseline"],
    ):
        proc = run_command(command, cwd=work)
        if proc.returncode != 0:
            raise Refusal(f"baseline git setup failed: {proc.stderr.decode(errors='replace').strip()}")
    (work / ".claude").mkdir()
    (work / ".devlyn").mkdir()
    shutil.copytree(REPO / "config/skills", work / ".claude/skills")
    for name in ("CLAUDE.md", "AGENTS.md"):
        shutil.copy2(REPO / name, work / name)
    (work / ".claude/settings.json").write_bytes(SETTINGS_BYTES)
    (work / ".devlyn/engines.json").write_bytes(ENGINES_BYTES)
    (work / ".devlyn/goal.txt").write_bytes(goal)
    return validate_staged_intervention(work, params)


def manifestation_count(task_dir: pathlib.Path) -> int:
    try:
        payload = read_object(task_dir / "hidden/manifests.json")
        values = payload["manifestations"]
        return len(values) if isinstance(values, list) else 0
    except (OSError, KeyError, Refusal):
        return 0


def envelope_usage(payload: dict[str, Any] | None) -> tuple[list[str], dict[str, int]]:
    if payload is None:
        return [], {}
    usage = payload.get("modelUsage")
    if not isinstance(usage, dict):
        return [], {}
    outputs: dict[str, int] = {}
    for model, counters in usage.items():
        if not isinstance(model, str) or not isinstance(counters, dict):
            continue
        output = counters.get("outputTokens", counters.get("output_tokens"))
        if type(output) is int and output >= 0:
            outputs[model] = output
    return sorted(usage), outputs


def decode_envelope(raw: bytes) -> dict[str, Any] | None:
    try:
        value = strict_json_bytes(raw)
    except (ValueError, UnicodeError):
        return None
    return value if isinstance(value, dict) else None


def find_state(work: pathlib.Path) -> tuple[pathlib.Path | None, dict[str, Any] | None]:
    active = work / ".devlyn/pipeline.state.json"
    candidates = [active] if active.is_file() else sorted((work / ".devlyn/runs").glob("*/pipeline.state.json"))
    if len(candidates) != 1:
        return None, None
    try:
        return candidates[0], read_object(candidates[0])
    except (OSError, Refusal):
        return candidates[0], None


def sibling_artifact(state_path: pathlib.Path | None, work: pathlib.Path, name: str) -> pathlib.Path | None:
    candidates = [work / ".devlyn" / name]
    if state_path is not None:
        candidates.append(state_path.parent / name)
    existing = [path for path in candidates if path.is_file()]
    return existing[0] if existing else None


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


def codex_stderr_attestation(
    raw: bytes,
    *,
    tokens_required: bool = True,
) -> tuple[str | None, str | None, str | None, int | None, list[str]]:
    text = raw.decode("utf-8", errors="replace")
    lines = text.splitlines()
    errors: list[str] = []
    version_indexes = [index for index, line in enumerate(lines) if line.startswith("OpenAI Codex v")]
    versions = [lines[index].removeprefix("OpenAI Codex v") for index in version_indexes]
    header: list[str] = []
    if len(version_indexes) == 1:
        start = version_indexes[0] + 1
        if start < len(lines) and lines[start] == "--------":
            try:
                stop = lines.index("--------", start + 1)
                header = lines[start + 1:stop]
            except ValueError:
                pass
    models = [line.split(":", 1)[1].strip() for line in header if line.startswith("model:")]
    efforts = [line.split(":", 1)[1].strip() for line in header if line.startswith("reasoning effort:")]
    token_indexes = [index for index, line in enumerate(lines) if line.strip() == "tokens used"]
    version = versions[0] if len(versions) == 1 else None
    model = models[0] if len(models) == 1 else None
    effort = efforts[0] if len(efforts) == 1 else None
    tokens: int | None = None
    if len(token_indexes) == 1 and token_indexes[0] + 1 < len(lines):
        rendered = lines[token_indexes[0] + 1].strip().replace(",", "")
        if rendered.isdigit():
            tokens = int(rendered)
    if version is None:
        errors.append("Codex stderr version header missing or ambiguous")
    if model is None:
        errors.append("Codex stderr model header missing or ambiguous")
    if effort is None:
        errors.append("Codex stderr effort header missing or ambiguous")
    if tokens is None and tokens_required:
        errors.append("Codex stderr tokens-used value missing or malformed")
    return version, model, effort, tokens, errors


def validate_codex_stderr(
    raw: bytes,
    params: dict[str, Any],
    *,
    tokens_required: bool = True,
) -> tuple[str | None, str | None, str | None, int | None, list[str]]:
    version, model, effort, tokens, errors = codex_stderr_attestation(
        raw,
        tokens_required=tokens_required,
    )
    if version is not None and version != params["pair"]["codex_cli_version"]:
        errors.append("L2 Codex CLI version attestation mismatch")
    if model is not None and model != params["pair"]["model_id"]:
        errors.append("L2 pair model attestation mismatch")
    if effort is not None and effort != params["pair"]["effective_effort"]:
        errors.append("L2 pair effort attestation mismatch")
    return version, model, effort, tokens, errors


def surface_close_receipt(
    state: dict[str, Any],
    envelope_path: pathlib.Path | None,
) -> tuple[bool, list[str]]:
    phases = state.get("phases")
    surface = phases.get("surface_close") if isinstance(phases, dict) else None
    ran = (
        isinstance(surface, dict)
        and surface.get("skipped_reason") != "auto_surface_close_claude_unavailable"
    )
    errors: list[str] = []
    if ran and envelope_path is None:
        errors.append("surface-close state records a run but envelope is absent")
    if not ran and envelope_path is not None:
        errors.append("surface envelope exists without state run")
    return ran, errors


def verification_bullets(path: pathlib.Path | None) -> int:
    if path is None or not path.is_file():
        return 0
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    inside = False
    count = 0
    for line in lines:
        if line.startswith("## "):
            if inside:
                break
            inside = line.strip() == "## Verification"
            continue
        if inside and line.startswith("- "):
            count += 1
    return count


def diff_changed_by_verify(state: dict[str, Any], state_path: pathlib.Path | None, work: pathlib.Path) -> bool | None:
    rounds = state.get("rounds")
    if not isinstance(rounds, dict) or type(rounds.get("global")) is not int or rounds["global"] < 1:
        return False
    roots = [work / ".devlyn"]
    if state_path is not None:
        roots.append(state_path.parent)
    receipts: list[pathlib.Path] = []
    for root in roots:
        receipts.extend(root.glob("closure-durability.round-*.json"))
    surface = state.get("phases", {}).get("surface_close") if isinstance(state.get("phases"), dict) else None
    durability = surface.get("durability") if isinstance(surface, dict) else None
    ledger_origins = {
        item.get("origin_phase")
        for item in durability
        if isinstance(item, dict) and isinstance(item.get("origin_phase"), str)
    } if isinstance(durability, list) else set()
    established = False
    for receipt_path in dict.fromkeys(receipts):
        try:
            receipt = read_object(receipt_path)
        except (OSError, Refusal):
            continue
        if receipt.get("origin_phase") != "verify":
            continue
        established = True
        before = receipt.get("pre_fix_sha")
        after = receipt.get("post_restore_sha")
        if isinstance(before, str) and isinstance(after, str):
            before_tree = git(work, "rev-parse", f"{before}^{{tree}}")
            after_tree = git(work, "rev-parse", f"{after}^{{tree}}")
            if before_tree.returncode != 0 or after_tree.returncode != 0:
                return None
            if before_tree.stdout.strip() != after_tree.stdout.strip():
                return True
        else:
            return None
    if established:
        return False
    if ledger_origins and "verify" not in ledger_origins:
        return False
    return None


def harness_terminal(state: dict[str, Any], report_path: pathlib.Path | None = None) -> str | None:
    phases = state.get("phases")
    final = phases.get("final_report") if isinstance(phases, dict) else None
    if not isinstance(final, dict):
        return None
    artifacts = final.get("artifacts")
    if isinstance(artifacts, dict):
        explicit = artifacts.get("terminal_verdict")
        if isinstance(explicit, str) and explicit:
            return explicit
    verdict = final.get("verdict")
    if verdict in {"PASS", "PASS_WITH_ISSUES", "NEEDS_WORK"}:
        return verdict
    if verdict == "BLOCKED":
        if report_path is not None and report_path.is_file():
            match = re.search(
                r"BLOCKED:[A-Za-z0-9_.-]+",
                report_path.read_text(encoding="utf-8", errors="replace"),
            )
            if match is not None:
                return match.group(0)
        for phase_name, phase in (phases.items() if isinstance(phases, dict) else []):
            if isinstance(phase, dict) and phase.get("verdict") == "BLOCKED":
                return f"BLOCKED:{phase_name}"
        return "BLOCKED:unspecified"
    if isinstance(verdict, str) and verdict.startswith("BLOCKED:"):
        return verdict
    return None


def copy_if_present(source: pathlib.Path | None, destination: pathlib.Path) -> None:
    if source is not None and source.is_file():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def run_oracle(
    task_dir: pathlib.Path,
    work: pathlib.Path,
    output: pathlib.Path,
    interruption: InterruptionController | None = None,
) -> tuple[int, int, bool]:
    total = manifestation_count(task_dir)
    try:
        proc = run_cell_command(
            [sys.executable, str(task_dir / "hidden/oracle.py"), str(work)],
            cwd=work,
            timeout=60,
            interruption=interruption,
        )
        output.write_bytes(proc.stdout)
        if proc.returncode != 0:
            return total, total, True
        payload = strict_json_bytes(proc.stdout)
        manifestations = payload["manifestations"] if isinstance(payload, dict) else None
        if not isinstance(manifestations, list):
            return total, total, True
        failed = sum(1 for item in manifestations if not isinstance(item, dict) or item.get("passed") is not True)
        return len(manifestations), failed, False
    except (OSError, subprocess.TimeoutExpired, ValueError, UnicodeError, KeyError):
        output.write_bytes(b"")
        return total, total, True


def base_row(run_id: str, attempt: int, arm: str, task: str, rep: int, model: str, topup: bool) -> dict[str, Any]:
    return {
        "run_id": f"{run_id}:a{attempt}:{arm}:{task}:r{rep}",
        "attempt": attempt,
        "arm": arm,
        "task": task,
        "class": task_class(task),
        "rep": rep,
        "topup": topup,
        "model_requested": model,
        "model_attested": None,
        "surface_close_ran": False,
        "surface_model_attested": None,
        "pair_judge_ran": None,
        "pair_model_attested": None,
        "pair_effort_attested": None,
        "pair_cli_version_attested": None,
        "pair_timeout": False,
        "codex_tokens_total": 0,
        "terminal": "BARE" if arm == "L0" else "BLOCKED:unclassified",
        "f_tree": "1/1",
        "f_ship": "1/1",
        "manifestations_total": 0,
        "manifestations_failed": 0,
        "catastrophic": False,
        "incomplete": False,
        "infra_invalid": False,
        "infra_reason": None,
        "wall_ms": 0,
        "output_tokens": {"parent": {}, "surface_close": {}},
        "output_tokens_total": 0,
        "verification_bullets": None if arm == "L0" else 0,
        "fix_round_ran": None if arm != "L2" else False,
        "diff_changed_by_pair": None,
        "prompt_sha256": sha256_bytes(b""),
        "goal_sha256": sha256_bytes(b""),
        "staged_intervention_sha256": None,
        "claude_binary_sha256": None,
        "started_at": None,
        "finished_at": None,
    }


def execute_attempt(
    *,
    params: dict[str, Any],
    model: str,
    run_id: str,
    attempt: int,
    arm: str,
    task: str,
    rep: int,
    out_dir: pathlib.Path,
    topup: bool = False,
    launcher_command: Callable[[list[str], pathlib.Path, int, dict[str, str] | None], subprocess.CompletedProcess[bytes]] | None = None,
    interruption: InterruptionController | None = None,
    codex_auth_source: pathlib.Path | None = None,
) -> dict[str, Any]:
    row = base_row(run_id, attempt, arm, task, rep, model, topup)
    started = dt.datetime.now(dt.timezone.utc)
    row["started_at"] = started.isoformat().replace("+00:00", "Z")
    task_dir = TASKS_ROOT / task
    attempt_dir = out_dir / "attempts" / f"a{attempt}" / arm / task / f"r{rep}"
    attempt_dir.mkdir(parents=True, exist_ok=True)
    scratch = pathlib.Path("/private/tmp") / f"nx-{secrets.token_hex(8)}"
    work = scratch / "ws"
    claude_home = scratch / "claude-home"
    codex_home = scratch / "codex-home"
    stdout_path = attempt_dir / "cli.stdout"
    stderr_path = attempt_dir / "cli.stderr"
    oracle_path = attempt_dir / "oracle.json"
    launcher_metadata_path = attempt_dir / "launcher-metadata.json"
    stdout_path.write_bytes(b"")
    stderr_path.write_bytes(b"")
    oracle_path.write_bytes(b"")
    reasons: list[str] = []
    payload: dict[str, Any] | None = None
    state: dict[str, Any] | None = None
    state_path: pathlib.Path | None = None
    timed_out = False
    pair_verdict = None
    try:
        if interruption is not None:
            interruption.refuse_if_interrupted()
        if not corpus_task_is_sealed(task, params, TASKS_ROOT):
            raise Refusal("corpus task integrity mismatch")
        task_payload = read_object(task_dir / "task.json")
        goal = task_payload.get("goal")
        if not isinstance(goal, str):
            raise Refusal("task goal must be a string")
        goal_bytes = goal.encode("utf-8")
        row["goal_sha256"] = sha256_bytes(goal_bytes)
        shutil.copytree(task_dir / "visible", work)
        binary, row["claude_binary_sha256"] = registered_binary(
            "Claude", params["claude"]["binary_path"], params["claude"]["binary_sha256"],
        )
        if arm == "L0":
            prompt = goal_bytes
        else:
            row["staged_intervention_sha256"] = stage_harness(work, goal_bytes, params)
            prompt = (
                b"/devlyn:resolve --goal-file .devlyn/goal.txt --no-pair"
                if arm == "L1"
                else b"/devlyn:resolve --goal-file .devlyn/goal.txt --pair-verify"
            )
        prompt_path = attempt_dir / "prompt.txt"
        prompt_path.write_bytes(prompt)
        row["prompt_sha256"] = sha256_bytes(prompt)
        command = [
            sys.executable, str(CLAUDE_ISOLATION), "launch", "--mode", "arm",
            "--model", model, "--home", str(claude_home), "--codex-home", str(codex_home),
            "--workdir", str(work), "--prompt-file", str(prompt_path),
            "--debug-file", str(attempt_dir / "claude-debug.log"),
            "--metadata-out", str(launcher_metadata_path),
            "--user-memory-file", str(pathlib.Path.home() / ".claude/CLAUDE.md"),
        ]
        if arm == "L0":
            command.extend(["--allowed-tools-csv", ",".join(params["tools"])])
        launch_env = {
            **os.environ, "CEILING_TEST_CLAUDE_BIN": str(binary),
            "CEILING_TEST_CODEX_BIN": params["pair"]["codex_binary_path"],
        }
        if codex_auth_source is not None:
            launch_env["CEILING_TEST_AUTH_JSON"] = str(codex_auth_source)
        bound = params["bounds_seconds"]["L0" if arm == "L0" else "harness"]
        before = time.monotonic()
        try:
            proc = invoke_launcher(command, work, bound, launcher_command, interruption, launch_env)
        except subprocess.TimeoutExpired as exc:
            proc = subprocess.CompletedProcess(command, 124, exc.output or b"", exc.stderr or b"")
            timed_out = True
        row["wall_ms"] = bound * 1000 if timed_out else int((time.monotonic() - before) * 1000)
        try:
            launcher_metadata = read_object(launcher_metadata_path)
        except FileNotFoundError as exc:
            if not timed_out or os.path.lexists(launcher_metadata_path):
                reasons.append(f"launcher metadata unavailable: {exc}")
        except (OSError, Refusal, ValueError) as exc:
            reasons.append(f"launcher metadata invalid: {exc}")
        else:
            direct_claude = launcher_metadata.get("direct_claude")
            if not isinstance(direct_claude, dict) or (
                direct_claude.get("path") != str(binary)
                or direct_claude.get("sha256") != row["claude_binary_sha256"]
            ):
                reasons.append("launcher Claude binary attestation mismatch")
            direct_codex = launcher_metadata.get("direct_codex")
            if not isinstance(direct_codex, dict) or (
                direct_codex.get("path") != params["pair"]["codex_binary_path"]
                or direct_codex.get("sha256") != params["pair"]["codex_binary_sha256"]
            ):
                reasons.append("launcher Codex binary attestation mismatch")
        stdout_path.write_bytes(proc.stdout)
        stderr_path.write_bytes(proc.stderr)
        payload = decode_envelope(proc.stdout)
        failure_text = (proc.stdout + b"\n" + proc.stderr).decode("utf-8", errors="replace")
        catastrophic, incomplete, infra_invalid, model_attested = classify_cli_result(
            model, proc.returncode, payload, failure_text,
        )
        row["catastrophic"] = catastrophic
        row["incomplete"] = incomplete
        row["model_attested"] = model_attested
        if timed_out:
            row["terminal"] = "TIMEOUT"
            infra_invalid = model_attested not in {None, model}
        if infra_invalid:
            reasons.append("CLI infrastructure failure")
        models, parent_output = envelope_usage(payload)
        row["output_tokens"]["parent"] = parent_output
        if payload is not None and not timed_out:
            if any(runtime_model not in parent_output for runtime_model in models):
                reasons.append("parent modelUsage outputTokens are missing or malformed")
        if proc.returncode == 78 and not timed_out:
            reasons.append("Claude isolation launcher failed")
        if arm != "L0" and not timed_out:
            state_path, state = find_state(work)
            if state_path is None or state is None:
                reasons.append("missing or ambiguous pipeline state")
            else:
                copy_if_present(state_path, attempt_dir / "pipeline.state.json")
                final_report_path = sibling_artifact(state_path, work, "final-report.md")
                terminal = harness_terminal(state, final_report_path)
                if terminal is None:
                    reasons.append("pipeline state lacks terminal final_report verdict")
                else:
                    row["terminal"] = terminal
                    if terminal in {"BLOCKED:claude-unavailable", "BLOCKED:codex-unavailable"}:
                        reasons.append(f"engine unavailable: {terminal}")
                surface_path = sibling_artifact(state_path, work, "surface-close.output.json")
                ran, surface_errors = surface_close_receipt(state, surface_path)
                row["surface_close_ran"] = ran
                reasons.extend(surface_errors)
                if ran:
                    if surface_path is not None:
                        copy_if_present(surface_path, attempt_dir / "surface-close.output.json")
                        surface_payload = decode_envelope(surface_path.read_bytes())
                        surface_models, surface_output = envelope_usage(surface_payload)
                        row["surface_model_attested"] = ",".join(surface_models) or None
                        row["output_tokens"]["surface_close"] = surface_output
                        if surface_models != ["claude-sonnet-5"]:
                            reasons.append(f"surface modelUsage expected ['claude-sonnet-5'], got {surface_models}")
                        if any(runtime_model not in surface_output for runtime_model in surface_models):
                            reasons.append("surface modelUsage outputTokens are missing or malformed")
                criteria_path = sibling_artifact(state_path, work, "criteria.generated.md")
                row["verification_bullets"] = verification_bullets(criteria_path)
                copy_if_present(criteria_path, attempt_dir / "criteria.generated.md")
                risk = state.get("risk_profile")
                phases = state.get("phases")
                verify = phases.get("verify") if isinstance(phases, dict) else None
                trigger = verify.get("pair_trigger") if isinstance(verify, dict) else None
                sub = verify.get("sub_verdicts") if isinstance(verify, dict) else None
                pair_verdict = sub.get("pair_judge") if isinstance(sub, dict) else None
                codex_stdout = sibling_artifact(state_path, work, "codex-judge.stdout")
                codex_stderr = sibling_artifact(state_path, work, "codex-judge.stderr")
                captured = codex_stdout is not None or codex_stderr is not None
                unopened = (
                    isinstance(phases, dict) and "verify" in phases and verify is None
                    and row["terminal"].startswith("BLOCKED:")
                )
                mechanical_skip = (
                    isinstance(trigger, dict) and trigger.get("eligible") is False
                    and trigger.get("reasons") == [] and trigger.get("skipped_reason") == "mechanical_blocker"
                    and isinstance(sub, dict) and sub.get("mechanical") in {"NEEDS_WORK", "BLOCKED"}
                    and "judge" in sub and sub["judge"] is None
                    and "pair_judge" in sub and pair_verdict is None
                    and row["terminal"] not in {"PASS", "PASS_WITH_ISSUES", "TIMEOUT"}
                )
                if arm == "L1":
                    if not isinstance(risk, dict) or risk.get("pair_default_enabled") is not False:
                        reasons.append("L1 risk_profile.pair_default_enabled is not false")
                    if not (unopened or mechanical_skip or (
                        isinstance(trigger, dict) and trigger.get("skipped_reason") == "user_no_pair"
                        and trigger.get("eligible") is False and trigger.get("reasons") == []
                        and isinstance(sub, dict) and "pair_judge" in sub and pair_verdict is None
                    )):
                        reasons.append("L1 pair trigger is not a canonical skip")
                    if captured:
                        reasons.append("L1 skipped pair has captures")
                else:
                    rounds = state.get("rounds")
                    row["fix_round_ran"] = isinstance(rounds, dict) and type(rounds.get("global")) is int and rounds["global"] >= 1
                    row["diff_changed_by_pair"] = diff_changed_by_verify(state, state_path, work)
                    row["pair_judge_ran"] = not (unopened or mechanical_skip)
                    row["pair_timeout"] = pair_verdict == "TIMEOUT"
                    if state.get("pair_verify") is not True:
                        reasons.append("L2 state.pair_verify is not true")
                    if row["pair_judge_ran"] is False:
                        if captured:
                            reasons.append("L2 skipped pair has captures")
                    else:
                        if not (
                            isinstance(trigger, dict) and trigger.get("eligible") is True
                            and isinstance(trigger.get("reasons"), list) and "pair.default" in trigger["reasons"]
                            and all(isinstance(reason, str) and reason for reason in trigger["reasons"])
                            and trigger.get("skipped_reason") is None
                        ):
                            reasons.append("L2 pair trigger does not establish dispatch")
                        if pair_verdict not in {"PASS", "PASS_WITH_ISSUES", "NEEDS_WORK", "BLOCKED", "TIMEOUT"}:
                            reasons.append("L2 pair_judge sub-verdict is null or invalid")
                copy_if_present(final_report_path, attempt_dir / "final-report.md")
        if arm == "L2":
            if timed_out:
                state_path, state = find_state(work)
            codex_stdout = sibling_artifact(state_path, work, "codex-judge.stdout")
            codex_stderr = sibling_artifact(state_path, work, "codex-judge.stderr")
            captured = codex_stdout is not None or codex_stderr is not None
            if timed_out and captured:
                row["pair_judge_ran"] = True
            if row["pair_judge_ran"] is True or captured:
                if codex_stdout is None:
                    reasons.append("L2 codex-judge.stdout is absent")
                else:
                    copy_if_present(codex_stdout, attempt_dir / "codex-judge.stdout")
                    if not timed_out and not row["pair_timeout"]:
                        ranks = PAIR_COLLECTOR["VERDICT_RANK"]
                        try:
                            findings, summary = PAIR_COLLECTOR["collect_stdout"](codex_stdout)
                            normalized_rank = max([ranks[summary["verdict"]]] + [
                                PAIR_COLLECTOR["finding_rank"](finding) for finding in findings
                            ])
                        except (SystemExit, UnicodeDecodeError):
                            # Product emission-contract failures are BLOCKED, not free retries.
                            normalized_rank = ranks["BLOCKED"]
                        if ranks.get(pair_verdict, -1) < normalized_rank:
                            reasons.append("L2 pair_judge sub-verdict understates normalized stdout")
                        if normalized_rank >= ranks["NEEDS_WORK"] and row["terminal"] in {"PASS", "PASS_WITH_ISSUES"}:
                            reasons.append("L2 shipping terminal contradicts binding pair stdout")
                if codex_stderr is None:
                    reasons.append("L2 codex-judge.stderr is absent")
                else:
                    copy_if_present(codex_stderr, attempt_dir / "codex-judge.stderr")
                    version, pair_model, effort, tokens, header_errors = validate_codex_stderr(
                        codex_stderr.read_bytes(), params, tokens_required=not timed_out and not row["pair_timeout"],
                    )
                    row["pair_cli_version_attested"] = version
                    row["pair_model_attested"] = pair_model
                    row["pair_effort_attested"] = effort
                    row["codex_tokens_total"] = tokens or 0
                    reasons.extend(header_errors)
        rollouts = sorted(codex_home.rglob("rollout-*.jsonl"))
        if rollouts:
            reasons.append(f"{arm} Codex home contains rollout(s)")
        if row["catastrophic"] and not timed_out:
            total = manifestation_count(task_dir)
            failed = total
            oracle_failed = False
        else:
            if interruption is not None:
                interruption.refuse_if_interrupted()
            total, failed, oracle_failed = run_oracle(task_dir, work, oracle_path, interruption)
        row["manifestations_total"] = total
        row["manifestations_failed"] = failed
        if oracle_failed:
            row["catastrophic"] = True
        if total > 0:
            row["f_tree"] = fraction_text(Fraction(failed, total))
        if timed_out or row["incomplete"]:
            row["f_ship"] = "1/1"
        elif arm == "L0":
            row["terminal"] = "BARE"
            row["f_ship"] = row["f_tree"]
        elif row["terminal"] in {"PASS", "PASS_WITH_ISSUES"}:
            row["f_ship"] = row["f_tree"]
        else:
            row["f_ship"] = "1/1"
        if interruption is not None:
            interruption.refuse_if_interrupted()
        diff_stat = git(work, "diff", "baseline..HEAD", "--stat") if arm != "L0" else subprocess.CompletedProcess([], 0, b"", b"")
        status = git(work, "status", "--porcelain") if arm != "L0" else subprocess.CompletedProcess([], 0, b"", b"")
        (attempt_dir / "git-diff.stat").write_bytes(diff_stat.stdout + diff_stat.stderr)
        (attempt_dir / "git-status.porcelain").write_bytes(status.stdout + status.stderr)
    except (OSError, Refusal, subprocess.TimeoutExpired, ValueError, KeyError, TypeError) as exc:
        reasons.append(str(exc))
        row["catastrophic"] = True
        total = manifestation_count(task_dir)
        row["manifestations_total"] = total
        row["manifestations_failed"] = total
        row["f_tree"] = "1/1"
        row["f_ship"] = "1/1"
        stderr_path.write_text(str(exc) + "\n", encoding="utf-8")
    finally:
        if reasons:
            row["infra_invalid"] = True
            row["infra_reason"] = "; ".join(dict.fromkeys(reasons))
        if row["terminal"] == "TIMEOUT" or row["pair_timeout"]:
            row["codex_tokens_total"] = None
            row["output_tokens_total"] = None
        else:
            row["output_tokens_total"] = (
                sum(row["output_tokens"]["parent"].values())
                + sum(row["output_tokens"]["surface_close"].values())
                + row["codex_tokens_total"]
            )
        row["finished_at"] = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
        shutil.rmtree(scratch, ignore_errors=True)
    return row


def append_row(path: pathlib.Path, row: dict[str, Any]) -> None:
    data = json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
    with ROW_LOCK:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())


def load_rows(path: pathlib.Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            value = strict_json_bytes(line.encode())
        except ValueError as exc:
            raise Refusal(f"rows.jsonl:{number}: {exc}") from exc
        if not isinstance(value, dict):
            raise Refusal(f"rows.jsonl:{number}: object required")
        rows.append(value)
    return rows


def latest_rows(rows: Iterable[dict[str, Any]]) -> dict[tuple[str, str, int], dict[str, Any]]:
    latest: dict[tuple[str, str, int], dict[str, Any]] = {}
    for row in rows:
        key = (row.get("arm"), row.get("task"), row.get("rep"))
        if not isinstance(key[0], str) or not isinstance(key[1], str) or type(key[2]) is not int:
            continue
        previous = latest.get(key)
        if previous is None or int(row.get("attempt", 0)) > int(previous.get("attempt", 0)):
            latest[key] = row
    return latest


def saturated(rows: list[dict[str, Any]], tasks: list[str]) -> bool:
    latest = latest_rows(row for row in rows if not row.get("topup"))
    expected = [("L0", task, rep) for task in tasks for rep in range(1, 5)]
    if any(key not in latest or latest[key].get("infra_invalid") for key in expected):
        return False
    values = [Fraction(str(latest[key]["f_ship"])) for key in expected]
    return sum(values, Fraction()) / len(values) < Fraction(1, 10)


def run_metadata(params: dict[str, Any], model: str, panel: str, run_id: str) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "model": model,
        "panel": panel,
        "params_sha256": sha256_file(PARAMS_PATH),
        "apparatus_sha256": params["apparatus_sha256"],
    }


def bind_run_metadata(path: pathlib.Path, current: dict[str, Any], *, rows_exist: bool) -> None:
    if path.exists():
        if read_object(path) != current:
            raise Refusal("run metadata/digests differ from the registered run")
        return
    if rows_exist:
        raise Refusal("rows.jsonl exists without run metadata/digests")
    path.write_bytes(canonical_json(current))


def expected_cell_digests(params: dict[str, Any], arm: str, task: str) -> dict[str, str | None]:
    task_payload = read_object(TASKS_ROOT / task / "task.json")
    goal = task_payload.get("goal")
    if not isinstance(goal, str):
        raise Refusal(f"task goal must be a string: {task}")
    goal_bytes = goal.encode("utf-8")
    if arm == "L0":
        prompt = goal_bytes
        staged = None
    else:
        prompt = (
            b"/devlyn:resolve --goal-file .devlyn/goal.txt --no-pair"
            if arm == "L1"
            else b"/devlyn:resolve --goal-file .devlyn/goal.txt --pair-verify"
        )
        staged = params["harness"]["staged_intervention_sha256"]
    return {
        "prompt_sha256": sha256_bytes(prompt),
        "goal_sha256": sha256_bytes(goal_bytes),
        "staged_intervention_sha256": staged,
        "claude_binary_sha256": params["claude"]["binary_sha256"],
    }


def validate_resume_rows(rows: list[dict[str, Any]], tasks: list[str], params: dict[str, Any], run_id: str) -> set[tuple[str, str, int]]:
    base_keys = {(arm, task, rep) for arm, task, rep, _ in schedule_base(tasks)}
    present: set[tuple[str, str, int]] = set()
    for row in rows:
        key = (row.get("arm"), row.get("task"), row.get("rep"))
        arm, task, rep = key
        attempt = row.get("attempt")
        if arm not in ARMS or task not in tasks or type(rep) is not int or type(attempt) is not int:
            raise Refusal(f"attempt 1 resume ledger contains an unknown cell: {key}")
        if attempt != 1 or row.get("topup") is not False or key not in base_keys:
            raise Refusal("attempt 1 resume accepts only attempt 1 base history")
        if row.get("run_id") != f"{run_id}:a{attempt}:{arm}:{task}:r{rep}":
            raise Refusal(f"attempt 1 resume run identity differs for {key}")
        expected = expected_cell_digests(params, arm, task)
        for field, digest in expected.items():
            if row.get(field) != digest:
                raise Refusal(f"attempt 1 resume {field} differs for {key}")
        if key in present:
            raise Refusal(f"attempt 1 resume ledger contains a duplicate cell: {key}")
        present.add(key)
    return present


def schedule_base(tasks: list[str]) -> list[tuple[str, str, int, bool]]:
    jobs: list[tuple[str, str, int, bool]] = []
    for task in tasks:
        for rep_index in range(1, max(BASE_REPS.values()) + 1):
            for arm in ARMS:
                if rep_index <= BASE_REPS[arm]:
                    jobs.append((arm, task, rep_index, False))
    return jobs


def jobs_for_attempt(
    rows: list[dict[str, Any]],
    tasks: list[str],
    attempt: int,
    *,
    resume_present: set[tuple[str, str, int]] | None = None,
) -> list[tuple[str, str, int, bool]]:
    if attempt == 1:
        expected = schedule_base(tasks)
        if resume_present is not None:
            return [job for job in expected if job[:3] not in resume_present]
        if any(not row.get("topup") for row in rows):
            raise Refusal("attempt 1 base rows already exist")
        return expected
    expected = schedule_base(tasks)
    attempt_one = {
        (row["arm"], row["task"], row["rep"])
        for row in rows
        if not row.get("topup") and row.get("attempt") == 1
    }
    base_keys = {(arm, task, rep) for arm, task, rep, _ in expected}
    if attempt_one != base_keys:
        raise Refusal("attempt 1 base rows are incomplete or contain an extra cell")
    prior_rows = [row for row in rows if int(row.get("attempt", 0)) < attempt]
    prior_latest = latest_rows(prior_rows)
    missing = [(arm, task, rep) for arm, task, rep, _ in expected if (arm, task, rep) not in prior_latest]
    if missing:
        raise Refusal(f"base rows before attempt {attempt} are incomplete: {missing}")
    ordered_keys = [(arm, task, rep) for arm, task, rep, _ in expected]
    ordered_keys.extend(sorted(key for key in prior_latest if key not in base_keys))
    current_keys = {
        (row["arm"], row["task"], row["rep"])
        for row in rows
        if row.get("attempt") == attempt
    }
    jobs: list[tuple[str, str, int, bool]] = []
    for key in ordered_keys:
        prior = prior_latest[key]
        if prior.get("infra_invalid") is not True:
            continue
        if prior.get("attempt") != attempt - 1:
            raise Refusal(f"attempt {attempt - 1} replacement is missing for infrastructure-invalid cell {key}")
        if key in current_keys:
            raise Refusal(f"attempt {attempt} row already exists for {key}")
        jobs.append((key[0], key[1], key[2], bool(prior.get("topup"))))
    return jobs


def detach(args: argparse.Namespace) -> int:
    out = pathlib.Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    argv = [arg for arg in sys.argv[1:] if arg != "--detach"]
    stdout = (out / "driver.stdout").open("ab")
    stderr = (out / "driver.stderr").open("ab")
    proc = subprocess.Popen(
        [sys.executable, str(pathlib.Path(__file__).resolve()), *argv],
        cwd=REPO,
        stdin=subprocess.DEVNULL,
        stdout=stdout,
        stderr=stderr,
        preexec_fn=os.setsid,
        close_fds=True,
    )
    (out / "driver.pid").write_text(f"{proc.pid}\n", encoding="ascii")
    stdout.close()
    stderr.close()
    print(proc.pid)
    return 0


def attempt_artifact_dir(out: pathlib.Path, attempt: int, arm: str, task: str, rep: int) -> pathlib.Path:
    return out / "attempts" / f"a{attempt}" / arm / task / f"r{rep}"


def append_committed_row(path: pathlib.Path, row: dict[str, Any], controller: InterruptionController) -> bool:
    previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM})
    try:
        if controller.interrupted:
            return False
        append_row(path, row)
        return True
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)


def execute_jobs(args: argparse.Namespace, params: dict[str, Any], jobs: list[tuple[str, str, int, bool]], *, attempt_runner: Callable[..., dict[str, Any]] = execute_attempt, controller: InterruptionController | None = None, install_sigterm_handler: bool = True) -> list[dict[str, Any]]:
    out = pathlib.Path(args.out).resolve()
    rows_path = out / "rows.jsonl"
    results: list[dict[str, Any]] = []
    interrupt = controller or InterruptionController()
    previous_handler = None
    if install_sigterm_handler:
        if threading.current_thread() is not threading.main_thread():
            raise Refusal("SIGTERM handler installation requires the main thread")
        previous_handler = signal.signal(signal.SIGTERM, interrupt.handle_sigterm)
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=params["lanes"], thread_name_prefix="lift")

    def run_job(job: tuple[str, str, int, bool]) -> dict[str, Any]:
        arm, task, rep, topup = job
        if not interrupt.begin_cell():
            raise CellInterrupted("window-boundary interruption")
        if getattr(args, "resume", False):
            shutil.rmtree(attempt_artifact_dir(out, args.attempt, arm, task, rep), ignore_errors=True)
        return attempt_runner(
            params=params, model=args.model, run_id=args.run_id, attempt=args.attempt,
            arm=arm, task=task, rep=rep, out_dir=out, topup=topup, interruption=interrupt,
        )

    pending: dict[concurrent.futures.Future[dict[str, Any]], tuple[str, str, int, bool]] = {}
    try:
        for job in jobs:
            if interrupt.interrupted:
                break
            pending[pool.submit(run_job, job)] = job
        for future in concurrent.futures.as_completed(pending):
            arm, task, rep, _ = pending[future]
            try:
                row = future.result()
            except CellInterrupted:
                shutil.rmtree(attempt_artifact_dir(out, args.attempt, arm, task, rep), ignore_errors=True)
            else:
                if append_committed_row(rows_path, row, interrupt):
                    print(json.dumps(row, sort_keys=True), flush=True)
                    results.append(row)
                else:
                    shutil.rmtree(attempt_artifact_dir(out, args.attempt, arm, task, rep), ignore_errors=True)
        if interrupt.interrupted:
            raise WindowInterrupted("WINDOW-INTERRUPTED")
    finally:
        for future in pending:
            if interrupt.interrupted:
                future.cancel()
        pool.shutdown(wait=True, cancel_futures=True)
        if install_sigterm_handler and previous_handler is not None:
            signal.signal(signal.SIGTERM, previous_handler)
    return results


def validate_panel_model(params: dict[str, Any], model: str, panel: str) -> None:
    if panel == "quick" and model == params["calibrator"]["engine"]:
        raise Refusal("quick panel model must differ from the calibrator engine")


def prepare_run(
    args: argparse.Namespace,
    *,
    preflight_check: Callable[[], dict[str, Any]] = preflight,
    task_check: Callable[[str, dict[str, Any]], bool] = corpus_task_is_sealed,
) -> tuple[dict[str, Any], list[str], pathlib.Path, list[dict[str, Any]]]:
    if MODEL_RE.fullmatch(args.model) is None:
        raise Refusal("--model must be an exact claude-* id")
    params = preflight_check()
    validate_panel_model(params, args.model, args.panel)
    out = pathlib.Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    tasks = selected_tasks(params, args.panel)
    if getattr(args, "smoke", False):
        if args.task not in tasks and args.task not in selected_tasks(params, "full"):
            raise Refusal("--task is not in the sealed corpus")
        tasks = [args.task]
    elif args.task is not None and args.task not in tasks:
        raise Refusal("--task is not in the selected panel")
    unsealed = [task for task in tasks if not task_check(task, params)]
    if unsealed:
        raise Refusal(f"corpus task integrity mismatch: {unsealed}")
    rows = load_rows(out / "rows.jsonl")
    metadata_path = out / "run-metadata.json"
    current = run_metadata(params, args.model, args.panel, args.run_id)
    bind_run_metadata(metadata_path, current, rows_exist=bool(rows))
    if saturated(rows, selected_tasks(params, args.panel)):
        raise Refusal("PANEL_SATURATED: further scheduling refused")
    return params, tasks, out, rows


def smoke_gate(rows: list[dict[str, Any]], model: str, pair: dict[str, Any]) -> bool:
    by_arm = {row["arm"]: row for row in rows}
    checks = {
        "all_rows_infra_valid": len(rows) == len(ARMS) and all(row.get("infra_invalid") is False for row in rows),
        "parent_model_exact": all(by_arm.get(arm, {}).get("model_attested") == model for arm in ARMS),
        "l1_user_no_pair": (
            by_arm.get("L1", {}).get("infra_invalid") is False
            and by_arm.get("L1", {}).get("terminal") != "TIMEOUT"
            and by_arm.get("L1", {}).get("model_attested") == model
        ),
        "surface_close_attested_when_run": all(
            (not row.get("surface_close_ran")) or row.get("surface_model_attested") == "claude-sonnet-5"
            for row in rows if row["arm"] != "L0"
        ),
        "wall_and_token_anchors": (
            all(
                type(by_arm.get(arm, {}).get("wall_ms")) is int
                and by_arm[arm]["wall_ms"] > 0
                and type(by_arm[arm].get("output_tokens_total")) is int
                and by_arm[arm]["output_tokens_total"] > 0
                for arm in ARMS
            )
            and type(by_arm.get("L2", {}).get("codex_tokens_total")) is int
            and by_arm["L2"]["codex_tokens_total"] > 0
        ),
        "l2_pair_attested": by_arm.get("L2", {}).get("pair_judge_ran") is True and all(by_arm.get("L2", {}).get(field) == pair[value] for field, value in (
            ("pair_model_attested", "model_id"), ("pair_effort_attested", "effective_effort"),
            ("pair_cli_version_attested", "codex_cli_version"),
        )),
        "oracle_all_arms": all(
            row.get("manifestations_total", 0) > 0 and row.get("catastrophic") is False
            for row in rows
        ),
    }
    for name, passed in checks.items():
        print(f"SMOKE-CONJUNCT {name}={'PASS' if passed else 'FAIL'}")
    passed = all(checks.values())
    print(f"SMOKE-0113: {'PASS' if passed else 'FAIL'}")
    return passed


def validate_resume_mode(args: argparse.Namespace) -> None:
    if not args.resume:
        return
    if args.attempt != 1:
        raise Refusal("--resume is valid only with --attempt 1")
    if args.smoke:
        raise Refusal("--resume is invalid with --smoke")


def validate_task_mode(args: argparse.Namespace) -> None:
    if args.smoke and not args.task:
        raise Refusal("--smoke requires --task")
    if args.task and not args.smoke and (args.attempt != 1 or not args.resume):
        raise Refusal("--task without --smoke requires --attempt 1 --resume")


def command_run(
    args: argparse.Namespace,
    *,
    prepare: Callable[[argparse.Namespace], tuple[dict[str, Any], list[str], pathlib.Path, list[dict[str, Any]]]] = prepare_run,
    job_runner: Callable[..., list[dict[str, Any]]] = execute_jobs,
) -> int:
    validate_resume_mode(args)
    validate_task_mode(args)
    if args.detach:
        return detach(args)
    params, tasks, _, rows = prepare(args)
    if args.smoke:
        if args.attempt != 1:
            raise Refusal("smoke uses attempt 1 only")
        if rows:
            raise Refusal("smoke output directory must not contain rows")
        jobs = [(arm, tasks[0], 1, False) for arm in ARMS]
        produced = job_runner(args, params, jobs)
        return 0 if smoke_gate(produced, args.model, params["pair"]) else 2
    resume_present = validate_resume_rows(rows, tasks, params, args.run_id) if args.resume else None
    scheduled_tasks = [args.task] if args.task else tasks
    jobs = jobs_for_attempt(rows, scheduled_tasks, args.attempt, resume_present=resume_present)
    if not jobs:
        if args.task:
            print(f"NO-JOBS: {args.task} has no missing base cells")
        return 0
    job_runner(args, params, jobs)
    return 0


def command_topup(args: argparse.Namespace) -> int:
    params, tasks, _, rows = prepare_run(args)
    arm = "L0" if args.leg == "E1" else "L1"
    first = BASE_REPS[arm] + 1
    if args.n < first:
        raise Refusal(f"--n must be >= {first} for {args.leg}")
    latest = latest_rows(rows)
    requested = [(arm, task, rep) for task in tasks for rep in range(first, args.n + 1)]
    invalid_existing = [key for key in requested if key in latest and latest[key].get("infra_invalid") is True]
    if invalid_existing:
        next_attempt = max(int(latest[key]["attempt"]) for key in invalid_existing) + 1
        if next_attempt > 3:
            raise Refusal(f"top-up infrastructure retry budget exhausted: {invalid_existing}")
        raise Refusal(
            f"top-up infrastructure-invalid cells require run --attempt {next_attempt}: {invalid_existing}"
        )
    jobs = [
        (arm, task, rep, True)
        for _, task, rep in requested
        if (arm, task, rep) not in latest
    ]
    execute_jobs(args, params, jobs)
    return 0


def self_test_a15() -> None:
    """Synthetic outcome receipts and inert end-to-end launches; no panel assets."""
    global TASKS_ROOT
    original_tasks = TASKS_ROOT
    with tempfile.TemporaryDirectory(prefix="lift-a15-") as raw:
        root = pathlib.Path(raw).resolve()
        TASKS_ROOT = root / "tasks"
        task = TASKS_ROOT / "EQ3-AF1"
        (task / "visible").mkdir(parents=True)
        (task / "hidden").mkdir()
        (task / "visible/fixture.txt").write_text("synthetic\n")
        (task / "task.json").write_bytes(canonical_json({"goal": "Keep the synthetic fixture."}))
        (task / "hidden/manifests.json").write_bytes(canonical_json({"manifestations": [{}]}))
        (task / "hidden/oracle.py").write_text('print(\'{"manifestations":[{"passed":true}]}\')\n')
        manifest = {"EQ3-AF1": {p.relative_to(task).as_posix(): sha256_file(p) for p in task.rglob("*") if p.is_file()}}
        manifest_path = root / "manifest.json"
        manifest_path.write_bytes(canonical_json({"tasks": manifest}))
        auth = root / "auth.json"
        auth.write_bytes(b'{}\n')
        binary = root / "claude"
        binary.write_text("#!/bin/sh\nexit 99\n")
        binary.chmod(0o700)
        params = read_object(PARAMS_PATH)
        params = {**params, "corpus": {"manifest_path": str(manifest_path),
                  "tree_sha256": sha256_bytes(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode())},
                  "claude": {"binary_path": str(binary), "binary_sha256": sha256_file(binary)},
                  "pair": {**params["pair"], "codex_binary_path": str(binary), "codex_binary_sha256": sha256_file(binary)}}
        pair = params["pair"]
        metadata = {
            "direct_claude": {"path": str(binary), "sha256": sha256_file(binary)},
            "direct_codex": {"path": str(binary), "sha256": sha256_file(binary)},
        }
        telemetry = (f'OpenAI Codex v{pair["codex_cli_version"]}\n--------\n'
                     f'model: {pair["model_id"]}\nreasoning effort: {pair["effective_effort"]}\n'
                     '--------\ntokens used\n11\n').encode()
        parent = canonical_json({"subtype": "success", "modelUsage": {"claude-fixture": {"outputTokens": 10}}})
        mechanical = {"pair_trigger": {"eligible": False, "reasons": [], "skipped_reason": "mechanical_blocker"},
                      "sub_verdicts": {"mechanical": "NEEDS_WORK", "judge": None, "pair_judge": None}}
        executed = {"pair_trigger": {"eligible": True, "reasons": ["pair.default", "mode.pair-verify"], "skipped_reason": None},
                    "sub_verdicts": {"mechanical": "PASS", "judge": "PASS", "pair_judge": "PASS"}}
        scratches: list[pathlib.Path] = []
        counter = 0

        def run(arm: str, verify: object = None, terminal: str = "BLOCKED:fixture", *,
                capture: tuple[bytes | None, bytes | None] = (None, None),
                meta: object = metadata, timeout: bool = False, state_kind: str = "valid",
                returncode: int = 0) -> dict[str, Any]:
            nonlocal counter
            counter += 1
            def launch(command: list[str], work: pathlib.Path, bound: int,
                       env: dict[str, str] | None) -> subprocess.CompletedProcess[bytes]:
                assert bound == params["bounds_seconds"]["L0" if arm == "L0" else "harness"]
                assert command[1] == str(CLAUDE_ISOLATION) and "--timeout-seconds" not in command
                assert env is not None and env["CEILING_TEST_AUTH_JSON"] == str(auth)
                scratches.append(work.parent)
                if arm == "L0":
                    assert pathlib.Path(command[command.index("--prompt-file") + 1]).read_text() == "Keep the synthetic fixture."
                    assert command[command.index("--allowed-tools-csv") + 1] == ",".join(params["tools"])
                    assert not (work / ".claude").exists() and not (work / "AGENTS.md").exists()
                else:
                    assert "--allowed-tools-csv" not in command
                    state = {"pair_verify": True, "risk_profile": {"pair_default_enabled": False},
                             "phases": {"surface_close": {"verdict": None, "skipped_reason": "auto_surface_close_claude_unavailable"},
                                        "verify": verify, "final_report": {"verdict": terminal}}}
                    if state_kind == "absent-verify":
                        del state["phases"]["verify"]
                    state_path = work / ".devlyn/pipeline.state.json"
                    if state_kind != "missing":
                        state_path.write_bytes(b'{' if state_kind == "malformed" else canonical_json(state))
                    for name, content in zip(("stdout", "stderr"), capture):
                        if content is not None:
                            (work / f".devlyn/codex-judge.{name}").write_bytes(content)
                path = pathlib.Path(command[command.index("--metadata-out") + 1])
                if meta == "directory":
                    path.mkdir()
                elif meta is not None:
                    path.write_bytes(meta if isinstance(meta, bytes) else canonical_json(meta))
                if timeout:
                    raise subprocess.TimeoutExpired(command, bound, output=parent, stderr=b"partial stderr\n")
                return subprocess.CompletedProcess(command, returncode, parent, b"")
            row = execute_attempt(params=params, model="claude-fixture", run_id="a15", attempt=1,
                                  arm=arm, task="EQ3-AF1", rep=1, out_dir=root / str(counter),
                                  launcher_command=launch, codex_auth_source=auth)
            assert not scratches[-1].exists()
            artifacts = root / str(counter) / "attempts/a1" / arm / "EQ3-AF1/r1"
            for name, content in zip(("stdout", "stderr"), capture):
                if arm == "L2" and content is not None:
                    assert (artifacts / f"codex-judge.{name}").read_bytes() == content
            if timeout:
                assert (artifacts / "cli.stdout").read_bytes() == parent
                assert (artifacts / "cli.stderr").read_bytes() == b"partial stderr\n"
                assert row["terminal"] == "TIMEOUT" and row["f_ship"] == "1/1"
                assert row["output_tokens_total"] is None and row["codex_tokens_total"] is None
            print("a15-outcome", arm, state_kind, terminal, "timeout=" + str(timeout),
                  "pair_judge_ran=" + str(row["pair_judge_ran"]), "infra=" + str(row["infra_invalid"]), row["infra_reason"])
            return row

        try:
            retained: list[dict[str, Any]] = []
            for arm in ("L1", "L2"):
                for verify in (None, mechanical, {**mechanical, "sub_verdicts": {**mechanical["sub_verdicts"], "mechanical": "BLOCKED"}}):
                    row = run(arm, verify)
                    assert not row["infra_invalid"] and row["f_ship"] == "1/1" and row["f_tree"] == "0/1"
                    assert row["pair_judge_ran"] is (False if arm == "L2" else None)
                    assert row["pair_model_attested"] is None and row["codex_tokens_total"] == 0 and not row["pair_timeout"]
                    retained.append(row)
                for terminal in ("BLOCKED:claude-unavailable", "BLOCKED:codex-unavailable"):
                    infra = run(arm, terminal=terminal)
                    assert infra["infra_invalid"]
                    # The real replacement consumer sees a complete synthetic base ledger.
                    ledger = [base_row("a15", 1, a, t, r, "claude-fixture", u) for a, t, r, u in schedule_base(["EQ3-AF1"])]
                    index = next(i for i, item in enumerate(ledger) if item["arm"] == arm)
                    ledger[index] = infra
                    assert jobs_for_attempt(ledger, ["EQ3-AF1"], 2) == [(arm, "EQ3-AF1", 1, False)]
                    ledger[index] = row
                    assert jobs_for_attempt(ledger, ["EQ3-AF1"], 2) == []
                for kind in ("missing", "malformed", "absent-verify"):
                    assert run(arm, state_kind=kind)["infra_invalid"]
                for invalid in ({"pair_trigger": None}, {**mechanical, "pair_trigger": {**mechanical["pair_trigger"], "eligible": 0}},
                                {**mechanical, "sub_verdicts": {**mechanical["sub_verdicts"], "judge": "PASS"}}):
                    assert run(arm, invalid)["infra_invalid"]
                assert run(arm, mechanical, capture=(b"stale", telemetry))["infra_invalid"]
                assert run(arm, mechanical, terminal="PASS")["infra_invalid"]
            user_skip = {"pair_trigger": {"eligible": False, "reasons": [], "skipped_reason": "user_no_pair"},
                         "sub_verdicts": {"mechanical": "PASS", "judge": "PASS", "pair_judge": None}}
            assert not run("L1", user_skip, terminal="PASS")["infra_invalid"]
            valid = run("L2", executed, terminal="PASS", capture=(b'# SUMMARY {"verdict":"PASS"}\n', telemetry))
            assert not valid["infra_invalid"] and valid["pair_judge_ran"] is True and valid["codex_tokens_total"] == 11
            missing = run("L2", state_kind="missing", capture=(b'# SUMMARY {"verdict":"PASS"}\n', telemetry))
            assert missing["infra_invalid"] and "missing or ambiguous pipeline state" in missing["infra_reason"]
            high = b'{"id":"a15-binding","severity":"HIGH"}\n'
            low = b'{"id":"a15-advisory","severity":"LOW"}\n'
            malformed = (("empty", b""), ("whitespace", b" \n\t"),
                         ("malformed", b"# SUMMARY PASS\n"), ("no-verdict", high),
                         ("binary", b"\xff\xfe"), ("HIGH+PASS", high + b"PASS\n"))
            cases = [(label, output, claim, terminal, invalid)
                     for label, output in malformed
                     for claim, terminal, invalid in (("PASS", "PASS", True),
                                                      ("BLOCKED", "BLOCKED", False),
                                                      ("BLOCKED", "PASS", True))]
            cases += [
                ("NEEDS_WORK falsely claimed PASS", high + b"NEEDS_WORK\n", "PASS", "BLOCKED", True),
                ("binding with overall PASS", high + b"NEEDS_WORK\n", "NEEDS_WORK", "PASS", True),
                ("binding with overall PASS_WITH_ISSUES", high + b"NEEDS_WORK\n", "NEEDS_WORK", "PASS_WITH_ISSUES", True),
                ("binding normalized", high + b"PASS_WITH_ISSUES\n", "NEEDS_WORK", "NEEDS_WORK", False),
                ("binding underclaimed", high + b"PASS_WITH_ISSUES\n", "PASS_WITH_ISSUES", "BLOCKED", True),
                ("FAIL normalized", high + b"FAIL\n", "NEEDS_WORK", "NEEDS_WORK", False),
                ("advisory normalized", low + b"PASS\n", "PASS_WITH_ISSUES", "PASS_WITH_ISSUES", False),
                ("advisory underclaimed", low + b"PASS\n", "PASS", "BLOCKED", True),
                ("stricter outcome", high + b"NEEDS_WORK\n", "BLOCKED", "BLOCKED", False),
                ("PASS stricter outcome", b"PASS\n", "NEEDS_WORK", "NEEDS_WORK", False),
            ]
            for label, output, claim, terminal, invalid in cases:
                verify = {**executed, "sub_verdicts": {**executed["sub_verdicts"], "pair_judge": claim}}
                row = run("L2", verify, terminal=terminal, capture=(output, telemetry))
                print("a15-stream", label, "pair=" + claim, "terminal=" + terminal,
                      "expected_infra=" + str(invalid), "actual_infra=" + str(row["infra_invalid"]))
                assert row["infra_invalid"] is invalid, (label, claim, terminal, row["infra_reason"])
                if not invalid and terminal not in {"PASS", "PASS_WITH_ISSUES"}:
                    assert row["f_ship"] == "1/1" and row["codex_tokens_total"] == 11
                    ledger = [base_row("a15", 1, a, t, r, "claude-fixture", u) for a, t, r, u in schedule_base(["EQ3-AF1"])]
                    index = next(i for i, item in enumerate(ledger) if item["arm"] == "L2")
                    ledger[index] = row
                    assert jobs_for_attempt(ledger, ["EQ3-AF1"], 2) == []
            pair_timeout = {**executed, "sub_verdicts": {**executed["sub_verdicts"], "pair_judge": "TIMEOUT"}}
            row = run("L2", pair_timeout, terminal="NEEDS_WORK", capture=(b"partial", telemetry))
            assert not row["infra_invalid"] and row["pair_timeout"] and row["f_ship"] == "1/1"
            assert row["output_tokens_total"] is None and row["codex_tokens_total"] is None
            assert run("L2", pair_timeout, capture=(b"partial", b"malformed"))["infra_invalid"]
            assert run("L2", pair_timeout, capture=(None, telemetry))["infra_invalid"]
            for bad_capture in ((None, telemetry), (b"PASS", None), (b"PASS", b"malformed"),
                                (b"PASS", telemetry.replace(pair["model_id"].encode(), b"wrong-model")),
                                (b"PASS", telemetry.replace(pair["effective_effort"].encode(), b"wrong-effort")),
                                (b"PASS", telemetry.replace(pair["codex_cli_version"].encode(), b"wrong-version"))):
                assert run("L2", executed, terminal="BLOCKED:fixture", capture=bad_capture)["infra_invalid"]
            assert run("L2", terminal="PASS")["infra_invalid"]
            assert not run("L2", executed, timeout=True, capture=(b"partial", telemetry))["infra_invalid"]
            assert run("L2", executed, timeout=True, capture=(b"partial", b"malformed"))["infra_invalid"]
            for arm in ARMS:
                assert not run(arm, timeout=True, meta=None)["infra_invalid"]
                for bad_meta in (b"{", "directory", {**metadata, "direct_claude": {"path": "wrong"}},
                                 {**metadata, "direct_codex": {"path": "wrong"}}):
                    assert run(arm, timeout=True, meta=bad_meta)["infra_invalid"]
                assert run(arm, meta=None)["infra_invalid"]
                assert run(arm, returncode=78)["infra_invalid"]
            smoke = [run("L0"), retained[0], valid]
            for row in smoke:
                row["wall_ms"] = max(1, row["wall_ms"])
            assert smoke_gate(smoke, "claude-fixture", pair)
            smoke[2] = retained[-1]
            assert not smoke_gate(smoke, "claude-fixture", pair)

            # Exercise the actual isolation subprocess with hostile ambient context.
            receipt = root / "inert.json"
            pids = root / "pids.jsonl"
            mode_path = root / "mode"
            binary.write_text(f'''#!{sys.executable}
import json, os, pathlib, signal, sys, time
root = pathlib.Path({str(root)!r})
mode = (root / "mode").read_text()
if "--version" in sys.argv and mode != "prep":
    print("inert-1")
    sys.exit(0)
if mode in ("sleep", "prep"):
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    for depth in range(2):
        if os.fork():
            break
    with (root / "pids.jsonl").open("a") as stream:
        stream.write(json.dumps([os.getpid(), os.getpgrp()]) + "\\n")
    print("partial inert stream", flush=True)
    time.sleep(30)
else:
    home = pathlib.Path(os.environ["HOME"])
    auth = pathlib.Path(os.environ["CODEX_HOME"]) / "auth.json"
    (root / "inert.json").write_text(json.dumps({{"argv":sys.argv[1:], "env":dict(os.environ),
        "work":str(pathlib.Path.cwd()), "staged":pathlib.Path(".claude/skills").exists(),
        "auth":auth.read_text(), "auth_mode":auth.stat().st_mode & 0o777}}))
    print(json.dumps({{"subtype":"success", "modelUsage":{{"claude-fixture":{{"outputTokens":10}}}}}}))
''')
            params["claude"]["binary_sha256"] = sha256_file(binary)
            params["pair"]["codex_binary_sha256"] = sha256_file(binary)
            hostile = root / "hostile"
            hostile.mkdir()
            (hostile / ".zshenv").write_text("export A15_POISON=1\n")
            credentials = root / "credentials"
            credentials.write_bytes(b'{"fake":"inert"}\n')
            updates = {"HOME": str(hostile), "ZDOTDIR": str(hostile), "PATH": str(hostile),
                       "BASH_ENV": str(hostile / ".zshenv"), "ENV": str(hostile / ".zshenv"),
                       "CEILING_TEST_CLAUDE_CREDENTIALS": str(credentials)}
            original_env = {key: os.environ.get(key) for key in updates}
            try:
                os.environ.update(updates)
                mode_path.write_text("normal")
                actual = execute_attempt(params=params, model="claude-fixture", run_id="inert", attempt=1,
                    arm="L0", task="EQ3-AF1", rep=1, out_dir=root / "normal", codex_auth_source=auth)
                assert not actual["infra_invalid"], actual
                observed = read_object(receipt)
                env = observed["env"]
                assert all(key not in env for key in ("ZDOTDIR", "BASH_ENV", "ENV", "A15_POISON"))
                assert env["HOME"] != str(hostile) and str(hostile) not in env["PATH"]
                assert observed["auth"] == '{}\n' and observed["auth_mode"] == 0o600
                argv = observed["argv"]
                assert argv[argv.index("-p") + 1] == "Keep the synthetic fixture."
                assert argv[argv.index("--allowedTools") + 1] == ",".join(params["tools"]) and "--tools" not in argv
                assert argv[argv.index("--effort") + 1] == "xhigh" and argv[argv.index("--model") + 1] == "claude-fixture"
                assert argv[argv.index("--mcp-config") + 1] == '{"mcpServers":{}}' and "--strict-mcp-config" in argv
                assert argv[argv.index("--setting-sources") + 1] == "project,local"
                assert not observed["staged"] and not pathlib.Path(env["HOME"]).exists()
                print("a15-inert isolation, exact allowedTools, auth, scratch cleanup: PASS")
            finally:
                for key, value in original_env.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value

            for mode, interrupt in (("prep", False), ("prep", True), ("sleep", False), ("sleep", True)):
                mode_path.write_text(mode)
                pids.unlink(missing_ok=True)
                controller = InterruptionController()
                def cancel() -> None:
                    deadline = time.monotonic() + 5
                    while time.monotonic() < deadline:
                        if pids.exists() and len(pids.read_text().splitlines()) == 3:
                            break
                        time.sleep(0.01)
                    controller.request_interrupt()
                thread = threading.Thread(target=cancel) if interrupt else None
                if thread is not None:
                    thread.start()
                os.environ["CEILING_TEST_CLAUDE_CREDENTIALS"] = str(credentials)
                # Capture the actual scratch path without replacing the subprocess call.
                launched: list[pathlib.Path] = []
                def bounded(command: list[str], work: pathlib.Path, bound: int,
                            env: dict[str, str] | None) -> subprocess.CompletedProcess[bytes]:
                    launched.append(work.parent)
                    return run_cell_command(command, cwd=work, timeout=bound, env=env, interruption=controller)
                before = time.monotonic()
                try:
                    try:
                        row = execute_attempt(params={**params, "bounds_seconds": {"L0": 3, "harness": 3}},
                            model="claude-fixture", run_id="inert", attempt=1, arm="L0", task="EQ3-AF1", rep=1,
                            out_dir=root / (mode + str(interrupt)), codex_auth_source=auth,
                            launcher_command=bounded, interruption=controller)
                    except CellInterrupted:
                        assert interrupt
                        assert not append_committed_row(root / "interrupted.jsonl", {}, controller)
                        assert not (root / "interrupted.jsonl").exists()
                    else:
                        assert not interrupt and row["terminal"] == "TIMEOUT" and not row["infra_invalid"], row
                        assert row["output_tokens_total"] is None and row["wall_ms"] == 3000
                    assert time.monotonic() - before < 8
                    assert not launched[0].exists()
                    descendants = [json.loads(line) for line in pids.read_text().splitlines()]
                    assert len(descendants) == 3 and len({pgid for _, pgid in descendants}) == 1
                    for pid, _ in descendants:
                        deadline = time.monotonic() + 3
                        while True:
                            try:
                                os.kill(pid, 0)
                            except ProcessLookupError:
                                break
                            assert time.monotonic() < deadline, f"ordinary descendant survived: {pid}"
                            time.sleep(0.01)
                    print("a15-inert", mode, "interrupt=" + str(interrupt), "ordinary descendants stopped; scratch removed: PASS")
                finally:
                    if thread is not None:
                        thread.join(timeout=6)
                    old_credentials = original_env["CEILING_TEST_CLAUDE_CREDENTIALS"]
                    if old_credentials is None:
                        os.environ.pop("CEILING_TEST_CLAUDE_CREDENTIALS", None)
                    else:
                        os.environ["CEILING_TEST_CLAUDE_CREDENTIALS"] = old_credentials
        finally:
            TASKS_ROOT = original_tasks


def self_test() -> int:
    self_test_a15()
    names: list[str] = []
    params = read_object(PARAMS_PATH)
    def refuses(call: Callable[[], object], text: str) -> None:
        try:
            call()
        except Refusal as exc:
            assert text in str(exc), exc
        else:
            raise AssertionError(f"expected refusal containing {text!r}")

    validate_apparatus(params)
    with tempfile.TemporaryDirectory(prefix="lift-apparatus-") as raw:
        root = pathlib.Path(raw)
        for relative in APPARATUS_FILES:
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO / relative, destination)
        launcher = root / "benchmark/ceiling/scripts/claude-isolation.py"
        launcher.write_bytes(launcher.read_bytes() + b"# drift\n")
        refuses(lambda: validate_apparatus(params, root), "apparatus digest mismatch")
    names.append("normalized-apparatus-digest-refusal")
    mismatched_reps = {**params, "base_reps": {"L0": 4, "L1": 2, "L2": 1}}
    refuses(lambda: validate_apparatus(mismatched_reps), "BASE_REPS differs")
    names.append("registered-base-reps-match-runner")
    derived = derive_panel(pathlib.Path(params["calibrator"]["path"]))
    assert derived == read_object(PANEL_PATH)
    assert derived["tasks"] == {
        "AF": ["EQ3-AF2", "EQ3-AF1", "EQ3-AF5"],
        "BD": ["EQ3-BD2", "EQ3-BD3", "EQ3-BD4"],
        "MI": ["EQ3-MI5", "EQ3-MI3", "EQ3-MI6"],
        "UA": ["EQ3-UA2", "EQ3-UA3", "EQ3-UA5"],
    }
    names.append("exact-panel-derivation")
    with tempfile.TemporaryDirectory(prefix="lift-stage-") as raw:
        root = pathlib.Path(raw)
        work = root / "work"
        shutil.copytree(TASKS_ROOT / "EQ3-AF2/visible", work)
        digest = stage_harness(work, b"goal", params)
        assert digest == params["harness"]["staged_intervention_sha256"]
        assert (work / ".devlyn/engines.json").read_bytes() == ENGINES_BYTES
        assert (work / ".devlyn/goal.txt").read_bytes() == b"goal"
        (work / "CLAUDE.md").write_bytes((work / "CLAUDE.md").read_bytes() + b"drift\n")
        refuses(lambda: validate_staged_intervention(work, params), "intervention digest mismatch")
    names.append("harness-staging")
    names.append("staged-intervention-drift-refusal")
    jobs = schedule_base(["EQ3-AF2", "EQ3-BD2"])
    assert len(jobs) == 12
    assert jobs[:6] == [
        ("L0", "EQ3-AF2", 1, False), ("L1", "EQ3-AF2", 1, False),
        ("L2", "EQ3-AF2", 1, False), ("L0", "EQ3-AF2", 2, False),
        ("L0", "EQ3-AF2", 3, False), ("L0", "EQ3-AF2", 4, False),
    ]
    names.append("task-major-arm-round-robin")
    base = [base_row("retry", 1, arm, task, rep, "claude-test", topup) for arm, task, rep, topup in schedule_base(["EQ3-AF2"])]
    base[2]["infra_invalid"] = True
    assert jobs_for_attempt(base, ["EQ3-AF2"], 2) == [("L2", "EQ3-AF2", 1, False)]
    replacement = base_row("retry", 2, "L2", "EQ3-AF2", 1, "claude-test", False)
    replacement["infra_invalid"] = True
    base.append(replacement)
    assert jobs_for_attempt(base, ["EQ3-AF2"], 3) == [("L2", "EQ3-AF2", 1, False)]
    clean_base = [base_row("retry-topup", 1, arm, task, rep, "claude-test", topup) for arm, task, rep, topup in schedule_base(["EQ3-AF2"])]
    topup_row = base_row("retry-topup", 1, "L0", "EQ3-AF2", 5, "claude-test", True)
    topup_row["infra_invalid"] = True
    clean_base.append(topup_row)
    assert jobs_for_attempt(clean_base, ["EQ3-AF2"], 2) == [("L0", "EQ3-AF2", 5, True)]
    names.append("infra-only-attempt-replacement")
    reply = b'# SUMMARY {"verdict": "PASS"}\n'
    telemetry = (
        b"[codex-monitored] start: ts=2026-07-29T15:47:20Z heartbeat=30s timeout=0s bin=codex\n"
        b"[codex-monitored] isolated=1\n[codex-monitored] codex pid=92976\n"
        b"Reading additional input from stdin...\nOpenAI Codex v0.153.4\n--------\n"
        b"workdir: /fixture\nmodel: gpt-6-astra\nprovider: openai\napproval: never\n"
        b"sandbox: read-only\nreasoning effort: medium\nreasoning summaries: none\n"
        b"session id: fixture\n--------\ncodex\n# SUMMARY {\"verdict\": \"PASS\"}\n"
        b"tokens used\n22,696\n[codex-monitored] codex exited: code=0 elapsed=197s\n"
    )
    assert reply.startswith(b"# SUMMARY") and b"OpenAI Codex" not in reply
    version, pair_model, effort, tokens, errors = validate_codex_stderr(telemetry, params)
    assert (version, pair_model, effort, tokens, errors) == ("0.153.4", "gpt-6-astra", "medium", 22696, [])
    with tempfile.TemporaryDirectory(prefix="lift-pair-streams-") as raw:
        root = pathlib.Path(raw)
        path_bin = root / "path-bin"
        path_bin.mkdir()
        path_claude = path_bin / "claude"
        path_codex = path_bin / "codex"
        for path_binary in (path_claude, path_codex):
            path_binary.write_bytes(b"#!/bin/sh\nexit 99\n")
            path_binary.chmod(0o755)
        auth = root / "auth.json"
        auth.write_bytes(b'{}\n')
        state = {
            "pair_verify": True,
            "rounds": {"global": 0},
            "phases": {
                "surface_close": {
                    "verdict": None,
                    "skipped_reason": "auto_surface_close_claude_unavailable",
                },
                "verify": {"sub_verdicts": {"pair_judge": "PASS"},
                           "pair_trigger": {"eligible": True, "reasons": ["pair.default", "mode.pair-verify"], "skipped_reason": None}},
                "final_report": {"verdict": "PASS"},
            },
        }
        launcher_environments: list[dict[str, str]] = []
        def pair_result(
            stdout: bool,
            stderr: bool,
            metadata_binary: str | None = None,
            metadata_codex_binary: str | None = None,
        ) -> Callable[[list[str], pathlib.Path, int, dict[str, str] | None], subprocess.CompletedProcess[bytes]]:
            def launch(
                command: list[str], work: pathlib.Path, _timeout: int,
                env: dict[str, str] | None,
            ) -> subprocess.CompletedProcess[bytes]:
                assert env is not None
                launcher_environments.append(env)
                metadata_path = pathlib.Path(command[command.index("--metadata-out") + 1])
                metadata_path.write_bytes(canonical_json({
                    "direct_claude": {
                        "path": metadata_binary or params["claude"]["binary_path"],
                        "sha256": params["claude"]["binary_sha256"],
                    },
                    "direct_codex": {
                        "path": metadata_codex_binary or params["pair"]["codex_binary_path"],
                        "sha256": params["pair"]["codex_binary_sha256"],
                    },
                }))
                (work / ".devlyn/pipeline.state.json").write_bytes(canonical_json(state))
                if stdout:
                    (work / ".devlyn/codex-judge.stdout").write_bytes(reply)
                if stderr:
                    (work / ".devlyn/codex-judge.stderr").write_bytes(telemetry)
                parent = {"subtype": "success", "modelUsage": {"claude-opus-5": {"outputTokens": 1}}}
                return subprocess.CompletedProcess(command, 0, canonical_json(parent), b"")
            return launch
        common = dict(
            params=params, model="claude-opus-5", run_id="pair-streams", attempt=1,
            arm="L2", task="EQ3-AF2", out_dir=root, codex_auth_source=auth,
        )
        original_path = os.environ.get("PATH")
        os.environ["PATH"] = str(path_bin) + os.pathsep + (original_path or "")
        try:
            valid = execute_attempt(**common, rep=1, launcher_command=pair_result(True, True))
            assert valid["infra_invalid"] is False and valid["codex_tokens_total"] == 22696
            assert valid["output_tokens_total"] == 22697
            artifacts = root / "attempts/a1/L2/EQ3-AF2/r1"
            assert (artifacts / "codex-judge.stdout").read_bytes() == reply
            assert (artifacts / "codex-judge.stderr").read_bytes() == telemetry
            missing_stdout = execute_attempt(**common, rep=2, launcher_command=pair_result(False, True))
            missing_stderr = execute_attempt(**common, rep=3, launcher_command=pair_result(True, False))
            bad_metadata = execute_attempt(
                **common, rep=4,
                launcher_command=pair_result(True, True, str(path_claude)),
            )
            bad_codex_metadata = execute_attempt(
                **common, rep=5,
                launcher_command=pair_result(True, True, metadata_codex_binary=str(path_codex)),
            )
        finally:
            if original_path is None:
                os.environ.pop("PATH", None)
            else:
                os.environ["PATH"] = original_path
        assert "codex-judge.stdout is absent" in missing_stdout["infra_reason"]
        assert "codex-judge.stderr is absent" in missing_stderr["infra_reason"]
        assert "launcher Claude binary attestation mismatch" in bad_metadata["infra_reason"]
        assert "launcher Codex binary attestation mismatch" in bad_codex_metadata["infra_reason"]
        assert all(
            env["CEILING_TEST_CLAUDE_BIN"] == params["claude"]["binary_path"]
            and env["CEILING_TEST_CODEX_BIN"] == params["pair"]["codex_binary_path"]
            for env in launcher_environments
        )
    names.append("rollout-attestation-and-final-usage")
    with tempfile.TemporaryDirectory(prefix="lift-smoke1-l1-") as raw:
        root = pathlib.Path(raw)
        auth = root / "auth.json"
        auth.write_bytes(b'{}\n')
        blocked_terminal = "BLOCKED:surface-close-adjudication-out-of-surface"
        smoke1_state = {
            "risk_profile": {"pair_default_enabled": False},
            "phases": {
                "surface_close": {"verdict": "BLOCKED"},
                "verify": None,
                "final_report": {"verdict": "BLOCKED"},
            },
        }
        smoke1_report = (
            "# resolve — FINAL REPORT\n\n"
            "| | |\n|---|---|\n"
            f"| **verdict** | **`{blocked_terminal}`** |\n"
        )
        def smoke1_l1_result(
            command: list[str], work: pathlib.Path, _timeout: int,
            _env: dict[str, str] | None,
        ) -> subprocess.CompletedProcess[bytes]:
            metadata_path = pathlib.Path(command[command.index("--metadata-out") + 1])
            metadata_path.write_bytes(canonical_json({
                "direct_claude": {
                    "path": params["claude"]["binary_path"],
                    "sha256": params["claude"]["binary_sha256"],
                },
                "direct_codex": {
                    "path": params["pair"]["codex_binary_path"],
                    "sha256": params["pair"]["codex_binary_sha256"],
                },
            }))
            devlyn = work / ".devlyn"
            (devlyn / "pipeline.state.json").write_bytes(canonical_json(smoke1_state))
            (devlyn / "final-report.md").write_text(smoke1_report, encoding="utf-8")
            (devlyn / "surface-close.output.json").write_bytes(canonical_json({
                "subtype": "success",
                "modelUsage": {"claude-sonnet-5": {"outputTokens": 1}},
            }))
            parent = {"subtype": "success", "modelUsage": {"claude-opus-5": {"outputTokens": 1}}}
            return subprocess.CompletedProcess(command, 0, canonical_json(parent), b"")
        smoke1_l1_row = execute_attempt(
            params=params, model="claude-opus-5", run_id="smoke1-l1", attempt=1,
            arm="L1", task="EQ3-AF2", rep=1, out_dir=root,
            launcher_command=smoke1_l1_result, codex_auth_source=auth,
        )
        copied_report = root / "attempts/a1/L1/EQ3-AF2/r1/final-report.md"
        assert copied_report.read_text(encoding="utf-8") == smoke1_report
        assert harness_terminal(smoke1_state, copied_report) == blocked_terminal
        assert smoke1_l1_row["terminal"] == blocked_terminal
        assert smoke1_l1_row["f_ship"] == "1/1"
        assert smoke1_l1_row["infra_invalid"] is False
        assert smoke1_l1_row["infra_reason"] is None
    with tempfile.TemporaryDirectory(prefix="lift-smoke3-l1-") as raw:
        root = pathlib.Path(raw)
        auth = root / "auth.json"
        auth.write_bytes(b'{}\n')
        smoke3_state = {
            "risk_profile": {"pair_default_enabled": False},
            "phases": {
                "plan": {"verdict": "PASS"},
                "implement": {"verdict": "PASS"},
                "surface_close": {"verdict": "BLOCKED"},
                "build_gate": None,
                "cleanup": None,
                "verify": None,
                "final_report": {"verdict": blocked_terminal},
            },
        }
        assert harness_terminal(smoke3_state) == blocked_terminal
        assert harness_terminal({"phases": {"final_report": {"verdict": "DONE"}}}) is None
        def smoke3_l1_result(
            command: list[str], work: pathlib.Path, timeout: int,
            env: dict[str, str] | None,
        ) -> subprocess.CompletedProcess[bytes]:
            result = smoke1_l1_result(command, work, timeout, env)
            (work / ".devlyn/pipeline.state.json").write_bytes(canonical_json(smoke3_state))
            return result
        smoke3_l1_row = execute_attempt(
            params=params, model="claude-opus-5", run_id="smoke3-l1", attempt=1,
            arm="L1", task="EQ3-AF2", rep=1, out_dir=root,
            launcher_command=smoke3_l1_result, codex_auth_source=auth,
        )
        assert smoke3_l1_row["terminal"] == blocked_terminal
        assert smoke3_l1_row["f_ship"] == "1/1"
        assert smoke3_l1_row["infra_invalid"] is False
        assert smoke3_l1_row["infra_reason"] is None
    with tempfile.TemporaryDirectory(prefix="lift-claude-pin-") as raw:
        root = pathlib.Path(raw)
        refuses(lambda: registered_binary("Claude", str(root / "missing"), params["claude"]["binary_sha256"]), "is missing")
        altered = root / "claude"
        altered.write_bytes(b"altered binary\n")
        altered.chmod(0o755)
        refuses(lambda: registered_binary("Claude", str(altered), params["claude"]["binary_sha256"]), "digest mismatch")
    names.append("path-independent-claude-pin-refusal")
    with tempfile.TemporaryDirectory(prefix="lift-codex-pin-") as raw:
        root = pathlib.Path(raw)
        refuses(lambda: registered_binary("Codex", str(root / "missing"), params["pair"]["codex_binary_sha256"]), "is missing")
        altered = root / "codex"
        altered.write_bytes(b"altered binary\n")
        altered.chmod(0o755)
        refuses(lambda: registered_binary("Codex", str(altered), params["pair"]["codex_binary_sha256"]), "digest mismatch")
    names.append("path-independent-codex-pin-refusal")
    for before, after, expected in (
        (b"v0.153.4", b"v0.153.5", "version attestation mismatch"),
        (b"gpt-6-astra", b"gpt-6-terra", "model attestation mismatch"),
        (b"effort: medium", b"effort: high", "effort attestation mismatch"),
        (b"22,696", b"not-a-number", "tokens-used value"),
    ):
        *_, mismatch_errors = validate_codex_stderr(telemetry.replace(before, after), params)
        assert any(expected in error for error in mismatch_errors), mismatch_errors
    names.append("codex-stdout-header-mismatch-refusal")
    for label, returncode, payload, stderr in (
        ("zero-turn", 1, {"is_error": True, "subtype": "error", "modelUsage": {}}, ""),
        ("429", 1, {"is_error": True, "subtype": "error", "api_error_status": 429, "modelUsage": {"claude-opus-5": {}}}, ""),
        ("529", 1, {"is_error": True, "subtype": "error", "api_error_status": 529, "modelUsage": {"claude-opus-5": {}}}, ""),
    ):
        assert classify_cli_result("claude-opus-5", returncode, payload, stderr)[2] is True, label
    names.append("zero-turn-429-529-infra-replaceable")
    with tempfile.TemporaryDirectory(prefix="lift-outcomes-") as raw:
        outcome_dir = pathlib.Path(raw)
        path_bin = outcome_dir / "path-bin"
        path_bin.mkdir()
        path_claude = path_bin / "claude"
        path_claude.write_bytes(b"#!/bin/sh\nexit 99\n")
        path_claude.chmod(0o755)
        l0_launches: list[tuple[list[str], dict[str, str]]] = []
        def fake_result(returncode: int, payload: dict[str, Any] | None) -> Callable[[list[str], pathlib.Path, int, dict[str, str] | None], subprocess.CompletedProcess[bytes]]:
            raw_payload = canonical_json(payload) if payload is not None else b""
            def launch(
                command: list[str], _cwd: pathlib.Path, _timeout: int,
                env: dict[str, str] | None,
            ) -> subprocess.CompletedProcess[bytes]:
                assert env is not None
                l0_launches.append((command, env))
                if returncode == 124:
                    raise subprocess.TimeoutExpired(command, _timeout)
                pathlib.Path(command[command.index("--metadata-out") + 1]).write_bytes(canonical_json({
                    "direct_claude": {"path": params["claude"]["binary_path"], "sha256": params["claude"]["binary_sha256"]},
                    "direct_codex": {"path": params["pair"]["codex_binary_path"], "sha256": params["pair"]["codex_binary_sha256"]},
                }))
                return subprocess.CompletedProcess(command, returncode, raw_payload, b"")
            return launch
        common = dict(params=params, model="claude-opus-5", attempt=1, arm="L0", task="EQ3-AF2", out_dir=outcome_dir)
        original_path = os.environ.get("PATH")
        os.environ["PATH"] = str(path_bin) + os.pathsep + (original_path or "")
        try:
            timeout_row = execute_attempt(**common, run_id="timeout", rep=1, launcher_command=fake_result(124, None))
            failure = {"is_error": True, "subtype": "error_max_turns", "modelUsage": {"claude-opus-5": {"outputTokens": 1}}}
            incomplete_row = execute_attempt(**common, run_id="incomplete", rep=2, launcher_command=fake_result(0, failure))
        finally:
            if original_path is None:
                os.environ.pop("PATH", None)
            else:
                os.environ["PATH"] = original_path
        assert timeout_row["terminal"] == "TIMEOUT"
        assert timeout_row["f_ship"] == "1/1" and timeout_row["infra_invalid"] is False
        assert timeout_row["wall_ms"] == params["bounds_seconds"]["L0"] * 1000
        assert timeout_row["output_tokens_total"] is None and timeout_row["codex_tokens_total"] is None
        assert incomplete_row["incomplete"] is True and incomplete_row["infra_invalid"] is False
        assert incomplete_row["f_ship"] == "1/1"
        assert all(
            env["CEILING_TEST_CLAUDE_BIN"] == params["claude"]["binary_path"]
            and command[command.index("--allowed-tools-csv") + 1] == ",".join(params["tools"])
            and shutil.which("claude", path=env["PATH"]) == str(path_claude)
            for command, env in l0_launches
        )
    names.append("l0-timeout-and-incomplete-ship-penalty")
    with tempfile.TemporaryDirectory(prefix="lift-surface-") as raw:
        envelope = pathlib.Path(raw) / "surface-close.output.json"
        envelope.write_bytes(b"{}\n")
        ran_state = {"phases": {"surface_close": {"verdict": "PASS"}}}
        idle_state = {"phases": {"surface_close": {
            "verdict": None, "skipped_reason": "auto_surface_close_claude_unavailable",
        }}}
        recovery_state = {"phases": {"surface_close": {
            "verdict": None,
            "skipped_reason": "surface_close_rolled_back_adjudication_malformed",
            "continued_after_block": True,
        }}}
        assert surface_close_receipt(ran_state, None) == (True, ["surface-close state records a run but envelope is absent"])
        assert surface_close_receipt(idle_state, envelope) == (False, ["surface envelope exists without state run"])
        assert surface_close_receipt(recovery_state, envelope) == (True, [])
    names.append("surface-envelope-orphan-and-missing-refusal")
    validate_panel_model(params, "claude-opus-5", "quick")
    validate_panel_model(params, params["calibrator"]["engine"], "full")
    refuses(lambda: validate_panel_model(params, params["calibrator"]["engine"], "quick"), "must differ")
    names.append("quick-calibrator-model-refusal")
    smoke_rows = [base_row("smoke", 1, arm, "EQ3-AF2", 1, "claude-opus-5", False) for arm in ARMS]
    for row in smoke_rows:
        row.update(
            model_attested="claude-opus-5", manifestations_total=1, catastrophic=False,
            wall_ms=1, output_tokens_total=1,
        )
    smoke_rows[1] = {**smoke1_l1_row, "wall_ms": max(smoke1_l1_row["wall_ms"], 1)}
    smoke_rows[2].update(terminal="PASS", pair_judge_ran=True, pair_model_attested=params["pair"]["model_id"],
                         pair_effort_attested=params["pair"]["effective_effort"],
                         pair_cli_version_attested=params["pair"]["codex_cli_version"],
                         codex_tokens_total=1, infra_invalid=True, infra_reason="fixture")
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        assert smoke_gate(smoke_rows, "claude-opus-5", params["pair"]) is False
    assert "SMOKE-CONJUNCT all_rows_infra_valid=FAIL" in captured.getvalue()
    assert "SMOKE-CONJUNCT l1_user_no_pair=PASS" in captured.getvalue()
    names.append("smoke1-l1-verify-absent-valid")
    names.append("smoke-all-rows-infra-valid")
    smoke3_rows = [smoke_rows[0], smoke3_l1_row, smoke_rows[2]]
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        assert smoke_gate(smoke3_rows, "claude-opus-5", params["pair"]) is False
    assert "SMOKE-CONJUNCT l1_user_no_pair=PASS" in captured.getvalue()
    names.append("smoke3-l1-blocked-prefix-terminal")
    smoke_rows[2].update(
        pair_timeout=True, codex_tokens_total=None, output_tokens_total=None,
        infra_invalid=False, infra_reason=None,
    )
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        assert smoke_gate(smoke_rows, "claude-opus-5", params["pair"]) is False
    assert "SMOKE-CONJUNCT wall_and_token_anchors=FAIL" in captured.getvalue()
    names.append("smoke-wall-and-token-anchors")
    with tempfile.TemporaryDirectory(prefix="lift-append-") as raw:
        ledger = pathlib.Path(raw) / "rows.jsonl"
        row = base_row("r", 1, "L0", "EQ3-AF2", 1, "claude-opus-5", False)
        append_row(ledger, row)
        assert load_rows(ledger) == [row]
    names.append("append-fsync-ledger")
    preflight_calls: list[str] = []
    def fake_writer(_repo: pathlib.Path) -> tuple[bool, str]:
        preflight_calls.append("writer")
        return True, "fake quiet"
    calls: list[list[str]] = []
    def fake_launch(
        command: list[str], _cwd: pathlib.Path, _timeout: int,
        _env: dict[str, str] | None,
    ) -> subprocess.CompletedProcess[bytes]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, b'{"subtype":"success","modelUsage":{"claude-test":{"outputTokens":1,"inputTokens":1}}}', b"")
    invoked = invoke_launcher(["fake-claude", "-p", "goal"], pathlib.Path("/private/tmp"), 1, fake_launch)
    assert invoked.returncode == 0 and calls == [["fake-claude", "-p", "goal"]]
    def injected_preflight() -> None:
        preflight(
            writer_probe=fake_writer,
            now=dt.datetime(2026, 9, 3, 3, 0, tzinfo=ZoneInfo("Asia/Seoul")),
        )
    if PARAMS_PIN_SHA256 == "TBD-FREEZE":
        refuses(injected_preflight, "TBD-FREEZE")
    else:  # exercised after the registration owner embeds the final pin
        injected_preflight()
    assert preflight_calls == ["writer"]
    def quiet_process(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(["ps"], 0, "", "")
    with tempfile.TemporaryDirectory(prefix="lift-writer-state-") as raw:
        root = pathlib.Path(raw)
        nested = root / "benchmark/ceiling/external/archive/.devlyn/pipeline.state.json"
        nested.parent.mkdir(parents=True)
        nested.write_bytes(canonical_json({"phases": {"final_report": {"verdict": None}}}))
        assert real_writer_check(root, process_probe=quiet_process) == (True, "quiet")
        root_state = root / ".devlyn/pipeline.state.json"
        root_state.parent.mkdir()
        root_state.write_bytes(canonical_json({"phases": {"final_report": None}}))
        assert real_writer_check(root, process_probe=quiet_process) == (
            False, f"live writer/state found: {root_state}",
        )
        root_state.write_bytes(canonical_json({"phases": {"final_report": {"verdict": None}}}))
        okay, detail = real_writer_check(root, process_probe=quiet_process)
        assert okay is False and str(root_state) in detail
        root_state.write_bytes(canonical_json({"phases": {"final_report": {"verdict": "PASS"}}}))
        assert real_writer_check(root, process_probe=quiet_process) == (True, "quiet")
    names.append("sandbox-writer-and-launcher-injection")
    with tempfile.TemporaryDirectory(prefix="lift-seal-preflight-") as raw:
        root = pathlib.Path(raw)
        changed_tasks = root / "tasks"
        changed_task = changed_tasks / "EQ3-AF2"
        shutil.copytree(TASKS_ROOT / "EQ3-AF2", changed_task)
        visible_file = next(path for path in (changed_task / "visible").rglob("*") if path.is_file())
        visible_file.write_bytes(visible_file.read_bytes() + b"drift\n")
        args = argparse.Namespace(
            model="claude-opus-5", panel="quick", out=str(root / "out"), run_id="seal",
            attempt=1, resume=False, detach=False, smoke=True, task="EQ3-AF2",
        )
        launcher_calls: list[object] = []
        def changed_prepare(run_args: argparse.Namespace) -> tuple[dict[str, Any], list[str], pathlib.Path, list[dict[str, Any]]]:
            return prepare_run(
                run_args,
                preflight_check=lambda: params,
                task_check=lambda task, registered: corpus_task_is_sealed(task, registered, changed_tasks),
            )
        def forbidden_jobs(*_args: object, **_kwargs: object) -> list[dict[str, Any]]:
            launcher_calls.append(object())
            return []
        refuses(
            lambda: command_run(args, prepare=changed_prepare, job_runner=forbidden_jobs),
            "corpus task integrity mismatch",
        )
        assert launcher_calls == []
    names.append("preflight-corpus-drift-zero-launch")
    resume_tasks = ["EQ3-AF2"]
    registered_jobs = schedule_base(resume_tasks)
    completed_jobs = (registered_jobs[0], registered_jobs[2], registered_jobs[4])
    completed_rows: list[dict[str, Any]] = []
    for arm, task, rep, topup in completed_jobs:
        row = base_row("resume", 1, arm, task, rep, "claude-opus-5", topup)
        row.update(expected_cell_digests(params, arm, task))
        completed_rows.append(row)
    present = validate_resume_rows(completed_rows, resume_tasks, params, "resume")
    assert present == {(job[0], job[1], job[2]) for job in completed_jobs}
    assert jobs_for_attempt(completed_rows, resume_tasks, 1, resume_present=present) == [job for job in registered_jobs if job not in completed_jobs]
    refuses(lambda: jobs_for_attempt(completed_rows, resume_tasks, 1), "attempt 1 base rows already exist")
    drifted = [dict(row) for row in completed_rows]
    drifted[-1]["staged_intervention_sha256"] = "f" * 64
    refuses(lambda: validate_resume_rows(drifted, resume_tasks, params, "resume"), "staged_intervention_sha256")
    later = dict(completed_rows[0], attempt=2, run_id="resume:a2:L0:EQ3-AF2:r1")
    refuses(
        lambda: validate_resume_rows([*completed_rows, later], resume_tasks, params, "resume"),
        "only attempt 1 base history",
    )
    topup = dict(completed_rows[0], rep=5, topup=True, run_id="resume:a1:L0:EQ3-AF2:r5")
    refuses(
        lambda: validate_resume_rows([*completed_rows, topup], resume_tasks, params, "resume"),
        "only attempt 1 base history",
    )
    full_resume_tasks = ["EQ3-AF2", "EQ3-BD2"]
    full_resume_rows: list[dict[str, Any]] = []
    for arm, task, rep, topup in schedule_base(full_resume_tasks):
        row = base_row("task-resume", 1, arm, task, rep, "claude-opus-5", topup)
        row.update(expected_cell_digests(params, arm, task))
        full_resume_rows.append(row)
    task_args = argparse.Namespace(
        model="claude-opus-5", panel="quick", out="/fixture", run_id="task-resume",
        attempt=1, resume=True, detach=False, smoke=False, task="EQ3-AF2",
    )
    task_launches: list[list[tuple[str, str, int, bool]]] = []
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        assert command_run(
            task_args,
            prepare=lambda _args: (params, full_resume_tasks, pathlib.Path("/fixture"), full_resume_rows),
            job_runner=lambda _args, _params, jobs: task_launches.append(jobs) or [],
        ) == 0
    assert task_launches == [] and captured.getvalue() == "NO-JOBS: EQ3-AF2 has no missing base cells\n"
    missing_task_rows = [
        row for row in full_resume_rows
        if (row["arm"], row["task"], row["rep"]) != ("L1", "EQ3-AF2", 1)
    ]
    assert command_run(
        task_args,
        prepare=lambda _args: (params, full_resume_tasks, pathlib.Path("/fixture"), missing_task_rows),
        job_runner=lambda _args, _params, jobs: task_launches.append(jobs) or [],
    ) == 0
    assert task_launches == [[("L1", "EQ3-AF2", 1, False)]]
    for invalid in (
        argparse.Namespace(smoke=False, task="EQ3-AF2", attempt=1, resume=False),
        argparse.Namespace(smoke=False, task="EQ3-AF2", attempt=2, resume=True),
    ):
        refuses(lambda invalid=invalid: validate_task_mode(invalid), "--task without --smoke")
    validate_task_mode(task_args)
    names.append("task-resume-full-ledger-task-only-schedule-and-zero-job")
    with tempfile.TemporaryDirectory(prefix="lift-resume-metadata-") as raw:
        metadata_path = pathlib.Path(raw) / "run-metadata.json"
        metadata = {"params_sha256": sha256_file(PARAMS_PATH)}
        bind_run_metadata(metadata_path, metadata, rows_exist=False)
        refuses(lambda: bind_run_metadata(metadata_path, {"params_sha256": "f" * 64}, rows_exist=True), "metadata/digests differ")
    for invalid in (argparse.Namespace(resume=True, attempt=2, smoke=False), argparse.Namespace(resume=True, attempt=1, smoke=True)):
        refuses(lambda invalid=invalid: validate_resume_mode(invalid), "--resume")
    with tempfile.TemporaryDirectory(prefix="lift-resume-interrupt-") as raw:
        resume_out = pathlib.Path(raw)
        resume_args = argparse.Namespace(out=str(resume_out), model="claude-opus-5", run_id="resume-interrupt", attempt=1, resume=True)
        interrupt = InterruptionController()
        started = threading.Event()
        def interrupted_attempt(**kwargs: Any) -> dict[str, Any]:
            artifact = attempt_artifact_dir(pathlib.Path(kwargs["out_dir"]), kwargs["attempt"], kwargs["arm"], kwargs["task"], kwargs["rep"])
            artifact.mkdir(parents=True)
            (artifact / "partial").write_text("not a row\n", encoding="utf-8")
            started.set()
            assert kwargs["interruption"].event.wait(2)
            kwargs["interruption"].refuse_if_interrupted()
            raise AssertionError("interrupted attempt continued")
        def trigger_interrupt() -> None:
            assert started.wait(2)
            interrupt.request_interrupt()
        trigger = threading.Thread(target=trigger_interrupt, name="lift-self-test-interrupt")
        trigger.start()
        try:
            execute_jobs(resume_args, params, [("L0", "EQ3-AF2", 1, False)], attempt_runner=interrupted_attempt, controller=interrupt, install_sigterm_handler=False)
        except WindowInterrupted as exc:
            assert str(exc) == "WINDOW-INTERRUPTED"
        else:
            raise AssertionError("interrupted driver returned success")
        trigger.join(timeout=2)
        assert not trigger.is_alive()
        assert not (resume_out / "rows.jsonl").exists()
        assert not attempt_artifact_dir(resume_out, 1, "L0", "EQ3-AF2", 1).exists()
    names.append("window-interruption-resume")
    print(f"PASS run-lift self-test {len(names)}/{len(names)}: {', '.join(names)}")
    return 0


def parser() -> argparse.ArgumentParser:
    help_suffix = " Real runs refuse until fable replaces TBD-FREEZE after pinning."
    ap = argparse.ArgumentParser(description="iter-0113 layer-lift runner." + help_suffix)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--derive-panel", action="store_true")
    sub = ap.add_subparsers(dest="command")

    run = sub.add_parser("run", help="run base panel or one-task smoke;" + help_suffix)
    run.add_argument("--model", required=True)
    run.add_argument("--panel", required=True, choices=("quick", "full"))
    run.add_argument("--out", required=True)
    run.add_argument("--run-id", required=True)
    run.add_argument("--attempt", type=int, default=1, choices=(1, 2, 3))
    run.add_argument("--resume", action="store_true")
    run.add_argument("--detach", action="store_true")
    run.add_argument("--smoke", action="store_true")
    run.add_argument("--task")

    topup = sub.add_parser("topup", help="run registered efficiency-only reps;" + help_suffix)
    topup.add_argument("--model", required=True)
    topup.add_argument("--panel", required=True, choices=("quick", "full"))
    topup.add_argument("--out", required=True)
    topup.add_argument("--run-id", required=True)
    topup.add_argument("--leg", required=True, choices=("E1", "E2"))
    topup.add_argument("--n", type=int, required=True)
    topup.set_defaults(attempt=1)
    return ap


def main() -> int:
    ap = parser()
    args = ap.parse_args()
    try:
        validate_apparatus(read_object(PARAMS_PATH))
        if args.self_test:
            return self_test()
        if args.derive_panel:
            panel = write_derived_panel()
            print(json.dumps(panel, sort_keys=True))
            return 0
        if args.command == "run":
            return command_run(args)
        if args.command == "topup":
            return command_topup(args)
        ap.error("choose --self-test, --derive-panel, run, or topup")
    except WindowInterrupted as exc:
        print(str(exc), file=sys.stderr)
        return 143
    except Refusal as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 3
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
