# Finished f04: unreaped orphans and process-slot exhaustion

2026-10-10. Read-only audit of frozen apparatus and the completed
`f04-CF-CONFIG-claude-B-r1` native evidence. No new experiment, model call,
container probe, product/input change or regrading was performed. Active f05
was not inspected. The dispatcher is held separately as recorded in
`confirmation-environment-hold.json`; f05 continues under its unchanged inputs.

**Finding:** f04 actually ran with the Claude CLI as PID 1, without an init
reaper in front of it. Its native tool results record 242 orphan zombies and
251–253 occupied task slots against a limit of 256, persisting until shortly
before exit. The owner performed concrete environment diagnosis and recovery
work. This establishes an environment contribution; it does not establish the
fraction of total time or tokens caused by it.

**Outcome boundary:** preserve the raw `PRODUCT_INCOMPLETE`, public 23 PASS,
11 hidden PASS / `recursive-merge-value-kinds` FAIL, matching local delivery,
COMPLETE usage, 3276.343909959003 owner seconds, 44,253,577 processed input
tokens and 400,250 output tokens. The sole hidden failure is separately under
contract-provenance review: the oracle mutates `merge()`'s returned value and
then requires its inputs to remain detached, while the visible text promises
non-mutation during merging and detachment for Loader/manager results. Do not
describe that assertion as a validated product defect until that review is
resolved. The oracle itself completed normally; the native fork failures below
are not evidence that its execution failed. See `f04-source-audit.md` for the
separate source/oracle audit. No raw outcome is relabeled here.

## Frozen apparatus and actual process identity

All source paths below are relative to `autoresearch/experiments/`.

- `0237/runner.py:41–65` loads `0233/run_cell.py`, which loads its `cell.py`.
  `0237/runner.py:98–108` seals the imported 0222/0232/0233 Python sources;
  confirmation runtime and those source hashes match the retained freeze and
  completed-cell seals. The owner container creator is
  `0233/cell.py`, SHA-256
  `06c2258058acb4c69371b0a7ad342e1c57939bbe562fa97143a8530cc4247a4b`.
- `0233/cell.py:145–159` creates the container with `--pids-limit 256`,
  `--memory 4g`, `--cpus 2`, a read-only root, private writable cell/home/tmp
  and no `--init` or reaper wrapper. It records the exact creation argv.
  f04's `run/started.json` and `run/result.json` retain that configuration.
- `0233/prepare.py:133–144` selects direct native Claude `-p` execution with
  `--permission-mode bypassPermissions`; `0237/runner.py:130–136` adds isolated
  MCP settings. The apparatus does not wrap each native Bash command with a
  child subreaper. Codex's separate registered native shell/config policy is in
  `0222/prepare.py:59–66`; it does not change this Claude observation.
- `0233/cell.py:163–186` waits on the native owner under the existing watchdog,
  then removes the stopped container and preserves its tmp volume. f04 reports
  `EXITED_0`, `CLEAN` teardown and empty native stderr. The recorded argv alone
  would leave daemon-default init or inherited entrypoint uncertainty; f04's
  actual `/proc/1` output below closes that uncertainty for this cell.

The pinned image is
`sha256:0f472bb41685b7daa5923d51d31983f4b3c70053dd773fdf712bd0dcd6d87998`.
Its provenance is `0237/image.json`; neither the new image Dockerfile nor the
retained 0231 base Dockerfile adds a reaper entrypoint.

## Retained native observations

Raw cell root:
`/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/f04-CF-CONFIG-claude-B-r1/`.

Root transcript, abbreviated **R** below:
`home/.claude/projects/-cell-work/f6b8aac4-820c-441a-8d4d-a829c469cc2d.jsonl`.

Child transcript, abbreviated **C** below:
`home/.claude/projects/-cell-work/f6b8aac4-820c-441a-8d4d-a829c469cc2d/subagents/agent-aa95b267778af4fc5.jsonl`.

These are public tool arguments/results and visible messages, not an inference
from hidden reasoning.

