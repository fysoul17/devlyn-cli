# 0247 s01 native protocol audit

Prospective read-only audit prediction, recorded 2026-10-10T20:48:11.562258+00:00:

The retained run should bind one Claude owner and one Codex Astra/max peer session across fresh and resume, preserve source during each call, deliver both full answers before finalization, and retain ten unchanged canonical peer files after the two caller TemporaryDirectory contexts disappear. Complete accounting should reconcile owner and peer costs once. Actual Unicode and repeated-init shapes will be counted from untouched bytes; their absence will not be replaced with a replay or a fixture-derived native claim. The recorded CHECKS_PASS/COMPLETE outcome will be preserved, with ambiguous rounding semantics treated only as owner observations.

## Result and scope

**PASS for native protocol, custody, and recorded accounting.** The retained verdict remains **CHECKS_PASS / COMPLETE**, owner exit 0, cleanup CLEAN, identity/peer-policy/Claude-accounting MATCH, and no usage gaps. Recorded cost is **5,238,939 input / 119,409 output tokens over 1169.6533141669934 seconds**. This is a smoke cell with `measurement_eligible: false`; its oracle list is empty. No efficacy inference or hidden S2 semantic regrade follows from this audit.

The sibling verdict SHA-256 is `bbda248a6f880af26ca9cafacea202c261b5cd6936102479d7a34d27fa8af923`. This audit read retained files only: no model, native, evaluator, test, or authentication replay. The accompanying JSON identifies the 118 protected source/evidence files and their before/after hashes.

## Actual identity, capability, and request fidelity

The Claude owner was `claude-opus-5-5` at max effort, session `3e45936a-058a-4ca7-b927-eddb5eac50cd`. Owner stdout contains one startup init and 1,385 LF-delimited records. Actual owner calls comprise 36 Bash, two Read, three Write, and one Edit.

Both peer calls were **Codex gpt-6-astra/max** in session `01a1278d-56c4-7852-a720-8132bc7afd12`: fresh completed in 65.01826419700228 seconds; resume in 14.931124590992113 seconds. Both canonical completions say EXITED, exit 0, no error, and unchanged source. Resume requested the exact fresh session.

The actual first inference requests, not merely planned argv, bind Astra/max and contain only the `functions` and `clock` tool namespaces. Neither includes collaboration tools, `multi_agent_role`, or `multi_agent_mode`. Their payload4.json hashes are fresh `9222244a3a2b9425473e3a40309a100720842bfbec4009a91bf94ca95022372a` and resume `7cc87034191a04174ce3b74efeaf2bb51085037aa7a80a59e9c418183e1964d6`. The shared rollout's turn contexts at LF lines 6 and 46 record read-only sandbox, approval never, and disabled multi-agent mode. The session metadata has no parent; only the fresh/resume trace directories belong to this peer session.

Both argv retain `agents.enabled=false` and `features.multi_agent_v2.enabled=false`, read-only sandbox, approval never, Astra/max, JSON output, and the 540-second watchdog. Fresh used three exec tool calls encompassing seven commands; resume used one command. Observed actions read source, guide, git state, and consumers, and execute Python with `-B` for unit/decimal checks. No edits, child delegation, or network calls were observed.

The fresh prompt is 8,667 characters. The original caller.json **request value** occurs verbatim once at character 744, before the owner interpretation at character 7,622. This is not a claim that the whole caller.json file was embedded. Actual fresh inference input contains the exact fresh prompt; actual resumed input retains that prompt and the exact resume prompt. The recorded prompt hashes bind both.

All four source snapshots—before/after fresh and before/after resume—are equal, each with 55 entries and baseline HEAD `b546ed579627f34203db2dcb51866925f98bc108`. Final source bytes also match those snapshots. The subsequent local commit changes repository history, not the reviewed source bytes.

## Actual temporary cleanup and canonical records

The owner actually ran `cell/work/.devlyn/pair/owner/peer_call.py` twice. Each invocation entered a TemporaryDirectory, wrote request.md, called the installed helper, copied/read the answer there, and then exited the context. The driver inherited its environment unchanged and checked only CLAUDECODE presence.

