#!/usr/bin/env python3
"""Aggregate existing benchmark artifacts into a seat-fitness matrix."""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import re
import sys
from typing import Any


SEATS = (
    "orchestrator",
    "drift_resistance",
    "verify_primary_judge",
    "verify_pair_judge",
    "implement_executor",
    "plan_ideate_designer",
)
JUDGE_CERT_RECALL_MIN = 0.75
JUDGE_CERT_FP_MAX = 0.125


def reject_json_constant(token: str) -> None:
    raise ValueError(f"invalid JSON numeric constant: {token}")


def load_json(path: pathlib.Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_json_constant)


def strict_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def rel(root: pathlib.Path, path: pathlib.Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def model_value(cli_version: Any, model_id_or_alias: Any) -> str | None:
    if isinstance(cli_version, str) and cli_version and isinstance(model_id_or_alias, str) and model_id_or_alias:
        return f"{cli_version}/{model_id_or_alias}"
    return None


def model_from_identity(identity_path: pathlib.Path, root: pathlib.Path) -> tuple[str | None, str | None]:
    if not identity_path.is_file():
        return None, None
    try:
        identity = load_json(identity_path)
    except (OSError, ValueError, json.JSONDecodeError):
        return None, None
    if not isinstance(identity, dict):
        return None, None
    value = model_value(identity.get("cli_version"), identity.get("model_id_or_alias"))
    return value, rel(root, identity_path) if value else None


def model_from_judge_payload(payload: dict[str, Any], artifact: pathlib.Path, root: pathlib.Path) -> tuple[str | None, str | None]:
    value = model_value(payload.get("_judge_cli"), payload.get("_judge_model"))
    return value, f"{rel(root, artifact)}:_judge_cli/_judge_model" if value else None


def cell_status(engine_versions: dict[str, str], engine_alias: str, model_version_value: str | None, artifact: str | None) -> str:
    if artifact is None:
        return "unmeasured"
    if model_version_value is not None and engine_versions.get(engine_alias) == model_version_value:
        return "current"
    return "stale"


def make_cell(
    *,
    date: str,
    engine_versions: dict[str, str],
    seat: str,
    engine_alias: str,
    metric: str,
    value: float | int | None,
    n: int | None,
    artifact: str | None,
    model_version_value: str | None = None,
    model_version_source: str | None = None,
) -> dict[str, Any]:
    return {
        "seat": seat,
        "engine_alias": engine_alias,
        "model_version": {
            "value": model_version_value,
            "source": model_version_source,
        },
        "metric": metric,
        "value": value,
        "n": n,
        "date": date,
        "artifact": artifact,
        "status": cell_status(engine_versions, engine_alias, model_version_value, artifact),
    }


def collect_drift_cells(root: pathlib.Path, date: str, engine_versions: dict[str, str]) -> list[dict[str, Any]]:
    cells: list[dict[str, Any]] = []
    results = root / "benchmark/probes/results"
    for name in (
        "iter0058-base-matrix.json",
        "iter0062-a-matrix-corrected.json",
        "iter0062-b-matrix-corrected.json",
    ):
        path = results / name
        if not path.is_file():
            continue
        data = load_json(path)
        totals = data.get("totals") if isinstance(data, dict) else {}
        if not isinstance(totals, dict):
            continue
        for engine_alias, total in sorted(totals.items()):
            if not isinstance(total, dict):
                continue
            reps = total.get("reps")
            violations = total.get("violations")
            if not (isinstance(reps, int) and reps > 0 and isinstance(violations, int) and violations >= 0):
                continue
            cells.append(make_cell(
                date=date,
                engine_versions=engine_versions,
                seat="drift_resistance",
                engine_alias=str(engine_alias),
                metric="non_violation_rate",
                value=(reps - violations) / reps,
                n=reps,
                artifact=rel(root, path),
            ))
    return cells


def collect_compliance_cells(root: pathlib.Path, date: str, engine_versions: dict[str, str]) -> list[dict[str, Any]]:
    cells: list[dict[str, Any]] = []
    results = root / "benchmark/probes/results"
    for path in sorted(results.glob("**/compliance-check.json")):
        if "devlyn-snapshot" in path.parts:
            continue
        data = load_json(path)
        if not isinstance(data, dict):
            continue
        cli = data.get("cli")
        if not isinstance(cli, str) or not cli:
            continue
        overall = data.get("overall")
        cells.append(make_cell(
            date=date,
            engine_versions=engine_versions,
            seat="orchestrator",
            engine_alias=cli,
            metric="compliance_pass",
            value=1.0 if overall == "PASS" else 0.0,
            n=1,
            artifact=rel(root, path),
        ))
    return cells


def case_meta(root: pathlib.Path) -> dict[str, dict[str, Any]]:
    meta: dict[str, dict[str, Any]] = {}
    for path in sorted((root / "benchmark/probes/judge-quality/cases").glob("*.json")):
        data = load_json(path)
        if isinstance(data, dict) and isinstance(data.get("id"), str) and isinstance(data.get("ground_truth"), dict):
            meta[data["id"]] = data["ground_truth"]
    return meta


def collect_judge_quality_cells(
    root: pathlib.Path,
    date: str,
    engine_versions: dict[str, str],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    cells: list[dict[str, Any]] = []
    certification: dict[str, dict[str, Any]] = {}
    meta = case_meta(root)
    results = root / "benchmark/probes/judge-quality/results"
    if not results.is_dir():
        return cells, certification
    for judge_dir in sorted(path for path in results.iterdir() if path.is_dir()):
        records = []
        for path in sorted(judge_dir.glob("*-rep*.json")):
            try:
                data = load_json(path)
            except (ValueError, json.JSONDecodeError):
                continue
            if isinstance(data, dict) and isinstance(data.get("case"), str):
                records.append(data)
        if not records:
            continue
        judge = judge_dir.name
        engine_alias = {"sonnet": "sonnet", "codex": "codex"}.get(judge, judge)
        identity_value, identity_source = model_from_identity(judge_dir / "identity.json", root)
        defect = [r for r in records if meta.get(r["case"], {}).get("type") != "clean"]
        clean = [r for r in records if meta.get(r["case"], {}).get("type") == "clean"]
        hits = sum(1 for r in defect if r.get("hit") is True)
        fps = sum(1 for r in clean if r.get("false_positive") is True)
        parse_errors = sum(1 for r in records if r.get("parse_error") is True)
        recall = hits / len(defect) if defect else None
        fp_rate = fps / len(clean) if clean else None
        certification[judge] = {
            "recall_rate": recall,
            "false_positive_rate": fp_rate,
            "defect_reps": len(defect),
            "clean_reps": len(clean),
            "parse_errors": parse_errors,
            "certified": (
                strict_number(recall)
                and strict_number(fp_rate)
                and recall >= JUDGE_CERT_RECALL_MIN
                and fp_rate <= JUDGE_CERT_FP_MAX
            ),
        }
        for metric, value, n in (
            ("recall_rate", recall, len(defect)),
            ("false_positive_rate", fp_rate, len(clean)),
            ("parse_failure_rate", parse_errors / len(records) if records else None, len(records)),
        ):
            cells.append(make_cell(
                date=date,
                engine_versions=engine_versions,
                seat="verify_primary_judge",
                engine_alias=engine_alias,
                metric=metric,
                value=value,
                n=n,
                artifact=rel(root, judge_dir),
                model_version_value=identity_value,
                model_version_source=identity_source,
            ))
    return cells, certification


def collect_pair_judge_cells(root: pathlib.Path, date: str, engine_versions: dict[str, str]) -> list[dict[str, Any]]:
    cells: list[dict[str, Any]] = []
    artifacts = [
        root / "benchmark/auto-resolve/results/swebench-lite-proof-gate-n11.json",
        root / "benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof/full-pipeline-pair-gate.json",
    ]
    for path in artifacts:
        if not path.is_file():
            continue
        data = load_json(path)
        if not isinstance(data, dict):
            continue
        engine_alias = data.get("engine_alias") if isinstance(data.get("engine_alias"), str) else "codex"
        version = data.get("model_version") if isinstance(data.get("model_version"), str) else None
        version_source = f"{rel(root, path)}:model_version" if version else None
        rows = data.get("rows") if isinstance(data.get("rows"), list) else []
        if path.name == "swebench-lite-proof-gate-n11.json":
            n = len([r for r in rows if isinstance(r, dict)])
            lift = sum(
                1 for r in rows
                if isinstance(r, dict) and (r.get("pair_verdict_lift") is True or r.get("pair_internal_verdict_lift") is True)
            )
            value = lift / n if n else None
            metric = "pair_lift_rate"
        else:
            total = data.get("fixtures_total")
            passed = data.get("fixtures_passed")
            n = total if isinstance(total, int) and total >= 0 else len(rows)
            value = passed / total if isinstance(total, int) and total > 0 and isinstance(passed, int) else None
            metric = "pair_gate_pass_rate"
        cells.append(make_cell(
            date=date,
            engine_versions=engine_versions,
            seat="verify_pair_judge",
            engine_alias=engine_alias,
            metric=metric,
            value=value,
            n=n,
            artifact=rel(root, path),
            model_version_value=version,
            model_version_source=version_source,
        ))
    return cells


def collect_implement_cells(root: pathlib.Path, date: str, engine_versions: dict[str, str]) -> list[dict[str, Any]]:
    cells: list[dict[str, Any]] = []
    proof_root = root / "benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof"
    if not proof_root.is_dir():
        return cells
    by_arm: dict[str, dict[str, list[float]]] = {}
    version_by_arm: dict[str, tuple[str | None, str | None]] = {}
    for judge_path in sorted(proof_root.glob("*/judge.json")):
        judge = load_json(judge_path)
        if not isinstance(judge, dict):
            continue
        scores = judge.get("scores_by_arm")
        if not isinstance(scores, dict):
            continue
        version = model_from_judge_payload(judge, judge_path, root)
        for arm, score in scores.items():
            if strict_number(score):
                by_arm.setdefault(str(arm), {}).setdefault("judge_score_mean", []).append(float(score))
                version_by_arm.setdefault(str(arm), version)
        fixture_dir = judge_path.parent
        for result_path in sorted(fixture_dir.glob("*/result.json")):
            arm = result_path.parent.name
            result = load_json(result_path)
            if not isinstance(result, dict):
                continue
            verify_score = result.get("verify_score")
            if strict_number(verify_score):
                by_arm.setdefault(arm, {}).setdefault("verify_score_mean", []).append(float(verify_score))
                version_by_arm.setdefault(arm, version)
    for arm, metrics in sorted(by_arm.items()):
        version_value, version_source = version_by_arm.get(arm, (None, None))
        for metric, values in sorted(metrics.items()):
            if not values:
                continue
            cells.append(make_cell(
                date=date,
                engine_versions=engine_versions,
                seat="implement_executor",
                engine_alias=arm,
                metric=metric,
                value=sum(values) / len(values),
                n=len(values),
                artifact=rel(root, proof_root),
                model_version_value=version_value,
                model_version_source=version_source,
            ))
    return cells


def add_unmeasured_cells(cells: list[dict[str, Any]], date: str, engine_versions: dict[str, str]) -> None:
    populated = {cell["seat"] for cell in cells if cell.get("artifact") is not None}
    aliases = sorted(engine_versions) or ["unassigned"]
    for seat in SEATS:
        if seat in populated:
            continue
        for alias in aliases:
            cells.append(make_cell(
                date=date,
                engine_versions=engine_versions,
                seat=seat,
                engine_alias=alias,
                metric="unmeasured",
                value=None,
                n=None,
                artifact=None,
            ))


def best_current(cells: list[dict[str, Any]], seat: str, metrics: set[str], *, lower_is_better: bool = False) -> str | dict[str, str]:
    candidates = [
        c for c in cells
        if c.get("seat") == seat
        and c.get("metric") in metrics
        and c.get("status") == "current"
        and strict_number(c.get("value"))
    ]
    if not candidates:
        return {"recommendation": "recert required", "seat": seat}
    candidates.sort(key=lambda c: c["value"], reverse=not lower_is_better)
    return str(candidates[0]["engine_alias"])


def pair_priority(cells: list[dict[str, Any]]) -> list[str] | dict[str, str]:
    candidates = [
        c for c in cells
        if c.get("seat") == "verify_pair_judge"
        and c.get("metric") in {"pair_lift_rate", "pair_gate_pass_rate"}
        and c.get("status") == "current"
        and strict_number(c.get("value"))
    ]
    if not candidates:
        return {"recommendation": "recert required", "seat": "verify_pair_judge"}
    best_by_alias: dict[str, float] = {}
    for cell in candidates:
        alias = str(cell["engine_alias"])
        best_by_alias[alias] = max(best_by_alias.get(alias, float("-inf")), float(cell["value"]))
    return [alias for alias, _ in sorted(best_by_alias.items(), key=lambda item: item[1], reverse=True)]


def recommendation(cells: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "executor": best_current(cells, "implement_executor", {"judge_score_mean", "verify_score_mean"}),
        "pair_judge_priority": pair_priority(cells),
    }


def render_md(report: dict[str, Any]) -> str:
    lines = [
        f"# Seat Matrix - {report['date']}",
        "",
        f"Cells: {len(report['cells'])}",
        "",
        "## Recommendation",
        "",
        "```json",
        json.dumps(report["recommendation"], indent=2, sort_keys=True),
        "```",
        "",
        "## Cells",
        "",
        "| Seat | Engine | Metric | Value | N | Status | Model version | Artifact |",
        "|---|---|---|---:|---:|---|---|---|",
    ]
    for cell in report["cells"]:
        value = cell["value"]
        if isinstance(value, float):
            value_text = f"{value:.3f}"
        else:
            value_text = "n/a" if value is None else str(value)
        n_text = "n/a" if cell["n"] is None else str(cell["n"])
        version = cell["model_version"]["value"] or "null"
        artifact = cell["artifact"] or "none"
        lines.append(
            f"| {cell['seat']} | {cell['engine_alias']} | {cell['metric']} | "
            f"{value_text} | {n_text} | {cell['status']} | {version} | `{artifact}` |"
        )
    return "\n".join(lines) + "\n"


def build_report(root: pathlib.Path, date: str, engine_versions: dict[str, str]) -> dict[str, Any]:
    cells: list[dict[str, Any]] = []
    cells.extend(collect_compliance_cells(root, date, engine_versions))
    cells.extend(collect_drift_cells(root, date, engine_versions))
    judge_cells, certification = collect_judge_quality_cells(root, date, engine_versions)
    cells.extend(judge_cells)
    cells.extend(collect_pair_judge_cells(root, date, engine_versions))
    cells.extend(collect_implement_cells(root, date, engine_versions))
    add_unmeasured_cells(cells, date, engine_versions)
    cells.sort(key=lambda c: (c["seat"], c["engine_alias"], c["metric"], c["artifact"] or ""))
    return {
        "date": date,
        "engine_versions": engine_versions,
        "schema": "devlyn-seat-matrix-v0",
        "cells": cells,
        "judge_certification": certification,
        "recommendation": recommendation(cells),
    }


def parse_engine_versions(raw: str) -> dict[str, str]:
    data = json.loads(raw)
    if not isinstance(data, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in data.items()):
        raise argparse.ArgumentTypeError("--engine-versions must be a JSON object of string:string")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", required=True, help="YYYY-MM-DD; also used in output filename")
    parser.add_argument("--engine-versions", required=True, type=parse_engine_versions)
    parser.add_argument("--repo-root", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parents[2])
    parser.add_argument("--out-dir", type=pathlib.Path)
    args = parser.parse_args()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", args.date):
        parser.error("--date must be YYYY-MM-DD")
    root = args.repo_root.resolve()
    out_dir = args.out_dir or (root / "benchmark/seats")
    out_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(root, args.date, args.engine_versions)
    out_json = out_dir / f"seat-matrix-{args.date}.json"
    out_md = out_dir / f"seat-matrix-{args.date}.md"
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    out_md.write_text(render_md(report), encoding="utf-8")
    print(json.dumps({"json": str(out_json), "md": str(out_md), "cells": len(report["cells"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
