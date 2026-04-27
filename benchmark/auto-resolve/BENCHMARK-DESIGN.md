# Benchmark Suite Design — v1

**Outer goal**: see [`autoresearch/NORTH-STAR.md`](../../autoresearch/NORTH-STAR.md) — the harness composes frontier LLMs into a hands-free pipeline that delivers engineer-quality software for users who do not know context engineering, with each composition layer (L0 bare → L1 solo harness → L2 pair harness) justifying its added cost on quality AND wall-time efficiency. This benchmark is the measurement instrument for that contract.

**Purpose.** Replace ad-hoc A/B benchmarking with a permanent, comprehensive,
one-command suite that gates every future harness change with a ship/rollback
decision. Any prompt edit, phase reorder, new native skill, or model upgrade
can be validated by running the suite and reading the numbers.

**Arm structure (current vs planned).** Today the suite runs `variant` (L2: Claude + Codex pair) vs `bare` (L0). The L1 (solo harness on a single LLM) arm is queued for iter-0020 — until then the benchmark cannot directly verify the L1 contract, only the L0 ↔ L2 delta. Single-LLM users (Opus alone, GPT-5.5 alone) are first-class per the North Star, so this gap is a release-blocker for them, not a future enhancement.

**Non-goals.** Publishable-research statistical rigor. Not a regression test
library for the product code — those live elsewhere. Not a substitute for
production telemetry — just enough signal for ship decisions.

---

## Principles

1. **One command.** `npx devlyn-cli benchmark` runs everything and prints a
   verdict. No manual fixture setup.
2. **Novice-proof.** The suite exercises the same paths a first-time user
   hits — including an end-to-end `ideate → auto-resolve → preflight` fixture.
3. **LLM-upgrade friendly.** Rubric, fixture semantics, and thresholds stay
   stable; scores and margins float up as models improve. Nothing is
   hardcoded to a specific model version.
4. **Karpathy.** No fixture earns its place unless it tests a distinct
   failure mode. Tooling stays boring. History plumbing is simple.
5. **Ship gate is numbers, not vibes.** Concrete thresholds in RUBRIC.md.

---

## Directory Layout

```
benchmark/auto-resolve/
├── BENCHMARK-DESIGN.md       # this file
├── README.md                 # how to run, interpret, extend
├── RUBRIC.md                 # stable judge rubric + ship gates
│
├── fixtures/
│   ├── SCHEMA.md             # fixture file format
│   ├── test-repo/            # bootstrap Node project (shared base)
│   │   ├── bin/cli.js
│   │   ├── server/index.js
│   │   ├── web/page.html
│   │   ├── tests/
│   │   ├── playwright.config.js
│   │   └── package.json
│   │
│   ├── F1-cli-trivial-flag/
│   ├── F2-cli-medium-subcommand/
│   ├── F3-backend-contract-risk/
│   ├── F4-web-browser-design/
│   ├── F5-fix-loop-red-green/
│   ├── F6-dep-audit-native-module/
│   ├── F7-out-of-scope-trap/
│   ├── F8-known-limit-ambiguous/
│   └── F9-e2e-ideate-to-preflight/
│
├── scripts/
│   ├── run-suite.sh          # single entry — runs all fixtures × 2 arms + judge + report
│   ├── run-fixture.sh        # one fixture, one arm
│   ├── judge.sh              # Codex blind judge (model-agnostic)
│   ├── compile-report.py     # aggregate into report.md + summary.json
│   └── ship-gate.py          # apply thresholds, return ship/rollback verdict
│
├── results/                  # per-run artifacts (overwritten)
│   └── <run-id>/
│       ├── <fixture>/
│       │   ├── variant/{input.md, transcript.txt, diff.patch, verify.json, timing.json}
│       │   └── bare/{same}
│       ├── <fixture>/judge.json
│       ├── report.md
│       └── summary.json
│
└── history/
    ├── runs/                 # append-only immutable records
    │   └── 2026-04-23T120000Z-v3.6.json
    ├── latest.json           # pointer to most recent run
    └── baselines/
        └── shipped.json      # last blessed version, used for regression check
```

---

## Fixture Schema

Every fixture is a directory with these files (see `fixtures/SCHEMA.md`):

