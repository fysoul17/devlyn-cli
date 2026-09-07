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
import runpy
from typing import Any


JUDGE_OUTPUT_PARSER = runpy.run_path(pathlib.Path(__file__).with_name("judge-output-parser.py"))
PROCESS_EVIDENCE = runpy.run_path(pathlib.Path(__file__).with_name("process-evidence.py"))


SOURCE_FILES = (
    ("mechanical", "verify-mechanical.findings.jsonl"),
    ("judge", "verify.findings.jsonl"),
    ("pair_judge", "verify.pair.findings.jsonl"),
    ("pair_judge", "verify.pair-judge.findings.jsonl"),
)
REQUIRED_SOURCE_FILES = {
    "mechanical": "verify-mechanical.findings.jsonl",
    "judge": "verify.findings.jsonl",
}

VERDICT_RANK = {
    "PASS": 0,
    "TIMEOUT": 0,
    "PASS_WITH_ISSUES": 1,
    "FAIL": 2,
    "NEEDS_WORK": 2,
    "BLOCKED": 3,
}
RANK_VERDICT = {0: "PASS", 1: "PASS_WITH_ISSUES", 2: "NEEDS_WORK", 3: "BLOCKED"}
ALLOWED_PAIR_SKIP_REASONS = {
    "user_no_pair",
    "mechanical_blocker",
    "primary_judge_blocker",
    "auto_pair_other_engine_unavailable",
}
KNOWN_PAIR_TRIGGER_REASONS = {
    "pair.default",
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


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def loads_strict_json(text: str) -> Any:
    return json.loads(
        text,
        parse_constant=reject_json_constant,
        object_pairs_hook=reject_duplicate_keys,
    )


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


def state_uses_default_pair_contract(state: dict[str, Any]) -> bool:
    return state.get("version") == "3.0"


def finding_rank(finding: dict[str, Any]) -> int:
    severity = str(finding.get("severity") or "").upper()
    if severity in {"CRITICAL", "HIGH"}:
        return 2
    if severity == "MEDIUM" and finding.get("verdict_binding") is True:
        return 2
    if severity in {"LOW", "MEDIUM"}:
        return 1
    return 0


def mechanical_evidence_required(devlyn: pathlib.Path, state: dict[str, Any]) -> bool:
    return PROCESS_EVIDENCE["mechanical_evidence_required"](devlyn.parent.resolve(), state)


def mechanical_evidence_carrier(devlyn: pathlib.Path) -> dict[str, Any] | None:
    state_path = devlyn / "pipeline.state.json"
    state = loads_strict_json(state_path.read_text(encoding="utf-8"))
    if not isinstance(state, dict):
        raise ValueError("pipeline.state.json must contain a JSON object")
    results_path = devlyn / "spec-verify.results.json"
    if not results_path.is_file():
        if state.get("version") == "3.0" and mechanical_evidence_required(devlyn, state):
            raise ValueError("spec-verify.results.json is required for VERIFY MECHANICAL evidence")
        return None
    results = loads_strict_json(results_path.read_text(encoding="utf-8"))
    if not isinstance(results, dict):
        raise ValueError("spec-verify.results.json must contain a JSON object")
    commands = results.get("commands")
    if not isinstance(commands, list):
        raise ValueError("spec-verify.results.json commands must be an array")
    carrier = results.get("process_evidence")
    if carrier is None:
        if commands:
            raise ValueError("MECHANICAL commands exist without a process-evidence carrier")
        if mechanical_evidence_required(devlyn, state):
            raise ValueError("required VERIFY MECHANICAL evidence has no process-evidence carrier")
        run_id = state.get("run_id")
        phases = state.get("phases")
        verify_phase = phases.get("verify") if isinstance(phases, dict) else None
        round_ = verify_phase.get("round") if isinstance(verify_phase, dict) else None
        if isinstance(run_id, str) and isinstance(round_, int) and not isinstance(round_, bool):
            manifest_path = (
                devlyn / "process-evidence" / run_id / "verify"
                / f"round-{round_}" / "manifest.json"
            )
            if manifest_path.exists():
                raise ValueError("VERIFY manifest exists without a process-evidence carrier")
        return None
    run_id = state.get("run_id")
    phases = state.get("phases")
    verify_phase = phases.get("verify") if isinstance(phases, dict) else None
    round_ = verify_phase.get("round") if isinstance(verify_phase, dict) else None
    if not isinstance(run_id, str) or not run_id:
        raise ValueError("state.run_id is required for sealed MECHANICAL evidence")
    if isinstance(round_, bool) or not isinstance(round_, int) or round_ < 0:
        raise ValueError("phases.verify.round is required for sealed MECHANICAL evidence")
    if not isinstance(carrier, dict) or carrier.get("phase") != "verify" or carrier.get("round") != round_:
        raise ValueError("MECHANICAL process-evidence carrier does not match the VERIFY round")
    PROCESS_EVIDENCE["validate_summary_commands"](
        devlyn.parent.resolve(), commands, carrier,
    )
    expected_prefix = f".devlyn/process-evidence/{run_id}/verify/round-{round_}/"
    manifest = carrier.get("manifest")
    if not isinstance(manifest, dict) or not str(manifest.get("path", "")).startswith(expected_prefix):
        raise ValueError("MECHANICAL process-evidence carrier does not match state.run_id")

    bound = state.get("process_evidence")
    if bound is not None:
        if not isinstance(bound, list):
            raise ValueError("state.process_evidence must be null or an array")
        same_round = [
            item for item in bound
            if isinstance(item, dict)
            and item.get("phase") == "verify"
            and item.get("round") == round_
        ]
        if same_round and same_round != [carrier]:
            raise ValueError("state-bound VERIFY evidence disagrees with MECHANICAL results")
    return carrier


def mechanical_evidence_violation(devlyn: pathlib.Path) -> dict[str, Any] | None:
    try:
        mechanical_evidence_carrier(devlyn)
    except (PROCESS_EVIDENCE["EvidenceError"], OSError, UnicodeError, ValueError) as exc:
        return {
            "id": "verify-mechanical-evidence-invalid",
            "rule_id": "invariant.process-evidence-invalid",
            "severity": "CRITICAL",
            "confidence": "high",
            "file": "spec-verify.results.json",
            "line": 1,
            "message": f"Sealed VERIFY MECHANICAL evidence failed rehash before merge: {exc}",
            "criterion_ref": "process-evidence://mechanical",
            "source": "mechanical",
        }
    return None


def mechanical_evidence_outcome(devlyn: pathlib.Path) -> dict[str, Any] | None:
    carrier = mechanical_evidence_carrier(devlyn)
    if carrier is None:
        return None
    return PROCESS_EVIDENCE["bound_carrier_outcome"](devlyn.parent.resolve(), carrier)


ROLE_CONFIG = runpy.run_path(pathlib.Path(__file__).with_name("role-config.py"))
JUDGE_ROLE_EVIDENCE = runpy.run_path(pathlib.Path(__file__).with_name("judge-role-evidence.py"))


def resolved_primary_engine(state):
    return ROLE_CONFIG["primary_engine"](state)


def primary_timeout_blocker(id_: str, message: str) -> dict[str, Any]:
    return {
        "id": id_,
        "rule_id": "verify.primary.timeout-contract",
        "severity": "CRITICAL",
        "confidence": "high",
        "file": "verify.primary.timeout.json",
        "line": 1,
        "message": message,
        "criterion_ref": "verify.primary.timeout",
        "source": "judge",
    }


def read_primary_timeout_marker(
    devlyn: pathlib.Path,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    path = devlyn / "verify.primary.timeout.json"
    if not path.is_file():
        return None, None
    try:
        marker = loads_strict_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        return None, primary_timeout_blocker(
            "verify-primary-timeout-marker-malformed",
            f"verify.primary.timeout.json is malformed: {exc}",
        )
    if not isinstance(marker, dict) or set(marker) != {"engine", "budget_seconds"}:
        return None, primary_timeout_blocker(
            "verify-primary-timeout-marker-malformed",
            "verify.primary.timeout.json must contain exactly engine and budget_seconds.",
        )
    engine = marker["engine"]
    budget_seconds = marker["budget_seconds"]
    if not isinstance(engine, str) or not engine:
        return None, primary_timeout_blocker(
            "verify-primary-timeout-marker-malformed",
            "verify.primary.timeout.json engine must be a non-empty string.",
        )
    if (
        not isinstance(budget_seconds, int)
        or isinstance(budget_seconds, bool)
        or budget_seconds != 600
    ):
        return None, primary_timeout_blocker(
            "verify-primary-timeout-budget-mismatch",
            "verify.primary.timeout.json budget_seconds must equal 600.",
        )
    try:
        state = loads_strict_json(
            (devlyn / "pipeline.state.json").read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, ValueError) as exc:
        return None, primary_timeout_blocker(
            "verify-primary-timeout-engine-mismatch",
            f"Cannot authenticate the primary timeout engine from pipeline.state.json: {exc}",
        )
    try:
        expected_engine = resolved_primary_engine(state) if isinstance(state, dict) else None
    except ValueError:
        expected_engine = None
    if (
        not isinstance(expected_engine, str)
        or not expected_engine
        or engine != expected_engine
    ):
        return None, primary_timeout_blocker(
            "verify-primary-timeout-engine-mismatch",
            "Primary timeout engine does not match the resolved primary judge.",
        )
    return {"engine": engine, "budget_seconds": budget_seconds}, None


def read_findings(devlyn: pathlib.Path) -> tuple[list[dict[str, Any]], dict[str, str | None]]:
    findings: list[dict[str, Any]] = []
    source_verdicts: dict[str, str | None] = {source: "PASS" for source, _ in SOURCE_FILES}
    primary_timeout_marker, primary_timeout_violation = read_primary_timeout_marker(devlyn)
    # A verdict must come from a judge that ran: pair_judge stays null until
    # spawn evidence exists (a pair findings file or pair stdout). verify.md's
    # pair contract records null when no second agent is spawned.
    source_verdicts["pair_judge"] = None
    for source, name in SOURCE_FILES:
        path = devlyn / name
        if not path.is_file():
            # A verdict-binding mechanical result contractually skips both
            # judges. Its absent primary carrier is therefore not evidence a
            # dispatched primary judge failed to produce.
            if source == "judge" and rank(source_verdicts.get("mechanical")) >= 2:
                source_verdicts[source] = None
                continue
            if source == "judge" and primary_timeout_marker is not None:
                continue
            if REQUIRED_SOURCE_FILES.get(source) == name:
                findings.append({
                    "id": f"verify-merge-required-source-missing-{source}",
                    "rule_id": "verify.findings.required-source-missing",
                    "severity": "CRITICAL",
                    "confidence": "high",
                    "file": name,
                    "line": 1,
                    "message": f"Required VERIFY {source} findings file is missing: {name}",
                    "criterion_ref": "verify-merge",
                    "source": source,
                })
                source_verdicts[source] = "BLOCKED"
            continue
        if source_verdicts[source] is None:
            source_verdicts[source] = "PASS"
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
    evidence_violation = mechanical_evidence_violation(devlyn)
    if evidence_violation is not None:
        findings.append(evidence_violation)
        source_verdicts["mechanical"] = "BLOCKED"
    else:
        outcome = mechanical_evidence_outcome(devlyn)
        if outcome is not None and outcome["verdict"] != "PASS":
            blocked = outcome["verdict"] == "BLOCKED"
            ids = (
                [item["id"] for item in outcome["capability_denials"]]
                if blocked else outcome["failed_ids"]
            )
            findings.append({
                "id": (
                    "verify-mechanical-capability-denied"
                    if blocked else "verify-mechanical-expectation-mismatch"
                ),
                "rule_id": (
                    "invariant.build-env-underprovisioned"
                    if blocked else "invariant.mechanical-expectation-mismatch"
                ),
                "severity": "CRITICAL" if blocked else "HIGH",
                "confidence": "high",
                "file": "spec-verify.results.json",
                "line": 1,
                "message": (
                    "Sealed VERIFY MECHANICAL evidence records a capability denial: "
                    if blocked else
                    "Sealed VERIFY MECHANICAL evidence records failed expectations: "
                ) + ",".join(ids),
                "criterion_ref": "process-evidence://mechanical",
                "source": "mechanical",
                "verdict_binding": True,
            })
            source_verdicts["mechanical"] = outcome["verdict"]
    if primary_timeout_violation is not None:
        findings.append(primary_timeout_violation)
        source_verdicts["judge"] = "BLOCKED"
    elif primary_timeout_marker is not None:
        findings.append(primary_timeout_blocker(
            "verify-primary-timeout",
            "Primary JUDGE exceeded its authenticated 600-second wall budget.",
        ))
        source_verdicts["judge"] = "BLOCKED"
    findings.extend(detect_pair_stdout_contract_violations(devlyn, source_verdicts))
    pair_summary_path = devlyn / "pair-judge.summary.json"
    pair_carrier_exists = any(
        (devlyn / name).is_file()
        for name in ("verify.pair.findings.jsonl", "verify.pair-judge.findings.jsonl")
    )
    if pair_carrier_exists and pair_summary_path.is_file():
        try:
            pair_summary = loads_strict_json(pair_summary_path.read_text(encoding="utf-8"))
        except ValueError as exc:
            summary_error = f"pair-judge.summary.json is malformed JSON: {exc}"
        else:
            pair_verdict = pair_summary.get("verdict") if isinstance(pair_summary, dict) else None
            summary_error = None
            if not isinstance(pair_summary, dict):
                summary_error = "pair-judge.summary.json must be a JSON object."
            elif not isinstance(pair_verdict, str) or pair_verdict not in {
                "PASS", "PASS_WITH_ISSUES", "FAIL", "NEEDS_WORK", "BLOCKED"
            }:
                summary_error = (
                    "pair-judge.summary.json verdict must be PASS, PASS_WITH_ISSUES, "
                    "FAIL, NEEDS_WORK, or BLOCKED."
                )
        if summary_error is not None:
            findings.append(
                pair_blocker(
                    "verify-pair-summary-invalid",
                    summary_error,
                    pair_summary_path.name,
                )
            )
            source_verdicts["pair_judge"] = "BLOCKED"
        elif (
            source_verdicts["pair_judge"] != "TIMEOUT"
            or rank(pair_verdict) > rank("TIMEOUT")
        ):
            source_verdicts["pair_judge"] = worse(
                source_verdicts["pair_judge"], pair_verdict
            )
    if (devlyn / "pipeline.state.json").is_file():
        try:
            state = loads_strict_json((devlyn / "pipeline.state.json").read_text())
            required = JUDGE_ROLE_EVIDENCE["required_roles"](state)
            if rank(source_verdicts.get("mechanical")) >= 2:
                required = []
            for role in required:
                source = "judge" if role == "primary_judge" else "pair_judge"
                if source_verdicts.get(source) in {"BLOCKED", "TIMEOUT"}:
                    continue
                try:
                    JUDGE_ROLE_EVIDENCE["authenticate"](devlyn, state, role)
                except (ValueError, OSError, TypeError, KeyError) as exc:
                    source_verdicts[source] = "BLOCKED"
                    findings.append({**primary_timeout_blocker("verify-role-evidence-invalid", str(exc)),
                                     "source": source, "rule_id": "verify.role-evidence"})
        except (ValueError, OSError, TypeError, KeyError) as exc:
            source_verdicts["judge"] = "BLOCKED"
            findings.append({**primary_timeout_blocker("verify-role-resolution-invalid", str(exc)),
                             "rule_id": "verify.role-resolution"})
    return findings, source_verdicts


def has_pair_findings(devlyn: pathlib.Path) -> bool:
    for name in ("verify.pair.findings.jsonl", "verify.pair-judge.findings.jsonl"):
        path = devlyn / name
        if path.is_file() and path.read_text(encoding="utf-8").strip():
            return True
    return False


def canonical_other_judge_stdout(devlyn: pathlib.Path, primary_engine: str) -> list[pathlib.Path]:
    adapters = pathlib.Path(__file__).with_name("adapters")
    engine_names = {
        path.stem for path in adapters.glob("*.md")
        if path.stem != "README"
    }
    return sorted(
        devlyn / f"{engine}-judge.stdout"
        for engine in engine_names
        if engine != primary_engine and (devlyn / f"{engine}-judge.stdout").is_file()
    )


def pair_capture_exists(devlyn: pathlib.Path, stdout_paths: list[pathlib.Path]) -> bool:
    return bool(stdout_paths) or has_pair_findings(devlyn) or any(
        (devlyn / name).is_file()
        for name in (
            "verify.pair.timeout.json",
            "pair-judge.summary.json",
        )
    )


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


def verify_state_contract_violation(devlyn: pathlib.Path) -> dict[str, Any] | None:
    state_path = devlyn / "pipeline.state.json"
    if not state_path.is_file():
        return {
            "id": "verify-state-missing",
            "rule_id": "verify.state.missing",
            "message": "pipeline.state.json is required before VERIFY merge.",
            "file": "pipeline.state.json",
        }
    try:
        state = loads_strict_json(state_path.read_text(encoding="utf-8"))
    except ValueError:
        return {
            "id": "verify-pair-trigger-state-malformed",
            "rule_id": "verify.pair.emission-contract",
            "message": "pipeline.state.json is malformed; cannot verify pair_trigger contract.",
            "file": "pipeline.state.json",
        }
    if not isinstance(state, dict):
        return {
            "id": "verify-state-malformed",
            "rule_id": "verify.state.malformed",
            "message": "pipeline.state.json must be a JSON object before VERIFY merge.",
            "file": "pipeline.state.json",
        }
    try:
        engine = resolved_primary_engine(state)
    except ValueError:
        engine = None
    if not isinstance(engine, str) or not engine.strip():
        rule = "verify.state.engine-malformed"
        return {
            "id": rule,
            "rule_id": rule,
            "message": "pipeline.state.json requires a valid primary engine before VERIFY merge.",
            "file": "pipeline.state.json",
        }
    if not state_uses_default_pair_contract(state):
        return None
    source = state.get("source")
    if not isinstance(source, dict) or source.get("type") != "generated":
        return None
    goal_path = source.get("goal_path")
    goal_sha256 = source.get("goal_sha256")
    if (
        not isinstance(goal_path, str)
        or not goal_path
        or not isinstance(goal_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", goal_sha256) is None
    ):
        rule = "verify.state.goal-persistence-missing"
        return {
            "id": rule,
            "rule_id": rule,
            "message": (
                "schema-v3 generated runs require source.goal_path as a non-empty string "
                "and source.goal_sha256 as 64 lowercase hexadecimal characters."
            ),
            "file": "pipeline.state.json",
        }
    if state.get("complexity") in {"trivial", "medium"}:
        phases = state.get("phases")
        surface_close = phases.get("surface_close") if isinstance(phases, dict) else None
        skipped = (
            isinstance(surface_close, dict)
            and surface_close.get("verdict") is None
            and surface_close.get("started_at") is None
            and surface_close.get("skipped_reason") == "auto_surface_close_claude_unavailable"
        )
        if (
            not isinstance(surface_close, dict)
            or (surface_close.get("verdict") is None and not skipped)
        ):
            rule = "verify.state.surface-close-skipped"
            return {
                "id": rule,
                "rule_id": rule,
                "message": (
                    "schema-v3 generated trivial/medium runs require completed SURFACE_CLOSE "
                    "or its canonical automatic Claude-unavailable skip before VERIFY merge."
                ),
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
    source_verdicts: dict[str, str | None],
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
    if (
        state_uses_default_pair_contract(state)
        and risk_profile.get("pair_default_enabled") is not False
    ):
        reasons.append("pair.default")
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


def outcome_independent_reasons(devlyn: pathlib.Path) -> list[str]:
    return [
        reason
        for reason in state_pair_trigger_reasons(devlyn, {})
        if reason not in ("coverage.failed", "mechanical.warning", "judge.warning")
    ]


def pair_trigger_missing_contract_violation(
    devlyn: pathlib.Path,
    source_verdicts: dict[str, str | None],
) -> dict[str, Any] | None:
    if rank(source_verdicts.get("mechanical")) >= 2:
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
    source_verdicts: dict[str, str | None],
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
                "mechanical_blocker, primary_judge_blocker, "
                "auto_pair_other_engine_unavailable, or null."
            ),
            "file": "pipeline.state.json",
        }
    if skipped_reason == "auto_pair_other_engine_unavailable":
        # alpha+ capability-gating: an AUTOMATIC pair trigger may skip to solo
        # VERIFY when the OTHER engine is unavailable (single-LLM users stay
        # first-class). An EXPLICIT --pair-verify route is a promise and must
        # BLOCK on an unavailable engine, never skip — enforce that here so the
        # auto-skip cannot launder an explicit request.
        pair_verify = state.get("pair_verify") if isinstance(state, dict) else None
        if pair_verify is True:
            return {
                "id": "verify-pair-trigger-auto-skip-explicit-conflict",
                "message": (
                    "pair_trigger skipped_reason auto_pair_other_engine_unavailable is "
                    "only valid for an automatic trigger; an explicit --pair-verify run "
                    "must BLOCK on an unavailable OTHER engine, not skip."
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
    if skipped_reason == "primary_judge_blocker":
        if state_uses_default_pair_contract(state):
            return {
                "id": "verify-pair-trigger-primary-judge-blocker-retired",
                "message": (
                    "pair_trigger skipped_reason primary_judge_blocker is archived-v2.0 "
                    "state only; schema-v3 runs must dispatch the pair-JUDGE."
                ),
                "file": "pipeline.state.json",
            }
        if rank(source_verdicts.get("judge")) < 2:
            return {
                "id": "verify-pair-trigger-primary-judge-blocker-unsupported",
                "message": (
                    "pair_trigger skipped_reason primary_judge_blocker requires a "
                    "verdict-binding primary JUDGE finding."
                ),
                "file": "pipeline.state.json",
            }
        preknown_reasons = outcome_independent_reasons(devlyn)
        if preknown_reasons:
            return {
                "id": "verify-pair-trigger-primary-judge-blocker-preknown",
                "message": (
                    "pair_trigger cannot skip the pair-JUDGE for a primary JUDGE blocker "
                    "when outcome-independent reasons applied at spawn: "
                    + ", ".join(preknown_reasons)
                ),
                "file": "pipeline.state.json",
            }
    return None


def pair_trigger_reason_completeness_violation(
    devlyn: pathlib.Path,
    source_verdicts: dict[str, str | None],
) -> dict[str, Any] | None:
    if rank(source_verdicts.get("mechanical")) >= 2:
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


def pair_blocker(
    id_: str,
    message: str,
    file_: str | None = None,
    rule_id: str = "verify.pair.emission-contract",
) -> dict[str, Any]:
    return {
        "id": id_,
        "rule_id": rule_id,
        "severity": "CRITICAL",
        "confidence": "high",
        "file": file_,
        "line": 1 if file_ else None,
        "message": message,
        "criterion_ref": "verify.pair.findings",
        "source": "pair_judge",
    }


def read_pair_timeout_marker(devlyn: pathlib.Path) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    path = devlyn / "verify.pair.timeout.json"
    if not path.is_file():
        return None, None
    try:
        marker = loads_strict_json(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return None, {
            "id": "verify-pair-timeout-marker-malformed",
            "message": f"verify.pair.timeout.json is malformed JSON: {exc}",
            "file": "verify.pair.timeout.json",
        }
    if not isinstance(marker, dict):
        return None, {
            "id": "verify-pair-timeout-marker-malformed",
            "message": "verify.pair.timeout.json must be a JSON object.",
            "file": "verify.pair.timeout.json",
        }
    engine = marker.get("engine")
    budget_seconds = marker.get("budget_seconds")
    if not isinstance(engine, str) or not engine:
        return None, {
            "id": "verify-pair-timeout-marker-malformed",
            "message": "verify.pair.timeout.json engine must be a non-empty string.",
            "file": "verify.pair.timeout.json",
        }
    if (
        not isinstance(budget_seconds, int)
        or isinstance(budget_seconds, bool)
        or budget_seconds <= 0
    ):
        return None, {
            "id": "verify-pair-timeout-marker-malformed",
            "message": "verify.pair.timeout.json budget_seconds must be a positive integer.",
            "file": "verify.pair.timeout.json",
        }
    return {"engine": engine, "budget_seconds": budget_seconds}, None


def is_result_less_message_stream(stdout_text: str) -> bool:
    """True when a declared whole-message stream stops before its terminal result.

    The timeout marker attests the killed process. This classifier admits only a
    valid stream prefix, optionally ending in one truncated JSON record.
    """
    lines = [raw for line in stdout_text.splitlines() if (raw := line.strip())]
    if not lines:
        return False
    try:
        first = JUDGE_OUTPUT_PARSER["loads_strict_json"](lines[0])
    except ValueError:
        return False
    if (
        not isinstance(first, dict)
        or first.get("type") != "system"
        or first.get("subtype") != "init"
        or not isinstance(first.get("session_id"), str)
    ):
        return False
    session_id = first["session_id"]
    for index, raw in enumerate(lines[1:], 1):
        try:
            item = JUDGE_OUTPUT_PARSER["loads_strict_json"](raw)
        except ValueError:
            return index == len(lines) - 1 and raw.startswith("{") and not raw.endswith("}")
        if (
            not isinstance(item, dict)
            or item.get("type") not in {"assistant", "user"}
            or item.get("session_id") != session_id
        ):
            return False
    return True


def detect_pair_stdout_contract_violations(
    devlyn: pathlib.Path,
    source_verdicts: dict[str, str | None],
) -> list[dict[str, Any]]:
    # The primary uses its explicit phase engine, or the legacy executor; only the OTHER engine's
    # capture is pair evidence.
    timeout_marker, timeout_violation = read_pair_timeout_marker(devlyn)
    if timeout_violation is not None:
        source_verdicts["pair_judge"] = "BLOCKED"
        return [
            pair_blocker(
                timeout_violation["id"],
                timeout_violation["message"],
                timeout_violation["file"],
            )
        ]
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
    state_violation = verify_state_contract_violation(devlyn)
    if state_violation is not None:
        source_verdicts["pair_judge"] = "BLOCKED"
        return [
            pair_blocker(
                state_violation["id"],
                state_violation["message"],
                state_violation["file"],
                state_violation["rule_id"],
            )
        ]
    state = loads_strict_json((devlyn / "pipeline.state.json").read_text(encoding="utf-8"))
    assert isinstance(state, dict)
    engine = resolved_primary_engine(state)
    assert isinstance(engine, str) and engine.strip()
    stdout_paths = canonical_other_judge_stdout(devlyn, engine)
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
    trigger_present = pair_trigger_present(devlyn)
    if trigger_present and not required:
        if pair_capture_exists(devlyn, stdout_paths):
            source_verdicts["pair_judge"] = "BLOCKED"
            return [
                pair_blocker(
                    "verify-pair-skipped-output-present",
                    "Pair state is skipped or ineligible, but a canonical OTHER-judge carrier exists.",
                    stdout_paths[0].name if stdout_paths else "verify.pair.findings.jsonl",
                    "verify.pair.state-capture-contradiction",
                )
            ]
        source_verdicts["pair_judge"] = None
        return []
    if len(stdout_paths) > 1:
        source_verdicts["pair_judge"] = "BLOCKED"
        return [
            pair_blocker(
                "verify-pair-output-ambiguous",
                "Multiple canonical OTHER-engine stdout carriers exist: "
                + ", ".join(path.name for path in stdout_paths),
                stdout_paths[0].name,
            )
        ]
    if timeout_marker is not None:
        expected_timeout_stdout = f"{timeout_marker['engine']}-judge.stdout"
        if timeout_marker["engine"] == engine or (
            stdout_paths and stdout_paths[0].name != expected_timeout_stdout
        ):
            source_verdicts["pair_judge"] = "BLOCKED"
            return [
                pair_blocker(
                    "verify-pair-timeout-engine-mismatch",
                    "Pair timeout engine does not match the canonical OTHER-engine carrier.",
                    "verify.pair.timeout.json",
                )
            ]
    if not stdout_paths:
        if timeout_marker is not None:
            if rank(source_verdicts["pair_judge"]) <= rank("TIMEOUT"):
                source_verdicts["pair_judge"] = "TIMEOUT"
            return []
        if required:
            source_verdicts["pair_judge"] = "BLOCKED"
            return [
                pair_blocker(
                    "verify-pair-required-output-missing",
                    "Pair-mode was required, but the pair-JUDGE produced no canonical OTHER-engine stdout.",
                    "verify.pair.findings.jsonl",
                )
            ]
        return []
    if has_pair_findings(devlyn):
        return []
    if source_verdicts["pair_judge"] is None and timeout_marker is None:
        source_verdicts["pair_judge"] = "PASS"
    for stdout_path in stdout_paths:
        stdout_text = stdout_path.read_text(encoding="utf-8")
        if not stdout_text.strip():
            if timeout_marker is not None:
                continue
            source_verdicts["pair_judge"] = "BLOCKED"
            return [
                pair_blocker(
                    "verify-pair-empty-output",
                    f"pair-JUDGE stdout {stdout_path.name} was empty; the bounded contract requires a JSONL finding or PASS line.",
                    stdout_path.name,
                )
            ]
        try:
            stdout_findings, stdout_summary = JUDGE_OUTPUT_PARSER["collect_stdout"](stdout_path)
        except SystemExit as exc:
            if timeout_marker is not None and is_result_less_message_stream(stdout_text):
                continue
            source_verdicts["pair_judge"] = "BLOCKED"
            return [
                pair_blocker(
                    "verify-pair-emission-contract-violated",
                    f"pair-JUDGE stdout {stdout_path.name} violates the shared emission parser: {exc}",
                    stdout_path.name,
                )
            ]
        if stdout_findings or stdout_summary is None or stdout_summary["verdict"] != "PASS":
            source_verdicts["pair_judge"] = "BLOCKED"
            return [
                pair_blocker(
                    "verify-pair-emission-contract-violated",
                    (
                        f"pair-JUDGE stdout {stdout_path.name} contained findings or a non-PASS "
                        "verdict, but the canonical pair findings JSONL file was empty."
                    ),
                    stdout_path.name,
                )
            ]
    if timeout_marker is not None:
        source_verdicts["pair_judge"] = "TIMEOUT"
    return []


def write_outputs(
    devlyn: pathlib.Path,
    findings: list[dict[str, Any]],
    source_verdicts: dict[str, str | None],
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
    if source_verdicts.get("pair_judge") == "TIMEOUT":
        timeout_marker, _timeout_violation = read_pair_timeout_marker(devlyn)
        if timeout_marker is not None:
            summary["pair_timeout"] = timeout_marker
            summary["report_header_note"] = "solo verdict after pair TIMEOUT"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def write_state(devlyn: pathlib.Path, summary: dict[str, Any]) -> None:
    state_path = devlyn / "pipeline.state.json"
    if not state_path.is_file():
        raise SystemExit(f"error: {state_path} not found")
    state = loads_strict_json(state_path.read_text(encoding="utf-8"))
    try:
        carrier = mechanical_evidence_carrier(devlyn)
    except (PROCESS_EVIDENCE["EvidenceError"], OSError, UnicodeError, ValueError) as exc:
        if summary.get("source_verdicts", {}).get("mechanical") != "BLOCKED":
            raise SystemExit(f"error: invalid MECHANICAL process evidence: {exc}") from exc
        carrier = None
    if carrier is not None:
        bound = state.get("process_evidence")
        if bound is None:
            bound = []
        elif not isinstance(bound, list):
            raise SystemExit("error: state.process_evidence must be null or an array")
        same_round = [
            item for item in bound
            if isinstance(item, dict)
            and item.get("phase") == carrier["phase"]
            and item.get("round") == carrier["round"]
        ]
        if same_round and same_round != [carrier]:
            raise SystemExit("error: state-bound VERIFY evidence disagrees with MECHANICAL results")
        if not same_round:
            bound.append(carrier)
        state["process_evidence"] = bound
    phases = state.setdefault("phases", {})
    verify = phases.get("verify")
    if not isinstance(verify, dict):
        verify = {}
        phases["verify"] = verify
    role_evidence = {}
    try:
        required_roles = JUDGE_ROLE_EVIDENCE["required_roles"](state)
    except ValueError as exc:
        if summary.get("source_verdicts", {}).get("judge") != "BLOCKED":
            raise SystemExit(str(exc)) from exc
        required_roles = []  # Persist the invalid-resolution failure; no legacy dispatch.
    for role in required_roles:
        source = "judge" if role == "primary_judge" else "pair_judge"
        if summary.get("source_verdicts", {}).get(source) in {"PASS", "PASS_WITH_ISSUES", "NEEDS_WORK"}:
            role_evidence[role] = JUDGE_ROLE_EVIDENCE["authenticate"](devlyn, state, role)
    if role_evidence:
        verify["role_evidence"] = role_evidence
    verify["verdict"] = summary["verdict"]
    sub = verify.get("sub_verdicts")
    if sub is None:
        # spawn (state-phase-write.py) always writes sub_verdicts: null as
        # part of the per-round reset contract (state-schema.md#write-protocol)
        # — legal, expected state before this function populates it.
        # setdefault() would not replace an existing null, only an absent key.
        sub = {}
        verify["sub_verdicts"] = sub
    elif not isinstance(sub, dict):
        raise SystemExit(
            f"error: phases.verify.sub_verdicts must be null or an object, got {type(sub).__name__}"
        )
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
    import subprocess

    try:
        loads_strict_json('{"verdict":"PASS","verdict":"BLOCKED"}')
    except ValueError as exc:
        assert "duplicate JSON key" in str(exc)
    else:
        raise AssertionError("duplicate VERIFY authority key was accepted")
    with tempfile.TemporaryDirectory() as tmp:
        devlyn = pathlib.Path(tmp)

        # Every completed VERIFY has deterministic mechanical and primary
        # judge carriers.  Missing either one is an evidence failure, not PASS.
        (devlyn / "verify-mechanical.findings.jsonl").write_text("", encoding="utf-8")

        # state-phase-write.py's spawn always writes sub_verdicts: null (the
        # per-round reset contract, state-schema.md#write-protocol) — this is
        # the real shape write_state() sees on every VERIFY completion, not
        # the pre-populated {} the other scenarios below seed for brevity.
        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "engine": "claude",
                "phases": {
                    "verify": {
                        "verdict": None,
                        "sub_verdicts": None,
                        "judge_durations_ms": {"judge": 23, "pair_judge": 31},
                    }
                }
            }),
            encoding="utf-8",
        )
        (devlyn / "verify.findings.jsonl").write_text("", encoding="utf-8")

        sealed_work = pathlib.Path(tmp) / "sealed-work"
        sealed_devlyn = sealed_work / ".devlyn"
        sealed_devlyn.mkdir(parents=True)
        sealed_state = {
            "run_id": "rs-sealed-mechanical",
            "engine": "claude",
            "process_evidence": None,
            "phases": {"verify": {"round": 2, "verdict": None, "sub_verdicts": None}},
        }
        obligation = PROCESS_EVIDENCE["normalize_obligation"]({
            "id": "mechanical-0",
            "phase": "verify",
            "argv": [sys.executable, "-c", "print('sealed')"],
        })
        manifest_rel = PROCESS_EVIDENCE["manifest_relative_path"](sealed_state, "verify")
        PROCESS_EVIDENCE["capture_process"](
            sealed_work, sealed_work / manifest_rel, sealed_state["run_id"],
            "verify", 2, obligation,
        )
        carrier = PROCESS_EVIDENCE["validate_manifest"](
            sealed_work, manifest_rel, sealed_state["run_id"], "verify", 2,
            [obligation], require_expectations=False,
        )
        (sealed_devlyn / "pipeline.state.json").write_text(
            json.dumps(sealed_state), encoding="utf-8",
        )
        sealed_commands = PROCESS_EVIDENCE["bound_carrier_summary_commands"](
            sealed_work, carrier,
        )
        (sealed_devlyn / "spec-verify.results.json").write_text(
            json.dumps({"commands": sealed_commands, "process_evidence": carrier}),
            encoding="utf-8",
        )
        (sealed_devlyn / "verify-mechanical.findings.jsonl").write_text("", encoding="utf-8")
        (sealed_devlyn / "verify.findings.jsonl").write_text("", encoding="utf-8")
        sealed_findings, sealed_verdicts = read_findings(sealed_devlyn)
        assert sealed_verdicts["mechanical"] == "PASS", sealed_findings
        sealed_summary = write_outputs(sealed_devlyn, sealed_findings, sealed_verdicts)
        write_state(sealed_devlyn, sealed_summary)
        bound_state = loads_strict_json(
            (sealed_devlyn / "pipeline.state.json").read_text(encoding="utf-8")
        )
        assert bound_state["process_evidence"] == [carrier], bound_state

        failed_work = pathlib.Path(tmp) / "failed-work"
        failed_devlyn = failed_work / ".devlyn"
        failed_devlyn.mkdir(parents=True)
        failed_state = {
            "version": "3.0",
            "run_id": "rs-failed-mechanical",
            "engine": "claude",
            "source": {"type": "spec", "spec_path": "docs/failed/spec.md"},
            "process_evidence": None,
            "phases": {"verify": {"round": 0, "verdict": None, "sub_verdicts": None}},
        }
        failed_spec = failed_work / "docs" / "failed"
        failed_spec.mkdir(parents=True)
        (failed_spec / "spec.md").write_text("# failed fixture\n", encoding="utf-8")
        (failed_spec / "spec.expected.json").write_text(json.dumps({
            "verification_commands": [{"cmd": "exit 7", "exit_code": 0}],
        }) + "\n", encoding="utf-8")
        failed_obligation = PROCESS_EVIDENCE["normalize_obligation"]({
            "id": "verification-command-0001",
            "phase": "verify",
            "cmd": "exit 7",
        })
        failed_manifest = PROCESS_EVIDENCE["manifest_relative_path"](failed_state, "verify")
        PROCESS_EVIDENCE["capture_process"](
            failed_work, failed_work / failed_manifest, failed_state["run_id"],
            "verify", 0, failed_obligation,
        )
        failed_carrier = PROCESS_EVIDENCE["validate_manifest"](
            failed_work, failed_manifest, failed_state["run_id"], "verify", 0,
            [failed_obligation], require_expectations=False,
        )
        (failed_devlyn / "pipeline.state.json").write_text(
            json.dumps(failed_state), encoding="utf-8",
        )
        # Exact laundering attempt: mutable derivatives say PASS/empty while
        # the state-identical sealed manifest still records the failed command.
        laundered_commands = PROCESS_EVIDENCE["bound_carrier_summary_commands"](
            failed_work, failed_carrier,
        )
        laundered_commands[0]["pass"] = True
        (failed_devlyn / "spec-verify.results.json").write_text(json.dumps({
            "commands": laundered_commands, "process_evidence": failed_carrier,
        }), encoding="utf-8")
        (failed_devlyn / "verify-mechanical.findings.jsonl").write_text("", encoding="utf-8")
        (failed_devlyn / "verify.findings.jsonl").write_text("", encoding="utf-8")
        failed_findings, failed_verdicts = read_findings(failed_devlyn)
        assert failed_verdicts["mechanical"] == "BLOCKED", failed_verdicts
        assert any(
            item.get("id") == "verify-mechanical-evidence-invalid"
            for item in failed_findings
        ), failed_findings
        assert write_outputs(failed_devlyn, failed_findings, failed_verdicts)["verdict"] == "BLOCKED"

        (failed_devlyn / "spec-verify.results.json").write_text(json.dumps({
            "commands": [], "process_evidence": None,
        }), encoding="utf-8")
        removed_findings, removed_verdicts = read_findings(failed_devlyn)
        assert removed_verdicts["mechanical"] == "BLOCKED", removed_verdicts
        assert any(
            item.get("id") == "verify-mechanical-evidence-invalid"
            for item in removed_findings
        ), removed_findings
        print("PASS iter-0112 sealed VERIFY outcome resists mutable-derivative laundering")

        sealed_stdout = sealed_work / carrier["streams"][0]["stdout"]["path"]
        sealed_stdout.write_bytes(sealed_stdout.read_bytes() + b"altered")
        altered_findings, altered_verdicts = read_findings(sealed_devlyn)
        assert altered_verdicts["mechanical"] == "BLOCKED", altered_verdicts
        assert any(
            finding.get("id") == "verify-mechanical-evidence-invalid"
            for finding in altered_findings
        ), altered_findings

        skipped_work = pathlib.Path(tmp) / "skipped-work"
        skipped_work.mkdir()
        (skipped_work / "pipeline.state.json").write_text(json.dumps({
            "engine": "claude",
            "risk_profile": {"pair_default_enabled": False},
            "phases": {"verify": {"pair_trigger": {
                "eligible": False,
                "reasons": [],
                "skipped_reason": "user_no_pair",
            }}},
        }), encoding="utf-8")
        (skipped_work / "verify-mechanical.findings.jsonl").write_text("", encoding="utf-8")
        (skipped_work / "verify.findings.jsonl").write_text("", encoding="utf-8")
        generic_primary = skipped_work / "verify-judge.stdout"
        for generic_output in ("PASS\n", "NEEDS_WORK\n"):
            generic_primary.write_text(generic_output, encoding="utf-8")
            generic_findings, generic_verdicts = read_findings(skipped_work)
            assert generic_verdicts["pair_judge"] is None, generic_verdicts
            assert not any(
                finding.get("file") == generic_primary.name for finding in generic_findings
            ), generic_findings
        (skipped_work / "codex-judge.stdout").write_text("PASS\n", encoding="utf-8")
        contradiction_findings, contradiction_verdicts = read_findings(skipped_work)
        assert contradiction_verdicts["pair_judge"] == "BLOCKED", contradiction_verdicts
        assert any(
            finding.get("id") == "verify-pair-skipped-output-present"
            for finding in contradiction_findings
        ), contradiction_findings
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        write_state(devlyn, summary)
        state = loads_strict_json((devlyn / "pipeline.state.json").read_text(encoding="utf-8"))
        assert summary["verdict"] == "PASS", summary
        assert state["phases"]["verify"]["sub_verdicts"] == {
            "mechanical": "PASS", "judge": "PASS", "pair_judge": None,
        }, state
        assert state["phases"]["verify"]["judge_durations_ms"] == {
            "judge": 23, "pair_judge": 31,
        }, state
        original_state = (devlyn / "pipeline.state.json").read_bytes()
        for malformed in (None, {}, {"roles": {}}):
            bad_state = loads_strict_json(original_state)
            bad_state["role_resolution"] = malformed
            (devlyn / "pipeline.state.json").write_text(json.dumps(bad_state))
            result = subprocess.run([sys.executable, str(pathlib.Path(__file__).resolve()),
                                     "--devlyn-dir", str(devlyn), "--write-state"], capture_output=True, text=True)
            assert result.returncode == 0 and "Traceback" not in result.stderr, result.stderr
            persisted = loads_strict_json((devlyn / "pipeline.state.json").read_text())
            assert persisted["phases"]["verify"]["verdict"] == "BLOCKED"
            assert "verify-role-resolution-invalid" in (devlyn / "verify-merged.findings.jsonl").read_text()
        (devlyn / "pipeline.state.json").write_bytes(original_state)
        different_primary = {"engine": "codex", "phases": {"verify": {"engine": "claude"}}}
        (devlyn / "pipeline.state.json").write_text(json.dumps(different_primary))
        (devlyn / "verify.primary.timeout.json").write_text(json.dumps({"engine": "claude", "budget_seconds": 600}))
        marker, violation = read_primary_timeout_marker(devlyn)
        assert marker is not None and violation is None
        different_primary["phases"]["verify"]["engine"] = None
        (devlyn / "pipeline.state.json").write_text(json.dumps(different_primary))
        assert read_primary_timeout_marker(devlyn)[1] is not None
        (devlyn / "verify.primary.timeout.json").unlink()
        (devlyn / "pipeline.state.json").write_bytes(original_state)

        (devlyn / "verify.findings.jsonl").unlink()
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert summary["source_verdicts"]["judge"] == "BLOCKED", summary
        assert any(
            finding["id"] == "verify-merge-required-source-missing-judge"
            for finding in findings
        ), findings

        # iter-0113: a valid primary timeout is an explicit BLOCKED source,
        # never the generic missing-source path or pair-style TIMEOUT.
        (devlyn / "verify.primary.timeout.json").write_text(
            json.dumps({"engine": "claude", "budget_seconds": 600}) + "\n",
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert summary["source_verdicts"]["judge"] == "BLOCKED", summary
        assert any(
            finding["id"] == "verify-primary-timeout"
            for finding in findings
        ), findings
        assert not any(
            finding["id"] == "verify-merge-required-source-missing-judge"
            for finding in findings
        ), findings

        (devlyn / "verify.findings.jsonl").write_text(
            json.dumps({"id": "primary-timeout-high", "severity": "HIGH"}) + "\n",
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        assert source_verdicts["judge"] == "BLOCKED", source_verdicts
        assert {finding["id"] for finding in findings} >= {
            "primary-timeout-high", "verify-primary-timeout",
        }, findings

        for marker, expected_id in (
            ("{\n", "verify-primary-timeout-marker-malformed"),
            (
                json.dumps({"engine": "codex", "budget_seconds": 600}) + "\n",
                "verify-primary-timeout-engine-mismatch",
            ),
            (
                json.dumps({"engine": "claude", "budget_seconds": 601}) + "\n",
                "verify-primary-timeout-budget-mismatch",
            ),
        ):
            (devlyn / "verify.primary.timeout.json").write_text(marker, encoding="utf-8")
            findings, source_verdicts = read_findings(devlyn)
            assert source_verdicts["judge"] == "BLOCKED", source_verdicts
            assert any(finding["id"] == expected_id for finding in findings), findings
        (devlyn / "verify.primary.timeout.json").unlink()
        (devlyn / "verify.findings.jsonl").write_text("", encoding="utf-8")

        # iter-0072 Amendment 3: generated schema-v3 runs mechanically prove
        # raw-goal persistence and required SURFACE_CLOSE dispatch.
        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "version": "3.0",
                "engine": "claude",
                "complexity": "large",
                "source": {"type": "generated"},
                "phases": {"verify": {"verdict": None, "sub_verdicts": None}},
            }),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert summary["source_verdicts"]["pair_judge"] == "BLOCKED", summary
        assert any(
            finding.get("rule_id") == "verify.state.goal-persistence-missing"
            for finding in findings
        ), findings

        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "version": "3.0",
                "engine": "claude",
                "complexity": "large",
                "source": {"type": "generated", "goal_path": "", "goal_sha256": "A" * 64},
            }),
            encoding="utf-8",
        )
        violation = verify_state_contract_violation(devlyn)
        assert violation is not None, violation
        assert violation["rule_id"] == "verify.state.goal-persistence-missing", violation

        generated_source = {
            "type": "generated",
            "goal_path": ".devlyn/goal.raw.txt",
            "goal_sha256": "a" * 64,
        }
        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "version": "3.0",
                "engine": "claude",
                "complexity": "medium",
                "source": generated_source,
                "phases": {
                    "surface_close": None,
                    "verify": {"verdict": None, "sub_verdicts": None},
                },
            }),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert any(
            finding.get("rule_id") == "verify.state.surface-close-skipped"
            for finding in findings
        ), findings

        for surface_entry in (
            {"verdict": "PASS"},
            {
                "verdict": None,
                "started_at": None,
                "skipped_reason": "auto_surface_close_claude_unavailable",
            },
        ):
            (devlyn / "pipeline.state.json").write_text(
                json.dumps({
                    "version": "3.0",
                    "engine": "claude",
                    "complexity": "medium",
                    "source": generated_source,
                    "phases": {"surface_close": surface_entry},
                }),
                encoding="utf-8",
            )
            assert verify_state_contract_violation(devlyn) is None

        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "version": "3.0",
                "engine": "claude",
                "complexity": "medium",
                "source": generated_source,
                "phases": {
                    "surface_close": {
                        "verdict": None,
                        "started_at": None,
                        "skipped_reason": "claude-unavailable",
                    },
                },
            }),
            encoding="utf-8",
        )
        assert verify_state_contract_violation(devlyn)["rule_id"] == "verify.state.surface-close-skipped"

        for state_shape in (
            {
                "version": "3.0", "engine": "claude", "complexity": "medium",
                "source": {"type": "spec"}, "phases": {"surface_close": None},
            },
            {
                "version": "3.0", "engine": "claude", "complexity": "large",
                "source": generated_source, "phases": {"surface_close": None},
            },
            {
                "version": "2.0", "engine": "claude", "complexity": "medium",
                "source": {"type": "generated"}, "phases": {"surface_close": None},
            },
        ):
            (devlyn / "pipeline.state.json").write_text(
                json.dumps(state_shape), encoding="utf-8",
            )
            assert verify_state_contract_violation(devlyn) is None

        # 2026-07-04 field bug (iter-0060 G1): an AUTO pair trigger skipped on
        # OTHER-engine unavailability spawns no second judge — pair_judge must
        # be recorded null, never a synthesized PASS.
        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "version": "3.0",
                "engine": "claude",
                "mode": "spec",
                "risk_profile": {"pair_default_enabled": True},
                "phases": {
                    "verify": {
                        "verdict": None,
                        "sub_verdicts": None,
                        "pair_trigger": {
                            "eligible": False,
                            "reasons": [],
                            "skipped_reason": "auto_pair_other_engine_unavailable",
                        },
                    }
                },
            }),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        write_state(devlyn, summary)
        state = loads_strict_json((devlyn / "pipeline.state.json").read_text(encoding="utf-8"))
        assert summary["verdict"] == "PASS", summary
        assert summary["source_verdicts"]["pair_judge"] is None, summary
        assert state["phases"]["verify"]["sub_verdicts"]["pair_judge"] is None, state

        # A non-null, non-dict sub_verdicts is corrupted state, not a legal
        # placeholder — write_state() must fail loud, not silently coerce it.
        (devlyn / "pipeline.state.json").write_text(
            json.dumps({"engine": "claude", "phases": {"verify": {"verdict": None, "sub_verdicts": "corrupt"}}}),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        try:
            write_state(devlyn, summary)
        except SystemExit as e:
            assert "sub_verdicts must be null or an object" in str(e), e
        else:
            raise AssertionError("write_state() must reject non-dict, non-null sub_verdicts")

        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "engine": "claude",
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
        (devlyn / "codex-judge.stdout").write_text("PASS\n", encoding="utf-8")
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        write_state(devlyn, summary)
        state = loads_strict_json((devlyn / "pipeline.state.json").read_text(encoding="utf-8"))
        assert summary["verdict"] == "NEEDS_WORK", summary
        assert state["phases"]["verify"]["verdict"] == "NEEDS_WORK", state
        assert state["phases"]["verify"]["sub_verdicts"]["pair_judge"] == "NEEDS_WORK", state
        assert (devlyn / "verify-merged.findings.jsonl").read_text(encoding="utf-8")
        (devlyn / "codex-judge.stdout").unlink()
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
            json.dumps({"engine": "claude", "phases": {"verify": {"verdict": "PASS", "sub_verdicts": {}}}}),
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

        # Engine-neutral stdout contract (iter-0060): a Claude pair-judge
        # capture (claude-judge.stdout, adapters/claude.md ## Invocation)
        # binds the same emission contract as the Codex one.
        (devlyn / "pipeline.state.json").write_text(
            json.dumps({"engine": "codex", "phases": {"verify": {"verdict": "PASS", "sub_verdicts": {}}}}),
            encoding="utf-8",
        )
        (devlyn / "claude-judge.stdout").write_text(
            json.dumps({"id": "clj1", "severity": "HIGH"}) + "\n",
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert any(
            finding.get("id") == "verify-pair-emission-contract-violated"
            and "claude-judge.stdout" in finding.get("message", "")
            for finding in findings
        ), findings
        (devlyn / "claude-judge.stdout").unlink()

        # iter-0065 case 1: a valid pair timeout marker plus empty pair output
        # records TIMEOUT and leaves the merged verdict to mechanical+primary.
        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "engine": "codex",
                "phases": {
                    "verify": {
                        "verdict": "PASS",
                        "sub_verdicts": {},
                        "pair_trigger": {
                            "eligible": True,
                            "reasons": ["judge.warning"],
                            "skipped_reason": None,
                        },
                    }
                }
            }),
            encoding="utf-8",
        )
        (devlyn / "verify.findings.jsonl").write_text(
            json.dumps({"id": "j-timeout-low", "severity": "LOW"}) + "\n",
            encoding="utf-8",
        )
        (devlyn / "verify.pair.findings.jsonl").write_text("", encoding="utf-8")
        (devlyn / "claude-judge.stdout").write_text("", encoding="utf-8")
        (devlyn / "verify.pair.timeout.json").write_text(
            json.dumps({"engine": "claude", "budget_seconds": 600}),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        write_state(devlyn, summary)
        state = loads_strict_json((devlyn / "pipeline.state.json").read_text(encoding="utf-8"))
        assert summary["verdict"] == "PASS_WITH_ISSUES", summary
        assert summary["source_verdicts"]["pair_judge"] == "TIMEOUT", summary
        assert summary["pair_timeout"] == {"engine": "claude", "budget_seconds": 600}, summary
        assert summary["report_header_note"] == "solo verdict after pair TIMEOUT", summary
        assert state["phases"]["verify"]["sub_verdicts"]["pair_judge"] == "TIMEOUT", state
        (devlyn / "claude-judge.stdout").unlink()
        (devlyn / "verify.pair.timeout.json").unlink()
        (devlyn / "verify.findings.jsonl").write_text("", encoding="utf-8")

        # iter-0065 case 2: canonical pair findings still bind after timeout.
        (devlyn / "pipeline.state.json").write_text(
            json.dumps({"engine": "claude", "phases": {"verify": {"verdict": "PASS", "sub_verdicts": {}}}}),
            encoding="utf-8",
        )
        (devlyn / "verify.pair.findings.jsonl").write_text(
            json.dumps({"id": "p-timeout-high", "severity": "HIGH"}) + "\n",
            encoding="utf-8",
        )
        (devlyn / "verify.pair.timeout.json").write_text(
            json.dumps({"engine": "codex", "budget_seconds": 600}),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "NEEDS_WORK", summary
        assert summary["source_verdicts"]["pair_judge"] == "NEEDS_WORK", summary
        assert "pair_timeout" not in summary, summary
        (devlyn / "verify.pair.timeout.json").unlink()
        (devlyn / "verify.pair.findings.jsonl").write_text("", encoding="utf-8")

        # iter-0065 case 2b: stdout-only HIGH still blocks on emission contract;
        # timeout never converts an observed finding into a solo pass.
        (devlyn / "pipeline.state.json").write_text(
            json.dumps({"engine": "claude", "phases": {"verify": {"verdict": "PASS", "sub_verdicts": {}}}}),
            encoding="utf-8",
        )
        (devlyn / "codex-judge.stdout").write_text(
            json.dumps({"id": "cj-timeout-high", "severity": "HIGH"}) + "\n",
            encoding="utf-8",
        )
        (devlyn / "verify.pair.timeout.json").write_text(
            json.dumps({"engine": "codex", "budget_seconds": 600}),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert summary["source_verdicts"]["pair_judge"] == "BLOCKED", summary
        assert any(
            finding.get("id") == "verify-pair-emission-contract-violated"
            for finding in findings
        ), findings
        (devlyn / "codex-judge.stdout").unlink()
        (devlyn / "verify.pair.timeout.json").unlink()

        # iter-0106: a budget abort can truncate the whole-message stream before
        # its terminal result. With a valid marker that capture stays TIMEOUT.
        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "engine": "claude",
                "phases": {
                    "verify": {
                        "verdict": "PASS",
                        "sub_verdicts": {},
                        "pair_trigger": {
                            "eligible": True,
                            "reasons": ["judge.warning"],
                            "skipped_reason": None,
                        },
                    }
                }
            }),
            encoding="utf-8",
        )
        partial_stream = (
            '{"type":"system","subtype":"init","session_id":"s106"}\n'
            '{"type":"assistant","session_id":"s106","message":{"stop_reason":null,'
            '"content":[{"type":"text","text":"reading the diff"}]}}\n'
        )
        (devlyn / "grok-judge.stdout").write_text(partial_stream, encoding="utf-8")
        (devlyn / "verify.pair.timeout.json").write_text(
            json.dumps({"engine": "grok", "budget_seconds": 600}),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "PASS", summary
        assert summary["source_verdicts"]["pair_judge"] == "TIMEOUT", summary
        assert summary["pair_timeout"] == {"engine": "grok", "budget_seconds": 600}, summary
        assert not findings, findings

        # A kill may cut the final JSON record mid-write; one malformed tail is
        # still a valid prefix, while malformed/unknown complete records are not.
        (devlyn / "grok-judge.stdout").write_text(
            partial_stream + '{"type":"assistant","session_id":"s106"',
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["source_verdicts"]["pair_judge"] == "TIMEOUT", summary
        assert not findings, findings

        for invalid_prefix in (
            '{"type":"system","subtype":"init"}\n',
            partial_stream + "trailing narration\n",
            partial_stream
            + '{"type":"user","session_id":"other"}\n',
            partial_stream
            + '{"type":"stream_event","session_id":"s106"}\n',
            partial_stream
            + '{"type":"system","subtype":"compact_boundary","session_id":"s106"}\n',
            partial_stream
            + '{"type":"assistant"\n'
            + '{"type":"user","session_id":"s106"}\n',
        ):
            (devlyn / "grok-judge.stdout").write_text(invalid_prefix, encoding="utf-8")
            findings, source_verdicts = read_findings(devlyn)
            summary = write_outputs(devlyn, findings, source_verdicts)
            assert summary["source_verdicts"]["pair_judge"] == "BLOCKED", summary
            assert any(
                finding.get("id") == "verify-pair-emission-contract-violated"
                for finding in findings
            ), findings

        # iter-0106 control: the marker conserves TIMEOUT only for that shape. A
        # stream that reached its result but welded narration into the terminal
        # message stays BLOCKED on the emission contract.
        (devlyn / "grok-judge.stdout").write_text(
            '{"type":"system","subtype":"init","session_id":"s106"}\n'
            + json.dumps({
                "type": "assistant",
                "session_id": "s106",
                "message": {
                    "stop_reason": "end_turn",
                    "content": [{"type": "text", "text": "I reviewed the diff.\nPASS"}],
                },
            }) + "\n"
            + json.dumps({
                "type": "result",
                "subtype": "success",
                "is_error": False,
                "stop_reason": "end_turn",
                "session_id": "s106",
                "result": "I reviewed the diff.\nPASS",
            }) + "\n",
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert summary["source_verdicts"]["pair_judge"] == "BLOCKED", summary
        assert any(
            finding.get("id") == "verify-pair-emission-contract-violated"
            for finding in findings
        ), findings
        (devlyn / "verify.pair.timeout.json").unlink()

        # iter-0106 control: without a marker the same truncated stream is a
        # plain emission-contract violation.
        (devlyn / "grok-judge.stdout").write_text(partial_stream, encoding="utf-8")
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert summary["source_verdicts"]["pair_judge"] == "BLOCKED", summary
        assert any(
            finding.get("id") == "verify-pair-emission-contract-violated"
            for finding in findings
        ), findings
        (devlyn / "grok-judge.stdout").unlink()

        # iter-0065 case 3: without a marker, required empty pair output remains BLOCKED.
        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "engine": "codex",
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
        (devlyn / "claude-judge.stdout").write_text("", encoding="utf-8")
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert any(
            finding.get("id") == "verify-pair-empty-output"
            for finding in findings
        ), findings
        (devlyn / "claude-judge.stdout").unlink()

        # iter-0065 malformed timeout markers fail closed as a CRITICAL pair blocker.
        (devlyn / "pipeline.state.json").write_text(
            json.dumps({"engine": "claude", "phases": {"verify": {"verdict": "PASS", "sub_verdicts": {}}}}),
            encoding="utf-8",
        )
        (devlyn / "verify.pair.timeout.json").write_text(
            json.dumps({"engine": "claude", "budget_seconds": 0}),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert summary["source_verdicts"]["pair_judge"] == "BLOCKED", summary
        assert any(
            finding.get("id") == "verify-pair-timeout-marker-malformed"
            and finding.get("severity") == "CRITICAL"
            for finding in findings
        ), findings
        (devlyn / "verify.pair.timeout.json").unlink()
        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "engine": "claude",
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
                "engine": "claude",
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
                "engine": "claude",
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
                "engine": "claude",
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
                "engine": "claude",
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
                "engine": "claude",
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
                "engine": "claude",
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
                "engine": "claude",
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
                "engine": "claude",
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
                "engine": "claude",
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
                "engine": "claude",
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
                "engine": "claude",
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
                "engine": "claude",
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
                "engine": "claude",
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
                "engine": "claude",
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
                "engine": "claude",
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
                "engine": "claude",
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
                "engine": "claude",
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
                "engine": "claude",
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
                "engine": "claude",
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
                "engine": "claude",
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
                "engine": "claude",
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
                "engine": "claude",
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
                "engine": "claude",
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
                "engine": "claude",
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
                "engine": "claude",
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
                "engine": "claude",
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
                "engine": "claude",
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
        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "engine": "claude",
                "phases": {
                    "verify": {
                        "verdict": None,
                        "sub_verdicts": None,
                        "judge_durations_ms": {"judge": None, "pair_judge": None},
                    }
                }
            }),
            encoding="utf-8",
        )
        (devlyn / "verify.findings.jsonl").unlink()
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        write_state(devlyn, summary)
        state = loads_strict_json((devlyn / "pipeline.state.json").read_text(encoding="utf-8"))
        assert summary["verdict"] == "NEEDS_WORK", summary
        assert summary["source_verdicts"]["judge"] is None, summary
        assert state["phases"]["verify"]["verdict"] == "NEEDS_WORK", state
        assert state["phases"]["verify"]["sub_verdicts"]["judge"] is None, state
        (devlyn / "verify.findings.jsonl").write_text("", encoding="utf-8")
        (devlyn / "verify-mechanical.findings.jsonl").write_text("", encoding="utf-8")

        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "engine": "claude",
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

        # Self-test: preknown_primary_blocker_requires_pair.
        (devlyn / "verify.pair.findings.jsonl").unlink(missing_ok=True)
        (devlyn / "verify.findings.jsonl").write_text(
            json.dumps({"id": "j-preknown", "severity": "HIGH"}) + "\n",
            encoding="utf-8",
        )
        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "version": "2.0",
                "engine": "claude",
                "mode": "spec",
                "pair_verify": True,
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
                },
            }),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert any(
            finding.get("id") == "verify-pair-trigger-primary-judge-blocker-preknown"
            and "mode.pair-verify" in str(finding.get("message"))
            for finding in findings
        ), findings

        # Self-test: schema-v3 default pair reason is required before merge.
        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "version": "3.0",
                "engine": "claude",
                "mode": "spec",
                "pair_verify": True,
                "phases": {
                    "verify": {
                        "verdict": "PASS",
                        "sub_verdicts": {},
                        "pair_trigger": {
                            "eligible": True,
                            "reasons": ["mode.pair-verify"],
                            "skipped_reason": None,
                        },
                    }
                },
            }),
            encoding="utf-8",
        )
        (devlyn / "verify.pair.findings.jsonl").write_text(
            json.dumps({"id": "p-preknown", "severity": "LOW"}) + "\n",
            encoding="utf-8",
        )
        (devlyn / "codex-judge.stdout").write_text("PASS\n", encoding="utf-8")
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert any(
            finding.get("id") == "verify-pair-trigger-reasons-incomplete"
            and "pair.default" in str(finding.get("message"))
            for finding in findings
        ), findings
        state = loads_strict_json((devlyn / "pipeline.state.json").read_text(encoding="utf-8"))
        state["phases"]["verify"]["pair_trigger"]["reasons"].insert(0, "pair.default")
        (devlyn / "pipeline.state.json").write_text(json.dumps(state), encoding="utf-8")
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "NEEDS_WORK", summary
        assert summary["source_verdicts"]["judge"] == "NEEDS_WORK", summary
        assert summary["source_verdicts"]["pair_judge"] == "PASS_WITH_ISSUES", summary
        assert '"id":"p-preknown"' in (
            devlyn / "verify-merged.findings.jsonl"
        ).read_text(encoding="utf-8"), findings
        (devlyn / "codex-judge.stdout").unlink()

        # Self-test: archived-v2 sequential primary blocker remains legal.
        (devlyn / "verify.pair.findings.jsonl").unlink()
        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "version": "2.0",
                "engine": "claude",
                "mode": "spec",
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
                },
            }),
            encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "NEEDS_WORK", summary
        assert summary["source_verdicts"]["pair_judge"] is None, summary
        assert not any(
            finding.get("id") in {
                "verify-pair-trigger-primary-judge-blocker-unsupported",
                "verify-pair-trigger-primary-judge-blocker-preknown",
            }
            for finding in findings
        ), findings
        # Replay the same state as schema v3 and require the retired-skip blocker.
        state = loads_strict_json((devlyn / "pipeline.state.json").read_text(encoding="utf-8"))
        state["version"] = "3.0"
        (devlyn / "pipeline.state.json").write_text(json.dumps(state), encoding="utf-8")
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        assert summary["verdict"] == "BLOCKED", summary
        assert any(
            finding.get("id") == "verify-pair-trigger-primary-judge-blocker-retired"
            for finding in findings
        ), findings
        (devlyn / "verify.findings.jsonl").write_text("", encoding="utf-8")
        (devlyn / "verify.pair.findings.jsonl").write_text("", encoding="utf-8")

        (devlyn / "pipeline.state.json").write_text(
            json.dumps({
                "engine": "claude",
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

        # stdout-only spawn evidence: no pair findings file at all; a clean
        # PASS stdout from a claude judge promotes pair_judge null -> PASS.
        (devlyn / "verify.pair.findings.jsonl").unlink()
        (devlyn / "pipeline.state.json").write_text(
            json.dumps({"engine": "codex", "phases": {"verify": {"verdict": None, "sub_verdicts": None}}}),
            encoding="utf-8",
        )
        (devlyn / "claude-judge.stdout").write_text("PASS\n", encoding="utf-8")
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        write_state(devlyn, summary)
        state = loads_strict_json((devlyn / "pipeline.state.json").read_text(encoding="utf-8"))
        assert summary["verdict"] == "PASS", summary
        assert state["phases"]["verify"]["sub_verdicts"]["pair_judge"] == "PASS", state
        (devlyn / "claude-judge.stdout").unlink()

        # The primary capture must not be misattributed to the OTHER-engine
        # pair seat merely because both adapters use *-judge.stdout names.
        (devlyn / "pipeline.state.json").write_text(
            json.dumps({"engine": "claude", "phases": {"verify": {"verdict": None, "sub_verdicts": None}}}),
            encoding="utf-8",
        )
        (devlyn / "claude-judge.stdout").write_text("primary prose\n", encoding="utf-8")
        (devlyn / "codex-judge.stdout").write_text("PASS\n", encoding="utf-8")
        findings, source_verdicts = read_findings(devlyn)
        assert source_verdicts["pair_judge"] == "PASS", source_verdicts
        assert not any(finding["source"] == "pair_judge" for finding in findings), findings
        (devlyn / "codex-judge.stdout").write_text("pair prose\n", encoding="utf-8")
        findings, source_verdicts = read_findings(devlyn)
        assert source_verdicts["pair_judge"] == "BLOCKED", source_verdicts
        assert any(finding["id"] == "verify-pair-emission-contract-violated" for finding in findings)
        (devlyn / "claude-judge.stdout").unlink()
        (devlyn / "codex-judge.stdout").unlink()

        # A primary capture cannot become pair evidence when the state needed
        # to identify the primary seat is absent, incomplete, or malformed.
        (devlyn / "claude-judge.stdout").write_text("primary prose\n", encoding="utf-8")
        (devlyn / "pipeline.state.json").unlink()
        findings, source_verdicts = read_findings(devlyn)
        assert source_verdicts["pair_judge"] == "BLOCKED", source_verdicts
        assert any(finding["id"] == "verify-state-missing" for finding in findings), findings
        assert not any(finding.get("file") == "claude-judge.stdout" for finding in findings), findings

        (devlyn / "pipeline.state.json").write_text(
            json.dumps({"version": "3.0", "phases": {"verify": {}}}), encoding="utf-8",
        )
        findings, source_verdicts = read_findings(devlyn)
        assert source_verdicts["pair_judge"] == "BLOCKED", source_verdicts
        assert any(finding.get("rule_id") == "verify.state.engine-malformed" for finding in findings), findings

        (devlyn / "pipeline.state.json").write_text("{", encoding="utf-8")
        findings, source_verdicts = read_findings(devlyn)
        assert source_verdicts["pair_judge"] == "BLOCKED", source_verdicts
        assert any(finding["id"] == "verify-pair-trigger-state-malformed" for finding in findings), findings
        (devlyn / "claude-judge.stdout").unlink()

        # iter-0083: canonical summary verdict conservation.
        iter_0083_paths = (
            "pipeline.state.json",
            "verify-mechanical.findings.jsonl",
            "verify.findings.jsonl",
            "verify.pair.findings.jsonl",
            "verify.pair-judge.findings.jsonl",
            "pair-judge.summary.json",
            "codex-primary-judge.summary.json",
            "grok-judge.summary.json",
            "verify.pair.timeout.json",
            "codex-judge.stdout",
            "claude-judge.stdout",
        )

        def iter_0083_reset() -> None:
            for name in iter_0083_paths:
                (devlyn / name).unlink(missing_ok=True)

        def iter_0083_case(
            summary_payload: object | None,
            severity: str | None,
            *,
            carrier: str | None = "verify.pair.findings.jsonl",
            other_summary: str | None = None,
            timeout: bool = False,
        ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
            iter_0083_reset()
            (devlyn / "pipeline.state.json").write_text(
                json.dumps({"engine": "claude", "phases": {"verify": {}}}), encoding="utf-8",
            )
            (devlyn / "verify-mechanical.findings.jsonl").write_text("", encoding="utf-8")
            (devlyn / "verify.findings.jsonl").write_text("", encoding="utf-8")
            if carrier is not None:
                content = (
                    json.dumps({"id": "iter-0083", "severity": severity}) + "\n"
                    if severity
                    else ""
                )
                (devlyn / carrier).write_text(content, encoding="utf-8")
            if summary_payload is not None:
                content = (
                    summary_payload
                    if isinstance(summary_payload, str)
                    else json.dumps(summary_payload)
                )
                (devlyn / "pair-judge.summary.json").write_text(content, encoding="utf-8")
            if other_summary is not None:
                (devlyn / other_summary).write_text(
                    json.dumps({"verdict": "BLOCKED"}), encoding="utf-8"
                )
            if timeout:
                (devlyn / "verify.pair.timeout.json").write_text(
                    json.dumps({"engine": "codex", "budget_seconds": 600}),
                    encoding="utf-8",
                )
            case_findings, case_source_verdicts = read_findings(devlyn)
            return case_findings, write_outputs(devlyn, case_findings, case_source_verdicts)

        for case_id, verdict, severity, expected in (
            ("P1", "NEEDS_WORK", "INFO", "NEEDS_WORK"),
            ("P2", "NEEDS_WORK", "LOW", "NEEDS_WORK"),
            ("P3", "NEEDS_WORK", "MEDIUM", "NEEDS_WORK"),
            ("P4", "PASS", "HIGH", "NEEDS_WORK"),
            ("P5", "BLOCKED", "INFO", "BLOCKED"),
            ("P6", "FAIL", "INFO", "NEEDS_WORK"),
            ("P7", "PASS", None, "PASS"),
        ):
            _, summary = iter_0083_case({"verdict": verdict}, severity)
            assert summary["source_verdicts"]["pair_judge"] == expected, case_id
            assert summary["verdict"] == expected, case_id

        for case_id, severity, expected in (
            ("P8-INFO", "INFO", "PASS"),
            ("P8-LOW", "LOW", "PASS_WITH_ISSUES"),
        ):
            _, summary = iter_0083_case(None, severity)
            assert summary["source_verdicts"]["pair_judge"] == expected, case_id
            assert summary["verdict"] == expected, case_id

        def assert_iter_0083_blocked(
            case_id: str,
            case_findings: list[dict[str, Any]],
            summary: dict[str, Any],
        ) -> None:
            assert summary["source_verdicts"]["pair_judge"] == "BLOCKED", case_id
            assert summary["verdict"] == "BLOCKED", case_id
            assert any(
                finding.get("source") == "pair_judge"
                and finding.get("severity") == "CRITICAL"
                and finding.get("file") == "pair-judge.summary.json"
                for finding in case_findings
            ), case_id

        for case_id, payload in (
            ("N1-malformed", "{"),
            ("N1-non-object", []),
            ("N1-unknown", {"verdict": "UNKNOWN"}),
            ("N2", {}),
            ("N7", {"verdict": "TIMEOUT"}),
        ):
            case_findings, summary = iter_0083_case(payload, "INFO")
            assert_iter_0083_blocked(case_id, case_findings, summary)

        _, summary = iter_0083_case({"verdict": "BLOCKED"}, None, carrier=None)
        assert summary["source_verdicts"]["pair_judge"] is None, summary
        assert summary["verdict"] == "PASS", summary

        _, summary = iter_0083_case(
            {"verdict": "PASS"},
            "INFO",
            other_summary="codex-primary-judge.summary.json",
        )
        assert summary["source_verdicts"]["pair_judge"] == "PASS", "N4"
        assert summary["verdict"] == "PASS", "N4"

        _, summary = iter_0083_case(
            None,
            "INFO",
            other_summary="grok-judge.summary.json",
        )
        assert summary["source_verdicts"]["pair_judge"] == "PASS", "N5"
        assert summary["verdict"] == "PASS", "N5"

        _, summary = iter_0083_case(
            {"verdict": "NEEDS_WORK"},
            "INFO",
            carrier="verify.pair-judge.findings.jsonl",
        )
        assert summary["source_verdicts"]["pair_judge"] == "NEEDS_WORK", "N6"
        assert summary["verdict"] == "NEEDS_WORK", "N6"

        case_findings, summary = iter_0083_case({"verdict": "BLOCKED"}, None, timeout=True)
        assert case_findings == [], "VERIFY-JUDGE-001"
        assert summary["source_verdicts"]["pair_judge"] == "BLOCKED", "VERIFY-JUDGE-001"
        assert summary["verdict"] == "BLOCKED", "VERIFY-JUDGE-001"
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
