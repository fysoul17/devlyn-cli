The Candidate section's paraphrase is not safe. "A standing request to commit, push, open the PR and merge" is broader than the owner decision.

- A request that says commit only, PR only, local-only, no-push, no-commit, or just-edit must win. "Standing" can be read as outranking the current message. "Explicit limits win" is already in the bullet, and it did not win against Claude Code's system line.
- `devlyn.completionMode=pr` is project policy and must not be rewritten into a merge.
- With no GitHub origin, implicit delivery is a reported local commit. An explicit PR or merge stays blocked. Authentication and network failures are not that fallback (`task-completion.md` lines 18–21). Every measured repository has an origin, so the run cannot see this.
- Read-only work, unchanged work, and incidental files do not trigger delivery. The sentence has to keep the "completed, verified, with changes" gate.
- The managed block still opens with "Project-specific instructions outside this managed block take precedence over these defaults." That line has to stay.

Publishing when the user installed devlyn and gave no delivery limit is the product. Publishing when they limited delivery, set `pr`, or have no origin is the failure this paraphrase allows. ADOPT would ship that as a patch.

## Measurement

The skeleton matches rp-d4 and the ladder. Claude `high` is the primary. X is registry 4.2.22. Y changes only the two templates and their fingerprint data. `common.txt` stays fixed. BV and Z0 are interleaved X/Y, Y/X. Eight slots are never replaced. Codex Y on BV and Z0, plus one Claude `max` Y on BV, are guards. Smoke qualifying the apparatus when delivery does not happen is the right correction to rp-d5. The paired one-sided range 0.06–0.25 for a 3/4 against 0/4 result is an honest routing gate. Cost uses 0232 §6 in the right direction: all three per-pass figures ≤, `S_Y = 0` fails, `S_X = 0 < S_Y` passes by dominance, and a cost miss is HOLD with no adoption.

These parts do not yet hold:

- Branch 1 fires before any comparison. X=4/4 and Y=2/4, or X=3/4 and Y=2/4, is named NO PROBLEM. That is a regression. X≥3/4 also drops a real 3/4→4/4 lift. Keeping 3/4 as "not adopted at this size" is a fair product choice. Calling a worse Y "no problem" is not.
- "No publishing limit" is false as a model fact. Those two `common.txt` sentences are what o08 treated as one. Keep the prompt (one mechanism, comparable to rp-d1 through rp-d5), and pre-register the failure class: uncommitted "didn't ask" versus `LOCAL_ONLY` citing the prompt. Both fail delivery. They are not the same cause.
- "Every dispatched attempt" can be read as folding g01–g03 and smoke into Y's cost. The pool is m01–m08 only. Guards are pass/fail. Smoke and guards stay out of W, I, and O.
- The rewritten decision section never says incomplete usage is INCONCLUSIVE. A partial token total can make a more expensive Y look cheaper.
- A `merge_refused` byte hit fails the slot and can swing ADOPT or REJECT. rp-d4 made any such hit INCONCLUSIVE and did not replace the slot. Repo policy and transcript refusal are not evidence about this sentence.
- The token gate sits inside ADOPT. It is a registration precondition. A failed gate must stop the run before smoke.
- The models-cache change is spare-only. rp-d5's spare died because staging re-hashed the live host file (`38e0d508…` registered, `5a0d377d…` at the re-run). Every attempt, including the first, has to bind the copy frozen at registration.
- Smoke "failure" is undefined. No delivery still qualifies. An apparatus miss (owner exit, release, Claude effort binding, COMPLETE usage, archive, 404, pack diff) consumes the one spare pair. A second miss stops the run. Smoke must not edit the sentence, arms, or thresholds.
- Effort binding applies to Claude bodies. Codex guards may not have `output_config.effort`.
- The frozen prediction ("Y raises X to at least 3/4") does not match the branches. Freeze "Y ≥ 3/4 and Y > X, and no guard fails delivery" after the branch order is fixed.
- Guards are observed safety on the no-limit prompt, not a controlled comparison, and they do not cover commit-only, `completionMode=pr`, or no origin. Say that in the interpretation limits. One Claude `max` BV cell is enough only with that label. g03 failing adoption is already MIXED, which is right.

