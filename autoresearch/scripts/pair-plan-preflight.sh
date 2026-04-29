#!/usr/bin/env bash
# pair-plan-preflight.sh — orchestrate the iter-0022 plan-preflight pipeline
# for one fixture. Stages a blind input bundle, generates the canonical ID
# registry, produces solo + pair plan artifacts (dry-run stubs in iter-0022),
# lints both, and emits a machine-readable verdict.
#
# iter-0022 contract: real provider/model invocations = 0. The --dry-run flag
# (default in iter-0022) substitutes deterministic Python stubs for the
# Claude / Codex planning calls. iter-0023 will introduce a non-dry-run path
# that wires `claude -p` and `codex-monitored.sh` in place of the stubs.
#
# Output layout (per HANDOFF.md:280, with canonical_id_registry.json in
# place of the deprecated `canonical-ids.json` name):
#
#   <output-base>/<run_id>/<blind_alias>/plan-preflight/
#     input.bundle/
#       spec.md
#       expected.json
#       metadata.json
#       task.txt
#       canonical_id_registry.json
#     canonical_id_registry.json
#     solo-plan.json
#     drafts/
#       claude.json
#       codex.json
#     merged/
#       pair-plan.json
#     lint.solo.json
#     lint.pair.json
#     verdict.json

set -euo pipefail

usage() {
  cat <<'EOF'
Usage: pair-plan-preflight.sh [options]

  --fixture <dir>          Path to fixture dir (required). Must contain
                           spec.md, expected.json, metadata.json, task.txt.
  --output-base <dir>      Where to write the result tree. Default:
                           benchmark/auto-resolve/results
  --run-id <id>            Run identifier. Default: auto-generated UTC stamp.
  --generated-at <iso8601> Pin idgen's generated_at field for determinism.
                           Default: UTC now.
  --dry-run                Use deterministic stubs in place of real model calls.
                           This is the only mode supported in iter-0022.
                           (No-op flag in iter-0022; reserved for iter-0023.)
  --no-dry-run             EXPLICITLY refuse to run — in iter-0022 the script
                           always uses stubs. Calling --no-dry-run today is a
                           configuration error and exits 65.
  -h | --help              Show this message.
EOF
}

FIXTURE=""
OUTPUT_BASE="benchmark/auto-resolve/results"
RUN_ID=""
GENERATED_AT=""
DRY_RUN=1

while [ $# -gt 0 ]; do
  case "$1" in
    --fixture)        FIXTURE="$2"; shift 2 ;;
    --output-base)    OUTPUT_BASE="$2"; shift 2 ;;
    --run-id)         RUN_ID="$2"; shift 2 ;;
    --generated-at)   GENERATED_AT="$2"; shift 2 ;;
    --dry-run)        DRY_RUN=1; shift ;;
    --no-dry-run)
      cat >&2 <<'EOF'
[pair-plan-preflight] error: --no-dry-run is unsupported in iter-0022.
iter-0022 contract requires real provider/model invocations = 0. The
non-dry-run path lands in iter-0023 along with the measurement pilot.
EOF
      exit 65
      ;;
    -h|--help)        usage; exit 0 ;;
    *) printf '[pair-plan-preflight] unknown arg: %s\n' "$1" >&2; usage >&2; exit 64 ;;
  esac
done

if [ -z "$FIXTURE" ]; then
  echo "[pair-plan-preflight] --fixture is required" >&2
  usage >&2
  exit 64
fi
if [ ! -d "$FIXTURE" ]; then
  echo "[pair-plan-preflight] fixture dir does not exist: $FIXTURE" >&2
  exit 64
fi
for required in spec.md expected.json metadata.json task.txt; do
  if [ ! -f "$FIXTURE/$required" ]; then
    echo "[pair-plan-preflight] fixture missing required file: $FIXTURE/$required" >&2
    exit 64
  fi
done

if [ -z "$RUN_ID" ]; then
  RUN_ID="ppf-$(date -u +%Y%m%dT%H%M%SZ)"
fi
if [ -z "$GENERATED_AT" ]; then
  GENERATED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
fi

# Deterministic blind alias: 12-hex prefix of sha256(fixture-name + run-id).
FIXTURE_BASENAME="$(basename "$FIXTURE")"
BLIND_ALIAS="blind-$(printf '%s|%s' "$FIXTURE_BASENAME" "$RUN_ID" | shasum -a 256 | awk '{print substr($1,1,12)}')"

