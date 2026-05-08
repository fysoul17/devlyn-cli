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


def rank(verdict: str | None) -> int:
    return VERDICT_RANK.get(verdict or "PASS", 0)


def worse(a: str | None, b: str | None) -> str:
    return RANK_VERDICT[max(rank(a), rank(b))]


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
                    item = json.loads(raw)
                except json.JSONDecodeError as exc:
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


def pair_trigger_required(devlyn: pathlib.Path) -> bool:
    state_path = devlyn / "pipeline.state.json"
    if not state_path.is_file():
        return False
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    phases = state.get("phases") if isinstance(state, dict) else {}
    verify_phase = phases.get("verify") if isinstance(phases, dict) else None
    trigger = None
    if isinstance(verify_phase, dict):
        trigger = verify_phase.get("pair_trigger")
    if trigger is None and isinstance(state, dict):
        verify_state = state.get("verify")
        if isinstance(verify_state, dict):
            trigger = verify_state.get("pair_trigger")
    return bool(
        isinstance(trigger, dict)
        and trigger.get("eligible") is True
        and trigger.get("reasons")
    )


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
    if has_pair_findings(devlyn):
        return []
    if not stdout_path.is_file():
        if pair_trigger_required(devlyn):
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
                summary = json.loads(raw.removeprefix("# SUMMARY ").strip())
            except json.JSONDecodeError:
                continue
            if summary.get("verdict") in {"NEEDS_WORK", "FAIL", "BLOCKED"}:
                has_nonpass_summary = True
            continue
        if raw.startswith("#"):
            continue
        try:
            item = json.loads(raw)
        except json.JSONDecodeError:
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
    state = json.loads(state_path.read_text(encoding="utf-8"))
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
            json.dumps({"phases": {"verify": {"verdict": "PASS", "sub_verdicts": {}}}}),
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
        state = json.loads((devlyn / "pipeline.state.json").read_text(encoding="utf-8"))
        assert summary["verdict"] == "NEEDS_WORK", summary
        assert state["phases"]["verify"]["verdict"] == "NEEDS_WORK", state
        assert state["phases"]["verify"]["sub_verdicts"]["pair_judge"] == "NEEDS_WORK", state
        assert (devlyn / "verify-merged.findings.jsonl").read_text(encoding="utf-8")
        (devlyn / "verify.findings.jsonl").write_text("", encoding="utf-8")
        (devlyn / "verify.pair.findings.jsonl").write_text("", encoding="utf-8")
        findings, source_verdicts = read_findings(devlyn)
        summary = write_outputs(devlyn, findings, source_verdicts)
        write_state(devlyn, summary)
        state = json.loads((devlyn / "pipeline.state.json").read_text(encoding="utf-8"))
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
        state = json.loads((devlyn / "pipeline.state.json").read_text(encoding="utf-8"))
        assert summary["verdict"] == "BLOCKED", summary
        assert state["phases"]["verify"]["sub_verdicts"]["pair_judge"] == "BLOCKED", state
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
