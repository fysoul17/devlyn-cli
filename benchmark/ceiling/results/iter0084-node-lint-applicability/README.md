# iter-0084 evidence

This directory preserves the post-edit evidence for the frozen Node lint
applicability bar.

- `replay/`: 12 valid Sonnet 5 receipts, deterministic summary, before/after
  input hashes, and four disclosed missing-case operator artifacts excluded
  before scoring.
- `build_gate.lint-skills.*`: the authoritative full-skill-lint receipt and
  140-line raw log (`exit_code: 0`, `All checks passed`).
- `formal-verify/`: Codex primary judge, Fable 5 pair judge, empty findings
  carriers, and the merged PASS summary.
- `grok-replay-review.*`: Grok 4.5's independent 12-receipt review. The final
  structured result is PASS with zero discrepancies; the raw stdout also
  preserves its concatenated interim JSON emission.

Key SHA-256 values:

| Artifact | SHA-256 |
|---|---|
| `replay/summary.json` | `0c7139a1cd533224342d04cd83c7136a2252b34fb7647aa66b24b0c34bc9b7f5` |
| `build_gate.lint-skills.log` | `94ab1d892544bc0ceb67c7d16d58ee123e28ac0de884d7ae493c20e7a10263cd` |
| `formal-verify/codex-primary-judge.stdout` | `93095f92823e7d46b7ef1480356c77493010c3730adff4c4143863d9101dcc07` |
| `formal-verify/claude-judge.stdout` | `1bdefc6d5fc0ba7a8fb39c08dbe688e4414e8e6063a12a887f0eae08ac382132` |
| `formal-verify/verify-merge.summary.json` | `f47450f8a3ce380cb9ef67048d37ba49dcea5412dd93fb61ac00fa1f03ca8a40` |
| `grok-replay-review.stdout` | `a166f797decba1eb5a6e4483df1614def17c93f44af3089aff1fbc30e9ef4d20` |

Claim boundary: this proves only the four frozen treatment/control shapes and
the removal of the observed F7 false-lint trigger. It does not prove whole-
cohort wall improvement, broad project generality, or the deferred M1.5
deterministic runner.
