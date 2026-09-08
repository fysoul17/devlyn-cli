#!/usr/bin/env bash
# Regression tests for seat-matrix.py.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MATRIX="$SCRIPT_DIR/seat-matrix.py"
TMP_DIR="$(mktemp -d /tmp/seat-matrix-test.XXXXXX)"
trap 'status=$?; if [ "$status" -eq 0 ]; then rm -rf "$TMP_DIR"; else echo "retained failure: $TMP_DIR" >&2; fi' EXIT
ROOT="$TMP_DIR/root"
mkdir -p "$ROOT/benchmark/probes/results" \
  "$ROOT/benchmark/probes/judge-quality/cases" \
  "$ROOT/benchmark/probes/judge-quality/results/sonnet" \
  "$ROOT/benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof/F1/codex" \
  "$ROOT/benchmark/auto-resolve/results/stub-frozen-verify/solo" \
  "$ROOT/benchmark/ceiling/results/synthetic-ceiling"

cat > "$ROOT/benchmark/probes/results/iter0058-base-matrix.json" <<'JSON'
{
  "matrix": {
    "sonnet": {
      "DB-silent-catch-root-cause": {
        "reps": 4,
        "violations": 1,
        "violation_reps": [2],
        "flip_band": 1
      }
    }
  },
  "models": ["sonnet"],
  "probes": ["DB-silent-catch-root-cause"],
  "run_prefix": "synthetic",
  "totals": {"sonnet": {"violations": 1, "reps": 4}}
}
JSON

mkdir -p "$ROOT/benchmark/probes/results/synthetic-codex-compliance/compliance/codex-small"
cat > "$ROOT/benchmark/probes/results/synthetic-codex-compliance/compliance/codex-small/compliance-check.json" <<'JSON'
{
  "cli": "codex",
  "assertions": {"state_found": {"pass": true}},
  "overall": "PASS",
  "failed_assertions": []
}
JSON

mkdir -p "$ROOT/benchmark/probes/results/other-codex-compliance/compliance/codex-small"
cat > "$ROOT/benchmark/probes/results/other-codex-compliance/compliance/codex-small/compliance-check.json" <<'JSON'
{
  "cli": "codex",
  "assertions": {"state_found": {"pass": true}},
  "overall": "PASS",
  "failed_assertions": []
}
JSON

mkdir -p "$ROOT/benchmark/probes/results/synthetic-violation-sonnet-r1/drift-bait/DB-one" \
  "$ROOT/benchmark/probes/results/synthetic-violation-sonnet-r1/drift-bait/DB-two"
cat > "$ROOT/benchmark/probes/results/synthetic-violation-sonnet-r1/drift-bait/DB-one/verdict.json" <<'JSON'
{"passed": true}
JSON
cat > "$ROOT/benchmark/probes/results/synthetic-violation-sonnet-r1/drift-bait/DB-two/verdict.json" <<'JSON'
{"passed": false}
JSON

cat > "$ROOT/benchmark/probes/judge-quality/cases/WD1.json" <<'JSON'
{
  "id": "WD1",
  "task": "Fix root cause.",
  "authorized_files": ["src/a.js"],
  "diff": "diff --git a/src/a.js b/src/a.js",
  "ground_truth": {"type": "defect", "class": "no_workaround", "file": "src/a.js"}
}
JSON
cat > "$ROOT/benchmark/probes/judge-quality/cases/WD1-CLEAN.json" <<'JSON'
{
  "id": "WD1-CLEAN",
  "task": "Fix root cause.",
  "authorized_files": ["src/a.js"],
  "diff": "diff --git a/src/a.js b/src/a.js",
  "ground_truth": {"type": "clean"}
}
JSON
cat > "$ROOT/benchmark/probes/judge-quality/results/sonnet/WD1-rep1.json" <<'JSON'
{"case": "WD1", "rep": 1, "error": null, "parsed": {"findings": []}, "hit": true, "false_positive": null}
JSON
cat > "$ROOT/benchmark/probes/judge-quality/results/sonnet/WD1-CLEAN-rep1.json" <<'JSON'
{"case": "WD1-CLEAN", "rep": 1, "error": null, "parsed": {"findings": []}, "hit": null, "false_positive": false}
JSON

