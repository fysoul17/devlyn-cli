#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

checks=0
pass() {
  checks=$((checks + 1))
}
fail() {
  echo "noncoding self-test: FAIL: $*" >&2
  exit 1
}

python3 "$SCRIPT_DIR/conformance-gate.py" --self-test
pass

if python3 "$SCRIPT_DIR/run-packet-attempt.py" >/dev/null 2>&1; then
  fail "runner accepted missing required arguments"
fi
pass

read -r first_fixture first_packet < <(
  python3 - "$ROOT/manifest.json" <<'PY'
import json, sys
from pathlib import Path
manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
fixture = sorted(manifest["fixtures"])[0]
print(fixture, manifest["fixtures"][fixture]["packets"]["good_a"])
PY
)
if python3 "$SCRIPT_DIR/run-packet-attempt.py" \
  --fixture "$first_fixture" --packet "$first_packet" --seat sol \
  --attempt 1 --run-id selftest --validate-only >/dev/null 2>&1; then
  fail "runner accepted the forbidden sol seat"
fi
pass

python3 - "$ROOT" <<'PY'
from __future__ import annotations

import ast
import hashlib
import json
import math
import os
import re
import runpy
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from statistics import NormalDist

root = Path(sys.argv[1]).resolve()
scripts = root / "scripts"
manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
schema = runpy.run_path(str(scripts / "packet-schema.py"))
gate = runpy.run_path(str(scripts / "conformance-gate.py"))
runner = runpy.run_path(str(scripts / "run-packet-attempt.py"))

assert manifest["namespace"] == "calibration"
assert manifest["fixtures"], "manifest has no fixtures"
assert Path(manifest["no_op_packet"]).as_posix().startswith("packets/")
no_op_path = root / manifest["no_op_packet"]
no_op = schema["load_packet"](no_op_path)
assert no_op["tasks"] == [] and no_op["project_acceptance"] == []

host_home = Path("/Users/aipalm")
external_root = host_home / ".local/share/nx02"
workspace = external_root / "r1/t1/p1/s1/a1/w"
scan = runner["scan_contamination"]
scan_args = {
    "fixture_id": "opaque-fixture",
    "run_id": "opaque-run",
    "packet_name": "opaque-packet.json",
    "workspace": workspace,
    "external_root": external_root,
    "host_home": host_home,
}
assert scan(f"cwd={workspace}\nfile={workspace}/src/app.py\nroot={external_root}\n", **scan_args) == []
assert scan(f"cwd={workspace}\n/Users/aipalm/Documents/private.txt\n", **scan_args) == ["host-context"]
for skills_path in (
    f"{workspace}/.agents/skills/private/SKILL.md",
    f"{external_root}/.codex/skills/private/SKILL.md",
    "~/.claude/CLAUDE.md",
):
    assert scan(skills_path, **scan_args) == ["host-context"], skills_path

