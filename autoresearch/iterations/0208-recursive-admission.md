# 0208 — recursive accounting and contained termination

2026-09-22 KST. Root direct from56e4331/PR88, no resolve. Research-only
[source and reproduction](../experiments/0208/README.md); no model comparison,
assessment or confirmation was launched.0204 candidate/0206 registration hashes
are unchanged. Evidence: `.devlyn/0208/` in the retained continuation checkout.

## Verified progress

An incremental observer now aggregates fresh native-shaped owner/child/grandchild
counters without summing repeated cumulative samples, cache or reasoning twice.
It rejects unknown baselines, missing lineage, regression, incomplete terminals,
invalid dispatch IDs, stale telemetry and observed file replacement/truncation.
Redispatch consumes another session slot; provider requests within one dispatched
session are not extra slots under0206's explicit definition.

Prediction before controls: input/output/session-dispatch overages and silent
active telemetry trigger teardown; a real detached, reparented, TERM-ignoring
child cannot outlive its private Linux PID namespace. Four controls pass under
`python3 -O -B` in0.853/0.868/1.167/1.862s, each including Docker start, observation,
kill and stopped-state evidence within10s (3s reserved inside the wall).
This is kernel-containment inference from the observed namespace teardown, not
direct host-PID death evidence or macOS CLI containment. Raw: `controls-final.jsonl`.

Final accounting suite:21 tests PASS. Historical replay of the three0205 owner
rollouts matches every supplied exec terminal usage component; replay program,
rollout hashes and final accounting hash are retained in `replay-history.py` and
`history-final.json`. Separately,66 existing child records have1,203 increasing
updates and18 unchanged cumulative samples; every increasing cumulative difference
matches the native last-usage vector. Of the18 repeats,15 repeat the last vector
and3 change it (two sessions). Those3 are now unsupported and reject instead of
being assumed harmless duplicates. Raw: `native-duplicates.json`. This is not proof that every
provider/fork/resume route has exclusive billing or complete dispatch telemetry.

Preparation failures are retained: r0/r1 fixture launch timed out because Bun's
`posix_spawn` of the shell returned EACCES in the local image. The fixture now
uses the existing shell to detach the child and exec Bun only as the writer;
this does not certify Bun subprocess capability or Linux participant parity.
The temporary probe containers are removed; no generic product helper changed.

## Independent review and repaired witnesses

Actual Fable5.1 and Grok4.7 design reviews completed. Their useful challenges
include dispatch-before-telemetry gaps, copied baselines, protected log custody
and Linux/macOS parity. Root did not adopt suggestions to subtract newly billed
inherited context or to infer lineage where native records lack it. Native child
metadata does expose `source.subagent.thread_spawn.parent_thread_id`; shell
launches remain outside that demonstrated lineage.

Fable source review found a false PASS with optimized Python and a false terminal
completion with an empty turn ID. Both were reproduced before repair. Explicit
checks replace `assert`; the same deliberately disabled-meter control now returns
FAIL/WALL_RESERVE under `-O`. Empty/falsy IDs reject. Additional failing witnesses
for metadata-only silence and non-integer last usage were repaired. The expanded
suite fails6 subcases before repair and passes19 tests after it. Review wording
that equated a dispatch with every provider request was rejected using0206's
quoted session definition; it does not justify silently changing that budget.

Grok source review challenged duplicate semantics, log integrity and containment
claims. Exact repeated native samples remain deduplicated; changed last vectors
now reject. Same-inode rewriting stays outside trusted-log custody, explicitly
unproved. Container security settings are now checked, and removal uses the
created container ID. Fable closure also exposed weak control oracles: expected
totals/dispatches and complete emitted fixture records are now independently
checked, plus minimum silence duration. Deliberately premature breach/silence
meters both produce FAIL (`early-negative.json`). No unexecuted in-container
post-kill command is described as observing a dead child. Fable final review
accepted the scoped code with one LOW: an empty child rollout escaped terminal
validation. Root reproduced it (1/21 failing), added the missing file-session
check and reran21/21 plus all four controls on the final source.

Final Fable and Grok dispositions are **scoped ACCEPT**; Fable additionally
confirmed the final one-line empty-rollout repair. All5 Fable5.1 and3 Grok4.7
preparation reviews returned terminal results with matching native identities,
no tool calls and no timeout. These are static source/advice reviews, not
independent execution or a native launch certificate. Source-bound packets and
raw streams remain under `.devlyn/0208/`. Root accepts diagnostic controls only.

## Stop boundary

**BLOCKED_NATIVE_ACCOUNTING_AND_PARITY.** These tests improve the evidence beyond
0207's known-broken group-only wrapper, but do not admit the comparison. The
observer acts after dispatch and per polling batch; never-logged calls, final
usage during interruption, bounded provider delivery, Fable counters and protected
telemetry need native binding. Docker fixtures alone do not establish Linux
Codex/Fable capability parity. The full0206 execution seal remains required.
No event-exact token cap, whole-project billing or adoption claim is made.

Next is that native binding and parity check, not another round of task selection,
evaluator calibration or a new scheduler.0201 confirmation, migration, adoption,
Mission1 and gate15 remain OPEN. **No workaround/Production ready** retain the
blocked gate; **No guesswork** retains both false-PASS witnesses and raw failures;
**No overengineering** confines the change to research controls. Removing the
native-limit paragraph would erase the distinction these controls actually test.
