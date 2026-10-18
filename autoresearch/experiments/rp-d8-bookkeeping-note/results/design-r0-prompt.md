You are reviewing an experiment design in the devlyn-cli repository (read-only review; do not edit files).

Read:
- autoresearch/experiments/rp-d8-bookkeeping-note/DESIGN.md (the draft under review) and its design-round records in results/ (design-evidence.md, design-round-astra.md, design-round-grok.md, design-synthesis.json)
- autoresearch/experiments/rp-d6-claude-delivery/DESIGN.md and results.md, autoresearch/experiments/rp-d7-prompt-delivery/DESIGN.md and results.md (the experiments it follows and reuses)
- config/skills/_shared/task-completion.md (the file the candidate edits; check every quoted sentence, line number and deletion against it), CLAUDE.md/AGENTS.md (managed block), scripts/test-windows-portability.py, bin/skill-history.json and scripts/update-skill-history.js (shipping mechanics)
- CLAUDE.md principles: no guesswork, no overengineering, tokens never increase (harness ladder), falsifiable prediction frozen before the experiment.

Review for: (a) whether the candidate sentence and the four deletions are exact, correctly placed, genuinely redundant (no learned failure mode lost), and safe (cannot be read as overriding explicit delivery limits, write bans or the no-origin route; cannot lead to committing .devlyn/ or .gitignore changes); (b) whether the schedule, guards and their pass rules test what matters and are gradeable from sealed evidence; (c) whether the decision rules are complete, ordered, unambiguous, consistent with the prediction, and match rp-d6's structure where reused; (d) the token gate and shipped-path rules; (e) overclaims or missing interpretation limits; (f) anything that would make the result uninterpretable. Keep scope proportionate: do not propose expanding the experiment unless the result would otherwise be uninterpretable.

Report findings as a numbered list with severity HIGH / MEDIUM / LOW, each with the exact text to change and a concrete fix. End with exactly one final line: `VERDICT: SHIP` or `VERDICT: REVISE`.
