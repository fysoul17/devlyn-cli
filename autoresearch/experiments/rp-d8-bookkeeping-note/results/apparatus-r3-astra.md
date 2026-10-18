# apparatus-r3 — astra

1. **MEDIUM — [capture.py:223](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d8/autoresearch/experiments/rp-d8-bookkeeping-note/capture.py:223): abbreviated value options can hide real pushes.** `git push --push-opt -un origin HEAD` consumes `-un` as the `--push-option` value, per [Git’s option parser](https://github.com/git/git/blob/v2.52.0/parse-options.c#L484-L553) and [push option definitions](https://github.com/git/git/blob/v2.52.0/builtin/push.c#L520-L560). The new scanner skips only exact option names, then mistakes that value for dry-run switches. A sealed successful push consequently leaves `pushed=None` and `push_command_unresolved=False`; the parent retained `pushed=True`.

   **Fix:** recognize unambiguous prefixes of value-taking push options and consume their values before detecting dry-run switches. Leave `flags()` unchanged. Add capture and grading regressions for this command expecting successful-push evidence.

The explicitly requested A1/G2 cases and G1 behavior otherwise check out. Static review only; no files edited, tests run, or live operations performed.

VERDICT: REVISE
