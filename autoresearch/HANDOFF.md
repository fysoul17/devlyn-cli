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
5. **Deliver as a PR.** Commit, write `.devlyn/acceptance.json` (kind `direct`), then run `python3 config/skills/_shared/task-complete.py complete --receipt <receipt> --acceptance .devlyn/acceptance.json --mode pr`. Root merges each session PR once the Astra/Grok reviews and any CI pass (user decision 2026-09-24: "세션마다 제가 merge", chosen over "user merges directly").
6. **Hand off.** In the same PR, update the table below and the "Next" line in this file with your branch name. Record the base SHA, scope, actual check results, open items and the next command. The PR URL is findable by that branch name.

## Sessions

| # | Scope (details: 0221 §5) | Packets | Status |
|---|---|---|---|
| 0 | Register 0221, packets, this HANDOFF (branch `candidate/0221-subtraction-direction`) | — | merged (PR #109) |
| 1 | Installed-product cleanup: standards frontmatter plus a move to optional-skills; reread sentence deletion; pair-plan-schema to benchmark; stop the global adaptive-thinking env injection; completion default `pr` (receipt reuse and owned auto-merge handled); fix the spec-verify-check research-gate false positive (branch `candidate/0221-s1-installed-cleanup`) | T1a, T1b (c1, c2, b3) | merged (PR #110) |
| 2 | Benchmark out of the npm package (branch `candidate/0221-s2-benchmark-unpackage`) | T1b (a1–a5) | merged (PR #111) |
| 3 | Comparison apparatus v2 without budgets; arm F = published 3.2.1, verified in-container; evaluator fixes (branch `candidate/0221-s3-apparatus-v2`, [0222](experiments/0222/DESIGN.md)) | E1 | merged (PR #112) |
| 4 | Always-loaded instruction screen, 288 short runs (branch `candidate/0221-s4-instruction-layer`, [0223](experiments/0223/RESULT.md)) | E2 | merged (PR #113) — `SLIM_REJECTED` |
| 5 | Add the `/devlyn:intent` candidate (no default change); counterexample tests (branch `candidate/0221-s5-intent-candidate`) | I1, I2 PR-A | merged (PR #114) |
| 6 | Structure screen: 0185 + D4 × {A, B′, C, F} × 2 configs, plus 4 Grok static checks (branch `candidate/0221-s6-structure-screen`, [0224](experiments/0224/RESULT.md)) | E1 apparatus | PR open — `SCREEN:B'=none;C=none` |
| 7 | Freeze, then untouched confirmation (40, plus 8 light); adopt, hold or stop per config | — | not run: no candidate continues (0224) |
| 8 | Next major: intent becomes the default and resolve/ideate become guidance-only, OR the candidate is closed | I2 PR-B, T1b (b) | **NEXT** — candidate-close branch |
| 9 | After one major: remove the stubs and any helpers left without references | I2 PR-C, I1 | pending |

**Next:** Session 8, candidate-close branch, after the Session 6 PR (branch `candidate/0221-s6-structure-screen`) is merged. The structure screen continued neither B′ nor C ([0224 RESULT](experiments/0224/RESULT.md)), so Session 7 does not run (0221 §4: no signal → close without the confirmation and light stages). Per 0221 §5 row 8 (drop branch): close the `/devlyn:intent` candidate and keep full resolve as it is; then do the research-vocabulary cleanup (T1b b1, b2, b4, b5). Do not auto-merge or publish to npm. If the user rejects the block reading, the only route is a new registration, not a regrade of 0224.

Session 6 record (base `79532e97`): B′ is bound in the 0222 apparatus, and the structure screen was registered, run and resulted as [0224](experiments/0224/DESIGN.md).
- Binding: `control.py` packs the Session 5 merge (`npm pack`, byte-reproducible, sha256 `433cb672…`) into control tree v2 (manifest `f51c73f2…`). `prepare.py` installs it like F with the shared `product_roles` (renamed from `F_roles`). `cell.identity` checks every executor and reviewer model the gate recorded, including failed calls' saved Codex header or Claude result. `record_usage` counts intent Claude reviews and names the isolated Codex review gap.
- B′ route smoke: 2/2 held every prediction (gate PASS, routed models, usage PARTIAL only for the Codex review gap).
- Registration: Astra R0 REVISE (6 items, all adopted) → R1 FREEZE; branch pushed before dispatch; `analyze.py` committed before the first verdict.
- Run: the first pass hit two shared faults. The registered Claude account's weekly limit (429) broke cells 6–16. On the bind-mounted `CODEX_HOME`, a second `codex` deleted a live process's `arg0` helpers, which broke F's worker in cells 7 and 11 (reproduced model-free). Amendment 1 (Astra A1 REVISE, both operator-script findings fixed, no re-review):
  - fixes: a tmpfs `CODEX_HOME/tmp`, and a screen stop when an assessor returns no verdict;
  - 9 cells re-dispatched and 2 re-assessed on a second Max account, with the originals kept as `*.stop-1`.
- Result `SCREEN:B'=none;C=none`: I0185 0/8 COMPLETE (every product fails the `release` replay). D4 COMPLETE: A-codex, B′ ×2, C ×2. F ended BLOCKED in all 4 cells. 0 false completions, 0 scope violations. Grok: B′ defect and repair `NONE`; both C calls timed out at 600 s. Predictions 1, 4, 6 and 7 were falsified, 2 half held, 3 and 5 held.
- Why none: the Claude config had a D4 quality signal for B′ and C. Every candidate I0185 cell, however, has a codex-assessor HIGH (Requirement 2: no restore after one lock-release failure) that the `release` replay reproduces against the final tree, so the frozen block rule stops both. The first computation had skipped that step (`SCREEN:B'=claude;C=claude`, kept as `.devlyn/0224/analysis.pre-final-review.json`), and the final Astra verification caught it. The counter-reading (a shared unmet requirement should not also block) is recorded in RESULT; changing it would need a new registration.
- Open: the Session 6 completion scratch (`.git/devlyn-completion/def536965e5b1678b8c023ac/scratch`) holds a copy of the evidence; the preserved evidence is `.devlyn/0224/`. The slim+orphan add-back decision (Session 4) is still open.

Session 5 record (base `f3b2b81`): `/devlyn:intent` is added as an explicit-only preview next to the unchanged resolve and ideate. Nothing is deleted and no default changes.
- `config/skills/devlyn:intent/SKILL.md` (7.9 KB) holds the kernel, modes and run steps. `references/review.md` is the reviewer prompt body.
- `config/skills/_shared/intent-gate.py` (~775 lines plus a 285-line self-test) is the single writer of `.devlyn/intent/` and the only path to PASS. Its commands are `start`, `scope`, `commit`, `check`, `retire`, `delegate`, `review`, `status` and `finish`. Evidence is keyed to HEAD plus the worktree tree, so any later edit or commit makes it stale. PASS writes `kind: direct` acceptance for the existing task-complete. The gate reuses role-config (roles, fail-closed), run-bounded (tree kill), judge-output-parser, judge-role-evidence (Claude result model, Codex header), spec-verify-check (expected-contract findings) and codex-monitored.sh.
- Termination: on Linux the gate is a child subreaper and reaps every descendant (affirmative); on macOS an environment-marker scan plus held-pipe detection is best-effort and disclosed as a verdict note; on Windows the job object kills the tree. A pipe still held after the reap is `termination-failed`. A watchdog 124 is distinct from a natural exit 124.
- A pair TIMEOUT leaves a disclosed primary-only PASS; a primary TIMEOUT blocks. Effort requested without a resolvable model fails closed at `start` (`unsupported-role-option`). Claude workers under a Codex owner are refused (`unsupported-delegation`).
- Installer A1 adds intent to every root; lint A2 adds critical paths, the 5a literal and the gate self-test; CI A3 makes the Windows smoke assert `devlynintent`; README A4 adds one line. PR-A stays unreleased (I2 Q9).
- Checks: gate self-test PASS locally and inside `devlyn-0222` (Linux `/proc` path); lint `All checks passed`; installer smoke in four roots (intent next to resolve, Codex stamp absolute); npm pack contains the three intent files; offline install of the packed tarball in the image for both `-y` and `agents codex` (`.devlyn/0221/s5-design/image/`).
- Reviews: Astra design R0 REVISE (9 items) was adopted before implementation. Named deltas: evidence is bound to the commit (commit before checks/review); decisive attempts use the latest run; pure-design is exempt; expected-file/pattern/dependency rules are enforced through spec-verify-check; termination is affirmative; delegation is authenticated on model and effort; prospective allocation and `--receipt` delivery are in the SKILL; the verify-only dirty exemption is kept; the Windows sibling alias is named; probes can be retired; K20 pair-timeout is preserved. Final verification R1 REVISE (10 defects, all fixed):
  - evidence bytes are rehashed at evaluation;
  - duplicate required commands keep every expectation, and retired checks no longer count as the required check;
  - Linux uses a child subreaper, so hidden descendants are reaped; macOS discloses best-effort termination;
  - the executor must have made every owned path;
  - a binding finding sticks across retries on the same source;
  - `--no-pair` is honored with OTHER available;
  - verify-only needs no executor;
  - Claude effort is bound by the dispatched argv;
  - the Codex header workdir/sandbox and ignored-option diagnostics are checked;
  - commit refuses foreign staged files.
  R2 REVISE (3, all fixed): owned paths must carry the executor-produced blob, binding findings stick by content tree (empty commits cannot erase them), and the Codex sandbox is compared by mode (native `workspace-write [workdir, …]`). R3 REVISE (2, fixed): executor provenance binds git mode + object, and only findings from source-stable reviews stick. R4 SHIP (16 extra read-only probes pass).
- Open: the gate's Windows termination rests on the job-object kill (no marker scan) and its self-test is POSIX-only in CI. The Grok reviewer engine is refused by the gate (`unsupported-review-engine`), because the gate authenticates only Claude and Codex. There is no live model smoke; Session 6 is the first model run of B′.

Session 4 record (base `9684dc6`): [0223](experiments/0223/DESIGN.md) makes the drift probe isolated for both engines. Claude runs through the sealed claude-isolation.py, and Codex gets a fresh CODEX_HOME, `env -i` and a render check. Both use pinned CLI snapshots (`~/.local/share/nx01/pins/{claude-2.1.282,codex-0.156.1}-0223`); their sha256 is recorded per run and required by the adjudicator. Timeouts are scored, infra gets at most two attempts, and verdicts are written atomically. The matrix driver gains `--instructions`/`--probes`.
- Result: 288/288 scored, 0 infra, frozen token `SLIM_REJECTED:claude-sonnet-5,gpt-6-astra`. Both regressions are B5; every failure leaves the self-orphaned helper and import. The leading hypothesis is the dropped "orphans YOUR change created → clean them up" sentence, which is untested until an add-back run. EQ3 shows no regression; slim cuts median input tokens by 14–51%.
- Consequence: Session 8 has no measured instruction candidate, so the current text stays. A slim+orphan add-back candidate needs its own registration (open user decision; see RESULT.md "Follow-up").
- Checks: adjudicator self-test, fake-engine plumbing, lint and test-seat-matrix pass; the smoke passed (18 runs: 12 B4 plus 6 canary).
- Reviews: R1 REVISE from Astra and Grok (5 defects, all fixed); R2 SMOKE-READY from both.
- Open: the Session 3 scratch (`clean-scratch --receipt .git/devlyn-completion/31acb01f544054541f034b19/receipt.json --writers-stopped`) is still BLOCKED because the Docker Desktop VM holds file handles; its credential snapshots are already deleted. `.devlyn/0222/` keeps the Session 3 evidence.

Session 3 record (base `b8c1073`): [0222](experiments/0222/DESIGN.md) replaces the 0210–0220 wrapper chain with one directory:
- a pinned image (Codex 0.156.1, Claude 2.1.281, less, login PATH fixed), a tracked `/control` build with a sha256 manifest, route-driven prepare (arms A, C and F; B′ binds its package in Session 5), a hang-wall-only owner run, post-hoc usage (never 0), and an in-image evaluator
- I0185 wired as exposed regression: heldout plus four promoted replays; NOT_TRIGGERED → ADJUDICATE
- dual blinded assessors and a serial `screen.sh`; the stop rules are in DESIGN.md
- F = published devlyn-cli@3.2.1 installed offline and bound through `.devlyn/engines.json`, with Claude judges model-only because 3.2.1's effort table would block `high`

The Session 6 structure-screen shape is frozen: {I0185, D4} × {A, B′, C, F} × {claude, codex}.

Checks:
- 30 unit tests, including container cases
- calibration: P2 115/115 over 5 repeats; P3 23/23 after fixes, with one disclosed P1 miss (the 0207 D3 reference is not Prettier-clean)
- route smoke across all six routes, with clean teardown and routed identities; it stopped once on a real apparatus defect (identity: an un-normalized `[1m]` model suffix), which was fixed and re-run. In the same cell a missing Codex models cache produced a product BLOCKED, so the host cache is now seeded into every cell. The route smoke shows the routes work; it is not product-completion evidence (11 of 12 assessments were not complete because the smoke request carries an unverifiable process instruction) ([SMOKE.md](experiments/0222/SMOKE.md))

Reviews: Astra design R0 REVISE, adopted; implementation R1–R4 REVISE from Astra and Grok, all fixed; R5 SMOKE-READY from both.

Open (carried from Session 1): the `/devlyn:queue` branch-reconciliation rule is not exercised by a model-driven drain; ideate/resolve prose still mentions solo-headroom checks that spec-verify-check no longer enforces (T1b b1/b2/b4, Session 8); a null `autoMergeRequest` does not prove merge-queue removal.

## Standing rules

- **No token, cost or call budgets** in the harness or in tests. Keep only the watchdog (90 min per task, 10 min per review) and post-hoc usage recording; missing usage is recorded as UNKNOWN, never 0.
- **Models.** Claude config: `claude-opus-5-5`. Codex config: `gpt-6-astra` owner with `gpt-6-sol` implementation. Light path: `claude-sonnet-5` or `gpt-6-sol`. `grok-4.7` is an optional reviewer only. Do not auto-substitute Fable 5.2+.
- **No resolve invocation** except as arm F. Do not rerun D1. 0185 and D1–D4 are not holdout evidence.
- **Checkpoints.** Every 2 business days, decide whether to continue, shrink or stop the current path.
- **Frozen material.** A16, frozen results and the original WIP stay untouched. Past stop verdicts (0211–0219) are history, not something to regrade.
- **Open user item.** The only one left is old-name handling: an executing alias vs guidance-only. The default is guidance-only (0221 §8).
