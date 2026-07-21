#!/usr/bin/env python3
"""Deterministic PHASE-0 bootstrap for /devlyn:resolve."""
from __future__ import annotations

import datetime
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import secrets
import stat
import subprocess
import sys
import tempfile


VALUE_FLAGS = {
    "--max-rounds", "--engine", "--spec", "--verify-only", "--goal-file", "--bypass",
}
BOOL_FLAGS = {"--pair-verify", "--no-pair", "--risk-probes", "--no-risk-probes", "--perf"}
SINGLE_VALUE_FLAGS = VALUE_FLAGS - {"--bypass"}
VALID_BYPASSES = {"build-gate", "cleanup"}
PHASE_NAMES = (
    "plan", "probe_derive", "implement", "surface_close",
    "build_gate", "cleanup", "verify", "final_report",
)
RISK_KEYWORDS = {
    "auth/authz": r"\b(?:auth|authz|authentication|authorization)\b",
    "permissions": r"\bpermissions?\b",
    "security": r"\bsecurity\b",
    "token/session": r"\b(?:tokens?|sessions?)\b",
    "payment/money/billing/invoice/pricing/tax/ledger": (
        r"\b(?:payments?|money|billing|invoices?|pricing|tax(?:es)?|ledgers?)\b"
    ),
    "persistence/data mutation/deletion/migration": (
        r"\b(?:persistence|data mutation|delet(?:e|es|ed|ing|ion)|migrations?|database write)\b"
    ),
    "idempotency/replay/duplicate": r"\b(?:idempoten\w*|replay|duplicates?)\b",
    "API/webhook/raw-body/signature": r"\b(?:api|webhooks?|raw[- ]body|signatures?)\b",
    "allocation/scheduling/inventory/rollback/transaction": (
        r"\b(?:allocation|scheduling|inventory|rollback|transactions?)\b"
    ),
    "error-priority/output-shape": r"\b(?:error[- ]priority|output[- ]shape)\b",
}
PAIR_EVIDENCE_RE = re.compile(
    r"benchmark evidence|pair[- ]evidence|risk[- ]probe measurement|"
    r"solo\s*[<]?[ ]*pair|solo[- ]headroom",
    re.IGNORECASE,
)
UNMEASURED_PAIR_RE = re.compile(
    r"\b(?:add|create|promote|run)\b.{0,80}\b(?:benchmark|shadow fixture|golden fixture|risk[- ]probe|pair[- ]evidence)\b",
    re.IGNORECASE | re.DOTALL,
)
PATH_RE = re.compile(
    r"(?<![\w.-])(?:[\w.-]+/)+[\w.*:-]+|"
    r"(?<![\w.-])[\w.-]+\.(?:py|js|jsx|ts|tsx|rs|go|java|sh|md|json|ya?ml)(?![\w.-])"
)
SYMBOL_RE = re.compile(
    r"\b(?:[a-z]+(?:[A-Z][A-Za-z0-9]*)+|[A-Z][a-z0-9]+(?:[A-Z][A-Za-z0-9]*)+|"
    r"[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+)\b|`[A-Za-z_][A-Za-z0-9_.:-]*`"
)
VERBS = ("fix", "add", "refactor", "debug", "review", "rewrite", "migrate")
COMMAND_PREFIXES = {
    "bash", "bun", "cargo", "git", "go", "jest", "make", "node", "npm", "pnpm",
    "printf", "pytest", "python", "python3", "ruff", "sh", "uv", "vitest", "yarn",
}
SOLO_CEILING_CONTROL_RE = re.compile(
    r"\bS[2-6]\b|S2-S6|solo-saturated|rejected controls?|solo ceiling", re.IGNORECASE,
)
SOLO_CEILING_DIFFERENCE_RE = re.compile(
    r"\bdiffer(?:s|ent|ence)?\b|\bunlike\b|\bbecause\b|\bpreserve\b|\bheadroom\b",
    re.IGNORECASE,
)


class BootstrapBlocked(Exception):
    def __init__(self, reason: str, detail: str):
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


def block(reason: str, detail: str) -> None:
    raise BootstrapBlocked(reason, detail)


def reject_json_constant(token: str) -> None:
    raise ValueError(f"invalid JSON numeric constant: {token}")


