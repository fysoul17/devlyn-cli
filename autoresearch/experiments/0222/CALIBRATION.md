# 0222 calibration

Model-free and in-image, through the same `check.evaluate` that grades cells ([calibrate.py](calibrate.py)). Expectations were fixed before each run from prior evidence: the 0207 reference/mutant rules for D3/D4, and the recorded 0185 replay outcomes for I0185. Predictions and raw results live in `.devlyn/0221/s3-design/predictions.md` and the receipt scratch.

| Run | Image | Result |
|---|---|---|
| P1 attempt 1 | 84a01941 | NO_VERDICT: the `/cell` tmpfs was root-owned, so the evaluator could not create its fixture directory. Fixed with `mode=1777`. |
| P1 attempt 2 | 84a01941 | 22/23 as predicted. **Miss:** the D3 reference fails the Prettier gate (its oracle rows all pass). The 0207 reference predates the 0218 format gate, and the mutants are exact-string edits of it, so it cannot be reformatted. Amendment, disclosed after seeing the result: reference/baseline variants judge the test-suite checks and exclude the format gate. Cells still grade the format gate. |
| P2, 5 repeats | 84a01941 | 115/115 as predicted. Every variant's rows were identical across repeats. No D3.6 timeout. Host load 3.4–7.5. |
| P3, after the R1 fixes | 84a01941 | 23/23 as predicted, rows identical to P2. No oracle or replay run exited non-zero, so the later rule that JSON counts only after exit 0 cannot change these results. |

## What each variant shows

- **D3 (8 variants):** the baseline is rejected (D3.1, D3.2, D3.4 fail) while its public suites pass; the reference passes every oracle row; each of the 6 mutants fails its named row (D3.6 included, in-image).
- **D4 (7 variants):** the baseline fails D4.1-2 and D4.3; the reference is clean, and its full `python -m pytest` passes on the read-only mount; each of the 5 mutants fails its named row.
- **I0185 (8 variants):**
  - The original is rejected by heldout.
  - The sealed A1/A2/B1/B2 products fail exactly release and terminal-alias; C1 fails exactly absence-lock; C2 passes everything, matching 0185's root-complete column.
  - The 0185 reference fails release and terminal-alias, and its absence-lock replay is **NOT_TRIGGERED**. This exercises the adjudication path, as recorded in 0185.
