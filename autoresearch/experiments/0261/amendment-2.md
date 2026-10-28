# 0261 amendment 2: FIFOs in a preserved end tree (2026-10-28)

This is a dated amendment to the frozen [DESIGN.md](DESIGN.md) (r6), after [amendment 1](amendment-1.md).

**Timing.** Root wrote it after:
- all 64 measured verdicts;
- amendment 1's recording of `d021-D4-claude-B-r11.stop-1`;
- every witness pass and the F10 probe (all resolved).

No packet had been read, and no judgment had been made.

## Observed failure

The first `blind.py packets` run stopped with `ValueError: non-regular end-tree file:` on a FIFO under
`d021-D4-claude-B-r11.stop-1/tmp/pytest-of-participant/`.
- **Why it hit only this attempt.** A STOP before grading has no graded snapshot, so `packets()` copies its preserved
  `cell/` and `tmp/` trees. D4 tests read from FIFOs, and the owner's pytest left nine FIFOs (named pipes) in `/tmp`.
- **Why it stopped.** `copy_tree` accepts only directories, regular files and symlinks. Reading a FIFO would block.
- **The first output.** It had written its `label-map.json` and 32 packets. Nobody opened them, and its sha256 was
  never printed. Root deleted that directory.

## Change

1. **FIFOs are recorded, not opened.** `copy_tree` records each FIFO by name in `special-files.json` at the tree's
   root, as `{relative path: "fifo"}`. That file is redacted the same way as `symlinks.json`. A FIFO is skipped
   under the same name exclusions as files and links. Any other non-regular file still stops packet generation.
   So does a tree file whose name matches a manifest it would overwrite (`symlinks.json` or `special-files.json`).
2. **Tests.**
   - A regular file, a FIFO, and FIFOs under excluded names.
   - A socket still raises.
   - The manifest-name collision raises.
3. **Review.** Astra (`results/amend2-r1-astra.md`) found the overwrite, which the change above fixes. Grok
   (`results/amend2-r1-grok.md`) found nothing.
4. **New packets.** Root reran `blind.py packets` into a new directory (`blind-2`). It logged that map's sha256,
   `81447d81b956c345501722b272b711ec7be4997156b90a20de98a7067f80df05`, in `driver.log` at 2026-10-28T08:41:25Z,
   before any judgment.

**Blinding note.** This follows from amendment 1. The one packet with two attempts is the d021 slot, so root knows
that packet's arm (B). The verifiers are not told which arm it is.

Everything else is unchanged.
