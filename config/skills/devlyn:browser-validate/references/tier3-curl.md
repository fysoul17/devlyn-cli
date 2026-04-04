# Tier 3: HTTP Smoke (curl)

Bare-minimum fallback. No browser, no JavaScript execution, no interaction testing. This tier confirms the dev server responds and pages return valid HTML. It catches "app doesn't start" and "page returns 500" but nothing subtler.

Read this file only when Tier 3 was selected during DETECT phase.

---

## What You Can Test

- Server responds on the expected port
- Pages return HTTP 200
- HTML contains a `<body>` with content (not an empty shell)
- No server-side error indicators in the HTML

## What You Cannot Test

- Client-side rendering (SPA content won't appear in curl output)
- JavaScript errors or console output
- Network requests made by the client
- Interactive elements (forms, buttons, navigation)
- Visual layout or responsive behavior
- Screenshots

## Smoke Test

For each affected route:

```bash
# Check HTTP status
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:{PORT}{route} --max-time 10)

# Get HTML content
HTML=$(curl -s http://localhost:{PORT}{route} --max-time 10)
```

### Pass Criteria

A route passes if:
1. `STATUS` is `200` (or `304`)
2. HTML contains `<body` tag
3. HTML body has more than 100 characters of text content (not just empty divs)
4. HTML does not contain server error indicators: `Internal Server Error`, `500`, `ECONNREFUSED`, `Cannot GET`, `404`

### Parsing HTML Content

Since curl returns raw HTML (no JS execution), for SPAs the body may only contain a root `<div id="root"></div>` or `<div id="__next"></div>`. This is normal and counts as a PASS for Tier 3 — note it as "SPA shell detected, client-side rendering not verifiable at this tier."

For SSR frameworks (Next.js with server components, Nuxt, Astro), the HTML should contain actual rendered content.

## Report Adjustments

When writing BROWSER-RESULTS.md from Tier 3:
- Set confidence level to LOW
- Leave Console Errors, Network Failures, Flow Tests, and Visual Check sections as "N/A — Tier 3 (HTTP only)"
- Note the limitation: "Tier 3 testing provides HTTP-level validation only. Client-side behavior, JavaScript errors, and visual rendering were not tested. For comprehensive browser validation, install the claude-in-chrome extension (Tier 1) or Playwright (Tier 2)."
