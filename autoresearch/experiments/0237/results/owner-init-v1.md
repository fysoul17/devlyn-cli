# Prospective owner container init, version 1

2026-10-10. Research apparatus only; not a product instruction, model result,
historical regrade or authorization to dispatch. The observed failure is
documented in `f04-process-lifetime-audit.md`.

`../runner-init-v1.py` subclasses the frozen 0237 Runner, changes only its owner
module to `../cell-init-v1.py`, and adds both new source files to `seal.inputs`.
The inherited authentication, account check, task/model routing, source/delivery
checks, native identity, usage accounting and watchdog rules remain unchanged.
The historical runner, dispatcher, tasks and imported 0222/0232/0233 files were
not edited. The old dispatcher still invokes its original runner.

The existing owner implementation has no creation-argument injection point.
The new owner therefore retains its run function verbatim except for an
explicit `--init` in the Docker create argv. Identity, evidence parsing, Docker
primitive, tmp preservation and final-message extraction are imported from the
frozen implementation. The recorded `create_argv` is the actual argument list
passed to Docker, and `source_sha256` identifies the new owner source. No
argument is injected behind the recorded command. The PID limit remains 256,
memory 4g, CPUs 2 and the owner wait 5400 seconds. Init adoption/reaping is the
only intended execution change; cleanup and failure classification are inherited.

Use only with a separately registered immutable runtime, fresh output/cell
identities and common settings across every compared arm:

```sh
python3 -B autoresearch/experiments/0237/runner-init-v1.py run \
  /absolute/path/to/new-runtime.json <fresh-cell> <task> <A-or-B-or-C> <claude-or-codex>
```

`prepare` and the separately authorized `assess` retain the existing CLI shape.
This adapter does not reschedule old cells, alter old records, change native
background-wait settings or add an environment-dependent product exception.

## Offline validation

`owner-init-v1-prediction.json` was written before execution and binds exact
candidate/test bytes plus all 54 historical input hashes from the completed
confirmation seal. The prediction was four passing tests, covering five mocked
owner lifecycles. `test_runner_init_v1.py` passed 4/4 in 0.195 seconds, exit 0.
Every subprocess boundary was mocked; no Docker or native model ran. All 54
historical input hashes still matched afterward. Retained raw stdout, stderr,
command, timing and post-test comparisons are in `owner-init-v1-mock.*`.

The checks establish:

- The new run function's AST equals the frozen function after removing only
  the added `--init` argument, and delegated helpers are the original functions.
- Actual create arguments equal both saved argument records; existing process
  limits, native arguments, wait timeout and new source identity are preserved.
- Success, nonzero exit, hang timeout, surviving-container failure and native
  identity gaps retain their prior handling; credentials are removed and tmp
  preservation is delegated at the same boundary.
- The old input map is unchanged, both new files are additionally sealed, source
  drift changes that map, the actual selected task object reaches native identity
  validation, and the existing Runner methods are inherited unchanged.

These mocks do not prove real reaping, CLI compatibility or native usage under
init. An independently predicted no-model Docker calibration of actual creation,
orphan reaping and teardown remains required after the active frozen owner
finishes and root authorizes that calibration. No efficacy or cost improvement
is claimed by this preparation.

## Subsequent actual owner-boundary calibration

2026-10-10T10:17:25Z, after f05 completed and root authorized one bounded
model-free probe: `owner-init-v1-calibration-prediction.json` was registered
before invoking `owner-init-v1-calibration.py`. The driver constructs the new
Runner and calls its actual `frame.cell_run.run()` with a small Python workload,
new dummy credential placeholders and the same pinned image/caps. It does not
call authentication preflight, read/copy real credentials or launch inference.
The actual create/start/inspect/teardown/tmp-preservation path is exercised;
this is not a separately assembled Docker invocation.

Prediction confirmed, exit 0, owner 0.230152 s / host 0.918891 s:

- PID 1 is `/sbin/docker-init -- python3 -B /cell/probe.py`; actual caller PID 7
  has PPid 1. A double-fork descendant PID 9 records adoption by PID 1 before
  terminating, then its `/proc/9` entry disappears.
- Cgroup tasks return from 2 before to 2 after, with 3 recorded while the
  orphan is adopted. `pids.max=256`, `memory.max=4294967296` and
  `cpu.max="200000 100000"` confirm unchanged caps.
- Both recorded create argv arrays agree and include `--init`; the new owner
  source SHA is recorded. Input hashes remain unchanged, the per-cell dummy
  credential directory is removed and teardown is `CLEAN`.
- Native identity is `UNKNOWN`, as expected without a model. No MATCH/COMPLETE
  inference claim or product verdict was manufactured.

Raw host stdout/stderr and command/exit/timing are retained in
`owner-init-v1-calibration-1.{stdout,stderr,json}`. The exact runtime, plan,
before/after input maps, owner `run/started.json`, `run/result.json`, raw owner
streams and preserved child report are under
`/Users/aipalm/.local/share/nx01/0237-live/owner-init-v1-calibration-1/`.
The source probe itself is retained in `owner-init-v1-calibration.py`.

This closes the actual reaping/teardown calibration item above. Native
Claude/Codex inference compatibility, usage and task effects under init were
not tested by this probe. Historical results remain unchanged.
