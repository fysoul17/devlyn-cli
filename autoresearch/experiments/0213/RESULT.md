# 0213 — one completed cell; second cell stopped at the input target

2026-09-22. Root direct, no resolve. Current-login and frozen credential account/
organization matched before launch (provider session usage49% at that observation).
Both participant Fable5.1/medium reviews and the blinded Fable assessment worked;
the stale-account error from0212 is corrected. Source launch commit1adc2c7.

| Registered cell | Result | Owner + participant review INPUT / OUTPUT | Calls |
| --- | --- | --- | --- |
| D1, repetition1, A | COMPLETE | 370,000 /7,660 terminal | 2 |
| D1, repetition1, B | BUDGET_EXCEEDED; terminal usage UNKNOWN | 423,489 /10,333 last observed | 2 observed |
| Remaining22 cells | NOT_RUN | Not dispatched | 0 |

A passed all four frozen requirement checks and the independent public suite:
1,418 passed,1 skipped. Its blinded assessment returned complete:true with no
violating findings; assessment usage31,799 INPUT/3,160 OUTPUT/1 call is separate
from the400,000 owner-pool target. Total measured A time, including deterministic
checks and external assessment, was265.92s. Root accepted the participant's
rejection of combining-mark expansion against the explicit letter/number caller
contract; source did not change after participant review. Native full-suite color
failures were preserved, reproduced on original code, and absent in root checks.

B first exceeded the400,000 cache-inclusive owner-pool input target at266.667s:
390,690 native +32,799 participant review =423,489. Its review input was compact
(73,370 bytes) and Fable succeeded. The owner was preparing further checks after
a test-format edit when interrupted. Local teardown finished at266.894s and the
container was removed. No B external assessment or later owner was started.
Raw classes: BUDGET_EXCEEDED, UNKNOWN, INFRA_INVALID accounting. The last snapshot
is an observation, not terminal all-attempt usage or independently proven spend.

This screen therefore has2 attempts,1 completed,1 stopped,22 NOT_RUN and1 external
assessment. Across0211/0212/0213 there are4 public owner attempts, including both
previously retained failures. All-attempt final usage remains UNKNOWN; complete-A
numbers must not substitute for it. There is no completed A/B/C comparison, paired
efficiency ratio, causal inference, advancement or adoption conclusion.

Packet reduction and corrected authentication enabled an actual completed cell.
They do not guarantee that native multi-turn work stays below the registered
observed input target. The first-breach rule remains effective; neither thresholds
nor model/account routing were changed during this screen.

Evidence: `.devlyn/0213/launch-seal.json`, `auth-binding.json`, `cohort.json`,
`screen-stop.json`, `stop-guards.json`, `totals.json`, and both cell directories.
Raw originals remain in0211 and0212;377 original0211 files were reverified.
