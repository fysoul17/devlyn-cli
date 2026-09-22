# 0208 — recursive observation and contained termination controls

Research preparation only, root direct, no resolve or comparison draws.
The0204 candidate and0206 registration are unchanged. These controls are **not
a participant runner or execution seal**. Do not launch models through them.

`accounting.py` incrementally reads fresh, isolated Codex-shaped JSONL files.
It links native `source.subagent.thread_spawn.parent_thread_id` across generations,
counts `task_started` dispatches (including later turns in the same session), and
sums the latest cumulative counters per session. It checks each increment against
`last_token_usage`; unknown baselines or missing increments block observation.
Cached input/reasoning are reported as subsets, never added again. Exact duplicate
samples do not refresh liveness; changed last-usage vectors at the same total reject. Incomplete terminal records, observed file
replacement/truncation, lineage gaps, regression and stale active usage fail.
Errors remain latched; they cannot become a later successful snapshot.

`controls.py` connects that observer to real synthetic writers in an owned Linux
container on Docker Desktop. Each fixture also double-forks a TERM-ignoring
`setsid` child. Before emission, `/proc/<pid>/stat` proves its session identity
and reparenting to PID1. On input/output/call breach or silent usage, the test
kills the container, checks stopped state/PID0 and rejected execution into that
same stopped container, then removes it by ID. Child death is inferred from Linux
[PID-namespace teardown](https://man7.org/linux/man-pages/man7/pid_namespaces.7.html),
not observed by an executed post-kill command. Private PID namespace, no restart, no network,
no extra mounts, dropped capabilities and no privilege escalation are asserted
or fixed in the invocation. No host `ps` absence is used as proof.

The literal `model_calls: 0` is a fixture invariant (no inference commands,
credentials or network), not measured native call telemetry. The wall starts at
`docker start`; image inspection and stopped-container creation precede dispatch.

Prediction: three recursive budget breaches and silent active telemetry cause
termination; each detached fixture is gone before the10s wall ends. Three seconds
of that wall are reserved for kill and stopped-state checks. The1.5s staleness
threshold is a **synthetic test setting**, not a calibrated inference timeout.

```sh
python3 -B -m unittest discover -s autoresearch/experiments/0208 -p 'test_*.py' -v
docker image inspect oven/bun:1.3.14 --format '{{.Id}}'
python3 -B autoresearch/experiments/0208/controls.py \
  --image <inspected-local-sha256-ID> --scratch <owned-scratch> \
  --output <new-results.jsonl>
```

No pull occurs. The measured image was
`sha256:b4e28676860761b02257849f827ecee18611343a0541b1bf45007dc59be0bcfb`.
The four controls retain source hashes, native Docker state, process witnesses,
snapshots and synthetic logs. Failed attempts remain evidence, not retries of
participant cells. Results and review: [0208 milestone](../../iterations/0208-recursive-admission.md).

## Remaining admission boundary

- This observes dispatch **after** a log event. It cannot reserve the fifth
  descendant slot before native dispatch or detect a never-logged failed call.
  Shell-launched engines without native lineage are rejected, not guessed.
- A polling batch may contain several usage events; tokens emitted after its
  snapshot are not covered by its observed overshoot. No one-event overshoot
  guarantee or final charged usage is claimed for an interrupted native call.
- Historical counter consistency is not proof of parent-exclusive billing for
  every native fork/resume/provider route. Copied history and unknown baselines
  reject. Newly billed inherited context must not be subtracted merely because
  its text was already seen by the parent.
- Stale detection bounds observer tolerance, not provider reporting latency.
  Native long reasoning, Fable streaming/terminal reconciliation, failed-call
  totals and authenticated pre-dispatch lineage still require a native binding.
- Files must be supplied from trusted isolated telemetry custody. The observer
  does not enforce custody or detect arbitrary in-place rewrites between polls.
- These fixtures use Linux processes, not macOS participant CLIs. Linux native
  tool/model/capability parity and dependency/configuration identities remain
  unsealed. Docker daemon failure can defeat a deadline; a failed check is FAIL,
  never an inferred clean process tree. Recovery attempts do not repair that verdict.

Collection remains **BLOCKED_NATIVE_ACCOUNTING_AND_PARITY**. No new scheduler,
product transport changes, benchmark spending or adoption follows from these
diagnostic passes. Complete the native binding and0206 seal before any draw;
do not silently weaken the registration or substitute synthetic telemetry.
