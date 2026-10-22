I'll read the round-1 prompt, both reviewer answers, and the 0256/0257 study constraints before judging the synthesis.The synthesis mixes two incompatible gates. I'll check it against the 0256 addendum, the §6 admission rule, and the decision code.The n = 10 layout and the completion/row Fisher stand. The witness rule, the headline order, the parser score, and the instruction check do not.

**3. Witnesses.** Point 2 maps "lower, Fisher does not reject" to INCONCLUSIVE. Point 3 maps "B reproduces more, Fisher does not reject" to a count that still allows DEVELOPMENT_PASS. One-sided Fisher does not reject 0/10 vs 3/10 (p = 19448/184756 ≈ 0.105) or 0 vs 1 (p = 0.5), so a binding witness A never shows can hit three B cells and the headline can still be PASS. The addendum's two pooled rules both reject a B-only witness, and §6 treats severe regression as absolute. The "≈ 0.23" figure is P(A = 0, B ≥ 1) at a shared rate 0.1. I0185 has 11 scripts, not ~13 (`adjudication.md`); several are 0/8 or 8/8. Saturated completions cannot false-reject; these witnesses can, so the completion family's "no Bonferroni" reason does not transfer.

Fix: binding set is I0185 K2, K3, K4, K5, K7, K8, K10, X1, X2 and D4 W1, W2. K6 and K9 are reported and do not gate. Per task × engine × binding witness, n_A = 0 < n_B is PACKAGE_LOWERS_QUALITY. If n_A ≥ 1 and n_B > n_A, Fisher reject → PACKAGE_LOWERS_QUALITY, otherwise INCONCLUSIVE. Union and per-replicate deltas are reported only. n_A = n_B passes, including a one-and-one swap.

**4 and 7. Headline.** "Any one B cell → PACKAGE_UNSAFE" is false under this first match: NO_CLAIM and PACKAGE_LOWERS_QUALITY come first. A prefix collides with point 7, which says NOT_FINISHED.

Fix: evaluate every clause and list them all. First match sets only the headline: NOT_FINISHED if any development slot lacks a verdict or an instruction STOP is unresolved; else PACKAGE_UNSAFE; else NO_CLAIM; else PACKAGE_LOWERS_QUALITY; else INCONCLUSIVE; else PACKAGE_COSTS_MORE; else COST_UNKNOWN; else NO_STRICT_GAIN; else DEVELOPMENT_PASS. A's false-completion count is printed beside B's and does not offset. Admission is the development headline. Confirmation and easy use the same rule, are printed beside it, and do not gate; no Fisher at n = 1. User-data harm stops dispatch. Until development is complete the headline stays NOT_FINISHED, with the harm listed.

**5. Parser.** Fix: fresh claude F10/F11 only; body `{`; `Content-Type: application/json`; POST `/items` and POST `/items/import`; 5 s. Classes: JSON-object-with-error 400, HTML 400, other, unassessable. Store-preserved is a separate bit. Scored outside the token, over all 20 scheduled cells per arm: B's JSON-object-with-error-400 count is lower than A's. Missing and unassessable cells stay in the denominator and are not passes.

**6. Instruction STOP fires on a correct install.** `managedBlock` wraps each template (`instructions.js`). The Claude attachment is that CLAUDE.md, not `sha256(CLAUDE.md ‖ AGENTS.md)`. Codex's file is the wrapped AGENTS.md. On I0185 the installer returns at "Skipping ${name}; shipped instruction template in devlyn-cli source checkout" and leaves the source files in place.

Fix: at qualification, seal the bytes `-y --claude` and `-y` write on an empty tree. Non-I0185 Claude B: the attachment hash equals sealed CLAUDE.md. Non-I0185 Codex B: on-disk AGENTS.md equals the sealed file before the owner starts. I0185 B: skip line present, skills present, both instruction hashes unchanged from the pre-install tree. I0185 A: those source hashes, and no managed block added. Other A cells: no sealed attachment and no installer AGENTS.md. Mismatch is STOP.

**7. "As 0256" is the wrong order.** 0256 reverses task order on r2 (`cells.tsv`). Freeze instead: SMOKE, E1, E2, then r = 1..10 with tasks fixed as D3, D4, I0185, B5, F10, F11. Within a task, claude's pair then codex's pair, arms back to back, AB on odd r and BA on even r.

**8. Caps are not frozen.** 0256 wrote 85/70, then 95/95, then 100/100 with `direct_run.py`, which drops the two-arm reserve (`registration.md`). Before SMOKE, write both percentages and pin `driver.py`: a block starts only when both arms fit; no `direct_run.py`. A later change stops the run until a dated amendment.

**Qualification is missing.** Before SMOKE, run the installer checks above and unit-test that a 0-vs-1 witness is LOWERS_QUALITY, completion 10 vs 7 is INCONCLUSIVE, 10 vs 6 is LOWERS_QUALITY, one false completion is UNSAFE even when a row also fails, and a prefix is NOT_FINISHED. Then four SMOKE cells.

**9. Predictions, scored separately:** claude development headline in {LOWERS_QUALITY, UNSAFE, INCONCLUSIVE}; codex development completions, 40 cells per arm, B ≥ A; both engines and both arms, zero I0185 completions; the point-5 count. I0185 stays inside the package headline and outside any principles-text sentence.

VERDICT: REVISE
