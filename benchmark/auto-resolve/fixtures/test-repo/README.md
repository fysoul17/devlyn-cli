# bench-test-repo

Deterministic base Node project used by every devlyn-cli auto-resolve
benchmark fixture. Fixtures extend this skeleton via `setup.sh` patches.

## What's in it

- `bin/cli.js` — tiny CLI (`hello`, `version`)
- `server/index.js` — tiny Express app (`/health`, `/items`, `/items/:id`)
- `web/index.html` — minimal static page with a click interaction
- `tests/cli.test.js`, `tests/server.test.js` — node:test fixtures
- `playwright.config.js` — used by web/browser fixtures only
- `package.json` — `express` dep, `engines: node >= 18`

## How it's used

`run-fixture.sh` copies this directory to a temp path per run, applies the
fixture's `setup.sh`, then invokes the arm (variant or bare) against that
copy. No fixture modifies this source tree — modifications happen only in
the per-run temp copies.

## Keep it minimal

Adding features to `test-repo` enlarges the surface every fixture works
against. Add only when an existing fixture can't express itself against the
current baseline. Preferred path: push complexity into the fixture's
`setup.sh`, not into this base.
