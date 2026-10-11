# 0248 d07 native protocol and novelty audit

Prospective read-only audit prediction, 2026-10-10T22:14:50.151322+00:00: the retained evidence should bind a separate read-only Claude Opus/max peer, stable review source, complete answer consumption and exact whole accounting. Submillisecond novelty must be supported by pre-peer probes/source/tests and the executed post-answer witness, not by final narrative alone. Existing oracle outcomes will be preserved; no replay is planned.

## Result and scope

**PASS for native protocol, custody, accounting, and the evidence chronology below.** The original measured-cell outcome remains **CHECKS_PASS / COMPLETE**, public 8 PASS, all four frozen oracles PASS, source/delivery PASS, identity/accounting/peer policy MATCH, and cleanup CLEAN. Recorded whole cost is **8,690,338 input / 206,662 output tokens over 1650.809419874975 seconds**. Verdict SHA-256: `7d735bf545596ba71eaead04450db3437fc2265e9e316a087a6e5889c58c035c`.

Effective inputs are 0248 registration-v2.md and freeze-measured-v2.json, bound in the JSON companion. No model/native/authentication call, new test, evaluator replay, source edit, or oracle regrade was performed.

## Actual independent session and read-only capability

The owner is **Claude Opus 5.5 / max**, session `a2d06a1d-6c64-4501-ba63-d9195e68e9a9`. The fresh peer is a different native Claude session, **`569709e8-8a1e-40ab-96b5-a6395fccaf07`**, also **claude-opus-5-5 / max**. Both transcripts' effort and per-turn effort fields are max; native model identity and modelUsage agree. There was one peer invocation and no resume.

The peer argv requests permission mode dontAsk, tools Read/Grep/Glob, strict empty MCP configuration, JSON output, and its explicit fresh session ID. Its **actual retained prompt snapshot at peer transcript LF 24** lists only **Glob, Grep, Read**, whereas the owner's retained catalog includes mutation/execution/delegation capabilities. Actual peer actions are five Read, two Glob, and one Grep. Native peer subagent statistics show zero spawned, and there are no peer descendants or additional model sessions. This capability conclusion is supported by the native catalog and observed calls, not argv alone.

The peer completed EXITED/0 with no error in **407.5358268079872 seconds**, inside its 540-second watchdog. The before/after source snapshots are equal over **680 entries**, baseline HEAD `7e398fc2fa5dddec0ef6e2db16497eb2eb48687a`. Source stability applies to the peer review interval; the owner subsequently changed source and tests after reading its answer.

The exact 24,778-character peer prompt appears as the peer's initial user message at transcript LF 3. The original caller.json **request value** is verbatim once at character 31, before candidate diff at 4,021 and raw public checks at 22,819. It has no separate owner-interpretation section. Its SHA is `07601aa03f9f191291e103246eb7de2b210bc26b46c3af41d1e48d06f0c00913`. The fresh session receives the request, candidate source/diff, and check results, rather than the owner's preceding conversation.

## Answer consumption and custody

The canonical `cell/work/.devlyn/pair/peer-y2sgha_n` directory retains exactly five files: attempt.json, completion.json, native result JSON, stderr, and finalanswer.txt. The latter is **4,309 bytes**, SHA `a38ee0f9138855d783360f05ebd6f134ddc4b4128c9ab56522a829816960b2ec`; it matches the complete native result text. The owner reads the whole answer at stdout **LF 995**, before reproducing the finding and before final response LF 1,513. The JSON companion preserves all five exact custody hashes.

The peer expressly states it could not execute its proposed checks because it had only reading/search tools. Its answer is a source-derived prediction. The subsequent owner executions are the empirical confirmation; they must not be attributed to the peer itself.

## Novelty, with the earlier owner observations retained

This is a real observed review-assisted repair, with a narrower novelty claim than the owner's final narrative might suggest.

| Owner stdout LF lines | Evidence |
| --- | --- |
| 273 / 274, before peer | Owner already probes Date.parse on .123456Z and sees .123Z. Fractional truncation is therefore not first discovered by the peer. |
| 741 / 742, before peer | A one-order .123456+05:30 input is accepted. It cannot expose ordering against a competing order. |
| 683 / 684 and 791 / 792 | Public tests pass 8. The original ordering test covers whole-second offsets and equivalent whole-second times resolved by ID, with no competing nonzero submillisecond instants. |
| 794 | Fresh peer launch. Candidate still converts submitted_at to milliseconds and sorts that numeric value before ID. |
| 995 | Owner consumes the full answer proposing a=.000002Z versus b=.000001Z with only one stock unit. |
| 1,020 / 1,021 | Owner executes that exact wave: a is accepted, b rejected, exit 0. A separate Date.parse equality check prints true; fraction probes print [123, 999]. |
| 1,188–1,204 | Owner preserves fractional digits beyond milliseconds, compares them before ID, and strengthens the existing ordering regression with .0000002/.0000001 orders. |
| 1,212 / 1,213 | Same peer wave now accepts b and rejects a, exit 0; public tests still pass 8. Removing the new submillisecond comparison makes test 7 fail (pass 7/fail 1). |

