1. **HIGH — A complete refusal can be discarded before scanning.** [smoke.py:348](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d4/autoresearch/experiments/rp-d4-helper-report/smoke.py:348) unwraps the first recognized field and drops its siblings. For `text({text:"delivery", result: await tools.exec_command(...)})`, a receipt-bound refusal inside `result.output` disappears. Reproduced: refusal followed by success returns only `COMPLETE` and `merge_refused=False`. Scan all output fields before unwrapping transport fragments.

2. **HIGH — Split refusals disappear under variable or batched polling.** [smoke.py:377](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d4/autoresearch/experiments/rp-d4-helper-report/smoke.py:377) starts a separate stream when continuation ownership is unresolved or multiple. A refusal split across execution and `write_stdin({session_id: session})` is lost; literal batched polling also reproduces it. Later success yields `merge_refused=False`. Literal single-session polling correctly retains the same refusal. Reconstruct these continuations or fail closed on unreconstructable helper evidence.

Both failures bypass DESIGN’s mandatory **INCONCLUSIVE** outcome.

Validation: 103 receipt/carrier/inspection cases and seven unreadable-transcript checks passed. Targeted observer, smoke qualification, and decision checks passed. No files changed; file-backed suites were not run under the read-only restriction.

VERDICT: REVISE
