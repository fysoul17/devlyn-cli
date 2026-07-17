# iter-0072 — changed-surface closure (quality axis): PRE-REGISTRATION (frozen 2026-07-14, three-way converged R0+R1)

Status: PRE-REGISTERED, NOT STARTED. No lever ships outside this
registration (user directive 2026-07-14). Archives (ephemeral):
/tmp/quality-round/{packet,r1-packet}.md + {codex,grok}-r{0,1}.log.

## Problem (measured)

nodeg-20260713: objective 7/7 PASS, blind quality 0/7 (codex judge 28/28
axes prefer frozen bare B), wall 0/7. Quality-omission class on saturated
rows: A ships the literal floor; B additionally closes the CHANGED
SURFACE — help/usage of the changed command (same authorized file),
error-path tests of the changed behavior, error text carrying the observed
value (F7), plus design-level closure (F25 catalog parse handling, all
matching promotions).

## Root cause (three-way converged, receipts)

Causal chain: free-form synthesis "when in doubt, narrower"
(free-form-mode.md:62) → criteria.generated.md narrows explicit goal
clauses (F25 "file-read failures" → --input only; F7 --help declared out
of scope) → PLAN EXCLUDES the closure work verbatim ("Refuse: touching
USAGE"; error-path regression test labeled "unrequested addition" — F7
plan.md:15,22; F25 plan.md:14,22 in the archived A-arm workspaces) →
IMPLEMENT obeys (implement.md:6,:35) → VERIFY grades against generated
criteria (verify.md:9), structurally cannot re-open. Always-loaded
anti-drift prose (CLAUDE.md:80,109,110,122; runtime-principles.md:25,54,55,
66-67; E1 = measured suppressor iter-0062) is the background field the
narrowing agent runs under — plausible co-cause, held for isolation.

## Decisive criterion (both engines, near-identical)

**Changed-Surface Coherence Is Requested; Cross-Surface Expansion Is
Drift** (Grok) ≡ **Frozen-Boundary Changed-Surface Closure** (Codex): an
addition is in scope only when it (a) preserves an explicit goal clause,
(b) updates an existing user-visible reference made stale by the named
change, or (c) regression-tests a specified success/failure path — all
inside the frozen file/behavior boundary. Other behaviors/files, drive-by
cleanup, speculative handlers for cases the change does not create remain
drift.

## Stage 1 (the only shipping lever until its falsifier resolves)

free-form-mode.md:62 (+ .claude/.agents mirrors), one-clause substitution:
- OLD: "every assumption scope-narrowing and reversible — when in doubt,
  narrower"
- NEW (candidate wording, final at build time): "every assumption
  reversible; narrow only unspecified behavior outside the named change —
  never an explicit clause, its existing user-visible references, or
  focused tests of specified success/failure paths"

Token caps: root/shared delta = 0; resolve load-set ≤ +0.1% (both gauge
approximations).

## Stage 2 (HELD; unlocks only per ladder branch 2)

L1 E1-sentence carve + L2 CLAUDE.md:122 completeness-bullet narrowing +
L3 edge-cases-created-by-this-change exception (CLAUDE.md:80 region) +
L4 implement.md:17 quality_bar expansion. Caps: always-loaded ≤ +6 lines
net across the three mirrors; L4 resolve-load ≤ +0.1%. Attribution caveat
(Codex R1): Stage-2 recovery attributes to the downstream composite, not
to any single sentence.

## Falsifier ladder (5 branches, frozen)

1. Stage-1 ARTIFACT predictions fail (regenerated F7 criteria/PLAN still
   exclude banner update + unsupported-format regression test, or F25
   criteria drop catalog failure clauses) → lever wording falsified; STOP;
   fresh pre-registration required; does NOT unlock Stage 2.
2. Artifacts open + objective 7/7 + quality floor FAILS (< 2/7 or F7/F25
   not both passing "no B_win on any axis from either judge") → Stage 2
   unlocks.
3. Stage 2 reruns identical gates (objective, quality, drift, compliance,
   stable-clean, token).
4. Artifacts open + quality ≥ floor → STOP, Stage 2 stays unshipped
   (subtractive-first).
5. Stage 2 also fails → next pre-registered locus: PLAN "simplest tactic"
   (implement.md:6), then VERIFY advisory-quality threshold. Never "more
   completeness prose".

## Merged gates (ship = ALL pass)

- Artifact predictions (branch-1 early kill, before any full re-measure).
- nodeg re-run, same 7 rows, same frozen B hashes (nodeg-verdict.json
  frozen_b_sources), same seats (sonnet orchestrator/judge + terra
  executor/judge), --pair-verify parity: objective stays 7/7; quality
  0/7 → ≥2/7 with F7+F25 mandatory; any timeout/objective loss = no-ship.
- Advisory (not gating): codex B_win 28/28 → ≤22/28 (style-match risk noted).
- Drift non-regression: violation-matrix N=4 within established flip
  bands; stable-clean B2/B5/DB-failing-adjacent-test stay 0/4; six-probe
  resolve-framed drift-bait hidden verifiers all pass.
- Compliance cells: 3 CLI × 2 size all pass (state, ordered phases, VERIFY
  evidence, archive, finish-gate).
