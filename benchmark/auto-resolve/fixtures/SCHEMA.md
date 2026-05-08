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
- **difficulty** — expected difficulty independent of category. Rubric uses this only for saturation detection (when both arms > 95 for two versions, flag fixture for rotation).
- **timeout_seconds** — per-arm hard timeout. Runner kills the arm at this limit and marks result `TIMEOUT`.
- **required_tools** — binaries the arm's environment must provide. Runner checks before invocation.
- **browser** — true if arm must be able to run Playwright. Runner uses this to decide whether `test-repo`'s Playwright deps get installed before the arm starts.
- **deps_change_expected** — true if the task involves modifying `package.json` / lockfiles. Variant's CRITIC security sub-pass is expected to trigger native `security-review` dep audit when true.
- **intent** — **load-bearing**. A short plain-language statement shared by both arms. `spec.md` formalizes it into auto-resolve-ready form; `task.txt` renders it as a direct prompt. A CI lint ensures both derive from this field and stay in sync.

## spec.md

Auto-resolve-ready spec for the pipeline arm. Same format `/devlyn:ideate` produces:

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
- Explicit "must NOT build" list. Audited by preflight as anti-commitments.

## Verification
- Concrete commands whose expected behavior is named.
```

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
  directory when the arm should not read the verifier source.
  Any command that references `BENCH_FIXTURE_DIR` is a hidden oracle and must
  include `contract_refs`: exact substrings from `spec.md` proving the oracle
  tests a visible contract rather than inventing a narrower one.
- **forbidden_patterns** — regexes scanned across `diff.patch`. Match at `severity: "disqualifier"` is a hard-floor fail. Match at `severity: "warning"` goes into the judge's critical-findings report.
- **required_files** — must exist after the arm runs.
- **forbidden_files** — must NOT appear in the arm's diff.
- **tier_a_waivers** — optional globs for files the spec explicitly authorizes even though Tier A scope oracle would normally flag them.
- **spec_output_files** — files or globs that define the authorized output surface for Tier B scope tracing.
- **max_deps_added** — count of new entries under `dependencies`/`devDependencies` in `package.json`. Exceeds → hard-floor fail.

## NOTES.md

Human-readable explanation of why this fixture exists. Must answer:

1. What specific failure mode does this fixture detect?
2. What pipeline phase(s) is this testing?
3. Why can't another fixture cover this?
4. When should this fixture be retired or replaced?

Notes are read during suite design review, not during runs.

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
- `setup.sh` is executable.
