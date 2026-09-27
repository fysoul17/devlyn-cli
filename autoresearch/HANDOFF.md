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
| 2 | Scripted VERIFY (renderer, one supervisor starts both judges, one merge call) (branch `candidate/0225-s2-scripted-verify`) | done (Astra SHIP) |
| — | Replay: 7 archived VERIFY rounds × 2 judges (mechanics registered in 0225 "Replay mechanics") | attempt 1 FAIL 4/5 ([RESULT](experiments/0225/RESULT.md)); step-2 revision, then the one repeat |
| 3 | One final mechanical gate; SURFACE_CLOSE removed | pending |
| 4 | Fewer owner turns (no API-discovery reads, no polling, one rendered report) | pending |
| 5 | Contract-first PLAN; defect-4 executable witnesses | pending |
| 6 | Claude inline IMPLEMENT (separate arm) | pending |
| — | Live confirmation: 8 + 2 runs (user approved 2026-09-27) | pending |

**Next:** the one registered step-2 revision, then replay attempt 2 (the registration's only repeat; a second failure holds steps 2–5 and only step 1 ships).
- **Attempt 1** ([RESULT](experiments/0225/RESULT.md)) FAILED by the letter. 4 of 5 binding HIGHs came back as HIGH, and the fifth (s6-04 r1, writer readiness) came back as MEDIUM `verdict_binding: true` at the same line. It had 0 input BLOCKEDs, overlap in all 7 rounds and an unchanged archive.
- **Revision (Astra-concurred).** Fix the step-2 regression it exposed. Step 2 extended the pair-only strict emission contract to the primary seat, so a Claude primary's one prose line made s6-16-r0 BLOCKED although the pair had the binding HIGH. Keep the fix general, with negative cases. Do not touch the binding-MEDIUM channel, which predates step 2.
- **Apparatus before the repeat.** Move the replay root outside `$HOME`: attempt 1's Claude seats loaded `~/.claude/CLAUDE.md` as an ancestor `.claude/CLAUDE.md`. Verify the Claude instruction attachments (s6-07 must fall back to its `AGENTS.md`) before any call, and widen the scanner.
- **Repeat.** Re-prepare, re-freeze, and run all 7 rounds once, scored by the committed criteria.
- **Driver.** `autoresearch/experiments/0225/replay.py` (prepare → freeze commit → run → score).

Step 1 (PR #117): the state writer owns the repair budget (`rounds.global` admissions under the state lock, `BLOCKED:repair-budget-exhausted`); VERIFY `BLOCKED` goes to the report without repair; relative `--devlyn-dir` judge paths resolve. No saving claimed.

Step 2 record (base `366d837a`; design `.devlyn/0225/s2-design.md`, spec `s2-spec-astra.out.md` amended by `s2-spec-r1-astra.out.md`):
- The owner runs MECHANICAL, then one foreground command, `verify-judges.py`. It claims the round by exclusively creating `.devlyn/verify-judge.r<N>.dispatch.json`, routes each seat from the frozen roles, and renders both prompts from one hash-checked snapshot with `phase-prompt-render.py` (contract, goal, sibling expected, authorized surface, diff, sealed MECHANICAL results). It starts both judges before waiting on either (Claude `claude -p` under `run-bounded.py 600`, Codex isolated read-only `codex-monitored.sh`), writes role evidence for each successful seat, and ends with the single `verify-merge-findings.py --write-state` call.
- The merge runs once per round, under the lock. It validates the dispatch record against the span and the frozen selection, publishes `pair_trigger`, authorizes every seat's runner-written transport (v2: `outcome`, `started_at`, `ended_at`, `elapsed_ms`), and regenerates the findings files from authenticated output. Each seat is floored at its own terminal verdict; a primary timeout is BLOCKED and a pair timeout with no findings is TIMEOUT. It seals seats that did not exit 0 in `phases.verify.executions`.
- Deleted: owner-written judge packets and launch recipes, the no-tools Windows packet route, the judge-side contract re-hash, orchestration prose in `verify.md`, pair-reason completeness, both timeout marker files, stdout-versus-findings reconciliation, the evidence CLI, and the streaming-capture classifier.
- Behavior changes: unconfigured Claude primary judges run through the CLI, not a native Agent. Grok/omp judge seats and effort-only judge profiles fail at role freeze (`BLOCKED:judge-route-unsupported:<engine>` / `unsupported-role-option`). Judges get no owner focus text; the replay tests the recall risk. The replay addendum was registered in 0225.
- Process: Astra design review R0 REVISE → spec → root counters C1–C6 (C1 synthesized, C2–C6 adopted) → root implementation → Astra verification R1 REVISE (8) → R2 (7) → R3 (7; the root cause was re-merge, fixed by one merge per round) → R4 (3) → R5 SHIP. A Claude adversarial review confirmed 12 of 15 claims, and every non-duplicate was fixed.
- Checks: self-tests of verify-judges (stub end-to-end), verify-merge-findings, judge-role-evidence, phase-prompt-render, invocation-receipt, role-config, state-phase-write, archive_run, resolve-bootstrap, collect-codex-findings and terminal-claim-check; r-weld collector contract; `scripts/lint-skills.sh` All checks passed; the packed `scripts/test-windows-portability.py` on POSIX (63 tests); `git diff --check`; `.agents`/`.claude` parity. Native Windows runs only in CI.
- Open: no saving claimed. Pre-existing and untouched: pyflakes reports an undefined `prior_results` in `state-phase-write.py` self-test code.

Carried from 0221: the `/devlyn:queue` branch-reconciliation rule is not exercised by a model-driven drain; a null `autoMergeRequest` does not prove merge-queue removal; the slim+orphan instruction add-back (0223) is an open user decision.

## Standing rules

- **No token, cost or call budgets** in the harness or in tests. Keep only the watchdog (90 min per task, 10 min per review) and post-hoc usage recording; missing usage is recorded as UNKNOWN, never 0.
- **Models.** Claude config: `claude-opus-5-5`. Codex config: `gpt-6-astra` owner with `gpt-6-sol` implementation. Light path: `claude-sonnet-5` or `gpt-6-sol`. `grok-4.7` is an optional reviewer only. Do not auto-substitute Fable 5.2+.
- **No resolve invocation** in research (0201 rule 5, the user's no-resolve instruction), except 0225's registered live confirmation runs, which the user approved on 2026-09-27. Do not rerun D1. 0185 and D1–D4 are not holdout evidence.
- **Frozen material.** A16, frozen results and the original WIP stay untouched. Past stop verdicts (0211–0219, 0224) are history, not something to regrade.
- **User-facing messages** are always in Korean, plain and short: conclusion first, then what the user must decide, then the recommendation.
