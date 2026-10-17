The registered **MIXED** decision is correct, but the write-up needs revision. No HIGH findings.

- **MEDIUM — Incorrect Claude attribution.** [results.md:45](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d4/autoresearch/experiments/rp-d4-helper-report/results.md:45) says g01 paraphrased the helper. [g01’s report:16](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d4/autoresearch/experiments/rp-d4-helper-report/results/measured/verdicts/g01-final-report.txt:16) quotes it verbatim. Both guards quoted the sentence.

- **MEDIUM — Interpretation and next-step claims exceed the evidence.** [results.md:65](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d4/autoresearch/experiments/rp-d4-helper-report/results.md:65) says the mechanism “moves Codex”; [line 73](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d4/autoresearch/experiments/rp-d4-helper-report/results.md:73) says eight per arm “would resolve” the effect and calls this the cheapest next step. Under **No guesswork**, describe an observed difference and a possible further test. Repeating the observed proportions at eight pairs gives X=0/8, Y=4/8 and one-sided p=0.0625. Neither confirmation, cheapest cost, nor a stable omission rate is established.

- **MEDIUM — Route evidence is missing from the commit.** [results.md:9](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d4/autoresearch/experiments/rp-d4-helper-report/results.md:9) asserts network stability and links the evidence directory, but `route-watch.log` is untracked, ignored by `*.log`. Retain the sanitized log or qualify the evidence claim. Its local contents show no later interface transition; they alone cannot establish absence of connection drops.

- **LOW — Quotation differs.** [results.md:37](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d4/autoresearch/experiments/rp-d4-helper-report/results.md:37) attributes “fast-forwarded” to both successful Codex reports. m07 says “fast forwarded”. Preserve its wording or remove quotation marks.

- **LOW — Handoff cost wording lacks qualification.** [HANDOFF.md:3](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d4/autoresearch/HANDOFF.md:3) says “also cheaper”. Specify lower observed raw totals and cost-gate passage by dominance over zero-success X; no general cost improvement was established.

- **LOW — Design-round count.** [HANDOFF.md:243](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d4/autoresearch/HANDOFF.md:243) says “5 design rounds”; the retained reviews span r0–r5: six rounds.

All ten measurement rows, rounded times, totals, category counts, historical first-success claim, and p=0.25 match the evidence. Applying the registered rules in order yields MIXED because only the cleanup adoption threshold fails.

`git diff cbc33be9 -- config .agents` is empty; the worktree is clean. No actual credentials or VPN hostname/IP were found in the committed rp-d4 evidence and HANDOFF, including branch-history versions. No files changed.

VERDICT: REVISE
