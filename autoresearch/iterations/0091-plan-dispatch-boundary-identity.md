---
id: "0091-plan-dispatch-boundary-identity"
title: "PLAN dispatch-boundary identity — outcome-independent oracle + exact Agent.prompt population"
kind: reliability
status: REGISTERED-FROZEN 2026-08-03 — Fable 5/Grok 4.5 R1 CONFIRM; Terra satisfiability PASS
complexity: medium
depends_on: ["0089-plan-authority", "0090-plan-delivery-compliance"]
---

# iter-0091 — PLAN dispatch-boundary identity

## Why this iteration exists (pre-flight 0)

iter-0090 implemented worker-scoped PLAN render inputs and passed every
mechanical/build/VERIFY gate, but its two live Sonnet canaries scored 1/2.
Canary 2 delivered the recorded render byte-for-byte. Canary 1 opened a
schema-complete PLAN receipt, read `.devlyn/plan.prompt`, then populated the
sole native `Agent.prompt` field with the literal 68-byte string
`$(cat /Users/aipalm/Documents/GitHub/devlyn-cli/.devlyn/plan.prompt)` instead
of the 9,196-byte render. The worker recovered by reading the path, wrote a
valid plan, and returned PASS, but the delivery contract was violated.

The current oracle compounded the product failure: it recognizes PLAN Agent
calls by finding the canonical heading inside the delivered prompt
(`benchmark/ceiling/scripts/plan-dispatch-oracle.py:19-20,141-157`). Because
the mismatched 68-byte prompt lacks that heading, it classified a fully
captured adverse dispatch as `INCOMPLETE`/missing evidence rather than
`CONTRACT-VIOLATION`. Fable 5 and Grok 4.5 independently classified the arm
NONCOMPLIANT and named both the parent prompt-population boundary and the
heading-stem instrumentation residual
(`~/.local/share/nx01/iter0090-reg/canaries/fable-adjudication.log`,
`grok-adjudication-final.log`; 0090 implementation/adjudication record).

**Mission-bound**: Mission 1 single-task harness reliability. This iteration
closes the measured render-to-native-dispatch link required before H1-v3 can
be re-registered. It makes no startup/wall/quality claim and adds no model
call, dispatcher, parallel substrate, or M1.5 mechanism.

## Root cause / violated invariants

1. Why did Canary 1 deliver a path expression after reading the file? The
   current product instruction says only "deliver `.devlyn/plan.prompt`
   verbatim" (`config/skills/devlyn:resolve/SKILL.md:104,112`). It specifies
   the desired result but not the native tool-field operation. One parent
   treated the non-shell `Agent.prompt` field as if it evaluated shell syntax.
2. Why did the oracle call captured adverse bytes missing evidence? Dispatch
   identity depends on a heading inside the delivered content. A delivery
   corruption that removes that heading therefore removes its own identity
   from the detector — the measured outcome controls whether the instrument
   can see the arm.

**Violated invariant A — Outcome-Independent Dispatch Identity**: a PLAN
dispatch must be identified from authorization and event provenance, not from
whether its delivered content happens to resemble a valid PLAN prompt.

**Violated invariant B — Data-Field Exactness**: after PLAN authorization, the
native worker's `prompt` data field must contain the exact rendered text bytes.
Paths, shell commands, command substitutions, backticks, and variable
references are different bytes and are never delivery substitutes.

## Root position before R0

Use two ordered stages so measurement is repaired before the product treatment
is scored.

### Stage A — outcome-independent oracle identity

Replace heading-content identity with ledger-window identity in the existing
oracle:

1. Collect every top-level parent-session `Agent` tool use with its timestamp,
   tool-use id, prompt string/digest, subagent type, source, and source line.
   Here top-level means the record's `parent_tool_use_id` is null. This
   exclusion applies only to Agent candidates; sidechain `Write`/`Edit`
   evidence for `.devlyn/plan.md` remains available as corroboration. A
   canonical-heading match becomes diagnostics, not the primary identity key.
