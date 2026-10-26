# Build contract: 0259 apparatus

You are the implementation executor for a research apparatus in the devlyn-cli repository.
Work only in `autoresearch/experiments/0259/` of the worktree you were started in
(`/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0259-ablation`).

Hard limits:
- Never commit, push, tag, open a PR, or run `git add`. Root reviews and commits.
- Never modify anything outside `autoresearch/experiments/0259/`, and never modify `0259/DESIGN.md` or the existing
  files in `0259/results/` (you may create `0259/results/operator/` and `0259/results/witnesses/`). Files of 0256,
  0257, 0258 and every other experiment are frozen history: import them, or copy and edit a copy, never edit them.
- No network, no Docker and no model calls are available or needed: unit tests run offline with fakes and fixtures,
  as 0258's do. You may read 0257/0258 evidence under `~/.local/share/nx01/0257-live/` and `0258-live/` (`output/`,
  `control/`, `instructions.seal.json`, `runtime.json`) to build fixtures, but never open any `output/<cell>/home/`
  directory, `auth/`, credential files (`.credentials*`, `auth.json`) or keychain output, and never copy anything
  containing a token into the repository.
- Follow the repository's CLAUDE.md principles: smallest change, no workaround, no silent fallback, explicit errors.

## What to build

Read `autoresearch/experiments/0259/DESIGN.md` first; it is the specification and wins over this contract on any
conflict. 0259 is 0258's apparatus (`autoresearch/experiments/0258/*.py`, `README.md`,
`results/operator/judge.py`, `results/witnesses/*.js`) with only the deltas below. Copy each 0258 file into `0259/`
and edit the copy; keep 0258's structure, names and error style, and keep its imports of 0256/0257 modules unchanged.

1. **Deleted text.** In `control.py` and `instructions.py`, replace 0258's clause with exactly this line, newline
   included (UTF-8; the dash is U+2014):

   ```
   2. **No overengineering** — smallest change that closes the goal. New abstractions require an observed failure mode they prevent. Subtractive-first: ask "what can I delete instead?" before writing anything new. Remove code your change makes unused; only report unrelated pre-existing dead code.
   ```

   Name the constant for what it is (for example `DELETED_LINE`). `control.py` still requires it exactly once in each
   of `AGENTS.md`, `CLAUDE.md` and `config/skills/_shared/runtime-principles.md`. Check against the real B package
   at `~/.local/share/nx01/0258-live/control/packages/B/package` (read-only) that each file contains the line
   exactly once, and report it.
2. **Names.** Experiment `0259` everywhere 0258 says `0258` in code, messages and paths: runtime root
   `~/.local/share/nx01/0259-live`, `NX01_0259_RUNTIME` in `judge.py`, the token prefix `0259:claude=`, and the
   headlines `PRINCIPLE_IMPLICATED` and `PRINCIPLE_PARTIAL` instead of `CLAUSE_IMPLICATED` and `CLAUSE_PARTIAL`.
   Keep `prior_runtime` (0257's `runtime.json`) as the source of the B-equality seals, exactly as 0258 does.
3. **Witness and probe.** Copy `0258/results/witnesses/d3-parseoptions-override.js` and `f-malformed-json.js`
   byte for byte into `0259/results/witnesses/`. A test pins their sha256 values
   (`5e706105f608b888ff04fdff530855b84d4c994a466b320640957efa70e14c61` and
   `6bcba20346013972696cd856e99545df48334f7cb777e49ab2defdc3c98979cb`). Do not copy 0258's other result files.
4. **Tests.** `test_apparatus.py` adapted: every 0258 test still applies with the new text and names. The package-diff
   test must use a fake B whose target files contain the full line between other lines, and prove C equals B with
   that line removed and nothing else; B without the line or with it twice fails.
5. **README.md** (≤ 30 lines): each file, its 0258 origin and the delta, and the operator steps (build C, seal,
   SMOKE, seal-forms, run, probe, witness, decide), with 0259 paths.

## Done means

- `python3 -m pytest -q autoresearch/experiments/0259` passes offline (report the exact output), and the 0258 and
  0257 suites still pass.
- `python3 -m py_compile` is clean on every new Python file.
- `diff -r autoresearch/experiments/0258 autoresearch/experiments/0259` (excluding `results/`, `__pycache__`,
  `DESIGN.md`, `registration.md`, `RESULT.md`, `cells.tsv`, `smoke.tsv`) shows only the deltas above; summarize it.
- Your final message lists files created, the real-package check from item 1, anything in DESIGN.md you could not
  implement exactly, and the test output. Do not claim anything you did not run.
