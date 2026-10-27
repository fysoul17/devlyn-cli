R1’s timeout, witness setup/applicability, omission-gating, per-task guard and scoring-calibration issues are addressed at design level. The deliberate paired-bound approach is reasonable; G3’s estimand remains problematic.

- **HIGH — G3 can pass token growth far beyond its caps (§Endpoints).** With equal B costs, 31 C/B ratios of 0.8 and one of 20 produce a geometric ratio of **0.8847** and upper 90% bound of **1.0092**. Both token guards pass despite **40% higher total tokens**. This concerns the log estimand, not the choice of bounds over point estimates. **Fix:** retain paired bounds but target arithmetic cost—for example, require the upper bound on mean(`C − qB`) ≤ 0, with the chosen cap `q`.

- **MEDIUM — Unknown usage has no decision rule (§Readiness).** Inherited accounting permits incomplete totals: archived 0257 c017 has `UNKNOWN` usage because its result envelope is missing. R2 requires judgments and witnesses but never complete costs; lower-bound totals cannot safely become exact log ratios. **Fix:** require complete accounting or conservative bounds proving the same guard result; otherwise return `NOT_FINISHED`.

- **MEDIUM — Blind packets cannot support the entire promised audit (§Apparatus 5, §Grading).** Earlier completion messages and one end tree cannot establish whether an archived attempt’s claim was false on that attempt’s tree. The inherited 0260 audit also requires execution traces and baseline/Git/outside-repository evidence for safety judgments. **Fix:** include sanitized evidence and trees per attempt, plus the required provenance evidence or a separately blinded safety audit.

- **MEDIUM — “Both ways” is insufficiently specified for multiple disagreements (§Grading).** Two reviewer-wide tallies can agree while a mixed resolution changes the headline: B9/C2 gives Fisher p=.02166; B10/C3 gives p=.02981; B9/C3 gives p=.05343. **Fix:** evaluate attainable headlines across unresolved item assignments, using extrema where sufficient. Keep the deliberate rule that only a possible headline change causes `NOT_FINISHED`.

- **MEDIUM — G1 permits an unclassified ADVANCE (§Decision).** C may have three additional reproducing pairs on each task, passing G1 with pooled +6. Neither `REPORT_ONLY` nor `DEFECTS_DOWN` then applies. **Fix:** explicitly classify pooled increases +4…+6, or define `REPORT_ONLY` consistently with the per-task margins and qualify its interpretation.

VERDICT: REVISE
