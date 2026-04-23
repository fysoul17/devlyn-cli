# F3 — Notes

## Purpose

High-risk contract change. Exercises the pipeline's ability to catch
**breaking changes hidden inside a reasonable-looking refactor**: lazy
implementations wrap `items` in an envelope but forget to update tests, or
update tests but forget backward-compat requirements (single-item route,
`items` key), or paginate without validating query params.

## Failure modes detected

- **Test lie**: arm changes the handler but leaves old `assert.ok(Array.isArray(body.items))` that still passes against `{ items: [...] }` inside the envelope → test passes but new paging fields aren't asserted. Fixture requires ≥ 2 NEW tests.
- **Query-param trust**: accepts `?per_page=abc` → `parseInt` returns `NaN` → handler explodes or silently treats as default. Fixture requires explicit 400.
- **Contract drift on single-item lookup**: arm paginates `/items/:id` too, breaking existing clients.
- **Silent catch**: wrapping `Number(req.query.page)` in a `try/catch { return [] }` — caught by forbidden pattern.

## Pipeline exercise

- Phase 0 routing: likely `strict` (no risk keywords, but cross-file multi-function change may escalate in Stage B).
- Phase 1 BUILD: Codex BUILD produces the implementation.
- Phase 1.4 BUILD GATE: `node --test tests/server.test.js` must pass.
- Phase 2 EVAL: scrutinizes that new tests cover new behavior (not just rename passes).
- Phase 3 CRITIC design: checks invalid-query branch and backward-compat.

## Rotation trigger

Retire when both arms consistently score > 95 AND produce 2+ new tests covering paging edge cases without pipeline intervention.
