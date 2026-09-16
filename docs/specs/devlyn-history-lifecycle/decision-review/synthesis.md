# Decision review synthesis — round 1 (2026-09-16)

Seats (read-only, isolated): Claude Fable 5.1 `claude-fable-5-1` effort max (`fable.md`, 728 s),
Codex `gpt-6-astra` xhigh (`astra.stdout`, 478 s, 126,931 tokens), Grok `grok-4.6-build` xhigh (`grok.md`).
Input: `brief.md`. Result: **D1 AMEND ×3, D2 AMEND ×3, D3 AMEND ×3.** No seat reversed a decision.

## Brief facts corrected by the seats (orchestrator errors)

1. `prune(keep=10)` has two callers: `archive_run.py:942` and `resolve-bootstrap.py:221` (verified).
2. Prune selects by state content, not the `rs-` prefix (`archive_run.py:485`).
3. `terminal_checkpoint.rs:117` reads stdout for checkpoint hashing; the unbounded PTY spool writer is `crates/devlynd/src/supervisor.rs:1658-1681`. The 8 MiB cap (`terminal_checkpoint.rs:18`) is checkpoint JSON only.
4. The 3-iteration / re-enter-through-archive rule is `CLAUDE.md:63` and `devlyn:queue/SKILL.md:37`, not `outer-loop.md`.
5. "Ended" in devlyn-os needs an exit record (`sessions_ipc.rs:381-387`, `work_monitor.rs:1271-1287`), not merely a free guard; crashed sessions are excluded forever.
6. `complete --local-only` returns at `task-complete.py:619-622` before acceptance binding; COMPLETE is set at `:576` after merge evidence.
7. `runs/` has a third owner: devlynd loop runs `run_*` (`runstate.rs:73-92`). devlyn-os reads CLI `rs-*` archives (`work_monitor.rs:2045-2078`, `resolve.rs:244-287`).
8. Completion custody copies the whole accepted run into `<gitdir>/devlyn-completion/<id>/custody/` with no expiry (`task-complete.py:95-132, 331`; `task-completion.md:139`). Not counted in the 84 GiB.
9. The automatic tick is renderer-driven, view-scoped, 15 min, open workspace only (`OrchestrationHome.tsx:76, 539-548`).
10. D3 reverses approved devlyn-os spec text: explicit activation, no silent historical enrollment, "never recursively delete an arbitrary run directory", historical details stay visible as unavailable (verified in devlyn-os-v1 `docs/specs`).

## Consensus amendments (3/3 — no user decision needed)

**D1**
- Owner is the outer task owner in `task-complete.py`, never PHASE 6 archive or `prune(keep=10)`.
- Stamp a task identity on every run at allocate/bootstrap; deletion names runs by that identity only. No spec/branch/path heuristics.
- Delete only after acceptance is bound and custody-dependent verification/cleanup has finished; otherwise resume fails on "evidence bytes changed".
- `task-completion.md:139` custody contract must change together with D1.
- Failure → `CLEANUP_PENDING` + exact paths + retry command; product verdict unchanged. Never `ignore_errors`.
- devlyn-os History/verdict readers must treat a missing `rs-*` archive as "no archive", not corruption.

**D2**
- "Forbid" alone fails: scratch forbids reports/restart evidence (`task-completion.md:27-31`), the run dir exists only after archive, multi-week programs have no legal home.
- Required: named top-level allowlist, mechanical enforcement (not prose), a named task-owned evidence root, and a named durable home for cross-task evidence.
- Existing folders: classified one-time pass with a printed plan; never an age reap. `.devlyn/archive/**` contains git worktree registration data → retain until inspected; live pointers from HANDOFF files retained.

**D3**
- Default ON + historical included is the only way this class ever drains (opt-in + prospective enrollment + detail-only + unsettled-usage stdout retention `work_monitor.rs:1316-1356`).
- Scope strictly `open_*`/`terminal_*` (validated, not prefix alone); never `rs-*`, `run_*`, or unowned dirs.
- Keep existing protections: `keep` pin, orchestrator undismissed, `running|suspended|merge_ready`, symlink/redirect refusal (`:1185-1214`).
- `guard.lock` lives inside the deleted dir → lock recreation race; delete via tombstone rename under the exclusive guard (or a guard outside the dir); crash-resumable; outcome recorded in `storage-cleanup.json`.
- Scheduler must cover all registered workspaces, not the active renderer view.
- Record the spec reversal as an explicit amendment with the named delta (2026-09-16 ENOSPC, 64.9 GiB undrainable).

## Forks (seats disagree or user value judgment required)

