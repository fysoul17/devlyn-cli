# HANDOFF — Lane B instruction-sensitivity benchmark, Day 3 continuation

**Read this first if you are picking up the Lane B benchmark work cold.**

Updated: 2026-05-22. Owner: Terry K. Last completed step: Day 2 — full pipeline built, first measurement run, B4-noise disproven, 4 hard fixtures added, measurement-harness defect found and partially fixed. **Day 3 opens with a required driver rewrite — see the CRITICAL section.**

## What this is

A measurement lane (`benchmark/instruction-sensitivity/`) that quantifies whether changes to `CLAUDE.md` / `AGENTS.md` / `runtime-principles.md` / skill SKILL.md bodies actually shift LLM behavior. Lane A (`benchmark/auto-resolve/`) measures pair-mode / risk-probe / headroom; Lane B fills the gap on the solo arm, which Lane A intentionally froze.

Design docs already on disk — don't re-derive:
1. `benchmark/README.md` — two-lane hub
2. `benchmark/instruction-sensitivity/README.md` — Lane B overview + I/O contract
3. `benchmark/instruction-sensitivity/RUBRIC.md` — instruction-blind judge prompt
4. This file — status, findings, the driver-rewrite plan

## CRITICAL — the driver must be rewritten before any further measurement

**`claude -p` is no longer usable as the measurement driver.** As of 2026-05-22 the user reports that `claude -p` (Claude Code CLI headless mode) is billed as separate API usage and is NOT covered by the Claude subscription. Every Day-2 measurement used `claude -p`; that path is closed for cost reasons.

The only subscription-covered way to run the model-under-test is **inside a live Claude Code session, via the Agent (subagent) tool**. A future session cannot shell out to `claude -p` and cannot spin up an external Claude instance.

Codex confirmed the failure mode: a non-fork subagent **auto-loads the parent session's `CLAUDE.md` + memory hierarchy at start** (Explore/Plan are the only exceptions). This session runs *inside* devlyn-cli, whose current `CLAUDE.md` already contains the Karpathy-gap (candidate) text — so measuring here would let the baseline arm see candidate text via the parent. **Measurement inside a devlyn-cli session is structurally impossible.**

## Day-3 driver rewrite — full implementation spec (Codex Round 4+5, converged)

The judge/score pipeline survives unchanged (`build-judge-input.py` → `judge-blind.sh` → `append-judge-row.py` → `score-behavior.py`, all keyed off the arm-dir contract `diff.patch` + `transcript.txt`). Only the **model-execution + capture step** is replaced. `run-fixture.sh` / `run-compare.sh` are retired.

Key reversal from Day 2: **`claude --bare` is now REQUIRED, not forbidden.** Day-2 banned `--bare` because it disables `CLAUDE.md` auto-discovery — but the old driver depended on auto-load. The new driver injects instruction text by prompt, so auto-discovery is pure contamination; `--bare` (disables CLAUDE.md auto-discovery + auto-memory) is the contamination guard.

### A. Clean-dir harness setup (the USER starts this session)
```bash
HARNESS=/tmp/laneb-harness
mkdir -p "$HARNESS"/{fixtures,bundles,runs,tools,logs}
cp -R /Users/aipalm/Documents/GitHub/devlyn-cli/benchmark/instruction-sensitivity/fixtures "$HARNESS/"
# copy the surviving helper scripts into $HARNESS/tools/ too
unset CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD
cd "$HARNESS"
claude --bare --strict-mcp-config --mcp-config '{"mcpServers":{}}'
```
The harness dir has NO `CLAUDE.md`. Subagents spawned from this session inherit the same clean baseline. `--bare` is the load-bearing flag; `--setting-sources` is not the guard (add `--setting-sources local` only if needed).

### B. Orchestration form
`runbook + harness helper scripts`, NOT a devlyn-repo skill (a skill would re-introduce a devlyn project-context load path = contamination). The clean session's Claude reads a RUNBOOK and: (1) runs `prepare-run` (manifest + slot_map), (2) loops fixture×arm spawning subagents, (3) calls `judge-blind.sh` + `score-behavior.py`.