The source-backed invariant is concrete: validation accepted fractional digits that the old sorting key silently discarded. The new sort key is epoch milliseconds plus the finer fractional digits as text with trailing zeroes removed; comparison considers both before ID. The owner preserved accepted precision rather than adopting the peer's alternative suggestion to reject fractions beyond three digits.

No pre-answer owner execution in the retained record presents the peer's competing submillisecond stock-allocation witness. The peer's contribution is the **new concrete counterexample and its consequence for the stated processing order**, connecting a primitive limitation the owner had already observed to an untested failure. The pre/post executions and targeted mutation substantiate that local repair. They do not establish a general advantage for this model or harness, nor what the owner would eventually have found without review.

## Other findings and verification limits

The peer separately labels a leading-dash file path a **weaker, debatable** issue: `--input -wave.json` is refused while `./-wave.json` works, matching the existing --name convention. It was a static observation; no owner command reproducing this path case was found. The owner retained that choice. It is not another demonstrated/fixed bug.

The safe-integer cap, unique warehouse IDs, unique sku+lot pairs, mandatory boolean single_warehouse, zero-quantity rows in remaining, and UTC for offsetless timestamps are observed candidate choices. Several were already exercised before review. This audit does not expand the contract or turn the peer's “not counted” observations into additional defects or correctness proofs. The final blanket “nothing unresolved” and broad statement about large JSON integers are owner statements, not additional evaluator findings.

Five pre-peer mutations are actually caught at LF 717. A targeted removal of the new fraction comparison is caught at 1,213. The final eight mutation definitions all trigger failures at 1,366: **14 mutation-suite executions across these three batches**, including repetition. The public count stays at eight because the regression strengthens an existing test.

The retained edge probe has 25 CLI cases before the peer; post-fix timestamp probing has 12 validity cases and eight ordering/timezone cases at LF 1,241. The earlier edge corpus is also rerun. These support the reported approximate edge-case exercise, with overlapping and repeated inputs. They do not prove universal equivalence of accepted-input behavior. In particular, the final short summaries discard ordering details, so this audit relies on the earlier complete outputs and direct peer-witness replay rather than interpreting those shortened summaries as stronger evidence.

## Whole accounting and startup shapes

Independent message-ID deduplication gives **53 owner terminal assistant messages** and **five peer messages**. Owner usage is 108 input + 8,279,066 cache-read + 227,576 cache-creation = **8,506,750 normalized input**, with **161,376 output**. Peer usage is 10 + 115,672 + 67,906 = **183,588 normalized input**, with **45,286 output**.

Their sum is exactly **8,690,338 input / 206,662 output**, matching whole-run usage. Peer capture and transcript are two observations of the same call, not two charges. Owner terminal records at LF 981 and 1,514 carry disjoint usage increments, while the final modelUsage is cumulative; the aggregate is not added twice. Thinking/cache subtotals are already included. COMPLETE is native-emitted accounting, not an independent provider-billing audit.

The owner has **two init records**, LF **1 and 985**, identical except uuid, including model/session and catalogs. This actual continuation passes the consistent repeated-init handling. Owner stdout and the native peer JSON contain **zero literal U+2028, U+2029, or NEL**. The peer capture is one terminal JSON object; this run does not supply a new Unicode JSONL regression witness.

## Delivery and preservation

Local commit **bfe240bef00cb04a4c3ea402ab7bb4df3f40397e**, parent **7e398fc2fa5dddec0ef6e2db16497eb2eb48687a**, changes only bin/cli.js and tests/cli.test.js. The receipt binds matching source/publish commits, LOCAL_ONLY delivery, released writers, recovery ref `refs/devlyn/completed/7c4d6cc244fee449f7ebacb0`, and CLEAN scratch cleanup. The committed worktree public check passes 8 at LF 1,443; main passes 8 at 1,499. Source reconciliation and branch/worktree removal are recorded at 1,474, and scratch removal at 1,509.

Read-only git inspection independently confirms the commit/parent, two-file scope, clean main, and no remaining task worktree/branch. Peer custody remains retained. There was no second review of the repaired source, and no publication is claimed.

All **884 protected raw, source, registration, and freeze hashes** match before/after. Only this Markdown and its JSON companion were written; the prospective prediction is preserved verbatim.
