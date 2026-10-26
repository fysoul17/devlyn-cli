# Fix contract r1: 0259 renumbered edit

Same hard limits as `results/build-contract.md` (work only in `autoresearch/experiments/0259/`, never edit
`DESIGN.md` or existing `results/` files, no commit/push/`git add`, no network/Docker/model calls, never open
`home/`, `auth/` or credential files).

The design changed after review: read `autoresearch/experiments/0259/DESIGN.md` "Arms" again. Arm C is no longer a
single line deletion. It is an ordered edit, applied in each of `AGENTS.md`, `CLAUDE.md` and
`config/skills/_shared/runtime-principles.md`, where each source text must occur exactly once in the file before its
step (else fail with an explicit error naming the file and the text):

1. delete the full rule-2 line, newline included (the current `DELETED_LINE`);
2. `Seven rules govern every change.` → `Six rules govern every change.`;
3. `\n3. **No guesswork**` → `\n2. **No guesswork**`, `\n4. **Worldclass**` → `\n3. **Worldclass**`,
   `\n5. **Best practice**` → `\n4. **Best practice**`, `\n6. **Optimized**` → `\n5. **Optimized**`,
   `\n7. **Production ready**` → `\n6. **Production ready**`.

Do:

- Replace the single deletion in `control.py` and `instructions.py` with one ordered list of (source, replacement)
  pairs and one function that applies it with the exactly-once checks; `instructions.py`'s comparison
  (`only_deleted_line`) becomes "applying the edit to B's text gives C's text". Keep it small and keep 0258's
  structure; name things for what they are.
- Tests: the package-diff test uses a fake B whose target files hold a realistic seven-rule block (all source texts,
  between other lines) and proves C equals the expected six-rule text exactly and nothing else changed; a B missing
  any one source text, or holding one twice, fails without creating C. Adapt the instruction-form tests the same way.
  Add one test that applies the edit to the real B `AGENTS.md` at
  `~/.local/share/nx01/0258-live/control/packages/B/package/AGENTS.md` only if that file exists (skip otherwise),
  and checks the result has rules numbered 1–6 with no `No overengineering` and `Six rules`.
- Update `README.md` rows for `control.py`, `instructions.py` and `test_apparatus.py`.

Done means: `python3 -m pytest -q autoresearch/experiments/0259` passes (report exact output), the 0258 suite still
passes, `py_compile` clean; report the `diff -u` of the real B `AGENTS.md` against your edited text (print it, do not
write it into the repository).
