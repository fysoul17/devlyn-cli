# 0248 d05 native protocol and novelty audit

Prospective audit prediction, 2026-10-10T21:32:35.237824+00:00:

The retained evidence should bind one Claude owner and one read-only Codex Astra/max peer with unchanged source during review, a fully consumed answer, retained canonical custody, and whole-run usage reconciled once. The owner may already have exercised timestamp and integer bounds before peer review; novelty will be attributed only after checking command/output chronology. The recorded CHECKS_PASS/COMPLETE and frozen oracle outcomes will be preserved. Unicode/startup shapes and baseline failures will be reported only as actually evidenced. No execution replay is planned.

## Result and preserved outcome

**PASS for this bounded protocol, custody, accounting, and chronology audit.** The original measured-cell outcome remains **CHECKS_PASS / COMPLETE**, owner exit 0, all recorded gates PASS/MATCH, cleanup CLEAN, and peer activated. Whole cost is **10,593,254 input / 193,245 output tokens, 1751.5711559999909 owner seconds**. The verdict SHA-256 is `7ebc4cbafd44f16c41027becc3c4b3dcb8cb917ce4ab426fbe290ae150ebd028`.

Effective registration is 0248 registration-v2.md, SHA `866b4384dd32f891b8539ba93a6dd645e2010d85d2fa02966d3203e1fb27e91f`, and freeze-measured-v2.json, SHA `16b49370e62922eed63aa3396102f89cfb258c7cc001503a407d6bf6045e00d3`. The four recorded oracle results—priority rollback, single-warehouse FEFO, submillisecond ordering, and offset equivalence—remain PASS. They were not rerun or regraded.

## Actual peer protocol and custody

The native Claude owner is `claude-opus-5-5` at max effort, session `f2d492ec-107d-4a74-b2c9-f7d77208dacb`. Actual execution argv and transcript effort/per-turn-effort fields agree. Owner calls were 52 Bash, ten Edit, two Read, and one ToolSearch. Both owner terminal results report zero spawned subagents.

The owner read pair.md at stdout LF line 33 and invoked the helper at line 1,454 without an explicit pair request in the caller contract. There was **one fresh Codex peer**, no resume, session `01a127b4-62df-7ba2-a03c-229ea7201b2e`, **gpt-6-astra/max**. It finished EXITED/0 in **125.28582834899134 seconds**, error null, within the 540-second watchdog.

The actual first inference request payload4.json has SHA `5840e78ee251654b15ba3d973cbd88ad8b07ec872865e05777cff7a3fba8b50a`. Its `additional_tools` catalog contains only `functions` and `clock`, with no collaboration namespace or child-agent instructions. `multi_agent_role` and `multi_agent_mode` are absent. Actual native context records read-only sandbox, approval never, restricted network, and disabled multi-agent mode. Both disabling flags are also present in argv; the finding is supported by actual request/context evidence, not flags alone. One session/trace exists and no descendants were observed.

Four peer exec calls invoked nine shell commands. They read source, git state, instructions, and consumers, and executed in-memory /dev/stdin reproductions. The quantity-2^53 command's exit 2 is the deliberate observed product rejection, not a failed native peer run. There were no observed peer edits or child launches. The source-before and source-after snapshots are identical: **680 entries**, HEAD `8414826b8cba4ae2264eb2220bb776815bd6bc3e`.

The 26,138-byte prompt binds the original caller.json **request value** verbatim once at character 121, before candidate diff at character 4,220 and raw public-check results. There is no separate owner-interpretation section. The actual inference input contains this exact prompt, SHA `ee5ef042e1b88f82b54284e056548468ecf5dcb8e8dfcd5300780d077b556846`.

The canonical `cell/work/.devlyn/pair/peer-o71uk85w` directory retains all five files: attempt.json, completion.json, native JSONL, stderr, and finalanswer.txt. Their exact byte hashes are in the JSON companion. The full 1,217-byte answer matches native final message LF line 24. An initial oversized completion read was followed by a focused read: owner stdout **1,568 contains the entire answer**, before final response line 1,994. Its hash is `572e695bca1dedadd0d3a4fc17669782eb0bd35e3b1c410fcab16d55df442895`. This ordinary cell used retained canonical custody directly; it did not need the earlier smoke's temporary-directory exercise.

## What the peer added

The chronology does **not** support crediting the peer with discovering an unknown timestamp or quantity boundary:

| Actual owner stdout LF lines | Retained operation and output |
| --- | --- |
| 418 / 419 | Before implementation, Date.parse probes show calendar normalization, submillisecond truncation, timezone behavior, and safe-integer versus integer differences. |
| 952 / 953 | Before peer launch, CLI probes accept MAX_SAFE_INTEGER, reject exactly **2^53** with exit 2 and the old “positive integer” message, and verify .00015 precedes .0002. A no-offset timestamp case is also run under a different TZ. |
| 1,447 / 1,448 | Public command `node --test tests/cli.test.js` passes 10; its complete output and candidate diff are embedded in the peer request. |
| 1,454 | The peer is launched. |
| 1,568 | Full peer answer is consumed. |
| 1,644 / 1,645 | Owner runs the peer's complete 2^53 allocation witness: exit 2. It also demonstrates adjacent integer parsing/arithmetic loss using a scratch mutant. |
| 1,684–1,693 | Owner keeps the safe-integer predicate, clarifies its comment/error message, and adds a boundary rejection test row. |
| 1,715 / 1,718 | Public tests still pass 10; the peer witness still exits 2, now explicitly saying “no larger than 9007199254740991.” |