- Token caps per stage (above).
- Wall axis explicitly OUT of this iter's success claim (iter-0071's
  mechanism).

## Sequencing note

Runs AFTER the iter-0071 nodeg re-measure (P1/P2'/P3' baseline capture) so
the two levers' effects don't confound: 0071 re-measure first (no 0072
edits in tree), then Stage 1 lands, then the 0072 nodeg run doubles as the
quality gate.

## Amendment 1 — Stage-1 lever RELOCATED branch-neutrally (2026-07-16, three-way converged; Fable + Codex sol + Grok 4.5, 3/3 on option B)

**Trigger (new evidence, orchestrator-verified then independently re-read by
both seats).** The nx01 A-arm workspaces survive post-run (contra the 0071.4
retention-gap wording — `.devlyn/runs/<id>/{criteria.generated.md,plan.md,
pipeline.state.json}` are intact for both nodeg cohorts). Reading them:

| Row | nodeg-20260713 (pre-L-A) | nodeg-20260714 (post-L-A baseline) |
|---|---|---|
| F7 | `complexity=large`; criteria:26 `## Assumptions`; plan:15 "Refuse: touching USAGE"; plan:22 error-path test = "unrequested addition" (= the registration receipts) | `complexity=medium`; NO Assumptions block; same omission via criteria Constraints ("No other subcommand (`hello`, `--help`) may change behavior") + plan Risks ("Byte-for-byte … including the `USAGE` string"; only json-path test planned) |
| F25 | `complexity=large`; criteria:25 narrows explicit "file-read failures" clause to "on the `--input` path" **inside `## Requirements`** | `complexity=medium`; criteria R5 carries the clause VERBATIM; plan adds the USAGE entry; quality loss = 3602s timeout (invoke_exit 124), not criteria narrowing |

iter-0071 L-A (goal_length>80 Large-trigger deletion) moved both receipt rows
Large→Medium, so the registered host — the line-62 Large-branch Assumptions
parenthetical — is no longer traversed by any receipt row. Running branch-1
against it would test unmeasured context-seepage and make placement-miss
indistinguishable from wording failure.

**Named deltas.** Codex sol: "Post-L-A Branch-Host Reachability" (R0 accepted
the registered path; pipeline.state.json complexity fields disprove it).
Grok: R0 held line 62 as the only open surface; the fresh artifacts are
placement evidence, not wording taste. Decisive criterion (all seats):
**Causal-Path Placement** — a wording lever ships only into text the receipt
rows demonstrably traverse.

**Relocated lever (replaces §Stage 1's line-62 substitution; line 62 stays
UNCHANGED — no dual-host token spend).** Replace the "Mini-spec quality bar"
intro line (free-form-mode.md:75 + `.claude`/`.agents` mirrors):

- OLD (91c/13w): `The internal mini-spec written for trivial / medium /
  large-assumptions paths must satisfy:`
- NEW (194c/25w): `Never narrow an explicit goal clause, nor exclude
  user-visible references the change stales or tests of specified
  success/failure paths. Every mini-spec (trivial/medium/large) must also
  satisfy:`
- Delta +103c/+12w — under the frozen caps (≤+120c/≤+15w = +0.1% resolve
  load-set both gauges); root/shared delta 0.

Fable synthesis delta vs both seats' R1 texts (named): their
"Constraints/Out-of-Scope never absorb …" scoping misses the third observed
channel — F25-20260713's intra-clause narrowing sat inside `## Requirements`
(criteria:25 under heading :5). "Never narrow an explicit goal clause"
is section-unscoped by design; carriers (b)/(c) are exclusion-verbs
("nor exclude …"), matching how F7's omissions actually manifest.

**Gate protocol updates (predictions otherwise unchanged).**
- Record which branch fired per row (`pipeline.state.json` `complexity`).
- F7 stays THE discriminating row: regenerated criteria/PLAN must include the
  USAGE update and the unsupported-format error-path test.
- F25 re-anchored to non-regression (its post-L-A baseline already carries
  the clause + USAGE entry).
- Artifact inspection happens as each row completes inside the full nodeg
  run (rows execute in CONTROL_ORDER F7→F25→…), before judge wall is spent;
  branch-1 fire → kill the run, STOP per ladder (fresh pre-registration;
  Stage 2 stays locked).

**Authority.** Both seats: formal amendment + DECISIONS entry recorded before
the edit lands satisfies "no lever ships outside this registration"
(2026-07-14); relocation is reported to the user before the nodeg quality
run. Seat dissent would have escalated to the user; there was none (3/3 B).

## Branch-1 FIRED — Stage-1 wording FALSIFIED, valid-negative (2026-07-16, same session)

Run `nodeg-20260716` (runner `03c3e4b`, CLI pin 2.1.211, amendment loaded in the
workspace skill copy — verified by grep before judging the artifacts). F7
regenerated under the relocated lever, `complexity: medium` as predicted:

- criteria.generated.md again lists `--help` under `## Out of Scope` and demands
  only the json-path test — the new quality-bar sentence sat in the same file
  and was not obeyed at synthesis time.