2. Open a binding window for every completion-valid `d1-complete`,
   `legacy-pre-d1-four-key`, and `legacy-pre-d1-current` receipt in ledger
   order. `invalid` or unparseable timestamps fail closed and open no window.
   Bind top-level Agent calls whose timestamps lie within the inclusive
   `[started_at, completed_at]` authorization window. Delivery attestation is
   computed only from these bindings; delete the current heading-filtered,
   index-zipped receipt/dispatch path as a competing authority.
3. The normative product invariant is exactly one top-level Agent call inside
   each PLAN receipt window. Zero candidates remains evidence-INCOMPLETE. More
   than one captured candidate is an explicit product contract violation with
   every candidate surfaced; it is not missing evidence. One candidate binds
   regardless of heading and its prompt digest is compared with the receipt
   digest. If receipt windows overlap, or one Agent falls inside more than one
   window, surface the full ambiguity as a product contract violation and bind
   nothing silently.
4. Apply one-way content escalation outside the windows: a top-level Agent
   prompt with the canonical PLAN heading outside every authorization window
   is conclusive `plan-dispatch-outside-authorization-window` product evidence.
   Heading presence may escalate captured evidence; heading absence may never
   exculpate an in-window Agent or turn its bytes into missing evidence.
   Other out-of-window Agents remain non-PLAN diagnostics.
5. Bump the oracle output schema from 1 to 2 because identical input changes
   identity authority and classification. Rename the advertised authority to
   `ledger-window+top-level-parent-Agent`; retain heading fields only under
   diagnostics.

This is an instrument repair, not product ship credit. It must replay the five
retained iter-0088 shapes plus both 0090 canaries before Stage B begins.

### Stage B — exact native Agent.prompt population

Replace the ambiguous delivery sentence in the canonical resolve skill with
the smallest concrete native-tool contract:

- immediately before a Claude Code PLAN dispatch, load
  `.devlyn/plan.prompt` and set the native `Agent` tool's `prompt` field to the
  exact file content — the renderer output bytes whose SHA-256 preimage is the
  receipt's `prompt_sha256`; the line-numbered/truncated display returned by a
  Read tool is a loading aid, not the payload authority;
- state locally that `Agent.prompt` is a data field, not a shell, and therefore
  a path, `$(cat ...)`, command text, backticks, or variable reference is not
  the rendered prompt;
- use the same procedure for the sole round-1 corrective re-spawn;
- preserve the current engine/model choice, subagent-type freedom, renderer,
  raw adapters, ledger, cap, task context, and worker prompt bytes.

Both 0090 arms already performed a pre-dispatch Read, so that step is not the
treatment. The tested delta is the explicit file-bytes/data-not-shell contract.
Do not pin `subagent_type=claude` merely because the compliant arm used
`claude` while the non-compliant arm used `general-purpose`: the parent chooses
the prompt field before either worker consumes it, so that correlation does
not establish the worker type as the cause. The accepted falsifier is a live
exact-prompt failure under whichever supported native type each arm's parent
chooses; two uncontrolled arms do not promise coverage of both types.

## Subtractive-first record

1. **Delete to avoid addition**: demote the circular heading-content selector;
   reuse the already-shipped ledger timestamps rather than add a dispatch id,
   state field, transcript interceptor, or wrapper.
2. **Delete to make smaller**: replace the two ambiguous "deliver file
   verbatim" clauses with one exact data-field procedure and one round-1
   reference; do not add a new adapter or renderer mode.
3. **Minimum addition**: ledger-window binding in the existing oracle, its
   retained-receipt tests, and the exact native `Agent.prompt` operation in the
   existing PHASE 1 prose. Every added branch is backed by Canary 1 or by the
   zero/multiple-candidate falsifiers required to make the identity total.

## Deliverables — closed list

**A1 — Oracle collection and binding.** Edit only
`benchmark/ceiling/scripts/plan-dispatch-oracle.py`. Separate raw top-level
Agent collection from receipt-window binding; remove both heading match and
index-order zip as identity authorities; retain heading match as diagnostics
plus the out-of-window one-way escalator. Scope sidechain exclusion to Agent
candidates so plan-writer corroboration remains intact. Bump only this oracle's
output schema to 2.

