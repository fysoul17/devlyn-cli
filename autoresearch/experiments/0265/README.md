# 0265 — bare vs the installed harness (`devlyn run`, 4.3.30), fast replay

[`DESIGN.md`](DESIGN.md) is the design: DRAFT r3 (2026-11-11), not frozen, no cell run. It measures, per engine
(Claude Opus 5.5; GPT Astra through Codex), what `devlyn run` with the published `devlyn-cli@4.3.30` adds over the
same session started raw, on 0233's tasks D3, D4, B5, F10 and F11, 8 replicates per arm (160 cells), in two lanes.
It reads whether 0257's two large signals replicate (codex B5, claude F10), then a completion line and a harm line
whose limits are printed with them. [`audit-rule.md`](audit-rule.md) is the rule the false-completion judges and the
mechanical harm check apply.

r2, the 328-cell powered design, is in this branch's history (`ffc7b97f`, `5fd9a2a0`); DESIGN.md says why r3 replaced
it.
