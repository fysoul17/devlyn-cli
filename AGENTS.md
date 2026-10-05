Treat the request and supplied acceptance criteria as the contract. Inspect relevant source, callers and checks before editing. Resolve material ambiguity, preserve user changes and stay within authorized scope. Prefer the smallest root-cause fix; do not create a duplicate specification.

For behavior changes, demonstrate a relevant baseline failure before repair when feasible. Otherwise explain the missing baseline witness and verify the required behavior with meaningful coverage.

Remove orphans and disposable artifacts your change created, and repair references it invalidated. Leave unrelated pre-existing dead code alone.

Run required checks against the source being submitted. Before claiming completion, obtain one fresh review from another engine using the contract, current source/diff and actual check results. For that review, pipe the contract and check results to `node "$HOME/.devlyn/review.js" --engine claude` inside the repository; it adds the diff and untracked files (pass `--base <start commit>` if any of the change is committed) and can take several minutes. Evaluate findings against evidence, repair justified findings, rerun affected checks and refresh review of changed source. Reuse valid evidence for unchanged source.

Report completed behavior, actual verification, unresolved findings and missing evidence. Report delivery separately. An unavailable reviewer or failed invocation is an explicit limitation, never completed review.
