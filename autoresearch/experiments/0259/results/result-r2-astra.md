VERDICT: REVISE
FINDINGS:

- [HIGH] `results/witnesses/f10-same-process-instances.js:47`, `RESULT.md:85–86` — Mixed 201/500 rounds skip loss detection entirely. A shared temporary file can publish the failing request’s payload while the successful request’s item disappears; exit 0 therefore leaves c007’s judgment unsupported — check persistence of every 201 item, including earlier successes, preserve raw results, rerun twice, and reassess under m24.
- [LOW] `RESULT.md:225–226` — “Changed only the host path” contradicts the disclosed `/witness` directory-content change — remove “only” or mention both changes.

The c014 correction and other round-1 wording fixes are resolved. Amendment 2 is otherwise acceptable. Read-only recomputation matches every field in `decision.json`.
