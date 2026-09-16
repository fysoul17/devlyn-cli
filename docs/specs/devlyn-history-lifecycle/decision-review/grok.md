I verified the locators against the trees. Two brief claims are wrong; the rest of the mechanism description holds. All three decisions point the right way and none is safe to ship as written.

**Wrong facts in the brief**

1. **`outer-loop.md` is not the 3-iteration / “re-enter through the archive” contract.** `config/skills/devlyn:resolve/references/outer-loop.md` is only the owner-commit order (allocate → spec amendment → queue `[x]`/`[F]` → `task-complete`). “At most 3 outer iterations” and “re-enters through committed durable artifacts (spec, findings, run archive)” are `devlyn-cli/CLAUDE.md:63` and `config/skills/devlyn:queue/SKILL.md:37`.
2. **`terminal_checkpoint.rs:117` does not write stdout.** That line *reads* `io/<session>.stdout` to hash checkpoint identity. The unbounded write is `crates/devlynd/src/supervisor.rs:1658–1681` (`open_spool_at`, `create_new`, no length check) and the write loop around `:1273–1416`. The 8 MiB cap (`MAX_CHECKPOINT_BYTES` at `terminal_checkpoint.rs:18`) is the checkpoint JSON, not the PTY spool.

I did **not** re-`du` the 84 GiB / 310 / 384 / 29 / 202 / 42 counts, and I did **not** re-check live `flock` holders (`guard.lock` *files* exist on many `terminal_*` dirs; a holder is not the same thing). In `pyx-memory-v1/.devlyn` the five classes exist: `runs/terminal_*`, top-level `x50-*` / `session-audit-*`, unowned `runs/unified-delivery`, completed `rs-*`, and incomplete `rs-*` (e.g. `runs/rs-20260710T001023Z-10e4c77d46fb/pipeline.state.json` has `"final_report": null`). I did not open any `io/*.stdout`.

---

## D1 — Delete CLI `runs/rs-*` at task terminal completion

### Verdict: `AMEND`

### Strongest form of the user's decision

Keep-10 is the wrong axis. `archive_run.prune` (`config/skills/_shared/archive_run.py:485–504`, called only from `main` at `:942`) keeps the 10 newest *completed* archives in that worktree and skips everything else. `is_completed` (`:173–192`) treats `NEEDS_WORK` as completed, so a retry archive can be deleted because some *other* task produced 10 newer PASS runs. Terminal sessions, ad-hoc `runs/*`, and incomplete `rs-*` are never touched (`read_state` requires `pipeline.state.json`; `ArchiveError` → skip).

The user's trigger is the one the rest of the CLI already uses for “work is finished”: outer loop done, delivery accepted (merge or accepted local commit). That is subtractive, task-scoped, and it stops keep-10 from deleting the findings trail *during* `NEEDS_WORK` retries (`CLAUDE.md:63`).

### Strongest counter

A repo with many past `rs-*` and no `task_id` on pipeline state (`references/state-schema.md` top-level shape has `run_id`, not task identity). At “task complete”, the helper only names **one** archive (`task-complete.py:331` `paths.append(".devlyn/runs/" + acceptance["run_id"])`). “Delete every run of that task, including interrupted ones” then either:

- **guesses** (same `spec_path` / same worktree / all `rs-*`) and deletes another live or parked task’s archive, or
- **doesn’t guess** and leaves the 42 incomplete / 202 completed-but-never-`task-complete`’d runs forever.

Worse concrete path: `complete --local-only` returns at `task-complete.py:619–622` *before* `bind_acceptance`. Hooking delete on that flag without a bound acceptance wipes archives that were never accepted. And `task-complete.py:95–132` `snapshot_files` + `custody` copies the **entire** accepted run tree into `<gitdir>/devlyn-completion/<id>/custody/` with no expiry (`task-completion.md:139`). Deleting `.devlyn/runs/rs-*` while custody keeps the bytes does not free disk; deleting custody too breaks post-merge `cleanup()` re-verify (`:519–521`).

