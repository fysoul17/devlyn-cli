# 0243 d02 custody failure: bounded design advice

Independent opinion from `/root/review_0242`, 2026-10-10 UTC. This is diagnosis and prospective design advice, not implementation approval, a new registration, a replacement verdict, or dispatch authority. No models, authentication, tests or replays were run. Only this file was written.

## Observed failure and responsible contract

The before-end observation correctly predicted the loss. Its event and command hashes match stdout line 40. The owner calls the exact helper inside TemporaryDirectory with --out=/tmp/bench-cli-peer-…/review. Line 50 returns EXITED/0, source_unchanged:true, a receipt path in that directory and a substantive peer answer. The context then deletes that directory. The helper writes its only attempt.json, completion.json, native capture, stderr and finalanswer.txt under the caller's --out; external directories are expressly supported by its code.

The original verdict remains STOP/PARTIAL. Claude session 905d504d-30ca-4d3f-97f6-ac4f1f6bac6e is visible, but there is no retained terminal aggregate or typed receipt binding. Accounting is UNKNOWN and policy UNVERIFIED, with input/output totals null and retained lower bounds 1,796,844 / 69,638. Owner time is 807.6238686249999 seconds. The printed successful receipt and answer do not reconstruct the missing aggregate or establish retained custody. Do not turn this into verified non-activation, an efficacy success, or a complete cost.

This is both an owner adherence failure and a helper API lifetime flaw. The owner read a guide requiring ignored .devlyn/pair records and retention of the native capture, then violated that instruction. However, the helper accepts a normal disposable output directory and treats it as the sole repository of execution records. It checks source isolation, not record lifetime. Repeating the prose or blaming the collector leaves that mismatch intact. The collector is correctly refusing incomplete evidence. The candidate helper's retention contract is the smallest product-level boundary at which to fix it; this does not establish a defect in the already shipped solo baseline.

## Recommended minimum change

Give the helper one canonical, helper-owned record directory per invocation in the repository's ignored .devlyn/pair subtree. Allocate it exclusively before dispatch. Write attempt, native stdout/stderr, completion and canonical final answer there directly. A copy after success is insufficient: timeout, failure and interruption costs need the same custody. Keep the current receipt schema and native argv/accounting semantics; returned receipt and final-answer paths should identify canonical retained records.

If --out remains supported, make it a disposable answer/export destination, not the authority for records. For compatibility with this observed caller, an answer copy at --out/finalanswer.txt (and diagnostic stderr where needed) can preserve its existing consumption path. Do not mirror typed receipts and native captures into two competing authoritative inventories. Persist completion before export; an export failure must be explicit without discarding the already recorded native attempt or claiming no call ran. An optional --out is sufficient; no second custody flag, registry, service or configurable backend is needed.

Use existing Git/source checks and standard exclusive directory creation. Verify the resolved custody directory stays in the intended repository subtree and is actually ignored; refuse before launching if it cannot be established. Do not edit Git configuration/ignore rules automatically or silently fall back to /tmp. This is protection against ordinary caller output cleanup, not a claim that a same-permission owner cannot deliberately delete records. The existing delivery path already retains repository .devlyn records when removing owned worktrees; keep that lifecycle rather than inventing another store.

A stricter alternative is to restrict --out itself to the durable ignored .devlyn/pair subtree and reject outside paths before any native call. That is a valid, smaller API if external outputs are intentionally unsupported; it closes the loss by refusal. I prefer separating canonical custody from optional answer output because the observed caller's temporary output pattern then remains usable without requiring a second corrective owner turn. Merely adding a default directory does not close explicit temporary --out. A /tmp blacklist is neither portable nor a lifetime guarantee.

A short guide change should describe retained helper records versus disposable exports and use the returned paths. Do not add more review rounds, stronger activation instructions, model changes or receipt reconstruction to this repair. These choices follow **No workaround**, **No overengineering**, **Best practice** and **Production ready**.

## Bounded prospective validation

Before implementation/testing, register the falsifiable prediction: the same temporary-output call pattern may delete its export directory, but the helper's single native receipt/capture set remains intact and the unchanged collector reconciles it; genuine missing or invalid native usage still stops.

Use targeted fake-native functional cases to cover deletion of the exact TemporaryDirectory output pattern, successful Claude/Codex captures, a failed/timed-out attempt with retained streams, distinct fresh/resumed invocation records, and custody creation/refusal before dispatch. Check unchanged source identity and that collectors see one authoritative call rather than duplicated usage. Exercise the failure branches the patch actually changes; no new general parser or large framework is warranted.

Then one separately registered native operational cell on the observed Codex-owner/Claude-peer route can validate the changed persistence path, including caller output cleanup and whole-run reconciliation. Reuse unchanged transport evidence only where still applicable. A full ten-cell efficacy rerun is not a substitute for this focused operational check. No classifier weakening, acceptance of answer text as accounting, or salvage of the original d02 is needed.

## Prospective continuation and d01 reuse

Reusing the unchanged d01 Claude/S observation is defensible in a newly registered continuation. It does not invoke the changed peer helper. Its source package, guide, task/oracles, actual runtime/model configuration, evaluator and accounting inputs must remain byte-identical or be shown execution-irrelevant, with its original outcome and costs carried forward regardless of favorability. The retained verdict is CHECKS_PASS/COMPLETE; this advice does not independently re-audit its protocol or quality outcome.

The new registration must explicitly supersede the stopped sequence prospectively, identify the revised H/P package versions, name d01 as historical reused evidence rather than a new replicate, and fix the remaining order and decision rules before another efficacy result. If the patch changes S/common owner instructions or an evaluator input relevant to d01, that reuse claim fails and the affected cell needs a new prospective observation. Do not rerun d01 merely because its outcome is inconvenient, or count it twice.

A new d02 under a changed helper is a new attempt, not a repaired old row. Retain the original STOP, unknown residual and all known costs separately and in the study's total expenditure; do not hide them in a best-of-two comparison. Preserve the other nine planned cells/order as applicable, with exactly one retained d01 observation. The original d02 peer finding has now exposed further task behavior, so the continuation remains an adaptive diagnostic screen, not fresh confirmation or clean evidence for the original helper version. A positive signal still requires the previously registered harder, fresh confirmation path. No favorable reroll or adoption is licensed by this advice.

## Source bindings

- Before-end observation: 4f9e44a277a5f68273198309613b1f35239054c710fdcb4de3f809a11e2484d2
- d02 run/stdout: 7e835bb76e0beed2a0e599be11802b25dc3a576fd314484f2941961a7b6491d6
- d02 verdict: 5dae1c69e1c90024962e08aacc7524598b7e2f4944b9429b370725ad6456f51b
- d01 verdict: dc50789bcb12813d57e53ea14cd66203b938a6e1d91d40804b598347f5c1db89
- 0242/peer.py: f3f4c878847e6d33149cb9d6ebfe6a78dd12eba82d5ce417fdef79ee6af28d95
- 0242/guides/P.md: 9523319d650db1d5176261cb00d254e6216915b86d9d222bfacc85cefa23993a
- 0243/registration-v1.md: 1559e729fef2f252174b8d2e921a2c8b1bff6d103f7626670c8ff6f9f6c9c988
