ed in the current files:

- Guard attribution. `results.md` now says both Claude reports quoted the helper sentence verbatim. `g01-final-report.txt` and `g02-final-report.txt` both contain `Removed the task worktree; deleted the local task branch; deleted the remote task branch; emptied the task scratch.`
- `HANDOFF.md` line 3 now says one Y report quoted the sentence and one paraphrased it, and it attributes the cost pass to dominance over zero-success X.
- The reading states a 2/4 versus 0/4 difference at one-sided exact p = 0.25 and calls it an observed difference, not an established effect.
- Reconciliation hyphenation is split: m02 `fast-forwarded`, m07 `fast forwarded`, matching those final reports.

The slot table, arm totals (X 2,264,753 in / 21,286 out / 512.6 s; Y 1,581,115 / 20,458 / 425.8 s), cleanup 0/4 versus 2/4, success 0/4 versus 2/4, and one-decimal owner seconds match `summary.json`. Two favourable discordant pairs give p = 0.25. The scale note (X 0/8, Y 4/8, about 0.06) is 0.5⁴ = 0.0625 and is labeled a routing test. m02, m07, g01, and g02 quotes match the reports. Reviewers agree on every SUPPORTED finding; the only split is MISSING versus AMBIGUOUS on failing reconciliation. No FALSE. All ten measured slots have `merge_refused` false. Live helper stdout for m03, m06, and the Y smoke contains the cleanup sentence in command output Codex received.

Ordered rules in `DESIGN.md`: no INCONCLUSIVE precondition, X cleanup 0/4 is below BASELINE MOVED, Y 2/4 is above REJECT, and ADOPT fails only on Y cleanup ≥ 3/4. `summary.json` has `claude_guard`, `no_y_false`, `other_categories`, `successes`, cost dominance, and strict improvement true, with `cleanup` false and reason `an adoption condition other than cost or strict improvement failed`. That is MIXED. `HANDOFF.md` line 3 and the rp-d4 paragraph at line 243 use the same counts. The paragraph’s token recount is the registration figure (4867 → 4862 Claude, 2979 → 2976 o200k).

The candidate cleanup sentence is absent from `config/` and `.agents/` in this worktree. This session has no shell, so `git diff cbc33be9 -- config .agents` and `git diff HEAD~1` were not executed; the skill-file text matches the baseline checkout at `cbc33be9`, and the four round-1 wording changes are in the current files. A scan of committed json, md, txt, and log evidence found no token, private key, IPv4, or VPN hostname. `route-watch.log` names only `en0` and `none`, last line `2026-10-17T02:07:25Z`.

VERDICT: SHIP
