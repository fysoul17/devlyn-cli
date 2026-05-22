#!/usr/bin/env python3
"""
Lane B arm capturer (Day-3 driver, §C/§F of RUNBOOK.md).

Everything that must happen AFTER a measurement subagent finishes one
fixture-arm and BEFORE the judge runs. Replaces the capture half of the retired
`run-fixture.sh` — the model-execution half is now an Agent (subagent) call the
orchestrator makes directly.

Given the run's manifest (workspace + scaffold_sha) and the subagent's verbatim
final message, it writes the four-file arm-dir contract the unchanged judge
pipeline keys off, then runs the two mechanical passes:
  arms/<arm>/<fixture>/diff.patch            git diff workspace vs scaffold
  arms/<arm>/<fixture>/transcript.txt        subagent final message, verbatim
  arms/<arm>/<fixture>/transcript.meta.json  size / truncation diagnostics
  arms/<arm>/<fixture>/meta.json             run-level diagnostics
  <run-dir>/detector-findings.jsonl          appended (detect-mechanical.py)
  <run-dir>/hidden-verify.jsonl              appended (fixture hidden/verify.sh)

Usage:
  capture-arm.py --run-dir <runs/<run-id>> --fixture <id> --arm <solo_old|solo_new> \
                 --subagent-msg <file>
"""
from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path
from typing import Callable

# Judge input caps the transcript at this size (build-judge-input.py). Recorded
# in transcript.meta.json so an over-long subagent report is a visible flag.
JUDGE_TRANSCRIPT_CAP = 4096


def git(workspace: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(workspace), *args],
                          capture_output=True, text=True)


def capture_diff(workspace: Path, scaffold_sha: str, out: Path) -> dict:
    """`git add -A && git diff <scaffold_sha>` — captures tracked edits, new
    files, and deletions as one unified diff. Returns a status dict."""
    if not (workspace / ".git").is_dir():
        out.write_text("", encoding="utf-8")
        return {"diff_capture_ok": False, "diff_error": "workspace .git missing",
                "diff_bytes": 0, "diff_files": 0}
    add = git(workspace, "add", "-A")
    if add.returncode != 0:
        out.write_text("", encoding="utf-8")
        return {"diff_capture_ok": False, "diff_error": f"git add failed: {add.stderr.strip()}",
                "diff_bytes": 0, "diff_files": 0}
    diff = git(workspace, "diff", scaffold_sha)
    if diff.returncode != 0:
        out.write_text("", encoding="utf-8")
        return {"diff_capture_ok": False, "diff_error": f"git diff failed: {diff.stderr.strip()}",
                "diff_bytes": 0, "diff_files": 0}
    out.write_text(diff.stdout, encoding="utf-8")
    n_files = sum(1 for ln in diff.stdout.splitlines() if ln.startswith("diff --git "))
    return {"diff_capture_ok": True, "diff_error": None,
            "diff_bytes": len(diff.stdout.encode("utf-8")), "diff_files": n_files}


def purge_rows(jsonl: Path, match: Callable[[dict], bool]) -> None:
    """Drop rows matching `match` so a re-run of one arm replaces, not
    duplicates, its detector / hidden-verify rows (RUNBOOK §D re-run path)."""
    if not jsonl.is_file():
        return
    kept = []
    for line in jsonl.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            kept.append(line)
            continue
        if not match(row):
            kept.append(line)
    jsonl.write_text("".join(l + "\n" for l in kept), encoding="utf-8")


