#!/usr/bin/env python3
"""Prepare a SWE-bench instance for frozen VERIFY solo-vs-pair review.

The script does not run models and does not evaluate SWE-bench correctness.
It converts one official SWE-bench-style instance plus one candidate patch into
the case layout consumed by run-frozen-verify-pair.sh.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any

from pair_evidence_contract import loads_strict_json_object


SAFE_ID = re.compile(r"^[A-Za-z0-9_.-]+$")
SAFE_REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SAFE_COMMIT = re.compile(r"^[0-9a-fA-F]{7,40}$")


def run(cmd: list[str], cwd: Path | None = None) -> None:
    subprocess.run(cmd, cwd=cwd, check=True)


def read_json(path: Path) -> dict[str, Any]:
    try:
        return loads_strict_json_object(path.read_text(encoding="utf8"))
    except ValueError as exc:
        if str(exc) == "top-level JSON value must be an object":
            raise ValueError(f"expected JSON object: {path}") from exc
        raise


def require_text(instance: dict[str, Any], key: str) -> str:
    value = instance.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"SWE-bench instance missing non-empty {key!r}")
    return value.strip()


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be > 0")
    return parsed


def require_safe_repo(instance: dict[str, Any]) -> str:
    repo = require_text(instance, "repo")
    if not SAFE_REPO.match(repo):
        raise ValueError(f"unsafe SWE-bench repo: {repo!r}")
    return repo


def require_safe_base_commit(instance: dict[str, Any]) -> str:
    base_commit = require_text(instance, "base_commit")
    if not SAFE_COMMIT.match(base_commit):
        raise ValueError(f"unsafe SWE-bench base_commit: {base_commit!r}")
    return base_commit


def repo_cache_name(repo: str, base_commit: str) -> str:
    safe_repo = repo.replace("/", "__")
    return f"{safe_repo}-{base_commit[:12]}"


def prepare_repo(instance: dict[str, Any], repo_dir: Path | None, repos_root: Path) -> Path:
    repo = require_safe_repo(instance)
    base_commit = require_safe_base_commit(instance)
    repos_root.mkdir(parents=True, exist_ok=True)
    dest = repos_root / repo_cache_name(repo, base_commit)

    if repo_dir is not None:
        if dest.exists():
            shutil.rmtree(dest)
        run(["git", "clone", "--quiet", "--no-hardlinks", str(repo_dir), str(dest)])
    elif not dest.exists():
        run(["git", "clone", "--quiet", f"https://github.com/{repo}.git", str(dest)])

    run(["git", "fetch", "--quiet", "--all", "--tags"], cwd=dest)
    run(["git", "checkout", "--quiet", base_commit], cwd=dest)
    run(["git", "reset", "--hard", "--quiet"], cwd=dest)
    run(["git", "clean", "-ffdqx"], cwd=dest)
    return dest


def write_case_files(
    instance: dict[str, Any],
    case_dir: Path,
    patch_text: str,
    timeout_seconds: int,
) -> None:
    instance_id = require_text(instance, "instance_id")
    repo = require_safe_repo(instance)
    base_commit = require_safe_base_commit(instance)
    problem = require_text(instance, "problem_statement")
    case_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "id": instance_id,
        "category": "high-risk",
        "difficulty": instance.get("difficulty") or "swebench",
        "timeout_seconds": timeout_seconds,
        "required_tools": ["git", "python3"],
        "browser": False,
        "deps_change_expected": True,
        "intent": f"SWE-bench issue for {repo} at {base_commit}: resolve the supplied problem statement without using the gold patch.",
        "source": {
            "benchmark": "SWE-bench",
            "repo": repo,
            "base_commit": base_commit,
            "issue_url": instance.get("issue_url"),
            "pr_url": instance.get("pr_url"),
            "version": instance.get("version"),
        },
    }
    (case_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf8")

    spec = f"""---
id: "{instance_id}"
title: "SWE-bench {instance_id}"
status: planned
complexity: high
depends-on: []
---

