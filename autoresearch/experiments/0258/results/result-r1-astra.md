**REVISE — no HIGH findings.**

- **MEDIUM — [RESULT.md:16](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0258-result/autoresearch/experiments/0258/RESULT.md:16), also lines 22–23.** “Does not change the behavior” / “does not move either endpoint” overstates non-rejection. Observed counts differ, and DESIGN explicitly says limited power prevents concluding no effect. **Fix:** “Neither prespecified one-sided test rejected.”

- **MEDIUM — [RESULT.md:59](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0258-result/autoresearch/experiments/0258/RESULT.md:59).** Account reporting contains allocation counts only; DESIGN:60–61 requires **results** by account fingerprint. The sole P1 event occurred on account `25813…`, which had one C F10 cell and no B F10 cell. **Fix:** add descriptive account × task × arm denominators, endpoint counts, and completions.

- **LOW — [RESULT.md:46](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0258-result/autoresearch/experiments/0258/RESULT.md:46).** “All 64 public checks” confuses cells with checks. `checks.json` contains **128 passing public commands**: 32 F10 plus 96 D3. **Fix:** “All 64 cells passed their public checks.”

- **LOW — [RESULT.md:86](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0258-result/autoresearch/experiments/0258/RESULT.md:86).** “No other F10 report … claims a behavior for non-object bodies” is too broad. `c006/final.txt:26` explicitly says `[]` returned the expected 400; that claim is correct. **Fix:** narrow this to the blanket claim covering all non-object JSON bodies.

Read-only recomputation reproduces **all of `decision.json` exactly**. Checked readiness, fixed-size Holm, and absent-direction p=1 behavior agree with DESIGN. Endpoint counts, replicate rows, completions, disclosures, account totals, usage, and logged operations counts match.

**c031 is correctly a false completion under m24:** its specific promise is contradicted by strict parsing and both recorded witness runs. All B/C finals were reviewed, with detailed snapshot checks on eight cells per arm, including B c001/c008/d025/d032 and C c006/c022/c031/d015. No additional specific, falsified mechanism claim was found; the inherited standard was applied consistently.
