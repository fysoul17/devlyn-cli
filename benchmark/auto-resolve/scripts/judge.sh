#!/usr/bin/env bash
# judge.sh — Codex GPT-5.4 (or current flagship) blind judge for ONE fixture.
#
# Usage:
#   judge.sh --fixture <FID> --run-id <ID>
#
# Reads:
#   results/<run-id>/<fixture>/variant/diff.patch + verify.json
#   results/<run-id>/<fixture>/bare/diff.patch + verify.json
#   fixtures/<fixture>/spec.md + expected.json + NOTES.md
#   RUBRIC.md (stable rubric)
#
# Writes:
#   results/<run-id>/<fixture>/judge.json
#
# Blind: A/B assignment randomized per fixture, seed stored in judge.json.

set -euo pipefail

usage() { echo "usage: $0 --fixture <FID> --run-id <ID>"; exit 1; }
FIXTURE=""; RUN_ID=""
while [ $# -gt 0 ]; do
  case "$1" in
    --fixture) FIXTURE="$2"; shift 2;;
    --run-id)  RUN_ID="$2";  shift 2;;
    *) usage;;
  esac
done
[ -n "$FIXTURE" ] && [ -n "$RUN_ID" ] || usage

BENCH_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FIX_DIR="$BENCH_ROOT/fixtures/$FIXTURE"
RES_DIR="$BENCH_ROOT/results/$RUN_ID/$FIXTURE"
VARIANT_DIR="$RES_DIR/variant"
BARE_DIR="$RES_DIR/bare"

for f in \
  "$VARIANT_DIR/diff.patch" "$VARIANT_DIR/verify.json" \
  "$BARE_DIR/diff.patch" "$BARE_DIR/verify.json" \
  "$FIX_DIR/spec.md" "$FIX_DIR/expected.json" \
  "$BENCH_ROOT/RUBRIC.md"
do
  [ -f "$f" ] || { echo "missing required input: $f"; exit 1; }
done

# Blind A/B mapping — random but recorded
SEED=$RANDOM
if (( SEED % 2 == 0 )); then
  A_ARM="variant"; B_ARM="bare"
else
  A_ARM="bare"; B_ARM="variant"
fi

PROMPT_FILE="$RES_DIR/judge-prompt.txt"
A_DIFF="$RES_DIR/$A_ARM/diff.patch"
B_DIFF="$RES_DIR/$B_ARM/diff.patch"
A_VERIFY="$RES_DIR/$A_ARM/verify.json"
B_VERIFY="$RES_DIR/$B_ARM/verify.json"

# Sanitize diffs so stylistic tells that correlate with variant (e.g.
# pipeline-commit markers, .devlyn/ archive lines) don't leak to the judge.
# Judge sees only file-content changes; the transcript, arm label, NOTES.md,
# and all process artifacts stay out of the prompt.
python3 - "$PROMPT_FILE" "$FIX_DIR/spec.md" "$FIX_DIR/expected.json" "$BENCH_ROOT/RUBRIC.md" "$A_DIFF" "$B_DIFF" "$A_VERIFY" "$B_VERIFY" <<'PY'
import sys, pathlib, re, json
out, spec_p, exp_p, rubric_p, a_diff, b_diff, a_ver, b_ver = map(pathlib.Path, sys.argv[1:])
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
    data = json.loads(path.read_text())
    # Remove anything that could name the arm
    data.pop("arm", None)
    return json.dumps(data, indent=2)

a_diff_text = sanitize(a_diff.read_text())
b_diff_text = sanitize(b_diff.read_text())
a_ver_text = sanitize_verify(a_ver)
b_ver_text = sanitize_verify(b_ver)

prompt = f"""You are a blind code-review judge. Two engineers implemented the same spec. You do NOT know which implementation came from which process — grade them only on the merits of the code and its behavior.

Apply the 4-axis rubric from RUBRIC.md below. Each axis is 0-25, total 100.

Return STRICT JSON only — no prose outside the JSON. Format:

{{
  "a_score": <int 0-100>,
  "b_score": <int 0-100>,
  "winner": "A" | "B" | "tie",
  "margin": <int, a_score - b_score>,
  "a_breakdown": {{"spec": 0-25, "constraint": 0-25, "scope": 0-25, "quality": 0-25, "notes": "<3-5 bullets>"}},
  "b_breakdown": {{"spec": 0-25, "constraint": 0-25, "scope": 0-25, "quality": 0-25, "notes": "<3-5 bullets>"}},
  "critical_findings": {{"A": ["..."], "B": ["..."]}},
  "disqualifiers": {{"A": bool, "B": bool, "A_reason": "...", "B_reason": "..."}},
  "overall_reasoning": "<5-8 sentences>"
}}

=== RUBRIC ===
{rubric}

=== SPEC ===
{spec}

=== EXPECTED (machine-readable acceptance) ===
{expected}

=== IMPLEMENTATION A ===
Diff:
```diff
{a_diff_text}
```
Verification results:
```json
{a_ver_text}
```

=== IMPLEMENTATION B ===
Diff:
```diff
{b_diff_text}
```
Verification results:
```json
{b_ver_text}
```

Return the JSON and nothing else.
"""
out.write_text(prompt)
PY