Desktop history also **reads** those archives: `work_monitor.rs:2045–2078` joins VERIFY verdicts from every `runs/rs-*`. `crates/devlyn-runtime/src/resolve.rs:244–287` errors if it finds 0 or >1 archived `pipeline.state.json` when the live root file is gone.

### Decisive criterion

Can the deleter name *exactly* the runs of this task, and only after delivery+outer-loop, without relying on keep-10 or path heuristics? If task identity is not stamped at allocate/bootstrap, D1 as stated will either leak or delete the wrong tree. That is the whole “실수 없이” test.

### Synthesis (spec rule)

- **Owner:** outer task owner via `_shared/task-complete.py`, never PHASE 6 archive, never `prune(keep=10)`.
- **Trigger:** `complete` after (1) outer loop finished (PASS delivered, or `[F]`/3-iteration surface if the user later says abandoned work is in scope), (2) acceptance bound (`kind: pipeline` names the successful `run_id`; `kind: direct` has no `rs-*`), (3) merge evidence **or** local-only/no-push *after* bind, (4) `--writers-stopped` actually observed (`task-completion.md:115–123`).
- **What is deleted:** every `runs/rs-*` whose state (or sidecar) carries this task’s allocation id, including `BLOCKED` / incomplete archives of that task. Live root `.devlyn/pipeline.state.json` for a still-admitted run is never deleted (`resolve-bootstrap.py` unfinished refusal).
- **What is retained:** committed spec/queue; recovery git ref; custody of *binding* files only (acceptance, `pipeline.state.json`, `final-report.md`, digests) — not raw `*.stdout` / process-evidence streams. `engines.json` and other machine config stay (`archive_run.py` already leaves them).
- **Preconditions:** replace keep-10 (do not layer). Stamp `task_id` at `task-complete.py allocate` into bootstrap state. Prefix filter `rs-` only. No symlink follow (`safe_path`). Refuse if `pipeline.state.json` at root still names one of the targets. Surface `CLEANUP_PENDING` + retry command on any retain; never `shutil.rmtree(..., ignore_errors=True)` (today’s prune already uses `ignore_errors=False` at `:502`).
- **Failure:** same fail-closed style as scratch (`CLEANUP_PENDING`, product verdict unchanged). Desktop `history_joins` and `resolve_state_file` must treat missing `rs-*` as “no archive”, not `Corrupt` / guessed latest.

---

## D2 — Forbid ad-hoc top-level `.devlyn/<name>`

### Verdict: `AMEND`

### Strongest form of the user’s decision

The 14.1 GiB is not a retention bug. It is agents inventing unowned directories (`pyx-memory-v1/.devlyn/x50-*`, `session-audit-20260912`, `.devlyn/archive/…`). Age-delete would violate `task-completion.md:130–131` (“never silently archives or deletes arbitrary user content”). No automatic cleanup is how the pile formed. Forbidding creation is the root-cause, subtractive fix; one-time manual cleanup of what already exists is the only legal treatment of unowned data.

### Strongest counter

“Put it in the run dir / task-owned scratch” is false as stated.

- The run dir does not exist until PHASE 6 archive (`SKILL.md:385`; live artifacts sit at `.devlyn/<PER_RUN_PATTERNS>` files).
- Scratch is only disposable build intermediates; **reports and restart evidence are forbidden there** (`task-completion.md:28–31`). `clean_scratch` (`task-complete.py:470–502`) also refuses Git data and mounts.
- Product already uses top-level names that are not tasks: `.devlyn/engines.json`, `pipeline.state.json`, `ideate-draft.md`, `storage-policy.json`, `storage-cleanup.json`, `runs/`, `tasks/` (`run_dir.rs:153–159`), `probes/`, `process-evidence/`, `queue-drains/`, `queue-decisions/`.
- `pyx-memory-v1/.devlyn/archive/` holds relocated `terminal_*` trees **and** git worktree registrations (`COMMIT_EDITMSG`, `gitdir`, `commondir`). A one-time `rm -rf` of “ad-hoc folders” deletes Git recovery data the helper is written to refuse.

