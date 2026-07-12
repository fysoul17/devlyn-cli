#!/usr/bin/env bash
set -euo pipefail

CELL_ROOT="$(cd "$(dirname "$0")" && pwd)"
NONCODING_ROOT="$(cd "$CELL_ROOT/../.." && pwd)"
REPO_ROOT="$(cd "$NONCODING_ROOT/../.." && pwd)"
RUNNER="$CELL_ROOT/run-intent-attempt.py"
MANIFEST="$NONCODING_ROOT/manifest.json"

python3 - "$REPO_ROOT" "$NONCODING_ROOT" "$CELL_ROOT" "$RUNNER" "$MANIFEST" <<'PY'
from __future__ import annotations

import hashlib
import json
import os
import re
import runpy
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


repo_root, noncoding_root, cell_root, runner_path, manifest_path = map(Path, sys.argv[1:])
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
cell = manifest["cells"]["intent"]
fixtures = cell["fixtures"]
gate = runpy.run_path(str(noncoding_root / "scripts/conformance-gate.py"))
packet_runner = runpy.run_path(str(noncoding_root / "scripts/run-packet-attempt.py"))
runner = runpy.run_path(str(runner_path))

assert set(fixtures) == {"ledger-time-r", "ledger-time-q", "reset-flow-r", "reset-flow-q"}
method = (noncoding_root / cell["method_card"]["path"]).resolve()
assert hashlib.sha256(method.read_bytes()).hexdigest() == cell["method_card"]["sha256"]

