#!/usr/bin/env python3
"""Blind artifact-only judging for the iter-0064 ceiling harness."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import runpy
import shlex
import shutil
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
CEILING_ROOT = HERE.parent
RESULTS_ROOT = CEILING_ROOT / "results"
CORPUS_ROOT = CEILING_ROOT / "corpus"
EXTERNAL_ROOT = Path(
    os.environ.get("CEILING_EXTERNAL_ROOT", Path.home() / "devlyn-ceiling-external")
)
REAL_HOME = Path(os.environ.get("CEILING_REAL_HOME", str(Path.home())))
CLAUDE_ISOLATION = runpy.run_path(str(HERE / "claude-isolation.py"))
launch_claude = CLAUDE_ISOLATION["launch_claude"]
IsolationError = CLAUDE_ISOLATION["IsolationError"]
AXES = [
    "design_coherence",
    "robustness",
    "spec_long_horizon_consistency",
    "maintainability_api_ergonomics",
]
PACKETS = {"P1", "P2", "P3"}
MAX_JUDGE_ATTEMPTS = 2
RAW_TAIL_CHARS = 1000


def extract_json_object(text: str) -> Any | None:
    candidates: list[Any] = []
    start: int | None = None
    depth = 0
    in_string = False
    escaped = False
    for end, char in enumerate(text):
        if start is None:
            if char == "{":
                start = end
                depth = 1
            continue
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                try:
                    candidates.append(json.loads(text[start : end + 1]))
                except json.JSONDecodeError:
                    pass
                start = None
    return candidates[-1] if candidates else None


def raw_diagnostic(raw: str) -> str:
    return f"raw_length={len(raw)} tail={raw[-RAW_TAIL_CHARS:]!r}"


def retry_prompt(prompt: str, error: str | None) -> str:
    if (error or "").startswith("parse_error: incomplete_json"):
        instruction = "Your previous output was truncated; emit ONLY the JSON, complete."
    else:
        instruction = "Your previous output failed the required JSON shape; emit ONLY corrected JSON."
    return f"{prompt}\n\nRETRY: {instruction} Return one single complete JSON object and nothing else."


def terminate_process_group(pid: int) -> None:
    try:
        os.killpg(pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            return


def probe_version(command: list[str], args: list[str]) -> str | None:
    try:
        result = subprocess.run(
            [*command, *args],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    text = (result.stdout or result.stderr or "").strip()
    return text.splitlines()[0] if text else None


def validate_response(parsed: Any) -> str | None:
    if not isinstance(parsed, dict):
        return "top-level response must be an object"
    axes = parsed.get("axes")
    if not isinstance(axes, dict):
        return "missing axes object"
    for axis in AXES:
        row = axes.get(axis)
        if not isinstance(row, dict):
            return f"missing axis {axis}"
        tiers = row.get("tiers")
        if not isinstance(tiers, list) or not tiers:
            return f"{axis}: tiers must be a non-empty list"
        seen: list[str] = []
        for tier in tiers:
            if not isinstance(tier, list) or not tier:
                return f"{axis}: each tier must be a non-empty list"
            for label in tier:
                if label not in PACKETS:
                    return f"{axis}: unknown packet label {label!r}"
                seen.append(label)
        if sorted(seen) != ["P1", "P2", "P3"]:
            return f"{axis}: tiers must contain P1/P2/P3 exactly once"
        strict_pairs = {
            (winner, loser)
            for i, tier in enumerate(tiers)
            for later in tiers[i + 1 :]
            for winner in tier
            for loser in later
        }
        deltas = row.get("strict_win_deltas")
        if not isinstance(deltas, list):
            return f"{axis}: strict_win_deltas must be a list"
        covered: set[tuple[str, str]] = set()
        for delta in deltas:
            if not isinstance(delta, dict):
                return f"{axis}: delta entries must be objects"
            winner = delta.get("winner")
            loser = delta.get("loser")
            text = delta.get("delta")
            if (winner, loser) not in strict_pairs:
                return f"{axis}: delta {winner!r}>{loser!r} is not a strict tier win"
            if not isinstance(text, str) or len(text.strip().split()) < 3:
                return f"{axis}: delta for {winner}>{loser} must be a concrete sentence"
            covered.add((winner, loser))
        missing = strict_pairs - covered
        if missing:
            return f"{axis}: missing deltas for {sorted(missing)}"
    return None


def call_sonnet(
    prompt: str,
    scratch_dir: Path,
    task_dir: Path,
    attempt: int,
) -> tuple[Any | None, str | None, dict[str, Any]]:
    opaque_run = hashlib.sha256(task_dir.parent.name.encode()).hexdigest()[:12]
    opaque_call = hashlib.sha256(f"{task_dir.name}:{attempt}".encode()).hexdigest()[:12]
    home = EXTERNAL_ROOT / "judge-homes" / opaque_run / opaque_call
    shutil.rmtree(home, ignore_errors=True)
    metadata_path = task_dir / f"judge-sonnet-attempt{attempt}-isolation.json"
    try:
        result = launch_claude(
            mode="judge",
            home=home,
            codex_home=home / "codex",
            workdir=scratch_dir,
            prompt=prompt,
            debug_file=None,
            metadata_out=metadata_path,
            user_memory_file=REAL_HOME / ".claude/CLAUDE.md",
            timeout_seconds=900,
        )
    except subprocess.TimeoutExpired:
        return None, "transport_error: timeout", {"stdout": "", "stderr": ""}
    except (IsolationError, OSError) as exc:
        return None, f"isolation_error: {exc}", {
            "stdout": "",
            "stderr": str(exc),
            "isolation_path": str(metadata_path),
        }
    meta: dict[str, Any] = {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "isolation_path": str(metadata_path),
    }
    if result.returncode != 0:
        return None, f"transport_error: exit={result.returncode} stderr={result.stderr[:300]!r}", meta
    raw = result.stdout
    wrapper = extract_json_object(result.stdout)
    if isinstance(wrapper, dict) and isinstance(wrapper.get("result"), str):
        raw = wrapper["result"]
        meta["modelUsage"] = wrapper.get("modelUsage") or wrapper.get("usage")
        meta["wrapper"] = wrapper
        usage = meta["modelUsage"]
        if not isinstance(usage, dict) or not usage or not all(
            "sonnet" in str(model).casefold() for model in usage
        ):
            return None, f"isolation_error: runtime model is not sonnet: {sorted(usage) if isinstance(usage, dict) else usage!r}", meta
    parsed = extract_json_object(raw)
    if parsed is None:
        return None, f"parse_error: incomplete_json; {raw_diagnostic(raw)}", meta
    validation_error = validate_response(parsed)
    if validation_error:
        return None, f"parse_error: {validation_error}; {raw_diagnostic(raw)}", meta
    return parsed, None, meta


def call_codex(
    prompt: str,
    scratch_dir: Path,
    codex_command: list[str],
    stdout_path: Path,
    stderr_path: Path,
) -> tuple[Any | None, str | None, dict[str, Any]]:
    cmd = [
        *codex_command,
        "exec",
        "--ignore-user-config",
        "--ignore-rules",
        "--ephemeral",
        "--skip-git-repo-check",
        "--disable",
        "codex_hooks",
        "--disable",
        "hooks",
        "-C",
        str(scratch_dir),
        "-s",
        "read-only",
        # Benchmark judge codex seat = gpt-5.6-terra, never the user's global
        # sol default. --ignore-user-config above means config.toml is not
        # read, so -m is the only lever (same as the B/C arms). sol is
        # team-only; the measured benchmark uses sonnet + terra (user
        # directive 2026-07-10).
        "-m",
        "gpt-5.6-terra",
        "-c",
        "model_reasoning_effort=xhigh",
        prompt,
    ]
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
                returncode = proc.wait(timeout=900)
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
                return None, "transport_error: timeout", {"stdout_path": str(stdout_path), "stderr_path": str(stderr_path)}
    except FileNotFoundError:
        return None, f"transport_error: command_not_found {codex_command[0]}", {"stdout_path": str(stdout_path), "stderr_path": str(stderr_path)}
    stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace") if stdout_path.exists() else ""
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace") if stderr_path.exists() else ""
    meta = {"stdout_path": str(stdout_path), "stderr_path": str(stderr_path), "stdout": stdout_text, "stderr": stderr_text}
    if returncode != 0:
        return None, f"transport_error: exit={returncode} stderr={stderr_text[:300]!r}", meta
    parsed = extract_json_object(stdout_text)
    if parsed is None:
        return None, f"parse_error: incomplete_json; {raw_diagnostic(stdout_text)}", meta
    validation_error = validate_response(parsed)
    if validation_error:
        return None, f"parse_error: {validation_error}; {raw_diagnostic(stdout_text)}", meta
    return parsed, None, meta


def call_with_retry(judge: str, prompt: str, task_dir: Path, codex_command: list[str]) -> tuple[Any | None, str | None, list[dict[str, Any]], dict[str, Any]]:
    scratch_dir = EXTERNAL_ROOT / "judge-scratch" / judge
    scratch_dir.mkdir(parents=True, exist_ok=True)
    attempts: list[dict[str, Any]] = []
    last_meta: dict[str, Any] = {}
    parsed: Any | None = None
    err: str | None = None
    for attempt in range(1, MAX_JUDGE_ATTEMPTS + 1):
        attempt_prompt = prompt if attempt == 1 else retry_prompt(prompt, err)
        if judge == "sonnet":
            parsed, err, last_meta = call_sonnet(attempt_prompt, scratch_dir, task_dir, attempt)
            if (err or "").startswith("isolation_error:"):
                raise SystemExit(f"sonnet judge isolation failed: {err}")
        elif judge == "codex":
            parsed, err, last_meta = call_codex(
                attempt_prompt,
                scratch_dir,
                codex_command,
                task_dir / f"judge-codex-attempt{attempt}.stdout.txt",
                task_dir / f"judge-codex-attempt{attempt}.stderr.txt",
            )
        else:
            raise ValueError(f"unknown judge: {judge}")
        attempts.append({"attempt": attempt, "error": err})
        retryable = (err or "").startswith("parse_error:") or err == "transport_error: timeout"
        if parsed is not None or not retryable:
            break
    return parsed, err, attempts, last_meta


def parse_select(values: list[str]) -> dict[str, dict[str, str]]:
    selected: dict[str, dict[str, str]] = {}
    for value in values:
        if "=" not in value:
            raise SystemExit(f"--select must be task=arm-attempt, got {value!r}")
        task, arm_attempt = value.split("=", 1)
        if not re.match(r"^[ABC][0-9]+$", arm_attempt):
            raise SystemExit(f"invalid arm attempt in --select {value!r}")
        selected.setdefault(task, {})[arm_attempt[0]] = arm_attempt
    for task, arms in selected.items():
        arms.setdefault("A", "A1")
        missing = {"A", "B", "C"} - set(arms)
        if missing:
            raise SystemExit(f"{task}: missing selected arms {sorted(missing)}")
    return selected


def build_packets(run_id: str, task: str, arms: dict[str, str]) -> tuple[list[dict[str, str]], dict[str, Any]]:
    task_text = (CORPUS_ROOT / task / "task.txt").read_text(encoding="utf-8").rstrip("\n")
    packets: list[dict[str, str]] = []
    for arm in ("A", "B", "C"):
        attempt = arms[arm]
        patch_path = RESULTS_ROOT / run_id / task / attempt / "patch.diff"
        if not patch_path.exists():
            raise SystemExit(f"missing patch for {task} {attempt}: {patch_path}")
        packets.append({"arm": arm, "attempt": attempt, "task_text": task_text, "patch": patch_path.read_text(encoding="utf-8", errors="replace")})
    seed = int(hashlib.sha256(task.encode("utf-8")).hexdigest(), 16)
    shuffled = packets[:]
    random.Random(seed).shuffle(shuffled)
    labeled = []
    mapping: dict[str, Any] = {"seed": seed, "packets": {}, "arm_attempts": arms}
    for i, packet in enumerate(shuffled, start=1):
        label = f"P{i}"
        labeled.append({"label": label, **packet})
        mapping["packets"][label] = packet["attempt"]
    return labeled, mapping


def build_prompt(task_text: str, labeled_packets: list[dict[str, str]]) -> str:
    packet_blocks = []
    for packet in labeled_packets:
        packet_blocks.append(
            f"{packet['label']} patch.diff:\n```diff\n{packet['patch']}\n```"
        )
    return (
        "You are a blind ceiling-quality judge. You receive one task and three anonymized candidate patches. "
        "Do not infer or mention model, arm, attempt, harness, or author identity; judge only the task text and diffs.\n\n"
        f"Task text:\n{task_text}\n\n"
        + "\n\n".join(packet_blocks)
        + "\n\nRank P1/P2/P3 on exactly these axes: design_coherence, robustness, "
        "spec_long_horizon_consistency, maintainability_api_ergonomics.\n"
        "Emit exactly this JSON SHAPE. The packet labels and tier orderings below are ARBITRARY "
        "placeholders that illustrate the object shape only (a tie in one axis, distinct orders in "
        "the others) — do NOT copy this ordering; rank strictly from the three diffs you were given. "
        "Every axis needs its own `tiers` and a `strict_win_deltas` entry for each strict winner>loser "
        "pair those tiers create:\n"
        '{"axes":{"design_coherence":{"tiers":[["P1","P3"],["P2"]],"strict_win_deltas":[{"winner":"P1","loser":"P2","delta":"<one concrete sentence citing something visible in the diffs>"},{"winner":"P3","loser":"P2","delta":"<one concrete sentence citing something visible in the diffs>"}]},"robustness":{"tiers":[["P3"],["P1"],["P2"]],"strict_win_deltas":[{"winner":"P3","loser":"P1","delta":"<one concrete sentence citing something visible in the diffs>"},{"winner":"P3","loser":"P2","delta":"<one concrete sentence citing something visible in the diffs>"},{"winner":"P1","loser":"P2","delta":"<one concrete sentence citing something visible in the diffs>"}]},"spec_long_horizon_consistency":{"tiers":[["P2"],["P3"],["P1"]],"strict_win_deltas":[{"winner":"P2","loser":"P3","delta":"<one concrete sentence citing something visible in the diffs>"},{"winner":"P2","loser":"P1","delta":"<one concrete sentence citing something visible in the diffs>"},{"winner":"P3","loser":"P1","delta":"<one concrete sentence citing something visible in the diffs>"}]},"maintainability_api_ergonomics":{"tiers":[["P1"],["P2","P3"]],"strict_win_deltas":[{"winner":"P1","loser":"P2","delta":"<one concrete sentence citing something visible in the diffs>"},{"winner":"P1","loser":"P3","delta":"<one concrete sentence citing something visible in the diffs>"}]}}}\n'
        "Ties are allowed and expected wherever two packets are genuinely indistinguishable on an axis — put them in the same tier. "
        "For every strict winner-loser pair created by tiers, include exactly one concrete one-sentence delta citing something visible in the diffs. "
        "Output one single complete JSON object and nothing else -- no prose before or after, no markdown fences."
    )


def compare_packets(tiers: list[list[str]], a_packet: str, c_packet: str) -> str:
    positions = {label: i for i, tier in enumerate(tiers) for label in tier}
    if positions[a_packet] < positions[c_packet]:
        return "A_win"
    if positions[a_packet] > positions[c_packet]:
        return "C_win"
    return "tie"


def write_identity(run_root: Path, judge: str, run_id: str, codex_command: list[str], model_usage: Any | None = None) -> None:
    if judge == "sonnet":
        opaque_run = hashlib.sha256(run_id.encode()).hexdigest()[:12]
        home = EXTERNAL_ROOT / "judge-homes" / opaque_run / "identity"
        shutil.rmtree(home, ignore_errors=True)
        isolation_path = run_root / "judge-identities" / judge / "isolation.json"
        try:
            probe = launch_claude(
                mode="version",
                home=home,
                codex_home=home / "codex",
                workdir=EXTERNAL_ROOT,
                prompt=None,
                debug_file=None,
                metadata_out=isolation_path,
                user_memory_file=REAL_HOME / ".claude/CLAUDE.md",
                timeout_seconds=30,
            )
        except (IsolationError, OSError, subprocess.TimeoutExpired) as exc:
            raise SystemExit(f"sonnet identity isolation failed: {exc}") from exc
        cli_version = (probe.stdout or probe.stderr).strip().splitlines()[0]
        model = "sonnet"
    elif judge == "codex":
        cli_version = probe_version(codex_command, ["--version"])
        model = os.environ.get("CODEX_MODEL") or os.environ.get("OPENAI_MODEL")
    else:
        raise ValueError(judge)
    identity = {
        "cli_version": cli_version,
        "model_id_or_alias": model,
        "recorded_at_run_id": run_id,
    }
    if judge == "sonnet":
        identity["isolation"] = json.loads(isolation_path.read_text(encoding="utf-8"))
    if isinstance(model_usage, dict):
        identity["model_usage_keys"] = sorted(str(key) for key in model_usage)
    out_dir = run_root / "judge-identities" / judge
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "identity.json").write_text(json.dumps(identity, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--judges", default="sonnet,codex")
    parser.add_argument("--codex-command", default=os.environ.get("CEILING_CODEX_CMD", "codex"))
    parser.add_argument("--select", action="append", default=[], help="task=arm-attempt; pass B and C selections per task, A1 is implicit")
    args = parser.parse_args()

    judges = [judge for judge in args.judges.split(",") if judge]
    for judge in judges:
        if judge not in {"sonnet", "codex"}:
            parser.error(f"unsupported judge: {judge}")
    codex_command = shlex.split(args.codex_command)
    if not codex_command:
        parser.error("--codex-command must not be empty")
    selected = parse_select(args.select)
    if not selected:
        parser.error("at least one --select task=arm-attempt is required")

    run_root = RESULTS_ROOT / args.run_id
    EXTERNAL_ROOT.mkdir(parents=True, exist_ok=True)
    aggregate: dict[str, Any] = {"run_id": args.run_id, "tasks": {}}
    model_usage_by_judge: dict[str, Any] = {}
    for judge in judges:
        write_identity(run_root, judge, args.run_id, codex_command)

    for task in sorted(selected):
        task_dir = run_root / task
        task_dir.mkdir(parents=True, exist_ok=True)
        labeled_packets, mapping = build_packets(args.run_id, task, selected[task])
        (task_dir / "judge-mapping.json").write_text(json.dumps(mapping, indent=2) + "\n", encoding="utf-8")
        prompt = build_prompt(labeled_packets[0]["task_text"], labeled_packets)
        task_aggregate: dict[str, Any] = {
            "a_packet": next(label for label, attempt in mapping["packets"].items() if attempt == selected[task]["A"]),
            "c_packet": next(label for label, attempt in mapping["packets"].items() if attempt == selected[task]["C"]),
            "axes": {axis: {"per_judge": {}, "a_vs_c_counts": {"A_win": 0, "C_win": 0, "tie": 0}} for axis in AXES},
        }
        for judge in judges:
            parsed, err, attempts, meta = call_with_retry(judge, prompt, task_dir, codex_command)
            if judge == "sonnet" and isinstance(meta.get("modelUsage"), dict):
                model_usage_by_judge[judge] = meta["modelUsage"]
                write_identity(run_root, judge, args.run_id, codex_command, model_usage=meta["modelUsage"])
            raw = {
                "judge": judge,
                "task": task,
                "prompt": prompt,
                "attempts": attempts,
                "error": err,
                "parsed": parsed,
                "meta": {key: value for key, value in meta.items() if key not in {"wrapper"}},
            }
            (task_dir / f"judge-{judge}.json").write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
            if parsed is None or err is not None:
                raise SystemExit(f"{task} {judge} judge failed after retries: {err}")
            for axis in AXES:
                tiers = parsed["axes"][axis]["tiers"]
                outcome = compare_packets(tiers, task_aggregate["a_packet"], task_aggregate["c_packet"])
                task_aggregate["axes"][axis]["per_judge"][judge] = {
                    "tiers": tiers,
                    "a_vs_c": outcome,
                    "strict_win_deltas": parsed["axes"][axis]["strict_win_deltas"],
                }
                task_aggregate["axes"][axis]["a_vs_c_counts"][outcome] += 1
        aggregate["tasks"][task] = task_aggregate

    (run_root / "ceiling-judge-aggregate.json").write_text(json.dumps(aggregate, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"aggregate": str(run_root / "ceiling-judge-aggregate.json"), "tasks": sorted(selected)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
