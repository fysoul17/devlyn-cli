1. **MEDIUM — F10 attribution omits a material assessor inconsistency.**

   **Exact text:** “It accounts for the one Holm-rejected test (F10)” ([diagnosis L11](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0257-diagnosis/autoresearch/experiments/0257/results/claude-diagnosis.md:11)).

   **Evidence:** All eight Claude A handlers return `field: 'body'` for parser-rejected JSON `null`, yet their Codex assessments report complete with no findings. All eight Claude B assessments reject that input using a requirement for `field: 'name'`. See the [c001 handler](/Users/aipalm/.local/share/nx01/0257-live/output/c001-F10-claude-A-r1/snapshot/server/index.js:115), [c001 assessment](/Users/aipalm/.local/share/nx01/0257-live/output/c001-F10-claude-A-r1/assessment/codex/stdout:3), and [c002 assessment](/Users/aipalm/.local/share/nx01/0257-live/output/c002-F10-claude-B-r1/assessment/codex/stdout:3). Neither arm satisfies the exact response criterion stated against B. This direct inconsistency is missing from the assessment note and supports uneven grading as a competing explanation for the completion gap.

   **Fix:** Add the direct Claude A comparison to the assessment note. Replace “accounts for” with “tracks,” distinguishing the verified handler/probe difference from attribution of the completion gap.

VERDICT: REVISE
