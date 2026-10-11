# 0248 d09 native child process and novelty audit

Prospective read-only audit prediction, 2026-10-10T23:00:00.739174+00:00: native Agent review should appear as a child of the B owner, not an experimental peer-helper session. Session and terminal accounting should reconcile the child once. Concrete timestamp novelty and mutation/random-check claims must be traced to actual pre/post commands and controls. Preserve all recorded verdicts and costs; no replay is planned.

## Outcome and scope

PASS for this bounded process/accounting audit. Preserve the recorded **CHECKS_PASS / COMPLETE**, **8,074,123 input / 208,961 output**, **1,794.5719497080136 s**, public **8/8**, all four frozen oracle cases PASS, local delivery PASS and CLEAN cleanup. Nothing was replayed or regraded. This report does not prove every interpretation of the task.

## Actual native review and answer custody

B retained the native `Agent` capability and used it automatically. Owner stdout LF875 calls one `general-purpose` agent, “Independent spec review of diff”; `model` and `run_in_background` are absent. LF878 records native asynchronous launch. The actual owner and child transcripts both use **claude-opus-5-5**, with **effort=max / perTurnEffort=max**. Parent session is `a2ab75c1-dc97-47de-b8ef-72457e779b14`; the child has agent ID `a379a57d34288d96f` within that session. Terminal native statistics report one background start, one completed child, depth one, no grandchildren or failed children. Owner calls are Bash40/Edit18/Agent1; child calls are Bash16/Read2.

This is a baseline with native collaboration, not a strict solo run and not H/P experimental helper activation. The child receives an owner-authored condensed spec and the owner's interpretation choices; despite its “verbatim” label, that prompt is not the byte-exact original caller request. The native child has Bash and can create scratch files. The retained calls show its fixtures, reference implementation and mutations under `/tmp/fw-review`, with no observed child edit or commit in `/cell/work`. Owner source repairs follow the completed review. No five-file helper custody or enforced read-only tool catalog is claimed.

LF1082 explicitly says the review is still running and defers findings/fixes. The complete child final answer is at stdout LF1151 and completion notification LF1153. Owner native transcript LF233 contains its complete 4,128-character answer in the notification's `<result>`; XML decoding changes only `&amp;&amp;` back to `&&` and yields exact equality with the child final text (SHA256 `50bde5c79e0543d52004b4dd4432a9054e288ae993bcda49e544b54c56876e04`). Owner LF1221 responds to all four reported categories before editing. Two startup records, LF1 and LF1155, agree in every field except UUID. Raw stdout contains no literal U+2028, U+2029 or U+0085.

## Whole cost, counted once

Deduplicating actual assistant message IDs independently reproduces the retained accounting:

| Scope | Terminal messages | Ordinary input | Cache read | Cache creation | Normalized input | Output |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Owner | 48 | 98 | 6,995,891 | 207,183 | 7,203,172 | 154,967 |
| Child | 16 | 32 | 787,799 | 83,120 | 870,951 | 53,994 |
| Total | 64 | 130 | 7,783,690 | 290,303 | 8,074,123 | 208,961 |

Both final result envelopes (LF1615/1616) repeat the same cumulative `modelUsage`. Counting that aggregate once reconciles with the owner-plus-child terminal totals; adding both envelopes, or adding child usage to that already-inclusive aggregate, would double count. Thinking 156,236 is already in output. Notification token estimates are not additional usage. The existing accounting is MATCH with no gaps, API errors, retries or unknown residual. These are native emitted counters, not independently verified provider billing.

## What the child contributed

The owner had already seen `.123456Z` become `.123Z` in a Date.parse probe at LF320/321. Its earlier ordering tests and random population did not establish correct ordering inside a millisecond. The first retained concrete competing-order counterexample comes from the child at LF1112/1114: stock one; equal-priority orders **a at .000900Z** and **b at .000100Z**, each requiring one unit. The actual CLI accepts a/rejects b; the child's separate reference accepts b/rejects a.

