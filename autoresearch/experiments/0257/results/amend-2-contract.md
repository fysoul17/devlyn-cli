You are implementing 0257 amendment 2 in this worktree (devlyn-cli). Work only under `autoresearch/experiments/0257/`. Do not commit. Do not run Docker or any model; do not read credential files or the keychain.

## Owner decision (2026-10-22, verbatim Korean)

The owner showed the multi-account app (six Claude accounts; it switches the host Claude login automatically when the current account has 5% or less left) and said: "이중에 계정 아무거나 풀린거 쓰라니까??" and "그리고 어차피 알아서 5% 미만이면 다른계정으로 바뀌니까 걱정말고 좀 그냥 하자". The run had held for hours on the registered reserve rule (five-hour used 61% + 2×25% estimate > 70% cap) while other accounts were free.

## Rule change (amendment 2)

Replace the window reserve with an exhaustion guard:

- A cell (or block) starts when, for each Claude window (five_hour, seven_day), the current host account's utilization is below 95%. No estimate is added. 95 matches the app's switch threshold (5% left): at or above it the app is about to switch the login, so the driver holds and re-reads after 60 s.
- Caps become `{"seven_day": 95, "five_hour": 95}` registered through the existing `driver.py --amend-caps <amendment-file> <runtime.json>` path (the operator edits runtime.json; you do not touch any runtime file).
- Unchanged: a cell that hits a usage limit mid-run is a quota fault, archived and redispatched (DESIGN §Operations); account fingerprints per verdict (amendment 1); deadline; harm latch; everything else.
- Usage is descriptive only; nothing in decide.py reads estimates (verify this).

## Code

In `driver.py`:
- `fits(windows, caps)` = every window's `used < caps[window]`. Remove the estimate from `ready` and from the split-wait `exceeded` computation (a second cell waits for the reset of the windows at or over the cap, as before but without estimate).
- Remove code the change makes unused: `estimates`, `delta`, `FLOORS`, and anything else only they used (check `same_window` and others still have callers before removing). The "incomplete Claude account pair" integrity check lived inside `estimates`; if removing it drops the only check, say so in your report instead of re-adding machinery.
- The `hold` event for this reason should log `windows` and `caps` (no estimate). Reason text: `Claude window near exhaustion`.
- Keep the registration-time guard that requires 85/70 before first SMOKE (it describes the registered start); post-SMOKE cap changes still require the dated amendment path.

Tests in `test_apparatus.py`: update/remove tests of the removed estimate behaviour; add focused tests: dispatch at 94/94 with the old estimate that would have exceeded; hold at 95 in either window; split-wait second cell waits only on windows at/over the cap. Run `python3 -m pytest -q autoresearch/experiments/0257` and `python3 -m pytest -q autoresearch/experiments/0256` and report counts.

Docs:
- New `autoresearch/experiments/0257/amendment-2.md`, modelled on `amendment-1.md` (read it): date, owner quote, what changes, why it does not bias the A-vs-B comparison (both arms face the same guard; quota faults are already reruns; usage is descriptive), what stays, and the operator steps (stop the holding driver with no cell running, update the run worktree, set caps 95/95 in runtime.json, `--amend-caps amendment-2.md`, relaunch). Short.
- README.md: mention amendment 2 next to amendment 1 and update the driver row and the `--amend-caps` sentence if needed. Do not edit DESIGN.md (frozen).

Report: files changed, test counts, and anything you removed or could not remove.
