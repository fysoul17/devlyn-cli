You are reviewing an experiment design in the devlyn-cli repository (read-only review; do not edit files).

Read:
- autoresearch/experiments/rp-d7-prompt-delivery/DESIGN.md (the draft under review)
- autoresearch/experiments/rp-d6-claude-delivery/DESIGN.md and results.md (the previous experiment it follows)
- autoresearch/experiments/rp-d6-claude-delivery/results/measured/summary.md if present
- autoresearch/experiments/rp-d1-delivery-cost/common.txt (the benchmark prompt being ablated)
- CLAUDE.md (project principles: no guesswork, no overengineering, falsifiable prediction before the experiment)

Context: devlyn-cli's managed instruction block tells the engine to deliver completed, verified requests by project policy (default PR and merge). In rp-d6, Claude Opus 5.5 at effort high skipped that default delivery in 2/4 slots on the released 4.2.22, and the reports cited (1) the publication not being requested, (2) the benchmark prompt's Git-metadata sentence, (3) the benchmark prompt's allowed-paths sentence. rp-d7 removes the two benchmark sentences (P1) and measures Claude high's delivery on 4 slots of the unchanged product. The owner chose this cheap next step: 4 slots, product unchanged.

Review for: (a) whether P1 is an exact, minimal, correctly specified ablation of the two sentences (check the byte-level replacements against common.txt); (b) whether the decision rules are complete, ordered, unambiguous and match the question; (c) whether the prediction is falsifiable and frozen properly; (d) whether the skip/quality/other classes and reason tags are well-defined and gradeable from evidence; (e) whether dropping guards, Codex and a contemporaneous P0 control is justified for a routing screen, or whether something essential is missing; (f) overclaims in the interpretation; (g) anything that would make the result uninterpretable. Keep the scope small: the owner explicitly chose 4 slots and no product change; do not propose expanding the experiment unless the result would otherwise be uninterpretable.

Report findings as a numbered list with severity HIGH / MEDIUM / LOW, each with the exact text to change and a concrete fix. End with exactly one final line: `VERDICT: SHIP` or `VERDICT: REVISE`.
