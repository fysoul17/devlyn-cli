# 0171 — direct execution repair (2026-09-14)

The user explicitly requested direct repair, without resolve. No new paid model
draw or pipeline run was launched; the 0169/0170 comparison remains incomplete.

0170 exposed two independent execution defects after scratch admission passed:
BUILD_GATE repeated staging already completed by the parent, and the research
controller aborted a live task after a single two-second process census timeout.

- BUILD_GATE now assigns staging to the parent IMPLEMENT checkpoint and uses
  read-only Git inspection for staging prerequisites. No additional Git writes
  or worker permissions are required.
- The maintained comparison controller preserves timeout streams and retries
  process observation within the existing 15-second window and overall deadline.
  Persistent blindness stays an explicit failure; signals require fresh PID/start
  identity checks. Cleanup observes dying processes within the existing reap bound.
- Frozen 0170 inputs and evidence remain unchanged. The next working input removes
  the redundant worker staging instruction and references the maintained controller.

Validation: seven regression checks passed in 4.260 seconds, including a real
subprocess surviving a slow census and a real committed Git test under an index
lock. The recovery and post-kill tests both reject the original controller.
`bash scripts/lint-skills.sh` passed. All 172 registered inputs, previous archives,
and phase mirror parity were checked. Raw evidence: `.devlyn/0171/`.

No workaround: repair ownership and observation semantics, not permission scope.
No overengineering: reuse existing deadlines and standard subprocess primitives;
no new configuration or restart fallback. Removing retry or post-kill observation
reintroduces the measured failures; an unused import was removed during review.

Next, announce and investigate why existing direct-first routing rules were
ignored. Preserve measured correctness and required full-route behavior while
reducing unnecessary phases, tokens and wall time; see the final queue entry.
