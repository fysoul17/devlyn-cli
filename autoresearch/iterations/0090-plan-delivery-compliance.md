---
id: "0090-plan-delivery-compliance"
title: "PLAN delivery compliance — worker-scoped render inputs"
kind: reliability
status: IMPLEMENTED 2026-08-03 — NO SHIP CREDIT; live delivery compliance 1/2; H1-v3 blocked
complexity: medium
depends_on: ["0089-plan-authority"]
---

# iter-0090 — PLAN delivery compliance

## Why this iteration exists (pre-flight 0)

This iteration unlocks the H1-v3 re-registration go/no-go by closing the one
open iter-0089 exit conjunct. The 0089 renderer, ledger, cap, and oracle are
green, but two independent live Sonnet PLAN canaries delivered prompts whose
bytes differed from the recorded render (`0089-plan-authority.md:383-425`):
canary 1 pruned the Claude adapter's pair-JUDGE invocation body and canary 2
pruned the same class plus condensed worker-irrelevant composition prose.
Delivery compliance is therefore 0/2; H1-v3 controls remain unscoreable.

**Mission-bound**: Mission 1, single-task harness reliability. This closes a
measured orchestration failure on the current product path. It adds no
dispatcher, run-scoped state, parallel substrate, or M1.5 mechanism.

## Root cause / violated invariant

1. Why did delivered bytes differ? The parent did not pass the rendered
   artifact verbatim; it removed or rewrote content before the native Agent
   dispatch (retained diffs in `~/.local/share/nx01/iter0089-reg/canary{1,2}`).
2. Why was the artifact rewritten twice? The supposed worker prompt contains
   orchestrator-only routing material: `adapters/claude.md:5-53` is an
   `## Invocation` recipe for a non-Claude orchestrator spawning a pair judge,
   while `adapters/README.md:45-50` classifies `## Role eligibility` and
   `## Invocation` as role/invocation metadata beyond the base model-prompt
   format. The PLAN body also carries composition prose and a task placeholder
   (`references/phases/plan.md:3,35,43`) although the task context is appended
   separately. Both parents supplied missing concrete cwd context; canary 1
   also appended the absolute output path. Canary 2 additionally removed the
   model-visible `## Examples and structure` section and de-bulleted the four
   runtime principles. Those are distinct one-arm residuals, not evidence that
   the typed metadata projection already closes every delivered-byte delta.

**Violated invariant — Worker-Input Relevance**: an artifact whose digest is
the delivery contract must contain only bytes meant for that worker. Engine
routing/invocation metadata remains available to the orchestrator in the raw
adapter, but must not be included in the model-visible PLAN render.

## Root/Codex position before R0

The smallest causal change is a render-time projection, not a new adapter and
not delivery forcing:

- keep raw adapter files and their `## Invocation` contracts unchanged;
- when `phase-prompt-render.py` builds a worker prompt, omit complete Markdown
  H2 sections named exactly `Role eligibility` and `Invocation`, from the exact
  heading through the byte before the next H2 heading or EOF, preserving all
  other bytes and section order;
- retain the PLAN body's adapter-injection narration (`plan.md:3`) because both
  parents delivered it and it remains true after projection; delete only the
  Claude-vs-Codex runtime preamble while retaining its four actual principles
  in their current bullet formatting, and delete the task placeholder;
- require the data-only PLAN task context to carry the absolute working
  directory and absolute `.devlyn/plan.md` output path in a fixed header before
  rendering, and have the renderer fail closed when either exact field is
  missing or non-absolute, so the parent has no missing worker context to append.

This is a hypothesis, not a ship decision. The 2/2 live result below decides it.

## Subtractive-first record

1. **Delete to avoid addition**: exclude two already-typed orchestration-only
   sections from the worker render; do not create `claude-plan.md` or duplicate
   adapter guidance.
2. **Delete to make smaller**: remove the runtime routing preamble and dead task
   placeholder. Keep line 3: deleting a byte both controls delivered would add
   an unobserved treatment delta.
3. **Minimum addition**: one deterministic adapter projection inside the
   existing renderer plus its byte-preservation self-test; one task-context
   contract line in the existing PLAN orchestration prose. No new runtime file,
   flag, schema field, oracle, or model call.

## Official-guide acceptance

- Anthropic's current prompting guide says prompt formatting influences output
  and recommends clear structure for mixed instructions/context; worker and
  orchestrator contracts should therefore not share one model-visible block:
  <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices>.
