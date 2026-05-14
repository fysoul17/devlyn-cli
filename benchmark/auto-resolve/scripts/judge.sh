#!/usr/bin/env bash
# judge.sh — Codex (CLI's current flagship, inherited) blind judge for ONE fixture.
#
# Usage:
#   judge.sh --fixture <FID> --run-id <ID>
#
# Reads:
#   results/<run-id>/<fixture>/variant/diff.patch + verify.json
#   results/<run-id>/<fixture>/bare/diff.patch + verify.json
#   fixtures/<fixture>/spec.md + expected.json, or shadow-fixtures/<fixture>/...
#   RUBRIC.md (stable rubric)
#
# Writes:
#   results/<run-id>/<fixture>/judge.json
#
# Blind: arm-to-slot assignment randomized per fixture, seed stored in judge.json.

set -euo pipefail

usage() { echo "usage: $0 --fixture <FID> --run-id <ID>"; exit 1; }
require_value() {
  local flag="$1"
  local value="${2:-}"
  if [ -z "$value" ] || [[ "$value" == --* ]]; then
    echo "$flag requires a value" >&2
    exit 1
  fi
}

FIXTURE=""; RUN_ID=""
while [ $# -gt 0 ]; do
  case "$1" in
    --fixture) require_value "$1" "${2:-}"; FIXTURE="$2"; shift 2;;
    --run-id)  require_value "$1" "${2:-}"; RUN_ID="$2";  shift 2;;
    *) usage;;
  esac
done
[ -n "$FIXTURE" ] && [ -n "$RUN_ID" ] || usage

BENCH_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RES_DIR="$BENCH_ROOT/results/$RUN_ID/$FIXTURE"
FIX_DIR=""
for candidate in "$BENCH_ROOT/fixtures/$FIXTURE" "$BENCH_ROOT/shadow-fixtures/$FIXTURE"; do
  if [ -d "$candidate" ]; then
    FIX_DIR="$candidate"
    break
  fi
done
[ -n "$FIX_DIR" ] || { echo "fixture not found in fixtures/ or shadow-fixtures/: $FIXTURE"; exit 1; }

# iter-0019: 3 arms — variant (L2), solo_claude (L1), bare (L0). The judge
# scores all three in a single pass with the same prompt + same model so
# margin derivations (L2-vs-L0, L1-vs-L0, L2-vs-L1) are calibrated against
# each other and not against separate judge calls. ARMS_PRESENT enumerates
# whichever subset actually has artifacts (so a missing arm doesn't abort
# the whole judge step). Two-arm judge mode is preserved for runs that pre-
# date iter-0019.
ARMS_PRESENT=()
# iter-0033c: l2_gated/l2_forced added for NEW L2 vs NEW L1 measurement.
# iter-0037: l2_risk_probes adds bounded visible-verification probes before
# IMPLEMENT; judge treats it as another blind arm when artifacts exist.
# Slot count is still A/B/C max 3. Current pair-candidate proof runs supply
# {bare, solo_claude, selected pair arm} where the selected pair arm is usually
# l2_risk_probes; older diagnostic runs may instead supply l2_gated/l2_forced.
# The blind-shuffle slot mapping below already tolerates arbitrary
# ARMS_PRESENT counts >=2.
for arm in variant solo_claude bare l2_gated l2_risk_probes l2_forced; do
  if [ -f "$RES_DIR/$arm/diff.patch" ] && [ -f "$RES_DIR/$arm/verify.json" ]; then
    ARMS_PRESENT+=("$arm")
  fi
