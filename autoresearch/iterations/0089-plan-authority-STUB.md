---
id: "0089-plan-authority"
title: "PLAN authority — dispatch ledger, cap enforcement, prompt-delivery attestation, round-aware oracle"
kind: reliability
status: PRE-REGISTRATION STUB — three-way design converged 2026-08-02; NOT registered (next session runs 3-seat R0+R1 on this stub)
complexity: medium
depends_on: ["0088-plan-route-startup-dedup"]
---

# iter-0089 STUB — PLAN authority (converged design, awaiting registration)

## Why this iteration exists

iter-0088 Stage B died at the control stage: at byte-identical product, 2 of
5 control runs deviated in the PLAN region (`0088` § STAGE B EXECUTED) —
(i) the parent composed the PLAN worker prompt with the canonical body under
an H2 heading (instrument-killing paraphrase; run itself healthy);
(ii) a replacement arm dispatched PLAN **three times** ("CORRECTING ROUND 0",
"narrow sync fix"; two superseded NEEDS_WORK rounds then PASS) against the
prose cap of one re-spawn, with divergent RISK_PROBES activation and a 516 s
state-vs-attribution startup disagreement. H1-v3 is UNSCORED; its
re-registration is blocked until PLAN-region evidence is scoreable.
The user directive (2026-08-02): decide what best practice is against the
whole picture and North Star — answered by three-way adjudication below.

## Three-way adjudication record (2026-08-02, durable receipts)

Seats: Fable 5 orchestrator (position first), Codex gpt-5.6-sol xhigh
read-only, Grok 4.5 headless read-only allowlist. Raw returns:
`~/.local/share/nx01/iter0088-stageb/seats/r3-{codex,grok}-determinism.log`
(+ prompt `r3-determinism-prompt.md`).

**Converged verdict — "identical every time" is the wrong target.** Named
criteria: Grok **Invariant-Bookkeeping Asymmetry** (Block-7 axiom applied:
skeleton owns invariant bookkeeping, intelligence keeps judgment; adopted
the orchestrator's layered position wholesale); Codex **narrow PLAN
authority** (neither pole wins: mandate the mechanical ledger, reject
prompt-delivery forcing). Both ranked the same sequencing #1.

**Named delta (orchestrator position moved)**: from "mechanical prompt
concatenation" to "render + digest + fail-closed delivery ATTESTATION" —
Codex's architectural evidence: PLAN workers are native-Agent dispatches
with **no mechanical interception seam** (contrast SURFACE_CLOSE's top-level
shell-out with `prompt_sha256` machinery, `state-schema.md:61`); a renderer
without a binding seam is theater; forcing delivery is
deterministic-runner-shaped (M1.5, out). The house pattern is detection +
honest halt (C2 terminal-claim / stop-hook precedent), corroborated by the
0088 receipts' observed session shapes.

## Scope (the ONLY three deliverables)

1. **Mechanical dispatch ledger + cap enforcement** in
   `state-phase-write.py`: initial PLAN = round 0; re-entry = previous
   round + 1; registered cap (current contract value N=1 out-of-scope
   re-spawn) enforced — an over-cap spawn fails explicitly
   `BLOCKED:plan-respawn-exhausted`; per-round append-only receipts carry
   round, timestamps, verdict, engine/model/session evidence, and prompt
   digest (today's receipts carry only timestamps+verdict,
   `state-phase-write.py:1256` area). SPW cannot physically prevent an
   off-ledger native dispatch — the oracle flags those fail-closed.
2. **Canonical prompt render + delivery attestation** (no forcing): a thin
   shared renderer (Codex: e.g. `phase-prompt-render.py`, NOT inside SPW)
   concatenates adapter bytes + canonical body bytes + task-context
   artifact, writes `.devlyn/plan.prompt` + sha256; SPW records the digest;
   experiment/product attestation compares the worker-received bytes
   against the digest and fails closed on mismatch. Delivery FORCING is
   explicitly deferred unless a binding seam passes a no-degradation test.
3. **Round-aware all-dispatch oracle** (instrument): attest every actual
   dispatch including failed/pre-write ones; PLAN region = first dispatch
   start → final legal completion, decomposed per-round + parent
   inter-round; conjunct `startup_recomputed == attribution.startup_ms`;
   PLAN identified by durable dispatch identity, never Markdown heading
   level; three-state classification — valid COMPLETE / **complete-evidence
   CONTRACT-VIOLATION** (e.g. a third dispatch: receipts retained, no valid
   comparator, no ship credit) / INCOMPLETE. Evidence completeness and
   product eligibility stay orthogonal axes (0088 D1 lineage).

## Explicitly OUT (Codex bounding, both seats concur)

- No general dispatcher / deterministic runner (M1.5 stays deferred).
- No attempt to make plan CONTENT identical; task-context authorship,
  plan conclusions, and the judgment to request a legal replan stay
  autonomous (no-suppression directive, Block 8).
- No cap-VALUE change inside 0089. N=1 stays the provisional shipping
  default ("slower but more thoughtful is not free", NORTH-STAR). A later
  candidate iter may run matched N=1 vs N=2 (≥4 reps per arm, 0058
  instability precedent) scored on TERMINAL outcomes — final acceptance,
  downstream BUILD_GATE/VERIFY defects, scope fidelity, total wall,
  no-degradation controls — never on plan-PASS (C3 counterexample: plan
  PASS after 3 rounds, terminal still NEEDS_WORK).
- No second "determinism infrastructure" iteration; 0089 must not grow
  into a determinism project.

## Exit gate (all four, by execution)

1. Every legal PLAN dispatch is accounted in the ledger with its receipt.
2. A third dispatch is mechanically rejected with the canonical BLOCKED
   verdict (red-tested).
3. Decorative heading variation cannot kill the oracle (H2-composition
   replay from the retained F12/C2 receipt classifies correctly).
4. Startup attribution agrees across receipt sources (F12/C3's 516 s
   disagreement class is detected as a conjunct failure, not silence).

Then IMMEDIATELY re-register H1-v3 with fresh controls (0087 and 0088
budgets/controls/ratios are dead; never reuse).

## Registration protocol for the next session

Cold start per HANDOFF read order. This stub is design input, NOT a
registration: run full 3-seat R0+R1 (Opus 5 / Codex gpt-5.6-sol / Grok 4.5
per current seat map; Fable 5 orchestrating, never a test arm), pre-flight
0 + principles check, frozen predictions + falsifiers + satisfiability BY
EXECUTION before FREEZE (binding lesson: a freeze is not frozen until a
seat has tried to satisfy every conjunct by execution — 0088's D4 omission
is the fourth receipt of this class). Replay assets available for
red-tests: `~/.local/share/nx01/iter0088-stageb/controls/F12/{C2,C3}`
(H2-composition and triple-dispatch receipts), plus the four COMPLETE
control receipts for green paths.
