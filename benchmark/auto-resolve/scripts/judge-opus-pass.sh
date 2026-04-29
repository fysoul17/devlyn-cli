#!/usr/bin/env bash
# judge-opus-pass.sh — POST-RUN Opus 4.7 dual-judge sidecar.
#
# Runs Opus 4.7 over the SAME sanitized blind prompts that judge.sh wrote
# (judge-prompt.txt), producing a parallel judge-opus.json alongside the
# canonical judge.json. Does NOT modify judge.sh and does NOT change the
# measurement contract for the in-flight run — this is a sidecar that adds
# cross-judge data after the suite finishes.
#
# Why: judge.sh runs GPT-5.5 today; variant arms run Codex BUILD/FIX on
# GPT-5.5 too — self-judgment bias. Opus pass tests inter-judge agreement.
#
# iter-0025 (B-1) rewrite — 3-arm aware. Prior version computed only legacy
# `variant_score / bare_score / margin` from A/B slots (Codex R0 caught: F1
# has variant in C; F6/F9 have bare in C — legacy parser silently produced
# wrong margins on iter-0020 mappings). This version mirrors judge.sh post
# iter-0023:
#   - Reads `_blind_mapping` from gpt judge.json (A/B/C → arm name).
#   - Requires C-slot score when C is present in mapping.
#   - Computes `scores_by_arm`, `margins.{variant_over_bare, solo_over_bare,
#     variant_over_solo}`, and per-arm 4-axis breakdown.
#   - Validates each axis cell ∈ [0, 25] (clamp + record under
#     `_axis_validation`, same shape as judge.sh).
#   - Always re-judges (no skip-on-exists) so cross-judge results never go
#     stale.
#   - Aggregator computes per-axis L1-L0 disagreement vs GPT (the decisive
#     metric per Codex R0 Q1 — falsification rule: any axis disagreement >2
#     means iter-0021/0023 L1 readout is single-judge artifact).
#
# Usage:
#   judge-opus-pass.sh --run-id <ID>
#
# Reads:   results/<run-id>/<fixture>/judge-prompt.txt  (blind A/B/C prompt)
#          results/<run-id>/<fixture>/judge.json        (blind mapping)
# Writes:  results/<run-id>/<fixture>/judge-opus.json   (Opus's parsed result)
#          results/<run-id>/cross-judge-summary.json    (agreement metrics)

set -euo pipefail

usage() { echo "usage: $0 --run-id <ID>"; exit 1; }
RUN_ID=""
while [ $# -gt 0 ]; do
  case "$1" in
    --run-id) RUN_ID="$2"; shift 2;;
    *) usage;;
  esac
done
[ -n "$RUN_ID" ] || usage

BENCH_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RES_ROOT="$BENCH_ROOT/results/$RUN_ID"
[ -d "$RES_ROOT" ] || { echo "no results dir: $RES_ROOT"; exit 1; }

command -v claude >/dev/null 2>&1 || { echo "claude CLI not on PATH"; exit 1; }

CLAUDE_CLI_VER=$(claude --version 2>/dev/null || echo "claude-cli unknown")
JUDGE_MODEL_ALIAS="opus-4.7"

echo "[opus-judge] run-id=$RUN_ID  cli=$CLAUDE_CLI_VER  model=$JUDGE_MODEL_ALIAS"

processed=0
skipped=0
failed=0

