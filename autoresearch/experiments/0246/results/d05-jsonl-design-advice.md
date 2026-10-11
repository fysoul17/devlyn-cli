# 0246 d05: JSONL framing, startup evidence and custody advice

Independent bounded design advice from `/root/review_0242`, 2026-10-10 UTC. No implementation, tests, model/authentication calls or verdict replay. Only this report was written. This is not permission to regrade or dispatch another efficacy sequence.

## Two observed failures, not one

Preserve the exact d05 **STOP / COMPLETE** verdict: 2,138.6585267500195 owner seconds, 12,316,264 input / 196,529 output. Identity/peer policy are MATCH with activation true, but helper validation is incomplete. Source/public/oracle/delivery were not graded. Manual owner consumption and repairs do not manufacture the missing registered acceptance.

The emitted STOP reason is `ValueError: Claude startup catalog missing or ambiguous`. The Codex helper's separate NATIVE_FAILED is an additional observed defect, not that emitted reason. The owner stdout has two actual system/init rows and two success results for the same owner session; both init catalogs/model match on inspection. There is no literal U+2028 in that stdout. The startup reader at 0237/runner.py requires exactly one init, so this is not Unicode splitting of an owner init. Independent protocol audit must establish the provenance of the second init before choosing its prospective acceptance rule. A helper-only repair cannot be claimed to close this STOP.

Separately, the retained native Codex capture has 56 valid LF-delimited JSON records, one thread.started, one turn.completed, no error/turn.failed and a nonempty agent answer. Literal U+2028 appears inside record 45's command-output JSON string. str.splitlines() produces 57 pieces and breaks that valid string, causing the helper's recorded `Unterminated string` error despite native exit 0. Canonical attempt, capture and completion survive. This is a JSONL framing defect, not missing native usage or failed native reasoning.

## Minimum prospective parser and startup repairs

For the helper, split native JSONL on its actual LF delimiter (or iterate physical file lines), not Python's broader Unicode text-line boundaries. Preserve exact stream bytes, existing completion/error requirements and strict JSON decoding; do not escape/sanitize model output, concatenate arbitrary malformed fragments, ignore bad rows to reach success, or select only a favorable final event. This is a small standards-consistent boundary correction.

Check the actual same-stream consumers, not every splitlines call in the repository. The bound 0234 evidence.lines reader also uses splitlines and skips undecodable pieces; on this capture it can discard the affected command event even though the terminal usage/session rows survive. That warrants prospective LF framing at the relevant shared inventory binding too, while retaining its existing validation/gap semantics. 0244 discovery's inline-JSONL path and the owner's separate base cell reader are other concrete native-stream boundaries to inspect. Do not edit frozen historical modules or turn this into a generic parsing framework; use a new bound adapter/copy as appropriate. The 0232 trace reader handles a different JSONL stream: do not assume the present capture proves it failed or add unrelated churn.

For startup catalogs, the invariant should concern observed identity/catalog consistency, not a guessed number of notifications. If the independent audit confirms legitimate same-owner continuation within the retained native execution, the smallest prospective rule can require at least one well-formed init, validate every init's owner/session/model and normalized explicit skills/plugins/MCP catalog against the frozen expectation, and reject missing fields, conflicting identities/catalogs or unexplained origins. Do not blindly take the first row, deduplicate without validation or permit arbitrary extra sessions. Old d05 remains STOP under its original exactly-one gate. This conditional recommendation awaits the separate provenance audit; it is not retrospective acceptance.

Targeted regressions should bind the exact retained Unicode record, successful final answers with U+2028/U+2029 (and another valid non-LF Unicode separator), normal LF/CRLF input, genuine malformed JSON, failed/error events and missing/duplicate terminal success. Verify the inventory preserves the command event rather than dropping it. For startup, cover the audited repeated-init shape plus absent, malformed, conflicting-catalog and wrong-session contrasts. Existing absent/unknown usage must still STOP. These fixtures close the observed contracts without broad suites or model calls.

A newly registered focused Claude-owner/Codex-peer operational cell is the relevant changed native route. Freeze exact parser/startup inputs first; require complete costs, canonical custody, answer consumption, identity/source/delivery and independent audits. If a stochastic run does not emit U+2028 or repeated init, it does not by itself prove those fixes; the exact regressions remain required. Do not rerun the old efficacy row as a test or obtain its withheld grades.

