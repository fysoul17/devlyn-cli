# 0228 closed at R2 FAIL — next step is the user's decision

2026-10-01 KST. Root direct, no resolve. The contract is [0228](iterations/0228-verify-rubric-rescreen.md) (amends [0227](iterations/0227-verify-rescreen.md) by reference), designed with Astra (gpt-6-astra, ultra) and registered before the G commit, any replay call and any corpus authoring. The raw record is `.devlyn/0228/`. 0227 closed NOT PASS ([RESULT](experiments/0227/RESULT.md), [DIAGNOSIS](experiments/0227/diagnosis/DIAGNOSIS.md)); its handoff is in git history (last version at `f3835c04`). User decision 2026-09-30 ("1"): fix the rubric where the diagnosis points, test by replay on 0227 material, then re-screen on fresh tasks.

## Start here (every new session)

1. **Confirm the previous PR is merged, then start from updated `main`** (checkout `~/.local/share/nx01/core-continuation-20260912`):
   - `gh pr list --repo fysoul17/devlyn-cli --state all --head <previous branch> --json number,state,mergedAt,url` must show `MERGED`; otherwise stop and report.
   - `git status --porcelain` must be empty apart from files you can prove you own; then `git switch main && git pull --ff-only origin main`.
2. **Read 0228** end to end (and 0227, which it amends by reference), then the step's row below.
3. **Allocate a task branch:** `python3 config/skills/_shared/task-complete.py allocate --repo . --task '<id>' --branch 'candidate/<id>' --worktree '<absent path>' --repository fysoul17/devlyn-cli --remote origin --base main`.
4. **Work and verify.** Root works directly. Astra reviews read-only and isolated (`CODEX_MONITORED_ISOLATED=1 DEVLYN_CODEX_PROMPT_FILE=<prompt> config/skills/_shared/codex-monitored.sh -C <repo> -s read-only -m gpt-6-astra -c model_reasoning_effort=ultra -`, stdout to a file, never a pipe; wait on `^\[codex-monitored\] codex exited` in stderr) until SHIP. `gpt-6-sol` implements where 0227 says so (`-s workspace-write`; it cannot write `.agents/`).
5. **Deliver as a PR.** Commit in the task worktree, write `<worktree>/.devlyn/acceptance.json` (kind `direct`), then from a cwd outside the checkout `task-complete.py complete --receipt <receipt> --acceptance <file> --mode pr --writers-stopped`. Root merges research PRs once Astra verification is SHIP and CI is green where it runs, with `--mode auto --writers-stopped`. G is a pushed branch with no PR, not merged during 0228.
6. **Hand off** in the same PR: update the table below.

**Replay batches (steps 3–4):** judges run as `_devlynjudge` (Addendum C2); the runner changes nothing outside `/Users/Shared/devlyn-vr-0227*` and `/Users/Shared/devlyn-vr-0228-dev`. After R3, or if the owner stops, tell the owner: the devlyn-os-v1 session removes the judge account and token.

## Steps (0228 "Work order")