def strict_json(text: str):
    return json.loads(text, parse_constant=reject_json_constant)


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def atomic_write(path: pathlib.Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".tmp.")
    try:
        with open(fd, "wb") as handle:
            handle.write(raw)
        pathlib.Path(name).replace(path)
    except BaseException:
        pathlib.Path(name).unlink(missing_ok=True)
        raise


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def parse_flags(argv: list[str]) -> dict:
    values: dict[str, str | list[str]] = {"--bypass": []}
    switches: set[str] = set()
    positional: list[str] = []
    seen_single: set[str] = set()
    i = 0
    positional_only = False
    while i < len(argv):
        token = argv[i]
        if positional_only:
            positional.append(token)
            i += 1
            continue
        if token == "--":
            positional_only = True
            i += 1
            continue
        if token in BOOL_FLAGS:
            switches.add(token)
            i += 1
            continue
        if token in VALUE_FLAGS:
            if token in SINGLE_VALUE_FLAGS and token in seen_single:
                block("BLOCKED:invalid-flags", f"{token} may be passed only once")
            if i + 1 >= len(argv) or argv[i + 1].startswith("--"):
                block("BLOCKED:invalid-flags", f"{token} requires a value")
            value = argv[i + 1]
            if token == "--bypass":
                assert isinstance(values[token], list)
                values[token].append(value)
            else:
                values[token] = value
                seen_single.add(token)
            i += 2
            continue
        if token.startswith("-"):
            block("BLOCKED:invalid-flags", f"unknown flag: {token}")
        positional.append(token)
        i += 1

    if "--pair-verify" in switches and "--no-pair" in switches:
        block("BLOCKED:invalid-flags", "--pair-verify and --no-pair are mutually exclusive")
    if "--goal-file" in values and any(flag in values for flag in ("--spec", "--verify-only")):
        block("BLOCKED:invalid-flags", "--goal-file is mutually exclusive with --spec/--verify-only")
    if "--goal-file" in values and positional:
        block("BLOCKED:invalid-flags", "--goal-file is mutually exclusive with an inline goal")
    if "--verify-only" in values and "--spec" not in values:
        block("BLOCKED:invalid-flags", "--verify-only requires --spec")
    if "--spec" in values and positional:
        block("BLOCKED:invalid-flags", "--spec is mutually exclusive with an inline goal")

    max_rounds_raw = values.get("--max-rounds", "4")
    try:
        max_rounds = int(str(max_rounds_raw))
    except ValueError:
        block("BLOCKED:invalid-flags", "--max-rounds must be a positive integer")
    if max_rounds < 1:
        block("BLOCKED:invalid-flags", "--max-rounds must be a positive integer")

    bypasses: list[str] = []
    for group in values["--bypass"]:
        for phase in group.split(","):
            if phase not in VALID_BYPASSES:
                block("BLOCKED:invalid-flags", f"invalid --bypass phase: {phase or '<empty>'}")
            if phase not in bypasses:
                bypasses.append(phase)

    mode = "verify-only" if "--verify-only" in values else "spec" if "--spec" in values else "free-form"
    return {
        "mode": mode,
        "max_rounds": max_rounds,
        "engine": values.get("--engine"),
        "spec": values.get("--spec"),
        "verify_ref": values.get("--verify-only"),
        "goal_file": values.get("--goal-file"),
        "inline_goal": " ".join(positional),
        "pair_verify": "--pair-verify" in switches,
        "no_pair": "--no-pair" in switches,
        "risk_probes": "--risk-probes" in switches,
        "no_risk_probes": "--no-risk-probes" in switches,
        "perf": "--perf" in switches,
        "bypasses": bypasses,
    }


def validate_shared_dir(shared_dir: pathlib.Path) -> None:
    for required in (shared_dir / "adapters", shared_dir / "spec-verify-check.py"):
        if not required.exists():
            block("BLOCKED:shared-dir-unresolved", str(required))


def adapter_role(adapter: pathlib.Path, role: str) -> bool:
    try:
        text = adapter.read_text(encoding="utf-8")
    except OSError as exc:
        block("BLOCKED:invalid-engine-config", f"cannot read adapter {adapter}: {exc}")
    section = re.search(r"(?ms)^## Role eligibility\s*$\n(.*?)(?=^## |\Z)", text)
    if section is None:
        return True
    match = re.search(rf"(?m)^{re.escape(role)}: (yes|no)\s*$", section.group(1))
    if match is None:
        block("BLOCKED:invalid-engine-config", f"adapter {adapter.name} has malformed {role} eligibility")
    return match.group(1) == "yes"


def adapter_for(shared_dir: pathlib.Path, engine: str, role: str) -> pathlib.Path:
    if re.fullmatch(r"[A-Za-z0-9._-]+", engine) is None:
        block("BLOCKED:invalid-engine-config", f"invalid engine name: {engine!r}")
    adapter = shared_dir / "adapters" / f"{engine}.md"
    if not adapter.is_file():
        block("BLOCKED:invalid-engine-config", f"{role} engine {engine!r} has no adapter: {adapter}")
    if not adapter_role(adapter, role):
        block("BLOCKED:invalid-engine-config", f"engine {engine!r} is ineligible for role {role}")
    return adapter


