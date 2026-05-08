#!/usr/bin/env python3
"""Prepare a SWE-bench instance worktree for producing a candidate patch."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


SAFE_ID = re.compile(r"^[A-Za-z0-9_.-]+$")


def run(cmd: list[str], cwd: Path | None = None) -> None:
    subprocess.run(cmd, cwd=cwd, check=True)


def read_instances(path: Path) -> list[dict[str, Any]]:
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


def require_text(instance: dict[str, Any], key: str) -> str:
    value = instance.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"SWE-bench instance missing non-empty {key!r}")
    return value.strip()


def pick_instance(path: Path, instance_id: str) -> dict[str, Any]:
    matches = [row for row in read_instances(path) if row.get("instance_id") == instance_id]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {instance_id!r} row in {path}, found {len(matches)}")
    return matches[0]


def repo_cache_name(repo: str, base_commit: str) -> str:
    return f"{repo.replace('/', '__')}-{base_commit[:12]}"


def prepare_repo(instance: dict[str, Any], repos_root: Path) -> Path:
    repo = require_text(instance, "repo")
    base_commit = require_text(instance, "base_commit")
    repos_root.mkdir(parents=True, exist_ok=True)
    dest = repos_root / repo_cache_name(repo, base_commit)

    if not dest.exists():
        run(["git", "clone", "--quiet", f"https://github.com/{repo}.git", str(dest)])

    run(["git", "fetch", "--quiet", "--all", "--tags"], cwd=dest)
    run(["git", "checkout", "--quiet", base_commit], cwd=dest)
    run(["git", "reset", "--hard", "--quiet"], cwd=dest)
    run(["git", "clean", "-ffdqx"], cwd=dest)
    return dest


def copy_worktree(repo_path: Path, worktree: Path) -> None:
    if worktree.exists():
        shutil.rmtree(worktree)
    run(["git", "clone", "--quiet", "--no-hardlinks", str(repo_path), str(worktree)])
    run(["git", "checkout", "--quiet", "HEAD"], cwd=worktree)
    run(["git", "reset", "--hard", "--quiet"], cwd=worktree)
    run(["git", "clean", "-ffdqx"], cwd=worktree)


def write_spec(instance: dict[str, Any], worktree: Path) -> Path:
    instance_id = require_text(instance, "instance_id")
    repo = require_text(instance, "repo")
    base_commit = require_text(instance, "base_commit")
    problem = require_text(instance, "problem_statement")
    spec_path = worktree / "docs" / "roadmap" / "phase-1" / f"{instance_id}.md"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(
        f"""---
id: "{instance_id}"
title: "SWE-bench {instance_id}"
status: planned
complexity: high
depends-on: []
---

# SWE-bench {instance_id}

Repository: `{repo}`
Base commit: `{base_commit}`

## Requirements

- [ ] Resolve the issue described in the problem statement.
- [ ] Preserve existing behavior outside the issue's scope.
- [ ] Keep the implementation consistent with the repository's local style and
      dependency policy.
- [ ] Add focused regression coverage when practical.

## Problem Statement

{problem}

## Constraints

- Do not inspect or rely on the SWE-bench gold `patch` or `test_patch` fields.
- Do not add broad rewrites, unrelated formatting churn, or new dependencies
  unless the visible problem statement strictly requires them.

## Verification

- Run the most focused practical verification for the changed behavior.
""",
        encoding="utf8",
    )
    return spec_path


def copy_devlyn_context(worktree: Path) -> None:
    skills_src = Path("config/skills")
    if skills_src.exists():
        skills_dst = worktree / ".claude" / "skills"
        if skills_dst.exists():
            shutil.rmtree(skills_dst)
        shutil.copytree(skills_src, skills_dst)
    claude_src = Path("CLAUDE.md")
    if claude_src.exists():
        shutil.copy2(claude_src, worktree / "CLAUDE.md")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instances-jsonl", required=True, type=Path)
    parser.add_argument("--instance-id", required=True)
    parser.add_argument(
        "--repos-root",
        default=Path("benchmark/auto-resolve/external/swebench/repos-solver"),
        type=Path,
    )
    parser.add_argument(
        "--worktrees-root",
        default=Path("benchmark/auto-resolve/external/swebench/worktrees"),
        type=Path,
    )
    parser.add_argument("--copy-devlyn-context", action="store_true")
    args = parser.parse_args()

    instance = pick_instance(args.instances_jsonl, args.instance_id)
    instance_id = require_text(instance, "instance_id")
    if not SAFE_ID.match(instance_id):
        raise ValueError(f"unsafe instance_id for path/spec use: {instance_id!r}")

    repo_path = prepare_repo(instance, args.repos_root)
    worktree = args.worktrees_root / instance_id
    args.worktrees_root.mkdir(parents=True, exist_ok=True)
    copy_worktree(repo_path, worktree)
    spec_path = write_spec(instance, worktree)
    if args.copy_devlyn_context:
        copy_devlyn_context(worktree)

    prompt = (
        f"You are solving SWE-bench instance {instance_id} in this checked-out repository at "
        "the base commit. Do not inspect any gold SWE-bench patch or test_patch. Read the "
        f"local code and the spec at {spec_path.relative_to(worktree)}. Make the smallest "
        "correct source/test change for the visible issue. Run a focused verification "
        "command. At the end, report changed files, verification command, and verdict."
    )
    (worktree / "solve-prompt.txt").write_text(prompt + "\n", encoding="utf8")
    print(
        json.dumps(
            {
                "instance_id": instance_id,
                "repo_dir": str(repo_path),
                "worktree": str(worktree),
                "spec_path": str(spec_path),
                "prompt_file": str(worktree / "solve-prompt.txt"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
