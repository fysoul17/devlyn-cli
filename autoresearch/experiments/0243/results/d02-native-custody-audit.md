# 0243 d02 native custody audit

**Confirmed custody failure. Preserve the emitted STOP/PARTIAL.** The native owner exited 0, but the runner stopped because a real Claude peer lost the records needed to bind and account for its execution. This report does not regrade source, delivery, hidden requirements, or prior cells.

Raw cell: `/Users/aipalm/.local/share/nx01/0243-live/staged-v1/out-measured/d02-f23-codex-p`. The original verdict remains `ValueError: peer model identity/evidence UNVERIFIED`, source assessment and delivery both null. Owner duration is **807.623868625 seconds**. Recorded usage is only a lower bound: **1,796,844 input / 69,638 output**, with an unknown residual.

## Exact failure and why collection must remain strict

At `run/stdout:40`, the owner launches the installed `peer.py` inside `with tempfile.TemporaryDirectory(prefix='bench-cli-peer-') as scratch`, using `--out scratch/review`. It prints the helper's summary receipt and complete final answer, then raises `SystemExit(result.returncode)` inside the context. Normal context unwinding removes `/tmp/bench-cli-peer-32dnx1a1/review`, including the attempt, completion, untouched native result, stderr, and source snapshots. It never retains those artifacts elsewhere.

The exact command SHA-256 is `63d2d04d01cfb2903716b96b050a5b7bf8cf08612cab3672ad27cf2e35ce61cc`; the exact event line hash is `fed09f462a414c81d7c4c8d7f0d59439bd3a3192d274d808387073d6db089143`. Both match the parent's observation recorded at 18:10:58.925404 UTC, before completion. That was a reactive custody prediction, not an efficacy preregistration.

The evidence agrees at every boundary: line 46 observes a live attempt and incomplete capture; line 50 prints an EXITED/0 receipt with `source_unchanged:true`; the final evidence contains no attempt/completion/finalanswer/native peer-result files or matching temporary directory. The native transcript survives outside that temporary directory.

The violated invariant is **evidence lifetime**: invocation, source snapshots, and native terminal accounting must outlive the call until collection. The installed `pair.md` already says to keep request and raw answer in ignored `.devlyn/pair/`. The helper supports external output directories and only validates Git ignore status for paths inside the checkout (`peer.py:110–129`); it cannot preserve a directory the caller immediately deletes. This is a producer/caller retention failure, not the 0242 metadata-discovery false positive. A prospective fix must establish durable retained custody at this boundary. Counting a printed answer as a native result, accepting an unbound session, or weakening missing-result accounting would conceal the failure.

## What the surviving native evidence supports

The owner is native Codex `gpt-6-astra` / `max`, session `01a126f9-5b03-7281-a68e-0d53fc02516c`. The peer is one fresh native Claude session `905d504d-30ca-4d3f-97f6-ac4f1f6bac6e`; all 14 assistant rows record `claude-opus-5-5`, effort and per-turn effort `max`, and non-sidechain status. Its eight observed tool calls are four Read, three Glob, and one Grep. No peer shell, mutation, test execution, child, second session, or resume is observed. The installed helper configures Read/Grep/Glob and an empty strict MCP configuration. The deleted native result prevents a separate retained full-catalog assertion.

The actual native prompt at transcript line 3 has 25,412 characters, SHA-256 `e046b114165b9c3f0b1435ae15da089e57240588dcf656fb9e4b36ba382e5e62`. It contains the exact original caller JSON once at offset 687, before the candidate diff at 4,948, check results at 24,587, and review request at 24,864. Decoding that embedded JSON reproduces the original caller contract exactly. The check material is an accurately labeled 50-test TAP summary excerpt, not the full TAP output. No owner theory of the eventual timestamp finding was inserted ahead of the request.

The complete 4,424-character peer answer survives at Claude transcript line 47 and owner stdout line 50; its SHA-256 is `d6ec266361da41c787d4a44228ac91c652d050ad53acf54e386c45301ff5c8c9`. The owner's native tool result at rollout line 253 contains it without truncation, before the repair and final response. The peer reports one timestamp-precision violation and labels timezone/whitespace notes as weaker observations. Those observations are not new requirements or hidden-oracle findings.

Automatic invocation is directly observable: the owner reads the managed Worldclass/pair instructions, announces a review of ordering and rollback, and launches the other primary engine without a user pair command. However, `peer-policy.json` correctly remains `activated:false`, `NOT_ACTIVATED`, and `UNVERIFIED` because the required binding is unavailable. Observed invocation is not a valid measured P outcome.

## Finding order, stable review, and owner checks

| Event | Evidence |
|---|---|
| Pre-peer public checks: 50 pass | stdout 36 |
| Helper launch | owner rollout 107, 18:06:07.053 UTC |
| Owner independently predicts sub-millisecond collapse | rollout 124, 18:06:58.946 UTC |
| Owner executes witness: expected `z-earlier`, actual `a-later` | stdout 43 / rollout 128, 18:07:05.034 UTC |
| Peer completes answer about the same defect | Claude transcript 47, 18:11:50.334 UTC |
| Owner consumes full answer | rollout 253, 18:12:09.265 UTC |
| Added regression fails on the reviewed source | stdout 55 |
| Owner repairs fractional precision | stdout 56–57 |
| Peer-equivalent two-order check passes: accepted `b`, rejected `a` | stdout 59–60 |
| Public check: 51 pass, zero failures | stdout 63–64 |
| Local commit, then final response | stdout 67–68 |

The owner's independent prediction and execution precede the peer answer. **No novel peer-discovery or marginal efficacy credit is justified.** The owner later runs the peer's same two timestamps/input ordering with an equivalent assertion and temporary-file cleanup; it is not claimed to be a byte-for-byte shell replay.

No source edits appear between peer launch and completed answer; the owner explicitly delays repair and the helper reports unchanged source. The first subsequent edits add the failing regression and then repair the source. Because the source snapshots were deleted, this is an observed event sequence plus helper claim, not independently recoverable per-file before/after equality.

## Local outcome and accounting limits

Existing execution records show a final public check of 51 tests, all passing (902.290376 ms), and a successful `git diff --check`. Read-only Git inspection confirms local commit `50e604d155cfc4d987bca131d1a1254768456e44`, parent `ee954cc8a66a71a510afdfe989095ff39d4b911d`, with exactly `bin/cli.js` and `tests/cli.test.js` changed. The checkout is clean on main with one worktree. The recorded container and temporary volume are absent; raw teardown is CLEAN. These are observations only: the stopped runner's source/delivery fields remain null. No tests or semantic oracles were replayed.

Claude's five terminal-message usage records provide only 10 input + 55,850 cache creation + 120,503 cache read, and 37,824 output. The untouched native aggregate is absent. The owner contributes 1,620,481 input / 31,814 output. All observed cost remains charged; thinking is already within output. Neither the printed answer nor transcript reconstruction closes the native aggregate or session-binding gaps.

Prior d01 remains CHECKS_PASS/COMPLETE. The remaining eight cells remain NOT_RUN. No prior 0242 STOP is changed. No comparison, overall efficacy, or efficiency conclusion follows from this stopped cell.

The companion JSON records all protected source hashes and the final before/after comparison. This audit writes only these two reports, runs no models or tests, and leaves raw evidence, frozen inputs, and product source unchanged.

