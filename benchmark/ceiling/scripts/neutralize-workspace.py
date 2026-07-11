#!/usr/bin/env python3
"""Create an identity-neutral, deterministic git baseline in a workspace clone."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


PROJECT_NAME = "harbor-tools"
AUTHOR_NAME = "Project Maintainer"
AUTHOR_EMAIL = "maintainer@example.com"
COMMIT_DATE = "2000-01-01T00:00:00Z"
COMMIT_MESSAGE = "Initial project snapshot"

IDENTITY_REPLACEMENTS = (
    ("package.json", '"name": "bench-test-repo"', f'"name": "{PROJECT_NAME}"'),
    (
        "package.json",
        '"description": "Deterministic base Node project for devlyn-cli '
        'auto-resolve benchmarks. Every fixture starts from a fresh copy of '
        'this directory."',
        '"description": "A small Node.js toolkit with a command-line interface and HTTP server."',
    ),
    ("package-lock.json", '"bench-test-repo"', f'"{PROJECT_NAME}"'),
    (
        "bin/cli.js",
        "// bench-test-repo — tiny CLI used as the deterministic base for benchmark fixtures.",
        "// harbor-tools — small command-line utilities for local workflows.",
    ),
    (
        "bin/cli.js",
        "// Fixtures extend or modify this file; keep the baseline minimal and obvious.",
        "// Keep the core commands minimal and easy to understand.",
    ),
    (
        "playwright.config.js",
        "// Playwright config used only by browser-validate benchmark fixtures.",
        "// Playwright config for the browser checks.",
    ),
    (
        "playwright.config.js",
        "// Runs against web/index.html served via `npx serve web` (fixture setup.sh",
        "// Runs against web/index.html served via `npx serve web` (the check",
    ),
    (
        "server/index.js",
        "// Tiny Express server used by backend-contract fixtures. Intentionally small.",
        "// Tiny Express server with a deliberately small API surface.",
    ),
    ("server/index.js", "bench-test-repo", PROJECT_NAME),
    ("web/index.html", "bench-test-repo", PROJECT_NAME),
    (
        "web/index.html",
        "Minimal page used by browser-validate benchmark fixtures.",
        "Minimal page for checking the browser interaction.",
    ),
)


class NeutralizationError(RuntimeError):
    """The workspace cannot be neutralized without ambiguity."""


def run(command: list[str], workspace: Path, *, capture: bool = False) -> str:
    completed = subprocess.run(
        command,
        cwd=workspace,
        env={
            **os.environ,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
        },
        check=False,
        stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise NeutralizationError(
            f"command failed ({completed.returncode}): {' '.join(command)}: {detail}"
        )
    return completed.stdout.decode("utf-8", errors="strict") if capture else ""


def replace(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise NeutralizationError(f"expected identity text missing from {path}: {old!r}")
    path.write_text(text.replace(old, new), encoding="utf-8")


def transform_patch(input_path: Path, output_path: Path) -> None:
    patch = input_path.read_bytes()
    for _relative_path, old, new in IDENTITY_REPLACEMENTS:
        patch = patch.replace(old.encode("utf-8"), new.encode("utf-8"))
    output_path.write_bytes(patch)


def neutralize_seed_identity(workspace: Path) -> None:
    required = [
        "README.md",
        "package.json",
        "package-lock.json",
        "bin/cli.js",
        "playwright.config.js",
        "server/index.js",
        "web/index.html",
        ".gitignore",
    ]
    missing = [name for name in required if not (workspace / name).is_file()]
    if missing:
        raise NeutralizationError(
            "seed identity surface missing: " + ", ".join(sorted(missing))
        )

    (workspace / "README.md").write_text(
        """# harbor-tools

A small Node.js toolkit with a command-line interface, an HTTP server, and a
minimal browser page.

## Commands

- `npm test` runs the test suite.
- `npm run cli -- --help` prints command-line help.
- `npm start` starts the HTTP server.

