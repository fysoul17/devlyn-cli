# Tier 2: Playwright (Headless Browser)

Solid middle-ground tier. No browser extension needed — works in CI, SSH, Docker, and headless environments. Provides DOM interaction, console monitoring, screenshots, and network inspection. No GIF recording.

Read this file only when Tier 2 was selected during DETECT phase.

---

## Two Modes

Playwright Tier 2 has two sub-modes depending on what's available. The skill auto-detects which to use.

### Mode A: Playwright MCP (preferred)

If `mcp__playwright__*` tools are available (installed via `npx devlyn-cli` → select "playwright" MCP), use them directly. This gives interactive browser control similar to Tier 1:

- `mcp__playwright__browser_navigate` — navigate to URL
- `mcp__playwright__browser_screenshot` — capture screenshot
- `mcp__playwright__browser_click` — click elements
- `mcp__playwright__browser_type` — type into inputs
- `mcp__playwright__browser_console` — read console messages
- `mcp__playwright__browser_network` — read network requests
- `mcp__playwright__browser_resize` — resize viewport

When Playwright MCP is available, follow the same interaction pattern as Tier 1 (navigate → check → interact → screenshot) but using `mcp__playwright__*` tools instead of `mcp__claude-in-chrome__*`.

Load tools via ToolSearch before use: `ToolSearch: "select:mcp__playwright__browser_navigate"` etc.

### Mode B: Script Generation (fallback)

If Playwright MCP is not installed but `npx playwright` CLI is available, generate and execute test scripts. This is the approach documented below.

## Setup (Mode B only)

Playwright runs via `npx` with auto-download. No global install needed. If browsers aren't installed yet:
```bash
npx playwright install chromium 2>/dev/null
```
This downloads only Chromium (~130MB), not all browsers. It's a one-time cost.

## Approach (Mode B)

Generate a temporary test script from the test steps, run it with Playwright's JSON reporter, then parse the results. This avoids needing a persistent test infrastructure — the script is created, executed, and cleaned up.

## Script Generation

For each phase (smoke, flow, visual), generate a test script at `.claude/browser-test.spec.ts`.

### Smoke Test Script Template

```typescript
import { test, expect } from '@playwright/test';

const PORT = {PORT};
const ROUTES = {ROUTES_JSON_ARRAY};

test.describe('Smoke Tests', () => {
  for (const route of ROUTES) {
    test(`smoke: ${route}`, async ({ page }) => {
      const errors: string[] = [];
      const failedRequests: string[] = [];

      page.on('console', msg => {
        if (msg.type() === 'error') errors.push(msg.text());
      });

      page.on('response', response => {
        if (response.status() >= 400 && !response.url().includes('favicon')) {
          failedRequests.push(`${response.status()} ${response.url()}`);
        }
      });

      await page.goto(`http://localhost:${PORT}${route}`, { waitUntil: 'networkidle', timeout: 15000 });

      const bodyText = await page.textContent('body');
      expect(bodyText?.trim().length).toBeGreaterThan(0);

      await page.screenshot({ path: `.claude/screenshots/smoke${route.replace(/\//g, '-') || '-root'}.png`, fullPage: true });

      if (errors.length > 0) {
        test.info().annotations.push({ type: 'console_errors', description: errors.join(' | ') });
      }
      if (failedRequests.length > 0) {
        test.info().annotations.push({ type: 'network_failures', description: failedRequests.join(' | ') });
      }

      expect(errors.filter(e => !e.includes('[HMR]') && !e.includes('favicon'))).toHaveLength(0);
      expect(failedRequests).toHaveLength(0);
    });
  }
});
```

### Flow Test Script Template

For each flow test step from done-criteria, generate a test block:

```typescript
test('flow: [criterion description]', async ({ page }) => {
  // Navigate
  await page.goto(`http://localhost:${PORT}{start_route}`);

  // Find and interact
  await page.click('[text or selector]');
  await page.fill('[selector]', '[value]');
  await page.click('[submit selector]');

  // Verify
  await expect(page.locator('[verification selector]')).toBeVisible();

  // Screenshot
  await page.screenshot({ path: '.claude/screenshots/flow-[name].png' });
});
```

### Visual Test Script Template

```typescript
test.describe('Visual - Mobile', () => {
  test.use({ viewport: { width: 375, height: 812 } });
  for (const route of ROUTES) {
    test(`visual-mobile: ${route}`, async ({ page }) => {
      await page.goto(`http://localhost:${PORT}${route}`, { waitUntil: 'networkidle' });
      await page.screenshot({ path: `.claude/screenshots/visual-mobile${route.replace(/\//g, '-') || '-root'}.png`, fullPage: true });
    });
  }
});

test.describe('Visual - Desktop', () => {
  test.use({ viewport: { width: 1280, height: 800 } });
  for (const route of ROUTES) {
    test(`visual-desktop: ${route}`, async ({ page }) => {
      await page.goto(`http://localhost:${PORT}${route}`, { waitUntil: 'networkidle' });
      await page.screenshot({ path: `.claude/screenshots/visual-desktop${route.replace(/\//g, '-') || '-root'}.png`, fullPage: true });
    });
  }
});
```

## Execution

```bash
mkdir -p .claude/screenshots
npx playwright test .claude/browser-test.spec.ts \
  --reporter=json \
  --output=.claude/playwright-results \
  2>&1 | tee .claude/playwright-output.json
```

## Parsing Results

Read `.claude/playwright-output.json`. The JSON structure contains:
- `suites[].specs[].tests[].results[].status` — `"passed"`, `"failed"`, `"timedOut"`
- `suites[].specs[].tests[].results[].errors` — error messages with stack traces
- `suites[].specs[].tests[].annotations` — custom annotations (console_errors, network_failures)

Map these to BROWSER-RESULTS.md findings:
- `failed` → route fails smoke, include error message
- Annotations with `console_errors` → list in Runtime Errors section
- Annotations with `network_failures` → list in Failed Network Requests section

## Cleanup

After parsing results:
```bash
rm -f .claude/browser-test.spec.ts
rm -rf .claude/playwright-results
rm -f .claude/playwright-output.json
```

Keep `.claude/screenshots/` — those are evidence referenced by the report.

## Limitations vs Tier 1

- No GIF recording (can't capture multi-step flow animations)
- No live DOM exploration (tests are scripted, not interactive)
- Screenshots are full-page captures, not viewport-specific (use `fullPage: true`)
- Console filtering is code-based (less flexible than chrome MCP pattern matching)