A multi-week orchestrator (the x50 folders) has no legal home after the forbid, so it will either stop or quietly write next to the repo.

### Decisive criterion

Is there a *named allowlist* plus a *task-owned evidence root that is allowed to hold reports*, with mechanical refusal of anything else? Prose in a skill will not stop the next agent `mkdir`.

### Synthesis (spec rule)

- **Owner:** CLI bootstrap + finish-gate (fail closed). Desktop does not create these dirs and must not sweep them (`sessions_ipc.rs:482` already ignores non-`open_`/`terminal_` run ids).
- **Trigger (future):** any mkdir/write under `.devlyn/` whose first path segment is not allowlisted.
- **Allowlist (files):** `pipeline.state.json`, `engines.json`, `ideate-draft.md`, `acceptance.json`, `untracked.baseline`, `storage-policy.json`, `storage-cleanup.json`, `index.db`, plus live `PER_RUN_PATTERNS` files until archive.
- **Allowlist (dirs):** `runs/`, `tasks/<task_id>/`, `probes/`, `process-evidence/<run_id>/`, `queue-drains/`, `queue-decisions/`. Nothing else.
- **Where work artifacts go:** allocate-owned `tasks/<task_id>/` (or the completion-receipt directory next to `scratch/`, *not* scratch). During a resolve, keep today’s file layout, then archive into `runs/rs-*`.
- **Existing 14.1 GiB:** one-time **classified** manual pass: list, owner, Git/mount/symlink check, then delete only named disposable trees. Never a global age reap. `.devlyn/archive/**/gitdir` is retain-until-inspected.
- **Failure:** bootstrap/finish-gate `BLOCKED` with the illegal path; do not auto-move into `runs/` (that is how the 29 unowned `runs/*` were born).

---

## D3 — Auto-on, historical, whole-folder, 30-day, keep pins

### Verdict: `AMEND`

### Strongest form of the user’s decision

64.9 of 84 GiB is `terminal_*`. Current policy cannot drain it:

- Default is **off** (`storage_policy.rs:77–88` `auto_cleanup_activated_at: None`).
- Auto tick is **prospective-only** (`work_monitor.rs:1876–1882`); unenrolled runs are historical and only the separate preview may name them (`storage_policy.rs:1–10`, `run_eligibility` `:1289–1294`).
- Release is **detail-only** (`io/*.stdout|stderr|*.terminal-checkpoint.json`, `KEEP_MARKER` `:47`, `release_session` `:1723–1715`).
- For `kind != Shell|Installer`, unsettled usage **retains stdout forever** (`stdout_verdict` `:1316–1356`). Terminal PTY output is in that set. That is how a 1.38 GiB spool survives even an activated 0.2.3.
- Tick runs only while OrchestrationHome is mounted, every 15 minutes (`OrchestrationHome.tsx:76, 539–547`; settings copy: “Runs while Devlyn is open.”). The daemon enrolls at open (`open_terminal.rs:1239–1240`) but **does not tick cleanup**.

Default on + historical + delete the folder after the session has ended is the only combination that actually matches “0.2.3 must delete automatically” for this class. 30 days + `keep` is the user’s retention choice; `RetentionDays` already offers 7/30/90/Forever (`storage_policy.rs:34–38`).

### Strongest counter

Install 0.2.3 with default ON and historical in the auto tick. Retention clock = session exit, not activation. Every `terminal_*` / `open_*` whose session ended ≥30 days ago and that is not `keep`-pinned is eligible on the first tick — including installer sessions that live under a `terminal_*` prefix (`pyx-memory-v1/.devlyn/runs/terminal_2eac2ea8…/meta.json` `"kind": "installer"`; managed-id test is prefix-only, `sessions_ipc.rs:482–484`).