cat > "$ROOT/benchmark/auto-resolve/results/swebench-lite-proof-gate-n11.json" <<'JSON'
{
  "engine_alias": "codex",
  "model_version": "codex-cli fake/gpt-fake",
  "rows": [
    {"pair_verdict_lift": false, "pair_internal_verdict_lift": true}
  ]
}
JSON
cat > "$ROOT/benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof/full-pipeline-pair-gate.json" <<'JSON'
{
  "engine_alias": "codex",
  "model_version": "codex-cli fake/gpt-fake",
  "fixtures_total": 1,
  "fixtures_passed": 1,
  "rows": [{"fixture": "F1", "status": "PASS"}]
}
JSON
cat > "$ROOT/benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof/F1/judge.json" <<'JSON'
{
  "scores_by_arm": {"codex": 88},
  "_judge_cli": "codex-cli fake",
  "_judge_model": "gpt-fake"
}
JSON
cat > "$ROOT/benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof/F1/codex/result.json" <<'JSON'
{"verify_score": 0.9}
JSON
: > "$ROOT/benchmark/auto-resolve/results/stub-frozen-verify/solo/setup.log"

cat > "$ROOT/benchmark/ceiling/results/synthetic-ceiling/ceiling-verdict.json" <<'JSON'
{
  "loss_conditions": {
    "LC1_stack_vs_bare": {
      "A_resolved": 1,
      "best_B_resolved": 0
    }
  },
  "selection": {
    "tasks": {
      "T1": {"row_status": "VALID"},
      "T2": {"row_status": "VALID"},
      "T3": {"row_status": "INVALID-infra"}
    }
  }
}
JSON

OUT1="$TMP_DIR/out-current"
python3 "$MATRIX" \
  --repo-root "$ROOT" \
  --out-dir "$OUT1" \
  --date 2026-07-07 \
  --engine-versions '{"codex":"codex-cli fake/gpt-fake","sonnet":"claude fake/sonnet"}' \
  --attest-run-prefix synthetic \
  > "$TMP_DIR/current.stdout"

python3 - "$OUT1/seat-matrix-2026-07-07.json" "$OUT1/seat-matrix-2026-07-07.md" <<'PY'
import json
import pathlib
import sys

data = json.loads(pathlib.Path(sys.argv[1]).read_text())
md = pathlib.Path(sys.argv[2]).read_text()
cells = data["cells"]
seats = {cell["seat"] for cell in cells}
required = {
    "orchestrator",
    "drift_resistance",
    "verify_primary_judge",
    "verify_pair_judge",
    "implement_executor",
    "plan_ideate_designer",
}
missing = required - seats
if missing:
    raise SystemExit(f"missing seats: {sorted(missing)}")
non_attested_alias_only = [
    cell for cell in cells
    if "other-codex-compliance" in str(cell["artifact"]) and cell["model_version"]["value"] is None
]
if not non_attested_alias_only or any(cell["status"] != "stale" for cell in non_attested_alias_only):
    raise SystemExit("non-attested alias-only cells must stay stale")
attested = [
    cell for cell in cells
    if "synthetic-codex-compliance" in str(cell["artifact"])
]
if not attested or any(
    cell["engine_alias"] != "codex"
    or cell["status"] != "current"
    or cell["model_version"]["source"] != "recert-attestation:synthetic"
    for cell in attested
):
    raise SystemExit(f"attested compliance cell did not become current: {attested}")
attested_drift = [
    cell for cell in cells
    if cell["seat"] == "drift_resistance" and "synthetic-violation-sonnet-r*" in str(cell["artifact"])
]
if not attested_drift or any(cell["status"] != "current" or cell["engine_alias"] != "sonnet" for cell in attested_drift):
    raise SystemExit(f"attested drift cell did not become current: {attested_drift}")
