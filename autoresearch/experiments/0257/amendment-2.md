# 0257 amendment 2 — Claude window exhaustion guard (2026-10-22)

Dated amendment to the frozen [DESIGN.md](DESIGN.md) (r5), the
[registration](registration.md), and [amendment 1](amendment-1.md). It replaces
the window reserve only. The owner showed the six-account app, set to "switch
at or below 5% left" for the host Claude login, and said:
"이중에 계정 아무거나 풀린거 쓰라니까??" and "그리고 어차피 알아서 5% 미만이면 다른계정으로 바뀌니까 걱정말고 좀 그냥 하자".

## Change

For each Claude window (`five_hour`, `seven_day`), a cell or block starts when
the current host account's utilization is **below 95%**. No projected cell
usage is added. At 95% or above, the driver holds, re-reads after 60 seconds,
and waits for the affected window reset before a split block's second cell.
The post-SMOKE caps become `{"seven_day":95,"five_hour":95}` through the
existing dated `--amend-caps` registration path. The original 85/70 caps
remain required before the first SMOKE.

The same guard applies to A and B, and the AB/BA schedule is unchanged. Near
exhaustion, a longer cell is more likely to hit a limit mid-run. Such quota
faults are archived and redispatched under DESIGN §Operations; only the final
verdict is scored, while archived attempts still count toward the reported
attempts and usage of that arm. Window utilization is descriptive: `decide.py`
does not use window percentages or estimates for the comparison.
Account fingerprints per verdict (amendment 1), the deadline, harm latch,
and all other rules stay in force.

## Operator steps

1. Stop the holding driver while no cell is running.
2. Update the run worktree to include this amendment.
3. Set `caps` in that run's `runtime.json` to `{"seven_day":95,"five_hour":95}`.
4. Run `python3 driver.py --amend-caps amendment-2.md <runtime.json>` from the
   0257 directory. Registering the amendment clears pending split waits. Then
   relaunch the driver with the existing schedule.
