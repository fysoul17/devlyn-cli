# Loop protocol

`drain` runs the queue serially. Each eligible task gets an owned worktree, committed inputs, one executor exchange, evidence-derived acceptance, a queue-only terminal commit and delivery. The executor works under the installed methodology (the CLAUDE.md/AGENTS.md instruction block); the loop adds no phase graph, reviewer quota, engine router or restart cycle. Formats: [package-format.md](package-format.md). Allocation, custody, delivery and cleanup follow the completion contract in `$DEVLYN_SHARED_DIR/task-completion.md`.

## Commands

```sh
python3 "$DEVLYN_SKILL_DIR/scripts/queue.py" status --repo .
python3 "$DEVLYN_SKILL_DIR/scripts/queue.py" drain --repo . [--local-only] [--worktree-root <dir>] -- <executor argv containing {packet}>
```

Both print one JSON object; exit 1 is `BLOCKED` with a `reason`.

- `status` is read-only: reconciled counts (`pending`, `active`, `accepted`, `failed`, `blocked`, `legacy_pending`), the `next` task, `blockers`, and deliveries still pending with their resume: drain again until the terminal commit is attached, then `task-complete.py complete --receipt <receipt>`.
- `drain` ends `DRAINED` (nothing pending), `WAITING` (pending work waits on a delivery, or legacy rows need planning) or `BLOCKED` (conflict, invalid input or a recovery blocker). Progress lines `devlyn-loop: <task>: <event>` go to stderr.
- `--local-only` (alias `--no-push`) keeps the loop local. A manifest `delivery: local-only` and any earlier local receipt of the loop keep that restriction for later drains. A local loop needs no remote; nothing is fetched or pushed. A task whose PR is already pushed is refused, never rewritten to local.
- Worktrees default to `<repo parent>/<repo name>.devlyn/<loop-id>/<task-id>`.

The host supplies the executor and maps its configured engine to the argv; the loop has no model preference. Each `{packet}` in the argv is replaced by the task packet path. The executor runs with the task worktree as its working directory and the null device as stdin; its stdout and stderr are appended to `executor.stdout` and `executor.stderr` in the packet's `evidence_dir`, never a pipe.

`<common Gitdir>/devlyn-loops/drain.lock` is held for the controller's lifetime, so a second drain from any worktree of the repository is refused. `queue.lock` is held only to read the queue, append and make terminal transitions, so `add` works during a drain.

## Steps

