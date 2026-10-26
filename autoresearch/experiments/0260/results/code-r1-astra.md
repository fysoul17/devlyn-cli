VERDICT: REVISE
FINDINGS:

- [HIGH] autoresearch/experiments/0260/results/operator/judge.py:213 — A real first probe failure disappears if the retry’s create fails; `run()` likewise loses its first pass before line 148. Repeating the call resets attempts and can incorrectly resolve a measurement — Persist each completed attempt immediately and resume only missing attempts, excluding only failed creation.
- [HIGH] autoresearch/experiments/0260/results/operator/judge.py:95 — Cleanup failure after completed execution raises before its outcome is recorded, dropping real probe or witness failures — Persist the outcome and cleanup diagnostic before stopping; test removal errors and timeouts after completed execution.
- [LOW] autoresearch/experiments/0260/test_apparatus.py:864 — The refactor removes 0259’s assertions that `[2,1]` yields `unresolved` and preserves Docker error text — Restore both assertions.
