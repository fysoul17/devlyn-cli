---
id: "0096-transition-compliance-delivery-regate"
title: "PLAN→IMPLEMENT transition-protocol compliance (mechanical guard) + delivery byte-fidelity re-gate"
kind: reliability
status: CLOSED 2026-08-05 — matrix RAN 4/4 past watcher (guard validated live; 0095 death class closed); candidate structural bar FAILED 1/2 (candidate-discovery: SAME one-byte terminal-LF strip WITH the cue instruction — 12,150/12,151); NO SHIP CREDIT on delivery; PRE-NAMED ESCALATION FIRES: artifact canonicalization justified → successor 0097; guard + instrument fixes validated live
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
`70504f57…` (post-b23bde3 e2e rewrite; was 94a2c5d7 at e72bd1d) for the structural bar, registration scorer,
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

## R0 adjudication (2026-08-05; receipts ~/.local/share/nx01/iter0096-reg/) — adopted deltas

Both seats REVISE, complementary (no split). Adopted:

1. **Guard site = CLI argument layer** (parse/dispatch of the `complete`
   verb), not `do_complete` internals — unit paths stay valid (Grok).
2. **Co-land requirement (F2 fired by Grok with bytes)**: SPW's own
   in-file self-test uses `plan_cli(... complete PASS ...)` (~:1659) and
   the ORACLE's e2e block invokes standalone plan complete PASS
   (~:2555-2562) — both fixtures rewritten through `transition` (or halt
   verdicts) in the SAME product change; after landing, re-run the
   oracle self-test AND the four retained full-arm replays (on copies)
   before R1 (Codex).
3. **Guard live-receipt gate (Codex)**: before any timed arm, execute
   the exact installed writer from each fresh sibling base against an
   isolated synthetic state; freeze receipts (writer sha256, command,
   nonzero exit, transition-directed stderr, identical pre/post state
   sha256) for standalone PLAN PASS, plus legal PLAN BLOCKED and
   PASS→IMPLEMENT transition controls. Failure blocks the matrix; probes
   run outside the timed/scored window.
4. **F4 pre-committed ruling (both seats, merged)**: a guard-rejected
   standalone plan-complete is NOT a plan completion (no
   `plan.completed_at`; watcher stays not_ready until the atomic
   carrier, never PLAN_INVALID on the reject). SPW Bash retries are not
   PLAN Agent dispatches and do not alone fail `dispatch_clean`;
   `bash_tool_uses` may rise as non-binding telemetry; a repeated
   top-level PLAN Agent dispatch after a reject receives normal existing
   scoring; no bar rewrite, no replacement.
5. Prose sharpening: NOT adopted (guard-only; subtractive-first held).

## R1 round 1 (2026-08-05): Grok FREEZE; Codex REVISE with two NEW-evidence deltas (adopted)

1. EFFECTIVE-VERDICT CONSERVATION: the landed guard (:3221) rejects a
   supplied PLAN PASS BEFORE do_complete's attestation-failure conversion
   to terminal BLOCKED (:1453-1475) — a legal halting standalone
   completion. Fix: relocate the rejection to the point where the
   EFFECTIVE verdict is known (reject only when the effective verdict is
   PASS/PASS_WITH_ISSUES); spec amended, outer-loop iteration 2.
2. BYTE-ANCHORED ORACLE REPIN: full shas pinned in frozen-assets.sha256
   (oracle changed with the e2e rewrite). Done.

## R1 round 2 evidence (2026-08-05): both Codex deltas closed

Effective-verdict relocation LANDED `73d4b1b` via outer-loop
iteration 2 (spec amended; fresh PLAN/IMPLEMENT; verify-only
`rs-20260805T123417Z` PASS 3/3 — pair probe executed both branches:
attestation-converted BLOCKED writes legally, effective PASS rejected
pre-write with state bytes unchanged). SPW sha repinned
`bc7f74da20cd55b4…` in iter0096-reg/frozen-assets.sha256. Judges'
first dispatch BLOCKED on an orchestrator-mistyped spec sha —
fail-closed worked; re-dispatched with the authoritative state sha.
Both contaminated pipeline runs (concurrent user queue.md edits) closed
BLOCKED honestly with landed bytes re-verified via verify-only (0092
precedent, twice).

## MATRIX TERMINAL (2026-08-05) — bar 1 FAILED 1/2; guard + instruments validated live

Four ABBA arms (bases cand `95f4e06`/ctrl `401c522`, tokens 4e2cf6f7/
a0906f49/8f7df351/ce60ea29, mapping sealed `827277cc…`, nonce
`ca28c8dc…`): **watcher PASS 4/4** (SIGINT-only; the 0095
standalone-complete death class did not recur — the effective-verdict
guard is live-validated), **dispatch_clean 4/4** (corrected scorer, zero
false-fires — 0094's artifacts-clause defect closed live), **oracle
evidence issues 0 on all four live current-format sessions** (0094's
INCOMPLETE-cap defect closed live), **tripwires PASS** (candidate 0.895×
summed; 0.593/1.179 per-goal). **Deciding bar FAILED**:
candidate-discovery delivered the PLAN prompt minus its single terminal
LF (12,150 vs 12,151; common bytes identical; state/disk sha `24c20f8b…`
vs delivered `53b5fe5a…`) WITH the amended Read-cue instruction present
in its tree; candidate-simple delivered byte-exact (`27147a1b…` all
three). Live 2/2 bar → 1/2 → NO SHIP CREDIT. Controls: both
digest-mismatched their deliveries (control-simple additionally ran a
legal two-dispatch corrective respawn) — third consecutive live evidence
of both-conditions delivery variance. Blind quality bar NOT executed
(orchestrator call, logged): non-restorative by the frozen rule with the
deciding bar already failed; nonce retained unopened for audit.
**Pre-named escalation (0095 design round, carried) FIRES on exactly its
trigger**: the explicit cue failed a live 2/2 bar → artifact
canonicalization (renderer emits `plan.prompt` WITHOUT a terminal LF;
PLAN_PROMPT_SHA256 stays self-consistent since the renderer hashes what
it writes) is now evidence-justified → register iter-0097. Receipts:
`~/.local/share/nx01/iter0096-matrix/` (arms/sessions/worktrees),
`~/.local/share/nx01/iter0096-reg/` (git).