## Repository-local custody: now earned, but a distinct treatment change

Repeated d02 P and d04 H owners explicitly skipped the helper because its mandatory .devlyn/pair writes exceed their strict reading of the repository allowlist. This is now a repeated observed compatibility limitation, not a speculative concern. Both rows remain valid PRODUCT_INCOMPLETE observations with complete costs and nonactivation. Git-ignore is not permission, and changing the caller to force activation is not the root fix.

A future unshipped product candidate may now justifiably combine the parser repair with one fixed helper-owned application-state root under home, outside the reviewed checkout. Keep exclusive per-call directories and canonical returned paths; the existing attempt.repo and source snapshot already supply repository attribution. There is no need for --out, exports, fallback stores, per-repository configuration or a new storage service. The repository check-ignore requirement becomes irrelevant to that external store and should be removed rather than bypassed. Refuse an unusable/escaped root before native dispatch; never silently fall back into checkout or temporary caller custody. The existing lifetime guarantee must hold for failure, timeout, resume and source-worktree cleanup. A literal prohibition on all auxiliary filesystem state still cannot be overridden by choosing home.

Home collection is supported by actual code: evidence.WRITABLE is cell/tmp/home; 0242 policy.receipts scans attempt.json under all three; 0244 discovery takes expected Claude capture paths from those same receipt roots. Native Codex sessions are already read from retained home. Thus relocation does not inherently require a new collector namespace. Still prove both-engine receipts, source attribution, duplicate-free accounting and retained home custody with a focused fixture; do not merely assert compatibility from the directory name. The native smoke must use the actual fixed home root, not a caller-selected substitute.

## Continuation versus outcome-seeking rerolls

For completing the existing scientific question, prefer separating a machinery-only continuation from an activation redesign. A parser/startup-only continuation can retain valid earlier H/P nonactivation outcomes when the changed parser was never exercised and all relevant inputs remain unchanged. It resumes the unmeasured frontier with a new registration and identities; it does not buy another chance for d02/d04.

Moving custody changes what an owner is willing/able to activate. It is therefore a new H/P treatment, even if it is a small product patch. Do not rerun only the negative H/P rows under that version and call them replacements. If root chooses this combined candidate, register the new question/version and all included observations prospectively, preserve the old H/P outcomes and costs separately, and explicitly state the adaptive exposure. Valid A/B/S observations may be reused once only where selected package, task, runtime, gates and relevant evaluator behavior are identical or demonstrated execution-irrelevant. Currently completed A and S observations exist; B cannot be “reused” before it has run. Earlier H/P nonactivation rows are not observations of the new activation affordance.

The current machinery halt leaves the planned comparison incomplete; it is neither a demonstrated positive signal nor automatically a completed no-signal comparison. But it cannot erase existing negatives or license endless candidate revisions. Apply the registered decision rule once its required comparable evidence exists. A completed no-signal decision closes this mechanism; label changes, custody relocation or cherry-picked retakes must not evade it. Product compatibility work can still be assessed on its own correctness merits without pretending it has earned efficacy admission. Whole old/new/operational expenditure remains included, with prior unknown residuals explicit. Fresh harder confirmation remains mandatory after any diagnostic signal.

These boundaries follow No workaround (actual framing and lifetime contracts), No guesswork (distinct emitted STOP and helper error), No overengineering (one store, existing schema/collector), and Production ready (explicit failure and complete retained cost).

## Bound observations

- Native peer capture: f8c6946fff7c62d823fd21ea3aaacdf4c6d0f7b9378169f1fd9b9b51d1472332
- Peer attempt.json: b6f35472e9c8b300ce987d8a9dbd6b02a8179a4d250750417472f74ed9d8a0f0
- Peer completion.json: f737c4830547fd8682882143b62e4341b04d019c80064302c2598605e95c0204
- Owner run/stdout: 61973d08bf4c4557aa42f59a54be9957e8735b34103b727b73d5e9f17bc22a05
- d05 verdict: d7f1de56e6d2f0d7ead917788099c1586848a6ea80506e75256e4318a5ba1c6e
- 0246 registration: dd489ac8b05e973dacf413852664f814bde2da8e731ab3d6f8db2565e215f853
