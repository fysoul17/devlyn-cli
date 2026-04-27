# Benchmark Judge Rubric

Stable across model upgrades. This file is the single source of truth for how
arms are scored and how ship gates evaluate a run. Do not change the rubric
during a benchmarking window — changing it invalidates comparability with
prior `history/runs/`.

**Outer goal lives in [`autoresearch/NORTH-STAR.md`](../../autoresearch/NORTH-STAR.md).** The release-decision layer (L0 / L1 / L2 contracts, wall-time efficiency, pair-cost justification) sits on top of the per-arm scoring rules below. When NORTH-STAR.md adds a release-gate number that this file did not have, the new number applies — open a doc-fix iter to mirror it here.

## Scoring — 4 axes, 25 points each, 100 total

The blind judge scores both arms on identical axes without knowing which is
variant vs. bare.

### Axis 1 — Spec Compliance (0-25)

Does this implementation satisfy every Requirements bullet in `spec.md`?
Does every Verification command behave as the spec states?

- **25** — All Requirements satisfied. All Verification commands would pass.
- **19-24** — 90%+ coverage, minor omissions.
- **13-18** — Partial implementation or verification gaps.
- **7-12** — Major requirements missed.
- **0-6** — Does not address the core task.

### Axis 2 — Constraint Respect (0-25)

Zero new npm deps (unless spec allows), no silent catches (`try { } catch { return fallback }`), no `any`/`@ts-ignore`, explicit HOME/env guards where required, EACCES-specific handling, no hardcoded values that should be configurable.

- Each **disqualifier-severity forbidden_pattern match** or explicit constraint violation = −4 points, minimum 0.

### Axis 3 — Scope Discipline (0-25)

Out of Scope respected. No gratuitous refactors of unrelated code. No "while I'm here" additions. No opportunistic upgrades.

- Each out-of-scope change = −5 points, minimum 0.

### Axis 4 — Code Quality (0-25)

Readable, idiomatic for the language/framework, helpful error messages, appropriate abstraction level (not under- or over-engineered), uses standard library primitives where available (e.g., `fs.accessSync` over mode-bit checks per CLAUDE.md `phase-3-critic.md:32` calibration).

- This axis is judge-calibrated; no deterministic grading. The judge looks at
  naming, function/file decomposition, error handling, and comparability to
  idiomatic peer code.

---

## Judge Disqualifiers (hard floor)

Any of these produces `disqualifier: true` on the arm, overriding score:

- Silent-catch pattern in diff.
- Fabricated verification (code that claims to pass without actually running).
- Skipped a required test file that the spec names.
- Created a file listed in `expected.forbidden_files`.
- Exceeded `expected.max_deps_added`.
- `@ts-ignore` / `eslint-disable` without scoped justification comment.
- Hardcoded paths or values where spec required configurability.

Disqualifier arms automatically lose the fixture regardless of score.

---

## Ship Gates

After the judge finishes every fixture, `scripts/ship-gate.py` applies these
rules to the run's `summary.json`.

### Hard floors (any one failure blocks ship)

1. **No disqualifier-level violation** in variant on any fixture.
2. **F9 (E2E) must PASS** — novice-flow contract.
3. **≥ 7 of 9 fixtures** must have margin ≥ +5.
4. **No fixture regression worse than −5** vs. last `baselines/shipped.json` on the same fixture.

### Soft gates (produce WARNING but do not block)

5. Suite average margin drop > 3 vs. last shipped.
6. A fixture that previously had margin > +5 now has margin ≤ 0.
7. Critical-finding catch-rate decrease vs. last shipped variant (not vs. bare).

### Known-limit exception

- **F8-known-limit-ambiguous** is excluded from gates 3 and 4. It exists to
  document where the harness may not beat bare. Its allowed margin range is
  [-3, +3]. Margins outside this range trigger a WARNING regardless of sign
  (too-good means the fixture is no longer a known limit; too-bad means we
  shipped a regression somewhere else that this fixture caught).

---

## Run Record

Every suite run appends an immutable record to `history/runs/<ts>-<label>.json`:

```json
{
  "run_id": "2026-04-23T12:00:00Z-v3.6",
  "version_label": "v3.6",
  "git_sha": "fdb7428...",
  "branch": "benchmark/v3.6-ab-...",
  "n_per_fixture": 1,
  "judge_model": "<recorded from ~/.codex/config.toml at run time; do not hardcode>",
  "judge_effort": "xhigh",
  "fixtures": [
    {
      "id": "F2-cli-medium-subcommand",
      "variant": { "score": 92, "wall_s": 707, "tokens_agg": 108852, "disqualifier": false,
                   "axes": {"spec": 23, "constraint": 23, "scope": 24, "quality": 22} },
      "bare":    { "score": 81, "wall_s": 101, "tokens_agg": 55588,  "disqualifier": false,
                   "axes": {"spec": 19, "constraint": 19, "scope": 20, "quality": 23} },
      "winner": "variant",
      "margin": 11,
      "critical_findings": {
        "variant": [],
        "bare": ["silent catch in findSkillMdFiles (no-silent-catches violation)"]
      }
    }
  ],
  "suite": {
    "fixtures_run": 9,
    "variant_avg": 89.3,
    "bare_avg": 75.0,
    "margin_avg": 14.3,
    "hard_floor_violations": 0,
    "ship_gate": "PASS"
  }
}
```

---

## Fixture Rotation Policy

If any fixture has both arms scoring > 95 for two consecutive shipped
versions, it's saturated and no longer differentiates. Replace with a harder
equivalent and record the swap in
`history/runs/<ts>-fixture-rotation.json`:

```json
{
  "retired": "F1-cli-trivial-flag",
  "retired_reason": "both arms > 95 on v3.7 and v3.8 (saturation)",
  "replacement": "F1b-cli-trivial-flag-v2",
  "replacement_rationale": "adds exit-code precedence requirement that current leaders didn't handle on first try"
}
```

Retired fixtures stay in `fixtures/retired/` for replay if a regression is
suspected in their area.

---

## Why These Thresholds

- **+5 margin floor** — below this, variant isn't reliably beating bare given
  judge variance (empirically ~±3 per axis). Worth paying pipeline cost
  requires margin clearly above noise.
- **−5 regression floor** — one-axis regression can look like −5; allowing
  less would let real regressions slip through.
- **7/9 fixtures rule** — tolerates one close-call + F8 known-limit; anything
  worse means the suite is surfacing a broad harness problem.
