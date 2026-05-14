#!/usr/bin/env python3
"""Merge VERIFY findings and derive a deterministic verdict.

VERIFY judges are model-written, but routing on finding severity must be
mechanical. This script reads the known VERIFY JSONL finding files, writes a
merged JSONL artifact, computes source-level and overall verdicts, and can
write the merged verdict back to `.devlyn/pipeline.state.json`.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import tempfile
from typing import Any


SOURCE_FILES = (
    ("mechanical", "verify-mechanical.findings.jsonl"),
    ("judge", "verify.findings.jsonl"),
    ("pair_judge", "verify.pair.findings.jsonl"),
    ("pair_judge", "verify.pair-judge.findings.jsonl"),
)

VERDICT_RANK = {
    "PASS": 0,
    "PASS_WITH_ISSUES": 1,
    "FAIL": 2,
    "NEEDS_WORK": 2,
    "BLOCKED": 3,
}
RANK_VERDICT = {0: "PASS", 1: "PASS_WITH_ISSUES", 2: "NEEDS_WORK", 3: "BLOCKED"}
ALLOWED_PAIR_SKIP_REASONS = {"user_no_pair", "mechanical_blocker", "primary_judge_blocker"}
KNOWN_PAIR_TRIGGER_REASONS = {
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


def loads_strict_json(text: str) -> Any:
    return json.loads(text, parse_constant=reject_json_constant)


def rank(verdict: str | None) -> int:
    return VERDICT_RANK.get(verdict or "PASS", 0)


def worse(a: str | None, b: str | None) -> str:
    return RANK_VERDICT[max(rank(a), rank(b))]


def is_known_pair_trigger_reason(reason: str) -> bool:
    return reason in KNOWN_PAIR_TRIGGER_REASONS


def has_known_pair_trigger_reason(reasons: list[str]) -> bool:
    return any(is_known_pair_trigger_reason(reason) for reason in reasons)


def all_known_pair_trigger_reasons(reasons: list[str]) -> bool:
    return all(is_known_pair_trigger_reason(reason) for reason in reasons)


def finding_rank(finding: dict[str, Any]) -> int:
    severity = str(finding.get("severity") or "").upper()
    if severity in {"CRITICAL", "HIGH"}:
        return 2
    if severity == "MEDIUM" and finding.get("verdict_binding") is True:
        return 2
    if severity in {"LOW", "MEDIUM"}:
        return 1
    return 0


def read_findings(devlyn: pathlib.Path) -> tuple[list[dict[str, Any]], dict[str, str]]:
    findings: list[dict[str, Any]] = []
    source_verdicts = {source: "PASS" for source, _ in SOURCE_FILES}
    for source, name in SOURCE_FILES:
        path = devlyn / name
        if not path.is_file():
            continue
        with path.open(encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, 1):
                raw = line.strip()
                if not raw:
                    continue
                try:
                    item = loads_strict_json(raw)
                except ValueError as exc:
                    blocked = {
                        "id": f"verify-merge-invalid-json-{name}-{line_no}",
                        "rule_id": "verify.findings.invalid-json",
                        "severity": "CRITICAL",
                        "confidence": "high",
                        "file": name,
                        "line": line_no,
                        "message": f"Invalid JSONL finding: {exc}",
                        "criterion_ref": "verify-merge",
                        "source": source,
                    }
                    findings.append(blocked)
                    source_verdicts[source] = "BLOCKED"
                    continue
                if not isinstance(item, dict):
                    continue
                item = dict(item)
                item.setdefault("source", source)
                findings.append(item)
                source_verdicts[source] = worse(
                    source_verdicts[source], RANK_VERDICT[finding_rank(item)]
                )
    findings.extend(detect_pair_stdout_contract_violations(devlyn, source_verdicts))
    return findings, source_verdicts


def has_pair_findings(devlyn: pathlib.Path) -> bool:
    for name in ("verify.pair.findings.jsonl", "verify.pair-judge.findings.jsonl"):
        path = devlyn / name
        if path.is_file() and path.read_text(encoding="utf-8").strip():
            return True
    return False


def pair_trigger_status(devlyn: pathlib.Path) -> tuple[bool, dict[str, Any] | None]:
    state_path = devlyn / "pipeline.state.json"
    if not state_path.is_file():
        return False, None
    try:
        state = loads_strict_json(state_path.read_text(encoding="utf-8"))
    except ValueError:
        return False, {
            "id": "verify-pair-trigger-state-malformed",
            "message": "pipeline.state.json is malformed; cannot verify pair_trigger contract.",
            "file": "pipeline.state.json",
        }
    phases = state.get("phases") if isinstance(state, dict) else {}
    verify_phase = phases.get("verify") if isinstance(phases, dict) else None
    trigger = None
    if isinstance(verify_phase, dict):
        trigger = verify_phase.get("pair_trigger")
    if trigger is None and isinstance(state, dict):
        verify_state = state.get("verify")
        if isinstance(verify_state, dict):
            trigger = verify_state.get("pair_trigger")
    if trigger is None:
        return False, None
    if not isinstance(trigger, dict):
        return False, {
            "id": "verify-pair-trigger-malformed",
            "message": "pair_trigger must be an object.",
            "file": "pipeline.state.json",
        }
    eligible = trigger.get("eligible")
    if not isinstance(eligible, bool):
        return False, {
            "id": "verify-pair-trigger-eligible-malformed",
            "message": "pair_trigger.eligible must be a boolean.",
            "file": "pipeline.state.json",
        }
    reasons = trigger.get("reasons")
    if not isinstance(reasons, list) or not all(isinstance(item, str) for item in reasons):
        return False, {
            "id": "verify-pair-trigger-reasons-malformed",
            "message": "pair_trigger.reasons must be a list of strings.",
            "file": "pipeline.state.json",
        }
    skipped_reason = trigger.get("skipped_reason")
    if skipped_reason is not None and not isinstance(skipped_reason, str):
        return False, {
            "id": "verify-pair-trigger-skipped-reason-malformed",
            "message": "pair_trigger.skipped_reason must be a string or null.",
            "file": "pipeline.state.json",
        }
    if eligible is True and not reasons:
        return False, {
            "id": "verify-pair-trigger-reasons-empty",
            "message": "pair_trigger.eligible cannot be true with an empty reasons list.",
            "file": "pipeline.state.json",
        }
    if eligible is True and not has_known_pair_trigger_reason(reasons):
        return False, {
            "id": "verify-pair-trigger-reasons-unknown",
            "message": "pair_trigger.reasons must include a known pair-trigger reason.",
            "file": "pipeline.state.json",
        }
    if eligible is True and not all_known_pair_trigger_reasons(reasons):
        return False, {
            "id": "verify-pair-trigger-reasons-unknown",
            "message": "pair_trigger.reasons must only include known pair-trigger reasons.",
            "file": "pipeline.state.json",
        }
    if eligible is True and skipped_reason is not None:
        return False, {
            "id": "verify-pair-trigger-skip-contradiction",
            "message": "pair_trigger.eligible cannot be true while skipped_reason is set.",
            "file": "pipeline.state.json",
        }
    if eligible is False and reasons:
        return False, {
            "id": "verify-pair-trigger-ineligible-reasons",
            "message": "pair_trigger.reasons must be empty when pair_trigger.eligible is false.",
            "file": "pipeline.state.json",
        }
    return eligible is True and len(reasons) > 0, None


def pair_trigger_required(devlyn: pathlib.Path) -> bool:
    required, _malformed = pair_trigger_status(devlyn)
    return required


def pair_trigger_present(devlyn: pathlib.Path) -> bool:
    state_path = devlyn / "pipeline.state.json"
    if not state_path.is_file():
        return False
    try:
        state = loads_strict_json(state_path.read_text(encoding="utf-8"))
    except ValueError:
        return False
    phases = state.get("phases") if isinstance(state, dict) else {}
    verify_phase = phases.get("verify") if isinstance(phases, dict) else None
    if isinstance(verify_phase, dict) and "pair_trigger" in verify_phase:
        return True
    if isinstance(state, dict):
        verify_state = state.get("verify")
        if isinstance(verify_state, dict) and "pair_trigger" in verify_state:
            return True
    return False


def pair_flag_contract_violation(devlyn: pathlib.Path) -> dict[str, Any] | None:
    state_path = devlyn / "pipeline.state.json"
    if not state_path.is_file():
        return None
    try:
        state = loads_strict_json(state_path.read_text(encoding="utf-8"))
    except ValueError:
        return None
    if not isinstance(state, dict) or state.get("pair_verify") is not True:
        return None
    risk_profile = state.get("risk_profile")
    if isinstance(risk_profile, dict) and risk_profile.get("pair_default_enabled") is False:
        return {
            "id": "verify-pair-trigger-conflicting-pair-flags",
            "message": "--pair-verify and --no-pair are mutually exclusive.",
            "file": "pipeline.state.json",
        }
    return None


def risk_profile_contract_violation(devlyn: pathlib.Path) -> dict[str, Any] | None:
    state_path = devlyn / "pipeline.state.json"
    if not state_path.is_file():
        return None
    try:
        state = loads_strict_json(state_path.read_text(encoding="utf-8"))
    except ValueError:
        return None
    if not isinstance(state, dict) or "risk_profile" not in state:
        return None
    risk_profile = state.get("risk_profile")
    if not isinstance(risk_profile, dict):
        return {
            "id": "verify-risk-profile-malformed",
            "message": "risk_profile must be an object.",
            "file": "pipeline.state.json",
        }
    for field in ("high_risk", "risk_probes_enabled", "pair_default_enabled"):
        if field in risk_profile and not isinstance(risk_profile.get(field), bool):
            return {
                "id": "verify-risk-profile-malformed",
                "message": f"risk_profile.{field} must be a boolean.",
                "file": "pipeline.state.json",
            }
    reasons = risk_profile.get("reasons")
    if "reasons" in risk_profile and (
        not isinstance(reasons, list) or not all(isinstance(item, str) for item in reasons)
    ):
        return {
            "id": "verify-risk-profile-malformed",
            "message": "risk_profile.reasons must be a list of strings.",
            "file": "pipeline.state.json",
        }
    return None


def source_spec_text(state: dict[str, Any]) -> str | None:
    source = state.get("source") if isinstance(state.get("source"), dict) else {}
    for key in ("spec_path", "criteria_path"):
        raw_path = source.get(key)
        if not isinstance(raw_path, str) or not raw_path:
            continue
        path = pathlib.Path(raw_path)
        if not path.is_absolute():
            path = pathlib.Path.cwd() / path
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            continue
    return None


def spec_frontmatter_complexity(state: dict[str, Any]) -> str | None:
    text = source_spec_text(state)
    if text is None:
        return None
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    for line in text[3:end].splitlines():
        match = re.match(r"\s*complexity\s*:\s*[\"']?([A-Za-z_-]+)", line)
        if match:
            return match.group(1).lower()
    return None


def spec_has_solo_headroom_hypothesis(state: dict[str, Any]) -> bool:
    text = source_spec_text(state)
    if text is None:
        return False
    lower = text.lower()
    return (
        "solo-headroom hypothesis" in lower
        and "solo_claude" in lower
        and "miss" in lower
        and has_backticked_observable_command(text)
    )


def has_backticked_observable_command(text: str) -> bool:
    for line in text.splitlines():
        lower = line.lower()
        if "miss" not in lower or not any(marker in lower for marker in OBSERVABLE_COMMAND_MARKERS):
            continue
        if any(is_command_like_backtick(match.group(0).strip("`")) for match in BACKTICKED_TEXT_RE.finditer(line)):
            return True
    return False


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


def state_pair_trigger_reasons(
    devlyn: pathlib.Path,
    source_verdicts: dict[str, str],
) -> list[str]:
    state_path = devlyn / "pipeline.state.json"
    if not state_path.is_file():
        return []
    try:
        state = loads_strict_json(state_path.read_text(encoding="utf-8"))
    except ValueError:
        return []
    if not isinstance(state, dict):
        return []
    phases = state.get("phases") if isinstance(state.get("phases"), dict) else {}
    verify_phase = phases.get("verify") if isinstance(phases, dict) else {}
    verify_state = state.get("verify") if isinstance(state.get("verify"), dict) else {}
    risk_profile = state.get("risk_profile") if isinstance(state.get("risk_profile"), dict) else {}
    reasons: list[str] = []
    if state.get("mode") == "verify-only":
        reasons.append("mode.verify-only")
    if state.get("pair_verify") is True:
        reasons.append("mode.pair-verify")
    if state.get("complexity") in {"high", "large"}:
        reasons.append(f"complexity.{state.get('complexity')}")
    spec_complexity = spec_frontmatter_complexity(state)
    if spec_complexity in {"high", "large"}:
        reasons.append(f"spec.complexity.{spec_complexity}")
    if spec_has_solo_headroom_hypothesis(state):
        reasons.append("spec.solo_headroom_hypothesis")
    if risk_profile.get("high_risk") is True:
        reasons.append("risk.high")
    if risk_profile.get("risk_probes_enabled") is True:
        reasons.append("risk_probes.enabled")
    if (devlyn / "risk-probes.jsonl").is_file():
        reasons.append("risk_probes.present")
    coverage_failed = False
    if isinstance(verify_state, dict) and verify_state.get("coverage_failed") is True:
        coverage_failed = True
    if isinstance(verify_phase, dict) and verify_phase.get("coverage_failed") is True:
        coverage_failed = True
    if coverage_failed:
        reasons.append("coverage.failed")
    if rank(source_verdicts.get("mechanical")) == 1:
        reasons.append("mechanical.warning")
    if rank(source_verdicts.get("judge")) == 1:
        reasons.append("judge.warning")
    return reasons


def pair_trigger_missing_contract_violation(
    devlyn: pathlib.Path,
    source_verdicts: dict[str, str],
) -> dict[str, Any] | None:
    if rank(source_verdicts.get("mechanical")) >= 2 or rank(source_verdicts.get("judge")) >= 2:
        return None
    reasons = state_pair_trigger_reasons(devlyn, source_verdicts)
    if not reasons:
        return None
    return {
        "id": "verify-pair-trigger-required-missing",
        "message": (
            "pair_trigger is missing even though VERIFY state requires a pair decision: "
            + ", ".join(reasons)
        ),
        "file": "pipeline.state.json",
    }


def pair_trigger_skip_contract_violation(
    devlyn: pathlib.Path,
    source_verdicts: dict[str, str],
) -> dict[str, Any] | None:
    state_path = devlyn / "pipeline.state.json"
    if not state_path.is_file():
        return None
    try:
        state = loads_strict_json(state_path.read_text(encoding="utf-8"))
    except ValueError:
        return None
    phases = state.get("phases") if isinstance(state, dict) else {}
    verify_phase = phases.get("verify") if isinstance(phases, dict) else None
    trigger = None
    if isinstance(verify_phase, dict):
        trigger = verify_phase.get("pair_trigger")
    if trigger is None and isinstance(state, dict):
        verify_state = state.get("verify")
        if isinstance(verify_state, dict):
            trigger = verify_state.get("pair_trigger")
    if not isinstance(trigger, dict):
        return None
    skipped_reason = trigger.get("skipped_reason")
    if trigger.get("eligible") is False and skipped_reason is None:
        natural_reasons = state_pair_trigger_reasons(devlyn, source_verdicts)
        if natural_reasons:
            return {
                "id": "verify-pair-trigger-ineligible-unjustified",
                "message": (
                    "pair_trigger is ineligible without a skip reason even though "
                    "VERIFY state requires a pair decision: "
                    + ", ".join(natural_reasons)
                ),
                "file": "pipeline.state.json",
            }
    if skipped_reason is None:
        return None
    if skipped_reason not in ALLOWED_PAIR_SKIP_REASONS:
        return {
            "id": "verify-pair-trigger-skipped-reason-unsupported",
            "message": (
                "pair_trigger.skipped_reason must be user_no_pair, "
                "mechanical_blocker, primary_judge_blocker, or null."
            ),
            "file": "pipeline.state.json",
        }
    if skipped_reason == "user_no_pair":
        risk_profile = state.get("risk_profile") if isinstance(state, dict) else {}
        if not isinstance(risk_profile, dict) or risk_profile.get("pair_default_enabled") is not False:
            return {
                "id": "verify-pair-trigger-user-no-pair-unsupported",
                "message": (
                    "pair_trigger skipped_reason user_no_pair requires "
                    "risk_profile.pair_default_enabled false from an explicit --no-pair opt-out."
                ),
                "file": "pipeline.state.json",
            }
    if skipped_reason == "mechanical_blocker" and rank(source_verdicts.get("mechanical")) < 2:
        return {
            "id": "verify-pair-trigger-mechanical-blocker-unsupported",
            "message": (
                "pair_trigger skipped_reason mechanical_blocker requires a "
                "verdict-binding MECHANICAL finding."
            ),
            "file": "pipeline.state.json",
        }
    if skipped_reason == "primary_judge_blocker" and rank(source_verdicts.get("judge")) < 2:
        return {
            "id": "verify-pair-trigger-primary-judge-blocker-unsupported",
            "message": (
                "pair_trigger skipped_reason primary_judge_blocker requires a "
                "verdict-binding primary JUDGE finding."
            ),
            "file": "pipeline.state.json",
        }
    return None


def pair_trigger_reason_completeness_violation(
    devlyn: pathlib.Path,
    source_verdicts: dict[str, str],
) -> dict[str, Any] | None:
    if rank(source_verdicts.get("mechanical")) >= 2 or rank(source_verdicts.get("judge")) >= 2:
        return None
    state_path = devlyn / "pipeline.state.json"
    if not state_path.is_file():
        return None
    try:
        state = loads_strict_json(state_path.read_text(encoding="utf-8"))
    except ValueError:
        return None
    phases = state.get("phases") if isinstance(state, dict) else {}
    verify_phase = phases.get("verify") if isinstance(phases, dict) else None
    trigger = None
    if isinstance(verify_phase, dict):
        trigger = verify_phase.get("pair_trigger")
    if trigger is None and isinstance(state, dict):
        verify_state = state.get("verify")
        if isinstance(verify_state, dict):
            trigger = verify_state.get("pair_trigger")
    if not isinstance(trigger, dict) or trigger.get("eligible") is not True:
        return None
    reasons = trigger.get("reasons")
    if not isinstance(reasons, list) or not all(isinstance(item, str) for item in reasons):
        return None
    missing = [
        reason
        for reason in state_pair_trigger_reasons(devlyn, source_verdicts)
        if reason not in reasons
    ]
    if not missing:
        return None
    return {
        "id": "verify-pair-trigger-reasons-incomplete",
        "message": (
            "pair_trigger.reasons is missing applicable canonical reason(s): "
            + ", ".join(missing)
        ),
        "file": "pipeline.state.json",
    }


def pair_blocker(id_: str, message: str, file_: str | None = None) -> dict[str, Any]:
    return {
        "id": id_,
        "rule_id": "verify.pair.emission-contract",
        "severity": "CRITICAL",
        "confidence": "high",
        "file": file_,
        "line": 1 if file_ else None,
        "message": message,
        "criterion_ref": "verify.pair.findings",
        "source": "pair_judge",
    }


def detect_pair_stdout_contract_violations(
    devlyn: pathlib.Path,
    source_verdicts: dict[str, str],
) -> list[dict[str, Any]]:
    stdout_path = devlyn / "codex-judge.stdout"
    flag_violation = pair_flag_contract_violation(devlyn)
    if flag_violation is not None:
        source_verdicts["pair_judge"] = "BLOCKED"
        return [
            pair_blocker(
                flag_violation["id"],
                flag_violation["message"],
                flag_violation["file"],
            )
        ]
    required, malformed_trigger = pair_trigger_status(devlyn)
    if malformed_trigger is not None:
        source_verdicts["pair_judge"] = "BLOCKED"
        return [
            pair_blocker(
                malformed_trigger["id"],
                malformed_trigger["message"],
                malformed_trigger["file"],
            )
        ]
    risk_profile_violation = risk_profile_contract_violation(devlyn)
    if risk_profile_violation is not None:
        source_verdicts["pair_judge"] = "BLOCKED"
        return [
            pair_blocker(
                risk_profile_violation["id"],
                risk_profile_violation["message"],
                risk_profile_violation["file"],
            )
        ]
    if not required and not pair_trigger_present(devlyn):
        missing_violation = pair_trigger_missing_contract_violation(devlyn, source_verdicts)
        if missing_violation is not None:
            source_verdicts["pair_judge"] = "BLOCKED"
            return [
                pair_blocker(
                    missing_violation["id"],
                    missing_violation["message"],
                    missing_violation["file"],
                )
            ]
    skip_violation = pair_trigger_skip_contract_violation(devlyn, source_verdicts)
    if skip_violation is not None:
        source_verdicts["pair_judge"] = "BLOCKED"
        return [
            pair_blocker(
                skip_violation["id"],
                skip_violation["message"],
                skip_violation["file"],
            )
        ]
    reason_violation = pair_trigger_reason_completeness_violation(devlyn, source_verdicts)
    if reason_violation is not None:
        source_verdicts["pair_judge"] = "BLOCKED"
        return [
            pair_blocker(
                reason_violation["id"],
                reason_violation["message"],
                reason_violation["file"],
            )
        ]
    if has_pair_findings(devlyn):
        return []
    if not stdout_path.is_file():
        if required:
            source_verdicts["pair_judge"] = "BLOCKED"
            return [
                pair_blocker(
                    "verify-pair-required-output-missing",
                    "Pair-mode was required, but Codex pair-JUDGE produced no stdout or canonical findings file.",
                    "codex-judge.stdout",
                )
            ]
        return []
    raw_text = stdout_path.read_text(encoding="utf-8")
    if not raw_text.strip():
        source_verdicts["pair_judge"] = "BLOCKED"
        return [
            pair_blocker(
                "verify-pair-empty-output",
                "Codex pair-JUDGE stdout was empty; the bounded contract requires a JSONL finding or PASS line.",
                "codex-judge.stdout",
            )
        ]
    has_jsonl_finding = False
    has_nonpass_summary = False
    for line in raw_text.splitlines():
        raw = line.strip()
        if not raw:
            continue
        if raw.startswith("# SUMMARY "):
            try:
                summary = loads_strict_json(raw.removeprefix("# SUMMARY ").strip())
            except ValueError:
                continue
            if summary.get("verdict") in {"NEEDS_WORK", "FAIL", "BLOCKED"}:
                has_nonpass_summary = True
            continue
        if raw.startswith("#"):
            continue
        try:
            item = loads_strict_json(raw)
        except ValueError:
            continue
        if isinstance(item, dict) and str(item.get("severity") or "").upper() in {
            "CRITICAL",
            "HIGH",
            "MEDIUM",
            "LOW",
        }:
            has_jsonl_finding = True
    if not has_jsonl_finding and not has_nonpass_summary:
        return []
    source_verdicts["pair_judge"] = "BLOCKED"
    return [
        pair_blocker(
            "verify-pair-emission-contract-violated",
            (
                "Codex pair-JUDGE stdout contained findings or a non-PASS summary, "
                "but the canonical pair findings JSONL file was empty."
            ),
            "codex-judge.stdout",
        )
    ]


def write_outputs(
    devlyn: pathlib.Path,
    findings: list[dict[str, Any]],
    source_verdicts: dict[str, str],
) -> dict[str, Any]:
    merged_path = devlyn / "verify-merged.findings.jsonl"
    summary_path = devlyn / "verify-merge.summary.json"
    with merged_path.open("w", encoding="utf-8") as handle:
        for finding in findings:
            handle.write(json.dumps(finding, sort_keys=True, separators=(",", ":")) + "\n")
    verdict = "PASS"
    for source_verdict in source_verdicts.values():
        verdict = worse(verdict, source_verdict)
    summary = {
        "verdict": verdict,
        "source_verdicts": source_verdicts,
        "findings_count": len(findings),
        "findings_file": str(merged_path),
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def write_state(devlyn: pathlib.Path, summary: dict[str, Any]) -> None:
    state_path = devlyn / "pipeline.state.json"
    if not state_path.is_file():
        raise SystemExit(f"error: {state_path} not found")
    state = loads_strict_json(state_path.read_text(encoding="utf-8"))
    phases = state.setdefault("phases", {})
    verify = phases.get("verify")
    if not isinstance(verify, dict):
        verify = {}
        phases["verify"] = verify
    verify["verdict"] = summary["verdict"]
    sub = verify.setdefault("sub_verdicts", {})
    for source, source_verdict in summary["source_verdicts"].items():
        if source in {"mechanical", "judge", "pair_judge"}:
            sub[source] = source_verdict
    verify["merged"] = {
        "verdict": summary["verdict"],
        "findings_file": ".devlyn/verify-merged.findings.jsonl",
        "summary_file": ".devlyn/verify-merge.summary.json",
    }
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def self_test() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        devlyn = pathlib.Path(tmp)
        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "phases": {
                    "verify": {
                        "verdict": "PASS",
                        "sub_verdicts": {},
                        "pair_trigger": {
                            "eligible": True,
                            "reasons": ["risk.high", "judge.warning"],
                            "skipped_reason": None,
                        },
                    }
                }
            }),
            encoding="utf-8",
        )
        (devlyn / "verify.findings.jsonl").write_text(
            json.dumps({"id": "j1", "severity": "LOW"}) + "\n",
            encoding="utf-8",
        )
        (devlyn / "verify.pair.findings.jsonl").write_text(
            json.dumps({"id": "p1", "severity": "HIGH"}) + "\n",
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        write_state(devlyn, summary)
        state = loads_strict_json((devlyn / "pipeline.state.json").read_text(encoding="utf-8"))
        assert summary["verdict"] == "NEEDS_WORK", summary
        assert state["phases"]["verify"]["verdict"] == "NEEDS_WORK", state
        assert state["phases"]["verify"]["sub_verdicts"]["pair_judge"] == "NEEDS_WORK", state
        assert (devlyn / "verify-merged.findings.jsonl").read_text(encoding="utf-8")
        (devlyn / "verify.findings.jsonl").write_text(
            '{"id":"nan","severity":NaN}\n',
            encoding="utf-8",
        )
        (devlyn / "verify.pair.findings.jsonl").write_text("", encoding="utf-8")
        findings, source_verdicts = read_findings(devlyn)
        assert source_verdicts["judge"] == "BLOCKED", source_verdicts
        assert any(
            finding.get("id") == "verify-merge-invalid-json-verify.findings.jsonl-1"
            and "invalid JSON numeric constant: NaN" in finding.get("message", "")
            for finding in findings
        ), findings
        (devlyn / "pipeline.state.json").write_text(
            json.dumps({"phases": {"verify": {"verdict": "PASS", "sub_verdicts": {}}}}),
            encoding="utf-8",
        )
        (devlyn / "verify.findings.jsonl").write_text("", encoding="utf-8")
        (devlyn / "verify.pair.findings.jsonl").write_text("", encoding="utf-8")
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        write_state(devlyn, summary)
        state = loads_strict_json((devlyn / "pipeline.state.json").read_text(encoding="utf-8"))
        assert summary["verdict"] == "PASS", summary
        assert state["phases"]["verify"]["verdict"] == "PASS", state
        assert state["phases"]["verify"]["sub_verdicts"]["pair_judge"] == "PASS", state
        (devlyn / "codex-judge.stdout").write_text(
            json.dumps({"id": "cj1", "severity": "HIGH"}) + "\n"
            + '# SUMMARY {"verdict":"NEEDS_WORK"}\n',
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        write_state(devlyn, summary)
        state = loads_strict_json((devlyn / "pipeline.state.json").read_text(encoding="utf-8"))
        assert summary["verdict"] == "BLOCKED", summary
        assert state["phases"]["verify"]["sub_verdicts"]["pair_judge"] == "BLOCKED", state

        (devlyn / "codex-judge.stdout").unlink()
        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "phases": {
                    "verify": {
                        "verdict": "PASS",
                        "sub_verdicts": {},
                        "pair_trigger": {
                            "eligible": True,
                            "reasons": ["risk.high"],
                            "skipped_reason": None,
                        },
                    }
                }
            }),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        write_state(devlyn, summary)
        state = loads_strict_json((devlyn / "pipeline.state.json").read_text(encoding="utf-8"))
        assert summary["verdict"] == "BLOCKED", summary
        assert state["phases"]["verify"]["sub_verdicts"]["pair_judge"] == "BLOCKED", state
        assert any(
            finding.get("id") == "verify-pair-required-output-missing"
            for finding in findings
        ), findings

        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "mode": "spec",
                "risk_profile": {
                    "high_risk": True,
                    "risk_probes_enabled": True,
                    "pair_default_enabled": True,
                },
                "phases": {"verify": {"verdict": "PASS", "sub_verdicts": {}}},
            }),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert any(
            finding.get("id") == "verify-pair-trigger-required-missing"
            for finding in findings
        ), findings

        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "mode": "spec",
                "risk_profile": "enabled",
                "phases": {"verify": {"verdict": "PASS", "sub_verdicts": {}}},
            }),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert any(
            finding.get("id") == "verify-risk-profile-malformed"
            and "risk_profile must be an object" in str(finding.get("message"))
            for finding in findings
        ), findings

        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "mode": "spec",
                "risk_profile": {
                    "high_risk": True,
                    "risk_probes_enabled": "true",
                    "pair_default_enabled": True,
                },
                "phases": {"verify": {"verdict": "PASS", "sub_verdicts": {}}},
            }),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert any(
            finding.get("id") == "verify-risk-profile-malformed"
            and "risk_profile.risk_probes_enabled must be a boolean" in str(finding.get("message"))
            for finding in findings
        ), findings

        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "mode": "spec",
                "risk_profile": {
                    "high_risk": True,
                    "risk_probes_enabled": False,
                    "pair_default_enabled": True,
                    "reasons": ["explicit", 3],
                },
                "phases": {"verify": {"verdict": "PASS", "sub_verdicts": {}}},
            }),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert any(
            finding.get("id") == "verify-risk-profile-malformed"
            and "risk_profile.reasons must be a list of strings" in str(finding.get("message"))
            for finding in findings
        ), findings

        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "mode": "spec",
                "pair_verify": True,
                "phases": {"verify": {"verdict": "PASS", "sub_verdicts": {}}},
            }),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert any(
            finding.get("id") == "verify-pair-trigger-required-missing"
            and "mode.pair-verify" in finding.get("message", "")
            for finding in findings
        ), findings

        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "mode": "spec",
                "complexity": "large",
                "phases": {"verify": {"verdict": "PASS", "sub_verdicts": {}}},
            }),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert any(
            finding.get("id") == "verify-pair-trigger-required-missing"
            and "complexity.large" in str(finding.get("message"))
            for finding in findings
        ), findings

        spec_path = devlyn / "spec.md"
        spec_path.write_text(
            '---\nid: "spec-high"\ncomplexity: high\n---\n\n# Spec\n',
            encoding="utf-8",
        )
        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "mode": "spec",
                "source": {"spec_path": str(spec_path)},
                "phases": {"verify": {"verdict": "PASS", "sub_verdicts": {}}},
            }),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert any(
            finding.get("id") == "verify-pair-trigger-required-missing"
            and "spec.complexity.high" in str(finding.get("message"))
            for finding in findings
        ), findings

        spec_path.write_text(
            '---\nid: "spec-large"\ncomplexity: large\n---\n\n# Spec\n',
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert any(
            finding.get("id") == "verify-pair-trigger-required-missing"
            and "spec.complexity.large" in str(finding.get("message"))
            for finding in findings
        ), findings

        spec_path.write_text(
            "# Spec\n\n## Context\n\nsolo-headroom hypothesis: `SOLO_CLAUDE` should miss the priority rollback behavior; implementation token `rollback`.\n",
            encoding="utf-8",
        )
        assert spec_has_solo_headroom_hypothesis(
            {"source": {"spec_path": str(spec_path)}}
        ) is False
        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "mode": "spec",
                "source": {"spec_path": str(spec_path)},
                "phases": {"verify": {"verdict": "PASS", "sub_verdicts": {}}},
            }),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "PASS", summary
        assert not any(
            finding.get("id") == "verify-pair-trigger-required-missing"
            and "spec.solo_headroom_hypothesis" in str(finding.get("message"))
            for finding in findings
        ), findings

        spec_path.write_text(
            "# Spec\n\n## Context\n\nsolo-headroom hypothesis: solo_claude should miss the priority rollback behavior.\nObservable command: `node check.js` exposes behavior.\n",
            encoding="utf-8",
        )
        assert spec_has_solo_headroom_hypothesis(
            {"source": {"spec_path": str(spec_path)}}
        ) is False

        spec_path.write_text(
            "# Spec\n\n## Context\n\nsolo-headroom hypothesis: `SOLO_CLAUDE` should miss the priority rollback behavior; observable `SOLO_CLAUDE` exposes the miss.\n",
            encoding="utf-8",
        )
        assert spec_has_solo_headroom_hypothesis(
            {"source": {"spec_path": str(spec_path)}}
        ) is False

        spec_path.write_text(
            "# Spec\n\n## Context\n\nsolo-headroom hypothesis: solo_claude should miss behavior where observable `priority rollback` exposes the miss.\n",
            encoding="utf-8",
        )
        assert spec_has_solo_headroom_hypothesis(
            {"source": {"spec_path": str(spec_path)}}
        ) is False

        spec_path.write_text(
            "# Spec\n\n## Context\n\nsolo-headroom hypothesis: `SOLO_CLAUDE` should miss the priority rollback behavior exposed by `node check.js`.\n",
            encoding="utf-8",
        )
        assert spec_has_solo_headroom_hypothesis(
            {"source": {"spec_path": str(spec_path)}}
        ) is True
        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "mode": "spec",
                "source": {"spec_path": str(spec_path)},
                "phases": {"verify": {"verdict": "PASS", "sub_verdicts": {}}},
            }),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert any(
            finding.get("id") == "verify-pair-trigger-required-missing"
            and "spec.solo_headroom_hypothesis" in str(finding.get("message"))
            for finding in findings
        ), findings

        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "mode": "spec",
                "source": {"spec_path": str(spec_path)},
                "risk_profile": {
                    "high_risk": True,
                    "risk_probes_enabled": False,
                    "pair_default_enabled": True,
                },
                "phases": {
                    "verify": {
                        "verdict": "PASS",
                        "sub_verdicts": {},
                        "pair_trigger": {
                            "eligible": True,
                            "reasons": ["risk.high"],
                            "skipped_reason": None,
                        },
                    }
                },
            }),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert any(
            finding.get("id") == "verify-pair-trigger-reasons-incomplete"
            and "spec.solo_headroom_hypothesis" in str(finding.get("message"))
            for finding in findings
        ), findings

        criteria_path = devlyn / "criteria.generated.md"
        criteria_path.write_text(
            "# Criteria\n\nsolo-headroom hypothesis: `SOLO_CLAUDE` should miss the priority rollback behavior exposed by `node check.js`.\n",
            encoding="utf-8",
        )
        assert spec_has_solo_headroom_hypothesis(
            {"source": {"criteria_path": str(criteria_path)}}
        ) is True
        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "mode": "free-form",
                "source": {"criteria_path": str(criteria_path)},
                "phases": {"verify": {"verdict": "PASS", "sub_verdicts": {}}},
            }),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert any(
            finding.get("id") == "verify-pair-trigger-required-missing"
            and "spec.solo_headroom_hypothesis" in str(finding.get("message"))
            for finding in findings
        ), findings

        (devlyn / "verify-mechanical.findings.jsonl").write_text(
            json.dumps({"id": "m0", "severity": "HIGH"}) + "\n",
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "NEEDS_WORK", summary
        assert not any(
            finding.get("id") == "verify-pair-trigger-required-missing"
            for finding in findings
        ), findings
        (devlyn / "verify-mechanical.findings.jsonl").write_text("", encoding="utf-8")

        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "phases": {
                    "verify": {
                        "verdict": "PASS",
                        "sub_verdicts": {},
                        "pair_trigger": {
                            "eligible": "true",
                            "reasons": ["risk.high"],
                            "skipped_reason": None,
                        },
                    }
                }
            }),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert any(
            finding.get("id") == "verify-pair-trigger-eligible-malformed"
            for finding in findings
        ), findings

        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "phases": {
                    "verify": {
                        "verdict": "PASS",
                        "sub_verdicts": {},
                        "pair_trigger": {
                            "eligible": True,
                            "reasons": "risk.high",
                            "skipped_reason": None,
                        },
                    }
                }
            }),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert any(
            finding.get("id") == "verify-pair-trigger-reasons-malformed"
            for finding in findings
        ), findings

        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "phases": {
                    "verify": {
                        "verdict": "PASS",
                        "sub_verdicts": {},
                        "pair_trigger": {
                            "eligible": True,
                            "reasons": ["risk.high", "looks-hard"],
                            "skipped_reason": None,
                        },
                    }
                }
            }),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert any(
            finding.get("id") == "verify-pair-trigger-reasons-unknown"
            and "only include known" in finding.get("message", "")
            for finding in findings
        ), findings

        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "phases": {
                    "verify": {
                        "verdict": "PASS",
                        "sub_verdicts": {},
                        "pair_trigger": {
                            "eligible": True,
                            "reasons": ["risk high"],
                            "skipped_reason": None,
                        },
                    }
                }
            }),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert any(
            finding.get("id") == "verify-pair-trigger-reasons-unknown"
            and "include a known" in finding.get("message", "")
            for finding in findings
        ), findings

        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "phases": {
                    "verify": {
                        "verdict": "PASS",
                        "sub_verdicts": {},
                        "pair_trigger": {
                            "eligible": True,
                            "reasons": ["risk_profile.high_risk", "risk_probes_enabled"],
                            "skipped_reason": None,
                        },
                    }
                }
            }),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert any(
            finding.get("id") == "verify-pair-trigger-reasons-unknown"
            and "include a known" in finding.get("message", "")
            for finding in findings
        ), findings

        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "phases": {
                    "verify": {
                        "verdict": "PASS",
                        "sub_verdicts": {},
                        "pair_trigger": {
                            "eligible": True,
                            "reasons": ["risk.high", 3],
                            "skipped_reason": None,
                        },
                    }
                }
            }),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert any(
            finding.get("id") == "verify-pair-trigger-reasons-malformed"
            for finding in findings
        ), findings

        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "phases": {
                    "verify": {
                        "verdict": "PASS",
                        "sub_verdicts": {},
                        "pair_trigger": {
                            "eligible": True,
                            "reasons": [],
                            "skipped_reason": None,
                        },
                    }
                }
            }),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert any(
            finding.get("id") == "verify-pair-trigger-reasons-empty"
            for finding in findings
        ), findings

        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "phases": {
                    "verify": {
                        "verdict": "PASS",
                        "sub_verdicts": {},
                        "pair_trigger": {
                            "eligible": True,
                            "reasons": ["risk.high"],
                            "skipped_reason": "user_no_pair",
                        },
                    }
                }
            }),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert any(
            finding.get("id") == "verify-pair-trigger-skip-contradiction"
            for finding in findings
        ), findings

        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "phases": {
                    "verify": {
                        "verdict": "PASS",
                        "sub_verdicts": {},
                        "pair_trigger": {
                            "eligible": False,
                            "reasons": ["risk.high"],
                            "skipped_reason": "user_no_pair",
                        },
                    }
                }
            }),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert any(
            finding.get("id") == "verify-pair-trigger-ineligible-reasons"
            for finding in findings
        ), findings

        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "mode": "spec",
                "risk_profile": {
                    "high_risk": True,
                    "risk_probes_enabled": False,
                    "pair_default_enabled": True,
                },
                "phases": {
                    "verify": {
                        "verdict": "PASS",
                        "sub_verdicts": {},
                        "pair_trigger": {
                            "eligible": False,
                            "reasons": [],
                            "skipped_reason": None,
                        },
                    }
                },
            }),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert any(
            finding.get("id") == "verify-pair-trigger-ineligible-unjustified"
            and "risk.high" in str(finding.get("message"))
            for finding in findings
        ), findings

        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "mode": "spec",
                "risk_profile": {
                    "high_risk": True,
                    "risk_probes_enabled": True,
                    "pair_default_enabled": True,
                },
                "phases": {
                    "verify": {
                        "verdict": "PASS",
                        "sub_verdicts": {},
                        "pair_trigger": {
                            "eligible": False,
                            "reasons": [],
                            "skipped_reason": "user_no_pair",
                        },
                    }
                },
            }),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert any(
            finding.get("id") == "verify-pair-trigger-user-no-pair-unsupported"
            and "pair_default_enabled false" in str(finding.get("message"))
            for finding in findings
        ), findings

        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "pair_verify": True,
                "risk_profile": {
                    "high_risk": True,
                    "risk_probes_enabled": False,
                    "pair_default_enabled": False,
                },
                "phases": {
                    "verify": {
                        "verdict": "PASS",
                        "sub_verdicts": {},
                        "pair_trigger": {
                            "eligible": False,
                            "reasons": [],
                            "skipped_reason": "user_no_pair",
                        },
                    }
                },
            }),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert any(
            finding.get("id") == "verify-pair-trigger-conflicting-pair-flags"
            for finding in findings
        ), findings

        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "mode": "spec",
                "risk_profile": {
                    "high_risk": True,
                    "risk_probes_enabled": True,
                    "pair_default_enabled": False,
                },
                "phases": {
                    "verify": {
                        "verdict": "PASS",
                        "sub_verdicts": {},
                        "pair_trigger": {
                            "eligible": False,
                            "reasons": [],
                            "skipped_reason": "user_no_pair",
                        },
                    }
                },
            }),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "PASS", summary
        assert not any(
            finding.get("id") == "verify-pair-trigger-required-missing"
            for finding in findings
        ), findings

        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "phases": {
                    "verify": {
                        "verdict": "PASS",
                        "sub_verdicts": {},
                        "pair_trigger": {
                            "eligible": False,
                            "reasons": [],
                            "skipped_reason": ["user_no_pair"],
                        },
                    }
                }
            }),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert any(
            finding.get("id") == "verify-pair-trigger-skipped-reason-malformed"
            for finding in findings
        ), findings

        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "phases": {
                    "verify": {
                        "verdict": "PASS",
                        "sub_verdicts": {},
                        "pair_trigger": {
                            "eligible": False,
                            "reasons": [],
                            "skipped_reason": "codex_unavailable",
                        },
                    }
                }
            }),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert any(
            finding.get("id") == "verify-pair-trigger-skipped-reason-unsupported"
            for finding in findings
        ), findings

        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "phases": {
                    "verify": {
                        "verdict": "PASS",
                        "sub_verdicts": {},
                        "pair_trigger": {
                            "eligible": False,
                            "reasons": [],
                            "skipped_reason": "mechanical_blocker",
                        },
                    }
                }
            }),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert any(
            finding.get("id") == "verify-pair-trigger-mechanical-blocker-unsupported"
            for finding in findings
        ), findings

        (devlyn / "verify-mechanical.findings.jsonl").write_text(
            json.dumps({"id": "m1", "severity": "HIGH"}) + "\n",
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "NEEDS_WORK", summary
        assert not any(
            finding.get("id") == "verify-pair-trigger-mechanical-blocker-unsupported"
            for finding in findings
        ), findings
        (devlyn / "verify-mechanical.findings.jsonl").write_text("", encoding="utf-8")

        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "phases": {
                    "verify": {
                        "verdict": "PASS",
                        "sub_verdicts": {},
                        "pair_trigger": {
                            "eligible": False,
                            "reasons": [],
                            "skipped_reason": "primary_judge_blocker",
                        },
                    }
                }
            }),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert any(
            finding.get("id") == "verify-pair-trigger-primary-judge-blocker-unsupported"
            for finding in findings
        ), findings

        (devlyn / "verify.findings.jsonl").write_text(
            json.dumps({"id": "j2", "severity": "HIGH"}) + "\n",
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "NEEDS_WORK", summary
        assert not any(
            finding.get("id") == "verify-pair-trigger-primary-judge-blocker-unsupported"
            for finding in findings
        ), findings
        (devlyn / "verify.findings.jsonl").write_text("", encoding="utf-8")

        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "phases": {"verify": {"verdict": "PASS", "sub_verdicts": {}}},
                "verify": {
                    "pair_trigger": {
                        "eligible": True,
                        "reasons": ["looks-hard"],
                        "skipped_reason": None,
                    }
                },
            }),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert any(
            finding.get("id") == "verify-pair-trigger-reasons-unknown"
            for finding in findings
        ), findings
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--devlyn-dir", default=".devlyn")
    parser.add_argument("--write-state", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()

    devlyn = pathlib.Path(args.devlyn_dir)
    if not devlyn.is_dir():
        sys.stderr.write(f"error: {devlyn} is not a directory\n")
        return 1
    findings, source_verdicts = read_findings(devlyn)
    summary = write_outputs(devlyn, findings, source_verdicts)
    if args.write_state:
        write_state(devlyn, summary)
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
