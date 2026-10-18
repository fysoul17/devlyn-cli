# rp-d7 write-up review r1 — Astra ultra

- **MEDIUM — Unsupported causal claim:** [results.md:102](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d7/autoresearch/experiments/rp-d7-prompt-delivery/results.md:102) says real requests rarely contain allowed-file lists and the residual skip “needs” such a contract. Every slot retained `caller.json`; neither prevalence nor necessity was tested. **Fix:** remove those claims and say applicability to requests without such restrictions remains untested. Clarify that BV 4/4 pools both runs.

- **LOW — Rounding unstated:** [results.md:65](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d7/autoresearch/experiments/rp-d7-prompt-delivery/results.md:65). The numbers are correct, including 6,526.5 → 6,527, but the requested rounding explanation is absent. **Fix:** state that calculations use unrounded values, seconds display to one decimal, and per-delivery tokens round to the nearest integer, with halves rounded up.

- **LOW — Prediction quotation is not exact:** [results.md:59](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d7/autoresearch/experiments/rp-d7-prompt-delivery/results.md:59) abbreviates the frozen prediction inside quotation marks. **Fix:** reproduce DESIGN’s prediction verbatim or remove the quotation marks and identify it as a paraphrase.

- **LOW — Fisher test direction omitted:** [HANDOFF.md:3](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d7/autoresearch/HANDOFF.md:3) gives “Fisher p 0.5” without specifying one-sided. **Fix:** write “one-sided Fisher exact p = 0.5”; the two-sided value is 1.0.

The delivery counts, cost arithmetic, m04 quotations, MIXED decision, fixed-unset/non-final explanation, prediction scoring, and cleanup statements otherwise check out. No secrets, VPN hostnames, or IP addresses found. No files edited or live experiments run.

VERDICT: REVISE
hook: Stop
hook: Stop
hook: Stop Completed
hook: Stop Completed
tokens used
91,597
- **MEDIUM — Unsupported causal claim:** [results.md:102](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d7/autoresearch/experiments/rp-d7-prompt-delivery/results.md:102) says real requests rarely contain allowed-file lists and the residual skip “needs” such a contract. Every slot retained `caller.json`; neither prevalence nor necessity was tested. **Fix:** remove those claims and say applicability to requests without such restrictions remains untested. Clarify that BV 4/4 pools both runs.

- **LOW — Rounding unstated:** [results.md:65](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d7/autoresearch/experiments/rp-d7-prompt-delivery/results.md:65). The numbers are correct, including 6,526.5 → 6,527, but the requested rounding explanation is absent. **Fix:** state that calculations use unrounded values, seconds display to one decimal, and per-delivery tokens round to the nearest integer, with halves rounded up.

- **LOW — Prediction quotation is not exact:** [results.md:59](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d7/autoresearch/experiments/rp-d7-prompt-delivery/results.md:59) abbreviates the frozen prediction inside quotation marks. **Fix:** reproduce DESIGN’s prediction verbatim or remove the quotation marks and identify it as a paraphrase.

- **LOW — Fisher test direction omitted:** [HANDOFF.md:3](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d7/autoresearch/HANDOFF.md:3) gives “Fisher p 0.5” without specifying one-sided. **Fix:** write “one-sided Fisher exact p = 0.5”; the two-sided value is 1.0.

The delivery counts, cost arithmetic, m04 quotations, MIXED decision, fixed-unset/non-final explanation, prediction scoring, and cleanup statements otherwise check out. No secrets, VPN hostnames, or IP addresses found. No files edited or live experiments run.

VERDICT: REVISE
