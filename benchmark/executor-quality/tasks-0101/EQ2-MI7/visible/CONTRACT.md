# Waitlist promotion contract

Within one bounded promotion board, submissions sharing a request key must reuse the first duplicate-log outcome and change the queue or roster at most once, rejection reasons rank paused candidate before full roster before out-of-turn position with source order breaking equal-reason ties, and when duplicate bodies would fail for different reasons the first recorded ranked rejection must remain stable without a second log row or promotion side effect.

`submit_promotion(board, log, request)` returns a `PromotionOutcome`. A request key names one submission even when a retry carries a changed candidate body. The duplicate-entry log owns that identity boundary; the promoter owns queue and roster mutation.

Promotion boards are bounded. A successful promotion removes the next candidate from the queue and appends that candidate to the roster. Rejections leave both collections unchanged.
