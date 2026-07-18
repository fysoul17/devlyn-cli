# nodeg-20260718d ship adjudication — R0 (independent position requested)

You are one of three seats (Fable orchestrator, Codex sol, Grok 4.5) adjudicating the iter-0072 v6 ship gate. Read receipts directly at /Users/aipalm/Documents/GitHub/devlyn-cli — verify every claim below yourself.

## Frozen contract
Registration v6 + graduation ladder: `autoresearch/iterations/0072-changed-surface-closure.md:760-969`; ship step = "ONE fresh nodeg diagnostic row under the UNCHANGED all-checks gate" (v5 precedent 0072.13: ALL checks → no-ship; the v5 row was killed on a genuine carrier FAIL, check 7).

## Row receipts (nodeg-20260718d, F7, CLI pin 2.1.211, sonnet orchestrator / terra executor / SC=claude)
- Gate readout (orchestrator ran `f7-carrier-gate.py <ws> --v5 --post-implement` on the surviving worktree copy): **9/11 PASS** — PASS: 1, 3v5, 5, 6, 12, **13 attribution (pre-SC patch has BOTH carriers absent)**, **7 USAGE version row**, **8 unsupported-format exit-1 test**, 9 bait. FAIL: 11, 10.
- SC evidence (archived, `/tmp/nodeg-20260718d/f7-live/devlyn.snapshot/runs/rs-20260718T000000Z-a1b2c3d4e5f6/`): `surface-close.stdout` = `UVR-STALE: FIRED bin/cli.js:12 — <evidence>` + `PATH-TEST: FIRED tests/cli.test.js:33 — <evidence>` + `PASS`; state `phases.surface_close`: engine=claude, round 0, 189.6s, verdict PASS, input/prompt sha recorded; worker session JSONL archived. Row repo commits: implement → surface-close, harness files untracked only. Live worktree: `~/.local/share/nx01/w/r19d8684a2e44/ff10888c89791/A1/repo`.
- First live dual-carrier closure in six registrations; Amendment-4 tailed-FIRED shape exercised (pre-Am4 grammar would have BLOCKED this correct run).
- nodeg 3-bar: objective PASS (sealed oracle: `A1/objective.json` oracle_exit=0, tests 1/1, hidden 0, neutralized workspace); quality FAIL under frozen both-judges rule BUT seat-split is NEW — sonnet judge A_win on 3/4 axes +1 tie, codex judge B_win 3/4 +1 tie (prior cohorts: bare blind-preferred across the board); wall 37.4× (2509s vs frozen-B 67s; cap 3.0; wall axis excluded from 0072 scope per 0072.0, owned by 0071's problem statement).

## The two FAILed checks — orchestrator's investigation (verify it)
- **Check 11 (goal.raw.txt exact+hash)**: 673 vs 674 bytes — PHASE-0 persisted the goal WITHOUT the source task.txt's trailing newline (diff shows only "\ No newline at end of file"); state goal_sha256 matches the persisted 673-byte file. Real mechanical-contract deviation by the SONNET ORCHESTRATOR at PHASE 0 (SKILL.md: persist exact bytes), zero semantic loss (both carriers fired citing goal clauses). Not attributable to the v6 mechanism.
- **Check 10 (oracle + node --test in-place)**: sealed objective instrument PASSED (neutralized workspace). The gate's in-place rerun fails for two instrument-context reasons the orchestrator reproduced: (a) post-run worktree contains harness residue (.devlyn/, AGENTS.md, CLAUDE.md untracked) that the sealed instrument's neutralizer strips — oracle flags them out-of-scope; (b) the gate's hardcoded PATH resolves /opt/homebrew/bin/node v25.4.0 while the harness runs nvm v20.19.0 — `node --test tests/` passes 8/8 on v20, fails on v25 (both reproduced in the original worktree). Not attributable to the row's code (sealed oracle 1/1).

## Question to adjudicate (position-stating; convergence is the stop)
Under the frozen "unchanged all-checks gate" letter the row reads 9/11 → no-ship. Under check-semantics both FAILs are non-mechanism-attributable (one PHASE-0 orchestrator fidelity defect with zero information loss; one gate-instrument context artifact contradicted by the sealed instrument). Decide:
A) SHIP — v6 stays in the skill; record check-11 defect + follow-ups (goal-file byte-copy enforcement; gate check-10 post-archive semantics; engine-session-log coupling — orchestrator observed model_effective null despite archived session files).
B) NO-SHIP — revert v6 from the skill trees, fix check-11 root cause + gate instrument, run ONE more fresh row.
C) Another disposition you argue for.

State: strongest counter to YOUR position, strongest form of it, synthesis with a NAMED decisive criterion, and your falsifier. The kill-discipline concern (post-hoc gate softening = the exact behavior our falsification record forbids) must be addressed head-on, not waved off. Also state whether the check-11 defect and check-10 instrument gap each REQUIRE a fix commit regardless of A/B.
