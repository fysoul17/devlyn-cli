# Outer-owner task completion

Completion belongs to the outer task owner after source acceptance; it does not
change product verdicts or worker isolation. Direct work edits the current
checkout, then delivers each completed, verified request with attributable
changes. Finish the whole request, including steering received before acceptance;
internal subtasks, messages and conversation end are not delivery boundaries.
Honor explicit batching or delivery holds; otherwise deliver completed requests
without waiting for later requests.

Without a delivery instruction, use project policy below, default `auto`. A bare
commit request uses `--local-only`, a PR request `--mode pr`, and a merge request
`--mode auto`. Local-only/no-push restrictions prevent publication; no-commit or
just-edit instructions skip delivery. Existing session-wide restrictions remain
in force until changed. Read-only work, unchanged work and incidental generated
files do not trigger delivery. An ideate drain delivers every task.

## Concurrent writers

When other sessions or agents are known to write this checkout (the user says
so, or you see them), allocate a worktree below before editing. Changes present
at the start are the user's work in progress: preserve them, and continue unless
their ownership or the task's dependence on them is unclear. Re-read a file
before overwriting it, and check `git status` and the diff at verification and
commit points. On changes you cannot explain, stop writing to the shared
checkout and ask whether to continue there or isolate. With no one to ask, move
only your own edits, and only when the task's context can be rebuilt in the
worktree; otherwise leave the checkout as it is and report the task blocked.
Isolation changes the work location, not delivery scope. Allocate for the
resolved delivery policy and reuse that worktree when suitable. Isolation
without delivery uses `--local-base`. A local receipt remains local; later
publication requires a fresh publication allocation, candidate and acceptance.

## Allocate for delivery or isolation

Use the caller's DEVLYN_SHARED_DIR. When this reference is opened
directly, bind it to this reference's reader-supplied containing
directory, resolving directory symlinks first. Missing source identity is
BLOCKED:skill-source-unresolved; a missing task-complete.py is
BLOCKED:shared-dir-unresolved. Never select another installation.

For direct delivery, run the bound task-complete.py after completing the request's
edits and checks, before committing the delivery candidate. Allocate before
editing when concurrency requires isolation; if isolation is unavailable, do
not write to the shared checkout. Queue drains retain their allocation order.

```sh
python3 "$DEVLYN_SHARED_DIR/task-complete.py" allocate --repo . \
  --task '<task identity>' --branch '<absent task branch>' \
  --worktree '<absent path>' --repository '<owner/repo>' --remote origin --base main
```

Every delivery allocation owns a linked worktree; `--worktree` is required.
A publication allocation normally starts at the exact fetched remote base,
independent of the anchor's branch or dirty state, and leaves the anchor's
HEAD, index and files untouched. For a commit request, local-only work or
isolation without publication, use `--local-base` with the exact current HEAD
and omit `--repository`/`--remote`. Nothing is fetched or pushed; complete with
`--local-only` only when committing is allowed.

When delivery is implicit and no GitHub origin is configured, use the existing
local-only route and report `LOCAL_ONLY`, the commit and why no PR/merge occurred.
An explicit PR/merge request remains blocked. Authentication, network and
configuration failures are not grounds for this fallback.

After local completion or confirmed PR merge, reconcile the original checkout
only when its branch and changes remain understood and can be preserved.
Use `git merge --ff-only <task branch>` for local delivery; after remote delivery,
fetch and use `git merge --ff-only <remote>/<base>` on the base branch.
Do not switch branches, create a reconciliation merge commit or discard WIP
to force this step. If reconciliation is unsafe, retain and report the edits,
delivered result and remaining bring-in action.

Save the returned receipt path under the common Gitdir. `reconciled` reports earlier accepted,
PR-delivered tasks whose merged resources were cleaned or retained; it is
informational, so never resume or release a receipt you do not own. Existing
branches/trees cannot be adopted, even when their names look generated. Nor
can a receipt that never reached `allocation: owned`: remove its worktree and
branch if present, delete its receipt directory, then allocate again.
Unreceipted tasks remain owner-managed.

Copy attributable task edits into the allocated worktree as a patch, never a
stash. Establish attribution from the pre-edit contents and starting Git state,
including staged, unstaged and untracked work. A path-scoped diff against HEAD
is suitable only when every included change belongs to this task and its
prerequisites exist in the candidate baseline. Otherwise construct the task-only
delta; if attribution or independence from unshipped work is unclear, preserve
the checkout and report delivery blocked.

Review the resulting candidate diff and verify that candidate. Reuse prior
check evidence only when the checked source and relevant execution inputs are
unchanged; changed bases, conflict resolutions or other relevant differences
require the affected checks again.

Keep the original edits through pending or failed delivery. Remove copied edits
only as part of safe reconciliation after local completion or confirmed merge,
after rechecking their current ownership and contents. Preserve all other work
and report anything left behind.

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

In the allocated worktree, finish the candidate's decisive checks and diff
review, then stage and commit only accepted task changes. The helper never
stages product files. Write a
root acceptance file in the checkout (usually ignored `.devlyn/acceptance.json`):

```json
{"kind":"direct","task":"<task identity>","source_sha":"<full commit>","checks":[{"command":"<actual check>","evidence":".devlyn/checks.log"}]}
```

The owner accepts these checks; the helper preserves evidence bytes and does
not independently prove the assertions. Acceptance binds exact source and
evidence before publication. Direct `complete` binds acceptance itself; no
separate `accept` call is needed.

Changed accepted source or evidence requires a new accepted task, never implicit
descendant approval. Resume an existing receipt only for its unchanged candidate.
After merge, implement follow-ups from the updated base. An additive follow-up
depending on an open PR waits for that predecessor to merge.

If a correction invalidates an open candidate, run `complete --mode pr` against
its unchanged receipt to cancel owned auto-merge, then reobserve the PR. If it
remains open, close it as superseded and retain its receipt and custody; do not
resume its delivery. Allocate a replacement from the current remote base,
include only the still-needed task changes and correction, and verify and
accept it anew. If the predecessor has merged, make a new follow-up instead.

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
`BLOCKED` names the cause and retry action; repair that condition before retrying.
Resume reobserves Git/PR state under a per-receipt lock, reuses the original
acceptance and performs only missing eligible effects.

Verification and delivery obey the session's actual permissions. When an
operation needs unavailable approval, finish permitted work, preserve the edits
and evidence, and report that operation and its retry action. Before allocation,
identify the original checkout and outstanding operation; after allocation,
include the receipt-based resume command. Headless execution neither waives
permissions nor silently changes delivery policy.

Report verification, delivery and checkout reconciliation separately. A delivery
error does not rewrite an accepted product result; unperformed verification
must never be reported as accepted.

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
`refs/devlyn/completed/<id>` recovery ref. Check evidence is copied there
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
