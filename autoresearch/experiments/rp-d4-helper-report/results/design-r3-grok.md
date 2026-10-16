## HIGH — ADOPT still fires with zero four-condition successes

`DESIGN.md` lines 176–182 and 208–210 call the delivery (the first three rp-d1 conditions) a correctly completed task and divide each arm total by 4. Attribution already requires every delivery to pass, so that test is raw arm total Y ≤ raw arm total X.

The owner rule this cites is O4 and 0232 §6 (`NORTH-STAR.md` lines 66–69). S is the frozen completion count. In this design that count is rp-d1’s four conditions, report included (lines 174–176). §6 sets per-success cost to total/S when S > 0, and to +∞ for selection when S = 0. A zero-success candidate never qualifies. When the baseline has S = 0 and the candidate has S > 0, the cost gate passes by dominance, and the raw sum is not the comparison. rp-d1 recorded Codex as 0/4 with every PR merged and published no per-success cost.

The extra bullet (both arms have a success, then per-success Y ≤ X) does not add a rejection. ADOPT already requires S_Y ≥ S_X. When S_X > 0 and total_Y ≤ total_X, total_Y/S_Y ≤ total_X/S_X. When S_X = 0 the bullet is skipped.

Round 2’s counterexample still adopts. X cleanup 0/4, Y cleanup 3/4, verification and merge 4/4, reconciliation 0/4, four-condition successes 0 and 0, every delivery passed, no Y category FALSE, both Claude guards passed, totals 99 versus 100. Per delivery, 99/4 ≤ 100/4. The per-success bullet does not run. Successes 0 ≥ 0. ADOPT fires. §6 does not qualify that candidate.

The same denominator COST HOLDs a case §6 passes: X successes 0 with total 100, Y successes 4 with total 101. Dominance would pass the cost gate. The /4 test holds it on the raw sum.

**Fix.** Delete the delivery denominator. Keep S as the four-condition success, totals over every dispatched attempt.

- S_Y = 0: the cost gate fails. With the other ADOPT conditions holding, that is COST HOLD.
- S_X = 0 and S_Y > 0: the cost gate passes by dominance. Publish that reason.
- Both S > 0: Y’s wall, input, and output per success are each ≤ X’s. UNKNOWN usage stays a STOP.

Requiring a success on both arms before cost can pass would COST HOLD the predicted Codex repair. The recorded baseline is 0 successes because cleanup was unreported. §6 admits S_X = 0 < S_Y by dominance. O4 chose that per-success rule over strict sums.

## Round-2 MEDIUM and LOW

**Conditional quote: resolved.** Against `main` at `cbc33be9724d3a6ebf85d708ea1dcd9bf8346440`, both instruction files change only two sentences. The report line is “Report verification, delivery, the result's `cleanup` verbatim when present and checkout reconciliation separately.” `BLOCKED` still names the cause and retry action (line 191). “No task is described as cleaned while owned disposable files remain.” is still there. The refused-cleanup sentence no longer carries the handoff/retry clause. The byte change is −22 (14309 → 14287), which matches those two edits. The Claude and o200k counts were not re-run here.

**Mirror: resolved.** `config/skills/_shared/task-completion.md` and `.agents/skills/_shared/task-completion.md` both contain those sentences and the same surrounding text.

**Grading rubric: resolved, with one LOW below.** The rp-d3 prompt is the pinned prompt, including “resources removed or their state truthfully reported.” Removal, `emptied`, and `was absent` match `COMPLETE` when the final resources are clear, and the emptied scratch directory is allowed to remain. Deferred, skipped, and scratch-incomplete clauses are mapped to `CLEANUP_PENDING`.

**In-place clause: resolved.** On `COMPLETE`, `linked` false says “the in-place checkout is not a cleanup target,” and the row says the call does not enter removal and does not stat the checkout.

## LOW — “undelivered fact” is not a cleanup fact

`DESIGN.md` lines 167–169 let deferred, skipped, and scratch-incomplete clauses match `CLEANUP_PENDING` or an undelivered fact. `github.py:359` sets cleanup only to `COMPLETE` or `CLEANUP_PENDING`. A failed delivery is still one of those two. Delete “or an undelivered fact.”

VERDICT: REVISE