1. **Reconcile.** Read the queue, every `<common Gitdir>/devlyn-completion/*/receipt.json` and their recovery refs. A row's identity, its receipt's branch `devlyn/<loop-id>/<task-id>`, the recovery ref (equal to the receipt's `publish_sha`, or to its validated terminal commit while that attachment is unfinished), the terminal commit's mark and, while active, the committed contract digests must agree. A receipt's terminal result supplements a stale `[ ]` row. Two receipts for one task, a terminal row contradicting its receipt or an interrupted allocation stop selection with the conflict named. An active task whose contract or expected acceptance changed in the repository, also when that text is now missing or invalid, becomes `[F] inputs-changed` without executing again, its workspace retained; other work continues and the revision is planned as a new task. A pending task whose package text fails validation waits with that error, as do its dependents; independent tasks continue. Unsettled receipts (active, terminal commit unattached, or delivery not final) resume before any new allocation.
2. **Select** the earliest pending row whose prerequisites are accepted with a receipt in every mode (a hand-written `[x]` never counts) and, for `auto`/`pr`, delivered (merged). A failed or blocked prerequisite makes its dependent `[F] blocked-prerequisite:<id>` without invoking the executor; that derived mark is proven by the prerequisite's receipt and travels into later checkouts and the report. A prerequisite awaiting delivery leaves its dependent pending while independent work continues. Legacy rows wait for `add --materialize`.
3. **Allocate** a new owned worktree on the absent branch `devlyn/<loop-id>/<task-id>` with `task-complete.py allocate`. First, `.devlyn/` must be ignored in the commit the task starts from (a committed `.gitignore` entry there, or `<common Gitdir>/info/exclude`); otherwise nothing is allocated and the drain blocks naming both fixes.
   - Local: the first task uses `--local-base <add commit>`, the commit `add` made with the package and rows (recorded in `<common Gitdir>/devlyn-loops/<loop-id>/added.json`); later tasks use `--from-receipt <latest accepted receipt of the loop>`, which starts from that receipt's exact `source_sha`, never its terminal commit, current HEAD or workspace. Every prerequisite's accepted source must be an ancestor of that frontier; divergent dependencies need a planned integration task, because the driver never merges. A failure leaves the frontier unchanged.
   - `auto`/`pr`: `--start` the refreshed remote base once a merged task has brought it the package, else the add commit, which the task's PR then carries. The start must contain each prerequisite's merge commit, checked before allocation and again before every execution or resume. A squash merge needs no original-source ancestry.
4. **Commit scoped inputs** on the owned branch before any executor write, only what the allocation base lacks: `meta.md`, the task's `spec.md` and `spec.expected.json`, and `docs/specs/queue.md` as the base's queue with this task's row and, for a local loop, the receipt-proven terminal rows of the same loop (typically a predecessor's `[x]`), in queue order with every other byte unchanged. A base that already carries them gets no inputs commit; unrelated product commits stay out.
5. **Exchange one packet.** Write `<receipt dir>/packet.json`, then run the executor. An executor that exits without writing its submission is recorded as `blocked-infrastructure`; one that cannot start blocks the drain.
6. **Derive acceptance** with `acceptance.py accept`. It binds the committed contract to the packet digests; requires the candidate to be the owned branch head with HEAD checked out on that branch, to descend from the inputs, to leave the package and queue untouched and to have a clean worktree; executes each declared command on that source, recording raw stdout/stderr and exit, timeout or spawn outcomes (a runner result is reused only when it is wholly clean — no reasons, so no failed check and no source change during its checks — for the same source and contract digests, with unchanged streams); evaluates the file and diff guards against the inputs; confirms the source is unchanged; checks review records; and writes `.devlyn/loop/acceptance.json`. Missing checks, missing review coverage and open binding findings cannot produce `[x]`, and acceptance weakening is not repair. This establishes command outcomes and evidence completeness, not a reviewer's semantic judgment; deliberate evidence forgery is outside the trust model.
7. **Bind before terminal metadata.** `task-complete.py accept --receipt <receipt> --acceptance <worktree>/.devlyn/loop/acceptance.json` takes evidence custody and points the recovery ref at the source. Failed results are bound the same way; they never become a frontier or a publishable product.
8. **Commit the terminal transition** under the queue lock: one commit whose sole parent is the bound source and whose only change is this task's row (`[x]`, or `[F] — <first reason> (receipt <id>)`), validated as the only legal transition. Then `task-complete.py attach --receipt <receipt> --commit <terminal> --file docs/specs/queue.md` records it separately from the source and moves the recovery ref to it.
9. **Deliver** with `task-complete.py complete --receipt <receipt> --writers-stopped`, plus `--local-only` or `--mode auto|pr`. Local-only keeps source, custody and the recovery ref with no remote effect. `auto`/`pr` publish the terminal commit under the completion contract; a pending or refused delivery keeps product acceptance, resources and a resume command. Where writer cessation cannot be observed, a merged delivery settles (`COMPLETE`) with its workspace, task ref and custody retained and reported under workspace cleanup; retained cleanup never blocks the queue. Failed products are never published. The receipt's `delivery` field checkpoints the latest outcome. A local chain is never turned into stacked PRs; publishing it requires integrated acceptance of the actual publication candidate.
10. **Recover** from durable state only:

    | Interrupted | Resume |
    |---|---|
    | During allocation | A receipt without `allocation: owned` blocks; it is never adopted. |
    | Inputs commit | A branch head equal to the expected inputs tree is adopted; anything else blocks. |
    | During execution | Each attempt's start is recorded before its spawn and its exit after it. A start without an exit waits until task-complete observes no process using the worktree, then adopts the submission that executor wrote or runs the executor again; where writers cannot be observed (native Windows) the task becomes `[F] interrupted-unobservable` with its workspace retained, its dependents become prerequisite-blocked and independent work continues. Exactly-once execution is not promised. |
    | During checks | Acceptance reruns; incomplete evidence stays unreferenced. |
    | Accepted, before terminal commit | Only the missing transition is created. |
    | Terminal committed, before attachment | The commit is validated and attached, also when attachment already moved the recovery ref; nothing reruns. |
    | Terminal committed, before delivery | Only the missing delivery effects run. |
    | After delivery, before cleanup | Owned cleanup resumes; the product verdict is unchanged. |

