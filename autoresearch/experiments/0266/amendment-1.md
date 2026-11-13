# 0266 amendment 1: a refused usage reading no longer holds a dispatch (2026-11-13)

This is a dated amendment to [DESIGN.md](DESIGN.md) "Operations", which takes 0265's "Windows" rule
([../0265/DESIGN.md](../0265/DESIGN.md)): a cell starts only while every usage window is below 95%; "Otherwise the
lane holds and re-reads every 60 s." It changes only what a dispatch does when the usage endpoint refuses its reading.
DESIGN.md and [registration.md](registration.md) are unchanged.

## What happened

Times are KST on 2026-11-13, from `output/driver-claude.log` and `night/*.log` in the runtime root. The app's
readings (43%, 65%, its five-minute steps) are from the app's own board and cooldown files (`~/.devlyn/cli-usage.json`,
`~/.devlyn/claude-active.cooldown.json`) as the orchestrator read them at those times; the runtime root does not keep
them.

- The screen lane started at 08:39:56 and wrote 8 of the 18 screen verdicts, s01 to s08, the last at 09:13:10.
- From 09:13:10 every usage reading was refused (`Claude window check failed: HTTP Error 429: Too Many Requests`):
  46 holds one minute apart until 09:58:46, then the operator hold from 09:59:46. The operator's back-off loop
  removed that hold at 11:19:06; the lane's next reading, at 11:19:47, came after 81 minutes without a request and
  was refused too, and the loop set the hold again at 11:19:51.
- The block then ended early: the app's board showed an answered reading, the loop removed the hold at 11:58:19, and
  the screen went on under the old rule (s09's verdict at 12:03:55). From 09:13:10 to 11:58:19 no cell started: 2 h
  45 min. The board read 65% of the default login's week at 12:03, up from 43% at 09:05 with the lane idle: other
  sessions use the same login.
- The endpoint's `Retry-After` was 909 s at 09:58:01: the block would end at 10:13:10, one hour after the first
  refusal. It was 3137 s at 10:24:45: a new one-hour block from 10:17:02, started by the first reading after the old
  block ended. The lane was on the operator hold then. The Devlyn app reads the same login every five minutes: its
  board's last answered reading of the default login was at 09:05 (43% of the week), and its refused readings since
  fall on 10:17:02 plus whole five-minute steps (the latest at 11:22:02).
- The Devlyn app's own source records the same behaviour (`crates/devlynd/src/cli_accounts/claude/credential_store.rs`
  in devlyn-os-v1, measured 2026-10-18): "a 3600 s block on a busy login". The host's default Claude login is used
  by several Claude Code sessions at once, and Claude Code itself reads the same endpoint.
- The gate's history: 0257 lost 6.0 h to HTTP 429 on this endpoint, and no hold came from a window itself (0265
  DESIGN "Why" item 3); 0265 had 38 such holds (24 Claude, 14 Codex) and none for a window (0265 RESULT "Holds");
  0266 lost the 2 h 45 min above and none for a window. The gate was set by
  [0257 amendment 2](../0257/amendment-2.md), which also says that quota faults are archived and redispatched and that
  window utilization is descriptive (`decide.py` does not use it).

## The change

In `driver.py`, `ready()`:

1. A usage reading the endpoint refuses with HTTP 429 no longer holds the dispatch. The lane logs the event
   `window_unread` (with `cell` when a slot is given, and `retry_after`: the seconds the endpoint named, or null) and
   the dispatch goes on, with the account approved as after a reading that answered.
2. Exception: a slot that has a recorded split wait (an earlier reading found a window at or above its cap for that
   slot) still holds while the reading is refused, because the reset cannot be confirmed: a `hold` with reason
   `awaiting split window reset: windows unread`. A split wait recorded for another account is dropped as before.
3. While a refusal's `Retry-After` runs, the lane does not read the endpoint again: such a dispatch is `window_unread`
   too, with `until` (the deadline) in place of `retry_after`, and rule 2 applies the same way. The deadline is kept
   in memory only; a header that is absent or not a whole number of seconds sets no deadline, so the next dispatch
   reads again.
4. Everything else is as before: another HTTP status, a network error, an answer that is not JSON and a reading
   without the seven-day window hold and are re-read after 60 s; a reading that answers is applied exactly as before (caps, split
   wait, split block).

## What does not change

- A limit met inside a cell is a quota fault, classified from the cell's own evidence, archived and redispatched as
  DESIGN says.
