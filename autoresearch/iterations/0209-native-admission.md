# 0209 — native admission boundary, reproduced

2026-09-22 KST. Root direct, no resolve. PR90 is merged as3719265.
**Comparison NOT_RUN; admission remains BLOCKED_NATIVE_ACCOUNTING_AND_PARITY.**
This continuation tests proposed native bindings rather than repeating0208's
synthetic accounting tests. It does not change0204,0206, product code or defaults.

## Installed-binary evidence

Prediction before execution: Codex's native shared budget stops excess output,
but its cache/override semantics differ from0206; valid hook denials stop a
dispatch, while malformed output and ordinary hook failure do not.

The installed Codex0.155.1 connects to a credential-free loopback Responses
fixture. These are actual CLI/tool/hook executions with synthetic server usage,
not real inference, participant draws or evidence of the production provider's
payload. Ten controls reproduce the expected behavior under optimized Python:

| Control (native weighted limit100) | Observed result |
| --- | --- |
| Input10, output10 | completed; terminal usage matches |
| Input10, output101 | exit1; `shared rollout token budget exhausted` |
| Input1000, all cached, output1 | completed; terminal usage still reports input1000 |
| Input1000, output101, provider budget units0 | completed; raw token totals are not the enforced metric |
| Wildcard PreToolUse, valid JSON deny | hook ran; no child;2 owner requests |
| Wildcard PreToolUse, exit2 with reason | hook ran; no child;2 owner requests |
| Wildcard PreToolUse, malformed JSON | hook ran; child created;2–3 requests |
| Wildcard PreToolUse, exit1 | hook ran; child created;2–3 requests |
| Wildcard PreToolUse, deny nested shell | Bash hook ran; no child;2 requests |
| `spawn_agent\|Agent` matcher, valid deny | startup hook ran; pre-tool hook did not; child created;2–3 requests |

The wildcard spawn hook receives `tool_name: collaborationspawn_agent` on this
namespaced V2 route. The named-matcher witness is route/version-specific, not a
claim that all native subagent hooks fail. Startup-hook witnesses, hook inputs,
unique session metadata and raw requests distinguish a configured denial from
missing dispatch or a silently skipped hook. Child counts exclude the owner and
deduplicate copied session metadata.

Official tag `rust-v0.155.1`, `codex-rs/core/src/rollout_budget.rs:48–67` uses
provider budget units when supplied, otherwise weighted output plus non-cached
input. `core/src/session/rollout_budget.rs:29–41` raises a budget error.
`hooks/src/events/pre_tool_use.rs:199–280` starts with `should_block=false` and
distinguishes explicit denial from failed hook execution. The captured config
schema defines a concurrent-thread limit, not a lifetime-dispatch budget.
These counterexamples reject direct equivalence to0206's separate cache-inclusive
input/output totals, recursive session count and external Fable accounting.

The first attempt rejected missing `reminder_at_remaining_tokens` before any
request. It is retained, not counted as a passing control. The first hook attempt
also used the named matcher and inherited ancestor project context; the final
fixture initializes its own Git root and uses a wildcard plus separate named
control. Those preparation failures cannot qualify a participant environment.
A later control correctly failed its overly strict three-request expectation:
the owner can finish after successful spawn and cancel the child before its
first provider request. Final validation instead requires both unique child
metadata and a successful native spawn result, allowing2–3 requests. The failed
attempt remains evidence; no participant outcome was regraded. Fable independently
identified the same request race and a shell oracle that only checked hook
invocation. Final controls inspect the native tool-result denial. Deliberately
replacing the shell-deny hook with a no-op makes that control FAIL under `-O`.

## Review and disposition

Actual Fable5.1 and Grok4.7 design reviews returned in69.653/56.598s, with matching
native identities, one turn each and no tool calls. Both identify the metric and
cross-engine gaps. Fable suggests adding external observation without changing
0206; root retains that as an unproved candidate, not an admission certificate.
Its claim of a fully bindable OUTPUT cap is conditional on the provider override
and whole-tree termination, neither established by the supplied source.

Real Fable review usage exposes ordinary input, cache-read, cache-write, output
and thinking counters. A terminal result does not establish bounded delivery,
failed/interrupted-call totals or an enforcement connection to Codex. Preparation
reviews remain outside participant budgets and do not substitute for a comparison.

**No workaround:** do not silently replace0206's totals with the native weighted
metric, move Fable outside the cell, disable A's native children, or call a hook
watchdog a pre-dispatch guarantee. **No overengineering:** no engine patch,
proxy or scheduler is added to rescue an unsealed benchmark. The current native
settings/hooks are not sufficient evidence to launch unchanged0206. An external
binding remains possible, but must demonstrate protected cross-engine usage,
fail-closed dispatch and contained Linux capabilities; this report does not claim
that such a binding is universally impossible.0201 adoption/migration/confirmation
remain open. Model availability is confirmed; execution admission is the blocker.

Final Fable and Grok closure reviews both **ACCEPT** the corrected diagnostic
source/report. Three preparation calls per reviewer completed with native identity
checks. Root verified the final source hash,10 controls and the no-op negative
control. Removing the Git-root isolation or tool-result witnesses would restore
the demonstrated context/oracle defects; no product abstraction was added.

## Reproduction and custody

`autoresearch/experiments/0209/native_probe.py` requires an installed Codex binary,
Python3 and Git. It calls no real model endpoint and supplies no credentials.

```sh
python3 -O -B autoresearch/experiments/0209/native_probe.py \
  --scratch <owned-scratch> --output <absent-evidence-directory>
```

Evidence: `.devlyn/0209/native-final-r2/` (config, raw requests/outputs, native
identity, source hash and verdict); earlier attempts and source-bound Fable/Grok
packets remain in `.devlyn/0209/`. Official source tree and relevant tag files are
retained there. A passing diagnostic verdict explicitly sets
`comparison_admitted:false`; it is not a launch seal.

0208 cleanup was retried with its existing receipt and again refused because
Docker VM27213 retains task-file handles. Other live containers share that VM;
it was not killed. Receipt `a991fe829b78fb1ddc8db6e8`, branch and recovery evidence
remain in `../core-continuation-20260912/.git/devlyn-completion/`. This continuation
uses a separately allocated linked checkout; original three-file WIP is preserved.