- Claude Code's official headless guide treats `claude -p`, tool permissions,
  and structured output as CLI invocation concerns. Those bytes belong to the
  orchestrator's raw adapter contract, not a PLAN worker prompt:
  <https://code.claude.com/docs/en/headless>.

## Deliverables — closed list

**D1 — Worker-scoped adapter projection.** Edit
`config/skills/_shared/phase-prompt-render.py` and its two installed mirrors
(`.claude/skills`, `.agents/skills`; three copies total).
Before concatenation, remove complete H2 sections named exactly
`Role eligibility` and `Invocation`, with section extent ending immediately
before the next start-of-line H2 or at EOF; preserve every other byte. Assert on
the projected **adapter bytes** (not the whole prompt, whose task text may quote
the headings) that neither excluded H2 survives. The raw adapter
file is not edited, so `engine-preflight.md` and VERIFY still read its invocation
contract. Self-test covers: both excluded sections, a kept Identity section,
binary/non-normalized bytes outside excluded ranges, and Codex's no-metadata
adapter plus omp's no-metadata shape remaining byte-identical.

**D2 — Worker-ready PLAN inputs.** Edit the canonical PLAN body to delete only
the runtime routing preamble and task placeholder; retain line 3 and the four
principle bullets byte-for-byte. Edit the PLAN render contract in
`devlyn:resolve/SKILL.md` so `.devlyn/plan.task-context` starts with fixed
absolute cwd and output-path fields before rendering. The renderer validates
that fixed header and exits nonzero before writing `.devlyn/plan.prompt` when a
field is missing or non-absolute. Sync the three skill mirrors.

**D3 — Existing oracle only.** Change no oracle code. Reuse
`benchmark/ceiling/scripts/plan-dispatch-oracle.py` to compare every live
worker-received PLAN prompt with its recorded digest. A missing capture remains
INCOMPLETE; any byte mismatch remains non-compliant. Detection is not success.

## Untreated residual register (R0 amendment; verdict-binding)

- **R1 — model-guidance prune**: canary 2 alone removed `## Examples and
  structure`; canary 1 retained it. Preemptively deleting that model-visible
  guidance would violate the projection boundary and confound the treatment.
- **R2 — principle-format rewrite**: canary 2 kept the four principle sentences
  but removed their Markdown bullets; canary 1 retained the rendered form. D2
  removes the worker-irrelevant preamble, not the bullet formatting.

R1/R2 are named, untreated, and replacement-ineligible. Any recurrence in a
completed canary is a non-compliant arm, never infrastructure INCOMPLETE. Every
future **scored** PLAN delivery run in this ladder, including the H1-v3 controls,
must retain the mismatch diff and run the existing delivery oracle; otherwise
the run is unscoreable. This register is honest bounding, not ship credit.

## Explicitly OUT

- No native-Agent interception, prompt rewrite, transcript parser, or delivery
  forcing.
- No new phase-specific adapter file, adapter schema, renderer mode flag, or
  general Markdown framework.
- No change to the raw `## Invocation` text or pair-JUDGE routing.
- No PLAN content determinism, dispatcher, cap-value change, H1-v3 treatment,
  or startup/wall claim.
- No Fable test arm. Mechanical/replay work routes to Terra; live PLAN canaries
  route to Sonnet. Fable 5 and Grok 4.5 are design/adjudication seats only.

## Frozen-candidate predictions (R0 may amend before freeze)

- **P-0090-1 — projection exactness**: a Claude-shaped adapter loses exactly
  the two orchestration-only H2 sections and retains every other byte; a
  Codex- and omp-shaped adapters with neither section are unchanged. Falsifier:
  excluded bytes survive, worker guidance disappears, the section extent eats
  the following H2, or kept bytes normalize/change.
- **P-0090-2 — raw-contract conservation**: raw
  `adapters/claude.md` remains byte-identical and existing engine-preflight /
  VERIFY invocation checks remain green. Falsifier: any raw adapter delta or
  existing invocation check failure.
- **P-0090-3 — live compliance**: two serial fresh Sonnet `/devlyn:resolve`
  canaries each record a prompt digest and the existing oracle classifies the
  delivered PLAN prompt COMPLETE with byte equality. Falsifier: either
  mismatch, missing delivery evidence, off-ledger dispatch, or contract
  violation, R1 recurrence, or R2 recurrence. Detector output alone does not
  satisfy this prediction.
- **P-0090-4 — no worker-output regression**: both canaries produce a
  mechanically valid `plan.md` with the expected authorized surface and
  acceptance restatement; full skill lint stays green. Falsifier: either PLAN
  artifact fails its existing gate or any lint regression.