if data["recommendation"]["executor"] != "codex":
    raise SystemExit(data["recommendation"])
if data["recommendation"]["pair_judge_priority"] != ["codex"]:
    raise SystemExit(data["recommendation"])
if not any(cell["seat"] == "implement_executor" and cell["engine_alias"] == "codex" and cell["status"] == "current" for cell in cells):
    raise SystemExit("exact-version implement cell did not become current")
ceiling_impl = [
    cell for cell in cells
    if cell["seat"] == "implement_executor" and cell["metric"] == "ceiling_objective_resolved_under_harness"
]
if len(ceiling_impl) != 1 or ceiling_impl[0]["status"] != "stale" or ceiling_impl[0]["value"] != 0.5 or ceiling_impl[0]["n"] != 2:
    raise SystemExit(f"ceiling implement cell missing or wrong: {ceiling_impl}")
ceiling_plan = [
    cell for cell in cells
    if cell["seat"] == "plan_ideate_designer" and cell["metric"] == "ceiling_pilot_a_resolved"
]
if len(ceiling_plan) != 1 or ceiling_plan[0]["status"] != "stale" or ceiling_plan[0]["engine_alias"] != "sonnet+codex stack":
    raise SystemExit(f"ceiling plan cell missing or wrong: {ceiling_plan}")
if "stub-frozen-verify" in json.dumps(data):
    raise SystemExit("stub frozen-verify directory was incorrectly treated as evidence")
if "plan_ideate_designer" not in md or "ceiling_pilot_a_resolved" not in md:
    raise SystemExit("ceiling plan seat not rendered")
PY

OUT2="$TMP_DIR/out-stale"
python3 "$MATRIX" \
  --repo-root "$ROOT" \
  --out-dir "$OUT2" \
  --date 2026-07-08 \
  --engine-versions '{"codex":"different-codex","sonnet":"different-sonnet"}' \
  > "$TMP_DIR/stale.stdout"

python3 - "$OUT2/seat-matrix-2026-07-08.json" <<'PY'
import json
import pathlib
import sys

data = json.loads(pathlib.Path(sys.argv[1]).read_text())
rec = data["recommendation"]
if rec["executor"] != {"recommendation": "recert required", "seat": "implement_executor"}:
    raise SystemExit(rec)
if rec["pair_judge_priority"] != {"recommendation": "recert required", "seat": "verify_pair_judge"}:
    raise SystemExit(rec)
PY

python3 - "$MATRIX" "$ROOT" <<'PY'
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
from unittest import mock

matrix_path, root = map(Path, sys.argv[1:])
matrix = runpy.run_path(matrix_path)
runner = runpy.run_path(matrix_path.parents[1] / "probes/judge-quality/run_judge_quality.py")
directory = root / "benchmark/probes/judge-quality/results/codex"
directory.mkdir()
work = root / "owned-codex-work"; work.mkdir()
fake = root / "native.py"
fake.write_text('''import os, sys
a = sys.argv[1:]
assert a[0] == "exec" and a[a.index("-m") + 1] == "gpt-fake"
cwd = a[a.index("-C") + 1]
sys.stderr.write(f"OpenAI Codex vfake\\n--------\\nworkdir: {cwd}\\nmodel: gpt-fake\\nsandbox: read-only\\nreasoning effort: xhigh\\nsession id: fake-session\\n--------\\nuser\\n" + a[-1] + "\\n")
print(os.environ["FAKE_FINDINGS"])
''')
records = []
for case_id in ("WD1", "WD1-CLEAN"):
    case = json.loads((root / "benchmark/probes/judge-quality/cases" / (case_id + ".json")).read_text())
    findings = [] if case_id.endswith("CLEAN") else [{"id": "F1", "severity": "HIGH", "axis": "no_workaround", "file": "src/a.js", "line": 1, "summary": "fixture"}]
    stem = case_id + "-rep1"
    with mock.patch.dict(os.environ, {"FAKE_FINDINGS": json.dumps({"findings": findings})}):
        parsed, error, attempt = runner["call_codex"](runner["build_prompt"](case), work, [sys.executable, str(fake)], directory / (stem + "-attempt1.stdout.txt"), directory / (stem + "-attempt1.stderr.txt"), "gpt-fake")
    assert error is None, error
    record = {"case": case_id, "rep": 1, "error": error, "parsed": parsed,
              "attempts": [{"attempt": 1, "error": error, **attempt}], **runner["score_response"](case, parsed)}
    (directory / (stem + ".json")).write_text(json.dumps(record))
    records.append(record)
