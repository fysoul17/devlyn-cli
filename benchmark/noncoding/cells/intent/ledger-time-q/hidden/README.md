# Counterfactual identifiability: ledger time / question

The sole R/Q seed delta is `seed/docs/data-contract.md`. In this variant, the
sentence beginning ``Downstream consumers`` contains the decisive bytes
`either UTC normalized values with a trailing Z or values preserving each
source offset; the product choice ... is still pending`. Those bytes keep
exactly the two alternatives named in `task.txt` live, so neither
implementation is authorized and the terminal behavior must ask which one is
required without mutating product files.

The R sibling replaces only that file with bytes selecting UTC normalization.
No source, test, task, or other seed byte changes.

`hidden-conformance-2` binds the message validator to hashes and excerpts from
both `task.txt` and this repo-evidence file. The validator accepts varied
phrasing only when it requests a decision and semantically names both UTC/Z
normalization and source-offset preservation; generic ambiguity language does
not satisfy either alternative predicate.

Oracle environment contract: `FINAL_MESSAGE_PATH` is the arm's UTF-8 final
message, `BASELINE_COMMIT_SHA` is the staged seed commit, and
`FIXTURE_HIDDEN_DIR` is this directory.