| Evidence | Observed result |
| --- | --- |
| R:258–259, 08:26:02–08:26:22 UTC | Owner-selected pre-flight command runs the installed `task-complete.py --self-test`. Its output reports 71 tests, 26 failures, Git fork/resource errors, and shell wall time 20.063 s. |
| R:261–262, 08:26:29 | `ulimit -u` is unlimited; cgroup `pids.max=256`, `pids.current=252`; process enumeration reports 247. |
| R:264–265, 08:26:34 | `ps` groups 238 `git Zs` and 4 `sh Z`; the retained tail shows defunct Git/shell processes with PPID 1. |
| R:267–268, 08:27:20 | `/proc/1/comm` is `claude`, PPid 0, Threads 9; cgroup tasks are 253. |
| R:287–288, 08:29:22 | The owner's single-process `/proc`/cgroup reader reports `tasks 253/256 free=3 zombies=242`. |
| C:58, 08:30:30 | Reviewer's baseline find/checksum pipeline reports `Resource temporarily unavailable` and Bash fork retries. Its later report C:73 explicitly treats that before-snapshot as unverified. |
| R:406–407, 08:35:55 | Live-process enumeration confirms PID 1 is the actual Claude command with 9 threads; the only other listed live process is the diagnostic Python command. |
| R:645–646, 08:49:38 | Before the final response, 242 zombies remain and cgroup tasks are 252/256. Git config is unchanged, the task worktree is removed and no stray checkout caches/pipeline state are reported. |

The exact self-test invocation at R:258 is:

```sh
cd /tmp && time python3 -B /cell/work/.claude/skills/_shared/task-complete.py --self-test 2>&1 | tail -8; echo "exit=${PIPESTATUS[0]}"; git -C /cell/work status --short; sha256sum /cell/work/.git/config
```

No pre-self-test PID census was found in this bounded audit. The temporal
sequence and retained defunct-process ages strongly connect the heavy Git
fixture run to the exhaustion, but do not prove that every one of the 242
zombies originated in that command. The observations distinguish persistent
unreaped orphans from a large population of still-running model workers.

## Observed recovery work and cost limits

The owner wrote scratch `reap.py`, `slots.py`, `procs.py` and `state.py` under
`/tmp/beacon-delivery/`. The reaper sets `PR_SET_CHILD_SUBREAPER`, runs a command
and waits for adopted children. Five retained wrapper results each report
`orphans_reaped=1`: R:328,340,344 are scratch commit/merge controls; R:588,622
are the eventual product commit and fast-forward merge. These newly adopted
children were reaped; the already orphaned PID-1 zombies stayed at 242.
R:279 warns the child about the observed slot shortage. Subsequent commands
avoid pipelines or use `exec` and in-process Python. These are concrete extra
actions attributable to the observed environment problem, not a calculated
token or wall-time counterfactual.

The first retained fork-error result at 08:26:22.574 is 1826.047 seconds after
the recorded container-creation start; the root's final public response at
08:50:32.416 is another 1449.842 seconds later. Work after the error includes
ordinary review, repair and delivery as well as recovery. Neither interval is
an estimate of environment-only cost. Do not subtract them, estimate tokens
from command counts, or attribute the entire 54.6-minute run/44.3M processed
input to the missing reaper. Processed input includes cached input and is not
a billed-money figure.

## Comparison with the already retained offline control

`cleanup-zombie-proposal.md:71–77`,
`cleanup-zombie-proposal-evidence/manifest.json:39–52`, and the prospective
`full-suite-retry-prediction.json` preserve the earlier same-image comparison:

- No init, Python PID 1, PID limit 128: 71 tests in 13.171 s, 21 successful
  before resource failure and 50 Git fixture setup failures.
- Same source, image, tests and PID limit, with Docker `--init`: 71/71 pass
  in 54.380 s (`v3-full-linux-init.stderr`).

The earlier removed container's final PID inventory was not saved, so its
orphan-accumulation explanation remains the inference originally recorded.
f04 now supplies direct PID-1, zombie and cgroup evidence for the measured
container. The workloads and PID limits differ; the prior control does not
quantify f04's counterfactual cost or validate its disputed source assertion.

The frozen comparison is unchanged. Any later apparatus correction must be
separately identified and common across compared arms; an environment fix must
not receive causal credit as an instruction or pair-reasoning improvement.
