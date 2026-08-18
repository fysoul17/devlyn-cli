---
id: "0104-model-checkup-loop"
title: "Model-checkup loop v1 — bind recert + violation matrix + frozen discovery band into one standing checkup"
kind: process-binding
status: CLOSED 2026-08-18 — SHIPPED (playbook + template trio-FROZEN; rehearsal ×2, run 2 PASS by user ruling). Design history: three-way converged 2026-08-18 — fable R0 draft, sol REVISE ×6 + grok REVISE ×9, all findings adjudicated and folded
complexity: medium
depends_on: ["0102-executor-quality-discovery-corpus", "0103-opus-line-regression-cell"]
---

# iter-0104 — model-checkup loop v1

## Why this iter exists (pre-flight 0)

User reorder 2026-08-18 (`HANDOFF.md:19-35`): model releases are a RECURRING
event, so **the product is the standing loop** "new model → measure on the
harness → tighten from findings → re-pin", not any single hypothesis. This
supersedes the earlier repo-scale-first pick; repo scale becomes 0105, the
loop's first coverage module, built after the loop so it is reusable per model.

The instruments already exist and are proven. Seat recert + the 6-probe
violation panel certified both exact opus IDs with `failures: []`
(`benchmark/seats/results/ckf0099-recert/recert-status.json`;
`benchmark/seats/recert-seats.sh:7-9,128-133`). The frozen 0102 discovery
corpus produced two terminal verdicts — 0102 opus-5 vs fable-5 (Δ=−0.047,
CI [−0.116,+0.016]) and 0103 opus-5 vs opus-4-8 (Δ=−0.181, CI [−0.256,−0.109])
— on one sealed tree (`DECISIONS.md` 0102.1, 0103.1). 0103 proved the marginal
cost of the next model cell is already low: one attempt, 128/128 attested, 93
min at 2 lanes (`iterations/0103-opus-line-regression-cell.md:218-236`).

What is NOT low-cost is everything around the arms: registration prose, freeze
audits, launch gates, adjudication — all re-derived by hand each time
(`HANDOFF.md:23-26`). 0104 binds the three instruments into one documented
checkup, freezes the per-model registration template so the next instance is a
copy-and-fill rather than a design round, and gives the tightening lane
(terra implements → trio verifies) its durable home.

## Decisive criterion (frozen)

0104 CLOSES when BOTH hold:

**(a) Artifact frozen.** `autoresearch/playbooks/model-checkup.md` and its
embedded registration template are trio-FROZEN — fable + sol + grok, zero
open findings.

**(b) New-ID dry-instantiate rehearsal passes.** A FRESH agent — no 0102/0103
context, no conversation history — receives exactly two inputs: the playbook,
and a **scenario card**. The card carries ONLY the instance judgments that are
user inputs in a real checkup:

- candidate exact model ID;
- seat under decision (executor / pair judge);
- whether the regression question is asked (decides the opt-in predecessor arm);
- the operator's prediction direction (the registration's `P-<NNNN>-1`).

The card also carries a **results annex** — stand-in numbers the agent APPLIES
the decision table to, so the rehearsal exercises the outcome logic without any
live arm firing:

- `recert-status.json` `failures[]`;
- per-engine cell statuses, **suite-scoped to each engine's class** per §6 —
  Claude-family engines carry `drift_resistance` + `orchestrator` +
  `verify_primary_judge`; a `codex` entry carries `orchestrator` +
  `verify_primary_judge` only, with NO `drift_resistance` cell (the card must
  reflect that absence, not fill it in, so the rehearsal exercises the
  absent-by-class branch). A class-expected cell may also be given as MISSING
  rather than stale — per §6 that fails row 1, and only the absent-by-class
  cell is exempt;
- violation totals per model (violations/reps + flip band);
- a stand-in `cohort-verdict.json`: `terminal`, `delta`, `ci`, `R`, and the
  cohort health counts.