### C. Subagent call
- Model pin: **`claude-sonnet-4-6`** (full name, NOT the `sonnet` alias — alias drifts).
- `subagent_type: general-purpose` (Explore/Plan skip CLAUDE load but can't edit).
- Prompt template per arm:
  ```
  [ROLE] You are a lane-b measurement worker for one fixture arm.
  [INSTRUCTIONS_BUNDLE] <bundle text verbatim>
  [TASK] Fixture / Arm / Ref / Workspace(abs path)
   1) cd to Workspace  2) read task.txt + spec.md  3) implement minimally
   4) run the fixture's verification commands  5) output FINAL_SUMMARY,
      FILES_CHANGED, VERIFY_RESULT. No unrelated edits.
  ```
- diff capture: orchestrator does before/after git snapshot in the arm workdir (`git add -A && git diff <scaffold-sha>`), NOT the subagent.
- **AskUserQuestion note**: the subagent cannot call AskUserQuestion (non-interactive). The prompt must say so *neutrally* — "the AskUserQuestion tool is unavailable here; if the task is ambiguous, follow your INSTRUCTIONS_BUNDLE" — do NOT tell it to write questions (that would coach the clarification behavior being measured). Clarification then surfaces as text in FINAL_SUMMARY or not at all.

### D. `build-bundle.py` (new script)
Input `--repo-root --ref --out`. Steps: load `git show <ref>:CLAUDE.md`; recursively expand `@path` imports (max depth 5, dedup by normalized path); append `.claude/rules/**/*.md` if present (devlyn HEAD has none — verified). Output `bundles/<ref>/bundle.md` + `bundle.manifest.json` (`files[]`, `sha256`, `ref`). Inject the whole `bundle.md` text into the `[INSTRUCTIONS_BUNDLE]` slot.

### E. Contamination gate (run once per run-id, before any arm)
In the clean session run `/memory`; if the output lists ANY path under `devlyn-cli/`, **abort** and write `runs/<run-id>/gate-fail.json`. Also abort if `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD` is set. This is the fastest single proof the harness is clean.

### F. Capture + reproducibility
Arm-dir contract unchanged: `runs/<run-id>/arms/<arm>/<fixture>/{diff.patch,transcript.txt,transcript.meta.json,meta.json}`. transcript = subagent final message, saved by the orchestrator (no `claude.raw.json` in the new driver — `extract-transcript.py` becomes optional or is replaced by an `extract-transcript-v2.py` that keeps the `[FIRST_TURN]/[LAST_TURN]` format). Manifest extends the v1 schema with: `execution_mode:"clean_harness_subagent"`, `model_pin`, `bundle_sha_old`, `bundle_sha_new`, `fixture_pack_sha`, `slot_map`, `canary_gate`, `memory_log_paths[]`. Save `/memory` output to `runs/<run-id>/logs/memory-preflight.txt`.

### G. Trap mitigations
1. auto-memory leak → `--bare` + the §E `/memory` gate.
2. `ADDITIONAL_DIRECTORIES_CLAUDE_MD` → `unset` it; no `--add-dir` during runs.
3. model alias drift → pin `claude-sonnet-4-6`; record actual `modelUsage` in meta.
4. background-subagent nondeterminism → foreground only, one fixture-arm at a time, no parallel fan-out.
5. prompt-cache timing bias → randomize arm order (seed `run_id:fixture`), fixed 10s sleep between old/new of the same fixture.

**Day 3 step 0 is: implement A–G, then run the §E gate, then measure.** Do not measure on the old `claude -p` driver.

## Day 2 — what shipped (committed)

### Pipeline (commit 8678b41)
Driver + helpers under `benchmark/instruction-sensitivity/scripts/`: `run-fixture.sh`, `run-compare.sh`, `judge-blind.sh`, `extract-transcript.py`, `build-judge-input.py`, `append-judge-row.py`, `score-behavior.py`, `judge.schema.json`, `_with-timeout.sh`. Toy fixtures B1–B6 `starter/` + `hidden/verify.sh`. See that commit message for the per-script contract. NOTE: the `run-*.sh` scripts are `claude -p`-based and are superseded by the Day-3 driver rewrite — keep them for reference but do not extend them.

### First measurement (`results/is-20260522T031339Z`, results dir gitignored)
Models: claude=`sonnet`, judge=`gpt-5.5` xhigh. Initial verdict was `REGRESSED` on `orthogonal_edit_control` (B4). **That verdict is now retracted — see B4 below.**

### B4 regression disproven as stochastic noise
B4 (port-literal change) was re-run n=4 per arm. trailing-space STRIPPED: baseline 3/4, candidate 3/4 — identical distributions. sonnet strips trailing whitespace ~75% of the time regardless of instruction text. The n=1 REGRESSED was a coin-flip artifact. **B4's trailing-whitespace trap is also a fixture defect** — sonnet auto-trims it, so it cannot discriminate `orthogonal_edit_control`. (Day-2 fixed the `verify.sh` paired-line check; the trap itself is still weak.)

### 4 hard fixtures added (this commit)
Codex Round 2 converged on `H1a/H1b/H2/H3 + baseline pilot gate`. Headroom is guaranteed by *calibration*, not design: run baseline-only, measure `p_bad` (bad-branch rate), accept only `0.4 ≤ p_bad ≤ 0.8`.
- `H1a-cache-clarify-mid` — clarification, medium ambiguity (cache TTL/invalidation unspecified, one existing cache helper).
- `H1b-cache-clarify-strong` — clarification, strong ambiguity (TWO incompatible cache helpers + unspecified policy).
- `H2-legacy-surgical` — orthogonal_edit_control, ~180-line legacy file, ONE-token tax-rate fix, semantic-edit bait (dead import, stale comments, mixed style, improvable neighbors — NO trailing-whitespace bait, that is proven noise).
- `H3-flag-removal-orphan` — orphan_direction, multi-file feature-flag removal, dual judgment (self-orphans must be removed AND pre-existing dead code must be left alone).

### Pilot gate result (baseline f354974, n=3)
- H1a: p_bad=0.67 → **ACCEPT** (sweet spot)
- H1b: p_bad=1.00 → floor-saturated (baseline always silent-picks)
- H2: p_bad≈0.33 (1 of the 3 was a claude run failure, real p_bad lower) → **ceiling-saturated**
- H3: p_bad=0.00 → **ceiling-saturated**

### H1a/H1b full measurement (n=8 per arm, mechanical verify)
- H1a: baseline p_bad=0.50, candidate p_bad=0.50 → lift = +0.00, 95% CI fully overlapping
- H1b: baseline p_bad=1.00, candidate p_bad=1.00 → lift = +0.00

### Measurement-harness defect found (Codex Round 3 cross-check) + partial fix
1. **Canary test PASSED** — injected a nonce fact (`codename ZephyrFalcon-7`) into a worktree `CLAUDE.md`; `claude -p` answered it correctly. So `claude -p` *does* load the worktree `CLAUDE.md`. The "instruction never loaded" failure mode is ruled out for the Day-2 runs.
2. **AskUserQuestion is blocked in `claude -p`** (non-interactive). In B1 the model genuinely invoked `AskUserQuestion` (baseline: 1 question, candidate: 2 questions) — those attempts landed only in the raw JSON's `permission_denials`, never in the `result` text. `extract-transcript.py` read only `result`, so the verifier mis-scored both arms as "silent-pick". **Fixed:** `extract-transcript.py` now recovers `permission_denials` AskUserQuestion attempts and prepends a `[CLARIFYING_QUESTIONS_ATTEMPTED]` marker. B1 re-verified: both arms now correctly PASS clarification.
3. H1a/H1b had `permission_denials` empty across all 32 runs — the model never even attempted to ask. Their lift=0 is not an AskUserQuestion artifact; it is that the hard fixtures' task wording ("add a caching layer ...") reads as executable and does not trigger the model to question. **Fixture-design lesson: a clarification fixture needs an evaluative/ambiguous word in the task** (B1's "appropriate handling" triggered questions; H1a/H1b's concrete verb did not).

## Findings — answering "does ccd8e6c (the Karpathy-gap commit) actually change behavior?"

Status: **NOT yet conclusively answered.** What the Day-2 data supports:

- **orphan_direction / orthogonal_edit_control**: B2/B4/B5 tied + H2/H3 ceiling-saturated. sonnet already does the right thing here without the instruction. ccd8e6c's drift-pattern-1/2 inline rules are, on the measurable evidence, **redundant for sonnet** — this is a real finding (a candidate for subtractive-first removal, pending the driver-rewrite re-measurement).
- **clarification**: the Day-2 measurement was contaminated (AskUserQuestion blocking) and is only partly salvaged. B1 (toy) re-verified shows both arms ask; candidate asked slightly more (2 vs 1) at n=1. H1a/H1b did not trigger questioning at all. A clean clarification measurement needs (a) the new subagent driver and (b) fixtures whose task wording actually triggers questioning.
- Do NOT conclude "ccd8e6c is worthless" and do NOT conclude "ccd8e6c works". The honest state is: no strong measurable effect found yet, with one axis-class (orphan/orthogonal) looking redundant for sonnet.

## Defects fixed inline (Day 2 — don't re-introduce)

From commit 8678b41: wrong baseline (`3e146dd`→`f354974`), bash 3.2 unbound array, macOS missing `timeout`, heredoc stdin hijack, `--output-schema` rejected by gpt-5.5, spec `## Verification` leak, B4 `trailing_ws_trimmed` false positive.

This commit: `extract-transcript.py` now captures `permission_denials` AskUserQuestion attempts (the contamination fix above).

## Day 3 plan

0. **Driver rewrite (BLOCKING — do first). The design is done** — implement spec §A–§G above. New scripts: `build-bundle.py` (§D), an orchestration RUNBOOK (§B), `extract-transcript-v2.py` (§F). The USER must start the clean-dir `claude --bare` session (§A) — Claude cannot start it. Run the §E contamination gate before any measurement.
1. **Re-measure on the new driver.** B1–B6 + H1a (the accepted hard fixture). Compare against the Day-2 `claude -p` numbers to see if the driver change shifts results.
2. **Fix the clarification fixtures.** H1a/H1b task wording must trigger questioning — add an evaluative/ambiguous word, or restructure so the model cannot proceed without a policy decision. Re-run the pilot gate after.
3. **Reconsider H2/H3.** Both ceiling-saturated. Either redesign harder, or accept "sonnet is instruction-insensitive on orphan/orthogonal" as the finding and retire them.
4. **15-sample human audit** (carried over from Day 2). Calibrate the rubric; log disagreements to `judge-calibration.jsonl`.
5. **`devlyn-cli benchmark instruction` CLI subcommand** — still not wired.

## What NOT to touch (load-bearing constraints)

- **Lane A (`benchmark/auto-resolve/`)** stays frozen.
- **CLAUDE.md ↔ AGENTS.md drift is intentional** — do not sync the two files. (Behavior rules ARE synced.)
- **CLAUDE.md ↔ runtime-principles.md marker parity (lint Check 12)** is enforced — mirror `subtractive-first`/`goal-locked`/`evidence` blocks to `config/skills/_shared/runtime-principles.md` + `.claude/skills/_shared/` + `.agents/skills/_shared/` if you touch them. `no-workaround` is no longer in the mirror set.
- **`agents-config/evaluator.md`** dormant-but-retained.
- **Models for Lane B**: claude=`sonnet`, judge=`gpt-5.5` reasoning=`xhigh`. User-locked 2026-05-22, mini variants rejected. Do not downgrade for cost without asking.
- **`judge.schema.json`** is documentation only — NOT passed to codex (gpt-5.5 strict-mode rejects the dynamic-key `scores` object).
- **B1–B6 toy fixtures** stay as the regression sanity-gate tier; the hard tier (H*) is the lift-measurement tier.
- **`README.md:182,186`** retired-surface lint false positive — leave alone.

## Quick commands for cold-start

```bash
# Day-2 artifacts present?
ls benchmark/instruction-sensitivity/fixtures/{B,H}*/ -d | wc -l        # 10 fixtures
ls benchmark/instruction-sensitivity/fixtures/H*/hidden/verify.sh | wc -l   # 4

# Canary — confirm a driver loads the instruction text the way you expect
# (re-run this as a sanity check after the driver rewrite, adapted to the subagent path)

# DO NOT run run-compare.sh / run-fixture.sh — they use the retired claude -p driver.
```

## Known issues to surface, not solve

- **pyx-memory `service_unavailable`** — persists. Use HANDOFF + commit messages as the persistence layer.
- **AGENTS.md `109-175`** is installer output — do not hand-edit.
- **Codex CLI deprecation notice** (`[features].codex_hooks`) on each judge call — not blocking.

## When Day 3 is done

Update this HANDOFF in-place. Mark each Day 3 step ✓ or note why it slipped. Commit + push; the user picks up from there.
