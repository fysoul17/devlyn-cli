# Return batch contract

A rejected return batch leaves the order store byte-identical to its pre-batch form, rejection causes are reported by precedence with bad amount before missing order before closed return and arrival order breaking ties, and when successful refund writes precede validation and conflict failures the highest-precedence cause is reported while every earlier write is rolled back.

`process_returns` owns the batch boundary. The refund engine may inspect and
write the store while evaluating requests, but callers must observe either one
completed batch or the exact bytes that existed before the call.

The reason ranker receives every rejection with its original arrival index.
It orders by the precedence above, then by that index. `RefundBatchError.reason`
is the first ranked cause and `RefundBatchError.rejections` preserves the full
ranked sequence.
