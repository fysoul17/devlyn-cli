# 0232 harness ladder — stage 1 CLOSED (A admitted, I not); resolve being retired; next: register the installed baseline

## The owner's direction (2026-10-05)

The owner redirected the work. The details are in NORTH-STAR "Owner direction 2026-10-05" and the record [0232](iterations/0232-harness-ladder.md).

Follow the product direction in NORTH-STAR and O1–O4 in 0232:
- instruction-only first, with `intent` mechanisms only where earned;
- `ideate` as the loop designer;
- `design-ui` retired.

Wall, input and output are judged per correctly completed task, failures included. Incumbent replacement targets at least 30% less wall per success than F, with quality preserved and no input or output increase; §6 defines zero-success comparisons. Core routes come first. Run the registered 0232 cells when ready; no further run approval is required.

## State

- **0230 bundle** (`bundle/0225-steps-2-5`, head `f71a17d3`): parked, unmerged.
  - The v7 review-fix round is kept for reference and for reusing primitives on remote branches: `candidate/bundle-review-fix-v7` at `3eed3956`, and the parked wave 2 as `candidate/v7-w5` (`fc7c1bbe`) and `candidate/v7-w6` (`fa7d0e82`), committed unreviewed.
  - Owner decision R5 (2026-10-05) protects pre-run ignored user files. It applies again if a methodology layer is ever earned.
- **0231:** superseded by 0232 and never run.
- **0232 stage 1: CLOSED** (0232 §7). The result is `LIVE:claude=admitted:A,replaces_F:FAIL;codex=admitted:A,replaces_F:FAIL`.
  - Native A stays the admitted rung. I is not admitted: in the claude config it fails on I0185 quality, in the codex config on wall.
  - F completes fewer cells than A at far higher cost.
  - The evidence is in `experiments/0232/results/` and `~/.local/share/nx01/0232-live/out`.
  - Rung 1 stays unmerged on `candidate/0232-rung1` (`5bf3dc74`).
- **Product:**
  - The ideate loop and the retirement of design-ui and the queue skill are merged (PR #169).
  - resolve is being retired as a product-scope decision (0232 §8). The owner can veto that by reverting the product PR before release.

**Next:**

1. **Finish resolve's retirement** to the plan in `.devlyn/bundle/result-product-a1-astra.out.md` Part B. Get Astra's review and CI including native Windows, then merge.
2. **Final whole-product check** against the original intent: intake, loop design, autonomous execution, acceptance, truthful reporting, delivery.
3. **Next registration:** the actual installed baseline, meaning principles plus ideate, with the easy-task panel. After that, I′, licensed by I's lost final reviews and review cost.
4. **Release preparation** (version, notes, publish) stays with the owner.

## Open user decisions and carried notes

- **The `_devlynjudge` user record (uid 450) remains.** macOS refuses its deletion without Full Disk Access. Removing it is the user's call.
- **Raw outputs of the 0228/0229 replays** remain in `/Users/Shared/devlyn-vr-0228-dev` (owner-only) until the user decides.
- **Orphan cleanup.** Rung 1 keeps the orphan-cleanup obligation. Its isolated effect is unmeasured, and the separate 0223 slim-plus-orphan add-back is unrun and remains an open user decision.
- **The `/devlyn:queue` branch-reconciliation rule** has not been exercised by a model-driven drain. A null `autoMergeRequest` does not prove the merge queue was removed.

## Start here (every new session)

1. **Confirm the previous PR is merged, then start from an updated `main`.** The checkout is `~/.local/share/nx01/core-continuation-20260912`.
   - `gh pr list --repo fysoul17/devlyn-cli --state all --head <previous branch> --json number,state,mergedAt,url` must show `MERGED`. Otherwise stop and report.
   - `git status --porcelain` must be empty apart from files you can prove you own. Then run `git switch main && git pull --ff-only origin main`.
2. **Read NORTH-STAR's 2026-10-05 block and 0232** end to end.
3. **Allocate a task branch:** `python3 config/skills/_shared/task-complete.py allocate --repo . --task '<id>' --branch 'candidate/<id>' --worktree '<absent path>' --repository fysoul17/devlyn-cli --remote origin --base main`.
4. **Work and verify.**
   - Root works directly.
   - Astra reviews read-only and isolated: `CODEX_MONITORED_ISOLATED=1 DEVLYN_CODEX_PROMPT_FILE=<prompt> config/skills/_shared/codex-monitored.sh -C <repo> -s read-only -m gpt-6-astra -c model_reasoning_effort=ultra -`.
     - Send stdout to a file, never a pipe.
     - Wait on `^\[codex-monitored\] codex exited` in stderr.
     - Continue until SHIP.
   - Review and fix rounds follow the 2026-10-05 threat model: one bounded review per fix round.
5. **Deliver as a PR.**
   - Commit in the task worktree.
   - Write `<worktree>/.devlyn/acceptance.json` (kind `direct`).
   - From a cwd outside the checkout, run `task-complete.py complete --receipt <receipt> --acceptance <file> --mode pr --writers-stopped`.
   - Root merges research PRs once Astra verification is SHIP and CI is green where it runs, with `--mode auto --writers-stopped`.
6. **Hand off** in the same PR by updating this file.

## Standing rules

- **No token, cost or call budgets in the harness or in tests.**
  - Keep only the watchdogs: 90 min per task, 10 min per review, 600 s per judge seat.
  - Keep post-hoc usage recording. Missing usage is UNKNOWN, never 0.
  - Promotion criteria compare recorded usage; they are not budgets.
- **Models.**
  - Claude: `claude-opus-5-5`.
  - Codex: `gpt-6-astra` for design, review and judges, and `gpt-6-sol` for implementation.
  - `grok-4.7` is an optional reviewer only.
  - Do not auto-substitute Fable 5.2+.
- **Resolve and intent run only inside registered comparisons the owner approved.**
  - 0232's cells were approved on 2026-10-05.
  - Do not rerun D1. 0185 and D1–D4 are not holdout evidence.
- **Frozen material.**
  - A16, frozen results and the original WIP stay untouched.
  - 0226's sealed root `/Users/Shared/devlyn-vr` stays byte-identical.
  - Past stop verdicts (0211–0219, 0224, 0225) are history, not something to regrade.
  - Do not run a third 0225 replay or its live comparison, and do not publish its held candidate `22616b57`.
- **Replay apparatus gotchas (0225).**
  - Judge roots go outside `$HOME`: Claude loads every ancestor `.claude/CLAUDE.md`.
  - Codex judges need an isolated HOME (a shim), because `--ignore-user-config` still loads `$CODEX_HOME/AGENTS.md` and `~/.agents/skills`.
  - nvm Codex auto-updates silently, so pin a private install (0.156.1 at `/Users/Shared/devlyn-0225-codex-0.156.1`).
- **User-facing messages** are always in Korean, plain and short: the conclusion first, then what the user must decide, then the recommendation.
