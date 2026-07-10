# F21 base snapshot

`source.bundle` contains the committed pre-task state from
`benchmark/auto-resolve/fixtures/test-repo`, including the realistic server,
web, and test distractors. The ignored `node_modules` directory is excluded:
the F21 oracle uses only Node core modules and `node --test`, so evaluation
requires no package installation.