# Invoke Codex — no -m so CLI flagship is inherited. Model identity is
# recorded from the codex config.toml so rejudging with a newer flagship is
# traceable. Run from a clean temp CWD so the judge can't peek at project
# files that would leak arm identity.
command -v codex >/dev/null 2>&1 || { echo "codex CLI not on PATH; cannot judge"; exit 1; }
CODEX_CLI_VER=$(codex --version 2>/dev/null || echo "codex-cli unknown")
JUDGE_MODEL=$(grep -E '^model\s*=' "${HOME}/.codex/config.toml" 2>/dev/null | head -1 | sed -E 's/.*=\s*"?([^"]+)"?.*/\1/')
[ -z "$JUDGE_MODEL" ] && JUDGE_MODEL="(unknown — codex config.toml not readable)"

JUDGE_CWD="/tmp/judge-$RUN_ID-$FIXTURE"
rm -rf "$JUDGE_CWD"
mkdir -p "$JUDGE_CWD"

JUDGE_OUT="$RES_DIR/judge-output.txt"
set +e
cat "$PROMPT_FILE" | (cd "$JUDGE_CWD" && codex exec -s read-only -c model_reasoning_effort=xhigh - ) > "$JUDGE_OUT" 2>&1
JUDGE_EXIT=$?
set -e
rm -rf "$JUDGE_CWD"
if [ $JUDGE_EXIT -ne 0 ]; then
  echo "codex exec failed (exit $JUDGE_EXIT); see $JUDGE_OUT"
  exit 1
fi

# Extract JSON (codex wraps with banners; pick the last {...} block)
python3 - "$JUDGE_OUT" "$RES_DIR/judge.json" "$A_ARM" "$B_ARM" "$SEED" "$CODEX_CLI_VER" "$JUDGE_MODEL" <<'PY'
import sys, re, json, pathlib
out = pathlib.Path(sys.argv[1]).read_text()
target = pathlib.Path(sys.argv[2])
a_arm, b_arm, seed, codex_ver, judge_model = sys.argv[3:8]

# Find the last balanced JSON object in the output
candidates = []
depth = 0
start = None
for i, ch in enumerate(out):
    if ch == '{':
        if depth == 0: start = i
        depth += 1
    elif ch == '}':
        depth -= 1
        if depth == 0 and start is not None:
            candidates.append(out[start:i+1])
            start = None
chosen = None
for c in reversed(candidates):
    try:
        parsed = json.loads(c)
        if "a_score" in parsed and "b_score" in parsed:
            chosen = parsed; break
    except Exception:
        continue
if chosen is None:
    raise SystemExit(f"no valid JSON in judge output; see {sys.argv[1]}")

# Decode blind labels
mapping = {a_arm: "A", b_arm: "B"}
chosen["_blind_mapping"] = {"A": a_arm, "B": b_arm, "seed": int(seed)}
chosen["_judge_cli"] = codex_ver.strip()
chosen["_judge_model"] = judge_model.strip()

# Convenience: translate winner A/B to variant/bare
w = chosen.get("winner")
if w == "A":
    chosen["winner_arm"] = a_arm
elif w == "B":
    chosen["winner_arm"] = b_arm
else:
    chosen["winner_arm"] = "tie"

chosen["variant_score"] = chosen["a_score"] if a_arm == "variant" else chosen["b_score"]
chosen["bare_score"]    = chosen["a_score"] if a_arm == "bare"    else chosen["b_score"]
chosen["margin"] = chosen["variant_score"] - chosen["bare_score"]

target.write_text(json.dumps(chosen, indent=2))
print(f"[judge] variant={chosen['variant_score']} bare={chosen['bare_score']} margin={chosen['margin']}")
PY
