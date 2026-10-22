# Build contract: 0257 apparatus

You are the implementation executor for a research apparatus in the devlyn-cli repository.
Work only in `autoresearch/experiments/0257/` of the worktree you were started in
(`/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0257-powered-replay`).

Hard limits:
- Never commit, push, tag, open a PR, or run `git add`. Root reviews and commits.
- Never modify anything outside `autoresearch/experiments/0257/`, and never modify `0257/DESIGN.md` or `0257/results/`
  (except creating `0257/results/operator/` and `0257/results/witnesses/` as item 6 says). Files of 0222, 0232, 0233,
  0237, 0256 and every other experiment are frozen history: import or copy them, never edit them.
- No network access, no Docker, no model calls are available or needed: unit tests must run offline without Docker
  (fakes and fixtures, as 0256's tests do). You may read 0256 evidence under `~/.local/share/nx01/0256-live/output/`
  to build fixtures, but never read or copy credential files (`home/.claude/.credentials*`, `home/.codex/auth.json`,
  keychain output) and never copy anything containing a token into the repository.
- Follow the repository's CLAUDE.md principles: smallest change, no workaround, no silent fallback, explicit errors.

## What to build

Read `autoresearch/experiments/0257/DESIGN.md` first; it is the specification and wins over this contract on any
conflict. Then read 0256's apparatus (`autoresearch/experiments/0256/*.py`, `DESIGN.md`, `registration.md`,
`results/operator/judge.py`, `results/witnesses/`). 0257 is a copy of 0256 with only the deltas below; copy a 0256
module and edit it, or import it unchanged, whichever leaves the smaller, clearer diff. Keep 0256's structure, names
and error style. Modules that need no change are imported from 0256, not copied.

1. `generate_cells.py` — DESIGN "Schedule": SMOKE (4, `smoke-<config>-<arm>`, written to `smoke.tsv`), then easy E1,
   E2 (prefix `e`, one replicate), then r = 1..16 over D3, D4, I0185, B5 (prefix `d`) and, on even r only, F10, F11
   (prefix `c`, confirmation replicate k = r/2). Within a task, claude's block then codex's. A block's arms run AB on
   odd replicates of that task (k for confirmation) and BA on even ones. Cell names keep 0256's shape
   `<prefix><NNN>-<task>-<config>-<arm>-r<rep>`. `cells.tsv` has 328 rows in run order.
2. **Instruction-load assertion** — a new module `instructions.py` used by `run_cell.py`:
   - `seal` (CLI, run by root before SMOKE): run the B installer from the control package on an empty Git tree with
     `-y --claude` and with `-y` (in the cell image via the same mechanism 0256 `prepare.install` uses; tests use a
     fake), and record the sha256 and bytes of every instruction file it writes (`CLAUDE.md`, `AGENTS.md`) in
     `instructions.seal.json` under the runtime root. A second step seals the forms each engine receives from one
     preserved SMOKE B session per engine: Claude's `instructions` attachment content for `CLAUDE.md` and the imported
     `AGENTS.md` (read from the owner transcript), and Codex's AGENTS.md content in the first owner request (read
     from the Codex session trace). Derive the exact transcript/trace shapes from 0256 evidence (claude: e.g.
     `d02-D3-claude-B-r1`, codex: e.g. `d03-D3-codex-B-r1`); state every assumption in a docstring.
   - `check(cell, plan, evidence, seal)` → list of violations, per DESIGN "Environment and apparatus" item 2:
     claude B non-I0185: attachment equals the sealed Claude form; codex B non-I0185: on-disk AGENTS.md before the owner
     starts equals the sealed file and the first owner request carries the sealed content; I0185 B: the installer's skip
     line in the install output, skills present, and both source instruction hashes unchanged from the pre-install
     tree; A: no sealed attachment, no installer-written AGENTS.md, I0185 source hashes unchanged. A non-empty result is
     a STOP verdict with reason starting `instruction assertion:`.
   - Tests: valid, missing, altered and I0185-skip controls for each engine, built from 0256 evidence fixtures
     (copy only the minimal non-secret excerpts into `0257/fixtures/`).