**The agent must APPLY these, never invent them.** Fabricating a result — or
firing a live arm to obtain one — is a rehearsal FAIL, not a workaround; live
instrument arms stay forbidden inside 0104.

Everything MECHANICAL must be derivable from the playbook + template with ZERO
ad-hoc decisions: `NNNN`/slug (§9), recert CSV composition (§3b), corpus
reference resolution (§3c), both transforms (§5), field paths (§6), and outcome
selection via §6's top-down first-match precedence. From those two inputs the
agent produces the complete instantiation:

1. the `recert-seats.sh` command line, with a legal `--engines` CSV and a
   `ck<NNNN>-<slug>` run prefix;
2. the corpus-reference resolution via the Step-0 rule, applied to the LIVE
   `.devlyn/engines.json` + latest seat matrix;
3. the tuple-replacement transform stated against the LIVE seed
   (`benchmark/executor-quality/scripts/mx-driver.py:31`) and the LIVE scorer
   (`benchmark/executor-quality/scripts/score-cohort.py:19`), with the
   `ENGINES[0] = candidate` sign convention correct;
4. the registration file with freeze-inventory blanks marked and R-A/R-B
   parameterized;
5. the one-page field-path table;
6. a provisional outcome obtained by applying §6's top-down first-match table
   to the card's results annex — the selected row plus the specific annex
   values that made it fire;
7. the re-pin act described as the TWO-LAYER act (§8). Layer 1 = a human
   `/devlyn:engines` write when the seat ENGINE changes, using the subcommand
   that matches the SEAT UNDER DECISION — `executor <adapter-name>` for the
   executor seat, `pair <name>[,<name>...]` for the pair-judge seat
   (`config/skills/devlyn:engines/SKILL.md:43-45`); naming the wrong surface for
   the card's seat is a fail. Layer 2 = model-within-`claude`, where
   `.devlyn/engines.json` is unchanged, model selection lives in the engine
   CLI's own configuration, and enactment is bound to the certified exact ID by
   an exact-ID `modelUsage` smoke attestation. Naming an exact model ID as the
   pin VALUE is a fail — pins take adapter names only.

Bar: **ZERO ad-hoc design decisions**, and correct fail-closed behavior on the
two branch cases — a cross-provider (non-runner-compatible) incumbent, and a
recert-illegal engine name. Any decision the template cannot answer → REVISE,
not ship.

**Falsifier accepted at registration**: a rehearsal that surfaces an
unanswerable decision refutes template completeness. **NO live instrument arms
fire inside 0104** — no recert run, no cohort launch.

## Design decisions (R0 adoption record)

Five original positions, all held:

- **D1** — ONE playbook with the registration template embedded; zero new
  scripts, zero new flags on existing scripts.
- **D2** — flow = compatibility preflight → recert (violation inside it) →
  frozen discovery band → one-page verdict → tightening → re-pin.
- **D3** — closure is a fresh-agent rehearsal, not a self-review.
- **D4** — the template floor is the 0103 shape: inherit-by-reference with full
  digests, enumerated deltas, freeze inventory, R-A/R-B, terminal bijection.
- **D5** — `autoresearch/playbooks/iteration-loop.md` is stale generic template
  (`:19-70`) but stays UNTOUCHED in this iter; noted as a finding only.

Adjudicated amendments, with seat attribution — all ADOPTED:

