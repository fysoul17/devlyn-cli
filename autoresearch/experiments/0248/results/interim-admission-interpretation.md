# 0248 interim admission interpretation

**PROVISIONAL — before d08/d09/d10 and completion of the d07 independent audits.** Recorded 2026-10-10T22:15:56.543121+00:00. Read-only interpretation of the existing registration, not a new rule, result regrade, confirmation registration, or dispatch authorization.

**A genuine within-run peer counterexample does not alone require a larger confirmation campaign.** The inherited screen defines a signal as “more correct completions or equal correctness with lower resources” (0238/registration-proposal.md:76–90; 0243/registration-v1.md:111–122). It separately requires H to justify independence against S and P to justify its route against S/H. The 0246 registration explicitly records novel peer findings separately from quality/resources. Accordingly, 0248 v2's “any apparent diagnostic signal” inherits this comparative screen definition; it does not redefine every useful review comment as a passing candidate. Fresh confirmation is necessary before advancing an eligible signal toward admission, not an obligation triggered by any mechanistic observation.

The currently observed Claude H, P, S and A all pass the registered delivered-quality gates. Whole-run costs from their retained verdicts are:

| Arm | Owner wall seconds | Input tokens | Output tokens |
|---|---:|---:|---:|
| S | 1360.389 | 6,020,526 | 154,630 |
| A | 825.760 | 3,441,785 | 93,953 |
| P | 1751.571 | 10,593,254 | 193,245 |
| H | 1650.809 | 8,690,338 | 206,662 |

Against S, H costs 21.3%/44.3%/33.6% more and P costs 28.8%/76.0%/25.0% more in wall/input/output respectively. Thus neither currently demonstrates an incremental registered quality/resource benefit over the extra-owner-check control. P versus H also trades higher wall/input for lower output; it does not dominate H. A is cheaper than both, but remains the separately reported native comparator, not a substitute for the required integrated-baseline comparison. Claude B is still unrun, so do not finalize its comparison. A later B failure could establish an observed benefit over B while leaving H/P's missing advantage over S unchanged.

Preserve the distinct mechanistic finding. The preliminary d07 audit reports that the owner had already observed Date truncating `.123456` to `.123`, but its comparator/tests did not handle competing fractional orders. The Read/Grep/Glob-only peer proposed the `.000002` versus `.000001` semantic counterexample; the owner executed it, observed the wrong ID, repaired fractional comparison, and observed the correct ID. Credit that new counterexample and resulting repair if the final audit confirms it—not first discovery of precision loss, peer execution of the witness, or proof that the owner could never repair it unaided. This within-run contribution is compatible with no incremental final-quality benefit over S and higher whole-run costs. Extra self-selected tests or the pre-repair defect do not change the frozen final-quality endpoint.

Finish the remaining registered cells and audits under the unchanged stop rules. If the completed comparison still has no eligible comparative signal, close this mechanism conservatively and retain the useful counterexample as diagnostic evidence; no additional campaign is required solely to honor that observation. If an eligible signal does emerge, any advancement still needs separately registered fresh current-version harder repeats, matching arms and easy/orphan controls for each engine, with all quality/wall/input/output nonregression gates. This statement neither grants admission nor adds an early-stop or follow-up rule.

Keep Codex B's observed PRODUCT_INCOMPLETE and precision failures. Historical Codex H/P negatives remain version-qualified observations with original costs; current-helper Codex H/P remain NOT OBSERVED. Do not infer their outcomes from Claude, pool versions, retake negatives, or claim a global/current-version null. Retain all failed/recovered/operational expenditure, old d05 STOP cost and old 0243 d02 unknown residual; peer-only cost cannot replace whole-run cost. This interpretation applies **No guesswork** and **No overengineering** without weakening the registered comparison.

Binding: registration-v2 SHA-256 `866b4384dd32f891b8539ba93a6dd645e2010d85d2fa02966d3203e1fb27e91f`. d05/d06/d07 verdict hashes respectively `7ebc4cbafd44f16c41027becc3c4b3dcb8cb917ce4ab426fbe290ae150ebd028`, `462530dd619068d80153dc553421d33e283e0534f30698c952b93c3faa6fe5af`, `7d735bf545596ba71eaead04450db3437fc2265e9e316a087a6e5889c58c035c`. No native/authentication/test/evaluator calls or input/result edits were performed.
