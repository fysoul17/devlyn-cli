#!/usr/bin/env python3
"""Measure the portable post-judge VERIFY finalization envelope."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import statistics
import sys
import tempfile
from decimal import Decimal
from pathlib import Path

import attribution


GATE_ID = "P-0085-VENV"
CONSERVATION_TOLERANCE_MS = 1000
MIN_FINALIZE_MS = 120_000
MIN_FINALIZE_RATIO = Decimal("0.2")
PRIMARY_JUDGE_OUTPUT_NAMES = frozenset(
    {
        "verify-judge-primary.raw.stdout",
        "codex-primary.raw-stdout.txt",
        "verify-primary.codex.raw.txt",
        "verify.primary.codex-raw.stdout",
    }
)
PAIR_JUDGE_OUTPUT_NAME = "claude-judge.stdout"
JUDGE_VERDICTS = frozenset({"PASS", "PASS_WITH_ISSUES", "NEEDS_WORK"})
TERMINAL_MARKERS = (
    "PASS\n",
    "**PASS_WITH_ISSUES**\n",
    '# SUMMARY {"verdict":"NEEDS_WORK"}\n',
    "NEEDS_WORK\n",
)
FROZEN_REGRESSION_EXPECTED = {
    "aggregate": {
        "discovered_attribution_rows": 7,
        "eligible_rows": 4,
        "median_post_judge_finalize_ms": 138631.328,
        "median_post_judge_finalize_ratio": 0.251,
        "verify_complete_rows": 4,
    },
    "gate": {
        "conjuncts": {
            "at_least_three_eligible_rows": True,
            "eligible_rows_conserve": True,
            "eligible_rows_ordered": True,
            "exactly_four_verify_complete_rows": True,
            "median_finalize_at_least_120000_ms": True,
            "median_finalize_ratio_at_least_20_percent": True,
            "paths_are_relative": True,
            "selected_receipts_have_sha256": True,
        },
        "failed_conjuncts": [],
        "id": GATE_ID,
        "passed": True,
        "verdict": "PASS",
    },
    "rows": {
        "DR-atomic-state-f11-batch-import": {
            "attribution": {
                "path": "DR-atomic-state-f11-batch-import/A1/attribution.json",
                "sha256": "a856ac6ff8a47743e09989a9d04a32f75042931fd5669e5e7b0db8e8746e9597",
            },
            "buckets": {
                "judge_to_merge_ms": 73008.235,
                "merge_to_phase_end_ms": 35321.669,
                "post_judge_finalize_ms": 108329.904,
                "pre_final_judge_ms": 510415.096,
            },
            "conservation": {
                "conserves_within_tolerance": True,
                "error_ms": 0,
                "partition_total_ms": 618745,
                "tolerance_ms": 1000,
            },
            "judge": {
                "path": "DR-atomic-state-f11-batch-import/A1/devlyn-snapshot/runs/rs-20260722T155851Z-5069eee5b1d7/claude-judge.stdout",
                "sha256": "1229edf5145ddbbea7ff393ddbe573f5ee6a595a16a0bc97f0ba9c17a0e78105",
            },
            "merge": {
                "path": "DR-atomic-state-f11-batch-import/A1/devlyn-snapshot/runs/rs-20260722T155851Z-5069eee5b1d7/verify-merge.summary.json",
                "sha256": "ad719da19283f28d259ac2b7d10ccbd651d2c23e16ec0fb86be8ee0d5831a0db",
            },
            "state": {
                "path": "DR-atomic-state-f11-batch-import/A1/devlyn-snapshot/runs/rs-20260722T155851Z-5069eee5b1d7/pipeline.state.json",
                "sha256": "77ccac67dfd84ca32b644046fff51deec0d39c0dbfbdb50272b5586d0e805034",
            },
        },
        "DR-byte-preservation-f7-out-of-scope-trap": {
            "attribution": {
                "path": "DR-byte-preservation-f7-out-of-scope-trap/A1/attribution.json",
                "sha256": "d31c1f70e8c367d1a2968fc757625d4a195b32275354cfcbe801b08b80a2bfb8",
            },
            "buckets": {
                "judge_to_merge_ms": 130303.383,
                "merge_to_phase_end_ms": 38629.369,
                "post_judge_finalize_ms": 168932.752,
                "pre_final_judge_ms": 446590.248,
            },
            "conservation": {
                "conserves_within_tolerance": True,
                "error_ms": 0,
                "partition_total_ms": 615523,
                "tolerance_ms": 1000,
            },
            "judge": {
                "path": "DR-byte-preservation-f7-out-of-scope-trap/A1/devlyn-snapshot/runs/rs-20260722T140503Z-b330a3d32334/claude-judge.stdout",
                "sha256": "716f846aed8c2759092416c2e4be06296ade0c77ae979b7dc47d8a4052d84b4b",
            },
            "merge": {
                "path": "DR-byte-preservation-f7-out-of-scope-trap/A1/devlyn-snapshot/runs/rs-20260722T140503Z-b330a3d32334/verify-merge.summary.json",
                "sha256": "4693ddb8f422079b22b2206a8747b73686440f4f860205280ef7e6b88d0bd137",
            },
            "state": {
                "path": "DR-byte-preservation-f7-out-of-scope-trap/A1/devlyn-snapshot/runs/rs-20260722T140503Z-b330a3d32334/pipeline.state.json",
                "sha256": "2cff082650044a47d91d32caf71df532f610362f1599b1d6325ad777b020d3d9",
            },
        },
        "DR-ledger-rounding-consistency-f26-payout": {
            "attribution": {
                "path": "DR-ledger-rounding-consistency-f26-payout/A1/attribution.json",
                "sha256": "ddfb94dc3de4f32ffed73b30c1c0aa2dc7eec7f927175a57ee69acab04e851b5",
            },
            "buckets": {
                "judge_to_merge_ms": 64990.793,
                "merge_to_phase_end_ms": 40155.381,
                "post_judge_finalize_ms": 105146.174,
                "pre_final_judge_ms": 357658.826,
            },
            "conservation": {
                "conserves_within_tolerance": True,
                "error_ms": 0,
                "partition_total_ms": 462805,
                "tolerance_ms": 1000,
            },
            "judge": {
                "path": "DR-ledger-rounding-consistency-f26-payout/A1/devlyn-snapshot/runs/rs-20260722T151656Z-300755c095d5/claude-judge.stdout",
                "sha256": "556fe4f4a22b74e0e3568a4ffe5eb918d40c0c494c79cc2aeb0ddbcc1958dc83",
            },
            "merge": {
                "path": "DR-ledger-rounding-consistency-f26-payout/A1/devlyn-snapshot/runs/rs-20260722T151656Z-300755c095d5/verify-merge.summary.json",
                "sha256": "837fc3c5919e0c4d377a8eb7bdeef41907a066722472e29745e562c2274df4a9",
            },
            "state": {
                "path": "DR-ledger-rounding-consistency-f26-payout/A1/devlyn-snapshot/runs/rs-20260722T151656Z-300755c095d5/pipeline.state.json",
                "sha256": "d9ab5ad009a026ca768ba569936b6754be6de6b1ddcd99c3b59075469236883a",
            },
        },
        "DR-shape-compound-rules-f25-cart": {
            "attribution": {
                "path": "DR-shape-compound-rules-f25-cart/A1/attribution.json",
                "sha256": "d1ae5513f0fe0096ed8b8a6d303ee760c69a7bc5c139a394b6a5d872512ff188",
            },
            "buckets": {
                "judge_to_merge_ms": 203608.917,
                "merge_to_phase_end_ms": 37523.987,
                "post_judge_finalize_ms": 241132.904,
                "pre_final_judge_ms": 380181.096,
            },
            "conservation": {
                "conserves_within_tolerance": True,
                "error_ms": 0,
                "partition_total_ms": 621314,
                "tolerance_ms": 1000,
            },
            "judge": {
                "path": "DR-shape-compound-rules-f25-cart/A1/devlyn-snapshot/runs/rs-20260722T144227Z-83ff017fab0f/claude-judge.stdout",
                "sha256": "ee10eccde04d32200306a6692049e020a2eca8348b6c890f03210f4ee722df0d",
            },
            "merge": {
                "path": "DR-shape-compound-rules-f25-cart/A1/devlyn-snapshot/runs/rs-20260722T144227Z-83ff017fab0f/verify-merge.summary.json",
                "sha256": "4693ddb8f422079b22b2206a8747b73686440f4f860205280ef7e6b88d0bd137",
            },
            "state": {
                "path": "DR-shape-compound-rules-f25-cart/A1/devlyn-snapshot/runs/rs-20260722T144227Z-83ff017fab0f/pipeline.state.json",
                "sha256": "160cdb8234451d91e3c92f197f9f9961faa3f7216c8e37cf3263f891da76e910",
            },
        },
    },
}


class EnvelopeError(ValueError):
    pass


def load_object(path: Path) -> dict:
    value = attribution.load_json(path)
    if not isinstance(value, dict):
        raise EnvelopeError(f"{path} must contain a JSON object")
    return value


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError as exc:
        raise EnvelopeError(f"path escapes input root: {path}") from exc


def datetime_ns(value: dt.datetime) -> int:
    epoch = dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)
    delta = value - epoch
    return (
        (delta.days * 86_400 + delta.seconds) * 1_000_000_000
        + delta.microseconds * 1000
    )


def ns_iso(value: int) -> str:
    seconds, nanoseconds = divmod(value, 1_000_000_000)
    whole = dt.datetime.fromtimestamp(seconds, tz=dt.timezone.utc)
    return f"{whole:%Y-%m-%dT%H:%M:%S}.{nanoseconds:09d}Z"


def state_iso(value: int) -> str:
    seconds, nanoseconds = divmod(value, 1_000_000_000)
    whole = dt.datetime.fromtimestamp(seconds, tz=dt.timezone.utc)
    return f"{whole:%Y-%m-%dT%H:%M:%S}.{nanoseconds // 1_000_000:03d}Z"


def normalized_ms(value_ns: int) -> int | float:
    return attribution.normalized(value_ns / 1_000_000)


def exact_finalize_ratio(
    phase_end_ns: int, judge_ns: int, verify_duration_ms: int | float
) -> Decimal:
    return Decimal(phase_end_ns - judge_ns) / (
        Decimal(str(verify_duration_ms)) * 1_000_000
    )


def receipt(path: Path, root: Path, *, include_mtime: bool = False) -> dict:
    result = {
        "path": relative_path(path, root),
        "sha256": sha256_file(path),
    }
    if include_mtime:
        mtime_ns = path.stat().st_mtime_ns
        result.update({"mtime_ns": mtime_ns, "mtime_utc": ns_iso(mtime_ns)})
    return result


def successful_judge_output(path: Path) -> bool:
    lines = [
        line.strip()
        for line in path.read_text(
            encoding="utf-8", errors="replace"
        ).splitlines()
        if line.strip()
    ]
    if not lines:
        return False
    terminal = lines[-1]
    if terminal in JUDGE_VERDICTS:
        return True
    if (
        terminal.startswith("**")
        and terminal.endswith("**")
        and terminal[2:-2] in JUDGE_VERDICTS
    ):
        return True
    prefix = "# SUMMARY "
    if not terminal.startswith(prefix):
        return False
    try:
        summary = json.loads(terminal[len(prefix) :])
    except json.JSONDecodeError:
        return False
    return (
        isinstance(summary, dict)
        and summary.get("verdict") in JUDGE_VERDICTS
    )


def current_verify_candidates(snapshot: Path) -> list[tuple[Path, dict]]:
    candidates: list[tuple[Path, dict]] = []
    for state_path in attribution.state_paths(snapshot):
        state = load_object(state_path)
        phases = state.get("phases")
        verify = phases.get("verify") if isinstance(phases, dict) else None
        if not isinstance(verify, dict):
            continue
        required = ("started_at", "completed_at", "duration_ms")
        if all(verify.get(field) is not None for field in required):
            candidates.append((state_path, verify))
    return candidates


def matched_judge_outputs(
    snapshot: Path,
    state_path: Path,
    input_root: Path,
    phase_start_ns: int,
    phase_end_ns: int,
) -> list[dict]:
    matches: list[dict] = []
    candidates = [
        snapshot / name for name in sorted(PRIMARY_JUDGE_OUTPUT_NAMES)
    ]
    candidates.append(state_path.parent / PAIR_JUDGE_OUTPUT_NAME)
    for path in sorted(
        candidate for candidate in candidates if candidate.is_file()
    ):
        item = receipt(path, input_root, include_mtime=True)
        within_phase = phase_start_ns <= item["mtime_ns"] <= phase_end_ns
        nonempty = path.stat().st_size > 0
        item.update(
            {
                "basename": path.name,
                "nonempty": nonempty,
                "successful": (
                    within_phase and nonempty and successful_judge_output(path)
                ),
                "within_phase": within_phase,
            }
        )
        matches.append(item)
    return matches


def analyze_row(attribution_path: Path, input_root: Path) -> dict:
    attempt = attribution_path.parent
    snapshot = attempt / "devlyn-snapshot"
    source = load_object(attribution_path)
    row = {
        "attribution": receipt(attribution_path, input_root),
        "eligible": False,
        "errors": [],
        "row": relative_path(attempt.parent, input_root),
        "thermometer": {
            "advisory_only": True,
            "judge_durations_ms": source.get("judge_durations_ms"),
            "used_for_anchors": False,
            "used_for_eligibility": False,
            "used_for_gate": False,
        },
    }
    candidates = current_verify_candidates(snapshot)
    row["current_verify_candidate_count"] = len(candidates)
    row["state_receipts"] = [
        receipt(path, input_root) for path, _verify in candidates
    ]
    if len(candidates) != 1:
        row["errors"].append(
            f"expected exactly one current VERIFY state, found {len(candidates)}"
        )
        return row

    state_path, verify = candidates[0]
    phase_start = attribution.parse_time(
        verify.get("started_at"), f"{state_path}: phases.verify.started_at"
    )
    phase_end = attribution.parse_time(
        verify.get("completed_at"), f"{state_path}: phases.verify.completed_at"
    )
    verify_duration_ms = attribution.number(
        verify.get("duration_ms"), f"{state_path}: phases.verify.duration_ms"
    )
    assert verify_duration_ms is not None
    phase_start_ns = datetime_ns(phase_start)
    phase_end_ns = datetime_ns(phase_end)
    row.update(
        {
            "phase_end": phase_end.isoformat().replace("+00:00", "Z"),
            "phase_end_ns": phase_end_ns,
            "phase_start": phase_start.isoformat().replace("+00:00", "Z"),
            "phase_start_ns": phase_start_ns,
            "verify_duration_ms": verify_duration_ms,
        }
    )

    matches = matched_judge_outputs(
        snapshot, state_path, input_root, phase_start_ns, phase_end_ns
    )
    row["matched_judge_outputs"] = matches
    successful = [item for item in matches if item["successful"]]
    if not successful:
        row["errors"].append("no successful recognized judge output in phase window")
        return row
    final_judge = max(successful, key=lambda item: (item["mtime_ns"], item["path"]))

    merge_path = state_path.parent / "verify-merge.summary.json"
    if not merge_path.is_file():
        row["errors"].append("current run verify-merge.summary.json is missing")
        return row
    merge = receipt(merge_path, input_root, include_mtime=True)
    judge_ns = final_judge["mtime_ns"]
    merge_ns = merge["mtime_ns"]
    ordered = phase_start_ns <= judge_ns <= merge_ns <= phase_end_ns
    row["anchors"] = {
        "final_judge_output": final_judge,
        "merge_complete": merge,
        "ordered": ordered,
    }
    if not ordered:
        row["errors"].append(
            "anchor order is not phase_start <= final_judge_output "
            "<= merge_complete <= phase_end"
        )
        return row

    pre_final_judge_ms = normalized_ms(judge_ns - phase_start_ns)
    judge_to_merge_ms = normalized_ms(merge_ns - judge_ns)
    merge_to_phase_end_ms = normalized_ms(phase_end_ns - merge_ns)
    post_judge_finalize_ms = attribution.normalized(
        judge_to_merge_ms + merge_to_phase_end_ms
    )
    partition_total_ms = attribution.normalized(
        pre_final_judge_ms + post_judge_finalize_ms
    )
    conservation_error_ms = attribution.normalized(
        abs(partition_total_ms - verify_duration_ms)
    )
    conserves = conservation_error_ms <= CONSERVATION_TOLERANCE_MS
    row.update(
        {
            "buckets": {
                "judge_to_merge_ms": judge_to_merge_ms,
                "merge_to_phase_end_ms": merge_to_phase_end_ms,
                "post_judge_finalize_ms": post_judge_finalize_ms,
                "pre_final_judge_ms": pre_final_judge_ms,
            },
            "conservation": {
                "conserves_within_tolerance": conserves,
                "error_ms": conservation_error_ms,
                "partition_total_ms": partition_total_ms,
                "tolerance_ms": CONSERVATION_TOLERANCE_MS,
            },
            "eligible": True,
            "post_judge_finalize_ratio": attribution.normalized(
                float(exact_finalize_ratio(phase_end_ns, judge_ns, verify_duration_ms))
            ),
        }
    )
    return row


def median(values: list[int | float]) -> int | float | None:
    if not values:
        return None
    return attribution.normalized(statistics.median(values))


def build_cohort(input_root: Path) -> dict:
    attribution_paths = sorted(input_root.glob("*/A1/attribution.json"))
    scored_paths = [
        path
        for path in attribution_paths
        if load_object(path).get("verify_complete") is True
    ]
    rows = [analyze_row(path, input_root) for path in scored_paths]
    eligible = [row for row in rows if row["eligible"]]
    finalize_values = [
        row["buckets"]["post_judge_finalize_ms"] for row in eligible
    ]
    ratio_values = [
        exact_finalize_ratio(
            row["phase_end_ns"],
            row["anchors"]["final_judge_output"]["mtime_ns"],
            row["verify_duration_ms"],
        )
        for row in eligible
    ]
    median_finalize = median(finalize_values)
    median_ratio_exact = statistics.median(ratio_values) if ratio_values else None
    median_ratio = (
        attribution.normalized(float(median_ratio_exact))
        if median_ratio_exact is not None
        else None
    )
    paths = [
        item["path"]
        for row in rows
        for key in ("attribution",)
        for item in (row[key],)
    ]
    paths.extend(
        item["path"]
        for row in rows
        for item in row.get("state_receipts", [])
    )
    paths.extend(
        item["path"]
        for row in rows
        for item in row.get("matched_judge_outputs", [])
    )
    paths.extend(
        anchor["path"]
        for row in rows
        for anchor in row.get("anchors", {}).values()
        if isinstance(anchor, dict)
    )
    selected_receipts = [
        row["anchors"]["final_judge_output"]
        for row in eligible
        if "anchors" in row
    ]
    selected_receipts.extend(
        row["anchors"]["merge_complete"]
        for row in eligible
        if "anchors" in row
    )
    conjuncts = {
        "at_least_three_eligible_rows": len(eligible) >= 3,
        "eligible_rows_conserve": all(
            row["conservation"]["conserves_within_tolerance"] for row in eligible
        ),
        "eligible_rows_ordered": all(
            row["anchors"]["ordered"] for row in eligible
        ),
        "exactly_four_verify_complete_rows": len(rows) == 4,
        "median_finalize_at_least_120000_ms": (
            median_finalize is not None and median_finalize >= MIN_FINALIZE_MS
        ),
        "median_finalize_ratio_at_least_20_percent": (
            median_ratio_exact is not None
            and median_ratio_exact >= MIN_FINALIZE_RATIO
        ),
        "paths_are_relative": all(not Path(path).is_absolute() for path in paths),
        "selected_receipts_have_sha256": all(
            isinstance(item.get("sha256"), str) and len(item["sha256"]) == 64
            for item in selected_receipts
        ),
    }
    failed = sorted(name for name, passed in conjuncts.items() if not passed)
    structural = {
        "at_least_three_eligible_rows",
        "eligible_rows_conserve",
        "eligible_rows_ordered",
        "exactly_four_verify_complete_rows",
        "paths_are_relative",
        "selected_receipts_have_sha256",
    }
    verdict = (
        "PASS"
        if not failed
        else "INVALID"
        if structural.intersection(failed)
        else "STOP"
    )
    return {
        "aggregate": {
            "discovered_attribution_rows": len(attribution_paths),
            "eligible_rows": len(eligible),
            "median_post_judge_finalize_ms": median_finalize,
            "median_post_judge_finalize_ratio": median_ratio,
            "verify_complete_rows": len(rows),
        },
        "gate": {
            "conjuncts": conjuncts,
            "failed_conjuncts": failed,
            "id": GATE_ID,
            "passed": verdict == "PASS",
            "verdict": verdict,
        },
        "input_root": ".",
        "rows": rows,
        "schema_version": 1,
    }


def json_bytes(payload: dict) -> bytes:
    return (
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def synthetic_fixture(root: Path) -> list[dict]:
    rows: list[dict] = []
    base_ns = 1_750_000_000 * 1_000_000_000
    primary_names = sorted(PRIMARY_JUDGE_OUTPUT_NAMES)
    for index in range(4):
        attempt = root / f"row-{index}" / "A1"
        snapshot = attempt / "devlyn-snapshot"
        run = snapshot / "runs" / f"run-{index}"
        run.mkdir(parents=True)
        start_ns = base_ns + index * 1_000_000_000_000
        end_ns = start_ns + 600_000_000_000
        primary = snapshot / primary_names[index]
        pair = run / "claude-judge.stdout"
        merge = run / "verify-merge.summary.json"
        primary.write_text(TERMINAL_MARKERS[index], encoding="utf-8")
        pair.write_text(TERMINAL_MARKERS[index], encoding="utf-8")
        write_json(merge, {"verdict": "PASS"})
        os.utime(primary, ns=(start_ns + 250_000_000_000,) * 2)
        os.utime(pair, ns=(start_ns + 300_000_000_000,) * 2)
        os.utime(merge, ns=(start_ns + 450_000_000_000,) * 2)
        state = {
            "phases": {
                "verify": {
                    "completed_at": state_iso(end_ns),
                    "duration_ms": 600_000,
                    "judge_durations_ms": {"judge": 1, "pair_judge": 2},
                    "started_at": state_iso(start_ns),
                }
            },
            "run_id": f"run-{index}",
        }
        state_path = run / "pipeline.state.json"
        write_json(state_path, state)
        attribution_path = attempt / "attribution.json"
        write_json(
            attribution_path,
            {
                "judge_durations_ms": {"judge": 999_999, "pair_judge": None},
                "verify_complete": True,
            },
        )
        rows.append(
            {
                "attempt": attempt,
                "merge": merge,
                "pair": pair,
                "run": run,
                "start_ns": start_ns,
                "state": state,
                "state_path": state_path,
            }
        )
    return rows


def fixture_payload(root: Path) -> tuple[dict, list[dict]]:
    rows = synthetic_fixture(root)
    return build_cohort(root), rows


def frozen_regression_projection(payload: dict) -> dict:
    rows = {}
    for row in payload["rows"]:
        anchors = row["anchors"]
        states = row["state_receipts"]
        assert len(states) == 1
        rows[row["row"]] = {
            "attribution": row["attribution"],
            "buckets": row["buckets"],
            "conservation": row["conservation"],
            "judge": {
                key: anchors["final_judge_output"][key]
                for key in ("path", "sha256")
            },
            "merge": {
                key: anchors["merge_complete"][key]
                for key in ("path", "sha256")
            },
            "state": states[0],
        }
    return {
        "aggregate": payload["aggregate"],
        "gate": payload["gate"],
        "rows": rows,
    }


def self_test() -> int:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        payload, rows = fixture_payload(root / "ordered")
        assert payload["gate"]["verdict"] == "PASS"
        assert payload["aggregate"]["median_post_judge_finalize_ms"] == 300_000
        assert (
            rows[0]["state"]["phases"]["verify"]["started_at"]
            == "2025-06-15T15:06:40.000Z"
        )
        assert ns_iso(rows[0]["start_ns"]) == "2025-06-15T15:06:40.000000000Z"

        missing_root = root / "missing"
        _payload, rows = fixture_payload(missing_root)
        for path in rows[0]["attempt"].glob("devlyn-snapshot/**/claude-judge.stdout"):
            path.unlink()
        for path in rows[0]["attempt"].glob("devlyn-snapshot/*"):
            if path.is_file() and path.name in PRIMARY_JUDGE_OUTPUT_NAMES:
                path.unlink()
        missing = build_cohort(missing_root)
        assert missing["rows"][0]["eligible"] is False

        ambiguous_root = root / "ambiguous"
        _payload, rows = fixture_payload(ambiguous_root)
        duplicate = rows[0]["attempt"] / "devlyn-snapshot" / "runs" / "duplicate"
        duplicate.mkdir()
        write_json(duplicate / "pipeline.state.json", rows[0]["state"])
        ambiguous = build_cohort(ambiguous_root)
        assert ambiguous["rows"][0]["current_verify_candidate_count"] == 2
        assert ambiguous["rows"][0]["eligible"] is False

        order_root = root / "order"
        _payload, rows = fixture_payload(order_root)
        os.utime(
            rows[0]["pair"],
            ns=((rows[0]["start_ns"] + 500_000_000_000),) * 2,
        )
        order = build_cohort(order_root)
        assert order["rows"][0]["eligible"] is False
        assert "anchor order" in order["rows"][0]["errors"][0]

        conservation_root = root / "conservation"
        _payload, rows = fixture_payload(conservation_root)
        rows[0]["state"]["phases"]["verify"]["duration_ms"] = 590_000
        write_json(rows[0]["state_path"], rows[0]["state"])
        conservation = build_cohort(conservation_root)
        assert conservation["rows"][0]["eligible"] is True
        assert (
            conservation["rows"][0]["conservation"][
                "conserves_within_tolerance"
            ]
            is False
        )
        assert conservation["gate"]["verdict"] == "INVALID"

        irrelevant_root = root / "irrelevant"
        _payload, rows = fixture_payload(irrelevant_root)
        irrelevant = rows[0]["attempt"] / "devlyn-snapshot" / "implement.stdout"
        irrelevant.write_text("PASS\n", encoding="utf-8")
        os.utime(
            irrelevant,
            ns=((rows[0]["start_ns"] + 400_000_000_000),) * 2,
        )
        ignored = build_cohort(irrelevant_root)
        assert all(
            item["basename"] != "implement.stdout"
            for item in ignored["rows"][0]["matched_judge_outputs"]
        )
        assert (
            ignored["rows"][0]["anchors"]["final_judge_output"]["basename"]
            == "claude-judge.stdout"
        )

        retry_root = root / "retry"
        _payload, rows = fixture_payload(retry_root)
        retry = rows[0]["run"] / "retry" / "claude-judge.stdout"
        retry.parent.mkdir()
        retry.write_text("PASS\n", encoding="utf-8")
        os.utime(
            retry,
            ns=((rows[0]["start_ns"] + 400_000_000_000),) * 2,
        )
        canonical = build_cohort(retry_root)
        assert all(
            item["path"] != relative_path(retry, retry_root)
            for item in canonical["rows"][0]["matched_judge_outputs"]
        )
        assert (
            canonical["rows"][0]["anchors"]["final_judge_output"]["path"]
            == relative_path(rows[0]["pair"], retry_root)
        )

        narrative_root = root / "narrative"
        _payload, rows = fixture_payload(narrative_root)
        rows[0]["pair"].write_text(
            "The earlier PASS token is narrative, not the result.\n"
            "Review complete without a terminal marker.\n",
            encoding="utf-8",
        )
        os.utime(
            rows[0]["pair"],
            ns=((rows[0]["start_ns"] + 400_000_000_000),) * 2,
        )
        narrative = build_cohort(narrative_root)
        rejected = next(
            item
            for item in narrative["rows"][0]["matched_judge_outputs"]
            if item["basename"] == "claude-judge.stdout"
        )
        assert rejected["successful"] is False
        assert (
            narrative["rows"][0]["anchors"]["final_judge_output"]["basename"]
            != "claude-judge.stdout"
        )

        ratio_root = root / "ratio"
        _payload, rows = fixture_payload(ratio_root)
        for row in rows:
            end_ns = row["start_ns"] + 1_000_000_000_000
            row["state"]["phases"]["verify"].update(
                {
                    "completed_at": state_iso(end_ns),
                    "duration_ms": 1_000_000,
                }
            )
            write_json(row["state_path"], row["state"])
            os.utime(
                row["pair"],
                ns=((row["start_ns"] + 800_400_000_000),) * 2,
            )
            os.utime(
                row["merge"],
                ns=((row["start_ns"] + 900_000_000_000),) * 2,
            )
        ratio = build_cohort(ratio_root)
        assert ratio["aggregate"]["median_post_judge_finalize_ratio"] == 0.2
        assert (
            ratio["gate"]["conjuncts"][
                "median_finalize_ratio_at_least_20_percent"
            ]
            is False
        )
        assert ratio["gate"]["failed_conjuncts"] == [
            "median_finalize_ratio_at_least_20_percent"
        ]
        assert ratio["gate"]["verdict"] == "STOP"

        deterministic_root = root / "deterministic"
        deterministic, _rows = fixture_payload(deterministic_root)
        assert json_bytes(deterministic) == json_bytes(
            build_cohort(deterministic_root)
        )

    frozen = (
        Path(__file__).resolve().parents[1]
        / "results"
        / "nodeg-hook-20260722c"
    )
    if frozen.is_dir():
        regression = build_cohort(frozen)
        assert (
            frozen_regression_projection(regression)
            == FROZEN_REGRESSION_EXPECTED
        )
    print("self-test: PASS (11 cases)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_root", nargs="?", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if args.input_root is None:
        parser.error("input_root is required unless --self-test is used")
    input_root = args.input_root.resolve()
    output = (
        args.output.resolve()
        if args.output
        else input_root / "verify-envelope-anatomy.json"
    )
    try:
        payload = build_cohort(input_root)
        output.write_bytes(json_bytes(payload))
    except (
        EnvelopeError,
        attribution.AttributionError,
        OSError,
        ValueError,
    ) as exc:
        print(f"verify-envelope-anatomy failed: {exc}", file=sys.stderr)
        return 2
    print(output)
    return 0 if payload["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
