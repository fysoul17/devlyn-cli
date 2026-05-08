#!/usr/bin/env python3
"""Prepare a SWE-bench prediction JSONL as frozen VERIFY review cases."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
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


def require_text(row: dict[str, Any], key: str, source: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{source} missing non-empty {key!r}")
    return value.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instances-jsonl", required=True, type=Path)
    parser.add_argument("--predictions-jsonl", required=True, type=Path)
    parser.add_argument(
        "--cases-root",
        default=Path("benchmark/auto-resolve/external/swebench/cases"),
        type=Path,
    )
    parser.add_argument(
        "--repos-root",
        default=Path("benchmark/auto-resolve/external/swebench/repos"),
        type=Path,
    )
    parser.add_argument("--repo-dir", type=Path, help="Use one local repo clone for every selected instance.")
    parser.add_argument("--instance-id", action="append", help="Prepare only these instance ids.")
    parser.add_argument("--limit", type=int, help="Prepare at most N matched instances after filtering.")
    parser.add_argument("--timeout-seconds", type=int, default=2400)
    parser.add_argument("--out-manifest", type=Path)
    args = parser.parse_args()

    instances = {require_text(row, "instance_id", f"{args.instances_jsonl}"): row for row in read_jsonl(args.instances_jsonl)}
    predictions: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(args.predictions_jsonl):
        instance_id = require_text(row, "instance_id", f"{args.predictions_jsonl}")
        if instance_id in predictions:
            raise ValueError(f"duplicate prediction for {instance_id}")
        predictions[instance_id] = row

    selected_ids = args.instance_id or list(predictions)
    script = Path(__file__).with_name("prepare-swebench-frozen-case.py")
    prepared: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for instance_id in selected_ids:
            if args.limit is not None and len(prepared) >= args.limit:
                break
            if instance_id not in instances:
                raise ValueError(f"prediction instance not found in instances JSONL: {instance_id}")
            prediction = predictions.get(instance_id)
            if prediction is None:
                raise ValueError(f"selected instance missing prediction: {instance_id}")
            patch_value = prediction.get("model_patch")
            if not isinstance(patch_value, str) or not patch_value.strip():
                raise ValueError(f"prediction {instance_id} missing non-empty 'model_patch'")
            instance_path = tmp_dir / f"{instance_id}.instance.json"
            patch_path = tmp_dir / f"{instance_id}.patch"
            instance_path.write_text(json.dumps(instances[instance_id], indent=2) + "\n", encoding="utf8")
            patch_path.write_text(patch_value, encoding="utf8")

            cmd = [
                "python3",
                str(script),
                "--instance-json",
                str(instance_path),
                "--model-patch",
                str(patch_path),
                "--cases-root",
                str(args.cases_root),
                "--repos-root",
                str(args.repos_root),
                "--timeout-seconds",
                str(args.timeout_seconds),
            ]
            if args.repo_dir is not None:
                cmd.extend(["--repo-dir", str(args.repo_dir)])
            completed = subprocess.run(cmd, check=True, text=True, capture_output=True)
            prepared.append(json.loads(completed.stdout))

    manifest = {
        "instances_jsonl": str(args.instances_jsonl),
        "predictions_jsonl": str(args.predictions_jsonl),
        "cases_root": str(args.cases_root),
        "repos_root": str(args.repos_root),
        "prepared_count": len(prepared),
        "prepared": prepared,
    }
    if args.out_manifest:
        args.out_manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
