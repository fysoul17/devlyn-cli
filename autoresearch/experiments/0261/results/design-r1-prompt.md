Read-only design review for devlyn-cli research experiment 0261. Do not edit any file.

The draft design is at /private/tmp/claude-501/-Users-aipalm-Documents-GitHub-devlyn-cli/39734701-88f7-45dd-bd5a-f5397ef89eed/scratchpad/0261-DESIGN-draft.md. It follows your round-0 answer to the design question (/private/tmp/claude-501/-Users-aipalm-Documents-GitHub-devlyn-cli/39734701-88f7-45dd-bd5a-f5397ef89eed/scratchpad/fc-design-r1.md; answers fc-r1-astra.raw and fc-r1-grok.raw in the same folder).

Its template is 0260 (repository /Users/aipalm/Documents/GitHub/devlyn-cli; read with `git show origin/main:autoresearch/experiments/0260/DESIGN.md`, `.../0260/registration.md`, `.../0260/README.md`, and the apparatus files there; 0257's D4 grading in `.../0257/RESULT.md` and `.../0257/DESIGN.md`). The checkout itself is behind origin/main. Archived reports and trees: /Users/aipalm/.local/share/nx01/archive/reports-0256-0260/.

Check:
1. Does the design answer the owner's goal (fewer Claude false completions) and the owner's harness-ladder rule (instruction-only, one change, keep only if nothing measured worsens; tokens must not increase)? Is G3 a fair reading of "tokens must not increase" given the measured per-cell variation, or should it be different?
2. Endpoint validity: is the explicit m24 line, the pooled one-sided Fisher on false-completion cells, and the wording-blind witness guard (G1) sound? Can a vaguer report win? Is the blind-audit procedure workable and sufficient?
3. Feasibility: D4 replacing D3 in 0260's apparatus; rebuilding B's control root and seal without 0256–0260's deleted runtime roots, verified against recorded identities; witness qualification on archived trees without node_modules.
4. The sentence's wording and placement.
5. Anything that would make the result uninterpretable or that contradicts the cited evidence.

Report findings as HIGH / MEDIUM / LOW with a concrete fix each, under 700 words. End with exactly one line: `VERDICT: SHIP` or `VERDICT: REVISE`.
