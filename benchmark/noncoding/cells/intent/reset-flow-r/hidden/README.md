# Counterfactual identifiability: reset flow / resolved

The sole R/Q seed delta is `seed/docs/reset-policy.md`. In this variant, the
decisive bytes are `must require an explicit confirmation before defaults are
applied; immediate reset on activation is not allowed`. They select the
confirmation behavior from the two alternatives named in `task.txt`, so the
implementation must proceed and a product question is an unnecessary halt.

The Q sibling replaces only that file with bytes keeping immediate reset and
confirmation equally live. No source, test, task, or other seed byte changes.

The v2 conformance channels bind the reference behavior and terminal-message
validator to content hashes and excerpts from both the task and policy file.

Oracle environment contract: `FINAL_MESSAGE_PATH` is the arm's UTF-8 final
message, `BASELINE_COMMIT_SHA` is the staged seed commit, and
`FIXTURE_HIDDEN_DIR` is this directory.