def default_availability(engine: str, adapter: pathlib.Path, cwd: pathlib.Path) -> bool:
    text = adapter.read_text(encoding="utf-8")
    declared = re.search(r"\*\*Availability probe\*\*:\s*`([^`]+)`", text)
    command = declared.group(1) if declared else f"command -v {engine} >/dev/null 2>&1"
    return subprocess.run(command, cwd=cwd, shell=True, executable="/bin/sh").returncode == 0


def load_engine_config(devlyn: pathlib.Path, shared_dir: pathlib.Path) -> dict:
    path = devlyn / "engines.json"
    if not path.exists():
        return {}
    try:
        config = strict_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        block("BLOCKED:invalid-engine-config", f"{path}: {exc}")
    if not isinstance(config, dict):
        block("BLOCKED:invalid-engine-config", f"{path}: top-level must be an object")
    executor = config.get("executor")
    priorities = config.get("pair_judge_priority")
    if executor is not None and (not isinstance(executor, str) or not executor):
        block("BLOCKED:invalid-engine-config", "executor must be a non-empty string")
    if priorities is not None and (
        not isinstance(priorities, list)
        or any(not isinstance(item, str) or not item for item in priorities)
    ):
        block("BLOCKED:invalid-engine-config", "pair_judge_priority must be a string array")
    if executor is not None:
        adapter_for(shared_dir, executor, "executor")
    for engine in priorities or []:
        adapter_for(shared_dir, engine, "pair_judge")
    return config


def resolve_engines(
    parsed: dict,
    cwd: pathlib.Path,
    devlyn: pathlib.Path,
    shared_dir: pathlib.Path,
    default_engine: str,
    probe=None,
) -> dict:
    config = load_engine_config(devlyn, shared_dir)
    if parsed["engine"] is not None:
        engine, source = parsed["engine"], "flag"
    elif config.get("executor") is not None:
        engine, source = config["executor"], "engines.json"
    else:
        engine, source = default_engine, "default"
    adapter = adapter_for(shared_dir, engine, "executor")
    available = probe(engine, adapter) if probe else default_availability(engine, adapter, cwd)
    if not available:
        block(
            f"BLOCKED:{engine}-unavailable",
            f"install/configure {engine} CLI; complete auth/login; verify `{engine} --version`; rerun",
        )

    priorities = config.get("pair_judge_priority")
    if priorities is None:
        if engine == "claude":
            candidates = ["codex"]
        elif engine == "codex":
            candidates = ["claude"]
        else:
            candidates = [name for name in ("claude", "codex") if name != engine]
    else:
        candidates = [name for name in priorities if name != engine]
    pair_engine = None
    unavailable: list[str] = []
    for candidate in candidates:
        pair_adapter = adapter_for(shared_dir, candidate, "pair_judge")
        pair_available = probe(candidate, pair_adapter) if probe else default_availability(candidate, pair_adapter, cwd)
        if pair_available:
            pair_engine = candidate
            break
        unavailable.append(candidate)

    explicit_pair = parsed["pair_verify"] or parsed["risk_probes"]
    if explicit_pair and pair_engine is None:
        if not candidates:
            block("BLOCKED:invalid-engine-config", "pair route has no configured OTHER engine")
        missing = unavailable[0]
        block(
            f"BLOCKED:{missing}-unavailable",
            f"install/configure {missing} CLI; complete auth/login; verify `{missing} --version`; rerun",
        )
    return {
        "engine": engine,
        "engine_source": source,
        "pair_engine": pair_engine,
        "pair_unavailable": unavailable[0] if unavailable else None,
    }


def safe_goal_file(cwd: pathlib.Path, raw_path: str) -> bytes:
    supplied = pathlib.Path(raw_path)
    if supplied.is_absolute() or ".." in supplied.parts:
        block("BLOCKED:goal-file-invalid-path", raw_path)
    target = cwd / supplied
    try:
        resolved = target.resolve(strict=True)
        resolved.relative_to(cwd.resolve())
    except (OSError, ValueError):
        if target.exists():
            block("BLOCKED:goal-file-invalid-path", raw_path)
        block("BLOCKED:goal-file-unreadable", raw_path)
    try:
        metadata = resolved.stat()
    except OSError:
        block("BLOCKED:goal-file-unreadable", raw_path)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_mode & 0o444 == 0:
        block("BLOCKED:goal-file-unreadable", raw_path)
    try:
        raw = resolved.read_bytes()
        text = raw.decode("utf-8")
    except (OSError, UnicodeError):
        block("BLOCKED:goal-file-unreadable", raw_path)
    if not text.strip():
        block("BLOCKED:goal-file-empty", raw_path)
    return raw