OUT_DIR="$OUTPUT_BASE/$RUN_ID/$BLIND_ALIAS/plan-preflight"
mkdir -p "$OUT_DIR/input.bundle" "$OUT_DIR/drafts" "$OUT_DIR/merged"

# ---------------------------------------------------------------------------
# Step 1 — stage blind input bundle.
# Copy spec.md / expected.json / metadata.json / task.txt verbatim.
# fixture_id inside metadata + registry is preserved for traceability;
# iter-0022's blinding goal is fixture-name-level only (alias the directory
# and bundle files), not field-level scrubbing — that is iter-0023 work if
# measurement shows it matters.
# ---------------------------------------------------------------------------
cp "$FIXTURE/spec.md"        "$OUT_DIR/input.bundle/spec.md"
cp "$FIXTURE/expected.json"  "$OUT_DIR/input.bundle/expected.json"
cp "$FIXTURE/metadata.json"  "$OUT_DIR/input.bundle/metadata.json"
cp "$FIXTURE/task.txt"       "$OUT_DIR/input.bundle/task.txt"

# ---------------------------------------------------------------------------
# Step 2 — generate canonical_id_registry.json via idgen.
# idgen reads the ORIGINAL fixture (not the bundle copy) so source SHAs match
# the on-disk authoritative files. The output is then snapshotted into both
# the bundle dir (so planners see it) and the top-level output dir (so
# consumers can read it without descending into input.bundle).
# ---------------------------------------------------------------------------
REGISTRY_OUT="$OUT_DIR/canonical_id_registry.json"
python3 benchmark/auto-resolve/scripts/pair-plan-idgen.py \
  --fixture "$FIXTURE" \
  --generated-at "$GENERATED_AT" \
  --output "$REGISTRY_OUT"
cp "$REGISTRY_OUT" "$OUT_DIR/input.bundle/canonical_id_registry.json"

# ---------------------------------------------------------------------------
# Step 3 — produce solo plan via dry-run stub.
# Stub policy: solo plan accepts every expected.json-derived invariant but
# only HALF of the oracle-derived invariants (deterministic by sorted id).
# This guarantees pair_caught > solo_caught on any fixture with oracle
# entries, which exercises the lift comparison logic in step 6.
# ---------------------------------------------------------------------------
SOLO_PLAN="$OUT_DIR/solo-plan.json"
python3 - "$REGISTRY_OUT" "$OUT_DIR/input.bundle" "$SOLO_PLAN" "solo" 1 <<'PYEOF'
import sys, json, hashlib, copy, pathlib
registry_path, bundle_dir, plan_path, mode, num_rounds = sys.argv[1:6]
num_rounds = int(num_rounds)

with open(registry_path, "r", encoding="utf-8") as f:
    registry = json.load(f)

ids_all = [e["id"] for e in registry["required_invariants"]]
oracle_ids = [i for i in ids_all if i.startswith(("test-fidelity:", "scope-tier-a:", "scope-tier-b:"))]
non_oracle = [i for i in ids_all if i not in oracle_ids]

unresolved_ids = []
if mode == "solo":
    # Half the oracle entries — keep ones at even sorted-index. Dropped
    # ids land in unresolved[] so the plan stays coverage-valid at draft
    # status (lint enforces full coverage only when plan_status==final).
    accepted_oracle = [oid for k, oid in enumerate(sorted(oracle_ids)) if k % 2 == 0]
    dropped_oracle  = [oid for k, oid in enumerate(sorted(oracle_ids)) if k % 2 == 1]
    accepted_ids = sorted(non_oracle + accepted_oracle)
    unresolved_ids = sorted(dropped_oracle)
elif mode == "pair":
    accepted_ids = sorted(ids_all)
else:
    sys.exit(f"unknown mode: {mode}")

# rounds[] required for pair, forbidden for solo
if mode == "pair":
    rounds = [{
        "round": 1,
        "claude_draft_sha256": "0" * 64,
        "codex_draft_sha256":  "1" * 64,
        "merged_sha256":       "2" * 64,
        "note": "dry-run stub: claude+codex independent drafts merged in one round",
    }]
    if num_rounds > 1:
        for r in range(2, num_rounds + 1):
            rounds.append({
                "round": r,
                "claude_draft_sha256": (str(r) * 64)[:64],
                "codex_draft_sha256":  (str(r + 1) * 64)[:64],
                "merged_sha256":       (str(r + 2) * 64)[:64],
                "note": f"dry-run stub: round {r}",
            })
else:
    rounds = []

def fsha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()

