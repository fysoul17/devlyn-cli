---
name: devlyn:browser-validate
description: Browser-based validation for web applications — verifies that implemented features actually work by testing them in a real browser. Starts the dev server, tests the feature end-to-end (click buttons, fill forms, verify results), and reports what's broken with screenshot evidence. Use this skill whenever the user says "test in browser", "check if it works", "does the feature work", "browser test", "validate the UI", or when auto-resolve needs to verify web changes actually function correctly. Also use proactively after implementing UI changes. The primary goal is feature verification, not just checking if pages render.
---

Verify that implemented features actually work in the browser. The primary job is to test the feature that was just built — click the button, fill the form, check the result. Smoke tests and visual checks are supporting checks, not the main event.

The whole point of browser validation is to catch the gap between "code looks correct" and "user can actually do the thing." Static analysis and unit tests can confirm the code is well-structured. Browser validation confirms it *works*.

<config>
$ARGUMENTS
</config>

<workflow>

## PHASE 1: DETECT

1. **What was built**: This is the most important input. Read `.devlyn/done-criteria.md` if it exists — it tells you what the feature is supposed to do. If it doesn't exist, read `git diff --stat` and `git log -1` to understand what changed. You need to know what to test before anything else.

2. **Framework detection**: Read `package.json` → identify framework and start command from `scripts.dev`, `scripts.start`, or `scripts.preview`.

3. **Port inference**: Defaults — Next.js: 3000, Vite: 5173, CRA: 3000, Nuxt: 3000, Astro: 4321, Angular: 4200. Override with `--port` flag.

4. **Affected routes**: Map changed files to routes (e.g., `app/dashboard/page.tsx` → `/dashboard`).

5. **Tier selection** — pick the best available browser tool. **You must verify each tier actually works before committing to it** — tools can be registered but not connected:
   - **Tier 1 probe** (Chrome DevTools): Check if `mcp__claude-in-chrome__*` tools exist. If they do, load `mcp__claude-in-chrome__tabs_context_mcp` via ToolSearch and call it. If the call **succeeds** (returns tab data without error), use Tier 1. Read `references/tier1-chrome.md`. If the call **fails** (timeout, connection error, extension not running), Tier 1 is unavailable — fall through to Tier 2.
   - **Tier 2 probe** (Playwright): Check if `mcp__playwright__*` tools exist (try ToolSearch for `mcp__playwright__browser_navigate`). If they exist and respond, use Tier 2 Mode A. Else run `npx playwright --version 2>/dev/null` — if it succeeds, use Tier 2 Mode B. Read `references/tier2-playwright.md`.
   - **Tier 3** (HTTP smoke): Fallback when no browser tool is functional. Read `references/tier3-curl.md`.
   
   **Critical rule**: Never treat a tier as available just because its tools appear in the tool list. Deferred/registered tools may not have a running backend. Always probe before committing.

6. **Skip gate**: If no web-relevant files changed (no `*.tsx`, `*.jsx`, `*.vue`, `*.svelte`, `*.astro`, `*.css`, `*.scss`, `*.html`, `page.*`, `layout.*`, `route.*`, `+page.*`, `+layout.*`), skip. Report: "Browser validation skipped — no web changes detected."

7. **Parse flags** from `<config>`:
   - `--skip-feature` — skip feature testing, only run smoke + visual
   - `--port PORT` — override detected port
   - `--tier N` — force a specific tier (1, 2, or 3)
   - `--mobile-only` / `--desktop-only` — limit viewport testing
   - `--topic SLUG` — override the auto-derived screenshot topic slug

8. **Derive the screenshot topic slug**. All screenshots for this run go under `.devlyn/screenshots/<topic-slug>/` so runs for different features don't pile up together. Resolution order:
   1. `--topic` flag value, kebab-cased
   2. First non-blank heading/line of `.devlyn/done-criteria.md` (strip `#`, kebab-case, max 40 chars)
   3. Current git branch name, if not `main`/`master`/`HEAD`
   4. Fallback: `run-<YYYYMMDD-HHMM>`

   Then wipe and recreate the topic dir (fresh evidence per run; don't touch other topics' dirs):
   ```bash
   SCREENSHOT_DIR=".devlyn/screenshots/<topic-slug>"
   rm -rf "$SCREENSHOT_DIR"
   mkdir -p "$SCREENSHOT_DIR"/{smoke,feature,visual}
   ```

   Record `$SCREENSHOT_DIR` and reuse it through the run. All screenshot paths below are **relative to `$SCREENSHOT_DIR`**:
   - Smoke: `smoke/<route-slug>.png` (root → `smoke/root.png`)
   - Feature: `feature/<criterion-slug>-step<N>.png`
   - Visual: `visual/<viewport>-<route-slug>.png` (e.g., `visual/mobile-dashboard.png`)

Announce:
```
Browser validation starting
Feature: [what was built, from done-criteria or git diff]
Framework: [detected] | Port: [PORT] | Tier: [N — name]
Topic: [topic-slug] → .devlyn/screenshots/<topic-slug>/
Phases: Server → Smoke → Feature Test → Visual → Report
```

## PHASE 2: SERVER

Get the dev server running. If it doesn't start, diagnose and fix — don't just report failure.

