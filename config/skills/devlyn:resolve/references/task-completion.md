# Outer-owner task completion

Completion belongs to the outer task owner after source acceptance. It does not
add a phase or change product verdicts, finish-gate/archive authority or worker
isolation. Explicit local-only/no-push instructions win. Otherwise delivery is
authorized by the task scope; no additional approval ceremony is required.

## Allocate before work

Use the installed `_shared/task-complete.py` from the retained base checkout,
before committing owner inputs or starting direct/full work:

```sh
python3 "$DEVLYN_SHARED_DIR/task-complete.py" allocate --repo . \
  --task '<task identity>' --branch '<absent task branch>' \
  --repository '<owner/repo>' --remote origin --base main
```

This creates and switches to a native task branch. Add `--worktree <absent path>`
only when the owner explicitly chooses a linked checkout; allocation is optional
for worktrees. Save the returned receipt path, outside the task checkout under
the common Gitdir. Existing branches/trees cannot be adopted, even when their
names look generated. An interrupted allocation stays blocked for inspection;
do not delete its receipt and enroll the resulting branch. Pre-existing tasks
remain owner-managed and cannot use this helper retroactively.

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

For a queue drain, resolve returns the acceptance/archive to the queue owner.
Commit the terminal queue transition first, then add
`"queue":{"commit":"<full terminal commit>","file":"docs/specs/queue.md"}` to
acceptance. This commit must have only the verified source as parent and change
exactly the declared queue file. The owner reviews the transition; the helper
does not infer that arbitrary edits to that file are valid queue metadata.
Complete once per item after that commit. Failed items are never published.

## Deliver and resume

```sh
python3 "$DEVLYN_SHARED_DIR/task-complete.py" complete \
  --receipt '<returned receipt.json>' --acceptance .devlyn/acceptance.json
```

Project policy is `git config --local devlyn.completionMode auto|pr`; absent means
`auto`. Invalid local values fail before external effects, even with an override.
Use `complete --mode auto|pr` for one task, or `--local-only`/`--no-push` to honor
the user's delivery restriction. These per-task choices persist in the receipt.

`pr` pushes the exact accepted task ref and creates/reuses its exact repository,
head and base PR, then reports `PR` with its URL and retains the checkout. `auto`
also requests `gh pr merge --auto --merge --match-head-commit <accepted SHA>`.
Repository checks/reviews and merge policy remain authoritative: no admin bypass,
strategy fallback or repository setting changes. A repository that disallows
merge commits fails visibly; disabled auto merge may also reject a pending
request. Command success alone never proves merge.

`PENDING` retains the workspace and reports a receipt-based resume command.
`BLOCKED` includes the cause and the same retry path; repair the reported condition
before retrying. Resume reobserves Git/PR state under a per-receipt lock, reuses
the original acceptance, and performs only missing eligible effects. Delivery results remain separate from the
immutable product result; do not rewrite an archived PASS for a delivery error.

## Yield and retain recoverability

After actual matching MERGED evidence, wait for the owner's actual children,
stop/yield known task writers, and invoke completion with `--writers-stopped`.
For a removable linked checkout, run from outside it using the installed helper
outside that checkout. An OS process observation supplements the owner assertion;
neither the receipt nor a scan guarantees exclusion of future writers. Unknown
writers, inaccessible process state, caller cwd inside the tree, dirty/untracked
files, changed refs/Gitdir/registration or locks retain the affected resources.
On native Windows, locking and file durability are supported, but the helper cannot prove writer cessation and reports `writer observation unsupported on this platform; retain workspace`. Even `--writers-stopped` cannot authorize deletion without that observation: retain the workspace, refs and external receipt/custody, report delivery separately, and preserve the receipt-based resume command. Do not kill unknown processes or force worktree removal to make completion pass.

The receipt directory holds byte-verified `custody/`, `manifest.json` and a guarded
`refs/devlyn/completed/<id>` recovery ref. Archive/check evidence is copied there
before publication; removal rechecks it and source reachability through the merge.
Ignored files in removable trees must be covered by that exact owned evidence
manifest. Unknown ignored data requires explicit owner custody outside the helper;
it never silently archives or deletes arbitrary user content. A partial/corrupt
custody copy blocks cleanup and retains the original for repair.

In-place completion retains the checkout and its ignored user data, switches
safely to updated base, then compare-deletes only its exact owned task refs.
Linked completion uses native non-force removal. Local ref deletion is guarded
by the expected SHA; remote deletion uses an exact force-with-lease solely as
compare-and-delete, never for product publication. A changed remote branch is
retained. Retry after removal uses the external receipt and evidence, so the
removed checkout is not needed. Recovery refs/evidence have no automatic expiry.

Queue drains remain serial. Record source verdict and delivery status separately;
retain pending/PR workspaces. Before advancing, use a separate owned branch from
base; do not put the next item's commits on a retained pending branch. If safe
placement is unavailable, report remaining items pending and stop the drain.
