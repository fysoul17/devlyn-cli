---
id: "0095-plan-delivery-byte-fidelity"
title: "PLAN delivery byte-fidelity: live 2/2 byte-exact delivery through the amended Read-cue instruction"
kind: reliability
status: CLOSED-UNSCORED 2026-08-05 — matrix protocol-failed-at-controls at arm 1/4 (control-simple PLAN_INVALID: standalone `plan complete` without the atomic IMPLEMENT carrier; R-final Codex CONFIRM); candidate arms unscored, R1 + LF instruction NOT refuted; product edits stay landed on formal verification; NO SHIP CREDIT; failure class → NEW registration
complexity: high
depends_on: ["0094-r5-regate", "0092-plan-native-foreground-dispatch"]
---

# iter-0095 — PLAN delivery byte-fidelity

## Why this iter exists (pre-flight 0)

This iter exists because it closes the last open conjunct of the
0089/0090/0094 delivery-compliance lineage: live byte-exact PLAN delivery.
iter-0094's matrix ran past controls for the first time and failed exactly
one bar — candidate-discovery delivered the rendered PLAN prompt minus its
single terminal LF (10,015 vs 10,016 bytes; DECISIONS 0094.1). The design
round (2026-08-05, receipts `~/.local/share/nx01/iter0095-design/`)
refuted the orchestrator's "invisible byte" position via its own
precommitted falsifier F2 — Claude Code's Read output renders a terminal
LF as a final empty numbered line, verified in both retained 0094
sessions plus a no-LF control — so the adopted remedy is an
instruction-only amendment under the named criterion OBSERVABLE RECEIPT
INTEGRITY: keep the byte-exact digest gate, keep the 0094 verdict, amend
only the Claude PLAN-delivery instruction. Mission 1; it advances the
ceiling gate lineage (live delivery credit for R1's native foreground
dispatch, H1-v3 unblocking behind it).

## Candidate product change — LANDED (not yet live-credited)

One sentence inserted into `config/skills/devlyn:resolve/SKILL.md` PHASE 1
round-0 dispatch paragraph (+ `.agents`/`.claude` mirrors byte-identical):

> In Read output, a final empty numbered line denotes the file's terminal
> LF — reproduce that LF at the end of the `prompt` field; if no empty
> numbered line appears, do not add one.

Shipped via `/devlyn:resolve --spec docs/specs/iter0095-plan-delivery-byte-fidelity/spec.md
--pair-verify` (executor pin codex): run `rs-20260805T084519Z-2ef5617f73fa`,
commit `8f99b51`, VERIFY PASS 3/3 (mechanical + codex primary + claude
pair), finish gate clean. No renderer change, no digest/state/oracle
change, no normalization layer. Pre-named escalation path: if a live 2/2
bar still fails WITH the explicit cue, that evidence justifies artifact
canonicalization (renderer emits no terminal LF) in a successor round —
not before.

Satisfiability receipt (register as such): 0094's candidate-simple
delivered byte-exact WITH the trailing LF through the identical
Read→transcribe route (all three digests `ff7bda46…`); the retained
LF/no-LF contrast pair is the registration's satisfiability evidence.

## Instrument follow-ups folded into this registration (freeze-closed at R0, 2026-08-05)

Both fired at 0094 first contact, scored against no one (DECISIONS 0094.1).
Drafts + proofs: `~/.local/share/nx01/iter0095-reg/` (git). R0 seats: Codex
gpt-5.6-sol REVISE + Grok 4.5 REVISE (receipts `r0-codex-response.log`,
`r0-grok-response.log`, packet sha `ea31a470…`).

Ownership (freeze-closed, both seats convergent): **oracle evidence
scoping is product-owned** — it lands via its own `/devlyn:resolve` run on
`benchmark/ceiling/scripts/plan-dispatch-oracle.py` BEFORE freeze
completion, and the frozen-assets manifest names the post-patch PRODUCT
oracle sha256; a registration-owned oracle fork/overlay is forbidden (the
registration scorer loads the product oracle path). The **dispatch-scorer
artifacts clause is registration-owned**; freeze pins the scorer sha after
selftest green.

