# rp-d7 apparatus review r2 — Astra ultra

1. **HIGH — Encoded extra credentials bypass the scoped-only gate.** [runner.py:24](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d7/autoresearch/experiments/rp-d7-prompt-delivery/runner.py:24): A valid ASCII `hosts.yml` plus UTF-16LE `config.yml` containing an additional `oauth_token: ghp_…` passes validation. Interleaved NUL bytes evade the key/prefix checks. The entire directory is then mounted, exposing the recoverable full-access token; scanning covers only the selected PAT. **Fix:** require a canonical encoding without NULs and validate an allowed configuration schema before mounting. Add UTF-16/UTF-32 rejection cases.

2. **MEDIUM — Publication revalidation reads an unbound baseline.** [grading.py:126](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d7/autoresearch/experiments/rp-d7-prompt-delivery/grading.py:126): Recomputed publication facts depend on `baseline.json`, but the evidence manifest covers only `run`, `cell`, `tmp`, and `home`. Changing `allocation_sha` after grading to the archived main commit can make a previously non-baseline ref appear clean and permit a skip finding when no command witness or PR remains. The bound grade and manifest remain unchanged. **Fix:** bind the baseline digest into the grade/record and verify it before recomputation; missing baseline must remain unknown, and mutations must fail. Add a baseline-mutation regression case.

The other five fixes check out: exact `CLAUDE.md` binding, classification order, combinable `none`, unresolved false completion, and prediction uncertainty. Existing scan-before-seal and token-free launcher arguments remain connected.

Static inspection only; no files changed or tests/live operations run.

VERDICT: REVISE
hook: Stop
hook: Stop
hook: Stop Completed
hook: Stop Completed
tokens used
93,595
1. **HIGH — Encoded extra credentials bypass the scoped-only gate.** [runner.py:24](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d7/autoresearch/experiments/rp-d7-prompt-delivery/runner.py:24): A valid ASCII `hosts.yml` plus UTF-16LE `config.yml` containing an additional `oauth_token: ghp_…` passes validation. Interleaved NUL bytes evade the key/prefix checks. The entire directory is then mounted, exposing the recoverable full-access token; scanning covers only the selected PAT. **Fix:** require a canonical encoding without NULs and validate an allowed configuration schema before mounting. Add UTF-16/UTF-32 rejection cases.

2. **MEDIUM — Publication revalidation reads an unbound baseline.** [grading.py:126](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d7/autoresearch/experiments/rp-d7-prompt-delivery/grading.py:126): Recomputed publication facts depend on `baseline.json`, but the evidence manifest covers only `run`, `cell`, `tmp`, and `home`. Changing `allocation_sha` after grading to the archived main commit can make a previously non-baseline ref appear clean and permit a skip finding when no command witness or PR remains. The bound grade and manifest remain unchanged. **Fix:** bind the baseline digest into the grade/record and verify it before recomputation; missing baseline must remain unknown, and mutations must fail. Add a baseline-mutation regression case.

The other five fixes check out: exact `CLAUDE.md` binding, classification order, combinable `none`, unresolved false completion, and prediction uncertainty. Existing scan-before-seal and token-free launcher arguments remain connected.

Static inspection only; no files changed or tests/live operations run.

VERDICT: REVISE
