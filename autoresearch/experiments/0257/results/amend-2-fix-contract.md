Apply two review fixes to the uncommitted 0257 amendment 2 in this worktree (autoresearch/experiments/0257 only). Do not commit; no Docker, models, credentials or runtime files.

1. driver.py `amend_caps`: split-wait entries computed under the previous caps must not survive the cap change. When registering the amendment, clear `self.state['split_wait']` and include the cleared entries in the `caps_amended` event (e.g. `cleared_split_wait=`). Keep `split_blocks` (history). Add a focused test: a split_wait recorded under 85/70 is cleared by `--amend-caps` to 95/95, and the second cell then dispatches at 60/60.

2. amendment-2.md: replace the "does not favor either arm" claim with an accurate statement: the same guard applies to A and B and the AB/BA schedule is unchanged, but near exhaustion a longer cell is more likely to hit a limit mid-run; such quota faults are archived and redispatched, only the final verdict is scored, and archived attempts still count toward the reported attempts/usage of that arm. Restrict "usage is descriptive" to window utilization (decide.py does not use window percentages or estimates). Note the app setting is "switch at or below 5% left" (matching the driver's hold at >= 95% used). Mention in the operator steps that registering the amendment clears pending split waits.

Run `python3 -m pytest -q autoresearch/experiments/0257` and report the count.
