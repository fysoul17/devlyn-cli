# Browser Auditor Prompt

Use this as the subagent prompt when spawning the browser-auditor in PHASE 2.

**Skip conditions** (check in order before spawning):
1. `--skip-browser` flag → skip
2. No web-relevant files in project (no `*.tsx`, `*.jsx`, `*.vue`, `*.svelte`, `*.html`, `page.*`, `layout.*`) → skip with note "Browser validation skipped — no web files detected"
3. Otherwise → spawn

---

You are performing browser-based verification of a web application against its planning commitments.

Read `.devlyn/commitment-registry.md` for the user-facing features that should be working.

**Your workflow:**
1. Read `.claude/skills/devlyn:browser-validate/SKILL.md` for the browser testing methodology and tier system
2. Start the dev server
3. For each user-facing FEATURE and BEHAVIOR commitment:
   - Navigate to the relevant page
   - Perform the user action described in the commitment
   - Verify the expected outcome
   - Take screenshots as evidence
4. Pay special attention to:
   - Error states: trigger errors and verify error UI appears
   - Empty states: verify empty state UI for lists/collections
   - Loading states: verify loading indicators during async operations
   - Edge cases explicitly mentioned in specs

Write findings to `.devlyn/audit-browser.md` with screenshot paths as evidence.

If browser tools are unavailable, fall back to HTTP smoke testing (curl endpoints, verify response codes and shapes). Note the reduced coverage in your findings.

## Principles emission (added iter-0019.A — narrow scope)

You MAY emit `principle.*` rule_ids on browser findings, but ONLY for two patterns and ONLY when runtime behavior proves them with screenshot or route evidence. Do NOT emit other `principle.*` rule_ids — those are code-auditor scope.

| Pattern observed in browser | rule_id | Evidence required |
|---|---|---|
| Error state silently shows fallback content (default value, blank, "0") instead of surfacing the error to the user | `principle.no-silent-fallback` (overlay on `BROKEN` HIGH) | Screenshot of the silently-fallback UI **AND** the route/URL where it occurred (both required) + how you triggered the error |
| Feature visibly works beyond what any commitment in the registry asked for (e.g. an extra panel, an out-of-scope export button) | `principle.goal-locked-drift` (overlay on `SCOPE_VIOLATION` HIGH) | Screenshot of the unrequested UI **AND** the URL/route (both required) + the commitments you checked the registry against |

Other principle violations (subtractive-first, unjustified duplicate machinery, hand-rolled stdlib, no-workaround) are NOT browser-observable — leave those to the code-auditor. `docs-auditor` does not emit `principle.*` at all.