# Source file shas — we hash the bundle copies because they are what the
# planner saw. The plan's source.*_path fields point to the bundle so a
# downstream lint --plan <plan> works against the bundle inputs.
spec_p     = pathlib.Path(bundle_dir) / "spec.md"
expected_p = pathlib.Path(bundle_dir) / "expected.json"
registry_p = pathlib.Path(bundle_dir) / "canonical_id_registry.json"
# Rubric is repo-relative, not in the bundle (planner sees authoritative copy).
rubric_rel = "benchmark/auto-resolve/RUBRIC.md"
rubric_p   = pathlib.Path(rubric_rel)

accepted_invariants = []
id_lookup = {e["id"]: e for e in registry["required_invariants"]}
for rid in accepted_ids:
    e = id_lookup[rid]
    accepted_invariants.append({
        "id": rid,
        "paraphrase": e["operational_check"][:120],
        "source_refs": [e["source_ref"]],
        "operational_check": e["operational_check"],
        "authority": e["authority"],
    })

plan_status = "draft" if mode == "solo" and unresolved_ids else "final"
plan = {
    "schema_version": "1",
    "plan_status": plan_status,
    "planning_mode": mode,
    "fixture_id": registry["fixture_id"],
    "source": {
        "spec_path":          str(spec_p),
        "spec_sha256":        fsha(spec_p),
        "expected_path":      str(expected_p),
        "expected_sha256":    fsha(expected_p),
        "rubric_path":        rubric_rel,
        "rubric_sha256":      fsha(rubric_p),
        "canonical_id_registry_path":   str(registry_p),
        "canonical_id_registry_sha256": fsha(registry_p),
    },
    "authority_order": [
        "spec.md",
        "expected.json/rubric",
        "phase prompt",
        "model preference",
    ],
    "rounds": rounds,
    "accepted_invariants": accepted_invariants,
    "rejected_alternatives": [],
    "unresolved": [{"id": uid, "note": "dry-run stub: solo planner did not capture this oracle invariant"} for uid in unresolved_ids],
    "escalated_to_user": [],
    "model_stamps": {
        "claude": {
            "status": "sign",
            "blocked_ids": [],
            "signed_plan_sha256": "TODO",
            "model": "claude-opus-4-7",
            "timestamp": "2026-04-29T18:30:00Z",
        },
        "codex": {
            "status": "sign",
            "blocked_ids": [],
            "signed_plan_sha256": "TODO",
            "model": "gpt-5.5",
            "timestamp": "2026-04-29T18:31:00Z",
        },
    },
}

