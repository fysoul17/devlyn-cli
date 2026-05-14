"""Shared pair-evidence contract for benchmark audits."""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any


ALLOWED_PAIR_ARMS = {"l2_risk_probes", "l2_gated"}
CANONICAL_PAIR_TRIGGER_REASONS = {
    "mode.verify-only",
    "mode.pair-verify",
    "complexity.high",
    "complexity.large",
    "spec.complexity.high",
    "spec.complexity.large",
    "spec.solo_headroom_hypothesis",
    "risk.high",
    "risk_probes.enabled",
    "risk_probes.present",
    "coverage.failed",
    "mechanical.warning",
    "judge.warning",
}
HISTORICAL_PAIR_TRIGGER_REASON_ALIASES = {
    "risk_profile.high_risk",
    "risk_probes_enabled",
}
HISTORICAL_NORMALIZED_PAIR_TRIGGER_REASON_ALIASES = {
    "complexity.high.spec.frontmatter",
    "frontmatter.complexity.high",
    "high.complexity.spec",
    "high.risk.profile",
    "spec.frontmatter.complexity.high",
    "state.complexity.high",
}
# Benchmark readers accept historical aliases only for archived artifacts.
# Runtime /devlyn:resolve state must continue to emit canonical reasons.
KNOWN_PAIR_TRIGGER_REASONS = (
    CANONICAL_PAIR_TRIGGER_REASONS | HISTORICAL_PAIR_TRIGGER_REASON_ALIASES
)
OBSERVABLE_COMMAND_MARKERS = ("command", "observable", "expose")
BACKTICKED_TEXT_RE = re.compile(r"`[^`\n]+`")
RESERVED_BACKTICK_TERMS = {"solo-headroom hypothesis", "solo_claude", "miss"}
COMMAND_PREFIXES = {
    "bash",
    "bun",
    "cargo",
    "git",
    "go",
    "jest",
    "make",
    "node",
    "npm",
    "pnpm",
    "printf",
    "pytest",
    "python",
    "python3",
    "ruff",
    "sh",
    "uv",
    "vitest",
    "yarn",
}


def reject_json_constant(token: str) -> None:
    raise ValueError(f"invalid JSON numeric constant: {token}")


def loads_strict_json_object(text: str) -> dict[str, Any]:
    data = json.loads(text, parse_constant=reject_json_constant)
    if not isinstance(data, dict):
        raise ValueError("top-level JSON value must be an object")
    return data


def normalized_pair_trigger_reason(reason: str) -> str:
    return re.sub(r"[^a-z0-9]+", ".", reason.lower()).strip(".")


def is_known_pair_trigger_reason(reason: str) -> bool:
    normalized = normalized_pair_trigger_reason(reason)
    return (
        reason in CANONICAL_PAIR_TRIGGER_REASONS
        or reason in HISTORICAL_PAIR_TRIGGER_REASON_ALIASES
        or normalized in HISTORICAL_NORMALIZED_PAIR_TRIGGER_REASON_ALIASES
    )


def is_canonical_pair_trigger_reason(reason: str) -> bool:
    return reason in CANONICAL_PAIR_TRIGGER_REASONS


def is_historical_pair_trigger_reason(reason: str) -> bool:
    normalized = normalized_pair_trigger_reason(reason)
    return (
        reason in HISTORICAL_PAIR_TRIGGER_REASON_ALIASES
        or normalized in HISTORICAL_NORMALIZED_PAIR_TRIGGER_REASON_ALIASES
    )


def has_known_pair_trigger_reason(reasons: list[str]) -> bool:
    return any(is_known_pair_trigger_reason(reason) for reason in reasons)


def all_known_pair_trigger_reasons(reasons: list[str]) -> bool:
    return all(is_known_pair_trigger_reason(reason) for reason in reasons)


def has_canonical_pair_trigger_reason(reasons: list[str]) -> bool:
    return any(is_canonical_pair_trigger_reason(reason) for reason in reasons)


def has_historical_pair_trigger_reason(reasons: list[str]) -> bool:
    return any(is_historical_pair_trigger_reason(reason) for reason in reasons)


