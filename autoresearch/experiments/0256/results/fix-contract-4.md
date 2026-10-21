# Fix round 4: 0256 apparatus (measured-run finding)

Same hard limits as `autoresearch/experiments/0256/results/build-contract.md` (work only in
`autoresearch/experiments/0256/` — prepare.py, test_apparatus.py, and a short note in registration.md — never DESIGN.md
or results/, no commits, offline tests). Never touch anything under `/Users/aipalm/.local/share/nx01/`.

## Finding

Measured cell d11-I0185-codex-B-r1 crashed in preparation: `git commit -qm 'install B'` in `prepare.install` exited 1.
I0185's registered `.gitignore` ignores `.agents/`, so the Codex install (`.agents/skills/...`, present on disk) adds no
tracked change and the commit has nothing to record. `committed_tree`'s docstring already expects ignored installer
output to stay behind in the anchor; only the commit step is wrong.

## Fix

In `prepare.install`, record the install commit even when the installer changed no tracked file (`--allow-empty`), so
the baseline and allocation commit are defined exactly as for every other B cell. No other behavior changes.

Test (offline, no Docker): a repository whose `.gitignore` ignores the install target; with the Docker installer call
mocked to write only ignored files, `install` succeeds, HEAD is a new commit with message `install B` and an unchanged
tree. Observe it fail before the fix.

Add to registration.md, under "Operational amendments", one bullet: "**Empty install commit (fix round 4).** Measured
cell d11-I0185-codex-B-r1 stopped in preparation because I0185's `.gitignore` ignores `.agents/`, so Codex's install
left no tracked change and the install commit failed. The install commit is now recorded even when empty. Cells
d01–d10 had non-empty install commits or no install and are unaffected; d11 had not been dispatched."

Done means: `python3 -m pytest -q autoresearch/experiments/0256` passes, pyflakes clean, and a final message with the
change, test name and before/after observation.
