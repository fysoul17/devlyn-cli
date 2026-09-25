---
name: devlyn:intent
description: Preview candidate for the full route, used only when the user explicitly invokes /devlyn:intent. One native owner takes a goal, goal file or spec through implementation, real checks and independent review/repair to a verified commit. `--plan-only` plans without implementing; `--verify-only` reviews an existing diff. Never auto-selected; /devlyn:resolve remains the default full route.
---

You own this task from intent to a verified commit. You plan, implement and run the checks in this context. Separate models run only as the selected executor and as independent reviewers, both through the gate below.

<pipeline_config>
$ARGUMENTS
</pipeline_config>

<runtime_paths>
Resolve shared scripts from this skill's installed directory, never from the project cwd:

```bash
DEVLYN_SKILL_DIR="${CLAUDE_SKILL_DIR:-__DEVLYN_SKILL_DIR__}"
if [ "$DEVLYN_SKILL_DIR" = "__DEVLYN_SKILL_DIR__" ] || [ ! -d "$DEVLYN_SKILL_DIR/../_shared" ]; then
  echo "BLOCKED:shared-dir-unresolved: $DEVLYN_SKILL_DIR/../_shared" >&2
  exit 1
fi
DEVLYN_SHARED_DIR="$(cd "$DEVLYN_SKILL_DIR/../_shared" && pwd)"
GATE="$DEVLYN_SHARED_DIR/intent-gate.py"
if [ ! -f "$GATE" ]; then
  echo "BLOCKED:shared-dir-unresolved: $GATE" >&2
  exit 1
fi
```

Claude Code supplies `CLAUDE_SKILL_DIR`; Codex/oh-my-pi installs receive an absolute copy-time stamp in the default branch.
</runtime_paths>

## Kernel

1. **The user's contract comes first.** The request, spec, explicit choices and authorized scope are immutable inputs. Resolve material ambiguity before changing behavior. After the run starts, work hands-free: take the safe default and log it in the report instead of asking.
2. **You implement and run real checks.** Apply the project instructions (CLAUDE.md / AGENTS.md). State the smallest change and the check that could refute it. Reproduce a bug with a failing check before fixing it. Existing tests are contract. Remove code your change made unused.
3. **Counterexample → reproduce → repair → recheck.** Independent review is mandatory. Reproduce every binding finding with a failing check before repairing it. After any source change, rerun the checks and get fresh reviews; earlier results never carry over.
4. **Failure never becomes success.** `intent-gate.py finish` writes the only verdict. Missing, stale or failed evidence is reported as it is; never describe the run as more complete than the gate says.

## Modes

- `"<goal>"` or `--goal-file <path>`: goal mode.
- `--spec <path>`: spec mode. The spec and its sibling `spec.expected.json` (or inline `<!-- devlyn:verification -->` block) are read-only. Every verification command is a required check, run verbatim.
- `--verify-only <diff-file-or-git-ref> --spec <path>`: review only. No scope, edits, commit or delivery.
- `--plan-only [--quick | --from-spec <path> | --project]`: plan without implementing. Follow the installed sibling ideate skill (`devlyn:ideate/SKILL.md`; on Windows the directory is `devlynideate`) with the remaining arguments. Write the same outputs in the same locations, and end with `/devlyn:intent --spec <path>` instead of the resolve command. Do not start the gate and do not edit product files.
- Other flags keep their existing meaning: `--engine`, `--role-config`, `--pair-verify`, `--no-pair`, `--max-rounds <n>` (review rounds, default 4). Any other flag stops with `BLOCKED:invalid-flags`.

## Run

Run every gate command in the foreground from the repository root, with a tool timeout longer than its own bound (checks 30 min unless the spec sets one, reviews 10 min, delegation 90 min). Never background them. A `BLOCKED:<reason>` exit (code 2) stops the step. Report it; do not work around it.