If eligibility is weakened to “no live guard holder” as stated, a run with `status: running` and a dead writer (no flock) is deleted while the UI still shows it live (`run_eligibility` today requires `"exited"` and excludes `running|suspended|merge_ready`, `:1271–1287`). `history_detail` (`:2308–2316`) then returns “Managed run does not exist.” Whole-folder also drops managed usage sidecars (canonical cost source per `usage_ipc/global_history.rs:1–8`).

Separately: a **live** session wrote 1.38 GiB and filled the volume. 30-day post-exit deletion does not cap the spool (`supervisor.rs:1658–1681`). Rejected (b)’s size cap is the control for *today’s* ENOSPC; D3 as stated does not.

### Decisive criterion

Will 0.2.3, with the app closed overnight, delete only ended, unpinned, prefix-managed run directories whose retention has elapsed, without touching `rs-*`, without following redirects, and without taking a live writer’s files — and will a live session still be unable to fill the disk? If any of those is no, D3 as stated fails “실수 없이”.

### Synthesis (spec rule)

- **Owner:** `devlynd` (not the renderer). Enrollment at `open_terminal` / `open_session` stays. Auto tick moves into the daemon so “default on” works while the app is closed.
- **Default:** auto cleanup ON; `auto_cleanup_activated_at` stamped on first 0.2.3 launch if no saved policy. Saved `false` stays off. UI still shows “on since …”.
- **Scope:** `open_*` and `terminal_*` only (`is_managed_session_run_id`). Never `rs-*`, never unowned `runs/<other>`, never top-level ad-hoc.
- **Trigger:** session ended **and** exclusive non-blocking `flock` on `guard.lock` (`run_dir.rs:107–111`) **and** retention elapsed (default 30 days from observed exit, `retention_verdict` `:1360–1373`) **and** no `keep` file. Keep today’s status gates (`exited`; not `running|suspended|merge_ready`; orchestrator `open_*` still needs `dismissed` unless the user later says otherwise). Do **not** require usage fingerprint to delete the folder after that point (that gate is why terminal stdout never left).
- **What is deleted:** the whole run directory (`meta.json`, `io/`, `events.jsonl`, `sessions/`, `usage/`, `control/`, `terminal-file-*`, `guard.lock`).
- **What is retained:** `keep`-pinned runs; live writers; redirected/symlink components (`direct_io_dir` `:1185–1213`); `rs-*`; `.devlyn/engines.json`; `index.db` rows must be dropped or marked released in the same commit as the rmtree (no dangling index).
- **History:** missing dir = released, not a validation error. `history-removed` marker is unnecessary if the folder is gone; list/detail must agree.
- **Live safety (required extra, not a substitute):** cap or rotate the PTY spool while writing. Retention does not prevent ENOSPC. Surface the cap as a run event, not a silent truncate of bytes still needed for an unsettled usage fingerprint *during* the session.
- **Failure:** same `CleanupOutcome` + `storage-cleanup.json` (`last_outcome_path` `:1142–1144`); tick banner already exists. Refuse the run, continue others. `SCAN_CAP` 2000 oldest-first (`:45, :1385–1390`) is acceptable if the daemon pages; do not drop the oldest.

---

## Cross-cutting

**Namespace.** `.devlyn/runs/` is shared and already partitioned by prefix: OS manages `open_`/`terminal_` (`sessions_ipc.rs:482`); CLI prune only understands dirs with `pipeline.state.json` (`archive_run.py:488–493`). CLI D1 must never `rmtree` a `terminal_*`. OS D3 must never touch `rs-*`. `history_joins` is the one OS reader of `rs-*`; after D1 it must tolerate absence.

