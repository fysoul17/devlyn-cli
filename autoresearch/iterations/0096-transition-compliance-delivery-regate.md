---
id: "0096-transition-compliance-delivery-regate"
title: "PLAN→IMPLEMENT transition-protocol compliance (mechanical guard) + delivery byte-fidelity re-gate"
kind: reliability
status: REGISTRATION-DRAFT 2026-08-05 — candidate design NOT yet adjudicated; 3-seat FREEZE (R0+R1) required; nothing frozen
complexity: high
depends_on: ["0095-plan-delivery-byte-fidelity", "0094-r5-regate"]
---

# iter-0096 — transition-protocol compliance + delivery byte-fidelity re-gate

## Why this iter exists (pre-flight 0)

iter-0095's frozen matrix died at arm 1/4 (DECISIONS 0095.1): the
control-simple Sonnet parent completed PLAN with a STANDALONE
`state-phase-write.py --phase plan complete --verdict PASS` instead of
the atomic `transition` verb, leaving `phases.implement = null` at
`plan.completed_at` — the exact fail-closed class the frozen watcher
catches. The violated contract is SHARED text (outside the delivery
hypothesis delta): condition-independent parent variance, the same
both-conditions product-variance family as 0094's control delivery
variance. This iter (a) closes that user-visible failure class
mechanically and (b) re-gates the still-owed 0094/0095 live delivery
byte-fidelity credit, unblocked by (a). Mission 1, ceiling-gate lineage.

## Candidate product change (adjudicate at R0; route through /devlyn:resolve; SHARED by both matrix conditions)

**Mechanical guard, not more prose** (the prose already exists at
SKILL.md `<transition_protocol>` and was violated): `state-phase-write.py`
rejects a STANDALONE `complete` on `--phase plan` with a continuing
verdict (`PASS` / `PASS_WITH_ISSUES`) — error text directs to the
`transition` verb. Rationale: a PLAN PASS ALWAYS opens a next phase
(implement, or probe_derive when risk probes are enabled); standalone
completion is only legal for halts (`BLOCKED` / `FAIL` / `NEEDS_WORK`
remain untouched). Delete-the-bug shape: the illegal write becomes
impossible at the writer, instead of detected post-hoc by the watcher.
Self-tests: plan+PASS standalone → error (state unchanged);
plan+BLOCKED standalone → legal; plan transition PASS→implement → legal
(existing); non-plan phases unchanged. Mirrors synced 3-way. One
sentence in SKILL.md transition_protocol MAY be sharpened only if the
seats judge the guard alone insufficient (subtractive-first: prefer
guard-only).

Scope note for seats: the guard is SHARED product code — it appears in
BOTH matrix conditions (it is not the delivery hypothesis). The sibling
mutual delta stays exactly the delivery-hypothesis SKILL.md bytes.

## Re-gate protocol (carry from 0095 frozen registration; re-freeze, do not redesign)

Everything in `0095-plan-delivery-byte-fidelity.md` §§ Carry-over/Bars/
Operator-rules carries: amended watcher (grace 5000 ms), branch
worktrees + fresh path per attempt, four serial ABBA arms with Sonnet 5
parents via the run-owned pinned CLI, frozen
`Run /devlyn:resolve --no-risk-probes "<goal>"` invocation, goals
carried verbatim, opaque tokens + sealed mapping, landed oracle
`94a2c5d7…` (e72bd1d) for the structural bar, registration scorer,
sha-anchored assets. FRESH per 0088.3: sibling base commits regenerated
at the post-guard candidate SHA (control = candidate with ONLY the
delivery-hypothesis hunks reverse-applied — 0094 patch + 8f99b51 LF
sentence; the transition guard stays in BOTH trees), fresh opaque
tokens + sealed mapping, fresh controls, fresh judging nonce; 0095's
bases `49b150e`/`559e244`, tokens, and nonce are retired.

Bars unchanged from 0095: (1) candidate structural 2/2 byte-exact
deliveries; (2) dispatch_clean all four arms; (3) watcher PASS all four
arms; (4) blind no-loser quality (Fable 5 + Grok 4.5, file:line
mandatory; hard conjunct, non-restorative); (5) duration tripwires
≤1.25 summed / ≤1.50 per arm. Ship rule: all bars pass → live delivery
credit for R1 + the LF instruction, AND the guard earns its live
compliance evidence; any bar fails → no ship credit, new registration.

## Falsifiers the orchestrator accepts (R0 seats: fire with bytes)

- F1: a legal pipeline path exists where standalone `plan complete` with
  PASS is correct (no next phase opens) → guard breaks a contract →
  redesign (verdict-conditional or site-conditional).
- F2: an archived-run replay / benchmark interpreter re-executes the
  standalone plan-complete write and would now fail → replay-parity
  break (0083/0093 class) → guard needs a replay carve-out or lands
  differently.
- F3: the guard cannot be proven live (no receipt distinguishes
  guard-present behavior) → it is decoration on the measured path →
  re-scope.
- F4: watcher/scorer semantics double-count the guard (a guard-blocked
  parent retry changes dispatch counts) → bars need a named ruling
  before freeze.

## Freeze protocol

R0 adversarial (Codex gpt-5.6-sol + Grok 4.5; orchestrator positions
above stated first) on this draft; adjudicate with named deltas; land
the guard via its own `/devlyn:resolve` run per adjudication; seat-
executed proofs (SPW self-test, watcher/scorer re-run against a
synthetic guard-blocked fixture if F4 fires); R1 FREEZE on the amended
whole with liveness markers + self-computed shas (mandatory for every
re-invocation); then the matrix. Receipts:
`~/.local/share/nx01/iter0096-reg/` (git, sha-anchored).