**A2 — Oracle self-test and retained replay.** Extend the in-file self-test
with real-receipt-derived fixtures for: heading-less captured mismatch, zero
candidate, two candidates in one receipt window, overlapping windows / one
candidate matching multiple windows, malformed/missing timestamp,
heading-positive outside authorization, ordinary out-of-window non-PLAN Agent,
and Agent-only sidechain exclusion with writer corroboration conserved. Replay
retained C2, C3, F7/C1, F7/C2, F12/C1 plus 0090 Canary 1 and Canary 2 from
immutable copies. Preserve Canary 2's observed round-0 `triggered_by: "plan"`
as a diagnostic fact; do not normalize it inside 0091.

**B1 — Native prompt-field contract.** Edit the canonical
`config/skills/devlyn:resolve/SKILL.md` PHASE 1 delivery wording and synchronize
the `.claude` and `.agents` mirrors. Change no other product prompt bytes or
phase behavior.

**B2 — Existing live delivery gate.** Reuse the 0089 ledger/digest and Stage A
oracle. Run two serial fresh Sonnet PLAN canaries with the same one-file
placeholder goal and the 0090 stop rule. Terra owns mechanical fixture/replay
execution. Fable 5 and Grok 4.5 remain read-only design/adjudication seats.

## Explicitly OUT

- No prompt interception, transcript rewrite, native Agent wrapper, new state
  field, dispatch id, renderer mode, adapter file, or delivery forcing.
- No subagent-type pin, model/engine change, PLAN content determinism, cap
  change, additional PLAN round, or retry after a completed arm.
- No full native Agent-call schema or `mode` pin; only the observed `prompt`
  field failed, and both 0090 calls already used `run_in_background: false`.
- No change to the worker-scoped projection, raw adapters, PLAN canonical body,
  task-context header, or recorded digest semantics shipped in 0090.
- No H1-v3 treatment, startup envelope, wall-time credit, full-pipeline
  completion requirement, or claim about other phases/engines.
- No Fable/Grok test arm. Mechanical/replay work uses Terra; live PLAN arms use
  Sonnet.

## Frozen predictions

- **P-0091-A1 — adverse capture remains visible**: replaying 0090 Canary 1
  yields one ledger-window PLAN dispatch with delivered SHA-256 `b5f3c822…`,
  recorded SHA-256 `4474b851…`, evidence complete, product violation
  `delivered-prompt-digest-mismatch`, and classification
  `CONTRACT-VIOLATION`. Falsifier: any missing-evidence classification or lost
  captured bytes.
- **P-0091-A2 — compliant/legacy conservation**: Canary 2 remains COMPLETE
  with digest `65b101ba…`. C2 remains COMPLETE with one in-window PLAN dispatch,
  four top-level Agents total, and three out-of-window non-PLAN diagnostics.
  Enriched C3 remains evidence-complete CONTRACT-VIOLATION with three bound
  dispatches, 181,191 ms startup, 42,978 ms first composition gap, cap
  violation, and region 04:11:49.215Z→04:19:42.566Z. Raw C3 remains
  evidence-complete CONTRACT-VIOLATION with three legacy-unattestable receipts
  and the same cap fact. Raw F7/C1 remains legacy-unattestable INCOMPLETE with
  one bound dispatch, its round-continuity finding, and startup delta 0. F7/C2
  and F12/C1 retain startup 154,197/156,297 ms and delta 0 on their exact raw
  replay shapes. Falsifier: any named fact changes without raw timestamp/schema
  evidence.
- **P-0091-A3 — total cardinality and one-way escalation**: zero in-window
  candidates is INCOMPLETE only when no conclusive outside-authorization PLAN
  call exists; more than one candidate, overlapping windows, one candidate
  matching multiple windows, or a heading-positive top-level PLAN call outside
  every window is CONTRACT-VIOLATION with all captured candidates disclosed;
  malformed timestamps fail closed. Falsifier: ambiguity silently chooses one,
  content absence exculpates an in-window call, captured heading-positive
  off-ledger evidence earns plain INCOMPLETE, or any such case earns COMPLETE.
