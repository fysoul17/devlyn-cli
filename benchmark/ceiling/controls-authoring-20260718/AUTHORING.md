# Accuracy controls — authoring record (2026-07-18)

Outcome-blind author: fresh Opus seat. Two `(goal, input.patch, expected-disposition)`
triples for the worker-audit accuracy instrument. Authored strictly from the task
definitions and the four permitted context sources — no run results consulted.

## Blinding attestation

I did NOT open any file under `benchmark/ceiling/results/r6-replay-20260718/`, nor
`autoresearch/DECISIONS.md`, nor the tail of
`autoresearch/iterations/0072-changed-surface-closure.md` beyond the `Registration v6`
section. I did not learn any worker run results, adjudications, or pass/fail outcomes.
This authoring derives only from:

1. The F7 seed repo at commit `e5a20d9` (base CLI: `bin/cli.js` USAGE block + `version`
   subcommand, `tests/cli.test.js`), cloned from
   `benchmark/ceiling/results/nodeg-20260718c/gate-fail-artifacts/f7-row-repo.bundle`.
2. `nodeg-20260718c/gate-fail-artifacts/goal.raw.txt` (original task goal bytes).
3. `nodeg-20260718c/gate-fail-artifacts/surface-close.input.patch` (original implement diff).
4. The worker obligation grammar supplied in the task brief (UVR-STALE / PATH-TEST).

## Obligation grammar (as given)

- **UVR-STALE** — diff modified symbol S's behavior AND an authorized file carries
  user-visible text documenting S's old interface omitting the newly specified
  option/shape → update minimally.
- **PATH-TEST** — goal specifies a success/failure path, patch implements it, and no
  authorized test exercises that path → add one minimal regression test.
- Neither applies → empty PASS.

Authorized surface for both controls: `bin/cli.js` + `tests/cli.test.js` only.
Pre-tree a worker audits = seed@`e5a20d9` + the control's `input.patch`.

## Control A — "no-stale"  →  UVR-STALE: N/A, PATH-TEST: FIRED

- `goal.raw.txt`: byte-identical to the original goal (verified via `cmp`).
- `input.patch`: implements `version --format json` (single-line `{"version":"<x.y.z>"}`;
  unsupported format → `console.error` + `exit 1`) **and already updates the USAGE
  `version` row** to document the option (`version [--format json]`), so no user-visible
  help text is stale → UVR-STALE has nothing to fire on. A success-path test is present;
  **no failure-path (exit-1) test** is present → PATH-TEST fires (add the missing
  unsupported-format regression test).
- Implementation written in the author's own style (`resolveVersionFormat` helper,
  distinct error string, if/else print) — not the archived hunks verbatim.
- `expected-disposition.json`: `{"UVR-STALE": "N/A", "PATH-TEST": "FIRED", "expected_delta": "test-only"}`

## Control B — "goal-frozen"  →  UVR-STALE: N/A, PATH-TEST: N/A, empty delta

- `goal.raw.txt`: original goal + one naturally-worded sentence appended to the scope
  paragraph that explicitly freezes the USAGE help text ("Leave the `USAGE` help-text
  block exactly as it is: the help output must stay byte-for-byte identical, and you must
  not document the new `--format` option there or edit that block in any way, even though
  the option now exists."). The only delta from the original goal is this sentence
  (verified via `diff`).
- `input.patch`: implements `version --format json` per the goal, **does not touch USAGE**
  (consistent with the freeze → UVR-STALE N/A), and includes **both** a `--format json`
  success-path test **and** an unsupported-format exit-1 failure-path test (→ PATH-TEST
  has nothing left to add). Correct disposition is empty delta.
- `expected-disposition.json`: `{"UVR-STALE": "N/A", "PATH-TEST": "N/A", "expected_delta": "empty"}`

## Validation performed (all passing)

Each control was validated against a fresh, pristine `e5a20d9` checkout — twice: once
on the staging copy and again on the repo-committed deliverable patch.

| Check | Control A | Control B |
|---|---|---|
| `git apply --check` on pristine `e5a20d9` | OK | OK |
| USAGE state | version row documents `--format json` | USAGE untouched (original row; no `--format`) |
| success-path test present | yes | yes |
| failure-path (exit-1) test present | **no** (intended) | yes |
| `node --test tests/cli.test.js` | 4 pass / 0 fail | 5 pass / 0 fail |
| runtime: `version --format json` | `{"version":"0.1.0"}` exit 0 | `{"version":"0.1.0"}` exit 0 |
| runtime: `version` (plain) | `0.1.0` exit 0 | `0.1.0` exit 0 |
| runtime: `version --format yaml` | error, exit 1 | error, exit 1 |

`tests/server.test.js` failures (environment-restricted) were ignored per brief; only
`tests/cli.test.js` was exercised.

## sha256 of deliverables

```
f3467374f6554ece0b14e48250222d11fc6675aae4cb0ded70fc3503a78c9674  control-a-no-stale/goal.raw.txt
e5be398eb42114657e73822de2ffef6310eae743874d16b930735a65035c7256  control-a-no-stale/input.patch
d679f385d41c2d66347bfa9f3aa4e5055dd8ad2e0d757c85c06dbf578429748b  control-a-no-stale/expected-disposition.json
35eea7dd8f6736c962e608191ff0ef09cfb6daa85e335f76c25534f1b6e90e9b  control-b-goal-frozen/goal.raw.txt
8f7f2914cc166504d309415b0cd9e7dc92a0cbc67cd3c8dfc54aa191b1944bfb  control-b-goal-frozen/input.patch
cec46cc16b191248334da5164d8a5df327ae16e0cf23376b5bb19b177dcd072d  control-b-goal-frozen/expected-disposition.json
```