11. **Report** to `<common Gitdir>/devlyn-loops/<loop-id>/drain-report.md` after every drain: per task the product result and reason, receipt, evidence custody and recovery ref, allocation base, accepted (or unaccepted) source, terminal commit, delivery status, PR URL and resume command, assumptions and unresolved questions, the retained worktree and branch, and workspace and scratch cleanup. Whole-loop acceptance is reported separately over the manifest's complete task set: every task needs receipt-backed acceptance, including the integration task's assembled-product check on the final frontier; a manifest task missing from the queue is reported as not yet run. `Bring into` names the command that brings the accepted frontier into the branch the loop was added on: a local loop's `git merge --ff-only <frontier branch>`, or a plain merge once that branch has moved since the add commit; for `auto`/`pr`, a pull after delivery, a fast-forward.

## Executor exchange

The packet (`<receipt dir>/packet.json`) carries everything a fresh executor needs:

| Field | Meaning |
|---|---|
| `task`, `title`, `kind` | Queue identity and deliverable description. |
| `worktree`, `branch`, `receipt`, `scratch` | Absolute owned worktree, branch, receipt and disposable build directory. |
| `allocation_base`, `inputs_sha` | Allocation base and the committed-inputs commit. |
| `contract`, `expected`, `meta` | `{path, sha256}` of the committed task contract, expected acceptance and meta-prompt. |
| `requirements`, `review_requirements` | Requirement IDs and those needing review evidence. |
| `shared_constraints` | The meta-prompt's `Constraints and exclusions`. |
| `dependencies` | `{task, receipt, source_sha}` of each accepted prerequisite. |
| `methodology` | `{path, sha256}` of the installed instruction files at the inputs commit. |
| `delivery` | `local-only`, `auto` or `pr`. |
| `evidence_dir`, `runner` | Where loop evidence lives (`<worktree>/.devlyn/loop`, ignored by Git) and the runner argv. |
| `submission`, `obligations` | Where to write the submission, and the completion obligations. |

Run `runner` (`acceptance.py run --packet <packet>`) on the committed candidate before review. It prints `{"result": <path>, "passed": ..., "reasons": [...]}`; listing a wholly clean result (empty `reasons`) lets drain reuse its outcomes. Then write the submission:

```json
{
  "schema_version": 1,
  "task": "<identity>",
  "source_sha": "<candidate commit on the owned branch>",
  "runner_results": ["<worktree>/.devlyn/loop/runs/<n>/result.json"],
  "reviews": ["<worktree>/.devlyn/reviews/<name>.json"],
  "findings": [{"id": "F1", "disposition": "resolved", "evidence": "<what changed>"}],
  "cleanup": "<residue removed, output retained>",
  "handoff": "<state a successor needs>",
  "assumptions": ["<each assumption, recorded once>"],
  "blockers": [],
  "summary": "<informational only>"
}
```

`schema_version`, `task` and `source_sha` are required. A blocker `{"kind": "failed" | "needs-review" | "blocked-infrastructure", "detail": "<concrete question or cause>"}` records `[F]` with that reason and runs no checks; material ambiguity becomes `needs-review`, never a weakened acceptance. The summary is never evidence.

## Review records

Each `review_requirements` ID needs review evidence: a JSON record under `<worktree>/.devlyn/`, listed in the submission's `reviews`, in this shape:

```json
{
  "schema_version": 1,
  "kind": "devlyn-review",
  "task": "<identity>",
  "engine": "<engine>",
  "model": "<exact model id>",
  "source_sha": "<reviewed commit>",
  "contract_sha256": "<packet.contract.sha256>",
  "expected_sha256": "<packet.expected.sha256>",
  "requirements": ["R3"],
  "findings": [{"id": "F1", "binding": true, "disposition": "resolved", "requirement": "R3", "summary": "<finding>"}]
}
```

A record counts only when it binds this task, the candidate source and both contract digests; any other well-formed record is reported under `ignored_reviews` (a source change invalidates earlier reviews). A listed review or runner record that is unreadable or not this shape fails acceptance with its path named. The counted records' `requirements` must cover `review_requirements`. Each finding's `disposition` is `open`, `resolved` or `rejected` (`rejected` needs a `reason`); an open binding finding blocks acceptance. The loop requires no particular engine or number of reviewers; the installed methodology decides who reviews.
