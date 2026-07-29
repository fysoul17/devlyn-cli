---
id: "0087-startup-semantic-dedup"
title: "Remove duplicated free-form discovery before PLAN"
kind: optimization
status: FROZEN
complexity: medium
depends_on: ["0086-claude-primary-model-attestation"]
---

# iter-0087 — remove duplicated free-form discovery before PLAN

## Why this iteration exists

Iter-0077 revoked the mechanical-absorption startup claim: moving PHASE-0
steps into a script did not stop the model from re-deriving their semantic
context at LLM latency (`0077-wall-residual-lever.md:383-390`). The corrected
`nodeg-hook-20260722c` baseline now registers startup at 193,016 ms,
interphase wait at 50,600 ms, phase union at 1,661,503 ms, and elapsed at
2,068,641 ms. The old 250-second startup estimate is superseded.

The surviving F12 receipt makes the next mechanism falsifiable. Before PLAN,
the orchestrator made 26 tool calls and read the task's server, tests, package,
secret, and sample event to author generated criteria. The fresh PLAN worker
then read the generated criteria and the same task files again. For the six
surviving raw-session rows, median pre-PLAN tool calls were 25 and median
startup was 191,798.5 ms. This is duplicated semantic discovery, not missing
mechanical absorption.

The 600-second foreground BUILD_GATE transport failure is explicitly outside
this iteration. It remains deferred to the Mission 1.5 deterministic runner.

## Team R0 and named deltas

Codex, Fable 5, and Grok 4.5 independently reviewed the raw-receipt packet.
All returned `GO-WITH-EDITS` and rejected prompt-only compression and a new
pre-LLM controller.

- Codex proposed checkpointing after criteria and resuming the same worker.
- Fable searched the current worker surface and found no supported PLAN-worker
  resume primitive. It replaced that proposal with one ordered worker return:
  write criteria first, then plan, then return.
- Grok independently named the same blocker **Unsupported-Resume Primitive**
  and accepted the ordered one-return shape under **Frozen-Criteria Authority,
  not Dual-Mind Authorship**.
- Orchestrator correction after R0: `SKILL.md:104` binds product PLAN to Claude.
  A Terra PLAN treatment for F7 would therefore conflate the mechanism with an
  engine change. Both task rows must exercise the actual Sonnet PLAN route;
  Terra is reserved for mechanical transcript and result validation.

R1 reconciled both remaining questions before freeze. Codex first cited the
iter-0066 boundary that n=1 gates mechanisms, not stochastic latency claims;
Fable and Grok then adopted unconditional replication under the named criterion
**Measurement-integrity claim-type boundary**. All three also adopted
**User-visible chronology integrity**: final risk cannot be known before
criteria exist, but the sole start banner cannot move behind PLAN.

## Registered mechanism hypothesis H1-v3

**Ordered one-return co-location:** in free-form mode only, retain bootstrap,
engine preflight, untracked-baseline capture, deterministic classification,
and every exceptional halt in the parent. Open the PLAN span, then dispatch
one fresh Claude PLAN worker with the raw goal, deterministic complexity, and
the existing mini-spec quality rules. The worker must:

1. inspect the repository once;
2. write `.devlyn/criteria.generated.md` first;
3. use those exact bytes to write `.devlyn/plan.md` in the same context;
4. return only after both artifacts exist.

Immediately before dispatch, the parent emits the existing free-form start line
with `risk_probes pending`, opens the PLAN span, and dispatches. After return,
the parent hashes and registers the generated criteria, computes the unchanged
risk profile from goal plus criteria, and applies the existing PLAN checks and
small-surface probe demotion. It then emits one resolved
`risk_probes <on|off> — <reason>` line before PLAN completion/transition. If the
out-of-scope check requires the existing single PLAN re-spawn, criteria bytes
and `criteria_sha256` stay immutable: the re-spawn may revise only
`.devlyn/plan.md`. A second failure still halts. Spec and verify-only modes keep
their current single announcement and remain behaviorally unchanged.

The decisive criterion is **matched-envelope semantic deduplication without
authority collapse**. The change earns startup credit only if each task row's
`invoke_start -> PLAN complete` treatment duration is at most 85% of its
matched control, the registered startup bucket does not increase, and the
receipt shows one repository-discovery pass rather than parent-plus-worker
duplication.

