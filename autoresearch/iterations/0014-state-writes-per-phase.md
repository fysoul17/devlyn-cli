# 0014 — State-writes-per-phase observability + archive script path

**Status**: SHIPPED
**Started**: 2026-04-27
**Decided**: 2026-04-27 (same-day, single empirical verification run)

## Hypothesis

iter-0013 surfaced two bugs:

1. **State-writes-per-phase contract drift.** `references/pipeline-state.md:165-171` requires per-phase `phases.<name>.{started_at, round, triggered_by}` writes at phase start (orchestrator) and `{verdict, completed_at, duration_ms, artifacts}` at phase end (phase agent). Empirically, F1 successful runs populate only `phases.evaluate`. `build`, `build_gate`, `browser_validate`, `critic`, `docs`, `final_report` are missing.
2. **Archive script path bug** (Codex iter-0014 R0 finding #6). `SKILL.md:216`/`:229` invoked `python3 scripts/archive_run.py` and `python3 scripts/terminal_verdict.py`. Work_dir at `/tmp/bench-...` has NO root-level `scripts/` directory; the scripts live at `.claude/skills/devlyn:auto-resolve/scripts/{archive_run.py, terminal_verdict.py}`. Silent failure: orchestrator runs the archive command, gets "No such file or directory", proceeds without archiving. Knock-on: artifacts pile up in `.devlyn/`, never moved to `.devlyn/runs/<run_id>/`.

iter-0014 closes both with prompt-side guidance + path corrections. No code mechanism change.

## Mechanism

Why-chain (extending iter-0013 at #64):

65. Why does the contract get ignored despite being documented? → `pipeline-state.md` is a reference; it's not where the orchestrator's running attention lives during phases. SKILL.md's PHASE sections (lines 88-180) jump straight from spawn → criteria check → diff stat → commit, with no state-write step. The contract is too far from the action site.
66. Why isn't strengthening only the phase prompt body sufficient? → Codex iter-0014 R0 #3: `build-gate.md:122-128` already explicitly requires the four end-fields and the orchestrator still skipped the write on a clean F1 run. Prompt-body output contracts alone proved insufficient empirically. The orchestrator (not the phase agent) owns `started_at`; relying on the phase agent to write all four is a single-point-of-failure design.
67. Why D4-lite (universal block + per-phase reminders + targeted prompt-body fixes)? → Defense in depth: universal block establishes the contract, per-phase reminders keep salience at the action site, prompt-body strengthening covers the case where the agent (not orchestrator) is the only writer. Codex iter-0014 R0 explicitly recommended this combination.
68. Why the archive script path bug? → SKILL.md's relative `scripts/archive_run.py` was correct when the orchestrator ran from repo root. In benchmark fixtures, the orchestrator runs from a fresh `WORK_DIR` (`/tmp/bench-...`) where no `scripts/` exists. The skill files themselves (with the scripts subdir) ARE staged into the work_dir at `.claude/skills/devlyn:auto-resolve/scripts/`. Use that absolute-from-work-dir path. Same fix for `terminal_verdict.py`.
69. Root: the orchestrator's contract for phase observability and archive must be expressed at SKILL.md PHASE-section salience, not just in references; and script paths must be relative to the work_dir (where the skill mirror lives), not the repo root.

## Predicted change

Static + 1 empirical falsification:

- **Lint Check 6 (mirror parity) PASSES** after surgical sync.
- **Empirical run on F1 variant**: `state.phases.{build, build_gate, evaluate, final_report}` ALL have `started_at`, `completed_at`, numeric `duration_ms`, non-null `verdict`. Archive moved artifacts from `.devlyn/` to `.devlyn/runs/<run_id>/`.
- **No regression**: F1 variant still completes within budget (900s post iter-0013); same `verify_score=0.8`.

## Diff plan

Five edits across four files. No new files, no new abstractions.

1. **`SKILL.md`** — Add `<state_write_protocol>` block between `<perf_opt_in>` and `## PHASE 0`. Universal contract: orchestrator writes started_at before spawn; orchestrator validates completed_at populated after agent returns; phases listed (`build, build_gate, browser_validate, evaluate, critic, docs, final_report`); rationale (prompt-body alone proved insufficient; archive prune-safety depends on `final_report.verdict`).
2. **`SKILL.md`** — Per-phase one-line reminder ("State write (per `<state_write_protocol>`): write `phases.<name>.started_at` before spawn; after agent returns, validate `phases.<name>.{verdict, completed_at, duration_ms, artifacts}` populated and write any missing fields before branching.") inserted in PHASE 1 BUILD, 1.4 BUILD GATE, 1.5 BROWSER VALIDATE, 2 EVALUATE, 3 CRITIC, 4 DOCS. PHASE 5 FINAL REPORT gets a more detailed write directive (started_at at top, verdict/completed_at/duration_ms before archive).
3. **`SKILL.md` PHASE 5** — Fix script paths: `python3 scripts/terminal_verdict.py` → `python3 .claude/skills/devlyn:auto-resolve/scripts/terminal_verdict.py`; same for `archive_run.py`.
4. **`references/phases/phase-1-build.md`** output_contract — add explicit final state.json write line listing all required fields.
5. **`references/phases/phase-2-evaluate.md`** output_contract:26 — strengthen vague "timing" to explicit `started_at/completed_at/duration_ms` + explicit artifact paths.
6. **`references/phases/phase-3-critic.md`** output_contract:75 — add explicit timestamps + artifact paths + sub_verdicts list.

NOT in this diff:

- **Per-phase ENGINE auto-detection on path resolution.** Some teams may run auto-resolve from repo root in production; the new path is work_dir-relative. If that becomes a regression, a future iter could try `command -v python3 + repo-detect`. Not pressing.
- **PARSE phase observability.** `phases.parse` isn't in the contract (Phase 0 creates state.json with empty phases per `pipeline-state.md:167`). Skipped.
- **Hooks for state-write telemetry.** Codex iter-0013 R0 mentioned this as an alternative; the prompt-tightening approach is cheaper and matches the orchestrator-driven design.

## Falsification gate result (2026-04-27)

All gates passed.

### Static gate

`bash scripts/lint-skills.sh` — all 10 checks pass after mirror sync.

### Empirical run (F1 variant, RUN_ID=iter0014-verify-20260427T092859Z)

Result.json:
- `elapsed_seconds: 610`, `timed_out: false`, `invoke_exit: 0`, `verify_score: 0.8`.

state.phases keys: `['build', 'build_gate', 'evaluate', 'final_report']` (was `['evaluate']` only on iter-0013 run).

Per-phase fields populated:

| Phase | verdict | started_at | completed_at | duration_ms | engine | artifacts |
|---|---|---|---|---|---|---|
| `build` | PASS | 2026-04-27T09:29:50Z | 2026-04-27T09:33:22Z | 212000 | codex | {} |
| `build_gate` | PASS | 2026-04-27T09:34:30Z | 2026-04-27T09:34:35Z | 5000 | bash | {findings_file, log_file} |
| `evaluate` | PASS | 2026-04-27T09:34:40Z | 2026-04-27T09:35:30Z | 50000 | claude | {findings_file, log_file} |
| `final_report` | PASS | 2026-04-27T09:35:45Z | 2026-04-27T09:35:50Z | 5000 | bash | {} |

Archive ran: `/tmp/bench-.../iter0014-verify-…/.devlyn/runs/ar-20260427T092945Z-f221066a9098/` exists with all per-run artifacts. `.devlyn/` root no longer holds them.

## Codex collaboration (CLI, not MCP)

Per user direction: codex CLI / GPT-5.5 only.

R0 (pre-edit design review): I presented evidence + 4 design options (D1-D4) + 5 questions. Codex verdict, applied:

1. **D1 alone insufficient** — top-level guidance gets glossed over by orchestrator at per-phase action sites.
2. **D2 alone also insufficient** — `build-gate.md` already had explicit prompt-body output contract and orchestrator still skipped the write empirically. Proves prompt-body guidance is not enough.
3. **Use D4-lite shape**: universal block + per-phase salience reminders + targeted prompt-body fixes. Defense in depth.
4. **Pushback on knock-on bug claim**: I'd claimed `final_report.verdict == null` explained the missing archive. Codex went and READ `archive_run.py`: the script moves artifacts **unconditionally**; verdict only gates **pruning of old archives**. The artifact-staying-in-.devlyn issue must be a different bug — Codex grep'd and found: SKILL.md's `python3 scripts/archive_run.py` path doesn't resolve in the work_dir context. This was a separate, real bug iter-0014 also fixes.
5. **Verification approach** — true dry-run not available (orchestrator is prompt-driven). One canary run with assertions on phase-keys + archive directory + non-null verdicts.

## Lessons

- **References are docs; SKILL.md PHASE sections are scripts.** Contracts that live only in references (here, `pipeline-state.md:168`) get ignored by the orchestrator at action time. Salience matters: contracts must surface where the orchestrator's attention is during execution.
- **Prompt-body output contracts are not enough alone.** `build-gate.md:122-128` was explicit about all four state fields and still got skipped. Defense in depth: orchestrator validates after the agent.
- **Script paths must be relative to where they're invoked from.** SKILL.md ran `scripts/archive_run.py`, but the orchestrator runs from work_dir, not repo root. The skill mirror at `.claude/skills/<skill>/scripts/...` is the right anchor in that context. Same lesson generalizes: any script invocation in a SKILL.md must be addressable from the user's expected CWD.
- **Codex pushback on my own claims continues to earn its keep.** I'd connected the missing-archive symptom to the missing-final_report.verdict cause via the prune-safety rule. Codex read the actual archive_run.py and refuted the link in 30s. The real cause was simpler (broken path) and would have been missed by my edit if Codex hadn't grep'd.
- **Empirical verification is non-optional for prompt-driven changes.** Static lint passes don't prove orchestrator behavior changed. One ~$2 / 10-min canary run is the cheapest discriminator and covers both bugs at once.
