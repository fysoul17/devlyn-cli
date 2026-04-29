#!/usr/bin/env python3
"""
pair-plan-idgen.py — emit canonical_id_registry.json for a benchmark fixture.

Reads `expected.json` + `metadata.json` from the fixture directory and the
checked-in oracle scripts' `--list-categories` output (filtered through
metadata.json:pair_plan_oracle_categories). Produces a deterministic,
sorted-by-id registry that `pair-plan-lint.py` validates plans against.

Hard rules (iter-0022 D2 acceptance gates):
  * NEVER reads any path containing `/results/`. A `builtins.open` /
    `os.open` wrapper raises AssertionError if any code path tries.
    Reading archived run artifacts would leak iter-0020 outcome data into
    the registry source-of-truth, contaminating iter-0023 measurement.
  * Same input → byte-identical output (after fixing the volatile
    `generated_at` field via `--generated-at`). Lint Check 13 enforces.
  * Output JSON is sorted by required_invariants[].id, sort_keys=True for
    every dict, indent=2 for human review, trailing newline for POSIX.

See `config/skills/_shared/pair-plan-schema.md` for the full registry
shape and the slug rules implemented here.
"""
import argparse
import builtins
import datetime
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys

ORACLE_SCRIPTS = {
    "test-fidelity":  "oracle-test-fidelity.py",
    "scope-tier-a":   "oracle-scope-tier-a.py",
    "scope-tier-b":   "oracle-scope-tier-b.py",
}

SCHEMA_VERSION = "1"


# ---------------------------------------------------------------------------
# Path trap — refuse any read under a `/results/` directory.
# ---------------------------------------------------------------------------
_real_open = builtins.open
_real_os_open = os.open


def _trap_path(path):
    """Raise if `path` contains a `/results/` segment. Read-side only — call
    this just before opening for read; write-mode opens skip the check."""
    if isinstance(path, (bytes, bytearray)):
        path = path.decode("utf-8", "replace")
    elif isinstance(path, os.PathLike):
        path = os.fspath(path)
    s = str(path).replace("\\", "/")
    if "/results/" in s:
        raise AssertionError(
            f"pair-plan-idgen.py: forbidden read — {s!r} contains '/results/'. "
            "iter-0022 hard rule: idgen MUST NOT read archived run artifacts. "
            "Registry sources are limited to expected.json + metadata.json + checked-in oracle scripts. "
            "Writes to /results/ are legitimate (e.g. preflight output) and are NOT trapped."
        )


def _is_read_mode(args, kwargs):
    """`open()` 1st positional or `mode` kwarg. Default 'r' is read."""
    mode = kwargs.get("mode")
    if mode is None and args:
        mode = args[0]
    if mode is None:
        return True  # default 'r'
    return isinstance(mode, str) and ("w" not in mode and "a" not in mode and "x" not in mode and "+" not in mode)


def _trapped_open(file, *args, **kwargs):
    if _is_read_mode(args, kwargs):
        _trap_path(file)
    return _real_open(file, *args, **kwargs)


def _is_read_flags(flags):
    """`os.open` flags: O_WRONLY | O_RDWR | O_CREAT | O_APPEND | O_TRUNC are write-side."""
    write_bits = (
        getattr(os, "O_WRONLY", 0)
        | getattr(os, "O_RDWR", 0)
        | getattr(os, "O_CREAT", 0)
        | getattr(os, "O_APPEND", 0)
        | getattr(os, "O_TRUNC", 0)
    )
    return (flags & write_bits) == 0


def _trapped_os_open(path, flags, mode=0o777, **kwargs):
    if _is_read_flags(flags):
        _trap_path(path)
    return _real_os_open(path, flags, mode, **kwargs)


def install_path_trap():
    builtins.open = _trapped_open
    os.open = _trapped_os_open


# ---------------------------------------------------------------------------
# Slug + sha helpers.
# ---------------------------------------------------------------------------
def sanitize(s, max_len):
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = s.strip("_")
    return s[:max_len]


def canonical_compact_json(obj):
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def sha8(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:8]


def file_sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def forbidden_pattern_slug(item, index, prior_slugs):
    desc = item.get("description", "")
    files = item.get("files", []) or []
    file0 = files[0] if files else ""
    base = f"forbidden_pattern__{sanitize(desc, 60)}__{sanitize(file0, 30)}"
    if base in prior_slugs:
        return f"{base}__i{index}"
    return base