1. Start the dev server in background via Bash with `run_in_background: true`.
2. Health-check: poll `http://localhost:PORT` every 2s, timeout 30s. Ready when you get an HTTP response.
3. **If it doesn't come up — troubleshoot** (up to 2 attempts): read stderr for the error, fix it (npm install, port conflict, build error, etc.), restart, re-check.
4. If still down after 2 attempts: write BLOCKED verdict and stop.

## PHASE 3: SMOKE (quick prerequisite)

Quick check that the app is alive. This is not the main test — it's a gate to make sure feature testing is even possible.

Navigate to `/` and each affected route. For each page, judge: is this the actual application, or an error page? A connection error, framework error overlay, or blank shell is not the app. If broken, try to fix (read console errors, fix source, let hot-reload pick it up). Up to 2 fix attempts per route.

**Tier downgrade on failure**: If you're on Tier 1 or Tier 2 Mode A and the browser tool consistently fails during smoke (connection errors, timeouts, extension disconnected), **do not skip browser testing**. Instead, downgrade to the next tier (Tier 1 → Tier 2 → Tier 3), re-read the corresponding reference file, and retry the smoke phase with the new tier. Announce: `"Tier [N] browser tools not responding — downgrading to Tier [N+1]."` The goal is to always run the best available browser test, not to give up.

If the app isn't rendering, the verdict is BLOCKED — feature testing can't happen.

## PHASE 4: FEATURE TEST (the main event)

This is the primary purpose of browser validation. Everything else is in service of getting here.

Read `.devlyn/done-criteria.md` (or infer from git diff what was built). For each criterion that describes something a user can do or see in the UI, test it end-to-end in the browser:

1. **Plan the test**: What would a user do to verify this feature works? Navigate where, click what, type what, expect what result?
2. **Execute it**: Navigate to the page, find the interactive elements, perform the actions, verify the outcome. Read `references/flow-testing.md` for patterns on converting criteria to browser steps.
3. **Capture evidence**: Screenshot at each key step. Record console errors and network failures that happen during the interaction.
4. **If it fails — try to fix**: Read the error (console, network, or the UI state) to understand why the feature broke. Fix the source code, let hot-reload update, and re-test. Up to 2 fix attempts per criterion.
5. **Record the result**: For each criterion — PASS (feature works as specified), FAIL (feature doesn't work, include what went wrong), SKIPPED (criterion isn't browser-testable, e.g., "API returns 401"), or UNVERIFIABLE (feature depends on external services not available in the test environment — e.g., real API keys, third-party auth, paid services).

**Don't churn on external dependencies.** If a feature test is blocked because an API times out, a third-party service isn't configured, or auth credentials aren't available — that's not a bug to fix, it's a test environment limitation. Note it as UNVERIFIABLE, move on to the next criterion. Don't spend more than 30 seconds waiting for a response that's never coming. The goal is to verify what *can* be verified in the current environment, and be honest about what can't.

The verdict depends primarily on this phase. If the implemented features don't work in the browser, the validation fails — even if every page renders perfectly and the layout looks great. And if most features couldn't be verified due to environment limitations, be honest about that — don't call it PASS.

## PHASE 5: VISUAL (supporting check)

Quick layout check at two viewports (skip if `--mobile-only` or `--desktop-only`):

1. **Mobile** (375x812): screenshot each affected route, check for overflow/overlap/unreadable text
2. **Desktop** (1280x800): screenshot each affected route, check for broken layouts

Judgment-based — look at the screenshots and report visible issues.

## PHASE 6: REPORT

Write `.devlyn/BROWSER-RESULTS.md`:

```markdown
# Browser Validation Results

## Verdict: [PASS / PASS WITH ISSUES / NEEDS WORK / PARTIALLY VERIFIED / BLOCKED]
Verdict rules:
- BLOCKED = server won't start or app doesn't render
- NEEDS WORK = implemented features don't work in the browser
- PARTIALLY VERIFIED = some features verified working, but others couldn't be tested due to environment limitations (missing API keys, external service dependencies). Be explicit about what was and wasn't verified.
- PASS WITH ISSUES = all testable features work but visual issues or minor warnings exist
- PASS = all testable features verified working, pages render, layout clean

## What Was Tested
[Brief description of the feature/task from done-criteria or git diff]

## Feature Verification (primary)
| Criterion | Test Steps | Result | Evidence |
|-----------|-----------|--------|----------|
| [what should work] | [what you did] | PASS/FAIL/SKIPPED/UNVERIFIABLE | [screenshot, errors, what went wrong] |

## Unverifiable Features (if any)
[List features that couldn't be tested and why — e.g., "Badge rendering requires /api/backends/status which needs real API keys not present in test env. Verified via source code and unit tests instead."]

## Smoke Test (prerequisite)
| Route | Renders | Console Errors | Network Failures |
|-------|---------|---------------|-----------------|
| / | YES/NO | [count] | [count] |

## Visual Check
| Viewport | Route | Issues |
|----------|-------|--------|
| Mobile (375px) | / | [issues or "Clean"] |
| Desktop (1280px) | / | [issues or "Clean"] |

## Fixes Applied During Validation
[List any bugs found and fixed during testing — server startup issues, broken routes, feature bugs]

## Runtime Errors
[Console errors captured during testing]

## Failed Network Requests
[Failed API calls captured during testing]
```

## PHASE 7: CLEANUP

Kill the dev server PID. If `--keep-server` was passed (auto-resolve pipeline), skip — the pipeline handles cleanup.

</workflow>
