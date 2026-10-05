# Outer-owner task completion

Completion belongs to the outer task owner after source acceptance. It does not
add a phase or change product verdicts, finish-gate/archive authority or worker
isolation. Explicit local-only/no-push instructions win. Otherwise delivery is
authorized by the task scope; no additional approval ceremony is required.

## Allocate before work

Use the caller's DEVLYN_SHARED_DIR. When this reference is opened
directly, bind it to this reference's reader-supplied containing
directory, resolving directory symlinks first. Missing source identity is
BLOCKED:skill-source-unresolved; a missing task-complete.py is
BLOCKED:shared-dir-unresolved. Never select another installation.

Run the bound task-complete.py before committing owner inputs or
starting direct/full work:

```sh
python3 "$DEVLYN_SHARED_DIR/task-complete.py" allocate --repo . \
  --task '<task identity>' --branch '<absent task branch>' \
  --worktree '<absent path>' --repository '<owner/repo>' --remote origin --base main
```

Every task owns a linked worktree; `--worktree` is required. Its baseline is the
exact fetched remote base, independent of the anchor's branch or dirty state;
allocation leaves the anchor's HEAD, index and files untouched. Save the returned
receipt path under the common Gitdir. `reconciled` reports earlier accepted,
PR-delivered tasks whose merged resources were cleaned or retained; it is
informational, so never resume or release a receipt you do not own. Existing
branches/trees cannot be adopted, even when their names look generated. An
interrupted allocation stays blocked for inspection; do not delete its receipt
and enroll the resulting branch. Unreceipted tasks remain owner-managed.

Allocation also returns a receipt-owned `scratch` directory. Put disposable
build intermediates there (for example, set
`CARGO_TARGET_DIR` to `<scratch>/target`). Keep source checkouts, Git data,
lockfiles, reports and restart evidence outside scratch. Do not create unowned
temporary build trees or preserve them by copying them into evidence custody.
Prefer `TemporaryDirectory`/`finally` for short-lived test fixtures.

After waiting for task writers, `complete --writers-stopped` empties this
scratch on delivery returns, including local-only and pending-PR routes. To
release build caches when parking or after a failed run, use:

```sh
python3 "$DEVLYN_SHARED_DIR/task-complete.py" clean-scratch \
  --receipt '<returned receipt.json>' --writers-stopped
```

This empties only the prospectively owned scratch, preserves its directory
identity for interrupted cleanup and later builds, checks live users and reports
the logical byte count separately from actual free disk space. It does not depend on a product PASS or rewrite that verdict.
Unknown historical roots, source/recovery data, shared caches and terminal
history are never adopted or swept. A refused cleanup does not block source
delivery; it stays visible in the handoff with its receipt and retry command
(`CLEANUP_PENDING` after delivered source). No task is described as cleaned
while owned disposable files remain. On resumption, finish any pending scratch
cleanup before allocating more temporary storage; the next allocation also
retries it for completed deliveries with released writers. Rebuild from retained
inputs when needed; cleanup is not an instruction to restart parked work.

## Accept a scoped commit

Direct work: finish actual decisive checks and diff review, stage only the
accepted paths and commit them. The helper never stages product files. Write a
root acceptance file in the checkout (usually ignored `.devlyn/acceptance.json`):

```json
{"kind":"direct","task":"<task identity>","source_sha":"<full commit>","checks":[{"command":"<actual check>","evidence":".devlyn/checks.log"}]}
```

The owner accepts these checks; the helper preserves evidence bytes and does not
claim to have independently proved the assertions. No synthetic pipeline state
or full resolve run is needed to deliver a direct task.

For full resolve, use only its intended successfully archived normal run:

```json
{"kind":"pipeline","task":"<task identity>","source_sha":"<cleanup.post_sha>","run_id":"<exact archived run_id>"}
```

Terminal CLEAN alone is insufficient. Successful VERIFY and terminal precedence,
the run-bound report/digest, clean finish summary and required evidence must
agree. Failed, incomplete and verify-only runs are ineligible. Acceptance binds
exact bytes and source before push; changed acceptance/evidence or subsequent
product commits require a new accepted task, never implicit descendant approval.

