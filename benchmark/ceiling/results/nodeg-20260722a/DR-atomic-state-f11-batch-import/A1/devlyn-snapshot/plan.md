<!-- devlyn:authorized-surface -->
## Files to touch

- `server/index.js` — edit — Add the `POST /items/import` handler required by Requirements 1–5, validating the entire batch before appending normalized rows with sequential numeric ids.
- `tests/server.test.js` — edit — Add the two required `/items/import` integration tests from Requirement 6 while preserving the existing GET-route tests.

```json
{"authorized_surface":["server/index.js","tests/server.test.js"]}
```

## Risks

- Do not touch files outside the two authorized paths or add dependencies; the criteria explicitly prohibits both.
- Interpret request-body validation strictly: an empty/missing/non-array `items` value returns exactly `400 { error: 'invalid_body' }` without mutation. The existing JSON middleware supplies `req.body` (`server/index.js:5`), while no current route mutates the module-scoped `items` list (`server/index.js:7-28`).
- Validate every item before assigning or appending rows, so the first invalid input-order index produces exactly `400 { error: 'invalid_batch', index, field }` and an invalid middle item cannot partially import. Check `name` before `qty` on the same item; accept only a non-empty trimmed string and `Number.isInteger(qty) && qty > 0`.
- Preserve the existing sequential numeric id scheme seeded at 1 and 2 (`server/index.js:7-10`): compute ids from the pre-request maximum and assign consecutive, distinct ids in input order, including within one valid batch.
- Store only `id`, trimmed `name`, and `qty`; do not retain extra item fields. Treat an empty `items` array as valid and return `201 { inserted: 0 }` without appending.
- Extend the existing direct-HTTP test style (`tests/server.test.js:6-24`) rather than introducing a test dependency. Tests share the module-scoped app and item list (`tests/server.test.js:4`), so assertions must use before/after GET results and avoid assuming the initial list remains only the two seed rows after other tests run.
- Refuse unrelated changes to the existing GET routes, health endpoint, persistence, authentication, rate limiting, or request-size limits; all are out of scope.

## Acceptance restatement

## Verification

```json
{
  "verification_commands": [
    { "cmd": "npm test", "exit_code": 0 }
  ]
}
```
