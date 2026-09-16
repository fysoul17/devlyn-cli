# Decision review brief — `.devlyn` history lifecycle (2026-09-16)

You are one of three independent seats (Claude Fable 5.1, Codex gpt-6-astra, Grok 4.6)
reviewing three product decisions the user made. You have no other context than this file
and read-only access to the repositories below. Do not edit anything.

## 1. The user's goal (verbatim intent)

> "작업이 다 끝나고 더이상 필요없는 히스토리면 클린업을 제대로 해야한다" — when work is
> finished and the history is no longer needed, it must be cleaned up properly. "CLI 에서도
> 다 하고나면 지워야하고, 0.2.3 에서도 자동으로 지워야 하는데. 이거 실수 없이 해야해."
> The CLI must delete after completion, devlyn-os 0.2.3 must delete automatically, with no mistakes.

Incident: on 2026-09-16 the macOS data volume reached 100% (ENOSPC aborted a running model call).
At review time: 419 GiB used of 460 GiB, 13 GiB free. `.devlyn/` directories across ~40 repos
under `~/Documents/GitHub` total **84 GiB**.

## 2. Repositories (read-only)

- `~/Documents/GitHub/devlyn-cli` — canonical CLI/skill source. Skills live in `config/skills/`
  (`devlyn:resolve`, `_shared/*.py`). Project contract: `CLAUDE.md` (principles: no workaround,
  root cause, subtractive-first, goal-locked, production ready / no silent failure, evidence over claim).
- `~/Documents/GitHub/devlyn-os-v1` — desktop app (Tauri/Rust). Storage policy/cleanup work is on
  `main` (`apps/desktop/src-tauri/tauri.conf.json` still says 0.2.2; the user calls the release
  that ships it "0.2.3" and has not installed it yet).
- `~/Documents/GitHub/pyx-memory-v1/.devlyn` — a real, heavily used example. **Never open
  `io/*.stdout` / `io/*.stderr` files (single files reach 1.38 GiB).** Use sizes/listings only.

## 3. Measured inventory (all repos, 2026-09-16)

Classified with devlyn-cli's own `archive_run.is_completed` / `read_state`:

| Class | Dirs | Size | Created by |
|---|---|---|---|
| `.devlyn/runs/terminal_*` | 310 | 64.9 GiB | devlyn-os terminal sessions (9 had a live `guard.lock` holder at check time) |
| `.devlyn/<ad-hoc name>` outside `runs/` (e.g. `x50-findings-20260915`, `session-audit-20260912`) | 384 | 14.1 GiB | orchestrator/agents writing scratch, evidence, handoffs ad hoc |
| `.devlyn/runs/<other>` (e.g. `manual-20260905-production-audit` 2.2 GiB, `unified-delivery` 51 MiB, `_stale-cleanup-20260830`, `resolve-20260622-...`, `team-fix-...`, `ar-...`) | 29 | 2.2 GiB | ad hoc / older tooling; no owner recognizes them |
| `.devlyn/runs/rs-*` completed (final_report verdict + completed_at) | 202 | 1.9 GiB | `/devlyn:resolve` |
| `.devlyn/runs/rs-*` incomplete/indeterminate (interrupted, aborted) | 42 | 0.6 GiB | `/devlyn:resolve` |

Inside one `terminal_*` dir: `io/sess_<id>.stdout` 1.38 GiB (raw PTY output), plus small
`meta.json` (`"kind":"terminal"`), `events.jsonl`, `sessions/`, `usage/`, `control/`, `guard.lock`.

## 4. Current mechanisms (verify every locator yourself)

CLI (`devlyn-cli/config/skills/`):
- `devlyn:resolve/SKILL.md:385` — PHASE 6 archive: `archive_run.py` moves per-run artifacts to `.devlyn/runs/<run_id>/`.
- `_shared/archive_run.py:485-504` `prune(runs_dir, keep=10)` — called only from archive (`:942`);
  iterates `runs/*/`, `read_state(d)` requires `pipeline.state.json`; `ArchiveError` → skip ("never prune");
  deletes oldest completed beyond 10. `is_completed` at `:173`.
- Consequences: `terminal_*`, ad-hoc `runs/*`, incomplete `rs-*` are never pruned; ad-hoc top-level dirs are never looked at; pruning is count-based, not tied to task completion.
- `devlyn:resolve/references/task-completion.md` — task-branch ownership, delivery, owned-resource cleanup. Note `:130-131` ("never silently archives or deletes arbitrary user content"), `:139` ("Recovery refs/evidence have no automatic expiry"). `_shared/task-complete.py:470` `clean_scratch` empties only the owned `scratch/` dir.
- `devlyn:resolve/references/outer-loop.md` and `CLAUDE.md` — outer loop re-enters "through committed durable artifacts (spec, findings, run archive)", at most 3 iterations; queue drains mark items and commit transitions.

