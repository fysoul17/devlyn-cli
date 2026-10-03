#!/usr/bin/env python3
"""Deterministic spawn/complete writer for phases.<name> in pipeline.state.json.

Usage:
    python3 state-phase-write.py --devlyn-dir .devlyn --phase implement spawn \
        --round 1 --triggered-by verify [--engine claude] [--model <id>]
    python3 state-phase-write.py --devlyn-dir .devlyn --phase implement durability-enforce \
        --round 1
    python3 state-phase-write.py --devlyn-dir .devlyn --phase implement complete \
        --verdict PASS [--findings-file <path>] [--log-file <path>] \
        [--engine claude] [--model <requested-id>] [--engine-session-log <path>]
    python3 state-phase-write.py --devlyn-dir .devlyn --phase implement transition \
        --verdict PASS --next-phase verify --next-round 0 --next-engine claude

references/state-schema.md#write-protocol is the contract this implements.
A prior hand-edited fix-loop respawn left `started_at` at its original round's
value while `completed_at`/`duration_ms`/`round`/`triggered_by` advanced to the
new round, producing an internally inconsistent phase timeline. `spawn` always
resets `started_at` fresh and nulls the completion fields; `complete` derives
`duration_ms` from the phase's own recorded `started_at`, so the two can never
drift apart again.
"""
from __future__ import annotations

import argparse
import copy
import datetime
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import runpy
import shutil
import subprocess
import sys
import tempfile

