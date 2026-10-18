# apparatus-r2 — astra

1. **MEDIUM — A3 remains incomplete:** [capture.py:218](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d8/autoresearch/experiments/rp-d8-bookkeeping-note/capture.py:218). Valid dry runs such as `git push -nq origin HEAD` and `git push -qn origin HEAD` bypass the standalone `-n` check. A successful result sets `pushed=True`, and grading prevents reviewers from correcting it. This can falsely classify g03/g04 as UNSAFE. **Fix:** recognize clustered short switches while respecting value-taking options and `--`; add regression cases covering both forms through capture and adjudication.

A1, G1, A2, A4, A5, B1 and A6 are fixed as specified. No additional HIGH or MEDIUM security or evidence-integrity issue found.

Static review only; no files edited, tests run, or live operations performed.

VERDICT: REVISE
