#!/usr/bin/env python3
"""
Lane B instruction-bundle builder (Day-3 driver).

Produces the instruction text a Claude Code session would load from a given git
ref: root CLAUDE.md plus `.claude/rules/**/*.md`. The Day-3 driver injects this
bundle into the [INSTRUCTIONS_BUNDLE] slot of the measurement subagent's prompt.
Because the driver runs `claude --bare` (CLAUDE.md auto-discovery disabled), the
bundle is the ONLY instruction-text channel — it must be a faithful snapshot.

Run during USER setup (§A of RUNBOOK.md), before the clean session launches,
because it needs read access to the devlyn repo's git history. The clean
measurement session never touches the devlyn repo.

Usage:
  build-bundle.py --repo-root <devlyn-repo> --ref <sha-or-ref> --out <bundle-dir>

Writes:
  <bundle-dir>/bundle.md             concatenated instruction text
  <bundle-dir>/bundle.manifest.json  {ref, resolved_ref, files[], unresolved_imports[], sha256}

@import handling — FAIL-CLOSED. A faithful bundle must expand `@path` imports at
their token site (Claude Code inlines them there). Inline expansion is NOT
implemented here because every devlyn ref measured to date has zero resolvable
imports (root CLAUDE.md's only `@` tokens — `@ts-ignore`, `@HANDOFF.md` — sit in
code spans or name files absent at the ref). Rather than silently APPEND imports
out of position, this builder ABORTS if it finds any `@path` that resolves at
the ref. That converts a silent fidelity bug into a loud stop: implement inline
expansion before measuring such a ref. Imports that do not resolve are recorded
under `unresolved_imports` and ignored (a ref legitimately may predate a path a
later commit added).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

# `@path` import token: `@` at start-of-line or after whitespace, then a path
# run. Trailing sentence punctuation is trimmed after capture.
IMPORT_RE = re.compile(r"(?:^|(?<=\s))@([^\s`)\]]+)")


def git_show(repo_root: str, ref: str, path: str) -> str | None:
    """Content at <ref>:<path>, or None if it does not exist at the ref."""
    proc = subprocess.run(
        ["git", "-C", repo_root, "show", f"{ref}:{path}"],
        capture_output=True, text=True,
    )
    return proc.stdout if proc.returncode == 0 else None


def resolve_ref(repo_root: str, ref: str) -> str:
    proc = subprocess.run(
        ["git", "-C", repo_root, "rev-parse", "--verify", f"{ref}^{{commit}}"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        sys.exit(f"build-bundle: error: ref not found in repo: {ref}")
    return proc.stdout.strip()


def list_rule_files(repo_root: str, ref: str) -> list[str]:
    """`.claude/rules/**/*.md` at the ref, sorted. Rules have no @-token site,
    so appending them after CLAUDE.md is a faithful representation of how Claude
    Code loads them (as additional files)."""
    proc = subprocess.run(
        ["git", "-C", repo_root, "ls-tree", "-r", "--name-only", ref, "--", ".claude/rules"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return []
    return sorted(line for line in proc.stdout.splitlines() if line.endswith(".md"))


def strip_code(text: str) -> str:
    """Blank out fenced blocks and inline code spans so `@` tokens inside them
    (e.g. `@ts-ignore`) are not mistaken for imports."""
    out: list[str] = []
    in_fence = False
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            out.append("")
        elif in_fence:
            out.append("")
        else:
            out.append(re.sub(r"`[^`]*`", "", line))
    return "\n".join(out)


def find_imports(text: str) -> list[str]:
    """Ordered, de-duplicated import paths in `text` (code spans/fences excluded)."""
    seen: set[str] = set()
    ordered: list[str] = []
    for raw in IMPORT_RE.findall(strip_code(text)):
        path = raw.rstrip(".,;:!?")
        if path and path not in seen:
            seen.add(path)
            ordered.append(path)
    return ordered


def norm_repo_path(raw: str) -> str | None:
    """Normalize an import path (relative to repo root, where CLAUDE.md lives)
    to a repo-relative POSIX path. None if it escapes the repo or is home/
    absolute (not reachable via `git show <ref>:`)."""
    if raw.startswith("~") or raw.startswith("/"):
        return None
    parts: list[str] = []
    for part in PurePosixPath(raw).parts:
        if part == ".":
            continue
        if part == "..":
            if not parts:
                return None
            parts.pop()
        else:
            parts.append(part)
    return "/".join(parts) if parts else None


def build(repo_root: str, ref: str) -> tuple[str, dict]:
    resolved = resolve_ref(repo_root, ref)

    root_body = git_show(repo_root, ref, "CLAUDE.md")
    if root_body is None:
        sys.exit(f"build-bundle: error: {ref}:CLAUDE.md does not exist "
                 f"— not a valid measurement ref")

    resolved_imports: list[str] = []
    unresolved: list[dict] = []
    for raw in find_imports(root_body):
        norm = norm_repo_path(raw)
        if norm is None:
            unresolved.append({"raw": raw, "reason": "outside-repo"})
        elif git_show(repo_root, ref, norm) is not None:
            resolved_imports.append(norm)
        else:
            unresolved.append({"raw": raw, "resolved": norm, "reason": "absent-at-ref"})

    if resolved_imports:
        sys.exit(f"build-bundle: error: {ref}:CLAUDE.md has @imports that resolve "
                 f"at this ref: {resolved_imports}. Inline import expansion is not "
                 f"implemented — implement it before measuring this ref; appending "
                 f"imports would misrepresent their position and precedence.")

    def file_entry(path: str, body: str, kind: str) -> dict:
        return {"path": path, "kind": kind,
                "bytes": len(body.encode("utf-8")),
                "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest()}

    files = [file_entry("CLAUDE.md", root_body, "claude_md")]
    sections = [root_body]
    for rule_path in list_rule_files(repo_root, ref):
        body = git_show(repo_root, ref, rule_path)
        if body is None:
            continue
        files.append(file_entry(rule_path, body, "rule"))
        sections.append(f"\n\n<!-- lane-b-bundle: rule {rule_path} -->\n\n{body}")

    bundle_md = "".join(sections)
    if not bundle_md.endswith("\n"):
        bundle_md += "\n"

    manifest = {
        "schema_version": "v1",
        "ref": ref,
        "resolved_ref": resolved,
        "files": files,
        "unresolved_imports": unresolved,
        "import_handling": "fail-closed-if-resolvable",
        "sha256": hashlib.sha256(bundle_md.encode("utf-8")).hexdigest(),
        "bytes": len(bundle_md.encode("utf-8")),
    }
    return bundle_md, manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--ref", required=True)
    parser.add_argument("--out", required=True,
                        help="bundle directory — bundle.md + bundle.manifest.json land here")
    args = parser.parse_args()

    if subprocess.run(["git", "-C", args.repo_root, "rev-parse", "--git-dir"],
                       capture_output=True).returncode != 0:
        sys.exit(f"build-bundle: error: --repo-root is not a git repository: {args.repo_root}")

    bundle_md, manifest = build(args.repo_root, args.ref)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "bundle.md").write_text(bundle_md, encoding="utf-8")
    (out_dir / "bundle.manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"build-bundle: {args.ref} ({manifest['resolved_ref'][:12]}) -> {out_dir}")
    print(f"  files={len(manifest['files'])} "
          f"unresolved_imports={len(manifest['unresolved_imports'])} "
          f"sha256={manifest['sha256'][:12]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