- plan.md REFUSES both carriers explicitly: "do not update `USAGE` to mention
  `--format` — that's unrequested scope expansion … even though it would look
  'more complete'"; "do not add an exit-1/`--format yaml` test … since that
  isn't requested". Archived: `benchmark/ceiling/results/nodeg-20260716/
  branch1-early-kill/` (criteria + plan + pipeline.state + VERDICT.md).

Ladder branch 1 executed as frozen: run killed before judge wall (no row
completed; run-id dead), lever REVERTED in all three mirrors (falsified prose
does not stay shipped — iter-0066 L5 precedent), Stage 2 stays LOCKED, fresh
pre-registration required.

**Diagnostic carried into the fresh registration**: the refusals quote the
always-loaded anti-drift vocabulary verbatim ("unrequested scope expansion",
"subtractive-first / no-overengineering", "isn't requested"). A same-file
reference rule loses to the always-loaded field. This is evidence FOR the
registration's original isolation hypothesis (root cause §: "always-loaded
anti-drift prose … plausible co-cause, held for isolation") — but branch 1
does NOT unlock Stage 2; the next lever must be re-registered three-way from
these receipts.

## Registration v3 — Verbatim-Goal Contract (VGC), three-way converged 2026-07-16 night (Grok M3 R0 + Fable adjudication + Codex R1 CONFIRM; archives /tmp/codex-0072-r3/)

**Status: FROZEN ON DISK, NOT COMMITTED, NOT BUILT** — T1 val3 cohort is
running (mid-cohort commit ban); build + gate run open at the next window.

**Decisive criterion**: Information-Preservation over Instruction — make the
verbatim goal REACH the deciding agents by DELETING the lossy PHASE-0
synthesis, not by annotating it. Named seat criteria: Grok "Lossy-Transform
Deletion with One-File Reach"; Codex R0 "Minimum Lossless Authority Change"
(M1-first) WITHDRAWN in R1 with named delta — M1's diagnostic is confounded
(v2 criteria carried the yaml clause verbatim beside the freeze list and
still refused: co-location cannot distinguish information loss from
authority conflict), M3's falsifier is clean.

**Mechanism (M3/VGC)**: free-form `.devlyn/criteria.generated.md` becomes:
`## Goal (verbatim)` (raw `goal_text`, byte-identical, collision-safe
fenced) → optional `## Context anchors (non-binding)` (1-2 codebase anchors,
no scope law) → `<!-- devlyn:verification -->` + `## Verification`
(machine JSON, unchanged carrier). NO synthesized binding
Requirements/Constraints/Out-of-Scope on any free-form branch (trivial/
medium/large share the shape; Large keeps `## Assumptions` for true
assumptions only, non-binding or halt-to-ideate). Spec-mode and verify-only
UNTOUCHED. No new flag/file/schema field.

**Edit surface (build packet must cover every consumer — Codex R1 sweep)**:
1. free-form-mode.md trivial/medium/large actions + mini-spec quality bar
   (mechanical: Goal-first, raw-byte preservation, collision-safe fencing,
   canonical Verification LAST, no binding scope sections) + SKILL.md:100
   free-form bullet; 3 mirrors.
2. plan.md — "Requirement" dependencies → "binding clause in Goal";
   anchors cannot license/forbid files; authorized_surface derives solely
   from raw Goal clauses (downstream BUILD_GATE/finish-gate consumers
   mechanically unchanged).
3. implement.md:16 + state-schema.md:61 — free-form criteria ledger becomes
   ONE non-authoritative `criteria.generated://goal` entry (implemented only
   when every raw Goal clause is satisfied); never regenerate 3-5 bullets.
4. verify.md:32 free-form grading frame — grade every binding raw-Goal
   clause; Verification = mechanical evidence; anchors non-binding; Scope
   axis uses explicit Goal boundaries (VERIFY cannot read PLAN).
   cleanup.md:11 — raw Goal is the scope authority.
5. spec-verify-check.py — FIX the opaque-text collision (first-match
   sentinel regex can bind a fake sentinel inside the fenced goal —
   spec-verify-check.py:118); select the canonical TAIL carrier / ignore
   fenced goal content; add a self-test with fake sentinels/headings/JSON
   fences inside the goal.
6. verify-merge-findings.py:346 — solo-headroom trigger scan scoped to the
   Goal section only (a non-binding anchor must not trigger routing).
7. Lint needles + probe/archive surfaces re-checked; mirrors parity.

**Gates (ship = ALL; any fail → revert all, valid-negative, STOP)**:
- Static: mirror parity, lint, token gauges ≤ +0.1% both approximations
  (contract prose only; embedded goal = run-scoped artifact), no new
  flag/file; spec-verify-check self-test incl. collision case; verify-merge
  self-test; spec/verify-only byte-behavior unchanged.
- F7 early kill (inside fresh nodeg run, CLI pinned, engines serial):
  complexity=medium recorded; extracted Goal == task.txt bytes; no binding
  synthesized R/C/O; canonical Verification parses; PLAN includes BOTH
  carriers as work items (USAGE update + unsupported-format unit test);
  authorized_surface stays the two named files. F25 non-regression (raw
  Goal exact; closure retained; timeout semantics per 0072.3).
- CLEAN FALSIFIER (pre-stated): raw Goal is demonstrably the sole scoping
  authority; renewed carrier refusal kills before judge wall and falsifies
  information-preservation for this class — next mechanism class is
  structural PLAN scope-lock/policy (e.g. PLAN may not emit refuse-lists
  contradicting Goal clauses; IMPLEMENT binds Goal over plan Risks), never
  more prose. Seat predictions recorded: Grok P(refusal persists) ≈
  0.40-0.50; Codex ≈ 0.40.
