codex
- **HIGH — [runner.py:28](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d3/autoresearch/experiments/rp-d3-prompt-ablation/runner.py:28): Secret-scan finding remains open.** An accepted Unicode-escaped OAuth snapshot, printed through Codex’s normal JSON `aggregated_output` envelope, matches neither decoded tokens nor raw snapshot bytes. The actual scanner accepted this synthetic evidence without markers; decoding recovered every credential. The new regression tests only the unwrapped dump. Cover the actual transport and reject or detect it.

- **MEDIUM — [stage.py:47](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d3/autoresearch/experiments/rp-d3-prompt-ablation/stage.py:47): Runtime aliases bypass stage-root isolation.** An external symlink or copy of the runtime permits renewal to `original-stage/private-auth`: the guard checks the supplied runtime’s parent. `--check` repeats this at line 71. An in-memory renewal probe confirmed acceptance. Bind the guard to the original stage and test runtime aliases.

OAuth-only/competing-credential and MIXED/no-follow-up fixes passed targeted probes. Two existing pytest tests passed; full-suite results remain operator-reported. The remaining gaps violate **Production ready**.

VERDICT: REVISE
