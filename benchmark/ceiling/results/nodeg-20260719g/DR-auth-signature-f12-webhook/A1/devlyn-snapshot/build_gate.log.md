# BUILD_GATE log (round 3 — final budgeted fix-loop round, max_rounds=4)

Run against HEAD `160dda9` (IMPLEMENT fix-round commit "chore(pipeline): implement fix round 3"), base `d5e479312b6f9573373bd2057e630bba7d22c608`.
Changed files across the whole run: `server/index.js`, `tests/server.test.js` (matches `authorized_surface` in `.devlyn/plan.md`; confirmed via `git diff --stat` against base — 66 insertions/1 deletion in `server/index.js`, 166 insertions in `tests/server.test.js`, zero other files touched, `package.json`/`package-lock.json` diff empty — no new deps).

## End-to-end history (bg-001 → bg-004)

- **bg-001** (ordering decision, round 0) — flagged, then independently re-verified as the *correct* spec reading (signature check before body-shape validation, duplicate check before full shape validation). Never re-opened.
- **bg-002** (malformed-JSON crash / HTML stack-trace leak, sig-check bypass, round 0→1) — fixed round 1 via a `SyntaxError`/`entity.parse.failed` error-handling middleware that returns clean 400/401 JSON instead of crashing.
- **bg-003** (bg-002's fix regressed malformed-JSON+invalid-signature to 400 instead of 401, round 1→2) — fixed round 2 by extracting a shared `hasValidSignature(req)` helper used by both the error middleware and the `/webhook` route handler, so signature is always checked first, even for syntactically-broken bodies.
- **bg-004** (Content-Type-mismatch / missing-Content-Type crash — `req.rawBody` undefined → `Hmac.update(undefined)` throws → 500 HTML stack trace, same failure class as bg-002 but a different trigger, round 2→3) — fixed round 3 via `if (!req.rawBody) return false;` guard at the top of `hasValidSignature` (server/index.js:11), reusing the existing 401 `invalid_signature` path, plus a new regression test (`tests/server.test.js:101`, "rejects a non-JSON request as an invalid signature") asserting 401 for `Content-Type: text/plain`.

This round verifies bg-004's fix and re-audits the whole feature end to end as the last budgeted round.

## 1. Type check
N/A — no `tsconfig.json` present. Skipped.

## 2. Lint
N/A — no eslint config present. Skipped.

## 3. Test suite

Command: `npm test` (`node --test tests/`)

Exit code: `0`

```
# tests 15
# suites 0
# pass 15
# fail 0
# cancelled 0
# skipped 0
# todo 0
```

15 tests (14 in round 2 + 1 new test this round, `POST /webhook rejects a non-JSON request as an invalid signature`, asserting 401). All pass. Zero findings from this gate.

## 4. Spec literal verification

Command: `python3 .claude/skills/_shared/spec-verify-check.py --include-risk-probes`

Exit code: `0`
Output: `[spec-verify] all 1 command(s) passed`

`.devlyn/spec-verify-findings.jsonl` present, 0 bytes (empty — no findings). Zero findings from this gate.

## 5. Browser tier
N/A — diff touches only `server/index.js` and `tests/server.test.js`. Skipped.

## 6. Independent spec-compliance re-check (round 3 — final, exhaustive pass)

Read the full `git diff d5e479312b6f9573373bd2057e630bba7d22c608 HEAD` top to bottom, plus `.devlyn/criteria.generated.md` and `.devlyn/goal.raw.txt` verbatim, one more time.

### bg-004 fix re-verified live, and its reasoning independently checked (not just accepted)

Live probes against the exported `app` (throwaway scripts, deleted after run — not left in the tree):

```
(a) text/plain, well-formed body, NO signature                          -> 401 {"error":"invalid_signature"}  (matches existing test, no crash)
(b) text/plain, well-formed body, VALID signature over the exact bytes  -> 401 {"error":"invalid_signature"}  (NOT 200 — see analysis below)
```

Analysis of (b): is a legitimately-signed non-JSON-Content-Type request being wrongly rejected? Traced through `body-parser`'s (via `express.json()`) internals: the library's type-matcher checks `Content-Type` *before* reading the request body at all. For `Content-Type: text/plain` it never reads the stream, never invokes the `verify` callback, and never populates `req.rawBody` or a parsed `req.body` — the raw bytes are simply never captured by this application (there is no wildcard/raw-body parser registered, nor should there be — adding one for all content types is not requested by the spec and would be scope growth, not a proportionate fix). Rechecked the literal spec text: `.devlyn/criteria.generated.md`'s Requirement 1 and body-shape Requirement 2 both describe the payload as JSON (`{ id, type, timestamp, data }`), and the Constraints section's raw-body instruction is scoped explicitly to `express.json()`'s `verify` option ("`express.json()`'s default body parser discards the raw buffer, so the raw body must be captured... before JSON parsing") — it never contemplates non-JSON Content-Types. A real webhook provider posting a JSON event always sets `Content-Type: application/json`; a request that doesn't is outside the shape space the spec describes, and this codebase has no mechanism (nor a spec mandate) to capture raw bytes for it. Given that, `hasValidSignature` returning `false` (and thus 401) for this class is the correct, safe-by-default behavior — strictly better than the pre-bg-004 crash, and not a new regression, since no candidate implementation using the spec's prescribed `verify`-option approach could do otherwise without out-of-scope additions. Confirmed acceptable, not filed as a finding.

### Duplicate/replay interaction with both crash-class fixes (bg-002/bg-004), tested live

```
baseline: accept a valid JSON event (id=probe-replay-textplain)                                    -> 200 {"accepted":true,...}
replay same id via Content-Type: text/plain, signature validly computed over those exact bytes      -> 401 {"error":"invalid_signature"}  (NOT 409)

baseline: accept a valid JSON event (id=probe-replay-malformed)                                     -> 200 {"accepted":true,...}
replay same id via malformed JSON, VALID signature computed over the malformed bytes                -> 400 {"error":"invalid_body"}       (NOT 409)
replay same id via malformed JSON, INVALID signature                                                -> 401 {"error":"invalid_signature"}
```

None of these interactions produce an incorrect 409 — the signature-check-first invariant (bg-001/bg-003) holds even when the request also triggers a crash-class guard: `hasValidSignature` is always evaluated before `acceptedEventIds` is ever consulted, in both the route handler and the error middleware. The malformed-JSON-with-valid-sig case (400, not 409) is not a bug: the id can only be read from body-parser's parsed `req.body`, which is never populated when `JSON.parse` throws (the request never reaches the route handler at all — it's caught entirely by the error middleware, which has no access to `acceptedEventIds`). Duplicate detection *before* full shape validation is already covered and passing via the pre-existing test `tests/server.test.js:133` ("rejects a replay before validating its second body" — syntactically-valid-but-incomplete JSON, `{"id": "..."}`, correctly returns 409), which is the only case where the spec's "regardless of what the second body contains" language is actually satisfiable (it presupposes a parseable body, since `id` must be extracted).

