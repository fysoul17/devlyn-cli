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
