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

For each phase (smoke, flow, visual), generate a test script at `.devlyn/browser-test.spec.ts`.

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

      // If goto throws (connection refused), the test fails — that's correct behavior
      await page.goto(`http://localhost:${PORT}${route}`, { waitUntil: 'networkidle', timeout: 15000 });

      // Verify this is the actual application, not an error page.
      // When a server is down or a route is broken, the browser shows an error page
      // that still has text content — "Unable to connect", "This site can't be reached", etc.
      // A naive length check would pass on these. The title is the best signal:
      // browser error pages have titles like "Problem loading page" or the URL itself,
      // while real apps have meaningful titles set by the application.
      const title = await page.title();
      const bodyText = await page.textContent('body') || '';

      // Page must have substantive content
      expect(bodyText.trim().length, 'Page body is empty').toBeGreaterThan(0);

      // Fail if the page navigation itself failed (Playwright sets title to the URL on error)
      const pageUrl = page.url();
      expect(title, 'Page shows a browser error — server may be down').not.toBe(pageUrl);

      await page.screenshot({ path: `${SCREENSHOT_DIR}/smoke/${route.replace(/^\//, '').replace(/\//g, '-') || 'root'}.png`, fullPage: true });
      // SCREENSHOT_DIR is the topic-scoped dir set up in PHASE 1 of SKILL.md
      // (e.g., .devlyn/screenshots/add-login-page). Inject it at test-generation
      // time so every test writes into the same per-run folder.

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
  await page.screenshot({ path: `${SCREENSHOT_DIR}/feature/[criterion-slug]-step[N].png` });
});
```

### Visual Test Script Template

```typescript
test.describe('Visual - Mobile', () => {
  test.use({ viewport: { width: 375, height: 812 } });
  for (const route of ROUTES) {
    test(`visual-mobile: ${route}`, async ({ page }) => {
      await page.goto(`http://localhost:${PORT}${route}`, { waitUntil: 'networkidle' });
      await page.screenshot({ path: `${SCREENSHOT_DIR}/visual/mobile-${route.replace(/^\//, '').replace(/\//g, '-') || 'root'}.png`, fullPage: true });
    });
  }
});

test.describe('Visual - Desktop', () => {
  test.use({ viewport: { width: 1280, height: 800 } });
  for (const route of ROUTES) {
    test(`visual-desktop: ${route}`, async ({ page }) => {
      await page.goto(`http://localhost:${PORT}${route}`, { waitUntil: 'networkidle' });
      await page.screenshot({ path: `${SCREENSHOT_DIR}/visual/desktop-${route.replace(/^\//, '').replace(/\//g, '-') || 'root'}.png`, fullPage: true });
    });
  }
});
```

## Execution

```bash
mkdir -p "$SCREENSHOT_DIR"/{smoke,feature,visual}
npx playwright test .devlyn/browser-test.spec.ts \
  --reporter=json \
  --output=.devlyn/playwright-results \
  2>&1 | tee .devlyn/playwright-output.json
```

## Parsing Results

Read `.devlyn/playwright-output.json`. The JSON structure contains:
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
rm -f .devlyn/browser-test.spec.ts
rm -rf .devlyn/playwright-results
rm -f .devlyn/playwright-output.json
```

Keep `$SCREENSHOT_DIR` (`.devlyn/screenshots/<topic-slug>/`) — those are evidence referenced by the report. Don't touch other topics' directories.

## Limitations vs Tier 1

- No GIF recording (can't capture multi-step flow animations)
- No live DOM exploration (tests are scripted, not interactive)
- Screenshots are full-page captures, not viewport-specific (use `fullPage: true`)
- Console filtering is code-based (less flexible than chrome MCP pattern matching)