def has_actionable_solo_headroom(text: str) -> bool:
    lower = text.lower()
    if not all(marker in lower for marker in ("solo-headroom hypothesis", "solo_claude", "miss")):
        return False
    for line in text.splitlines():
        line_lower = line.lower()
        if "miss" not in line_lower or not any(marker in line_lower for marker in ("command", "observable", "expose")):
            continue
        for wrapped in re.findall(r"`[^`\n]+`", line):
            value = wrapped.strip("`").strip()
            first = value.lower().split(maxsplit=1)[0] if value else ""
            if (
                value.lower() not in {"solo-headroom hypothesis", "solo_claude", "miss"}
                and (
                    first in COMMAND_PREFIXES
                    or any(marker in value for marker in ("/", "$", "=", "|", "&&", ";"))
                    or value.endswith((".js", ".py", ".sh"))
                )
            ):
                return True
    return False


def has_solo_ceiling_avoidance(text: str) -> bool:
    lower = text.lower()
    return (
        "solo ceiling avoidance" in lower
        and "solo_claude" in lower
        and SOLO_CEILING_CONTROL_RE.search(text) is not None
        and SOLO_CEILING_DIFFERENCE_RE.search(text) is not None
    )


def classify_complexity(goal: str, cwd: pathlib.Path) -> tuple[str, dict, str | None]:
    words = re.findall(r"\S+", goal)
    scope = sorted(set(PATH_RE.findall(goal)) | set(SYMBOL_RE.findall(goal)))
    lower = goal.lower()
    verb_matches = [
        (match.start(), item)
        for item in VERBS
        if (match := re.search(rf"\b{item}\b", lower)) is not None
    ]
    verb = min(verb_matches)[1] if verb_matches else "other"
    failing_test = bool(re.search(r"failing test|test fail|stack trace|traceback|assertionerror", lower))
    pair_intent = bool(PAIR_EVIDENCE_RE.search(goal))
    actionable_headroom = has_actionable_solo_headroom(goal)
    unmeasured_pair = bool(UNMEASURED_PAIR_RE.search(goal))
    ceiling_avoidance = has_solo_ceiling_avoidance(goal)
    tracked = subprocess.run(
        ["git", "ls-files", "-z"], cwd=cwd, capture_output=True, check=False,
    )
    if tracked.returncode != 0:
        block("BLOCKED:invalid-flags", "cannot classify outside a git worktree")
    file_count = len([item for item in tracked.stdout.split(b"\0") if item])
    multi_subsystem = len(scope) > 3 or bool(re.search(r"multi[- ]subsystem|across (?:the )?(?:repo|project)", lower))
    design_heavy_feature = bool(
        re.search(r"\bnew feature\b", lower)
        and re.search(r"\b(?:architecture|design decision|new api|new workflow)\b", lower)
    )
    signals = {
        "goal_length": len(words),
        "file_scope_signals": len(scope),
        "file_scope_matches": scope,
        "verb_class": verb,
        "codebase_size": "<50" if file_count < 50 else "<500" if file_count < 500 else ">=500",
        "has_failing_test": failing_test,
        "pair_evidence_intent": pair_intent,
        "has_actionable_solo_headroom": actionable_headroom,
        "unmeasured_pair_candidate_intent": unmeasured_pair,
        "has_solo_ceiling_avoidance": ceiling_avoidance,
    }
    large = (
        len(scope) > 10 or len(scope) == 0
        or (verb in {"rewrite", "migrate"} and multi_subsystem)
        or design_heavy_feature
        or (pair_intent and not actionable_headroom)
        or (unmeasured_pair and not ceiling_avoidance)
    )
    if large:
        if pair_intent and not actionable_headroom:
            return "large", signals, "BLOCKED:solo-headroom-hypothesis-required"
        if unmeasured_pair and not ceiling_avoidance:
            return "large", signals, "BLOCKED:solo-ceiling-avoidance-required"
        if len(scope) == 0:
            return "large", signals, "BLOCKED:large-needs-ideation"
        return "large", signals, None
    medium = (
        len(words) > 30 or 4 <= len(scope) <= 10
        or (verb in {"refactor", "debug", "review"} and not multi_subsystem)
        or (not failing_test and bool(re.search(r"\b(?:verify|test|check|acceptance)\b", lower)))
    )
    if medium:
        return "medium", signals, None
    trivial = (
        len(words) <= 30 and 1 <= len(scope) <= 3 and verb in {"fix", "add"}
        and (failing_test or len(scope) == 1)
    )
    return ("trivial" if trivial else "medium"), signals, None


