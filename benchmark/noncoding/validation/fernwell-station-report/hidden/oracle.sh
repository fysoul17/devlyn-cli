#!/usr/bin/env bash
# Mechanical pass/fail check for the Fernwell task.
# Usage: oracle.sh [repo_root]   (defaults to $PWD)
set -u

ROOT="${1:-$PWD}"
cd "$ROOT" || { echo "FAIL: cannot enter repo root: $ROOT" >&2; exit 1; }

fail() { echo "FAIL: $*" >&2; exit 1; }

# ---------------------------------------------------------------- leg 1: suite
python3 - <<'PY' || fail "test discovery collected no tests"
import sys, unittest
suite = unittest.defaultTestLoader.discover("tests")
count = suite.countTestCases()
print("discovered %d test(s)" % count)
sys.exit(0 if count >= 1 else 1)
PY

python3 -m unittest discover -s tests >/dev/null 2>&1 || fail "the test suite does not pass"

# ------------------------------- leg 2: frozen text renderer, exact CSV and text
python3 - <<'PY' || fail "task outcomes not satisfied (see messages above)"
import hashlib
import pathlib
import subprocess
import sys

errors = []

# The task freezes report/renderer_text.py: other teams import it and diff its output.
RENDERER_TEXT_SHA = "ec9f63d0754b689c2eec0d64b51e69dba13c7de8daef8a8d2174e8e0199c7416"
actual_sha = hashlib.sha256(pathlib.Path("report/renderer_text.py").read_bytes()).hexdigest()
if actual_sha != RENDERER_TEXT_SHA:
    errors.append(
        "report/renderer_text.py was modified (sha256 %s, expected %s) — the task "
        "requires it to stay byte-for-byte unchanged" % (actual_sha, RENDERER_TEXT_SHA)
    )

EXPECTED_CSV = (
    "station,trips,avg_minutes\n"
    "Birch Gate,5,9.2\n"
    "Alder Quay,3,13.0\n"
    "Cedar Row,3,21.0\n"
    "Dunes Landing,1,30.0\n"
)

EXPECTED_TEXT = (
    "STATION          TRIPS  AVG MINUTES\n"
    "Alder Quay           3         13.0\n"
    "Birch Gate           5          9.2\n"
    "Cedar Row            3         21.0\n"
    "Dunes Landing        1         30.0\n"
    "ALL STATIONS        12         14.8\n"
)


def run(args):
    return subprocess.run(
        [sys.executable, "-m", "report.cli"] + args,
        capture_output=True,
        text=True,
    )


csv_run = run(["--format", "csv"])
if csv_run.returncode != 0:
    errors.append(
        "`python3 -m report.cli --format csv` exited %d: %s"
        % (csv_run.returncode, csv_run.stderr.strip().splitlines()[-1:] or [""])
    )
elif csv_run.stdout != EXPECTED_CSV:
    errors.append(
        "`--format csv` output does not match the required CSV.\n      got:      %r\n"
        "      expected: %r" % (csv_run.stdout, EXPECTED_CSV)
    )

text_run = run(["--format", "text"])
if text_run.returncode != 0:
    errors.append("`python3 -m report.cli --format text` exited %d" % (text_run.returncode,))
elif text_run.stdout != EXPECTED_TEXT:
    errors.append(
        "`--format text` output changed.\n      got:      %r\n      expected: %r"
        % (text_run.stdout, EXPECTED_TEXT)
    )

default_run = run([])
if default_run.returncode != 0 or default_run.stdout != EXPECTED_TEXT:
    errors.append("`python3 -m report.cli` with no --format no longer prints the text report")

# render_csv must live in its own module and render the same bytes.
try:
    from report.loader import load_summaries
    from report.renderer_csv import render_csv
except Exception as exc:  # noqa: BLE001
    errors.append("report.renderer_csv.render_csv is not importable: %r" % (exc,))
else:
    rendered = render_csv(load_summaries())
    if rendered != EXPECTED_CSV:
        errors.append(
            "render_csv(load_summaries()) does not match the required CSV.\n"
            "      got:      %r\n      expected: %r" % (rendered, EXPECTED_CSV)
        )

for message in errors:
    print("  - " + message, file=sys.stderr)
sys.exit(1 if errors else 0)
PY

echo "PASS"
