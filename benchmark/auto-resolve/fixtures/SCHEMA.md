# Fixture Schema

Every fixture is a directory under `benchmark/auto-resolve/fixtures/F<N>-<slug>/` with these files. **All six files are required** (setup.sh may be empty when the starting `test-repo` copy needs no modification).

## metadata.json

```json
{
  "id": "F2-cli-medium-subcommand",
  "category": "medium",
  "difficulty": "medium",
  "timeout_seconds": 1200,
  "required_tools": ["node"],
  "browser": false,
  "deps_change_expected": false,
  "intent": "One-sentence plain-language statement of the work, the SINGLE source of truth for spec.md and task.txt."
}
```

- **id** — matches directory name, used across artifacts.
- **category** — one of `trivial | medium | high-risk | stress | edge | e2e`. Drives which ship-gate rule applies.
- **difficulty** — expected difficulty independent of category. Rubric uses this only for saturation detection (when `bare` and `solo_claude` both exceed 95 for two versions, flag fixture for rotation).
- **timeout_seconds** — per-arm hard timeout. Runner kills the arm at this limit and marks result `TIMEOUT`.
- **required_tools** — binaries the arm's environment must provide. Runner checks before invocation.
- **browser** — true if arm must be able to run Playwright. Runner uses this to decide whether `test-repo`'s Playwright deps get installed before the arm starts.
- **deps_change_expected** — true if the task involves modifying `package.json` / lockfiles. The pipeline arm's CRITIC security sub-pass is expected to trigger native `security-review` dep audit when true.
- **intent** — **load-bearing**. A short plain-language statement shared by all arms. `spec.md` formalizes it into resolve-ready form; `task.txt` renders it as a direct prompt. A CI lint ensures both derive from this field and stay in sync.

## spec.md

Resolve-ready spec for the pipeline arm. Same format `/devlyn:ideate` produces:

```markdown
---
id: "<fixture-id>"
title: "<short title>"
status: planned
complexity: medium
depends-on: []
---

# <fixture-id> <Title>

## Context
2-3 sentences describing WHY (not HOW). Must be traceable back to `metadata.intent`.

## Requirements
- [ ] Specific, testable, scoped.
- [ ] ...

## Constraints
- Concrete, with reasoning for each (not bare).

## Out of Scope
- Explicit "must NOT build" list. Audited by resolve/JUDGE as anti-commitments.

## Verification
- Concrete commands whose expected behavior is named.
```

`complexity` is the resolve spec contract enum, not the benchmark difficulty
label. Use `trivial`, `medium`, or `high` for new fixtures; `large` is accepted
only for compatibility with external/legacy specs. Keep ambiguous calibration
labels in `metadata.difficulty`, not spec frontmatter.

## task.txt

Bare-arm input. Plain English, same intent, but framed as a user request rather than a formal spec. Intentionally lacks the structured Requirements/Constraints/Out-of-Scope sections — bare must make those calls itself. Must not leak "use the devlyn skill" hints.

## expected.json

Machine-readable acceptance criteria used by both `run-fixture.sh` verification and the judge's rubric anchor.

```json
{
  "verification_commands": [
    {
      "cmd": "node bin/cli.js doctor",
      "exit_code": 0,
      "stdout_contains": ["doctor: "],
      "stdout_not_contains": ["undefined"],
      "contract_refs": []
    }
  ],
  "forbidden_patterns": [
    {
      "pattern": "catch\\s*\\(\\s*[a-zA-Z_]*\\s*\\)\\s*\\{\\s*return",
      "description": "silent catch returning a fallback value — violates no-silent-catches policy",
      "files": ["bin/cli.js"],
      "severity": "disqualifier"
    }
  ],
  "required_files": ["bin/cli.js"],
  "forbidden_files": [],
  "tier_a_waivers": [],
  "spec_output_files": ["bin/cli.js"],
  "max_deps_added": 0
}
```

