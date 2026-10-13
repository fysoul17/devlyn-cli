- **MEDIUM — [summarize.py:125](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d1-apparatus/autoresearch/experiments/rp-d1-delivery-cost/summarize.py:125):** Reviewer identity is unchecked. Pointing both reviewer arguments at Astra’s directory counts the same approval twice and yields SUCCESS. Validate the expected reviewer identity.

- **MEDIUM — [summarize.py:131](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d1-apparatus/autoresearch/experiments/rp-d1-delivery-cost/summarize.py:131):** Accepted `PASS` records become SUCCESS without either review. Current runner cannot emit this status, but the summarizer explicitly accepts and tests the bypass. Reject it or require both reviews.

- **MEDIUM — [summarize.py:151](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d1-apparatus/autoresearch/experiments/rp-d1-delivery-cost/summarize.py:151):** UNKNOWN usage retains numeric wall cost per success. Null all per-success costs for that engine; preserve total wall seconds.

In-memory probes confirmed these behaviors. Runner field mapping, template round-trip, failure totals, STOP/NOT_RUN handling, and zero-success handling checked correctly. No files changed.

VERDICT: REVISE
