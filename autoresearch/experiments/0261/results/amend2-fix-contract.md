# 0261 amendment 2 — review fix (executor: Codex)

Work only in `/Users/aipalm/Documents/GitHub/.devlyn-worktrees/devlyn-cli/0261-result`. Do not commit. Do not touch
anything under `/Users/aipalm/.local/share/nx01/`. No Docker, models or network.

Astra's review (MEDIUM): in `autoresearch/experiments/0261/blind.py` `copy_tree`, when the source tree root holds a
regular file named `special-files.json` (or `symlinks.json`) and the tree also has a FIFO (or a symlink), the copied
evidence file is silently overwritten by the manifest.

Fix: before writing either manifest, if that path already exists in the target, raise
`ValueError(f'manifest name collides with an end-tree file: {source / name}')` (keep the file's style). Packet
generation then fails closed, as it does for other unexpected trees. Add one regression test next to
`test_copy_tree_records_fifos_without_opening`: a tree with a regular `special-files.json` at its root plus a FIFO
raises that error. No other change.

Verify: `python3 -m pytest -q -p no:cacheprovider autoresearch/experiments/0261` (the socket test may fail inside your
sandbox only because `AF_UNIX.bind` is denied; say so), and `git diff --check`.
