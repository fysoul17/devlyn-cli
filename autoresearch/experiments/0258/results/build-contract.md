# Build contract: 0258 apparatus

You are the implementation executor for a research apparatus in the devlyn-cli repository.
Work only in `autoresearch/experiments/0258/` of the worktree you were started in
(`/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0258-clause-ablation`).

Hard limits:
- Never commit, push, tag, open a PR, or run `git add`. Root reviews and commits.
- Never modify anything outside `autoresearch/experiments/0258/`, and never modify `0258/DESIGN.md` or the existing
  files in `0258/results/` (you may create `0258/results/operator/` and `0258/results/witnesses/`). Files of 0222,
  0232, 0233, 0256, 0257 and every other experiment are frozen history: import them, or copy and edit a copy, never
  edit them.
- No network, no Docker and no model calls are available or needed: unit tests run offline with fakes and fixtures,
  as 0257's do. You may read 0257 evidence under `~/.local/share/nx01/0257-live/` (`output/`, `control/`,
  `instructions.seal.json`, `runtime.json`) to build fixtures, but never open any `output/<cell>/home/` directory,
  `auth/`, credential files (`.credentials*`, `auth.json`) or keychain output, and never copy anything containing a
  token into the repository.
- Follow the repository's CLAUDE.md principles: smallest change, no workaround, no silent fallback, explicit errors.

## What to build

Read `autoresearch/experiments/0258/DESIGN.md` first; it is the specification and wins over this contract on any
conflict. Then read 0257's apparatus (`autoresearch/experiments/0257/*.py`, `README.md`, `DESIGN.md`,
`amendment-{1,2,3}.md`, `results/operator/judge.py`, `results/witnesses/f-malformed-json.js`) and the 0256/0233
modules it loads. 0258 is 0257 with only the deltas below. Import a 0257/0256 module unchanged where it needs no
change; otherwise copy it into `0258/` and edit the copy, whichever leaves the smaller, clearer diff. Keep 0257's
structure, names and error style.

1. **Arm C package** (DESIGN "Arms", apparatus item 1). A function/CLI that builds `control/packages/C/package` from
   `control/packages/B/package` of a given control root by deleting exactly
   `do not silently pick one interpretation when multiple exist, ` once from each of `AGENTS.md`, `CLAUDE.md` and
   `config/skills/_shared/runtime-principles.md` (each must contain it exactly once, else fail), copying everything
   else byte- and mode-identically (symlinks preserved). The control manifest (0256 `control.py` mechanism) covers
   both packages. A test builds C from a small fake B and proves the diff is exactly the three deletions, and that a
   B without the clause, or with it twice, fails.
2. **`prepare.py`** (item 2): arms `('B', 'C')`, each installing from `packages/<arm>`; the plan records the arm's
   package digest. Claude only (`config` is always `claude`).
3. **`instructions.py`** (item 3): per-arm installer seals and per-arm Claude forms; no Codex form. `seal` runs each
   arm's installer offline on an empty tree with `-y --claude` (via the same mechanism as 0257; tests use a fake) and
   requires B's bytes to equal 0257's sealed B installer bytes (path of 0257's `instructions.seal.json` from
   `runtime.json`). `seal-forms` reads the two SMOKE sessions (`smoke-claude-B`, `smoke-claude-C`), requires B's Claude
   form to equal 0257's sealed B Claude form, and records qualification only when: the two Claude forms differ only
   by the clause; the installed `AGENTS.md` files differ by the clause plus the managed-block `sha256=` digest; the
   installed `.agents/skills/_shared/runtime-principles.md` and `.claude/skills/_shared/runtime-principles.md` differ
   only by the clause. `check` passes a cell only when it matches its own arm's seal and not the other's. Tests:
   valid, missing, altered and wrong-arm controls.
4. **`run_cell.py`** (item 4): claude-only seal requirement (no Codex form), the arm's own package digest in
   `seal.json`, and the instruction assertion from item 3. Keep the Codex limit preflight: the Codex assessor still
   runs on every cell.
5. **`generate_cells.py`** (item 5): SMOKE `smoke-claude-B`, `smoke-claude-C` to `smoke.tsv`; then r = 1..16, D3 block
   then F10 block, BC on odd r and CB on even r; names `<prefix><NNN>-<task>-claude-<arm>-r<rep>` (`d` for D3, `c`
   for F10, NNN in run order); `cells.tsv` 64 rows. A test checks counts and order.
6. **`results/operator/judge.py`** (item 6): copy of 0257's with `NX01_0258_RUNTIME`; `run` records witness exit ≥ 2
   (and a timeout) as an explicit `unresolved` result instead of aborting; `probe` reruns a missing or `unassessable`
   result once on the same tree and records both attempts; witness and probe results go to the 0258 output.
7. **`results/witnesses/d3-parseoptions-override.js`** (item 7): exactly DESIGN "P2", including the return value of
   `super.parseOptions`, exit 0/1/2 and a 10 s self-timeout. Run it yourself with plain `node` (no Docker) on the
   0257 trees `~/.local/share/nx01/0257-live/output/{d241-D3-claude-B-r16,d049-D3-claude-B-r4}/snapshot` (expect 1)
   and `{d002-D3-claude-B-r1,d017-D3-claude-B-r2}/snapshot` (expect 0), twice each, without writing into those
   trees, and report the exact exits. Root reruns it in the cell image.
8. **`decide.py`** (item 8): DESIGN "Endpoints" and "Decision" exactly: readiness per test, the fixed-size two-test
   Holm family (unresolved P2 enters as p = 1), p = 1 for an absent adverse direction, exact one-sided Fisher (reuse
   0257's implementation), the headline order, the listed flags, the token, cost per success (0257 accounting) and
   predictions 1–3 with their scoring conditions. Inputs: verdicts, the probe results, the witness results and the
   audit/severe judgment files in 0257's formats.
9. **`driver.py`** (item 9): 0257's driver with arms B/C, 64 slots plus 2 SMOKE, runtime root from `runtime.json`
   (`~/.local/share/nx01/0258-live`), caps 95/95 required from the first dispatch (no amendment step), deadline 14 days
   after the first SMOKE dispatch, and everything else of 0257 including amendments 1–3, holds, faults, account
   fingerprints, the Docker-loss archive and the harm latch.
10. **`test_apparatus.py`**: 0257's tests that still apply, adapted, plus every unit test DESIGN "Qualification" lists
    (Fisher/Holm hand cases 8 vs 0 → p ≈ 0.0012 rejects, 4 vs 0 → p ≈ 0.051 does not; readiness cases; C_UNSAFE beside
    a rejected P1; P2 unresolved with F10 6/16 vs 1/16, raw p ≈ 0.0415 → P2_UNRESOLVED), the package-diff tests, the
    instruction controls and the driver controls that 0257 tests for the inherited behavior.

## Done means

- `python3 -m pytest -q autoresearch/experiments/0258` passes offline (report the exact output), and
  `python3 -m pytest -q autoresearch/experiments/0257` still passes.
- `python3 -m py_compile` is clean on every new Python file.
- `autoresearch/experiments/0258/README.md` (≤ 40 lines): each file, its origin and the delta, and the operator steps
  (build C, seal, SMOKE, seal-forms, run, probe, witness, decide).
- Your final message lists files created, the witness exits from item 7, anything in DESIGN.md you could not implement
  exactly, and the test output. Do not claim anything you did not run.
