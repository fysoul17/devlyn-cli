I'll confirm the commit against both r7 reviews: the named hiding paths, the 0600 installer marker, and that the existing anchor checks stayed in place.The reviews name index flags and attribute/filter hides. I'll read `fecccb04` and the regressions that are supposed to close them.`fecccb04` closes the r7 anchor hides. The out-of-scope check reads raw `packet.tree` bytes, folds regular-file modes to Git's `100644`/`100755` (any execute bit; symlinks stay `link:`), treats index tags `h`/`S`/`s` as damage, and still runs `--cached` against `allocation_sha` plus the raw submitted-snapshot compare.

Each named hide now has a regression that passes only because of that check. On parent `0d5c7188` the worktree `git diff` is empty, so `done_check` did not report damage:

- `test_index_flags_and_hidden_content_edits_fail` covers assume-unchanged, skip-worktree, and both, including a flag with unchanged bytes. `core.ignorestat` is that same bit.
- `test_index_flag_on_new_out_of_scope_tracked_path_fails` covers a new out-of-scope path. An in-scope flag still passes.
- `test_clean_filter_hidden_content_edit_fails` attaches `filter.hide-damage.clean` to `git show <allocation>:<path>` through `.git/info/attributes` and asserts `git diff` is empty. Raw bytes also cover a `process` filter and `core.attributesFile`, which only affect that diff.

The installer marker passes. `writeInstallMarker` and the instruction files are created at `0600`, while the baseline checkout is `644`. `git_mode` maps both to `100644` when the bytes match. `test_tracked_file_installer_permissions_pass` expects no failure.

Content edits, deletion, `744`/`654`/`645` with `core.filemode=false`, symlink and directory replacement, and staged-only edits are still failures. This pass inspected those tests and did not re-run the suite.

VERDICT: SHIP