### A — oracle evidence scoping (adjudicated rule; F1 fired in orphan-correlation form)

R0 split: Codex fired F1 with bytes — pinned 2.1.222 emits no-`message`
`attachment` records carrying `hookName PreToolUse:Agent`/`PostToolUse:Agent`
plus the exact `toolUseID` (retained session `1809fe7f…jsonl:176,178`), and
2.1.220 `system/task_started` dual-writes the full Agent prompt
(`canary1/sessions/parent.jsonl:95`) — so an unconditional key-absence skip
can launder dispatch CARDINALITY in a partially truncated session (one
message-path record lost, hook record retained → hidden second dispatch
scores COMPLETE; 0091 Stage B's cardinality gate is the precedent that two
exact-prompt uses in one window is a violation). Grok ruled NOT-FIRED
(delivery carrier is message-path only; skip alone cannot mint COMPLETE)
and rejected Codex's full typed-table + metadata collection as scope
expansion / a rot vector. Orchestrator adjudication (named delta: the
`:176,178` attachment bytes were unexamined when P3 was written; decisive
criterion (3) fail-closed against real malformation): adopt the MINIMAL
ORPHAN-CORRELATION rule —

1. A record WITHOUT a `message` key that references an Agent tool-use
   identity (an Agent hook `toolUseID`, or a `system`/`task_*` record
   carrying an Agent `tool_use_id`/prompt) must CORRELATE to a
   message-path collected Agent tool_use/tool_result id; an orphan
   reference is an evidence issue (INCOMPLETE). No collection of parallel
   metadata as evidence; identity correlation only.
2. A record WITHOUT a `message` key and WITHOUT any Agent identity
   reference is benign — skipped, no issue (this closes the 0094 false
   INCOMPLETE: summary/file-history/non-Agent-hook records). No typed
   record-`type` allowlist (rot vector).