- **verification_commands** — runner executes each. Each command's pass/fail contributes to the arm's `verify_score`.
  Commands run with `BENCH_WORKDIR` (fresh arm work tree) and
  `BENCH_FIXTURE_DIR` (the fixture directory outside the arm work tree) in
  the environment. Put discriminator/oracle scripts under the fixture
  directory when the arm should not read the verifier source; any
  `$BENCH_FIXTURE_DIR/...` file path referenced by a command must exist and
  must not escape the fixture directory. Hidden oracle commands must reference
  the verifier through an explicit `$BENCH_FIXTURE_DIR/...` path rather than
  `cd "$BENCH_FIXTURE_DIR"` indirection.
  Any command that references `BENCH_FIXTURE_DIR` is a hidden oracle and must
  include `contract_refs`: exact substrings from `spec.md` proving the oracle
  tests a visible contract rather than inventing a narrower one. Hidden oracle
  commands must also assert `stdout_contains: ["\"ok\":true"]` so a verifier
  cannot pass silently without emitting the success sentinel.
- **forbidden_patterns** — regexes scanned across `diff.patch`. Match at `severity: "disqualifier"` is a hard-floor fail. Match at `severity: "warning"` goes into the judge's critical-findings report.
- **required_files** — must exist after the arm runs.
- **forbidden_files** — must NOT appear in the arm's diff.
- **tier_a_waivers** — optional globs for files the spec explicitly authorizes even though Tier A scope oracle would normally flag them.
- **spec_output_files** — files or globs that define the authorized output surface for Tier B scope tracing.
- **max_deps_added** — count of new entries under `dependencies`/`devDependencies` in `package.json`. Exceeds → hard-floor fail.

## high-risk metadata

Fixtures with `metadata.json` `category: "high-risk"` must include at least
one resolve risk-trigger term in `metadata.intent` or `spec.md`, matching the
conditional pair/risk-probe triggers used by `/devlyn:resolve`: security/auth,
money/pricing/tax/ledger, persistence/data mutation, idempotency/replay,
API/webhook/signature, allocation/scheduling/inventory/rollback/transaction,
priority, or output/response-shape contracts. This keeps future pair-evidence
candidates from relying on a label that would not actually activate the pair
path.

## NOTES.md

Human-readable explanation of why this fixture exists. Must answer:

1. What specific failure mode does this fixture detect?
2. What pipeline phase(s) is this testing?
3. Why can't another fixture cover this?
4. When should this fixture be retired or replaced?

Notes are read during suite design review, not during runs.

If `NOTES.md` records that a fixture failed a headroom gate or was rejected as
pair-lift evidence, add the fixture to
`benchmark/auto-resolve/scripts/pair-rejected-fixtures.sh` in the same change.
Rejected controls should remain replayable, but they must not be silently
re-spent as fresh pair candidates.

## Retired fixtures

Move fixtures that are no longer valid active golden-suite evidence to
`fixtures/retired/<fixture-id>/`. Retired fixtures are preserved for replay and
historical diagnosis, but `run-suite.sh` does not auto-discover them. Each
retired fixture must keep the six fixture files plus `RETIRED.md` explaining
the run id or concrete reason it left the active suite.

## setup.sh

Deterministic starting state. Runs against a fresh copy of `benchmark/auto-resolve/fixtures/test-repo/` before either arm starts. Common uses:

- Install extra deps (`npm install --prefix . something`).
- Apply a `.patch` that introduces a bug to fix.
- Create pre-existing files referenced by the spec.

Script must be idempotent when re-applied. Empty file (just `#!/usr/bin/env bash\nset -e\n`) is valid when no setup needed.

---

## Drift Prevention

A CI lint step (`scripts/lint-fixtures.sh`) verifies:

- All six files present per fixture.
- `metadata.intent` substring appears in both `spec.md::Context` and `task.txt` (≥ 60% token overlap using simple tokenization).
- `spec.md` frontmatter `id` matches directory name.
- `expected.json` is valid JSON.
- Active high-risk fixtures include a resolve risk-trigger term in
  `metadata.intent` or `spec.md`.
- Active fixtures whose `NOTES.md` records headroom-gate failure or pair-lift
  rejection are covered by `pair-rejected-fixtures.sh`.
- Active fixtures whose `NOTES.md` records `pair_evidence_passed` include an
  actionable solo-headroom hypothesis in `spec.md`, using the same checker as
  shadow candidates, and the hypothesis observable command must match a
  `verification_commands[].cmd` entry in `expected.json`.
- `setup.sh` is executable.
- Retired fixtures under `fixtures/retired/F*/` keep `RETIRED.md`, preserve the
  six fixture files, and are excluded from active suite discovery.
