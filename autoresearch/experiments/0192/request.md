---
complexity: trivial
---
# Recover from a partially copied archive file

The supplied `package/archive_run.py` and sibling helpers are unchanged real
Devlyn source. `package/resolve-bootstrap.py` is a real caller supplied for
inspection; the copied module is the task, not the installed workflow helpers.
`move_artifacts` uses shutil.move and rolls back completed moves. When rename
falls back to copying across filesystems, a copy/metadata/source-unlink failure
can leave the current target behind. Keep the existing shutil.move transport and
its standard copy function; do not replace it with a custom transfer path.
Retry then rejects its own partial archive
as a collision. Fix this in `package/archive_run.py`.

On a synchronous forward file-transfer error (including partial copy, metadata
copy, or source unlink), re-raise the original exception unwrapped, restore every original
artifact byte and permission mode at its original path, remove incomplete output
from this attempted archive, and permit an ordinary retry without manual cleanup.
This applies to the first and later transfers, including nested probe and
state-bound evidence paths. Recovery IO is assumed to succeed. Empty directories
created by this attempt may remain; unrelated destination entries must survive.

Preserve successful same-filesystem rename and cross-filesystem copy/unlink,
file modes, relative layouts, moved-file count and source cleanup. Keep the CLI,
strict JSON/state/report/evidence validation, collision refusal before mutation,
pruning policy and existing self-tests. Pre-existing collisions (including links)
must never be overwritten or removed. An error must not become a success return.
No concurrent writers, adversarial path replacement, process death, disk durability,
rollback-IO failure guarantee or general filesystem confinement is required.
Post-transfer empty-directory cleanup and pruning are outside the new recovery
contract. Do not broaden the public API or add dependencies/options.

Only `package/archive_run.py` and optional `tests/test_regression.py` may change.
All other source, supplied tests, spec files and .gitignore are protected.
Use disposable fixture directories within this checkout; remove test-created
files. Never run `package/archive_run.py` on the checkout's own `.devlyn` or a real user's
archive. C's separately installed workflow helper may archive its own pipeline
state as required; it is not the product under repair. Do not modify or import a
workflow helper as the product implementation.
No network task operations, outside-checkout task writes, or global changes.
The owner handles delivery; local experiment commits are allowed, no publication.

Run `/opt/homebrew/bin/python3 -B -m unittest discover -s tests -v` and relevant
focused regressions. Inspect the real caller for compatibility, without editing it.
