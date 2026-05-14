#!/usr/bin/env python3
"""Fetch SWE-bench instances as JSONL without Hugging Face Python deps."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from pair_evidence_contract import reject_json_constant


DATASETS = {
    "lite": "princeton-nlp/SWE-bench_Lite",
    "verified": "princeton-nlp/SWE-bench_Verified",
    "full": "princeton-nlp/SWE-bench",
}


def fetch_rows(dataset: str, split: str, offset: int, length: int) -> dict[str, Any]:
    params = urllib.parse.urlencode(
        {
            "dataset": dataset,
            "config": "default",
            "split": split,
            "offset": offset,
            "length": length,
        }
    )
    url = f"https://datasets-server.huggingface.co/rows?{params}"
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.load(response, parse_constant=reject_json_constant)


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be > 0")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=sorted(DATASETS), default="lite")
    parser.add_argument("--dataset-id", help="Override the Hugging Face dataset id.")
    parser.add_argument("--split", default="test")
    parser.add_argument("--limit", type=positive_int, help="Fetch at most N rows.")
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--instance-id", action="append", help="Keep only these instance ids.")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    if args.page_size <= 0:
        raise ValueError("--page-size must be > 0")
    dataset = args.dataset_id or DATASETS[args.dataset]
    keep = set(args.instance_id or [])
    rows: list[dict[str, Any]] = []
    offset = 0
    total: int | None = None

    while True:
        remaining = args.page_size
        if args.limit is not None:
            remaining = min(remaining, max(args.limit - len(rows), 0))
            if remaining == 0:
                break
        page = fetch_rows(dataset, args.split, offset, remaining)
        if total is None:
            total = int(page.get("num_rows_total") or 0)
        page_rows = page.get("rows") or []
        if not isinstance(page_rows, list):
            raise ValueError("fetched page malformed: rows must be a list")
        if not page_rows:
            break
        for row_index, wrapper in enumerate(page_rows, start=1):
            if not isinstance(wrapper, dict):
                raise ValueError(f"malformed fetched row {row_index}: wrapper must be object")
            row = wrapper.get("row")
            if not isinstance(row, dict):
                raise ValueError(f"malformed fetched row {row_index}: row must be object")
            instance_id = row.get("instance_id")
            if not isinstance(instance_id, str) or not instance_id:
                raise ValueError(f"malformed fetched row {row_index}: instance_id must be a non-empty string")
            if keep and instance_id not in keep:
                continue
            rows.append(row)
            if args.limit is not None and len(rows) >= args.limit:
                break
        offset += len(page_rows)
        if offset >= total:
            break

    if keep:
        found = {row.get("instance_id") for row in rows}
        missing = sorted(keep - found)
        if missing:
            raise ValueError(f"requested instance ids not found in fetched split: {', '.join(missing)}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(
        json.dumps(
            {
                "dataset": dataset,
                "split": args.split,
                "rows_written": len(rows),
                "rows_total": total,
                "out": str(args.out),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"fetch-swebench-instances: {exc}", file=sys.stderr)
        raise SystemExit(1)