3. `decide.py` — DESIGN "Decision" and "Question and estimands":
   - `endpoints.json` (written by you, frozen with the design): the 43-test development family and the 11-test
     confirmation family per engine exactly as DESIGN lists them; verify the row ids against 0233's `tasks.json`,
     `0233/oracle.js` and 0256's `decisions.json` / verdicts, and fail loudly on any id that does not exist.
   - Pooled counts per task × engine × arm over replicates; one-sided Fisher exact tests (exact hypergeometric, no
     SciPy); Holm at family α = 0.05; p = 1 for a test where B is not worse; a D3/D4 synthetic oracle crash
     (`0222/check.py`) fails that task's frozen oracle rows and adds no row; other crashed commands fail only their row.
   - D and the Wilson-MOVER sign interval with DESIGN's exact equations (`math` only), readings B_BETTER / B_WORSE /
     NO_DETECTED_DIFFERENCE.
   - Witness counts from `decisions.json` `witnesses` (every binding witness must have an explicit result on every tree
     of its task, else NOT_FINISHED); new-mechanism witnesses are reported and excluded from family, headline, token.
   - Headlines in DESIGN's order; every failed clause listed; NOT_FINISHED still evaluates and lists clauses (a B
     false completion appears as PACKAGE_UNSAFE) but emits no p-value and no D.
   - Costs per slot over every dispatched attempt (final verdict plus the attempts the driver archives), 0256's
     `at_most` and lower-bound rules.
   - Token `0257:claude=D:<reading>(<D>[<lo>,<hi>]),dev:<headline>[<failed clauses>],conf:<headline>[…];codex=…`.
   - Predictions 1–6 scored per DESIGN, only on finished panels (prediction 6 from the probe results file, item 6).
4. `driver.py` — 0256's with DESIGN "Operations": caps from `runtime['caps']` (85 / 70 at registration); 0256's
   block-reserve rule and floors; an account or organization mismatch with `runtime['account']` STOPS (exit, latch),
   never holds and never updates the recorded account; the deadline = first SMOKE dispatch time (persisted in
   `driver-status.json`) + 21 days, after which nothing new is dispatched; the harm latch exactly as DESIGN (graded
   verdicts: missing or non-empty `scope_violations`, `teardown != CLEAN`, `identity.status != MATCH`; any verdict,
   STOP included, with identity `MISMATCH`, `UNVERIFIED`, or `UNKNOWN` while the owner was launched, latches before any
   archive or retry); latches persist in `driver-status.json` and survive restarts until an explicit
   `driver.py --clear-latch <amendment-file>` that requires the file to exist. Archived attempts keep their usage for
   item 3. No `direct_run.py`.
5. `run_cell.py`, `prepare.py` — 0256's, plus the item-2 check after the owner run and before assessment, and
   `seal.json` gaining the `instructions.seal.json` sha256 and `endpoints.json` sha256. Runtime root is
   `~/.local/share/nx01/0257-live` (from `runtime.json`; never hard-coded elsewhere).
6. `results/operator/judge.py` (copy of 0256's with 0257 paths) and `results/witnesses/f-malformed-json.js`: the probe
   of DESIGN item 4 (POST body `{`, `Content-Type: application/json`, `/items` for F10, `/items/import` for F11, 5 s
   timeout; classes `json_error_400`, `html_400`, `other`, `unassessable`; separate `store_preserved` bit), run in the
   cell image exactly as the other witnesses are (no network, cap-drop ALL, uid 501). `judge.py probe <cell>...` writes
   `probes.json` in the runtime output. Qualify on 0256 trees: c01 (A) → `json_error_400`, c02 (B) → `html_400`; a
   test may use a fake runner, and root runs the real check.
7. `test_apparatus.py` — 0256's tests adapted, plus every unit test DESIGN "Qualification" lists (counts and order;
   both families; Fisher/Holm hand cases: 16 vs 7 rejects with every other p = 1, p ≈ 0.00041, 16 vs 8 does not,
   p ≈ 0.00122; 0-vs-1 witness INCONCLUSIVE; one false completion UNSAFE even when a row fails; equal witness counts
   with a swap pass; prefix NOT_FINISHED, and a prefix with a B false completion lists PACKAGE_UNSAFE without p-values;
   unresolved witness → NOT_FINISHED; D3/D4 synthetic crash; D and interval hand cases including four tasks 0/16 vs
   16/16 with D = 1 inside, the arm swap, one 16-vs-0 task with three 8-vs-8; the simulation table's null and
   alternative cases rerun through `decide.py`'s interval with a fixed seed, within ±0.01 of DESIGN's figures at
   20,000 runs; driver controls: quota-fault then success charges both attempts, deadline and harm latch across
   dispatch, holds and restart, a quota STOP with identity MISMATCH latches before archive, quota/assessor STOPs with
   MATCH do not latch, an account mismatch stops).

## Done means

- `python3 -m pytest -q autoresearch/experiments/0257` passes offline (report the exact output), and
  `python3 -m pytest -q autoresearch/experiments/0256` still passes.
- `python3 -m py_compile` clean on every new file.
- `autoresearch/experiments/0257/README.md` (≤ 40 lines): each file, its 0256 origin, the delta.
- Your final message lists files created, every assumption about Claude Code 2.1.281 / Codex 0.156.1 transcript or
  trace shapes, anything in DESIGN.md you could not implement exactly, and the test output. Do not claim anything you
  did not run.