| File | Purpose |
|------|---------|
| `metadata.json` | id, category, difficulty, timeout, required tools, intent block |
| `spec.md` | pipeline-arm input (auto-resolve-ready spec with Requirements/Constraints/Out-of-Scope/Verification) |
| `task.txt` | bare-arm input (same intent, natural-language framing) |
| `expected.json` | machine-readable acceptance criteria + forbidden patterns + verification commands |
| `NOTES.md` | why this fixture exists, the specific failure mode it tests |
| `setup.sh` | deterministic starting state — applies to a fresh copy of `test-repo/` |

**Drift prevention**: `spec.md` and `task.txt` both derive from the same
`intent` block in `metadata.json`. A lint step in CI verifies they stay
consistent.

---

## The 9 Fixtures

Category coverage matrix (rows = concerns, columns = fixtures):

| Fixture | Trivial | Medium | High-risk | Stress | Edge | E2E |
|---------|---------|--------|-----------|--------|------|-----|
| F1-cli-trivial-flag | ✓ | | | | | |
| F2-cli-medium-subcommand | | ✓ | | | | |
| F3-backend-contract-risk | | | ✓ | | | |
| F4-web-browser-design | | | | ✓ (browser-validate) | | |
| F5-fix-loop-red-green | | | | ✓ (FIX LOOP) | | |
| F6-dep-audit-native-module | | | | ✓ (CRITIC security dep audit) | | |
| F7-out-of-scope-trap | | | | ✓ (scope discipline) | | |
| F8-known-limit-ambiguous | | | | | ✓ (documents where pipeline may lose) | |
| F9-e2e-ideate-to-preflight | | | | | | ✓ (novice full-flow) |

**F9 is load-bearing** for the "novice user types `/devlyn:ideate`" promise.
Input is a vague idea; pipeline arm runs ideate → auto-resolve on every
generated spec → preflight; bare arm runs a direct prompt. Judge compares
the final usable artifact set (code + docs + roadmap state).

---

## Single-Command Invocation

### User experience

```bash
npx devlyn-cli benchmark            # n=1 smoke, all fixtures
npx devlyn-cli benchmark --n 3      # higher confidence for ship decisions
npx devlyn-cli benchmark F2 F5      # specific fixtures only
npx devlyn-cli benchmark --judge-only --run-id <id>   # re-judge without re-running
```

Output on completion:

```
Benchmark Suite Run — 2026-04-23T12:00Z (v3.6)
Judge: codex CLI flagship, xhigh, blind (model recorded in run history)

Fixture                         Variant   Bare   Margin   Verdict
F1-cli-trivial-flag                 95     88     +7      PASS
F2-cli-medium-subcommand            92     81    +11      PASS
F3-backend-contract-risk            89     72    +17      PASS
F4-web-browser-design               87     79     +8      PASS
F5-fix-loop-red-green               91     65    +26      PASS
F6-dep-audit-native-module          88     70    +18      PASS
F7-out-of-scope-trap                94     73    +21      PASS
F8-known-limit-ambiguous            78     79     -1      EXPECTED (known-limit)
F9-e2e-ideate-to-preflight          90     68    +22      PASS
---------------------------------------------------------
Suite average variant score: 89.3
Suite average bare score:    75.0
Suite average margin:       +14.3  (ship floor: +5)
Hard-floor violations:        0
Regression vs shipped:       n/a (first run of v3.6)
SHIP-GATE VERDICT: ✅ PASS
```

### Runner orchestration

`run-suite.sh`:

1. Generate run-id `<ISO>-<sha>-<branch>`
2. For each fixture × each arm (variant, bare): parallelizable via `xargs -P`
   - `run-fixture.sh --fixture FX --arm variant` → writes `results/<run-id>/FX/variant/*`
3. For each fixture: `judge.sh FX <run-id>` → writes `results/<run-id>/FX/judge.json`
4. `compile-report.py <run-id>` → writes `report.md` + `summary.json`
5. `ship-gate.py <run-id>` → exit 0 (PASS) / 1 (FAIL). Prints verdict to stdout.
6. If PASS and `--bless` flag: copy `summary.json` → `history/baselines/shipped.json`
7. Always: append `history/runs/<run-id>.json` + update `latest.json`

### `run-fixture.sh` contract