runner["write_identity"]("codex", directory, "synthetic", records=records, model_requested="gpt-fake")
baseline = {path.name: path.read_bytes() for path in directory.iterdir()}
sonnet = root / "benchmark/probes/judge-quality/results/sonnet"
legacy_bytes = {path.name: path.read_bytes() for path in sonnet.iterdir()}
versions = {"codex": "codex-cli fake/gpt-fake", "sonnet": "claude fake/sonnet"}

def check(label, valid, current=None):
    current = valid if current is None else current
    cells, certification = matrix["collect_judge_quality_cells"](root, "2026-09-08", versions, "judge")
    rows = [cell for cell in cells if cell["engine_alias"] == "codex"]
    assert rows and all((cell["status"] == "current") is current for cell in rows), (label, rows)
    assert certification["codex"]["certified"] is valid, (label, certification)
    assert certification["sonnet"]["certified"] is True
    assert legacy_bytes == {path.name: path.read_bytes() for path in sonnet.iterdir()}
    print("PASS Codex seat identity", label)
    return certification["codex"]

def restore():
    for path in directory.iterdir():
        if path.name not in baseline:
            path.unlink()
    for name, raw in baseline.items():
        (directory / name).write_bytes(raw)

def rebind_records():
    identity = json.loads((directory / "identity.json").read_text())
    identity["records"] = [runner["artifact"](directory / binding["path"]) for binding in identity["records"]]
    (directory / "identity.json").write_text(json.dumps(identity))

check("intact native bindings; version spelling matches recert", True)
for label, name, replacement in (
    ("missing identity", "identity.json", None),
    ("legacy identity plus attested prefix", "identity.json", b'{"cli_version":"codex-cli fake","model_id_or_alias":"gpt-fake"}'),
    ("missing record", "WD1-CLEAN-rep1.json", None),
    ("altered record", "WD1-CLEAN-rep1.json", b'{}'),
    ("altered stdout", "WD1-rep1-attempt1.stdout.txt", b'{"findings":[]}'),
    ("altered argv", "WD1-rep1-attempt1.argv.json", b'[]'),
    ("extra malformed record", "EXTRA-rep1.json", b'{'),
    ("orphan raw attempt", "EXTRA-rep1-attempt1.stdout.txt", b'PASS'),
):
    restore()
    path = directory / name
    if replacement is None: path.unlink()
    else: path.write_bytes(replacement)
    result = check(label, False)
    if label.startswith("legacy"):
        assert result["declared_identity"] == "codex-cli fake/gpt-fake"
        assert path.read_bytes() == replacement

# Internally consistent attempt bindings must still fail on cross-attempt drift.
restore()
record_path = directory / "WD1-CLEAN-rep1.json"
record = json.loads(record_path.read_text())
attempt = record["attempts"][0]
stderr = directory / attempt["stderr"]["path"]
stderr.write_bytes(stderr.read_bytes().replace(b"Codex vfake", b"Codex vother"))
attempt["stderr"] = runner["artifact"](stderr)
_, error, native, identity_error = runner["inspect_codex_attempt"](directory, attempt, "gpt-fake", "WD1-CLEAN-rep1-attempt1")
assert error is None and identity_error is None
attempt["native"] = native
record_path.write_text(json.dumps(record))
rebind_records()
check("mixed native versions despite rebound per-attempt artifacts", False)