## Subtractive-first answer

1. Delete the parent model's free-form repository discovery; do not add a
   second summarizer, cache, dispatcher, or controller.
2. Move existing criteria authorship rules into the already-required PLAN
   worker prompt; do not invent a new artifact or state field.
3. Keep deterministic classification, exceptional halts, raw-byte hashing,
   risk policy, and downstream validators in their current owners.
4. Do not add worker resume: the current agent surface does not provide it.

## Frozen experiment

### Rows and seats

- `F12` and `F7`, two unconditional matched control/treatment pairs each.
- Both control and treatment use the product's actual Claude Sonnet PLAN seat.
- Terra runs the deterministic receipt comparator and mechanical checks.
- Fable 5 and Grok 4.5 review design and evidence only; they do not execute
  repeated test arms.
- All four pairwise treatment/control ratios are independent ship conjuncts;
  no average or adaptive rescue may hide one failure.
- A pair with an incomplete receipt is replaced at most once. Completeness is
  adjudicated before its ratio is read; a second incomplete receipt fails the
  row as incomplete. Incomplete pairs are never scored.
- Matched means identical task snapshot, benchmark-harness tree digest,
  `.devlyn/engines.json` bytes, requested PLAN model, and product route within
  a pair. The attempt commit SHAs necessarily differ because the treatment is
  the registered product-skill diff; both are retained, and the only allowed
  non-harness delta is the exact candidate product surface below. Requiring an
  identical repository commit would make a treatment impossible because
  `run-ceiling-arm.sh:370` copies product skills from that commit.

### Required receipts

For every control and treatment retain exact runner SHA, task/attempt identity,
requested and effective PLAN model, raw session path, `invoke_start`, PLAN
completion time, registered startup duration, pre-PLAN tool sequence, and the
SHA-256 of both generated criteria and plan. Retain the final
`state.risk_profile` booleans and reasons; control and treatment must preserve
the same route result, including F12's small-surface demotion when applicable.

The treatment receipt must show that the final criteria write precedes the
first plan write, no later criteria mutation occurs, the parent-registered hash
equals the returned criteria bytes, and PLAN's Verification restatement is
verbatim. It must also show no repository read/search between those writes that
repeats a parent discovery pass. This is experiment attestation only. R1
actively searched the current product path and found no observed ordering
failure that would authorize a runtime transcript parser; adding one is out.

### Quality and halt gates

- Generated criteria preserve every goal constraint and meet the current
  mini-spec quality bar: non-empty testable Requirements, explicit scope,
  verification sentinel and commands when runnable, plus literal preservation
  of any solo-headroom or solo-ceiling contract.
- PLAN retains the authorized-surface carrier, risks, and verbatim acceptance
  restatement. No file outside the criteria-authorized goal may appear.
- Raw goal to criteria comparison loses or shades no constraint. VERIFY receives
  frozen criteria, not an independent semantic oracle for omitted goal text, so
  this remains an explicit experiment gate.
- Trivial, medium, and large-assumptions free-form routes reach PLAN.
- Zero-scope, missing solo-headroom, and missing solo-ceiling cases retain their
  exact terminal blockers before any worker dispatch.
- Spec mode and verify-only mode are unchanged controls.

## Rejection rules

Reject H1-v3 and do not ship if any of these occurs:

- any of the four valid matched pairs exceeds the 0.85 matched-envelope ratio;
- any treatment's registered startup exceeds its matched control;
- the treatment still performs two semantic repository-discovery passes;
- criteria lose or shade a goal constraint, or any exceptional halt moves into
  LLM judgment;
- satisfying ordered authorship requires worker resume, a transcript parser in
  the product path, a deterministic runner, or any BUILD_GATE transport change.

Near-miss latency with clean mechanism receipts returns to a smaller prompt or
artifact hypothesis. A criteria-quality or halt failure revokes co-location and
re-registers a different startup lever. No failure authorizes Mission 1.5 work.

## Exact candidate product surface

If and only if R1 freezes this registration and the pre-change controls are
captured, IMPLEMENT may edit the smallest subset of:

- `config/skills/devlyn:resolve/SKILL.md` and installed mirrors;
- `config/skills/devlyn:resolve/references/free-form-mode.md` and installed
  mirrors;