def run_detector(lane_root: Path, fixture_dir: Path, arm_dir: Path,
                  out_jsonl: Path) -> bool:
    detector = lane_root / "scripts" / "detect-mechanical.py"
    proc = subprocess.run(
        ["python3", str(detector), "--fixture-dir", str(fixture_dir),
         "--arm-dir", str(arm_dir), "--out", str(out_jsonl)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        print(f"capture-arm: detector failed: {proc.stderr.strip()}", file=sys.stderr)
    return proc.returncode == 0


def run_hidden_verify(fixture_dir: Path, fixture: str, arm: str, arm_dir: Path,
                      out_jsonl: Path) -> None:
    verify_sh = fixture_dir / "hidden" / "verify.sh"
    if not verify_sh.is_file():
        return
    res = subprocess.run(["bash", str(verify_sh), str(arm_dir)],
                         capture_output=True, text=True)
    try:
        parsed = json.loads(res.stdout)
    except json.JSONDecodeError:
        parsed = {"raw_stdout": res.stdout, "stderr": res.stderr, "parse_error": True}
    parsed["arm"] = arm
    parsed["fixture_id"] = fixture
    with out_jsonl.open("a", encoding="utf-8") as f:
        f.write(json.dumps(parsed, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--arm", required=True, choices=["solo_old", "solo_new"])
    parser.add_argument("--subagent-msg", required=True, type=Path,
                        help="file holding the subagent's verbatim final message")
    args = parser.parse_args()

    lane_root = Path(__file__).resolve().parents[1]
    fixture_dir = lane_root / "fixtures" / args.fixture
    run_dir = args.run_dir.resolve()

    manifest_path = run_dir / "manifest.json"
    if not manifest_path.is_file():
        sys.exit(f"capture-arm: error: manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    try:
        ws_info = manifest["workspaces"][args.fixture][args.arm]
    except KeyError:
        sys.exit(f"capture-arm: error: no workspace for {args.fixture}/{args.arm} "
                 f"in manifest — was prepare-run.py run for this fixture?")
    arm_info = manifest["arms"][args.arm]
    workspace = Path(ws_info["workspace"])
    scaffold_sha = ws_info["scaffold_sha"]
    arm_dir = run_dir / "arms" / args.arm / args.fixture
    arm_dir.mkdir(parents=True, exist_ok=True)

    diff_status = capture_diff(workspace, scaffold_sha, arm_dir / "diff.patch")

    msg = (args.subagent_msg.read_text(encoding="utf-8", errors="replace")
           if args.subagent_msg.is_file() else "")
    (arm_dir / "transcript.txt").write_text(msg, encoding="utf-8")
    (arm_dir / "transcript.meta.json").write_text(
        json.dumps({
            "chars": len(msg),
            "lines": msg.count("\n") + 1 if msg else 0,
            "empty": not msg.strip(),
            "judge_truncates": len(msg) > JUDGE_TRANSCRIPT_CAP,
        }, indent=2) + "\n", encoding="utf-8")

    meta = {
        "fixture": args.fixture,
        "arm": args.arm,
        "ref": arm_info["ref"],
        "resolved_ref": arm_info["resolved_ref"],
        "bundle_sha": arm_info["bundle_sha"],
        "model_pin": manifest["model_pin"],
        "model_pin_method": manifest.get("model_pin_method", "parent_session_inherit"),
        "execution_mode": manifest["execution_mode"],
        "workspace": str(workspace),
        "scaffold_sha": scaffold_sha,
        "subagent_msg_chars": len(msg),
        "captured_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        **diff_status,
    }
    (arm_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n",
                                       encoding="utf-8")

    # Idempotent capture — drop any prior rows for this arm before re-appending.
    detector_jsonl = run_dir / "detector-findings.jsonl"
    verify_jsonl = run_dir / "hidden-verify.jsonl"
    purge_rows(detector_jsonl, lambda r: r.get("arm_dir") == str(arm_dir))
    purge_rows(verify_jsonl,
               lambda r: r.get("fixture_id") == args.fixture and r.get("arm") == args.arm)
    run_detector(lane_root, fixture_dir, arm_dir, detector_jsonl)
    run_hidden_verify(fixture_dir, args.fixture, args.arm, arm_dir, verify_jsonl)

    flag = "" if diff_status["diff_capture_ok"] else f"  DIFF-ERROR: {diff_status['diff_error']}"
    print(f"capture-arm: {args.fixture}/{args.arm} -> "
          f"diff={diff_status['diff_files']}file/{diff_status['diff_bytes']}B "
          f"transcript={len(msg)}ch{flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
