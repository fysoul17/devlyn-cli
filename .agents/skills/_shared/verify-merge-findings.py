#!/usr/bin/env python3
"""Merge VERIFY findings and derive a deterministic verdict.

VERIFY judges are model-written, but routing on finding severity must be
mechanical. This script reads the known VERIFY JSONL finding files, writes a
merged JSONL artifact, computes source-level and overall verdicts, and can
write the merged verdict back to `.devlyn/pipeline.state.json`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import sys
import tempfile
import runpy
from typing import Any


JUDGE_OUTPUT_PARSER = runpy.run_path(pathlib.Path(__file__).with_name("judge-output-parser.py"))
PROCESS_EVIDENCE = runpy.run_path(pathlib.Path(__file__).with_name("process-evidence.py"))
RECEIPT = runpy.run_path(pathlib.Path(__file__).with_name("invocation-receipt.py"))
RENDER = runpy.run_path(pathlib.Path(__file__).with_name("phase-prompt-render.py"))


SOURCE_FILES = (
    ("mechanical", "verify-mechanical.findings.jsonl"),
    ("judge", "verify.findings.jsonl"),
    ("pair_judge", "verify.pair.findings.jsonl"),
)
REQUIRED_SOURCE_FILES = {
    "mechanical": "verify-mechanical.findings.jsonl",
    "judge": "verify.findings.jsonl",
}

VERDICT_RANK = JUDGE_OUTPUT_PARSER["VERDICT_RANK"]
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


finding_rank = JUDGE_OUTPUT_PARSER["finding_rank"]


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


def judge_blocker(source: str, id_: str, message: str, rule_id: str) -> dict[str, Any]:
    return {
        "id": id_,
        "rule_id": rule_id,
        "severity": "CRITICAL",
        "confidence": "high",
        "file": "pipeline.state.json",
        "line": 1,
        "message": message,
        "criterion_ref": "verify.judge",
        "source": source,
    }


def read_jsonl_source(
    devlyn: pathlib.Path, source: str, name: str, findings: list[dict[str, Any]], verdict: str,
) -> str:
    with (devlyn / name).open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            raw = line.strip()
            if not raw:
                continue
            try:
                item = loads_strict_json(raw)
            except ValueError as exc:
                findings.append({
                    "id": f"verify-merge-invalid-json-{name}-{line_no}",
                    "rule_id": "verify.findings.invalid-json",
                    "severity": "CRITICAL",
                    "confidence": "high",
                    "file": name,
                    "line": line_no,
                    "message": f"Invalid JSONL finding: {exc}",
                    "criterion_ref": "verify-merge",
                    "source": source,
                })
                verdict = "BLOCKED"
                continue
            if not isinstance(item, dict):
                continue
            item = dict(item)
            item.setdefault("source", source)
            findings.append(item)
            verdict = worse(verdict, RANK_VERDICT[finding_rank(item)])
    return verdict


def required_source_missing(source: str, name: str) -> dict[str, Any]:
    return {
        "id": f"verify-merge-required-source-missing-{source}",
        "rule_id": "verify.findings.required-source-missing",
        "severity": "CRITICAL",
        "confidence": "high",
        "file": name,
        "line": 1,
        "message": f"Required VERIFY {source} findings file is missing: {name}",
        "criterion_ref": "verify-merge",
        "source": source,
    }


_SPEC_VERIFY: dict[str, Any] | None = None


def mechanical_seal_violation(devlyn: pathlib.Path, verdict: str) -> dict[str, Any] | None:
    """A VERIFY span opened with a writer-recorded `pre_sha` reviews only sealed source.

    An unsealed round is acceptable only when MECHANICAL already binds NEEDS_WORK
    (the `--seal` refusal or another binding finding routes it to repair). A seal
    is rechecked against the live tree at every call: dispatch and merge.
    """
    global _SPEC_VERIFY
    state = loads_strict_json((devlyn / "pipeline.state.json").read_text(encoding="utf-8"))
    verify = (state.get("phases") or {}).get("verify") if isinstance(state, dict) else None
    if not isinstance(verify, dict) or not verify.get("pre_sha"):
        return None

    def blocker(message: str) -> dict[str, Any]:
        return {"id": "verify-mechanical-seal", "rule_id": "invariant.mechanical-seal",
                "severity": "CRITICAL", "confidence": "high", "file": "source-seal.json", "line": 1,
                "message": message, "criterion_ref": "mechanical://seal", "source": "mechanical",
                "verdict_binding": True}

    try:
        record = loads_strict_json((devlyn / "source-seal.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return blocker(f"MECHANICAL source seal is missing or unreadable: {exc}")
    if not isinstance(record, dict) or (record.get("run_id"), record.get("round")) != (
            state.get("run_id"), verify.get("round")):
        return blocker("MECHANICAL source seal belongs to another run or round")
    seal = record.get("seal")
    if seal is None:
        return None if rank(verdict) >= 2 else blocker(
            "MECHANICAL source was never sealed; run spec-verify-check.py --seal after artifact cleanup")
    if _SPEC_VERIFY is None:
        _SPEC_VERIFY = runpy.run_path(str(pathlib.Path(__file__).with_name("spec-verify-check.py")))
    try:
        _document, digest, _problems = _SPEC_VERIFY["source_snapshot"](devlyn.parent.resolve(), devlyn, state)
    except (OSError, ValueError) as exc:
        return blocker(f"MECHANICAL source seal could not be rechecked: {exc}")
    if not isinstance(seal, dict) or seal.get("digest") != record.get("digest") or digest != record.get("digest"):
        return blocker("source changed after the MECHANICAL seal")
    return None


def mechanical_source(devlyn: pathlib.Path) -> tuple[list[dict[str, Any]], str]:
    """MECHANICAL findings plus the sealed-evidence verdict; rank >= 2 skips both judges."""
    findings: list[dict[str, Any]] = []
    name = REQUIRED_SOURCE_FILES["mechanical"]
    if (devlyn / name).is_file():
        verdict = read_jsonl_source(devlyn, "mechanical", name, findings, "PASS")
    else:
        findings.append(required_source_missing("mechanical", name))
        verdict = "BLOCKED"
    evidence_violation = mechanical_evidence_violation(devlyn)
    if evidence_violation is not None:
        findings.append(evidence_violation)
        return findings, "BLOCKED"
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
        verdict = outcome["verdict"]
    seal_violation = mechanical_seal_violation(devlyn, verdict)
    if seal_violation is not None:
        findings.append(seal_violation)
        return findings, "BLOCKED"
    return findings, verdict


def read_findings(
    devlyn: pathlib.Path, collected: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, str | None]]:
    findings, mechanical = mechanical_source(devlyn)
    # A verdict must come from a judge that ran: pair_judge stays null until
    # its findings exist. A binding MECHANICAL result skips both judges.
    source_verdicts: dict[str, str | None] = {"mechanical": mechanical, "judge": "PASS", "pair_judge": None}
    for source, name in SOURCE_FILES[1:]:
        if (devlyn / name).is_file():
            source_verdicts[source] = read_jsonl_source(
                devlyn, source, name, findings, source_verdicts[source] or "PASS",
            )
        elif source == "judge" and rank(mechanical) >= 2:
            source_verdicts[source] = None
        elif source == "judge":
            findings.append(required_source_missing(source, name))
            source_verdicts[source] = "BLOCKED"
    for role, seat in (collected or {}).get("roles", {}).items():
        source = "judge" if role == "primary_judge" else "pair_judge"
        findings.extend(seat["blockers"])
        if seat["verdict"] is not None:
            source_verdicts[source] = worse(source_verdicts[source], seat["verdict"])
        if seat["timeout"] and rank(source_verdicts[source]) <= rank("TIMEOUT"):
            source_verdicts[source] = "TIMEOUT"
    findings.extend(pair_state_contract_violations(devlyn, source_verdicts))
    return findings, source_verdicts


def dispatch_name(round_: object) -> str:
    return f"verify-judge.r{round_}.dispatch.json"


def seal_file(path: pathlib.Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"not a regular judge artifact: {path.name}")
    raw = path.read_bytes()
    return {"path": ".devlyn/" + path.name, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def atomic_write_text(path: pathlib.Path, text: str) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(text)
    pathlib.Path(handle.name).replace(path)


def judge_seat(
    devlyn: pathlib.Path, state: dict[str, Any], record: dict[str, Any], role: str, collected: dict[str, Any],
) -> dict[str, Any]:
    """One seat's verdict from its runner-authored outcome and authenticated output."""
    source = "judge" if role == "primary_judge" else "pair_judge"
    entry = record["roles"][role]
    seat: dict[str, Any] = {"verdict": None, "blockers": [], "timeout": False}

    def blocked(id_: str, message: str, rule_id: str = "verify.judge.execution") -> dict[str, Any]:
        seat["verdict"] = "BLOCKED"
        seat["blockers"].append(judge_blocker(source, id_, message, rule_id))
        return seat

    if entry["decision"] == "skip":
        return seat
    if entry["decision"] == "blocked":
        return blocked("verify-judge-route-blocked", str(entry.get("reason")), "verify.judge.route")
    # Artifact names come from the frozen selection, never from the dispatch record alone.
    engine = ROLE_CONFIG["snapshot"](state)["roles"][role]["engine"]
    stem = f"{engine}-judge.r{state['phases']['verify']['round']}"
    capture = devlyn / (stem + (".output.json" if engine == "claude" else ".stdout"))
    # Seal every artifact the seat left before judging it, so none can change unobserved.
    names = [stem + suffix for suffix in (".prompt", ".argv.json", ".stderr", ".prompt.transport.json",
                                          ".role-evidence.json", ".stdout")] + [capture.name]
    try:
        artifacts = [seal_file(devlyn / name) for name in dict.fromkeys(names) if os.path.lexists(devlyn / name)]
    except ValueError as exc:
        return blocked("verify-judge-execution-incomplete", f"{stem}: {exc}")
    execution = {"artifacts": artifacts, "outcome": None, "exit_code": None}
    try:
        prompt = (devlyn / (stem + ".prompt")).read_bytes()
        argv = loads_strict_json((devlyn / (stem + ".argv.json")).read_text(encoding="utf-8"))
        if (entry.get("engine") != engine or entry.get("stem") != stem or argv != entry.get("argv")
                or hashlib.sha256(prompt).hexdigest() != entry["prompt_sha256"]
                or hashlib.sha256(RENDER["prompt_frames"](prompt)["snapshot"]).hexdigest() != record["snapshot_sha256"]):
            raise ValueError("prompt, argv or seat differ from the dispatch record")
        transport = JUDGE_ROLE_EVIDENCE["bound_transport"](devlyn, stem, ROLE_CONFIG["snapshot"](state)["roles"][role],
                                                           argv, prompt.decode("utf-8"))
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
        collected["executions"][role] = execution
        return blocked("verify-judge-execution-incomplete", f"{stem}: {exc}")
    collected["durations"][source] = transport["elapsed_ms"]
    outcome, exit_code = transport["outcome"], transport["exit_code"]
    execution.update(outcome=outcome, exit_code=exit_code)
    if outcome == "exited" and exit_code == 0:
        try:
            collected["role_evidence"][role] = JUDGE_ROLE_EVIDENCE["authenticate"](devlyn, state, role)
        except (ValueError, OSError, TypeError, KeyError) as exc:
            detail = str(exc)
            if not (devlyn / (stem + ".role-evidence.json")).exists():
                try:
                    JUDGE_ROLE_EVIDENCE["describe"](devlyn, state, role, 0)
                except (ValueError, OSError, TypeError, KeyError) as reason:
                    detail = str(reason)
            collected["executions"][role] = execution
            return blocked("verify-role-evidence-invalid", detail, "verify.role-evidence")
        output = devlyn / (stem + ".stdout")
    else:
        collected["executions"][role] = execution
        if outcome != "timed_out":
            return blocked("verify-judge-exit-nonzero" if outcome == "exited" else "verify-judge-not-completed",
                           f"{stem} {outcome} with exit {exit_code}")
        seat["timeout"] = True
        if role == "primary_judge":
            blocked("verify-primary-timeout", "Primary JUDGE exceeded its runner-authenticated 600-second budget.",
                    "verify.primary.timeout-contract")
        else:
            collected["pair_timeout"] = {"engine": engine, "budget_seconds": transport["timeout_sec"]}
        output = capture
    try:
        text = output.read_text(encoding="utf-8")
        if seat["timeout"] and not text.strip():
            return seat
        if seat["timeout"] and engine == "claude":
            # A Claude seat killed at the deadline after writing its result envelope still said something.
            result = JUDGE_ROLE_EVIDENCE["structured_judgment"](loads_strict_json(text)).decode("utf-8")
            found, summary = JUDGE_OUTPUT_PARSER["judge_findings"](*JUDGE_OUTPUT_PARSER["collect_text"](result, output))
        else:
            found, summary = JUDGE_OUTPUT_PARSER["collect_judge"](output)
    except (SystemExit, UnicodeError, OSError, ValueError, AttributeError) as exc:
        return blocked("verify-judge-emission-contract-violated", f"{output.name}: {exc}",
                       "verify.judge.emission-contract")
    collected["findings"][source] = found
    verdict = worse(RANK_VERDICT[max((finding_rank(item) for item in found), default=0)], summary["verdict"])
    seat["verdict"] = worse(seat["verdict"], verdict)
    return seat


