# HANDOFF — Lane B instruction-sensitivity benchmark, Day 3 continuation

**Read this first if you are picking up the Lane B benchmark work cold.**

Updated: 2026-05-22. Owner: Terry K. Last completed step: **Day 3 step 0 — driver rewrite IMPLEMENTED** (3 new scripts + RUNBOOK.md, Codex-reviewed REWORK→SHIP). Next: the USER starts the clean `claude --bare` session and runs the measurement per `benchmark/instruction-sensitivity/RUNBOOK.md`.

## What this is

A measurement lane (`benchmark/instruction-sensitivity/`) that quantifies whether changes to `CLAUDE.md` / `AGENTS.md` / `runtime-principles.md` / skill SKILL.md bodies actually shift LLM behavior. Lane A (`benchmark/auto-resolve/`) measures pair-mode / risk-probe / headroom; Lane B fills the gap on the solo arm, which Lane A intentionally froze.

Design docs already on disk — don't re-derive:
1. `benchmark/README.md` — two-lane hub
2. `benchmark/instruction-sensitivity/README.md` — Lane B overview + I/O contract
3. `benchmark/instruction-sensitivity/RUBRIC.md` — instruction-blind judge prompt
4. `benchmark/instruction-sensitivity/RUNBOOK.md` — **authoritative Day-3 driver operations doc** (§A setup → §E judge/score)
5. This file — status, findings, the driver-rewrite record

## Day-3 driver — REWRITTEN (step 0 done)

`claude -p` is retired as the driver — it is billed as separate API usage, not
subscription-covered, and every Day-2 measurement used it. The model under test
now runs as an **Agent (subagent)** spawned from a clean, isolated `claude
--bare` session whose harness directory has no `CLAUDE.md`; instruction text
reaches each arm only via a bundle injected by prompt. (Measuring inside a
devlyn-cli session is structurally impossible: a non-fork subagent auto-loads
the parent's `CLAUDE.md`, so the baseline arm would see candidate text.)

**On disk now** — `benchmark/instruction-sensitivity/`:
- `RUNBOOK.md` — **authoritative** operations doc (USER setup → judge/score). Read it, don't re-derive from §A–§G.
- `scripts/build-bundle.py` — ref → instruction bundle (`bundle.md` + manifest).
- `scripts/prepare-run.py` — bundles + slot_map + workspace scaffolding + fail-closed gate → v2 manifest.
- `scripts/capture-arm.py` — post-subagent capture (diff/transcript/meta + detector + hidden-verify).
- `extract-transcript.py` + `run-fixture.sh` + `run-compare.sh` are the retired `claude -p` driver — kept for reference, do not extend.
- The judge/score pipeline (`build-judge-input.py` → `judge-blind.sh` → `append-judge-row.py` → `score-behavior.py`) is UNCHANGED and works in the harness because the harness mirrors the repo's `benchmark/instruction-sensitivity/` path layout.

**Deviations from the converged §A–§G spec** (RUNBOOK.md supersedes §A–§G):
1. Harness MIRRORS the `benchmark/instruction-sensitivity/` tree (not §A's flat `$HARNESS/{...}`) — the unchanged judge scripts resolve repo-root via `parents[3]`; a flat layout breaks fixture resolution.
2. `build-bundle.py` runs in USER setup, not the clean session — keeps the clean session 100% devlyn-isolated.
3. No `extract-transcript-v2.py` — transcript = subagent final message verbatim, written by `capture-arm.py`; `[FIRST_TURN]/[LAST_TURN]` markers dropped (a `claude -p` multi-turn artifact).
4. `prepare-run.py` scaffolds all fixture-arm workspaces up front.
5. Model pin: the parent session is launched `--model claude-sonnet-4-6` and Agent calls OMIT `model` so subagents inherit it — the Agent tool's `model` param is an alias-only enum and cannot take the full ID. RUNBOOK §C adds a parent-model self-check gate.
6. `exec_order` randomization uses an independent seed (`run_id:fixture:exec`), decoupled from the A/B judge-slot seed.
7. `build-bundle.py` FAIL-CLOSES on any `@import` that resolves at the ref (inline expansion unimplemented) instead of recursive append — both real refs have zero resolvable imports, so `bundle.md` == `CLAUDE.md` verbatim.
8. Workspaces are opaque OS-temp git repos outside the harness tree (no arm identity in the path; manifest/other-bundle unreachable by walking up). Subagent prompt uses neutral wording — no "implement minimally" (would coach the `anti_overengineering` axis).

**Codex review**: Round 1 → REWORK (2 CRITICAL — arm identity leaked via workspace path; subagent could walk up to the manifest and read both bundles — plus 4 HIGH/MED/LOW). All 6 fixed (deviations 7+8 above). Round 2 → **SHIP**.

**Day 3 step 0 is DONE.** Next: the USER starts the clean `claude --bare` session and runs the measurement per RUNBOOK.md. Do not measure on the old `claude -p` driver.

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

0. ✓ **Driver rewrite — DONE.** 3 scripts + RUNBOOK.md on disk, self-tested, Codex REWORK→SHIP. See the "Day-3 driver — REWRITTEN" section above.
1. **Re-measure on the new driver.** USER starts the clean `claude --bare` session and follows RUNBOOK.md: B1–B6 + H1a (the accepted hard fixture). Compare against the Day-2 `claude -p` numbers to see if the driver change shifts results.
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

# Day-3 measurement is driven by RUNBOOK.md §A onward — start there, not here.
# DO NOT run run-compare.sh / run-fixture.sh — retired claude -p driver.
```

## Known issues to surface, not solve

- **pyx-memory `service_unavailable`** — persists. Use HANDOFF + commit messages as the persistence layer.
- **AGENTS.md `109-175`** is installer output — do not hand-edit.
- **Codex CLI deprecation notice** (`[features].codex_hooks`) on each judge call — not blocking.

## When Day 3 is done

Update this HANDOFF in-place. Mark each Day 3 step ✓ or note why it slipped. Commit + push; the user picks up from there.
