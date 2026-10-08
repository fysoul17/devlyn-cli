Task 1: **REVISE the record; REJECT remains correct. No HIGH findings.**

- **MEDIUM — [Result:201](/Users/aipalm/.local/share/nx01/0236-reg/autoresearch/iterations/0236-review-findings-repair.md:201):** Costs labeled “c05 not counted” actually count it. Excluding c05, F per repair is **2548 s / 5.64M input / 124.9k output**; operationally **7181 s / 13.25M / 401.3k**. G’s figures are correct. F’s tokens are approximately **4×**, not 2×, G’s.
- **MEDIUM — [Result:184](/Users/aipalm/.local/share/nx01/0236-reg/autoresearch/iterations/0236-review-findings-repair.md:184):** “F repaired 2” overstates the evidence. Say **“F confirmed 1 repair, with c05 unresolved; at most 2, versus G’s 4.”** Apply the same distinction to the r04 table row.

Verification passed: all 16 witness judgments match `decisions.json` and the audit summary. c05’s writer uses `O_NONBLOCK` at `test_File.py:113`, genuinely outside injection coverage. `decide.py` rejects STOP; both hypothetical resolutions exactly reproduce stored `decision.json` and yield REJECT. This bounds the decision without resolving c05.

c12’s `f.read` at `test_File.py:176` and c16’s `lf.read` at `:209` open on the main thread before their bounded helpers; recorded watchdog stacks confirm genuine defects. c12 explicitly claims boundedness, supporting false completion. G’s four repairs are witness/audit clean. Claude passes all 16; Codex alone blocks all 10 incompletes, with zero severe findings. No containers rerun.

Task 2: **Stop this gate-plus-retry candidate here; retain the instruction-only baseline** (*No overengineering*, *Optimized*).
The favorable B-origin subset already fails the cost constraint in a descriptive replay: granting unchanged gate-pass successes, completion rises from 4/8 to 7/8.
Charging both assessors and retries gives **615 versus 495 s**, **1.438M versus 1.357M input**, and **42.2k versus 33.9k output per success**.
These reused snapshots are a cost diagnostic, not fresh admission evidence.
**Falsifiable prediction:** on fresh tasks, this unchanged policy improves Claude completion but increases at least one token-per-success metric versus B.
Codex’s complementary catches justify retaining independent evaluation; they do not establish an affordable production loop.