- Drift battery: violation matrix N=4 flip bands; stable-clean B2/B5 +
  DB-failing-adjacent-test 0/4; six drift-bait probes; 3-CLI × 2-size
  compliance cells (VGC touches every free-form run).
- Full nodeg: same frozen B; objective 7/7; quality ≥2/7 F7-mandatory; F25
  per 0072.3. Wall axis OUT of the claim; record PHASE-0/PLAN wall.

**Vehicle**: iter-0072 Registration v3 (both seats; fresh pre-registration =
newly frozen mechanism, not a new iter number).

## Registration v2 — D1 authority-matched carve (2026-07-16, three-way R0+R1; Codex R1 arithmetic dissent resolved)

**Decisive criterion**: Authority-Matched Causal Placement with Frozen-Boundary
Closure — the lever must edit the authority tier that produced the refusal
(always-loaded Goal-locked field) and classify exactly the three in-boundary
carriers as requested. Seat records: Codex R0 "Authority-Matched Frozen-Boundary
Closure"; Grok R0 "Authority-Tier Causal Placement" + named delta reversing its
own R0 drift-test locus in R1; Grok R0 receipt killing D2 (plan.md:29 "Existing
tests are contract. Plan to extend them" was already present and refused).
D2/D3 held, D4 rejected (stale-reference not mechanically decidable), no
stacking or rescue inside this registration.

**Frozen edits (0 line growth; arithmetic verified three-way)**:
1. CLAUDE.md:108 + runtime-principles.md:53 (+ .claude/.agents mirrors),
   pattern 1 replaced (−45c/−25w): "1. **Unrequested work.** Inside the stated
   file/behavior boundary, the named change also requests preserving explicit
   goal clauses, updating existing user-visible references it makes stale, and
   regression-testing specified success/failure paths. Other fixes remain
   unrequested: surface them; do not include them. **Pre-existing dead code →
   mention only, do NOT delete; orphans YOUR change created (now-unused
   imports, variables, functions) → clean them up.**" (dead-code invariant
   byte-identical — B5 probe surface.)
2. CLAUDE.md:122 + runtime-principles.md:67 bullet replaced (+48c/+1w):
   "- \"It would be incomplete without this\" is **not** a justification
   outside frozen-boundary closure (the pattern-1 carriers). Cross-surface
   \"completeness\" remains drift."
3. AGENTS.md:66 bullet replaced (+109c/+13w, Codex R0 draft): "- Unrequested
   work. Inside the stated file/behavior boundary, the named change also
   requests preserving explicit goal clauses, updating user-visible references
   it stales, and testing specified success/failure paths. All else is drift.
   Keep pre-existing dead code; clean only self-created orphans."
   Net per surface: CLAUDE.md +3c/−24w; runtime-principles +3c ×3 mirrors;
   AGENTS.md +109c. E1 byte-preservation sentence (pattern 2) byte-identical.
   Drift-test line and the rest of Goal-locked untouched.

**Gates (ship = ALL pass; any fail → revert all surfaces, valid-negative, STOP)**:
- lint (incl. Check 12 CLAUDE↔runtime parity) + self-tests + token gauge.
- Artifact early-kill inside the full nodeg run (fresh run-id, CLI pin, engines
  serial — no other engine work during the run): F7 criteria must NOT freeze
  `--help`/USAGE and must carry BOTH carriers; F7 plan includes both as work
  items (not Risks/refusals); F25 non-regression (R5 verbatim + USAGE cart
  entry); per-row complexity recorded. Refusal → kill before judge wall.
- Full nodeg vs same frozen B: objective 7/7; quality 0/7 → ≥2/7 with F7
  mandatory; F25 timeout semantics: exit-124 row judgeable iff attested patch +
  objective resolves (recorded as deviation, NO retry); F25 not
  quality-mandatory (F7 + any second valid row satisfies ≥2/7).
- Drift battery AFTER nodeg (engines serial): violation matrix N=4 within flip
  bands; stable-clean B2/B5 + DB-failing-adjacent-test 0/4; six resolve-framed
  drift-bait hidden verifiers; E1 B4 class both arms ≤1/4 (pattern-1 is
  E1-adjacent).
- Wall axis OUT of the quality claim (0071 mechanism).

**Sign-off**: not required pre-landing (2/3 + orchestrator; Grok R1 CONFIRM
withdrew its R0 yes) — the Forbidden rule is disjunctive and observed failure +
probe gates + Block 4 user mandate all hold; iter-0062 E1 is the precedent for
probe-guarded root-contract prose landing via the loop. Prominent user report
before/with the gate run; revert-on-fail.

## Registration v2 FALSIFIED — second valid-negative, same day (2026-07-16)