# A failed clean execution must not certify from diagnostic recall=1, FP=0.
restore()
record = json.loads(record_path.read_text())
attempt = record["attempts"][0]
attempt["exit_code"] = 17
_, error, native, identity_error = runner["inspect_codex_attempt"](directory, attempt, "gpt-fake", "WD1-CLEAN-rep1-attempt1")
attempt.update(error=error, native=native, identity_error=identity_error)
record.update(error=error, parsed=None, parse_error=True)
record_path.write_text(json.dumps(record))
rebind_records()
result = check("failed clean run with perfect diagnostic rates", False)
assert result["recall_rate"] == 1 and result["false_positive_rate"] == 0

# Reproduce F2 with an actual fake-native miss, then rebind only the stored hit.
restore()
case = json.loads((root / "benchmark/probes/judge-quality/cases/WD1.json").read_text())
with mock.patch.dict(os.environ, {"FAKE_FINDINGS": '{"findings":[]}'}):
    parsed, error, attempt = runner["call_codex"](runner["build_prompt"](case), work, [sys.executable, str(fake)], directory / "WD1-rep1-attempt1.stdout.txt", directory / "WD1-rep1-attempt1.stderr.txt", "gpt-fake")
assert error is None
miss = {"case": "WD1", "rep": 1, "error": error, "parsed": parsed,
        "attempts": [{"attempt": 1, "error": error, **attempt}], **runner["score_response"](case, parsed)}
miss_path = directory / "WD1-rep1.json"
miss_path.write_text(json.dumps(miss)); rebind_records()
assert check("scorer-consistent native miss", False, current=True)["recall_rate"] == 0
raw_bindings = [runner["artifact"](directory / attempt[key]["path"]) for key in ("argv", "stdout", "stderr")]
miss["hit"] = True
miss_path.write_text(json.dumps(miss)); rebind_records()
assert check("rebound hit cannot certify unchanged native miss", False)["recall_rate"] == 1
assert raw_bindings == [runner["artifact"](directory / attempt[key]["path"]) for key in ("argv", "stdout", "stderr")]
assert json.loads(miss_path.read_text())["hit"] is True  # diagnostic record was not rewritten

for field, value in (("hit", 1), ("false_positive", False), ("false_positive", 0), ("parse_error", 0), ("parse_error", None), ("parse_error", True)):
    restore()
    path = record_path if field == "false_positive" and type(value) is int else miss_path
    record = json.loads(path.read_text())
    record[field] = value
    path.write_text(json.dumps(record)); rebind_records()
    check(f"rebound strict field {field}={value!r}", False)

# Two normal native exits with terminal parse failure preserve identity, not certification.
restore()
case = json.loads((root / "benchmark/probes/judge-quality/cases/WD1-CLEAN.json").read_text())
with mock.patch.dict(os.environ, {"FAKE_FINDINGS": "not JSON"}):
    parsed, error, attempts = runner["call_judge_with_retry"](
        "codex", runner["build_prompt"](case), work, codex_command=[sys.executable, str(fake)],
        judge_dir=directory, artifact_stem="WD1-CLEAN-rep1", model_requested="gpt-fake")
assert parsed is None and error.startswith("parse_error:") and len(attempts) == 2
assert all(a["exit_code"] == 0 and a["identity_error"] is None for a in attempts)
record = {"case": "WD1-CLEAN", "rep": 1, "error": error, "parsed": parsed,
          "attempts": attempts, "parse_error": True, **runner["score_response"](case, parsed)}
record_path.write_text(json.dumps(record)); rebind_records()
result = check("terminal parse failure retains native identity only", False, current=True)
assert result["recall_rate"] == 1 and result["false_positive_rate"] == 0 and result["parse_errors"] == 1
restore()
assert baseline == {path.name: path.read_bytes() for path in directory.iterdir()}