def collect_judges(devlyn: pathlib.Path) -> dict[str, Any]:
    """Validate this round's dispatch record and derive each seat's findings.

    Runs under the state lock. The findings files are regenerated outputs of
    this call, never trusted inputs; the pre-launch pair_trigger is published
    to both state locations before any contract check reads it. It runs once
    per VERIFY round: a round that already has a merged verdict, or a dispatch
    record for a different run, round or span, stops the merge without writing.
    """
    state_path = devlyn / "pipeline.state.json"
    state = loads_strict_json(state_path.read_text(encoding="utf-8"))
    collected: dict[str, Any] = {"roles": {}, "role_evidence": {}, "executions": {}, "findings": {},
                                 "durations": {"judge": None, "pair_judge": None}, "dispatch": None}
    verify = (state.get("phases") or {}).get("verify") or {}
    if verify.get("merged") is not None:
        raise SystemExit("BLOCKED:verify-already-merged: this VERIFY round already has a merged verdict; open a new round")
    name = dispatch_name(verify.get("round"))

    def invalid(detail: object) -> dict[str, Any]:
        collected["roles"]["primary_judge"] = {"verdict": "BLOCKED", "timeout": False, "blockers": [
            judge_blocker("judge", "verify-dispatch-invalid", f"{name}: {detail}", "verify.judge.dispatch")]}
        return collected

    try:
        raw = (devlyn / name).read_bytes()
        record = loads_strict_json(raw.decode("utf-8"))
        identity = (state.get("run_id"), verify.get("round"), verify.get("started_at"),
                    ROLE_CONFIG["snapshot"](state)["sha256"])
        recorded = (record.get("run_id"), record.get("round"), record.get("verify_started_at"),
                    record.get("resolution_sha256"))
    except (OSError, UnicodeError, ValueError, KeyError, TypeError, AttributeError) as exc:
        return invalid(exc)
    # A record for another run, round or span is never published here.
    if recorded != identity:
        raise SystemExit("BLOCKED:verify-state-changed: dispatch record differs from the open VERIFY span")
    if verify.get("pre_sha"):
        seal = devlyn / "source-seal.json"
        current_seal = hashlib.sha256(seal.read_bytes()).hexdigest() if seal.is_file() else None
        if record.get("source_seal_sha256") != current_seal:
            return invalid("MECHANICAL source seal changed after the dispatch decision")
    try:
        collected["dispatch"] = seal_file(devlyn / name)
    except ValueError as exc:
        return invalid(exc)
    try:
        roles = record["roles"]
        if record.get("schema") != 1 or set(roles) != {"primary_judge", "pair_judge"} or any(
            entry.get("decision") not in {"dispatch", "skip", "blocked"} for entry in roles.values()
        ):
            raise ValueError("dispatch record is malformed")
        # Re-derive what the record may skip: a binding MECHANICAL result skips both seats,
        # and a pair skip is exactly the published ineligible trigger.
        mechanical_blocker = rank(mechanical_source(devlyn)[1]) >= 2
        trigger = record["pair_trigger"]
        pair_skipped = roles["pair_judge"]["decision"] == "skip"
        if ((roles["primary_judge"]["decision"] == "skip") != mechanical_blocker
                or (mechanical_blocker and not pair_skipped)
                or trigger.get("eligible") is pair_skipped
                or (pair_skipped and trigger.get("skipped_reason") != roles["pair_judge"].get("reason"))):
            raise ValueError("dispatch skip decisions contradict MECHANICAL or the pair trigger")
        # A pair skip must be one the frozen selection allows: a pinned pair never skips as unavailable.
        pair = ROLE_CONFIG["snapshot"](state)["roles"]["pair_judge"]
        allowed = ({"mechanical_blocker"} if mechanical_blocker else {pair["skipped_reason"]} if pair.get("skipped_reason")
                   else {"auto_pair_other_engine_unavailable"}
                   if pair.get("source") == "default" and state.get("pair_verify") is not True else set())
        if pair_skipped and roles["pair_judge"].get("reason") not in allowed:
            raise ValueError("dispatch pair skip is not allowed by the frozen pair selection")
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        return invalid(exc)  # The sealed record stays bound as the evidence of its own defect.
    verify["pair_trigger"] = record["pair_trigger"]
    state["verify"] = {**(state.get("verify") if isinstance(state.get("verify"), dict) else {}),
                       "pair_trigger": record["pair_trigger"]}
    atomic_write_text(state_path, json.dumps(state, indent=2, sort_keys=True) + "\n")
    for role in ("primary_judge", "pair_judge"):
        collected["roles"][role] = judge_seat(devlyn, state, record, role, collected)
        source = "judge" if role == "primary_judge" else "pair_judge"
        findings_path = devlyn / SOURCE_FILES[1 if source == "judge" else 2][1]
        if record["roles"][role]["decision"] == "skip":
            findings_path.unlink(missing_ok=True)  # A skipped seat has no findings, stale or not.
            continue
        atomic_write_text(findings_path, "".join(
            json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n"
            for item in collected["findings"].get(source, [])
        ))
    return collected


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


