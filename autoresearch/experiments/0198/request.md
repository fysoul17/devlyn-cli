# Bind new run state to its existing task receipt

Implement the pending history-lifecycle R1 slice on the supplied real bootstrap.
An operator must be able to associate a new run with its prospectively owned task,
without adopting a pre-existing branch or reviving a finished task. No lifecycle
cleanup, reconciliation, inventory, allocation, new flags or resolve workflow.

Every newly written pipeline.state.json has `task`: either null or exactly
`{"receipt_id": "<id>"}`. Under the existing admission lock, before archiving a
prior run or writing .devlyn outputs, inspect only the receipt at
`<git-common-dir>/devlyn-completion/<sha256(current-branch UTF-8)[:24]>/receipt.json`.
Use the actual Git common directory, including for linked worktrees. Detached HEAD
or absent receipt means null. Do not scan other receipts or require a GitHub remote.

The receipt is strict JSON (use the existing strict reader) and must be an object.
A present receipt must have string `branch` and `worktree` fields. Compare branch
to the actual branch and worktree to the canonical bootstrap root as exact strings.
A valid object for a different branch or worktree means null, even if terminal or
interrupted. For a matching receipt:

- `allocation == "owned"` is required; otherwise block.
- `id` must equal the directory's computed id; otherwise block.
- `status`, when present, must be string or null; `local_only`, when present, must
  be boolean; `acceptance`, when present, must be object or null. Other types block.
- COMPLETE or ABANDONED blocks. LOCAL_ONLY (status) or `local_only: true` blocks
  only when `acceptance` is a nonnull object, including an empty object. A local-only
  receipt without bound acceptance is still usable. Absent/null status is usable.
- Otherwise stamp the computed id. Never interpret the receipt's `task` as run
  ownership metadata. The real allocator stores a task-description STRING there;
  the new pipeline state's `task` is a DIFFERENT field with an object/null schema.
  Extra receipt fields, including task description, are preserved and ignored.

Missing devlyn-completion, id directory or receipt.json means null. Existing
containers must be directories and the receipt must be a regular file. Symlinks
(including dangling links) at either container or receipt.json block without being
followed. Invalid JSON, duplicate keys, nonfinite constants, structural errors,
unreadable receipt or filesystem errors block visibly, never become null silently.
For detached HEAD skip receipt lookup altogether. Concurrent receipt edits are
outside this bounded slice; no new locking protocol or snapshot claim is requested.

A block uses existing CLI JSON (`ok:false`, nonempty `BLOCKED:` reason and detail)
and exits nonzero. It must precede any archival or .devlyn write: existing .devlyn
bytes, modes and paths stay unchanged and an absent .devlyn stays absent. Preserve
receipt bytes/modes, Git refs/index and source files on success and refusal. The
existing bootstrap admission-lock file and its normal acquisition are allowed.

Apply to free-form, spec and verify-only modes. Preserve current source staging,
prior-run admission and archive behavior and engine flags. The existing self-test
exact-state expectation gains `task: null`; preserve every other assertion without
removal or weakening. Adding new tests is allowed.
Only config/skills/_shared/resolve-bootstrap.py and optional tests/test_regression.py
may change. Run supplied tests and resolve-bootstrap.py --self-test. Invoking this
deterministic helper in isolated test repos is not a resolve workflow execution.
This task does not change schemas/readers elsewhere or ship the full R1 feature.
