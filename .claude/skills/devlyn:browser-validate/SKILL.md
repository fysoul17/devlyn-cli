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

The goal is to get the dev server running. If it doesn't start on the first try, diagnose and fix — don't just report failure. Browser validation is only useful when there's a running app to test.

1. Start the dev server in background: run the detected start command via Bash with `run_in_background: true`.
2. **Health-check loop**: Poll `http://localhost:PORT` every 2 seconds using `curl -s -o /dev/null -w "%{http_code}"`. Timeout after 30 seconds. The server is ready when you get an HTTP response (200, 301, 302, 304).
3. **If it doesn't come up — troubleshoot** (up to 2 attempts):
   - Read the server's stderr/stdout for the actual error (missing dependency, port conflict, env var, syntax error, build failure)
   - Fix the root cause: `npm install` for missing deps, kill the conflicting process on the port, fix the build error, etc.
   - Restart the server and health-check again
   - If it still fails after 2 fix attempts, write BLOCKED verdict with what you tried and what the underlying error is, then stop.
4. Record the server PID for cleanup.

## PHASE 3: SMOKE

Test that the app actually renders your application — not just "a page."

Here's the trap to avoid: when a server is down, misconfigured, or a route is broken, the browser still shows *something* — a connection error page, a framework error overlay, a blank shell. These pages have text, layout, even interactive elements like "Retry" buttons. If you only check "did the page render something?", you'll report PASS on a completely broken app. The question isn't "is there content on screen?" — it's "is this *my application's* content?"

For each affected route (and always `/` as the first):
1. Navigate to the page
2. Read the page content and judge: **is this the actual application, or an error/fallback page?**
3. Capture console messages — filter for errors (ignore dev-mode noise like HMR, Fast Refresh, favicon 404s)
4. Capture network requests — flag failed API calls (4xx/5xx, CORS errors). Ignore dev tooling requests.
5. Take a screenshot as evidence

**If a route is broken — try to fix it.** Read the console errors or the error overlay to understand what went wrong. Common issues: missing import, undefined variable, failed API call due to missing env var, hydration mismatch. Fix the root cause in the source code, let the dev server hot-reload, then re-test the route. Attempt up to 2 fixes per route before marking it as failed.

If the root route (`/`) is broken and you can't fix it, the verdict is BLOCKED.

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
Verdict rules:
- BLOCKED = server didn't start, or any page shows an error/fallback instead of real application content
- NEEDS WORK = flow tests fail or console errors on affected routes
- PASS WITH ISSUES = visual issues or minor warnings only
- PASS = all pages render real application content, zero runtime errors

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