def pair_state_contract_violations(
    devlyn: pathlib.Path,
    source_verdicts: dict[str, str | None],
) -> list[dict[str, Any]]:
    """Pair routing state must be well formed and justify the pair seat's presence or absence."""
    def blocked(violation: dict[str, Any]) -> list[dict[str, Any]]:
        source_verdicts["pair_judge"] = "BLOCKED"
        return [pair_blocker(violation["id"], violation["message"], violation["file"],
                             violation.get("rule_id", "verify.pair.emission-contract"))]

    required, malformed_trigger = pair_trigger_status(devlyn)
    for violation in (
        pair_flag_contract_violation(devlyn),
        malformed_trigger,
        risk_profile_contract_violation(devlyn),
        verify_state_contract_violation(devlyn),
    ):
        if violation is not None:
            return blocked(violation)
    present = pair_trigger_present(devlyn)
    if not required and not present:
        violation = pair_trigger_missing_contract_violation(devlyn, source_verdicts)
        if violation is not None:
            return blocked(violation)
    violation = pair_trigger_skip_contract_violation(devlyn, source_verdicts)
    if violation is not None:
        return blocked(violation)
    pair_output = (devlyn / SOURCE_FILES[2][1]).is_file()
    if present and not required:
        if pair_output:
            return blocked({
                "id": "verify-pair-skipped-output-present",
                "message": "Pair state is skipped or ineligible, but pair findings exist.",
                "file": SOURCE_FILES[2][1],
                "rule_id": "verify.pair.state-capture-contradiction",
            })
        source_verdicts["pair_judge"] = None
        return []
    if required and source_verdicts["pair_judge"] is None:
        return blocked({
            "id": "verify-pair-required-output-missing",
            "message": "Pair-mode was required, but the pair-JUDGE produced no findings.",
            "file": SOURCE_FILES[2][1],
        })
    return []