def verification_slug(verification_obj):
    return f"verification__{sha8(canonical_compact_json(verification_obj))}"


# ---------------------------------------------------------------------------
# Oracle category enumeration via subprocess.
# ---------------------------------------------------------------------------
def list_oracle_categories(scripts_dir, oracle_name):
    script = scripts_dir / ORACLE_SCRIPTS[oracle_name]
    r = subprocess.run(
        [sys.executable, str(script), "--list-categories"],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(r.stdout)
    if payload.get("oracle") != oracle_name:
        raise ValueError(
            f"oracle name mismatch: expected {oracle_name}, got {payload.get('oracle')}"
        )
    return payload["categories"]


# ---------------------------------------------------------------------------
# Registry assembly.
# ---------------------------------------------------------------------------
def build_registry(fixture_dir, scripts_dir, generated_at, repo_root):
    fixture_dir = pathlib.Path(fixture_dir).resolve()
    expected_path = fixture_dir / "expected.json"
    metadata_path = fixture_dir / "metadata.json"

    with open(expected_path, "r", encoding="utf-8") as f:
        expected = json.load(f)
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    fixture_id = metadata.get("id") or fixture_dir.name

    entries = []

    # forbidden_patterns ----------------------------------------------------
    seen_slugs = set()
    for i, item in enumerate(expected.get("forbidden_patterns", []) or []):
        slug = forbidden_pattern_slug(item, i, seen_slugs)
        seen_slugs.add(slug)
        desc = item.get("description", "")
        sev = item.get("severity", "flag")
        files = item.get("files", []) or []
        pattern = item.get("pattern", "")
        entries.append({
            "id": slug,
            "source_field": f"expected.json/forbidden_patterns/{i}",
            "source_ref": f"expected.json:forbidden_patterns[{i}]",
            "operational_check": (
                f"variant arm output MUST NOT contain regex pattern {pattern!r} "
                f"in files {files}; rationale: {desc}"
            ),
            "severity": sev,
            "authority": "expected.json/forbidden_patterns",
        })

    # verification_commands -------------------------------------------------
    for i, item in enumerate(expected.get("verification_commands", []) or []):
        slug = verification_slug(item)
        cmd = item.get("cmd", "")
        exit_code = item.get("exit_code")
        sc = item.get("stdout_contains", []) or []
        sn = item.get("stdout_not_contains", []) or []
        entries.append({
            "id": slug,
            "source_field": f"expected.json/verification_commands/{i}",
            "source_ref": f"expected.json:verification_commands[{i}]",
            "operational_check": (
                f"running `{cmd}` in the post-arm work dir MUST exit with code {exit_code}; "
                f"stdout MUST contain all of {sc}; stdout MUST NOT contain any of {sn}"
            ),
            "severity": "hard",
            "authority": "expected.json/verification_commands",
        })

    # required_files --------------------------------------------------------
    for path in expected.get("required_files", []) or []:
        entries.append({
            "id": f"required_file__{sanitize(path, 60)}",
            "source_field": "expected.json/required_files",
            "source_ref": f"expected.json:required_files[{path}]",
            "operational_check": (
                f"variant arm output MUST contain file {path!r} "
                "(created or preserved)"
            ),
            "severity": "hard",
            "authority": "expected.json/required_files",
        })

    # forbidden_files -------------------------------------------------------
    for path in expected.get("forbidden_files", []) or []:
        entries.append({
            "id": f"forbidden_file__{sanitize(path, 60)}",
            "source_field": "expected.json/forbidden_files",
            "source_ref": f"expected.json:forbidden_files[{path}]",
            "operational_check": (
                f"variant arm output MUST NOT add file {path!r}"
            ),
            "severity": "hard",
            "authority": "expected.json/forbidden_files",
        })

    # spec_output_files -----------------------------------------------------
    for path in expected.get("spec_output_files", []) or []:
        entries.append({
            "id": f"spec_output_file__{sanitize(path, 60)}",
            "source_field": "expected.json/spec_output_files",
            "source_ref": f"expected.json:spec_output_files[{path}]",
            "operational_check": (
                "variant-touched files MUST be inside (or reachable via static "
                f"imports from) the spec_output_files set; {path!r} is one Tier C seed"
            ),
            "severity": "warn",
            "authority": "expected.json/spec_output_files",
        })

    # max_deps_added --------------------------------------------------------
    if "max_deps_added" in expected:
        v = expected["max_deps_added"]
        entries.append({
            "id": f"max_deps_added__{v}",
            "source_field": "expected.json/max_deps_added",
            "source_ref": "expected.json:max_deps_added",
            "operational_check": (
                f"variant arm MUST NOT add more than {v} new npm dependencies "
                "(count delta of package.json:dependencies + devDependencies)"
            ),
            "severity": "hard",
            "authority": "expected.json/max_deps_added",
        })

    # oracle categories per metadata allowlist -----------------------------
    allowlist = metadata.get("pair_plan_oracle_categories", []) or []
    used_oracles = set()
    cat_index = {}
    for entry_id in allowlist:
        if ":" not in entry_id:
            raise ValueError(
                f"malformed pair_plan_oracle_categories entry: {entry_id!r} (expected '<oracle>:<category>')"
            )
        oracle_name = entry_id.split(":", 1)[0]
        if oracle_name not in ORACLE_SCRIPTS:
            raise ValueError(
                f"unknown oracle {oracle_name!r} (known: {sorted(ORACLE_SCRIPTS)})"
            )
        if oracle_name not in cat_index:
            cat_index[oracle_name] = list_oracle_categories(scripts_dir, oracle_name)
        match = next(
            (c for c in cat_index[oracle_name] if c["id"] == entry_id),
            None,
        )
        if match is None:
            available = [c["id"] for c in cat_index[oracle_name]]
            raise ValueError(
                f"oracle {oracle_name!r} has no category {entry_id!r}; available: {available}"
            )
        used_oracles.add(oracle_name)
        entries.append({
            "id": match["id"],
            "source_field": f"oracle/{oracle_name}/{match['id']}",
            "source_ref": f"{ORACLE_SCRIPTS[oracle_name]}",
            "operational_check": match["operational_check"],
            "severity": match["severity"],
            "authority": "metadata/oracle-allowlist",
        })

    # sort entries by id (deterministic) ------------------------------------
    entries.sort(key=lambda e: e["id"])

    # file shas (raw bytes) -------------------------------------------------
    expected_sha = file_sha256(expected_path)
    metadata_sha = file_sha256(metadata_path)
    oracle_shas = {}
    for ora in sorted(used_oracles):
        oracle_shas[ora] = file_sha256(scripts_dir / ORACLE_SCRIPTS[ora])

    # repo-root-relative paths for portability ------------------------------
    def rel(p):
        try:
            return str(pathlib.Path(p).resolve().relative_to(repo_root))
        except ValueError:
            return str(p)

    return {
        "schema_version": SCHEMA_VERSION,
        "fixture_id": fixture_id,
        "generated_at": generated_at,
        "generated_from": {
            "expected_path": rel(expected_path),
            "expected_sha256": expected_sha,
            "metadata_path": rel(metadata_path),
            "metadata_sha256": metadata_sha,
            "oracle_script_shas": oracle_shas,
        },
        "required_invariants": entries,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--fixture",
        required=True,
        help="Path to fixture directory (e.g. benchmark/auto-resolve/fixtures/F2-cli-medium-subcommand)",
    )
    ap.add_argument(
        "--scripts-dir",
        default="benchmark/auto-resolve/scripts",
        help="Directory containing oracle-*.py scripts",
    )
    ap.add_argument(
        "--output",
        help="Write to this path (default: stdout)",
    )
    ap.add_argument(
        "--generated-at",
        default=None,
        help="ISO8601 timestamp to embed (default: UTC now); pin to a fixed value for determinism testing",
    )
    ap.add_argument(
        "--repo-root",
        default=None,
        help="Repo root for resolving relative paths in output (default: cwd)",
    )
    args = ap.parse_args()

    install_path_trap()

    generated_at = (
        args.generated_at
        or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    scripts_dir = pathlib.Path(args.scripts_dir).resolve()
    repo_root = pathlib.Path(args.repo_root or os.getcwd()).resolve()

    registry = build_registry(args.fixture, scripts_dir, generated_at, repo_root)
    out_text = json.dumps(
        registry,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    ) + "\n"

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out_text)
    else:
        sys.stdout.write(out_text)


if __name__ == "__main__":
    main()
