# Two prospective native-foreground transport smokes

Draft only, 2026-10-10. No native or Docker call has run. Runtime, package/arm,
cell names, order and output destinations remain unselected until root review
and registration. These fixtures do not touch `../fixtures/CFG-LIFE`.

`../tasks-foreground-smoke-draft.json` copies the exact existing 0237 max routes,
assessor definitions and watchdogs, replacing only its task list. Dispatch is
proposed for Claude only: `claude-opus-5-5` / `max`, with one same-model native
child inheriting that route. Inherited Codex/reviewer definitions do not authorize
invocation. No independent CLI peer or new model is requested.

| Task | Child commands, each a separate native Bash call | Purpose |
| --- | --- | --- |
| FG-SHORT | `python3 -B /cell/work/child_gate.py 1`, waiting 1 second | Short foreground launch, return and delivery |
| FG-LONG | `python3 -B /cell/work/child_gate.py 1`, then `python3 -B /cell/work/child_gate.py 2`, each waiting 305 seconds | Foreground child lifetime above 600 seconds using two individually supported tool durations |

Both use Bash `timeout: 360000` and `run_in_background: false`. Each part prints
start and terminal JSON without writing files. The long calls must be sequential
and distinct, not combined into a single shell command. The child returns
`{"parts": [...]}` with their exact terminal payloads in order.

The `visible/` trees contain only README, scenario JSON, gate and receipt checker.
Their hashes and literal requests are bound by `manifest-draft.json`. Only
`receipt.json` may change. Tasks use existing `source_dir`, `oracle_commands: []`
and public-check routes; no new runner/evaluator adapter is needed. The local
commit endpoint uses the unchanged 0237 runner/prompt. Select
`0237/runner-init-v1.py`, pinned image
`sha256:0f472bb41685b7daa5923d51d31983f4b3c70053dd773fdf712bd0dcd6d87998`, and
unchanged caps, 5400-second owner watchdog, authentication/account checks and
native accounting. Root must freeze a new runtime and fresh outputs; do not
repurpose the closed confirmation runtime.

## What this calibration can establish

The literal request forces Agent `run_in_background: false`, one read-only child
and owner consumption of the terminal result before writing/checking/committing
its receipt and ending. Flag omission does not satisfy that launch condition.
This is transport calibration, not spontaneous compliance, instruction efficacy,
useful review or an engineering-quality benchmark. Prescribed waits are test
stimulus and cannot count as instruction-efficiency results.

The per-Bash timeout and noninteractive post-final background ceiling are
separate. `native-api-static-audit.md` records the 2.1.296 static schema/defaults
and official documentation. Both 305-second commands fit within the ordinary
600000ms Bash limit; their 360000ms requested timeout provides 55 seconds of
headroom each. No ceiling or environment value changes. A command failure is a
concrete tool/setup result, not by itself foreground Agent lifetime failure.
Native auto-backgrounding or API behavior must be reported if observed rather
than silently repaired. No fabricated wait interface or favorable retry.

## Evidence to retain and inspect

Register final inputs/order before native calls. Save existing runner plan/seals,
actual create argv, whole stdout/stderr, owner and child transcripts, tool results,
native final result and usage, evaluated snapshot, checks and delivery binding.
The trace must establish this sequence rather than an owner's claim:

1. Actual Agent arguments contain `run_in_background: false`; native statistics
   confirm foreground execution, not background substitution.
2. Every registered part runs exactly once using its own foreground Bash call
   with timeout360000. Native result timestamps establish part1 terminal before
   part2 launch. FG-LONG has two successful terminal payloads, each elapsed>=305s,
   and child lifetime>600s; retain actual command durations as well as payloads.
3. The child's final answer contains the exact ordered terminal payloads, after
   both long commands complete. It reaches the owner before receipt creation,
   public verification, local commit and parent final response. Progress or
   incomplete/cancelled output is not terminal completion.
4. No post-final background-ceiling/system kill substitutes for completion.
   Native statistics and stderr agree with the transcript.
5. Public checker passes, only the allowed receipt changes, and a post-baseline
   local commit matches the evaluated snapshot under existing delivery checks.
6. Actual owner/child model and effort match the registered route. Missing
   identity stays unverified. Whole usage includes both agents and all failed
   work; unknown usage never becomes zero. Input includes cache categories, and
   native aggregate accounting is distinguished from a provider billing record.

A raw product CHECKS_PASS without this lifecycle sequence is not a transport
pass. Report product/delivery and transport separately, preserving raw verdicts.
No candidate admission or broader claim follows. Finished f02 supplies negative
background-lifetime evidence; no additional background-failure run is proposed.

## Local validation provenance

`prediction-draft.json` was written before revised checker controls. The raw
outcome goes to `local-validation.json`. These checks compile supplied files and
exercise saved synthetic payloads only, never gates or native waiting. The
superseded unregistered single-command draft, its prediction and its eight local
checker controls are retained verbatim under `superseded-single-command-draft/`.
That earlier 610-second Bash request was replaced before any native invocation;
its output is not evidence for these revised fixtures.

Revised local results: four source files compiled, and all 11 predicted receipt
controls matched (eight shared controls plus missing, duplicate and reversed
long-part controls). Literal goal/task requests and every source hash match.
Non-task routes, assessors and watchdogs remain equal to the 0237 source task
table. No gate, native CLI or Docker invocation occurred. Raw inputs, commands,
stdout, stderr and exits are retained in `local-validation.json`.

Root's proposed registration is `s01-claude-b-short` then `s02-claude-b-long`,
both phase `smoke`, unchanged B archive prefix `8c4dcdfa`, using
`0237/runner-init-v1.py`. This proposal is not dispatch authorization; final
runtime, exact archive hash and cell plan must be frozen by root.
