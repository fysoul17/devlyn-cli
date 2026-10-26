# Fix contract: 0260 code review round 2

Same hard limits as `results/build-contract.md`. Finding: `results/code-r2-astra.md` (one HIGH); Grok's
`code-r2-grok.md` is SHIP. DESIGN r3 (Apparatus, "A container that never starts is not an attempt") states the rule.
Change only `results/operator/judge.py` and `test_apparatus.py`.

**The HIGH:** `docker start -a` exits 1 when Docker fails to start the container, so a generic witness reads a
daemon failure as a reproduced defect, and stderr is dropped.

**Fix, in `docker_attempt`:** after `docker start -a` returns or times out, and before `docker rm -f`, read the
container's state with `docker inspect --format '{{json .State}}' <container>` (10 s limit).

1. Inspect fails, times out, or prints something that is not a JSON object with `StartedAt`, `Running` and `ExitCode`:
   raise `RuntimeError('<cell>: container state unreadable: ...')` after cleanup, recording nothing for this attempt.
2. `StartedAt` is Docker's zero time (it starts with `0001-01-01`): the container never started. Raise
   `RuntimeError('<cell>: container never started: <start stdout+stderr>')` after cleanup, recording nothing for this
   attempt (the same rule as a failed create).
3. Started and the start call timed out: return the timeout as now.
4. Started and finished: return a `CompletedProcess` whose `returncode` is `State.ExitCode` and whose stdout/stderr
   are the start call's. If `State.Running` is true, or the start call's exit code differs from `State.ExitCode`,
   the attempt is invalid: witness exit 2, probe `unassessable`, with both codes and the stderr in `error`.

Earlier completed attempts stay written (fix round 1's rule), and the cleanup and `cleanup_error` behavior is unchanged.

Tests, with a fake `subprocess.run`: (a) a generic witness whose start exits 1 with `StartedAt` zero raises, leaves
the attempt unrecorded, and keeps an earlier pass; (b) the same for the probe; (c) inspect failure and inspect
timeout raise and record nothing; (d) `Running` true or a code mismatch gives witness exit 2 / probe `unassessable`
with the diagnostic kept; (e) a normal started run uses `State.ExitCode`; (f) all existing tests still pass, updated
only where the fake now needs an inspect reply.

Done means: `python3 -m pytest -q -p no:cacheprovider autoresearch/experiments/0260` passes (report the output),
the 0259 and 0258 suites still pass when run separately, `py_compile` is clean, and your final message lists what
changed and the test output. Do not claim anything you did not run.
