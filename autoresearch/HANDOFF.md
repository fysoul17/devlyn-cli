# 0230 bundle development — steps 2–5 merged and the whole-bundle review fixed on `bundle/0225-steps-2-5`; next: live-comparison registration

2026-10-03 KST. Owner direction: resume bundle development with a thorough Astra ultra review at the end. The record is [0230](iterations/0230-bundle-steps-3-5.md) (converged design, owner decisions U1–U4 and R1–R4, PR-3 to PR-5 results, the whole-bundle review). On the bundle branch (never main):
- PR #157: port of the 0229 candidate onto 4.1.0.
- PR #158: step-2 follow-up — omp judge auto-assign, grok diagnostic, global Bash-max guidance.
- PR #159: step 3 — one sealed MECHANICAL gate inside VERIFY. Astra v4 SHIP.
- PR #161: step 4 — scripts take over the owner state writes except the small-surface probe demotion; `final_report complete` derives supported verdicts, requires a supplied halt reason where it cannot derive one, and renders the report. Astra v3 SHIP; merged `ea14d7fe`.
- PR #163: step 5 — contract-first PLAN, rendered worker prompts, U4 probes, defect-4 witnesses. Astra v3 SHIP; merged `ac90bb0c`.
- PR #164: whole-bundle review fixes. Astra v6 SHIP; owner decisions R1–R4 (2026-10-04); merged `f71a17d3`.

Next: a live-comparison registration for the bundle. Running it needs the owner's approval for resolve. The seven-lens Claude review of the rounds after `f1c06224` can run once the Claude weekly limit resets (2026-10-10 08:00 KST). Deferred follow-ups are in the 0230 record's "Honest limits". Nothing ships. Working notes are in `.devlyn/bundle/`.

The 0229 handoff follows unchanged.


2026-10-01 KST. Root direct, no resolve. The contract is [0229](iterations/0229-verify-existing-behavior-rescreen.md), which amends [0228](iterations/0228-verify-rubric-rescreen.md) (itself amending [0227](iterations/0227-verify-rescreen.md)) by reference; registered with Astra (gpt-6-astra, ultra) before the H commit and any call. The raw record is `.devlyn/0229/` and `.devlyn/0228/`. 0228 closed at R2 FAIL (Addendum C3, [DIAGNOSIS](experiments/0228/diagnosis/DIAGNOSIS.md)); the owner chose to fix and re-screen (2026-10-01). 0227 closed NOT PASS ([RESULT](experiments/0227/RESULT.md), [DIAGNOSIS](experiments/0227/diagnosis/DIAGNOSIS.md)); its handoff is in git history (last version at `f3835c04`). User decision 2026-09-30 ("1"): fix the rubric where the diagnosis points, test by replay on 0227 material, then re-screen on fresh tasks.

## Start here (every new session)

1. **Confirm the previous PR is merged, then start from updated `main`** (checkout `~/.local/share/nx01/core-continuation-20260912`):
   - `gh pr list --repo fysoul17/devlyn-cli --state all --head <previous branch> --json number,state,mergedAt,url` must show `MERGED`; otherwise stop and report.
   - `git status --porcelain` must be empty apart from files you can prove you own; then `git switch main && git pull --ff-only origin main`.
2. **Read 0229** end to end (and 0228 and 0227, which it amends by reference), then the step's row below.
3. **Allocate a task branch:** `python3 config/skills/_shared/task-complete.py allocate --repo . --task '<id>' --branch 'candidate/<id>' --worktree '<absent path>' --repository fysoul17/devlyn-cli --remote origin --base main`.
4. **Work and verify.** Root works directly. Astra reviews read-only and isolated (`CODEX_MONITORED_ISOLATED=1 DEVLYN_CODEX_PROMPT_FILE=<prompt> config/skills/_shared/codex-monitored.sh -C <repo> -s read-only -m gpt-6-astra -c model_reasoning_effort=ultra -`, stdout to a file, never a pipe; wait on `^\[codex-monitored\] codex exited` in stderr) until SHIP. `gpt-6-sol` implements where 0227 says so (`-s workspace-write`; it cannot write `.agents/`).
5. **Deliver as a PR.** Commit in the task worktree, write `<worktree>/.devlyn/acceptance.json` (kind `direct`), then from a cwd outside the checkout `task-complete.py complete --receipt <receipt> --acceptance <file> --mode pr --writers-stopped`. Root merges research PRs once Astra verification is SHIP and CI is green where it runs, with `--mode auto --writers-stopped`. H is a pushed branch with no PR, not merged during 0229.
6. **Hand off** in the same PR: update the table below.

**Replays and the screen (steps 4–5) are finished.** Judges ran as `_devlynjudge` (0228 Addendum C2, 0229 D2), and nothing changed outside `/Users/Shared/devlyn-vr-0227*` and `/Users/Shared/devlyn-vr-0228-dev`.

**Judge cleanup (2026-10-02, done and reported by the devlyn-os-v1 session):**
- That session's search of HOME, `/Users/Shared`, `/private/tmp` and `/private/var/folders` found no copy of the token. The token file and `~/.config/devlyn-vr` were then deleted.
- Also removed: the sudoers rule, the `_devlynjudge` group, `/private/tmp/claude-450` and `cc-socks-450`, and every uid-450 process.
- **Still present:** the `_devlynjudge` user record: UniqueID 450, shell `/usr/bin/false`, home `/var/empty`. As the devlyn-os-v1 session reported, macOS refused its deletion without Full Disk Access (TCC). Root checked on 2026-10-02: no uid-450 process, the `_devlynjudge` group record is gone, and `/etc/sudoers.d` holds no rule. Removing the user record is the user's call.
- **Raw outputs** of the replays and the screen remain in `/Users/Shared/devlyn-vr-0228-dev` (owner-only, mode 0700, including files the judge owns) until the user decides.

## Steps (0229 "Work order")

| # | Scope | Status |
|---|---|---|
| 1 | Diagnosis and registration: Astra FREEZE, PR, merge | merged (PR #149) |
| 2 | H on G (`candidate/0229-fix`, pushed, no PR), runner change, Astra SHIP each; Addendum D1 | done: H = `3afbb18e`, runner `17c8b7b8`, D1 |
| 3 | **Owner approval** of 0229 — nothing runs before it | approved 2026-10-01 23:44 (relayed by devlyn-os-v1) |
| 4 | R1 (stage H, product, stub 64/64, inventory, open check, probe, owner compare), R2, R3 with Astra reviews and the owner's compares | **PASS** (0229 "Gate results"): R2 H 40/40 clean vs F 5/16 blocked; R3 72/72 twin hits, 28/28 references clean, 0 demotions |
| 5 | Corpus, screen driver D2 (judge account), screen, scoring, RESULT | **PASS** ([RESULT](experiments/0229/RESULT.md)): 32/32 hits, 0 false alarms, 0 unsupported extras, 0 invalid references, 128/128 seats accepted, no dispute after Astra's audit |

0228 in one line: under G, the correct J4 reference was blocked in 1 of 40 replays (a Codex primary binding the base's own eviction deferral as a violation of "the existing … behavior"), F in 4 of 16; R3 not run. Isolation by the judge account held (owner compare changed 0; both tokens absent from all files).

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
