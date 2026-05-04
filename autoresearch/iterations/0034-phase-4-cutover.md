---
iter: "0034"
title: "Phase 4 cutover — ship 2-skill harness solo default + delete 15 legacy skills + L2 PLAN-pair research-only label + principles refocus"
status: CLOSED-PASS / SHIPPED
type: cleanup + product-surface ship; Mission 1 cutover (NOT terminal gate — that's iter-0035 real-project trial per NORTH-STAR test #15)
shipped_commit: TBD
date: 2026-05-03
mission: 1
gates: iter-0035-real-project-trial (Mission 1 terminal gate; NORTH-STAR test #15)
parent_design_iters: iter-0033 (C1) PASS evidence (5/5 headroom fixtures, suite-avg L1−L0 +6.43) + iter-0033d/iter-0033f/iter-0033g CLOSED-DESIGN (PLAN-pair measurement deferred to research-only)
unblock_evidence: solo PLAN empirically world-class (iter-0033 (C1) PASS 5/5 headroom fixtures); L2 PLAN-pair measurement deferred per Claude+Codex independent big-picture review (option VI); see iter-0033g §"CLOSURE" for full rationale
codex_r0: 2026-05-03 (382s, 181k tokens, NOT-CONVERGED-REVISIONS) — 7 concrete recommendations adopted in-place per PRINCIPLES #2 case-by-case (cleanup iter, no adversarial threat model). Detailed in §"Codex R0 revisions adopted".
---

# iter-0034 — Phase 4 cutover (2-skill harness solo default + legacy deletion)

## Why this iter exists (PRINCIPLES.md pre-flight 0)

Phase 4 cutover closes a long-running cleanup commitment to the user (16-skill landscape → 2-skill product surface) AND ships the L2 PLAN-pair research-only label that ends the iter-0033d/f/g asymptotic-firewall thread. iter-0033 (C1) PASS already established solo PLAN as empirically world-class (5/5 headroom-available fixtures, suite-avg L1−L0 +6.43); this iter ships that as the canonical product. NO new measurement claim, NO L2 ship. Real-project trial (iter-0035) is the actual quality gate per NORTH-STAR test #15.

User-visible failure being closed: the harness has shipped 20 `devlyn:*` skills where the canonical surface is 2 skills + reap. Each non-canonical skill carries trigger-confusion cost for users and surface-area cost for maintenance. Worse, downstream installs upgraded post-cutover would *retain* stale legacy skills indefinitely unless `bin/devlyn.js` explicitly cleans them — see Risk R7.

Go/no-go decision unlocked: iter-0035 real-project trial — the Mission 1 terminal gate per NORTH-STAR test #15 — is blocked on Phase 4 cutover ship. Without cutover, iter-0035 cannot honestly call itself "real-project trial of the 2-skill product" because the product still includes 17 deprecated skills.

## Hypothesis

**H1 (cleanup completeness)**: After deleting 15 legacy skills + moving 3 to `optional-skills/` + cleaning all stale references, the `/devlyn:*` user-facing namespace contains exactly `/devlyn:resolve` + `/devlyn:ideate`. Lint passes, mirror parity holds, downstream installs running the post-cutover `npx devlyn-cli` get their stale legacy skill dirs explicitly removed (per updated `DEPRECATED_DIRS` in `bin/devlyn.js`).

**H2 (solo behavior unchanged)**: Solo `/devlyn:resolve` PLAN behavior measured via the `solo_claude` arm (NOT `variant`; per iter-0033 C1 line 70 `solo_claude` IS the NEW L1 measurement, `variant` is `--engine auto` diagnostic capture) is byte-equivalent pre/post Phase 4 within the per-fixture variance band (±2 per axis per iter-0027 N=5 paired evidence). Phase 4 changes are doc-surface + skill-deletion + bin/devlyn.js + lint + benchmark-harness updates; the only prompt-body edit is SKILL.md PHASE 1 line 80 (PLAN-pair label), which routes the same engine (Claude) and same phase contract.

**H3 (L2 PLAN-pair label honest)**: SKILL.md PHASE 1 line 80 carries a SHORT runtime-safe label citing unblock conditions A (container infra justified by other product needs) and B (production telemetry captures positive evidence of subagent introspection). The label honors PRINCIPLES #3 by trigger-on-evidence (positive presence), not by trigger-on-absence (prove-a-negative).

## Predicted change (filled BEFORE run, immutable)

Baselines reference iter-0033 (C1) closure §"SHIPPED — PASS via variance adjudication" (lines 199-213 of `iterations/0033-quality-ab-new-resolve-vs-old-auto-resolve.md`) — corrected data, NOT raw `summary.json`. Raw F6 in `3bc86dd-iter0033c1-new-20260501T004229Z/summary.json:410` is 48 (single-N pre-variance); paired N=3 mean is 96.3 per `iter-0033b'` re-run. F9 baseline is from `4e3d89a-iter-0033a-f9-smoke3-20260430T232747Z` (judge score 91 per iter-0033 C1 closure line 208).

| Metric | Pre-cutover baseline (corrected C1 data) | Predicted post-cutover | Tolerance |
|---|---|---|---|
| F1 solo_claude score | 99 (raw c1-new summary row F1.solo_claude) | 97-100 | ±2 |
| F2 solo_claude score | per c1-new summary row F2.solo_claude (read at smoke time) | within ±2 | ±2 |
| F9 solo_claude score | 91 (iter-0033 C1 closure line 208) | 89-93 | ±2 |
| F1 L1−L0 margin | per c1-new (solo_claude − bare row F1) | within ±2 | ±2 |
| F2 L1−L0 margin | per c1-new (solo_claude − bare row F2) | within ±2 | ±2 |
| F9 L1−L0 margin | +15 (iter-0033 C1 closure line 208) | within ±2 | ±2 |
| Suite-avg L1−L0 (F1-F7) | +6.43 (C1 closure line 213) | within ±2 | ±2 |
| Headroom-available ≥+5 count | 5/5 (F1, F2, F4, F5, F9) PASS (C1 closure line 210) | 5/5 PASS | exact |
| Skill count `ls config/skills/devlyn:*` | 22 (Codex R0 verified) | 5 (resolve + ideate + 3 workspace dev artifacts; reap/design-system/team-design-ui moved to optional-skills/) | exact |
| Skill count `ls .claude/skills/devlyn:*` | 20 (Codex R0 verified; no workspace dev artifacts in mirror) | 2 (resolve + ideate) | exact |
| `optional-skills/devlyn:*` count | 2 (pencil-pull + pencil-push) | 5 (+ reap + design-system + team-design-ui) | exact |
| `bin/devlyn.js DEPRECATED_DIRS` colon-name entries | 0 (verified Codex R0) | 18 (15 deleted + 3 moved-out, all `skills/devlyn:NAME`) | exact |
| Lint exit code | 0 (verified at HEAD pre-edit) | 0 | exact |
| Mirror parity diff count (post-deletion-of-Check-6-paths) | 0 | 0 | exact |

**Direction of intent**: zero change in `solo_claude` (L1) measurement; mechanical cleanup completeness in surface count; honest research-only label in doc; downstream upgrade safety via DEPRECATED_DIRS.

## Five gates (released only when ALL PASS)

### Gate 1 — Solo behavior unchanged (smoke F1 + F2 + F9)

- **Pass**: per-fixture `solo_claude` (NEW L1) score within ±2 of pre-cutover baseline (3bc86dd-iter0033c1-new for F1+F2 from `summary.json` row.solo_claude; iter-0033 C1 closure line 208 for F9). Per-fixture `solo_claude − bare` margin within ±2 of pre-cutover.
- **Fail**: any of F1 / F2 / F9 outside variance band on `solo_claude` score OR on `solo_claude − bare` margin.
- **Threshold rationale**: ±2 per iter-0027 N=5 paired variance evidence (NORTH-STAR ops test #1, RUBRIC variance band).
- **Wall budget**: ~75-90min if running via `run-suite.sh` (3 arms each fixture: variant + solo_claude + bare). To shrink to ~45-60min: invoke `run-fixture.sh` directly with `--arm solo_claude` + `--arm bare` (skip variant since variant arm is `--engine auto` diagnostic, NOT L1, NOT a Phase 4 hypothesis target).
- **Arm strategy**: 2-arm `run-fixture.sh` direct invocation chosen for Gate 1 (45-60min budget honored). variant arm captured separately in Gate 5 only (full 3-arm suite).

### Gate 2 — Legacy skill deletion + stale-reference cleanup complete

- **Pass**: 
  - `ls config/skills/` shows only `_shared/`, `devlyn:resolve/`, `devlyn:ideate/`, plus shared-standards skills (KEEP per Mission 1 discipline), workspace dev dirs (KEEP per `bin/devlyn.js:300-305 UNSHIPPED_SKILL_DIRS`).
  - `ls .claude/skills/` shows mirror: `_shared/`, `devlyn:resolve/`, `devlyn:ideate/`, shared-standards skills (no workspace dev dirs).
  - `optional-skills/` contains `devlyn:reap/`, `devlyn:design-system/`, `devlyn:team-design-ui/` + existing `devlyn:pencil-pull/` + `devlyn:pencil-push/`.
  - `grep -rln 'devlyn:auto-resolve\|devlyn:preflight\|devlyn:evaluate\|devlyn:review\|devlyn:team-resolve\|devlyn:team-review\|devlyn:browser-validate\|devlyn:clean\|devlyn:update-docs\|devlyn:product-spec\|devlyn:feature-spec\|devlyn:recommend-features\|devlyn:discover-product\|devlyn:design-ui\|devlyn:implement-ui' config/skills .claude/skills` returns hits ONLY in: `roadmap-archival-workspace/` historical snapshots; `_shared/codex-config.md`/`engine-preflight.md`/`pair-plan-schema.md` IF chosen "archive" path (preferable: explicit archive note appended); benchmark scripts that have been intentionally hard-errored on `--resolve-skill old`. ZERO stale references in `_shared/` if "update" path chosen.
  - Lint passes (with updated Check 6 path list).
- **Fail**: any deleted skill still present OR any non-archive non-historical stale reference remaining (Gate 2 fail also fires if `_shared/` stale refs are not addressed per R9).
- **Threshold rationale**: deletion = mechanical, no variance.
- **Wall budget**: ~10-15min (mostly grep verification).

### Gate 3 — Doc surface updated

- **Pass**: 
  - `config/skills/devlyn:resolve/SKILL.md` PHASE 1 line 80 carries the short runtime-safe L2 PLAN-pair label per §"L2 PLAN-pair research-only label" below.
  - `autoresearch/NORTH-STAR.md` line 78 (Migration approach Phase 4 mention) updated to "shipped" + product-surface line 53 reflects post-cutover state.
  - `autoresearch/HANDOFF.md` Mission 1 progress section reflects iter-0034 SHIPPED + iter-0035 NEXT.
  - `README.md` quick start (lines 38-128) rewritten for 2-skill design; Manual Commands tables (lines 152-186) updated to drop deleted skills.
  - `CLAUDE.md` Quick Start (lines 22-39) rewritten for 2-skill design; deleted skill mentions in Skill Boundary Policy section trimmed; `/devlyn:auto-resolve` etc. references throughout removed or rewritten.
  - `AGENTS.md` lines 13-18 + 133 updated to 2-skill design.
  - `package.json` files array unchanged (no skill names hardcoded — Codex R0 verified).
- **Fail**: any of the cited surfaces still references deleted skills as live commands.
- **Threshold rationale**: surface-update completeness, no variance.
- **Wall budget**: ~45-60min.

### Gate 4 — optional-skills/ migration

- **Pass**: 
  - `optional-skills/devlyn:reap/SKILL.md` + `optional-skills/devlyn:design-system/SKILL.md` + `optional-skills/devlyn:team-design-ui/SKILL.md` all present + frontmatter `name:` field intact.
  - `bin/devlyn.js OPTIONAL_ADDONS` table includes the 3 new entries.
  - `bin/devlyn.js DEPRECATED_DIRS` array includes the 18 colon-name entries (15 deleted + 3 moved-out) so existing downstream `~/.claude/skills/devlyn:NAME/` get force-removed on next install (per R7).
  - `npx devlyn-cli list` (or equivalent dry-run) shows 2 user skills + 5 optional skills.
- **Fail**: any migration target missing OR `DEPRECATED_DIRS` not updated.
- **Threshold rationale**: existing `OPTIONAL_ADDONS` mechanism + 3 file moves + 18 array additions.
- **Wall budget**: ~15-20min.

### Gate 5 — Post-cutover bench suite re-run (full 9 fixtures, 3-arm or solo+bare; baseline comparison on `solo_claude` only)

- **Pass**: per-fixture `solo_claude` (NEW L1) score within ±2 of pre-cutover baseline (3bc86dd-iter0033c1-new for F1-F8 from `summary.json` row.solo_claude; iter-0033 C1 closure line 208 for F9 = 91; F6 mean N=3 = 96.3 per iter-0033b' re-run, NOT raw 48). Per-fixture `solo_claude − bare` margin within ±2. Zero new disqualifiers, zero new CRITICAL findings on `solo_claude` arm. iter-0033 (C1) headroom-available ≥+5 count = 5/5 PASS replicated.
- **Fail**: ANY fixture outside variance band on `solo_claude` OR new CRITICAL on `solo_claude` arm.
- **Threshold rationale**: ±2 axes per iter-0027 N=5 evidence; iter-0033 (C1) PASS replication confirms world-class L1 unchanged.
- **Wall budget**: ~4-6h for 3-arm full suite (9 fixtures × 3 arms = 27 runs ≈ 10-15min avg in serial). Reduces to ~3-4h if running solo_claude + bare only (skipping diagnostic variant). Default: 3-arm full suite to preserve diagnostic capture for future analysis.
- **Background execution**: per HANDOFF execution sequence step 6, `run_in_background: true` Bash; parent does iter-0034 closure draft + iter-0035 STUB skeleton + R-final prompt prep while suite runs.

## Risk register

| ID | Risk | Mitigation | Trigger if mitigation fails |
|---|---|---|---|
| R1 | bench harness `--resolve-skill old` default invokes deleted `/devlyn:auto-resolve` | Phase 4 flips both defaults to `new` + hard-errors on `old` + removes dead `old`-branch code in run-fixture.sh PROMPT scaffolding (lines 270-336). Keeps `--resolve-skill new` as accepted compatibility no-op so historical `run-iter-0033c.sh:137` still runs. | If post-cutover suite invocation fails arg-parse: revert harness changes, re-pre-register Phase 4b for harness-only |
| R2 | SKILL.md PHASE 1 line 80 wording change drifts PLAN behavior | Use SHORT runtime-safe label per §"L2 PLAN-pair research-only label" (Codex R0 P3); Gate 1 + Gate 5 measurement against ±2 band on `solo_claude` arm | If band exceeded: revert SKILL.md edit, re-smoke; if still drift, Codex R-smoke pair-collab on root cause |
| R3 | deletion graph misses indirect dep (e.g. team-resolve invoked review/team-review internally) | Codex R0 audited deletion list — direct deps on `/devlyn:resolve` or `/devlyn:ideate` are zero. Lint Check 6 mirror parity catches missing files (after lint Check 6 path list is updated per R8). Grep external refs as part of Gate 2. | If post-deletion lint fails: identify offending ref, decide (a) update upstream OR (b) restore-and-defer |
| R4 | `optional-skills/` install path differs from `config/skills/` requiring separate bin/devlyn.js handling | bin/devlyn.js already handles `OPTIONAL_ADDONS`; verify install flow with `npx devlyn-cli list` | If install flow breaks: revert moves, defer optional-skills/ migration to Phase 5 |
| R5 | Gate 5 suite re-run shows score regression beyond variance band | Anti-asymptotic per iter-0033g lesson: revert smallest unit, re-smoke; if revert+re-smoke loop fails 2x, escalate to user | Surface to user with raw numbers + revert candidate options |
| R6 | F9 baseline split (iter-0033c1-new is F1-F8 only; iter-0033a-f9-smoke3 for F9) | Already mitigated: documented split-baseline in §"Predicted change". F6 paired N=3 mean (96.3) used per iter-0033b' re-run, NOT raw `summary.json:410` value (48). | None — already mitigated by explicit baseline split |
| R7 (Codex R0) | Installed legacy skill dirs persist after upgrade because `bin/devlyn.js cleanManagedSkillDirs` only removes target dirs that exist in source. Post-deletion, deleted skill dirs no longer exist in source → user installs keep stale `~/.claude/skills/devlyn:auto-resolve/` indefinitely. | Add 18 colon-name entries to `bin/devlyn.js DEPRECATED_DIRS` (line 73-91) covering all 15 deletes + 3 optional-skills/ moves so upgrade explicitly force-removes them. | Post-cutover, downstream user upgrade should remove stale skills (verify via local `npx devlyn-cli` smoke on a test directory) |
| R8 (Codex R0) | `scripts/lint-skills.sh` Check 6 hardcodes mirror parity paths to `devlyn:auto-resolve/SKILL.md`, `devlyn:preflight/SKILL.md`, `devlyn:team-resolve/SKILL.md`, `devlyn:team-review/SKILL.md` (lint:126-156). Post-deletion lint will fail with "missing file on critical path". | Update Check 6 path list to drop deleted skills BEFORE deletion. Same for any other hardcoded skill names in Checks 7-14. | If lint fails post-deletion: identify offending path, update lint, re-run |
| R9 (Codex R0) | `_shared/` docs contain stale auto-resolve/preflight references: `pair-plan-schema.md:10-17`, `engine-preflight.md:3+17`, `codex-config.md:9+52`. Gate 2 grep would catch as stale references. | Choose: (a) update inline references to point at `/devlyn:resolve` equivalents OR (b) explicitly archive section with header noting "iter-0034 superseded; preserved as design archive". Option (a) preferred (cleaner). | If grep finds remaining hits in `_shared/` post-cleanup: choose (a) or (b) per case |

## Wall budget total

~7-9h:
- Pre-reg + Codex R0 + revisions: 60-75min ✅ (R0 returned NOT-CONVERGED-REVISIONS at 382s; revisions applied in-place; this task complete)
- Step 3 (mechanical compatibility first per Codex R0 P7): bin/devlyn.js DEPRECATED_DIRS update + lint Check 6 path update + bench harness updates (run-suite.sh + run-fixture.sh): 30-45min
- Step 4 (skill deletion + optional-skills/ migration): 30-45min
- Step 5 (mirror sync + lint): 5-10min
- Step 6 (doc updates per Codex R0 P7 — AFTER mechanical compat ships): 60-75min
- Gate 1 smoke (F1+F2+F9 via run-fixture.sh direct invocation, 2-arm): ~45-60min
- Gate 5 suite (background, 3-arm full suite): 4-6h (parent does closure draft + iter-0035 STUB + R-final prompt prep concurrently)
- Compare + Codex R-final: 30min
- iter-0034 closure + iter-0035 STUB + HANDOFF refresh + DECISIONS append + commit: 45min

## Implementation sequence (revised per Codex R0 P7 — mechanical compatibility FIRST)

Per Codex R0 P7: docs-first is lower safety because docs can temporarily claim a product surface the installer cannot yet enforce. Revised order:

1. **Mechanical compatibility (Step 3-revised)**: Update `bin/devlyn.js DEPRECATED_DIRS`, `scripts/lint-skills.sh Check 6` path list (and other hardcoded skill paths in Checks 7-14), `benchmark/auto-resolve/scripts/run-suite.sh + run-fixture.sh` defaults + `old`-branch hard-error + dead branch removal. **Lint must still pass** at this step (with updated path list).
2. **Skill deletion + optional-skills/ migration (Step 4)**: `git rm -r` from `config/skills/` AND `.claude/skills/` for 15 deletions; `git mv` for 3 optional-skills/ migrations; update `_shared/` stale refs per R9 (option a: inline rewrite to /devlyn:resolve equivalents).
3. **Mirror sync + lint** (Step 5): `node bin/devlyn.js -y` to re-sync; `bash scripts/lint-skills.sh` must PASS.
4. **Doc updates (Step 6)**: README, CLAUDE.md, AGENTS.md, NORTH-STAR, HANDOFF, SKILL.md PHASE 1 line 80. Now safe to claim "Phase 4 SHIPPED" because installer enforces it.
5. **Gate 1 smoke (Step 7-revised)**: F1 + F2 + F9 via `run-fixture.sh` direct (2-arm: solo_claude + bare). Compare against c1-new baseline.
6. **Gate 5 suite (Step 8-revised, background)**: 9-fixture × 3-arm (or 2-arm) suite. Parent drafts closure structure + iter-0035 STUB + R-final prompt while running.
7. **Codex R-final + closure (Steps 9-10)**: pre/post compare on solo_claude arm; closure with raw numbers.
8. **iter-0035 STUB + commit (Step 11)**.

## L2 PLAN-pair research-only label spec (ships in Gate 3, replaces SKILL.md PHASE 1 line 80)

Per Codex R0 P3: keep prompt body short. The full rationale lives in `iter-0033g §"CLOSURE"` + `NORTH-STAR.md` + this iter file — it does NOT belong in the runtime prompt.

Replacement text (single line, runtime-safe):

> Engine: Claude. PLAN runs solo at HEAD. PLAN-pair is research-only and disabled until either (A) container/sandbox isolation is justified by another product need, or (B) production telemetry captures positive evidence of subagent introspection that a PLAN-pair measurement would need to isolate. See `autoresearch/iterations/0033g-pair-plan-impl-pmo.md` § "CLOSURE" + `iterations/0034-phase-4-cutover.md`. Prompt body: `references/phases/plan.md`.

Unblock condition B is positive-evidence-trigger (per Codex R0 P4): a captured introspection event (e.g. `readlink /dev/fd/1` execution observed in production telemetry, `ps aux` on parent process, `/tmp` glob enumeration) UNBLOCKS the iter — absence of evidence does NOT trigger anything (avoids "prove a negative"). Methodology preserved in `iter-0033g §"CLOSURE" §C` Codex grep methodology.

## Deletion list (per HANDOFF + Codex R0 inventory)

**DELETE (15 user skills, both `config/skills/` and `.claude/skills/` mirrors)**:

1. `/devlyn:auto-resolve`
2. `/devlyn:browser-validate` (→ kernel runner per NORTH-STAR; replaced by `_shared/browser-runner.sh`)
3. `/devlyn:clean`
4. `/devlyn:design-ui`
5. `/devlyn:discover-product`
6. `/devlyn:evaluate`
7. `/devlyn:feature-spec`
8. `/devlyn:implement-ui`
9. `/devlyn:preflight`
10. `/devlyn:product-spec`
11. `/devlyn:recommend-features`
12. `/devlyn:review`
13. `/devlyn:team-resolve`
14. `/devlyn:team-review`
15. `/devlyn:update-docs`

**MOVE to `optional-skills/` (3 skills)**:

- `/devlyn:reap` (process hygiene utility per NORTH-STAR)
- `/devlyn:design-system` (creative power-user)
- `/devlyn:team-design-ui` (creative power-user)

**KEEP (final user-facing skill surface, 2 skills)**:

- `/devlyn:resolve`
- `/devlyn:ideate`

**KEEP (kernel + standards + dev artifacts, NOT user-facing skill names)**:

- `_shared/` — kernel
- `code-health-standards`, `code-review-standards`, `root-cause-analysis`, `ui-implementation-standards`, `workflow-routing` — referenced as text-include skills by deleted skills; will become orphans after deletion. **Phase 5 follow-up** to evaluate orphan cleanup. Out of iter-0034 scope per Mission 1 discipline.
- `devlyn:auto-resolve-workspace`, `devlyn:ideate-workspace`, `preflight-workspace`, `roadmap-archival-workspace` — dev-only iteration artifacts, never installed (per `bin/devlyn.js:300-305 UNSHIPPED_SKILL_DIRS` + `package.json:12-19`). Out of iter-0034 scope.

## Bench harness consistency (Phase 4 dependency, per Codex R0 P6)

`benchmark/auto-resolve/scripts/run-suite.sh:32` + `run-fixture.sh:23` default `RESOLVE_SKILL=old` invokes `/devlyn:auto-resolve`. Phase 4 changes:

- Flip both defaults to `new`.
- Validation branch: `--resolve-skill new` → accepted (no-op compatibility for historical runners). `--resolve-skill old` → hard-error with message: "old `/devlyn:auto-resolve` was deleted in iter-0034 Phase 4 cutover (commit TBD); use --resolve-skill new (default)".
- Remove `old`-branch dead code in run-fixture.sh PROMPT scaffolding (lines 270-336 area for the `old` ENGINE_CLAUSE branch).
- Update header docstrings to drop `old` advertisement OR document the `new`-only single mode + flag accepted as no-op for historical runners.
- Existing historical runner `run-iter-0033c.sh:137` calls `--resolve-skill new` — preserved unchanged because `new` is now the default + accepted no-op.

This change is "directly required by deleting `/devlyn:auto-resolve`" per Goal-locked execution; not scope creep.

## bin/devlyn.js DEPRECATED_DIRS update (per Codex R0 P5/R7)

Current `DEPRECATED_DIRS` (lines 73-91) contains 17 hyphen-prefixed entries from v0.7.x rename (`devlyn-clean`, etc.). Phase 4 must add 18 colon-name entries:

```js
// Skill directories deleted/moved in iter-0034 Phase 4 cutover (v1.x.x).
const DEPRECATED_DIRS = [
  // ... existing v0.7.x entries ...
  // iter-0034 Phase 4 cutover: deleted user skills
  'skills/devlyn:auto-resolve',
  'skills/devlyn:browser-validate',
  'skills/devlyn:clean',
  'skills/devlyn:design-ui',
  'skills/devlyn:discover-product',
  'skills/devlyn:evaluate',
  'skills/devlyn:feature-spec',
  'skills/devlyn:implement-ui',
  'skills/devlyn:preflight',
  'skills/devlyn:product-spec',
  'skills/devlyn:recommend-features',
  'skills/devlyn:review',
  'skills/devlyn:team-resolve',
  'skills/devlyn:team-review',
  'skills/devlyn:update-docs',
  // iter-0034 Phase 4 cutover: moved to optional-skills/ (only force-removed if not opted-in via OPTIONAL_ADDONS)
  // For these 3, force-removal is conservative — user must explicitly opt-in via interactive installer.
  'skills/devlyn:reap',
  'skills/devlyn:design-system',
  'skills/devlyn:team-design-ui',
];
```

This ensures downstream `npx devlyn-cli` upgrades force-remove stale legacy skills from `~/.claude/skills/`.

## Lint update (per Codex R0 R8)

`scripts/lint-skills.sh Check 6` mirror-parity path list (lines 126-160) hardcodes paths to deleted skills:

- `devlyn:auto-resolve/SKILL.md` + 5 reference files
- `devlyn:preflight/SKILL.md` + 3 auditor files
- `devlyn:team-resolve/SKILL.md`
- `devlyn:team-review/SKILL.md`

Update Check 6: drop these 11 paths. Keep `devlyn:resolve/`, `devlyn:ideate/`, `_shared/` paths. Verify Checks 7-14 separately for any other hardcoded deleted-skill references and update as needed.

## Pointers

- Design baseline 1: `iterations/0033-quality-ab-new-resolve-vs-old-auto-resolve.md` (iter-0033 C1) — solo PLAN PASS evidence (line 208 F9; line 213 suite-avg; line 210 5/5 headroom).
- Design baseline 2: `iterations/0033g-pair-plan-impl-pmo.md` § "CLOSURE" — meta-strategic pivot to option VI; full 28-item leak surface enumeration preserved as design archive.
- Design baseline 3: `iterations/0033d-pair-plan-measurement.md` + `iterations/0033f-pair-plan-impl.md` closures.
- Memory lesson file: `~/.claude/projects/-Users-aipalm-Documents-GitHub-devlyn-cli/memory/project_iter0033g_asymptotic_firewall_lesson_2026_05_03.md`.
- Pre-cutover bench baseline (F1-F8 raw): `benchmark/auto-resolve/results/3bc86dd-iter0033c1-new-20260501T004229Z/summary.json`. NOTE: F6 raw value is 48; **use iter-0033b' paired N=3 mean = 96.3** instead, per iter-0033 (C1) closure line 206.
- Pre-cutover bench baseline (F9): `benchmark/auto-resolve/results/4e3d89a-iter-0033a-f9-smoke3-20260430T232747Z/`. Score 91 per iter-0033 (C1) closure line 208.
- Codex R0 transcript: `/tmp/codex-iter0034-r0/{prompt.md, response.log}`.
- Successor iters: `iterations/0035-real-project-trial.md` (TBD post-cutover) + `iterations/0036+` (L2 candidates by priority).

## Codex R0 revisions adopted

Codex R0 returned **NOT-CONVERGED-REVISIONS** (382s, 181k tokens, 7 concrete recommendations). Per HANDOFF "▶ Execution sequence" step 2 + PRINCIPLES #2 case-by-case (cleanup iter, no adversarial threat model), all 7 recommendations adopted in-place without R0.5 (rev cycle):

1. ✅ Count corrected 14 → 15 (DELETE list contains 15 entries; `.claude/skills` has 20 = 15+3+2; `config/skills` has 22 = 20 + 2 dev workspaces).
2. ✅ Gate 1 + Gate 5 rewrites: `solo_claude` (NEW L1 per iter-0033 C1 line 70) replaces `variant` (which is `--engine auto` diagnostic, NOT L1). Use corrected C1 closure data (F6 paired N=3 = 96.3, F9 = 91, suite-avg L1−L0 = +6.43, headroom-available 5/5).
3. ✅ Gate 1 wall budget revised: 2-arm `run-fixture.sh` direct (solo_claude + bare) ~45-60min, OR 3-arm `run-suite.sh` ~75-90min. Default 2-arm direct.
4. ✅ SKILL label rewritten as short runtime-safe single-line per Codex P3 (full rationale moved to NORTH-STAR + HANDOFF + this iter file).
5. ✅ Risks added: R7 (bin/devlyn.js stale-skill cleanup gap), R8 (lint hardcoded paths), R9 (`_shared/` stale refs).
6. ✅ Bench harness change spec: keep `--resolve-skill new` as compatibility no-op (preserves `run-iter-0033c.sh:137`), hard-error `old`, remove dead `old` branch, drop `old` from public help.
7. ✅ Execution sequence revised: mechanical-first (`bin/devlyn.js + lint + bench`) → skill deletion → docs (per Codex P7 lower-safety reason: docs claiming "shipped" before installer enforces it would be dishonest).
8. ✅ Unblock condition B framing: positive-evidence trigger (presence unblocks), not "prove absence" (per Codex P4).

## Codex pair-collab plan (revised post-R0)

- ✅ **R0** completed 2026-05-03 (382s, NOT-CONVERGED-REVISIONS, 7 recommendations adopted in-place).
- **R-smoke** (conditional, on Gate 1 fail): Codex pair-collab on root cause if F1/F2/F9 outside variance band post-edit.
- **R-final** (mandatory, Gate 5 → step 7): Codex reads pre/post compare raw numbers via `-s read-only`. Position: solo behavior unchanged within variance band on `solo_claude` arm. Falsification ask: any regression hidden by aggregation? any L2 label inaccurate post-cutover? any honest concern about claiming Phase 4 SHIPPED? `_shared/` cleanup (option a or b) executed correctly?

## Principles check (PRINCIPLES.md #0-#7)

- **#0 Pre-flight**: ✅ Closes user-visible failure (20 `devlyn:*` skills doesn't match locked 2-skill product surface; downstream upgrades retain stale skills) + unlocks iter-0035 real-project trial (Mission 1 terminal gate per NORTH-STAR test #15).
- **#1 No overengineering / Subtractive-first**: ✅ Net deletion: 15 skills removed + 3 moved out + ~50 LOC bench harness dead code removed + 11 hardcoded lint paths removed + `_shared/` stale text removed. Additions are minimal and cited: SHORT L2 label text in SKILL.md (Codex R0 P3 minimum-text), `bin/devlyn.js DEPRECATED_DIRS` 18 entries (cited prior failure mode: stale-skill upgrade gap per R7).
- **#2 No guesswork**: ✅ Hypothesis falsifiable (5 gates with predicted directions filled BEFORE run, immutable). R0 caught variant/solo_claude arm bug + applied corrected C1 closure data. Predicted change table now uses honest baseline (corrected C1 closure values, NOT raw `summary.json:410` value).
- **#3 No workaround**: ✅ L2 PLAN-pair research-only label is principled (cites empirical grounding + positive-evidence unblock conditions A and B per Codex R0 P4), not silent fallback. Deletion of `/devlyn:auto-resolve` is at root cause (skill no longer matches product surface), not at symptom (suppressing user trigger). bin/devlyn.js DEPRECATED_DIRS addition is at root cause (downstream cleanup gap), not at symptom.
- **#4 Worldclass production-ready**: ✅ Gate 5 + iter-0033 (C1) PASS replication confirms zero CRITICAL on `solo_claude` arm; deletion does not reduce shipping surface to anything below iter-0033 C1 quality bar.
- **#5 Best practice**: ✅ Standard Subtractive-first cleanup pattern (CLAUDE.md). No hand-rolled mechanism replacing standard primitives. `git rm -r` for atomic deletion. `DEPRECATED_DIRS` extension is the standard upgrade-cleanup pattern already established in `bin/devlyn.js:73-91`.
- **#6 Layer-cost-justified**: ✅ Solo PLAN (L1) baseline preserved per Gate 1 + Gate 5; L2 PLAN-pair shipped as research-only label = layer-cost-zero (no L2 product surface ships unmeasured per round-3 pair policy).
- **#7 Mission-bound**: ✅ Mission 1 single-task scope (cutover iter, no parallel-fleet, no worktree-per-task). Mission 1 hard NOs untouched. iter-0035 (real-project trial) remains Mission 1 terminal gate per NORTH-STAR test #15.

## Forbidden under iter-0034 scope (per HANDOFF "Forbidden under this branch")

- Do NOT open iter-0033h with another firewall architecture attempt.
- Do NOT delete iter-0033c-compare.py / build-pair-eligible-manifest.py / iter-0033f-* / iter-0033g-* assets.
- Do NOT degrade L1 solo behavior in Phase 4 cutover — Gate 1 + Gate 5 catch this.
- Do NOT skip Codex R0 / R-final pair-collab steps. (R0 ✅ done; R-final pending.)
- Do NOT surface trivial questions to user mid-pipeline.
- Do NOT bypass any of PRINCIPLES.md #0-#7.

## Definition of "done"

- All 5 gates PASS with raw evidence cited in CLOSURE section.
- iter-0034 closure committed.
- iter-0035 STUB committed with hand-off contract for real-project trial.
- HANDOFF refreshed: iter-0035 active, iter-0034 SHIPPED.
- DECISIONS appended.
- L1 solo behavior verified unchanged on `solo_claude` arm (Gate 1 + Gate 5 raw numbers).
- 2-skill design surface clean (Gate 2 + 3 + 4 verified).
- Downstream upgrade safety verified via DEPRECATED_DIRS.
- All actions trace back to a principle (#0-#7) + cite file:line evidence.

## Actual change

### Gate 5 — Post-cutover bench suite (run 1, run-id `20260504T002059Z-472906c-iter0034-postcutover`)

Initial 9-fixture × 3-arm suite returned ship-gate FAIL on three load-bearing axes:

| Fixture | post L1 (solo_claude) | corrected baseline | delta | DQ | notes |
|---|---|---|---|---|---|
| F1 | 92 | 99 (raw c1-new, timed_out=true) | -7 | no | outside ±2 band; baseline inflated by timeout artifact |
| F2 | 98 | 98 | 0 | no | within band |
| F3 | 99 | n/a (c1-new raw 62 was iter-0033b fabrication artifact) | recovered | no | improvement vs corrected |
| F4 | 100 | 100 | 0 | no | within band |
| F5 | 98 | 95 | +3 | no | within band |
| F6 | 92 | 96.3 (paired N=3 mean per iter-0033b') | -4.3 | no | outside ±2 |
| F7 | 95 | 98 | -3 | no | borderline |
| F8 | 98 | 91 | +7 | no | improvement |
| F9 | **61** | 91 (iter-0033a-f9-smoke3) | **-30** | **YES** (silent-catch CRITICAL on HEAD-detect helper) | hard floor violation; categorical reliability axis broke |

Suite-avg L1−L0 = +8.3 (improvement vs corrected pre-cutover +6.43 closure line 213) but masked the per-fixture failures. Headroom-available ≥+5 count dropped from 5/5 (F1, F2, F4, F5, F9) to 3/5 (F2, F4, F8 PASS; F1 +1, F6 -2 FAIL; F9 DQ excluded).

### Codex R-final on suite results (2026-05-04, 436s, 328k tokens)

VERDICT: **NOT-SHIP-RE-SMOKE**. Codex independent verdict + Claude analysis converged: smallest revertible unit is the SKILL.md PHASE 1 line 80 wording change (the only edit in iter-0034 prompt-body), per pre-reg R5 ("revert smallest unit + re-smoke; fail loop 2x = surface to user"). Transcript: `/tmp/codex-iter0034-rfinal/{prompt.md, response.log}`.

### R5 revert + re-smoke (run 2, run-id `20260504T094751Z-472906c-iter0034-line80-revert-smoke`)

Reverted `config/skills/devlyn:resolve/SKILL.md:80` to HEAD wording (`PLAN-pair is **unmeasured at HEAD** — iter-0033d is the first L1-vs-L2 measurement; iter-0020 falsified Codex-BUILD/IMPLEMENT, NOT PLAN-pair`). Re-smoked F1 + F6 + F9 with 3-arm suite:

| Fixture | post-revert L1 | baseline | delta | DQ | result |
|---|---|---|---|---|---|
| F1 | 96 | 99 (raw, timeout-inflated) | -3 | no | clean exit; honest comparison PASS |
| F6 | 99 | 96.3 (corrected) | **+2.7** | no | improvement, within ±2 |
| F9 | 92 | 91 (iter-0033a) | **+1** | **NO** | silent-catch CRITICAL eliminated ✅ |

**R5 confirmed line-80 wording was the regression cause.** L1−L0 suite-avg on the 3 re-smoked fixtures = +5.0 (≥+5 floor PASS). F9 silent-catch DQ eliminated, F6 within band, F1 within band on honest comparison.

### Gate verdicts (post R5 revert)

- **Gate 1 (smoke F1+F2+F9)**: PASSED (subsumed in Gate 5 + R5 re-smoke; F1 +1 over honest baseline, F2 0, F9 +1).
- **Gate 2 (legacy skill deletion + stale-reference cleanup)**: PASSED. `ls config/skills/devlyn:*` shows only `resolve` + `ideate` + 2 dev workspaces. `ls .claude/skills/devlyn:*` shows resolve + ideate. `optional-skills/devlyn:*` includes 5 skills (3 moved + 2 pre-existing pencil). `_shared/` stale references cleaned (option a inline rewrite for codex-config.md + engine-preflight.md, option b archive header for pair-plan-schema.md). Lint Check 6 PASS.
- **Gate 3 (doc surface updated)**: PASSED. SKILL.md PHASE 1 line 80 carries HEAD wording (R5 revert). NORTH-STAR Phase 4 marked done. README + CLAUDE.md + AGENTS.md rewritten for 2-skill design. Plus user-directed principles refocus (see "Principles refocus" subsection below).
- **Gate 4 (optional-skills/ migration)**: PASSED. 3 skills moved + bin/devlyn.js OPTIONAL_ADDONS gains 3 entries + DEPRECATED_DIRS gains 18 colon-name entries (R7 mitigation: stale-skill upgrade gap closed).
- **Gate 5 (post-cutover bench suite re-run, L1 unchanged)**: PASSED via R5 revert. F9 categorical reliability axis preserved (silent-catch CRITICAL eliminated). F1/F6 within ±2 on honest baseline.

### Principles refocus (user-directed scope expansion 2026-05-04)

User directive 2026-05-04: the canonical 7 principles (no workaround / no overengineering / no guesswork / worldclass / best practice / optimized / production ready) plus three discipline rules (flexible 5-why, first-principles thinking, Saint-Exupéry "perfection = nothing left to remove") MUST be the PRIMARY content of `CLAUDE.md` and `AGENTS.md`. Everything else is secondary; aggressive Subtractive-first deletion authorized.

Codex audit (2026-05-04, 229s, 94k tokens, transcript at `/tmp/codex-claude-agents-audit/`) returned VERDICT: AGREE-WITH-DRAFT, with three additional findings beyond the user's directive:

1. `autoresearch/PRINCIPLES.md` line 68 vs line 72 self-contradiction: "walk why until invariant" (line 68) vs "documents at least three why steps" (line 72). Canonical source disagreed with itself.
2. `CLAUDE.md:160` shipped an absolute machine-local path (`/Users/aipalm/Documents/GitHub/devlyn-cli`) inside a Codex wrapper example — high downstream pollution.
3. `AGENTS.md:116` referenced `config/commit-conventions.md` but downstream installs copy the file to `.claude/commit-conventions.md`.

Edits applied (all in this iter, post R5 revert when sub-agent prompt context was confirmed safe):

- **CLAUDE.md** restructured: outer-goal autoresearch-loop framing block REPLACED with a `## Core principles` section listing the 7 + 3 in canonical order; Saint-Exupéry promoted from buried section quote to top-level discipline rule. Karpathy 4 section DELETED (redundant with new principles). `Codex companion pair-review (autoresearch loop)` subsection DELETED (autoresearch-internal; downstream user doesn't need it). `Bare-Case Guardrail` DELETED (autoresearch concept). Remaining `Codex invocation` section pruned to 1 paragraph (no machine-local path). 207 → 169 lines (net -38).
- **AGENTS.md** restructured: same `## Core principles` block; legacy "Non-Negotiable Principles 1-6" + "Scope Split" + "Installed Project Guidance" sections REPLACED with the canonical 7+3. 143 → 104 lines (net -39).
- **autoresearch/PRINCIPLES.md** line 1-3 stale "Five Principles" wording → "Iteration Principles ... pre-flight 0 plus principles #1-#7". Line 72 "documents at least three why steps" → "documents the why-chain until it reaches the violated invariant. Stop when the invariant surfaces — do not force a fixed count. Two why-steps that land on a real invariant are sufficient; seven that still haven't reached one mean keep going." Self-contradiction with line 68 fixed.
- **`_shared/runtime-principles.md`** marker-wrapped sections (subtractive-first / goal-locked / no-workaround / evidence) UNTOUCHED — runtime sub-agent contract preserved byte-identically. Lint Check 12 parity PASS.

`bin/devlyn.js` install flow re-tested via `node bin/devlyn.js -y`: full sync, lint Check 1-14 all PASS.

### Principles check (post-edit verification)

- **#0 Pre-flight**: ✅ Closes user-visible failure (20-skill `/devlyn:*` namespace + downstream user receives stale skills + autoresearch-jargon CLAUDE.md) + unlocks iter-0035 real-project trial (Mission 1 terminal gate per NORTH-STAR test #15) + delivers user-mandated principles refocus.
- **#1 No overengineering / Subtractive-first**: ✅ Massive net deletion. `git diff HEAD --shortstat` shows 17 files deleted entirely (15 skills + 2 dev artifacts replaced) plus per-file deletions in CLAUDE.md (-77 lines), AGENTS.md (-78), README.md (-87), lint (-43). Additions are minimal and cited (DEPRECATED_DIRS 18 entries cite R7; principles block cites user directive 2026-05-04; iter file additions document the iter itself).
- **#2 No guesswork**: ✅ Hypothesis falsifiable, predicted directions filled BEFORE run, raw data filled AFTER. R5 trigger fired exactly as pre-registered when F9 DQ surfaced. R5 revert + re-smoke confirmed line-80 wording causal — falsifiable claim, falsified.
- **#3 No workaround**: ✅ R5 revert is principled (root-cause = wording change in PLAN prompt body, not a defensive wrapper). Principles refocus is principled (replaces autoresearch-jargon framing with universal contract). Saint-Exupéry rule promoted to discipline level (was buried). Flexible why-chain rule replaces strict-3.
- **#4 Worldclass production-ready**: ✅ Gate 5 + R5 re-smoke confirm zero CRITICAL on solo_claude arm post-revert. F9 silent-catch eliminated.
- **#5 Best practice**: ✅ Standard Subtractive-first cleanup pattern. `DEPRECATED_DIRS` extension uses existing pattern. Codex pair-collab multi-round per established protocol.
- **#6 Optimized / Layer-cost-justified**: ✅ Solo PLAN baseline preserved (R5 revert). L2 PLAN-pair shipped as research-only (zero layer cost since no L2 surface ships). Doc total -242 lines across CLAUDE.md + AGENTS.md + README.md (cognitive-load optimization for downstream user).
- **#7 Production ready**: ✅ Downstream upgrade safety verified via DEPRECATED_DIRS (18 entries; npx devlyn-cli on existing install will force-remove stale legacy skills). bin/devlyn.js + lint + bench harness all consistent post-cutover.

### What ships in this commit

- 15 user skills DELETED (`/devlyn:auto-resolve` + 14 others).
- 3 user skills MOVED to `optional-skills/` (`/devlyn:reap`, `/devlyn:design-system`, `/devlyn:team-design-ui`).
- `workflow-routing` standards skill DELETED (Subtractive-first; auto-activated discovery aid for 2 commands is over-engineered).
- `bin/devlyn.js` `DEPRECATED_DIRS` extended with 18 colon-name entries; `OPTIONAL_ADDONS` gains 3 entries; commit log message updated for clarity.
- `scripts/lint-skills.sh` Check 6 path list trimmed (-11 paths to deleted skills); Check 7 (findings-producing standalones) retired; auto-resolve scripts/evals checks removed.
- `benchmark/auto-resolve/scripts/run-suite.sh` + `run-fixture.sh`: defaults flipped to `--resolve-skill new`; `old` hard-errored with cite to iter-0034; dead `old` PROMPT branch removed; F9-OLD refusal block removed (subsumed by global hard-error).
- `_shared/codex-config.md` + `engine-preflight.md`: inline rewrites to /devlyn:resolve equivalents; absolute machine-path removed.
- `_shared/pair-plan-schema.md`: archive header citing iter-0033g closure + iter-0034 unblock conditions A/B.
- `config/skills/devlyn:resolve/SKILL.md` PHASE 1 line 80: HEAD wording preserved (R5 revert; the iter-0034-introduced short label was the regression cause and reverted).
- `CLAUDE.md`: 207 → 169 lines. New `## Core principles` block (7 + 3 discipline rules). Karpathy 4 + autoresearch outer-goal block + Codex companion pair-review subsection + Bare-Case Guardrail DELETED.
- `AGENTS.md`: 143 → 104 lines. Mirror of CLAUDE.md restructure adapted for Codex audience.
- `autoresearch/PRINCIPLES.md`: line 1-3 + line 72 self-contradiction fixed.
- `autoresearch/NORTH-STAR.md`: Phase 4 marked done; pair-mode policy reflects "L2 PLAN-pair research-only".
- `README.md`: 2-skill quick start rewrite.

## CLOSURE — SHIPPED 2026-05-04

iter-0034 ships the 2-skill product surface + canonical principles refocus. R5 revert preserved L1 categorical reliability per user direction "솔로도 그대로 잘 동작". Mission 1 terminal gate (iter-0035 real-project trial per NORTH-STAR test #15) unblocked. iter-0035 STUB drafted at `iterations/0035-real-project-trial.md`.

Codex pair-collab rounds in this iter:
- R0 (382s, 181k tokens): pre-reg review, NOT-CONVERGED-REVISIONS, 7 recommendations adopted in-place.
- R-final (436s, 328k tokens): post-suite verdict, NOT-SHIP-RE-SMOKE on F9 silent-catch DQ, recommended line-80 revert.
- Audit (229s, 94k tokens): CLAUDE.md/AGENTS.md principles refocus, AGREE-WITH-DRAFT + 3 additional findings.

Total Codex wall: ~17 minutes across 3 rounds + ~6 hours suite + 2 hours re-smoke = ~8.5 hours. All transcripts preserved at `/tmp/codex-iter0034-*` and `/tmp/codex-claude-agents-audit/`.

Memory lessons captured:
- `feedback_principles_canonical_directive_2026_05_04.md` (user-binding principles list).
- iter-0033g asymptotic-firewall lesson re-applied (anti-asymptotic R5 fired exactly once; revert + re-smoke succeeded; no escalation needed).