- `config/skills/devlyn:resolve/references/phases/plan.md` and installed mirrors;
- `config/skills/devlyn:resolve/references/state-schema.md` and installed
  mirrors, only to correct the stale `risk_profile` phase provenance;
- `scripts/lint-skills.sh` only for contract assertions required by changed
  prose.

Here, installed mirrors means only the repository-local tracked
`.claude/skills/devlyn:resolve/**` and `.agents/skills/devlyn:resolve/**` paths.
User-global `/Users/aipalm/.claude`, `/Users/aipalm/.agents`, and
`/Users/aipalm/.codex` skill paths are outside the authorized surface. Edit the
`config/skills` sources first, then use a repo-relative mechanical copy for the
two tracked mirrors.

No shared state writer, bootstrap, adapter, benchmark runner, BUILD_GATE file,
transport wrapper, prior iteration, or raw receipt may change.

Subtractive-first stale-text inventory: the rewrite must replace, not duplicate,
the current PHASE-0 criteria/risk/announcement sequence in `SKILL.md:92-98`,
the stale "gated off in PHASE 0" sentence at `SKILL.md:121-124`, the downstream
source sentence at `free-form-mode.md:84`, the source input at `plan.md:10`, and
the `risk_profile` PHASE-0 provenance at `state-schema.md:56`.

## Claim boundary

PASS would prove only that the registered free-form F12/F7 shape avoids one
duplicated semantic discovery pass and reduces the matched startup-plus-PLAN
envelope without weakening criteria or halt behavior. It would not prove a
whole-cohort wall improvement, authorize a dispatcher, change PLAN engines,
generalize to spec mode, or solve the 600-second transport boundary.

## Principles check

0. **Not score-chasing:** the mechanism removes a repeated semantic pass visible
   in a real raw session.
1. **No overengineering:** one existing worker owns two existing artifacts; no
   new service, state field, flag, or runtime parser is presumed.
2. **No guesswork:** per-row matched receipts can falsify both latency and
   single-pass claims.
3. **No workaround:** eliminates duplicated authorship instead of hiding time
   in a different bucket.
4. **Worldclass / production-ready:** deterministic halts and raw-byte source
   integrity stay fail-closed.
5. **Best practice:** product PLAN remains on its certified Claude seat.
6. **Layer-cost-justified:** no additional model call; one semantic call is
   removed.
7. **Mission-bound:** this is a Mission 1 skill/reference refinement. Runner
   and transport ownership remain Mission 1.5.

<!-- devlyn:verification -->
## Verification

- R1 Codex, Fable 5, and Grok 4.5 converge on the registration.
- Before `status: FROZEN`, Terra executes the receipt-extraction shape against
  the surviving F12 A1 raw session and demonstrates that invoke/PLAN timestamps,
  ordered artifact writes, repeated-discovery sequence, and artifact hashes are
  mechanically recoverable. Assertion without execution does not freeze.
- Pre-change and treatment F12/F7 receipts satisfy the registered comparator.
- Existing skill lint and mirror parity pass using Sonnet/Terra test seats only.
- A formal fresh-context VERIFY reports zero CRITICAL/HIGH findings.

The fixed literal verifier checks diff integrity; BUILD_GATE runs the full skill
lint and mirror-parity suite directly so that suite is not duplicated under the
per-command verifier budget.

```json
{
  "verification_commands": [
    {
      "cmd": "git diff --check",
      "exit_code": 0
    }
  ],
  "max_deps_added": 0
}
```

Done means H1-v3 clears every mechanism, quality, halt, and matched-envelope
gate without touching the separately deferred M1.5 transport surface.

## FROZEN — 2026-07-29

R0 and R1 completed with actual Codex, Fable 5, and Grok 4.5. R0 removed the
unsupported resume shape. R1 converged on H1-v3, Sonnet PLAN for both task rows,
Terra-only mechanical testing, two unconditional matched pairs per row, receipt
attestation instead of a product transcript parser, immutable criteria on the
one allowed plan re-spawn, raw-goal fidelity as an explicit experiment gate,
and a pre-dispatch `risk_probes pending` announcement followed by one resolved
line.