Run `nodeg-20260716b` (runner `e74f00c`): F7 regenerated with the carve
grep-VERIFIED loaded in workspace CLAUDE.md + runtime-principles mirror +
AGENTS.md. Criteria still froze USAGE byte-for-byte ("`parseNameFlag`, `USAGE`,
formatting/whitespace elsewhere — must remain byte-for-byte as-is"; Out of
Scope "top-level usage text") and demanded only the json-path test; plan still
refused both carriers ("do not add extra tests beyond the one required for the
json path; that would be unrequested work"). Killed pre-judge; ALL surfaces
reverted; evidence `benchmark/ceiling/results/nodeg-20260716b/
gate-fail-artifacts/` + VERDICT.md. DECISIONS 0072.4.

**Anti-asymptotic stop (iter-0033g rule): the prose-lever class is DEAD on
this behavior** — two authority tiers (reference rule, always-loaded field
carve incl. sub-agent mirror) falsified in one day with identical refusal
shape. Ladder branch 5's remaining prose loci (implement.md:6 "simplest
tactic", VERIFY advisory threshold) inherit this precedent and are NOT to be
attempted as prose-only levers.

**Surviving causal observation for the next registration** (not yet a
registered lever): bare-B closes the changed surface reading the RAW task
text; A's narrowing is INTRODUCED at PHASE-0 criteria synthesis (the task's
own "code unrelated … must remain exactly as-is" sentence gets EXPANDED into
an enumerated freeze list that swallows USAGE) and then locked in by PLAN's
criteria-obedience. The information bottleneck — PLAN/IMPLEMENT see only the
transformed criteria, never the verbatim goal — is upstream of every prose
lever tried. Candidate mechanism CLASS for round 3 (three-way to design +
register before any edit): structural context routing (e.g., criteria file
carries the verbatim goal text alongside generated sections, or PLAN receives
goal_text directly), i.e., delete the lossy transformation instead of
instructing around it. Falsifier shape stays the F7 artifact gate.

## Registration v3 FALSIFIED — F7 gate check 5, CLEAN falsifier fired (2026-07-17; third valid-negative of iter-0072)

Run `nodeg-20260717` (runner `6d0e9f1` = VGC build, CLI pin 2.1.211): F7 row
killed pre-judge at IMPLEMENT (row exit=143). Full receipts in
`benchmark/ceiling/results/nodeg-20260717/VERDICT.md` + gate-fail-artifacts.

**The mechanism worked; the hypothesis died.** All five information checks
PASS: complexity=medium; fenced Goal byte-identical to task.txt (674B exact);
no synthesized R/C/O (contract = verbatim Goal + non-binding anchors +
Verification); canonical tail carrier parses (4 cmds); authorized_surface
exactly the two named files; state ledger = single
`criteria.generated://goal` entry. The lossy PHASE-0 transformation no longer
existed — PLAN read the raw goal as sole scoping authority.

**Check 5 FAIL**: PLAN still refused both carriers. USAGE in the Risks
refuse-list ("do not touch … `USAGE` text", grouped with genuinely
out-of-scope FILES package.json/server/ — though USAGE lives inside
authorized `bin/cli.js:8-13` and the version row documents no `--format`);
tests work item = the goal's literal-minimum json-path test only, no
unsupported-format error-path test.

**Information-preservation is falsified as the mechanism class** — per the
pre-stated clean falsifier, the narrowing lives in PLAN's own scope
reasoning, not upstream information loss: the goal's byte-preservation
sentence ("code unrelated … must remain exactly as-is") is expanded by PLAN
into refusing a stale user-visible reference INSIDE the authorized file, and
"add at least one test for the json path" is read as a ceiling, not a floor.
Seat predictions pre-gate: Grok P(refusal persists) 0.40-0.50, Codex 0.40 —
outcome inside the band. Partial deltas vs v2 (recorded, not claimed): no
freeze-list synthesized; no "unrequested work" framing; plan quotes Goal
clauses as binding; refusal surface narrowed to exactly the two carriers.

All surfaces reverted (`957c583`); .claude mirrors re-synced; reverted
self-tests PASS; no rescue; STOP per the frozen gate.

**Next mechanism class (pre-registered in the v3 falsifier, NOT yet
designed)**: structural PLAN scope-lock/policy — e.g. PLAN may not emit
refuse-lists contradicting Goal clauses; IMPLEMENT binds Goal over plan
Risks. Requires a fresh three-way registration round. iter-0072 now carries
THREE same-iter valid-negatives (v1 prose reference rule, v2 authority-
matched carve, v3 verbatim-goal contract) — surfaced to the user at the
outer-loop 3-iteration checkpoint before any round-4 registration.

## Registration v4 — Scope-Only PLAN (three-way converged 2026-07-17; archives /tmp/codex-0072-r4/)