for fixture_dir in "$RES_ROOT"/F*/; do
  [ -d "$fixture_dir" ] || continue
  fid=$(basename "$fixture_dir")
  prompt_f="$fixture_dir/judge-prompt.txt"
  gpt_judge_f="$fixture_dir/judge.json"
  opus_out_raw="$fixture_dir/judge-opus-output.txt"
  opus_judge_f="$fixture_dir/judge-opus.json"

  if [ ! -f "$prompt_f" ] || [ ! -f "$gpt_judge_f" ]; then
    echo "[opus-judge] skip $fid (missing prompt or gpt judge)"
    skipped=$((skipped + 1))
    continue
  fi

  echo "[opus-judge] judging $fid ..."

  # Codex R1 #2: drop any stale judge-opus.json before re-judging. Otherwise
  # a parse failure here keeps the previous run's file and the aggregator
  # silently reads it.
  rm -f "$opus_judge_f"

  # Strict MCP isolation matches the variant arm contract — no user MCP
  # leakage into the judge call. Run from a clean tmp CWD so it can't peek
  # at project files that might leak arm identity.
  JUDGE_CWD="/tmp/opus-judge-$RUN_ID-$fid"
  rm -rf "$JUDGE_CWD"
  mkdir -p "$JUDGE_CWD"

  set +e
  ( cd "$JUDGE_CWD" && claude -p "$(cat "$prompt_f")" \
      --dangerously-skip-permissions \
      --strict-mcp-config --mcp-config '{"mcpServers":{}}' \
  ) > "$opus_out_raw" 2>&1
  rc=$?
  set -e
  rm -rf "$JUDGE_CWD"

  if [ $rc -ne 0 ]; then
    echo "[opus-judge] ✗ $fid claude -p exit=$rc (output preserved at $opus_out_raw)"
    failed=$((failed + 1))
    continue
  fi

  python3 - "$opus_out_raw" "$gpt_judge_f" "$opus_judge_f" "$CLAUDE_CLI_VER" "$JUDGE_MODEL_ALIAS" <<'PY' || { echo "[opus-judge] ✗ $fid parse failed"; failed=$((failed + 1)); continue; }
import sys, json, pathlib

raw = pathlib.Path(sys.argv[1]).read_text()
gpt = json.loads(pathlib.Path(sys.argv[2]).read_text())
target = pathlib.Path(sys.argv[3])
cli_ver = sys.argv[4].strip()
model_alias = sys.argv[5].strip()

# Robust JSON extraction — last valid {} block with required score keys.
mapping = gpt.get("_blind_mapping") or {}
required_score_keys = ["a_score", "b_score"]
if "C" in mapping:
    required_score_keys.append("c_score")

decoder = json.JSONDecoder()
brace_positions = [i for i, c in enumerate(raw) if c == '{']
chosen = None
for pos in reversed(brace_positions):
    try:
        obj, _ = decoder.raw_decode(raw[pos:])
    except json.JSONDecodeError:
        continue
    if isinstance(obj, dict) and all(k in obj for k in required_score_keys):
        chosen = obj
        break
if chosen is None:
    raise SystemExit(
        f"no valid JSON with keys {required_score_keys} in opus output: {sys.argv[1]}"
    )

# Axis validation — mirror judge.sh post iter-0023.
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
        if not isinstance(v, (int, float)) or v < 0 or v > 25:
            axis_invalid_cells.append({"breakdown": bk, "axis": axis, "value": v})
            chosen[bk][axis] = max(0, min(25, int(v) if isinstance(v, (int, float)) else 0))
chosen["_axis_validation"] = {
    "out_of_range_count": len(axis_invalid_cells),
    "out_of_range_cells": axis_invalid_cells,
    "axis_range": [0, 25],
}
if axis_invalid_cells:
    sys.stderr.write(
        f"[opus-judge] WARNING: {len(axis_invalid_cells)} axis cell(s) out of [0,25] "
        f"clamped: {axis_invalid_cells}\n"
    )

# Reuse GPT's blind mapping verbatim (same blind A/B/C decoded the same way).
chosen["_blind_mapping"] = mapping
chosen["_judge_cli"] = cli_ver
chosen["_judge_model"] = model_alias

# scores_by_arm + margins — mirror judge.sh post iter-0023.
slot_keys = ["a_score", "b_score", "c_score"]
slot_letters = ["A", "B", "C"]
scores_by_arm = {}
for letter, key in zip(slot_letters, slot_keys):
    arm = mapping.get(letter)
    if arm is not None and key in chosen:
        scores_by_arm[arm] = chosen[key]
chosen["scores_by_arm"] = scores_by_arm

def margin(left, right):
    if left in scores_by_arm and right in scores_by_arm:
        return scores_by_arm[left] - scores_by_arm[right]
    return None

chosen["margins"] = {
    "variant_over_bare":   margin("variant", "bare"),
    "solo_over_bare":      margin("solo_claude", "bare"),
    "variant_over_solo":   margin("variant", "solo_claude"),
}

