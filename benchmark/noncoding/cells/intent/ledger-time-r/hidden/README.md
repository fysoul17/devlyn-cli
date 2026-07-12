# Counterfactual identifiability: ledger time / resolved

The sole R/Q seed delta is `seed/docs/data-contract.md`. In this variant, the
sentence beginning ``The supported representation`` contains the decisive
bytes `UTC normalized RFC 3339 with a trailing Z; source offsets must not be
preserved`. Those bytes select the first of the two alternatives named in
`task.txt`, so proceeding is required and asking product to choose is an
unnecessary halt.

The Q sibling replaces only that file with a sentence keeping both named
representations live. No source, test, task, or other seed byte changes.

Conformance schema delta: `hidden-conformance-2` extends v1 channels with
content-hashed `task.txt` and `seed/` bindings. The executable terminal-message
validator is therefore frozen against both the visible alternatives and the
repo evidence instead of encoding an unbound author preference.

Oracle environment contract: `FINAL_MESSAGE_PATH` is the arm's UTF-8 final
message, `BASELINE_COMMIT_SHA` is the staged seed commit, and
`FIXTURE_HIDDEN_DIR` is this directory.