for fixture_id, record in sorted(fixtures.items()):
    fixture = noncoding_root / record["path"]
    assert hashlib.sha256((fixture / "task.txt").read_bytes()).hexdigest() == record["task_sha256"]
    assert packet_runner["tree_sha256"](fixture / "seed") == record["seed_tree_sha256"]
    frozen = gate["validate_fixture"](fixture)
    assert frozen["schema_version"] == "hidden-conformance-2"
    oracle = fixture / "hidden/oracle.sh"
    assert oracle.is_file() and os.access(oracle, os.X_OK)
    assert subprocess.run(["bash", "-n", str(oracle)], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0
    for path in sorted(item for item in (fixture / "seed").rglob("*") if item.is_file()):
        text = path.read_text(encoding="utf-8", errors="replace")
        assert re.search(r"devlyn|benchmark|fixture|intent", text, re.IGNORECASE) is None, path

    if record["variant"] == "R":
        expected_roles = {"gold", "unnecessary-halt", "wrong-implementation", "no-op"}
    else:
        expected_roles = {"gold", "silent-guess", "generic-question", "assumption-disclosure", "no-op"}
        if fixture_id == "ledger-time-q":
            expected_roles |= {"gold-question-preservation", "gold-question-ending-z"}
    assert set(record["replays"]) == expected_roles
    for role, asset in record["replays"].items():
        replay = noncoding_root / asset["path"]
        assert hashlib.sha256((replay / "patch.diff").read_bytes()).hexdigest() == asset["patch_sha256"]
        assert hashlib.sha256((replay / "message.txt").read_bytes()).hexdigest() == asset["message_sha256"]

for pair_id, pair in sorted(cell["pairs"].items()):
    r_record = fixtures[pair["R"]]
    q_record = fixtures[pair["Q"]]
    r_root = noncoding_root / r_record["path"]
    q_root = noncoding_root / q_record["path"]
    assert (r_root / "task.txt").read_bytes() == (q_root / "task.txt").read_bytes(), pair_id
    evidence = Path(pair["evidence_path"])
    r_files = {path.relative_to(r_root / "seed") for path in (r_root / "seed").rglob("*") if path.is_file()}
    q_files = {path.relative_to(q_root / "seed") for path in (q_root / "seed").rglob("*") if path.is_file()}
    assert r_files == q_files
    changed = [path for path in sorted(r_files) if (r_root / "seed" / path).read_bytes() != (q_root / "seed" / path).read_bytes()]
    assert changed == [evidence], (pair_id, changed)

for fixture_id in sorted(fixtures):
    task = (noncoding_root / fixtures[fixture_id]["path"] / "task.txt").read_text(encoding="utf-8").rstrip()
    for arm in "ABC":
        completed = subprocess.run(
            [
                sys.executable, str(runner_path), "--fixture", fixture_id, "--arm", arm,
                "--attempt", "1", "--run-id", "opaque-preview", "--preview-prompt",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert completed.returncode == 0, completed.stderr
        assert task in completed.stdout
        lowered = completed.stdout.casefold()
        assert fixture_id.casefold() not in lowered
        assert "counterfactual intent holdout" not in lowered
        assert "benchmark/noncoding/cells/intent" not in lowered

with tempfile.TemporaryDirectory(prefix="nc-cell-") as temporary:
    temp = Path(temporary)
    opaque_workspace = temp / runner["opaque_id"]("r", "run") / runner["opaque_id"]("f", "fixture") / "r1/a1/w"
    baseline = packet_runner["initialize_workspace"](
        noncoding_root / fixtures["ledger-time-r"]["path"] / "seed", opaque_workspace
    )
    staged = runner["stage_harness"](opaque_workspace)
    assert staged != baseline
    assert re.search(r"intent|holdout|devlyn|bench|fixture", opaque_workspace.as_posix(), re.IGNORECASE) is None
    for path in (item for item in opaque_workspace.rglob("*") if item.is_file() and ".git" not in item.parts):
        lowered = path.read_text(encoding="utf-8", errors="replace").casefold()
        assert "counterfactual intent holdout" not in lowered, path
        assert "benchmark/noncoding/cells/intent" not in lowered, path
        assert "holdout" not in lowered, path

    changed_references = {
        "ledger-time-r": "2030-01-01T00:00:00Z",
        "reset-flow-r": "reset->confirmation_required",
    }
    for fixture_id, changed_reference in changed_references.items():
        fixture = noncoding_root / fixtures[fixture_id]["path"]
        workspace = temp / "behavior" / runner["opaque_id"]("f", fixture_id) / "w"
        packet_runner["initialize_workspace"](fixture / "seed", workspace)
        applied = subprocess.run(
            ["git", "apply", str(fixture / "replays/gold/patch.diff")],
            cwd=workspace,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert applied.returncode == 0, (fixture_id, applied.stderr)
        behavior_check = fixture / "hidden/behavior-check.py"
        conformance = fixture / "hidden/conformance.json"
        live = subprocess.run(
            [sys.executable, str(behavior_check), str(workspace), str(conformance)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert live.returncode == 0, (fixture_id, live.stderr)
        changed = json.loads(conformance.read_text(encoding="utf-8"))
        reference = next(channel for channel in changed["channels"] if channel["id"] == "reference-behavior")
        reference["values"][0] = changed_reference
        changed_conformance = workspace.parent / "changed-conformance.json"
        changed_conformance.write_text(json.dumps(changed), encoding="utf-8")
        rejected = subprocess.run(
            [sys.executable, str(behavior_check), str(workspace), str(changed_conformance)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert rejected.returncode != 0, fixture_id

    replay_checks = 0
    for fixture_id, record in sorted(fixtures.items()):
        for role, asset in sorted(record["replays"].items()):
            result_dir = temp / "results" / runner["opaque_id"]("f", fixture_id) / runner["opaque_id"]("p", role)
            environment = os.environ.copy()
            environment["NONCODING_EXTERNAL_ROOT"] = str(temp / "external")
            completed = subprocess.run(
                [
                    sys.executable, str(runner_path), "--fixture", fixture_id,
                    "--replay", str(noncoding_root / asset["path"]),
                    "--attempt", "1", "--run-id", "replay-selftest", "--result-dir", str(result_dir),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=environment,
            )
            assert completed.returncode == 0, (fixture_id, role, completed.stderr)
            result = json.loads((result_dir / "result.json").read_text(encoding="utf-8"))
            assert result["outcome"] == asset["expected"], (fixture_id, role, result)
            assert result["provenance"]["invalid_reasons"] == []
            assert json.loads((result_dir / "isolation.json").read_text())["opaque_paths"] is True
            assert json.loads((result_dir / "contamination.json").read_text())["passed"] is True
            replay_checks += 1

print(f"intent cell self-test: PASS ({len(fixtures)} fixtures, {len(cell['pairs'])} pairs, {replay_checks} replays)")
PY