Queue drains follow ideate's loop protocol
(`../devlyn-ideate/references/loop.md`): its evidence-derived `loop` result is
bound with `accept` before the queue-only terminal commit is attached with
`attach`, and dependent local tasks allocate from the accepted predecessor's
source. Failed results keep custody and a recovery ref but are never published.

## Deliver and resume

Wait for your children, stop your dev servers and task writers, then leave the
task tree. Make the FIRST completion call from outside it with the installed
helper and `--writers-stopped`; this releases the tree for cleanup after merge:

```sh
python3 "$DEVLYN_SHARED_DIR/task-complete.py" complete \
  --receipt '<returned receipt.json>' \
  --acceptance '<task worktree>/.devlyn/acceptance.json' --writers-stopped
```

Project policy is `git config --local devlyn.completionMode auto|pr`; absent means
`auto`. Invalid local values fail before external effects, even with an override.
Use `complete --mode auto|pr` for one task, or `--local-only`/`--no-push` to honor
the user's delivery restriction. These per-task choices persist in the receipt; `--local-only` is refused once the task ref is pushed.

`pr` pushes the exact accepted task ref and creates/reuses its exact repository,
head and base PR. While OPEN, it cancels owned auto-merge, reports `PR` with its URL
and retains the checkout. Once MERGED by any method, either mode cleans released
resources in that call, on resume or at the next allocation. Default `auto` also requests
`gh pr merge --auto --merge --match-head-commit <accepted SHA>`. Repository
checks/reviews and merge policy remain authoritative: no admin bypass, strategy
fallback or repository setting changes. When the repository disallows merge
commits or refuses the request, delivery reports `PR` with `merge_refused` and
the PR waits for a person. Command success alone never proves merge.

`PENDING` retains the workspace and reports a receipt-based resume command.
`BLOCKED` includes the cause and the same retry path; repair the reported condition
before retrying. Resume reobserves Git/PR state under a per-receipt lock, reuses
the original acceptance, and performs only missing eligible effects. Delivery results remain separate from the
immutable product result; do not rewrite an archived PASS for a delivery error.

## Yield and retain recoverability

Cleanup requires actual matching MERGED evidence; linked-tree removal also
requires the owner's recorded release. OS observation supplements it; neither the receipt
nor a scan guarantees exclusion of future writers. Processes with cwd or open
files inside the tree, inaccessible process state (on Linux, other users'
processes unless run as root), caller cwd inside the tree, dirty/untracked files,
a nested repository or worktree, or changed refs/Gitdir/registration retain
affected resources. Use `git worktree lock` to keep a tree.
On native Windows, locking and file durability are supported, but the helper cannot prove writer cessation and reports `writer observation unsupported on this platform; retain workspace`. Even `--writers-stopped` cannot authorize deletion without that observation: retain the workspace, its task refs and external receipt/custody, report delivery separately, and preserve the receipt-based resume command. A merged delivery therefore reports `CLEANUP_PENDING` (delivery `COMPLETE`) with `workspace_cleanup` naming the reason and resume. Do not kill unknown processes or force worktree removal to make completion pass.

The receipt directory holds byte-verified `custody/`, `manifest.json` and a guarded
`refs/devlyn/completed/<id>` recovery ref. Archive/check evidence is copied there
before publication; removal rechecks it, the recovery ref and the merge commit on base.
Ignored build output and other ignored files are disposable under native
non-force worktree removal. The tree's `.devlyn/` files are byte/mode-verified
and preserved as `<receipt dir>/records/.devlyn`; non-regular files or symlinks
there retain the tree. Partial/corrupt custody or records retain it for repair.

Legacy in-place receipts retire refs only once their task branch is no longer
checked out; their checkout is never modified. Local ref deletion is guarded by
the expected SHA; remote deletion uses an exact force-with-lease solely as
compare-and-delete, never for product publication. A changed remote branch is
retained. Retry uses the external receipt/evidence after removal. Recovery
refs/evidence have no automatic expiry.
