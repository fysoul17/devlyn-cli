# Continue 0226 — recall screen for the held scripted VERIFY

2026-09-28 KST. Root direct, no resolve. The contract is [0226](iterations/0226-verify-recall-screen.md): registered and frozen before any corpus authoring or candidate call, designed with Astra (gpt-6-astra, ultra). The raw record is `.devlyn/0226/`. The 0225 handoff is in git history (last version at `3eec48b4`).

## Start here (every new session)

1. **Confirm the previous PR is merged, then start from updated `main`** (checkout `~/.local/share/nx01/core-continuation-20260912`):
   - `gh pr list --repo fysoul17/devlyn-cli --state all --head <previous branch> --json number,state,mergedAt,url` must show `MERGED`; otherwise stop and report.
   - `git status --porcelain` must be empty apart from files you can prove you own; then `git switch main && git pull --ff-only origin main`.
2. **Read 0226** end to end, then the step's row below.
3. **Allocate a task branch:** `python3 config/skills/_shared/task-complete.py allocate --repo . --task '<id>' --branch 'candidate/<id>' --repository fysoul17/devlyn-cli --remote origin --base main`.
4. **Work and verify.** Root works directly. Astra reviews read-only and isolated (`CODEX_MONITORED_ISOLATED=1 DEVLYN_CODEX_PROMPT_FILE=<prompt> config/skills/_shared/codex-monitored.sh -C <repo> -s read-only -m gpt-6-astra -c model_reasoning_effort=ultra -`, stdout to a file, never a pipe) until SHIP. `gpt-6-sol` implements where 0226 says so (`-s workspace-write`; it cannot write `.agents/`).
5. **Deliver as a PR.** Commit, write the acceptance file (kind `direct`), then `task-complete.py complete --receipt <resolved path>/.git/devlyn-completion/<id>/receipt.json --acceptance <file> --mode pr`. Root merges 0226 PRs once Astra verification is SHIP and CI is green where it runs (user decision 2026-09-28, "예, 병합해도 됨"), with `--mode auto --writers-stopped` from a cwd outside the checkout.
6. **Hand off** in the same PR: update the table below.

## Steps (0226 "Work order")

| # | Scope | Status |
|---|---|---|
| 1 | Registration: Astra FREEZE, PR, merge | in progress (branch `candidate/0226-registration`) |
| 2 | Corpus: repository selection, blind authoring, implementation, calibration, calibration review | not started |
| 3 | Apparatus: driver, Astra SHIP, stub dry run of all 64 spans | not started |
| 4 | Freeze commit + PR witness, 64 rounds, scoring, masked adjudication with Astra audit, RESULT | not started |

## 0225 (steps 2–5 held)

- The replay failed twice by its letter ([RESULT](experiments/0225/RESULT.md)); steps 2–5 are held. The user chose (2026-09-28) to revert and register 0226.
- Revert PR #124 (Astra SHIP) merged as `3eec48b4`: every path outside `autoresearch/` equals `366d837a` (step 1, PR #117). The held candidate is `22616b57` (steps 2 + 2r) and stays in history.
- **Must not happen:** regrading either attempt, a third 0225 replay, the 0225 live comparison, or publishing the held bundle.

Carried from 0221: the `/devlyn:queue` branch-reconciliation rule is not exercised by a model-driven drain; a null `autoMergeRequest` does not prove merge-queue removal; the slim+orphan instruction add-back (0223) is an open user decision.

## Standing rules

- **No token, cost or call budgets** in the harness or in tests. Keep only the watchdogs (90 min per task, 10 min per review, the candidate's 600 s per judge seat) and post-hoc usage recording; missing usage is UNKNOWN, never 0.
- **Models.** Claude: `claude-opus-5-5`. Codex: `gpt-6-astra` (design, review, judges) and `gpt-6-sol` (implementation). `grok-4.7` is an optional reviewer only. Do not auto-substitute Fable 5.2+.
- **No resolve invocation** in research (0201 rule 5; the user repeated it on 2026-09-28). Running only the judge script `verify-judges.py` on synthesized spans, as the 0225 replay did, is not a resolve invocation (user decision 2026-09-28, "괜찮음"). 0225's live-run approval does not transfer. Do not rerun D1. 0185 and D1–D4 are not holdout evidence.
- **Frozen material.** A16, frozen results and the original WIP stay untouched. Past stop verdicts (0211–0219, 0224, 0225) are history, not something to regrade.
- **Replay apparatus gotchas** (0225): judge roots go outside `$HOME` (Claude loads every ancestor `.claude/CLAUDE.md`); Codex judges need an isolated HOME (shim), because `--ignore-user-config` still loads `$CODEX_HOME/AGENTS.md` and `~/.agents/skills`; nvm Codex auto-updates silently, so pin a private install (0.156.1 at `/Users/Shared/devlyn-0225-codex-0.156.1`).
- **User-facing messages** are always in Korean, plain and short: conclusion first, then what the user must decide, then the recommendation.