1. **Own the delivery branch first.** For work that will be delivered, allocate the task branch before any product edit, following the installed resolve skill's `references/task-completion.md` (sibling directory `devlyn:resolve`, or `devlynresolve` on Windows). Verify-only and local-only runs skip allocation.
2. **Start.** `python3 "$GATE" start --owner <claude|codex> -- <pipeline_config tokens>`. `--owner` is the CLI you are running in. The gate freezes the contract bytes, roles (`.devlyn/engines.json`, `--engine`, `--role-config`, `--no-pair`, with explicit routes failing closed), the base commit and the pre-existing untracked files. Those files are not yours: never edit, stage or commit them. The output says whether delegation is required, which reviewers run, and which checks the spec requires.
3. **Understand.** Read the contract, the relevant code, tests and callers. If the goal names nothing identifiable in this repository, stop with `BLOCKED:large-needs-ideation` and suggest `--plan-only`. For a broad goal, record your assumptions under `## Assumptions` in the report.
4. **Bind scope before the first edit.** `python3 "$GATE" scope <path-or-glob>...` lists every path you may change, including tests and docs (`dir/**` covers a subtree). It is bound once and never widened. If the work turns out to need more, finish and report the gap.
5. **Implement.** When the gate reports `delegate_required`, the pinned executor makes the edits. Write a bounded prompt with the contract, scope, plan and checks, then run `python3 "$GATE" delegate --prompt-file <file>`. Review its diff; do not re-implement it. Every path the run finally changes must come from a delegation, so reproduction tests and repairs go to the executor too. Otherwise implement here.
6. **Commit, then check.** `python3 "$GATE" commit --message "<message>"` commits only your in-scope changes. Evidence is bound to that exact commit and worktree, so commit before checking. Then run each check with `python3 "$GATE" check --cmd "<command>"`: every required spec command verbatim, plus the project's applicable tests, type checks, lint and build, and a browser check when you changed a web UI. If a probe turns out to be invalid, `retire --cmd "<command>" --reason "<why>"` keeps it visible in the verdict. Required commands cannot be retired.
7. **Review.** `python3 "$GATE" review --role primary_judge`, then `--role pair_judge` unless the start output says the pair is skipped. The two may run as parallel foreground calls. Each reviewer is a fresh read-only process that gets the contract, scope, the diff of this run and the check results on this source. The gate checks the reviewer's model against the requested one.
8. **Repair.** For each binding finding, reproduce it with a failing check, repair it (through `delegate` when an executor is pinned), commit, rerun the affected and required checks, and get fresh reviews. You cannot override a reviewer. If you believe a finding is wrong, put your evidence in the report and let the run end NEEDS_WORK. `--max-rounds` bounds the number of primary review rounds.
9. **Finish.** `python3 "$GATE" status` shows what is still missing. `python3 "$GATE" finish --task <task identity>` writes the verdict (`PASS`, `NEEDS_WORK` or `BLOCKED`) with its reasons and notes. On PASS outside verify-only, it also writes `.devlyn/acceptance.json` (kind `direct`) for the verified commit.
10. **Deliver** only on PASS, and only when neither verify-only nor local-only applies: `python3 "$DEVLYN_SHARED_DIR/task-complete.py" complete --receipt <receipt> --acceptance .devlyn/acceptance.json`. The default mode is a pull request. Report delivery status separately from the verdict.

## Report

Lead with the gate verdict, quoting its reasons and notes verbatim. Then give:
- the requirements met, with their checks;
- each finding and the evidence that closed it, or why it is still open;
- skipped or timed-out reviewers, retired probes and processes the gate killed;
- remaining limits and assumptions;
- delivery status (PR URL, pending or not delivered);
- usage per owner, executor and reviewer call where the CLI reports it, and `UNKNOWN` where it does not.

The run's evidence stays under `.devlyn/intent/`. The next `start` archives it to `.devlyn/intent/runs/<run_id>/`.