`S_Y = 0` inside ADOPT is unreachable once Y ≤ X is REJECT and ADOPT requires Y ≥ 3/4. Keep it as the 0232 clause. "Strict improvement in passes" is also automatic once the branch requires Y > X. 0232 already admits a completion increase with tied costs. The live cost test is: each of wall, input, and output per delivery pass is ≤ X, with dominance and no raw-sum substitute when S_X = 0.

## Candidate wording

Hand count only. I did not run `token_gate.py`, Claude `count_tokens`, or o200k. Do not treat this as a gate pass.

Current Delivery bullet: 445 characters. Proposed bullet: 439. A six-character margin can still retokenize upward. The gate is the whole managed block: the precedence line, the template, and the markers. The sha256 comment stays the same length. `CLAUDE.md` and `AGENTS.md` stay byte-identical, so one count plus an equality check covers both. Both counters must be ≤ the 4.2.22 block before registration.

```text
- Delivery — direct work edits the current checkout. No delivery limit on a completed, verified change is the user's ask: follow project policy now (`_shared/task-completion.md` in `.claude/skills/` or `.agents/skills/`, project else `~`; default PR and merge). Concurrent writers: isolate before edits; unexplained changes: pause until safe or isolated. An ideate drain delivers every task. Explicit limits win; commit alone stays local.
```

What this keeps: edit in place, the completed/verified/changes gate, the file path, default PR and merge, isolate-before-edit, pause on unexplained changes, drain delivery, and the existing limit sentence, including commit-only. "No delivery limit … is the user's ask" is the identity the smoke said was missing. "Follow project policy now" sends the model into `task-completion.md`, which already owns `completionMode`, no-origin `LOCAL_ONLY`, and blocked explicit PR with no origin. It does not issue a new standing order to push and merge.

If either counter rises, apply this payment order and stop at the first version that passes. Do not cut the North Star, the seven principles, or the Saint-Exupéry sentence.

1. `isolate before edits` → `isolate first` (−7).
2. Drop ` now` (−4).
3. Only then, and only if the gate still fails, drop ` An ideate drain delivers every task.` The same sentence remains at `task-completion.md` line 16. Record that payment. It is the one cut that can change behavior for a model that never opens the file.

`scripts/test-windows-portability.py` pins the current bullet in `CURRENT_RULES`. Update that fixture with the registered sentence.

## Findings

**HIGH — Unscoped standing request.** The paraphrase authorizes commit, push, PR, and merge. That overrides a commit-only request, `completionMode=pr`, and the no-origin local route, and the run cannot see any of those. Replace it with the scoped bullet above. ADOPT ships that registered sentence only.

**HIGH — Branch order.** First match on X ≥ 3/4 labels Y < X as NO PROBLEM. Put REGRESSION first: Y < X, no adoption. Then NO PROBLEM: X ≥ 3/4, skip not reproduced at this size, no adoption. Then REJECT: Y ≤ X. Then ADOPT, HOLD, MIXED as now.

**HIGH — Models cache.** Bind the registration-time copy on every stage, including the first attempt and the spare. Do not re-read `~/.codex/models_cache.json`.

**MEDIUM — Cost pool and UNKNOWN usage.** W, I, and O are m01–m08 only, divided by that arm's delivery passes. Guards and smoke are excluded. Usage other than COMPLETE on a measured slot or guard is INCONCLUSIVE before the branches. Dominance is reported as dominance, with no raw-sum comparison.

**MEDIUM — `merge_refused`.** Any structure-free hit on a measured slot or guard is INCONCLUSIVE. The slot is kept and not replaced.

**MEDIUM — Prompt confound.** Delete the claim that `common.txt` contains no publishing limit. Record uncommitted "didn't ask" and prompt-cited `LOCAL_ONLY` separately. The primary endpoint stays binary delivery.

**MEDIUM — Smoke and effort binding.** Define an apparatus miss as anything except non-delivery. One spare pair, then stop. Pack diff (templates plus fingerprint data only) is a qualification check. Claude effort binding is Claude bodies only. Smoke must not change the sentence.

**MEDIUM — Token gate placement.** Run both counters before registration. A miss means do not smoke. Remove the gate from the ADOPT branch.

**MEDIUM — Prediction and limits.** Align the frozen prediction with Y ≥ 3/4, Y > X, and guards delivering. State that guards are observed safety, not a comparison, and that explicit limits, commit-only, `completionMode=pr`, and no origin are untested.

**LOW — Name the Y paths and the fingerprint generator before registration.** g03 guards BV only. That is acceptable once it is labeled a guard.

VERDICT: REVISE