# The optional CLI input selects only that tree, including an absent/skipped tree.
legacy_results = directory.parent
legacy_all = {str(p.relative_to(legacy_results)): p.read_bytes() for p in legacy_results.rglob("*") if p.is_file()}
selected = root / "selected-judge-quality"
shutil.copytree(directory, selected / "codex")
for name, results_path in (("selected", selected), ("absent", root / "absent-judge-quality")):
    output = root / (name + "-report")
    result = subprocess.run([sys.executable, str(matrix_path), "--repo-root", str(root), "--out-dir", str(output),
        "--date", "2026-09-08", "--engine-versions", json.dumps(versions), "--judge-quality-results", str(results_path)],
        capture_output=True, text=True)
    (root / (name + ".stdout")).write_text(result.stdout)
    (root / (name + ".stderr")).write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    report = json.loads((output / "seat-matrix-2026-09-08.json").read_text())
    if name == "selected":
        assert set(report["judge_certification"]) == {"codex"}
        assert report["judge_certification"]["codex"]["certified"] is True
    else:
        assert report["judge_certification"] == {}
        assert all(c["status"] == "unmeasured" for c in report["cells"] if c["seat"] == "verify_primary_judge")
    print("PASS explicit judge-quality CLI input", name)

# Run the real wrapper in this owned repo; only suite/version executables are fake.
wrapper = root / "benchmark/seats/recert-seats.sh"
wrapper.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(matrix_path.with_name("recert-seats.sh"), wrapper)
fakebin = root / "recert-fakebin"; fakebin.mkdir()
python = fakebin / "python3"
python.write_text(f"#!{sys.executable}\n" + '''import json, os, pathlib, sys
args = sys.argv[1:]
name = pathlib.Path(args[0]).name
if name in ("run_judge_quality.py", "seat-matrix.py"):
    with open(os.environ["RECERT_CALLS"], "a") as out:
        out.write(json.dumps(args) + "\\n")
    if name == "run_judge_quality.py":
        directory = pathlib.Path(args[args.index("--results-dir") + 1])
        directory.mkdir(parents=True)
        (directory / "fake-suite-marker").write_text("mocked suite only\\n")
else:
    os.execv(sys.executable, [sys.executable, *args])
''')
python.chmod(0o700)
for cli in ("claude", "codex"):
    path = fakebin / cli
    path.write_text('#!/bin/sh\n[ "$#" -eq 1 ] && [ "$1" = "--version" ] || exit 97\nprintf "%s\\n" "' + cli + '-cli fake"\n')
    path.chmod(0o700)
for prefix, skip in (("mock-bound", "violation,compliance"), ("mock-skipped", "violation,compliance,judge_quality")):
    calls_path = root / (prefix + ".calls.jsonl")
    env = dict(os.environ, PATH=str(fakebin) + os.pathsep + os.environ["PATH"], RECERT_CALLS=str(calls_path))
    result = subprocess.run(["bash", str(wrapper), "--engines", "codex", "--run-prefix", prefix, "--skip", skip],
        env=env, capture_output=True, text=True)
    (root / (prefix + ".stdout")).write_text(result.stdout)
    (root / (prefix + ".stderr")).write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    calls = [json.loads(line) for line in calls_path.read_text().splitlines()]
    expected = str(wrapper.parent / "results" / prefix / "judge-quality")
    assert Path(calls[-1][0]).name == "seat-matrix.py"
    assert calls[-1][calls[-1].index("--judge-quality-results") + 1] == expected
    if prefix == "mock-bound":
        assert len(calls) == 2 and Path(calls[0][0]).name == "run_judge_quality.py"
        assert calls[0][calls[0].index("--results-dir") + 1] == expected
        assert (Path(expected) / "fake-suite-marker").is_file()
    else:
        assert len(calls) == 1 and not Path(expected).exists()
    print("PASS actual recert producer/consumer results path", prefix)
assert legacy_all == {str(p.relative_to(legacy_results)): p.read_bytes() for p in legacy_results.rglob("*") if p.is_file()}
PY

echo "PASS test-seat-matrix"
