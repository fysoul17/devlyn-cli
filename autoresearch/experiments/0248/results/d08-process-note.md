# 0248 d08 Codex/A process note

Bounded read-only inspection of `0248-live/out-measured/d08-f23-codex-a`. Original outcome preserved: **PRODUCT_INCOMPLETE / COMPLETE**, **223,364 input / 15,996 output tokens over 306.79681274999166 seconds**, public **64 PASS**, local delivery PASS, cleanup CLEAN. Priority rollback and single-warehouse FEFO pass; the two precision rows fail. No model/authentication/native call, new test, source edit, or oracle replay/regrade was performed.

The actual owner is **gpt-6-astra/max**, session `01a127e5-e621-7d72-9978-c95a471b07e9`, confirmed by native rollout turn context LF 8. There is one owner session/trace, no launched child session, and no peer activation/turn. Native multi-agent v2 capability exists but was unused. The A checkout contains no AGENTS.md, CLAUDE.md, .agents, .claude, or .devlyn; the owner's initial instruction-file search also returned no guide files.

**The implementation explains both retained failures.** At bin/cli.js:64, submittedTime accepts arbitrarily many fractional-second digits. At line 66 it reduces the timestamp to Date.parse's milliseconds. The sort at lines 116–117 compares that value and then ID. Accepted input therefore retains more precision than its sorting key.

The frozen evaluator's retained actual outputs show the consequence:

| Case | Expected accepted IDs | Actual accepted IDs |
| --- | --- | --- |
| .0002Z a-later versus .0001Z z-earlier, stock 1 | z-earlier | a-later |
| Add equivalent .000100+01:00 b-equivalent, stock 2 | b-equivalent, z-earlier | a-later, b-equivalent |

Both CLI invocations exit 0 with empty stderr but reject the wrong order. The raw precision result binds inspected source SHA `e1ea40fcde493072791b6b87d27886feb4d36efde9fb5681195e8d13109bb960`. The root cause is discarded submillisecond precision causing an ID tie, not a demonstrated absence of offset normalization. In the second case, the later .0002 instant incorrectly joins the earlier/equivalent instants at the same millisecond. No remaining-row interpretation is required to explain these recorded failures.

**Public coverage has a specific gap.** The 64 count comprises **11 top-level tests plus 53 nested cases**. Its ordering test at tests/cli.test.js:113–125 explicitly checks offset equivalence at whole-second precision: `00:00Z` and `01:00+01:00` tie and IDs decide. It also checks priority and different days. The general valid-wave fixture at line 70 uses `.123Z`, exactly millisecond precision, with one order. There is no ordering case contrasting nonzero submillisecond instants. Thus the suite genuinely checks ordinary offset normalization while leaving the finer distinction untested.

**Actual process.** Owner stdout LF 17 records baseline `node --test tests/cli.test.js`: 3 passed. After source/test edits, diff checks complete at LF 25 and the public command passes all 64 at LF 27. The owner stages only the two allowed files and commits at LF 30, then checks status, commit and file scope at LF 32. These are real verification/delivery steps, but there is no separate retained precision probe or competing submillisecond test. The owner's final “nothing unresolved” exceeds the subsequent frozen evaluation's support.

The local commit is **c742af95fccb1eff31962318d1744d2bdc6b4077**, baseline **3259569dc74f4d6a08ff9eaf84f507912da89b76**, changing only bin/cli.js and tests/cli.test.js. Delivery PASS and CLEAN remain unchanged. This note makes no claim that a guide, peer, or different model would have prevented the failure, and no general performance comparison.

**Integrity.** All **114 protected files** match before/after: source, raw verdict/results, native owner logs/trace/rollout, effective registration-v2 and freeze-measured-v2. Key unchanged hashes follow.

| File | SHA-256 |
| --- | --- |
| verdict-d08-f23-codex-a.json | `ba62d47cffe12936f0689b77b6ae5c7aa5135665baf220a1c7984f71656d66f4` |
| checks-raw.json | `68c0cc99e8ce2ed524488c4af9dea3e8963b6483919bb074ea600a9d38579be0` |
| run/stdout | `f91a62a4b1732880f65f4629eed94a528e0bf692d389fca9eb21576aa596e6c1` |
| bin/cli.js | `e1ea40fcde493072791b6b87d27886feb4d36efde9fb5681195e8d13109bb960` |
| tests/cli.test.js | `2e57f77eb318775186fb2992bf1d5910a6c295a41c0decf17ee3bf2493ae88a8` |
| registration-v2.md | `866b4384dd32f891b8539ba93a6dd645e2010d85d2fa02966d3203e1fb27e91f` |
| freeze-measured-v2.json | `16b49370e62922eed63aa3396102f89cfb258c7cc001503a407d6bf6045e00d3` |

Sorted compact JSON path→hash inventory SHA-256: `8ee383f34b76ff5fe67a457eee88d42825f986a3dbd99386a5d605d0e4efcf6d`. Only this note was written.