- Creates fresh temp copy of `test-repo/` at `/tmp/bench-<run-id>-<fixture>-<arm>/`
- Applies `setup.sh` if present
- Copies `spec.md` (variant) or `task.txt` (bare) as the prompt
- Invokes Claude/auto-resolve (variant) or bare Claude (bare) via isolated Agent
- Captures: `diff.patch`, `changed-files.txt`, `transcript.txt`, `timing.json`
- Runs `expected.json::verification_commands`, writes pass/fail per command to `verify.json`
- Writes `result.json` with aggregate: exit code, duration, files changed, verification score

### `judge.sh` contract

- Reads `results/<run-id>/<fixture>/{variant,bare}/{diff.patch,verify.json}` + fixture's `spec.md` + `expected.json`
- Builds a blind prompt: labels arms A and B randomly per fixture (seed recorded)
- Invokes `codex exec` (current flagship — no model hardcode) with RUBRIC.md
- Writes `judge.json`: per-axis scores, winner, margin, critical findings, disqualifiers
- Idempotent: re-running overwrites the same `judge.json`

---

## LLM-Upgrade Resilience

Three mechanisms:

1. **No hardcoded models.** Judge invocation is `codex exec` without `-m`; it
   inherits whichever flagship the CLI currently ships. Same for agents —
   they run against whatever Claude Code session-model the caller has.
   Model provenance is captured in `result.json` per run.

2. **Margin as primary signal, absolute score as secondary.** When models
   improve, both arms get better. Margin (variant − bare) is model-invariant
   — it measures **what the harness adds beyond bare**. Ship gates are
   defined on margin (`>= +5`) and regression (`-3 or worse`), not absolute
   score.

3. **Fixture difficulty gradient.** F1 (trivial) is expected to saturate near
   100 quickly as models improve — that's fine, it still catches catastrophic
   regressions. F5/F9 (stress/E2E) have enough depth that even a near-perfect
   model won't 100-zero bare. If any fixture saturates (both arms > 95 for
   two consecutive versions), we replace it with a harder one and document
   the swap in `history/runs/<ts>-fixture-rotation.json`.

---

## Ship Gates (from RUBRIC.md)

Hard floors (any single failure blocks ship):

- **No silent-catch / fabricated verification / skipped required test in variant.** Judge flags this as disqualifier.
- **Variant may not lose any fixture by more than −5** versus previous shipped version (per-fixture regression floor).
- **At least 7 of 9 fixtures** must have margin ≥ +5 (suite coverage).
- **F9 (E2E) must PASS** — novice-flow contract.

Soft gates (trigger rollback discussion):

- Suite average margin drop > 3 vs last shipped.
- Any fixture with margin ≤ 0 that previously had margin > +5.
- Critical-finding catch-rate decrease vs last shipped variant (not vs bare — bare is the opponent, not the regression baseline).

Known-limit exception:

- F8 is explicitly allowed to tie or lose (margin in [-3, +3]). Its job is to
  document honesty, not to beat bare.

---

## Karpathy Check

Where over-engineering lurks:

- ❌ **Automatic history mutation during development.** Add append-only
  history AFTER the suite format stabilizes (one version after initial ship).
- ❌ **Statistical tooling beyond mean/median/margin.** n=1-3 doesn't need
  t-tests.
- ❌ **Auto-generated fixture cards / dashboards.** Plain `report.md` is enough.
- ✅ **Keep scripts under 100 lines each** unless they're doing concrete,
  repeated work the user would do by hand.

If the suite tooling grows past ~800 total lines, prune aggressively before
adding anything.

---

## Open Questions (to be answered before first full ship-gate run)

1. Where does `benchmark` subcommand live? Inside `bin/devlyn.js` or as
   standalone `benchmark/auto-resolve/scripts/run-suite.sh` invoked via `npm
   run`? **Proposal**: both — `bin/devlyn.js benchmark` is the advertised
   entry, which shells out to the script.
2. Parallel run safety — can we run 9 fixtures × 2 arms concurrently without
   rate-limit / lockfile conflicts? **Proposal**: default sequential with
   `--parallel N` flag. Default `N=1` for safety; the user can opt in.
3. Token accounting — Claude Code doesn't expose subagent totals reliably.
   **Proposal**: capture wall time as primary efficiency metric; token
   estimate as best-effort secondary. Do not gate ship on token math alone.
