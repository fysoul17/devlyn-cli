# rp-d7 registration review r1 — Astra ultra

Three findings:

- **MEDIUM — Prediction scoring violates frozen DESIGN.** [DESIGN.md:176](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d7/autoresearch/experiments/rp-d7-prompt-delivery/DESIGN.md:176) requires the second clause to remain unscored whenever any skip’s tags are unset. [summarize.py:85](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d7/autoresearch/experiments/rp-d7-prompt-delivery/summarize.py:85) instead scores it false when another skip supplies a counterexample. **Fix:** prioritize unset tags, update the regression expectation, then refresh `apparatus_commit` and affected input hashes. Preserve DESIGN.

- **MEDIUM — Decision text is summarized, not copied unchanged.** [registration.md:55](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d7/autoresearch/experiments/rp-d7-prompt-delivery/registration.md:55) incorporates DESIGN by reference but fails the requested verbatim-copy check. **Fix:** copy DESIGN’s complete Decision section unchanged; include the prediction’s unscored-tags qualification too. The prediction quotation itself matches exactly.

- **LOW — Prediction assurance overclaims.** [registration.md:49](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d7/autoresearch/experiments/rp-d7-prompt-delivery/registration.md:49) says no prediction score occurs while outcomes are unknown, but code permits partial scoring. **Fix:** say “no positive prediction support while outcomes are unknown,” alongside the unset-tag correction above.

Verified: **all 16 input SHA-256 hashes match both worktree files and `apparatus_commit` blobs**. P1 derivation, 353-byte length, trailing newline and hash match. X release identities/integrity, cache identity, model/effort, schedule, smoke/spare names and six repository names are consistent with the retained sources and code. No secret, VPN hostname or IP was found in either registration file.

External release/cache bytes, rebuilt-image provenance and reported test totals were not independently verified. No files changed; no tests or live operations ran.

VERDICT: REVISE
hook: Stop
hook: Stop
hook: Stop Completed
hook: Stop Completed
tokens used
49,427
Three findings:

- **MEDIUM — Prediction scoring violates frozen DESIGN.** [DESIGN.md:176](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d7/autoresearch/experiments/rp-d7-prompt-delivery/DESIGN.md:176) requires the second clause to remain unscored whenever any skip’s tags are unset. [summarize.py:85](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d7/autoresearch/experiments/rp-d7-prompt-delivery/summarize.py:85) instead scores it false when another skip supplies a counterexample. **Fix:** prioritize unset tags, update the regression expectation, then refresh `apparatus_commit` and affected input hashes. Preserve DESIGN.

- **MEDIUM — Decision text is summarized, not copied unchanged.** [registration.md:55](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d7/autoresearch/experiments/rp-d7-prompt-delivery/registration.md:55) incorporates DESIGN by reference but fails the requested verbatim-copy check. **Fix:** copy DESIGN’s complete Decision section unchanged; include the prediction’s unscored-tags qualification too. The prediction quotation itself matches exactly.

- **LOW — Prediction assurance overclaims.** [registration.md:49](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d7/autoresearch/experiments/rp-d7-prompt-delivery/registration.md:49) says no prediction score occurs while outcomes are unknown, but code permits partial scoring. **Fix:** say “no positive prediction support while outcomes are unknown,” alongside the unset-tag correction above.

Verified: **all 16 input SHA-256 hashes match both worktree files and `apparatus_commit` blobs**. P1 derivation, 353-byte length, trailing newline and hash match. X release identities/integrity, cache identity, model/effort, schedule, smoke/spare names and six repository names are consistent with the retained sources and code. No secret, VPN hostname or IP was found in either registration file.

External release/cache bytes, rebuilt-image provenance and reported test totals were not independently verified. No files changed; no tests or live operations ran.

VERDICT: REVISE
