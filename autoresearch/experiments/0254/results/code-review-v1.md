# 0254 bounded code review v1

**REVISE — three HIGH findings and one MEDIUM.** Reviewed `audit.py` SHA256 `5bc5d6124cbed94b3c59019edd2783185fe57b4c0d743873457ad23459be130f` and the independent tests at `a2fdfa1c3b7d6dd0c41915479beb209e98b73cedb8888c72f0289d8eb4e6fef0`.

Root's first targeted run has 30 methods and 12 failed subcases. The unchanged real0253 positive control correctly matches three receipts, 49,313 input and468 output. That establishes compatibility only and cannot waive a negative-path failure.

A prospective reviewer prediction preceded seven isolated synthetic probes; the healthy fixture passed, while the seal-inventory, stdout-identity, symlink and unsupported-stop counterexamples incorrectly returned MATCH. Aggregate disagreement returned UNKNOWN but discarded validated observations. Raw probe metadata is preserved in `code-review-v1-probes.json`; fixtures were disposable, and no original capture was opened or changed by reviewer.

## H1 — HIGH: The complete-attempt census can forget sealed evidence that is now missing

`autoresearch/experiments/0254/audit.py:188`. The auditor compares actual BODY directory names only with index names. It never compares the relevant sealed-manifest inventory with the actual files. A synthetic unindexed request present in the supplied frozen seal, then deleted after sealing, returns MATCH. Thus a vanished unfinished attempt can disappear from accounting while the seal itself still proves it existed. The path check also follows a symlinked BODY ancestor inside the output root; that violated regular-custody expectation returns MATCH.

Compare the sealed versus actual relevant request/response/index/transcript/child-metadata inventories before reconciliation, and reject any missing/extra source or symlink component. Keep scope to relevant native captures, not unrelated harness files. Add focused regressions for a sealed orphan removed after seal and a symlinked carrier directory.

## H2 — HIGH: Conflicting native capture and child-result evidence is silently ignored

`autoresearch/experiments/0254/audit.py:232`. Stdout assistant validation ignores request_id and UUID, so changing either to a conflicting identity still returns MATCH. Child lifecycle events are not checked against the owner session. The child tool result usage and totalTokens are also ignored, so conflicting completed child counters pass. These conflicts must not be hidden by agreeing transcript/body aggregates. The current synthetic fixture omits stdout request_id although the actual0253 schema contains it, masking that requirement.

Validate each observed stdout assistant request/UUID against the exact anchored inference (and child parent-tool mapping where applicable), bind lifecycle/tool-result sessions to the owner, and reconcile child toolUseResult usage/totalTokens with that child receipt subset. Add the actual request_id field to the synthetic stdout shape rather than permitting missing/conflicting identity.

## H3 — HIGH: The initial successful-path contract accepts interruption and unobserved stop semantics

`autoresearch/experiments/0254/audit.py:167`. The existing suite shows the retained-native-shaped user interruption marker is ignored and MATCH remains possible despite a cancellation contradiction. STOPS additionally accepts pause_turn and other unobserved semantics, even though R0 froze only the observed successful terminal schema; a synthetic matching pause_turn child/body returns MATCH. The root is verifying the exact native interruption-marker shape before repair; the historical diagnosis already identifies that marker.

Recognize/reject the actual native interruption/cancellation marker and keep accepted stop semantics to the explicitly supported observed schema. Reject unsupported error/retry/cancel shapes as UNKNOWN without claiming new native recovery behavior. Synthetic stream_retry/type-api_error mutations are not proof native emits those shapes; document their unsupported-shape purpose or revise them against actual evidence.

## M1 — MEDIUM: UNKNOWN erases already verified receipt and aggregate metadata from the report

`autoresearch/experiments/0254/audit.py:83`. On a final aggregate disagreement, all three terminal receipts have been validated, yet the exception boundary returns messages=[] and no retained receipt counters or reported aggregate. Whole totals correctly remain null, but the agreed contract also requires known observations to remain separately visible.

Retain safe already-validated receipt metadata and valid reported aggregate in separately labelled observation fields while whole totals and residual stay UNKNOWN/null. Do not call the observations a proven lower bound, choose a winner, or subtract the discrepancy.

The structural approach is appropriate: a standalone module, explicit native-body numeric source, exact transcript anchors, every-terminal-copy checks, and separate owner/all-session aggregates. The requested fixes close observed invariant violations using the existing schema, not a new framework (**No workaround**, **No guesswork**, **No overengineering**, **Production ready**).

HEAD `186bbd84e004dd1ff458fb714b2872d9c7ef47bc`. Reviewed diff SHA256 `2c3d110fbfad5ebf853ec82138e2150492424f4ce49cfd18d2e7fd9296a73324` (40155 bytes), generated by concatenating sorted `git diff --no-index --binary /dev/null <relative path>` outputs because both new files are untracked. Source hashes are the definitive review binding.

No native/provider call, credential read, old capture mutation, product grading or tracked edit occurred. Preserve v1 and perform one bounded repair review after targeted checks pass.
