# 0013 — F1 timeout discriminator (config too tight, no real bug)

**Status**: SHIPPED
**Started**: 2026-04-27
**Decided**: 2026-04-27 (same-day, single discriminator run)

## Hypothesis (and revision)

HANDOFF originally framed iter-0013 as: "F1 reproducibly hits 480s cap with empty transcript even when no codex involvement … auto-resolve pipeline doesn't naturally exit cleanly after Stop on trivial fixtures." That framing didn't survive contact with the evidence.

Reframed hypothesis (with Codex CLI cross-check): the F1 variant pipeline (PARSE + BUILD + BUILD GATE + EVAL on the `fast` route) has irreducible overhead near the 480s budget. Most runs squeak under, some get cut off mid-EVAL. The "0-byte transcript" is `claude -p` output buffering interrupted by SIGTERM, not iter-0008 byte-watchdog starvation. Bumping the budget to 900s should let F1 complete cleanly with no mechanism change.

## Mechanism (evidence chain)

Why-chain (extending iter-0012 at #58):

59. Why is the original "doesn't exit cleanly after Stop" framing wrong? → On the prior failing run (iter0009-f1, elapsed=481, watchdog kill), the debug log showed SessionEnd hooks completing at status 0 between elapsed=480.4s and 480.7s, with watchdog SIGTERM at 480s. That's plausibly SIGTERM-induced cleanup (hooks running on shutdown), not proof of natural completion. Codex iter-0013 R0 caught my over-eager "0.6s away from natural exit" claim.
60. Why is "fast route incomplete on prior run" the right read? → The fast route requires PARSE→BUILD→BUILD GATE→EVAL→FINAL REPORT. Surviving artifacts in `/tmp/bench-*/.devlyn/` had `build_gate.findings.jsonl` + `build_gate.log.md` but **no `evaluate.*` and no archive**. The run was cut off at the EVAL boundary.
61. Why is the BUILD phase the dominant time sink? → Codex iter-0013 R0 inspected the debug log and found ONE Bash dispatch of 268.508s during BUILD (started 140s in, ended 409s in). On the new 900s run, the same dominant dispatch is 142.968s. Both are the BUILD Codex call (variance ~2x in xhigh API timing).
62. Why does bare arm complete in 43s vs variant 465s (10.8x)? → Variant runs the full auto-resolve pipeline with Codex for BUILD on `--engine auto`; bare invokes Claude directly with no skills loaded. The 10x overhead is the pipeline + Codex round-trip cost, not a bug.
63. Why isn't this a fix-the-pipeline iter? → The pipeline IS doing real work. State writes confirm route=`fast`, Stage A reasons=`spec.complexity=trivial, no risk keywords matched`. Verdict on the new 900s run: `PASS_WITH_ISSUES` (a single LOW finding, terminal on fast route). Mechanism is correct; budget is the only knob to turn.
64. Root: F1's 480s timeout was a benchmark-config artifact from when Codex BUILD was faster. Raise to 900s. State-writes-per-phase contract drift (observed: 1-2 writes total instead of per-phase) is a separate observability issue, queued.

## Predicted change

Static + 1-experiment falsification:

- **Discriminator run**: F1 variant with `metadata.timeout_seconds=900`, single iteration. Pass criteria: `invoke_exit=0`, `timed_out=false`, `transcript.txt` nonzero, `evaluate.*` artifacts present, terminal verdict in transcript.
- **No mechanism change** to skills, lint, or the wrapper.
- **No regression on bare arm** (bare doesn't read this fixture metadata field except for its own watchdog budget; it completes in 43s well under 900s).

## Diff plan

Single edit:

1. `benchmark/auto-resolve/fixtures/F1-cli-trivial-flag/metadata.json` — `timeout_seconds: 480` → `900`.

NOT in this diff:

- **State-writes-per-phase fix.** Codex iter-0013 R0 #2 flagged the contract (`pipeline-state.md:168`) calls for per-phase writes; the run did 1-2 bulk writes instead. Observability debt; doesn't affect verdicts. Queued as iter-NEXT candidate ("state-writes-per-phase observability fix").
- **`claude -p --output-format stream-json`.** Would make transcript flush incrementally and survive SIGTERM partial output. Not needed for now — a 900s budget means SIGTERM is the exception. Filed mentally; not yet a queue item.
- **Other fixture timeout audits.** F2/F4/F6/F9 may have similar drift but are not currently failing in this way; defer until they fail.

## Falsification gate result (2026-04-27)

Discriminator run **PASSED**.

```
RUN_ID=iter0013-discriminator-20260427T081727Z
elapsed_seconds: 465
timeout_seconds: 900
timed_out: false
invoke_exit: 0
invoke_failure: false
verify_score: 0.8
commands_passed: 4 / 5
files_changed: 2
diff_bytes: 3047
transcript.txt: 2304 bytes
```

`.devlyn/` artifacts on disk: `build_gate.{findings.jsonl, log.md}`, `evaluate.{findings.jsonl, log.md}`, `pipeline.state.json`. EVAL phase reached and completed (`verdict=PASS_WITH_ISSUES, completed_at=08:22:30Z`).

Stage A routing: `route.selected=fast`, reasons `[spec.complexity=trivial, no risk keywords matched]` — correct.

Final report verdict (from transcript): **PASS_WITH_ISSUES**, LOW-only finding, non-blocking on fast route. BUILD recorded as `Codex (gpt-5.5, xhigh), 142s, 60.8k tokens`.

## Codex collaboration (CLI, not MCP)

Per user direction: codex CLI / GPT-5.5 only.

R0 (pre-discriminator design review): I presented evidence + reframed hypotheses (H1 pipeline overhead, H2 transcript-buffer-on-SIGTERM, H3 PARSE-phase-suspicious) plus 4 questions. Codex verdict, applied:

1. **My reframe was right but slightly over-asserted.** SessionEnd hooks completing at status 0 ≠ proof of natural completion (could be SIGTERM cleanup). Corrected.
2. **F1 didn't complete fast route** — no `evaluate.*` artifacts; pipeline cut off mid-flow. (H1 stands; "completed cleanly except flush" reframe rejected.)
3. **Two state.json writes is observability drift, not a stall proof.** Per-phase writes are the contract; bulk writes obscure phase progress. Acknowledge as separate iter.
4. **One Bash dispatch took 268.5s** (Codex inspected debug log directly). That's the dominant time sink. Confirmed in 900s run as a 143s BUILD Codex call.
5. **Don't choose pure (d) "close as benchmark config"**: missing EVAL is enough residual risk that a 900s confirmation run is the cheap discriminator. Proceeded with the 900s run; outcome A confirmed.

## Lessons

- **HANDOFF framings can decay**. iter-0013 was queued with a framing ("doesn't exit cleanly after Stop") that didn't survive evidence inspection. Always re-read the raw artifacts, never trust prior framings without verification. Codex caught the over-assertion in my own reframe immediately after.
- **Discriminator > instrumentation when the experiment is cheap**. Codex pushed back on (b)/(c) "instrument PARSE/BUILD" in favor of running the 900s experiment first. The experiment cost ~$1-2 of API spend and 8 min wall time; instrumentation would have taken longer with no immediate result. Cheap discriminators first.
- **Observability drift can hide in plain sight.** State writes happening 1-2 times per run (instead of per-phase) didn't break verdicts but obscured this iter's diagnosis. File observability gaps as future iters even when they don't block the current verdict.
- **Trivial-fixture overhead is real**. Bare 43s vs variant 465s = 10.8x overhead from the auto-resolve pipeline + Codex BUILD call. That's a legit design cost, not a bug. F1's old 480s timeout was set when Codex was faster; trim or grow as the dominant cost shifts.
