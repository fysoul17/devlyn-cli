#!/usr/bin/env python3
"""
oracle-scope-tier-b.py — transitive-import classifier for benchmark arm diffs.

For each arm-touched file that is NOT in Tier C (spec_output_files) and NOT
in tier_a_waivers, determines whether it is reachable from a Tier C seed via
the static import/require graph:
- Reachable  → `tier-b-reachable` (legitimate structural extension)
- Unreachable → `scope-unmatched` (may overlap with step 2's Tier A globals;
  step 5's scoring dedupes against step 2)

BFS seeds = (spec_output_files glob matches in POST-arm work_dir) ∩
            (arm-touched files).
The intersection prevents BFS blow-up when Tier C globs are broad (e.g.
`bin/**`) and keeps the trace meaningful — "what the arm changed and where
did it propagate?" not "every theoretically-in-scope file."

Step 4 scope:
- JS/TS only (matches step 1 language scope). TS tsconfig path aliases NOT
  handled; none of the current fixtures use them.
- Static string-literal imports only. Dynamic requires via variables
  (`require(someVar)`) are invisible to the trace — documented limitation.
- Findings-only at this stage; scoring integration is step 5.

The `trace_method: "regex"` field in the output lets step 5 differentiate
heuristic traces from future AST-based traces without schema changes.
"""
import argparse
import fnmatch
import json
import os
import pathlib
import re
import subprocess
import sys

TRACE_METHOD = "regex"

# Static-import patterns. Order matters only for readability; duplicates
# are harmless because we dedupe by resolved path in BFS.
IMPORT_PATTERNS = [
    # CommonJS: require('./foo')
    r"require\(\s*['\"]([^'\"]+)['\"]\s*\)",
    # ES module static import (with or without binding)
    r"import\s+(?:[\w*{},\s\n]+\s+from\s+)?['\"]([^'\"]+)['\"]",
    # ES module re-export
    r"export\s+(?:\*|\{[^}]*\})\s+from\s+['\"]([^'\"]+)['\"]",
    # Dynamic import with string literal
    r"import\(\s*['\"]([^'\"]+)['\"]\s*\)",
]

