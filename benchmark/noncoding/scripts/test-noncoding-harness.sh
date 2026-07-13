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

python3 "$SCRIPT_DIR/classify-defect-family.py" --self-test
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
driver = runpy.run_path(str(scripts / "calibration-driver.py"))
classifier = runpy.run_path(str(scripts / "classify-defect-family.py"))

assert manifest["namespace"] == "calibration"
assert manifest["fixtures"], "manifest has no fixtures"
assert manifest["routing"] == {
    "ORDERING_MUTATION": "sonnet",
    "CONTENT_CONSTRAINT_MUTATION": "gpt-5.6-terra",
    "INELIGIBLE": None,
}
assert manifest["routing_export_policy"] == "This routing artifact is never included in author exports."
assert set(manifest["validation"]) == {
    "cartwheel-rate-card",
    "fernwell-station-report",
    "ledgerloom-proration",
    "tilebridge-notes-migration",
}
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

expected_families = {
    "cartwheel-rate-card": "ORDERING_MUTATION",
    "fernwell-station-report": "CONTENT_CONSTRAINT_MUTATION",
    "ledgerloom-proration": "CONTENT_CONSTRAINT_MUTATION",
    "tilebridge-notes-migration": "ORDERING_MUTATION",
}
for fixture_id, record in sorted(manifest["validation"].items()):
    fixture = (root / record["path"]).resolve()
    assert fixture.parent == (root / "validation").resolve()
    assert runner["fixture_record"](fixture_id) == (record, fixture)
    task = (fixture / "task.txt").read_bytes()
    assert hashlib.sha256(task).hexdigest() == record["task_sha256"]
    seed = fixture / "seed"
    observed_tree = tree_hash(seed)
    assert observed_tree == record["seed_tree_sha256"]
    base = json.loads((fixture / "base.json").read_text(encoding="utf-8"))
    assert base == {"repo": "./seed", "tree_sha256": observed_tree}
    gate["validate_fixture"](fixture)

    assert record["canonical_good"] == "good_a"
    assert record["family"] == expected_families[fixture_id]
    assert set(record["packets"]) == {"good_a", "good_b", "bad_1", "bad_2"}
    for bad_role in ("bad_1", "bad_2"):
        bad_name = Path(record["packets"][bad_role]).stem
        observed = classifier["classify_paths"](fixture, "good-a", bad_name)["family"]
        assert observed == record["family"], (fixture_id, bad_role, observed)
        assert classifier["classify_paths"](fixture, "good-b", bad_name)["family"] == "INELIGIBLE"

    packet_paths = {**record["packets"], "no_op": manifest["no_op_packet"]}
    for role, relative in packet_paths.items():
        completed = subprocess.run(
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
                "--validate-only",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert completed.returncode == 0, (fixture_id, role, completed.stderr)

routed_attempts = 0
canary_attempts = 0
for seat in ("terra", "sonnet"):
    schedule, fixture_cohorts = driver["validation_schedule_for"](manifest, seat)
    assert len(schedule) == 190
    for fixture_id, config in fixture_cohorts.items():
        fixture_attempts = [item for item in schedule if item["fixture"] == fixture_id]
        expected = 80 if config["mode"] == "routed" else 15
        assert len(fixture_attempts) == expected, (seat, fixture_id, len(fixture_attempts))
        assert {item["role"] for item in fixture_attempts} == set(driver["VALIDATION_ROLES"])
        if config["mode"] == "routed":
            routed_attempts += len(fixture_attempts)
        else:
            canary_attempts += len(fixture_attempts)
assert (routed_attempts, canary_attempts) == (320, 60)

for fixture_id, family in expected_families.items():
    expected_seat = "sonnet" if family == "ORDERING_MUTATION" else "terra"
    assert driver["routed_seat"](manifest, manifest["validation"][fixture_id]) == expected_seat
try:
    driver["routed_seat"](manifest, {"family": "INELIGIBLE"})
except driver["CalibrationError"]:
    pass
else:
    raise AssertionError("INELIGIBLE family did not fail closed")
driver["validate_seats"]("validation", ["terra", "sonnet"])
for invalid_seats in (["terra"], ["sonnet"]):
    try:
        driver["validate_seats"]("validation", invalid_seats)
    except driver["CalibrationError"]:
        pass
    else:
        raise AssertionError(f"validation accepted routing override: {invalid_seats}")

t1_pass_counts = {
    "synthetic": {"good_a": 16, "good_b": 15, "bad_1": 0, "bad_2": 1, "no_op": 0}
}
assert driver["evaluate_t1"](t1_pass_counts, 16, ("bad_1", "bad_2"))["status"] == "ADMIT"
t1_fail_counts = {
    "synthetic": {"good_a": 16, "good_b": 15, "bad_1": 5, "bad_2": 1, "no_op": 0}
}
assert driver["evaluate_t1"](t1_fail_counts, 16, ("bad_1", "bad_2"))["status"] == "DEAD"
t1_no_op_counts = {
    "synthetic": {"good_a": 16, "good_b": 15, "bad_1": 0, "bad_2": 1, "no_op": 1}
}
assert driver["evaluate_t1"](t1_no_op_counts, 16, ("bad_1", "bad_2"))["status"] == "DEAD"
canary_pass_counts = {
    "synthetic": {"good_a": 2, "good_b": 2, "bad_1": 1, "bad_2": 1, "no_op": 0}
}
assert driver["evaluate_canary"](canary_pass_counts, 3)["status"] == "CANARY_PASS"
canary_fail_counts = {
    "synthetic": {"good_a": 1, "good_b": 1, "bad_1": 1, "bad_2": 1, "no_op": 0}
}
assert driver["evaluate_canary"](canary_fail_counts, 3)["status"] == "CANARY_FAIL"
canary_no_op_counts = {
    "synthetic": {"good_a": 2, "good_b": 2, "bad_1": 1, "bad_2": 1, "no_op": 1}
}
assert driver["evaluate_canary"](canary_no_op_counts, 3)["status"] == "CANARY_FAIL"

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

print(
    "manifest harness checks: PASS "
    f"({len(manifest['fixtures'])} calibration + {len(manifest['validation'])} validation fixtures, "
    "pud-1, namespaces, routing, 320+60 schedule, admission, blinding, oracle smoke, power)"
)
PY
pass

bash -n "$SCRIPT_DIR/run-calibration.sh" "$SCRIPT_DIR/test-noncoding-harness.sh"
pass

bash "$ROOT/cells/intent/test-intent-cell.sh"
pass

echo "noncoding self-test: PASS ($checks groups)"
