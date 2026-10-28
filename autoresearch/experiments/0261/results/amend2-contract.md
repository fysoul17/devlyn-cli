# 0261 amendment 2 — implementation contract (executor: Codex)

Work only in `/Users/aipalm/Documents/GitHub/.devlyn-worktrees/devlyn-cli/0261-result`. Do not commit. Do not touch
anything under `/Users/aipalm/.local/share/nx01/`. Do not run Docker, models or network.

## Observed failure

`python3 autoresearch/experiments/0261/blind.py packets <runtime.json> <out>` stopped with
`ValueError: non-regular end-tree file: .../d021-D4-claude-B-r11.stop-1/tmp/pytest-of-participant/pytest-1/test_lazy_read_fifo_direct_Fal0/fifo`.

The archived STOP attempt has no graded snapshot, so `packets()` copies its preserved `cell/` and `tmp/` end trees
with `copy_tree`. The D4 task tests FIFOs, and the owner's pytest left nine FIFOs (named pipes) under `/tmp`.
`copy_tree` handles only directories, regular files and symlinks; it raises on anything else. It must not read a FIFO
(the read would block).

## Change (smallest that closes it)

1. `blind.py` `copy_tree`: a FIFO (`stat.S_ISFIFO` on `os.lstat`) is never opened. Record it in
   `special-files.json` at the tree root, as `{relative path: "fifo"}`, redacted like `symlinks.json`, and written only
   when the tree has one. The same exclusions apply as for files and links: a FIFO whose name is excluded or a
   credential path is skipped. Every other non-regular kind still raises the existing `ValueError`.
2. The module docstring line about symlinks gains the FIFO rule, in one clause.
3. `README.md`, "STOP evidence" bullet: after "Symlinks are recorded as link text and never followed.", add one
   sentence: "FIFOs are recorded by name in `special-files.json` and never opened (amendment 2)."
4. A test in `test_apparatus.py`, next to the existing blind tests: build a tree with a regular file and a FIFO
   (`os.mkfifo`) and a FIFO under an excluded name, run `copy_tree`, and assert the regular file is copied,
   `special-files.json` maps only the non-excluded FIFO to `"fifo"`, no FIFO exists in the target, and the call
   returns without blocking. Keep an existing test (or add an assertion) that a different non-regular kind still
   raises if one is easy to create portably (a Unix socket via `socket.socket(AF_UNIX).bind`); skip that assertion if
   the path is too long for `AF_UNIX`, rather than weakening it.

Match the file's style. No other behavior change.

## Verify

```
python3 -m pytest -q -p no:cacheprovider autoresearch/experiments/0261
python3 -m pytest -q -p no:cacheprovider autoresearch/experiments/0260
git diff --check
```

Report the diff summary and the test counts.