- **P-0091-B1 — exact live population**: two fresh Sonnet canaries each bind
  exactly one in-window native Agent call whose delivered digest equals the
  receipt/render digest. Falsifier: either path/command indirection, byte
  mismatch, missing capture, multiple candidate, off-ledger call, R1/R2
  recurrence, or invalid plan artifact.
- **P-0091-B2 — no adjacent regression**: exact mirror parity, existing
  renderer/state/oracle tests, raw adapter hashes, and full skill lint remain
  green. Falsifier: any unrelated product-prompt byte or existing gate changes.

## Stage gates and ship-credit boundary

### Stage A gate — instrumentation only

All must pass before Stage B implementation or canaries:

1. Oracle self-test, exact raw fixture provenance, and schema-2 assertions.
2. Five retained 0088 replays conserve their named facts.
3. 0090 Canary 1 becomes evidence-complete CONTRACT-VIOLATION with the two
   frozen digests; Canary 2 remains COMPLETE and byte-equal.
4. Full skill lint and formal pair VERIFY pass with zero HIGH/CRITICAL findings.

Stage A may ship as independently useful measurement repair if all four pass;
it grants no H1-v3 or PLAN-delivery credit.

### Stage B gate — product outcome

1. The product diff is limited to the exact PHASE 1 delivery clauses and three
   mirrors; renderer, adapter, canonical PLAN body, and state bytes are fixed.
2. Existing direct tests plus full skill lint pass.
3. Two fresh Sonnet PLAN canaries run serially after a writer check. Each has
   exactly one schema-complete ledger receipt, exactly one top-level Agent in
   its receipt window, delivered digest equal to recorded/rendered digest,
   Stage A oracle COMPLETE, valid plan artifact, and no surviving writer.
   Required score: **2/2**.
4. A compliant/non-compliant completed arm gets no replacement.
   Infrastructure-only INCOMPLETE gets at most one replacement, and only when
   raw evidence cannot decide the product outcome.

Terminal `/devlyn:resolve`, BUILD_GATE, or worker PASS is non-scoring. If Stage
B fails on a completed product arm, or if infrastructure-only INCOMPLETE
exhausts its one replacement, H1-v3 remains blocked, no delivery ship credit is
earned, and B1 plus its mirrors are reverted to the Stage A baseline before
close. Stage A stays if its independent gate passed. No failed or unscored B1
bytes survive to confound a successor baseline.

The 2/2 bar is the minimum ship bar under a permanently binding oracle, not a
residual-rate estimate. Any delivery violation in a later scored PLAN run,
including H1-v3 controls, blocks that run and reopens delivery compliance as
already required by 0090's residual register.

## R0/R1 protocol status

- [x] Root position stated before external seats.
- [x] Fable 5 R0: `GO-WITH-EDITS`.
- [x] Grok 4.5 R0: `GO-WITH-EDITS`.
- [x] Root reopened every adopted citation/receipt and records named deltas
      below.
- [x] R1 reconciliation: Fable 5 `CONFIRM`; Grok 4.5 `CONFIRM`; zero open
      findings.
- [x] FREEZE before implementation or canary execution.

## R0 record + named deltas

The independent R0 packet is
`~/.local/share/nx01/iter0091-reg/seats/r0-prompt.md`. Fable 5 ran as actual
`claude-fable-5` in read-only seat session
`a55a3903-37cc-4a01-9e48-fd501c4a6d81` and returned `GO-WITH-EDITS`;
Grok ran as actual `grok-4.5` in read-only seat session
`019fc81c-05c4-7aa3-82d7-3315ece24f3c` and returned `GO-WITH-EDITS`.
Receipts are `r0-fable-summary.md` and `r0-grok-full.md` beside the packet.

