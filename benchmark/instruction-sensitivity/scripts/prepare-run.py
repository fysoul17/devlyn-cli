#!/usr/bin/env python3
"""
Lane B run preparer (Day-3 driver, §B/§C/§F of RUNBOOK.md).

Everything that can be done BEFORE any measurement subagent runs:
  1. validate the two pre-built instruction bundles (built by build-bundle.py)
  2. run the scriptable half of the §C contamination gate — FAIL-CLOSED
  3. compute the per-fixture A/B judge slot map + the arm execution order
  4. scaffold one isolated git workspace per fixture-arm
  5. write the v2 manifest the loop + judge + score pipeline all key off

Run by the clean `claude --bare` session — it touches only the harness tree and
the OS temp dir, never the devlyn repo (the bundles already captured the devlyn
instruction text during USER setup). Layout is convention-based off this
script's location:
  <lane-root>/bundles/<ref>/bundle.md   pre-built bundles
  <lane-root>/fixtures/<fixture>/        fixture pack
  <lane-root>/runs/<run-id>/             this run's capture + judge output

Workspace isolation (Codex review, finding 1+2): each fixture-arm workspace is
an opaque OS-temp directory — NOT under runs/<run-id>/ and NOT under the
harness. So the workspace path carries no arm identity (it cannot leak
solo_old/solo_new into the subagent prompt or transcript), and walking up from
a workspace never reaches the manifest or the other arm's bundle. This closes
accidental cross-arm discovery. Adversarial filesystem-wide search is out of
the §G threat model — that would need an OS sandbox and is deferred.

Usage:
  prepare-run.py --run-id <id> --baseline-ref <ref> --candidate-ref <ref> \
                 --fixtures B1-... B2-... [...]
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_MODEL_PIN = "claude-sonnet-4-6"
SCAFFOLD_MSG = "__lane_b_scaffold__"


def die(msg: str) -> None:
    sys.exit(f"prepare-run: error: {msg}")


def load_bundle(bundles_root: Path, ref: str) -> dict:
    bundle_dir = bundles_root / ref
    if not (bundle_dir / "bundle.md").is_file() or \
       not (bundle_dir / "bundle.manifest.json").is_file():
        die(f"bundle for ref '{ref}' missing at {bundle_dir} — "
            f"run build-bundle.py for this ref first (RUNBOOK §A)")
    manifest = json.loads((bundle_dir / "bundle.manifest.json").read_text(encoding="utf-8"))
    return {
        "ref": ref,
        "resolved_ref": manifest.get("resolved_ref", ""),
        "bundle_path": str((bundle_dir / "bundle.md").resolve()),
        "bundle_sha": manifest.get("sha256", ""),
    }


def hash_fixture_pack(fixtures_root: Path, fixtures: list[str]) -> str:
    """Stable hash over every file in the selected fixture dirs."""
    h = hashlib.sha256()
    for fixture in sorted(fixtures):
        for path in sorted(p for p in (fixtures_root / fixture).rglob("*") if p.is_file()):
            h.update(path.relative_to(fixtures_root).as_posix().encode("utf-8"))
            h.update(b"\0")
            h.update(path.read_bytes())
            h.update(b"\0")
    return h.hexdigest()


def slot_for(run_id: str, fixture: str) -> dict:
    """A/B judge slot + arm execution order, each from an independent seed so
    the judge-slot assignment cannot be inferred from run order."""
    ab_even = int(hashlib.sha256(f"{run_id}:{fixture}".encode()).hexdigest(), 16) % 2 == 0
    exec_even = int(hashlib.sha256(f"{run_id}:{fixture}:exec".encode()).hexdigest(), 16) % 2 == 0
    a, b = ("solo_old", "solo_new") if ab_even else ("solo_new", "solo_old")
    exec_order = ["solo_old", "solo_new"] if exec_even else ["solo_new", "solo_old"]
    return {"A": a, "B": b, "seed": f"{run_id}:{fixture}", "exec_order": exec_order}


def scaffold_workspace(fixture_dir: Path, run_id: str) -> tuple[str, str]:
    """Copy the fixture starter into a fresh git repo in an opaque OS-temp dir.
    Returns (workspace_path, scaffold_sha)."""
    starter = fixture_dir / "starter"
    if not starter.is_dir():
        die(f"fixture starter missing: {starter}")
    workspace = Path(tempfile.mkdtemp(prefix=f"laneb-{run_id}-"))
    shutil.copytree(starter, workspace, dirs_exist_ok=True)
    git = ["git", "-C", str(workspace)]
    ident = ["-c", "user.name=lane-b", "-c", "user.email=lane-b@local"]
    subprocess.run([*git, "init", "-q"], check=True)
    subprocess.run([*git, *ident, "add", "-A"], check=True)
    subprocess.run([*git, *ident, "commit", "-q", "--allow-empty", "-m", SCAFFOLD_MSG],
                   check=True)
    sha = subprocess.run([*git, "rev-parse", "HEAD"], capture_output=True, text=True,
                         check=True).stdout.strip()
    return str(workspace), sha


def canary_gate(scan_dirs: list[Path]) -> dict:
    """Scriptable half of the §C contamination gate. The `/memory` check is the
    orchestrator's job (it needs the live session) — recorded as deferred."""
    env_unset = "CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD" not in os.environ
    scan: dict[str, bool] = {}
    for d in scan_dirs:
        hits = [p.name for p in d.iterdir()
                if p.is_file() and p.name.lower() in ("claude.md", "agents.md")] \
            if d.is_dir() else []
        scan[str(d)] = not hits
    clear = env_unset and all(scan.values())
    return {
        "additional_dirs_env_unset": env_unset,
        "instruction_file_absent": scan,
        "memory_preflight": "deferred-to-orchestrator",
        "scriptable_checks_clear": clear,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--baseline-ref", required=True)
    parser.add_argument("--candidate-ref", required=True)
    parser.add_argument("--fixtures", required=True, nargs="+")
    parser.add_argument("--model-pin", default=DEFAULT_MODEL_PIN)
    args = parser.parse_args()

    lane_root = Path(__file__).resolve().parents[1]
    harness_root = Path(__file__).resolve().parents[3]
    bundles_root = lane_root / "bundles"
    fixtures_root = lane_root / "fixtures"
    run_dir = lane_root / "runs" / args.run_id

    for fixture in args.fixtures:
        if not (fixtures_root / fixture).is_dir():
            die(f"fixture not found: {fixtures_root / fixture}")
    if run_dir.exists():
        die(f"run dir already exists: {run_dir} — pick a fresh --run-id")

    baseline = load_bundle(bundles_root, args.baseline_ref)
    candidate = load_bundle(bundles_root, args.candidate_ref)

    # §C contamination gate — FAIL-CLOSED. A failed gate aborts before any
    # workspace is scaffolded; the run dir holds only the failure record.
    gate = canary_gate([harness_root, lane_root])
    (run_dir / "logs").mkdir(parents=True)
    if not gate["scriptable_checks_clear"]:
        (run_dir / "gate-fail.json").write_text(
            json.dumps({"run_id": args.run_id, "phase": "prepare-run",
                        "canary_gate": gate}, indent=2) + "\n", encoding="utf-8")
        (run_dir / "manifest.json").write_text(
            json.dumps({"run_id": args.run_id, "schema_version": "v2",
                        "status": "gate-failed", "canary_gate": gate}, indent=2) + "\n",
            encoding="utf-8")
        print(f"prepare-run: CONTAMINATION GATE FAILED — see {run_dir}/gate-fail.json",
              file=sys.stderr)
        return 1

    slot_map: dict[str, dict] = {}
    workspaces: dict[str, dict] = {}
    for fixture in args.fixtures:
        slot_map[fixture] = slot_for(args.run_id, fixture)
        workspaces[fixture] = {}
        for arm in ("solo_old", "solo_new"):
            ws_path, sha = scaffold_workspace(fixtures_root / fixture, args.run_id)
            workspaces[fixture][arm] = {"workspace": ws_path, "scaffold_sha": sha}

    manifest = {
        "schema_version": "v2",
        "run_id": args.run_id,
        "execution_mode": "clean_harness_subagent",
        "model_pin": args.model_pin,
        "model_pin_method": "parent_session_inherit",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "baseline_ref": args.baseline_ref,
        "candidate_ref": args.candidate_ref,
        "bundle_sha_old": baseline["bundle_sha"],
        "bundle_sha_new": candidate["bundle_sha"],
        "fixture_pack_sha": hash_fixture_pack(fixtures_root, args.fixtures),
        "fixtures": list(args.fixtures),
        "arms": {
            "solo_old": {"ref": baseline["ref"], "resolved_ref": baseline["resolved_ref"],
                         "bundle_path": baseline["bundle_path"],
                         "bundle_sha": baseline["bundle_sha"]},
            "solo_new": {"ref": candidate["ref"], "resolved_ref": candidate["resolved_ref"],
                         "bundle_path": candidate["bundle_path"],
                         "bundle_sha": candidate["bundle_sha"]},
        },
        "slot_map": slot_map,
        "workspaces": workspaces,
        "canary_gate": gate,
        "memory_log_paths": [str((run_dir / "logs" / "memory-preflight.txt").resolve())],
        "status": "prepared",
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"prepare-run: {args.run_id} -> {run_dir}")
    print(f"  fixtures={len(args.fixtures)}  workspaces={len(args.fixtures) * 2} "
          f"(opaque OS-temp dirs)")
    print(f"  bundle_old={baseline['bundle_sha'][:12]}  "
          f"bundle_new={candidate['bundle_sha'][:12]}")
    print("  §C scriptable gate: PASS  (orchestrator must still run the /memory check)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
