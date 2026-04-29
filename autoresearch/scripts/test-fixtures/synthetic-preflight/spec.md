---
id: "synthetic-preflight"
title: "Synthetic preflight smoke fixture"
status: planned
complexity: low
depends-on: []
---

# Synthetic preflight smoke

This is a minimal test fixture used by `autoresearch/scripts/pair-plan-preflight.sh --dry-run` to exercise the iter-0022 preflight pipeline end-to-end without calling real provider/model subprocesses.

## Requirements

- [ ] `synthetic.js` exports a function `greet(name)` that returns `Hello, <name>!`.
- [ ] `tests/synthetic.test.js` asserts `greet("world") === "Hello, world!"`.

## Constraints

- **No new npm dependencies.**
- **No silent catches.**

## Verification

- `node --test tests/synthetic.test.js` passes.