Both temporary directories, `/tmp/pair-fresh-hfyz62ce` and `/tmp/pair-resume-5wl1m2ht`, are absent. Exactly two canonical directories remain: `peer-qg8uavxn` and `peer-tfjkhzlt`. Each retains attempt.json, completion.json, finalanswer.txt, native JSONL, and stderr: **ten canonical files total**.

For both calls, current canonical byte hashes equal the driver's in-context and after-exit maps. Fresh records also remain identical after resume. The owner checks this at stdout line 1,074 and checks final records, no live peer process, and no remaining temporary directory at line 1,369. The audit independently compared every retained file with those maps. The JSON's protected hash inventory contains their exact hashes.

## Full answers and executed witness

The fresh answer is 882 bytes / 872 characters; the resumed answer is 232 bytes / 230 characters. Both match their native final messages. The whole fresh answer appears in the owner's tool result at stdout line 933; the whole resume answer appears at line 1,038. Both are consumed before the owner's final response at line 1,384.

The peer reported no supported violation and proposed `calculate_total(1, 50, 50) == 2` under the chosen rounding interpretation. Resume recalled the same witness. The owner actually executed the assertion: command at line 979, exit 0 and value 2 at line 980. The witness was executed again during delivery checks at lines 1,225 and 1,253. These are retained command outputs, not acceptance-record command strings mistaken for executions. Peer source hashes and the four source snapshots remain stable across both calls.

## Usage reconciled once

The 38 deduplicated terminal Claude assistant messages sum to 76 ordinary input, 4,940,528 cache-read input, 193,680 cache-creation input, and 116,166 output tokens: **5,134,284 normalized input / 116,166 output**. These equal the retained Claude terminal and accounting totals. Thinking tokens are included in output.

Fresh Codex trace has four unique response IDs totaling **64,379 input / 2,859 output**. Resume has two further unique IDs totaling **40,276 input / 384 output**. Their sum is **104,655 input / 3,243 output**, exactly the resumed native cumulative turn.completed total. Adding fresh usage to that cumulative total would double-count fresh; the recorded whole-run usage does not do so.

Thus owner plus peer equals **5,238,939 input / 119,409 output**, exactly the verdict. Cache and reasoning subtotals are not added again. There are two actual peer calls, six distinct Codex response IDs, and no invented missing usage. COMPLETE describes the retained native accounting; this is not an independent provider billing audit.

## Delivery and limits

Retained evaluator artifacts report source PASS, four public tests PASS, and delivery PASS. The local commit is `2b4450f914910b4331d65b8ccf0d4413514e1484`, parent `b546ed579627f34203db2dcb51866925f98bc108`, adding only calculate_total.py and test_calculate_total.py. The completion receipt and `refs/devlyn/completed/0bb15e599fb544c2e07a9eee` retain acceptance, checks, and peer-check custody. Owner output records LOCAL_ONLY completion, source/publish commit equality, released writers, and cleanup. Read-only git inspection confirms the commit, clean worktree, main reconciliation, and removal of the temporary worktree/branch. No push is claimed.

The owner's additional outputs report 3,334,111 differential cases with zero mismatches and five killed mutants. These are owner-selected checks under the same rounding reading, not hidden-oracle evidence. The final response explicitly distinguishes rounding the discounted subtotal before tax from rounding the discount amount before subtraction: the peer witness gives 2 versus 0. The audit preserves that ambiguity as an observation; neither peer agreement nor the public checks independently resolves every possible interpretation of the task.

There is **one** actual owner init. Owner stdout, both peer captures, and the shared Codex rollout contain **zero literal U+2028, U+2029, or U+0085**. The fresh/resume captures contain 20 and seven LF records respectively. This native run therefore does not exercise the repaired Unicode/repeated-init failure shapes; the previously retained focused fixtures remain their direct regression evidence. No reroll was performed, and no prior STOP was modified or regraded.

## Integrity

All 118 protected hashes match the pre-audit snapshot. Only this report and its JSON companion were written. The prospective prediction above is preserved verbatim.