Terra then executed the freeze-satisfiability canary against the surviving F12
A1 receipt and returned PASS with no unrecoverable field. It mechanically
recovered startup 190,581 ms, PLAN 236,743 ms, and startup+PLAN 427,324 ms; the
parent criteria write at `2026-07-22T16:35:34.001Z`; the PLAN-worker plan write
at `2026-07-22T16:39:25.142Z`; duplicated reads of `server/index.js`,
`tests/server.test.js`, `data/webhook-secret.txt`, and `package.json`; criteria
SHA-256 `b1b3024782452848858eac3ac6fa101f179411aa3718d542cbd6c53abbe869c2`
matching pipeline state; plan SHA-256
`4ff1fcb4ca2d83255c5bfd9ab21e1545801ec240958ecc1dcd1698a47c7ccad0`;
and the effective `claude-sonnet-5` model from the worker receipt.

The matched-run wording uses an identical benchmark-harness tree digest rather
than an identical repository commit. This is a post-R1 named precision delta,
**Treatment identity without runner conflation**: the runner copies product
skills from `REPO_ROOT` (`run-ceiling-arm.sh:365-375`), so equal commits would
erase the treatment. No new injection flag or dirty-runner exception is
authorized; exact attempt commits plus an equal harness digest preserve both
integrity and a real product delta.

## PRE-CHANGE CONTROLS — 2026-07-30

All four unconditional controls ran sequentially from detached baseline
`c596aa3f4f60824db99c74e734aa3bf9b323085b` with the iter-0078 cohort seats:
Claude Code 2.1.215 requesting Sonnet, Codex CLI 0.144.5 requesting Terra, and
Node 20.19.0. The registered acceptance envelope is `startup_ms + PLAN
duration_ms`; later IMPLEMENT/BUILD_GATE/VERIFY outcomes do not change receipt
completeness once both spans have closed.

| Pair | startup ms | PLAN ms | envelope ms | treatment must be | result receipt |
|---|---:|---:|---:|---:|---|
| F7/C1 | 239,944 | 116,316 | 356,260 | <= 302,821 ms | `iter0087-controls/F7/C1` |
| F7/C2 | 249,946 | 126,504 | 376,450 | <= 320,982 ms | `iter0087-controls/F7/C2` |
| F12/C1 | 367,705 | 159,552 | 527,257 | <= 448,168 ms | `iter0087-controls/F12/C1` |
| F12/C2 | 300,198 | 192,285 | 492,483 | <= 418,610 ms | `iter0087-controls/F12/C2` |

Receipts live under
`/Users/aipalm/.local/share/nx01/iter0087-controls`. F7/C2 completed the full
pipeline. F7/C1 exited after its post-metric tail; F12/C1 hit the 3,600-second
outer cap during a later VERIFY fix loop; F12/C2 ended `NEEDS_WORK` after a
complete 1,051,013 ms VERIFY. Every row nevertheless has a complete
decomposition and closed startup and PLAN spans. These tail outcomes are
retained as raw evidence and are neither latency draws nor authority for a
BUILD_GATE/transport change.

## IMPLEMENTATION ATTEMPTS — BLOCKED, 2026-07-30

No candidate product diff exists and no treatment row has run.

- Claude Sonnet could not start a worker because the host OAuth credential was
  expired; no product bytes changed.
- Terra run `rs-20260729T180746Z-7156e3fbdc7e` completed a fresh PLAN after one
  failed PLAN attempt, then blocked in IMPLEMENT when the worker interpreted
  "installed mirrors" as user-global paths. The partial product diff was
  rolled back. The candidate-surface section above now names only the two
  repository-local mirrors and forbids user-global paths.
- Terra retry `rs-20260729T182952Z-07ac4f7b38eb` bootstrapped on
  `gpt-5.6-terra`, but the monitored PLAN wrapper could not remain attached to
  its fresh child and the formal run ended
  `BLOCKED:fresh-context-unavailable`. IMPLEMENT, BUILD_GATE, CLEANUP, and
  VERIFY did not run; the worktree retained no product diff.

This is an infrastructure blocker, not evidence for or against H1-v3. The
registration remains FROZEN. Resume IMPLEMENT only through a permitted
Sonnet/Terra fresh-context route. Do not repair or bypass the foreground
transport here: that surface remains deferred to Mission 1.5.
