---
name: devlyn:browser-validate
description: Browser-based validation for web applications — smoke tests, user flow testing, visual checks, and runtime error detection. Starts the dev server, navigates the app, and reports what's broken with screenshot evidence. Use this skill whenever the user says "test in browser", "check if it works", "smoke test", "browser test", "validate the UI", "does the app run", or when auto-resolve needs to verify web changes actually render and function correctly. Also use proactively after implementing UI changes to catch runtime errors that static analysis misses.
---

Browser validation for web applications. Starts a dev server, tests in a real browser (or falls back to Playwright/curl), and reports findings with evidence. Designed to catch the bugs that pass every static check but break when a user actually clicks something — runtime errors, failed API calls, blank pages, broken interactions.

<config>
$ARGUMENTS
</config>

<workflow>

## PHASE 1: DETECT

1. **Framework detection**: Read `package.json` → identify framework from dependencies (`next`, `vite`, `react-scripts`, `nuxt`, `astro`, `svelte`, `remix`, `angular`). Find the start command from `scripts.dev`, `scripts.start`, or `scripts.preview`.

2. **Port inference**: Check framework config files for custom ports. Defaults — Next.js: 3000, Vite: 5173, CRA: 3000, Nuxt: 3000, Astro: 4321, Angular: 4200. Override with `--port` flag if provided.

3. **Affected routes**: Run `git diff --name-only` and map changed files to routes (e.g., `app/dashboard/page.tsx` → `/dashboard`, `src/pages/about.vue` → `/about`). These are the pages that need testing.

4. **Tier selection** — pick the best available browser tool:
   - Check if `mcp__claude-in-chrome__*` tools exist in available tools → **Tier 1** (Chrome DevTools). Read `references/tier1-chrome.md`.
   - Else check if `mcp__playwright__*` tools exist (Playwright MCP installed via `npx devlyn-cli`) OR run `npx playwright --version 2>/dev/null` → **Tier 2** (Playwright). Read `references/tier2-playwright.md`.
   - Else → **Tier 3** (HTTP smoke). Read `references/tier3-curl.md`.

5. **Skip gate**: If no web-relevant files changed (no `*.tsx`, `*.jsx`, `*.vue`, `*.svelte`, `*.astro`, `*.css`, `*.scss`, `*.html`, `page.*`, `layout.*`, `route.*`, `+page.*`, `+layout.*`), skip the entire phase. Report: "Browser validation skipped — no web changes detected."

6. **Parse flags** from `<config>`:
   - `--skip-flow` — skip flow testing, only run smoke + visual
   - `--port PORT` — override detected port
   - `--tier N` — force a specific tier (1, 2, or 3)
   - `--mobile-only` — only test mobile viewport
   - `--desktop-only` — only test desktop viewport

Announce:
```
Browser validation starting
Framework: [detected] | Port: [PORT] | Tier: [N — name]
Affected routes: [list]
Phases: Smoke → [Flow] → Visual → Report
```

## PHASE 2: SERVER

1. Start the dev server in background: run the detected start command via Bash with `run_in_background: true`.
2. Health-check loop: poll `http://localhost:PORT` every 2 seconds using `curl -s -o /dev/null -w "%{http_code}"`. Timeout after 20 seconds.
3. If the server fails to start, capture stderr output and report as BLOCKED:
   ```
   Verdict: BLOCKED
   Reason: Dev server failed to start within 20s
   Error: [stderr output]
   ```
   Write this to `.claude/BROWSER-RESULTS.md` and stop.
4. Record the server PID for cleanup.

## PHASE 3: SMOKE

Test that the app renders and the runtime is clean. Follow the tier-specific reference file for exact tool calls.

For each affected route (and always `/` as the first):
1. Navigate to the page
2. Verify the page has meaningful content (not a blank page, not a raw error)
3. Capture console messages — filter for errors (ignore React dev-mode warnings, HMR noise, favicon 404s)
4. Capture network requests — flag any 4xx/5xx responses or CORS failures (ignore HMR websocket, source maps)
5. Take a screenshot as evidence

A route **fails smoke** if: the page is blank, shows an unhandled error, has console errors (excluding known dev noise), or has failed network requests to the app's own API.

## PHASE 4: FLOW (conditional)

Skip if `--skip-flow` is set or if `.claude/done-criteria.md` doesn't exist.

Read `references/flow-testing.md` for how to convert done-criteria into browser test steps. Then execute each test step using the tier-specific tools.

For each flow test:
1. Execute the action sequence (navigate → find → interact → verify)
2. After each interaction, check console + network for new errors
3. Screenshot at each verification point
4. Record pass/fail with evidence

## PHASE 5: VISUAL

Test layout integrity at two viewports (skip one if `--mobile-only` or `--desktop-only` is set):

1. **Mobile** (375x812): resize → navigate to each affected route → screenshot → check for overflow, overlapping elements, unreadable text
2. **Desktop** (1280x800): resize → navigate to each affected route → screenshot → check for broken layouts, missing sections

This is judgment-based — the agent looks at screenshots and reports visible issues. Not pixel-diff.

## PHASE 6: REPORT

Write `.claude/BROWSER-RESULTS.md`:

```markdown
# Browser Validation Results

## Verdict: [PASS / PASS WITH ISSUES / NEEDS WORK / BLOCKED]
Verdict rules: BLOCKED = app won't start or root page crashes. NEEDS WORK = flow tests fail or console errors on affected routes. PASS WITH ISSUES = visual issues or minor warnings. PASS = clean across all checks.

## Environment
- Framework: [detected]
- Dev server: [command] on port [PORT]
- Browser tier: [1/2/3 — name]
- Startup time: [N]s

## Smoke Test
| Route | Renders | Console Errors | Network Failures | Screenshot |
|-------|---------|---------------|-----------------|------------|
| / | YES/NO | [count]: [details] | [count]: [details] | [path] |

## Flow Tests
| Criterion | Steps | Result | Evidence |
|-----------|-------|--------|----------|
| [text] | [N] | PASS/FAIL | [screenshot, errors] |

## Visual Check
| Viewport | Route | Issues |
|----------|-------|--------|
| Mobile (375px) | / | [issues or "Clean"] |
| Desktop (1280px) | / | [issues or "Clean"] |

## Runtime Errors (full log)
[all unique console errors, deduplicated]

## Failed Network Requests
[all failed requests with URL, status, and context]
```

## PHASE 7: CLEANUP

Kill the dev server process using the stored PID. If running inside auto-resolve pipeline and the `--keep-server` flag was passed (set by the pipeline orchestrator), skip cleanup — the pipeline will handle it.

</workflow>
