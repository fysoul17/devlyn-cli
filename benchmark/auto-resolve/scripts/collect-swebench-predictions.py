#!/usr/bin/env python3
"""Collect patch.diff files into SWE-bench prediction JSONL."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf8") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_no}: expected JSON object")
            rows.append(value)
    return rows


def instance_ids_from_jsonl(path: Path | None) -> set[str] | None:
    if path is None:
        return None
    ids: set[str] = set()
    for row in read_jsonl(path):
        instance_id = row.get("instance_id")
        if not isinstance(instance_id, str) or not instance_id:
            raise ValueError(f"{path}: row missing non-empty instance_id")
        ids.add(instance_id)
    return ids


def collect_from_root(root: Path, patch_name: str, keep: set[str] | None) -> list[tuple[str, Path]]:
    patches: list[tuple[str, Path]] = []
    for patch_path in sorted(root.glob(f"*/{patch_name}")):
        instance_id = patch_path.parent.name
        if keep is not None and instance_id not in keep:
            continue
        patches.append((instance_id, patch_path))
    return patches


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-root", required=True, type=Path)
    parser.add_argument("--patch-name", default="patch.diff")
    parser.add_argument("--instances-jsonl", type=Path, help="Optional filter/validation set.")
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--allow-empty", action="store_true")
    args = parser.parse_args()

    keep = instance_ids_from_jsonl(args.instances_jsonl)
    patches = collect_from_root(args.patch_root, args.patch_name, keep)
    if not patches:
        raise ValueError(f"no {args.patch_name} files found under {args.patch_root}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    skipped_empty: list[str] = []
    with args.out.open("w", encoding="utf8") as f:
        for instance_id, patch_path in patches:
            patch = patch_path.read_text(encoding="utf8")
            if not patch.strip():
                if args.allow_empty:
                    skipped_empty.append(instance_id)
                    continue
                raise ValueError(f"empty patch for {instance_id}: {patch_path}")
            f.write(
                json.dumps(
                    {
                        "instance_id": instance_id,
                        "model_name_or_path": args.model_name,
                        "model_patch": patch,
                    }
                )
                + "\n"
            )
            written += 1

    report = {
        "patch_root": str(args.patch_root),
        "patch_name": args.patch_name,
        "model_name_or_path": args.model_name,
        "out": str(args.out),
        "predictions_written": written,
        "empty_skipped": skipped_empty,
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
