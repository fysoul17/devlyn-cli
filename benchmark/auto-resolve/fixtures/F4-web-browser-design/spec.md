---
id: "F4-web-browser-design"
title: "Add a Whisper button with italic lowercase output"
status: planned
complexity: medium
depends-on: []
---

# F4 Add Whisper button

## Context

`web/index.html` currently has one button ("Greet") that fills `#output`
with `Hello from bench-test-repo`. Add a second button beside it labelled
`Whisper` that fills `#output` with `hello from bench-test-repo` — lowercase
and italicized — using only the page's own CSS/JS.

## Requirements

- [ ] A new `<button id="whisper">Whisper</button>` renders beside the existing `#greet` button.
- [ ] Clicking `#whisper` sets `#output` textContent to `hello from bench-test-repo` (lowercase, no exclamation).
- [ ] `#output`'s rendering of the whisper text is italic. Use CSS (inline, a class, or toggling a class). Do not rely on Unicode italic characters.
- [ ] Clicking `#greet` continues to set `#output` to `Hello from bench-test-repo` as before (no italic styling).
- [ ] A text node in `#output` is readable by Playwright via `data-testid="output"` (already present in the baseline).
- [ ] Minimal diff: only `web/index.html` and any new files directly needed for the test harness (e.g., `tests/e2e/whisper.spec.js` per the existing Playwright config).

## Constraints

- **No new npm dependencies.** Playwright is already scripted via `npx serve` and the repo's `playwright.config.js`.
- **No external resources.** Don't link to CDN fonts, external CSS, or remote images.
- **No inline JS frameworks.** Stick to the vanilla pattern already in `index.html`.
- **Accessibility.** Both buttons must have accessible names equal to their visible labels; `#whisper` adds `aria-label="whisper"` only if its visible text differs (it doesn't, so leave it off).

## Out of Scope

- Animations / transitions.
- Theme toggle / dark mode.
- Any change to `bin/cli.js`, `server/`, or CLI tests.
- Moving styles into a separate .css file.

## Verification

- Page loads: `npx serve -l 5173 web &` + `curl -s http://127.0.0.1:5173/` returns HTML containing `<button id="whisper"`.
- Clicking whisper produces `hello from bench-test-repo` in `#output` — verifiable via Playwright:
  `npx playwright test tests/e2e/` passes the whisper spec.
- Clicking greet still produces `Hello from bench-test-repo` (test stays green).
- `git diff --stat` shows only `web/index.html` and the added Playwright test file.