## Candidate exit gate — all conjuncts independent

1. D1 self-test proves exact-H2 projection/extent, fixed task-context validation,
   and byte preservation on both metadata-bearing and metadata-free adapter
   shapes.
2. Existing state/renderer/oracle self-tests and full `bash scripts/lint-skills.sh`
   pass; raw invocation contracts remain unchanged.
3. Two fresh Sonnet PLAN canaries run serially with a pre-launch writer check;
   each has exactly one legal PLAN dispatch, schema-complete ledger receipt,
   delivered digest equal to rendered digest, oracle class COMPLETE, and a
   valid plan artifact. **Required score: 2/2.** No replacement after a
   compliant/non-compliant completed arm; infrastructure-only INCOMPLETE gets
   at most one pre-registered replacement.
4. No process from either canary remains capable of writing the repository's
   `.devlyn` before the next arm or adjudication.

Terminal `/devlyn:resolve` or BUILD_GATE success is explicitly non-scoring for
this PLAN-delivery gate. The two canaries still run on the real product path;
the gate reads only the PLAN ledger, delivery bytes, plan artifact, and writer
isolation named above.

If any conjunct fails, ship nothing from 0090 and keep H1-v3 blocked. A PASS
proves only worker-scoped PLAN delivery compliance on these two Sonnet canaries;
it does not prove general prompt-delivery determinism for other phases/engines.

## R0/R1 protocol status

- [x] Root position stated before external seats.
- [x] Fable 5 R0: `GO-WITH-EDITS`; strongest counter, strongest root position,
      synthesis,
      decisive criterion, accepted falsifier.
- [x] Grok 4.5 R0: `GO-WITH-EDITS`; same shape, independent read-only evidence
      search.
- [x] Root reopened every adopted citation/receipt and recorded named deltas.
- [x] R1 reconciliation: Fable 5 `CONFIRM`, Grok 4.5 `CONFIRM`; no open
      finding or contested position remains.
- [x] FREEZE before implementation or canary execution.

## Principles check (final)

0. Not score-chasing: closes the one open delivery conjunct that blocks the
   already-registered H1-v3 go/no-go. ✅
7. Mission-bound: Mission 1 single-task orchestration reliability; M1.5 and
   parallel surfaces excluded. ✅
1. No overengineering: project existing metadata sections at the existing
   renderer; no new file/flag/schema/oracle. ✅
2. No guesswork: 0/2 retained baseline, 2/2 precommitted treatment bar, detector
   success explicitly insufficient; the measured 1/2 result controls. ✅
3. No workaround: repair the worker/orchestrator boundary that caused both
   rewrites; no stronger imperative or forced delivery. ✅
4/5. Worldclass/best practice: exact-byte contract remains fail-closed; raw
   invocation surface conserved; official guidance cited. ✅
6. Layer-cost-justified: zero added model calls in product; only local byte
   projection. ✅

## R0 record + named deltas (2026-08-03)

Durable receipts: `~/.local/share/nx01/iter0090-reg/seats/`
(`r0-packet.md`, extracted delivered prompts + unified diffs + SHAs,
`r0-grok.log`, `r0-fable-embedded.md`, `r0-fable.log`). Fable's initial
read-tool transports failed and were terminated; its accepted R0 came from a
fresh no-tool Fable 5 session over the embedded verified bytes. Grok 4.5 read
the same source packet and returned independently.

Both seats returned **GO-WITH-EDITS** under **Causal Surface Closure**. Root
adopted four evidence-backed deltas after reopening both retained diffs:

1. **Incomplete mismatch inventory withdrawn**: canary 2 also removed Examples
   and de-bulleted principles. They are now R1/R2, verdict-binding and
   replacement-ineligible, not silently treated.
2. **Line-3 deletion withdrawn**: both parents retained adapter-injection
   narration, and it remains true. Zero unobserved delta outranks cosmetic
   subtraction here.
3. **Projection extent pinned**: exact H2 name through pre-next-H2/EOF; assert
   only the projected adapter, so user task text may still quote the headings.
4. **Context obligation made fail-closed**: fixed absolute cwd/output header is
   validated before render, not trusted to prose alone.

Fable's proposed 3/3 escalation was conditional on a canary-only oracle. The
oracle remains binding on all post-freeze scored PLAN runs, so the minimum bar
stays 2/2; any R1/R2 recurrence fails rather than consuming a replacement.

## R1 confirmation + freeze (2026-08-03)