**29 unowned `runs/*` (2.2 GiB).** Neither prefix, no `pipeline.state.json` contract, no enroll. Example: `pyx-memory-v1/.devlyn/runs/unified-delivery/`. D1/D2/D3 as stated leave them. Treat as D2-class: one-time classified manual, then forbid creating non-`rs-`/`open_`/`terminal_` children of `runs/`.

**42 incomplete `rs-*` (0.6 GiB).** Bootstrap only auto-archives *completed* priors (`resolve-bootstrap.py:1289–1317`); unfinished root state is refused. Incomplete dirs already in `runs/` are leftovers (manual move, older tooling, archive invoked without `final_report`). D1 can only take them if they carry `task_id`. Legacy ones need the one-time pass.

**One-time 84 GiB.** D3 historical with exit-time clock will free *old* `terminal_*` on first daemon tick; recent sessions (e.g. `terminal_006dc10b…` `createdAt` 2026-09-13) stay for 30 days. D2 is manual. D1 does **not** drain the existing 202 completed `rs-*` unless those tasks run `task-complete` (they will not). Migration must be an explicit classified pass for leftover `rs-*` and unowned `runs/*`, not hoped-for side effects of D1.

**`keep-10` vs D1.** If keep-10 remains, it still deletes `NEEDS_WORK` archives mid-loop. D1 replaces it.

---

## Missing decisions (design forks)

1. **Task binding:** stamp `task_id` at allocate/bootstrap, or D1 cannot identify “runs of that task”.
2. **Abandoned work:** 3-iteration surface, queue `[F]`, never-delivered — delete with D1 or retain until an operator names them?
3. **Custody vs “raw logs gone”:** shrink custody to binding digests, or also expire custody? `:139` must be rewritten either way.
4. **Legacy `rs-*` / 29 unowned `runs/*`:** one-time classified delete, or leave until a human names each?
5. **D3 clock on upgrade:** session-exit age (old terminals die on first tick) vs clock starts at 0.2.3 activation?
6. **Crashed “running” session:** status=`running`, no flock holder — delete after a heartbeat grace, or retain until the user dismisses?
7. **Live spool cap:** separate from D3 retention or not? The incident is live ENOSPC; D3 does not address it.
8. **History VERIFY badge** after D1 deletes `rs-*`: drop it, or persist a small join receipt outside the run dir?
9. **Orchestrator `open_*`:** still require `dismissed`, or treat “session ended” like terminals?

## Out of scope (do not add)

Compressing or content-addressing spools; moving `.devlyn` off the data volume; a global scanner of `~/Documents/GitHub`; changing Forever/7/90 options; cockpit disk UI; rewriting the usage ledger; Git GC of worktree copies; a second keep-N safety net “just in case”. Those do not close the stated goal.

```json
{"seat": "Grok 4.6", "D1": "AMEND", "D2": "AMEND", "D3": "AMEND", "wrong_facts": ["outer-loop.md does not contain the 3-iteration / re-enter-through-archive rule (that is CLAUDE.md:63 and queue/SKILL.md:37)", "terminal_checkpoint.rs:117 reads stdout for checkpoint hashing; the unbounded PTY write is supervisor.rs:1658-1681 / write loop ~1273 (checkpoint JSON is 8 MiB, not the spool)"], "missing_decisions": ["stamp task_id on every rs-* at allocate/bootstrap, or D1 cannot name 'runs of that task'", "abandoned/[F]/3-iteration-surface work: delete or retain", "custody: shrink to binding digests vs expire with the run (task-completion.md:139)", "legacy rs-* without receipts and the 29 unowned runs/*: one-time classified delete or leave", "D3 upgrade clock: session-exit age vs activation time", "status=running with no flock holder (crashed daemon): delete after grace or retain", "live PTY spool cap as a separate rule from 30-day folder deletion", "history VERIFY join after rs-* deletion: drop vs persist a receipt", "open_* orchestrator sessions: still require dismissed or treat as session-ended"]}
```