# iter-0065 — hands-free large-goal delivery (lever A) + bounded pair-VERIFY (lever B)

status: CLOSED 2026-07-07 — both levers SHIPPED and live-verified.
Lever A: FS1-class hands-free break closed (P1 A2 full delivery, hidden
oracle 14/14 vs iter-0064's 0-byte; zero-signal + measurement-integrity
halts preserved). Lever B: 600s pair-judge budget both directions +
TIMEOUT carrier live (self-tested; bound never fired on the live run).
Plus one live-caught new class fixed in-iter (backgrounded wrapper call
killed at headless wind-down). R0 SHIP-WITH-EDITS (all 4 MUST-FIX + 3
SHOULD-FIX adopted); R1 **VALID-WITH-EDITS** (one AGENTS.md orphan,
fixed). Archives `/tmp/codex-iter0065/`. Both levers adopted at
iter-0064 R1 from tranche-1 product findings; artifacts re-opened and
decomposed this session before design.

**Serves**: Mission 1 ceiling axis — tranche-1 verdict was FAIL-pilot on
LC3 efficiency with a 0-byte hands-free break (FS1) and a burned delivery
window (SW2) as the two named product findings. This iter closes both
failure classes; ceiling tranche 2 re-measures after.

## Why this exists (pre-flight 0)

One sentence: this iter removes two user-visible failures measured in
`benchmark/ceiling/results/iter0064-t1/` — (a) `/devlyn:resolve` delivered
0 bytes on a fully-specified feature goal that bare codex shipped 14/14
(FS1 A1), and (b) a resolving run burned to the 3600s cap after all build
phases PASSed (SW2 A1).

