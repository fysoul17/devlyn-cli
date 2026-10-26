# Build contract: 0260 apparatus

You are the implementation executor for a research apparatus in the devlyn-cli repository.
Work only in `autoresearch/experiments/0260/` of the worktree you were started in
(`/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0260-saint-exupery`).

Hard limits:
- Never commit, push, tag, open a PR, or run `git add`. Root reviews and commits.
- Never modify anything outside `autoresearch/experiments/0260/`, and never modify `0260/DESIGN.md` or the existing
  files in `0260/results/` (you may create `0260/results/operator/` and `0260/results/witnesses/`). Files of 0256–0259
  and every other experiment are frozen history: import them, or copy and edit a copy, never edit them.
- No network, no Docker and no model calls are available or needed: unit tests run offline with fakes and fixtures,
  as 0259's do. You may read 0257–0259 evidence under `~/.local/share/nx01/0257-live/`, `0258-live/` and `0259-live/`
  (`output/`, `control/`, `instructions.seal.json`, `runtime.json`) to build fixtures, but never open any
  `output/<cell>/home/` directory, `auth/`, `scratch/credentials`, credential files (`.credentials*`, `auth.json`) or
  keychain output, and never copy anything containing a token into the repository.
- Follow the repository's CLAUDE.md principles: smallest change, no workaround, no silent fallback, explicit errors.

## What to build

Read `autoresearch/experiments/0260/DESIGN.md` first; it is the specification and wins over this contract on any
conflict. 0260 is 0259's apparatus (`autoresearch/experiments/0259/*.py`, `README.md`, `cells.tsv`, `smoke.tsv`,
`results/operator/judge.py`, and the two endpoint files in `results/witnesses/`) with only the deltas below. Copy each
0259 file into `0260/` and edit the copy; keep 0259's structure, names and error style, and keep its imports of
0256/0257 modules unchanged.

1. **Edit.** In `control.py` (and wherever `instructions.py` uses it), replace 0259's seven-item `EDIT` with exactly
   these two ordered items (UTF-8; the dashes are U+2014; the first source includes its trailing newline):

   ```
   ('- **Perfection is achieved not when there is nothing more to add, but when there is nothing left to take away.** — Saint-Exupéry. This is the operating definition of "done." A change is finished when no further line, branch, flag, or doc paragraph can be removed without breaking a learned failure mode. Not before.\n', '')
   ('Three discipline rules govern HOW the principles are applied:', 'Two discipline rules govern HOW the principles are applied:')
   ```

   `control.py` still requires each source exactly once in each of `AGENTS.md`, `CLAUDE.md` and
   `config/skills/_shared/runtime-principles.md`. Check against the real B package at
   `~/.local/share/nx01/0259-live/control/packages/B/package` (read-only) that each file contains each source exactly
   once and that applying the edit leaves "Two discipline rules" followed by exactly two bullets; report it.
2. **Names.** Experiment `0260` everywhere 0259 says `0259` in code, messages, module names and paths: runtime root
   `~/.local/share/nx01/0260-live`, `NX01_0260_RUNTIME` and `NX01_0260_JUDGE_SCRATCH` in `judge.py`, the token prefix
   `0260:claude=`, and the headlines `RULE_IMPLICATED` and `RULE_PARTIAL` instead of `PRINCIPLE_IMPLICATED` and
   `PRINCIPLE_PARTIAL` (the others and the match order unchanged). Keep `prior_runtime`
   (0257's `runtime.json`) as the source of the B-equality seals, exactly as 0259 does.
3. **Amendments built in.** Copy 0259's `quota.py` (amendment 1) and `judge.py`'s scratch option (amendment 2)
   unchanged apart from names; confirm that `run_cell.py` and `driver.py` use 0260's `quota.py`, so a cell with the
   retry-only shape ends STOP during the run and the driver archives and reruns it in the same slot (a test shows
   this). Do not copy `reclassify.py`, 0259's `amendment-*.md`, `RESULT.md`, `registration.md` or any other result
   file.
3a. **A judge container that never starts is not an attempt** (DESIGN, Apparatus). In `judge.py`, both `probe` and
   `run` create each container with `docker create` (same options as 0259's `docker run --rm`, 60 s limit) and run
   it with `docker start -a` under 0259's run limits (probe 60 s, D3 witness 10 s, other witnesses 30 s), removing
   the container afterwards in every path. If `docker create` exits non-zero or times out, raise an error that names
   the cell, after writing every earlier cell's result but nothing for this cell, and remove any partly created
   container. A failure or timeout of `docker start -a` keeps 0259's meaning (probe `unassessable`, witness exit 2).
   Tests with a fake `subprocess.run`: a create timeout or create error stops the call and leaves the cell absent
   from `probes.json` / `witnesses.json` with earlier cells kept; a start timeout still records `unassessable` / exit
   2; the normal path records as 0259 does.
4. **Witness and probe.** Copy `0259/results/witnesses/d3-parseoptions-override.js` and `f-malformed-json.js` byte for
   byte into `0260/results/witnesses/`. A test pins their sha256 values
   (`5e706105f608b888ff04fdff530855b84d4c994a466b320640957efa70e14c61` and
   `6bcba20346013972696cd856e99545df48334f7cb777e49ab2defdc3c98979cb`). Do not copy 0259's other witnesses.
5. **Schedule.** `cells.tsv` and `smoke.tsv` byte-identical to 0259's; a test pins `cells.tsv` sha256
   `d1176888abd03b2ce21cda06a0bfc018fa25170ff2500d7da08c24a92b4f8d32`.
6. **Tests.** `test_apparatus.py` adapted: every 0259 test still applies with the new text and names. The package-diff
   test must use a fake B whose target files contain the three-bullet discipline block between other lines, and prove
   C equals B with the Saint-Exupéry line removed and the count sentence changed, and nothing else; a B without either
   source, or with either twice, fails. Where 0259 checks the real B package when available, check the 0259 control
   root's B.
7. **README.md** (≤ 30 lines): each file, its 0259 origin and the delta, and the operator steps (build C, runtime,
   seal, SMOKE, seal-forms, run, probe, witness, decide, and what to do when `judge.py` stops on a create failure),
   with 0260 paths.

## Done means

- `python3 -m pytest -q autoresearch/experiments/0260` passes offline (report the exact output), and the 0259 and
  0258 suites still pass, each run separately.
- `python3 -m py_compile` is clean on every new Python file.
- `diff -r autoresearch/experiments/0259 autoresearch/experiments/0260` (excluding `results/`, `__pycache__`,
  `DESIGN.md`, `registration.md`, `RESULT.md`, `amendment-*.md`, `reclassify.py`) shows only the deltas above;
  summarize it.
- Your final message lists files created, the real-package check from item 1, anything in DESIGN.md you could not
  implement exactly, and the test output. Do not claim anything you did not run.
