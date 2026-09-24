# 0218 screen — stopped at cell 7 (D2 A) by the first-breach rule

2026-09-24. Root direct, no resolve. Screen `0218-screen-20260924`, runner
[run_cell.py](run_cell.py) (source `21c8138`), per [DESIGN](DESIGN.md). Every
dispatched cell was sealed before launch with a fresh current-login snapshot.
Admission checks: calibration digest `253aed40…`, 8 format-gate controls,
meter controls and 24 dry bindings.

| Cell | Result | Owner + review INPUT / OUTPUT | Calls | Owner s |
| --- | --- | --- | --- | --- |
| 01 D1-1-A | COMPLETE | 248,094 / 6,935 | 2 | 221 |
| 02 D1-1-B | COMPLETE | 343,396 / 7,648 | 2 | 237 |
| 03 D1-1-C | COMPLETE | 243,241 / 7,426 | 2 | 194 |
| 04 D1-2-C | COMPLETE | 282,451 / 6,978 | 2 | 209 |
| 05 D1-2-B | COMPLETE | 288,354 / 8,368 | 2 | 249 |
| 06 D1-2-A | COMPLETE | 293,794 / 7,786 | 2 | 223 |
| 07 D2-1-A | BUDGET_EXCEEDED; terminal UNKNOWN | 1,007,058 / 13,091 last observed (target 800,000) | 2 | 379 |
| 08–24 | NOT_RUN | — | 0 | — |

All six D1 cells passed requirement checks, public suite, format gate and scope,
with blinded assessment complete:true and no HIGH/CRITICAL findings.

**Breach cause (observed):** D2 A's single Fable review consumed 387,323 input.
Its prompt was 1,104,757 bytes, mostly raw pytest logs the owner saved under
`checks-final` (for example, `baseline-pager/stdout.txt` 466 KB and `public-full`
157 KB). The compact packet ([0211/packet.py](../0211/packet.py)) filters only
repetitive Node TAP output, so this Click-side transport gap was never exercised
on D1. Owner native input was 619,735 over 19 generations. The observation that
brought the total from 574,693 to 1,007,058 arrived in one step when the review
finished, so the meter could not have shown it in time.

Setup events, no model dispatched: cell 1's first `docker create` timed out
(host overload); cell 2's first try ran after the Mac slept 03:04–08:11 and was
refused on login-token time. Host load stayed high (1-minute average 29–87, from
unrelated workloads), which is a timing limitation. Results are descriptive only
under 0210: no advancement, confirmation or adoption. D1 is exposed tuning material.

Evidence: `.devlyn/0218-screen/` in the retained base checkout, archived as
`.devlyn/0218-screen-evidence.tar.gz`.