# Extension order for resolution. .json is a valid import target but is a
# leaf (we don't recurse into it).
RESOLUTION_EXTENSIONS = (".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".json")
TRACEABLE_EXTENSIONS = (".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx")
INDEX_EXTENSIONS = (".js", ".mjs", ".ts")


def is_relative(spec: str) -> bool:
    return spec.startswith("./") or spec.startswith("../") or spec.startswith("/")


def resolve_import(source_rel: str, spec: str, work_dir: pathlib.Path):
    """Resolve a relative import. Returns a repo-root-relative path or None."""
    if spec.startswith("/"):
        target = spec.lstrip("/")
    else:
        source_dir = os.path.dirname(source_rel)
        target = os.path.normpath(os.path.join(source_dir, spec))
    # Normalize to forward slashes
    target = target.replace(os.sep, "/")
    # Reject paths that escape work_dir (e.g. `../../outside-repo`)
    if target.startswith("../") or target.startswith("/"):
        return None
    # Exact file
    if (work_dir / target).is_file():
        return target
    # Suffix candidates
    for ext in RESOLUTION_EXTENSIONS:
        cand = f"{target}{ext}"
        if (work_dir / cand).is_file():
            return cand
    # /index.* in directory
    for ext in INDEX_EXTENSIONS:
        cand = f"{target}/index{ext}"
        if (work_dir / cand).is_file():
            return cand
    return None


def read_imports(file_path: pathlib.Path):
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    specs = []
    for pattern in IMPORT_PATTERNS:
        for m in re.finditer(pattern, content, re.MULTILINE):
            specs.append(m.group(1))
    return specs


def bfs_trace(seeds, work_dir: pathlib.Path):
    """BFS following static imports. Returns dict: path → (depth, via)."""
    reachable = {s: (0, None) for s in seeds}
    queue = [(s, 0) for s in seeds]
    while queue:
        current, depth = queue.pop(0)
        if not any(current.endswith(ext) for ext in TRACEABLE_EXTENSIONS):
            continue
        full = work_dir / current
        if not full.is_file():
            continue
        for spec in read_imports(full):
            if not is_relative(spec):
                continue
            resolved = resolve_import(current, spec, work_dir)
            if resolved is None or resolved in reachable:
                continue
            if "node_modules" in resolved.split("/"):
                continue
            reachable[resolved] = (depth + 1, current)
            queue.append((resolved, depth + 1))
    return reachable


def git_touched_files(scaffold_sha: str, work_dir: pathlib.Path):
    """Arm-touched files (relative paths), excluding deletions."""
    r = subprocess.run(
        ["git", "diff", "--name-status", "-M", scaffold_sha],
        cwd=str(work_dir), capture_output=True, text=True,
    )
    touched = []
    for line in r.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status = parts[0]
        if status == "D":
            continue
        path = parts[-1]
        touched.append(path)
    return touched


def match_any(path: str, patterns) -> bool:
    return any(fnmatch.fnmatch(path, p) for p in patterns)


def analyze(work_dir_str: str, scaffold_sha: str, tier_c_globs, waivers,
            fixture_id=None):
    work_dir = pathlib.Path(work_dir_str).resolve()
    touched = git_touched_files(scaffold_sha, work_dir)

    # Seeds = arm-touched files matching spec_output_files globs.
    seeds = sorted(p for p in touched if match_any(p, tier_c_globs))

    reachable = bfs_trace(seeds, work_dir)

    # Structural exemption: the fixture's own spec file at
    # docs/roadmap/phase-*/<fixture_id>.md is always authorized — DOCS
    # phase Job 1 flips its frontmatter status by design. Kept in sync
    # with oracle-scope-tier-a.py.
    own_spec_globs = []
    if fixture_id:
        own_spec_globs.append(f"docs/roadmap/phase-*/{fixture_id}.md")

    findings = []
    for path in sorted(touched):
        if match_any(path, tier_c_globs):
            continue
        if match_any(path, waivers):
            continue
        if match_any(path, own_spec_globs):
            continue
        if path in reachable:
            depth, via = reachable[path]
            findings.append({
                "file": path,
                "type": "tier-b-reachable",
                "severity": "info",
                "reachable_via": via,
                "depth": depth,
                "verdict": "Reachable from Tier C via import chain",
            })
        else:
            findings.append({
                "file": path,
                "type": "scope-unmatched",
                "severity": "warn",
                "verdict": "Not in Tier C, not reachable from Tier C via static imports",
            })

    return seeds, findings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--scaffold", required=True)
    ap.add_argument("--expected", required=True,
                    help="Path to fixture expected.json")
    args = ap.parse_args()

    try:
        expected = json.loads(pathlib.Path(args.expected).read_text())
    except (OSError, json.JSONDecodeError) as e:
        sys.stderr.write(f"[oracle-scope-tier-b] cannot read expected: {e}\n")
        print(json.dumps({
            "oracle": "scope-tier-b",
            "trace_method": TRACE_METHOD,
            "tier_c_seeds_matched": [],
            "findings": [],
            "error": f"expected.json unreadable: {e}",
        }, indent=2))
        return

    tier_c = expected.get("spec_output_files", [])
    waivers = expected.get("tier_a_waivers", [])
    # fixture_id = parent directory name of expected.json
    fixture_id = pathlib.Path(args.expected).parent.name

    if not tier_c:
        print(json.dumps({
            "oracle": "scope-tier-b",
            "trace_method": TRACE_METHOD,
            "tier_c_seeds_matched": [],
            "fixture_id": fixture_id,
            "findings": [],
            "error": "no spec_output_files in expected.json",
        }, indent=2))
        return

    seeds, findings = analyze(args.work, args.scaffold, tier_c, waivers,
                              fixture_id=fixture_id)
    print(json.dumps({
        "oracle": "scope-tier-b",
        "trace_method": TRACE_METHOD,
        "tier_c_seeds_matched": seeds,
        "fixture_id": fixture_id,
        "findings": findings,
    }, indent=2))


if __name__ == "__main__":
    main()