# Per-arm axis breakdown.
breakdowns_by_arm = {}
for letter, bk in zip(slot_letters, BREAKDOWN_KEYS):
    arm = mapping.get(letter)
    if arm is not None and bk in chosen:
        breakdowns_by_arm[arm] = chosen[bk]
chosen["breakdowns_by_arm"] = breakdowns_by_arm

# Per-arm critical_findings + disqualifiers (same shape judge.sh emits).
findings_letters = chosen.get("critical_findings", {}) or {}
chosen["findings_by_arm"] = {
    mapping[l]: findings_letters.get(l, []) for l in slot_letters if l in mapping
}
dq_letters = chosen.get("disqualifiers", {}) or {}
dq_by_arm = {}
for l in slot_letters:
    if l not in mapping:
        continue
    arm = mapping[l]
    dq_by_arm[arm] = {
        "disqualifier": bool(dq_letters.get(l, False)),
        "reason": str(dq_letters.get(f"{l}_reason", "") or ""),
    }
chosen["disqualifiers_by_arm"] = dq_by_arm

# Winner letter → arm.
w = chosen.get("winner")
if w in slot_letters and w in mapping:
    chosen["winner_arm"] = mapping[w]
elif w == "tie":
    chosen["winner_arm"] = "tie"
else:
    chosen["winner_arm"] = None

# Legacy fields kept for back-compat.
a_arm = mapping.get("A")
b_arm = mapping.get("B")
chosen["variant_score"] = scores_by_arm.get("variant")
chosen["bare_score"]    = scores_by_arm.get("bare")
chosen["solo_score"]    = scores_by_arm.get("solo_claude")
if chosen["variant_score"] is not None and chosen["bare_score"] is not None:
    chosen["margin"] = chosen["variant_score"] - chosen["bare_score"]
else:
    chosen["margin"] = None

target.write_text(json.dumps(chosen, indent=2))
print(
    f"[opus-judge] {target.parent.name} "
    f"v={chosen.get('variant_score')} l1={chosen.get('solo_score')} l0={chosen.get('bare_score')} "
    f"l1-l0={chosen['margins']['solo_over_bare']} v-l1={chosen['margins']['variant_over_solo']}"
)
PY
  processed=$((processed + 1))
done

echo "[opus-judge] judge passes: processed=$processed skipped=$skipped failed=$failed"

# Aggregate cross-judge agreement, including per-axis L1-L0 disagreement.
python3 - "$RES_ROOT" <<'PY'
import json, pathlib, sys, math

res_root = pathlib.Path(sys.argv[1])
rows = []
axis_keys = ("spec", "constraint", "scope", "quality")

