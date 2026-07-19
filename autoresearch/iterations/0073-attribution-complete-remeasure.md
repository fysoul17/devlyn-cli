# iter-0073 — attribution-complete post-0072 nodeg re-measure (FROZEN 2026-07-19, three-way converged R0+R1)

**Why this iter exists (pre-flight 0)**: this is the last attribution run
before two decisions: (i) does iter-0072's SURFACE_CLOSE lever generalize
beyond its own F7 gate (post-0072 quality-bar status), and (ii) which
phase/gap owns the next wall lever (0071 addendum 5 left P2′/P3′ NOT
COMPUTABLE — retention gap). Serves Mission 1 ceiling-instrument track
(MISSIONS ceiling addendum); measurement license per PRINCIPLES:22
(single follow-up closing addendum-5's recorded instrument gap).

**Registered claim (single)**: one attribution-complete 7-row nodeg cohort
on the post-0072 stack, with per-phase wall attribution retained and
adjudicated against the frozen predictions below. Nothing else ships in
this iter. (Premature-terminal-during-VERIFY design round = separate
registration iter-0074, may run concurrently — single-claim discipline,
Codex R0 adopted over Grok's item-2 placement; Grok's own edit 5 already
conceded the primary-claim split.)

## Three-way provenance

R0 2026-07-19 (packet /tmp/threeway-0073-r0/packet.md; logs codex-r0.log,
grok-r0.log): Q1 close-0072 GO (Grok) / GO-WITH-EDITS (Codex honesty
edit); Q2 GO-WITH-EDITS ×2 (edits composed below); Q3 design-only license,
separate registration; Q4 F25 `.find` bounded root-cause investigation
licensed, no build; Cell 1 stays behind. Orchestrator verified every
load-bearing R0 citation live (rounds_history at interphase-turns.py:85
vs `history` at state-schema.md:90; runner-SHA die at nodeg-cell.py:746;
-19f verdict quality FAIL + CLI identity; C2 gating at
run-nodeg-cell.sh:95; -19f phase-sum 609.3s vs wall 1231s, implement
146.0s ≈ 12%; transcript `run_in_background: true` + terminal_reason
"completed").

R1 2026-07-19 (logs codex-r1.log, grok-r1.log): Grok FREEZE-NO-GO on ONE
blocker (P-c numerator double-counted implement fix rounds — biased
toward CONFIRM); Codex FREEZE-NO-GO on five: (1) trigger-filtered
history sums not computable (history[] carries no triggered_by,
state-phase-write.py:1056/:1268) + draft silently weakened the
registered 0.60/≥5-of-7 bar to 0.50/4-of-7 + INCONCLUSIVE outcome
missing; (2) unattributed_ms mislabeled (wall encloses whole CLI
invocation, run-ceiling-arm.sh:728) → non_phase_residual_ms; (3) P-a′
SC-carrier-axis causal claim contradicted by the actual winning delta
(-19f codex.json: exact-JSON assertion; robustness ranked A's
exit-status test below bare's error-text test); (4) Node pin must be an
exact binary path; (5) 0072 honesty rider must be APPLIED at freeze.
All six blockers adopted verbatim into this frozen text (orchestrator
re-verified (1) at state-phase-write.py append_phase_history and (3) in
the raw judge file before adopting). Convergence = both seats' own
required edits are the frozen text; no unresolved dissent.

## Stage A — retention + attribution instrument (build, benchmark-only; Codex sol executor)

1. **Whole-`.devlyn` retention**: in `run-ceiling-arm.sh`, after
   patch/timing persistence (~:737-739), `cp -a` the A-arm worktree's
   entire `.devlyn` into `$RESULT_DIR/devlyn-snapshot` (mechanism
   precedent :659-663). Must cover ALL outcome classes fail-closed:
   completed (state under `runs/<run_id>/`), premature-terminal (root
   `pipeline.state.json`, -19f flavor), timeout, and draw (draw path
   already snapshots — do not double-copy; skip when marker present).
   Failure to snapshot = arm error, not silent.
2. **Attribution helper fix**: `interphase-turns.py:85` reads
   `rounds_history`; canonical schema field is `history[]`
   (state-schema.md:90). Fix to `history`, add a synthetic re-entry
   self-test (a state with implement.history[] round + triggered_by)
   proving fix-loop spans are counted.
3. **Deterministic attribution artifact**: per A attempt, emit
   `attribution.json` from the retained state + timing.json:
   per-phase `{duration_ms, history_sum_ms, current_triggered_by}`
   (history entries intentionally carry NO round/triggered_by —
   state-phase-write.py:1056/:1268, Codex R1 — so no trigger-filtered
   history sums), `phase_sum_ms`, `elapsed_ms`,
   `non_phase_residual_ms = elapsed − clipped-union(phase spans)`
   (contains CLI startup, pre/post-phase, terminal, AND inter-phase
   orchestrator time — the wall timer encloses the whole invocation,
   run-ceiling-arm.sh:728; never labeled as inter-phase turns alone),
   `verify_complete` flag, `incomplete_spans` list. Judge durations are
   a subset of VERIFY — never double-counted.
4. Gates: self-tests (incl. conservation on synthetic complete +
   incomplete states: attributed + unattributed = elapsed, deterministic),
   `lint-skills.sh`, no skill-body change (benchmark-only surface).

## Frozen P-c arithmetic (per Grok R1 double-count blocker + Codex R1 computability blocker)

- `implement_total_ms = implement.duration_ms + Σ implement.history[].duration_ms`
  — implement re-entries ARE the fix-loop work channel (implement is
  respawned only by fix loops, state-schema.md:94), so this single term
  is the whole numerator. No trigger-filtered history sums: `history[]`
  intentionally retains only started_at/verdict/completed_at/duration_ms
  (state-phase-write.py:1056, self-test :1268) — a triggered_by filter
  over history is not computable and was rejected (Codex R1; the earlier
  two-addend form also double-counted, Grok R1).
- Primary predicate ratio = `implement_total_ms / (timing.elapsed_seconds × 1000)`;
  secondary = share of phase-sum. Primary population = complete-verify
  rows only; incomplete-verify rows classified and reported secondary
  (Grok edit).

## Predictions (FROZEN at registration; adjudicated by the verdict + attribution artifacts)

- **P-a′ (quality, replication frame — replaces the falsified-as-drafted
  P-a per Codex R0; causal axis label deleted per Codex R1)**:
  nodeg-20260719f already IS the post-0072 F7 pilot (n=1: objective
  PASS, quality FAIL, sonnet 3/4 A_win, codex 1/4 A_win). No causal
  claim about WHICH axis: codex's sole A-win delta was the exact-JSON
  test assertion, not an SC carrier — and its robustness delta ranked
  A's exit-status test BELOW bare's error-text test (-19f codex.json,
  orchestrator-verified). Fresh-cohort prediction: F7 codex-judge A_win
  ≥ 1 axis replicates; suite quality bar stays 0/7 (defect classes (b)
  design decomposition, (c) validation strictness/behavioral, (d) blast
  radius are NOT addressed by 0072). Quality bar moving to ≥1/7 would
  EXCEED prediction and license a generalization claim.
- **P-b (wall)**: unchanged or worse — median A/frozen-B ≥ 8×. SC + M-CP
  add phases; no wall lever shipped since 0071.
- **P-c (attribution, two-sided — the decision-unlocker)**: addendum-5's
  binding read ("bottleneck = IMPLEMENT/fix-loop") is CONFIRMED iff
  `implement_total_ms / elapsed_ms ≥ 0.60` on ≥ 5/7 complete-verify rows
  (the R0-registered bar restored — the draft's 0.50/4-of-7 was a silent
  weakening, Codex R1); REFUTED iff the predicate fails with ≥ 5
  complete-verify rows available; **INCONCLUSIVE** (not REFUTED) iff
  < 5 complete-verify rows (Codex R1 edit). On REFUTED the next wall
  lever retargets to the measured plurality owner. Orchestrator prior,
  stated honestly: REFUTED more likely (-19f implement ≈12% of wall,
  non-phase residual ≈50%; Grok n=21 opportunistic archives median
  implement 23% / verify 37% of phase-sum, 0/21 ≥60%). Either
  non-INCONCLUSIVE outcome changes the next wall iter's target — that is
  the license.
- **Reopening falsifier (Grok, accepted)**: if VERIFY(+judges) own ≥50%
  of wall on ≥5/7 complete rows, 0071's "must target IMPLEMENT/fix-loop"
  binding read REOPENS.

## Stage B — the exam (detached background; launched only after Stage A gates green)

- **Immutable checkout**: `git worktree add` at the exact post-Stage-A
  SHA (runner-SHA integrity die at nodeg-cell.py:746 — inner-loop commits
  on main must not invalidate the exam; measurement-lanes hard rule "no
  mid-cohort commits" satisfied by worktree pinning, main stays free).
  Results copied back to main's results/ tree at verdict time.
- **Launch**: fresh run-id; explicit CSV of ALL 7 tasks with F7 FIRST
  (C2 activates only under explicit --tasks, run-nodeg-cell.sh:95; CSV
  order is respected, nodeg-cell.py selected_controls — F7-first makes a
  pre8/cmds=0 draw abort cheap; expected diagnostic-draw rate ≈ 1/3,
  relaunch with fresh run-id licensed, not a prediction failure).
- **Identity**: CEILING_TEST_CLAUDE_BIN=/Users/aipalm/.local/share/claude/versions/2.1.211,
  CEILING_TEST_NODE_BIN=/Users/aipalm/.nvm/versions/node/v20.19.0/bin/node
  (exact binary, never PATH-resolved — run-ceiling-arm.sh:79 delegates a
  bare name to `command -v`; credited identity is v20.19.0, Codex R1),
  seats sonnet orchestrator / terra executor (user directive 2026-07-19),
  frozen best_B unchanged (labeled post-stack STATUS comparison, not
  clean 0072 treatment effect — frozen B codex-cli 0.144.1 vs current
  0.144.5, Codex edit 5), dual blind judge + verdict via existing driver.

## Falsifiers for the iter shape (pre-registered)

- **FS-A (Codex)**: Stage A cannot conserve wall deterministically across
  phase spans, re-entry history, and residual gaps on synthetic complete
  + incomplete states → Stage B must not launch as "attribution-complete";
  iter re-scopes.
- **FS-B (Grok)**: retained state lacks summable per-phase/history
  durations on ≥3/7 completed rows → attribution claim dies, re-scope.
- **FS-C**: fresh cohort's F7 row non-diagnostic ≥4 consecutive draws →
  surface to user (draw-rate assumption broken), do not silently retune.

## iter-0072 close-out rider (honesty edit, Codex R0 adopted; APPLIED at freeze per Codex R1)

APPLIED: iter-0072 §SHIP-CREDITED wording "clean diagnostic completion"
corrected in-place to "valid diagnostic final-tree row; arm exit 0;
pipeline terminal INCOMPLETE (verify.verdict=None — residual 1)"; the
DECISIONS 0072.28 entry (append-only, not edited) is corrected by the
0072.29 close-out entry. The 11/11 final-tree credit is unaffected
(gate completion-predicate-free, proven at ship round). iter-0072
CLOSED.

## Licensed side-item (no build): F25 `.find` root-cause investigation

Bounded investigation only (Codex+Grok concur): why did BUILD_GATE/VERIFY
coverage miss a real behavioral defect (later matching line-promotions
ignored, nodeg-20260714 F25 codex.json:44)? Output = written root-cause
note; any mechanism is a FUTURE registration.

## F25 `.find` root-cause investigation note (licensed side-item — investigation only, 2026-07-19)

**Defect**: nodeg-20260714 F25 A-arm `patch.diff:85` —
`catalog.line_promotions.find((entry) => entry.sku === sku)` applies at
most ONE promotion per SKU; bare iterated all matches (blind codex judge
robustness delta). **Why every harness gate missed it (receipts)**:

1. **Not a spec violation** — `task.txt` describes the two promotion
   TYPES (:7) and says "applies line promotions" (:1) but never states
   whether one SKU can carry multiple promotions. `.find` embeds an
   "at most one per SKU" uniqueness assumption the spec neither grants
   nor forbids.
2. **Not oracle-visible** — the shipped catalog has exactly one
   promotion per SKU (TEE buy_x_get_y_free, BAG per_unit_discount);
   the hidden tests never exercise a multi-promotion SKU; the A row is
   objective resolved=true. VERIFY audits spec fidelity; a latent
   data-shape assumption that spec+tests+data all leave unexercised is
   structurally invisible to spec-anchored verification.
3. **Class shape**: "spec-silent data-shape generality." The bare form
   is NOT more code and NOT speculative defensive robustness — it is
   the neutral reading of a list data-contract (a list may repeat
   keys); `.find` is the added assumption. The blind quality judges
   systematically reward the assumption-free form (same shape in the
   F26 canonicalJson-vs-JSON.stringify delta and the FS1 budget-reset
   delta).

**Named tension (recorded, not resolved)**: CLAUDE.md Goal-locked
pattern 3 forbids speculative robustness for unobserved cases; the
nodeg blind-quality bar rewards assumption-free generality. These are
compatible ONLY if the contract distinguishes "adding handlers for
unobserved cases" (drift, forbidden) from "not embedding uncovenanted
uniqueness/order/shape assumptions" (data-contract neutrality, part of
NORTH-STAR axis 5 unprompted completeness). Any future quality lever
must draw exactly this line mechanically. Mechanism = future
registration; nothing built under this iter (single-claim discipline).

## Execution deviations (Stage B live; recorded as observed)

1. **attribution.py final_report strictness defect (FS-A-adjacent,
   caught on the FIRST live row)**: nodeg-20260719g F7 A1 — the arm's
   attribution step failed `ATTRIBUTION_ERROR: phases.final_report must
   be an object` (exit 2 → arm exit 78) because the REAL premature-
   terminal state has NO `final_report` key at all, while the Stage A
   self-test's synthetic "-19f topology" state apparently included one.
   Self-test fidelity gap: synthetic ≠ real receipt. Consequence: exam
   rows retain devlyn-snapshot + timing (retention WORKS — verified on
   the live row) but lack attribution.json; the driver proceeded (78 +
   deps receipt present → falls through to eval; objective evaluated
   normally, resolved=true). Fix licensed: treat absent `final_report`
   as never-started (not an error) + regenerate the self-test synthetic
   from the actual -19f receipt; attribution.json for ALL exam rows is
   regenerated POST-HOC from retained snapshots (deterministic — same
   inputs, same output; the pinned exam worktree is NOT touched). The
   fix lands on main only; P-c adjudication uses the post-hoc artifacts.
2. **Premature-terminal-during-VERIFY: THIRD live receipt** —
   -20260719g F7 A1 devlyn-snapshot/pipeline.state.json: verify
   started_at set, verdict=None, duration_ms=None; all prior phases
   PASS; SC FIRED (UVR-STALE, surface-close.output.json); objective
   resolved=true; invoke_exit=0. Same flavor as -19f on a fresh row
   with the same seats — the class is not rare. Strengthens iter-0074's
   observed-failure anchoring; this row joins P-c's incomplete-verify
   secondary population (frozen split unchanged).