VALID_VERDICTS = {"PASS", "PASS_WITH_ISSUES", "FAIL", "NEEDS_WORK", "BLOCKED"}
FINAL_VERDICTS = {"PASS", "PASS_WITH_ISSUES", "NEEDS_WORK", "BLOCKED"}
VALID_TRIGGERS = {"verify"}
SPAWN_TRIGGERS = VALID_TRIGGERS | {"plan"}
PHASE_NAMES = {"plan", "probe_derive", "implement", "verify", "final_report"}
# Worker phases (PROBE_DERIVE, IMPLEMENT) open only by complete → render → standalone spawn.
LEGAL_TRANSITIONS = {
    "plan": {"final_report"},
    "probe_derive": {"final_report"},
    "implement": {"verify", "final_report"},
    "verify": {"final_report"},
    "final_report": set(),
}
WORKER_SESSION_ARTIFACT_PHASES = {"plan": "plan", "implement": "implement"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PLAN_MAX_DISPATCHES = 2
PHASE_HEADING_RE = re.compile(r"^###[ \t]+Phase[ \t]+[0-9]+")
FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
PLAN_SPAWN_RECEIPT_FIELDS = (
    "round", "started_at", "triggered_by", "engine", "model_requested", "prompt_sha256",
)
PLAN_COMPLETION_RECEIPT_FIELDS = (
    "completed_at", "duration_ms", "verdict", "model_effective", "output_sha256",
)
PLAN_RECEIPT_FIELDS = PLAN_SPAWN_RECEIPT_FIELDS + PLAN_COMPLETION_RECEIPT_FIELDS
_PROCESS_EVIDENCE_MODULE = None
_INVOCATION_RECEIPT_MODULE = None


def reject_json_constant(token: str) -> None:
    raise ValueError(f"invalid JSON numeric constant: {token}")


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def loads_strict_json(text: str):
    return json.loads(
        text,
        parse_constant=reject_json_constant,
        object_pairs_hook=reject_duplicate_keys,
    )


def now_ms() -> datetime.datetime:
    # Truncate to millisecond precision at capture time — now_iso()'s string
    # representation is millisecond-precise, so any duration_ms computed from
    # a not-yet-truncated `now` can be off by a sub-millisecond rounding
    # remainder from what re-parsing the stored completed_at would give.
    dt = datetime.datetime.now(datetime.timezone.utc)
    return dt.replace(microsecond=(dt.microsecond // 1000) * 1000)


def now_iso(dt: datetime.datetime | None = None) -> str:
    dt = dt or now_ms()
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def parse_iso(value: str) -> datetime.datetime:
    text = value[:-1] if value.endswith("Z") else value
    if "." in text:
        head, frac = text.split(".", 1)
        text = f"{head}.{(frac + '000000')[:6]}"
    return datetime.datetime.fromisoformat(text).replace(tzinfo=datetime.timezone.utc)


def read_state(state_path: pathlib.Path) -> dict:
    if not state_path.is_file():
        raise SystemExit(f"error: {state_path} not found")
    try:
        return loads_strict_json(state_path.read_text(encoding="utf-8"))
    except ValueError as e:
        raise SystemExit(f"error: {state_path} is not valid JSON: {e}")


def write_state(state_path: pathlib.Path, state: dict) -> None:
    fd, tmp_name = tempfile.mkstemp(dir=str(state_path.parent), prefix=state_path.name + ".tmp.")
    try:
        with open(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(state, indent=2, sort_keys=True) + "\n")
        pathlib.Path(tmp_name).replace(state_path)
    except BaseException:
        pathlib.Path(tmp_name).unlink(missing_ok=True)
        raise


def plan_output_error(state: dict, devlyn: pathlib.Path | None, phase: str) -> str | None:
    """Why the completed PLAN's bound output no longer verifies, or None."""
    plan = (state.get("phases") or {}).get("plan")
    if not isinstance(plan, dict) or plan.get("completed_at") is None:
        return None
    expected = plan.get("output_sha256")
    if expected is None and state.get("version") != "3.0":
        return None
    if (
        expected is None and "output_sha256" in plan and plan.get("verdict") == "BLOCKED"
        and devlyn is not None and not os.path.lexists(devlyn / "plan.md")
    ):
        return None if phase == "final_report" else "BLOCKED:plan-output-missing: only final_report is allowed"
    if not isinstance(expected, str) or SHA256_RE.fullmatch(expected) is None:
        return "BLOCKED:plan-integrity-invalid: phases.plan.output_sha256 is missing"
    if devlyn is None:
        return "BLOCKED:plan-integrity-invalid: .devlyn is required to rehash PLAN output"
    plan_path = devlyn / "plan.md"
    try:
        actual = hashlib.sha256(plan_path.read_bytes()).hexdigest()
    except OSError as exc:
        return f"BLOCKED:plan-integrity-invalid: cannot read {plan_path}: {exc}"
    if actual != expected:
        return f"BLOCKED:plan-integrity-mismatch: expected={expected} actual={actual} path={plan_path}"
    return None


def validate_plan_output(state: dict, devlyn: pathlib.Path | None, phase: str) -> None:
    """Work phases refuse a PLAN output that no longer verifies; FINAL_REPORT records it as its verdict."""
    error = plan_output_error(state, devlyn, phase)
    if error is not None and phase != "final_report":
        raise SystemExit(error)


def bind_plan_output(state: dict, devlyn: pathlib.Path | None) -> None:
    if devlyn is None:
        raise SystemExit("BLOCKED:plan-integrity-invalid: .devlyn is required to bind PLAN output")
    plan_path = devlyn / "plan.md"
    plan = state["phases"]["plan"]
    if (
        plan.get("verdict") == "BLOCKED" and plan.get("output_sha256") is None
        and not os.path.lexists(plan_path)
    ):
        digest = None
    else:
        try:
            digest = hashlib.sha256(plan_path.read_bytes()).hexdigest()
        except OSError as exc:
            raise SystemExit(f"BLOCKED:plan-integrity-invalid: cannot read {plan_path}: {exc}") from exc
    plan["output_sha256"] = digest


def final_report_digest(state: dict, devlyn: pathlib.Path | None, log_file: str | None) -> str:
    try:
        if devlyn is None or not log_file:
            raise ValueError("--log-file must name .devlyn/final-report.md")
        path = devlyn / "final-report.md"
        supplied = pathlib.Path(log_file)
        if supplied.parent.resolve() / supplied.name != devlyn.resolve() / path.name:
            raise ValueError("--log-file must name the canonical final-report.md")
        if path.is_symlink() or not path.is_file():
            raise ValueError("final-report.md must be a nonsymlink regular file")
        raw = path.read_bytes()
        lines = raw.decode("utf-8").splitlines()
        run_id = state.get("run_id")
        prefix = "<!-- devlyn:final-report run_id="
        if (
            not isinstance(run_id, str) or not run_id or not lines
            or lines[0] != f"{prefix}{run_id} -->"
            or sum(line.startswith(prefix) for line in lines) != 1
        ):
            raise ValueError("first line must uniquely identify the current state.run_id")
        if not any(line.strip() for line in lines[1:]):
            raise ValueError("final-report.md body must not be empty")
        return hashlib.sha256(raw).hexdigest()
    except (OSError, UnicodeError, ValueError) as exc:
        raise SystemExit(f"BLOCKED:final-report-invalid: {exc}") from exc


# Reasons only evidence can establish; a caller cannot supply them.
EVIDENCE_ONLY_REASONS = {"finish-gate-unclean", "build-env-underprovisioned", "repair-budget-exhausted"}
SKIPS_MARKER = "<!-- devlyn:mechanical-skips -->"
REPORT_PHASES = ("plan", "probe_derive", "implement", "verify")


def report_invalid(detail: str) -> SystemExit:
    return SystemExit(f"BLOCKED:final-report-invalid: {detail}")


def read_regular(path: pathlib.Path, label: str) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise report_invalid(f"{label} must be a nonsymlink regular file: {path.name}")
    return path.read_bytes()


def read_jsonl(path: pathlib.Path) -> list[dict]:
    if not path.exists() and not path.is_symlink():
        return []
    items = []
    for line in read_regular(path, "findings").decode("utf-8").splitlines():
        if line.strip():
            item = loads_strict_json(line)
            if not isinstance(item, dict):
                raise report_invalid(f"{path.name} has a non-object finding")
            items.append(item)
    return items


def bound_dispatch_roles(verify: dict, devlyn: pathlib.Path) -> dict:
    """Return the seat decisions of this round's state-bound dispatch record, rehashed."""
    binding = verify.get("dispatch")
    if binding is None:
        return {}
    expected = f".devlyn/verify-judge.r{verify.get('round')}.dispatch.json"
    if not isinstance(binding, dict) or binding.get("path") != expected:
        raise report_invalid("VERIFY dispatch binding is malformed")
    raw = read_regular(devlyn / pathlib.Path(expected).name, "VERIFY dispatch record")
    if hashlib.sha256(raw).hexdigest() != binding.get("sha256"):
        raise report_invalid("VERIFY dispatch record differs from its state binding")
    # The merge checked this record's run/round identity when it bound these exact bytes.
    record = loads_strict_json(raw.decode("utf-8"))
    roles = record.get("roles") if isinstance(record, dict) else None
    return {role: entry for role, entry in roles.items() if isinstance(entry, dict)} if isinstance(roles, dict) else {}


def verify_blocked_reason(state: dict, devlyn: pathlib.Path, work: pathlib.Path) -> str | None:
    """Derive a VERIFY BLOCKED reason from this round's state-bound evidence, rehashed."""
    verify = state["phases"]["verify"]
    carrier = next((item for item in state.get("process_evidence") or []
                    if isinstance(item, dict) and item.get("phase") == "verify"
                    and item.get("round") == verify.get("round")), None)
    if carrier is not None:
        module = process_evidence_module()
        try:
            outcome = module.bound_carrier_outcome(work, carrier)
        except module.EvidenceError as exc:
            raise report_invalid(f"bound VERIFY evidence: {exc}") from exc
        if outcome["verdict"] == "BLOCKED":
            return "BLOCKED:build-env-underprovisioned"
    roles = bound_dispatch_roles(verify, devlyn)
    for role in ("primary_judge", "pair_judge"):
        entry = roles.get(role) or {}
        reason = entry.get("reason") if entry.get("decision") == "blocked" else None
        if isinstance(reason, str) and reason.startswith("BLOCKED:") and len(reason) > 8:
            return reason.split(": ", 1)[0]
    return None


def terminal_verdict(state: dict, devlyn: pathlib.Path, work: pathlib.Path, supplied: str | None) -> str:
    """PHASE 6 precedence: bound PLAN, finish gate, BLOCKED phase, repair exhaustion, verify-only, VERIFY."""
    phases = state.get("phases") or {}
    plan_broken = plan_output_error(state, devlyn, "final_report") is not None
    if plan_broken:
        finish = {"exit": 0}  # a PLAN that no longer verifies decides; its surface cannot vouch for the gate
    else:
        try:
            finish = loads_strict_json(read_regular(devlyn / "finish-gate.summary.json", "finish-gate summary").decode("utf-8"))
        except SystemExit:
            raise report_invalid("run finish-gate.py before completing the final report") from None
        if not isinstance(finish, dict) or type(finish.get("exit")) is not int or finish["exit"] not in (0, 1, 2):
            raise report_invalid("finish-gate summary has no valid exit")
    blocked = [name for name in REPORT_PHASES
               if isinstance(phases.get(name), dict) and phases[name].get("verdict") == "BLOCKED"]
    implement = phases.get("implement")
    derived = None
    if plan_broken:
        derived = "BLOCKED:phase-input-invalid"
    # Before IMPLEMENT there is no product change; a malformed gate (no usable PLAN surface) then
    # does not displace the halt's own reason, while offenders (exit 2) always decide.
    elif finish["exit"] == 2 or (finish["exit"] == 1 and isinstance(implement, dict) and implement.get("started_at")):
        derived = "BLOCKED:finish-gate-unclean"
    elif blocked:
        derived = verify_blocked_reason(state, devlyn, work) if "verify" in blocked else None
    else:
        origin = exhausted_origin(state) if state.get("mode") != "verify-only" else None
        rounds = state.get("rounds") or {}
        if origin is not None:
            if type(rounds.get("global")) is int and rounds.get("global") == rounds.get("max_rounds"):
                derived = "NEEDS_WORK" if origin == "verify" else "BLOCKED:repair-budget-exhausted"
            elif supplied is None:
                raise report_invalid(f"{origin} repair budget remains; request repair admission or pass the halt reason")
        else:
            predecessor = repair_predecessor(state)
            verify = phases.get("verify")
            if (predecessor is not None and predecessor[0] == "verify" and verify.get("completed_at")
                    and (verify.get("verdict") in {"PASS", "PASS_WITH_ISSUES"}
                         or (state.get("mode") == "verify-only" and verify.get("verdict") == "NEEDS_WORK"))):
                derived = verify["verdict"]
    if derived is not None:
        if supplied is not None and supplied != derived:
            raise report_invalid(f"supplied {supplied} contradicts the evidence-derived {derived}")
        return derived
    if supplied is None:
        raise report_invalid("this halt is not represented in state; pass --verdict BLOCKED:<reason>")
    label = supplied.removeprefix("BLOCKED:").split(":", 1)[0].strip()
    if not supplied.startswith("BLOCKED:") or not label or label in EVIDENCE_ONLY_REASONS:
        raise report_invalid(f"supplied {supplied} is not supported by the recorded evidence")
    return supplied


def mechanical_skips(state: dict, devlyn: pathlib.Path) -> list[dict]:
    """Read this VERIFY round's marked skip block from mechanical.log.md, if any."""
    verify = (state.get("phases") or {}).get("verify")
    path = devlyn / "mechanical.log.md"
    if not isinstance(verify, dict) or (not path.exists() and not path.is_symlink()):
        return []
    lines = read_regular(path, "MECHANICAL log").decode("utf-8").splitlines()
    current = []
    for index, line in enumerate(lines):
        if line.strip() != SKIPS_MARKER:
            continue
        try:
            end = lines.index("```", index + 2)
            if lines[index + 1].strip() != "```json":
                raise ValueError("marker must precede a ```json block")
            block = loads_strict_json("\n".join(lines[index + 2:end]))
            if not isinstance(block, dict) or set(block) != {"run_id", "round", "skips"} or not isinstance(block["skips"], list):
                raise ValueError("block must be {run_id, round, skips}")
            for skip in block["skips"]:
                if (not isinstance(skip, dict) or set(skip) != {"gate", "reason"}
                        or not all(isinstance(v, str) and v.strip() for v in skip.values())):
                    raise ValueError("each skip must be {gate, reason} with nonempty strings")
        except (IndexError, ValueError) as exc:
            raise report_invalid(f"mechanical.log.md skip block at line {index + 1}: {exc}") from exc
        if (block["run_id"], block["round"]) == (state.get("run_id"), verify.get("round")):
            current.append(block)
    if len(current) > 1:
        raise report_invalid("mechanical.log.md has more than one skip block for this VERIFY round")
    return current[0]["skips"] if current else []


def cell(value: object) -> str:
    return "-" if value is None else str(value).replace("|", "\\|").replace("\n", " ")


def render_final_report(state: dict, devlyn: pathlib.Path, work: pathlib.Path, verdict: str,
                        detail: str | None) -> str:
    phases = state.get("phases") or {}
    verify = phases.get("verify") if isinstance(phases.get("verify"), dict) else {}
    predecessor = repair_predecessor(state)
    current_verify = predecessor is not None and predecessor[0] == "verify"
    merged = verify.get("merged") if current_verify else None
    notes = []

    def displayed(path: pathlib.Path, required: bool) -> list[dict]:
        # Findings are report text only; an unreadable file is shown, never a reason to withhold the report.
        if required and not os.path.lexists(path):
            notes.append(f"- {path.name} is missing")
            return []
        try:
            return read_jsonl(path)
        except (SystemExit, OSError, ValueError, UnicodeError) as exc:
            notes.append(f"- {path.name} unreadable: {exc}")
            return []

    findings = displayed(devlyn / "verify-merged.findings.jsonl", True) if isinstance(merged, dict) else []
    finish_findings = displayed(devlyn / "finish-gate.findings.jsonl", False)
    skips = mechanical_skips(state, devlyn) if current_verify else []
    started = state.get("started_at")
    wall = round((now_ms() - parse_iso(started)).total_seconds()) if isinstance(started, str) else None
    out = [f"<!-- devlyn:final-report run_id={state.get('run_id')} -->", "# devlyn-resolve final report", "",
           "| run_id | engine | mode | complexity | verdict | wall_time_s |", "|---|---|---|---|---|---|",
           "| " + " | ".join(cell(v) for v in (state.get("run_id"), state.get("engine"), state.get("mode"),
                                               state.get("complexity"), verdict, wall)) + " |", "",
           "## Phases", "", "| phase | verdict | duration_ms | round | triggered_by | findings_count | note |",
           "|---|---|---|---|---|---|---|"]
    for name in REPORT_PHASES:
        entry = phases.get(name)
        if not isinstance(entry, dict) or entry.get("started_at") is None:
            continue
        note = {"plan": "owner context",
                "verify": "MECHANICAL: orchestrator commands, no separate model"}.get(name, entry.get("engine"))
        if name == "implement" and valid_phase_gate_progress(entry.get("exec")):
            passed = sum(status == "PASS" for status in entry["exec"]["statuses"])
            note = f"{note}; {passed}/{entry['exec']['total']} phases passed"
        if name == "verify" and skips:
            note += "; skipped: " + ", ".join(f"{s['gate']} ({s['reason']})" for s in skips)
        count = len(findings) if name == "verify" and isinstance(merged, dict) else None
        out.append("| " + " | ".join(cell(v) for v in (name, entry.get("verdict"), entry.get("duration_ms"),
                                                        entry.get("round"), entry.get("triggered_by"), count, note)) + " |")
    profile = state.get("risk_profile") or {}
    seat = bound_dispatch_roles(verify, devlyn).get("pair_judge") if current_verify else None
    pair_status = ("not reached" if seat is None else "on" if seat.get("decision") == "dispatch"
                   else f"{seat.get('decision')}: {seat.get('reason')}")
    out += ["", "## Pair and risk probes", "", f"- pair: {pair_status}",
            "- risk_probes: " + ("on" if profile.get("risk_probes_enabled") else "off")
            + (f" ({'; '.join(profile['reasons'])})" if profile.get("reasons") else "")]
    out += ["", "## Findings", ""]
    rows = [("verify", f) for f in findings] + [("finish-gate", f) for f in finish_findings]
    if rows:
        out += ["| source | severity | rule_id | file:line | message | confidence |", "|---|---|---|---|---|---|"]
        out += ["| " + " | ".join(cell(v) for v in (source, f.get("severity"), f.get("rule_id"),
                                                    f"{f.get('file')}:{f.get('line')}", f.get("message"),
                                                    f.get("confidence"))) + " |" for source, f in rows]
    else:
        out.append("None.")
    plan_error = plan_output_error(state, devlyn, "final_report")
    if plan_error is not None:
        notes.append(f"- bound PLAN no longer verifies: {plan_error}")
    if state.get("complexity") == "large":
        try:
            criteria = read_regular(devlyn / "criteria.generated.md", "generated criteria")
        except (SystemExit, OSError) as exc:
            criteria = None
            notes.append(f"- generated criteria unavailable ({exc}); assumptions omitted")
        if criteria is None:
            pass
        elif hashlib.sha256(criteria).hexdigest() != (state.get("source") or {}).get("criteria_sha256"):
            notes.append("- generated criteria changed after freeze; assumptions omitted")
        else:
            text = criteria.decode("utf-8").splitlines()
            start = next((i for i, line in enumerate(text) if line.strip() == "## Assumptions"), None)
            if start is not None:
                end = next((i for i in range(start + 1, len(text)) if text[i].startswith("## ")), len(text))
                notes += ["Assumptions for user review (recommend: /devlyn-ideate first):", *text[start + 1:end]]
    if current_verify and (verify.get("sub_verdicts") or {}).get("pair_judge") == "TIMEOUT":
        notes.append("- solo verdict after pair TIMEOUT")
    if profile.get("pair_default_enabled") is False:
        notes.append("- opt-out: --no-pair")
    if profile.get("risk_probes_explicit") and not profile.get("risk_probes_enabled"):
        notes.append("- opt-out: --no-risk-probes")
    if verdict.startswith("BLOCKED:") and verdict.endswith("-unavailable"):
        engine = verdict.removeprefix("BLOCKED:").removesuffix("-unavailable")
        if (pathlib.Path(__file__).with_name("adapters") / f"{engine}.md").is_file():
            notes.append(f"- setup: install and authenticate {engine}, then rerun")
    if detail:
        notes.append(f"- detail: {detail}")
    if notes:
        out += ["", "## Follow-up", "", *notes]
    return "\n".join(out) + "\n"


def write_final_report(state: dict, devlyn: pathlib.Path, work: pathlib.Path, supplied: str | None,
                       detail: str | None) -> tuple[str, str]:
    """Derive the terminal verdict, render the report and return (verdict, digest)."""
    path = devlyn / "final-report.md"
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise report_invalid("existing final-report.md is not a regular file; nothing was replaced")
    if not isinstance(state.get("run_id"), str) or not state["run_id"]:
        raise report_invalid("state.run_id is required for the report marker")
    verdict = terminal_verdict(state, devlyn, work, supplied)
    text = render_final_report(state, devlyn, work, verdict, detail)
    with tempfile.NamedTemporaryFile("wb", dir=devlyn, delete=False, suffix=".tmp") as handle:
        handle.write(text.encode("utf-8"))
    os.replace(handle.name, path)
    return verdict, final_report_digest(state, devlyn, str(path))


def process_evidence_module():
    global _PROCESS_EVIDENCE_MODULE
    if _PROCESS_EVIDENCE_MODULE is None:
        module_path = pathlib.Path(__file__).with_name("process-evidence.py")
        spec = importlib.util.spec_from_file_location("devlyn_process_evidence", module_path)
        if spec is None or spec.loader is None:
            raise SystemExit(f"BLOCKED:process-evidence-invalid: cannot load {module_path}")
        module = importlib.util.module_from_spec(spec)
        previous_bytecode_setting = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            spec.loader.exec_module(module)
        finally:
            sys.dont_write_bytecode = previous_bytecode_setting
        _PROCESS_EVIDENCE_MODULE = module
    return _PROCESS_EVIDENCE_MODULE


def invocation_receipt_module():
    global _INVOCATION_RECEIPT_MODULE
    if _INVOCATION_RECEIPT_MODULE is None:
        module_path = pathlib.Path(__file__).with_name("invocation-receipt.py")
        spec = importlib.util.spec_from_file_location("devlyn_invocation_receipt", module_path)
        if spec is None or spec.loader is None:
            raise SystemExit(f"BLOCKED:invocation-receipt-invalid: cannot load {module_path}")
        module = importlib.util.module_from_spec(spec)
        previous_bytecode_setting = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            spec.loader.exec_module(module)
        finally:
            sys.dont_write_bytecode = previous_bytecode_setting
        _INVOCATION_RECEIPT_MODULE = module
    return _INVOCATION_RECEIPT_MODULE


def execution_phase_count(plan_bytes: bytes) -> int:
    """Count `### Phase <k>` headings under `## Execution phases`, outside fenced examples."""
    count, in_section, fence = 0, False, None
    for line in plan_bytes.decode("utf-8", "replace").splitlines():
        match = FENCE_RE.match(line)
        if fence is not None:
            # A fence closes only with the same character, at least as long, and nothing after it.
            if match and match.group(1)[0] == fence[0] and len(match.group(1)) >= len(fence) and not line[match.end():].strip():
                fence = None
        elif match:
            fence = match.group(1)
        elif line.startswith("## "):
            in_section = line[3:].strip() == "Execution phases"
        elif in_section and PHASE_HEADING_RE.match(line):
            count += 1
    return count


def bind_risk_probes(state: dict, devlyn: pathlib.Path | None, work: pathlib.Path | None) -> None:
    """A passing PROBE_DERIVE validates its artifact and binds the probe digest under the lock."""
    if devlyn is None or work is None:
        raise SystemExit("BLOCKED:probe-derive-malformed: the worktree is required to validate probes")
    checker = pathlib.Path(__file__).with_name("spec-verify-check.py")
    proc = subprocess.run([sys.executable, str(checker), "--validate-risk-probes"], cwd=work,
                          capture_output=True, text=True, encoding="utf-8", check=False)
    if proc.returncode != 0:
        raise SystemExit("BLOCKED:probe-derive-malformed: " + (proc.stderr.strip() or f"exit {proc.returncode}"))
    digest, error = runpy.run_path(str(checker))["risk_probes_digest"](devlyn)
    if error:
        raise SystemExit(f"BLOCKED:probe-derive-malformed: {error}")
    state["risk_probes_digest"] = digest


def bind_process_evidence(
    state: dict, phase: str, verdict: str | None,
    devlyn: pathlib.Path | None, work: pathlib.Path | None,
) -> None:
    if phase != "implement" or verdict not in {"PASS", "PASS_WITH_ISSUES"}:
        return
    source = state.get("source")
    if work is None or devlyn is None:
        if isinstance(source, dict) and source.get("type") == "spec":
            raise SystemExit(
                "BLOCKED:process-evidence-invalid: worktree is required for spec evidence validation"
            )
        state.setdefault("process_evidence", None)
        return
    runner = process_evidence_module()
    try:
        obligations = runner.declared_obligations(work, state, phase)
        if not obligations:
            state.setdefault("process_evidence", None)
            return
        carrier = runner.validate_manifest(
            work, runner.manifest_relative_path(state, phase), state.get("run_id"),
            phase, runner.phase_round(state, phase), obligations,
        )
    except (runner.EvidenceError, OSError, UnicodeError, ValueError) as exc:
        raise SystemExit(f"BLOCKED:process-evidence-invalid: {exc}") from exc
    existing = state.get("process_evidence")
    if existing is None:
        existing = []
    if not isinstance(existing, list):
        raise SystemExit("BLOCKED:process-evidence-invalid: state.process_evidence must be null or an array")
    try:
        for prior in existing:
            runner.validate_bound_carrier(work, prior)
    except (runner.EvidenceError, OSError, UnicodeError, ValueError) as exc:
        raise SystemExit(f"BLOCKED:process-evidence-invalid: {exc}") from exc
    if any(
        isinstance(item, dict)
        and item.get("phase") == carrier["phase"]
        and item.get("round") == carrier["round"]
        for item in existing
    ):
        raise SystemExit(
            "BLOCKED:process-evidence-invalid: duplicate state carrier for "
            f"{phase} round {carrier['round']}"
        )
    state["process_evidence"] = [*existing, carrier]


CLAUDE_USAGE_COUNTERS = (
    ("input_tokens", "inputTokens"),
    ("output_tokens", "outputTokens"),
    ("cache_read_input_tokens", "cacheReadInputTokens"),
    ("cache_creation_input_tokens", "cacheCreationInputTokens"),
)


def select_claude_primary_model(evidence: dict) -> str:
    model_usage = evidence.get("modelUsage")
    models = (
        [model for model in model_usage if isinstance(model, str) and model]
        if isinstance(model_usage, dict)
        else []
    )
    if len(models) == 1:
        return models[0]
    if not models:
        raise ValueError("Claude JSON wrapper has no effective-model evidence")

    usage = evidence.get("usage")
    if not isinstance(usage, dict):
        raise ValueError("multi-entry Claude JSON wrapper has malformed top-level usage")

    def counters(container: dict, fields: tuple[str, ...]) -> tuple[int, ...]:
        values = tuple(container.get(field) for field in fields)
        if any(
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < 0
            for value in values
        ):
            raise ValueError("multi-entry Claude JSON wrapper has malformed usage counters")
        return values

    primary_usage = counters(
        usage, tuple(field[0] for field in CLAUDE_USAGE_COUNTERS)
    )
    matches = []
    for model in models:
        entry = model_usage[model]
        if not isinstance(entry, dict):
            raise ValueError("multi-entry Claude JSON wrapper has malformed modelUsage entry")
        if counters(
            entry, tuple(field[1] for field in CLAUDE_USAGE_COUNTERS)
        ) == primary_usage:
            matches.append(model)
    if len(matches) == 1:
        return matches[0]
    raise ValueError(
        "multi-entry Claude JSON wrapper has no unique primary usage match"
    )


def parse_effective_model(session_log: pathlib.Path) -> str:
    try:
        text = session_log.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"cannot read engine session log {session_log}: {exc}") from exc

    models: set[str] = set()
    if session_log.suffix == ".jsonl":
        for line_number, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                event = loads_strict_json(line)
            except ValueError as exc:
                raise ValueError(
                    f"engine session log {session_log} has malformed JSONL at line {line_number}: {exc}"
                ) from exc
            if not isinstance(event, dict) or event.get("type") != "turn_context":
                continue
            payload = event.get("payload")
            model = payload.get("model") if isinstance(payload, dict) else None
            if isinstance(model, str) and model:
                models.add(model)
    else:
        try:
            evidence = loads_strict_json(text)
        except ValueError:
            evidence = None
        if isinstance(evidence, dict) and isinstance(evidence.get("modelUsage"), dict):
            return select_claude_primary_model(evidence)

    if len(models) == 1:
        return next(iter(models))
    if not models:
        raise ValueError(f"engine session log {session_log} has no effective-model evidence")
    raise ValueError(
        f"engine session log {session_log} has conflicting effective models: {sorted(models)}"
    )


def _git_text(work: pathlib.Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=work, capture_output=True, text=True,
                          encoding="utf-8", check=False)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip() or f"exit {proc.returncode}"
        raise SystemExit(f"BLOCKED:repair-checkpoint: git {args[0]} failed: {detail}")
    return proc.stdout.strip()


def repair_checkpoint(work: pathlib.Path, devlyn: pathlib.Path, round_: int) -> dict:
    """The fix checkpoint a VERIFY-origin repair round must leave before fresh VERIFY."""
    if _git_text(work, "status", "--porcelain", "--untracked-files=no", "--", ".", ":(exclude).devlyn"):
        raise SystemExit("BLOCKED:repair-checkpoint: tracked worktree/index is not clean")
    fix = _git_text(work, "rev-parse", "HEAD")
    subject = _git_text(work, "show", "-s", "--format=%s", fix)
    if subject != f"chore(pipeline): implement fix round {round_}":
        raise SystemExit(f"BLOCKED:repair-checkpoint: expected fix checkpoint round {round_}, got {subject!r}")
    findings = devlyn / "verify-merged.findings.jsonl"
    try:
        findings_sha = hashlib.sha256(findings.read_bytes()).hexdigest()
    except OSError as exc:
        raise SystemExit(f"BLOCKED:repair-checkpoint: {findings}: {exc}") from exc
    return {"round": round_, "origin_phase": "verify", "triggering_findings_sha256": findings_sha,
            "pre_fix_sha": _git_text(work, "rev-parse", f"{fix}^"), "fix_commit_sha": fix}


def checkpoint_ledger(state: dict) -> list:
    implement = (state.get("phases") or {}).get("implement")
    ledger = implement.setdefault("durability", []) if isinstance(implement, dict) else None
    if not isinstance(ledger, list) or any(not isinstance(item, dict) for item in ledger):
        raise SystemExit("BLOCKED:repair-checkpoint: phases.implement.durability is malformed")
    return ledger


def record_repair_checkpoint(work: pathlib.Path, devlyn: pathlib.Path, state: dict, round_: int) -> dict:
    ledger = checkpoint_ledger(state)
    receipt = repair_checkpoint(work, devlyn, round_)
    existing = [item for item in ledger if item.get("round") == round_]
    if existing and existing != [receipt]:
        raise SystemExit(f"BLOCKED:repair-checkpoint: round {round_} already has a different checkpoint")
    if not existing:
        ledger.append(receipt)
    return receipt


def enforce_repair_checkpoint(work: pathlib.Path, devlyn: pathlib.Path, state: dict, round_: int) -> None:
    matches = [item for item in checkpoint_ledger(state) if item.get("round") == round_]
    if len(matches) != 1:
        raise SystemExit(f"BLOCKED:repair-checkpoint: round {round_} checkpoint receipt is missing")
    if matches[0] != repair_checkpoint(work, devlyn, round_):
        raise SystemExit(f"BLOCKED:repair-checkpoint: round {round_} checkpoint no longer matches the tree")


def clear_verify_round_artifacts(devlyn: pathlib.Path) -> None:
    # The per-round reset contract covers files, not just JSON fields: a
    # VERIFY fix-loop respawn reuses the same .devlyn, so a prior round's
    # findings/stdout would otherwise read as current-round spawn evidence in
    # verify-merge-findings.py (iter-0060 R0 finding).
    # verify*.jsonl (not just *.findings.jsonl): judge-specific files like
    # verify.findings.judge-codex.jsonl end in .judge-<engine>.jsonl.
    # The judge suffixes cover harness-owned stdout/stderr captures and the
    # collector-written pair-judge.summary.json, without matching prompts.
    for pattern in ("verify*.jsonl", "*-judge.stdout", "*-judge.stderr", "*-judge.summary.json"):
        for path in devlyn.glob(pattern):
            path.unlink()
    for name in ("verify-merge.summary.json", "source-seal.json", "spec-verify.results.json"):
        (devlyn / name).unlink(missing_ok=True)


def is_plan_dispatch_receipt(entry: dict) -> bool:
    return all(field in entry for field in PLAN_RECEIPT_FIELDS)


OWNER_EXECUTION = {"plan": "orchestrator_context"}


def orchestrator_phase(entry: dict | None, phase: str) -> bool:
    if not isinstance(entry, dict) or "execution_kind" not in entry:
        return False
    if entry["execution_kind"] != OWNER_EXECUTION[phase]:
        raise SystemExit(f"error: phases.{phase}.execution_kind is invalid")
    return True


def validate_owner_identity(devlyn, phase, round_, engine=None, model=None,
                            prompt_sha256=None, engine_session_log=None, entry=None) -> None:
    if any(value is not None for value in (engine, model, prompt_sha256, engine_session_log)):
        raise SystemExit(f"error: orchestrator {phase} cannot claim worker identity or session")
    if entry is not None and (
        any(entry.get(field) is not None for field in ("engine", "model_requested", "model_effective"))
        or any(field in entry for field in ("model", "prompt_sha256", "invocation_receipt", "role_argv", "role_evidence"))
    ):
        raise SystemExit(f"error: orchestrator {phase} contains worker identity")
    if devlyn is not None:
        for name in (f"{phase}.prompt.{round_}", f"{phase}.worker-session.{round_}.jsonl",
                     f"{phase}.invocation.{round_}.json", f"{phase}.argv.{round_}.json"):
            if os.path.lexists(devlyn / name):
                raise SystemExit(f"error: orchestrator {phase} has current-round worker evidence: {name}")


def append_phase_history(entry: dict, phase: str) -> None:
    if entry.get("started_at") is None:
        return
    history = entry.get("history")
    if not isinstance(history, list):
        history = []
    if phase == "plan" and is_plan_dispatch_receipt(entry):
        fields = PLAN_RECEIPT_FIELDS + (
            ("invocation_receipt",) if "invocation_receipt" in entry else ()
        )
    elif phase in OWNER_EXECUTION and "execution_kind" in entry:
        fields = tuple(field for field in (
            "started_at", "verdict", "completed_at", "duration_ms", "round", "triggered_by",
            "execution_kind", "engine", "model", "model_requested", "model_effective", "prompt_sha256",
            "invocation_receipt", "role_argv", "artifacts", "output_sha256",
        ) if field in entry)
    elif phase in WORKER_SESSION_ARTIFACT_PHASES and "invocation_receipt" in entry:
        fields = (
            "started_at", "verdict", "completed_at", "duration_ms",
            "invocation_receipt",
        ) + (("role_argv",) if "role_argv" in entry else ())
    elif phase == "verify":
        fields = ("started_at", "verdict", "completed_at", "duration_ms", "round", "engine", "pre_sha", "role_evidence",
                  "executions", "dispatch", "pair_trigger", "judge_durations_ms", "sub_verdicts", "merged")
    else:
        fields = ("started_at", "verdict", "completed_at", "duration_ms")
    history.append({field: entry.get(field) for field in fields})
    entry["history"] = history


def role_config_module():
    return runpy.run_path(pathlib.Path(__file__).with_name("role-config.py"))


def bind_worker_role_argv(state, phase, entry, devlyn, receipt):
    if phase != "implement":
        return None
    helper = role_config_module()
    resolution = helper["snapshot"](state)
    effort = resolution["roles"]["worker"]["effort_requested"] if resolution else None
    if effort is None:
        return None
    path = devlyn / f"{phase}.argv.{entry['round']}.json"
    if path.is_symlink() or not path.is_file():
        raise ValueError("explicit worker effort requires the retained native argv array")
    raw = path.read_bytes()
    argv = helper["loads"](raw)
    if not isinstance(argv, list) or any(not isinstance(arg, str) for arg in argv):
        raise ValueError("worker argv must be an array of strings")
    if hashlib.sha256(json.dumps(argv, separators=(",", ":")).encode()).hexdigest() != receipt["argv_sha256"]:
        raise ValueError("worker argv differs from the actual invocation receipt")
    values = [argv[i + 1] for i, arg in enumerate(argv[:-1]) if arg in {"-c", "--config"}]
    efforts = [value.split("=", 1)[1].strip('"') for value in values if value.startswith("model_reasoning_effort=")]
    if efforts != [effort]:
        raise ValueError("worker effort differs from the frozen explicit selection")
    return {"path": ".devlyn/" + path.name, "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw), "effort_requested": effort, "identity_basis": "invocation-argv"}


COMPLEXITIES = ("trivial", "medium", "large")
AUTO_PROBE_PREFIX = "auto-risk-probes "
# Writer-recorded reasons; callers may not supply them and repeats ignore them.
DECLARED_REASON = "declared-risk-probe-requirements"


def writer_reason(reason: str) -> bool:
    return reason.startswith(AUTO_PROBE_PREFIX) or reason == DECLARED_REASON


def declares_probe_requirements(state: dict, work: pathlib.Path) -> bool:
    """Whether the source contract declares `required_risk_probe_requirements` (validated)."""
    source = state.get("source") if isinstance(state.get("source"), dict) else {}
    relative = source.get("criteria_path") if source.get("type") == "generated" else source.get("spec_path")
    if not isinstance(relative, str) or not relative:
        return False
    path = pathlib.Path(relative)
    resolver = runpy.run_path(str(pathlib.Path(__file__).with_name("spec-verify-check.py")))
    requirements, error = resolver["resolve_required_risk_probe_requirements"](path if path.is_absolute() else work / path)
    if error:
        raise ValueError(f"BLOCKED:invalid-classification: {error}")
    return bool(requirements)


def freeze_classification(state: dict, work: pathlib.Path, complexity: str | None,
                          reasons: list[str]) -> str | None:
    """Validate the owner's classification; return the generated criteria digest."""
    source = state.get("source") if isinstance(state.get("source"), dict) else {}
    generated = source.get("type") == "generated"
    if generated and complexity not in COMPLEXITIES:
        raise ValueError("BLOCKED:invalid-classification: free-form runs need --complexity "
                         + "|".join(COMPLEXITIES))
    if not generated and complexity is not None:
        raise ValueError("BLOCKED:invalid-classification: --complexity applies only to free-form runs")
    for reason in reasons:
        if (not isinstance(reason, str) or not reason.strip() or "\n" in reason
                or writer_reason(reason) or reasons.count(reason) > 1):
            raise ValueError(f"BLOCKED:invalid-classification: invalid high-risk reason {reason!r}")
    if not generated:
        return None
    criteria = work / ".devlyn" / "criteria.generated.md"
    if criteria.is_symlink() or not criteria.is_file():
        raise ValueError("BLOCKED:invalid-classification: free-form freeze needs the regular file "
                         ".devlyn/criteria.generated.md")
    # A malformed or missing verification carrier is an input error now, not a product finding in VERIFY.
    checker = pathlib.Path(__file__).with_name("spec-verify-check.py")
    carrier = subprocess.run([sys.executable, str(checker), "--check", str(criteria)],
                             capture_output=True, text=True, encoding="utf-8")
    found = runpy.run_path(str(checker))["extract_verification_block"](criteria.read_text(encoding="utf-8"))[1]
    if carrier.returncode != 0 or found is None:
        raise ValueError("BLOCKED:invalid-classification: generated criteria need a valid verification json block: "
                         + (carrier.stderr.strip() or "no fenced json block under <!-- devlyn:verification -->"))
    return hashlib.sha256(criteria.read_bytes()).hexdigest()


def freeze_roles(state: dict, work: pathlib.Path, default_engine: str, *, complexity: str | None = None,
                 high_risk_reasons: list[str] | tuple = (), available=None) -> dict:
    helper = role_config_module()
    reasons = list(high_risk_reasons)
    criteria_sha256 = freeze_classification(state, work, complexity, reasons)
    existing = helper["snapshot"](state)
    if existing is not None:
        profile = state.get("risk_profile") or {}
        frozen_reasons = [r for r in profile.get("reasons", []) if not writer_reason(r)]
        if (state.get("complexity") != complexity or frozen_reasons != reasons
                or (criteria_sha256 is not None and state["source"].get("criteria_sha256") != criteria_sha256)):
            raise ValueError("BLOCKED:invalid-classification: a repeated freeze differs from the frozen classification")
        return existing
    if any(isinstance(entry, dict) and entry.get("started_at") for entry in state.get("phases", {}).values()):
        raise ValueError("BLOCKED:invalid-engine-config: roles must be frozen before phase dispatch")
    available = available or (lambda engine: shutil.which(engine) is not None)
    declared = declares_probe_requirements(state, work)
    profile = copy.deepcopy(state.get("risk_profile") or {})
    resolved = helper["resolve"](
        work, default_engine,
        flag_engine=state.get("engine") if state.get("engine_source") == "flag" else None,
        run_input=state.get("role_config_input"),
        no_pair=profile.get("pair_default_enabled") is False,
        available=available,
    )
    reasons = reasons + [DECLARED_REASON] * declared
    profile["high_risk"], profile["reasons"] = bool(reasons), list(reasons)
    if reasons and profile.get("risk_probes_explicit") is False and state.get("mode") != "verify-only":
        # Probes route to the legacy executor's OTHER engine; VERIFY profiles never reroute them.
        legacy = resolved["legacy_engine"]
        project, _ = helper["read_config"](work / ".devlyn/engines.json", optional=True)
        candidates = [engine for engine in project.get("pair_judge_priority", ["codex" if legacy == "claude" else "claude"])
                      if engine != legacy]
        if any(available(engine) for engine in candidates):
            profile["risk_probes_enabled"] = True
        else:
            profile["reasons"].append(f"{AUTO_PROBE_PREFIX}skipped: {(candidates or ['other-engine'])[0]}-unavailable")
    state["role_resolution"] = resolved
    state["engine"], state["engine_source"] = resolved["legacy_engine"], resolved["legacy_source"]
    state["complexity"], state["risk_profile"] = complexity, profile
    if criteria_sha256 is not None:
        state["source"]["criteria_sha256"] = criteria_sha256
    return resolved


# build_gate/cleanup no longer open in new runs; they stay here so archived runs that used
# them still resolve their repair predecessor for terminal classification.
REPAIR_PHASES = ("implement", "build_gate", "cleanup", "verify")


def valid_phase_gate_progress(progress: object) -> bool:
    if not isinstance(progress, dict):
        return False
    total, current, statuses = progress.get("total"), progress.get("current"), progress.get("statuses")
    return (type(total) is int and total > 1 and type(current) is int and 1 <= current <= total
            and isinstance(statuses, list) and len(statuses) == total
            and all(status in ("PASS", "FAIL", None) for status in statuses)
            and all(status == "PASS" for status in statuses[:current - 1]))


def repair_predecessor(state: dict) -> tuple[str, dict] | None:
    """Select the most recent started repair boundary by invocation identity."""
    phases = state.get("phases", {})
    selected = None
    for order, name in enumerate(REPAIR_PHASES):
        entry = phases.get(name) if isinstance(phases, dict) else None
        if not isinstance(entry, dict) or entry.get("started_at") is None:
            continue
        round_ = entry.get("round")
        if type(round_) is not int or round_ < 0:
            raise SystemExit("BLOCKED:repair-edge-invalid")
        if selected is None or (round_, order) > selected[0]:
            selected = ((round_, order), name, entry)
    return None if selected is None else (selected[1], selected[2])


def exhausted_origin(state: dict) -> str | None:
    """Name the current failing repair predecessor whose refused admission ends the run."""
    predecessor = repair_predecessor(state)
    if predecessor is None or predecessor[1].get("completed_at") is None:
        return None
    name, entry = predecessor
    if name == "verify":
        merged = entry.get("merged")
        return "verify" if entry.get("verdict") == "NEEDS_WORK" and isinstance(merged, dict) and merged.get("verdict") == "NEEDS_WORK" else None
    if name == "cleanup":
        return name if entry.get("verdict") == "FAIL" and entry.get("execution_kind") == "orchestrator_commands" else None
    if name == "build_gate":
        return name if entry.get("verdict") == "FAIL" else None
    progress = entry.get("exec")
    if valid_phase_gate_progress(progress) and entry.get("verdict") == "FAIL" and progress["statuses"][progress["current"] - 1] == "FAIL":
        return "phase_gate"
    return None


def repair_admission(state: dict, phase: str, round_: int,
                     triggered_by: str | None, source_phase: str | None = None) -> None:
    if phase not in REPAIR_PHASES:
        return
    predecessor = repair_predecessor(state)
    if phase == "implement":
        if predecessor is None:
            if triggered_by not in {None, "plan"}:
                raise SystemExit("BLOCKED:repair-trigger-mismatch: expected=null supplied=" + triggered_by)
            expected_round, origin = 0, None
        else:
            prior_name, prior = predecessor
            if prior.get("completed_at") is None or (source_phase is not None and prior_name != source_phase):
                raise SystemExit("BLOCKED:repair-edge-invalid")
            verdict = prior.get("verdict")
            origin = None
            if prior_name == "verify":
                if not (verdict == "NEEDS_WORK" and isinstance(prior.get("merged"), dict)
                        and prior["merged"].get("verdict") == "NEEDS_WORK"):
                    raise SystemExit("BLOCKED:repair-edge-invalid")
                origin = prior_name
            elif prior_name == "implement":
                progress = prior.get("exec")
                if not valid_phase_gate_progress(progress):
                    raise SystemExit("BLOCKED:repair-edge-invalid")
                current, statuses = progress["current"], progress["statuses"]
                status = statuses[current - 1]
                if verdict == "FAIL" and status == "FAIL":
                    origin = "phase_gate"
                elif verdict not in {"PASS", "PASS_WITH_ISSUES"} or current < 2 or status is not None:
                    raise SystemExit("BLOCKED:repair-edge-invalid")
            else:
                raise SystemExit("BLOCKED:repair-edge-invalid")
            expected_round = prior["round"] + 1
            expected_trigger = origin if origin in VALID_TRIGGERS else None
            if triggered_by != expected_trigger:
                supplied = triggered_by if triggered_by is not None else "null"
                expected = expected_trigger if expected_trigger is not None else "null"
                raise SystemExit(f"BLOCKED:repair-trigger-mismatch: expected={expected} supplied={supplied}")
        if round_ != expected_round:
            raise SystemExit(f"BLOCKED:implement-round-nonmonotonic: expected={expected_round} supplied={round_}")
        if origin is not None:
            rounds = state.get("rounds")
            if (not isinstance(rounds, dict) or type(rounds.get("global")) is not int
                or rounds["global"] < 0 or type(rounds.get("max_rounds")) is not int
                or rounds["max_rounds"] < 1):
                raise SystemExit("BLOCKED:rounds-malformed")
            if rounds["global"] >= rounds["max_rounds"]:
                raise SystemExit(
                    f"BLOCKED:repair-budget-exhausted: global={rounds['global']} "
                    f"max_rounds={rounds['max_rounds']} origin={origin}"
                )
            rounds["global"] += 1
    elif phase == "verify":
        implement = (state.get("phases") or {}).get("implement")
        expected_round = implement.get("round", 0) if isinstance(implement, dict) and implement.get("started_at") else 0
        if round_ != expected_round:
            raise SystemExit(f"BLOCKED:phase-round-mismatch: phase={phase} expected={expected_round} supplied={round_}")


def validate_verdict(phase: str, verdict: str | None) -> None:
    allowed = (verdict in FINAL_VERDICTS or (
        isinstance(verdict, str) and verdict.startswith("BLOCKED:") and len(verdict) > 8
    )) if phase == "final_report" else verdict in VALID_VERDICTS
    if verdict is not None and not allowed:
        raise SystemExit(f"error: invalid verdict for phases.{phase}: {verdict}")


def do_spawn(state: dict, phase: str, round_: int, triggered_by: str | None,
             engine: str | None, model: str | None, *,
             source_phase: str | None = None,
             prompt_sha256: str | None = None,
             devlyn: pathlib.Path | None = None,
             work: pathlib.Path | None = None) -> None:
    # Omitted worker metadata selects owner PLAN. Explicit metadata keeps the
    # historical worker API; an owner span never accepts those claims.
    owner = phase == "plan" and all(value is None for value in (engine, model, prompt_sha256))
    if not owner and phase in {"implement", "verify"} and "role_resolution" in state:
        resolution = role_config_module()["snapshot"](state)
        selected = resolution["roles"]["primary_judge" if phase == "verify" else "worker"]
        if engine is not None and engine != selected["engine"]:
            raise SystemExit("BLOCKED:role-selection-mismatch: phase engine differs from frozen selection")
        engine = selected["engine"]
        wanted_model = selected["model_requested"]
        if wanted_model is not None and model is not None and wanted_model != model:
            raise SystemExit("BLOCKED:role-selection-mismatch: phase model differs from frozen selection")
        model = wanted_model or model
    # Merge, don't replace: a phase-gated large run's `exec` progress (or any
    # other field this script doesn't own) survives a fix-loop respawn.
    phases_value = state.get("phases")
    entry = phases_value.get(phase) if isinstance(phases_value, dict) else None
    validate_plan_output(state, devlyn, phase)
    if phase in OWNER_EXECUTION and orchestrator_phase(entry, phase):
        validate_owner_identity(devlyn, phase, entry.get("round"), entry=entry)
        if not owner:
            raise SystemExit("error: owner phase cannot respawn as a worker")
    if owner:
        validate_owner_identity(devlyn, phase, round_, engine, model, prompt_sha256)
    if phase == "plan":
        if owner and (state.get("phases", {}).get("implement") or {}).get("started_at"):
            raise SystemExit("BLOCKED:plan-already-in-use: scope cannot change after implementation starts")
        history = entry.get("history", []) if isinstance(entry, dict) else []
        if not isinstance(history, list):
            raise SystemExit("error: phases.plan.history must be an array")
        dispatch_count = len(history) + int(
            isinstance(entry, dict) and entry.get("started_at") is not None
        )
        if dispatch_count >= PLAN_MAX_DISPATCHES:
            raise SystemExit("BLOCKED:plan-respawn-exhausted")
        if round_ != dispatch_count:
            raise SystemExit(
                f"BLOCKED:plan-round-nonmonotonic: expected={dispatch_count} supplied={round_}"
            )
        if not owner and (not isinstance(engine, str) or not engine):
            raise SystemExit("error: phases.plan spawn requires --engine")
        if not owner and (not isinstance(model, str) or not model):
            raise SystemExit("error: phases.plan spawn requires --model")
        if not owner and (prompt_sha256 is None or not SHA256_RE.fullmatch(prompt_sha256)):
            raise SystemExit("error: phases.plan spawn requires --prompt-sha256")
        if dispatch_count > 0 and triggered_by is None:
            raise SystemExit("error: phases.plan re-spawn requires --triggered-by")
    if phase != "plan":
        if prompt_sha256 is not None and SHA256_RE.fullmatch(prompt_sha256) is None:
            raise SystemExit("error: --prompt-sha256 must be a lowercase SHA-256 digest")
        requested_engine = (
            engine if isinstance(engine, str) and engine else
            entry.get("engine") if isinstance(entry, dict) else
            state.get("engine")
        )
        if (
            state.get("version") == "3.0"
            and not owner
            and requested_engine == "codex"
            and phase in WORKER_SESSION_ARTIFACT_PHASES
            and prompt_sha256 is None
        ):
            raise SystemExit(
                f"error: schema-v3 Codex phases.{phase} spawn requires --prompt-sha256"
            )
        requested_model = (
            model if isinstance(model, str) and model else
            entry.get("model_requested") if isinstance(entry, dict) else None
        )
        if (
            state.get("version") == "3.0"
            and not owner
            and requested_engine == "codex"
            and phase in WORKER_SESSION_ARTIFACT_PHASES
            and not requested_model
        ):
            raise SystemExit(
                f"error: schema-v3 Codex phases.{phase} spawn requires --model"
            )
    phases = state.setdefault("phases", {})
    if not isinstance(entry, dict):
        entry = {}
        phases[phase] = entry
    if entry.get("started_at") is not None and entry.get("completed_at") is None:
        raise SystemExit(
            f"error: phases.{phase} has an open span — complete it before respawn"
        )
    pre_sha = None
    if phase == "verify" and work is not None:
        # MECHANICAL seals the source against the HEAD this span opened on.
        pre_sha = _git_text(work, "rev-parse", "HEAD")
    repair_admission(state, phase, round_, triggered_by, source_phase)
    if (devlyn is not None and "untracked_baseline_sha256" in state
            and state["untracked_baseline_sha256"] is None
            and not any(isinstance(item, dict) and item.get("started_at") for item in phases.values())):
        baseline = devlyn / "untracked.baseline"
        if baseline.is_file() and not baseline.is_symlink():
            state["untracked_baseline_sha256"] = hashlib.sha256(baseline.read_bytes()).hexdigest()
    append_phase_history(entry, phase)
    if phase == "implement" and "exec" not in entry and not entry.get("history") and devlyn is not None:
        plan = devlyn / "plan.md"
        total = execution_phase_count(plan.read_bytes()) if plan.is_file() and not plan.is_symlink() else 0
        if total >= 2:
            entry["exec"] = {"total": total, "current": 1, "statuses": [None] * total}
    if phase in WORKER_SESSION_ARTIFACT_PHASES:
        entry.pop("invocation_receipt", None)
        entry.pop("role_argv", None)
    entry["started_at"] = now_iso()
    entry["completed_at"] = None
    entry["duration_ms"] = None
    entry["round"] = round_
    entry["triggered_by"] = triggered_by
    entry["verdict"] = None
    entry["artifacts"] = {"findings_file": None, "log_file": None}
    entry["sub_verdicts"] = None
    if phase == "verify":
        entry["judge_durations_ms"] = None
        for field in ("role_evidence", "executions", "dispatch", "pair_trigger", "merged", "coverage_failed",
                      "source_seal", "pre_sha"):
            entry.pop(field, None)
        if pre_sha is not None:
            entry["pre_sha"] = pre_sha
        if isinstance(state.get("verify"), dict):
            state["verify"]["pair_trigger"] = None
    if engine is not None:
        entry["engine"] = engine
    elif (
        state.get("version") == "3.0"
        and "engine" not in entry
        and isinstance(state.get("engine"), str)
        and state["engine"]
    ):
        entry["engine"] = state["engine"]
    if model is not None:
        entry["model_requested"] = model
    else:
        entry.setdefault("model_requested", None)
    entry.pop("model", None)
    entry["model_effective"] = None
    if prompt_sha256 is not None:
        entry["prompt_sha256"] = prompt_sha256
    if owner:
        entry["execution_kind"] = OWNER_EXECUTION[phase]
        entry["engine"] = entry["model_requested"] = entry["model_effective"] = None
        entry.pop("prompt_sha256", None)
        entry.pop("role_evidence", None)


def do_complete(state: dict, phase: str, verdict: str | None,
                 findings_file: str | None, log_file: str | None,
                 engine: str | None, model: str | None,
                 engine_session_log: str | None = None,
                 devlyn: pathlib.Path | None = None,
                 work: pathlib.Path | None = None, *, detail: str | None = None) -> str | None:
    phases = state.setdefault("phases", {})
    entry = phases.get(phase)
    if not isinstance(entry, dict) or not entry.get("started_at"):
        raise SystemExit(f"error: phases.{phase} was never spawned (no started_at) — cannot complete")
    validate_verdict(phase, verdict)
    if phase == "verify" and verdict is not None:
        raise SystemExit(
            "error: phases.verify.verdict is owned by verify-merge-findings.py "
            "--write-state; do not pass --verdict to complete for this phase"
        )
    if entry.get("completed_at") is not None:
        raise SystemExit(
            f"error: phases.{phase} already completed — respawn before completing again"
        )
    owner = phase in OWNER_EXECUTION and orchestrator_phase(entry, phase)
    if owner:
        validate_owner_identity(
            devlyn, phase, entry.get("round"), engine, model,
            engine_session_log=engine_session_log, entry=entry,
        )
    if phase != "plan":
        validate_plan_output(state, devlyn, phase)
    if phase == "final_report":
        if devlyn is None or any(value is not None for value in (findings_file, log_file, engine, model, engine_session_log)):
            raise SystemExit("error: the writer renders .devlyn/final-report.md; pass only --verdict/--detail")
        verdict, report_digest = write_final_report(state, devlyn, work or devlyn.resolve().parent, verdict, detail)
        log_file = ".devlyn/final-report.md"
    if phase == "plan" and entry.get("prompt_sha256") is not None:
        missing = [field for field in PLAN_SPAWN_RECEIPT_FIELDS if field not in entry]
        if missing:
            raise SystemExit(
                "error: phases.plan spawn receipt is incomplete: " + ",".join(missing)
            )
        if engine is not None and engine != entry["engine"]:
            raise SystemExit("error: phases.plan completion cannot replace spawn engine")
        if model is not None and model != entry["model_requested"]:
            raise SystemExit("error: phases.plan completion cannot replace requested model")
    if state.get("version") == "3.0" and phase != "plan":
        if engine is not None and engine != entry.get("engine"):
            raise SystemExit(f"error: phases.{phase} completion cannot replace spawn engine")
        if model is not None and model != entry.get("model_requested"):
            raise SystemExit(
                f"error: phases.{phase} completion cannot replace requested model"
            )
    bind_process_evidence(state, phase, verdict, devlyn, work)
    if phase == "probe_derive" and verdict in {"PASS", "PASS_WITH_ISSUES"}:
        bind_risk_probes(state, devlyn, work)
    started = parse_iso(entry["started_at"])
    now = now_ms()
    entry["completed_at"] = now_iso(now)
    entry["duration_ms"] = max(0, round((now - started).total_seconds() * 1000))
    if phase == "verify":
        if entry.get("verdict") is None:
            raise SystemExit(
                "error: phases.verify.verdict is still null — run "
                "verify-merge-findings.py --write-state before complete"
            )
    elif verdict is not None:
        entry["verdict"] = verdict
    else:
        raise SystemExit(f"error: --verdict is required to complete phases.{phase}")
    if phase == "implement" and verdict == "FAIL" and isinstance(entry.get("exec"), dict):
        progress = entry["exec"]
        total, current, statuses = progress.get("total"), progress.get("current"), progress.get("statuses")
        if (type(total) is not int or total <= 1 or type(current) is not int
            or not 1 <= current <= total or not isinstance(statuses, list) or len(statuses) != total):
            raise SystemExit("BLOCKED:repair-edge-invalid")
        statuses[current - 1] = "FAIL"
    if phase == "plan":
        if state.get("version") == "3.0":
            bind_plan_output(state, devlyn)
        else:
            entry.setdefault("output_sha256", None)
    if phase == "final_report":
        entry["output_sha256"] = report_digest
    if findings_file is not None or log_file is not None:
        artifacts = entry.setdefault("artifacts", {"findings_file": None, "log_file": None})
        if findings_file is not None:
            artifacts["findings_file"] = findings_file
        if log_file is not None:
            artifacts["log_file"] = log_file
    if engine is not None and phase != "plan":
        entry["engine"] = engine
    if model is not None and phase != "plan":
        entry["model_requested"] = model
    elif phase != "plan":
        entry.setdefault("model_requested", None)
    entry.pop("model", None)

    artifact_phase = None if owner else WORKER_SESSION_ARTIFACT_PHASES.get(phase)
    retained_session = None
    if devlyn is not None and artifact_phase is not None:
        candidate = devlyn / f"{artifact_phase}.worker-session.{entry.get('round')}.jsonl"
        if candidate.is_file():
            retained_session = candidate

    attestation_error = None
    schema_v3_worker = (
        state.get("version") == "3.0"
        and artifact_phase is not None
        and entry.get("engine") == "codex"
    )
    if schema_v3_worker and retained_session is None:
        expected_session = (
            devlyn / f"{artifact_phase}.worker-session.{entry.get('round')}.jsonl"
            if devlyn is not None else
            pathlib.Path(".devlyn") / f"{artifact_phase}.worker-session.{entry.get('round')}.jsonl"
        )
        attestation_error = (
            "BLOCKED:model-attestation-failed: canonical retained worker session is missing: "
            f"{expected_session}"
        )
    if (
        attestation_error is None
        and schema_v3_worker
        and engine_session_log is not None
        and pathlib.Path(engine_session_log).resolve() != retained_session.resolve()
    ):
        attestation_error = (
            "BLOCKED:model-attestation-failed: --engine-session-log must be the canonical "
            f"phase/round session {retained_session}"
        )
    if attestation_error is not None:
        entry["model_effective"] = None
    elif engine_session_log is None:
        entry["model_effective"] = None
        if retained_session is not None:
            attestation_error = (
                "BLOCKED:model-attestation-failed: --engine-session-log is required because "
                f"retained worker session exists: {retained_session}"
            )
    elif schema_v3_worker:
        receipt_path = devlyn / f"{artifact_phase}.invocation.{entry.get('round')}.json"
        try:
            receipt = invocation_receipt_module().validate_receipt(
                work.resolve(), receipt_path,
                run_id=state.get("run_id"),
                phase=phase,
                round_=entry.get("round"),
                model=entry.get("model_requested"),
                prompt_sha256=entry.get("prompt_sha256"),
                session_path=retained_session,
            )
            if receipt["exit_code"] != 0:
                raise invocation_receipt_module().ReceiptError(
                    f"Codex invocation exited {receipt['exit_code']}"
                )
            role_argv = bind_worker_role_argv(state, phase, entry, devlyn, receipt)
            if role_argv is not None:
                entry["role_argv"] = role_argv
            entry["model_effective"] = None  # The receipt binds argv, not an observed model.
            entry["invocation_receipt"] = receipt
        except (OSError, UnicodeError, ValueError) as exc:
            entry["model_effective"] = None
            attestation_error = f"BLOCKED:invocation-receipt-invalid: {exc}"
    else:
        try:
            entry["model_effective"] = parse_effective_model(pathlib.Path(engine_session_log))
        except ValueError as exc:
            entry["model_effective"] = None
            attestation_error = f"BLOCKED:model-attestation-failed: {exc}"
        requested = entry.get("model_requested")
        effective = entry.get("model_effective")
        if attestation_error is None and requested is not None and requested != effective:
            attestation_error = (
                "BLOCKED:model-attestation-mismatch: "
                f"requested={requested} effective={effective}"
            )
    if attestation_error is not None:
        entry["verdict"] = "BLOCKED"
    elif (phase == "implement" and entry["verdict"] in {"PASS", "PASS_WITH_ISSUES"}
          and entry.get("triggered_by") != "verify" and valid_phase_gate_progress(entry.get("exec"))):
        # An attested passing phase advances progress; a VERIFY repair round never does.
        progress = entry["exec"]
        progress["statuses"][progress["current"] - 1] = "PASS"
        if progress["current"] < progress["total"]:
            progress["current"] += 1
    return attestation_error


def do_transition(
    state: dict,
    phase: str,
    next_phase: str,
    verdict: str | None,
    findings_file: str | None,
    log_file: str | None,
    engine: str | None,
    model: str | None,
    engine_session_log: str | None,
    devlyn: pathlib.Path,
    next_round: int,
    next_triggered_by: str | None,
    next_engine: str | None,
    next_model: str | None,
    *,
    between=None,
    work: pathlib.Path | None = None,
) -> dict:
    """Validate complete + caller-selected spawn against a copy of state.

    The caller owns the next phase and every judgment-bearing argument.  This
    primitive only validates the requested edge and applies both lifecycle
    mutations to a detached candidate, which the CLI commits with one atomic
    state-file replacement.
    """
    if next_phase not in LEGAL_TRANSITIONS.get(phase, set()):
        raise SystemExit(f"error: illegal phase transition: {phase} -> {next_phase}")
    validate_verdict(phase, verdict)
    candidate = copy.deepcopy(state)
    attestation_error = do_complete(
        candidate, phase, verdict, findings_file, log_file,
        engine, model, engine_session_log, devlyn, work,
    )
    if attestation_error is not None:
        raise SystemExit(attestation_error)
    if between is not None:
        between()
    do_spawn(
        candidate, next_phase, next_round, next_triggered_by,
        next_engine, next_model,
        source_phase=phase,
        devlyn=devlyn,
        work=work,
    )
    return candidate


def final_report_self_test() -> None:
    script = pathlib.Path(__file__).resolve()
    archive = script.with_name("archive_run.py")
    classifier = runpy.run_path(str(script.with_name("terminal-claim-check.py")))
    stamp = "2026-01-01T00:00:00.000Z"

    def span(verdict, round_=0, **extra):
        return {"started_at": stamp, "completed_at": stamp, "duration_ms": 1, "round": round_,
                "triggered_by": None, "verdict": verdict, **extra}

    def fixture(tmp, name, *, mode="spec", phases=None, rounds=(0, 2), finish=0, plan=True):
        work = pathlib.Path(tmp) / name
        devlyn = work / ".devlyn"
        devlyn.mkdir(parents=True)
        run_id = f"rs-final-{name}"
        state = {"version": "3.0", "run_id": run_id, "started_at": stamp, "engine": "claude", "mode": mode,
                 "complexity": None, "rounds": {"global": rounds[0], "max_rounds": rounds[1]},
                 "risk_profile": {"high_risk": False, "reasons": [], "risk_probes_enabled": False,
                                  "risk_probes_explicit": False, "pair_default_enabled": True},
                 "phases": {"plan": None, "probe_derive": None, "implement": None, "verify": None, "final_report": None}}
        if plan and mode != "verify-only":
            (devlyn / "plan.md").write_bytes(b"# PLAN\n")
            state["phases"]["plan"] = span("PASS", output_sha256=hashlib.sha256(b"# PLAN\n").hexdigest(),
                                           execution_kind="orchestrator_context")
        state["phases"].update(phases or {})
        if finish is not None:
            (devlyn / "finish-gate.summary.json").write_text(json.dumps({"exit": finish, "mode": mode}) + "\n", encoding="utf-8")
        write_state(devlyn / "pipeline.state.json", state)
        spawned = cli(work, "spawn", "--round", "0")
        assert spawned.returncode == 0, (name, spawned.stderr)
        return work, devlyn

    def cli(work, *args):
        return subprocess.run([sys.executable, str(script), "--devlyn-dir", ".devlyn", "--phase", "final_report", *args],
                              cwd=work, capture_output=True, text=True, encoding="utf-8")

    def refused(work, devlyn, needle, *args):
        report = devlyn / "final-report.md"
        before = (devlyn / "pipeline.state.json").read_bytes()
        prior = report.read_bytes() if report.is_file() and not report.is_symlink() else None
        result = cli(work, "complete", *args)
        assert result.returncode != 0 and needle in result.stderr, (needle, result)
        assert (devlyn / "pipeline.state.json").read_bytes() == before, needle
        if prior is not None or not os.path.lexists(report):
            assert (report.read_bytes() if report.is_file() and not report.is_symlink() else None) == prior, needle

    verify_pass = lambda verdict="PASS": span(verdict, merged={"verdict": verdict}, pre_sha="0" * 40)
    with tempfile.TemporaryDirectory() as tmp:
        # Refusals change neither state nor an existing report.
        work, devlyn = fixture(tmp, "refusals", phases={"verify": verify_pass()})
        for extra in (("--log-file", ".devlyn/final-report.md"), ("--engine", "codex"), ("--model", "m"),
                      ("--engine-session-log", ".devlyn/x.jsonl"), ("--findings-file", ".devlyn/f.jsonl")):
            refused(work, devlyn, "pass only --verdict/--detail", *extra)
            assert not os.path.lexists(devlyn / "final-report.md"), extra
        for invalid in ("FAIL", "BLOCKED:", "unknown"):
            refused(work, devlyn, f"invalid verdict for phases.final_report: {invalid}", "--verdict", invalid)
        refused(work, devlyn, "contradicts the evidence-derived PASS", "--verdict", "BLOCKED:plan-empty")
        finish_path = devlyn / "finish-gate.summary.json"
        finish_path.write_text('{"exit": 3}\n', encoding="utf-8")
        refused(work, devlyn, "no valid exit")
        finish_path.write_text('{"exit": 0}\n', encoding="utf-8")
        state = read_state(devlyn / "pipeline.state.json")
        state["phases"]["verify"]["dispatch"] = {"path": ".devlyn/elsewhere.json", "sha256": "0" * 64}
        write_state(devlyn / "pipeline.state.json", state)
        refused(work, devlyn, "dispatch binding is malformed")
        del state["phases"]["verify"]["dispatch"]
        write_state(devlyn / "pipeline.state.json", state)
        outside = work / "outside.md"
        outside.write_text("keep\n", encoding="utf-8")
        report = devlyn / "final-report.md"
        report.symlink_to(outside)
        refused(work, devlyn, "not a regular file")
        assert outside.read_text(encoding="utf-8") == "keep\n" and report.is_symlink()
        report.unlink(); report.mkdir()
        refused(work, devlyn, "not a regular file")
        report.rmdir()
        log = devlyn / "mechanical.log.md"
        log.write_text("<!-- devlyn:mechanical-skips -->\n```json\n{\"run_id\": 1}\n```\n", encoding="utf-8")
        refused(work, devlyn, "skip block at line 1")
        block = json.dumps({"run_id": "rs-final-refusals", "round": 0, "skips": [{"gate": "lint", "reason": "none"}]})
        log.write_text(("<!-- devlyn:mechanical-skips -->\n```json\n" + block + "\n```\n") * 2, encoding="utf-8")
        refused(work, devlyn, "more than one skip block")
        log.unlink()
        (devlyn / "finish-gate.summary.json").unlink()
        refused(work, devlyn, "run finish-gate.py")
        work, devlyn = fixture(tmp, "unrepresented")
        refused(work, devlyn, "pass --verdict BLOCKED:<reason>")
        for reason in sorted(EVIDENCE_ONLY_REASONS):
            refused(work, devlyn, "not supported by the recorded evidence", "--verdict", f"BLOCKED:{reason}")
            refused(work, devlyn, "not supported by the recorded evidence", "--verdict", f"BLOCKED:{reason}: detail")
        work, devlyn = fixture(tmp, "budget-left", rounds=(0, 2), phases={
            "implement": span("PASS"), "verify": span("NEEDS_WORK", merged={"verdict": "NEEDS_WORK"})})
        refused(work, devlyn, "verify repair budget remains")

        # Every terminal outcome: header verdict == bound verdict == TCC CLEAN after archive.
        denied = fixture(tmp, "denial", phases={"implement": span("PASS"), "verify": span("BLOCKED")})
        module = process_evidence_module()
        denial_state = read_state(denied[1] / "pipeline.state.json")
        manifest = module.manifest_relative_path(denial_state, "verify")
        module.record_capability_denial(denied[0], denied[0] / manifest, denial_state["run_id"], "verify", 0,
                                        module.normalize_obligation({"id": "tsc", "phase": "verify", "cmd": "tsc"}),
                                        "tool", b"tsc absent; the task prohibits supplying it")
        denial_state["process_evidence"] = [module.validate_manifest(
            denied[0], manifest, denial_state["run_id"], "verify", 0, require_expectations=False)]
        write_state(denied[1] / "pipeline.state.json", denial_state)
        unavailable = fixture(tmp, "judge-unavailable", phases={"implement": span("PASS"), "verify": span("BLOCKED")})
        record = json.dumps({"run_id": "rs-final-judge-unavailable", "round": 0, "roles": {
            "primary_judge": {"decision": "dispatch", "reason": None},
            "pair_judge": {"decision": "blocked", "reason": "BLOCKED:codex-unavailable: --pair-verify requires codex"}}}).encode()
        (unavailable[1] / "verify-judge.r0.dispatch.json").write_bytes(record)
        unavailable_state = read_state(unavailable[1] / "pipeline.state.json")
        unavailable_state["phases"]["verify"]["dispatch"] = {
            "path": ".devlyn/verify-judge.r0.dispatch.json", "sha256": hashlib.sha256(record).hexdigest(), "bytes": len(record)}
        write_state(unavailable[1] / "pipeline.state.json", unavailable_state)
        gated = {"total": 2, "current": 1, "statuses": ["FAIL", None]}
        matrix = [
            ("pass", fixture(tmp, "pass", phases={"implement": span("PASS"), "verify": verify_pass()}), [], "PASS"),
            ("issues", fixture(tmp, "issues", phases={"implement": span("PASS"), "verify": verify_pass("PASS_WITH_ISSUES")}),
             [], "PASS_WITH_ISSUES"),
            ("verify-only", fixture(tmp, "verify-only", mode="verify-only", phases={
                "verify": span("NEEDS_WORK", merged={"verdict": "NEEDS_WORK"})}), [], "NEEDS_WORK"),
            ("verify-exhausted", fixture(tmp, "verify-exhausted", rounds=(1, 1), phases={
                "implement": span("PASS", 1, triggered_by="verify"),
                "verify": span("NEEDS_WORK", 1, merged={"verdict": "NEEDS_WORK"})}), [], "NEEDS_WORK"),
            ("gate-exhausted", fixture(tmp, "gate-exhausted", rounds=(2, 2), phases={
                "implement": span("FAIL", 2, exec=gated)}), [], "BLOCKED:repair-budget-exhausted"),
            ("finish-unclean", fixture(tmp, "finish-unclean", finish=2, phases={
                "implement": span("PASS"), "verify": verify_pass()}), [], "BLOCKED:finish-gate-unclean"),
            ("denial", denied, [], "BLOCKED:build-env-underprovisioned"),
            ("judge-unavailable", unavailable, [], "BLOCKED:codex-unavailable"),
            ("plan-empty", fixture(tmp, "plan-empty", finish=None, phases={"plan": None}), ["--verdict", "BLOCKED:plan-empty"],
             "BLOCKED:plan-empty"),
            ("finish-malformed", fixture(tmp, "finish-malformed", finish=1, phases={
                "implement": span("PASS"), "verify": verify_pass()}), [], "BLOCKED:finish-gate-unclean"),
            ("budget-left-halt", fixture(tmp, "budget-left-halt", rounds=(0, 2), phases={
                "implement": span("PASS"), "verify": span("NEEDS_WORK", merged={"verdict": "NEEDS_WORK"})}),
             ["--verdict", "BLOCKED:codex-unavailable"], "BLOCKED:codex-unavailable"),
            ("stale-findings", fixture(tmp, "stale-findings", rounds=(1, 2), phases={
                "implement": span("BLOCKED", 1, triggered_by="verify"),
                "verify": span("NEEDS_WORK", merged={"verdict": "NEEDS_WORK"})}),
             ["--verdict", "BLOCKED:implement-empty"], "BLOCKED:implement-empty"),
            ("followups", fixture(tmp, "followups", mode="free-form", phases={
                "implement": span("PASS"), "verify": verify_pass()}), [], "PASS"),
            ("render-refused", fixture(tmp, "render-refused"),
             ["--verdict", "BLOCKED:phase-input-invalid", "--detail", "contract sha mismatch"], "BLOCKED:phase-input-invalid"),
            ("findings-unreadable", fixture(tmp, "findings-unreadable", phases={
                "implement": span("PASS"), "verify": verify_pass()}), [], "PASS"),
            ("plan-tampered", fixture(tmp, "plan-tampered", finish=None, phases={
                "implement": span("PASS"), "verify": verify_pass()}), [], "BLOCKED:phase-input-invalid"),
        ]
        plan_empty_devlyn = matrix[8][1][1]
        (plan_empty_devlyn / "plan.md").write_bytes(b"# PLAN\n")
        plan_empty_state = read_state(plan_empty_devlyn / "pipeline.state.json")
        plan_empty_state["phases"]["plan"] = span("BLOCKED", output_sha256=hashlib.sha256(b"# PLAN\n").hexdigest(),
                                                  execution_kind="orchestrator_context")
        write_state(plan_empty_devlyn / "pipeline.state.json", plan_empty_state)
        # Before IMPLEMENT the real finish gate is malformed (no usable PLAN surface); the halt keeps its reason.
        gate = subprocess.run([sys.executable, str(script.with_name("finish-gate.py"))], cwd=matrix[8][1][0],
                              capture_output=True, text=True, encoding="utf-8")
        assert gate.returncode == 1, gate
        (matrix[11][1][1] / "verify-merged.findings.jsonl").write_text(json.dumps({
            "severity": "HIGH", "rule_id": "stale.round", "file": "a.py", "line": 1, "message": "superseded",
            "confidence": "high"}) + "\n", encoding="utf-8")
        # Display-only findings never withhold the report; a PLAN that no longer verifies decides the verdict.
        (matrix[14][1][1] / "verify-merged.findings.jsonl").write_bytes(b"[1]\n")
        (matrix[15][1][1] / "plan.md").write_bytes(b"# PLAN\nwidened after binding\n")
        follow_work, follow_devlyn = matrix[12][1]
        criteria_bytes = b"# Criteria\n## Assumptions\n- narrowed to the CLI only\n## Verification\n"
        (follow_devlyn / "criteria.generated.md").write_bytes(criteria_bytes)
        follow = read_state(follow_devlyn / "pipeline.state.json")
        follow.update(complexity="large", source={"type": "generated", "criteria_path": ".devlyn/criteria.generated.md",
                                                  "criteria_sha256": hashlib.sha256(criteria_bytes).hexdigest()})
        follow["risk_profile"].update(pair_default_enabled=False, risk_probes_explicit=True)
        follow["phases"]["verify"]["sub_verdicts"] = {"pair_judge": "TIMEOUT"}
        write_state(follow_devlyn / "pipeline.state.json", follow)
        changed = copy.deepcopy(follow)
        changed["source"]["criteria_sha256"] = "0" * 64
        changed_report = render_final_report(changed, follow_devlyn, follow_work, "PASS", None)
        assert "assumptions omitted" in changed_report and "narrowed to the CLI only" not in changed_report
        (follow_devlyn / "criteria.generated.md").write_bytes(criteria_bytes.decode().encode("utf-16"))
        assert "assumptions omitted" in render_final_report(changed, follow_devlyn, follow_work, "PASS", None)
        (follow_devlyn / "criteria.generated.md").write_bytes(criteria_bytes)
        (follow_devlyn / "criteria.generated.md").rename(follow_devlyn / "criteria.off")
        assert "generated criteria unavailable" in render_final_report(follow, follow_devlyn, follow_work, "PASS", None)
        (follow_devlyn / "criteria.off").rename(follow_devlyn / "criteria.generated.md")
        if os.name != "nt":
            unreadable = matrix[0][1][1] / "verify-merged.findings.jsonl"
            unreadable.write_bytes(b"{}\n")
            unreadable.chmod(0)
            if not os.access(unreadable, os.R_OK):
                pass_state = read_state(matrix[0][1][1] / "pipeline.state.json")
                assert "verify-merged.findings.jsonl unreadable" in render_final_report(
                    pass_state, matrix[0][1][1], matrix[0][1][0], "PASS", None)
            unreadable.chmod(0o600)
            unreadable.unlink()
        pass_block = json.dumps({"run_id": "rs-final-pass", "round": 0, "skips": [{"gate": "lint", "reason": "no linter"}]})
        old_block = json.dumps({"run_id": "rs-older", "round": 0, "skips": [{"gate": "tests", "reason": "old"}]})
        (matrix[0][1][1] / "mechanical.log.md").write_text(
            "".join(f"<!-- devlyn:mechanical-skips -->\n```json\n{b}\n```\n" for b in (old_block, pass_block)), encoding="utf-8")
        (matrix[5][1][1] / "finish-gate.findings.jsonl").write_text(json.dumps({
            "severity": "HIGH", "rule_id": "scope.finish-unaudited-file", "file": "notes.txt", "line": 1,
            "message": "outside | surface", "confidence": "high"}) + "\n", encoding="utf-8")
        # Evidence is rehashed: a dispatch record or VERIFY carrier altered after binding refuses completion.
        for label, (work, devlyn), target in (("dispatch", unavailable, "verify-judge.r0.dispatch.json"),
                                              ("carrier", denied, None)):
            path = devlyn / target if target else work / manifest
            original = path.read_bytes()
            path.write_bytes(original + b" ")
            refused(work, devlyn, "differs from its state binding" if target else "bound VERIFY evidence")
            path.write_bytes(original)
        # A VERIFY result from before a later IMPLEMENT round never decides the verdict.
        work, devlyn = fixture(tmp, "stale-verify", phases={
            "implement": span("PASS", 1, triggered_by="verify"), "verify": verify_pass()})
        refused(work, devlyn, "pass --verdict BLOCKED:<reason>")
        for name, (work, devlyn), args, expected in matrix:
            result = cli(work, "complete", *args)
            assert result.returncode == 0, (name, result.stderr)
            raw_report = (devlyn / "final-report.md").read_bytes()
            report = raw_report.decode("utf-8")
            assert result.stdout.replace("\r\n", "\n") == report, name
            state = read_state(devlyn / "pipeline.state.json")
            final = state["phases"]["final_report"]
            assert final["verdict"] == expected, (name, final["verdict"])
            assert f"| {expected} |" in report.splitlines()[5], (name, report)
            assert final["output_sha256"] == hashlib.sha256(raw_report).hexdigest(), name
            if name == "pass":
                assert "skipped: lint (no linter)" in report and "old" not in report, report
            if name == "finish-unclean":
                assert "outside \\| surface" in report, report
            if name == "judge-unavailable":
                assert "setup: install and authenticate codex" in report, report
                assert "- pair: blocked: BLOCKED:codex-unavailable" in report, report
            if name == "gate-exhausted":
                assert "0/2 phases passed" in report, report
            if name == "findings-unreadable":
                assert "verify-merged.findings.jsonl unreadable" in report, report
            if name == "plan-tampered":
                assert "bound PLAN no longer verifies: BLOCKED:plan-integrity-mismatch" in report, report
            if name == "stale-findings":
                assert "## Findings\n\nNone." in report and "superseded" not in report, report
            if name == "followups":
                for line in ("Assumptions for user review", "- narrowed to the CLI only", "solo verdict after pair TIMEOUT",
                             "opt-out: --no-pair", "opt-out: --no-risk-probes"):
                    assert line in report, (line, report)
            archived = subprocess.run([sys.executable, str(archive), "--devlyn-dir", ".devlyn"],
                                      cwd=work, capture_output=True, text=True, encoding="utf-8")
            assert archived.returncode == 0, (name, archived.stderr)
            state_file = devlyn / "runs" / state["run_id"] / "pipeline.state.json"
            verdict = classifier["classify_state_bytes"](work, state_file, state_file.read_bytes(), archived=True)[0]
            assert verdict.status == "CLEAN", (name, verdict)

        # A report altered after binding blocks archive.
        work, devlyn = fixture(tmp, "tamper", phases={"implement": span("PASS"), "verify": verify_pass()})
        assert cli(work, "complete").returncode == 0
        with (devlyn / "final-report.md").open("a", encoding="utf-8") as handle:
            handle.write("edited\n")
        archived = subprocess.run([sys.executable, str(archive), "--devlyn-dir", ".devlyn"],
                                  cwd=work, capture_output=True, text=True, encoding="utf-8")
        assert archived.returncode == 1 and "error: archive blocked:" in archived.stderr, archived
    print("PASS final report: evidence-derived verdict matrix (16) agrees with archive and TCC; refusals preserve state")


def repair_admission_self_test() -> None:
    stamp = "2026-01-01T00:00:00.000Z"
    # Archived runs may still carry a failed BUILD_GATE or CLEANUP span; a new run never admits from one.
    for retired in ("build_gate", "cleanup"):
        candidate = {"phases": {retired: {"started_at": stamp, "completed_at": stamp, "round": 0, "verdict": "FAIL"}},
                     "rounds": {"global": 0, "max_rounds": 1}}
        try:
            do_spawn(candidate, "implement", 1, None, None, None)
        except SystemExit as exc:
            assert str(exc) == "BLOCKED:repair-edge-invalid", exc
        else:
            raise AssertionError(f"retired {retired} origin admitted a repair")
    origins = {
        "verify": ({"started_at": stamp, "completed_at": stamp, "round": 0,
                    "verdict": "NEEDS_WORK", "merged": {"verdict": "NEEDS_WORK"}}, "verify"),
        "phase_gate": ({"started_at": stamp, "completed_at": stamp, "round": 0, "verdict": "FAIL",
                        "exec": {"total": 2, "current": 1, "statuses": ["FAIL", None]}}, None),
    }
    for origin, (entry, trigger) in origins.items():
        source = "implement" if origin == "phase_gate" else origin
        initial = {"phases": {source: entry}, "rounds": {"global": 0, "max_rounds": 1}}
        for wrong in ((None, "plan", "verify") if trigger else ("plan", "verify")):
            if wrong == trigger:
                continue
            candidate = copy.deepcopy(initial)
            try:
                do_spawn(candidate, "implement", 1, wrong, None, None)
            except SystemExit as exc:
                assert "repair-trigger-mismatch" in str(exc), (origin, wrong, exc)
            else:
                raise AssertionError((origin, wrong))
        for malformed in ({"global": True, "max_rounds": 1}, {"global": -1, "max_rounds": 1},
                          {"global": 0, "max_rounds": True}, {"global": 0, "max_rounds": 0}, None):
            candidate = copy.deepcopy(initial)
            candidate["rounds"] = malformed
            try:
                do_spawn(candidate, "implement", 1, trigger, None, None)
            except SystemExit as exc:
                assert str(exc) == "BLOCKED:rounds-malformed"
            else:
                raise AssertionError((origin, malformed))
        candidate = copy.deepcopy(initial)
        try:
            do_spawn(candidate, "implement", 2, trigger, None, None)
        except SystemExit as exc:
            assert "implement-round-nonmonotonic" in str(exc)
        else:
            raise AssertionError((origin, "skipped round"))
        candidate = copy.deepcopy(initial)
        do_spawn(candidate, "implement", 1, trigger, None, None)
        assert candidate["rounds"]["global"] == 1, origin
        try:
            do_spawn(candidate, "implement", 1, trigger, None, None)
        except SystemExit:
            pass
        else:
            raise AssertionError((origin, "duplicate admission"))
        exhausted = copy.deepcopy(initial)
        exhausted["rounds"]["global"] = 1
        try:
            do_spawn(exhausted, "implement", 1, trigger, None, None)
        except SystemExit as exc:
            assert str(exc) == f"BLOCKED:repair-budget-exhausted: global=1 max_rounds=1 origin={origin}"
        else:
            raise AssertionError((origin, "shared exhaustion"))
    phased = {"rounds": {"global": 0, "max_rounds": 1}, "phases": {}}
    do_spawn(phased, "implement", 0, None, None, None)
    phased["phases"]["implement"].update({"completed_at": stamp, "verdict": "PASS",
        "exec": {"total": 2, "current": 2, "statuses": ["PASS", None]}})
    do_spawn(phased, "implement", 1, None, None, None)
    assert phased["rounds"]["global"] == 0
    do_complete(phased, "implement", "FAIL", None, None, None, None)
    assert phased["phases"]["implement"]["exec"]["statuses"] == ["PASS", "FAIL"]
    do_spawn(phased, "implement", 2, None, None, None)
    assert phased["rounds"]["global"] == 1
    do_complete(phased, "implement", "PASS", None, None, None, None)
    do_spawn(phased, "verify", 2, None, None, None)
    with tempfile.TemporaryDirectory() as tmp:
        transition_state = {"rounds": {"global": 0, "max_rounds": 1}, "phases": {}}
        do_spawn(transition_state, "implement", 0, None, None, None)
        transition_state["phases"]["implement"]["exec"] = {
            "total": 2, "current": 1, "statuses": [None, None],
        }
        for worker in ("implement", "probe_derive"):
            try:
                do_transition(transition_state, "implement" if worker == "implement" else "plan", worker, "FAIL",
                              None, None, None, None, None, pathlib.Path(tmp), 1, None, None, None)
            except SystemExit as exc:
                assert "illegal phase transition" in str(exc), exc
            else:
                raise AssertionError(f"a transition opened worker phase {worker}")
        assert transition_state["rounds"]["global"] == 0
        assert transition_state["phases"]["implement"]["completed_at"] is None
    print("PASS repair admission: verify and phase-gate origins, trigger/counter/round refusal, phased invocation and last repair")


def probe_digest_self_test() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        work = pathlib.Path(tmp); devlyn = work / ".devlyn"; devlyn.mkdir()
        spec = b"# Spec\n\n<!-- devlyn:verification -->\n## Verification\n\n- running the tool prints ok\n"
        (work / "spec.md").write_bytes(spec)
        probe = {"id": "probe-1", "cmd": "python3 -c \"print('ok')\"", "exit_code": 0, "stdout_contains": ["ok"],
                 "derived_from": "running the tool prints ok", "tags": ["shape_contract"],
                 "tag_evidence": {"shape_contract": ["uses_visible_input_key_names", "asserts_visible_output_key_names",
                                                     "asserts_no_unexpected_output_keys"]}}
        (devlyn / "risk-probes.jsonl").write_text(json.dumps(probe) + "\n", encoding="utf-8")
        state = {"run_id": "rs-probe", "mode": "spec", "phases": {},
                 "source": {"type": "spec", "spec_path": "spec.md", "spec_sha256": hashlib.sha256(spec).hexdigest()},
                 "risk_profile": {"high_risk": True, "reasons": ["x"], "risk_probes_enabled": True,
                                  "risk_probes_explicit": True, "pair_default_enabled": True}}
        write_state(devlyn / "pipeline.state.json", state)
        do_spawn(state, "probe_derive", 0, None, "codex", None, devlyn=devlyn)
        before = copy.deepcopy(state)
        do_complete(state, "probe_derive", "PASS", None, None, None, None, devlyn=devlyn, work=work)
        expected, _ = runpy.run_path(str(pathlib.Path(__file__).with_name("spec-verify-check.py")))["risk_probes_digest"](devlyn)
        assert state["risk_probes_digest"] == expected and expected
        (devlyn / "risk-probes.jsonl").write_text(json.dumps({**probe, "derived_from": "not in the spec"}) + "\n", encoding="utf-8")
        try:
            do_complete(before, "probe_derive", "PASS", None, None, None, None, devlyn=devlyn, work=work)
        except SystemExit as exc:
            assert str(exc).startswith("BLOCKED:probe-derive-malformed"), exc
        else:
            raise AssertionError("malformed probes were bound")
        assert before.get("risk_probes_digest") is None
        assert before["phases"]["probe_derive"]["completed_at"] is None
    print("PASS probe_derive PASS binds the validated probe digest; malformed probes refuse completion")


def freeze_classification_self_test() -> None:
    def fresh(mode="free-form", explicit=False, enabled=False, no_pair=False):
        source = ({"type": "generated", "criteria_path": ".devlyn/criteria.generated.md", "criteria_sha256": None}
                  if mode == "free-form" else {"type": "spec", "criteria_path": None, "criteria_sha256": None})
        return {"version": "3.0", "engine": "claude", "engine_source": "default", "mode": mode,
                "complexity": None, "source": source, "phases": {},
                "risk_profile": {"high_risk": False, "reasons": [], "risk_probes_enabled": enabled,
                                 "risk_probes_explicit": explicit, "pair_default_enabled": not no_pair}}

    def refused(state, work, needle, **kw):
        before = json.dumps(state, sort_keys=True)
        try:
            freeze_roles(state, work, "claude", **kw)
        except ValueError as exc:
            assert needle in str(exc), exc
        else:
            raise AssertionError("freeze accepted " + needle)
        assert json.dumps(state, sort_keys=True) == before, "a refused freeze changed state"

    both = lambda engine: engine in {"claude", "codex"}
    only_claude = lambda engine: engine == "claude"
    with tempfile.TemporaryDirectory() as tmp:
        work = pathlib.Path(tmp); devlyn = work / ".devlyn"; devlyn.mkdir()
        criteria = devlyn / "criteria.generated.md"
        state = fresh()
        refused(state, work, "need --complexity", available=both)
        refused(state, work, "regular file", complexity="medium", available=both)
        (work / "elsewhere.md").write_text("# C\n", encoding="utf-8")
        criteria.symlink_to(work / "elsewhere.md")
        refused(state, work, "regular file", complexity="medium", available=both)
        criteria.unlink()
        criteria.write_bytes(b"# Criteria\n")
        refused(state, work, "valid verification json block", complexity="medium", available=both)
        criteria.write_bytes(b"# Criteria\n\n<!-- devlyn:verification -->\n## Verification\n\n- ok\n")
        refused(state, work, "valid verification json block", complexity="medium", available=both)
        valid = b'# Criteria\n\n<!-- devlyn:verification -->\n## Verification\n\n- ok\n\n```json\n{"verification_commands": [{"cmd": "true"}]}\n```\n'
        criteria.write_bytes(valid)
        refused(state, work, "invalid high-risk reason", complexity="medium", high_risk_reasons=["auth", "auth"])
        refused(state, work, "invalid high-risk reason", complexity="medium",
                high_risk_reasons=["auto-risk-probes skipped: codex-unavailable"])
        frozen = freeze_roles(state, work, "claude", complexity="medium", high_risk_reasons=["auth"], available=both)
        assert state["complexity"] == "medium" and state["source"]["criteria_sha256"] == hashlib.sha256(valid).hexdigest()
        assert state["risk_profile"] == {"high_risk": True, "reasons": ["auth"], "risk_probes_enabled": True,
                                         "risk_probes_explicit": False, "pair_default_enabled": True}, state["risk_profile"]
        assert freeze_roles(state, work, "claude", complexity="medium", high_risk_reasons=["auth"], available=both) == frozen
        refused(state, work, "differs from the frozen classification", complexity="large", high_risk_reasons=["auth"])
        refused(state, work, "differs from the frozen classification", complexity="medium", high_risk_reasons=[])
        criteria.write_bytes(valid.replace(b"- ok", b"- changed"))
        refused(state, work, "differs from the frozen classification", complexity="medium", high_risk_reasons=["auth"])

        # The skip reason belongs only to an automatic high-risk run whose OTHER engine is absent.
        state = fresh()
        freeze_roles(state, work, "claude", complexity="trivial", high_risk_reasons=["payment"], available=only_claude)
        assert state["risk_profile"]["risk_probes_enabled"] is False
        assert state["risk_profile"]["reasons"] == ["payment", "auto-risk-probes skipped: codex-unavailable"]
        assert freeze_roles(state, work, "claude", complexity="trivial", high_risk_reasons=["payment"],
                            available=only_claude)["roles"]
        for explicit_enabled in (True, False):
            state = fresh(explicit=True, enabled=explicit_enabled)
            freeze_roles(state, work, "claude", complexity="trivial", high_risk_reasons=["payment"], available=only_claude)
            assert state["risk_profile"]["reasons"] == ["payment"]
            assert state["risk_profile"]["risk_probes_enabled"] is explicit_enabled
        state = fresh()
        freeze_roles(state, work, "claude", complexity="trivial", available=both)
        assert state["risk_profile"]["high_risk"] is False and state["risk_profile"]["risk_probes_enabled"] is False
        assert state["risk_profile"]["reasons"] == []
        state = fresh(mode="verify-only")
        refused(state, work, "only to free-form", complexity="medium", available=both)
        freeze_roles(state, work, "claude", high_risk_reasons=["webhook"], available=both)
        assert state["risk_profile"]["reasons"] == ["webhook"] and state["risk_profile"]["risk_probes_enabled"] is False
        assert state["complexity"] is None

        # Probes follow the legacy executor's OTHER engine, not an independently configured VERIFY seat.
        (devlyn / "engines.json").write_text(
            '{"executor":"codex","roles":{"primary_judge":{"engine":"claude"}}}', encoding="utf-8")
        state = fresh(mode="spec")
        freeze_roles(state, work, "claude", high_risk_reasons=["migration"], available=lambda engine: engine == "codex")
        assert state["role_resolution"]["roles"]["pair_judge"]["engine"] == "codex"
        assert state["risk_profile"]["reasons"] == ["migration", "auto-risk-probes skipped: claude-unavailable"]
        # Declared probe requirements mark the run high risk under the same automatic gating.
        (devlyn / "engines.json").unlink()

        def declaring(requirements):
            block = {"verification_commands": [{"cmd": "true"}], "required_risk_probe_requirements": requirements}
            return ("# C\n\n<!-- devlyn:verification -->\n## Verification\n\n- a write releases the lock\n\n```json\n"
                    + json.dumps(block) + "\n```\n").encode("utf-8")

        declared = [{"tag": "release_recovery", "derived_from": "a write releases the lock"}]
        criteria.write_bytes(declaring(declared))
        state = fresh()
        freeze_roles(state, work, "claude", complexity="medium", available=both)
        assert state["risk_profile"]["high_risk"] is True and state["risk_profile"]["risk_probes_enabled"] is True
        assert state["risk_profile"]["reasons"] == [DECLARED_REASON]
        assert freeze_roles(state, work, "claude", complexity="medium", available=both)["roles"]
        refused(state, work, "invalid high-risk reason", complexity="medium", high_risk_reasons=[DECLARED_REASON])
        state = fresh(explicit=True, enabled=False)
        freeze_roles(state, work, "claude", complexity="medium", available=both)
        assert state["risk_profile"]["reasons"] == [DECLARED_REASON] and state["risk_profile"]["risk_probes_enabled"] is False
        state = fresh()
        freeze_roles(state, work, "claude", complexity="medium", available=only_claude)
        assert state["risk_profile"]["reasons"] == [DECLARED_REASON, "auto-risk-probes skipped: codex-unavailable"]
        (work / "spec.md").write_bytes(declaring(declared))
        state = fresh(mode="verify-only")
        state["source"]["spec_path"] = "spec.md"
        freeze_roles(state, work, "claude", available=both)
        assert state["risk_profile"]["high_risk"] is True and state["risk_profile"]["risk_probes_enabled"] is False
        crowded = [{"tag": "fixture_cleanup", "derived_from": "a write releases the lock"}] + [
            {"tag": "fixture_cleanup", "derived_from": text} for text in ("a write", "releases", "the lock")]
        criteria.write_bytes(declaring(crowded))
        refused(fresh(), work, "at most 3 probes", complexity="medium", available=both)
        criteria.write_bytes(declaring([{**declared[0], "extra": 1}]))
        refused(fresh(), work, "unknown key(s): extra", complexity="medium", available=both)
        criteria.write_bytes(declaring([]))
        state = fresh()
        freeze_roles(state, work, "claude", complexity="medium", available=both)
        assert state["risk_profile"]["high_risk"] is False and state["risk_profile"]["reasons"] == []
    print("PASS freeze classification: complexity/criteria binding, auto-probe selection, declared requirements, repeat refusal")


def self_test() -> int:
    import time

    repair_admission_self_test()
    freeze_classification_self_test()
    probe_digest_self_test()
    final_report_self_test()
    with tempfile.TemporaryDirectory() as tmp:
        work = pathlib.Path(tmp); devlyn = work / ".devlyn"; devlyn.mkdir()
        helper = role_config_module()
        config = {"roles": {"worker": {"engine": "codex", "model": "gpt-6-astra", "effort": "high"},
                            "primary_judge": {"engine": "claude"}}}
        (devlyn / "engines.json").write_bytes(helper["encoded"](config))
        state = {"version": "3.0", "engine": "codex", "engine_source": "default", "phases": {}}
        frozen = freeze_roles(state, work, "codex")
        (devlyn / "engines.json").write_text('{"executor":"claude"}', encoding="utf-8")
        assert freeze_roles(state, work, "codex") == frozen
        do_spawn(state, "verify", 0, None, None, None, devlyn=devlyn)
        assert state["engine"] == "codex" and state["phases"]["verify"]["engine"] == "claude"
        for phase in ("implement",):
            before = copy.deepcopy(state)
            try:
                do_spawn(state, phase, 0, None, "claude", None, devlyn=devlyn)
            except SystemExit:
                pass
            else:
                raise AssertionError("wrong worker engine accepted")
            assert state == before
        argv = ["--json", "-m", "gpt-6-astra", "-c", "model_reasoning_effort=high", "task"]
        receipt = {"argv_sha256": hashlib.sha256(json.dumps(argv, separators=(",", ":")).encode()).hexdigest()}
        path = devlyn / "implement.argv.0.json"
        path.write_text(json.dumps(argv), encoding="utf-8")
        binding = bind_worker_role_argv(state, "implement", {"round": 0}, devlyn, receipt)
        assert binding["effort_requested"] == "high"
        path.write_text(json.dumps([*argv, "extra"]), encoding="utf-8")
        try:
            bind_worker_role_argv(state, "implement", {"round": 0}, devlyn, receipt)
        except ValueError:
            pass
        else:
            raise AssertionError("modified worker argv accepted")
        assert bind_worker_role_argv(state, "verify", {}, devlyn, receipt) is None
    print("PASS explicit roles: frozen primary/worker routing and actual worker argv binding")

    try:
        loads_strict_json('{"process_evidence":null,"process_evidence":[]}')
    except ValueError as exc:
        assert "duplicate JSON key" in str(exc)
    else:
        raise AssertionError("duplicate pipeline state key was accepted")

    with tempfile.TemporaryDirectory() as tmp:
        devlyn = pathlib.Path(tmp)
        state_path = devlyn / "pipeline.state.json"
        write_state(state_path, {"phases": {}})

        # Iter-0089 P-0089-1/2/6: PLAN authorization is a CLI-level,
        # state-derived ledger contract. Rejections must leave the actual
        # state file byte-identical, not merely preserve an in-memory copy.
        script = str(pathlib.Path(__file__).resolve())
        digest0 = hashlib.sha256(b"plan prompt round 0").hexdigest()
        digest1 = hashlib.sha256(b"plan prompt round 1").hexdigest()

        def plan_cli(*event_args: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                [
                    sys.executable, script, "--devlyn-dir", str(devlyn),
                    "--phase", "plan", *event_args,
                ],
                capture_output=True, text=True, check=False,
                encoding="utf-8",
            )

        def assert_plan_rejected_unchanged(
            expected_stderr: str, *event_args: str,
        ) -> None:
            before = state_path.read_bytes()
            before_hash = hashlib.sha256(before).hexdigest()
            result = plan_cli(*event_args)
            assert result.returncode != 0, result.stdout
            assert result.stderr.strip() == expected_stderr, result.stderr
            after = state_path.read_bytes()
            assert after == before
            assert hashlib.sha256(after).hexdigest() == before_hash

        required_spawn = (
            "spawn", "--round", "0", "--engine", "claude",
            "--model", "plan-test-model", "--prompt-sha256", digest0,
        )
        assert_plan_rejected_unchanged(
            "error: phases.plan spawn requires --engine",
            "spawn", "--round", "0", "--model", "plan-test-model",
            "--prompt-sha256", digest0,
        )
        assert_plan_rejected_unchanged(
            "error: phases.plan spawn requires --model",
            "spawn", "--round", "0", "--engine", "claude",
            "--prompt-sha256", digest0,
        )
        assert_plan_rejected_unchanged(
            "error: phases.plan spawn requires --prompt-sha256",
            "spawn", "--round", "0", "--engine", "claude",
            "--model", "plan-test-model",
        )
        assert_plan_rejected_unchanged(
            "error: phases.plan spawn requires --prompt-sha256",
            "spawn", "--round", "0", "--engine", "claude",
            "--model", "plan-test-model", "--prompt-sha256", "ABC",
        )
        assert_plan_rejected_unchanged(
            "BLOCKED:plan-round-nonmonotonic: expected=0 supplied=1",
            "spawn", "--round", "1", "--engine", "claude",
            "--model", "plan-test-model", "--prompt-sha256", digest0,
        )

        result = plan_cli(*required_spawn)
        assert result.returncode == 0, result.stderr
        plan0 = read_state(state_path)["phases"]["plan"]
        assert {field: plan0[field] for field in PLAN_SPAWN_RECEIPT_FIELDS} == {
            "round": 0,
            "started_at": plan0["started_at"],
            "triggered_by": None,
            "engine": "claude",
            "model_requested": "plan-test-model",
            "prompt_sha256": digest0,
        }
        result = plan_cli("complete", "--verdict", "NEEDS_WORK")
        assert result.returncode == 0, result.stderr
        completed0 = read_state(state_path)["phases"]["plan"]
        assert all(field in completed0 for field in PLAN_RECEIPT_FIELDS)
        assert completed0["model_effective"] is None
        assert completed0["completed_at"] is not None
        assert completed0["duration_ms"] >= 0
        assert_plan_rejected_unchanged(
            "BLOCKED:plan-round-nonmonotonic: expected=1 supplied=0",
            "spawn", "--round", "0", "--triggered-by", "plan",
            "--engine", "claude", "--model", "plan-test-model",
            "--prompt-sha256", digest1,
        )
        assert_plan_rejected_unchanged(
            "BLOCKED:plan-round-nonmonotonic: expected=1 supplied=2",
            "spawn", "--round", "2", "--triggered-by", "plan",
            "--engine", "claude", "--model", "plan-test-model",
            "--prompt-sha256", digest1,
        )
        assert_plan_rejected_unchanged(
            "error: phases.plan re-spawn requires --triggered-by",
            "spawn", "--round", "1", "--engine", "claude",
            "--model", "plan-test-model", "--prompt-sha256", digest1,
        )
        result = plan_cli(
            "spawn", "--round", "1", "--triggered-by", "plan",
            "--engine", "claude", "--model", "plan-test-model",
            "--prompt-sha256", digest1,
        )
        assert result.returncode == 0, result.stderr
        plan1 = read_state(state_path)["phases"]["plan"]
        assert len(plan1["history"]) == 1
        assert set(plan1["history"][0]) == set(PLAN_RECEIPT_FIELDS)
        assert plan1["history"][0]["prompt_sha256"] == digest0
        assert plan1["prompt_sha256"] == digest1
        result = plan_cli("complete", "--verdict", "PASS")
        assert result.returncode == 0, result.stderr
        for supplied_round in (0, 1, 2):
            assert_plan_rejected_unchanged(
                "BLOCKED:plan-respawn-exhausted",
                "spawn", "--round", str(supplied_round),
                "--triggered-by", "plan", "--engine", "claude",
                "--model", "plan-test-model", "--prompt-sha256", digest1,
            )
        old_receipt = {
            "started_at": "2026-01-01T00:00:00.000Z",
            "verdict": "PASS",
            "completed_at": "2026-01-01T00:00:01.000Z",
            "duration_ms": 1000,
        }
        assert not is_plan_dispatch_receipt(old_receipt)
        assert is_plan_dispatch_receipt(read_state(state_path)["phases"]["plan"])

        # Iter-0112: schema-v3 PLAN output is an immutable authority receipt.
        plan_output = devlyn / "plan.md"
        plan_output.write_text("# Authorized plan\n- config/skills/x.py\n", encoding="utf-8")
        write_state(state_path, {"version": "3.0", "phases": {}})
        result = plan_cli(*required_spawn)
        assert result.returncode == 0, result.stderr
        result = plan_cli("complete", "--verdict", "PASS")
        assert result.returncode == 0, result.stderr
        sealed_plan_state = read_state(state_path)
        assert sealed_plan_state["phases"]["plan"]["output_sha256"] == hashlib.sha256(
            plan_output.read_bytes()
        ).hexdigest()
        plan_output.write_text(
            "# Authorized plan\n- config/skills/x.py\n- unapproved.py\n",
            encoding="utf-8",
        )
        before = state_path.read_bytes()
        blocked_plan_mutation = subprocess.run(
            [
                sys.executable, script, "--devlyn-dir", str(devlyn),
                "--phase", "verify", "spawn", "--round", "0",
            ],
            capture_output=True, text=True, check=False,
            encoding="utf-8",
        )
        assert blocked_plan_mutation.returncode != 0
        assert "BLOCKED:plan-integrity-mismatch" in blocked_plan_mutation.stderr
        assert state_path.read_bytes() == before
        assert_plan_rejected_unchanged(
            "error: phases.plan already completed — respawn before completing again",
            "complete", "--verdict", "NEEDS_WORK",
        )
        print("PASS iter-0112 PLAN output digest blocks mid-flight widening")

        write_state(state_path, {
            "phases": {
                "plan": {
                    "started_at": "2026-01-01T00:00:00.000Z",
                    "completed_at": None,
                    "duration_ms": None,
                    "round": 0,
                    "triggered_by": None,
                    "verdict": None,
                },
                "implement": None,
            }
        })
        result = plan_cli("complete", "--verdict", "BLOCKED")
        assert result.returncode == 0, result.stderr
        assert read_state(state_path)["phases"]["plan"]["verdict"] == "BLOCKED"
        write_state(state_path, {
            "phases": {
                "plan": {
                    "started_at": "2026-01-01T00:00:00.000Z",
                    "completed_at": None,
                    "duration_ms": None,
                    "round": 0,
                    "triggered_by": None,
                    "verdict": None,
                },
                "implement": None,
            }
        })
        result = plan_cli(
            "complete", "--verdict", "PASS", "--engine-session-log",
            str(devlyn / "missing-session.jsonl"),
        )
        assert result.returncode == 1, result.stderr
        assert "BLOCKED:model-attestation-failed" in result.stderr
        attestation_blocked = read_state(state_path)["phases"]["plan"]
        assert attestation_blocked["verdict"] == "BLOCKED"
        assert attestation_blocked["completed_at"] is not None
        assert attestation_blocked["model_effective"] is None
        legacy_state = {"phases": {"plan": old_receipt | {"round": 0}}}
        write_state(state_path, legacy_state)
        result = plan_cli(
            "spawn", "--round", "1", "--triggered-by", "plan",
            "--engine", "claude", "--model", "plan-test-model",
            "--prompt-sha256", digest1,
        )
        assert result.returncode == 0, result.stderr
        archived_legacy = read_state(state_path)["phases"]["plan"]["history"][0]
        assert archived_legacy == old_receipt
        print("PASS iter-0089 PLAN ledger: P-0089-1/2/6")

        write_state(state_path, {"phases": {}, "rounds": {"global": 0, "max_rounds": 4}})

        # Round 0: spawn -> complete.
        state = read_state(state_path)
        do_spawn(state, "implement", 0, None, "claude", None)
        write_state(state_path, state)
        round0_started = read_state(state_path)["phases"]["implement"]["started_at"]

        time.sleep(0.05)
        state = read_state(state_path)
        do_complete(state, "implement", "NEEDS_WORK", None, None, None, "test-model-id")
        write_state(state_path, state)
        entry = read_state(state_path)["phases"]["implement"]
        assert "history" not in entry, "history must be absent before re-entry"
        assert entry["completed_at"] is not None
        assert entry["duration_ms"] >= 0
        assert parse_iso(entry["completed_at"]) >= parse_iso(entry["started_at"])
        expected_ms = round((parse_iso(entry["completed_at"]) - parse_iso(entry["started_at"])).total_seconds() * 1000)
        assert entry["duration_ms"] == expected_ms, (entry["duration_ms"], expected_ms)

        # Round 1: VERIFY finding admits a fix-loop respawn.
        time.sleep(0.05)
        state = read_state(state_path)
        do_spawn(state, "verify", 0, None, None, None)
        state["phases"]["verify"].update({
            "completed_at": now_iso(), "verdict": "NEEDS_WORK",
            "merged": {"verdict": "NEEDS_WORK"},
        })
        do_spawn(state, "implement", 1, "verify", None, None)
        write_state(state_path, state)
        respawned = read_state(state_path)["phases"]["implement"]
        assert respawned["started_at"] != round0_started, "started_at must refresh on respawn"
        assert respawned["completed_at"] is None, "respawn must null stale completed_at"
        assert respawned["duration_ms"] is None, "respawn must null stale duration_ms"
        assert respawned["verdict"] is None, "respawn must null stale verdict"
        assert respawned["engine"] == "claude", "engine preserved when not re-supplied"
        assert respawned["round"] == 1
        assert respawned["triggered_by"] == "verify"
        assert len(respawned["history"]) == 1
        history0 = respawned["history"][0]
        assert history0["started_at"] == round0_started
        assert history0["verdict"] == "NEEDS_WORK"
        assert history0["completed_at"] == entry["completed_at"]
        assert history0["duration_ms"] == entry["duration_ms"]
        assert set(history0) == {"started_at", "verdict", "completed_at", "duration_ms"}

        time.sleep(0.05)
        state = read_state(state_path)
        do_complete(state, "implement", "PASS", ".devlyn/x.jsonl", None, None, None)
        write_state(state_path, state)
        final = read_state(state_path)["phases"]["implement"]
        assert final["verdict"] == "PASS"
        assert read_state(state_path)["process_evidence"] is None
        assert parse_iso(final["started_at"]) == parse_iso(respawned["started_at"])
        assert parse_iso(final["completed_at"]) >= parse_iso(final["started_at"])
        assert final["artifacts"]["findings_file"] == ".devlyn/x.jsonl"

        # Iter-0111 R2: successful IMPLEMENT completion and transition both
        # validate declared evidence before any lifecycle mutation, then bind
        # the exact manifest and stream digests into state. Legacy runs with no
        # declaration remain legal through the null carrier asserted above.
        evidence_work = devlyn / "process-evidence-state"
        evidence_devlyn = evidence_work / ".devlyn"
        evidence_spec_dir = evidence_work / "docs" / "evidence"
        evidence_devlyn.mkdir(parents=True)
        evidence_spec_dir.mkdir(parents=True)
        subprocess.run(["git", "init", "-q"], cwd=evidence_work, check=True)
        subprocess.run(["git", "config", "user.name", "Evidence test"], cwd=evidence_work, check=True)
        subprocess.run(["git", "config", "user.email", "evidence@example.invalid"], cwd=evidence_work, check=True)
        (evidence_work / ".gitignore").write_text(".devlyn/\n", encoding="utf-8")
        (evidence_spec_dir / "spec.md").write_text("# Evidence fixture\n", encoding="utf-8")
        (evidence_spec_dir / "spec.expected.json").write_text(json.dumps({
            "verification_commands": [{"cmd": "printf build-gate"}],
            "process_evidence": [{
                "id": "red-first",
                "phase": "implement",
                "cmd": "printf red-before-fix >&2; exit 7",
                "exit_code": 7,
                "stdout_contains": ["red-before-fix"],
            }],
        }) + "\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=evidence_work, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=evidence_work, check=True)
        evidence_state = {
            "run_id": "rs-state-evidence",
            "source": {"type": "spec", "spec_path": "docs/evidence/spec.md"},
            "rounds": {"global": 0, "max_rounds": 4},
            "phases": {"implement": None, "verify": None},
        }
        do_spawn(evidence_state, "implement", 0, None, "codex", None)
        evidence_state_path = evidence_devlyn / "pipeline.state.json"
        write_state(evidence_state_path, evidence_state)
        evidence_script = str(pathlib.Path(__file__).resolve())

        def evidence_state_cli(event: str, *event_args: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                [
                    sys.executable, evidence_script, "--devlyn-dir", ".devlyn",
                    "--phase", "implement", event, *event_args,
                ],
                cwd=evidence_work, capture_output=True, text=True, check=False,
                encoding="utf-8",
            )

        for event_args in (
            ("complete", "--verdict", "PASS"),
            (
                "transition", "--verdict", "PASS", "--next-phase", "verify",
                "--next-round", "0",
            ),
        ):
            before = evidence_state_path.read_bytes()
            result = evidence_state_cli(event_args[0], *event_args[1:])
            assert result.returncode != 0
            assert "BLOCKED:process-evidence-invalid" in result.stderr
            assert "missing" in result.stderr
            assert evidence_state_path.read_bytes() == before

        runner_script = str(pathlib.Path(__file__).with_name("process-evidence.py").resolve())
        captured = subprocess.run(
            [
                sys.executable, runner_script, "--devlyn-dir", ".devlyn", "run",
                "--phase", "implement", "--id", "red-first",
            ],
            cwd=evidence_work, capture_output=True, text=True, check=False,
            encoding="utf-8",
        )
        assert captured.returncode == 0, captured.stderr
        manifest_rel = loads_strict_json(captured.stdout)["manifest_path"]
        manifest = evidence_work / manifest_rel
        stderr_path = manifest.parent / "red-first.stderr"
        original_stderr = stderr_path.read_bytes()
        stderr_path.write_bytes(b"altered")
        before = evidence_state_path.read_bytes()
        altered = evidence_state_cli("complete", "--verdict", "PASS")
        assert altered.returncode != 0
        assert "digest or byte count mismatch" in altered.stderr
        assert evidence_state_path.read_bytes() == before
        stderr_path.write_bytes(original_stderr)
        transitioned = evidence_state_cli(
            "transition", "--verdict", "PASS", "--next-phase", "verify",
            "--next-round", "0",
        )
        assert transitioned.returncode == 0, transitioned.stderr
        sealed_state = read_state(evidence_state_path)
        carrier = sealed_state["process_evidence"][0]
        assert carrier["phase"] == "implement" and carrier["round"] == 0
        assert carrier["manifest"]["path"] == manifest_rel
        assert carrier["manifest"]["sha256"] == hashlib.sha256(manifest.read_bytes()).hexdigest()
        assert sealed_state["phases"]["implement"]["verdict"] == "PASS"
        assert sealed_state["phases"]["verify"]["started_at"] is not None
        assert sealed_state["phases"]["verify"]["pre_sha"] == subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=evidence_work, capture_output=True, text=True,
            check=True, encoding="utf-8",
        ).stdout.strip()
        print("PASS iter-0111 process evidence: completion/transition gate and state digest binding")

        # complete() before spawn() must fail loudly, not silently invent data.
        write_state(state_path, {"phases": {}})
        state = read_state(state_path)
        try:
            do_complete(state, "probe_derive", "PASS", None, None, None, None)
        except SystemExit as e:
            assert "never spawned" in str(e)
        else:
            raise AssertionError("complete() without a prior spawn() must raise")

        # F11 rs-20260721T065728Z receipt: VERIFY merge wrote BLOCKED, but the
        # caller skipped complete() before re-entry. Respawn must fail without
        # archiving the open span as history.
        f11_open = {
            "phases": {
                "verify": {
                    "started_at": "2026-07-21T07:08:11.684Z",
                    "completed_at": None,
                    "duration_ms": None,
                    "verdict": "BLOCKED",
                }
            }
        }
        before_f11 = json.dumps(f11_open, sort_keys=True)
        try:
            do_spawn(f11_open, "verify", 1, "verify", "codex", None)
        except SystemExit as e:
            assert "open span" in str(e) and "complete it before respawn" in str(e)
        else:
            raise AssertionError("respawn over an open F11 span must fail")
        assert json.dumps(f11_open, sort_keys=True) == before_f11
        assert "history" not in f11_open["phases"]["verify"]

        # Transition is one state transaction: a forced failure between its
        # validated halves leaves the authoritative state byte-identical.
        transition_state = {
            "phases": {
                "plan": {
                    "started_at": "2026-01-01T00:00:00.000Z",
                    "completed_at": None,
                    "duration_ms": None,
                    "round": 0,
                    "triggered_by": None,
                    "verdict": None,
                },
                "implement": None,
            }
        }
        write_state(state_path, transition_state)
        transition_before = state_path.read_bytes()

        def fail_between_halves() -> None:
            raise RuntimeError("forced transition failure")

        try:
            do_transition(
                transition_state, "plan", "final_report", "PASS", None, None, None, None, None, devlyn, 0, None, None, None, between=fail_between_halves,
            )
        except RuntimeError as exc:
            assert str(exc) == "forced transition failure"
        else:
            raise AssertionError("forced transition failure did not fire")
        assert state_path.read_bytes() == transition_before
        assert transition_state["phases"]["plan"]["completed_at"] is None
        print("PASS self-test transition atomicity: forced midpoint failure left state unchanged")

        attestation_state = copy.deepcopy(transition_state)
        attestation_state["phases"]["plan"]["model_requested"] = "wanted-model"
        attestation_log = devlyn / "transition-attestation.log"
        attestation_log.write_text(json.dumps({
            "modelUsage": {"other-model": {"inputTokens": 1}},
        }) + "\n", encoding="utf-8")
        write_state(state_path, attestation_state)
        attestation_before = state_path.read_bytes()
        try:
            do_transition(
                attestation_state, "plan", "final_report", "PASS", None, None, None, None, str(attestation_log), devlyn,
                0, None, None, None,
            )
        except SystemExit as exc:
            assert "BLOCKED:model-attestation-mismatch" in str(exc)
        else:
            raise AssertionError("transition accepted mismatched model attestation")
        assert state_path.read_bytes() == attestation_before
        print("PASS self-test transition attestation: mismatch left state unchanged")

        try:
            do_transition(
                transition_state, "plan", "verify", "PASS", None, None, None, None, None, devlyn, 0, None, "claude", None,
            )
        except SystemExit as exc:
            assert "illegal phase transition: plan -> verify" in str(exc)
        else:
            raise AssertionError("transition accepted an illegal phase edge")
        assert state_path.read_bytes() == attestation_before
        print("PASS self-test transition legal-edge guard: illegal edge left state unchanged")

        transitioned = do_transition(
            transition_state, "plan", "final_report", "PASS", None, None, None, None, None, devlyn, 0, None, None, None,
        )
        write_state(state_path, transitioned)
        assert transitioned["phases"]["plan"]["verdict"] == "PASS"
        assert transitioned["phases"]["plan"]["completed_at"] is not None
        assert transitioned["phases"]["final_report"]["started_at"] is not None
        assert transitioned["phases"]["final_report"]["verdict"] is None
        print("PASS self-test transition happy path: complete + spawn committed together")

        cli_state = {
            "phases": {
                "plan": {
                    "started_at": "2026-01-01T00:00:00.000Z",
                    "completed_at": None,
                    "duration_ms": None,
                    "round": 0,
                    "triggered_by": None,
                    "verdict": None,
                },
                "implement": None,
            }
        }
        write_state(state_path, cli_state)
        cli_transition = subprocess.run(
            [
                sys.executable, str(pathlib.Path(__file__).resolve()),
                "--devlyn-dir", str(devlyn), "--phase", "plan", "transition",
                "--verdict", "PASS", "--next-phase", "final_report",
                "--next-round", "0",
            ],
            capture_output=True, text=True,
            encoding="utf-8",
        )
        assert cli_transition.returncode == 0, cli_transition.stderr
        cli_receipt = loads_strict_json(cli_transition.stdout)
        assert cli_receipt["completed_phase"] == "plan"
        assert cli_receipt["completed_verdict"] == "PASS"
        assert cli_receipt["next_phase"] == "final_report"
        assert cli_receipt["state_sha256"] == hashlib.sha256(state_path.read_bytes()).hexdigest()
        print("PASS self-test transition CLI: machine-only JSON receipt")

        open_next = copy.deepcopy(transition_state)
        open_next["phases"]["final_report"] = {
            "started_at": "2026-01-01T00:00:01.000Z",
            "completed_at": None,
            "duration_ms": None,
            "round": 0,
            "triggered_by": None,
            "verdict": None,
        }
        write_state(state_path, open_next)
        open_next_before = state_path.read_bytes()
        try:
            do_transition(
                open_next, "plan", "final_report", "PASS", None, None, None, None, None, devlyn, 0, None, None, None,
            )
        except SystemExit as exc:
            assert "open span" in str(exc) and "complete it before respawn" in str(exc)
        else:
            raise AssertionError("transition opened a phase that already had an open span")
        assert state_path.read_bytes() == open_next_before
        print("PASS self-test transition open-span guard: rejected without mutation")

        # A completed FAIL span must be retained before a same-invocation respawn
        # resets the live record.
        write_state(state_path, {"phases": {}})
        state = read_state(state_path)
        do_spawn(state, "probe_derive", 0, None, None, None)
        write_state(state_path, state)
        time.sleep(0.05)
        state = read_state(state_path)
        do_complete(state, "probe_derive", "FAIL", None, None, None, None)
        write_state(state_path, state)
        failed_round = read_state(state_path)["phases"]["probe_derive"]
        state = read_state(state_path)
        do_spawn(state, "probe_derive", 0, None, None, None)
        write_state(state_path, state)
        respawned_fail = read_state(state_path)["phases"]["probe_derive"]
        assert respawned_fail["verdict"] is None
        assert len(respawned_fail["history"]) == 1
        assert respawned_fail["history"][0]["verdict"] == "FAIL"
        assert respawned_fail["history"][0]["completed_at"] == failed_round["completed_at"]

        # VERIFY flow: verify-merge-findings.py already wrote verdict; complete()
        # must preserve it when --verdict is omitted.
        write_state(state_path, {"phases": {}})
        state = read_state(state_path)
        do_spawn(state, "verify", 0, None, "claude", None)
        assert state["phases"]["verify"]["judge_durations_ms"] is None
        state["phases"]["verify"]["verdict"] = "PASS"
        state["phases"]["verify"]["sub_verdicts"] = {"mechanical": "PASS", "judge": "PASS"}
        state["phases"]["verify"]["judge_durations_ms"] = {"judge": 23, "pair_judge": None}
        write_state(state_path, state)
        state = read_state(state_path)
        do_complete(state, "verify", None, None, None, None, None)
        write_state(state_path, state)
        verify_entry = read_state(state_path)["phases"]["verify"]
        assert verify_entry["verdict"] == "PASS", "complete() must preserve pre-set verdict when omitted"
        assert verify_entry["sub_verdicts"] == {"mechanical": "PASS", "judge": "PASS"}
        assert verify_entry["judge_durations_ms"] == {"judge": 23, "pair_judge": None}
        assert verify_entry["completed_at"] is not None

        # An explicit --verdict for VERIFY must be rejected — its verdict is
        # owned exclusively by verify-merge-findings.py --write-state.
        state = read_state(state_path)
        try:
            do_complete(state, "verify", "PASS", None, None, None, None)
        except SystemExit as e:
            assert "owned by verify-merge-findings.py" in str(e)
        else:
            raise AssertionError("complete() must reject an explicit --verdict for VERIFY")
        trigger = {"eligible": True, "reasons": ["pair.default"], "skipped_reason": None}
        dispatch = {"path": ".devlyn/verify-judge.r0.dispatch.json", "sha256": "0" * 64, "bytes": 1}
        state["verify"] = {"coverage_failed": False, "pair_trigger": trigger}
        state["phases"]["verify"].update(pair_trigger=trigger, dispatch=dispatch, merged={"verdict": "PASS"},
                                         executions={"pair_judge": dispatch}, coverage_failed=False)
        do_spawn(state, "verify", 0, None, None, None)
        respawned = state["phases"]["verify"]
        assert respawned["judge_durations_ms"] is None and state["verify"]["pair_trigger"] is None
        assert not {"pair_trigger", "dispatch", "merged", "executions", "coverage_failed"} & set(respawned)
        assert respawned["history"][-1]["dispatch"] == dispatch and respawned["history"][-1]["pair_trigger"] == trigger

        # Non-VERIFY phases require --verdict explicitly; complete() must not
        # silently accept an unset verdict the way VERIFY's omit-to-preserve
        # flow does.
        write_state(state_path, {"phases": {}})
        state = read_state(state_path)
        do_spawn(
            state, "plan", 0, None, "claude", "plan-test-model",
            prompt_sha256=digest0,
        )
        write_state(state_path, state)
        state = read_state(state_path)
        try:
            do_complete(state, "plan", None, None, None, None, None)
        except SystemExit as e:
            assert "is required" in str(e)
        else:
            raise AssertionError("complete() with no --verdict on a non-VERIFY phase must raise")

        # VERIFY complete() before verify-merge-findings.py wrote a verdict
        # must also fail loudly, not silently pass with a null verdict.
        write_state(state_path, {"phases": {}})
        state = read_state(state_path)
        do_spawn(state, "verify", 0, None, None, None)
        write_state(state_path, state)
        state = read_state(state_path)
        try:
            do_complete(state, "verify", None, None, None, None, None)
        except SystemExit as e:
            assert "still null" in str(e)
        else:
            raise AssertionError("VERIFY complete() with no verdict anywhere must raise")

        # VERIFY respawn must clear the prior round's on-disk artifacts too —
        # a stale round-0 pair findings file would otherwise read as
        # current-round spawn evidence in verify-merge-findings.py
        # (iter-0060 R0 finding: current-round spawn evidence).
        for name in (
            "verify.findings.jsonl",
            "verify.pair.findings.jsonl",
            "verify.findings.judge-codex.jsonl",
            "verify-merged.findings.jsonl",
            "verify-merge.summary.json",
            "codex-judge.stdout",
            "claude-judge.stdout",
            "claude-judge.stderr",
            "pair-judge.summary.json",
        ):
            (devlyn / name).write_text("stale\n", encoding="utf-8")
        (devlyn / "codex-primary-judge.prompt.md").write_text("current\n", encoding="utf-8")
        (devlyn / "spec-verify.json").write_text("{}", encoding="utf-8")
        clear_verify_round_artifacts(devlyn)
        for name in (
            "verify.findings.jsonl",
            "verify.pair.findings.jsonl",
            "verify.findings.judge-codex.jsonl",
            "verify-merged.findings.jsonl",
            "verify-merge.summary.json",
            "codex-judge.stdout",
            "claude-judge.stdout",
            "claude-judge.stderr",
            "pair-judge.summary.json",
        ):
            assert not (devlyn / name).exists(), f"{name} must be cleared on VERIFY spawn"
        assert (devlyn / "codex-primary-judge.prompt.md").exists(), "judge prompts must survive VERIFY spawn"
        assert (devlyn / "spec-verify.json").exists(), "non-VERIFY-round files must survive"

        # Phase-gated IMPLEMENT: the writer derives `exec` from the PLAN's `### Phase <k>` blocks,
        # a passing phase advances it, the next phase's spawn keeps it and charges nothing, and
        # nothing spawns after the last phase passes. A single block is not phase-gated.
        write_state(state_path, {"phases": {}, "rounds": {"global": 0, "max_rounds": 4}})
        (devlyn / "plan.md").write_text("# PLAN\n## Execution phases\n### Phase 1 — a\n### Phase 2 — b\n### Phase 3 — c\n", encoding="utf-8")
        state = read_state(state_path)
        do_spawn(state, "implement", 0, None, "claude", None, devlyn=devlyn)
        assert state["phases"]["implement"]["exec"] == {"total": 3, "current": 1, "statuses": [None, None, None]}
        for round_, statuses in ((1, ["PASS", None, None]), (2, ["PASS", "PASS", None])):
            do_complete(state, "implement", "PASS", None, None, None, None)
            assert state["phases"]["implement"]["exec"] == {"total": 3, "current": round_ + 1, "statuses": statuses}
            do_spawn(state, "implement", round_, None, None, None, devlyn=devlyn)
            assert state["phases"]["implement"]["verdict"] is None and state["rounds"]["global"] == 0
        do_complete(state, "implement", "PASS", None, None, None, None)
        assert state["phases"]["implement"]["exec"] == {"total": 3, "current": 3, "statuses": ["PASS", "PASS", "PASS"]}
        assert [entry["verdict"] for entry in state["phases"]["implement"]["history"]] == ["PASS", "PASS"]
        try:
            do_spawn(state, "implement", 3, None, None, None, devlyn=devlyn)
        except SystemExit as exc:
            assert str(exc) == "BLOCKED:repair-edge-invalid", exc
        else:
            raise AssertionError("IMPLEMENT spawned after its last phase passed")
        # A phase-gate FAIL keeps current and its charged repair advances on PASS_WITH_ISSUES;
        # a VERIFY repair round and an attestation failure never advance progress.
        (devlyn / "plan.md").write_text("# PLAN\n## Execution phases\n### Phase 1 — a\n### Phase 2 — b\n", encoding="utf-8")
        gated = {"phases": {}, "rounds": {"global": 0, "max_rounds": 4}}
        do_spawn(gated, "implement", 0, None, "claude", None, devlyn=devlyn)
        do_complete(gated, "implement", "FAIL", None, None, None, None)
        assert gated["phases"]["implement"]["exec"] == {"total": 2, "current": 1, "statuses": ["FAIL", None]}
        do_spawn(gated, "implement", 1, None, None, None, devlyn=devlyn)
        assert gated["rounds"]["global"] == 1
        do_complete(gated, "implement", "PASS_WITH_ISSUES", None, None, None, None)
        assert gated["phases"]["implement"]["exec"] == {"total": 2, "current": 2, "statuses": ["PASS", None]}
        repair = json.loads(json.dumps(gated))
        repair["phases"]["implement"]["exec"] = {"total": 2, "current": 2, "statuses": ["PASS", None]}
        repair["phases"]["implement"].update(started_at=now_iso(), completed_at=None, verdict=None, triggered_by="verify")
        do_complete(repair, "implement", "PASS", None, None, None, None)
        assert repair["phases"]["implement"]["exec"]["statuses"] == ["PASS", None], "a VERIFY repair advanced progress"
        attested = json.loads(json.dumps(gated))
        attested["phases"]["implement"].update(started_at=now_iso(), completed_at=None, verdict=None, triggered_by=None)
        bad_session = devlyn / "no-model.jsonl"
        bad_session.write_text("no model evidence\n", encoding="utf-8")
        failure = do_complete(attested, "implement", "PASS", None, None, None, None, str(bad_session))
        assert failure and attested["phases"]["implement"]["verdict"] == "BLOCKED"
        assert attested["phases"]["implement"]["exec"]["statuses"] == ["PASS", None], "a failed attestation advanced progress"
        bad_session.unlink()
        planned = {"phases": {}, "rounds": {"global": 0, "max_rounds": 4}}
        do_spawn(planned, "implement", 0, "plan", "claude", None, devlyn=devlyn)
        do_complete(planned, "implement", "PASS", None, None, None, None)
        assert planned["phases"]["implement"]["exec"]["statuses"] == ["PASS", None], "a PLAN-triggered phase did not advance"
        (devlyn / "plan.md").write_text("# PLAN\n## Execution phases\n### Phase 1 — only\n", encoding="utf-8")
        single = {"phases": {}}
        do_spawn(single, "implement", 0, None, "claude", None, devlyn=devlyn)
        assert "exec" not in single["phases"]["implement"]
        # Only real headings under `## Execution phases` count; fenced examples and other sections never do.
        example = b"## Acceptance\n```md\n### Phase 1 \xe2\x80\x94 a\n### Phase 2 \xe2\x80\x94 b\n```\n### Phase 3 \xe2\x80\x94 c\n"
        assert execution_phase_count(example) == 0
        assert execution_phase_count(b"## Execution phases\n~~~\n### Phase 1\n~~~\n### Phase 2 \xe2\x80\x94 x\n## Risks\n### Phase 3\n") == 1
        assert execution_phase_count(b"````md\n```\n## Execution phases\n### Phase 1\n### Phase 2\n````\n") == 0
        assert execution_phase_count(b"```\n``` not a close\n## Execution phases\n### Phase 1\n### Phase 2\n```\n") == 0
        assert execution_phase_count(b"```\n~~~\n## Execution phases\n### Phase 1\n### Phase 2\n```\n") == 0
        (devlyn / "plan.md").write_bytes(example + b"## Execution phases\n### Phase 1 \xe2\x80\x94 only\n")
        examples = {"phases": {}}
        do_spawn(examples, "implement", 0, None, "claude", None, devlyn=devlyn)
        assert "exec" not in examples["phases"]["implement"]
        (devlyn / "plan.md").unlink()

        # Existing history is append-only; a respawn must not clobber prior
        # entries that were already preserved from older rounds.
        write_state(state_path, {
            "rounds": {"global": 0, "max_rounds": 4},
            "phases": {
                "implement": {
                    "started_at": "2026-01-01T00:00:02.000Z",
                    "completed_at": "2026-01-01T00:00:03.000Z",
                    "duration_ms": 1000,
                    "round": 2,
                    "triggered_by": "verify",
                    "verdict": "FAIL",
                    "exec": {"total": 2, "current": 2, "statuses": ["PASS", "FAIL"]},
                    "engine": "codex",
                    "history": [{
                        "started_at": "2026-01-01T00:00:00.000Z",
                        "verdict": "FAIL",
                        "completed_at": "2026-01-01T00:00:01.000Z",
                        "duration_ms": 1000,
                    }],
                }
            }
        })
        state = read_state(state_path)
        do_spawn(state, "implement", 3, None, None, None)
        write_state(state_path, state)
        history_preserved = read_state(state_path)["phases"]["implement"]["history"]
        assert len(history_preserved) == 2
        assert history_preserved[0]["started_at"] == "2026-01-01T00:00:00.000Z"
        assert history_preserved[1]["started_at"] == "2026-01-01T00:00:02.000Z"

        # Effective model evidence: handwritten headers are not provenance;
        # canonical rollout JSONL and Claude wrapper output remain accepted.
        header_log = devlyn / "codex-build.log"
        header_log.write_text("session\nmodel: gpt-5.6-sol\n", encoding="utf-8")
        try:
            parse_effective_model(header_log)
        except ValueError as exc:
            assert "no effective-model evidence" in str(exc)
        else:
            raise AssertionError("plaintext model header was accepted as provenance")
        rollout_log = devlyn / "rollout.jsonl"
        rollout_log.write_text(json.dumps({
            "type": "turn_context", "payload": {"model": "gpt-5.6-terra"},
        }) + "\n", encoding="utf-8")
        assert parse_effective_model(rollout_log) == "gpt-5.6-terra"
        claude_log = devlyn / "claude-result.json"

        def claude_wrapper(primary_usage, entries):
            wrapper = {"modelUsage": {}}
            if primary_usage is not None:
                wrapper["usage"] = dict(zip((
                    "input_tokens", "output_tokens", "cache_read_input_tokens",
                    "cache_creation_input_tokens",
                ), primary_usage))
            for model, entry_usage, metadata in entries:
                entry = dict(zip((
                    "inputTokens", "outputTokens", "cacheReadInputTokens",
                    "cacheCreationInputTokens",
                ), entry_usage))
                entry.update(metadata)
                wrapper["modelUsage"][model] = entry
            return wrapper

        oversized_counter = 10 ** 400
        claude_selector_rows = (
            (
                "singleton",
                {"modelUsage": {"claude-alpha-1": {"inputTokens": 1}}},
                "claude-alpha-1",
            ),
            (
                "opus-primary",
                claude_wrapper(
                    (2854, 9927, 1095180, 73889),
                    (
                        ("claude-" "haiku-4-5-20251001", (4106, 14, 0, 0), {
                            "costUSD": 0.004176,
                        }),
                        ("claude-" "opus-5[1m]", (2854, 9927, 1095180, 73889), {
                            "costUSD": 1.5489249999999999,
                            "canonicalModel": "claude-" "opus-5",
                        }),
                    ),
                ),
                "claude-" "opus-5[1m]",
            ),
            (
                "fable-primary",
                claude_wrapper(
                    (8068, 26740, 403950, 76656),
                    (
                        ("claude-" "haiku-4-5-20251001", (2246, 22, 0, 0), {
                            "costUSD": 0.002356,
                        }),
                        ("claude-" "fable-5", (8068, 26740, 403950, 76656), {
                            "costUSD": 3.35475,
                            "canonicalModel": "claude-" "fable-5",
                        }),
                    ),
                ),
                "claude-" "fable-5",
            ),
            (
                "rank-confound",
                claude_wrapper(
                    (3, 5, 7, 11),
                    (
                        ("larger-auxiliary", (300000, 500000, 700000, 1100000), {
                            "costUSD": 999.0,
                        }),
                        ("expected-primary", (3, 5, 7, 11), {"costUSD": 0.01}),
                    ),
                ),
                "expected-primary",
            ),
            (
                "oversized-integer",
                claude_wrapper(
                    (oversized_counter, 5, 7, 11),
                    (
                        ("oversized-primary", (oversized_counter, 5, 7, 11), {}),
                        ("auxiliary", (3, 5, 7, 11), {}),
                    ),
                ),
                "oversized-primary",
            ),
            (
                "zero-match",
                claude_wrapper(
                    (1, 2, 3, 4),
                    (("model-a", (10, 2, 3, 4), {}), ("model-b", (1, 20, 3, 4), {})),
                ),
                ValueError,
            ),
            (
                "duplicate-match",
                claude_wrapper(
                    (1, 2, 3, 4),
                    (("model-a", (1, 2, 3, 4), {}), ("model-b", (1, 2, 3, 4), {})),
                ),
                ValueError,
            ),
            (
                "missing-top-level-usage",
                claude_wrapper(
                    None,
                    (("model-a", (1, 2, 3, 4), {}), ("model-b", (5, 6, 7, 8), {})),
                ),
                ValueError,
            ),
            (
                "malformed-top-level-float",
                claude_wrapper(
                    (1.0, 2, 3, 4),
                    (("model-a", (1, 2, 3, 4), {}), ("model-b", (5, 6, 7, 8), {})),
                ),
                ValueError,
            ),
            (
                "malformed-top-level-negative",
                claude_wrapper(
                    (-1, 2, 3, 4),
                    (("model-a", (-1, 2, 3, 4), {}), ("model-b", (5, 6, 7, 8), {})),
                ),
                ValueError,
            ),
            (
                "malformed-entry-counter",
                claude_wrapper(
                    (1, 2, 3, 4),
                    (("model-a", (1, 2, 3, 4), {}), ("model-b", (True, 20, 30, 40), {})),
                ),
                ValueError,
            ),
        )
        for row_name, wrapper, expected in claude_selector_rows:
            claude_log.write_text(json.dumps(wrapper) + "\n", encoding="utf-8")
            if expected is ValueError:
                try:
                    parse_effective_model(claude_log)
                except ValueError:
                    pass
                else:
                    raise AssertionError(f"Claude selector accepted {row_name}")
            else:
                assert parse_effective_model(claude_log) == expected, row_name

        claude_log.write_text(
            json.dumps(claude_selector_rows[-1][1]) + "\n", encoding="utf-8"
        )
        write_state(state_path, {"phases": {}})
        state = read_state(state_path)
        do_spawn(
            state, "plan", 0, None, "claude", "claude-default",
            prompt_sha256=digest0,
        )
        malformed = do_complete(
            state, "plan", "PASS", None, None, None, None, str(claude_log)
        )
        assert malformed and "model-attestation-failed" in malformed
        assert state["phases"]["plan"]["model_effective"] is None
        assert state["phases"]["plan"]["verdict"] == "BLOCKED"

        # Requested/effective drift is a persisted, fail-closed attestation.
        write_state(state_path, {"phases": {}})
        state = read_state(state_path)
        do_spawn(state, "implement", 0, None, "codex", "gpt-5.5")
        mismatch = do_complete(
            state, "implement", "PASS", None, None, None, None, str(rollout_log)
        )
        mismatched = state["phases"]["implement"]
        assert mismatch and "model-attestation-mismatch" in mismatch
        assert mismatched["model_requested"] == "gpt-5.5"
        assert mismatched["model_effective"] == "gpt-5.6-terra"
        assert mismatched["verdict"] == "BLOCKED"

        claude_log.write_text(
            json.dumps(claude_selector_rows[1][1]) + "\n", encoding="utf-8"
        )
        write_state(state_path, {"phases": {}})
        state = read_state(state_path)
        # Claude worker evidence keeps the requested/effective mismatch guard.
        state["phases"]["implement"] = {
            "started_at": now_iso(), "completed_at": None, "round": 0,
            "engine": "claude", "model_requested": "claude-" "opus-5",
        }
        mismatch = do_complete(
            state, "implement", "PASS", None, None, None, None, str(claude_log)
        )
        mismatched = state["phases"]["implement"]
        assert mismatch and "model-attestation-mismatch" in mismatch
        assert mismatched["model_requested"] == "claude-" "opus-5"
        assert mismatched["model_effective"] == "claude-" "opus-5[1m]"
        assert mismatched["verdict"] == "BLOCKED"

        # A retained mutation-worker session makes the completion flag
        # mandatory; without a retained file, null remains legal.
        retained_log = devlyn / "implement.worker-session.0.jsonl"
        retained_log.write_text(json.dumps({
            "type": "turn_context", "payload": {"model": "gpt-5.6-terra"},
        }) + "\n", encoding="utf-8")
        write_state(state_path, {"phases": {}})
        state = read_state(state_path)
        do_spawn(state, "implement", 0, None, "codex", "gpt-5.6-terra")
        omitted = do_complete(
            state, "implement", "PASS", None, None, None, None,
            devlyn=devlyn,
        )
        assert omitted and "model-attestation-failed" in omitted
        assert str(retained_log) in omitted
        assert state["phases"]["implement"]["model_effective"] is None
        assert state["phases"]["implement"]["verdict"] == "BLOCKED"

        write_state(state_path, {"phases": {}})
        state = read_state(state_path)
        do_spawn(state, "implement", 0, None, "codex", "gpt-5.6-terra")
        assert do_complete(
            state, "implement", "PASS", None, None, None, None,
            str(retained_log), devlyn=devlyn,
        ) is None
        assert state["phases"]["implement"]["model_effective"] == "gpt-5.6-terra"
        assert state["phases"]["implement"]["verdict"] == "PASS"

        receipt_work = devlyn / "receipt-work"
        receipt_devlyn = receipt_work / ".devlyn"
        receipt_devlyn.mkdir(parents=True)
        receipt_prompt = receipt_devlyn / "implement.prompt.0"
        receipt_prompt.write_text("implement exactly\n", encoding="utf-8")
        receipt_session = receipt_devlyn / "implement.worker-session.0.jsonl"
        receipt_session.write_text('{"type":"thread.started"}\n', encoding="utf-8")
        receipt_path = receipt_devlyn / "implement.invocation.0.json"
        receipt_model = "gpt-5.6-sol"
        receipt_prompt_sha = hashlib.sha256(receipt_prompt.read_bytes()).hexdigest()
        inherited_engine_state = {
            "version": "3.0",
            "run_id": "rs-inherited-engine",
            "engine": "codex",
            "phases": {"implement": None},
        }
        try:
            do_spawn(
                inherited_engine_state, "implement", 0, None, None, None,
                prompt_sha256=receipt_prompt_sha, devlyn=receipt_devlyn,
            )
        except SystemExit as exc:
            assert "spawn requires --model" in str(exc)
        else:
            raise AssertionError("schema-v3 inherited Codex engine accepted no model")
        do_spawn(
            inherited_engine_state, "implement", 0, None, None, receipt_model,
            prompt_sha256=receipt_prompt_sha, devlyn=receipt_devlyn,
        )
        assert inherited_engine_state["phases"]["implement"]["engine"] == "codex"
        receipt_state = {
            "version": "3.0",
            "run_id": "rs-invocation-state",
            "engine": "codex",
            "phases": {"implement": None},
        }
        do_spawn(
            receipt_state, "implement", 0, None, "codex", receipt_model,
            prompt_sha256=receipt_prompt_sha, devlyn=receipt_devlyn,
        )
        receipt_runner = invocation_receipt_module()
        receipt_runner.start_receipt(
            receipt_work, receipt_path, receipt_state["run_id"], "implement", 0,
            str(receipt_prompt), str(receipt_session),
            ["--json", "-C", str(receipt_work), "-s", "workspace-write", "-m", receipt_model,
             "-c", "sandbox_workspace_write.network_access=false", "implement exactly"],
        )
        receipt_runner.finish_receipt(receipt_work, receipt_path, 0)
        rerouted_state = copy.deepcopy(receipt_state)
        assert do_complete(
            receipt_state, "implement", "PASS", None, None, None, None,
            str(receipt_session), devlyn=receipt_devlyn, work=receipt_work,
        ) is None
        receipt_entry = receipt_state["phases"]["implement"]
        assert receipt_entry["model_effective"] is None
        assert receipt_entry["model_requested"] == receipt_model
        assert receipt_entry["invocation_receipt"]["path"] == (
            ".devlyn/implement.invocation.0.json"
        )

        # A native reroute remains a failed phase even after a successful terminal event.
        receipt_session.write_text(
            '{"type":"item.completed","item":{"type":"error",'
            '"message":"model rerouted: gpt-5.6-sol -> other (Policy)"}}\n'
            '{"type":"turn.completed"}\n', encoding="utf-8",
        )
        receipt_path.unlink()
        receipt_runner.start_receipt(
            receipt_work, receipt_path, rerouted_state["run_id"], "implement", 0,
            str(receipt_prompt), str(receipt_session),
            ["--json", "-C", str(receipt_work), "-s", "workspace-write", "-m", receipt_model,
             "-c", "sandbox_workspace_write.network_access=false", "implement exactly"],
        )
        receipt_runner.finish_receipt(receipt_work, receipt_path, 0)
        reroute_error = do_complete(
            rerouted_state, "implement", "PASS", None, None, None, None,
            str(receipt_session), devlyn=receipt_devlyn, work=receipt_work,
        )
        assert reroute_error and "model reroute" in reroute_error
        assert rerouted_state["phases"]["implement"]["verdict"] == "BLOCKED"
        try:
            do_spawn(rerouted_state, "implement", 1, None, "codex", receipt_model,
                     prompt_sha256=receipt_prompt_sha, devlyn=receipt_devlyn)
        except SystemExit as exc:
            assert str(exc) == "BLOCKED:repair-edge-invalid"
        else:
            raise AssertionError("BLOCKED IMPLEMENT was admitted as a product repair")

        plan_prompt = receipt_devlyn / "plan.prompt.0"
        plan_prompt.write_text("plan exactly\n", encoding="utf-8")
        plan_session = receipt_devlyn / "plan.worker-session.0.jsonl"
        plan_session.write_text('{"type":"thread.started"}\n', encoding="utf-8")
        plan_path = receipt_devlyn / "plan.invocation.0.json"
        (receipt_devlyn / "plan.md").write_text("## Files to touch\n", encoding="utf-8")
        plan_model = "gpt-5.6-sol"
        plan_prompt_sha = hashlib.sha256(plan_prompt.read_bytes()).hexdigest()
        plan_state = {
            "version": "3.0",
            "run_id": "rs-plan-invocation",
            "engine": "codex",
            "phases": {"plan": None},
        }
        do_spawn(
            plan_state, "plan", 0, None, "codex", plan_model,
            prompt_sha256=plan_prompt_sha, devlyn=receipt_devlyn,
        )
        receipt_runner.start_receipt(
            receipt_work, plan_path, plan_state["run_id"], "plan", 0,
            str(plan_prompt), str(plan_session),
            ["--json", "-C", str(receipt_work), "-s", "workspace-write",
             "-m", plan_model, "-c",
             "sandbox_workspace_write.network_access=false", "plan exactly"],
        )
        receipt_runner.finish_receipt(receipt_work, plan_path, 0)
        assert do_complete(
            plan_state, "plan", "PASS", None, None, None, None,
            str(plan_session), devlyn=receipt_devlyn, work=receipt_work,
        ) is None
        plan_entry = plan_state["phases"]["plan"]
        assert plan_entry["model_effective"] is None
        assert plan_entry["model_requested"] == plan_model
        assert plan_entry["invocation_receipt"]["path"] == ".devlyn/plan.invocation.0.json"
        assert plan_entry["output_sha256"] == hashlib.sha256(
            (receipt_devlyn / "plan.md").read_bytes()
        ).hexdigest()
        plan_prompt_1 = receipt_devlyn / "plan.prompt.1"
        plan_prompt_1.write_text("replan exactly\n", encoding="utf-8")
        plan_session_1 = receipt_devlyn / "plan.worker-session.1.jsonl"
        plan_session_1.write_text('{"type":"thread.started"}\n', encoding="utf-8")
        plan_path_1 = receipt_devlyn / "plan.invocation.1.json"
        plan_prompt_sha_1 = hashlib.sha256(plan_prompt_1.read_bytes()).hexdigest()
        do_spawn(
            plan_state, "plan", 1, "plan", "codex", plan_model,
            prompt_sha256=plan_prompt_sha_1, devlyn=receipt_devlyn,
        )
        plan_history = plan_state["phases"]["plan"]["history"]
        assert plan_history[0]["invocation_receipt"]["path"] == (
            ".devlyn/plan.invocation.0.json"
        )
        assert "invocation_receipt" not in plan_state["phases"]["plan"]
        receipt_runner.start_receipt(
            receipt_work, plan_path_1, plan_state["run_id"], "plan", 1,
            str(plan_prompt_1), str(plan_session_1),
            ["--json", "-C", str(receipt_work), "-s", "workspace-write",
             "-m", plan_model, "-c",
             "sandbox_workspace_write.network_access=false", "replan exactly"],
        )
        receipt_runner.finish_receipt(receipt_work, plan_path_1, 0)
        assert do_complete(
            plan_state, "plan", "PASS", None, None, None, None,
            str(plan_session_1), devlyn=receipt_devlyn, work=receipt_work,
        ) is None
        assert plan_state["phases"]["plan"]["invocation_receipt"]["path"] == (
            ".devlyn/plan.invocation.1.json"
        )

        confused_state = {
            "version": "3.0",
            "run_id": "rs-invocation-confused",
            "engine": "codex",
            "phases": {"implement": None},
        }
        do_spawn(
            confused_state, "implement", 0, None, "codex", receipt_model,
            prompt_sha256=receipt_prompt_sha, devlyn=receipt_devlyn,
        )
        confused_before = copy.deepcopy(confused_state)
        try:
            do_complete(
                confused_state, "implement", "PASS", None, None,
                "claude", receipt_model, str(receipt_session),
                devlyn=receipt_devlyn, work=receipt_work,
            )
        except SystemExit as exc:
            assert "cannot replace spawn engine" in str(exc)
        else:
            raise AssertionError("completion replaced a Codex spawn with Claude attestation")
        assert confused_state == confused_before
        try:
            do_complete(
                confused_state, "implement", "PASS", None, None,
                None, "other-model", str(receipt_session),
                devlyn=receipt_devlyn, work=receipt_work,
            )
        except SystemExit as exc:
            assert "cannot replace requested model" in str(exc)
        else:
            raise AssertionError("completion replaced the requested Codex model")
        assert confused_state == confused_before

        wrong_path_state = {
            "version": "3.0",
            "run_id": "rs-invocation-wrong-path",
            "engine": "codex",
            "phases": {"implement": None},
        }
        do_spawn(
            wrong_path_state, "implement", 0, None, "codex", receipt_model,
            prompt_sha256=receipt_prompt_sha, devlyn=receipt_devlyn,
        )
        arbitrary_log = receipt_devlyn / "handwritten.log"
        arbitrary_log.write_text(f"model: {receipt_model}\n", encoding="utf-8")
        wrong_path_error = do_complete(
            wrong_path_state, "implement", "PASS", None, None, None, None,
            str(arbitrary_log), devlyn=receipt_devlyn, work=receipt_work,
        )
        assert wrong_path_error and "canonical phase/round session" in wrong_path_error
        assert wrong_path_state["phases"]["implement"]["verdict"] == "BLOCKED"
        print("PASS iter-0112 canonical Codex invocation receipt and session ownership")

        # Iter-0121: rs-20260906T173436Z-5a086a70590e exited 1 with an
        # empty canonical session and no plan. Exercise the real CLI writes.
        receipt_state_path = receipt_devlyn / "pipeline.state.json"
        missing_plan_output = receipt_devlyn / "plan.md"
        missing_plan_output.unlink()
        plan_session.write_bytes(b"")
        plan_path.unlink()
        receipt_runner.start_receipt(
            receipt_work, plan_path, plan_state["run_id"], "plan", 0,
            str(plan_prompt), str(plan_session),
            ["--json", "-C", str(receipt_work), "-s", "workspace-write",
             "-m", plan_model, "-c",
             "sandbox_workspace_write.network_access=false", "plan exactly"],
        )
        receipt_runner.finish_receipt(receipt_work, plan_path, 1)
        failed_receipt_bytes = plan_path.read_bytes()

        def receipt_cli(phase: str, *event_args: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                [sys.executable, script, "--devlyn-dir", str(receipt_devlyn),
                 "--phase", phase, *event_args],
                cwd=receipt_work, capture_output=True, text=True, check=False,
                encoding="utf-8",
            )

        write_state(receipt_state_path, {
            "version": "3.0", "run_id": plan_state["run_id"],
            "engine": "codex", "phases": {},
        })
        result = receipt_cli(
            "plan", "spawn", "--round", "0", "--engine", "codex",
            "--model", plan_model, "--prompt-sha256", plan_prompt_sha,
        )
        assert result.returncode == 0, result.stderr
        open_plan_bytes = receipt_state_path.read_bytes()
        blocked_args = (
            "--verdict", "BLOCKED", "--engine-session-log", str(plan_session),
        )
        result = receipt_cli("plan", "complete", *blocked_args)
        assert result.returncode == 1, result.stderr
        assert "BLOCKED:invocation-receipt-invalid: Codex invocation exited 1" in result.stderr, result.stderr
        blocked_plan = read_state(receipt_state_path)["phases"]["plan"]
        assert blocked_plan["verdict"] == "BLOCKED"
        assert blocked_plan["output_sha256"] is None
        assert blocked_plan["model_effective"] is None
        assert blocked_plan["completed_at"] is not None
        assert blocked_plan["duration_ms"] == round((
            parse_iso(blocked_plan["completed_at"]) - parse_iso(blocked_plan["started_at"])
        ).total_seconds() * 1000)
        assert blocked_plan["duration_ms"] >= 0
        assert not os.path.lexists(missing_plan_output)
        assert plan_path.read_bytes() == failed_receipt_bytes
        print("PASS iter-0121 failed PLAN worker persists BLOCKED timing/null output and receipt error")

        for phase, event_args in [
            (phase, (
                "spawn", "--round", "1" if phase == "plan" else "0",
                "--triggered-by", "plan", "--engine", "codex",
                "--model", plan_model, "--prompt-sha256", plan_prompt_sha,
            )) for phase in sorted(PHASE_NAMES - {"final_report"})
        ] + [
            ("implement", ("durability-enforce", "--round", "1")),
        ]:
            before = receipt_state_path.read_bytes()
            result = receipt_cli(phase, *event_args)
            assert result.returncode == 1, (phase, event_args, result.stderr)
            assert "BLOCKED:plan-output-missing" in result.stderr, (phase, event_args, result.stderr)
            assert receipt_state_path.read_bytes() == before
        result = receipt_cli("final_report", "spawn", "--round", "0")
        assert result.returncode == 0, result.stderr
        blocked_report = receipt_devlyn / "final-report.md"
        (receipt_devlyn / "finish-gate.summary.json").write_text('{"exit": 0}\n', encoding="utf-8")
        result = receipt_cli("final_report", "complete", "--verdict", "BLOCKED:invocation-receipt-invalid",
                             "--detail", "PLAN invocation failed; no PLAN output was produced.")
        assert result.returncode == 0, result.stderr
        terminal_state = read_state(receipt_state_path)
        assert terminal_state["phases"]["plan"] == blocked_plan
        assert terminal_state["phases"]["final_report"]["completed_at"] is not None
        assert terminal_state["phases"]["final_report"]["verdict"] == "BLOCKED:invocation-receipt-invalid"
        assert "detail: PLAN invocation failed" in blocked_report.read_text(encoding="utf-8")
        assert terminal_state["phases"]["final_report"]["output_sha256"] == hashlib.sha256(blocked_report.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as archive_tmp:
            archive_work = pathlib.Path(archive_tmp)
            archive_devlyn = archive_work / ".devlyn"
            archive_devlyn.mkdir()
            retained = (receipt_state_path, blocked_report, plan_path, plan_prompt, plan_session)
            for source in retained:
                shutil.copy2(source, archive_devlyn / source.name)
            archived = subprocess.run(
                [sys.executable, str(pathlib.Path(script).with_name("archive_run.py"))],
                cwd=archive_work, capture_output=True, text=True,
                encoding="utf-8",
            )
            assert archived.returncode == 0, archived.stderr
            destination = archive_devlyn / "runs" / terminal_state["run_id"]
            assert not (archive_devlyn / "pipeline.state.json").exists()
            assert not (destination / "plan.md").exists()
            assert all((destination / source.name).read_bytes() == source.read_bytes() for source in retained)
        print("PASS iter-0121 missing-output BLOCKED permits final closure and refuses all work spawns/special events")

        # Non-BLOCKED requests cannot obtain the exception via failed attestation.
        for verdict in sorted(VALID_VERDICTS - {"BLOCKED"}):
            receipt_state_path.write_bytes(open_plan_bytes)
            result = receipt_cli(
                "plan", "complete", "--verdict", verdict,
                "--engine-session-log", str(plan_session),
            )
            assert result.returncode == 1, (verdict, result.stderr)
            assert "BLOCKED:plan-integrity-invalid" in result.stderr
            assert receipt_state_path.read_bytes() == open_plan_bytes
        for next_phase in ("implement", "probe_derive", "final_report"):
            result = receipt_cli(
                "plan", "transition", *blocked_args, "--next-phase", next_phase,
                "--next-round", "0", "--next-engine", "claude",
            )
            assert result.returncode in (1, 2), result.stderr
            assert ("Codex invocation exited 1" if next_phase == "final_report" else "illegal phase transition") in result.stderr
            assert receipt_state_path.read_bytes() == open_plan_bytes
        plan_path.write_text("{", encoding="utf-8")
        result = receipt_cli("plan", "complete", *blocked_args)
        assert result.returncode == 1, result.stderr
        assert "BLOCKED:invocation-receipt-invalid" in result.stderr
        malformed_plan = read_state(receipt_state_path)["phases"]["plan"]
        assert malformed_plan["verdict"] == "BLOCKED"
        assert malformed_plan["model_effective"] is None
        assert malformed_plan["output_sha256"] is None
        assert malformed_plan["completed_at"] is not None

        # Even attested BLOCKED completion cannot transition into more work.
        plan_path.unlink()
        receipt_runner.start_receipt(
            receipt_work, plan_path, plan_state["run_id"], "plan", 0,
            str(plan_prompt), str(plan_session),
            ["--json", "-C", str(receipt_work), "-s", "workspace-write",
             "-m", plan_model, "-c",
             "sandbox_workspace_write.network_access=false", "plan exactly"],
        )
        receipt_runner.finish_receipt(receipt_work, plan_path, 0)
        receipt_state_path.write_bytes(open_plan_bytes)
        for next_phase in ("implement", "probe_derive"):
            result = receipt_cli(
                "plan", "transition", *blocked_args, "--next-phase", next_phase,
                "--next-round", "0", "--next-engine", "claude",
            )
            assert result.returncode == 1, result.stderr
            assert "illegal phase transition" in result.stderr
            assert receipt_state_path.read_bytes() == open_plan_bytes
        result = receipt_cli(
            "plan", "transition", *blocked_args, "--next-phase", "final_report",
            "--next-round", "0",
        )
        assert result.returncode == 0, result.stderr
        absent_transition_bytes = receipt_state_path.read_bytes()
        assert read_state(receipt_state_path)["phases"]["plan"]["model_effective"] is None
        print("PASS iter-0121 non-BLOCKED output requirement, malformed receipt and atomic transitions")

        for path_kind in ("file", "directory", "dangling-symlink", "unreadable"):
            if path_kind == "directory":
                missing_plan_output.mkdir()
            elif path_kind == "dangling-symlink":
                missing_plan_output.symlink_to(receipt_devlyn / "missing-target")
            else:
                missing_plan_output.write_bytes(b"## Files to touch\n")
                if path_kind == "unreadable":
                    missing_plan_output.chmod(0)
            try:
                receipt_state_path.write_bytes(absent_transition_bytes)
                # Bytes at the never-bound path make the PLAN unverifiable: closure derives that, never a bare BLOCKED.
                result = receipt_cli("final_report", "complete", "--verdict", "BLOCKED")
                assert result.returncode == 1, (path_kind, result.stderr)
                assert "contradicts the evidence-derived BLOCKED:phase-input-invalid" in result.stderr
                assert receipt_state_path.read_bytes() == absent_transition_bytes
                if path_kind in {"directory", "dangling-symlink"} or (
                    path_kind == "unreadable" and not os.access(missing_plan_output, os.R_OK)
                ):
                    receipt_state_path.write_bytes(open_plan_bytes)
                    result = receipt_cli("plan", "complete", *blocked_args)
                    assert result.returncode == 1, (path_kind, result.stderr)
                    assert "BLOCKED:plan-integrity-invalid" in result.stderr
                    assert receipt_state_path.read_bytes() == open_plan_bytes
            finally:
                if path_kind == "directory":
                    missing_plan_output.rmdir()
                else:
                    if path_kind == "unreadable":
                        missing_plan_output.chmod(0o600)
                    missing_plan_output.unlink()
        print("PASS iter-0121 lexical absence rejects existing/nonregular/unreadable output")

        # BLOCKED with bytes still binds them, including across legal correction.
        missing_plan_output.write_bytes(b"## Files to touch\n")
        receipt_state_path.write_bytes(open_plan_bytes)
        result = receipt_cli("plan", "complete", *blocked_args)
        assert result.returncode == 0, result.stderr
        bound_bytes = receipt_state_path.read_bytes()
        assert read_state(receipt_state_path)["phases"]["plan"]["output_sha256"] == hashlib.sha256(
            missing_plan_output.read_bytes()
        ).hexdigest()
        result = receipt_cli(
            "plan", "spawn", "--round", "1", "--triggered-by", "plan",
            "--engine", "codex", "--model", plan_model,
            "--prompt-sha256", plan_prompt_sha_1,
        )
        assert result.returncode == 0, result.stderr
        correction_bytes = receipt_state_path.read_bytes()
        missing_plan_output.unlink()
        result = receipt_cli(
            "plan", "complete", "--verdict", "BLOCKED",
            "--engine-session-log", str(plan_session_1),
        )
        assert result.returncode == 1, result.stderr
        assert "BLOCKED:plan-integrity-invalid" in result.stderr
        assert receipt_state_path.read_bytes() == correction_bytes
        # Work phases still refuse; FINAL_REPORT closes the run as phase-input-invalid and names the failure.
        for changed in (False, True):
            if changed:
                missing_plan_output.write_bytes(b"altered plan\n")
            receipt_state_path.write_bytes(bound_bytes)
            refused_work = receipt_cli("implement", "spawn", "--round", "0", "--engine", "claude")
            assert refused_work.returncode == 1 and "BLOCKED:plan-integrity-" in refused_work.stderr, refused_work.stderr
            assert receipt_state_path.read_bytes() == bound_bytes
            result = receipt_cli("final_report", "spawn", "--round", "0")
            assert result.returncode == 0, result.stderr
            result = receipt_cli("final_report", "complete")
            assert result.returncode == 0, result.stderr
            assert read_state(receipt_state_path)["phases"]["final_report"]["verdict"] == "BLOCKED:phase-input-invalid"
            assert "bound PLAN no longer verifies: BLOCKED:plan-integrity-" in result.stdout
            (receipt_devlyn / "final-report.md").unlink()
        print("PASS iter-0121 BLOCKED output binding: work phases refuse deletion/tampering; closure records it")

        retained_log.unlink()
        write_state(state_path, {"phases": {}})
        state = read_state(state_path)
        do_spawn(state, "implement", 0, None, "claude", "claude-default")
        assert do_complete(
            state, "implement", "PASS", None, None, None, None,
            devlyn=devlyn,
        ) is None
        assert state["phases"]["implement"]["model_effective"] is None

        # Supplied evidence must parse and never silently record null.
        write_state(state_path, {"phases": {}})
        state = read_state(state_path)
        do_spawn(
            state, "plan", 0, None, "claude", "claude-default",
            prompt_sha256=digest0,
        )
        assert do_complete(state, "plan", "PASS", None, None, None, None) is None
        assert state["phases"]["plan"]["model_effective"] is None
        invalid_log = devlyn / "invalid-session.log"
        invalid_log.write_text("no model evidence\n", encoding="utf-8")
        write_state(state_path, {"phases": {}})
        state = read_state(state_path)
        do_spawn(
            state, "plan", 0, None, "claude", "claude-default",
            prompt_sha256=digest0,
        )
        invalid = do_complete(
            state, "plan", "PASS", None, None, None, None, str(invalid_log)
        )
        assert invalid and "model-attestation-failed" in invalid
        assert state["phases"]["plan"]["model_effective"] is None
        assert state["phases"]["plan"]["verdict"] == "BLOCKED"

        # A VERIFY-origin repair round leaves a clean tracked tree whose HEAD is its
        # `chore(pipeline): implement fix round <n>` commit, bound to the triggering
        # findings; fresh VERIFY re-entry rechecks that receipt against the tree.
        repo = devlyn / "repair-checkpoint"
        repo.mkdir()

        def repo_git(*args: str) -> str:
            return subprocess.run(
                ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=repo,
                check=True, capture_output=True, text=True, encoding="utf-8",
            ).stdout.strip()

        repo_git("init", "-q")
        (repo / ".gitignore").write_text(".devlyn/\n", encoding="utf-8")
        (repo / "a.txt").write_text("base\n", encoding="utf-8")
        repo_git("add", "-A")
        repo_git("commit", "-qm", "base")
        base = repo_git("rev-parse", "HEAD")
        repo_devlyn = repo / ".devlyn"
        repo_devlyn.mkdir()
        merged = repo_devlyn / "verify-merged.findings.jsonl"
        merged.write_text('{"id": "VERIFY-0001", "severity": "HIGH"}\n', encoding="utf-8")
        (repo / "a.txt").write_text("fixed\n", encoding="utf-8")
        repo_git("commit", "-qam", "chore(pipeline): implement fix round 1")
        fix = repo_git("rev-parse", "HEAD")
        checkpoint_state = {"phases": {"implement": {"round": 1, "triggered_by": "verify"}}}
        receipt = record_repair_checkpoint(repo, repo_devlyn, checkpoint_state, 1)
        assert receipt == {"round": 1, "origin_phase": "verify",
                           "triggering_findings_sha256": hashlib.sha256(merged.read_bytes()).hexdigest(),
                           "pre_fix_sha": base, "fix_commit_sha": fix}, receipt
        assert record_repair_checkpoint(repo, repo_devlyn, checkpoint_state, 1) == receipt
        assert checkpoint_state["phases"]["implement"]["durability"] == [receipt]
        enforce_repair_checkpoint(repo, repo_devlyn, checkpoint_state, 1)

        def refused(call, needle: str) -> None:
            try:
                call()
            except SystemExit as exc:
                assert str(exc).startswith("BLOCKED:repair-checkpoint") and needle in str(exc), exc
            else:
                raise AssertionError(f"repair checkpoint accepted: {needle}")

        refused(lambda: enforce_repair_checkpoint(repo, repo_devlyn, checkpoint_state, 2), "receipt is missing")
        (repo / "a.txt").write_text("uncommitted\n", encoding="utf-8")
        refused(lambda: enforce_repair_checkpoint(repo, repo_devlyn, checkpoint_state, 1), "not clean")
        repo_git("add", "a.txt")
        refused(lambda: enforce_repair_checkpoint(repo, repo_devlyn, checkpoint_state, 1), "not clean")
        repo_git("reset", "-q", "--hard", fix)
        merged.write_text('{"id": "VERIFY-0002", "severity": "HIGH"}\n', encoding="utf-8")
        refused(lambda: enforce_repair_checkpoint(repo, repo_devlyn, checkpoint_state, 1), "no longer matches")
        refused(lambda: record_repair_checkpoint(repo, repo_devlyn, checkpoint_state, 1), "different checkpoint")
        merged.write_text('{"id": "VERIFY-0001", "severity": "HIGH"}\n', encoding="utf-8")
        (repo / "a.txt").write_text("later\n", encoding="utf-8")
        repo_git("commit", "-qam", "wip after the checkpoint")
        refused(lambda: enforce_repair_checkpoint(repo, repo_devlyn, checkpoint_state, 1), "expected fix checkpoint round 1")
        refused(lambda: record_repair_checkpoint(repo, repo_devlyn, {"phases": {"implement": {}}}, 1),
                "expected fix checkpoint round 1")
        repo_git("reset", "-q", "--hard", fix)
        refused(lambda: checkpoint_ledger({"phases": {"implement": {"durability": {}}}}), "malformed")

        # CLI: re-entry without a receipt is refused with state unchanged; durability-enforce
        # records it, then fresh VERIFY opens on the fix commit.
        checkpoint_state_path = repo_devlyn / "pipeline.state.json"
        write_state(checkpoint_state_path, {
            "version": "3.0", "run_id": "rs-repair-checkpoint", "rounds": {"global": 1, "max_rounds": 4},
            "phases": {"implement": {"started_at": "2026-01-01T00:00:00.000Z", "completed_at": None,
                                     "round": 1, "triggered_by": "verify", "verdict": None}},
        })

        def checkpoint_cli(*cli_args: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run([sys.executable, script, "--devlyn-dir", ".devlyn", *cli_args],
                                  cwd=repo, capture_output=True, text=True, check=False, encoding="utf-8")

        before = checkpoint_state_path.read_bytes()
        refused_reentry = checkpoint_cli("--phase", "implement", "transition", "--verdict", "PASS",
                                         "--next-phase", "verify", "--next-round", "1", "--next-triggered-by", "verify")
        assert refused_reentry.returncode != 0 and "receipt is missing" in refused_reentry.stderr, refused_reentry.stderr
        assert checkpoint_state_path.read_bytes() == before
        recorded = checkpoint_cli("--phase", "implement", "durability-enforce", "--round", "1")
        assert recorded.returncode == 0, recorded.stderr
        reentered = checkpoint_cli("--phase", "implement", "transition", "--verdict", "PASS",
                                   "--next-phase", "verify", "--next-round", "1", "--next-triggered-by", "verify")
        assert reentered.returncode == 0, reentered.stderr
        reentered_state = read_state(checkpoint_state_path)
        assert reentered_state["phases"]["verify"]["pre_sha"] == fix
        assert reentered_state["phases"]["implement"]["durability"] == [receipt]
        print("PASS repair checkpoint: receipt binding, dirty/moved/stale refusal, CLI re-entry")

        # Retired phases, events and caller-supplied SHAs are rejected before any state write.
        before = checkpoint_state_path.read_bytes()
        for cli_args in (("--phase", "build_gate", "spawn", "--round", "1"),
                         ("--phase", "cleanup", "complete", "--verdict", "PASS"),
                         ("--phase", "verify", "surface-skip"),
                         ("--phase", "verify", "spawn", "--round", "1", "--pre-sha", fix),
                         ("--phase", "implement", "complete", "--verdict", "PASS", "--post-sha", fix)):
            rejected_cli = checkpoint_cli(*cli_args)
            assert rejected_cli.returncode == 2 and "error:" in rejected_cli.stderr, (cli_args, rejected_cli.stderr)
            assert checkpoint_state_path.read_bytes() == before
        # The first phase spawn binds the PHASE 0 untracked baseline once.
        baseline = repo_devlyn / "untracked.baseline"
        baseline.write_text("keep.local\n", encoding="utf-8")
        baseline_state = {"untracked_baseline_sha256": None, "phases": {}}
        do_spawn(baseline_state, "plan", 0, None, None, None, devlyn=repo_devlyn)
        bound = hashlib.sha256(b"keep.local\n").hexdigest()
        assert baseline_state["untracked_baseline_sha256"] == bound
        baseline.write_text("residue.txt\n", encoding="utf-8")
        do_spawn(baseline_state, "probe_derive", 0, None, None, None, devlyn=repo_devlyn)
        assert baseline_state["untracked_baseline_sha256"] == bound
        print("PASS retired phases/arguments rejected unchanged; baseline digest bound at first spawn")

    return 0


def _main_unlocked() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--devlyn-dir", default=".devlyn")
    ap.add_argument("--phase", choices=sorted(PHASE_NAMES))
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--freeze-roles", action="store_true")
    ap.add_argument("--default-engine", default="claude")
    ap.add_argument("--complexity", choices=COMPLEXITIES, default=None)
    ap.add_argument("--high-risk-reason", action="append", default=[])
    sub = ap.add_subparsers(dest="event")

    spawn_p = sub.add_parser("spawn")
    spawn_p.add_argument("--round", type=int, required=True)
    spawn_p.add_argument("--triggered-by", choices=sorted(SPAWN_TRIGGERS), default=None)
    spawn_p.add_argument("--prompt-sha256", default=None)
    spawn_p.add_argument("--engine", default=None)
    spawn_p.add_argument("--model", default=None)

    complete_p = sub.add_parser("complete")
    complete_p.add_argument("--verdict", default=None)
    complete_p.add_argument("--findings-file", default=None)
    complete_p.add_argument("--log-file", default=None)
    complete_p.add_argument("--engine", default=None)
    complete_p.add_argument("--model", default=None)
    complete_p.add_argument("--engine-session-log", default=None)
    complete_p.add_argument("--detail", default=None)

    transition_p = sub.add_parser("transition")
    transition_p.add_argument("--verdict", default=None)
    transition_p.add_argument("--findings-file", default=None)
    transition_p.add_argument("--log-file", default=None)
    transition_p.add_argument("--engine", default=None)
    transition_p.add_argument("--model", default=None)
    transition_p.add_argument("--engine-session-log", default=None)
    transition_p.add_argument("--next-phase", choices=sorted(PHASE_NAMES), required=True)
    transition_p.add_argument("--next-round", type=int, required=True)
    transition_p.add_argument("--next-triggered-by", choices=sorted(SPAWN_TRIGGERS), default=None)
    transition_p.add_argument("--next-engine", default=None)
    transition_p.add_argument("--next-model", default=None)

    durability_p = sub.add_parser("durability-enforce")
    durability_p.add_argument("--round", type=int, required=True)

    args = ap.parse_args()
    if args.self_test:
        return self_test()

    if args.freeze_roles:
        devlyn = pathlib.Path(args.devlyn_dir)
        state_path = devlyn / "pipeline.state.json"
        try:
            state = read_state(state_path)
            result = freeze_roles(state, devlyn.resolve().parent, args.default_engine,
                                  complexity=args.complexity, high_risk_reasons=args.high_risk_reason)
            write_state(state_path, state)
            print(json.dumps(result, sort_keys=True))
            return 0
        except (ValueError, OSError) as exc:
            print(str(exc), file=sys.stderr)
            return 1

    if not args.phase or args.event not in {"spawn", "complete", "transition", "durability-enforce"}:
        ap.error("--phase and a phase event are required unless --self-test")
    devlyn = pathlib.Path(args.devlyn_dir)
    if not devlyn.is_dir():
        sys.stderr.write(f"error: {devlyn} is not a directory\n")
        return 1
    state_path = devlyn / "pipeline.state.json"
    state = read_state(state_path)
    work = pathlib.Path.cwd()

    if args.event == "durability-enforce":
        if args.phase != "implement":
            ap.error("durability-enforce is valid only for --phase implement")
        validate_plan_output(state, devlyn, args.phase)
        record_repair_checkpoint(work, devlyn, state, args.round)
        write_state(state_path, state)
        sys.stdout.write(f"ok: phases.implement.durability.round-{args.round}\n")
        return 0

    if args.event in {"spawn", "transition"}:
        spawn_phase = args.phase if args.event == "spawn" else args.next_phase
        spawn_round = args.round if args.event == "spawn" else args.next_round
        implement = (state.get("phases") or {}).get("implement")
        if (spawn_phase == "verify" and spawn_round >= 1 and isinstance(implement, dict)
                and implement.get("round") == spawn_round and implement.get("triggered_by") == "verify"):
            enforce_repair_checkpoint(work, devlyn, state, spawn_round)
        if args.event == "spawn":
            do_spawn(
                state, args.phase, args.round, args.triggered_by, args.engine, args.model,
                prompt_sha256=args.prompt_sha256,
                devlyn=devlyn,
                work=work,
            )
        else:
            state = do_transition(
                state, args.phase, args.next_phase, args.verdict,
                args.findings_file, args.log_file, args.engine, args.model,
                args.engine_session_log, devlyn, args.next_round,
                args.next_triggered_by, args.next_engine, args.next_model,
                work=work,
            )
        write_state(state_path, state)
        if spawn_phase == "verify":
            clear_verify_round_artifacts(devlyn)
        if args.event == "transition":
            opened = state["phases"][args.next_phase]
            completed = (
                opened["history"][-1]
                if args.phase == args.next_phase
                else state["phases"][args.phase]
            )
            raw = state_path.read_bytes()
            sys.stdout.write(json.dumps({
                "completed_phase": args.phase,
                "completed_at": completed["completed_at"],
                "completed_verdict": completed["verdict"],
                "next_phase": args.next_phase,
                "next_started_at": opened["started_at"],
                "next_round": opened["round"],
                "state_path": str(state_path),
                "state_sha256": hashlib.sha256(raw).hexdigest(),
            }, sort_keys=True) + "\n")
            return 0
    else:
        attestation_error = do_complete(
            state, args.phase, args.verdict, args.findings_file,
            args.log_file, args.engine, args.model, args.engine_session_log, devlyn,
            work, detail=args.detail,
        )

    if args.event not in {"spawn", "transition"}:
        write_state(state_path, state)
    if args.event == "complete" and attestation_error is not None:
        sys.stderr.write(attestation_error + "\n")
        return 1
    if args.event == "complete" and args.phase == "final_report":
        sys.stdout.write((devlyn / "final-report.md").read_bytes().decode("utf-8"))
        return 0
    sys.stdout.write(f"ok: phases.{args.phase}.{args.event}\n")
    return 0


def main() -> int:
    if "--self-test" in sys.argv[1:]:
        return _main_unlocked()
    selector = argparse.ArgumentParser(add_help=False)
    selector.add_argument("--devlyn-dir", default=".devlyn")
    known, _ = selector.parse_known_args()
    devlyn = pathlib.Path(known.devlyn_dir).resolve()
    if not devlyn.is_dir():
        sys.stderr.write(f"error: {devlyn} is not a directory\n")
        return 1
    lock = runpy.run_path(str(pathlib.Path(__file__).with_name("platform-support.py")))["file_lock"]
    with lock(devlyn / "pipeline.state.lock", blocking=True):
        return _main_unlocked()


if __name__ == "__main__":
    runpy.run_path(str(pathlib.Path(__file__).with_name("platform-support.py")))["configure_utf8"]()
    raise SystemExit(main())
