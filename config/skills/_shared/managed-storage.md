# Managed storage

New allocation and warming modes come from enrollment state alone:

| `~/.devlyn/storage-client.json` | recovery marker | unenroll journal | Mode |
|---|---|---|---|
| absent | absent | not read | standalone (never enrolled) |
| valid | any | not read | managed; a fenced authority refuses |
| invalid or unreadable | any | not read | refuse; repair registration |
| absent | present | verified `retired: true` | standalone (unenrollment complete) |
| absent | present | absent, unreadable or incomplete | refuse; Open Devlyn to repair its storage registration |

An unfinished retirement takes precedence over enrollment; follow its
operation-specific retained-helper resume to reconcile or cancel as named.
The journal `storage-client-unenroll.json` is read no-follow for retirement
recovery and the last two rows. Schema 1, canonical UUIDv7 operation, permanent `storage-client-fence.json`,
matching operation/root/lock identities and Rust's archive ordering/path
validation are required. If native root/lock identities or the home path changed,
completed retirement permits standalone only when `storage`, `control`,
`harness/state.json` and `storage-client.json` are all absent under the current
lifecycle root (checked without following links). Live inventory requires repair.
No repository-wide receipt scan selects mode. Other keys can allocate after
completed unenrollment; a leftover managed key retains its own recovery command.

Existing operations keep their managed identity. Receipts pin the control
identity; current enrollment verifies the helper before allocation. Recovery uses
the current verified `storage-client-recovery/pins.json`, including after uninstall
or unenrollment, and requires its authority binding to match the receipt, except
for a proven moved task: use its unflagged, operation-specific `recover-storage`
resume to release it, retain its files, and archive its receipt under `moved/`. Missing
or invalid pins retain resources and require repair; saved artifacts are never a
fallback. Enrolled checkout preserves
`managed_pending`/`managed_owned` and Rust's `storage-allocation.json` subreceipt.
After an interrupted reply, use the returned `recover-storage` resume. Never
delete managed receipts or replace an unfinished operation ID.

Owner `recover-storage --receipt <receipt.json> --operation-id <saved ID>
--for-removal` fences allocation and reconciles closure and the exact cache set.
Never-published allocations are abandoned. Accepted LOCAL_ONLY, FAILED, and PRs
observed CLOSED without merge share custody/recovery-ref verification and fenced
removal, retaining task branches and a durable terminal delivery. Release writers
with `complete --writers-stopped` first. A queue-produced FAILED checkout is
advanced by `read-tree -m -u <source_sha> <publish_sha>` only when HEAD is at the
attached publish commit and the index and worktree are exactly at source; other
differences refuse as dirty.

Removal-finished receipts with final COMPLETE, LOCAL_ONLY, FAILED or CLOSED
delivery move under `devlyn-completion/retired/`, regardless of scratch status.
Retirement moves scratch and its saved cleanup record with the audit and deletes
nothing. `complete --writers-stopped` saves the writer release there and retries
pending scratch, including an interrupted cleanup with no saved result; the next
allocation retries completed deliveries with released writers. `clean-scratch`
remains available there and never downgrades CLEAN.
Saved managed `complete`, `recover-storage` and `clean-scratch` resumes carry an
operation ID validated under the receipt lock. Without an ID, a locator selects
its active receipt. An ID selects only that operation, including its verified
retired receipt; a mismatched ID refuses. Retired paths also remain usable.
A new allocation may reuse a retired key without disturbing its audit.

Retained submodule repositories in the admin directory block removal even when
the checkout is absent; preserve/publish their source and explicitly resolve
them. Manual checkout removal is advised only after portable source checks and
record preservation succeed; changed or new source requires retention. If native
Windows or unobservable writers then require retention, stop all
writers, remove the task checkout by hand, keep its branch and receipt, then run
the returned owner-removal resume. The absent-tree path completes the fenced
registration removal. Scratch cleanup requires positive allocation closure,
without a cache-removal fence; actual checkout removal owns that fence, including
empty cache sets. Missing helpers or uncertain closure retain resources with a
repair/resume action. Compatible recovery artifacts and Rust's LaunchGate remain
required while managed obligations exist.

Managed allocations currently start cold; `build_dirs` retains each returned cache
and publication lease ID. Managed warming is deferred. Standalone allocations keep
the warming behavior in [task-completion.md](task-completion.md).

For managed receipts, use the saved `clean-scratch` resume with `--operation-id <saved ID>`.

New managed allocations use the recovery ref `refs/devlyn/completed/<id>.<operation>` so branch reuse
preserves earlier recovery refs.
