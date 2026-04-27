# PROPOSAL — CLAUDE.md install-time identity + minimization audit

**Status**: PROPOSED 2026-04-28. Not yet numbered (will become iter-0020 / iter-0020.5 / iter-0021 depending on whether iter-0019 finishes first and what its verdict surfaces).
**Trigger**: AFTER iter-0019 paid 5-fixture smoke completes and L1-claude data is in.
**Prerequisite**: do NOT bundle with iter-0020 pair-policy work. Codex R3 attribution-clarity rule — change one variable per iter when measurement matters.

## Why this is load-bearing

CLAUDE.md is the **single document loaded at session start for every Claude Code invocation in this repo**. It shapes every modal interaction:
1. **modal: `/devlyn:auto-resolve`** — runs, walks away. Doesn't need iteration-loop meta-rules.
2. **secondary: `/devlyn:ideate`, `/devlyn:preflight`** — skill internals not load-bearing for users.
3. **occasional: `/devlyn:resolve`, `/devlyn:review`, `/devlyn:clean`, plain prompting, single-task work**. CLAUDE.md is global background — every short interaction pays its context cost.

Two coupled concerns:

### (1) Install-time identity (load-bearing for benchmark validity)

The benchmark variant arm uses `$REPO_ROOT/CLAUDE.md` (per `run-fixture.sh:71`: `cp "$REPO_ROOT/CLAUDE.md" "$WORK_DIR/CLAUDE.md"`). The end-user install path uses `bin/devlyn.js:568-572`:

```
const claudeMdSrc = path.join(__dirname, '..', 'CLAUDE.md');
const claudeMdDest = path.join(process.cwd(), 'CLAUDE.md');
if (fs.existsSync(claudeMdSrc)) {
  fs.copyFileSync(claudeMdSrc, claudeMdDest);
  log('  → CLAUDE.md', 'dim');
}
```

For benchmark variant scores to predict end-user experience, **the shipped package's CLAUDE.md must be byte-identical to the repo CLAUDE.md**. Otherwise we measure something the user does not run.

**Current state baseline (2026-04-28, captured before any change)**:
- `<repo>/CLAUDE.md` SHA256: `c1a45872426a519dd4fcce84f402410418c27603c9ab954fd3f54ac32114e3ea`
- Line count: 137
- `package.json:9-32 files[]` includes `"CLAUDE.md"` ✓ (npm pack will include it)
- `bin/devlyn.js:568` reads `path.join(__dirname, '..', 'CLAUDE.md')` ✓ (same file, no transform)
- No tooling enforces continued identity between commits

**Verification action items**:
- [ ] Run `npx pack --dry-run` and confirm CLAUDE.md is in the tarball.
- [ ] In a temp dir, run `npx devlyn-cli` and `diff <repo>/CLAUDE.md $temp/CLAUDE.md` — must be silent.
- [ ] Add lint Check 11: `shasum -a 256 CLAUDE.md` recorded in a tracked baseline file; lint compares + fails if drift without explicit baseline update.
- [ ] CI step: on release, fail if package CLAUDE.md ≠ repo CLAUDE.md.

### (2) Minimization opportunity (context pollution)

Current CLAUDE.md (137 lines) covers:

| Section | Universal? | Notes |
|---|---|---|
| Outer goal block + L0/L1/L2 + 5+1 principles | ✅ KEEP | Universal — every Claude session inherits these |
| Quick Start (auto-resolve / ideate / preflight) | ⚠️ TRIM | List 3 commands but cut the Karpathy-flavored prose; let the SKILL.md docs carry detail |
| Karpathy Principles (Karpathy 4) | ✅ KEEP | Universal "Think/Simplicity/Surgical/Goal-driven" — applies to every edit |
| Error Handling Philosophy + No-silent-fallback | ✅ KEEP | Universal — applies to single-prompt code edits too |
| Codex invocation | ⚠️ MOVE | Not universal — only matters when a skill spawns Codex. Move to `config/skills/_shared/codex-config.md` (already exists; pointer here) |
| Codex companion pair-review | ❌ REMOVE | Iteration-loop concern, NOT runtime. Move entirely to `autoresearch/PRINCIPLES.md` or `HANDOFF.md`. End users running `/devlyn:auto-resolve` don't need this |
| Working Mode (TaskCreate, disk persistence, fan-out) | ⚠️ TRIM | Some universal (TaskCreate for non-trivial work), some skill-specific (`.devlyn/runs/<run_id>/`). Split |
| Skill Boundary Policy (auto-resolve standalone delegation rules) | ❌ REMOVE | auto-resolve internals. Belongs in `config/skills/devlyn:auto-resolve/SKILL.md` (already partially there) |
| Native Claude Code Skills (security-review, simplify) | ❌ REMOVE | auto-resolve internals — same as above |
| Bare-Case Guardrail | ❌ REMOVE | autoresearch-loop concern. Move to `autoresearch/PRINCIPLES.md` (it's principle #6 layer-cost-justified) |
| No-Workaround Bar | ✅ KEEP | Restates principle #3 in run-time language; load-bearing for plain coding too |
| Communication Style | ✅ KEEP | Universal — applies to every interaction |
| Commit Conventions | ✅ KEEP (pointer-only) | Universal — but only the pointer line, not duplicated content |
| Design System | ✅ KEEP (pointer-only) | Universal but conditional ("if exists") |

**Estimated post-prune size**: 60-80 lines (vs current 137). ~50% reduction.

**Lazy-load principle**: skill-specific guidance lives in `config/skills/<skill>/SKILL.md` and reference docs; CLAUDE.md becomes the universal background only. Skills load their own context when invoked.

## A/B falsification gate (mandatory)

Even small CLAUDE.md changes shift benchmark numbers (user-stated invariant). Therefore:

1. **Land iter-0019 + iter-0020 (pair policy) FIRST** so the L1 data baseline is calibrated under current CLAUDE.md.
2. **Branch off, prune CLAUDE.md** per the table above.
3. **Re-run iter-0019 smoke** (F1+F2+F4+F6+F9 × {variant, solo_claude, bare}) under pruned CLAUDE.md.
4. **Ship only if**:
   - L0 (bare) margins move within ±2 of pre-prune (CLAUDE.md doesn't materially affect bare arm — but verify).
   - L1 / L2 margins do not regress on any fixture by ≥5.
   - F9 (novice flow) margin holds ≥+5.
   - No new variant disqualifier emerges.
5. **Revert if any of the above fails**, with the failed-prune iteration file documenting which removed section was load-bearing — that section moves to a "must-not-prune" lock list in PRINCIPLES.md.

## Codex GPT-5.5 deep collaboration plan

User direction: deep Codex pair-review on this. Plan:
- **R0**: send Codex the full current CLAUDE.md + the section-by-section table above + the iter-0019 verdict data. Ask for: (a) which sections he agrees are removable, (b) which "removable" picks he pushes back on with specific failure-mode scenarios, (c) a single A/B falsification design (one branch, one paid run) vs multi-pass (prune-test-prune-test) trade-off, (d) any extraction we missed (sections he'd KEEP that we marked REMOVE / vice versa).
- **R1**: pre-edit critique on the actual diff after we draft it.
- **R2**: post-paid-run verdict synthesis. If pair (Codex + Claude) agree the prune is safe, ship. If disagreement, escalate to user with both views (per `feedback_user_directions_vs_debate.md` rule).

## Open questions to resolve before iter starts

1. **Where does "Codex companion pair-review" land?** It's iteration-loop content but currently in CLAUDE.md so a session continuing the loop can find it. Two options:
   - Move to `autoresearch/PRINCIPLES.md` (the iteration-loop is supposed to read PRINCIPLES.md first anyway)
   - Move to `autoresearch/HANDOFF.md` "Codex collaboration log" header
   Codex R0 picks.
2. **Bare-Case Guardrail wording**: it's currently in CLAUDE.md as a runtime rule but it's actually an autoresearch invariant. Move to PRINCIPLES.md #6 expansion?
3. **5+1 principles**: keep all 6 enumerated in CLAUDE.md (current state), or just first-line summary + pointer to PRINCIPLES.md? The 6 short bullets are the user's anchor — losing them breaks "fresh session knows the rules without opening another file." Default: keep enumerated, prune everything else around them.
4. **Quick Start trim depth**: keep the 3-command table (modal user value) but drop the Karpathy-philosophical prose around it. Aim: 8 lines including the table.

## Watch list (do not regress)

These behaviors must not change post-prune:
- A fresh Claude Code session in this repo knows the L0/L1/L2 contract without opening NORTH-STAR.md.
- A fresh session knows the 6 principles by name (so user "no overengineering" instruction maps to the right principle).
- A fresh session knows the no-silent-fallback rule (universal coding contract).
- Plain coding sessions (no skill invoked) inherit the same scope-discipline + error-handling discipline that variant arm enforces.

## Why this is queued, not done now

iter-0019 paid run is in flight as of 2026-04-28 (PID 93465, RUN_ID `20260427T155638Z-c08130f-iter-0019-smoke`). The L1 data this audit needs as the calibration baseline arrives only when that completes. Touching CLAUDE.md mid-run would invalidate iter-0019's variant-arm data (it reads `$REPO_ROOT/CLAUDE.md` and any change applies to all subsequent fixtures).