The shared R0 delta was adopted: Stage B means exact file content bytes, not a
Read tool's line-numbered/truncated display; sidechain exclusion is scoped to
Agent candidates; the three eligible receipt forms are explicit; window
cardinality and multi-window ambiguity are total; the old index zip is removed
as an authority; schema 2 names the new authority; worker subtype and the full
native Agent schema stay unpinned; failed B1 prose is reverted while an
independently passing Stage A remains; 2/2 is a minimum ship bar, not a rate
estimate.

Fable alone found the temporal blind spot in pure window identity. The adopted
delta is one-way escalation: a canonical-heading top-level Agent outside all
authorization windows is conclusive product evidence, while missing content
can never exculpate an in-window Agent. Fable also surfaced Canary 2's raw
`triggered_by: "plan"`; it is retained as a diagnostic fact, not normalized.

One R0 position remained contested. Fable described overlapping windows or a
candidate belonging to multiple windows as an evidence issue; Grok described
the same fully captured state as a product contract violation. Root resolves
this as `CONTRACT-VIOLATION`: the named delta is that all timestamps, receipts,
and candidate events are present, so the ambiguity is invalid captured product
state rather than absent evidence. R1 must explicitly confirm or object to this
resolution; no last-speaker flip is accepted.

Before R1, Terra mechanically attempted every Stage A binding conjunct against
all seven retained raw arms. Actual seat `gpt-5.6-terra`, read-only session
`019fc829-2aee-7c72-8360-6f4070e39c8f`, returned `PASS` with no unsatisfied
conjuncts and no tracked changes. Every valid window had exactly one top-level
Agent candidate; F12/C3's three windows were non-overlapping; all named startup,
composition, cap, digest, and sidechain facts remained computable. Receipt:
`~/.local/share/nx01/iter0091-reg/seats/terra-satisfiability-summary.md`.

## R1 reconciliation and freeze

Fable 5 (`claude-fable-5`, session
`9ffc9cb7-2163-4420-b591-12807f19c848`) and Grok 4.5 (requested
`grok-4.5`, model-usage key `grok-4.5-build`, session
`019fc830-53ae-7233-a29a-7bd9be55a3d4`) independently returned
`R1: CONFIRM`, `OPEN FINDINGS: []`, and `FREEZE: YES`. Receipts:
`~/.local/share/nx01/iter0091-reg/seats/r1-{fable,grok}-summary.md`.

Both seats confirmed all twelve amendments: the two-stage boundary; exact file
bytes rather than Read display/path/command text; Agent-only top-level
filtering with nested writer evidence conserved; explicit legacy windows;
total zero/one/many and overlap semantics with index zip removed; one-way
heading escalation; oracle schema 2 and authority rename; no worker subtype or
full Agent-schema pin; B1 revert with independent Stage A retained; seven-arm
Terra satisfiability; and 2/2 as a permanently re-openable minimum ship bar.

The sole R0 disagreement is resolved by a named criterion rather than seat
order. Fable reversed its “evidence issue” position after applying
CAPTURED-PRODUCT-STATE COMPLETENESS to the reopened product semantics: PLAN
receipt spans are written serially, so overlap with complete receipts,
timestamps, and candidate events means the product wrote invalid authorization
state. Grok preserved the same product-violation position. Root therefore
freezes overlap/multi-window membership as `CONTRACT-VIOLATION`, with every
candidate surfaced and no silent binding.

## Principles check (frozen)

0. Not score-chasing: closes the measured delivery boundary blocking H1-v3. ✅
7. Mission-bound: Mission 1 single-task reliability only. ✅
1. No overengineering: existing ledger windows + existing oracle + two prose
   clauses; no new runtime object or wrapper. ✅
2. No guesswork: exact raw timestamps, prompts, digests, and 1/2 outcome bind
   the hypotheses; retained replay precedes product scoring. ✅
3. No workaround: fixes circular measurement authority and the actual
   non-shell tool-field contract; worker recovery does not count. ✅
4/5. Worldclass/best practice: outcome-independent identity, fail-closed
   ambiguity, versioned classification semantics, exact-byte verification. ✅
6. Optimized: no added model call; ledger-window matching is linear in the
   tiny PLAN ledger/Agent event sets. ✅