done
if [ ${#ARMS_PRESENT[@]} -lt 2 ]; then
  echo "judge needs at least 2 arms with diff.patch + verify.json; have: ${ARMS_PRESENT[*]:-(none)}"
  exit 1
fi
for f in "$FIX_DIR/spec.md" "$FIX_DIR/expected.json" "$BENCH_ROOT/RUBRIC.md"; do
  [ -f "$f" ] || { echo "missing required input: $f"; exit 1; }
done

# Blind randomization: shuffle ARMS_PRESENT into ABC order. Seed recorded
# in judge.json so runs are reproducible if rejudged.
SEED=$RANDOM
# iter-0019.4: Bash 3.2 compatible (macOS /bin/bash). `mapfile` is Bash 4+
# only; replaced with while-read loop. The `|| [ -n "$line" ]` guard
# preserves exact `mapfile -t` behavior on a final unterminated line (Python
# print() emits trailing \n so this guard is belt-and-suspenders here, but
# matches mapfile semantics for future producers).
SLOTS=()
while IFS= read -r line || [ -n "$line" ]; do
  SLOTS+=("$line")
done < <(python3 - "$SEED" "${ARMS_PRESENT[@]}" <<'PY'
import sys, random
seed = int(sys.argv[1]); arms = sys.argv[2:]
random.seed(seed)
random.shuffle(arms)
print("\n".join(arms))
PY
)
A_ARM="${SLOTS[0]:-}"
B_ARM="${SLOTS[1]:-}"
C_ARM="${SLOTS[2]:-}"

PROMPT_FILE="$RES_DIR/judge-prompt.txt"
A_DIFF="$RES_DIR/$A_ARM/diff.patch"
A_VERIFY="$RES_DIR/$A_ARM/verify.json"
B_DIFF="$RES_DIR/$B_ARM/diff.patch"
B_VERIFY="$RES_DIR/$B_ARM/verify.json"
if [ -n "$C_ARM" ]; then
  C_DIFF="$RES_DIR/$C_ARM/diff.patch"
  C_VERIFY="$RES_DIR/$C_ARM/verify.json"
else
  C_DIFF=""
  C_VERIFY=""
fi

# Sanitize diffs so stylistic tells that correlate with variant (e.g.
# pipeline-commit markers, .devlyn/ archive lines) don't leak to the judge.
# Judge sees only file-content changes; the transcript, arm label, NOTES.md,
# and all process artifacts stay out of the prompt.
python3 - "$PROMPT_FILE" "$FIX_DIR/spec.md" "$FIX_DIR/expected.json" "$BENCH_ROOT/RUBRIC.md" "$A_DIFF" "$B_DIFF" "$A_VERIFY" "$B_VERIFY" "$C_DIFF" "$C_VERIFY" "$BENCH_ROOT/scripts" <<'PY'
import sys, pathlib, re, json
args = sys.argv[1:]
out_p, spec_p, exp_p, rubric_p = map(pathlib.Path, args[:4])
a_diff, b_diff, a_ver, b_ver = map(pathlib.Path, args[4:8])
c_diff_arg, c_ver_arg = args[8], args[9]
sys.path.insert(0, args[10])
from pair_evidence_contract import loads_strict_json_object

c_diff = pathlib.Path(c_diff_arg) if c_diff_arg else None
c_ver = pathlib.Path(c_ver_arg) if c_ver_arg else None
out = out_p
spec = spec_p.read_text()
expected = exp_p.read_text()
rubric = rubric_p.read_text()

# Strip pipeline-origin tells from the diff before the judge sees it.
TELLS = [
    re.compile(r"^diff --git.*\.devlyn/.*$", re.M),
    re.compile(r"^chore\(pipeline\):.*$", re.M),
    re.compile(r"^\.devlyn/.*$", re.M),
    re.compile(r"^Co-Authored-By:.*$", re.M),
]
def sanitize(diff: str) -> str:
    # Drop whole-file hunks under .devlyn/
    out_lines, skip = [], False
    for line in diff.splitlines(keepends=True):
        if line.startswith("diff --git ") and ".devlyn/" in line:
            skip = True
            continue
        if line.startswith("diff --git "):
            skip = False
        if skip:
            continue
        out_lines.append(line)
    text = "".join(out_lines)
    for pat in TELLS:
        text = pat.sub("", text)
    return text

# Also strip arm-identifying fields from verify.json before passing to judge.
def sanitize_verify(path: pathlib.Path) -> str:
    data = loads_strict_json_object(path.read_text())
    # Remove anything that could name the arm
    data.pop("arm", None)
    return json.dumps(data, indent=2)

a_diff_text = sanitize(a_diff.read_text())
b_diff_text = sanitize(b_diff.read_text())
a_ver_text = sanitize_verify(a_ver)
b_ver_text = sanitize_verify(b_ver)
have_c = c_diff is not None
if have_c:
    c_diff_text = sanitize(c_diff.read_text())
    c_ver_text = sanitize_verify(c_ver)

n_arms = 3 if have_c else 2
arms_phrase = "Three engineers" if have_c else "Two engineers"
slot_keys = ["a_score", "b_score", "c_score"][:n_arms]
slot_breakdowns = ["a_breakdown", "b_breakdown", "c_breakdown"][:n_arms]
slot_letters = ["A", "B", "C"][:n_arms]

# Build the JSON-format hint dynamically so the judge sees the right shape
# for either 2 or 3 arms. Same scoring rules; same rubric.
score_lines = ",\n  ".join(f'"{k}": <int 0-100>' for k in slot_keys)
breakdown_lines = ",\n  ".join(
    f'"{b}": {{"spec": 0-25, "constraint": 0-25, "scope": 0-25, "quality": 0-25, "notes": "<3-5 bullets>"}}'
    for b in slot_breakdowns
)
findings_keys = ", ".join(f'"{l}": ["..."]' for l in slot_letters)
dq_keys = ", ".join(f'"{l}": bool' for l in slot_letters)
dq_reasons = ", ".join(f'"{l}_reason": "..."' for l in slot_letters)
winner_choices = " | ".join(f'"{l}"' for l in slot_letters) + ' | "tie"'

# Per-arm sections of the prompt
def section(label: str, diff_text: str, verify_text: str) -> str:
    return (
        f"=== IMPLEMENTATION {label} ===\nDiff:\n"
        f"```diff\n{diff_text}\n```\n"
        f"Verification results:\n```json\n{verify_text}\n```\n"
    )

impl_sections = section("A", a_diff_text, a_ver_text) + "\n" + section("B", b_diff_text, b_ver_text)
if have_c:
    impl_sections += "\n" + section("C", c_diff_text, c_ver_text)

prompt = f"""You are a blind code-review judge. {arms_phrase} implemented the same spec. You do NOT know which implementation came from which process — grade them only on the merits of the code and its behavior.

Apply the 4-axis rubric from RUBRIC.md below. Each axis is 0-25, total 100. Score every implementation independently — do not let one arm's score anchor another's. The judge's job is to apply the rubric absolutely; relative ordering falls out from the absolute scores.

Return STRICT JSON only — no prose outside the JSON. Format:

{{
  {score_lines},
  "winner": {winner_choices},
  {breakdown_lines},
  "critical_findings": {{{findings_keys}}},
  "disqualifiers": {{{dq_keys}, {dq_reasons}}},
  "overall_reasoning": "<5-8 sentences>"
}}

=== RUBRIC ===
{rubric}

=== SPEC ===
{spec}

=== EXPECTED (machine-readable acceptance) ===
{expected}

{impl_sections}
Return the JSON and nothing else.
"""
out.write_text(prompt)
PY

# Invoke Codex — no -m so CLI flagship is inherited. Model identity is
# recorded from the codex config.toml so rejudging with a newer flagship is
# traceable. Run from a clean temp CWD so the judge can't peek at project
# files that would leak arm identity.
command -v codex >/dev/null 2>&1 || { echo "codex CLI not on PATH; cannot judge"; exit 1; }
CODEX_CLI_VER=$(python3 - <<'PY'
import subprocess

try:
    proc = subprocess.run(
        ["codex", "--version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=5,
    )
    out = (proc.stdout or proc.stderr).strip()
    if proc.returncode == 0 and out:
        print(out)
    else:
        print(f"codex-cli unknown (version-exit-{proc.returncode})")
except subprocess.TimeoutExpired:
    print("codex-cli unknown (version-timeout)")
except FileNotFoundError:
    print("codex-cli missing")
except Exception as exc:
    print(f"codex-cli unknown ({type(exc).__name__})")
PY
)
JUDGE_MODEL=$({ grep -E '^model[[:space:]]*=' "${HOME}/.codex/config.toml" 2>/dev/null || true; } \
  | head -1 \
  | sed -E 's/.*=[[:space:]]*"?([^"]*)"?[[:space:]]*$/\1/' \
  | xargs)
[ -z "$JUDGE_MODEL" ] && JUDGE_MODEL="(unknown — codex config.toml not readable)"

JUDGE_CWD="/tmp/judge-$RUN_ID-$FIXTURE"
rm -rf "$JUDGE_CWD"
mkdir -p "$JUDGE_CWD"

JUDGE_OUT="$RES_DIR/judge-output.txt"
JUDGE_LAST="$RES_DIR/judge-last-message.txt"
JUDGE_SCHEMA="$RES_DIR/judge-output.schema.json"
python3 - "$JUDGE_SCHEMA" "$C_ARM" <<'PY'
import json
import pathlib
import sys

out = pathlib.Path(sys.argv[1])
have_c = bool(sys.argv[2])
letters = ["A", "B"] + (["C"] if have_c else [])

breakdown = {
    "type": "object",
    "required": ["spec", "constraint", "scope", "quality", "notes"],
    "properties": {
        "spec": {"type": "integer", "minimum": 0, "maximum": 25},
        "constraint": {"type": "integer", "minimum": 0, "maximum": 25},
        "scope": {"type": "integer", "minimum": 0, "maximum": 25},
        "quality": {"type": "integer", "minimum": 0, "maximum": 25},
        "notes": {"type": "string"},
    },
    "additionalProperties": False,
}
findings = {
    "type": "object",
    "required": letters,
    "properties": {letter: {"type": "array", "items": {"type": "string"}} for letter in letters},
    "additionalProperties": False,
}
disqualifier_props = {}
for letter in letters:
    disqualifier_props[letter] = {"type": "boolean"}
    disqualifier_props[f"{letter}_reason"] = {"type": "string"}
schema = {
    "type": "object",
    "required": [
        "a_score",
        "b_score",
        "winner",
        "a_breakdown",
        "b_breakdown",
        "critical_findings",
        "disqualifiers",
        "overall_reasoning",
    ] + (["c_score", "c_breakdown"] if have_c else []),
    "properties": {
        "a_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "b_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "winner": {"type": "string", "enum": letters + ["tie"]},
        "a_breakdown": breakdown,
        "b_breakdown": breakdown,
        "critical_findings": findings,
        "disqualifiers": {
            "type": "object",
            "required": list(disqualifier_props),
            "properties": disqualifier_props,
            "additionalProperties": False,
        },
        "overall_reasoning": {"type": "string"},
    },
    "additionalProperties": False,
}
if have_c:
    schema["properties"]["c_score"] = {"type": "integer", "minimum": 0, "maximum": 100}
    schema["properties"]["c_breakdown"] = breakdown
out.write_text(json.dumps(schema, indent=2))
PY
set +e
cat "$PROMPT_FILE" | (
  cd "$JUDGE_CWD" && codex exec \
    --ignore-user-config \
    --ignore-rules \
    --ephemeral \
    --disable codex_hooks \
    --disable hooks \
    -s read-only \
    --skip-git-repo-check \
    -c model_reasoning_effort=xhigh \
    --output-schema "$JUDGE_SCHEMA" \
    --output-last-message "$JUDGE_LAST" \
    -
) > "$JUDGE_OUT" 2>&1
JUDGE_EXIT=$?
set -e
rm -rf "$JUDGE_CWD"
if [ $JUDGE_EXIT -ne 0 ]; then
  echo "codex exec failed (exit $JUDGE_EXIT); see $JUDGE_OUT"
  exit 1
fi

# Extract JSON (codex wraps with banners; pick the last {...} block)
python3 - "$JUDGE_OUT" "$JUDGE_LAST" "$RES_DIR/judge.json" "$A_ARM" "$B_ARM" "$C_ARM" "$SEED" "$CODEX_CLI_VER" "$JUDGE_MODEL" "$BENCH_ROOT/scripts" <<'PY'
import math
import sys, re, json, pathlib
out_path = pathlib.Path(sys.argv[1])
last_path = pathlib.Path(sys.argv[2])
target = pathlib.Path(sys.argv[3])
a_arm, b_arm, c_arm, seed, codex_ver, judge_model = sys.argv[4:10]
sys.path.insert(0, sys.argv[10])
from pair_evidence_contract import loads_strict_json_object, reject_json_constant

out = last_path.read_text() if last_path.is_file() and last_path.stat().st_size else out_path.read_text()

# Extract the last valid judgment JSON. A naive brace-counter breaks on
# `{`/`}` that appear inside strings (e.g. JS source embedded in the arms'
# diffs), so use json.JSONDecoder.raw_decode starting at each `{` position
# and keep the last successful parse with the required keys.
decoder = json.JSONDecoder(parse_constant=reject_json_constant)
brace_positions = [i for i, c in enumerate(out) if c == '{']
chosen = None
for pos in reversed(brace_positions):
    try:
        obj, _ = decoder.raw_decode(out[pos:])
    except json.JSONDecodeError:
        continue
    if isinstance(obj, dict) and "a_score" in obj and "b_score" in obj:
        chosen = obj
        break
if chosen is None:
    raise SystemExit(f"no valid JSON in judge output; see {out_path}")

def is_score(value):
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 100

def is_bool(value):
    return isinstance(value, bool)

def is_axis_score(value):
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 25

required_score_keys = ["a_score", "b_score"] + (["c_score"] if c_arm else [])
invalid_scores = [key for key in required_score_keys if not is_score(chosen.get(key))]
if invalid_scores:
    raise SystemExit(f"invalid judge score value(s): {', '.join(invalid_scores)}")

# Decode blind labels — record full mapping so summary code can iterate
mapping = {"A": a_arm, "B": b_arm}
if c_arm:
    mapping["C"] = c_arm
chosen["_blind_mapping"] = {**mapping, "seed": int(seed)}
chosen["_judge_cli"] = codex_ver.strip()
chosen["_judge_model"] = judge_model.strip()

# iter-0023 — axis breakdown validation. Rubric axes are 0-25 (RUBRIC.md
# "Scoring — 4 axes, 25 points each"). Past runs (iter-0020 F9) recorded
# `quality: -1` because judge LLM occasionally emits sentinel/negative
# values; ship-gate then averaged invalid cells. Detect, clamp to [0, 25],
# and record the invalid cells under `_axis_validation` so downstream
# consumers can refuse to trust that fixture's margin.
AXIS_KEYS = ("spec", "constraint", "scope", "quality")
BREAKDOWN_KEYS = ("a_breakdown", "b_breakdown", "c_breakdown")
axis_invalid_cells = []
for bk in BREAKDOWN_KEYS:
    if bk not in chosen or not isinstance(chosen[bk], dict):
        continue
    for axis in AXIS_KEYS:
        if axis not in chosen[bk]:
            continue
        v = chosen[bk][axis]
        if not is_axis_score(v):
            axis_invalid_cells.append({"breakdown": bk, "axis": axis, "value": v})
            chosen[bk][axis] = max(0, min(25, int(v) if not isinstance(v, bool) and isinstance(v, (int, float)) else 0))
chosen["_axis_validation"] = {
    "out_of_range_count": len(axis_invalid_cells),
    "out_of_range_cells": axis_invalid_cells,
    "axis_range": [0, 25],
}
if axis_invalid_cells:
    sys.stderr.write(
        f"[judge.sh] WARNING: {len(axis_invalid_cells)} axis cell(s) out of [0,25] "
        f"clamped: {axis_invalid_cells}\n"
    )

# Verification is the machine-readable acceptance contract. RUBRIC.md puts
# verification behavior under Spec Compliance, but LLM judges can still grade
# generous prose around failed commands. Cap score mechanically so an arm that
# fails required verification cannot receive a ceiling score.
def arm_verify_score(arm: str):
    path = target.parent / arm / "verify.json"
    if not path.is_file():
        return None
    data = loads_strict_json_object(path.read_text())
    value = data.get("verify_score")
    return float(value) if isinstance(value, (int, float)) else None

verify_caps = []
for letter, score_key, breakdown_key in (
    ("A", "a_score", "a_breakdown"),
    ("B", "b_score", "b_breakdown"),
    ("C", "c_score", "c_breakdown"),
):
    arm = mapping.get(letter)
    if not arm:
        continue
    verify_score = arm_verify_score(arm)
    if verify_score is None:
        continue
    verify_score = max(0.0, min(1.0, verify_score))
    score_cap = math.floor(100 * verify_score)
    spec_cap = math.floor(25 * verify_score)
    raw_score = chosen.get(score_key)
    raw_spec = (chosen.get(breakdown_key) or {}).get("spec")
    row = {
        "letter": letter,
        "arm": arm,
        "verify_score": verify_score,
        "score_cap": score_cap,
        "spec_cap": spec_cap,
        "raw_score": raw_score,
        "raw_spec": raw_spec,
        "score_capped": False,
        "spec_capped": False,
    }
    if is_score(raw_score) and raw_score > score_cap:
        chosen[score_key] = score_cap
        row["score_capped"] = True
    breakdown = chosen.get(breakdown_key)
    if isinstance(breakdown, dict) and isinstance(raw_spec, (int, float)) and raw_spec > spec_cap:
        breakdown["spec"] = spec_cap
        row["spec_capped"] = True
    verify_caps.append(row)
chosen["_verify_score_caps"] = verify_caps

# scores_by_arm: arm-name → score, computed from the blind A/B/C scores.
# This is the canonical 3-arm-aware shape the report consumer reads. The
# legacy variant_score / bare_score / margin fields below are derived from
# scores_by_arm for backward compatibility with pre-iter-0019 callers.
scores_by_arm = {}
slot_keys = ["a_score", "b_score", "c_score"]
slot_letters = ["A", "B", "C"]
for letter, key in zip(slot_letters, slot_keys):
    arm = mapping.get(letter)
    if arm is not None and key in chosen and is_score(chosen[key]):
        scores_by_arm[arm] = chosen[key]
chosen["scores_by_arm"] = scores_by_arm

# Per-letter critical_findings / disqualifiers also rotated to per-arm.
raw_findings_letters = chosen.get("critical_findings")
findings_letters = raw_findings_letters if isinstance(raw_findings_letters, dict) else {}
findings_by_arm = {mapping[l]: findings_letters.get(l, []) for l in slot_letters if l in mapping}
chosen["findings_by_arm"] = findings_by_arm

raw_dq_letters = chosen.get("disqualifiers")
dq_letters = raw_dq_letters if isinstance(raw_dq_letters, dict) else {}
invalid_dq_letters = [
    letter for letter in slot_letters
    if letter in dq_letters and not is_bool(dq_letters.get(letter))
]
if invalid_dq_letters:
    raise SystemExit(f"invalid judge disqualifier value(s): {', '.join(invalid_dq_letters)}")
dq_by_arm = {}
for l in slot_letters:
    if l not in mapping:
        continue
    arm = mapping[l]
    dq_by_arm[arm] = {
        "disqualifier": dq_letters.get(l, False) is True,
        "reason": str(dq_letters.get(f"{l}_reason", "") or ""),
    }
chosen["disqualifiers_by_arm"] = dq_by_arm

# Pairwise margins (positive = first arm beat second).
def margin(left: str, right: str):
    if left in scores_by_arm and right in scores_by_arm:
        return scores_by_arm[left] - scores_by_arm[right]
    return None

chosen["margins"] = {
    "variant_over_bare":   margin("variant", "bare"),
    "solo_over_bare":      margin("solo_claude", "bare"),
    "variant_over_solo":   margin("variant", "solo_claude"),
}

# Translate winner letter to arm
w = chosen.get("winner")
chosen["winner_arm"] = mapping.get(w, "tie") if w in mapping else "tie"

# Legacy 2-arm fields preserved so older summary code still parses. When
# solo_claude is present, variant/bare margin is derived from scores_by_arm.
chosen["variant_score"] = scores_by_arm.get("variant")
chosen["bare_score"]    = scores_by_arm.get("bare")
if chosen.get("variant_score") is not None and chosen.get("bare_score") is not None:
    chosen["margin"] = chosen["variant_score"] - chosen["bare_score"]

target.write_text(json.dumps(chosen, indent=2))
parts = [f"{arm}={s}" for arm, s in scores_by_arm.items()]
mline = chosen.get("margins") or {}
mparts = [f"{k}={v:+d}" for k, v in mline.items() if v is not None]
print(f"[judge] " + " ".join(parts) + ("  | " + " ".join(mparts) if mparts else ""))
PY
