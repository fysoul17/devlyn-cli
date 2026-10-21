I'll review the revised design against the round-2 findings and the 0233 `at_most` decision, without changing any files. First I'll load the draft, the earlier reviews, and the decision code they cite.The draft and both round-2 reviews are in. Next I’ll check `at_most`, the 0239 negative control, and whether the new reserve and renewal rules match the code they cite.Keeping `at_most` is sound. `0233/decide.py:113-118` passes a complete candidate whose per-success cost is at most the reference figure, and returns unknown when the candidate is above an incomplete reference. When both totals are complete and the candidate is above the reference, that line returns false. Unknown on every incomplete reference would drop passes that hold whenever the recorded figure lower-bounds true cost.

`DESIGN.md:186-187` stores the larger of the envelope and the terminal sum as that figure. In the 0239 control the envelope excess is not a proven token count, and that excess is a different quantity from the unknown interrupted-stream usage (`d01-native-audit.md:99-104`). Residuals stay null. "Retain the larger native total" (`:112`) keeps the observed aggregate. It leaves `aggregate ≤ true cost` unshown, so `decide.py:116-117` can pass a candidate whose true cost is higher. The floor for the kept comparison is the summed terminal usage.

Resolved from round 2: COMPLETE equality, per-message terminal usage, and retry/abort/progress coverage (`DESIGN.md:182-185`); unmodified D3/D4 JSON, one fetch, one sha256, both arms (`:78-80`; development stays 32, measured 56); host renewal once per expiry (`:147-155`); cell deltas covering Codex-configuration Claude reviews, a second arm that waits for reset, and redraws only of arms with no verdict (`:159-174`); reading order, paired witnesses, `NOT_FINISHED`, and zero-success dominance (`:192-193`, `:220-236`; `decide.py:111-112`, `:134-137`); Codex project-trust (`:121-123`).

S and F, recorded before SMOKE, are the only pre-SMOKE owner inputs. Root's 85/70 is a recommendation. A powered study (`:46`) and the next candidate (`:238-239`) are later owner decisions.

**HIGH** `DESIGN.md:186-192`. The larger total is an unproven floor (`d01-native-audit.md:99-112`), so the kept pass can admit a higher true cost. The floor is the terminal sum.

**MEDIUM** `DESIGN.md:143-146` and `:252-255`. Assessors need a fresh snapshot and 1,500 s, but `assess.py:75` copies the preflight file (`run_cell.py:159`) inside `grade` (`:220`). `drive.sh` is named for that operation and does not run between the owner and the assessor.

**MEDIUM** `DESIGN.md:162-165`. "The larger of" 10 seven-day points and 25 five-hour points, plus one SMOKE change, is one number for two windows. Neither floor is measured.

REVISE
