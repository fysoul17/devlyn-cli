#!/usr/bin/env python3
"""Print a compact, wrap-safe benchmark snapshot from local artifacts."""
from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import sys
import textwrap
from typing import Any

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
FRONTIER_PATH = SCRIPT_DIR / "pair-candidate-frontier.py"


def load_frontier_module() -> Any:
    spec = importlib.util.spec_from_file_location("pair_candidate_frontier", FRONTIER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load frontier module: {FRONTIER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FRONTIER = load_frontier_module()


def best_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in report.get("rows", []):
        if row.get("status") != "pair_evidence_passed":
            continue
        best = FRONTIER.best_pair_evidence(row.get("passing_pair_evidence", []))
        if best is None:
            continue
        rows.append({"fixture": row["fixture"], **best})
    return rows


def display_fixture(fixture: str) -> str:
    short, _, rest = fixture.partition("-")
    return f"{short} {rest.replace('-', ' ')}" if rest else fixture


def fmt_margin(value: Any) -> str:
    return f"{value:+d}" if isinstance(value, int) and not isinstance(value, bool) else "n/a"


def fmt_decimal_margin(value: Any) -> str:
    return f"{value:+.2f}" if isinstance(value, (int, float)) and not isinstance(value, bool) else "n/a"


def fmt_wall(value: Any) -> str:
    return f"{value:.2f}x" if isinstance(value, (int, float)) and not isinstance(value, bool) else "n/a"


def fmt_score(value: Any) -> str:
    return str(value) if isinstance(value, int) and not isinstance(value, bool) else "n/a"


def wrap_item(prefix: str, text: str, *, width: int) -> list[str]:
    return textwrap.wrap(
        text,
        width=width,
        initial_indent=prefix,
        subsequent_indent=" " * len(prefix),
        break_long_words=False,
        break_on_hyphens=False,
    ) or [prefix.rstrip()]


def render_text(report: dict[str, Any], *, width: int) -> str:
    rows = best_rows(report)
    lines = [
        "Recent Benchmark Snapshot",
        "=========================",
        "",
        "Status",
        f"  Verdict: {report.get('verdict', 'n/a')}",
        f"  Active fixtures: {report.get('fixtures_total', 'n/a')}",
        f"  Rejected controls: {report.get('rejected_total', 'n/a')}",
        f"  Pair evidence rows: {report.get('pair_evidence_total', 'n/a')}",
        f"  Unmeasured candidates: {report.get('unmeasured_candidate_total', 'n/a')}",
        "",
        "Pair Lift",
        f"  Average margin: {fmt_decimal_margin(report.get('pair_margin_avg'))}",
        f"  Minimum margin: {fmt_margin(report.get('pair_margin_min'))}",
        f"  Average wall ratio: {fmt_wall(report.get('pair_solo_wall_ratio_avg'))}",
        f"  Maximum wall ratio: {fmt_wall(report.get('pair_solo_wall_ratio_max'))}",
        f"  Gate: margin >= {fmt_margin(report.get('min_pair_margin'))}; wall <= {fmt_wall(report.get('max_pair_solo_wall_ratio'))}",
        "",
        "Pair Evidence",
    ]
    if not rows:
        lines.append("  No passing pair evidence rows found.")
        return "\n".join(lines) + "\n"

    for item in rows:
        lines.append(f"  {display_fixture(item['fixture'])}")
        lines.append(
            "    scores: bare {bare} | solo_claude {solo} | pair {pair}".format(
                bare=fmt_score(item.get("bare_score")),
                solo=fmt_score(item.get("solo_score")),
                pair=fmt_score(item.get("pair_score")),
            )
        )
        lines.append(
            "    lift: {margin} | wall {wall} | arm {arm}".format(
                margin=fmt_margin(item.get("pair_margin")),
                wall=fmt_wall(item.get("pair_solo_wall_ratio")),
                arm=item.get("pair_arm") or "n/a",
            )
        )
        lines.extend(wrap_item("    run: ", str(item.get("run_id") or "n/a"), width=width))
        triggers = ", ".join(item.get("pair_trigger_reasons") or [])
        lines.extend(wrap_item("    triggers: ", triggers or "n/a", width=width))
    return "\n".join(lines) + "\n"


def render_markdown(report: dict[str, Any], *, width: int) -> str:
    rows = best_rows(report)
    lines = [
        "# Recent Benchmark Snapshot",
        "",
        "## Status",
        "",
        f"- Verdict: **{report.get('verdict', 'n/a')}**",
        f"- Active fixtures: {report.get('fixtures_total', 'n/a')}",
        f"- Rejected controls: {report.get('rejected_total', 'n/a')}",
        f"- Pair evidence rows: {report.get('pair_evidence_total', 'n/a')}",
        f"- Unmeasured candidates: {report.get('unmeasured_candidate_total', 'n/a')}",
        "",
        "## Pair Lift",
        "",
        f"- Average margin: **{fmt_decimal_margin(report.get('pair_margin_avg'))}**",
        f"- Minimum margin: **{fmt_margin(report.get('pair_margin_min'))}**",
        f"- Average wall ratio: {fmt_wall(report.get('pair_solo_wall_ratio_avg'))}",
        f"- Maximum wall ratio: {fmt_wall(report.get('pair_solo_wall_ratio_max'))}",
        f"- Gate: margin >= {fmt_margin(report.get('min_pair_margin'))}; wall <= {fmt_wall(report.get('max_pair_solo_wall_ratio'))}",
        "",
        "## Pair Evidence",
        "",
    ]
    if not rows:
        lines.append("No passing pair evidence rows found.")
        return "\n".join(lines) + "\n"

    for item in rows:
        lines.extend(
            [
                f"### {display_fixture(item['fixture'])}",
                "",
                f"- Scores: bare {fmt_score(item.get('bare_score'))}, solo_claude {fmt_score(item.get('solo_score'))}, pair {fmt_score(item.get('pair_score'))}.",
                f"- Lift: {fmt_margin(item.get('pair_margin'))}; wall {fmt_wall(item.get('pair_solo_wall_ratio'))}; arm `{item.get('pair_arm') or 'n/a'}`.",
                f"- Run: `{item.get('run_id') or 'n/a'}`.",
            ]
        )
        triggers = ", ".join(item.get("pair_trigger_reasons") or [])
        wrapped = wrap_item("- Triggers: ", triggers or "n/a", width=width)
        lines.extend(wrapped)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fixtures-root",
        type=pathlib.Path,
        default=pathlib.Path("benchmark/auto-resolve/fixtures"),
    )
    parser.add_argument(
        "--registry",
        type=pathlib.Path,
        default=SCRIPT_DIR / "pair-rejected-fixtures.sh",
    )
    parser.add_argument(
        "--results-root",
        type=pathlib.Path,
        default=pathlib.Path("benchmark/auto-resolve/results"),
    )
    parser.add_argument("--out-json", type=pathlib.Path)
    parser.add_argument("--out-md", type=pathlib.Path)
    parser.add_argument(
        "--max-width",
        type=int,
        default=92,
        help="target maximum line width for text and markdown output",
    )
    parser.add_argument(
        "--min-pair-margin",
        type=int,
        default=5,
        help="minimum pair-over-solo margin required to count passing pair evidence",
    )
    parser.add_argument(
        "--max-pair-solo-wall-ratio",
        type=float,
        default=3.0,
        help="maximum pair/solo wall-time ratio allowed to count passing pair evidence",
    )
    args = parser.parse_args()
    if args.max_width < 60:
        print("error: --max-width must be >= 60", file=sys.stderr)
        return 2

    try:
        report = FRONTIER.build_report(
            fixtures_root=args.fixtures_root,
            registry=args.registry,
            results_root=args.results_root,
            min_pair_margin=args.min_pair_margin,
            max_pair_solo_wall_ratio=args.max_pair_solo_wall_ratio,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf8")
    if args.out_md:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        args.out_md.write_text(render_markdown(report, width=args.max_width), encoding="utf8")

    print(render_text(report, width=args.max_width), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
