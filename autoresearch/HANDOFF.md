# 0232 stage 1 closed; resolve retired (PR #171); ideate loop redesigned and verified by real runs (PR #172); final fixes with in-place direct work (PR #173); the owner's release-prep decisions applied (PR #175); next is the version and release notes, then the installed-baseline registration

## The owner's direction (2026-10-05)

The owner redirected the work. The details are in NORTH-STAR "Owner direction 2026-10-05" and the record [0232](iterations/0232-harness-ladder.md).

Follow the product direction in NORTH-STAR and O1–O4 in 0232:
- instruction-only first, with `intent` mechanisms only where earned;
- `ideate` as the loop designer;
- `design-ui` retired.

Wall, input and output are judged per correctly completed task, failures included. Incumbent replacement targets at least 30% less wall per success than F, with quality preserved and no input or output increase; §6 defines zero-success comparisons. Core routes come first.

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
  - resolve is retired as a product-scope decision (0232 §8; PR #171, merge `d2d34e3e`). The owner confirmed it on 2026-10-07 (no veto).
  - The ideate redesign is merged (PR #172, merge `52636e19`). add captures the package under `refs/devlyn/captures/<loop-id>`, and each loop keeps its rows in its own `docs/specs/<loop-id>/queue.md`. The drain also fills the executor's `{worktree_git_dir}`, review records may carry keys acceptance does not read, a task waits while its start commit's CLAUDE.md or AGENTS.md differs from the checkout's, and local allocation needs no `--repository`.
    - Astra ultra reviewed it as SHIP (`e2e-fix-a2-astra.out.md` in the checkout's `.devlyn/bundle/`).
    - Real Claude-host and Codex-host loops passed first try with the documented commands; the evidence is in `~/.local/share/nx01/e2e-smoke3`.
  - The release-prep decisions PR (#175, merge `c8013cf1`; `candidate/release-prep-decisions`, owner decisions of 2026-10-07; contract `release-prep-contract.md`, Astra design records `rp-d1/d2/d3-*-astra.out.md` in `.devlyn/bundle/`):
    - **Delivery default restored:** with no delivery instruction, a completed, verified direct request with changes is delivered by project policy, default PR and merge. Explicit limits win (commit alone stays local, PR stops at the PR, local-only/no-push/just-edit). Edits stay in place; isolation changes location, not scope; the original edits stay until a safe `--ff-only` reconciliation; an implicit delivery without a GitHub origin falls back to a reported local commit.
    - **Cleanup sentence restored** to principle 2 as a contract correction (rp-d2); its isolated effect is still unmeasured.
    - **Ideate:** bounded autonomous defaults, which may be user-visible but must be low-consequence and recorded; the drain report carries the package's decisions; real dependencies are kept, with a check-only integration task when deliverables are independent; a local loop runs one task at a time, and its frontier is the accepted source containing the others.
    - **Release:** an MIT LICENSE; publish runs only after the portability suites pass; the Claude target no longer ships the three spec and prompt templates (earlier copies stay).
    - PR #175 was delivered by the product itself, `task-complete.py` with the default `auto`. It created the PR, merged it and removed the worktree and both task branches. This was the first real-GitHub run of direct `auto` delivery. GitHub merged at once although repository auto-merge is off, because no check is required.
  - The final-fixes PR (#173, `candidate/final-fixes`) applied `final-fixes-contract.md`, `final-fixes-part2-contract.md` and `final-fixes-part4-contract.md` (`.devlyn/bundle/`).
    - Owner decision (2026-10-07), from the slowness investigation (`slowness-investigation.json`): direct work edits the current checkout. Delivery runs only when the user asks to ship it, and only as far as asked; root mapped a commit request to local-only, a PR request to `--mode pr` and a merge request to `--mode auto`. Every drained task is still delivered.
    - Concurrent writers (owner decision; Astra's synthesis in `direct-work-design-astra.out.md`): with known concurrent writers, isolate before editing; on unexplained changes, pause writes (`task-completion.md` "Concurrent writers"). A patch replaces the stash transfer.
    - Astra ultra reviewed the fix round after its final-audit REVISE as SHIP (`final-fixes-round2-astra.out.md`); both of its follow-ups are fixed.
    - A direct-task smoke on the final block (`final-fixes-direct-smoke.md`) edited in place with no worktree or commit on both hosts. Claude took 13.5–15.6 s and 5–7 turns in 3 runs, against 63.8 s and 14 turns with the old delivery pointer; Codex took 44 s and ran its tests.

**Next:**

1. **Release prep (the owner's):** the version and release notes. The notes should name: the restored delivery default; the cleanup sentence; the bounded autonomous defaults; the check-only integration task; one task at a time in local loops; the removed templates; the LICENSE; and the publish gate.
2. **The installed-baseline registration:** the principles block plus ideate, with the easy-task panel and 0223's B5 task (0232 §8). After that, I′, licensed by I's lost final reviews and review cost.
3. **Follow-ups:** the Known follow-ups below.

## Known follow-ups

One line per class. Details, each with its reproduction described, are in the checkout's `.devlyn/bundle/`: `final-audit-phase-b.json` (phase B, findings quoted by title) and `final-audit-phase-a.json` (phase A); the scratch scripts they name were temporary.

- **merge_refused:** an auto loop in a squash-only repository reports `Delivery: PR` without the refusal reason (phase B "The drain drops merge_refused").
- **Custody binding:** a drain interrupted while binding custody never resumes a task whose checks failed or were rerun (phase B "A drain interrupted while binding custody").
- **Retained scratch:** the drain report shows `Scratch cleanup: RETAINED` without its reason or resume command (phase B "Retained scratch is reported without its reason").
- **Deleted branch:** the drain report prints `Branch:` for a task branch delivery already deleted (phase B "The report prints 'Branch:'").
- **Unread submission fields:** the submission asks for `findings`, `cleanup`, `handoff` and `summary`, which nothing reads (phase B "The submission shape asks for four fields").
- **Queued loops:** the planner reads them through status and the captures, but a later local loop starts from its add branch, never an earlier loop's unlanded frontier (an owner decision), and a queued loop cannot be withdrawn (phase B "The planner cannot see queued, unlanded loops"; "A queued loop cannot be withdrawn").
- **Codex host permissions:** status, add and drain write the Git directory, so a Codex host in its default sandbox needs escalation, and no doc says so (phase B "A Codex host in its default workspace-write sandbox").
- **Global install:** `--global` installs ideate without the principles block and says nothing (phase B "A global install gives ideate without the principles block").
- **Non-default `base_ref`:** an auto/pr loop whose `base_ref` is not the default branch runs its executor, then waits on a delivery task-complete refuses; check it before allocation (phase B "One task's delivery refusal", its base_ref part).
- **`attach --file`:** `task-complete.py attach` still defaults `--file` to the legacy `docs/specs/queue.md` (phase B "task-complete.py attach still defaults --file").
- **loop.md and task-completion.md:** loop.md sends drain hosts to the direct-work completion contract, which points back with a duplicate summary (phase B "loop.md sends drain hosts to the 152-line direct-work completion contract").
- **Repetition:** the block and SKILL.md repeat text other surfaces carry (phase B "The always-loaded block and SKILL.md repeat text").
- **Research staleness:** `benchmark/ceiling/README.md` lists the tranche and the no-degradation cell as live, though both stage the retired resolve skill, and NORTH-STAR's pair-mode commitments and policy still describe resolve's VERIFY pair as shipped.
- **`devlyn-engines clear` on Pi and Grok:** exits 1 after deleting the pin, because `role-config.py` resolves the host default after the edit.
- **Drain-wide stops:** a failed base refresh, an executor that cannot start, a missing prerequisite merge, an unignored `.devlyn/` and a receipt directory without `receipt.json` still stop the whole drain, short of the shared rule in `final-fixes-part2-contract.md` that only an unreadable queue does.
- **Installer layouts:** a CLAUDE.md that imports AGENTS.md other than by an exact `@AGENTS.md` line (inline, or `@./AGENTS.md`) still gets a copy of the block beside the imported one, and a CLAUDE.md linked to AGENTS.md is still refused (phase B "A CLAUDE.md that imports AGENTS.md gets the block loaded twice").
- **package.json guard:** a symlinked root `package.json`, or one npm rejects at the inputs commit, fails `max_deps_added` for every task, the repairing task included; it fails closed (part-4 verification).
- **`--receipt` alias:** `complete` refuses a receipt path written through a symlink or `..`; agents copy the printed path, so it was left as it predates part 4 (part-4 verification).
- **Earlier lists:** `r4-followups.md` (round 4) and the Deferred sections of `e2e-fix-r3-contract.md` (round 3) and `final-fixes-contract.md` (phase A).
- **Real-run evidence:** the real-host loop runs (`~/.local/share/nx01/e2e-smoke3` and `e2e-smoke4`) cover only local-only loops in repositories with no remote, and direct `auto` delivery has one real-GitHub run (PR #175); before release, run one ideate auto loop on a throwaway GitHub repository (phase B "Real-host evidence covers only local-only loops").
- **Default-delivery cost:** wall time and tokens per delivered request under the restored default are unmeasured (rp-d1); the 13.5–15.6 s smoke covered editing only.
- **Release fingerprints:** publish regenerates `bin/instruction-templates.json` from first-parent history, so a block installed only from a PR-branch commit (such as `7e2eef0a`) is not recognized after release.
- **Forked local loops:** a local loop forked by a build before the one-task-at-a-time rule still stops the whole drain, and no test asserts that refusal.
- **Bounded defaults across engines:** rp-d3's real-model cross-host planning cases (display defaults proceed and enter task checks; persistent-state ambiguity or an unrequested interface stops) are unrun.

## Open user decisions and carried notes

- **The `_devlynjudge` user record (uid 450) remains.** macOS refuses its deletion without Full Disk Access. Removing it is the user's call.
- **Orphan cleanup.** The block carries the cleanup sentence again (owner decision 2026-10-07, rp-d2). Its isolated effect is unmeasured; 0223's add-back measurement still belongs to the installed-baseline registration.

## Start here (every new session)

1. **Confirm the previous PR is merged, then start from an updated `main`.** The checkout is `~/.local/share/nx01/core-continuation-20260912`.
   - `gh pr list --repo fysoul17/devlyn-cli --state all --head <previous branch> --json number,state,mergedAt,url` must show `MERGED`. Otherwise stop and report.
   - `git status --porcelain` must be empty apart from files you can prove you own. Then run `git switch main && git pull --ff-only origin main`.
2. **Read NORTH-STAR's 2026-10-05 block and 0232** end to end.
3. **Allocate a task branch:** `python3 config/skills/_shared/task-complete.py allocate --repo . --task '<id>' --branch 'candidate/<id>' --worktree '<absent path>' --repository fysoul17/devlyn-cli --remote origin --base main`.
4. **Work and verify.**
   - Root works directly.
   - Astra reviews read-only with Codex's isolation flags: `DEVLYN_CODEX_PROMPT_FILE=<prompt> config/skills/_shared/codex-monitored.sh --ignore-user-config --ignore-rules --ephemeral --disable codex_hooks --disable hooks -C <repo> -s read-only -m gpt-6-astra -c model_reasoning_effort=ultra -`.
     - Send stdout to a file, never a pipe.
     - Wait on `^\[codex-monitored\] codex exited` in stderr.
     - Continue until SHIP.
   - Review and fix rounds follow the 2026-10-05 threat model: one bounded review per fix round.
5. **Deliver as a PR.**
   - Commit in the task worktree.
   - Write `<worktree>/.devlyn/acceptance.json` (kind `direct`).
   - From a cwd outside the checkout, run `task-complete.py complete --receipt <receipt> --acceptance <file> --mode pr --writers-stopped`.
   - Root merges research PRs once Astra verification is SHIP and the POSIX suites pass locally (since PR #174, CI runs only per release), with `--mode auto --writers-stopped`.
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
  - The 0225–0229 raw roots in `/Users/Shared` were deleted on 2026-10-07 with the owner's approval; their results remain under `experiments/`.
  - Past stop verdicts (0211–0219, 0224, 0225) are history, not something to regrade.
  - Do not run a third 0225 replay or its live comparison, and do not publish its held candidate `22616b57`.
- **Replay apparatus gotchas (0225).**
  - Judge roots go outside `$HOME`: Claude loads every ancestor `.claude/CLAUDE.md`.
  - Codex judges need an isolated HOME (a shim), because `--ignore-user-config` still loads `$CODEX_HOME/AGENTS.md` and `~/.agents/skills`.
  - nvm Codex auto-updates silently, so pin a private install.
- **User-facing messages** are always in Korean, plain and short: the conclusion first, then what the user must decide, then the recommendation.
