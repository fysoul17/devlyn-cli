# Read-only task history inventory

Implement only the visible-listing requirement R6 from the existing planned
`devlyn-history-lifecycle` feature, on the supplied real task-complete source.
The feature originated in disk exhaustion from retained task evidence. This slice
must let an operator see ownership and logical size before deciding what to retain.
Do not implement deletion, retirement, reconciliation, bootstrap changes or resolve.

Add `python3 -B config/skills/_shared/task-complete.py history --repo <checkout>`.
It works in a normal Git checkout and a linked worktree, using Git's common directory
for receipts and the requested checkout for `.devlyn` contents. It requires neither a
remote nor a checked-out task branch. Preserve existing commands and self-tests.

Print one JSON object to stdout and exit 0 on success, with exactly these fields and entry/group fields (no extra keys):

* `runs`: groups for direct nonsymlink directories named `rs-*` in `.devlyn/runs`.
  Read each `pipeline.state.json`, group by `task.receipt_id`, and emit each group as
  `{"receipt_id": id-or-null, "status": status, "runs": [{"path": relative-path,
  "logical_bytes": integer}], "logical_bytes": sum}`. Absent/null `task` or absent/null
  `receipt_id` means the null group with status `untasked`. A nonnull id must be a
  nonempty single safe path segment (neither `.` nor `..`, no slash, backslash or NUL).
  Its receipt is `<common-git-dir>/devlyn-completion/<id>/receipt.json`;
  absent receipt means `receipt-missing`; otherwise copy its `status` (null if unset).
  Other `runs` names are outside this listing, including `terminal_*` and `run_*`.
  Nonsymlink non-directory `rs-*` entries are ignored. Likewise ignore nonsymlink
  non-directory entries in `devlyn-completion` and receipt directories without
  `receipt.json`; symlink cases still fail as specified below.
* `task_evidence` and `programs`: all direct children of the respective `.devlyn`
  directories, as `{"path": relative-path, "logical_bytes": integer}` entries.
* `pending_reconcile`: all receipts in the common directory whose
  `reconcile.status` is `PENDING`, including ones belonging to other linked worktrees,
  as `{"receipt_id": directory-name, "path": common-dir-relative-receipt-path,
  "reason": reconcile.reason-or-null, "logical_bytes": receipt-file-size}`.
* `unowned_artifacts`: top-level `.devlyn` entries not written by the CLI, using
  the same path/bytes entries. CLI names are the current `archive_run.PER_RUN_PATTERNS`
  (glob matching, not literal names), `runs`, `probes`, `process-evidence`,
  `engines.json`, `ideate-draft.md`, `task-evidence`, `programs`, and top-level names
  containing this checkout's receipt-bound evidence paths. Those paths are the
  keys of an existing receipt's `files` mapping; include only safe relative paths
  under `.devlyn` and receipts with `worktree` equal to the requested checkout's
  canonical path. A receipt for another checkout must not hide this one's artifacts.

All `path` values use forward slashes and are relative to the checkout, except the
explicit common-dir-relative receipt paths. Sort entries by path; groups put null
first then ids lexically; pending receipts sort by id. Empty/missing history roots
yield empty arrays for that root; pending receipts are still listed when `.devlyn` is absent. No `.devlyn` or receipt directory is created by listing.

Logical bytes are the sum of regular-file sizes, counting each pathname once
(including hardlink aliases), not allocated disk blocks or directory sizes.
Symlinks and other special files contribute zero and are never followed. A symlink
inside a listed tree or as a task-evidence/program/unowned entry is listed with this
rule. A symlink used as `.devlyn`, a listing container (`runs`, `task-evidence`,
`programs`, `devlyn-completion`), an `rs-*` target, a receipt directory, or a JSON
metadata file must instead visibly fail; do not traverse it. Existing containers
must be directories. Missing run state is an error, not an untasked run.

State and receipt JSON must be objects and use the existing strict JSON reader.
If present and nonnull, `task` and `reconcile` must be objects, `files` must be a
mapping, and a receipt `status` must be a string or null. Malformed JSON, duplicate
keys, non-finite constants, invalid ids, structural type errors, unreadable required metadata/directories
and filesystem errors produce nonzero exit and JSON on stdout `{"status":"BLOCKED",
"reason": nonempty-string}`. Do not suppress errors into apparently complete output.

Listing must not change any files, links, permissions, Git refs or receipt contents.
Access times are excluded. No network, dependencies, locks or writes are required.
Concurrent mutation during listing is outside this bounded slice; no snapshot or
atomicity claim is required. Do not add flags or modify unrelated lifecycle behavior.
Only `task-complete.py` and optional `tests/test_regression.py` may change.
Run the supplied smoke tests and the existing task-complete self-test.