# SWE-bench {instance_id}

## Context

Repository: `{repo}`
Base commit: `{base_commit}`

This case is imported from a SWE-bench-style instance. Treat the problem
statement below as the visible user contract. Do not use the gold `patch` or
`test_patch` fields as implementation guidance during model generation or
review.

## Requirements

- [ ] Resolve the reported issue described in the problem statement.
- [ ] Preserve existing behavior outside the issue's scope.
- [ ] Keep the implementation consistent with the repository's local style and
      dependency policy.
- [ ] Surface failures explicitly; do not hide errors behind silent fallbacks.

## Problem Statement

{problem}

## Constraints

- Do not inspect or rely on the SWE-bench gold solution patch while producing
  or judging a candidate patch.
- Do not add broad rewrites, unrelated formatting churn, or new dependencies
  unless the problem statement strictly requires them.
- Frozen VERIFY compares reviewers on the same already-applied candidate patch;
  it is review evidence, not a full SWE-bench solve-rate measurement.

## Verification

- Run the official SWE-bench evaluator separately for solve-rate evidence.
- Use `/devlyn:resolve --verify-only` here only to compare solo vs gated pair
  review of the frozen candidate patch against the visible problem statement.
"""
    (case_dir / "spec.md").write_text(spec, encoding="utf8")
    (case_dir / "task.txt").write_text(problem + "\n", encoding="utf8")
    (case_dir / "expected.json").write_text(
        json.dumps(
            {
                "verification_commands": [],
                "forbidden_patterns": [],
                "required_files": [],
                "forbidden_files": [],
                "tier_a_waivers": [],
                "spec_output_files": [],
                "max_deps_added": 999,
            },
            indent=2,
        )
        + "\n",
        encoding="utf8",
    )
    (case_dir / "setup.sh").write_text("#!/usr/bin/env bash\nset -euo pipefail\n", encoding="utf8")
    (case_dir / "setup.sh").chmod(0o755)
    notes = f"""# {instance_id} — SWE-bench Frozen VERIFY Case

Source repo: `{repo}`
Base commit: `{base_commit}`

This case exists to measure whether gated pair VERIFY catches verdict-binding
review issues that solo VERIFY misses on a fixed candidate patch. It does not
replace official SWE-bench pass/fail evaluation.
"""
    (case_dir / "NOTES.md").write_text(notes, encoding="utf8")
    (case_dir / "model.patch").write_text(patch_text, encoding="utf8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instance-json", required=True, type=Path)
    parser.add_argument("--model-patch", required=True, type=Path)
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
    parser.add_argument(
        "--repo-dir",
        type=Path,
        help="Local clone/source repo to copy instead of cloning GitHub; useful for tests and cached runs.",
    )
    parser.add_argument("--timeout-seconds", type=positive_int, default=2400)
    args = parser.parse_args()

    instance = read_json(args.instance_json)
    instance_id = require_text(instance, "instance_id")
    if not SAFE_ID.match(instance_id):
        raise ValueError(f"unsafe instance_id for path/spec use: {instance_id!r}")
    patch_text = args.model_patch.read_text(encoding="utf8")
    if not patch_text.strip():
        raise ValueError(f"model patch is empty: {args.model_patch}")

    repo_path = prepare_repo(instance, args.repo_dir, args.repos_root)
    case_dir = args.cases_root / instance_id
    write_case_files(instance, case_dir, patch_text, args.timeout_seconds)

    command = [
        "bash",
        "benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh",
        "--fixture",
        instance_id,
        "--fixtures-root",
        str(args.cases_root),
        "--base-repo",
        str(repo_path),
        "--diff",
        str(case_dir / "model.patch"),
        "--pair-mode",
        "gated",
    ]
    (case_dir / "run-command.txt").write_text(shlex.join(command) + "\n", encoding="utf8")
    print(
        json.dumps(
            {
                "instance_id": instance_id,
                "case_dir": str(case_dir),
                "repo_dir": str(repo_path),
                "run_command": command,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
