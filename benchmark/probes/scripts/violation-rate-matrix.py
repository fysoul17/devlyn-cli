#!/usr/bin/env python3
"""Aggregate drift-bait violation-rate matrix + per-probe flip-band (iter-0058).

Reads every results/<run-id>/drift-bait/<probe>/verdict.json produced by
run-violation-matrix.sh run-ids of the shape <prefix>-<model>-r<N>. A
violation is a rep whose verdict.json has "passed": false (the probe's own
hidden/verify.sh — mechanical, no LLM judge). The flip-band per (model,
probe) cell is min(violations, reps - violations): 0 means all reps agreed;
any A/B delta on that cell smaller than or equal to the band is noise.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

RUN_ID_RE = re.compile(r"^(?P<prefix>.+)-(?P<model>[A-Za-z0-9.]+)-r(?P<rep>\d+)$")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--results-root", default="benchmark/probes/results")
    parser.add_argument("--run-prefix", required=True,
                        help="run-id prefix passed to run-violation-matrix.sh")
    parser.add_argument("--out", required=True,
                        help="output path for the matrix JSON (a sibling .md is also written)")
    args = parser.parse_args()

    root = pathlib.Path(args.results_root)
    cells: dict[tuple[str, str], dict[int, bool]] = {}
    for run_dir in sorted(root.glob(f"{args.run_prefix}-*")):
        match = RUN_ID_RE.match(run_dir.name)
        if not match or match.group("prefix") != args.run_prefix:
            continue
        model, rep = match.group("model"), int(match.group("rep"))
        for verdict_path in sorted(run_dir.glob("drift-bait/*/verdict.json")):
            probe = verdict_path.parent.name
            verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
            if not isinstance(verdict.get("passed"), bool):
                sys.stderr.write(f"error: {verdict_path} has no boolean 'passed'\n")
                return 1
            cells.setdefault((model, probe), {})[rep] = verdict["passed"] is False

    if not cells:
        sys.stderr.write(f"error: no verdicts under {root}/{args.run_prefix}-*\n")
        return 1

    models = sorted({model for model, _ in cells})
    probes = sorted({probe for _, probe in cells})
    matrix: dict[str, dict[str, dict[str, object]]] = {}
    for model in models:
        matrix[model] = {}
        for probe in probes:
            reps = cells.get((model, probe), {})
            violations = sum(reps.values())
            matrix[model][probe] = {
                "reps": len(reps),
                "violations": violations,
                "violation_reps": sorted(rep for rep, bad in reps.items() if bad),
                "flip_band": min(violations, len(reps) - violations),
            }

    out = {
        "run_prefix": args.run_prefix,
        "models": models,
        "probes": probes,
        "matrix": matrix,
        "totals": {
            model: {
                "violations": sum(matrix[model][p]["violations"] for p in probes),
                "reps": sum(matrix[model][p]["reps"] for p in probes),
            }
            for model in models
        },
    }
    out_path = pathlib.Path(args.out)
    out_path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [f"# Violation-rate matrix — `{args.run_prefix}`", ""]
    header = "| probe | " + " | ".join(models) + " |"
    lines += [header, "|" + "---|" * (len(models) + 1)]
    for probe in probes:
        row = [probe]
        for model in models:
            cell = matrix[model][probe]
            row.append(f"{cell['violations']}/{cell['reps']} (band {cell['flip_band']})")
        lines.append("| " + " | ".join(row) + " |")
    lines += ["", "cell = violations/reps; band = min(violations, reps-violations); "
              "an A/B delta ≤ band on that cell is within noise.", ""]
    out_path.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(out["totals"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
