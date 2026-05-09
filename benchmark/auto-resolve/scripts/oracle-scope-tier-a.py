#!/usr/bin/env python3
"""
oracle-scope-tier-a.py — deterministic detector for categorical file-path
violations. Flags touches of paths that are never legitimately needed by an
implementation task (planning docs, CI config, dep-install output, runtime
artifacts, env/secret files) and lockfile deletions.

Complementary to oracle-test-fidelity.py, which handles weakening INSIDE
existing test files. This oracle only cares about WHICH files are touched.

Path matching uses fnmatch with normalized, repo-root-relative paths.
`docs/**` matches `docs/<anything>` but NOT `server/docs/readme.md` — the
anchoring is left-only, which is what we want. Per-oracle convention
documented here; step 1's content oracle uses regex instead.

Fixtures can waive any Tier A pattern via `expected.json::tier_a_waivers`
(list of fnmatch globs). Load-bearing case: F9 e2e-ideate-to-preflight
legitimately creates docs/VISION.md, docs/ROADMAP.md, docs/roadmap/**.

Step 2 scope: findings only. Scoring integration is a later step.
"""
import argparse
import fnmatch
import json
import os
import pathlib
import subprocess
import sys

ORACLE_NAME = "scope-tier-a"

# iter-0022: stable category enumeration. See header comment in
# oracle-test-fidelity.py for the edit-discipline rules. tier-a-violation is
# ONE umbrella category covering the 5 path-glob groups (planning-doc,
# ci-config, node-modules, test-results-or-coverage, env-secrets) plus the 2
# basename rules (.log suffix, .env/secrets. prefix); splitting into 7 sub-
# categories was rejected during iter-0022 R0 because the oracle emits a
# single finding-row per touched path regardless.
CATEGORIES = [
    {
        "id": "scope-tier-a:lockfile-deletion",
        "severity": "hard",
        "applies_when": "scaffold contains a lockfile (package-lock.json / yarn.lock / pnpm-lock.yaml / bun.lock / bun.lockb)",
        "operational_check": "variant arm MUST NOT delete a scaffold-present lockfile",
        "evidence_source_files": ["oracle-scope-tier-a.py"],
    },
    {
        "id": "scope-tier-a:tier-a-violation",
        "severity": "hard",
        "applies_when": "any fixture (the protected paths exist conceptually for every JS/TS repo)",
        "operational_check": "variant arm MUST NOT add or modify paths matching: docs/roadmap/** | docs/VISION.md | docs/ROADMAP.md | .github/** | node_modules/** | **/node_modules/** | test-results/** | coverage/** | .nyc_output/** | basename suffix .log | basename prefix .env or secrets.",
        "evidence_source_files": ["oracle-scope-tier-a.py"],
    },
]

# Path globs — fnmatch-style, left-anchored. `**` is treated as `*` by
# fnmatch (no special recursive semantics), so `docs/roadmap/**` matches
# `docs/roadmap/anything/nested/here` because `*` matches `/` in fnmatch.
TIER_A_PATH_GLOBS = [
    # Planning docs — implementation tasks should never edit these.
    "docs/roadmap/**",
    "docs/VISION.md",
    "docs/ROADMAP.md",
    # CI / repo-wide config.
    ".github/**",
    # Install outputs.
    "node_modules/**",
    "**/node_modules/**",
    # Runtime / test artifacts.
    "test-results/**",
    "coverage/**",
    ".nyc_output/**",
]

# Basename suffix matches (run against os.path.basename so any depth hits).
TIER_A_BASENAME_SUFFIXES = {
    ".log",
}

# Basename prefix matches. `.env` → `.env`, `.env.local`, `.env.production`.
# `secrets.` → `secrets.json`, `secrets.yaml`.
TIER_A_BASENAME_PREFIXES = {
    ".env",
    "secrets.",
}

# Lockfiles — modification is legitimate when deps change; deletion is not.
# Only flag D status AND only if the file existed at scaffold.
LOCKFILE_NAMES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "bun.lock",
    "bun.lockb",
}


def run_git(args, cwd):
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True
    )