| # | Fork | Fable | astra | Grok | Orchestrator recommendation |
|---|---|---|---|---|---|
| F1 | Durable home for cross-task program evidence (x50-style) | committed `docs/specs/<id>/` or `autoresearch/` | normal durable project/spec locations; program owner | `.devlyn/tasks/<task_id>/` | open — size matters (GiB evidence cannot be committed) |
| F2 | What survives devlyn-os whole-folder deletion | user decides | compact settled usage + outcomes retained elsewhere | delete all incl. usage; index rows dropped | keep compact usage/outcome record (matches approved "history stays visible") |
| F3 | Crashed session without exit record | pid dead + exclusive guard = ended, clock = snapshot mtime | explicit reconciliation, never dir age | open question | open |
| F4 | Custody after D1 | user decides expiry | delete redundant raw copies, keep compact receipt | shrink to binding files only | shrink to binding files |
| F5 | `LOCAL_ONLY` as trigger | no | only if explicitly accepted + durably recorded | yes, after acceptance bind | yes, only after acceptance bind |
| F6 | keep-10 | keep as fallback for task-less incomplete runs | remove both call paths | replace | remove; legacy handled by one-time pass |
| F7 | Abandoned / `[F]` / never-delivered tasks | — | explicit abandon; `[F]` is not abandonment | open | explicit abandon, listed visibly |
| F8 | Scheduler while app closed | app-lifetime Rust timer | open question | devlynd daemon, works while closed | open |
| F9 | Historical clock on upgrade | exit time | notice before first historical sweep | exit age vs activation open | exit age + one-time notice/preview before first sweep |
| F10 | Live PTY spool size cap | out of scope | out of scope (separate storage budget) | required | separate follow-up (2/3) |

## User decisions on forks (2026-09-16)

- F1: task evidence in `.devlyn/tasks/<task_id>/` (deleted at task terminal); cross-task program evidence in `.devlyn/programs/<program_id>/` (deleted only on explicit program close); only small conclusions committed to `docs/specs`.
- F2: whole-folder deletion keeps a compact history record (usage/cost, outcome, timestamps); History shows "details expired".
- F3: a session without an exit record is ended when its process is dead and the exclusive guard is acquirable; clock starts at the last recorded snapshot time.
- F8: automatic cleanup runs in a Rust app-lifetime timer over all registered workspaces while the app runs.
- Orchestrator defaults accepted without objection: F4 custody shrinks to binding files; F5 `LOCAL_ONLY` counts only after acceptance bind; F6 keep-10 removed, legacy via one-time pass; F7 abandoned/`[F]` retained until explicit abandon, listed visibly; F9 exit-time clock with one-time notice/preview before the first historical sweep; F10 live spool cap is a separate follow-up.

## User decisions on spec open questions (2026-09-16, round 2)

- OS-1 (reverses D3 "whole folder" with named delta): full measurement over 313 `open_*`/`terminal_*` runs = 65.18 GiB, `io/` 61.67 GiB, `events.jsonl` 3.57 GiB (the run's durable record read by usage/conversation/sessions, `usage_ipc.rs:1467`), everything else ~27 MiB. User chose **release `io/` only**; the run folder, `events.jsonl`, and the compact skeleton stay. This removes the need for a compact-record store, reader changes, and the guard-recreation fix. F2 is satisfied by the retained skeleton.
- OS-2: first historical sweep requires **one app-wide confirmation** over a preview; automatic afterwards. Existing data is untouched until confirmed.
- OS-4: crashed sessions with unsettled usage expire after the window; usage is shown as **unmeasured**.
- OS-3: no saved `storage-policy.json` exists on this machine; spec default (saved explicit off stays off, absent → on) stands.
- CLI-1: task evidence path is `.devlyn/task-evidence/<receipt_id>/` (`.devlyn/tasks/` is devlynd-owned, `run_dir.rs:153`).
- CLI-2: allowlist check compares a top-level listing captured at task start with the listing at task terminal; only new non-CLI-owned names are reported (never deleted). No devlyn-os name list is synced.
- CLI-3: pending PR-mode tasks are completed and cleaned by the next CLI bootstrap/allocate once merge is verified; lookup failure keeps them visibly pending.
- CLI-4: a resolve started without an owned task receipt allocates one prospectively at bootstrap (feasibility to be proven in spec review).

## Round 3 (2026-09-16 evening) — measurements that changed the picture

- Old + unreferenced (>30 days, no reference anywhere in `~/Documents/GitHub` or memory, no lock, no keep, no git data): 138 entries, **0.1 GiB**. The backlog is not old history.
- Terminal `io/` written in the last 7 days: **61.5 GiB** (<1d 14.4, 1–3d 18.1, 3–7d 25.0). Per-session write rate 40–126 MiB/h. Tail sample of the largest spool: 80% ANSI redraw sequences (`ESC[H`, `ESC[m`), 20% text; codex is launched with `--no-alt-screen` (`open_terminal.rs:127`) so every TUI redraw lands in the spool (`supervisor.rs:1685` `open_spool_at`, no size bound). A 30-day retention policy would not have prevented the 2026-09-16 ENOSPC.
- **F10 reversed with named delta**: the live spool cap is in scope of the devlyn-os spec (limit and mechanism decided in spec review).
- Immediate relief executed by the orchestrator with the app's own rules (exited + no keep + guard exclusive + usage `unsupported_route`/settled, `released/<session>.json` receipt written): sessions exited ≥1 day ago. Sessions exited <1 day (18, 14.4 GiB), live (7, 4.05 GiB), stale without exit record (9, 1.6 GiB) untouched.

## Next

User answers forks → write `devlyn-cli` spec (D1, D2) and `devlyn-os-v1` spec amendment (D3) → 3-seat spec review → user go-ahead → `/devlyn:resolve --spec` per repo with 3-seat VERIFY.