| finding | seat(s) | adoption |
|---|---|---|
| F1 — the page needs a TOTAL re-pin decision table; `H1_MATERIAL_GAP_REFUTED` alone cannot decide adoption (it covers both "clearly better" and "merely not materially worse") | sol | §6 decision table, four exhaustive outcomes; explicit rule that adoption reads Δ sign + CI bounds |
| F2 ≈ grok F1 — "reference = incumbent" is not executable when the live pin is `codex` | sol, grok | §3 Step-0 compatibility preflight + fail-closed NO-CROSS-PROVIDER-AUTHORITY label + band-CURRENT-Claude fallback |
| F3 — ordering: measure → tighten → re-pin; the Step-3 recommendation is provisional | sol | §6 marks the recommendation PROVISIONAL; §8 sequences the final call after tightening |
| F4 — bind ALL apparatus bases by source path AND digest, fail closed on an unavailable base | sol | §5 apparatus derivation |
| F5 — the `autoresearch/README.md` playbook-index pointer is in scope for this iter | sol | sequencing step ⑧ |
| F6 ≈ grok C5 — R-A/R-B must be parameterized without weakening the invariant | sol, grok | §5 R-A/R-B parameterized over registration revision, freeze filename, scorer filename, inventory keys, digests |
| grok F2 — delta (i) is a TUPLE REPLACEMENT of the live seed's `ALLOWED_ENGINES`, never a named-model `sed` | grok | §5 delta 1 |
| grok F3 — rehearsal must be a NEW-ID dry-instantiate, not a 0103 retrospective | grok | decisive criterion (b) |
| grok F4 — the HANDOFF START-HERE 0104 block shrinks to a pointer in this same iter, at freeze | grok | sequencing step ⑧ |
| grok F5/F6 — the one-page verdict is human synthesis (no assembler script); recert-set vs corpus-reference are named as distinct sets | grok | §6 heading; §3 (b) vs (c) |
| grok F7 — the tightening section documents the standing PROCESS only; the closed batch-B narrative stays in HANDOFF/DECISIONS | grok | §7 |
| grok F8/F9 + sol C5 (STRONGEST-MINE) — `iteration-loop.md` untouched; no `executor_quality` fold-in to `recert-seats.sh` | grok, sol | scope guards below |

Zero cross-seat contradictions: every sol finding and every grok finding is
independent or convergent; none required choosing between seats.

## Scope guards (goal-locked)

- Zero new scripts. Zero new flags on `recert-seats.sh`, `seat-matrix.py`,
  `run-violation-matrix.sh`, `mx-driver.py`, or `score-cohort.py`.
- No `executor_quality` suite fold-in to `recert-seats.sh` — that is the
  unshipped 0100/0101 follow-up and stays out.
- No corpus changes; the 0102 candidate tree stays sealed.
- No live instrument arms inside 0104.
- `autoresearch/playbooks/iteration-loop.md` untouched.
- iter-0105 (repo-scale corpus, >100 files, multi-file dependency chains) is a
  SEPARATE registration (`HANDOFF.md:32-35`).

## Sequencing

1. Registration committed (this file).
2. terra drafts `autoresearch/playbooks/model-checkup.md`.
3. Trio review R0 on the actual artifact (fable + sol + grok).
4. Revise.
5. Trio FREEZE.
6. Fresh-agent rehearsal per the decisive criterion (b).
7. fable adjudicates the rehearsal against (b).
8. Companion edits: `autoresearch/README.md` playbook-index pointer +
   `HANDOFF.md` START-HERE 0104 block shrunk to a pointer.
9. `DECISIONS.md` 0104.1 + commit.

## Execution log

**2026-08-18 — registration authored.** Cold-start sanity, run in THIS session
and recorded first-hand (session record, not a stored receipt): `bash
scripts/lint-skills.sh` exit 0, trailing line "All checks passed."; `python3
benchmark/ceiling/probes/r-weld-0082/test-collector-contract.py` printed its
"114 checks" line (batch B + the terminal-verdict ruling `a75c2ee`); the
`_shared` self-tests `spec-verify-check.py`, `state-phase-write.py`,
`terminal-claim-check.py`, and `collect-codex-findings.py` each exited 0. The
check list itself is `HANDOFF.md:226-248`; the outputs above are this session's,
not an artifact on disk.

R0 packet dispatched to two seats: **sol** (xhigh, 355 s) returned REVISE with
6 findings; **grok** (high) returned REVISE with 9 findings. Zero cross-seat
contradictions. fable adjudication folded every finding (table above) into the
frozen design. Registration authored by terra direct-drive.