for fdir in sorted(res_root.glob("F*/")):
    g_f = fdir / "judge.json"
    o_f = fdir / "judge-opus.json"
    if not g_f.exists() or not o_f.exists():
        continue
    g = json.loads(g_f.read_text())
    o = json.loads(o_f.read_text())

    # Per-axis L1-L0 (solo_claude − bare) for both judges.
    # Codex R1 #1: judge.sh historically writes `a/b/c_breakdown` plus
    # `_blind_mapping`, NOT `breakdowns_by_arm`. iter-0020 judge.json files
    # are in that historical shape. Derive per-arm breakdowns from letter
    # fields when `breakdowns_by_arm` is absent; fail loudly when neither
    # source is available so axis disagreement never silently falls to zero.
    def axis_l1_l0(j, label):
        bka = j.get("breakdowns_by_arm") or {}
        if "solo_claude" in bka and "bare" in bka:
            l1 = bka["solo_claude"]; l0 = bka["bare"]
        else:
            mapping = j.get("_blind_mapping") or {}
            slot_letters = ["A", "B", "C"]
            slot_breakdowns = ["a_breakdown", "b_breakdown", "c_breakdown"]
            derived = {}
            for letter, bk in zip(slot_letters, slot_breakdowns):
                arm = mapping.get(letter)
                if arm is not None and bk in j:
                    derived[arm] = j[bk]
            if "solo_claude" not in derived or "bare" not in derived:
                raise SystemExit(
                    f"[cross-judge] {label} judge.json missing breakdowns for solo_claude/bare; "
                    "expected either `breakdowns_by_arm` or `a/b/c_breakdown` + `_blind_mapping`"
                )
            l1 = derived["solo_claude"]; l0 = derived["bare"]
        return {a: (l1.get(a, 0) - l0.get(a, 0)) for a in axis_keys}

    g_axes = axis_l1_l0(g, f"gpt {fdir.name}")
    o_axes = axis_l1_l0(o, f"opus {fdir.name}")
    axis_disagreement = {a: o_axes[a] - g_axes[a] for a in axis_keys}

    g_margins = (g.get("margins") or {})
    o_margins = (o.get("margins") or {})
    g_l1_l0 = g_margins.get("solo_over_bare")
    o_l1_l0 = o_margins.get("solo_over_bare")
    g_v_l0 = g_margins.get("variant_over_bare")
    o_v_l0 = o_margins.get("variant_over_bare")
    margin_l1_l0_diff = (
        abs(g_l1_l0 - o_l1_l0) if g_l1_l0 is not None and o_l1_l0 is not None else None
    )
    margin_v_l0_diff = (
        abs(g_v_l0 - o_v_l0) if g_v_l0 is not None and o_v_l0 is not None else None
    )

    rows.append({
        "fixture": fdir.name,
        "gpt_scores":   g.get("scores_by_arm") or {},
        "opus_scores":  o.get("scores_by_arm") or {},
        "gpt_margin_l1_l0":  g_l1_l0,
        "opus_margin_l1_l0": o_l1_l0,
        "margin_l1_l0_diff": margin_l1_l0_diff,
        "gpt_margin_v_l0":   g_v_l0,
        "opus_margin_v_l0":  o_v_l0,
        "margin_v_l0_diff":  margin_v_l0_diff,
        "gpt_axis_l1_l0":    g_axes,
        "opus_axis_l1_l0":   o_axes,
        "axis_disagreement": axis_disagreement,
        "winner_agree":   g.get("winner_arm") == o.get("winner_arm"),
        "gpt_winner":     g.get("winner_arm"),
        "opus_winner":    o.get("winner_arm"),
    })

if not rows:
    print("[cross-judge] no paired judgements found")
    sys.exit(0)

n = len(rows)

# Suite-level per-axis L1-L0 sum (both judges) and disagreement.
g_axis_sum = {a: sum(r["gpt_axis_l1_l0"][a] for r in rows) for a in axis_keys}
o_axis_sum = {a: sum(r["opus_axis_l1_l0"][a] for r in rows) for a in axis_keys}
axis_sum_disagreement = {a: o_axis_sum[a] - g_axis_sum[a] for a in axis_keys}
max_abs_axis_disagreement = max(abs(v) for v in axis_sum_disagreement.values())

# Per-axis falsification rule (Codex R0 Q1): any axis-sum disagreement >2 → single-judge artifact.
THRESHOLD = 2
falsified_by_axis = max_abs_axis_disagreement > THRESHOLD
flipped_axes = [a for a, v in axis_sum_disagreement.items() if abs(v) > THRESHOLD]

# Suite avg L1-L0 (both judges) — Codex R1 #3: divide by valid-count, report denom.
gpt_l1_l0_valid = [r["gpt_margin_l1_l0"] for r in rows if r["gpt_margin_l1_l0"] is not None]
opus_l1_l0_valid = [r["opus_margin_l1_l0"] for r in rows if r["opus_margin_l1_l0"] is not None]
gpt_l1_l0_avg = (sum(gpt_l1_l0_valid) / len(gpt_l1_l0_valid)) if gpt_l1_l0_valid else None
opus_l1_l0_avg = (sum(opus_l1_l0_valid) / len(opus_l1_l0_valid)) if opus_l1_l0_valid else None
suite_avg_diff = (
    abs(gpt_l1_l0_avg - opus_l1_l0_avg)
    if gpt_l1_l0_avg is not None and opus_l1_l0_avg is not None else None
)

# Sign agreement — Codex R1 #4: 3-way sign (-, 0, +) so tie vs positive don't agree.
def sign3(v):
    if v is None:
        return None
    return 1 if v > 0 else (-1 if v < 0 else 0)