# Compute canonical pre-stamp sha
pre = copy.deepcopy(plan)
pre["model_stamps"] = {}
pre_bytes = json.dumps(pre, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
sha = hashlib.sha256(pre_bytes).hexdigest()
plan["model_stamps"]["claude"]["signed_plan_sha256"] = sha
plan["model_stamps"]["codex"]["signed_plan_sha256"]  = sha

# In solo mode we don't actually have a Codex co-signer; for the dry-run
# stub we set both to sign so the lint passes. Real-mode (iter-0023) will
# emit `block` from Codex when planning_mode=solo since Codex didn't review.
with open(plan_path, "w", encoding="utf-8") as f:
    json.dump(plan, f, indent=2, sort_keys=True, ensure_ascii=False)
    f.write("\n")
PYEOF

# ---------------------------------------------------------------------------
# Step 4 — produce pair plan via dry-run stub (one round; preflight stops at
# round 1 in dry-run, mirrors HANDOFF "neither model has new substantive
# critique" stopping rule).
# ---------------------------------------------------------------------------
PAIR_PLAN="$OUT_DIR/merged/pair-plan.json"
python3 - "$REGISTRY_OUT" "$OUT_DIR/input.bundle" "$PAIR_PLAN" "pair" 1 <<'PYEOF'
import sys, json, hashlib, copy, pathlib
# (same script body as solo — re-imported because heredoc cannot share state)
registry_path, bundle_dir, plan_path, mode, num_rounds = sys.argv[1:6]
num_rounds = int(num_rounds)
with open(registry_path, "r", encoding="utf-8") as f:
    registry = json.load(f)
ids_all = [e["id"] for e in registry["required_invariants"]]
oracle_ids = [i for i in ids_all if i.startswith(("test-fidelity:", "scope-tier-a:", "scope-tier-b:"))]
non_oracle = [i for i in ids_all if i not in oracle_ids]
unresolved_ids = []
if mode == "solo":
    accepted_oracle = [oid for k, oid in enumerate(sorted(oracle_ids)) if k % 2 == 0]
    dropped_oracle  = [oid for k, oid in enumerate(sorted(oracle_ids)) if k % 2 == 1]
    accepted_ids = sorted(non_oracle + accepted_oracle)
    unresolved_ids = sorted(dropped_oracle)
else:
    accepted_ids = sorted(ids_all)
rounds = []
if mode == "pair":
    rounds.append({
        "round": 1,
        "claude_draft_sha256": "0" * 64,
        "codex_draft_sha256":  "1" * 64,
        "merged_sha256":       "2" * 64,
        "note": "dry-run stub: claude+codex independent drafts merged in one round",
    })
def fsha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
spec_p     = pathlib.Path(bundle_dir) / "spec.md"
expected_p = pathlib.Path(bundle_dir) / "expected.json"
registry_p = pathlib.Path(bundle_dir) / "canonical_id_registry.json"
rubric_rel = "benchmark/auto-resolve/RUBRIC.md"
rubric_p   = pathlib.Path(rubric_rel)
id_lookup = {e["id"]: e for e in registry["required_invariants"]}
accepted_invariants = []
for rid in accepted_ids:
    e = id_lookup[rid]
    accepted_invariants.append({
        "id": rid,
        "paraphrase": e["operational_check"][:120],
        "source_refs": [e["source_ref"]],
        "operational_check": e["operational_check"],
        "authority": e["authority"],
    })
plan_status = "draft" if mode == "solo" and unresolved_ids else "final"
plan = {
    "schema_version": "1",
    "plan_status": plan_status,
    "planning_mode": mode,
    "fixture_id": registry["fixture_id"],
    "source": {
        "spec_path":          str(spec_p),
        "spec_sha256":        fsha(spec_p),
        "expected_path":      str(expected_p),
        "expected_sha256":    fsha(expected_p),
        "rubric_path":        rubric_rel,
        "rubric_sha256":      fsha(rubric_p),
        "canonical_id_registry_path":   str(registry_p),
        "canonical_id_registry_sha256": fsha(registry_p),
    },
    "authority_order": [
        "spec.md",
        "expected.json/rubric",
        "phase prompt",
        "model preference",
    ],
    "rounds": rounds,
    "accepted_invariants": accepted_invariants,
    "rejected_alternatives": [],
    "unresolved": [{"id": uid, "note": "dry-run stub: solo planner did not capture this oracle invariant"} for uid in unresolved_ids],
    "escalated_to_user": [],
    "model_stamps": {
        "claude": {"status": "sign", "blocked_ids": [], "signed_plan_sha256": "TODO",
                   "model": "claude-opus-4-7", "timestamp": "2026-04-29T18:30:00Z"},
        "codex":  {"status": "sign", "blocked_ids": [], "signed_plan_sha256": "TODO",
                   "model": "gpt-5.5",         "timestamp": "2026-04-29T18:31:00Z"},
    },
}
pre = copy.deepcopy(plan); pre["model_stamps"] = {}
pre_bytes = json.dumps(pre, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
sha = hashlib.sha256(pre_bytes).hexdigest()
plan["model_stamps"]["claude"]["signed_plan_sha256"] = sha
plan["model_stamps"]["codex"]["signed_plan_sha256"]  = sha
with open(plan_path, "w", encoding="utf-8") as f:
    json.dump(plan, f, indent=2, sort_keys=True, ensure_ascii=False); f.write("\n")
# Also emit per-model draft snapshots for the drafts/ subdir.
draft_dir = pathlib.Path(plan_path).parent.parent / "drafts"
draft_dir.mkdir(parents=True, exist_ok=True)
for who in ("claude", "codex"):
    drafts_path = draft_dir / f"{who}.json"
    with open(drafts_path, "w", encoding="utf-8") as f:
        json.dump({"model": who, "round": 1, "stub": True, "accepted_ids": accepted_ids},
                  f, indent=2, sort_keys=True, ensure_ascii=False); f.write("\n")
PYEOF

# ---------------------------------------------------------------------------
# Step 5 — lint solo + pair plans.
# ---------------------------------------------------------------------------
LINT_SOLO="$OUT_DIR/lint.solo.json"
LINT_PAIR="$OUT_DIR/lint.pair.json"

set +e
python3 benchmark/auto-resolve/scripts/pair-plan-lint.py \
  --plan "$SOLO_PLAN" \
  --registry "$REGISTRY_OUT" \
  --quiet > "$LINT_SOLO"
SOLO_EXIT=$?
python3 benchmark/auto-resolve/scripts/pair-plan-lint.py \
  --plan "$PAIR_PLAN" \
  --registry "$REGISTRY_OUT" \
  --quiet > "$LINT_PAIR"
PAIR_EXIT=$?
set -e

# ---------------------------------------------------------------------------
# Step 6 — compute verdict.
# ---------------------------------------------------------------------------
python3 - "$REGISTRY_OUT" "$SOLO_PLAN" "$PAIR_PLAN" "$LINT_SOLO" "$LINT_PAIR" \
         "$OUT_DIR/verdict.json" "$RUN_ID" "$BLIND_ALIAS" "$FIXTURE_BASENAME" \
         "$SOLO_EXIT" "$PAIR_EXIT" <<'PYEOF'
import json, sys, pathlib
registry_p, solo_p, pair_p, lint_solo_p, lint_pair_p, out_p, run_id, blind, fixture_id, solo_exit, pair_exit = sys.argv[1:12]
solo_exit = int(solo_exit); pair_exit = int(pair_exit)

reg = json.load(open(registry_p, "r", encoding="utf-8"))
solo = json.load(open(solo_p, "r", encoding="utf-8"))
pair = json.load(open(pair_p, "r", encoding="utf-8"))

total_ids = {e["id"] for e in reg["required_invariants"]}
solo_ids  = {a["id"] for a in solo["accepted_invariants"]}
pair_ids  = {a["id"] for a in pair["accepted_invariants"]}

# Caught = registry id appears in accepted_invariants.
solo_caught = total_ids & solo_ids
pair_caught = total_ids & pair_ids
lift = len(pair_caught) - len(solo_caught)

# Verdict policy (iter-0022 dry-run): advance if both lints PASS AND pair
# captures every required id AND lift > 0. abort otherwise.
verdict = "advance"
reasons = []
if solo_exit != 0:
    verdict = "abort"
    reasons.append("solo plan failed lint")
if pair_exit != 0:
    verdict = "abort"
    reasons.append("pair plan failed lint")
if pair_caught != total_ids:
    verdict = "abort"
    missing = sorted(total_ids - pair_caught)
    reasons.append(f"pair plan missing required ids: {missing[:5]}{'…' if len(missing)>5 else ''}")
if not reasons and lift <= 0:
    verdict = "abort"
    reasons.append("pair plan did not lift over solo (lift <= 0)")

if not reasons:
    reasons.append("pair plan covers every required invariant and lifts over solo")

verdict_doc = {
    "schema_version": "1",
    "run_id":  run_id,
    "fixture_id": fixture_id,
    "blind_alias": blind,
    "canonical_ids_total": len(total_ids),
    "solo_caught_count": len(solo_caught),
    "pair_caught_count": len(pair_caught),
    "pair_minus_solo_lift": lift,
    "solo_lint_exit": solo_exit,
    "pair_lint_exit": pair_exit,
    "verdict": verdict,
    "reason": "; ".join(reasons),
}

# Inline schema validation: required keys + types.
SCHEMA = {
    "schema_version": str,
    "run_id":  str,
    "fixture_id": str,
    "blind_alias": str,
    "canonical_ids_total": int,
    "solo_caught_count": int,
    "pair_caught_count": int,
    "pair_minus_solo_lift": int,
    "solo_lint_exit": int,
    "pair_lint_exit": int,
    "verdict": str,
    "reason": str,
}
problems = []
for k, t in SCHEMA.items():
    if k not in verdict_doc:
        problems.append(f"missing field {k}")
    elif not isinstance(verdict_doc[k], t):
        problems.append(f"field {k} expected {t.__name__} got {type(verdict_doc[k]).__name__}")
verdict_value = verdict_doc.get("verdict")
if verdict_value not in ("advance", "abort"):
    problems.append(f"verdict must be advance|abort, got {verdict_value!r}")
if problems:
    print("[pair-plan-preflight] verdict.json failed inline schema check:", problems, file=sys.stderr)
    sys.exit(70)

with open(out_p, "w", encoding="utf-8") as f:
    json.dump(verdict_doc, f, indent=2, sort_keys=True, ensure_ascii=False); f.write("\n")
print(json.dumps({k: verdict_doc[k] for k in ("verdict", "reason", "pair_minus_solo_lift", "canonical_ids_total")}))
PYEOF

echo "[pair-plan-preflight] done — verdict at $OUT_DIR/verdict.json"
