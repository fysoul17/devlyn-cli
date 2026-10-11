# Two prospective native-foreground transport smokes

Draft only, 2026-10-10. No native or Docker call has run. Runtime, package/arm,
cell names, order and output destinations remain unselected until root review
and registration. These fixtures do not touch `../fixtures/CFG-LIFE`.

`../tasks-foreground-smoke-draft.json` copies the exact existing 0237 max routes,
assessor definitions and watchdogs, and replaces only its task list. Dispatch
is proposed for Claude only: `claude-opus-5-5` / `max`, with one same-model native
child inheriting that route. The inherited Codex/reviewer definitions do not
authorize their invocation. No independent CLI peer or new model is requested.

| Task | Child command | Purpose |
| --- | --- | --- |
| FG-SHORT | `python3 -B /cell/work/child_gate.py`, configured for 1 second | Short native foreground launch, return and owner delivery |
| FG-LONG | The same command, configured for 610 seconds | Child tool work extending beyond 600 seconds while its owner awaits the foreground Agent |

The two `visible/` trees contain only README, scenario JSON, read-only gate and
receipt checker. Their exact hashes and literal caller requests are bound by
`manifest-draft.json`. Only `receipt.json` may change. The task table uses the
existing `source_dir` route, `oracle_commands: []` and public checker; no new
runner or evaluator adapter is needed. The common local-commit endpoint comes
from the unchanged 0237 runner/prompt. Use the new
`0237/runner-init-v1.py`, pinned image
`sha256:0f472bb41685b7daa5923d51d31983f4b3c70053dd773fdf712bd0dcd6d87998`, and
unchanged caps, 5400-second owner watchdog, authentication/account checks and
native accounting. Root must create a new immutable runtime and fresh outputs;
do not repurpose the closed confirmation runtime.

## Deliberately forced behavior and timeout distinction

Each literal task explicitly requires a native Agent call with
`run_in_background: false`, exactly one read-only child, then owner consumption
of the actual terminal result before writing/checking/committing the receipt
and ending. Omission of the Agent flag is not a foreground launch. This is
transport calibration, not spontaneous compliance, instruction efficacy, useful
review or an engineering-quality benchmark. The prescribed 610-second wait is
test stimulus; its cost must not be counted as an instruction-efficiency result.

The gate emits a start JSON, waits and emits terminal JSON; it writes no files.
The public checker only validates the saved terminal payload and runs quickly.
A valid receipt by itself proves neither waiting nor child completion.

**Registration prerequisite:** the draft asks the child's Bash tool for
`timeout: 660000` and `run_in_background: false`. Its command timeout is distinct
from the `claude -p` post-final-turn background wait ceiling. The retained f04
request for 900000 ran for only 20 seconds and does not establish the native
tool's actual maximum. Before interpreting FG-LONG, verify the pinned native
tool can sustain the requested command duration. A rejected/clamped timeout or
early command termination is a named transport/setup limitation, not evidence
that Agent foreground fixes or fails the print ceiling. Preserve that attempt;
do not change native ceiling/environment values, shorten the registered gate,
invent an unavailable wait tool or retry under the same cell identity.

## Evidence to retain and inspect

The prospective prediction is in `prediction-draft.json`. Register the final
inputs/order before native calls. Save the existing runner's plan/input seals,
actual container argv, whole run stdout/stderr, native owner and child
transcripts, child tool output, native terminal result and usage, snapshot,
public checks, delivery binding and local commit.

The native trace must establish this sequence, not merely an owner's claim:

1. Agent input explicitly contains `run_in_background: false`; native execution
   statistics identify foreground launch rather than background substitution.
2. The child actually runs the unchanged gate once. Its native command result
   is successful; FG-LONG's terminal payload and native timing span at least
   610 seconds. Any asynchronous inner tool behavior must remain explicit.
3. The child's terminal answer contains the gate's exact completion payload.
   That result reaches the owner before the receipt write, verification, commit
   and final response. An intermediate progress notification is not terminal.
4. No background-ceiling/system kill substitutes for completion. The native
   final child statistics and stderr must agree with the retained transcript.
5. The saved receipt passes the unchanged public checker, permitted source
   scope holds, and the attributable post-baseline commit matches the evaluated
   snapshot under the existing local-delivery checker.
6. Actual owner and child model/effort match the registered route; missing
   identity remains unverified. Whole native usage includes both, any failed
   work and recovery. No fabricated counters or zero-cost missing child usage.

A raw product CHECKS_PASS without the lifecycle evidence is not a transport
pass. Report product/delivery and transport separately; never rewrite a raw
verdict to conflate them. No candidate admission or broader claim follows from
either smoke. Finished f02 remains the negative background-lifetime evidence;
no additional background-failure experiment is proposed.

## Local fixture validation only

After the draft prediction, both supplied Python files compiled in each tree.
Eight quick receipt-check controls passed: missing, wrong marker and too-short
payloads fail; a synthetic valid payload passes for each task. Full commands,
stdout, stderr and exits are retained in `local-validation.json`; source hashes
remained unchanged. Neither gate was executed, and no local or native 610-second
wait, child launch, Docker invocation or model call occurred. These controls
validate the receipt checker only.
