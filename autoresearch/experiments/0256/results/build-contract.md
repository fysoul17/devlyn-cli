# Build contract: 0256 apparatus

You are the implementation executor for a research apparatus in the devlyn-cli repository.
Work only in `autoresearch/experiments/0256/` of the worktree you were started in
(`/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0256-package-replay`).

Hard limits:
- Never commit, push, tag, open a PR, or run `git add`. Root reviews and commits.
- Never modify anything outside `autoresearch/experiments/0256/`, and never modify `0256/DESIGN.md` or `0256/results/`. Files of 0222, 0232, 0233, 0237 and every other
  experiment are frozen history: import or copy them, never edit them.
- No network access, no Docker, no model calls are available or needed: unit tests must run offline without Docker
  (use fakes and fixtures, as 0233's tests do).
- Follow the repository's CLAUDE.md principles: smallest change, no workaround, no silent fallback, explicit errors.

## What to build

Read `autoresearch/experiments/0256/DESIGN.md` first; it is the specification and wins over this contract on any
conflict. Then read 0233's apparatus (`autoresearch/experiments/0233/*.py`, `DESIGN.md`, `tasks.json`) and the modules
it imports from 0222 and 0232, plus `0237/cell-init-v1.py` and `0237/runner.py` (lines 115–160). 0256 is a copy of
0233's modules with only the deltas below; copy a 0233 module and edit it, or import it unchanged, whichever leaves the
smaller, clearer diff. Keep 0233's structure, names and error style.

1. `control.py` — one package arm `B`: download is NOT done in tests. Production path: `fetch(cache)` reads
   `cache/B.tgz` if present, otherwise downloads `https://registry.npmjs.org/devlyn-cli/-/devlyn-cli-4.2.24.tgz`;
   verify the npm integrity `sha512-bciFYsU0mRJLH9DunMRENLMOR4wjLygdKb9Ub9e/Vu8u9A20Noc/k1UskrRq+7vlCdG983ky9ObBydxq1ufhTQ==`
   (refuse on mismatch, never re-download silently); record its sha256 in the manifest. No pack step, no arm C.
   Public/oracle trees and the oracle path (`autoresearch/experiments/0233/oracle.js`) as in 0233.
2. `prepare.py` — arms `A` and `B` only; 0233's tasks with a 0256 override file `tasks-override.json`
   (`{"D3": {"issue_snapshot_sha256": ..., "fetched_at": ..., "url": ...}, "D4": {...}}`) replacing only
   `issue_snapshot_sha256`; refuse when the override is missing or malformed. After 0233's preparation, apply 0237
   runner's exclusions exactly: `home/.claude/settings.json` = `{"syncClaudeAiSkills": false, "syncClaudeAiPlugins":
   false}`, `ENABLE_CLAUDEAI_MCP_SERVERS=false` in the plan env, claude argv gains `--strict-mcp-config --mcp-config
   {"mcpServers":{}}`, and the Codex project-trust path rewrite with its refusal on unexpected inherited trust. The
   baseline/plan digests must cover the final prepared files (0237's `boot` list idea).
3. `snapshot_issues.py <sources-dir> <out-override-json>` — fetch the current JSON of tj/commander.js#2530 (D3) and
   pallets/click#2645 (D4) once via `gh api repos/<repo>/issues/<n>`, write the raw bytes unchanged to
   `<sources>/D3-issue.json` and `D4-issue.json`, refuse to overwrite existing files, and write the override with
   sha256, UTC fetch time and URL. (Root runs it at freeze; tests use a fake `gh`.)
4. `models_cache.py <runtime.json> <out>` — produce a Codex models cache with the pinned Codex 0.156.1 inside the
   frozen image (one minimal `codex exec` in a throwaway CODEX_HOME seeded with a copy of the host auth, as 0233's
   `codex_limits` does), copy `models_cache.json` to `<out>`, print its sha256; refuse if no cache was written.
   (Root runs it; tests cover argv construction and the refusal only.)
5. `cell.py` — use `0237/cell-init-v1.py`'s `run` unchanged (import it); no other lifecycle change.
6. `record_usage.py` — 0233's, with Claude reconciliation per DESIGN "Accounting": a Claude session is COMPLETE only
   when, for every model and counter, the result envelope's total equals the sum of terminal usage over its
   transcripts' assistant messages (deduplicate repeated copies of one message id; all terminal copies of an id must
   agree), every assistant message has terminal usage, and no retry/abort/progress event lacks a terminal message;
   otherwise UNKNOWN with the terminal sum as the lower bound. Read `autoresearch/experiments/0239/results/closure.md`
   (lines 15–40) and `0239/results/d01-native-audit.md` for the observed interrupted-stream shape, and
   `autoresearch/experiments/0254/audit.py` for how terminal copies were identified on Claude Code 2.1.296; the
   pinned CLI here is 2.1.281, so derive the transcript shape from 0233's own transcript fixtures/tests and state any
   assumption in a docstring. Tests: exact equality → COMPLETE; the 0239 d01 shape (envelope exceeds terminal sum,
   failed attempt without an assistant message) → UNKNOWN; a message without terminal usage → UNKNOWN; disagreeing
   terminal copies → UNKNOWN.
7. `generate_cells.py` — arms A/B; development (D3, D4, I0185, B5) 2 replicates prefix `d`, easy (E1, E2) 1 replicate
   prefix `e`, confirmation (F10, F11) 2 replicates prefix `c`; blocks task-major then claude/codex; replicate 1 block
   (t, c) runs AB when t + c is even else BA (t = task position in its panel, c = 0 claude, 1 codex); replicate 2
   reverses the block order and each block's arm order; SMOKE = 4 cells `smoke-<config>-<arm>`; write `cells.tsv`
   (56 rows, registered order development → easy → confirmation) and `smoke.tsv`. No screening file.
8. `decide.py` — 0232 §6 B/A per configuration for development (gating), confirmation and easy (reported), using
   0233's `quality`, `at_most`, `every` and `compare` semantics unchanged; the eight readings and the token
   `0256:claude=dev:<reading>[<conditions>],conf:<reading>[<conditions>];codex=…` from DESIGN "Decision" (easy
   reported in the JSON, not the token); NOT_FINISHED lists every missing verdict, STOP row and missing judgment
   instead of raising. Write `decision.json` as 0233 does.
9. `run_cell.py` — 0233's minus the screening/eligibility path, using 0256's modules; additions: before preparing,
   `docker image inspect <runtime image> --format {{.Id}}` must equal `runtime['image']` (else STOP 'image identity
   mismatch'; the driver handles loading); `seal.json` adds package sha256, models-cache sha256 and the sha256 of every
   imported module file from 0222/0232/0233/0237; the verdict records Claude window utilization at preflight and again
   after grading (`claude_limits`), so the driver can compute per-cell window changes; before assessment, a fresh
   same-account credential snapshot requiring at least 1,500 s of token life — when short, the verdict is STOP with
   reason starting `assessment held:` and `--regrade` accepts that reason like the other assessor STOPs.
10. `driver.py <runtime.json> <cells.tsv>[:<prefix>] ...` — the DESIGN "Operations" protocol: run cells in file order,
    skip slots that already have a verdict, never re-dispatch a finished verdict; holds (rc 3 from run_cell, short
    token, window reserve, missing image) wait and retry; the image is reloaded from `runtime['image_tarball']` with
    `docker load` when missing and rechecked; token renewal exactly as DESIGN (wait to within five minutes of expiry,
    one non-interactive host `claude -p` with no tools and an empty MCP set — verify the flags against
    `claude --help` text passed in tests as a fixture, and make the command configurable in runtime.json — then
    require the expiry to advance and both fingerprints to match, else hold for the owner without repeating); window
    caps from `runtime['caps']` (`seven_day`, `five_hour`, percent), per-arm estimates per window as DESIGN (a cell whose
    window reset time changed is indeterminate for that window and never lowers an estimate), block start and
    second-arm rules, split blocks recorded; execution quota STOPs re-dispatch only arms without a verdict; any other
    STOP (rc 2) stops the driver with a clear message. Log one line per event to `<output>/driver.log` and keep
    `<output>/driver-status.json` current. The driver is meant to run under `caffeinate -dimsu`.
11. `calibrate.py` — reuse 0233's calibration overlays by path.
12. `test_apparatus.py` — 0233's tests adapted to two arms plus: cell counts (56 + 4) and the order rule; every reading
    including NOT_FINISHED, NO_CLAIM, dominance and COST_UNKNOWN; the reconciliation cases; the integrity refusal; the
    override refusal; the image check; the assessment hold and its regrade; the driver's renewal, window and
    re-dispatch rules with fakes.

## Done means

- `python3 -m pytest -q autoresearch/experiments/0256` passes offline (report the exact output).
- `python3 -m pyflakes` or `python3 -m py_compile` clean on every new file.
- A short `autoresearch/experiments/0256/README.md` (≤ 40 lines) listing each file, its 0233 origin, and the delta.
- Your final message lists: files created, every assumption you made about Claude Code 2.1.281 transcripts or CLI
  flags, anything in DESIGN.md you could not implement exactly, and the test output. Do not claim anything you did not
  run.
