# 0219 screen — stopped at cell 2 (D1 B) by the first-breach rule

2026-09-24. Screen `0219-screen-20260924`, runner [run_cell.py](run_cell.py),
source `0ee2484`, admission per [PREPARED](PREPARED.md). Host load 8–27.

| Cell | Result | Owner + review INPUT / OUTPUT | Calls | Owner s |
| --- | --- | --- | --- | --- |
| 01 D1-1-A | COMPLETE | 230,575 / 6,472 | 2 | 165 |
| 02 D1-1-B | BUDGET_EXCEEDED; terminal UNKNOWN | 420,832 / 10,334 last observed (target 400,000) | 2 | 263 |
| 03–24 | NOT_RUN | — | 0 | — |

**Breach (observed):** the product work was done before the breach. One
review (64,711 B prompt) returned pass-with-notes, and the review disposition
records no in-scope findings. The meter read 318,607 after the review and
351,557 during the final audit. The owner still ran further wrap-up generations:
scope/hash audit, disposition, and meter re-reads. Each one re-sent the whole
context, roughly 30–35k cache-inclusive input: 351,557 → 385,698 → 420,832. The
breach therefore came from post-completion bookkeeping, not from the review
packet or a check-parity detour. The 0219 D2/D4 fix was not reached.

Per the registered stop rule, the screen stays stopped with no resume. Results
are descriptive only (0210). D1 is exposed material, and its prior 0216–0218 B
rows (302k–388k) are not pooled. Evidence: `.devlyn/0219-screen/`.
