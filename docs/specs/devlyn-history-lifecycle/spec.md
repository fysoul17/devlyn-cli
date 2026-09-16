---
id: "devlyn-history-lifecycle"
title: "Retire finished task history and forbid unowned .devlyn artifacts"
kind: feature
status: planned
complexity: high
depends_on: ["task-completion"]
---

# Retire finished task history and forbid unowned .devlyn artifacts

## Context

On 2026-09-16 the data volume hit 100% (ENOSPC); `.devlyn/` across ~40 repos held 84 GiB.
The CLI owns only a small part of it, but no CLI rule ties deletion to the moment work is
finished: `prune(keep=10)` counts archives and can delete a NEEDS_WORK retry trail, never
touches incomplete attempts, and agents create ad-hoc top-level folders with no owner at all.
The user's goal: when a task is finished and its history is no longer needed, it is cleaned up
properly and without mistakes. Decisions and their 3-seat review live in `decision-review/`
(`synthesis.md` is authoritative for D1, D2, forks F1–F10 and the round-2 answers CLI-1–4).

## Requirements

- [ ] **R1 Task identity on runs.** `resolve-bootstrap.py` writes a top-level `task` field into new pipeline state: `{"receipt_id": "<id>"}` when `<git-common-dir>/devlyn-completion/<sha256(branch)[:24]>/receipt.json` exists for the checked-out branch with `allocation: "owned"`, the same `branch`, and `worktree` equal to the bootstrap root; otherwise `null`. A matching receipt that is interrupted (`allocation != "owned"`) or already terminal (COMPLETE, ABANDONED, or LOCAL_ONLY with bound acceptance) blocks admission with a visible `BLOCKED:` reason and writes nothing. Readers accept absent/`null` for legacy state; `state-schema.md` documents the field.
- [ ] **R2 Remove count-based pruning.** `archive_run.py` no longer has `prune()` or `--keep`; `resolve-bootstrap.py:221` no longer prunes after archiving a prior run. Archive and bootstrap never delete archived runs. The stale "last 10 completed runs" text is removed from `archive_run.py`'s docstring, `devlyn:resolve/SKILL.md` (Archive step) and `state-schema.md` (Archive contract).
- [ ] **R3 Retire task history at the task terminal.** `task-complete.py` retires the task's history at exactly three terminal events: `complete` reaching COMPLETE; `complete --local-only` once acceptance is bound (a first local-only call that supplies `--acceptance` binds it with the same validation and custody as publish routes before reporting LOCAL_ONLY; local-only without acceptance keeps today's behavior and retains history); and `abandon` (R5).
  - Retirement set: every direct child of `<checkout>/.devlyn/runs/` named `rs-*` whose `pipeline.state.json` has `task.receipt_id` equal to the receipt id — including incomplete, BLOCKED and NEEDS_WORK attempts — plus `<checkout>/.devlyn/task-evidence/<receipt id>/` (`.devlyn/tasks/` is devlynd's, `crates/devlynd/src/run_dir.rs:153-156`). Nothing else: not untagged or other-task runs, not `terminal_*`/`open_*`/`run_*`, not `programs/`, not branches, refs, custody or the recovery ref.
  - Ordering: linked COMPLETE retires the non-accepted attempts before the ignored-content check (`task-complete.py:535-536`) so they no longer block native removal, and the accepted run leaves with the removed worktree after custody verification; in-place COMPLETE retires after `status: COMPLETE` is recorded (`:576`); LOCAL_ONLY retires after bind and custody. While `.devlyn/pipeline.state.json` at the checkout root names this receipt, nothing is retired.
  - Crash safety: the receipt records the exact targets before any change; each target is renamed to a tombstone in its parent, then removed without following links; resume finishes only recorded tombstones. After retirement, later `complete` calls verify custody and never require retired files in the worktree (today `:301-302`).
  - Safety preconditions: hold the checkout's bootstrap admission lock (`resolve-bootstrap.py:363`) non-blocking for selection and removal; refuse a redirected `.devlyn`, `runs`, target or ancestor, a mounted filesystem inside a target, and live users reported by the existing writer check (`task-complete.py:413`).
  - Outcome: success adds `history: {status: "RETIRED", runs: [...], logical_bytes_removed}`. Any refusal adds `history: {status: "RETAINED", paths, reason, resume}`, sets overall status `CLEANUP_PENDING`, leaves the delivery status and `product_verdict_unchanged: true` intact, and deletes nothing it did not record.
- [ ] **R4 Custody keeps binding files only.** Pipeline acceptance still validates and digests the full accepted run exactly as today, and the receipt keeps sha256/bytes/mode for every accepted file. `custody/` and `manifest.json` hold only the binding set: the acceptance file, the archived run's `pipeline.state.json`, `final-report.md`, `finish-gate.summary.json`, `verify-merge.summary.json`, and the bound spec/criteria/expected files. Direct acceptance custody is unchanged. Resume and cleanup verify custody against that set. Existing receipts are not rewritten.
- [ ] **R5 Explicit abandon.** `task-complete.py abandon --receipt <receipt> --writers-stopped` is refused with a visible reason once acceptance is bound or the task ref was pushed (those tasks finish through `complete`). Otherwise it retires history per R3, empties scratch with the existing scratch cleanup, and records `status: ABANDONED`; branch, worktree, commits and recovery ref are untouched and reported as retained. Queue `[F]` and outer-loop exhaustion never abandon implicitly.
- [ ] **R6 Visible listing.** `task-complete.py history --repo <checkout>` prints JSON and modifies nothing: `.devlyn/runs/rs-*` grouped by `task.receipt_id` with the receipt's status (`untasked` when the field is absent/null, `receipt-missing` when no receipt exists), `task-evidence/*`, `programs/*`, receipts whose `reconcile` is pending (R10), and top-level `.devlyn` entries the CLI does not write (R7), each with logical bytes.
- [ ] **R7 New top-level names are reported at completion.** `allocate` records the top-level `.devlyn` names of the task checkout in the receipt. At each terminal event, names present now but not at allocation and not written by the CLI itself are reported as `unowned_artifacts` and the result is `CLEANUP_PENDING`; they are never moved, adopted or deleted. CLI-written names are exactly: `archive_run.PER_RUN_PATTERNS` (`archive_run.py:29-107`), `runs`, `probes` (`spec-verify-check.py:238`), `process-evidence` (`process-evidence.py:254`), `engines.json` (`role-config.py:128`), `ideate-draft.md` (`devlyn:ideate/SKILL.md:100`), the receipt-bound acceptance and checks evidence paths (`task-completion.md:58-61`), `task-evidence` and `programs`. No devlyn-os name list exists or is synced; a name devlyn-os creates during the task is reported like any other (accepted false positive, CLI-2). Receipts without the recorded snapshot report the check as not applicable.
- [ ] **R8 Program evidence.** Evidence shared by several tasks lives in `.devlyn/programs/<program_id>/`; task retirement never touches it and nothing expires it. `task-complete.py close-program --repo <checkout> --program <id> --writers-stopped` is the only removal path: a single safe path segment, the same lock/redirect/mount/writer/tombstone rules as R3, and a `RETIRED` or `RETAINED` result with resume.
- [ ] **R9 Contract text says where things go.** `task-completion.md` replaces "Keep … reports and restart evidence outside scratch" with `.devlyn/task-evidence/<receipt id>/` (task-bound) and `.devlyn/programs/<program_id>/` (cross-task); replaces the custody description with the binding set; replaces "Recovery refs/evidence have no automatic expiry" with "the recovery ref and binding custody have no automatic expiry; task history is retired at the task terminal"; and adds `abandon`, `history`, `close-program` and `reconcile` usage concisely. `CLAUDE.md:167` names the two roots for restart evidence. Canonical skill files and `.agents/skills` mirrors stay identical.
- [ ] **R10 Pending PR tasks finish on the next CLI entry.** `task-complete.py reconcile --repo <checkout>` visits every `<git-common-dir>/devlyn-completion/*/receipt.json` with `allocation: "owned"`, a `pr_number`, and no terminal status. For each it reads the PR (`gh pr view`, `PR_FIELDS`, `validate_pr` `task-complete.py:386-396`); when the PR is MERGED it runs the existing post-merge path (`cleanup()` `:513-`, merge evidence `:514`) with writer cessation established by the existing observation (`stopped_writers` `:413`) and finishes at COMPLETE, so R3 retires the history. Anything else — OPEN, a `gh` failure, a live user, a changed local ref — records `reconcile: {status: "PENDING", reason, checked_at}` in that receipt and is listed by `history`; it never blocks the caller. `resolve-bootstrap.py` runs `reconcile` right after admission (`admission_lock` `:362`) and `allocate` runs it before creating the new receipt; their results carry `reconcile` outcomes verbatim. This closes the gap that `complete` in `pr` mode returns before any merge check (`:668-669`).

## Constraints

- **Stamp authorizes, prefix only hints.** Deletion requires the receipt id recorded in run state or an explicitly named program; a name prefix alone never authorizes removal. Why: `.devlyn/runs/` is shared with devlyn-os (`sessions_ipc.rs:482` `open_*`/`terminal_*`) and devlynd (`runstate.rs` `run_*`).
- **Replace, never layer.** No fallback count, age or size sweep survives or is added. Why: F6 — two cleaners for one class means one is wrong; keep-10 already deleted retry trails.
- **No adoption of legacy data.** Untagged runs, pre-existing custody, ad-hoc folders and interrupted allocations are listed or blocked, never swept. Why: `task-completion.md:22-25, 130-131`.
- **Failure is visible and never rewrites the product result.** `CLEANUP_PENDING` with exact paths and a resume command; no `ignore_errors`, no silent skip. Why: CLAUDE.md error philosophy and `task-completion.md:48-50`.
- **Reuse existing primitives.** `safe_path`, `stopped_writers`, `scratch_mounts`, `atomic_json`, `locked_receipt`, the bootstrap admission lock and `shutil.rmtree` symlink-attack safety. Why: one safety implementation, not two.
- **Unsupported writer observation retains.** Platforms where `stopped_writers` cannot observe (`task-complete.py:440-441`) report `RETAINED`. Why: cessation cannot be proven.
- **Zero new dependencies; tests use real isolated Git repositories and the existing fake `gh`, no network or model calls.** Why: installer surface and house test practice.
- **Prose does not grow beyond what the new actions need.** Remove superseded sentences before adding. Why: subtractive-first contract.

## Out of Scope

- devlyn-os changes: terminal/open run expiry, History and `resolve_state_file` tolerance of a missing `rs-*` archive (`work_monitor.rs:2045-2078` already skips unreadable archives; `crates/devlyn-runtime/src/resolve.rs:244-287` reports 0 archives as Corrupt). Separate devlyn-os spec.
- Live PTY spool size cap (devlyn-os spec).
- A shipped migration or sweeper for the existing backlog (untagged `rs-*`, existing full custody, ad-hoc top-level folders, unowned `runs/*`); handled once operationally with a classified plan.
- Reconciling receipts whose PR was closed without merge (`validate_pr` already refuses them, `:391`); they stay pending and visible.
- Deleting branches, worktrees, PRs or recovery refs on abandon; changing delivery modes or merge policy.
- Automatic abandonment by inactivity; any expiry of programs.

## Open questions (must be answered before resolve)

- **OQ1 Untasked runs (CLI-4 is not implementable as stated).** The answer "a resolve started without an owned receipt allocates one prospectively at bootstrap" conflicts with `allocate` (`task-complete.py:178-222`): it must run from the base checkout (`:193`), refuses a branch that already exists (`:192`; `task-completion.md:22-25` forbids adopting pre-existing tasks), needs a clean tree (`:194`), a single push==fetch remote (`:191`) and four caller-supplied identities (`--task`, `--branch`, `--repository`, `--base`, `:692-693`). Bootstrap runs on whatever branch is checked out and records that name as the base (`resolve-bootstrap.py:465-466`), so it has no base to allocate from, no new branch name, no `--repository`, and would have to create and switch branches itself. Until decided, runs with `task: null` are only listed (R6). Decisions needed: may resolve create the task branch itself (from which base, named how, `--repository` from where), and is a GitHub remote mandatory to run resolve at all?

## Authorized product surface

- `config/skills/_shared/task-complete.py`, `archive_run.py`, `resolve-bootstrap.py` and their `.agents/skills/_shared/` mirrors
- `config/skills/devlyn:resolve/references/task-completion.md`, `references/state-schema.md`, `SKILL.md` and their `.agents/skills/` mirrors
- `CLAUDE.md`
- `scripts/lint-skills.sh` only where an existing check references removed text

<!-- devlyn:verification -->
## Verification

- `python3 config/skills/_shared/task-complete.py --self-test` exits 0 and, with real isolated Git repositories and fake `gh`, covers:
  - in-place COMPLETE retires exactly the task's stamped runs including an incomplete attempt, while another task's stamped run, an untagged `rs-*`, a `terminal_*` dir and a `programs/` dir stay byte-identical;
  - linked COMPLETE with an extra stamped attempt removes the worktree instead of retaining on unknown ignored content;
  - LOCAL_ONLY without acceptance retains history; LOCAL_ONLY with bound acceptance retires it and a later `complete` resume succeeds without the retired files;
  - a crash after the tombstone rename resumes to RETIRED and touches nothing else;
  - a symlinked `.devlyn`, `runs` or target, an active writer, a contended bootstrap admission lock, or root pipeline state naming the receipt yields CLEANUP_PENDING with paths and resume, delivery status unchanged, nothing deleted;
  - custody holds only the binding set, the manifest matches it, and cleanup/resume verify it;
  - abandon is refused after acceptance bind; otherwise it records ABANDONED and retains branch and worktree;
  - a top-level entry created after allocation by something other than the CLI yields CLEANUP_PENDING with unowned_artifacts and the entry intact, while CLI-written names created during the task are not reported;
  - close-program removes only the named program directory;
  - `history` lists groups, pending reconciles and bytes and leaves the tree byte-identical;
  - `reconcile` with fake `gh`: a MERGED pending PR receipt reaches COMPLETE and its runs are retired; an OPEN one, a `gh` failure and a live user each record `reconcile.status: PENDING` with the reason, delete nothing, and return 0.
- `python3 config/skills/_shared/resolve-bootstrap.py --self-test` exits 0 and covers a stamp for an owned matching receipt, `null` without a receipt, a BLOCKED admission for an interrupted or terminal receipt, archiving a completed prior run that deletes no archived run, and a pending-reconcile outcome that leaves bootstrap admitted.
- `python3 config/skills/_shared/archive_run.py --self-test` exits 0 with prune assertions removed and archive behavior unchanged.
- `grep -rnE 'def prune|prune\(|--keep' config/skills/_shared/archive_run.py config/skills/_shared/resolve-bootstrap.py .agents/skills/_shared/archive_run.py .agents/skills/_shared/resolve-bootstrap.py` exits 1 (no count-based pruning remains).
- `bash scripts/lint-skills.sh` exits 0 with source and installed mirrors identical.
- `git diff --check` exits 0. Independent source review checks deletion authority, ordering against custody/resume, and that no legacy data is adopted.
