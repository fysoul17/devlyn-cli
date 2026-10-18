# rp-d8 apparatus validation

Scope: offline implementation and synthetic/local-Git verification only.
No GitHub or model API request, experiment cell, token-counting request,
repository provisioning, credential snapshot, image build or commit was run.
`DESIGN.md` is unchanged from `7c5dcdf2fca05f8d17d9e7fb3bc340461f8713c1`;
the product candidate remains HEAD
`e22dbaf3b7d4a458768c86e7ec8ff85e0f8bdb8c`.
The local Git diff confirms only the shipped file and its `.agents` mirror
changed between design and candidate; both candidate blobs are
`de7f9882dc8c3df1cb2b0a621c9c7fa794b01866`.

## Prediction before final verification

The rp-d8 suite should accept the exact registered pack, prompt, schedule and
sealed observations; reject changed bindings and forbidden effects; retain
unknowns; and implement the eight decision branches in their frozen order.
The unchanged rp-d7/rp-d6/rp-d4/rp-d5 suites should remain green. A test failure
invalidates this expectation until its root cause is fixed and retested.

## Coverage

| Contract | Offline evidence |
|---|---|
| Exact one-path pack, candidate commit/blob, frozen shipped set, SHA-256/SHA-512 | `test_pack_gate.py` |
| Installed task token nonincrease, unchanged root bytes, registration digest | `test_pack_gate.py`, `test_prepare_stage.py`; counters are synthetic, credentials are never read |
| Every P1 body/suffix/full caller contract, installed bindings | `test_prepare_stage.py` |
| 16 measured slots, 8 guards, 4 possible smoke slots, 27 repositories, high effort | `test_runner.py`, `test_prepare_stage.py` |
| Pair/guard renewal, same-account constraint, STOP, one spare pair | `test_prepare_stage.py`, `test_runner.py` |
| Strict credential schema and sealed effort mismatch STOP | Path-reused rp-d7 and rp-d6 suites |
| Original checkout census, transient creation/write evidence, config/exclude digests | `test_capture.py`, `test_local_only.py` |
| All commit objects beyond allocation, archived PR diffs including renames | `test_capture.py` |
| All guard pass/fail/unknown paths and forbidden versus missing effects | `test_grading.py`, `test_summary.py` |
| g06 no-remote materialization, local archive, continuation to g07 | `test_runner.py`, `test_local_only.py`, `test_grading.py` |
| Review input/manifests revalidation, non-delivery classes, two-reviewer tags | `test_grading.py`, `test_summary.py`, inherited rp-d7 suite |
| Severe regression only Y/guards, actual paired X | `test_grading.py`, `test_summary.py` |
| All decision branches/order, provisional reviews, prediction, sign test, costs | `test_summary.py` |
| Watcher alive/dead/unknown, log tail, observation before slot, smoke digest ordering | `test_runner.py` |

The suite-wide boundary rejects socket/HTTP access and external processes
other than local Git fixture operations. The README's separate-suite loop
disables bytecode/cache writes and includes rp-d8 on `PYTHONPATH`.

## Review and observed corrections

Independent cross-model review ran alongside tests. It identified two g06
integration errors: the inherited materializer received later guards' remote
targets, and rp-d7's publication reader expected `repository.json` in g06's
local archive. The runner now passes no remote targets to g06; local evidence
uses its manifest-bound observation. Regression tests exercise both paths.
The reviewer verified those fixes and returned **SHIP**, with no remaining
HIGH/CRITICAL findings.

Local review also verified successful allocation followed by cleanup remains
an evidenced creation, while failed or unresolved commands do not silently
become successful effects. Repeated runner construction installs the PR
census hook once. Route observations are stamped before smoke verdict digests
are registered.
Successful no-op removals do not establish a `.devlyn/` mutation; uncertain
working-directory context remains unknown. A STOP before full prompt binding
remains INCONCLUSIVE; any declared binding is still checked for tampering.

## Results

The README's five-suite loop, with rp-d8 included in `PYTHONPATH` and Python
bytecode/plugin/cache writes disabled, exited 0. Final raw pytest summaries:

```text
rp-d8: 286 passed in 36.90s
rp-d7: 325 passed in 24.83s
rp-d6: 277 passed in 36.10s
rp-d4: 268 passed, 18 subtests passed in 45.22s
rp-d5: 195 passed in 28.06s
```