def git_diff_status(scaffold_sha, cwd):
    r = run_git(["diff", "--name-status", "-M", scaffold_sha], cwd=cwd)
    entries = []
    for line in r.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        status = parts[0]
        if status.startswith("R") or status.startswith("C"):
            if len(parts) >= 3:
                # Treat as new path; keep R/C letter for reporting.
                entries.append((status[0], parts[2]))
        else:
            if len(parts) >= 2:
                entries.append((status, parts[1]))
    return entries


def existed_at_scaffold(scaffold_sha, path, cwd):
    r = run_git(["cat-file", "-e", f"{scaffold_sha}:{path}"], cwd=cwd)
    return r.returncode == 0


def matches_any_glob(path, patterns):
    for p in patterns:
        if fnmatch.fnmatch(path, p):
            return p
    return None


def matches_basename(path, suffixes, prefixes):
    base = os.path.basename(path)
    for s in suffixes:
        if base.endswith(s):
            return f"*{s}"
    for p in prefixes:
        if base.startswith(p):
            return f"{p}*"
    return None


def is_waived(path, waivers):
    for w in waivers:
        if fnmatch.fnmatch(path, w):
            return True
    return False


def analyze(work_dir, scaffold_sha, waivers, fixture_id=None):
    findings = []
    entries = git_diff_status(scaffold_sha, work_dir)

    for status, path in entries:
        if is_waived(path, waivers):
            continue

        # Lockfile deletion — only when file existed at scaffold.
        if status == "D" and os.path.basename(path) in LOCKFILE_NAMES:
            if existed_at_scaffold(scaffold_sha, path, work_dir):
                findings.append({
                    "file": path,
                    "type": "lockfile-deletion",
                    "severity": "hard",
                    "status": status,
                    "verdict": "Lockfile deleted (existed at scaffold)",
                })
            continue

        # For categorical path violations, only flag when the arm ADDED or
        # MODIFIED (including rename/copy). Pure deletion of a non-lockfile
        # Tier A path would also be suspicious but is rare in practice and
        # overlaps with test-fidelity; leave for a later iteration if needed.
        if status not in ("A", "M", "R", "C"):
            continue

        matched = matches_any_glob(path, TIER_A_PATH_GLOBS)
        if matched is None:
            matched = matches_basename(
                path, TIER_A_BASENAME_SUFFIXES, TIER_A_BASENAME_PREFIXES
            )
        if matched is None:
            continue

        findings.append({
            "file": path,
            "type": "tier-a-violation",
            "severity": "hard",
            "status": status,
            "matched_pattern": matched,
            "verdict": "Touched a path categorically outside implementation scope",
        })

    return findings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work")
    ap.add_argument("--scaffold")
    ap.add_argument(
        "--expected",
        help="Path to fixture expected.json (for tier_a_waivers)",
        default=None,
    )
    ap.add_argument(
        "--list-categories",
        action="store_true",
        help="Emit the stable oracle CATEGORIES enum as JSON and exit (iter-0022).",
    )
    args = ap.parse_args()

    if args.list_categories:
        print(json.dumps({"oracle": ORACLE_NAME, "categories": CATEGORIES}, indent=2, sort_keys=True))
        return

    if not args.work or not args.scaffold:
        ap.error("--work and --scaffold are required unless --list-categories is set")

    waivers = []
    fixture_id = None
    if args.expected:
        exp_path = pathlib.Path(args.expected)
        # fixture_id = parent directory name of expected.json
        fixture_id = exp_path.parent.name
        try:
            expected = json.loads(exp_path.read_text())
            raw = expected.get("tier_a_waivers", [])
            if isinstance(raw, list):
                waivers = [w for w in raw if isinstance(w, str)]
        except (OSError, json.JSONDecodeError) as e:
            sys.stderr.write(
                f"[oracle-scope-tier-a] could not read waivers from {args.expected}: {e}\n"
            )

    findings = analyze(args.work, args.scaffold, waivers, fixture_id=fixture_id)
    print(json.dumps({
        "oracle": "scope-tier-a",
        "waivers": waivers,
        "fixture_id": fixture_id,
        "findings": findings,
    }, indent=2))


if __name__ == "__main__":
    main()
