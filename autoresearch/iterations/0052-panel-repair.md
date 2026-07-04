# iter-0052 — probe panel repair (codex column)

**Status**: SHIPPED. Both defects recorded in `0046-mechanical-drift-gates.md`
("Bugs caught" #2/#3) and reiterated in `0048-human-language-robustness.md`'s
ranked next-classes list (#4/#7) are closed. `codex-small` is restored to a
trustworthy pass/fail instrument; codex/omp compliance cells now test the
repo under test instead of a stale global skill install.

## Defect evidence (read before this iteration, not re-derived)

1. **`codex-small` env-limited, not a compliance signal.** `benchmark/auto-resolve/fixtures/test-repo/tests/server.test.js`
   (shared base fixture, reused by every compliance cell regardless of task)
   calls `server.listen(0)` — a real TCP bind. codex's `workspace-write`
   sandbox denies it with `EPERM`. `0046`'s clean `git worktree`-at-HEAD A/B
   pair (`iter0046-baseline-head` / `-with-diff`) proved this fires
   identically with and without that iteration's own diff — a pre-existing
   fixture/sandbox incompatibility, not a code regression. Neither F1
   (`--loud` flag) nor F2 (`doctor` subcommand) task text mentions
   networking; the failing test is present in every cell's work dir purely
   because it ships with the shared `test-repo` baseline every fixture
   copies.
2. **`run-compliance-cell.sh`'s codex branch never refreshed skills.**
   Unlike the `claude` branch (`cp -R $REPO_ROOT/.claude/skills` into
   `WORK_DIR` every run), the `codex`/`omp` branches invoke `codex exec` /
   `omp -p` directly — these CLIs load skills from a **user-global**
   directory regardless of `cwd`, so a `WORK_DIR` copy is never seen. `0046`
   root-caused a false regression this way: one real `codex exec` transcript
   resolved `_shared/spec-verify-check.py` from `~/.agents/skills/` while
   `bin/devlyn.js`'s `CLI_TARGETS.codex.skillsDir` documents `~/.codex/skills/`
   as codex's location — the two directories were out of sync on that
   machine (`~/.codex/skills/` missing a file `~/.agents/skills/` had), and
   which one codex actually honors was left as an open, unresolved question.

## Fix design

### 1 — scaffold: remove the one unrelated failing test

`benchmark/probes/scripts/run-compliance-cell.sh`, right after the
`test-repo` copy and before the CLI branch:

```bash
rm -f "$WORK_DIR/tests/server.test.js"
```

One line, applied identically for all three CLIs (placed before the
`case "$CLI"` branch), so `node --test tests/` (the `package.json` `test`
script) can no longer discover any file that performs a network bind —
structurally impossible, not merely less likely, since the only such file
in the fixture is deleted from the copy before anything runs. `server/`,
`web/`, `playwright.config.js` are left in place (untouched, not imported by
anything `npm test` runs) — deleting only the file that caused the measured
defect is the smallest change that closes it; the base `test-repo` fixture
itself is untouched (its own `README.md` states "No fixture modifies this
source tree" — this iteration's surface is `benchmark/probes/**` only, so
the shared fixture stays exactly as every other benchmark that reuses it
expects).

### 2 — runner: sync current repo skills to wherever codex/omp actually read

New `sync_global_skills(dest_root)` in `run-compliance-cell.sh`, called
before the codex/omp branch invocation. Mirrors
`run-full-pipeline-pair-candidate.sh`'s existing `mirror_skills()` (source
`$REPO_ROOT/config/skills`, atomic staging-dir-then-move per skill,
same non-skill workspace-dir exclusion list — `devlyn:auto-resolve-workspace`,
`devlyn:ideate-workspace`, `preflight-workspace`, `roadmap-archival-workspace`
are scratch/snapshot directories with no `SKILL.md`, confirmed by listing
their contents, not installable skills), pointed at a global directory
instead of the repo-local `.claude/skills` mirror `mirror_skills()` targets.

**Dirs-synced decision**: `codex` → both `$HOME/.codex/skills` (documented
location, `bin/devlyn.js:36`) **and** `$HOME/.agents/skills` (the location
`0046`'s own transcript evidence showed a real `codex exec` run actually
resolving from). Precedence between the two is still unresolved — 0046
flagged it as a dedicated follow-up, not closed there — so syncing only one
would be a guess; syncing both is the evidence-based move (whichever one
codex honors, it now has current content) and costs nothing extra (a few
`cp -R` calls). `omp` → `$HOME/.agents/skills` only; `bin/devlyn.js` names
exactly one location for omp (`SHARED_AGENTS_SKILLS_DIR`, shared with Pi)
and no ambiguity was ever recorded for it.

## Verification

**codex-small, fresh, after fix** (`benchmark/probes/results/iter0052-verify-codex-small/compliance/codex-small/`):
all 4 assertions PASS.

```json
{
  "assertions": {
    "state_found": {"pass": true},
    "phases_ordered": {"pass": true},
    "verify_evidence": {"pass": true, "method": "sub_verdicts_with_artifacts",
      "findings_file_found": true, "merged_artifacts_found": true},
    "archive_ran": {"pass": true}
  },
  "overall": "PASS", "failed_assertions": []
}
```

PLAN/IMPLEMENT/BUILD_GATE/CLEANUP all PASS on round 0, zero
`build_gate.findings.jsonl` entries (the prior `EPERM`
`correctness.test-failure` findings are gone), diff is exactly
`bin/cli.js` + `tests/cli.test.js` — no scope leak, no unrelated changes.
1067s elapsed.

**codex-small, before (cited, not re-run)** — `0046`'s clean A/B pair
already established the counterfactual with a byte-verified clean-checkout
methodology stronger than a casual re-run would add:
`benchmark/probes/results/iter0046-baseline-head/compliance/codex-small/`
and `.../iter0046-baseline-with-diff/compliance/codex-small/`, both `FAIL`
with the identical `tests/server.test.js` `listen EPERM` signature, zero
`scope.*` findings, confirming the failure was sandbox-caused rather than
code-caused. Re-running that exact counterfactual here (i.e., reverting
this iteration's fix and re-executing) was judged unnecessary duplicate
spend given that pair already isolates the variable this iteration touches
(the `tests/server.test.js` removal) with a stronger methodology (`git
worktree`-at-HEAD, md5-verified) than a fresh single re-run would provide.

**claude-small (sonnet), regression, after fix**
(`benchmark/probes/results/iter0052-verify-claude-small/compliance/claude-small/`):
all 4 assertions PASS (`sub_verdicts_with_artifacts`, `judge:
PASS_WITH_ISSUES`, `mechanical: PASS`, `pair_judge: PASS`). `diff.patch` is
empty because the pipeline's own IMPLEMENT phase commits inside the work
dir's local git repo (`git log` inside `WORK_DIR` shows `baseline` →
`chore(pipeline): implement`, confirmed via `grep loud bin/cli.js` showing
the flag actually landed) — `git diff HEAD` is relative to that new HEAD,
not evidence of "no change." This is pre-existing `run-compliance-cell.sh`
behavior, untouched by this iteration. 1487s elapsed — the `claude` branch
was not touched by either fix (scaffold deletion applies before the
CLI branch; skill sync is codex/omp-only), so this run is a pure
before/after-neutral regression check, not expected to change from prior
runs (`0046`'s `claude-small` regression, `0048`'s `claude-small`/`omp-small`
Korean cells) and didn't.

## Comparability check (team-lead's explicit ask)

`claude`, `codex`, `omp` branches all receive the identical `test-repo` copy
with `tests/server.test.js` removed before the `case "$CLI"` split — the
deletion is unconditional and CLI-independent, so all three cells still run
against the same task material. Only the skill-loading *mechanism* differs
per CLI (project-local copy for claude vs. global-directory sync for
codex/omp), which was already true before this iteration (claude's
`.claude/skills` copy existed; codex/omp simply had no equivalent) — this
iteration completes that asymmetry rather than introducing a new one.

## Principles check

- **No workaround**: the scaffold fix removes the actual file that performs
  the disallowed operation rather than adding a try/catch, skip flag, or
  sandbox-permission escalation around the symptom.
- **No overengineering**: one `rm -f` line; one small mirrored function
  reusing an existing, already-reviewed pattern (`mirror_skills()`) rather
  than inventing a new sync mechanism. Did not touch the `claude` branch
  (not broken) or the shared `test-repo` fixture (out of this iteration's
  surface and explicitly against that fixture's own "no fixture modifies
  this source tree" convention).
- **No guesswork**: both dirs synced for codex specifically because
  precedence between them is *unresolved* evidence from `0046`, not a
  50/50 guess between two candidates — syncing both is the response to
  genuine uncertainty, not avoidance of investigating it further (that
  investigation is out of this iteration's scope, per the brief).
- **Evidence over claim**: every claim above cites a run dir with real
  `compliance-check.json`/`timing.json`/`diff.patch` artifacts on disk, or
  an already-verified prior iteration's byte-checked A/B pair — no claim
  rests on memory of what should happen.

## Artifacts

- Changed: `benchmark/probes/scripts/run-compliance-cell.sh` (`+47/-0`
  lines: `sync_global_skills()` + its two call sites, one `rm -f`).
- New: this file.
- Verification runs (gitignored, not committed):
  `benchmark/probes/results/iter0052-verify-codex-small/`,
  `benchmark/probes/results/iter0052-verify-claude-small/`.
- Cited (unchanged, not re-run): `benchmark/probes/results/iter0046-baseline-head/`,
  `benchmark/probes/results/iter0046-baseline-with-diff/`.
