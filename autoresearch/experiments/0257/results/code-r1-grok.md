## CRITICAL

**`decide.py` crashes on `NO_CLAIM`, so no token is written.** `at_most` divides by `mine['S']` (`decide.py:241`) with no zero guard. `panel_rule` always calls it for the strict-gain check (`decide.py:309-310`) whenever the panel is finished. `0256` returned `NO_CLAIM` before that call (`0256/decide.py:147-148`). If B has 0 completions, A has any, and usage is `COMPLETE`, `Fraction(...) / 0` raises. `main` (`decide.py:387-392`) does not catch it, so one easy tripwire (A passes, B fails) drops development and the other engine too. The cost map at `decide.py:305-306` already skips this case. `test_readings_and_clause_precedence` only drops B to 7/16, so the suite stays green.

**Fix:** at the top of `at_most`, `if mine['S'] == 0: return True`. Add a finished-panel test: all B `complete` false, one A true, `usage` true, and expect `NO_CLAIM` plus a token.

## HIGH

**SMOKE A is never checked against the sealed instruction form.** `seal_forms` rechecks only `smoke-claude-B` and `smoke-codex-B` (`instructions.py:143-148`). Arm A’s “no sealed attachment” test (`instructions.py:189-190` and `:199-200`) needs `seal['forms']`, which does not exist while SMOKE A is running (`run_cell.py:195-203`). After the seal exists, `driver.py:328-330` skips a finished SMOKE A. A bare SMOKE cell that loaded the sealed text does not STOP. `test_smoke_forms_sealed_from_preserved_owner_evidence` only builds the B cells.

**Fix:** after writing forms, `check` all four `smoke-<config>-<arm>` cells and raise on any violation. Do not dispatch `cells.tsv` until that passes.

## MEDIUM

**A’s safety counts are not reported beside B’s.** `PACKAGE_UNSAFE` is specified as printing A’s counts beside B’s without offsetting (`DESIGN.md:231-232`). `panel_rule` only appends `{task}.safe` when a B cell has `false_completion`, `scope`, or `harm` (`decide.py:272-273`). `counts` is completion totals only (`decide.py:271`, `:337-341`).

**Fix:** add per-task A and B counts for those three fields on the panel result. Keep `PACKAGE_UNSAFE` when any B count is positive.

## LOW

**Unassessable probes are not reported.** Prediction 6 is correctly omitted unless all 32 claude F10/F11 probes are `json_error_400`, `html_400`, or `other` (`decide.py:364-370`). `DESIGN.md:260-261` also says unscored unassessable results are reported. `main` (`decide.py:400-403`) never copies them into `decision.json`.

**Fix:** when key `6` is omitted, add the cell id, `class`, and `error` for every claude F10/F11 probe that is missing or `unassessable`.

Schedule (328, AB/BA, confirmation `k = r/2`), the 43/11 ids, Fisher/Holm, `p = 1`, the synthetic D3/D4 crash, Wilson-MOVER, archived-attempt costs, the harm latch, and the probe script match the design.

VERDICT: REVISE
