# iter-0094 — R5 re-gate registration (STUB, not yet registered)

Successor to iter-0092's R5 live matrix, which closed UNSCORED
protocol-failed-at-controls (DECISIONS 0092.1; adjudication and receipts in
`iterations/0092-plan-native-foreground-dispatch.md` § R5 terminal status and
`~/.local/share/nx01/iter0092-r5/`). The candidate under test is unchanged:
R1's native foreground PLAN dispatch (landed at `83b275e`, formal verification
green at verify-only `rs-20260805T030021Z`, oracle self-test 284 assertions).
Nothing here is frozen yet — a fresh registration round (Fable + Grok FREEZE
seats, Terra instrument proof) must freeze all of it before any arm runs.

## What the new registration must fold in (all evidence-backed, 2026-08-05)

1. **Watcher amendment** (`plan-stop-watch.py`, registration-owned copy):
   `.devlyn/implement.task-context` and `.devlyn/implement.prompt` become
   allowed pre-dispatch preparation artifacts — update BOTH
   `ALLOWED_DEVLYN_ARTIFACTS` and `DEFAULT_FORBIDDEN_ARTIFACTS` coherently
   (Grok delta). Still forbidden and arm-invalidating: `implement.stdout`,
   `implement.stderr`, any IMPLEMENT worker/tool dispatch in the retained
   transcript, detached processes, tracked/non-ignored mutation,
   non-quiescent group. Stop trigger stays the atomic IMPLEMENT `started_at`
   carrier.
2. **Watcher self-test re-proof**: retarget the forbidden-artifact case to
   `implement.stdout` and re-prove exit 0 before any arm (Grok delta; the old
   case deliberately used `implement.prompt`).
3. **SIGINT grace 5000ms** via the existing `--grace-ms` flag — 250ms was
   proven against a synthetic SIGINT-handling child; the live headless
   `claude` parent escalated at 250ms.
4. **Branch worktrees** (`git worktree add -b …`), never detached:
   `resolve-bootstrap.py` `git_text` blocks on nonzero exit even with
   `allow_empty=True`, so detached-HEAD checkouts can never bootstrap
   (registered product follow-up — fix it via its own scoped change, not
   inside this registration).
5. **Fresh worktree path per attempt** — replacement attempts must not share
   a munged `~/.claude/projects` session dir with a dead attempt.
6. **Fresh controls, fresh judging nonce** (0088.3 rule: reuse = new
   registration + new controls). The 0092 nonce was never revealed to a
   judge but retire it anyway.
7. Everything else re-freezes as in 0092's R5: ABBA serial order
   (control-simple → candidate-simple → candidate-discovery →
   control-discovery), Sonnet 5 arms via `~/.local/bin/claude` (never the
   Superset wrapper), goals with explicitly ordered authorized surfaces
   (watcher compares the surface list order-sensitively), blind A/B
   judging by Fable 5 + Grok 4.5 with a precommitted nonce, structural bar,
   no-loser quality bar, duration tripwires ≤1.25 summed / ≤1.50 per arm,
   infrastructure replacement only before any in-window PLAN Agent use.

## Known instrument gotchas for the operator (learned 2026-08-05)

- Judge emission must be pure JSONL + a bare `{"verdict": …}` terminal line;
  prose preambles/trailers break `collect-codex-findings.py`.
- `verify-merge-findings.py` crosschecks every `*judge.stdout` file in
  `.devlyn` as pair-side evidence — in flipped-seat runs name the primary
  judge's capture outside that pattern (registered harness follow-up).
- Arm goal texts must pin the exact ordered `authorized_surface` list so the
  watcher's order-sensitive comparison is deterministic; identical text goes
  to both arms of a pair, so this is hypothesis-neutral.