3. A record WITH a present non-dict `message` stays `message-not-object`.
4. `subagent_type`: ABSENT key = valid (0092 freeze "leave selection to
   the parent / no key-set pin"; live 0094 shape omits it); present but
   null/non-string/empty = malformed. (F3 not fired: zero explicit nulls
   in retained sessions.)
5. Self-tests added: benign no-message (clean), correlated Agent-hook
   no-message (clean), ORPHAN Agent-hook no-message (INCOMPLETE),
   no-message without Agent reference (clean), absent-`subagent_type`
   (valid/ACCEPTED); present-non-dict `message` case retained.

**Freeze gate — EXECUTED GREEN on landed bytes (2026-08-05)**: oracle
landed as `e72bd1d` (sha `94a2c5d7…`, pinned in
`iter0095-reg/frozen-assets.sha256`) through its own resolve outer loop —
run 1 `rs-20260805T100034Z` halted honestly at BLOCKED:verify-exhausted
(both VERIFY judges converged on a payload-boundary basename-collision
collapse the fix-round self-test had masked by asserting an internal
intermediate), spec amended (orphan `<file>` = collision-free source;
regression through the analyze() payload), run 2 `rs-20260805T103907Z`
PASS 3/3. Freeze-gate replays on full-arm COPIES (receipt-mutation
lesson: the oracle writes its JSON into the result dir, and `sessions/`
is a SIBLING of `result/` — copy the arm, not `result/`): 0091 C1 =
COMPLETE/0, 0091 C2 = CONTRACT-VIOLATION conserved, 0094
candidate-simple = COMPLETE + `ff7bda46…` (its real 2.1.222
hook-attachment records correlate cleanly), 0094 candidate-discovery =
CONTRACT-VIOLATION conserved with delivered `c9d8a32e…` — the 0094
failure is not laundered. Self-test 299 assertions.

### B — dispatch-scorer artifacts clause (registration-owned scorer)

The 0094 scorer's implement-carrier rule treats the product's canonical
spawn skeleton as a mutation: `bool(implement.get("artifacts"))` is truthy
for `{"findings_file": null, "log_file": null}` — the exact value
`state-phase-write.py:1350` writes on every spawn and the senior watcher
explicitly allowlists (`plan-stop-watch.py:271-272`,
`artifacts not in (None, {}, {"findings_file": None, "log_file": None})`).
Fired `implement-carrier-mutated` on all four 0094 arms; unsatisfiable
against the writer. Fix: align the scorer clause to the watcher allowlist;
ADD BOTH selftest cases (skeleton → clean; genuinely non-null value →
mutated). Built + 16/16 green; independently re-executed by the Grok R0
seat (seat-execution rule satisfied). R0 both seats FREEZE this clause.

## Carry-over from 0094 (re-freeze, do not redesign)

- Amended registration-owned watcher: preparation files
  `implement.task-context`/`implement.prompt` allowed; forbidden =
  `implement.stdout`/`implement.stderr`; grace 5000 ms + pre-arm SIGINT
  wind-down preflight.
- Branch (non-detached) arm worktrees; FRESH worktree path per attempt.
- Four serial ABBA arms (control-simple → candidate-simple →
  candidate-discovery → control-discovery), Sonnet 5 parents via a
  run-owned pinned CLI; frozen goal invocation
  `Run /devlyn:resolve --no-risk-probes "<goal>"`.
- Opaque arm tokens + sealed token→condition mapping commitment.
- Neutral machine-local sibling base commits REGENERATED at the new
  candidate SHA: identical parent + metadata; candidate tree = current
  main tree; control tree = candidate with ONLY the PLAN-dispatch product
  hunks reverse-applied (0094 patch `iter0094-reg/plan-dispatch-product.patch`
  PLUS the new instruction sentence from `8f99b51`); mutual delta = the
  hypothesis SKILL.md bytes only.
- sha-anchored frozen assets manifest (driver, goals, watcher, scorer,
  oracle SHA, IMPLEMENT heading source, CLI pin).
- FRESH controls + FRESH judging nonce (0088.3 rule; 0094's nonce
  retired). Infra replacement only before any in-window PLAN Agent use.

## Bars (pre-committed)

1. **Candidate structural**: 2/2 byte-exact deliveries (digest conjunct
   unchanged — render sha == state sha == delivered sha) via the frozen
   oracle on FULL-DIR arm sessions.
2. **dispatch_clean == true** all four arms via the corrected scorer.
3. **Watcher PASS** all four arms (SIGINT-only at 5000 ms grace).
4. **Blind no-loser quality**: Fable 5 + Grok 4.5, fresh nonce
   commitment, findings schema `target A|B|both` with file:line evidence
   MANDATORY per finding (the mechanically-checkable citations are what
   made 0094's judge attribution swap provable); candidate-only excludes
   `both`; strict no-loser gate — a HARD conjunct (can deny ship credit)
   that is NON-RESTORATIVE (can never compensate a failed structural
   bar). R0 both seats FREEZE this reading.
5. **Duration tripwires**: candidate ≤1.25× control summed; ≤1.50× per
   arm.

Ship rule: all bars pass → R1 (native foreground PLAN dispatch,
`83b275e`) plus the delivery instruction earn live delivery credit; any
bar fails → no ship credit, failure class routes to a NEW registration
(never amendment-in-place).

## Operator rules (binding, now default)

- Seat re-invocations MUST carry a liveness marker + the seat's
  self-computed sha256 of the current packet/file bytes (0094 measured a
  byte-identical stale re-emission from a Codex seat re-call; ruled
  invalid on seat-liveness).
- Never `/login` or rotate the host OAuth token while an arm is in
  flight.
- Judge emissions = a single JSON object only (prose breaks collection).
- No pipeline launch while any other process writes the same repo's
  `.devlyn` (0089 rule).
- Operator data point from the product run (2026-08-05): the
  orchestrator-surface Read display did NOT render the final-empty-
  numbered-line cue for `.devlyn/plan.prompt` in the Fable session,
  while F2's evidence base (pinned 2.1.222 Sonnet worker sessions)
  does render it. The matrix parents ARE the pinned-CLI surface, so F2's
  base holds for the experiment; the discrepancy is registered as an
  observation only — if the live 2/2 bar fails with the cue absent from
  the failing parent's Read result bytes, that is falsifier-relevant
  evidence for the canonicalization successor, not an instruction
  failure.
- codex-cli 0.146.0 workspace-write sandbox hard-denies `.agents/`
  writes (probe-confirmed); pipeline IMPLEMENT/CLEANUP rounds on this
  repo need `-c 'sandbox_workspace_write.writable_roots=[<repo>/.agents]'`.
  Product follow-up (separate from this iter): adjudicate adding this to
  `_shared/codex-config.md` canonical workspace-write invocation.

## Registered product follow-ups (schedule separately, not conjoined)

- `resolve-bootstrap.py` `git_text` ignores `allow_empty` on nonzero exit
  (detached-HEAD unbootstrappable).
- `verify-merge-findings.py` crosschecks every `*judge.stdout` as
  pair-side evidence (flipped-seat false BLOCKED).
- `devlyn:engines/SKILL.md` absent from lint `critical_path_files`.
- `_shared/codex-config.md` workspace-write invocation vs codex 0.146.0
  `.agents` sandbox denial (this session's live finding).

## Freeze protocol (required before any arm)

R0 adversarial (Codex gpt-5.6-sol + Grok 4.5 + Fable orchestrator
position stated first) on this file + the draft instrument patches + the
bars; R1 reconciliation on the amended whole; Terra executes instrument
proofs (scorer selftests, oracle full-dir replays) — a freeze is not
frozen until a seat has tried to satisfy every conjunct by execution
(0081-0083 lesson). Receipts: `~/.local/share/nx01/iter0095-reg/` (git,
sha-anchored).

## MATRIX TERMINAL (2026-08-05) — CLOSED-UNSCORED protocol-failed-at-controls

Arm 1/4 (token `cbf6af50` = control-simple, base `559e244`, pinned CLI
2.1.222, Sonnet 5 parent) died `PLAN_INVALID` under the frozen watcher:
the parent completed PLAN with a STANDALONE
`state-phase-write.py --phase plan complete --verdict PASS` (session
`5fcbfe61…jsonl:181`; SPW calls at lines 68/158/181, NO transition verb),
leaving `phases.implement = null` when `plan.completed_at` appeared —
the exact atomic-carrier fail-closed class the watcher exists to catch
(0092 adjudication, re-frozen here). SIGINT 6 ms after the write; clean
wind-down; startup_ms 136,267. Failure is AFTER in-window PLAN Agent use
→ no infra replacement; watcher-PASS-4/4 conjunct unsatisfiable → frozen
ship rule terminates the matrix. R-final Codex gpt-5.6-sol CONFIRM with
liveness marker (receipts `/tmp/r-final-0095-arm1.log`, copied to
`iter0095-reg/`): no legal continuation for score; remaining arms only
runnable as explicitly non-scoring diagnostics; failure class correctly
named **condition-independent PLAN→IMPLEMENT transition-protocol
compliance variance** (the violated atomic-transition contract is shared
text, outside the sibling hypothesis delta). Successor registration owns
BOTH: the still-owed delivery byte-fidelity credit AND the newly measured
transition-compliance variance (0094's "control delivery varied" bonus
finding is the same both-conditions product-variance family). Receipts:
`~/.local/share/nx01/iter0095-matrix/` (arm, sessions, worktree
retained), `~/.local/share/nx01/iter0095-reg/` (git).