def tree_hash(seed: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in seed.rglob("*") if item.is_file()):
        relative = path.relative_to(seed).as_posix()
        digest.update(relative.encode() + b"\0")
        digest.update(format(path.stat().st_mode & 0o777, "04o").encode() + b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()

for fixture_id, record in sorted(manifest["fixtures"].items()):
    fixture = (root / record["path"]).resolve()
    assert fixture.parent == (root / "calibration").resolve()
    task = (fixture / "task.txt").read_bytes()
    assert hashlib.sha256(task).hexdigest() == record["task_sha256"]
    seed = fixture / "seed"
    observed_tree = tree_hash(seed)
    assert observed_tree == record["seed_tree_sha256"]
    base = json.loads((fixture / "base.json").read_text(encoding="utf-8"))
    assert base == {"repo": "./seed", "tree_sha256": observed_tree}
    gate["validate_fixture"](fixture)

    for path in sorted(item for item in seed.rglob("*") if item.is_file()):
        text = path.read_text(encoding="utf-8", errors="replace")
        assert re.search(r"devlyn|benchmark|fixture", text, re.IGNORECASE) is None, path

    oracle = fixture / "hidden/oracle.sh"
    assert oracle.is_file() and os.access(oracle, os.X_OK)
    syntax = subprocess.run(["bash", "-n", str(oracle)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert syntax.returncode == 0, syntax.stderr.decode(errors="replace")

    roles = record["packets"]
    assert set(roles) == {"good_a", "good_b", "bad_dependency", "bad_constraint"}
    for role, relative in roles.items():
        packet = schema["load_packet"](root / relative)
        assert packet["schema_version"] == "pud-1"
        if role in {"good_a", "good_b"}:
            completed_tasks = set()
            for task_entry in packet["tasks"]:
                assert set(task_entry["depends_on"]) <= completed_tasks, (role, task_entry["id"])
                completed_tasks.add(task_entry["id"])
        preview = subprocess.run(
            [
                sys.executable,
                str(scripts / "run-packet-attempt.py"),
                "--fixture",
                fixture_id,
                "--packet",
                relative,
                "--seat",
                "terra",
                "--attempt",
                "1",
                "--run-id",
                "selftest",
                "--preview-prompt",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert preview.returncode == 0, preview.stderr
        visible = preview.stdout.casefold()
        assert (fixture / "task.txt").read_text(encoding="utf-8").rstrip() in preview.stdout
        assert "`depends_on` defines the legal execution order; array position is not a schedule." in preview.stdout
        forbidden = [
            "devlyn-cli",
            "benchmark/noncoding",
            fixture_id.casefold(),
            Path(relative).name.casefold(),
            role.casefold(),
            "selftest",
        ]
        assert not [value for value in forbidden if value in visible], (role, forbidden, visible)

    with tempfile.TemporaryDirectory(prefix="nch-") as temporary:
        work = Path(temporary) / "repo"
        shutil.copytree(seed, work)
        environment = {
            "PATH": "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
            "HOME": temporary,
            "LANG": "C",
            "LC_ALL": "C",
            "TZ": "UTC",
            "FIXTURE_HIDDEN_DIR": str(fixture / "hidden"),
        }
        base_run = subprocess.run([str(oracle)], cwd=work, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert base_run.returncode != 0, f"{fixture_id} no-op/base unexpectedly resolves"
        applied = subprocess.run(
            ["git", "apply", str(fixture / "hidden/reference.patch")],
            cwd=work,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert applied.returncode == 0, applied.stderr.decode(errors="replace")
        gold_run = subprocess.run([str(oracle)], cwd=work, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert gold_run.returncode == 0, gold_run.stderr.decode(errors="replace")
        for test_path in (work / "tests").glob("test*.py"):
            test_path.unlink()
        zero_test_run = subprocess.run(
            [str(oracle)], cwd=work, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        assert zero_test_run.returncode != 0, f"{fixture_id} oracle accepted zero discovered tests"

power = json.loads((root / "calibration/power.json").read_text(encoding="utf-8"))
p_good = power["declared_good_probability"]
p_bad = power["declared_bad_probability"]
n = power["repeats_per_packet"]
z = NormalDist().inv_cdf(1 - power["alpha"] / 2)
p_bar = (p_good + p_bad) / 2
mean = math.sqrt(n) * (p_good - p_bad)
critical = z * math.sqrt(2 * p_bar * (1 - p_bar))
sd = math.sqrt(p_good * (1 - p_good) + p_bad * (1 - p_bad))
observed_power = NormalDist().cdf((mean - critical) / sd) + NormalDist().cdf((-mean - critical) / sd)
assert abs(observed_power - power["power"]) < 1e-12
assert observed_power >= power["minimum_required_power"] >= 0.8

for script in sorted(scripts.glob("*.py")):
    ast.parse(script.read_text(encoding="utf-8"), filename=str(script))

print(f"manifest harness checks: PASS ({len(manifest['fixtures'])} fixtures, pud-1, blinding, oracle smoke, power)")
PY
pass

bash -n "$SCRIPT_DIR/run-calibration.sh" "$SCRIPT_DIR/test-noncoding-harness.sh"
pass

bash "$ROOT/cells/intent/test-intent-cell.sh"
pass

echo "noncoding self-test: PASS ($checks groups)"