**Status: FROZEN, NOT BUILT** — build + gates at the next usage window
(full nodeg needs a fresh account-limit window; T1 + F7 kill consumed
today's).

**Decisive criterion**: **Whole-Channel Suppressor Deletion** (Codex; ≡
Grok "Suppressor-Channel Deletion") — delete the binding semantic-PLAN
intermediary that refuses (carrier 1) and ceilings (carrier 2) bare-like
changed-surface closure; never add validators that force PLAN to restate
what Goal/Verification already carry.

**Convergence receipts (all three seats moved on the same artifact)**:
v3 `gate-fail-artifacts/plan.md:7` — carrier 2 suppressed by a POSITIVE
work item (json-test-only, goal's literal minimum restated as the task)
with zero refuse language; `:15` carrier-1 refuse; `:31` Verification
carried yaml-exit-1 yet the test item stayed json-only; `:43` Acceptance
repeated the ceiling. Named deltas: orchestrator moved from pre-round M-B
(Risks-unbind) on this receipt; Grok WITHDREW M-SSC in R1 (its Predicate B
existed to patch the ceiling channel its own criterion says to delete);
Codex R1 CONFIRM ("Positive Work-Item Ceiling").

**Mechanism (scope-only PLAN)**:
- Branch: `state.source.type == "generated"` AND `state.complexity ∈
  {trivial, medium}` (inline + `--goal-file`). Large keeps semantic PLAN
  (+ possible execution phases); spec-mode and `--verify-only`
  byte-unchanged everywhere.
- On-branch PLAN output = EXACTLY the canonical authorized-surface section
  (sentinel + heading + strict-JSON `authorized_surface`) — no title, work
  items, Risks, Acceptance, or trailing semantic bytes.
- On-branch IMPLEMENT inputs = verbatim Goal + canonical Verification +
  authorized_surface (+ extant risk probes) — never semantic PLAN.
- VGC re-lands as INFRASTRUCTURE on all proceeding free-form branches
  (Goal verbatim collision-safe fence + optional non-binding anchors +
  canonical Verification LAST; Large `## Assumptions` non-binding). Not a
  repeat of v3: the active lever is channel deletion; VGC only prevents
  the synthesis from re-freezing the surface (v2 observation).
- Grammar fail path (decidable, fail-closed): shape-parse fail → ONE
  re-spawn with the machine error + canonical template (SKILL.md:118
  precedent); second fail → `BLOCKED:plan-scope-invalid`. Never a
  semantic-plan fallback, never silent normalization. plan-empty check
  becomes empty-array check.
- Deleted: semantic PLAN sections as IMPLEMENT authority on the branch;
  free-form binding R/C/O synthesis. NOT shipped: M-SSC Predicates A/B,
  any "contradicts Goal" judgment, any PLAN work-item forcing (D4-dead).

**Edit surface**: SKILL.md (PHASE 1 dispatch/validation + PHASE 2 prompt
assembly + plan-empty semantics), plan.md (branch output contract),
implement.md (branch inputs/authority), VGC consumer sweep =
free-form-mode.md + verify.md + cleanup.md + state-schema.md +
spec-verify-check.py (collision fix + swallowing self-test + scope-only
exact-shape check via the existing authorized-surface loader) +
verify-merge-findings.py (goal-scoped solo-headroom scan); lint needles;
3 mirrors. No new flag/file/schema field.

**Gates (ship = ALL; any fail → revert all, valid-negative, STOP)**:
- Static: mirrors parity; lint; self-tests (sentinel collision +
  swallowing + scope-only grammar incl. re-spawn/fail-closed path); token
  gauges ≤ +0.1% both approximations (expect net-negative — semantic-plan
  deletion); spec/verify-only byte-behavior unchanged; no new flag/file.
- F7 early kill (fresh nodeg run, CLI pinned, pre-judge): (1)
  source=generated + complexity=medium; (2) Goal fence == task.txt bytes;
  (3) no binding R/C/O + canonical Verification parses incl. yaml exit-1;
  (4) plan.md == scope-only grammar exactly; (5) authorized_surface ==
  ["bin/cli.js","tests/cli.test.js"]; (6) post-IMPLEMENT diff ⊆ surface;
  (7) carrier 1: existing USAGE version row documents --format; (8)
  carrier 2: new unit test exercises version --format yaml (or other
  unsupported value) asserting exit 1; (9) planted same-file bait regions
  byte-identical; (10) F7 oracle + node --test pass.
- F25 non-regression per 0072.3 timeout semantics (raw Goal exact;
  closure retained). Codex R1: if F25 objective regresses, REJECT — do
  not restore a semantic side channel.
- Drift battery: violation matrix N=4 flip bands; stable-clean B2/B5 +
  DB-failing-adjacent-test 0/4; six drift-bait probes; 3-CLI × 2-size
  compliance cells. Same-file drift is conceded to be the strongest risk
  (path gates protect paths, not bytes) — the battery is the ship gate.
- Full nodeg: same frozen B; objective 7/7; quality ≥2/7 F7-mandatory;
  wall OUT of claim.

**Clean falsifier (pre-stated)**: F7 reaches IMPLEMENT with byte-exact
Goal, scope-only plan, exact two-file surface, zero semantic-PLAN bytes —
and the diff still omits the USAGE row or the unsupported-format test →
mechanism DEAD pre-judge; the narrowing localizes to IMPLEMENT's own
completion behavior. Next class: **structural post-IMPLEMENT
changed-surface evaluation/repair over the frozen authorized diff** —
not M-NPL (near-redundant once semantic PLAN is gone; Grok withdrew it),
never more prose.

**Seat predictions (pre-gate)**: P(both carriers in F7 IMPLEMENT diff |
gates 1-5 pass): Grok 0.60-0.75, Codex 0.65-0.75, Fable ~0.65.
P(quality ≥2/7 | F7/F25/drift pass): Grok 0.55-0.70, Codex 0.76,
Fable ~0.60. P(drift battery green): Grok 0.85-0.95.

**Vehicle**: iter-0072 Registration v4 (fresh registration; same iter).
Build delegated to Codex sol at the next window per the v3 packet pattern.

### v4 build record (2026-07-17, three-seat loop; packets/logs /tmp/codex-0072-v4-build/ + /tmp/grok-0072-v4-review/)

Built at `13a106a` (Codex sol workspace-write xhigh 1182s; .agents mirrors
completed by orchestrator after sandbox denial — v3 precedent). Two review
findings, both fixed pre-commit:

1. **Grok GO-WITH-EDITS**: the PHASE 1 step-3 rewrite dropped the mechanical
   demotion predicate (`risk_probes_enabled == true AND risk_probes_explicit
   == false`) — explicit `--risk-probes` could demote on a ≤2-path surface
   (F7's exact shape). HEAD-precise predicate restored; Codex R1 CONFIRM.
   Note-only (recorded, no edit): SKILL.md "PLAN's invariants" PHASE 2 lead-in
   (Codex REBUT — authorized surface IS a PLAN invariant); missing-state
   fail-open in `uses_scope_only_plan` (`read_state → {}` ⇒ predicate false ⇒
   exact-shape skipped; both seats: hardening candidate, outside the
   registered edit surface).
2. **Codex R1 NEW defect — global tail-sentinel regression**: last-sentinel
   binding applied to EVERY source type; a handwritten spec with a valid
   first carrier + later fenced sentinel example flipped carriers vs HEAD
   (reproduced) — frozen "spec/--verify-only byte-unchanged" violation.
   Fixed: keyword-only `tail_carrier=False` threaded from state-aware
   callers; only `source.type == "generated"` routes bind TAIL; spec-mode
   regression self-test asserted HEAD first-match equality.

Static gates at commit: SVC/VMF self-tests PASS; lint ALL PASS; token gauge
net-negative (resolve load-set −1.4% c4 / −2.0% w13); 3-tree parity 9/9;
spec-mode `--check` A/B byte-identical vs HEAD (6 drift-bait specs, 0
diffs); delegated-session git audit clean.

## Registration v4 FALSIFIED — F7 gate checks 7+8, CLEAN falsifier fired (2026-07-17 afternoon; FOURTH valid-negative of iter-0072)

Run `nodeg-20260717b` (runner `13a106a`, CLI pin 2.1.211): F7 row COMPLETED
(exit=0, 1248s, objective resolved=true) and the 10-item gate was decided
pre-judge; run killed during F25 (exit=143); run-id DEAD. Full receipts in
`benchmark/ceiling/results/nodeg-20260717b/VERDICT.md` + gate-fail-artifacts.

**The channel deletion worked; the carriers still died.** Gate checks 1-6 +
9-10 all PASS: live PLAN-time gate saw complexity=medium, Goal fence
byte-exact (674B), zero binding R/C/O, canonical Verification (4 cmds incl.
yaml exit-1), plan.md = the 126-byte canonical scope-only carrier accepted
by the shipped validator, surface exactly the two named files; post-run,
patch ⊆ surface, bait regions byte-identical, objective/oracle green.
Checks 7+8 FAIL: the patch has NO USAGE hunk (stale version row inside
authorized `bin/cli.js`) and only the json-path test (no unsupported-format
exit-1 test).

**Sharpest diagnostic**: the `--format yaml` exit-1 BEHAVIOR was implemented
(the Verification carrier drove it); what died were exactly the two closure
items with no mechanical verification command attached — the stale
user-visible reference and the error-path regression test. With information
loss eliminated (v3) and the binding semantic-PLAN intermediary deleted
(v4), the literal-minimum narrowing localizes to **IMPLEMENT's own
completion behavior** — no upstream suppressor channel remains. Prose-lever
class already dead (0072.4); instruction-shaped IMPLEMENT bindings
("stale user-visible references … tests of specified success and failure
paths", implement.md, loaded in the failing run) demonstrably do not close
it either.

Ladder executed as frozen: pre-judge kill → ALL surfaces reverted
(`c7927d9`) → .claude mirrors re-synced → reverted self-tests PASS → no
rescue → STOP. Seat predictions pre-gate (P(both carriers | gates 1-5
pass) 0.60-0.75 / 0.65-0.75 / ~0.65) resolved on the complementary branch —
the falsifier fired cleanly inside the registered decision tree.
Instrument gap recorded: row worktrees are cleaned at row end; the
PLAN-time watcher evaluated live but did not snapshot `.devlyn/` — raw
criteria/plan bytes unarchived (snapshot-while-live next time).

**Next mechanism class (pre-registered in the v4 falsifier, NOT yet
designed)**: structural post-IMPLEMENT changed-surface evaluation/repair
over the frozen authorized diff — design round only, fresh three-way
registration required before any edit; M-NPL stays withdrawn; never prose.
The mechanically-verified-vs-unverified clause split above is the first
design input: the omitted class is exactly the closure work no verification
command exercises.

## Registration v5 DRAFT — SURFACE_CLOSE (M-SC), round-5 design 2026-07-17 afternoon; 2-seat converged (Grok 4.5 + Fable), **PENDING Codex sol ratification** (archives /tmp/codex-0072-r5/)

**Status: DRAFT, NOT FROZEN, NOT BUILT.** Codex sol seat unavailable this
round (usage limit until 2026-07-23 13:15 KST; its R0 exited in 6s with the
limit error — no position formed). The v4 falsifier's "fresh three-way
registration" holds as a RATIFICATION GATE: no freeze, no build, until
Codex sol reads the round archives and CONFIRMs or contests. Nothing is
lost — the build executor seat is Codex, so no edit could land before 7/23
regardless.

**Decisive criteria (layered)**: packet's **Unverified-Closure Targeting**
(the target class — Goal-licensed closure work no verification command
exercises: stale in-surface user-visible references; untested
Goal-specified success/failure paths) + Grok's **Post-Diff Task-Frame
Shift** (the channel property — change the worker's JOB SHAPE over a
frozen authorized diff to audit-and-repair; never completeness text into
existing agents, never findings-only grading that already passed F7
dirty).

**Convergence receipts**: Grok R0 independent → S-A #1, rejecting
orchestrator's pre-round S-B-first. Orchestrator R1 WITHDREW S-B-first
with named delta (all receipts opened): (1) omission non-finding is
OBSERVED, repeated — F7 completed with carriers missing and VERIFY
passing on nodeg-20260713/-14/-17b; (2) S-B's repair executor is the
IMPLEMENT completion frame v4 just falsified; (3) channel-shape ledger —
instruction-into-existing-agent died 4×; post-diff repair-framed fresh
task is the only unfalsified shape and is bare-B's closing posture.
S-C dead (test-existence/USAGE-sync not command-shaped without fixture
literals; PHASE-0 derivation re-opens the v3-deleted synthesis channel).
Gold-gap flag (Grok, orchestrator-verified): F7 `hidden/reference.patch`
closes USAGE but has NO unsupported-format unit test → check 8 stays in
the falsifier as the measured QUALITY carrier, labeled gold-optional.

**Mechanism (M-SC SURFACE_CLOSE — one-shot post-IMPLEMENT audit+repair)**:
- Branch: `state.source.type == "generated"` AND `state.complexity ∈
  {trivial, medium}`. Skip: spec-mode, `--verify-only`, large.
- Placement: PHASE 2.5, after `implement_passed_sha` is set, BEFORE
  BUILD_GATE (repairs flow through the existing mechanical gates; CLEANUP
  is allowlist-wrong for additive tests; VERIFY is findings-only).
- Fresh worker; inputs = frozen `git diff base_ref…HEAD` + raw Goal bytes
  + `authorized_surface` + staged verification_commands AS DATA. Forbidden
  inputs: PLAN prose, IMPLEMENT transcript/reasoning.
- Obligation grammar (agent-decidable, zero fixture literals in harness
  text): UVR-STALE (diff modified symbol S's behavior AND an authorized
  file carries user-visible text documenting S's old interface omitting
  the newly specified option → minimal in-place update) + PATH-TEST (Goal
  specifies a success/failure path, diff implements it, no authorized
  test exercises it → one minimal regression test) + first-class EMPTY
  PASS (neither applies → empty diff, verdict PASS — the anti-accretion /
  B2/B5 guard).
- Mechanical envelope: post-spawn `git diff --name-only` ⊆
  authorized_surface; violation → ONE re-spawn with machine error; second
  → `BLOCKED:surface-close-out-of-scope` + revert to pre-spawn sha. One
  spawn only, never consumes `max_rounds`, hard timeout 600s.
- Edit surface (Grok R0 §3, file:line): SKILL.md:21 (declared-order
  amendment), :23 (halt conditions), :69-74 (post-implement invariant),
  ~:240 PHASE 2.5 insertion, :79 (budget exclusion); NEW
  `references/phases/surface-close.md`; state-schema.md
  `phases.surface_close`; state-phase-write.py phase-name allowlist;
  3 mirrors. NOT touched: implement.md/plan.md/always-loaded completeness
  prose; PLAN-side validators.
- Wall: one bounded spawn; wall stays OUT of the quality claim (0071);
  report median wall delta on F7/F25/drift; ship-reject if on-branch
  median wall > +1× same-complexity IMPLEMENT baseline or material
  timeout-abort rate. Token cap: resolve load-set ≤ +0.1% both gauges.

**Falsifier (pre-stated)**: rebuilt F7 (fresh nodeg, CLI pin): checks
1-6+9-10 HOLD, checks 7+8 FLIP to PASS; F25 objective non-regression
(regression → REJECT); drift battery green (stable-clean B2/B5 +
DB-failing-adjacent-test 0/4 — over-repair is the symmetric failure; six
drift-bait; violation matrix N=4 in band); thermometer check (shipped
harness text carries no fixture literals); `.devlyn` snapshotted while
rows are live (0072.8 instrument gap). CLEAN KILL: SURFACE_CLOSE runs,
envelope holds, Goal+diff present, and checks 7+8 still FAIL → mechanism
class DEAD → residual is engine-native completion behavior, measured at
the corpus/judge layer — no further harness lever for this class.

**Ratification protocol**: when the Codex window resets, Codex sol reads
this section + /tmp/codex-0072-r5/{packet,orchestrator-pre-round,
orchestrator-r1}.md + grok-r0.log and returns CONFIRM (freeze v5 as
registered) or a contested position (new round on the diff only). Build
remains Codex-delegated per the v3/v4 packet pattern.