### No fourth sibling of the rawBody-undefined crash family

`grep -n "rawBody\|req\.body" server/index.js` shows exactly three references: the guard (line 11) and the one `Hmac.update` call (line 14), both inside `hasValidSignature` and both reached only through the guarded function; and the `req.body || {}` destructure in the route handler (line 71), which was already null-safe. No other code path reads `req.rawBody` or an unguarded `req.body`. Additional live edge-case probes, all clean (no crash, no 500):

```
no Content-Type header, empty body, no signature                          -> 401 {"error":"invalid_signature"}
Content-Type: application/json, empty body, no signature                  -> 401 {"error":"invalid_signature"}
Content-Type: application/json, empty body, VALID signature over ''       -> 400 {"error":"invalid_body"}   (empty body parses to {} per body-parser convention, then fails shape validation)
Content-Type: application/json; charset=utf-8, valid sig, valid body      -> 200 {"accepted":true,...}       (parameterized Content-Type still recognized, no crash)
Content-Type: application/json, valid body, NO X-Signature header at all  -> 401 {"error":"invalid_signature"}
```

### Full 5-Requirement acceptance bar, re-confirmed end to end

1. `POST /webhook` verifies `X-Signature` (lowercase-hex HMAC-SHA256 over raw bytes) via `crypto.timingSafeEqual`; mismatches (including wrong length/format) → 401 `{error:'invalid_signature'}`. Confirmed via passing tests + all live probes above; the 64-char lowercase-hex regex guarantees `signatureBuffer` is always exactly 32 bytes before `timingSafeEqual` is called, so the length-mismatch throw can never occur.
2. Signature check runs before body-shape validation (400 only after signature passes) — confirmed via `tests/server.test.js:170` ("rejects a validly signed invalid body" → 400) and `:257` ("rejects a malformed signature" → 401 before shape is ever inspected).
3. Duplicate `id` tracking: first delivery → 200; any subsequent delivery (regardless of second body, once parseable) → 409 — confirmed via `:115`, `:133`.
4. `tests/server.test.js` updated: all 3 pre-existing GET tests still pass, plus 9 new webhook tests (exceeds the "at least three" bar: happy path, replay, replay-before-shape-validation, tampered-body/stale-signature, invalid-body-valid-sig, malformed-JSON+valid-sig, malformed-JSON+invalid-sig, malformed-signature-format, non-JSON-Content-Type).
5. No new npm dependency; only `server/index.js` and `tests/server.test.js` changed — confirmed via `git diff --stat` and an empty `package.json`/`package-lock.json` diff.

Constraints re-confirmed: exact-raw-byte HMAC (via `verify` option, captured before `JSON.parse`, confirmed byte-sensitive by the tampered-body test); `timingSafeEqual` length-throw guarded by the format/length regex; duplicate tracking is in-memory module-level `Set`, matching the existing `items` array style; `data/webhook-secret.txt` read once at module load (`fs.readFileSync` at top level, not per-request).

Out-of-scope items confirmed untouched: `web/index.html`, `bin/cli.js`, existing `GET` routes unchanged; no rate limiting/retry/persistence added; no new dependency.

## Verdict

**PASS** — zero CRITICAL/HIGH findings. Mechanical gates: 15/15 tests pass, `spec-verify-check.py` 1/1 commands pass with an empty findings file. Independent final-round spec-compliance re-check: bg-004's fix is confirmed correct and its always-401-for-non-JSON-Content-Type side effect is confirmed spec-consistent (not a new bug) after independently re-deriving the reasoning against the literal spec text rather than accepting it at face value; the duplicate/replay interaction with both crash-class fixes (bg-002, bg-004) is confirmed correct via live probes (never incorrectly returns 409); no fourth sibling of the rawBody-undefined crash family exists; all 5 Requirements and all Constraints hold end to end; exactly the authorized two files changed, no new dependencies. bg-001 through bg-004 are all closed and none are re-opened by this round.