Mission-bound (#7): Mission 1, ceiling contract / ops test #17 — the
instrument exists and was lost on efficiency; these are the pilot's two
R1-adopted levers, prerequisite to tranche 2.

## Lever A — hands-free spec-shaped free-form goals

### Evidence (all opened this session)

- `free-form-mode.md:52-64` — Large branch fires on `goal_length > 80` OR
  `file_scope_signals > 10`; default action `BLOCKED:large-needs-ideation`.
- FS1 A1 `criteria.generated.md` (workspace archive): goal_length 214,
  file_scope_signals >10, verb `add` → large → default halt. Wall 270s,
  exit 0, patch empty. Bare AND copycat codex: hidden tests 14/14.
- `SKILL.md:64`: "No mid-pipeline prompts in any branch" — the skill's own
  contract is hands-free.

### Why-chain → violated invariant

1. Why 0-byte? PHASE 0 halted (`large` default).
2. Why large? 214 words > 80; >10 symbols.
3. Why do those signals mean halt? They proxy "design decisions the harness
   cannot make" — but both signals GROW with specification completeness.
   **Violated invariant: the gate should measure under-specification
   (missing design decisions); it measures verbosity/breadth, which
   anti-correlates on spec-shaped goals.** A fully-specified goal is
   punished for being complete, inside a skill whose contract forbids
   asking. Found at depth 3; stop.

### Fix (default-flip + flag delete; subtractive-first)

- Large **action** becomes what `--continue-on-large` does today:
  synthesize a best-effort spec with an explicit `## Assumptions` block,
  log `recommend: /devlyn:ideate first` in criteria + final report,
  proceed. Assumptions must be scope-narrowing and reversible (queue-drain
  precedent, CLAUDE.md).
- **Zero-signal carve-out (R0 MUST-FIX 1, Class-Purity Boundary)**: the
  Large branch bundles two classes — spec-rich goals (>80 words / >10
  signals) and vague goals (`file_scope_signals == 0`, "the classifier
  cannot pick scope"). FS1 proved only the first unsafe to halt. When the
  large classification includes zero file-scope signals, assumptions would
  be scope-INVENTION, not narrowing → still halt
  `BLOCKED:large-needs-ideation` (same string; the narrowed class is
  exactly the "needs ideation" case). All other Large paths flip.
- **Delete `--continue-on-large`** (CLAUDE.md flag rule:
  default-fix-and-delete-flag; the flag was never even defined in the
  SKILL.md flags block — only referenced at `SKILL.md:98,321`).
- Classifier signals and trivial/medium branches UNCHANGED — only the
  Large action changes. No new signal (a spec-shape detector would be an
  addition without a failure it uniquely prevents; the flip alone closes
  FS1).
- UNCHANGED halts: `BLOCKED:solo-headroom-hypothesis-required`,
  `BLOCKED:solo-ceiling-avoidance-required` (measurement-integrity class —
  they already override the flag today), and all `BLOCKED:goal-file-*` /
  `BLOCKED:invalid-flags` input fail-closed halts.
- Downstream synergy kept: free-form `state.complexity == "large"` remains
  a canonical pair-VERIFY trigger (`complexity.large`), so assumed-defaults
  runs keep the extra audit — now bounded by lever B.
- Doc surface: `CLAUDE.md:56` rationale sentence ("routes into
  `BLOCKED:large-needs-ideation`") goes stale → rewrite: a spec file is the
  user's reviewed contract; free-form large now assumes-and-logs.

## Lever B — bounded pair-VERIFY (wall-budget abort)

### Evidence (artifact decomposition, opened this session)

SW2 A1, wall 3600s cap (`timing.json` exit 124): pre-VERIFY consumed
2205s = 61% (phases 1702s incl. probe_derive 484s + ~503s orchestrator
gaps); inside VERIFY: mechanical ~15s → primary codex judge 275s → pair
claude judge 143s ending `VERDICT: PASS` at 20:02:22Z → one Bash error +
an orchestrator API request at 20:04:53.729Z with **zero further
debug-log activity until the external cap kill (~11 min stall)**
(`claude-debug.log` ends mid-request).

**Named delta vs iter-0064's framing** ("pair audit consumed the
window"): that claim was written from `timing.json` + phase verdicts; the
new evidence (`.devlyn` mtimes + debug-log tail) shows the pair judge
PASSed 13 minutes before the cap. The window was consumed by pre-VERIFY
overhead plus a terminal orchestrator transport stall — the judges cost
~7 min. The reframe narrows lever B's shippable surface.

### Why-chain → violated invariant

1. Why did a resolving run record as timed out? VERIFY-path work after
   delivery existed had no wall bound; only the external benchmark cap
   ended it.
2. Why is the pair path unbounded? **PRINCIPLES.md #6 operational test
   already requires every pair-mode phase to specify "a wall-time budget
   abort … fall back to solo, surfaced explicitly — not silently." The
   pair-VERIFY contract shipped and was extended (iter-0060/0062/0063,
   `--pair-verify` convention) without that budget abort.** Violated
   invariant found at depth 2; stop. Corroborating same-class observation:
   codex compliance cell hung ≥2.5h idle (iter-0064 follow-up #4).

### Fix (mechanical budget + honest timeout carrier)

- **Pair-judge wall budget, both directions, mechanical**: codex judge →
  `CODEX_MONITORED_TIMEOUT_SEC=600` (mechanism exists,
  `codex-monitored.sh:44,73`, live-verified iter-0012; wrapper exits 124
  on watchdog fire). Claude judge → **portable budget runner
  `_shared/run-bounded.py 600 -- claude -p …`** (R0 MUST-FIX 2: bare
  `timeout 600` is command-not-found on stock macOS — `command -v
  timeout` empty on this host, iter-0003 precedent; python3 is already a
  hard pipeline dependency; runner kills the process group and exits 124).
  600s ≈ 4× max observed pair-judge wall (143s) and >2× max observed
  primary wall (275s), far below the 20-30 min window-loss class.
- **Timeout semantics (R0 MUST-FIX 3, Observed-Finding Preservation)**:
  judge subprocess exit 124 → orchestrator writes marker
  `.devlyn/verify.pair.timeout.json` `{engine, budget_seconds}` before
  merge. `verify-merge-findings.py` three-case contract, self-tested:
  1. marker + no parseable pair findings (canonical empty, stdout has
     none) → `sub_verdicts.pair_judge: "TIMEOUT"`; partial stdout is
     diagnostic; merged verdict from mechanical + primary; summary AND
     final report header carry "solo verdict after pair TIMEOUT" (R0
     SHOULD-FIX 2). Never silent; never `BLOCKED` for a budget abort.
  2. marker + complete verdict-binding findings (canonical file OR
     parseable stdout JSONL) → findings BIND (`NEEDS_WORK`); a timeout
     never discards an observed finding.
  3. no marker + missing/empty pair output → existing emission-contract
     `BLOCKED` behavior, byte-for-byte unchanged.
- Applies to AUTO and explicit `--pair-verify` triggers alike: PRINCIPLES
  #6 governs budget overruns universally; the no-workaround ban is on
  availability downgrades — an engine that RAN and overran is recorded,
  not downgraded. Decisive criterion: availability-fallback ≠ budget-abort.
- **NOT shipped, logged**: orchestrator terminal stall (SDK/transport
  layer — not skill-fixable; tranche-2 runner may checkpoint diffs);
  pre-VERIFY overhead (probe_derive 484s + inter-phase gaps — separate
  efficiency lever, own iter); primary-judge budget (no observed overrun —
  speculative robustness, drift pattern 3).
- **Claim boundary (R0 MUST-FIX 4, Causal-Claim Honesty)**: **LC3
  movement is NOT this iter's claim.** Lever B as scoped would not have
  saved SW2 A1 (its pair judge PASSed in-budget; the stall was
  SDK-layer). What lever B claims: the PRINCIPLES-#6 budget-abort
  contract exists, is mechanical, and a pair-judge overrun can no longer
  convert a completed delivery into an unbounded wait or a false
  `BLOCKED`. Tranche-2 LC3 is measured by its own iter after the
  pre-VERIFY overhead lever ships.

## Also in scope (HANDOFF-mandated doc nit)

`SKILL.md:110` "PLAN-pair is unmeasured at HEAD" vs NORTH-STAR
"research-only after 0033d/f/g" — reconcile to the NORTH-STAR label in
this skill-touching iter (HANDOFF rotation 2026-07-07 assigned it here).

## Predictions (before any implementation; retroactive edits are dishonest)

- **P1 (lever A)**: FS1 task text through free-form `/devlyn:resolve`
  (sonnet headless orchestrator, executor=codex pin, `--pair-verify`,
  hands-free — iter-0064 A-arm invocation shape): PHASE 0 classifies
  large, writes criteria with `## Assumptions`, proceeds; run produces a
  non-empty diff with no interactive stop. Mechanism: the halt branch no
  longer applies to scope-signal-bearing goals. (R0 Probe-to-Claim
  Alignment: hidden-oracle result + wall recorded with an explicit
  interpretation rule — oracle pass/fail speaks to executor quality, NOT
  to this iter's classifier-action claim; the P1 gate is
  delivery-mechanism only: no halt, no question, non-empty diff.)
- **P2 (lever A negative control)**: a pair-evidence-intent goal without
  an actionable solo-headroom hypothesis still halts
  `BLOCKED:solo-headroom-hypothesis-required` at PHASE 0.
- **P2b (R0 MUST-FIX 1 safety gate)**: a zero-file-scope-signal large
  goal (vague, no failing test, no verification shape) still halts
  `BLOCKED:large-needs-ideation` at PHASE 0.
- **P3 (lever B)**: merge self-test covers the three-case matrix above;
  PLUS live timeout smokes in BOTH directions (codex:
  `CODEX_MONITORED_TIMEOUT_SEC` small on a real codex call → exit 124;
  claude direction: `run-bounded.py` small budget on a long-running
  command → exit 124, process group dead — R0: the claude-direction
  mechanism must be live-smoked precisely because it is new). Result:
  `pair_judge: "TIMEOUT"` recorded, merge yields verdict from
  mechanical+primary (PASS fixtures stay PASS), no
  `verify.pair.emission-contract` BLOCK from partial stdout.
- **P4 (L1 guard)**: a trivial-goal smoke through resolve (sonnet) is
  unchanged — trivial path never touches the edited branches.
- **P5 (attention cost)**: resolve skill token total
  (`scripts/skill-token-gauge.py`) grows ≤ 2% — deletions
  (`--continue-on-large`, stale rationale) offset additions.

## Loss conditions (a change that cannot lose is invalid)

- **L1**: P1 falsified (halt, question, or empty diff) → lever A FAIL,
  revert.
- **L2**: P2 falsified (integrity halt lost) → revert immediately,
  regardless of P1.
- **L3**: P3 falsified (merge BLOCKs, or TIMEOUT absent from state/report)
  → lever B FAIL, revert lever B.
- **L4**: P4 falsified → revert smallest unit + re-smoke; 2× fail →
  surface (HANDOFF binding rule).

## Probes (test arms sonnet/codex only; Fable orchestrates, never an arm)

1. FS1-class A-arm re-run via `benchmark/ceiling/scripts/run-ceiling-arm.sh`
   mechanics (Reuse-Before-New-Script) — gates P1.
2. PHASE-0-only classification probe for P2 (cheap, no pipeline).
3. Merge self-test additions in `_shared` test harness for P3 (fake slow
   judge is acceptable for merge semantics; the real-CLI timeout mechanics
   are already live-verified — iter-0012 sentinel, POSIX `timeout` 124.
   Standing lens acknowledged: fake binaries never certify real-CLI
   contracts; that part is not what P3 claims).
4. Trivial smoke for P4.

## Implementation deliverables (Codex CLI, workspace-write; mirrors ×3)

1. `references/free-form-mode.md` — Large action rewrite (halt line
   deleted; assume-and-log default; exceptions verbatim-unchanged);
   mini-spec quality bar `--continue-on-large` mention updated.
2. `SKILL.md` — :64 mode description, :98 Large sentence, :321 report
   follow-up notes (`--continue-on-large` → large-assumptions note), :110
   PLAN-pair label, :304 codex judge budget + timeout outcome.
3. `references/state-schema.md` — :119 follow-up note; sub_verdicts
   `pair_judge` value set + timeout marker documented (~:60).
4. `references/phases/verify.md` — judge invocation budgets (codex env
   var, claude `timeout 600`), timeout-semantics paragraph in the merge
   section.
5. `_shared/adapters/claude.md` — invocation block wrapped in
   `run-bounded.py 600 --` + exit-124/marker semantics.
6. `_shared/run-bounded.py` — NEW portable budget runner (R0 MUST-FIX 2
   citation: `timeout(1)` absent on stock macOS; kills process group,
   exits 124, passes exit code through otherwise; ~30 lines).
7. `_shared/verify-merge-findings.py` — TIMEOUT carrier per three-case
   contract + `--self-test` cases (lint runs them).
8. `CLAUDE.md:56` — stale rationale rewrite.
9. Mirrors: `config/skills/` ↔ `.claude/skills/` ↔ `.agents/skills/`
   identical; `bash scripts/lint-skills.sh` clean; token gauge P5.

## Principles check (final, at close)

- **0 Pre-flight**: ✅ two named user-visible failures with archived
  repro; both closed with live re-run evidence (P1 A2 delivery + oracle
  14/14; probes P2/P2b/P4 green).
- **7 Mission-bound**: ✅ Mission 1 ceiling gate (ops #17 tranche 2
  prerequisite).
- **1 No overengineering**: ✅ net doc deletion on the flag path
  (`--continue-on-large` gone repo-wide); additions cited to observed
  failures (marker file → SW2-class false-BLOCKED; `run-bounded.py` →
  `timeout(1)` absent on this host; foreground rule → P1a debug-log
  kill line). Token gauge +1.996% ≤ 2% after dedup.
- **2 No guesswork**: ✅ P1-P5 frozen before implementation; P1a
  surprise recorded raw, adjudicated openly, not retro-edited (P4-style
  honesty from iter-0064 precedent).
- **3 No workaround**: ✅ fixes land at violated invariants (classifier
  action contract; PRINCIPLES #6 budget-abort; lint needle updated
  instead of keeping Codex's decoy sentence).
- **4/5 Worldclass/Best practice**: ✅ lint suite green; merge
  self-test extended (5 new pinned cases); stdlib-only portable runner;
  guard needles caught two over-trims and were honored.
- **6 Layer-cost-justified**: ✅ lever B IS #6's mandated budget abort;
  lever A removes a 0-byte outcome at zero added wall; pair budget
  never fired on the live run (143-316s observed vs 600s bound).

## Pair rounds

- **R0 (2026-07-07, read-only xhigh, archive
  `/tmp/codex-iter0065/r0-response.log`, 403s): SHIP-WITH-EDITS.**
  Named criteria returned per position: POS-1 Class-Purity Boundary
  (adopted → zero-signal carve-out); POS-2 Observed-Finding Preservation
  + Portable Budget (adopted → `run-bounded.py`, three-case matrix,
  explicit-route availability still fail-closed); POS-3
  Causal-Claim Honesty (adopted → LC3-not-claimed paragraph); POS-4
  Probe-to-Claim Alignment (adopted → P1 interpretation rule, P2b
  vague-goal probe, live claude-direction smoke). All 4 MUST-FIX + 3
  SHOULD-FIX adopted; no position rejected (each adoption cites the R0
  counter-evidence that changed the draft — named-delta rule satisfied).
- **R1 (2026-07-07, read-only xhigh on raw results + final diff, 367s,
  archive `/tmp/codex-iter0065/r1-response.log`): VALID-WITH-EDITS.**
  Q1 CONFIRMED — attempt 1 does not refute lever A (decisive criterion:
  causal attribution to the lever under test; A1 state/criteria/debug
  cited at file:line). Q2 prompt-level foreground rule acceptable for
  close (turn-end discipline ≠ iter-0009's pipe-shape class);
  **escalation trigger registered**: any post-0065 recurrence of
  `print wind-down: killing background shell` or 0-byte delivery traced
  to a backgrounded wrapper call ⇒ binding mechanism required. Q3 all
  four orchestrator deviations verified no-regression at file:line.
  Q4 one orphan found — AGENTS.md:41 "`--goal-file` is
  trivial/medium-only" — fixed to mirror CLAUDE.md:56; lint re-green.
  (R1 sandbox note: `--self-test` needs a writable tmpdir, so the
  orchestrator's local PASS run stands as that gate's evidence;
  `run-bounded.py` smokes reproduced by R1 itself.)

## Execution record (filled as gates clear; raw numbers only)

- **Implementation (2026-07-07, Codex CLI workspace-write xhigh, 1393s,
  archive `/tmp/codex-iter0065/impl-response.log`)**: 7 files +238/−23
  plus new `run-bounded.py` (44 lines). Codex sandbox could not write
  `.agents/` — orchestrator completed that mirror sync. Orchestrator
  line-by-line review found and fixed at root cause:
  1. Codex had inserted a lint-appeasement sentence in verify.md
     restating the old invocation phrase because **lint Check 10a's
     needle encoded the pre-0065 invocation literal**
     (`lint-skills.sh:1454`). Fix: deleted the decoy sentence, updated
     the needle to the new budgeted phrase
     (`CODEX_MONITORED_ISOLATED=1 CODEX_MONITORED_TIMEOUT_SEC=600` and
     `-c model_reasoning_effort=medium`) — the check now also enforces
     the budget (no-workaround; iter-0011 Check-10 precedent).
  2. Three-case matrix was duplicated verbatim in state-schema.md +
     verify.md + SKILL.md:304 → deduped: canonical home is verify.md's
     pair-budget section; state-schema keeps value + pointer; dropped
     the PRINCIPLES.md citation from verify.md (runtime surface must not
     reference non-shipped autoresearch doctrine).
  - **Implementation refinement vs R0 wording (accepted)**: case-2b
    (marker + stdout-only findings, canonical empty) implements as
    fail-closed emission-contract `BLOCKED`, not `NEEDS_WORK` — stronger
    than R0's literal ask; preservation holds (a timeout can never
    become a solo PASS); after the orchestrator runs the collector the
    findings land canonical → case-2 `NEEDS_WORK`. Self-test pins this.
- **Gates (2026-07-07, re-run by orchestrator, not trusted from
  delegate)**: `verify-merge-findings.py --self-test` PASS (incl. 5 new
  iter-0065 cases); `run-bounded.py 1 -- sleep 5` → exit 124 in 1.04s
  (live claude-direction smoke); `run-bounded.py 5 -- true` → exit 0;
  `lint-skills.sh` "All checks passed."; `grep continue-on-large` over
  config/ + both mirrors + CLAUDE.md → 0 hits; token gauge resolve
  SUBTOTAL 110,743 → 112,890 chars = **+1.94% ≤ 2%** (P5 PASS; was
  +2.32% before dedup).
- **P2 PASS (2026-07-07, sonnet headless, scratch repo, staged
  config/skills)**: pair-evidence goal without actionable hypothesis →
  `BLOCKED:solo-headroom-hypothesis-required` at PHASE 0, complexity
  `large` recorded, no criteria file, no code touched, ideate guidance
  rendered. Integrity halt survives the default flip (L2 avoided).
- **P2b PASS (2026-07-07, same probe shape)**: 93-word zero-scope-signal
  vague goal → `BLOCKED:large-needs-ideation` at PHASE 0, zero files
  changed, concrete ideate/goal-narrowing guidance rendered. Zero-signal
  carve-out live (R0 Class-Purity Boundary).
- **P4 PASS (2026-07-07, same probe shape, 600s probe cap)**: trivial
  goal → `complexity: trivial`, mini-spec written with
  `<!-- devlyn:verification -->` sentinel + verification JSON, PLAN PASS
  56s, IMPLEMENT in-flight at probe-cap kill (probe needed PHASE-0
  routing evidence only). Trivial branch unchanged (L4 avoided).
- **P1 attempt 1 — SPLIT (2026-07-07, `iter0065-p1`, 739s, exit 0)**:
  lever-A mechanism CONFIRMED — FS1 classified `large`, NO halt/question,
  `criteria.generated.md` written with an exemplary `## Assumptions`
  block (ValueError-vs-ScheduleValueError adjudicated by reading
  `schedule/__init__.py`, reversibility stated), PLAN PASS 272s,
  IMPLEMENT entered. Delivery gate FAILED — patch.diff 0 bytes — from a
  **previously-masked distinct class**: the sonnet orchestrator launched
  the IMPLEMENT `codex-monitored.sh` call as a background shell and
  ended its message; the headless print-mode session killed the child at
  wind-down (debug log: `print wind-down: killing background shell
  bjlc57w0n` — the old PHASE-0 halt had made this unreachable on
  FS1-class goals). No contract anywhere forbade backgrounding wrapper
  calls (`codex-config.md` checked). Fix shipped, cited to this
  observation: foreground-blocking rule at both read points
  (SKILL.md `<engine_routing>` codex bullet; `codex-config.md` Notes) —
  consistent with iter-0009's resolution (wrapper heartbeat = the
  observability channel; this is NOT iter-0006's rejected universal
  foreground ban, which predated the wrapper). Lint Check-suite guards
  caught two over-trims during the token-budget dedup (`must halt`
  literals) — restored verbatim. P1 re-run as attempt 2 below; L1
  adjudication: reverting lever A would restore a guaranteed 0-byte
  halt — the empty diff traces to the new class, not the lever-A
  mechanism (R1 to confirm or refute this adjudication).
- **P1 attempt 2 — PASS (2026-07-07, `iter0065-p1` A2, 3324s, no
  timeout)**: full delivery. `complexity: large`, no halt/question;
  every phase PASS (plan 219s, implement 364s, build_gate 267s, cleanup
  60s, verify 316s, final_report); `pair_trigger` eligible with
  canonical `[mode.pair-verify, complexity.large]`;
  `sub_verdicts: {mechanical: PASS, judge: PASS, pair_judge: PASS}` —
  both judges finished inside the 600s budget (no TIMEOUT fired, as
  predicted for normal ops). Patch 7,750 bytes, 2 commits over base;
  orchestrator self-corrected a PHASE-0 spec-drafting error via a
  documented `## Correction log` and re-ran fresh VERIFY. **Hidden
  oracle (informative per Probe-to-Claim Alignment): resolved 14/14
  hidden tests, upstream suite green (49 passed / 0 failed / 41
  skipped)** — the same task that produced 0-byte delivery in
  iter-0064 tranche-1. Interpretation rule holds: oracle pass speaks to
  executor quality; the iter's gated claim is the delivery mechanism
  (no halt + non-empty diff), which PASSed. Wall 3324s is recorded, not
  claimed (LC3 is not this iter's claim).