sign_agree_v_l0 = sum(
    1 for r in rows
    if r["gpt_margin_v_l0"] is not None and r["opus_margin_v_l0"] is not None
    and sign3(r["gpt_margin_v_l0"]) == sign3(r["opus_margin_v_l0"])
)
sign_agree_l1_l0 = sum(
    1 for r in rows
    if r["gpt_margin_l1_l0"] is not None and r["opus_margin_l1_l0"] is not None
    and sign3(r["gpt_margin_l1_l0"]) == sign3(r["opus_margin_l1_l0"])
)
sign_valid_l1_l0 = sum(
    1 for r in rows
    if r["gpt_margin_l1_l0"] is not None and r["opus_margin_l1_l0"] is not None
)
sign_valid_v_l0 = sum(
    1 for r in rows
    if r["gpt_margin_v_l0"] is not None and r["opus_margin_v_l0"] is not None
)
winner_agree = sum(1 for r in rows if r["winner_agree"])

l1_l0_diffs = [r["margin_l1_l0_diff"] for r in rows if r["margin_l1_l0_diff"] is not None]
mean_abs_l1_l0_diff = (sum(l1_l0_diffs) / len(l1_l0_diffs)) if l1_l0_diffs else None

summary = {
    "n_fixtures": n,
    "threshold": THRESHOLD,
    "falsified_by_axis_disagreement": falsified_by_axis,
    "flipped_axes": flipped_axes,
    "axis_sum_l1_l0": {
        "gpt": g_axis_sum,
        "opus": o_axis_sum,
        "disagreement": axis_sum_disagreement,
        "max_abs_disagreement": max_abs_axis_disagreement,
    },
    "suite_avg_l1_l0": {
        "gpt": gpt_l1_l0_avg,
        "opus": opus_l1_l0_avg,
        "abs_diff": suite_avg_diff,
        "gpt_valid_count":  len(gpt_l1_l0_valid),
        "opus_valid_count": len(opus_l1_l0_valid),
    },
    "winner_agree_count": winner_agree,
    "sign_agree_l1_l0":               sign_agree_l1_l0,
    "sign_valid_count_l1_l0":         sign_valid_l1_l0,
    "sign_agree_variant_over_bare":   sign_agree_v_l0,
    "sign_valid_count_variant_over_bare": sign_valid_v_l0,
    "mean_abs_l1_l0_margin_diff": mean_abs_l1_l0_diff,
    "mean_abs_l1_l0_valid_count": len(l1_l0_diffs),
    "rows": rows,
}
out = res_root / "cross-judge-summary.json"
out.write_text(json.dumps(summary, indent=2))

print(
    f"[cross-judge] n={n} "
    f"falsified={falsified_by_axis} flipped_axes={flipped_axes} "
    f"max_axis_disagreement={max_abs_axis_disagreement} "
    f"gpt_l1_l0_avg={gpt_l1_l0_avg:.2f} opus_l1_l0_avg={opus_l1_l0_avg:.2f} "
    f"suite_avg_diff={suite_avg_diff:.2f}"
)
print(f"[cross-judge] axis_sum_l1_l0: gpt={g_axis_sum} opus={o_axis_sum} disagree={axis_sum_disagreement}")
print(f"[cross-judge] wrote {out}")
PY

# Hard-fail summary if not all 9 fixtures produced paired judgements.
EXPECTED_FIXTURES=$(ls -d "$RES_ROOT"/F*/ 2>/dev/null | wc -l | awk '{print $1}')
PAIRED=$(find "$RES_ROOT" -maxdepth 2 -name 'judge-opus.json' | wc -l | awk '{print $1}')
echo "[opus-judge] expected_fixtures=$EXPECTED_FIXTURES paired=$PAIRED"
if [ "$PAIRED" -ne "$EXPECTED_FIXTURES" ]; then
  echo "[opus-judge] ✗ paired ($PAIRED) != expected ($EXPECTED_FIXTURES) — sidecar incomplete; do not interpret cross-judge until all fixtures judged."
  exit 2
fi
echo "[opus-judge] done: processed=$processed skipped=$skipped failed=$failed"