- In the screen a cell in which an owner ran is never dispatched again, so a screen cell cut by a limit after its
  owner started stays a STOP and, once its latch is cleared (README step 16), reads as an unknown.
- A shared account fault is redispatched once per slot and a repeat on the slot stays a STOP, which latches both
  lanes: a lane that starts cells unread into an exhausted window stops there, as it would after any repeated fault.
- An assessor that meets a limit is not that fault: the cell's STOP (`assessment failed`, `assessor produced`,
  `assessment held:`) is regraded from preserved evidence, as before, each regrade after the same readiness check.
  Where the old rule held such a regrade while a window read 95% or more, an unread window lets it try once a minute
  until the window resets, the default login changes or the slot's 99 archives are used, which latches the lanes.
- The caps, every decision rule and every verdict reading.

## What was known of the outcomes

When the change was decided and written (11:25), 8 of the 18 screen verdicts existed; no probe had run, so no event
was known; the orchestrator had seen the completion status of s01, s02 and s03 only (PRODUCT_INCOMPLETE, COMPLETE,
PRODUCT_INCOMPLETE). Checking these facts read those three statuses again and nothing else of the outcomes. While it
was reviewed the screen went on under the old rule, and the orchestrator saw the status of s08 and s09
(PRODUCT_INCOMPLETE, COMPLETE). The change does not depend on any outcome and applies to every arm alike. "Applied"
says where the run stood when the amended driver started.

## Which cells ran under which rule

Each cell's `seal.json` records `source_commit` and the sha256 of every apparatus file. The cells dispatched before
the lane's restart carry the registration commit `3691c4e9` and its `driver.py`; the cells dispatched after it carry
the merge commit of this amendment and the amended `driver.py`. A cell dispatched before the restart and regraded
after it keeps its seal; the lane's log names such a regrade (a `regrade` event after the restart).

## Operator steps

1. Set the operator hold (`touch $R/operator-hold`), wait until no cell is running, and stop the lane (an interrupt
   sets no latch).
2. Move the run worktree (`~/.local/share/nx01/0266-run`) to the merge commit of this amendment.
3. Stop the operator's back-off loop (`night/backoff.py`, which only set the operator hold after a refused reading).
4. Start the lane again with its README command. It skips the cells that have verdicts and holds on the operator
   hold until that file is removed (`rm $R/operator-hold`).

## Reported in RESULT.md

- The holds as before.
- The number of `window_unread` events per lane (the Claude lane's log holds the screen too):
  `for lane in claude codex; do echo "$lane $(grep -c '"event": "window_unread"' $R/output/driver-$lane.log)"; done`
  It counts readiness checks passed without a reading: a refused reading (`retry_after`) and a check inside a
  refusal's `Retry-After` (`until`), before a cell's run or before a regrade. It is not a count of distinct cells, and
  a check can still be followed by a preflight that refuses the dispatch. RESULT.md names the cells from the lane's
  next `run` or `regrade` event after each one.
- The operator holds of this morning.

## Reviews

One pass on `2b2905a9`, GPT Astra (ultra) and Grok 4.7, read-only, in parallel: Astra RUN, Grok RUN, no CRITICAL or
HIGH. Each lower finding was fixed or rejected:

- Fixed in this file: "a malformed answer" said more than the code does (an answer that is JSON but not an object
  raises outside the hold, as it did before the amendment), so rule 4 now says "an answer that is not JSON"; the
  assessor path under an unread window; a cell regraded after the restart keeps its seal; what the `window_unread`
  count is and is not; where the app's readings come from.
- Fixed in `test_driver.py`: an answer that is not JSON holds; the deadline is not kept across a restart; a regrade's
  readiness check passes unread too; a split wait recovers after the deadline.
- Rejected: a `Retry-After` of several hundred digits would raise outside the hold and latch the lanes (Grok). The
  endpoint names seconds (909 and 3137 here), the failure would be a visible stop and not a wrong reading, and no
  such answer has been seen.

`driver.py` did not change after the review. The fixes were re-checked by the orchestrator against the code they
describe.

## Applied

The amended driver starts with the registered run. The whole screen ran under the old rule: its 18 verdicts were
complete at 12:41:45 KST, its probe and decision followed (`0266-screen:GO(K2)`, 12:42 KST), and no screen cell was
dispatched without a reading. So when the amended driver starts, the screen's outcome is known and no cell of the
registered run has been dispatched; every registered cell, in both arms and both lanes, runs under the amended rule.