devlyn-os (`devlyn-os-v1`):
- `crates/devlynd/src/storage_policy.rs:1-10` — policy governs only disposable **detail** evidence (`io/*.stdout`, `io/*.stderr`, terminal checkpoint); per-run enrollment (`storage.json`) written only while auto cleanup is activated; runs created before activation are **historical** and only the separate existing-data preview can name them. `RetentionDays` = 7/30/90, or `Forever`.
- `apps/desktop/src-tauri/src/work_monitor.rs:128` `CleanupMode {Prospective, Historical}`; `:1876` `auto_cleanup_tick` returns nothing unless `auto_cleanup_activated_at` is set (opt-in); `release_run`/`release_session` release io files, not whole run dirs; `KEEP_MARKER = "keep"` (`:47`) pins a run.
- `apps/desktop/src-tauri/src/sessions_ipc.rs:482` — devlyn-os manages only run ids starting `open_` or `terminal_`.
- `crates/devlynd/src/run_dir.rs:107-119` — `guard.lock` is an `flock`: writers hold shared, cleanup takes exclusive non-blocking.
- `terminal_checkpoint.rs:117` — stdout written to `io/<session>.stdout`; no size cap found by the orchestrator (verify).

## 5. The three decisions under review

**D1 — When are CLI pipeline runs (`runs/rs-*`) deleted?**
User chose: **delete at task terminal completion.** Once delivery is accepted (merge / accepted local
commit) and the outer loop is finished, delete every run of that task, including interrupted/incomplete
runs of that task. Keep them while NEEDS_WORK retries are still in progress. Raw logs/findings are gone afterwards.
Rejected: (b) keep for a retention window (e.g. 7 days) after completion; (c) keep current keep-10 and add incomplete runs.

**D2 — Ad-hoc top-level `.devlyn/<name>` folders (14.1 GiB) created by agents.**
User chose: **forbid creation; require every work artifact to live in a task-owned location
(the run dir / task-owned scratch) so it is cleaned with the task.** Existing folders get a one-time manual cleanup.
Rejected: (b) CLI deletes them by age (conflicts with task-completion.md:130); (c) no automatic cleanup.

**D3 — devlyn-os terminal history cleanup.**
User chose: **auto cleanup ON by default; include existing (historical) runs; delete the whole run
folder** after the session has ended (no live guard holder) and the retention window (default 30 days) has passed; `keep` pins still respected.
This reverses the storage_policy.rs design (opt-in, prospective-only enrollment, detail-only release).
Rejected: (b) default ON + stdout size cap, keeping prospective/detail-only; (c) keep 0.2.3 as is.

## 6. What to deliver

Verify facts against the code before relying on them. Every claim needs a `path:line` you opened
or an explicit "searched X, found nothing". Report any fact in this brief that is wrong.

For EACH decision D1, D2, D3 give:
1. **Verdict**: `KEEP` (correct as stated), `AMEND` (right direction, needs specific changes), or `REVERSE` (a rejected or new option is better).
2. **Strongest form of the user's decision** — the best argument for it.
3. **Strongest counter** — the most damaging concrete failure scenario (inputs/state → data loss, broken resume, wrong deletion, race, cross-tool conflict, user-visible surprise).
4. **Decisive criterion** — what actually settles it.
5. **Synthesis** — the precise rule you would put in a spec: owner, trigger, what is deleted, what is retained, safety preconditions (locks, live writers, keep pins, crash atomicity, symlinks, worktrees, queue drains, multi-week programs whose evidence spans many tasks), and how failure is surfaced (no silent fallback).

Then:
- **Cross-cutting**: ownership of the shared `.devlyn/runs/` namespace between CLI and devlyn-os; the 29 unowned `runs/*` dirs and 42 incomplete `rs-*` runs that never reach a task terminal; one-time migration of the existing 84 GiB.
- **Missing decisions**: questions the user must still answer before a mistake-free spec can be written (only ones that change the design).
- **Out of scope drift**: anything you'd be tempted to add that the goal does not require — name it and leave it out.

End your answer with exactly one fenced JSON block:

```json
{"seat": "<model id>", "D1": "KEEP|AMEND|REVERSE", "D2": "KEEP|AMEND|REVERSE", "D3": "KEEP|AMEND|REVERSE", "wrong_facts": ["..."], "missing_decisions": ["..."]}
```