Credit the child with connecting the known primitive truncation to an executed order-allocation failure, not with first discovering that Date.parse truncates fractions. Independent execution is evidenced, but the review was primed by owner-supplied decisions. No general causal or harness-effectiveness inference follows.

After the answer, owner LF1222/1223 reprobes Date.parse on fine fractions. Source edits LF1283/1287 preserve epoch milliseconds and compare residual fractional digits (trailing zeros removed) before id. Test edits LF1312/1405 cover the gap, with subsequent passes and meaningful mutation failures. I did not locate a separate owner execution of the exact child's JSON before the fix; the child performed that reproduction, while owner confirmed the primitive and ran the repaired regressions.

The owner retains the leading-dash-path convention, narrows the displayed accepted timestamp format instead of supporting every suggested ISO form, and strengthens nearest qualifying warehouse and validation coverage. Final choices also retain zero-quantity remaining lots, UTC for offset-less times, unique warehouse IDs, nonnegative distances, explicit boolean single_warehouse and greedy input-line processing. These are reported choices/ambiguities, not new oracle requirements.

## What the retained validation counts mean

The child executes 400 then 600 random valid cases (1,000 total) against its own reference, with no differences, and separately executes the failing submillisecond witness. Its nine targeted mutations all survive at LF1134. The same scratch harness then detects two positive controls at LF1139: removing rollback and allowing zero quantity each fail a test. It checks replacement patterns before testing. “All survive” here identifies gaps in that selected test set, not a broken harness.

Owner mutation coverage develops in stages: 11 early candidates are caught; a later 25-candidate batch catches 24, while whole-second truncation survives (LF1359). A strengthened ordering test then catches that mutant plus five related candidates (LF1408). The final “25 deliberate bugs” statement combines stages; it is not one final 25-candidate all-fail rerun.

The owner's random comparisons also have distinct populations:

| Stage | Seeds | Successful waves | Actual CLI subset |
| --- | --- | ---: | ---: |
| Before review/fix, first coarse-time reference | 7, 12345 | 40,000 | 300 |
| Before review/fix, later source/test stage, same coarse population | 99, 4242 | 40,000 | 300 |
| After fix, fractional/offset timestamps and BigInt picosecond reference | 31, 777 | 40,000 | 300 |

Commands/results are LF698/701, 850/853 and 1430/1433. Most comparisons call functions exported from a scratch copy; the first 150 per seed also execute the actual CLI under Asia/Kolkata. Retained successful batches total 120,000 waves across stages, with **40,000** in the post-fix fractional population. The final 80,000 claim should not be represented as 80,000 final-version, fraction-aware CLI invocations. LF1455/1456 provides a positive control: dropping submillisecond comparison from a scratch copy makes the updated reference produce MISMATCH; the copy is restored.

LF922/923 reproduces the directory-form test command's MODULE_NOT_FOUND both on the current tree and an archive of the actual original HEAD `87d89d2`; package `npm test` delegates to that command. After repairs, LF1475/1477 executes both explicit test files and records **11/11**, while the final public delivery check is **8/8**. Node 18 was not available: compatibility is inspection-only, not a Node 18 execution claim.

## Local delivery and protection

The retained receipt and delivery check bind local commit **924942c7dec399d4c38ab48a4549c3e5acb33b81** from baseline **87d89d2ad867b2f39b7df57ae131989c803f0158**, changing only `bin/cli.js` and `tests/cli.test.js`. The LOCAL_ONLY receipt binds acceptance and the public log, source/publish SHA, and recovery ref `refs/devlyn/completed/7c4d6cc244fee449f7ebacb0`. Worktree cleanup is CLEAN; retained owner cleanup removes its scratch directories, and this audit's read-only git status is clean.

The accompanying JSON binds the bounded protected set of 34 raw/source/receipt/frozen files before and after audit. All match. Broader inventory integrity is a separate root audit. The prediction above is preserved verbatim; its pre-read SHA256 is recorded in JSON. Only this Markdown report and its JSON companion were written. No further writes are planned.