Total: **1,351 passed, plus 18 subtests**. New-file whitespace checks passed.
The final scope check found only the 21 new rp-d8 files; no tracked change
outside the allowed directory, no DESIGN change, and HEAD remained the
candidate commit.

These checks qualify code paths, not a live apparatus run. The installed
token gate, image, credentials, network route and real smoke remain operator
preconditions.

## Round-1 apparatus review follow-up — 2026-10-19

The initial build record above predates this follow-up. All eight real findings
in `results/apparatus-r1-verification.json` are fixed in the rp-d8 layer:
history-backed commit absence (A1), bound accepted-head proofs (G1), independent
registry and candidate-blob pins (A2), sealed publication outcomes and failed
attempt adjudication (A3), agreed positive history findings (A4), the rp-d7
executable input census (A5), final adoption despite unset descriptive tags
(B1), and exact-format route-watch tails (A6). G2 required no change.

The pre-fix prediction was that the new regressions would expose false zero
commit counts, invocation-only publication facts and rejected-proof unknowns.
The initial targeted run recorded `19 failed, 2 passed, 79 deselected`.
Cross-model review identified one MEDIUM option-value parsing error; after its
fix and regression coverage, the second round returned **SHIP**, with no
remaining HIGH/CRITICAL findings. Local registration and Git-object checks
independently confirmed the frozen registry hashes and candidate blob.

The README's separate-suite offline loop then exited 0:

```text
rp-d8: 366 passed in 43.48s
rp-d7: 325 passed in 35.81s
rp-d6: 277 passed in 36.81s
rp-d4: 268 passed, 18 subtests passed in 36.17s
rp-d5: 195 passed in 24.69s
```

Total: **1,431 passed, plus 18 subtests**; rp-d8 gained 80 cases. No network,
live cell or worktree commit was used. Task edits stay under rp-d8; DESIGN.md,
the supplied review artifacts and the pre-existing rp-d7 bytecode modification
remain untouched. Bytecode/plugin/cache writes were disabled for the checks.

## Smoke-attempt-1 binding repair — 2026-10-19

Prediction before the regression run: the valid Codex installation without
CLAUDE.md would fail, and private inherited EvidenceError classes would lose
their fixed messages in the rp-d1 slot recorder. The run confirmed both:
`8 failed, 25 passed, 88 deselected`. After the rp-d8-only fix, targeted checks
reported `40 passed, 81 deselected`, including rejection of wrong/import-plus-
extra/CRLF CLAUDE bytes, missing Claude instructions, and arbitrary exception
payload serialization. AGENTS managed-block validation remains inherited.

Both staged X/Y archives passed verification and their extracted trees matched.
Their identical installer SHA256 is
`fc60aa2ccc4435386ced243e88b4062058384090e845a1c23fef4740667e2122`.
The inherited installer invokes Codex with `-y`, selecting only AGENTS on a
fresh checkout; Claude also receives `--claude`, producing the exact 11-byte
`@AGENTS.md\n` import. Present CLAUDE files still use rp-d7's exact check.
The untouched smoke-codex checkout passed the repaired read-only installed
binding after X/Y release verification; no cell was dispatched.

No additional Codex blocker was found for g01, g02 or smoke-codex. API-body
capture and effort binding already branch on Claude. Auth selects by engine;
Codex's inherited `claude.env` mount is required to be empty. The rp-d7
credential parser checks GitHub credentials for either engine. Its Claude-only
Runner is outside rp-d8's inheritance chain, and bookkeeping capture supports
Codex sessions/events. The exception fix shares only the trusted EvidenceError
class across private modules, retained function aliases and lazy loads; private
GitHub hooks and generic exception redaction remain intact.

Astra review returned **SHIP**, with no findings. All three requested suites
passed with `PYTHONDONTWRITEBYTECODE=1`, plugin autoload and pytest cache disabled:

```text
rp-d8: 499 passed in 102.96s (0:01:42)
rp-d7: 325 passed in 50.00s
rp-d6: 277 passed in 59.37s
```

Total: **1,101 passed**. All edits stay in rp-d8; rp-d1..rp-d7, DESIGN.md and
sealed smoke artifacts remain unchanged. No network, live cell or worktree
commit was used.
