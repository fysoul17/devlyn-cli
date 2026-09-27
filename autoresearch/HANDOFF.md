# Continue 0225 — cut full resolve's own time and tokens

2026-09-27 KST. Root direct. The contract is [0225](iterations/0225-resolve-cost-cuts.md): registered and frozen before implementation. The design was converged with Astra (gpt-6-astra, ultra); the raw record is `.devlyn/0221/s9-diag/` (diagnosis, cost ledgers, cut designs) and `.devlyn/0225/` (per-step specs, reviews, logs). The closed [0221](iterations/0221-subtraction-direction.md) handoff is in git history (last version at `62eb2d98`).

## Start here (every new session)

1. **Confirm the previous step's PR is merged, then start from updated `main`.** In this checkout (`~/.local/share/nx01/core-continuation-20260912`):
   - `gh pr list --repo fysoul17/devlyn-cli --state all --head <previous branch> --json number,state,mergedAt,url` must show `MERGED`. If it does not, stop and report; do not stack a dependent branch on an unmerged one.
   - `git status --porcelain` must be empty, apart from files you can prove you own. Then run `git switch main && git pull --ff-only origin main`.
2. **Read the contract.** Read 0225 "Plan" and "Confirmation", then the step's row below.
3. **Allocate a task branch:** `python3 config/skills/_shared/task-complete.py allocate --repo . --task '<id>' --branch 'candidate/<id>' --repository fysoul17/devlyn-cli --remote origin --base main` (move untracked files aside first; allocation needs a clean tree).
4. **Design, implement, verify.** Astra writes the exact step spec (read-only, isolated, `config/skills/_shared/codex-monitored.sh -m gpt-6-astra -c model_reasoning_effort=ultra`); `gpt-6-sol` implements it (`-s workspace-write`, it cannot write `.agents/`); root mirrors `.agents/skills` and the local `.claude/skills`, runs the checks, and repeats Astra verification until SHIP. Grok 4.7 is an optional counterexample reviewer: pass the diff inline (under ~90 KB), no tools, `--permission-mode dontAsk`.
5. **Deliver as a PR.** Commit, write the acceptance file (kind `direct`), then `python3 config/skills/_shared/task-complete.py complete --receipt <receipt> --acceptance <file> --mode pr`. Root merges each step PR once Astra verification is SHIP and CI (posix + windows) is green (user decision 2026-09-27: "둘다 오케이").
6. **Hand off.** In the same PR, update the table and "Next" below.

## Steps

| # | Scope (0225 "Plan") | Status |
|---|---|---|
| 1 | Repair budget owned by the state writer; VERIFY `BLOCKED` no longer repairs; judge path fix (branch `candidate/0225-s1-budget-path`) | merged (PR #117) |
| 2 | Scripted VERIFY (renderer, one supervisor starts both judges, one merge call) | pending |
| — | Replay: 7 archived VERIFY rounds × 2 judges | after step 2 |
| 3 | One final mechanical gate; SURFACE_CLOSE removed | pending |
| 4 | Fewer owner turns (no API-discovery reads, no polling, one rendered report) | pending |
| 5 | Contract-first PLAN; defect-4 executable witnesses | pending |
| 6 | Claude inline IMPLEMENT (separate arm) | pending |
| — | Live confirmation: 8 + 2 runs (user approved 2026-09-27) | pending |

**Next:** step 2 (scripted VERIFY) from main `6fc425f2` or later. Both user decisions are settled (2026-09-27): root merges step PRs after Astra SHIP + green CI, and the live confirmation runs are approved.

Step 1 record (base `62eb2d98` + registration `ec3e1d24`):
- `rounds.global` now counts repair IMPLEMENT admissions and is written only by `state-phase-write.py`, under `.devlyn/pipeline.state.lock` (`verify-merge-findings.py --write-state` takes the same lock). Admission covers BUILD_GATE FAIL, CLEANUP FAIL, VERIFY NEEDS_WORK and phase-gate FAIL, requires the exact trigger and the next invocation round, and refuses with `BLOCKED:repair-budget-exhausted` when `global >= max_rounds` (default stays 4). The two-strike VERIFY rule and the one-fix phase-gate cap are gone; `verify-exhausted`, `build-gate-exhausted` and `phase-gate-exhausted` are retired. VERIFY exhaustion ends `NEEDS_WORK`; pre-VERIFY exhaustion ends `BLOCKED:repair-budget-exhausted`. VERIFY `BLOCKED` goes to the report without a repair. FINAL_REPORT stores the full terminal verdict; `terminal-claim-check.py` and `archive_run.py` accept it and validate exhaustion witnesses (schema v3 only; older archives classify as before).
- `judge-role-evidence.py:103` compares resolved paths, so a relative `--devlyn-dir` no longer BLOCKs Claude judges.
- Process: Astra spec (after root draft REVISE ×4) → sol implementation → Astra verification R1 REVISE (6) → R2 REVISE (2) → R3 REVISE (2 + one subtraction) → R4 REVISE (1) → R5 SHIP (1,060 admission assertions, 142 checker cases, 192 extra checks).
- Checks: self-tests of state-phase-write, terminal-claim-check, judge-role-evidence, verify-merge-findings, resolve-bootstrap, spec-verify-check and archive_run; `scripts/test-owner-phases.py` (12); `scripts/lint-skills.sh` All checks passed; `git diff --check`; `.agents/skills` parity.
- Open: no saving is claimed for step 1. The owner lock for hand-edited `exec` metadata is a documented contract, not script-enforced.

Carried from 0221: the `/devlyn:queue` branch-reconciliation rule is not exercised by a model-driven drain; a null `autoMergeRequest` does not prove merge-queue removal; the slim+orphan instruction add-back (0223) is an open user decision.

## Standing rules

- **No token, cost or call budgets** in the harness or in tests. Keep only the watchdog (90 min per task, 10 min per review) and post-hoc usage recording; missing usage is recorded as UNKNOWN, never 0.
- **Models.** Claude config: `claude-opus-5-5`. Codex config: `gpt-6-astra` owner with `gpt-6-sol` implementation. Light path: `claude-sonnet-5` or `gpt-6-sol`. `grok-4.7` is an optional reviewer only. Do not auto-substitute Fable 5.2+.
- **No resolve invocation** in research (0201 rule 5, the user's no-resolve instruction), except 0225's registered live confirmation runs, which the user approved on 2026-09-27. Do not rerun D1. 0185 and D1–D4 are not holdout evidence.
- **Frozen material.** A16, frozen results and the original WIP stay untouched. Past stop verdicts (0211–0219, 0224) are history, not something to regrade.
- **User-facing messages** are always in Korean, plain and short: conclusion first, then what the user must decide, then the recommendation.
