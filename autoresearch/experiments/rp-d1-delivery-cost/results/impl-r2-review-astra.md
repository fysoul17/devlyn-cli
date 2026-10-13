- **HIGH — [runner.py:197](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d1-apparatus/autoresearch/experiments/rp-d1-delivery-cost/runner.py:197): partial archives bypass PAT scanning.** `archive()` writes `repository.json` before manifest creation/verification. Injecting a manifest-write failure after a PAT-bearing PR body was retained produced `STOP`, usage `COMPLETE`, no revocation flag, and zero scan calls. Scan partial archives on failure; preserve the verified-archive requirement for deletion.

- **HIGH — [runner.py:200](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d1-apparatus/autoresearch/experiments/rp-d1-delivery-cost/runner.py:200): evaluator-generated records escape scanning.** The pre-seal scan precedes evaluation; the later scan covers only the archive. An in-memory probe with a correct BV implementation printing a decoded token at import passed all oracle rows while putting PAT bytes into `checks-raw.json`. Scan newly generated observation records before delivery assessment.

- **MEDIUM — [test_apparatus.py:711](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d1-apparatus/autoresearch/experiments/rp-d1-delivery-cost/test_apparatus.py:711): R1’s installer-date coverage remains incomplete.** The test replaces the real installer with a stub directly invoking `bootstrap_git`. The actual binding at `runner.py:63` is correct, but this test does not verify it. Exercise the real installer with only Docker mocked.

R1 closure evidence—all paths below are under `autoresearch/experiments/rp-d1-delivery-cost/`:

| R1 issue | Fix | Regression that detects its absence |
|---|---|---|
| Scan-error disclosure | `cell.py:59–97` | `test_apparatus.py:376`, integration `:825` |
| Compressed Git objects | `cell.py:81–87` | `test_apparatus.py:404`, `:422`, `:434` |
| Archived PR-body PAT | `runner.py:199–212` | `test_apparatus.py:886`; partial-failure gap above |
| Codex launch trust | `runner.py:116–117` | `test_apparatus.py:703` |
| Participant exceptions misgraded UNKNOWN | `oracle.py:65–69` | `test_apparatus.py:971` |
| Cross-engine routes | `tasks.json:3–21`, `runner.py:72–75` | `test_apparatus.py:728` |

The foreign-repository finding is superseded by the binding design.

Smoke uses the same lifecycle (`runner.py:180`), separate roots (`:54–62`), and frozen phase manifests (`:163–167`). Both smoke deletion receipts gate o01 before dispatch (`:148–160`); tests `:497`, `:564`, `:581`, and `:591` cover these boundaries.

Prior removable scaffolding is gone. No further justified removal or accounting/identity/seal regression found. Validation used read-only inspection and in-memory probes; no full suite or live smoke was run.

VERDICT: REVISE
