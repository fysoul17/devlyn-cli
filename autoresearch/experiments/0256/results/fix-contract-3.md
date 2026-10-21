# Fix round 3: 0256 apparatus (SMOKE finding)

Same hard limits as `autoresearch/experiments/0256/results/build-contract.md` (work only in
`autoresearch/experiments/0256/`, never DESIGN.md or results/, no commits, offline tests). SMOKE evidence, read-only:
`/Users/aipalm/.local/share/nx01/0256-live/output/smoke-codex-B/` (never modify anything under
`/Users/aipalm/.local/share/nx01/`).

## Finding

smoke-codex-B's check reported the scope violation `.agents/skills/.devlyn-install.json`, a file the participant never
touched (content identical, ctime equal to install time).

- The 4.2.24 installer creates the marker with mode 0600 (`bin/devlyn.js` `writeInstallMarker` opens it `0o600`).
- `prepare.py` commits the install; `baseline.json` `files` is `committed_tree(work, transport['head'])`, built from raw
  Git objects, so modes are normalized to 644/755: the marker is recorded `…:644`.
- The participant's working tree keeps 0600 (`git status` stays clean, since Git tracks only the executable bit).
- The anchor snapshot (0233 `locate.copy_tree`, `shutil.copy2`) keeps 0600, so 0233 `check.py` lists the file in
  `changed` and `scope_violations` and `product_check_pass` is false. A receipt snapshot (`raw_tree`) normalizes modes,
  which is why smoke-claude-B did not show it.

## Fix

The violated invariant: the participant starts from exactly the recorded baseline. Fix it in `0256/prepare.py` only
(not 0233, 0222 or the check/locate comparison):

1. After the install commit and before `baseline.json` is written, set each tracked regular file's working-tree mode
   to its committed mode (0o644 or 0o755, from the same commit the baseline records); symlinks are left alone.
2. Then verify that, for every tracked name, `packet.tree(work)` equals the committed tree; any difference raises
   `ValueError` (preparation fails; nothing runs).
3. Keep it minimal: one small helper used by `prepare`, reusing `committed_tree`; compute the committed tree once.

Test (offline, no Docker): a temporary Git repository with a committed file whose working mode is 0600 and a committed
executable at 0755. Before the fix, `packet.tree` of the work tree differs from the committed tree for the 0600 file;
after the helper runs, the file is 0644, the executable stays 0755, and the trees match. Also a test that a content
difference in a tracked file raises `ValueError`. Observe the first test fail before the fix.

Done means: `python3 -m pytest -q autoresearch/experiments/0256` passes, pyflakes clean, README updated only if a
file's role changed, and a final message listing the change, the test names and the before/after observation.
