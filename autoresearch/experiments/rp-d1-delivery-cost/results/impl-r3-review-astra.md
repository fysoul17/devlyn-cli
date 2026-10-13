Two new findings remain:

- **HIGH — [cell.py:94](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d1-apparatus/autoresearch/experiments/rp-d1-delivery-cost/cell.py:94): arbitrary-named bare repositories escape PAT scanning.** A compressed PAT-bearing blob in collected `tmp/cache.git` is never inflated. An in-memory probe returned clean with zero inflation calls or revocation markers; identical content under `.git` triggered UNKNOWN. Detect Git storage within the collected roots and add an arbitrary-name regression.

- **MEDIUM — [stage.py:60](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d1-apparatus/autoresearch/experiments/rp-d1-delivery-cost/stage.py:60): writable smoke output may overlap sealed control.** `--smoke-output <stage>/control/public` passes staging and `--check`. Preparation then changes the control census and fails the inherited seal gate after repository seeding. Reject this overlap before staging; existing tests cover only the default destination.

Round-2 findings are closed in code. These regressions contain assertions that detect removal of the fixes:

| Round-2 issue | Fix | Regression |
|---|---|---|
| HIGH: partial-archive PAT | `runner.py:226–240`, `cell.py:75` | `test_apparatus.py:988` — partial archive scanned, repository retained |
| HIGH: evaluator-generated PAT | `runner.py:226–241` | `test_apparatus.py:1034` — evaluator output produces UNKNOWN/revocation |
| MEDIUM: installer-date coverage | `runner.py:66`; real installer exercised | `test_apparatus.py:704`, date assertion `:741` |
| HIGH: measured Claude catalogs | `stage.py:63,139` | `test_stage.py:109`; missing-catalog refusal at `:125` |

The final scan follows generated records on success and failure paths and precedes `rp-verdict.json`. Seven in-memory wrapper probes confirmed this ordering. Deletion still requires verified archive custody at `github.py:194–197`, covered by `test_apparatus.py:337,348`.

Default staging matches inherited consumers; stage/check read no PAT value, contact no GitHub service, and launch no model. Check uses Docker image inspection only. No additional installed-4.2.18 delivery incompatibility, accounting/identity/seal regression, or justified removable code found.

Validation used source inspection and in-memory probes. Four targeted tests could not enter their bodies because the read-only sandbox prohibits temporary directories.

VERDICT: REVISE
