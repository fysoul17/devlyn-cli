# F12 base snapshot

`source.bundle` contains the committed pre-task state from
`benchmark/auto-resolve/fixtures/test-repo`, the fixture's seeded webhook
secret/sample, and its pinned dependency tree. The dependency snapshot is
included because the untouched server imports Express and the ceiling
evaluator performs no install. Hidden HTTP/signing clients use only Node core
modules and drive Express through in-memory `IncomingMessage`/`ServerResponse`
objects. This preserves exact request bytes and middleware ordering without
opening a TCP port.

L3 classification: **KEYWORD-TRAP** (`auth-signature`, domain-blindspot
subtype). `task.txt` is the ORIGINAL fixture spec verbatim (restored
2026-07-10 by the orchestrator): the first port rewrite had leaked the
discrimination axis ("compare against a digest computed from those same
received bytes") that `NOTES.md` explicitly keeps unhinted ("Raw-body trap is
intentionally left without explicit hint"), and announced the hidden
silent-catch disqualifier. The original text already states every
oracle-checked observable (tampered-body-401, replay-409, sig-before-body
precedence, `crypto.timingSafeEqual`) without naming `express.raw` or a
seen-id mechanism — it IS the correct de-leaked spec.
