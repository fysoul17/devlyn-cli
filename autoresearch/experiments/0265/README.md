# 0265 — bare vs the installed harness (`devlyn run`, 4.3.30)

[`DESIGN.md`](DESIGN.md) is the design: DRAFT r2 (2026-11-11), not frozen, nothing run. It measures, per engine
(Claude Opus 5.5; GPT Astra through Codex), what `devlyn run` with the published `devlyn-cli@4.3.30` adds over the
same session started raw, on 0233's tasks in 0257's shape and grading, and reads two frozen lines per engine:
completion (0257's D) and harm. [`audit-rule.md`](audit-rule.md) is the audit rule for false completion, scope and
user-data harm; the pre-SMOKE calibration may revise it, and registration pins its sha256.

No apparatus exists yet; the design's "Apparatus work list" says what is copied from 0257 and what changes. The freeze
waits for the 4.3.30 publish, the Astra ultra and Grok 4.7 design review, the owner's answers, the pre-SMOKE audit
calibration and the checked predictions.
