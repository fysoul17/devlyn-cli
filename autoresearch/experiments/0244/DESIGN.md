# 0244: distinguish terminal responses from owner summaries

Prospective repair, recorded 2026-10-10T16:51:41.625646+00:00.
0242 s03 is STOP/PARTIAL with its original raw verdict and known lower bound
1,325,063 input / 45,755 output tokens unchanged. No efficacy cell is authorized.

**No workaround / No guesswork:** 0241 discovery accepted any JSON object with
`type=result` and `session_id`, including owner-produced metadata. The s03 summary
has those two identifiers but no terminal payload or accounting fields. A summary
of an existing invocation is not evidence of another native result.

Keep declared carriers (typed receipts including custody copies, legacy dispatch,
observed literal redirects) unconditional and fail closed. Narrow only unbound
JSON and unrelated tool-output admission: require the existing result/session
shape plus presence of at least one terminal payload/accounting key: `modelUsage`,
`usage`, `result`, or `errors`. Test key presence, never validity or truthiness.
The existing accounting layer remains responsible for unknown counters. A real
terminal result with both usage fields removed still has result/errors and fails.

**No overengineering:** reuse the exact 0242 helper, policy, guides, packages,
tasks and runner behavior. Add a small runner adapter and a narrowly changed copy
of capture discovery; do not rewrite historical modules or regrade old cells.
No filename exemption, summary marker exemption, post-gap filtering, inferred
usage, launch budget, or watchdog/account-margin change is allowed.

Prediction before implementation/tests: the exact observed summary in a file,
custody copy and inline output contributes no additional native result, while
real results with missing/empty/invalid counters, failing expected captures,
unbound native sessions and observed launches without results still stop. All
inherited functional regression cases pass. A read-only component replay may
confirm the specific false positive is absent; it cannot change 0242's verdict.

This is bounded candidate classification, not a universal provenance proof.
A summary copying all native terminal fields cannot be distinguished by shape;
existing producer, receipt, session and accounting checks remain necessary.
Native validation, if reached, needs its own registration and seal after review.
