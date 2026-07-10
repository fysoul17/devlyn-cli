# F25 ceiling corpus port

Categorical-reliability class: `shape/compound-rules`.

L3 classification: **ALGORITHM**. The difficulty comes from composing
duplicate-SKU aggregation, stock validation, two line-promotion formulas,
coupon ordering, taxable-base selection, shipping threshold timing, and the
exact output shape. It is not a trigger-word trap, so `task.txt` preserves the
fixture's full public contract.

`source.bundle` contains the committed pre-task state from
`benchmark/auto-resolve/fixtures/test-repo` plus the catalog seed created by
the fixture setup. The ignored `node_modules` directory is excluded: the
oracle uses only Node core modules and `node --test`, so evaluation requires
no package installation.

The hidden oracle embeds the fixture's three behavioral verifiers verbatim,
runs the existing CLI suite, checks every class-defining forbidden source
pattern, and enforces the original `bin/cli.js` / `tests/cli.test.js` scope.