The earlier owner witness had a 2^53 lot and no orders. The peer supplied a **different concrete operation**: an order requesting that whole exactly representable quantity, plus the interpretation that the explicit “positive integers” requirement does not specify the safe-integer cap. It also ran a quantity-1 positive control. This is a novel full-allocation witness and a semantic challenge, while the limit and its rejection were already known.

The owner rejected the proposed behavioral change, showing that parsed 2^53+1 collapses to 2^53 and that permitting Number.isInteger-only stock can lose a unit for 2^53+2 minus 1. Those are actual neighboring witnesses. They motivate a safety policy but do not refute the peer's specific exactly representable whole-quantity case or prove that the contract requires that policy. The owner's broad final wording that JSON cannot hold those integers exactly must therefore be read with this qualification.

Independent comparison of the peer-read source with final source confirms the narrow change: **no allocation-logic or quantity-predicate change**; only a comment, the explicit upper-bound message used at the two quantity validators, and one test row. The final source was not sent to another peer. Stability claims apply to the original review interval, not to equality between that snapshot and final delivered bytes.

Accordingly, observed benefit is the challenge, explicit boundary message, and regression coverage—not repair of a newly discovered allocation failure. This audit does not impose a new task contract or adjudicate the disputed cap. It also does not treat oracle PASS as proof of every input interpretation.

Duplicate warehouse IDs were already rejected in the owner's pre-peer error probes (886 / 887), despite the request explicitly requiring uniqueness only for order IDs. Dropping exhausted lots from remaining was also a pre-peer chosen behavior and test. The final response openly retains these choices, strict presence of single_warehouse, UTC for offsetless times, and greedy line order without backtracking. They are preserved as reported ambiguities/choices, with no additional oracle claim.

## Recorded checks and cost qualifications

The baseline public command passes **3** at lines 62 / 63. The first candidate test batch passes **9** at 994 / 995; strengthened tests reach **10** before the peer and remain 10 afterward. The final main check at 1,958 / 1,959 passes 10. Explicitly listing CLI and server test files at 1,819 / 1,820 passes **13**.

The final claim of 20 killed mutations is supported by the final output at line 1,718: all 20 final mutations make tests fail. Earlier batches comprise 5, 10, 19, and 19 executions; the first string-time mutant and later ignore-distance mutant survived and prompted stronger tests. Thus there are **73 mutation-suite executions across five batches**, not 73 unique defects, and two observed early survivors. The scratch numerical probe is separate.

The owner-authored alternate allocator reports **400 seeded random waves, zero mismatches** both before and after peer review (1,416 and 1,718), with the same seed. These are repetitions of a 400-case corpus, not 800 independent cases or a hidden oracle. A 20,000-order timing run reports 0.155 seconds at line 1,379. The immediately preceding timing attempt failed because /usr/bin/time was absent and downstream JSON parsing saw empty input. The repaired local measurement is retained as one observation, not evidence that this harness is generally faster.

The owner did not literally invoke `npm test`; it invoked the package script's exact body, `node --test tests/`. At 1,819 / 1,820 Node v22.23.2 reports MODULE_NOT_FOUND for the directory. At 1,852 / 1,853 it reconstructs bin/cli.js, tests/cli.test.js, and package.json from the original HEAD in a fresh scratch directory and reproduces the same directory failure, with pass 0 / fail 1. Thus baseline provenance exists here, although this is not a full original-suite pass measurement. Package configuration was outside the two allowed paths and remained unchanged.

## Native accounting and repeated startup

The two owner terminal records at LF 1,558 and 1,995 belong to one session. Their usage fields describe disjoint increments; the final modelUsage is cumulative. Independently summing **56 deduplicated terminal assistant messages** gives 114 input + 10,188,418 cache-read + 260,870 cache-creation = **10,449,402 normalized input**, and **188,236 output**. This exactly matches retained Claude accounting.

The five unique Codex response IDs sum to **143,852 input / 5,009 output**, matching native turn.completed. Cached input 105,856 and reasoning output 3,532 are already included in those totals. Adding owner and peer gives exactly **10,593,254 / 193,245**. No cumulative terminal total is added twice, no cost is dropped, and no additional missing call is invented. COMPLETE describes emitted native accounting, not independent provider billing.

Unlike the earlier smoke, this run actually contains **two consistent owner startup init records**, LF **1 and 1,562**. All fields match except uuid, including session, model, tools, plugins, skills, and MCP servers. The second follows background-peer completion; the final accounting includes the continuation. This is actual evidence that consistent repeated initialization passed the repaired path. Owner stdout (1,995 LF records), peer capture (25), and Codex rollout (60) contain **no literal U+2028, U+2029, or NEL**. Unicode boundary handling remains fixture-backed; it was not exercised here.

## Local delivery and integrity

Recorded source/public/delivery gates pass. Local commit **42a1ae50f1d543b4018aedd821cce8a63c1f8d6e**, parent **8414826b8cba4ae2264eb2220bb776815bd6bc3e**, modifies only **bin/cli.js and tests/cli.test.js**. The receipt under `.git/devlyn-completion/7c4d6cc244fee449f7ebacb0` binds the public check, matching source/publish commit, LOCAL_ONLY status, writers released, recovery ref, and CLEAN scratch removal. Owner output at 1,930 records main reconciliation and temporary worktree/branch removal. Read-only git inspection independently confirms this commit, clean status, and only main's worktree/branch. Canonical peer records remain in ignored custody; no push is claimed.

All **1,015 protected raw, registration, and freeze hashes** match before/after. Only this audit's Markdown and JSON were written. No native/model/authentication call, evaluator replay, product edit, or test was performed by the auditor, and previous outcomes were not changed.