Receipts: `~/.local/share/nx01/iter0090-reg/seats/r1-packet.md`,
`r1-fable.log`, and `r1-grok.log`.
Grok re-read the amended draft and every cited product surface; Fable rechecked
the 43-line PLAN body, all adapter H2 inventories, raw Grok eligibility,
renderer mirrors, and 0089 in-repo adjudication record. Both marked amendments
1–9 PASS, reported **NAMED DELTA: none**, **OPEN FINDINGS: none**, and returned
`R1:CONFIRM`. The registration is therefore frozen exactly as written above.
Any design, prediction, residual, replacement, or exit-gate change after this
line requires a dated named-delta amendment before implementation/test output
is observed; silent in-flight substitution is forbidden.

## Implementation and live adjudication (2026-08-03)

The frozen registration landed without expanding its product surface:

- registration freeze: `b2f9c76`;
- implementation: `f273877` — canonical renderer, PLAN body, and resolve
  contract plus tracked `.agents` mirrors; ignored `.claude` mirrors were
  synchronized byte-for-byte;
- direct full skill lint: exit 0, `All checks passed` (123.57 seconds);
- formal verify-only run `rs-20260803T135631Z-5cbc6a7c37e9`: all 12
  mechanical commands PASS, Codex primary PASS, Sonnet pair PASS, zero merged
  findings, finish gate PASS. The full lint was consumed as direct BUILD_GATE
  evidence rather than duplicated inside the fixed 60-second literal verifier,
  per the iter-0085a carrier contract.

The implementation gates therefore passed, but they were explicitly
non-scoring for the live delivery outcome. Both serial canaries used the same
one-file placeholder goal and stopped after the first schema-complete PLAN
receipt plus valid `.devlyn/plan.md`; pre-launch and post-stop receipts show no
surviving repository writer.

| Arm | Raw result | Frozen classification |
|---|---|---|
| Canary 1 — run `rs-20260803T140946Z-a6616b2c408e`, session `f202bd4a-0170-479f-8cf9-387f775ccc62` | One `Agent` tool use delivered the 68-byte literal `$(cat /Users/aipalm/Documents/GitHub/devlyn-cli/.devlyn/plan.prompt)` instead of the 9,196-byte recorded render `4474b851…`; `delivery.diff` replaces all 112 rendered lines. Ledger receipt and one-file plan are valid. The oracle reports `INCOMPLETE` only because its heading-stem finder counts this captured tool use as non-PLAN (`agent_tool_use_count=1`, `plan_dispatch_count=0`); delivery attestation is FAIL. | **NONCOMPLIANT**, completed and replacement-ineligible. Capture exists and proves a mismatch; detector labeling cannot convert adverse evidence into missing infrastructure evidence. |
| Canary 2 — run `rs-20260803T141850Z-81b6e448870c`, session `88479197-185c-4da4-aaec-ee906b8e0754` | Exactly one heading-bearing PLAN dispatch; recorded, rendered, and delivered SHA-256 all `65b101ba…`; oracle `COMPLETE`, delivery PASS, startup PASS, valid one-file plan. | **COMPLIANT**. |

Score: **1/2** against the frozen **2/2** requirement. Exit-gate conjunct 3
fails, so 0090 earns **NO SHIP CREDIT** and H1-v3 remains blocked. No
replacement canary is authorized: Canary 1 is a completed non-compliant arm,
not infrastructure-only INCOMPLETE.

Fable 5 and Grok 4.5 independently read the frozen registration and raw
receipts, then unanimously returned `NOT-SHIP`, `CANARY-1: NONCOMPLIANT`, and
`SCORE: 1/2`. Receipts are durable at
`~/.local/share/nx01/iter0090-reg/canaries/`, especially
`canary1/delivery.diff`, both `result/plan-dispatch-oracle.json` files,
`fable-adjudication.log`, and `grok-adjudication-final.log`.

## Successor frontier — named, not implemented

Canary 2 proves the worker-scoped renderer can be delivered byte-identically;
Canary 1 exposes the next violated invariant at the parent dispatch boundary:
the bytes populated into `Agent.prompt` must equal the recorded render, not a
shell-style path indirection that the non-shell tool field never evaluates.
Any treatment requires a new frozen registration before code or live arms.

Carry one separate instrumentation residual into that registration: the
current oracle's heading-stem identity finder classifies a fully captured,
heading-less mismatched Agent dispatch as `INCOMPLETE`/missing evidence. This
made replacement status disputable even though the raw bytes decide the arm.
Do not silently fix the oracle inside the dispatch treatment; specify and
score the classification boundary explicitly.
