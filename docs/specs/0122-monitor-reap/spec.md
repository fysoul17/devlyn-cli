# 0122 — Reap monitoring descendants when Codex finishes

## Observed failure and intent

The registered 0120 quality/speed run `rs-20260907T014240Z-c67db5ae6156` completed its native work, report and archive, but the wrapper left its watchdog `sleep 3600` alive after exit 0. PID 76847 became a child of PID 1 while retaining the root wrapper's process group 76837. The external controller correctly continued waiting for an owned descendant. This prevents a valid verified-resolution time; it is not evidence of worker quality or speed.

The immutable source/ownership packet is main `.devlyn/0120-harness-direction-20260906/quality-speed-orphan-watchdog-r0/`. A separate single fake-native reproduction in `wrapper-watchdog-orphan-r0/` returned 0 after 1.504 seconds and left `sleep 12` alive until its natural expiry. No live pilot process was signaled. Current wrapper bytes exactly match the parent of existing fix `81164d2eb28bdb5e2250dd837642f490e47b8e33`, which is on separate branches and absent from current main history.

## Required behavior

- A successful or failed native exit must preserve its exit code and finish invocation receipts while reaping the wrapper's heartbeat and watchdog descendants. Captured streams must reach EOF without waiting for an unused timeout.
- TERM and INT retain exit 143 and 130; an actual hard timeout retains exit 124. Cleanup must also remove an owned monitor child that ignores TERM, without signaling unrelated processes.
- Preserve ordinary native capabilities, model arguments, isolation, receipt validation, heartbeat behavior and the existing native process-group cleanup.
- Reuse the existing monitor-group fix and its meaningful regression where compatible. Do not import unrelated changes from the historical capability branch or restore old whole files.

## Scope and verification

Runtime/test scope is `config/skills/_shared/codex-monitored.sh`, `config/skills/_shared/invocation-receipt.py` and their tracked `.agents` mirrors. Keep required local mirror parity. No dependencies, public flags, routing, permissions or schema changes.

Before testing, predict that a short successful fake native reaches prompt stream EOF and leaves no owned monitor descendants under a longer timeout. Run the existing receipt self-test with the restored monitor regression, bounded fake-native signal/timeout cases where the historical regression does not cover the required behavior, Bash syntax validation, required full skill lint and diff check. Retain raw exits, process ownership and cleanup evidence. Actual Fable 5.1/Grok 4.6 provide independent final advice; root adjudicates findings and adoption.

This is a bounded repair through the Codex implementation route, authorized by the user's continuation instruction. It does not start another resolve run in the diagnosed broken execution environment. Prepare it in a separate worktree while preserving all registered pilot inputs and the existing deadline. It cannot rescue, retry, replace or re-clock the original four-row registration. Stop its unlaunched rows once the common invocation defect is adjudicated; any later comparison requires a separate decision and fresh registration.

Subtractive-first: replace PID-only monitor cleanup with the existing group cleanup and remove duplicated cleanup statements; retaining the optional timeout is required for ordinary callers without an outer controller. **No workaround** fixes the owned-process lifecycle; **No overengineering** reuses a proven small delta; **No guesswork** retains the actual failure; **Optimized / Production ready** require prompt, truthful completion and bounded cleanup.