def classify_risk(text: str, parsed: dict, pair_engine: str | None, pair_unavailable: str | None) -> dict:
    reasons = [f"risk keyword: {name}" for name, pattern in RISK_KEYWORDS.items() if re.search(pattern, text, re.IGNORECASE)]
    high_risk = bool(reasons)
    explicit = parsed["risk_probes"]
    enabled = explicit or (high_risk and not parsed["no_risk_probes"] and pair_engine is not None)
    if high_risk and not explicit and not parsed["no_risk_probes"] and pair_engine is None:
        reasons.append(f"auto-risk-probes skipped: {pair_unavailable or 'other-engine'}-unavailable")
    return {
        "high_risk": high_risk,
        "reasons": reasons,
        "risk_probes_enabled": enabled,
        "risk_probes_explicit": explicit,
        "pair_default_enabled": not parsed["no_pair"],
    }


def run_checked(command: list[str], cwd: pathlib.Path, reason: str = "BLOCKED:invalid-flags") -> None:
    proc = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip() or "command failed"
        block(reason, detail)


def load_spec_helper(shared_dir: pathlib.Path):
    path = shared_dir / "spec-verify-check.py"
    spec = importlib.util.spec_from_file_location("devlyn_spec_verify_check", path)
    if spec is None or spec.loader is None:
        block("BLOCKED:shared-dir-unresolved", str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def init_spec_source(
    cwd: pathlib.Path, devlyn: pathlib.Path, shared_dir: pathlib.Path, raw_path: str,
) -> tuple[dict, str]:
    path = pathlib.Path(raw_path)
    path = path if path.is_absolute() else cwd / path
    if not path.is_file():
        block("BLOCKED:invalid-flags", f"spec not found: {raw_path}")
    try:
        raw = path.read_bytes()
        raw.decode("utf-8")
    except (OSError, UnicodeError) as exc:
        block("BLOCKED:invalid-flags", f"spec unreadable: {raw_path}: {exc}")
    helper = shared_dir / "spec-verify-check.py"
    expected = path.with_name("spec.expected.json")
    if expected.is_file():
        run_checked([sys.executable, str(helper), "--check-expected", str(expected)], cwd)
    else:
        run_checked([sys.executable, str(helper), "--check", str(path)], cwd)
    module = load_spec_helper(shared_dir)
    if expected.is_file():
        found, _staged, error, _expected_path, _data = module.stage_from_expected(path, devlyn)
        if not found or error:
            block("BLOCKED:invalid-flags", error or f"expected contract not found: {expected}")
    else:
        staged, error = module.stage_from_source(path, devlyn)
        if error:
            block("BLOCKED:invalid-flags", error)
        if not staged:
            (devlyn / "spec-verify.json").unlink(missing_ok=True)
    return ({
        "type": "spec",
        "spec_path": raw_path,
        "spec_sha256": sha256(raw),
        "criteria_path": None,
        "criteria_sha256": None,
    }, raw.decode("utf-8"))


def git_text(cwd: pathlib.Path, *args: str, allow_empty: bool = False) -> str:
    proc = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    text = proc.stdout.strip()
    if proc.returncode != 0 or (not allow_empty and not text):
        detail = (proc.stderr or proc.stdout).strip() or "git command failed"
        block("BLOCKED:invalid-flags", detail)
    return text


def capture_external_diff(cwd: pathlib.Path, devlyn: pathlib.Path, ref: str) -> None:
    supplied = pathlib.Path(ref)
    source = supplied if supplied.is_absolute() else cwd / supplied
    if source.is_file():
        raw = source.read_bytes()
    else:
        proc = subprocess.run(["git", "diff", "--binary", ref], cwd=cwd, capture_output=True)
        if proc.returncode != 0:
            block("BLOCKED:invalid-flags", os.fsdecode(proc.stderr or proc.stdout).strip())
        raw = proc.stdout
    atomic_write(devlyn / "external-diff.patch", raw)


def bootstrap(
    argv: list[str],
    cwd: pathlib.Path,
    shared_dir: pathlib.Path,
    *,
    default_engine: str = "claude",
    probe=None,
) -> dict:
    cwd = cwd.resolve()
    validate_shared_dir(shared_dir)
    parsed = parse_flags(argv)
    devlyn = cwd / ".devlyn"
    engines = resolve_engines(parsed, cwd, devlyn, shared_dir, default_engine, probe)

    complexity = None
    complexity_signals = None
    if parsed["mode"] == "free-form":
        raw_goal = (
            safe_goal_file(cwd, parsed["goal_file"])
            if parsed["goal_file"] is not None
            else parsed["inline_goal"].encode("utf-8")
        )
        goal_text = raw_goal.decode("utf-8")
        complexity, complexity_signals, halted = classify_complexity(goal_text, cwd)
        if halted:
            block(halted, f"deterministic complexity preclassification: {complexity}")
        atomic_write(devlyn / "goal.raw.txt", raw_goal)
        source = {
            "type": "generated",
            "spec_path": None,
            "spec_sha256": None,
            "goal_path": ".devlyn/goal.raw.txt",
            "goal_sha256": sha256(raw_goal),
            "criteria_path": ".devlyn/criteria.generated.md",
            "criteria_sha256": None,
        }
        classification_text = goal_text
    else:
        source, spec_text = init_spec_source(cwd, devlyn, shared_dir, parsed["spec"])
        classification_text = spec_text
        if parsed["mode"] == "verify-only":
            capture_external_diff(cwd, devlyn, parsed["verify_ref"])

    risk_profile = classify_risk(
        classification_text, parsed, engines["pair_engine"], engines["pair_unavailable"],
    )
    now = datetime.datetime.now(datetime.timezone.utc)
    started_at = now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"
    run_id = now.strftime("rs-%Y%m%dT%H%M%SZ-") + secrets.token_hex(6)
    state = {
        "version": "3.0",
        "run_id": run_id,
        "started_at": started_at,
        "engine": engines["engine"],
        "engine_source": engines["engine_source"],
        "mode": parsed["mode"],
        "pair_verify": parsed["pair_verify"],
        "complexity": complexity,
        "risk_profile": risk_profile,
        "risk_probes_digest": None,
        "base_ref": {
            "branch": git_text(cwd, "symbolic-ref", "--short", "-q", "HEAD", allow_empty=True) or "HEAD",
            "sha": git_text(cwd, "rev-parse", "HEAD"),
        },
        "rounds": {"max_rounds": parsed["max_rounds"], "global": 0},
        "bypasses": parsed["bypasses"],
        "implement_passed_sha": None,
        "source": source,
        "criteria": [],
        "phases": {name: None for name in PHASE_NAMES},
        "verify": {"coverage_failed": False, "pair_trigger": None},
    }
    atomic_write(devlyn / "pipeline.state.json", json_bytes(state))
    run_checked([sys.executable, str(shared_dir / "spec-verify-check.py"), "--write-untracked-baseline"], cwd)

    if parsed["no_pair"]:
        pair_status = "disabled"
    elif engines["pair_engine"] is None:
        pair_status = "solo:auto_pair_other_engine_unavailable"
    else:
        pair_status = "on"
    announce = (
        f"resolve starting — run {run_id} — engine {engines['engine']} — mode {parsed['mode']} "
        f"— complexity {complexity or 'na'} — pair {pair_status} — risk_probes "
        f"{'on' if risk_profile['risk_probes_enabled'] else 'off'}"
    )
    state_raw = (devlyn / "pipeline.state.json").read_bytes()
    return {
        "ok": True,
        "announce": announce,
        "run_id": run_id,
        "mode": parsed["mode"],
        "engine": engines["engine"],
        "engine_source": engines["engine_source"],
        "pair_engine": engines["pair_engine"],
        "pair_status": pair_status,
        "complexity": complexity,
        "complexity_signals": complexity_signals,
        "risk_profile": risk_profile,
        "source": source,
        "state_path": ".devlyn/pipeline.state.json",
        "state_sha256": sha256(state_raw),
        "untracked_baseline_path": ".devlyn/untracked.baseline",
        "perf": parsed["perf"],
        "judgment_retained": [
            "read goal/spec content",
            "synthesize free-form criteria",
            "override complexity/risk_profile with reasons",
        ],
    }


def self_test() -> int:
    script_shared = pathlib.Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        work = root / "repo"
        work.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=work, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=work, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=work, check=True)
        (work / "app.py").write_text("print('base')\n")
        subprocess.run(["git", "add", "app.py"], cwd=work, check=True)
        subprocess.run(["git", "commit", "-qm", "base"], cwd=work, check=True)
        always = lambda _engine, _adapter: True

        result = bootstrap(["fix", "app.py", "failing", "test"], work, script_shared, probe=always)
        state_path = work / ".devlyn" / "pipeline.state.json"
        state = strict_json(state_path.read_text())
        expected = {
            "version": "3.0",
            "run_id": state["run_id"],
            "started_at": state["started_at"],
            "engine": "claude",
            "engine_source": "default",
            "mode": "free-form",
            "pair_verify": False,
            "complexity": "trivial",
            "risk_profile": {
                "high_risk": False,
                "reasons": [],
                "risk_probes_enabled": False,
                "risk_probes_explicit": False,
                "pair_default_enabled": True,
            },
            "risk_probes_digest": None,
            "base_ref": {
                "branch": git_text(work, "symbolic-ref", "--short", "-q", "HEAD"),
                "sha": git_text(work, "rev-parse", "HEAD"),
            },
            "rounds": {"max_rounds": 4, "global": 0},
            "bypasses": [],
            "implement_passed_sha": None,
            "source": {
                "type": "generated",
                "spec_path": None,
                "spec_sha256": None,
                "goal_path": ".devlyn/goal.raw.txt",
                "goal_sha256": sha256(b"fix app.py failing test"),
                "criteria_path": ".devlyn/criteria.generated.md",
                "criteria_sha256": None,
            },
            "criteria": [],
            "phases": {name: None for name in PHASE_NAMES},
            "verify": {"coverage_failed": False, "pair_trigger": None},
        }
        schema = (script_shared.parent / "devlyn:resolve" / "references" / "state-schema.md").read_text()
        assert '"version": "3.0"' in schema and all(f'"{name}"' in schema for name in PHASE_NAMES)
        assert state_path.read_bytes() == json_bytes(expected)
        assert result["state_sha256"] == sha256(json_bytes(expected))
        assert (work / ".devlyn" / "goal.raw.txt").read_bytes() == b"fix app.py failing test"
        assert (work / ".devlyn" / "untracked.baseline").read_bytes() == b""
        print("PASS bootstrap self-test state-init byte contract: schema v3.0 exact")

        invalid_flag_cases = [
            ["--pair-verify", "--no-pair", "fix", "app.py"],
            ["--goal-file", "goal.txt", "--spec", "spec.md"],
            ["--goal-file", "goal.txt", "--verify-only", "patch", "--spec", "spec.md"],
            ["--goal-file", "goal.txt", "fix", "app.py"],
            ["--goal-file"],
            ["--goal-file", "a", "--goal-file", "b"],
            ["--verify-only", "patch"],
            ["--spec", "spec.md", "fix", "app.py"],
            ["--spec", "a", "--spec", "b"],
            ["--verify-only", "a", "--spec", "s", "--verify-only", "b"],
            ["--engine"],
            ["--engine", "claude", "--engine", "codex"],
            ["--max-rounds", "0", "fix", "app.py"],
            ["--max-rounds", "x", "fix", "app.py"],
            ["--max-rounds"],
            ["--bypass", "plan", "fix", "app.py"],
            ["--bypass"],
            ["--unknown", "fix", "app.py"],
        ]
        for case in invalid_flag_cases:
            try:
                parse_flags(case)
            except BootstrapBlocked as exc:
                assert exc.reason == "BLOCKED:invalid-flags", (case, exc.reason)
            else:
                raise AssertionError(f"invalid flag combination accepted: {case}")
        print(f"PASS bootstrap self-test BLOCKED:invalid-flags: {len(invalid_flag_cases)} combinations")
        cli_blocked = subprocess.run(
            [sys.executable, str(pathlib.Path(__file__).resolve()), "--pair-verify", "--no-pair"],
            cwd=work, capture_output=True, text=True,
        )
        assert cli_blocked.returncode == 1 and cli_blocked.stderr == ""
        assert strict_json(cli_blocked.stdout)["blocked"] == "BLOCKED:invalid-flags"
        print("PASS bootstrap self-test failure receipt: machine-only JSON")

        goal_file = work / "goal.txt"
        goal_file.write_bytes(b"fix app.py failing test\n")
        goal_result = bootstrap(["--goal-file", "goal.txt"], work, script_shared, probe=always)
        assert goal_result["source"]["goal_sha256"] == sha256(goal_file.read_bytes())
        goal_file.write_text(" \n")
        try:
            bootstrap(["--goal-file", "goal.txt"], work, script_shared, probe=always)
        except BootstrapBlocked as exc:
            assert exc.reason == "BLOCKED:goal-file-empty"
        else:
            raise AssertionError("empty goal file accepted")
        try:
            bootstrap(["--goal-file", "missing.txt"], work, script_shared, probe=always)
        except BootstrapBlocked as exc:
            assert exc.reason == "BLOCKED:goal-file-unreadable"
        else:
            raise AssertionError("missing goal file accepted")
        try:
            bootstrap(["--goal-file", "../outside.txt"], work, script_shared, probe=always)
        except BootstrapBlocked as exc:
            assert exc.reason == "BLOCKED:goal-file-invalid-path"
        else:
            raise AssertionError("escaping goal path accepted")
        print("PASS bootstrap self-test goal-file BLOCKED paths: empty/unreadable/invalid-path")

        halt_cases = [
            (["rewrite", "everything"], "BLOCKED:large-needs-ideation"),
            (["add", "pair-evidence", "benchmark", "for", "app.py"], "BLOCKED:solo-headroom-hypothesis-required"),
            (["create", "new", "shadow", "fixture", "for", "app.py"], "BLOCKED:solo-ceiling-avoidance-required"),
        ]
        for case, reason in halt_cases:
            try:
                bootstrap(case, work, script_shared, probe=always)
            except BootstrapBlocked as exc:
                assert exc.reason == reason, (case, exc.reason)
            else:
                raise AssertionError(f"classification halt not enforced: {reason}")
        strong_headroom = (
            "measure pair-evidence for app.py; solo-headroom hypothesis: solo_claude should miss. "
            "Observable command `python check.py` exposes the miss."
        )
        assert classify_complexity(strong_headroom, work)[2] is None
        weak_headroom = (
            "measure pair-evidence for app.py; solo-headroom hypothesis: solo_claude should miss. "
            "Observable `priority rollback` exposes the miss."
        )
        assert classify_complexity(weak_headroom, work)[2] == "BLOCKED:solo-headroom-hypothesis-required"
        print("PASS bootstrap self-test classifier BLOCKED paths: ideation/headroom/ceiling")

        engines_path = work / ".devlyn" / "engines.json"
        engines_path.write_text("{broken\n")
        try:
            bootstrap(["fix", "app.py"], work, script_shared, probe=always)
        except BootstrapBlocked as exc:
            assert exc.reason == "BLOCKED:invalid-engine-config"
        else:
            raise AssertionError("malformed engines.json accepted")
        engines_path.write_text('{"executor":"missing-adapter"}\n')
        try:
            bootstrap(["fix", "app.py"], work, script_shared, probe=always)
        except BootstrapBlocked as exc:
            assert exc.reason == "BLOCKED:invalid-engine-config"
        else:
            raise AssertionError("engine without an adapter accepted")
        engines_path.unlink()
        try:
            bootstrap(["--engine", "codex", "fix", "app.py"], work, script_shared, probe=lambda *_: False)
        except BootstrapBlocked as exc:
            assert exc.reason == "BLOCKED:codex-unavailable"
        else:
            raise AssertionError("unavailable explicit engine accepted")
        print("PASS bootstrap self-test engine BLOCKED paths: invalid-config/unavailable")

        try:
            bootstrap(["fix", "app.py"], work, root / "missing-shared", probe=always)
        except BootstrapBlocked as exc:
            assert exc.reason == "BLOCKED:shared-dir-unresolved"
        else:
            raise AssertionError("missing shared directory accepted")
        print("PASS bootstrap self-test BLOCKED:shared-dir-unresolved")

        spec_dir = work / "docs" / "specs" / "sample"
        spec_dir.mkdir(parents=True)
        spec_path = spec_dir / "spec.md"
        spec_path.write_text(
            "---\ncomplexity: medium\n---\n# Spec\n\n<!-- devlyn:verification -->\n"
            "## Verification\n\n```json\n{\"verification_commands\":[{\"cmd\":\"printf ok\",\"stdout_contains\":[\"ok\"]}]}\n```\n"
        )
        bootstrap(["--spec", str(spec_path.relative_to(work))], work, script_shared, probe=always)
        staged = strict_json((work / ".devlyn" / "spec-verify.json").read_text())
        assert staged["verification_commands"][0]["cmd"] == "printf ok"
        (spec_dir / "spec.expected.json").write_text(json.dumps({
            "verification_commands": [{"cmd": "printf expected", "stdout_contains": ["expected"]}],
        }) + "\n")
        bootstrap(["--spec", str(spec_path.relative_to(work))], work, script_shared, probe=always)
        staged = strict_json((work / ".devlyn" / "spec-verify.json").read_text())
        assert staged["verification_commands"][0]["cmd"] == "printf expected"
        print("PASS bootstrap self-test spec staging: --check and --check-expected")

    return 0


def main() -> int:
    if sys.argv[1:] == ["--self-test"]:
        return self_test()
    try:
        result = bootstrap(
            sys.argv[1:], pathlib.Path.cwd(), pathlib.Path(__file__).resolve().parent,
            default_engine=os.environ.get("DEVLYN_DEFAULT_ENGINE", "claude"),
        )
    except BootstrapBlocked as exc:
        sys.stdout.write(json.dumps({
            "ok": False,
            "blocked": exc.reason,
            "detail": exc.detail,
        }, sort_keys=True) + "\n")
        return 1
    sys.stdout.write(json.dumps(result, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
