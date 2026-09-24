# Continue 0221 — subtraction and `/devlyn:intent` full-replacement evaluation

2026-09-24 KST. Root direct. The contract is [0221](iterations/0221-subtraction-direction.md). It is registered, and the user's decisions are quoted verbatim in §2. Session-ready scoping lives in [experiments/0221/packets](experiments/0221/packets/README.md). The previous HANDOFF (0201–0209 narrative) is in git history; 0201's diagnosis still stands, but 0221 §7 lists which of its rules are superseded.

## Start here (every new session)

1. **Confirm the previous session's PR is merged, then start from updated `main`.** Each session's branch is recorded in the table below; Session 0's branch is `candidate/0221-subtraction-direction`. In this checkout (`~/.local/share/nx01/core-continuation-20260912`):
   - `gh pr list --repo fysoul17/devlyn-cli --state all --head <previous branch> --json number,state,mergedAt,url` must show `MERGED`. If it does not, stop and report; do not stack a dependent branch on an unmerged one.
   - `git status --porcelain` must be empty, apart from files you can prove you own. Then run `git switch main && git pull --ff-only origin main`, and confirm `git log -1` contains that PR's merge.
2. **Read the contract and the packets.** Read 0221 §3–§6, then the packet(s) that the table below names for the next session. Apply every packet's **verifier section**, and re-check each file:line against your base SHA before editing.
3. **Allocate a task branch** (from `main`, in this checkout):
   `python3 config/skills/_shared/task-complete.py allocate --repo . --task '<id>' --branch 'candidate/<id>' --repository fysoul17/devlyn-cli --remote origin --base main`
4. **Do the work and the checks.** Run the packet's acceptance checks. For a consequential change, get one read-only Astra review: `gpt-6-astra`, isolated, via `config/skills/_shared/codex-monitored.sh`. Add further review rounds only when an unresolved counterexample remains; root decides.
5. **Deliver as a PR only.** Commit, write `.devlyn/acceptance.json` (kind `direct`), then run `python3 config/skills/_shared/task-complete.py complete --receipt <receipt> --acceptance .devlyn/acceptance.json --mode pr`. **Never merge**; the user merges.
6. **Hand off.** In the same PR, update the table below and the "Next" line in this file with your branch name. Record the base SHA, scope, actual check results, open items and the next command. The PR URL is findable by that branch name.

## Sessions

| # | Scope (details: 0221 §5) | Packets | Status |
|---|---|---|---|
| 0 | Register 0221, packets, this HANDOFF (branch `candidate/0221-subtraction-direction`) | — | merged (PR #109) |
| 1 | Installed-product cleanup: standards frontmatter plus a move to optional-skills; reread sentence deletion; pair-plan-schema to benchmark; stop the global adaptive-thinking env injection; completion default `pr` (receipt reuse and owned auto-merge handled); fix the spec-verify-check research-gate false positive (branch `candidate/0221-s1-installed-cleanup`) | T1a, T1b (c1, c2, b3) | PR open |
| 2 | Benchmark out of the npm package | T1b (a1–a5) | **NEXT** |
| 3 | Comparison apparatus v2 without budgets; arm F = published 3.2.1, verified in-container; evaluator fixes | E1 | pending |
| 4 | Always-loaded instruction screen, 288 short runs; slim frozen as a candidate | E2 | pending |
| 5 | Add the `/devlyn:intent` candidate (no default change); counterexample tests | I1, I2 PR-A | pending |
| 6 | Structure screen: 0185 + D4 × {A, B′, C, F} × 2 configs, plus 4 Grok static checks | E1 apparatus | pending |
| 7 | Freeze, then untouched confirmation (40, plus 8 light); adopt, hold or stop per config | — | pending |
| 8 | Next major: intent becomes the default and resolve/ideate become guidance-only, OR the candidate is closed | I2 PR-B, T1b (b) | pending |
| 9 | After one major: remove the stubs and any helpers left without references | I2 PR-C, I1 | pending |

**Next:** Session 2, after the Session 1 PR (branch `candidate/0221-s1-installed-cleanup`) is merged.

Session 1 record (base `0f9f581`): T1a (a)–(d) and T1b c1, c2, b3 applied, plus the lint pins b3 needed and the `.agents` mirror. Net −1.9k lines. Checks: `bash scripts/lint-skills.sh` rc=0; `task-complete.py --self-test` 38/38 (new: absent policy → PR with no merge request; `--mode pr` cancels an owned auto-merge request and leaves a foreign PR untouched; mutation-checked); `spec-verify-check.py`, `verify-merge-findings.py`, `resolve-bootstrap.py` self-tests, `test-owner-phases.py`, fixture lints and `test-windows-portability.py` (61 OK, Node 20 locally) pass; npm pack and temp-HOME installer smokes (default excludes standards, upgrade removes old copies, opt-in installs them, global env keeps an existing adaptive-thinking value and never adds it). Added after Astra and Grok review: `/devlyn:queue` reads terminal `[x]`/`[F]` transitions held on retained owned branches (receipt `branch`, `git show`), and drains allocate every item with `--worktree` so the anchor stays on base, because under the PR default base no longer advances (already true for `[F]` items). Reviews: Astra SHIP; Grok REVISE (queue wording), fixed and re-checked. Open: that queue rule is not exercised by a model-driven drain; ideate/resolve prose still mentions solo-headroom checks that spec-verify-check no longer enforces (T1b b1/b2/b4, Session 8 per 0221 §5); `null autoMergeRequest` does not prove merge-queue removal.

## Standing rules

- **No token, cost or call budgets** in the harness or in tests. Keep only the watchdog (90 min per task, 10 min per review) and post-hoc usage recording; missing usage is recorded as UNKNOWN, never 0.
- **Models.** Claude config: `claude-opus-5-5`. Codex config: `gpt-6-astra` owner with `gpt-6-sol` implementation. Light path: `claude-sonnet-5` or `gpt-6-sol`. `grok-4.7` is an optional reviewer only. Do not auto-substitute Fable 5.2+.
- **No resolve invocation** except as arm F. Do not rerun D1. 0185 and D1–D4 are not holdout evidence.
- **Checkpoints.** Every 2 business days, decide whether to continue, shrink or stop the current path.
- **Frozen material.** A16, frozen results and the original WIP stay untouched. Past stop verdicts (0211–0219) are history, not something to regrade.
- **Open user item.** The only one left is old-name handling: an executing alias vs guidance-only. The default is guidance-only (0221 §8).
