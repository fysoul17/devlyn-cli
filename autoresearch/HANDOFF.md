# 0227 closed NOT PASS — next step is the user's decision

2026-09-29 KST. Root direct, no resolve. The contract is [0227](iterations/0227-verify-rescreen.md), designed with Astra (gpt-6-astra, ultra) and registered before the fix commit, any probe call and any corpus authoring. The raw record is `.devlyn/0227/`. 0226 closed NOT PASS ([RESULT](experiments/0226/RESULT.md)); its handoff is in git history (last version at `f72f74f4`).

## Start here (every new session)

1. **Confirm the previous PR is merged, then start from updated `main`** (checkout `~/.local/share/nx01/core-continuation-20260912`):
   - `gh pr list --repo fysoul17/devlyn-cli --state all --head <previous branch> --json number,state,mergedAt,url` must show `MERGED`; otherwise stop and report.
   - `git status --porcelain` must be empty apart from files you can prove you own; then `git switch main && git pull --ff-only origin main`.
2. **Read 0227** end to end (and 0226, which it amends by reference), then the step's row below.
3. **Allocate a task branch:** `python3 config/skills/_shared/task-complete.py allocate --repo . --task '<id>' --branch 'candidate/<id>' --repository fysoul17/devlyn-cli --remote origin --base main`.
4. **Work and verify.** Root works directly. Astra reviews read-only and isolated (`CODEX_MONITORED_ISOLATED=1 DEVLYN_CODEX_PROMPT_FILE=<prompt> config/skills/_shared/codex-monitored.sh -C <repo> -s read-only -m gpt-6-astra -c model_reasoning_effort=ultra -`, stdout to a file, never a pipe) until SHIP. `gpt-6-sol` implements where 0227 says so (`-s workspace-write`; it cannot write `.agents/`).
5. **Deliver as a PR.** Commit, write the acceptance file (kind `direct`), then `task-complete.py complete --receipt <resolved path>/.git/devlyn-completion/<id>/receipt.json --acceptance <file> --mode pr`. Root merges 0227 research PRs once Astra verification is SHIP and CI is green where it runs (user decision 2026-09-29, "둘 다 예"), with `--mode auto --writers-stopped` from a cwd outside the checkout. The fixed candidate is a pushed branch with no PR, not merged during 0227.
6. **Hand off** in the same PR: update the table below.

## Steps (0227 "Work order")

| # | Scope | Status |
|---|---|---|
| 1 | Registration: Astra FREEZE, PR, merge | merged (PR #130) |
| 2 | Fix commit F on `22616b57` (pushed branch, no PR): implementation, G1, Astra SHIP | done: F = `f40da73b` on `candidate/0227-fix`, Astra SHIP after one REVISE (3) |
| 3 | Driver copy with the registered changes and development mode, stub dry run, Astra SHIP; addendum B1 (F, driver, G2 spec copies, author/implementer templates) | done: B1 (driver Astra SHIP after two REVISE; 64-span dry run and G2 rehearsal passed) |
| 4 | G2 (6 live Claude calls), then G3 (64 exposed 0226 spans in a development root); Astra reviews | done: G2 PASS, G3 PASS (Astra audits; [GATES](experiments/0227/gates/GATES.md)) |
| 5 | Corpus: two fresh repositories, isolated blind author, Sol, calibration, calibration review | done: attrs `8f767776` (P1–P4) and node-lru-cache `7e71a1f3` (J1–J4; adm-zip dropped after Astra found the node-lru-cache exclusion misapplied the rule); Astra + Claude checkers SHIP after repairs (Addendum B2) |
| 6 | Fresh-corpus driver bindings, Astra SHIP; freeze, 64 rounds, masked scoring with Astra audit, join, RESULT | done: **NOT PASS on condition 2 only** ([RESULT](experiments/0227/RESULT.md)): 32/32 hits, condition 5 now holds, 1 reference false alarm (J4, Codex primary); freeze PR #138, score/result PR |

0227 in one line: the fix worked for 0226's causes (0 rejected Claude outputs, 0 BLOCKED, 128/128 seats accepted, 32/32 hits), but one Codex primary blocked a correct J4 reference by reading "existing eviction disposal behavior" as immediate delivery; two more Codex seats returned NEEDS_WORK on J2 reference rounds from coverage findings only. **Next: the user's decision** — steps 2–5 stay held; any new registration needs a materially new diagnosis (0227 "Registered outcome").

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