def write_outputs(
    devlyn: pathlib.Path,
    findings: list[dict[str, Any]],
    source_verdicts: dict[str, str | None],
    collected: dict[str, Any] | None = None,
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
    if source_verdicts.get("pair_judge") == "TIMEOUT" and (collected or {}).get("pair_timeout"):
        summary["pair_timeout"] = collected["pair_timeout"]
        summary["report_header_note"] = "solo verdict after pair TIMEOUT"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def write_state(devlyn: pathlib.Path, summary: dict[str, Any], collected: dict[str, Any] | None = None) -> None:
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
    if verify.get("pre_sha") and (devlyn / "source-seal.json").is_file():
        verify["source_seal"] = seal_file(devlyn / "source-seal.json")
    if collected is not None:
        # Bindings were authenticated or sealed by collect_judges under this same lock.
        for field in ("role_evidence", "executions", "dispatch"):
            if collected[field]:
                verify[field] = collected[field]
        verify["judge_durations_ms"] = collected["durations"]
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
    atomic_write_text(state_path, json.dumps(state, indent=2, sort_keys=True) + "\n")


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

        # Moved from BUILD_GATE completion: the sealed outcome sets the floor even when the
        # mutable findings file is empty — a failed expectation is NEEDS_WORK, a recorded
        # capability denial (including a prohibited missing tool) is BLOCKED.
        honest_commands = PROCESS_EVIDENCE["bound_carrier_summary_commands"](failed_work, failed_carrier)
        (failed_devlyn / "spec-verify.results.json").write_text(json.dumps({
            "commands": honest_commands, "process_evidence": failed_carrier,
        }), encoding="utf-8")
        floor_findings, floor_verdicts = read_findings(failed_devlyn)
        assert floor_verdicts["mechanical"] == "NEEDS_WORK", floor_verdicts
        assert any(item.get("rule_id") == "invariant.mechanical-expectation-mismatch"
                   for item in floor_findings), floor_findings
        tool_obligation = PROCESS_EVIDENCE["normalize_obligation"]({
            "id": "required-tool", "phase": "verify", "cmd": "tsc --noEmit",
        })
        PROCESS_EVIDENCE["record_capability_denial"](
            failed_work, failed_work / failed_manifest, failed_state["run_id"], "verify", 0,
            tool_obligation, "tool", b"tsc absent; the task prohibits supplying it",
        )
        denied_carrier = PROCESS_EVIDENCE["validate_manifest"](
            failed_work, failed_manifest, failed_state["run_id"], "verify", 0,
            require_expectations=False,
        )
        (failed_devlyn / "spec-verify.results.json").write_text(json.dumps({
            "commands": PROCESS_EVIDENCE["bound_carrier_summary_commands"](failed_work, denied_carrier),
            "process_evidence": denied_carrier,
        }), encoding="utf-8")
        denied_findings, denied_verdicts = read_findings(failed_devlyn)
        assert denied_verdicts["mechanical"] == "BLOCKED", denied_verdicts
        assert any(item.get("rule_id") == "invariant.build-env-underprovisioned"
                   and "required-tool" in item.get("message", "") for item in denied_findings), denied_findings
        print("PASS sealed outcome floor: failed expectation NEEDS_WORK, tool denial BLOCKED, empty findings")

        # New runs (VERIFY opened with a writer-recorded pre_sha) review only sealed source.
        seal_work = pathlib.Path(tmp) / "seal-work"
        seal_devlyn = seal_work / ".devlyn"
        seal_devlyn.mkdir(parents=True)

        def seal_git(*args: str) -> str:
            return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=seal_work,
                                  check=True, capture_output=True, text=True, encoding="utf-8").stdout.strip()

        seal_git("init", "-q")
        (seal_work / ".gitignore").write_text(".devlyn/\n", encoding="utf-8")
        (seal_work / "a.txt").write_text("base\n", encoding="utf-8")
        seal_git("add", "-A")
        seal_git("commit", "-qm", "base")
        seal_state = {"version": "3.0", "run_id": "rs-seal-merge", "engine": "claude", "process_evidence": None,
                      "phases": {"verify": {"round": 1, "started_at": "2026-10-03T00:00:00.000Z",
                                            "completed_at": None, "verdict": None, "sub_verdicts": None,
                                            "pre_sha": seal_git("rev-parse", "HEAD")}}}
        (seal_devlyn / "pipeline.state.json").write_text(json.dumps(seal_state), encoding="utf-8")
        (seal_devlyn / "verify-mechanical.findings.jsonl").write_text("", encoding="utf-8")
        checker = runpy.run_path(str(pathlib.Path(__file__).with_name("spec-verify-check.py")))

        def write_seal(sealed: bool) -> None:
            document, digest, problems = checker["source_snapshot"](seal_work, seal_devlyn, seal_state)
            (seal_devlyn / "source-seal.json").write_text(json.dumps({
                "schema": 1, "run_id": "rs-seal-merge", "round": 1, "snapshot": document, "digest": digest,
                "problems": problems, "seal": {"digest": digest, "head": document["head"]} if sealed else None,
            }), encoding="utf-8")

        def seal_rule(findings: list[dict[str, Any]]) -> bool:
            return any(item.get("rule_id") == "invariant.mechanical-seal" for item in findings)

        missing_findings, missing = mechanical_source(seal_devlyn)
        assert missing == "BLOCKED" and seal_rule(missing_findings), missing_findings
        write_seal(False)
        unsealed_findings, unsealed = mechanical_source(seal_devlyn)
        assert unsealed == "BLOCKED" and seal_rule(unsealed_findings), unsealed_findings
        (seal_devlyn / "verify-mechanical.findings.jsonl").write_text(json.dumps({
            "id": "VERIFY-MECH-0001", "rule_id": "scope.unsealed-source", "severity": "CRITICAL",
        }) + "\n", encoding="utf-8")
        repair_findings, repair = mechanical_source(seal_devlyn)
        assert repair == "NEEDS_WORK" and not seal_rule(repair_findings), repair_findings
        (seal_devlyn / "verify-mechanical.findings.jsonl").write_text("", encoding="utf-8")
        write_seal(True)
        sealed_findings, sealed = mechanical_source(seal_devlyn)
        assert sealed == "PASS", sealed_findings
        for mutate, restore in (
            (lambda: (seal_work / "a.txt").write_text("edited after seal\n", encoding="utf-8"),
             lambda: seal_git("checkout", "--", "a.txt")),
            (lambda: (seal_work / "new.txt").write_text("residue\n", encoding="utf-8"),
             lambda: (seal_work / "new.txt").unlink()),
        ):
            mutate()
            changed_findings, changed = mechanical_source(seal_devlyn)
            assert changed == "BLOCKED" and seal_rule(changed_findings), changed_findings
            restore()
        other_round = loads_strict_json((seal_devlyn / "source-seal.json").read_text(encoding="utf-8"))
        (seal_devlyn / "source-seal.json").write_text(json.dumps({**other_round, "round": 0}), encoding="utf-8")
        stale_findings, stale = mechanical_source(seal_devlyn)
        assert stale == "BLOCKED" and seal_rule(stale_findings), stale_findings
        write_seal(True)
        (seal_devlyn / "verify.findings.jsonl").write_text("", encoding="utf-8")
        bound_findings, bound_verdicts = read_findings(seal_devlyn)
        write_state(seal_devlyn, write_outputs(seal_devlyn, bound_findings, bound_verdicts))
        seal_bound = loads_strict_json((seal_devlyn / "pipeline.state.json").read_text(encoding="utf-8"))
        assert seal_bound["phases"]["verify"]["source_seal"] == seal_file(seal_devlyn / "source-seal.json")
        print("PASS MECHANICAL seal: required, rechecked against the tree, round-bound, bound at merge")

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
        (skipped_work / "verify.pair.findings.jsonl").write_text("", encoding="utf-8")
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
        # A present dispatch record makes the frozen-selection check itself the failing step.
        (devlyn / "verify-judge.rNone.dispatch.json").write_text("{}", encoding="utf-8")
        for malformed in (None, {}, {"roles": {}}):
            bad_state = loads_strict_json(original_state)
            bad_state["phases"]["verify"].pop("merged", None)
            bad_state["role_resolution"] = malformed
            (devlyn / "pipeline.state.json").write_text(json.dumps(bad_state), encoding="utf-8")
            result = subprocess.run([sys.executable, str(pathlib.Path(__file__).resolve()),
                                     "--devlyn-dir", str(devlyn), "--write-state"], capture_output=True, text=True, encoding="utf-8")
            assert result.returncode == 0 and "Traceback" not in result.stderr, result.stderr
            persisted = loads_strict_json((devlyn / "pipeline.state.json").read_text(encoding="utf-8"))
            assert persisted["phases"]["verify"]["verdict"] == "BLOCKED"
            merged = (devlyn / "verify-merged.findings.jsonl").read_text(encoding="utf-8")
            assert "verify-dispatch-invalid" in merged and "role resolution" in merged, merged
        (devlyn / "verify-judge.rNone.dispatch.json").unlink()
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
        # Generated trivial/medium runs no longer carry a SURFACE_CLOSE prerequisite.
        (devlyn / "pipeline.state.json").write_text(json.dumps({
            "version": "3.0", "engine": "claude", "complexity": "medium",
            "source": generated_source, "phases": {},
        }), encoding="utf-8")
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
        (devlyn / "verify.pair.findings.jsonl").unlink()
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

        # Self-test: a schema-v3 trigger merges on its recorded telemetry reasons.
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

        (devlyn / "verify.pair.findings.jsonl").unlink()
        # Pair state is checked even when state is absent, incomplete, or malformed.
        (devlyn / "pipeline.state.json").unlink()
        findings, source_verdicts = read_findings(devlyn)
        assert source_verdicts["pair_judge"] == "BLOCKED", source_verdicts
        assert any(finding["id"] == "verify-state-missing" for finding in findings), findings

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
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--devlyn-dir", default=".devlyn")
    # Publication happens only through the locked, once-per-round collection.
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write-state", action="store_true")
    mode.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()

    devlyn = pathlib.Path(args.devlyn_dir)
    if not devlyn.is_dir():
        sys.stderr.write(f"error: {devlyn} is not a directory\n")
        return 1
    lock = runpy.run_path(str(pathlib.Path(__file__).with_name("platform-support.py")))["file_lock"]
    with lock(devlyn.resolve() / "pipeline.state.lock", blocking=True):
        collected = collect_judges(devlyn)
        findings, source_verdicts = read_findings(devlyn, collected)
        summary = write_outputs(devlyn, findings, source_verdicts, collected)
        write_state(devlyn, summary, collected)
        print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    runpy.run_path(str(pathlib.Path(__file__).with_name("platform-support.py")))["configure_utf8"]()
    raise SystemExit(main())
