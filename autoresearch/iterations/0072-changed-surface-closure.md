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

## Registration v5 — SURFACE_CLOSE (M-SC), FROZEN 2026-07-17 evening, three-way converged (archives /tmp/codex-0072-r5/)

**Status: FROZEN, NOT BUILT.** Round arc: Grok R0 independent (S-A #1) +
orchestrator R1 named-delta withdrawal of S-B-first → 2-seat DRAFT while
Codex sol was usage-limited → user reset the limit same day → Codex
ratification round (independent position FIRST — its own R0 was a
read-only SURFACE_CLOSE evaluator inside VERIFY, withdrawn with named
delta "Observed Omission Non-Finding + Repair-Handoff Elimination":
July-13 F7 ended PASS_WITH_ISSUES leaving USAGE untouched; July-14
primary AND pair judges both passed the same omissions; a detector→
finding→IMPLEMENT handoff adds a hop without observed need) → verdict
**CONFIRM-WITH-EDITS, 5 exact edits** → Grok cross-confirm **5/5
CONFIRM** ("Freeze v5 with these five edits"). The five edits are
incorporated below (immutable inputs; one-attempt lifecycle; edit-surface
completion; attribution-gated falsifier; realistic token cap).

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
- Fresh worker; immutable inputs (Codex edit 1): PHASE 0 writes the exact
  resolved free-form Goal bytes to `.devlyn/goal.raw.txt` and records
  `state.source.goal_path` + `goal_sha256` (archived). After the
  IMPLEMENT checkpoint and before spawn, the orchestrator writes the
  immutable `git diff --binary base_ref…HEAD` to
  `.devlyn/surface-close.input.patch` and records `pre_sha` + its SHA-256
  under `phases.surface_close`. SURFACE_CLOSE validates both hashes
  before work; mismatch → `BLOCKED:surface-close-input-mismatch`. Inputs
  are those two immutable artifacts + `authorized_surface` + staged
  verification_commands AS DATA. Forbidden inputs: PLAN prose, IMPLEMENT
  transcript/reasoning.
- Obligation grammar (agent-decidable, zero fixture literals in harness
  text): UVR-STALE (diff modified symbol S's behavior AND an authorized
  file carries user-visible text documenting S's old interface omitting
  the newly specified option → minimal in-place update) + PATH-TEST (Goal
  specifies a success/failure path, diff implements it, no authorized
  test exercises it → one minimal regression test) + first-class EMPTY
  PASS (neither applies → empty diff, verdict PASS — the anti-accretion /
  B2/B5 guard).
- Lifecycle (Codex edit 2, replaces the draft's self-contradictory
  re-spawn/one-spawn text; Grok CONFIRM — "re-spawn was the weaker half
  of the contradiction"): exactly ONE SURFACE_CLOSE attempt. Record its
  pre-spawn SHA and untracked snapshot. Empty delta → PASS without
  commit. A non-empty delta wholly inside `authorized_surface` is
  scoped-staged and committed as `chore(pipeline): surface-close`. Any
  path-envelope violation, worker failure, or 600s timeout reverts only
  the pass-created delta and halts `BLOCKED:surface-close-<reason>`; no
  retry, no `max_rounds` consumption. The 600s cap is enforced by the
  monitored Codex route, bounded Claude subprocess route
  (`run-bounded.py`), or an equivalent native-task timeout; an
  unenforceable route blocks before spawn.
- Edit surface (Grok R0 §3 + Codex edit 3): SKILL.md:21 (declared-order
  amendment), :23 (halt conditions), :69-74 (post-implement invariant),
  ~:240 PHASE 2.5 insertion, :79 (budget exclusion); PHASE-0 raw-goal
  persistence/hash; PHASE-6 terminal-verdict and report phase lists
  (SKILL.md:315 region — without this the new phase disappears from
  terminal routing); NEW `references/phases/surface-close.md`;
  state-schema.md `phases.surface_close` + `source.goal_path/goal_sha256`
  + `BLOCKED:surface-close-*` verdicts; state-phase-write.py phase-name
  allowlist; `archive_run.py` patterns for `goal.raw.txt` +
  `surface-close.input.patch`; timeout/rollback and phase-state
  self-tests; lint needles; 3 mirrors. NOT touched:
  implement.md/plan.md/always-loaded completeness prose; PLAN-side
  validators.
- Wall: one bounded spawn; wall stays OUT of the quality claim (0071);
  report median wall delta on F7/F25/drift; ship-reject if on-branch
  median wall > +1× same-complexity IMPLEMENT baseline or material
  timeout-abort rate. Token cap (Codex edit 5; ≤+0.1% was arithmetically
  impossible — ~28 c4 tokens): root/shared prompt delta = 0; SKILL
  cold-start ≤ +2.0%; total resolve load-set ≤ +2.5% in both gauge
  approximations; excess → REJECT.

**Falsifier (pre-stated; attribution-gated per Codex edit 4)**: rebuilt
F7 (fresh nodeg, CLI pin): checks 1-6+9-10 HOLD, checks 7+8 FLIP to
PASS — and M-SC is causally diagnostic ONLY when
`.devlyn/surface-close.input.patch` (the pre-SURFACE_CLOSE patch) FAILS
checks 7 and 8 and the post-SURFACE_CLOSE patch PASSES both. If initial
IMPLEMENT already closes either carrier, the row is objective-valid but
non-diagnostic for that carrier: do not credit M-SC; rerun within the
frozen gate protocol. Archive raw Goal, input patch + hash,
`phases.surface_close` state, and final patch. F25 objective
non-regression (regression → REJECT); drift battery green (stable-clean
B2/B5 + DB-failing-adjacent-test 0/4 — over-repair is the symmetric
failure; six drift-bait; violation matrix N=4 in band); thermometer
check (shipped harness text carries no fixture literals); `.devlyn`
snapshotted while rows are live (0072.8 instrument gap). CLEAN KILL:
SURFACE_CLOSE runs, envelope holds, immutable inputs validated, and the
post patch still FAILS 7+8 → mechanism class DEAD → residual is
engine-native completion behavior, measured at the corpus/judge layer —
no further harness lever for this class.

**Ratification record**: Codex sol CONFIRM-WITH-EDITS (5 edits, all
incorporated above; named delta withdrawing its own VERIFY-evaluator R0
position); Grok cross-confirm 5/5 with falsifier acceptance unchanged;
orchestrator R1 named-delta withdrawal of S-B-first. 3/3 converged.
Build = Codex sol packet per the v3/v4 pattern.

**Pre-run check-numbering clarification (2026-07-18, mechanical
derivation — no design change; recorded before the gate run per the
Amendment-1 precedent)**: "checks 1-6+9-10 HOLD" inherited v4's
numbering. Under the frozen v5 edit surface ("NOT touched: free-form
prose levers; PLAN-side" — v4 stays reverted), v4 checks 3 (no binding
R/C/O) and 4 (scope-only plan grammar) are v4-lever artifacts that
CANNOT exist and are N/A; check 2's byte-preservation carrier in v5 is
`.devlyn/goal.raw.txt` (= new check 11, exact bytes + `goal_sha256`
match — Codex ratification edit 1 defines it as the byte carrier).
Applicable v5 gate set: 1 (source/complexity), 5 (authorized_surface ==
the two named files, sentinel-extracted from the semantic plan),
6 (diff ⊆ surface), 9 (bait byte-identical), 10 (oracle + tests),
11 (goal.raw.txt exact + hash), 12 (`phases.surface_close` +
input-patch hash), 13 (ATTRIBUTION: pre-SURFACE_CLOSE tree FAILS 7+8),
7+8 on the final tree. Decision logic unchanged: 7+8 flip with
attribution = lever works; post tree still failing 7+8 with envelope
+ inputs valid = clean kill. Concrete receipt of inapplicability:
`validate_scope_only_plan_text` no longer exists post-revert — a gate
citing it cannot run.

## Registration v5 FALSIFIED — F7 check 7; carrier 2 FLIPPED with clean attribution (2026-07-18; FIFTH valid-negative, and the first lever-caused closure)

Three-run gate arc, each run surfacing a distinct harness defect fixed by
a cross-confirmed amendment before the next attempt:

1. `nodeg-20260718`: SURFACE_CLOSE fired, produced the correct carrier-2
   repair, then ran the FULL test suite to validate — the fixture's
   pre-existing server tests fail listen-EPERM under the codex sandbox →
   fail-closed BLOCKED, byte-exact rollback. → **Amendment 2** (0072.11):
   workers execute nothing; validation belongs to BUILD_GATE; phase
   bodies pass VERBATIM (the A-arm orchestrator had appended its own
   "run node --test yourself"). Grok CONFIRM; Codex OBJECT adopted at
   the shipped-text root.
2. `nodeg-20260718b`: the sonnet A-arm orchestrator staged the v5 skill
   (state template proves it) yet silently skipped PHASE-0 goal
   persistence AND the PHASE 2.5 dispatch; 7 phases PASS. Same class as
   iter-0071's non-enforced omission. → **Amendment 3** (0072.12):
   verify-merge-findings.py state blockers
   `verify.state.goal-persistence-missing` +
   `verify.state.surface-close-skipped` — skip becomes mechanically
   fatal. 3/3 CONFIRM. (Side receipt: IMPLEMENT closed carrier 2 itself
   that run — variance — but left USAGE stale and VERIFY passed it: the
   4th observed omission non-finding.)
3. `nodeg-20260718c` — first DIAGNOSTIC row (VERDICT + full artifact
   set incl. live-snapshot `.devlyn`): every lifecycle/information/
   attribution check PASS; **SURFACE_CLOSE delta = exactly the
   unsupported-format exit-1 test → check 8 FLIPPED BY THE LEVER**;
   check 7 FAIL — the worker read the USAGE block (log receipts) and
   silently declined UVR-STALE, final message bare PASS + test diff.

Frozen all-checks gate → no-ship; reverts `1b32fb1`/`335aa3e`/`f0a5836`;
mirrors re-synced; reverted self-tests PASS; STOP.

**The class SPLIT — the central finding.** Neither pre-registered
falsifier branch assumed heterogeneity, and both missed: test-shaped
closure (PATH-TEST) is lever-reachable in the audit+repair frame;
documentation-sync closure (UVR-STALE) resists its SIXTH channel even
with the obligation delivered verbatim to a dedicated auditor holding
the file open. Seat note: the SC worker ran on codex (executor pin);
bare-B — the arm the blind judges prefer — closes USAGE reading the
same task. Seat/frame interaction is unmeasured; that is round-6's
first axis, alongside UVR-obligation decidability and a revisit of
mechanical staleness derivation under the split receipt. Never prose.

## Registration v6 — Adjudicated SURFACE_CLOSE (M-SC-A), FROZEN 2026-07-18, three-way converged (archives /tmp/codex-0072-r6/ + /tmp/grok-0072-r6/)

**Status: FROZEN, selection-first — no skill build until a replay cell
graduates.** Round arc: orchestrator packet (License Asymmetry under
Imported Suppressor Stack; levers L1 verdict-contract / L2
suppressor-subtraction / L3 seat / L4 mechanical-derivation-held; replay
selection) → Grok R0 independent (FDC-LA criterion; converged on the
package with 4 named deltas + 5 citation defects incl. D1 HIGH
inspection-depth) → Codex R0 (independent position "Adjudication Gate";
DISCOVERED the surviving nx01 worker session rollout; AGENTS.md-auto-load
receipt kills L2-as-registered; L4 recall gap — `version` not derivable
from modified symbol names) → orchestrator R1 named deltas (L2 WITHDRAWN
wrong-carrier; L5 ambient-residue FALSIFIED zero-`.devlyn`-reads;
criterion's suppressor-deletion clause dropped) → Grok cross-confirm
**CONFIRM-WITH-EDITS (2 edits, both strictly stricter)** with its own
named delta withdrawing "L2 mandatory in preferred cell". 3/3 converged.

**Rollout receipts (archived `7b42b29`
`gate-fail-artifacts/worker-session-rollout.jsonl` + `f7-row-repo.bundle`;
all three seats re-opened them independently)**: worker model
`gpt-5.6-terra` in-session (state's `gpt-5.5` = orchestrator fill-in
defect); worker ran exactly 4 tool calls — sanctioned hash check, diff +
full test read, **`nl -ba bin/cli.js` (full file, USAGE lines 8-18 with
the `hello [--name NAME]` sibling convention in context)**, apply_patch —
then final message `PASS` with PATH-TEST reasoning and ZERO UVR words:
declined AFTER full-file read (Grok D1 resolved; "non-inspection"
explanation dead); ZERO `.devlyn/plan.md`/criteria reads (ambient-residue
leak falsified as this row's cause); assembled prompt DROPPED the
`<runtime_principles>` read-sentence (assembly deviation — SKILL.md:27
excerpt-inline vs Amendment-2 verbatim are themselves in tension) while
the codex adapter header instructs "Do not narrate internal deliberation"
(silent exit adapter-encouraged); root `AGENTS.md` present in worker cwd
(`?? AGENTS.md` in the worker's own git-status output) → phase-local
suppressor deletion removes duplication, not the suppressor.

**Decisive criterion (Codex, adopted 3/3): Observed-Degree-of-Freedom
Closure** — v6 mechanically eliminates the exact freedom exercised in
nodeg-20260718c (silent per-obligation decline inside a legal bare `PASS`)
without perturbing proven PATH-TEST behavior and without pretending
semantic staleness is mechanically decidable. Grok's **FDC-LA**
(free-disposition closure under license asymmetry) is retained as the
behavioral HYPOTHESIS the matrix tests, not a design lever.

**Mechanism (single lever L1 — Adjudication Gate)**: worker terminal
message MUST contain, per obligation, exactly one of
`UVR-STALE: FIRED <authorized-file>:<line>` or
`UVR-STALE: N/A <authorized-file>:<line> — <one-line evidence-based
relationship judgment>` (same grammar for PATH-TEST), then `PASS`. Bare
`PASS`, missing rows, out-of-surface or nonexistent citations →
mechanical BLOCK at the phase boundary (surface-check extension,
Amendment-3 class). EMPTY PASS stays first-class = two evidenced N/A
rows. Obligation grammar, envelope, one-shot lifecycle, 600s bound,
immutable inputs unchanged from v5. Assembly defined mechanically:
adapter header + canonical body VERBATIM, body made self-contained (no
runtime-file read-sentence → verbatim and excerpt-inline stop
conflicting), assembled bytes hashed to
`phases.surface_close.prompt_sha256`. Prerequisite commits, separate
from the mechanism diff: (1) state-integrity — record requested +
effective model parsed from the engine session header, mismatch →
attestation fail (receipt: `gpt-5.5` fill-in); (2) instrument retention —
full worker rollout archived into run artifacts (receipt: D1 was
undecidable from the 2KB tail alone).

**Selection instrument (probe tier, HANDOFF rule 7 — replay BEFORE any
nodeg; frozen inputs, no command execution per Amendment 2)**: replay the
SC worker against the EXACT pre_sha tree `947dbf71…` from
`f7-row-repo.bundle` (fallback: neutralized-seed reconstruction with
carrier-state assertions). F1 = the rollout's actual assembled prompt
bytes; FL1 = F1 + the Adjudication Gate output contract (only delta).
Adaptive 4-cell: {F1, FL1} × {codex gpt-5.6-terra, claude sonnet},
2 replicas per cell; 0/2 UVR fire → cell stops (no 3rd); any fire → 3rd
replica; max 12 F7 replays (Grok Edit 2). Per-run receipts: effective
model, CLI version, prompt hash, pre-tree hash, output/diff hashes,
fresh home. Readout: UVR fired / PATH-TEST fired / verdict rows parse /
delta bytes (`f7-carrier-gate.py` checks 7/8 static).

**Graduation ladder (Grok Edit 1 — accuracy-green required)**: any cell
≥2/3 UVR fire → that cell runs accuracy controls (no-stale row +
genuinely-ambiguous row — over-repair/false-FIRED guard, B2/B5 discipline
at probe tier); ONLY accuracy-green cells graduate → freeze v6 final
skill text → ONE fresh nodeg diagnostic row under the UNCHANGED
all-checks gate (attribution check 13 as in v5). F1×sonnet ≥2/3 AND
accuracy-green → seat-routing IS the mechanism; L1 not registered (all
three seats' falsifier 1). **No cell reaches ≥2/3 UVR fire with accuracy
controls green** within max 12 replays (+ control budget on fire cells)
→ documentation-sync residual ACCEPTED: audit-frame class closed for
UVR, measurement moves to corpus/judge layer, iter-0072 closes with the
split as its terminal finding (pre-committed kill branch,
anti-asymptotic stop). Stage-2 ablation cells only if L1 wins and
attribution demands it, or systematic false N/A appears: clean-room
worker cwd (no AGENTS.md / `.devlyn`) as the true ambient-contract
ablation; F3 minimal-neutral. Grok early-L4 trigger retained verbatim:
systematic false N/A citing non-inspection while candidate UV strings
exist → promote L4 behind an independent positive/negative recall oracle
(Codex counter stands: `version` is not recoverable from modified symbol
names — r5 rejection holds until a generic extractor passes that oracle).

**Predictions (orchestrator, recorded pre-experiment)**: P(F1×terra UVR
fire) ≈ 0.10 (reproduce silent decline); P(F1×sonnet) ≈ 0.35;
P(FL1×terra) ≈ 0.60; P(FL1×sonnet) ≈ 0.65. P(kill branch) ≈ 0.25.

**Anti-overfit scope**: six channels have iterated against F7's USAGE
carrier; any v6 closure is row-class-scoped. "Documentation-sync class
closed" additionally requires a fresh held-out UVR row authored by an
excluded seat (0070a.6 precedent) — pre-registered as the claim gate,
not part of this selection. Test arms per user directive 2026-07-18:
claude = sonnet, codex = terra; sol team-only; fable never a test arm.

## v6 replay matrix RESULT + three-way adjudication (2026-07-18; runs r6-replay-20260718, commits 3cd3809+)

**Raw**: 12/12 receipts-valid; corrected oracle (check8 colon fix, live-
precedent-verified) gives UVR/PATH = F1-terra 3/3·2/3, F1-sonnet 3/3·2/3,
FL1-terra 3/3·1/3 (2 confident false-N/A on PATH), FL1-sonnet 3/3·3/3
(only dual-closure cell, verdict rows clean). All four orchestrator
predictions (.10/.35/.60/.65) busted high — recorded raw.

**Supersession (3/3 agree)**: the v5 split story ("documentation-sync
resists the audit frame") rested on n=1 and is DEAD — UVR fires 12/12
including the v5-verbatim live seat; F1-terra r02 mirrors the live row on
the OTHER obligation (USAGE-only + bare PASS). Revised phenomenon
(Codex formulation adopted): **stochastic per-obligation omission,
followed by seat-conditioned adjudication** — ungated workers silently
drop one obligation draw-dependently; L1 on terra converts omission into
confident false-N/A (Grok R0 §1a evidenced); L1 on sonnet closes both.
v6's criterion (Observed-DoF Closure) survives intact.

**Seat disagreement adjudicated** (Grok: graduate FL1-sonnet, execution
note = Low; Codex: BLOCKING — 3 sonnet replicas executed validation,
matrix incomplete, rerun): orchestrator verified Codex's three citations
in the preserved worker transcripts and ran the symmetric
defined-predicate audit over all 12 (execution-audit.json; predicate =
fixture validation execution: npm test / node --test / node -e / git
stash; read-only inspection allowed per the live worker's own
shasum/git/nl precedent). Result: terra 6/6 clean; exactly F1-sonnet
r01+r03 and FL1-sonnet r03 contaminated. **Named criterion:
Phase-Faithful Sample Crediting** — a replica is credited only if the
worker stayed within the replayed phase's own execute-nothing contract;
the FROZEN bars then apply to credited replicas, unchanged. Credited
arithmetic: FL1-sonnet 2/3 UVR fire (≥2/3 bar MET; 2/2 dual-closure,
zero false adjudication) → **graduates to accuracy controls**; F1-sonnet
1/3 (seat-routing branch definitively NOT met — resolves the branch
divergence under either validity reading); FL1-terra negative (L1
harmful on terra — never ship L1 to terra SC workers from this data).
Codex's further demands REJECTED with citation: a "3-valid-replica
graduation threshold" and "factorial-necessity proof" appear nowhere in
the frozen registration (bar = "≥2/3 UVR fire"; ladder branch decides
the composite); a full rerun is not licensed when the frozen bars are
decidable on credited samples. Codex's defect findings ACCEPTED:
execution-audit gap (now a mechanical audit artifact + probe patch
queued), sonnet transcript + prompt-bytes durability (all 12 transcripts
+ both prompt files committed into the results dir).

**Honest residuals**: (1) L1-necessity-on-sonnet unproven — the single
credited F1-sonnet replica dual-closed WITHOUT L1 (n=1); the composite
proceeds per the frozen ladder (seat-routing branch failed), and the
nodeg row remains the ship gate. (2) Live-row UVR decline vs 12/12
replay fire stays a variance/fidelity note (Q2, both partners: no longer
gates selection). (3) 12/12 UVR fire is uninterpretable against
over-repair until controls run — next step.

**Next (frozen order)**: (1) probe patch — mechanical validation-
execution audit into receipts + transcript/prompt archival (Codex Q6);
(2) accuracy controls authored OUTCOME-BLIND by a fresh excluded seat
(opus; D-protocol precedent), Grok UNFAIR audit + hash freeze, then
no-stale + goal-frozen-USAGE controls on FL1-sonnet, bar 2/2 correct
disposition + zero false-FIRED/forbidden edits per control (Codex's
stricter zero-tolerance adopted); (3) green → freeze v6 composite skill
build (claude-routed SURFACE_CLOSE + L1) → ONE fresh nodeg row,
unchanged all-checks gate; red → no graduation, kill branch stands.

## Accuracy controls GREEN + Amendment 4 (FIRED grammar) — 2026-07-18 (commits 1ee0085/04fba07+)

**Controls verdict (3/3 GREEN)**: control-b-goal-frozen 2/2 credited
fully correct (both N/A rows citing the freeze clause, empty delta);
control-a-no-stale substance-correct on both execution-clean replicas
(UVR N/A already-current evidence + PATH FIRED + test-only delta), with
r01/r04 validation-execution contaminated (mechanical audit caught them,
replacement scheduling worked). Zero false-FIRED / forbidden edits in
ANY replica → **over-repair NOT observed; the 12/12 UVR fire is
discrimination, not compulsion**. Crediting ruling (Grok CONFIRM +
Codex CONFIRM + orchestrator): the frozen control bar (0072.15) is
disposition + false-fired + forbidden-edits; the parser's
adjudication-format rejection is selection-matrix crediting machinery,
"a format-crediting defect, not a control-bar failure" (Codex).
Controls were outcome-blind authored (fresh opus seat, blinding
statement in AUTHORING.md) and Grok F21 UNFAIR-audited FAIR pre-run.

**Amendment 4 — FIRED-row grammar (registered for the v6 build; parser
+ self-test update lands with the build)**: control-A's clean replicas
appended ` — <evidence>` to FIRED rows and were parser-rejected;
matrix FL1-sonnet credited replicas used BARE FIRED. Both shapes occur
in correct runs, so an exclusive grammar in either direction causes
spurious production BLOCKED halts. Seat split adjudicated with a named
criterion — **No-Spurious-Halt on Observed-Correct Output Shapes**: the
grammar must accept every shape that occurred in credited correct runs.
Adopted: `FIRED <file>:<line>` with OPTIONAL ` — <one-line evidence>`
tail (Grok's position; parser treats the tail as evidence, per Codex);
N/A keeps its REQUIRED evidence tail (evidence-free N/A is exactly the
silent-decline risk). Named delta vs Codex's mandatory-tail: the
matrix's own graduated replicas were bare-FIRED — requiring the tail
fails the same test that motivated the amendment.

**GRADUATION COMPLETE**: FL1×sonnet is accuracy-green. Remaining to
close iter-0072 (next session): (1) v6 composite SKILL build — claude-
routed SURFACE_CLOSE + L1 adjudication contract with Amendment-4
grammar, Amendments 2+3 binding, prerequisite commits (effective-model
state integrity; worker-rollout retention); (2) ONE fresh nodeg
diagnostic row under the UNCHANGED all-checks gate — the ship decision.
Honest residuals carried: L1-necessity-on-sonnet n=1; live-row decline
= variance/fidelity note; row-class scope (held-out UVR row gate before
any class-closed claim).

## v6 composite build SHIPPED (2026-07-18 night; commits ebe4626/bd39a96/af91dad/6b63157)

Three-seat loop: Codex sol executor; orchestrator mirror-sync + scoped
commits (codex 0.144.5 sandbox classifies `.agents/` as outside the
project — protocol: codex edits `config/skills/**` + `scripts/` only,
orchestrator derives both mirrors and commits); Grok independent audit
GO-WITH-EDITS. Stack: (a) `ebe4626` effective-model attestation
(`model_requested`/`model_effective` parsed from engine session evidence
— exec header `model:` line / rollout `turn_context.payload.model` /
claude-result sole `modelUsage` key; mismatch or bad evidence → BLOCKED
+ exit 1; live receipt: single sonnet `-p` call yields exactly one
modelUsage key, so multi-key conflict-BLOCK is fail-closed, not a live
false-positive); (b) `bd39a96` mutation-worker rollout retention
(`<phase>.worker-session.<round>.jsonl` patterns; engine-global scans
forbidden + negative self-test); (c) `af91dad` mechanism — SURFACE_CLOSE
restored with claude seat routing, FL1 canonical body + Amendment-4
grammar in `<output>`, VERBATIM assembly hashed to
`phases.surface_close.prompt_sha256`, surface-check = adjudication-row
parser (missing/malformed/duplicate/out-of-surface/nonexistent-citation
/bare-PASS → BLOCK; EMPTY PASS = two evidenced N/A + empty delta) +
retained-rollout execution audit (session file missing → BLOCK, which
mechanically forces retention) + Amendment-3 VMF merge-boundary
enforcement (schema-v3-gated; canonical skip only); (d) `6b63157` Grok
Edit 1 predicate parity (`node bin/|node tests/` restored to match
`r6-replay-cell.py:73` — the predicate that credited the graduated
matrix) + Edit 2 seat fail-closed at spawn (`--engine claude` required,
state-mutation-free reject). Convergence 3/3: Grok "no other edits
required"; Codex R1 agreement, zero named deltas.

Token-cap baselines (recorded per Grok E-axis finding): registered
0072.10-edit-5 cap applies to the MECHANISM diff — SKILL c4 +1.998% ≤
2.0%, load-set +2.279% ≤ 2.5% (independently recomputed); full 4-commit
stack including prereqs = c4 +3.75% / w13 +2.99% (transparent, not the
registered cap basis). Acceptably-residual (Grok, watched on the row,
not pre-blocked): claude session-JSONL acquisition is instruction +
fail-closed-on-missing, assembly content-equality is hash-of-written-
file (mechanical assembler = new surface without a mis-assembly
receipt).

Ship gate next: ONE fresh nodeg diagnostic row `nodeg-20260718d` (F7,
`--v5` gate incl. check 13 attribution, CLI pin 2.1.211 as the v5-arc
identity, seats claude=sonnet / codex=terra, `.devlyn` snapshot live).

## nodeg-20260718d — first live dual-carrier closure; ship credit ADJUDICATED NO (3/3); instrument fixes pre-registered (2026-07-18 night, ceeaf4e)

**Row facts (all receipts committed under the results dir)**: CLI pin
2.1.211, sonnet orchestrator / terra executor / SC=claude (spawn seat
guard exercised). SURFACE_CLOSE one-shot 189.6s: `UVR-STALE: FIRED
bin/cli.js:12 — <evidence>` + `PATH-TEST: FIRED tests/cli.test.js:33 —
<evidence>` + `PASS`; both carriers in the final patch; pre-SC input
patch carries NEITHER → attribution clean (check 13 PASS). First live
dual closure in six registrations; Amendment-4 tailed-FIRED shape
exercised (pre-Am4 grammar would have BLOCKED this correct run).
Objective bar PASS (sealed neutralized oracle 1/1, hidden 0). Terminal
PASS_WITH_ISSUES.

**Gate readout 9/11** (`--v5 --post-implement`, unchanged code):
FAIL 11 goal bytes 673/674 — root cause = LAUNCHER
(`run-ceiling-arm.sh` json_quote_task_prompt does `.rstrip("\n")` then
inline goal; sonnet persisted exactly the bytes received; orchestrator's
initial "sonnet PHASE-0 defect" attribution RETRACTED, Grok's D-class
R0 attribution likewise retracted). FAIL 10 — instrument context:
in-place oracle sees harness residue the sealed instrument neutralizes;
gate's hardcoded PATH resolves node v25.4.0 vs harness nvm v20.19.0
(tests 8/8 on v20, fail on v25; both reproduced in the live worktree).
Also retracted: "sonnet judge A_win is new" (nodeg-20260714 F7 already
sonnet 3/4 A_win vs codex 4/4 B). Quality bar stays FAIL under the
frozen both-judges rule; wall 37.4× recorded (0072-out-of-scope, 0071
owns it).

**Adjudication (Grok R0 SHIP/MASP vs Codex R0 NO-SHIP/Ex-Ante → R1
converged 3/3)**: (1) NO ship credit from this row — **Ex-Ante Gate
Authority** (Codex, adopted wholesale): "all checks" cannot become
"all mechanism-attributable checks" after the outcome is visible; gate
stays honest at 9/11, no reclassification, MASP demoted (post-hoc-named).
(2) v6 stays **LANDED, NOT ship-credited** — revert is keyed to
falsification receipts (all five prior reverts followed falsifications;
this row has none); Codex yielded with its own named delta
**Invalid-Row Continuation Precedent** (v5 arc retained the candidate
through two harness-invalid rows; revert fired only on the valid
falsifying row). A falsifying valid re-row still reverts.
(3) **Pre-registered instrument fixes required before the re-row**:
(i) launcher byte transport — pass the task via `--goal-file`, stop
rstrip+inline, so check 11 is satisfiable; (ii) gate check-10
post-archive semantics — neutralized workspace + runner-pinned node,
not residue-bearing worktree on PATH node 25; (iii) engine-session-log
coupling — this row recorded `model_effective: null` on every phase
while the retained worker-session JSONL says `claude-sonnet-5`;
completion must fail closed when a retained session file exists but no
`--engine-session-log` was passed. Then ONE fresh nodeg diagnostic row
= the ship decision. iter-0072 does NOT close on this row.

**Carried residuals**: L1-necessity-on-sonnet n=1; held-out UVR row
(excluded-seat authored) still gates any "class closed" claim; quality/
wall bars unchanged.

## nodeg-20260718e — instrument fixes VALIDATED; non-diagnostic row; live execute-nothing violation caught; Amendment-5 design opened (2026-07-18 late night, 7d9d36a/be61dbd)

**Instrument fixes 3/3 landed** (`7d9d36a`, Codex round-5 + orchestrator
node_modules amendment CONFIRMED): launcher `--goal-file` byte transport;
gate check-10 transported neutralized workspace + `CEILING_TEST_NODE_BIN`
pin (+ dependency-artifact node_modules copy — MODULE_NOT_FOUND receipt);
SPW fail-closed session-log coupling. Validation on the OLD row
(20260718d workspace): 10/11 — check 10 flipped PASS (oracle 0 /
node--test 0 on pinned v20), only check 11 remains (old-launcher
artifact, retroactively unfixable). Grok round skipped by the
anti-asymptotic rule: fixes match Grok's own R0 required-fixes table;
the only new element carried a byte receipt and Codex reviewed it.

**Ship row nodeg-20260718e (runner 7d9d36a, CLI 2.1.211)**: gate 9/11
with a NEW shape — checks 11+10 now PASS (fix validation), but check 13
attribution FAIL pre8=True: this PHASE-0 criteria draw included the
yaml exit-1 verification command (674-byte goal via --goal-file), so
IMPLEMENT closed check 8 itself — stochastic draw (20260718d's was
yaml_exit1=False), row NON-DIAGNOSTIC per the frozen v5-edit-4
attribution rule → rerun licensed. THE MECHANISM EVENT: SC worker
adjudicated PERFECTLY — `UVR-STALE: FIRED bin/cli.js:12` with a correct
minimal USAGE repair, `PATH-TEST: N/A` with correct evidence (IMPLEMENT
had covered all three paths; zero false rows) — but among 16 Bash calls
(15 sanctioned read-only inspection) ran `node --test tests/` ONCE. The
v6 execution audit caught it → `BLOCKED:surface-close-validation-
execution` → surface-rollback discarded the CORRECT repair → check 7
FAIL on the final tree, terminal BLOCKED. Live confirmation of the 5/12
probe rate on the production seat; enforcement layers (audit + rollback
+ halt) all fired as designed; the discipline cost = a correct repair
died with the violation. Objective bar PASS (sealed oracle; IMPLEMENT
diff resolves), wall 18.4×, quality FAIL (frozen rule). Also observed:
`model_requested`/`model_effective` null on SC despite fix (iii) live —
the surface-check BLOCKED path bypasses the `complete` verb where the
coupling lives (gap to close with Amendment 5).

**Amendment-5 design round OPENED (three-way R0 in flight at close)**:
structural execute-nothing — spawn the SC claude worker WITHOUT
execution tools (Read/Grep/Glob/Edit/Write; no Bash), VERIFY-symmetric
spawn-level constraint making Amendment-2 violations impossible rather
than punished; worker self-hash sentence becomes deletable (SPW already
dual-hash validates mechanically); audit stays as backstop; probe-tier
replay validation (FL1×sonnet with restricted tools) BEFORE any live
row. Alternatives on the table: audit-only status quo (rerun-and-pray
against a ~40% violation rate), rollback-scope change (rejected shape:
crediting work produced under violation breaks Phase-Faithful
crediting). Positions land in the next addendum; nothing ships without
a frozen registration.

## Amendment-5 design round CONVERGED (three-way R0, 2026-07-18 late night; logs archived in row-artifacts of -20260718e — copy pending)

**Both seats GO on both decisions** (Grok + Codex independent R0s over
opened receipts): (1) Amendment 5 = structural execute-nothing — spawn
the SC claude worker with tool AVAILABILITY restricted to
Read/Grep/Glob/Edit/Write (Codex: must be `--tools`, not
`--allowedTools`-only — availability vs permission; CLI 2.1.211 exposes
it), delete the worker self-hash sentence (SPW dual-hash already
mechanical at spawn + surface-check), keep execution audit + rollback
as backstops; (2) NO rerun before Amendment 5 + restricted-route replay
validation. **Criterion (Codex, adopted): Phase-Legal Action-Space
Equivalence** — a structural restriction is admissible iff every valid
phase action stays expressible through allowed tools, the invalid class
becomes unavailable (not discouraged), and exact production-route
replay preserves the pre-existing accuracy bars (FL1×sonnet ≥2/3 +
both controls 2/2, ladder UNCHANGED). Falsifier (pre-registered): the
restricted-route cell missing ≥2/3, either control losing correct
disposition, or the runtime being unable to both exclude Bash and
retain auditable/model-attested evidence → Amendment 5 NO-GO, no live
row.

**Record corrections (orchestrator retractions on seat receipts)**:
(a) the worker ran `node --test` TWICE (session jsonl lines 41+50; 14
of 16 Bash calls were read-only) — my "once" was wrong; (b) matrix
validation-execution was 3/12 (sonnet-skewed) + 2 control replicas —
my "5/12" conflated runs; (c) "surface-check bypasses the complete
verb" RETRACTED — fix (iii)'s coupling FIRED
(`BLOCKED:model-attestation-failed` in the row state): the actual gaps
are (i) the parser lacks the claude-native `message.model` carrier
(retained JSONL records it on assistant events; neither
`turn_context` nor `modelUsage` shapes match), and (ii) SC spawn
omitted `--model` though the arm manifest pinned sonnet. **Attestation
fix frame (both seats aligned)**: restricted `claude -p
--output-format json` route supplies the parseable `modelUsage`
wrapper for completion evidence while the retained full JSONL serves
the execution audit; `--model` required at SC spawn (pre-registered
requested-model, never silently null).

**Next session**: freeze the Amendment-5 composite text (this section
is the frame; no re-design) → Codex builds (config/scripts only;
orchestrator mirrors) → restricted-route FL1×sonnet + controls replay
(probe tier) → green → fresh diagnostic row = the ship decision.
