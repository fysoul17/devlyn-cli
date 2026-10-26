I'll review the amendment against the spec, the classifier, reclassify, and the inherited 0233 rules, then check the tests. Read-only.The amendment is legitimate. It was written before the probe, the witness, and the audit, and the rule reads only native event fields, so it is blind to the endpoints and arm-neutral. It matches the inherited fault rule: an execution authentication fault is a shared-account STOP, which the driver archives and reruns. `d007` was graded `PRODUCT_INCOMPLETE` because 0233 only sees `api_error_status` on the result. Keep result text unread. Narrow the rule before the rerun uses it. The late slot for that rerun is already disclosed.

`quota.py` implements that written shape. A result 0233 already classifies keeps 0233's kind, so the same event is not counted twice, and a 401 followed by a successful result is not a hit. A 401/403 `api_retry` is still remembered for the rest of the file, so a later unrelated `api_error` result inherits it. The dry classification shows that this does not hit any other finished cell.

`reclassify.py` rewrites only a measured, non-STOP verdict whose recorded `quota.execution` is empty and whose evidence now has an execution hit. It checks every file before the first write. A malformed verdict or a missing cell directory exits nonzero and leaves the originals in place. The reason prefix is the one `driver.py` already archives to `.stop-N` and reruns. `decide.py` scores the new final verdict only. `slot_cost` keeps the archived wall time and tokens, and the archive stays in the mandatory audit. `d007`'s identity is `MATCH` (the next cell ran), so the harm latch does not block that archive.

The new tests lock the cases they build, including 0233 precedence and the no-partial-write failure. They never build a stale 401 followed by a later `api_error`, so they accept that false positive.

```
VERDICT: REVISE
FINDINGS:
- [HIGH] autoresearch/experiments/0259/quota.py — a 401/403 `api_retry` stays in force for the rest of the stream, so a later unrelated `result` (`terminal_reason: api_error`, including `api_error_status` 529 or null after an assistant turn) becomes `claude authentication retry` and the rerun archives that attempt — clear the remembered status on an `assistant` event, require `api_error_status is None`, and add both negative cases to `test_apparatus.py`. Check that `d007` still matches before applying: its result status is null and it had no model turn.
```