The project intentionally keeps each component small and independent.
""",
        encoding="utf-8",
    )
    for relative_path, old, new in IDENTITY_REPLACEMENTS:
        replace(workspace / relative_path, old, new)

    ignore = workspace / ".gitignore"
    lines = ignore.read_text(encoding="utf-8").splitlines()
    if ".devlyn" not in lines:
        raise NeutralizationError("expected .devlyn identity entry missing from .gitignore")
    ignore.write_text(
        "\n".join(line for line in lines if line != ".devlyn") + "\n",
        encoding="utf-8",
    )

    forbidden = (
        "devlyn-cli",
        "auto-resolve benchmark",
        "benchmark fixture",
        "bench-test-repo",
    )
    for name in required:
        text = (workspace / name).read_text(encoding="utf-8", errors="replace").lower()
        hit = next((token for token in forbidden if token in text), None)
        if hit is not None:
            raise NeutralizationError(f"identity token {hit!r} remains in {name}")


def atomic_write_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def neutralize(workspace: Path, seed_derived: bool) -> dict[str, object]:
    if not (workspace / ".git").exists():
        raise NeutralizationError(f"workspace is not a git repository: {workspace}")
    run(["git", "reset", "--hard", "--quiet"], workspace)
    run(["git", "clean", "-ffdqx"], workspace)
    if seed_derived:
        neutralize_seed_identity(workspace)

    diff = run(
        ["git", "diff", "--binary", "--no-ext-diff", "HEAD", "--", "."],
        workspace,
        capture=True,
    ).encode("utf-8")
    diff_sha256 = hashlib.sha256(diff).hexdigest()

    shutil.rmtree(workspace / ".git")
    run(["git", "init", "--quiet"], workspace)
    run(["git", "config", "core.logAllRefUpdates", "false"], workspace)
    run(["git", "add", "--all"], workspace)
    commit_env = {
        "GIT_AUTHOR_NAME": AUTHOR_NAME,
        "GIT_AUTHOR_EMAIL": AUTHOR_EMAIL,
        "GIT_AUTHOR_DATE": COMMIT_DATE,
        "GIT_COMMITTER_NAME": AUTHOR_NAME,
        "GIT_COMMITTER_EMAIL": AUTHOR_EMAIL,
        "GIT_COMMITTER_DATE": COMMIT_DATE,
    }
    completed = subprocess.run(
        ["git", "commit", "--quiet", "--no-gpg-sign", "-m", COMMIT_MESSAGE],
        cwd=workspace,
        env={
            **os.environ,
            **commit_env,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
        },
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        raise NeutralizationError(
            "deterministic commit failed: "
            + completed.stderr.decode("utf-8", errors="replace").strip()
        )

    baseline = run(["git", "rev-parse", "HEAD"], workspace, capture=True).strip()
    remotes = [
        line for line in run(["git", "remote"], workspace, capture=True).splitlines() if line
    ]
    reflogs = sorted(
        str(path.relative_to(workspace / ".git"))
        for path in (workspace / ".git" / "logs").rglob("*")
        if path.is_file()
    ) if (workspace / ".git" / "logs").exists() else []
    if remotes or reflogs:
        raise NeutralizationError(
            f"neutral git metadata leaked: remotes={remotes} reflogs={reflogs}"
        )
    return {
        "schema_version": 1,
        "seed_derived": seed_derived,
        "neutral_project_name": PROJECT_NAME if seed_derived else None,
        "neutralization_diff_sha256": diff_sha256,
        "neutralization_diff_bytes": len(diff),
        "neutral_baseline_sha": baseline,
        "author_name": AUTHOR_NAME,
        "author_email": AUTHOR_EMAIL,
        "commit_date": COMMIT_DATE,
        "commit_message": COMMIT_MESSAGE,
        "git_remotes": remotes,
        "git_reflogs": reflogs,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--seed-derived", action="store_true")
    parser.add_argument("--report", type=Path)
    parser.add_argument(
        "--transform-patch",
        nargs=2,
        type=Path,
        metavar=("IN", "OUT"),
    )
    args = parser.parse_args()
    if args.transform_patch is not None:
        if args.workspace is not None or args.report is not None or args.seed_derived:
            parser.error("--transform-patch cannot be combined with workspace neutralization")
        transform_patch(*args.transform_patch)
        return 0
    if args.workspace is None or args.report is None:
        parser.error("--workspace and --report are required for workspace neutralization")
    workspace = args.workspace.resolve()
    report = neutralize(workspace, args.seed_derived)
    atomic_write_json(args.report, report)
    print(report["neutral_baseline_sha"])
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NeutralizationError as exc:
        print(f"neutralize-workspace: {exc}", file=os.sys.stderr)
        raise SystemExit(2)