def is_command_like_backtick(value: str) -> bool:
    stripped = value.strip()
    lower = stripped.lower()
    if not stripped or lower in RESERVED_BACKTICK_TERMS:
        return False
    first = lower.split(maxsplit=1)[0]
    return (
        first in COMMAND_PREFIXES
        or any(marker in stripped for marker in ("/", "$", "=", "|", "&&", ";"))
        or stripped.endswith((".js", ".py", ".sh"))
    )


def actionable_observable_commands(text: str) -> list[str]:
    commands: list[str] = []
    for line in text.splitlines():
        lower = line.lower()
        if "miss" not in lower or not any(marker in lower for marker in OBSERVABLE_COMMAND_MARKERS):
            continue
        for match in BACKTICKED_TEXT_RE.finditer(line):
            value = match.group(0).strip("`")
            if is_command_like_backtick(value):
                commands.append(value)
    return commands


def has_actionable_solo_headroom_hypothesis_text(text: str) -> bool:
    lower = text.lower()
    return (
        "solo-headroom hypothesis" in lower
        and "solo_claude" in lower
        and "miss" in lower
        and bool(actionable_observable_commands(text))
    )


def path_has_actionable_solo_headroom_hypothesis(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return has_actionable_solo_headroom_hypothesis_text(text)


def normalize_pair_evidence_row(
    *,
    fixture: str,
    run_id: str,
    pair_arm: object,
    row: dict[str, Any],
) -> dict[str, Any] | None:
    bare_score = row.get("bare_score")
    solo_score = row.get("solo_score")
    pair_score = row.get("pair_score")
    pair_margin = row.get("pair_margin")
    pair_mode = row.get("pair_mode")
    pair_trigger_eligible = row.get("pair_trigger_eligible")
    pair_trigger_reasons = row.get("pair_trigger_reasons")
    wall_ratio = row.get("pair_solo_wall_ratio")
    if not fixture or not run_id:
        return None
    if not isinstance(pair_arm, str) or pair_arm not in ALLOWED_PAIR_ARMS:
        return None
    if not all(is_score(value) for value in [bare_score, solo_score, pair_score]):
        return None
    if not is_strict_int(pair_margin):
        return None
    if pair_margin != pair_score - solo_score:
        return None
    if pair_mode is not True:
        return None
    if pair_trigger_eligible is not True:
        return None
    if not (
        isinstance(pair_trigger_reasons, list)
        and pair_trigger_reasons
        and all(isinstance(reason, str) for reason in pair_trigger_reasons)
        and all_known_pair_trigger_reasons(pair_trigger_reasons)
        and has_canonical_pair_trigger_reason(pair_trigger_reasons)
    ):
        return None
    if not is_strict_number(wall_ratio):
        return None
    normalized = {
        "run_id": run_id,
        "pair_arm": pair_arm,
        "bare_score": bare_score,
        "solo_score": solo_score,
        "pair_score": pair_score,
        "pair_margin": pair_margin,
        "pair_mode": pair_mode,
        "pair_trigger_eligible": pair_trigger_eligible,
        "pair_trigger_reasons": pair_trigger_reasons,
        "pair_trigger_has_canonical_reason": True,
        "pair_trigger_has_hypothesis_reason": (
            "spec.solo_headroom_hypothesis" in pair_trigger_reasons
        ),
        "pair_solo_wall_ratio": wall_ratio,
    }
    return normalized


def best_pair_evidence(evidence: list[object]) -> dict[str, Any] | None:
    candidates = [
        normalized
        for item in evidence
        if isinstance(item, dict)
        if isinstance(item.get("run_id"), str)
        for normalized in [
            normalize_pair_evidence_row(
                fixture="_",
                run_id=item["run_id"],
                pair_arm=item.get("pair_arm"),
                row=item,
            )
        ]
        if normalized is not None
    ]
    if not candidates:
        return None

    def key(item: dict[str, Any]) -> tuple[int, int, str]:
        margin = item.get("pair_margin")
        pair_score = item.get("pair_score")
        return (
            margin if isinstance(margin, int) else -10_000,
            pair_score if isinstance(pair_score, int) else -10_000,
            str(item.get("run_id") or ""),
        )

    return max(candidates, key=key)


def is_strict_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def is_score(value: object) -> bool:
    return is_strict_int(value) and 0 <= value <= 100


def is_strict_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value > 0
    )
