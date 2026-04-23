# F6 — Notes

## Purpose

Primary exercise of the CRITIC security dep-audit trigger. The spec
explicitly disallows new dependencies; a lazy arm reaches for `sha256` or
`hash-sum` from npm; the suite's deterministic gate (`max_deps_added: 0`)
hard-fails that.

## Failure modes detected

- **Dependency bloat.** `npm i sha256` when Node `crypto` is already available.
- **Memory blowup.** `fs.readFileSync(path).toString()` → `crypto.createHash('sha256').update(...)`. Works for small files, blows memory on large. Non-disqualifier warning.
- **Broken error semantics.** Arms that catch ENOENT and exit 1 lose the fixture's exit-2 requirement.
- **Silent catches.** Masking fs errors with a generic fallback.

## Pipeline exercise

- Phase 3 CRITIC security native `security-review` skill triggers dep-audit
  because `deps_change_expected: true` in metadata. For v3.6 onward the
  native skill returns findings-only and is normalized into the critic
  JSONL; the pipeline catches a dep addition even if BUILD slipped it in.
- Phase 1.4 BUILD GATE runs `node --test tests/checksum.test.js` — if the
  digest doesn't match `sha256sum`, the test fails immediately.

## Why this matters for LLM upgrades

Models that "helpfully" suggest `npm i` for tasks like this are a hallmark
of over-reaching. As models improve, they should take the stdlib path more
often. Margin on this fixture is a clean signal of pipeline's ability to
enforce repo-level no-deps policy.

## Rotation trigger

When bare arms consistently avoid dependency-adding and pipeline still
shows margin ≥ +5 on two consecutive versions — sign that this is no longer
differentiating. Replace with a stricter dep-audit task (e.g., spec forbids
a semver bump of an existing dep).
