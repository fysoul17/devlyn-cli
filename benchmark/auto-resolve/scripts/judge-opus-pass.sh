#!/usr/bin/env bash
# judge-opus-pass.sh — POST-RUN Opus 4.7 dual-judge sidecar.
#
# Runs Opus 4.7 over the SAME sanitized blind prompts that judge.sh wrote
# (judge-prompt.txt), producing a parallel judge-opus.json alongside the
# canonical judge.json. Does NOT modify judge.sh and does NOT change the
# measurement contract for the in-flight run — this is a sidecar that adds
# cross-judge data after the suite finishes.
#
# Why: today's judge is GPT-5.5 only, but variant arms run BUILD/FIX on
# GPT-5.5 too — self-judgment bias. Opus pass tests inter-judge agreement.
#
# Usage:
#   judge-opus-pass.sh --run-id <ID>
#
# Reads:   results/<run-id>/<fixture>/judge-prompt.txt  (blind A/B prompt)
#          results/<run-id>/<fixture>/judge.json        (for blind mapping)
# Writes:  results/<run-id>/<fixture>/judge-opus.json   (Opus's parsed result)
#          results/<run-id>/cross-judge-summary.json    (agreement metrics)
#
# Permanent dual-judge in judge.sh itself is queued as iter-0007 candidate;
# see memory/project_dual_judge_2026_04_26.md.

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
# We document the model alias the user is on; actual model id is whatever
# Claude Code resolves at invocation time. Recorded for traceability.
JUDGE_MODEL_ALIAS="opus-4.7"

echo "[opus-judge] run-id=$RUN_ID  cli=$CLAUDE_CLI_VER  model=$JUDGE_MODEL_ALIAS"

processed=0
skipped=0

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

  if [ -f "$opus_judge_f" ]; then
    echo "[opus-judge] skip $fid (already have judge-opus.json)"
    skipped=$((skipped + 1))
    continue
  fi

  echo "[opus-judge] judging $fid ..."

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
    continue
  fi

  # Parse JSON using same robust extraction logic judge.sh uses; merge with
  # the GPT judge's blind A/B mapping so variant_score / bare_score align.
  python3 - "$opus_out_raw" "$gpt_judge_f" "$opus_judge_f" "$CLAUDE_CLI_VER" "$JUDGE_MODEL_ALIAS" <<'PY'
import sys, json, pathlib
raw = pathlib.Path(sys.argv[1]).read_text()
gpt = json.loads(pathlib.Path(sys.argv[2]).read_text())
target = pathlib.Path(sys.argv[3])
cli_ver = sys.argv[4].strip()
model_alias = sys.argv[5].strip()

decoder = json.JSONDecoder()
brace_positions = [i for i, c in enumerate(raw) if c == '{']
chosen = None
for pos in reversed(brace_positions):
    try:
        obj, _ = decoder.raw_decode(raw[pos:])
    except json.JSONDecodeError:
        continue
    if isinstance(obj, dict) and "a_score" in obj and "b_score" in obj:
        chosen = obj
        break
if chosen is None:
    raise SystemExit(f"no valid JSON in opus output: {sys.argv[1]}")

mapping = gpt["_blind_mapping"]
chosen["_blind_mapping"] = mapping
chosen["_judge_cli"] = cli_ver
chosen["_judge_model"] = model_alias

a_arm = mapping["A"]
b_arm = mapping["B"]
chosen["variant_score"] = chosen["a_score"] if a_arm == "variant" else chosen["b_score"]
chosen["bare_score"]    = chosen["a_score"] if a_arm == "bare"    else chosen["b_score"]
chosen["margin"] = chosen["variant_score"] - chosen["bare_score"]
w = chosen.get("winner")
chosen["winner_arm"] = a_arm if w == "A" else b_arm if w == "B" else "tie"
target.write_text(json.dumps(chosen, indent=2))
print(f"[opus-judge] {target.parent.name} variant={chosen['variant_score']} bare={chosen['bare_score']} margin={chosen['margin']}")
PY
  processed=$((processed + 1))
done

# Aggregate inter-judge agreement
python3 - "$RES_ROOT" <<'PY'
import json, pathlib, sys, math
res_root = pathlib.Path(sys.argv[1])
rows = []
for fdir in sorted(res_root.glob("F*/")):
    g = fdir / "judge.json"
    o = fdir / "judge-opus.json"
    if not g.exists() or not o.exists():
        continue
    g = json.loads(g.read_text())
    o = json.loads(o.read_text())
    rows.append({
        "fixture": fdir.name,
        "gpt_variant": g["variant_score"], "gpt_bare": g["bare_score"], "gpt_margin": g["margin"], "gpt_winner": g["winner_arm"],
        "opus_variant": o["variant_score"], "opus_bare": o["bare_score"], "opus_margin": o["margin"], "opus_winner": o["winner_arm"],
        "winner_agree": g["winner_arm"] == o["winner_arm"],
        "sign_agree": (g["margin"] > 0) == (o["margin"] > 0) or (g["margin"] == 0 and o["margin"] == 0),
        "margin_abs_diff": abs(g["margin"] - o["margin"]),
    })
if not rows:
    print("[cross-judge] no paired judgements found")
    sys.exit(0)

n = len(rows)
winner_agree = sum(1 for r in rows if r["winner_agree"])
sign_agree = sum(1 for r in rows if r["sign_agree"])
mean_abs_margin_diff = sum(r["margin_abs_diff"] for r in rows) / n

# simple Pearson on margins
xs = [r["gpt_margin"] for r in rows]
ys = [r["opus_margin"] for r in rows]
mean_x = sum(xs) / n; mean_y = sum(ys) / n
num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
den_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
den_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
pearson = (num / (den_x * den_y)) if den_x > 0 and den_y > 0 else None

summary = {
    "n_fixtures": n,
    "winner_agree_count": winner_agree,
    "winner_agree_rate": winner_agree / n,
    "sign_agree_count": sign_agree,
    "sign_agree_rate": sign_agree / n,
    "mean_abs_margin_diff": mean_abs_margin_diff,
    "pearson_margin": pearson,
    "rows": rows,
}
out = res_root / "cross-judge-summary.json"
out.write_text(json.dumps(summary, indent=2))
print(f"[cross-judge] n={n} winner_agree={winner_agree}/{n} sign_agree={sign_agree}/{n} "
      f"mean_abs_margin_diff={mean_abs_margin_diff:.2f} pearson={pearson if pearson is None else f'{pearson:.3f}'}")
print(f"[cross-judge] wrote {out}")
PY

echo "[opus-judge] done: processed=$processed skipped=$skipped"
