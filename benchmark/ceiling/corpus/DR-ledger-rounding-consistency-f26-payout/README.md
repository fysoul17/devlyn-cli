# F26 ceiling corpus port

Categorical-reliability class: `ledger/rounding-consistency`.

L3 classification: **ALGORITHM**. The difficulty comes from composing
idempotent and conflicting event semantics with per-event fee rounding,
refund/dispute treatment, reserve computation, minimum-payout holds,
first-seen ordering, and exact top-level totals. It is not a trigger-word
trap, so `task.txt` preserves the fixture's full public contract.

`source.bundle` contains the committed pre-task state from
`benchmark/auto-resolve/fixtures/test-repo` plus the payout-rules seed created
by the fixture setup. The ignored `node_modules` directory is excluded: the
oracle uses only Node core modules and `node --test`, so evaluation requires
no package installation.

The hidden oracle embeds the fixture's three behavioral verifiers verbatim,
runs the existing CLI suite, checks every class-defining forbidden source
pattern, and enforces the original `bin/cli.js` / `tests/cli.test.js` scope.