**No `~/.local/share/nx01/iter0104/` receipts exist, by design** — 0104 fires no
live instrument arms (no recert run, no cohort launch), so the iteration has no
run artifacts to bind. The first receipts in this lineage appear at the first
INSTANCE registration the playbook instantiates.

**2026-08-18 — rehearsal run 1 (decisive criterion b): REVISE, falsifier
fired.** Fresh sonnet agent, scenario card = candidate `claude-opus-6`, seat
under decision executor, cross-provider (`codex`) incumbent, plus a
recert-illegal engine name as a distractor. **All 7 deliverables matched the
pre-registered expected key exactly** (key held machine-side in the session
scratchpad, written before the run). The honesty channel nonetheless surfaced
three genuine template gaps plus one minor — (1)/(5) the Step-0(c) ELSE-branch
reference's standing was undefined (recert CSV? row-1 gate?), (2) the `NNNN`
rule collided with a number reserved in prose but unused by any file, (3) the
re-pin section did not say what happens when the fired outcome is a
non-adoption row. Per the frozen criterion an unanswerable decision refutes
template completeness, so the falsifier FIRED despite the clean deliverable
match: verdict REVISE, not ship. Closed by the R5 clauses (§3c corpus-only
baseline, §9 reservation tie-break, §8 no-enactment rule); gap 4 (a
paper-dry-run marker) adjudicated NO CHANGE as an artifact of the rehearsal
exercise rather than the standing loop. Rehearsal re-run scheduled per the
frozen criterion.

**2026-08-18 — rehearsal run 2: 8/8 deliverable match; closure verdict
ESCALATED.** Fresh sonnet agent, same scenario card plus a counterfactual
question. **All 8 deliverables matched the pre-registered run-2 key** (key
frozen machine-side in the session scratchpad before launch), including the
counterfactual — §6 row 3 RECOMMEND-REPIN reached with a pure layer-2
enactment quoting the exact smoke contract — and both fail-closed branches
(cross-provider incumbent, recert-illegal engine name). Honesty channel
returned four items, adjudicated: two are paper-run exercise artifacts (the
run-1 gap-4 precedent — artifacts of the rehearsal exercise, not template
scope), one is a latent wording ambiguity NOT exercised by this run
(§3b "seat incumbents"), and one is a presentation-equivalent reading with no
gate or outcome difference (zero-delta digest timing). The latter two are
closed by the R7 clauses (§3b full-pinned-surface, §9 zero-delta
fill-at-registration).

**Closure verdict ESCALATED to the user** per
`feedback_wait_for_fable_judgment`: PASS-with-registered-findings (the frozen
criterion's deliverable bar met twice, residuals being non-exercised or
presentation-level) vs strict REVISE + run 3 (any honesty-channel item fires
the falsifier, as it did at run 1). Not self-adjudicated — decisive-criterion
closure is the user's call.

**DECISION (2026-08-18) — iter-0104 CLOSED, SHIPPED.** The user ruled
**PASS-with-registered-findings** per `feedback_wait_for_fable_judgment`. The
frozen deliverable bar was met twice: run 1 matched the pre-registered key 7/7,
and its falsifier fired on three outcome-bearing gaps, closed as the R5 clauses;
run 2 matched 8/8 including the counterfactual (§6 row 3 RECOMMEND-REPIN reached
with a pure layer-2 enactment quoting the exact smoke contract) and both
fail-closed branches, with its residuals adjudicated non-outcome-bearing and
closed as the R7 clauses. Decisive criterion (a) — playbook + embedded template
trio-FROZEN through the R7 deltas — and (b) — fresh-agent rehearsal PASS —
are both satisfied. Deliverable: `autoresearch/playbooks/model-checkup.md`
(531 lines). Zero new scripts, zero new flags, no live instrument arms fired.