| # | Scope | Status |
|---|---|---|
| 1 | Registration: Astra FREEZE, PR, merge | merged (PR #141) |
| 2 | G on `f40da73b` (`candidate/0228-fix`, pushed, no PR): implement, lint, portability suite, identifier grep, Astra SHIP | done: G = `607c3cf7`, Astra SHIP |
| 3 | Replay copy, inventory and isolation, R1, Astra SHIP; Addendum C1 (G, replay commit, inventory, replay order) | done: C1; the C1 seals touched owner files (incident) → C2: isolation by the judge account `_devlynjudge` (Astra SHIP); R1 re-run passed (stub 64/64, probe, owner baseline compare changed 0) |
| 4 | R2 (J4 references, G vs F) and R3 (recall and breadth), Astra reviews; replay root deleted after its record is committed | **R2 FAIL** (C3): G blocked the correct J4 reference in 1/40 replays (Codex primary), F in 4/16; R3 not run |
| 5 | Corpus: selection, blind authoring, implementation, calibration, calibration review | not run (R2 FAIL) |
| 6 | Driver copy, stub dry run, Astra SHIP; freeze and witness, 64 rounds, masked scoring with Astra audit, join, RESULT | not run (R2 FAIL) |

0227 in one line: 0226's failures did not recur (0 rejected Claude outputs, 0 BLOCKED, 128/128 seats accepted, 32/32 hits; the P specs still carry an unevidenced "Run from the repository root"), but one Codex primary blocked a correct J4 reference by reading "existing eviction disposal behavior" as immediate delivery; two more Codex seats returned NEEDS_WORK on J2 reference rounds from coverage findings only. **Diagnosis (2026-09-30, user chose "diagnose first"; Astra SHIP):** [DIAGNOSIS](experiments/0227/diagnosis/DIAGNOSIS.md) — replays of the four J4 reference rounds from their pristine inputs show recurrent Codex blocks on the keep-existing clause (Codex primary 7/17, pair 1/12, Claude 0/29); all 8 binding claims on reference rounds across 0226, G3 and 0227 came from Codex seats; the rubric has no explicit preservation-comparison step (text predates the candidate); the J2 coverage blocks come from a coverage vs source-review rule conflict. Astra: materially new diagnostic evidence, not proof of rubric causation. The user chose to register 0228 (above); steps 2–5 stay held until 0228's outcome.

0226 in one line: 32/32 hits and 0 false alarms, NOT PASS on condition 5 because 5 reference rounds ended BLOCKED (3 Claude prose preambles the parser rejected; 3 Codex BLOCKEDs on an unevidenced "offline, with Node 22" condition). 
## 0225 (steps 2–5 held)

- The replay failed twice by its letter ([RESULT](experiments/0225/RESULT.md)); steps 2–5 are held. The user chose (2026-09-28) to revert and register 0226.
- Revert PR #124 (Astra SHIP) merged as `3eec48b4`: every path outside `autoresearch/` equals `366d837a` (step 1, PR #117). The held candidate is `22616b57` (steps 2 + 2r) and stays in history.
- **Must not happen:** regrading either attempt, a third 0225 replay, the 0225 live comparison, or publishing the held bundle.

Carried from 0221: the `/devlyn:queue` branch-reconciliation rule is not exercised by a model-driven drain; a null `autoMergeRequest` does not prove merge-queue removal; the slim+orphan instruction add-back (0223) is an open user decision.

## Standing rules

- **No token, cost or call budgets** in the harness or in tests. Keep only the watchdogs (90 min per task, 10 min per review, the candidate's 600 s per judge seat) and post-hoc usage recording; missing usage is UNKNOWN, never 0.
- **Models.** Claude: `claude-opus-5-5`. Codex: `gpt-6-astra` (design, review, judges) and `gpt-6-sol` (implementation). `grok-4.7` is an optional reviewer only. Do not auto-substitute Fable 5.2+.
- **No resolve invocation** in research (0201 rule 5; the user repeated it on 2026-09-28). Running only the judge script `verify-judges.py` on synthesized spans, as the 0225 replay did, is not a resolve invocation (user decision 2026-09-28, "괜찮음"). 0225's live-run approval does not transfer. Do not rerun D1. 0185 and D1–D4 are not holdout evidence.
- **Frozen material.** A16, frozen results and the original WIP stay untouched; 0226's sealed root `/Users/Shared/devlyn-vr` stays byte-identical. Past stop verdicts (0211–0219, 0224, 0225) are history, not something to regrade.
- **Replay apparatus gotchas** (0225): judge roots go outside `$HOME` (Claude loads every ancestor `.claude/CLAUDE.md`); Codex judges need an isolated HOME (shim), because `--ignore-user-config` still loads `$CODEX_HOME/AGENTS.md` and `~/.agents/skills`; nvm Codex auto-updates silently, so pin a private install (0.156.1 at `/Users/Shared/devlyn-0225-codex-0.156.1`).
- **User-facing messages** are always in Korean, plain and short: conclusion first, then what the user must decide, then the recommendation.
