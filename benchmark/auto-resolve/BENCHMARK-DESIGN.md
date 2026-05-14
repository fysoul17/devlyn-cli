# Benchmark Suite Design — v1

**Outer goal**: see [`autoresearch/NORTH-STAR.md`](../../autoresearch/NORTH-STAR.md) — the harness composes frontier LLMs into a hands-free pipeline that delivers engineer-quality software for users who do not know context engineering, with each composition layer (L0 bare → L1 solo harness → L2 pair harness) justifying its added cost on quality AND wall-time efficiency. This benchmark is the measurement instrument for that contract.

**Purpose.** Replace ad-hoc harness benchmarking with a permanent, comprehensive,
one-command suite that gates every future harness change with a ship/rollback
decision. Any prompt edit, phase reorder, new native skill, or model upgrade
can be validated by running the suite and reading the numbers.

**Arm structure.** Current full-pipeline evidence uses three arms: `bare` (L0),
`solo_claude` (L1 solo harness), and an L2 pair arm (`variant` in the smoke
suite, or a focused pair arm such as `l2_risk_probes` in pair-candidate runs).
Pair claims are headroom-gated: counted fixtures must leave room above solo
(`bare <= 60`, `solo_claude <= 80`, default 5-point `bare`/`solo_claude` headroom margins),
the pair arm must actually run, and blind judging must show pair above solo by
the configured margin.

**Non-goals.** Publishable-research statistical rigor. Not a regression test
library for the product code — those live elsewhere. Not a substitute for
production telemetry — just enough signal for ship decisions.

---

## Principles

1. **One command.** `npx devlyn-cli benchmark` runs everything and prints a
   verdict. No manual fixture setup.
2. **Novice-proof.** The suite exercises the same paths a first-time user
   hits — including an end-to-end `ideate → resolve` fixture.
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
│   ├── F9-e2e-ideate-to-resolve/
│   └── F10+ extensions for headroom, full-pipeline pair, and frozen VERIFY
│
├── scripts/
│   ├── run-suite.sh          # smoke entry — runs fixture arms + judge + report
│   ├── run-fixture.sh        # one fixture, one arm
│   ├── judge.sh              # Codex blind judge (model-agnostic)
│   ├── compile-report.py     # aggregate into report.md + summary.json
│   └── ship-gate.py          # apply thresholds, return ship/rollback verdict
│
├── results/                  # per-run artifacts (overwritten)
│   └── <run-id>/
│       ├── <fixture>/
│       │   ├── bare/{input.md, transcript.txt, diff.patch, result.json}
│       │   ├── solo_claude/{same}
│       │   └── variant or l2_risk_probes/{same}
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
| `spec.md` | pipeline-arm input (resolve-ready spec with Requirements/Constraints/Out-of-Scope/Verification) |
| `task.txt` | bare-arm input (same intent, natural-language framing) |
| `expected.json` | machine-readable acceptance criteria + forbidden patterns + verification commands |
| `NOTES.md` | why this fixture exists, the specific failure mode it tests |
| `setup.sh` | deterministic starting state — applies to a fresh copy of `test-repo/` |

**Drift prevention**: `spec.md` and `task.txt` both derive from the same
`intent` block in `metadata.json`. A lint step in CI verifies they stay
consistent.

---

## Core Fixtures And Extensions

The original v3.6 matrix covered F1-F9. Later fixtures extend the same schema
for headroom, full-pipeline pair, and frozen VERIFY evidence.

Category coverage matrix for the original core set (rows = concerns, columns =
fixtures):

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
| F9-e2e-ideate-to-resolve | | | | | | ✓ (novice full-flow) |

**F9 is load-bearing** for the "novice user types `/devlyn:ideate`" promise.
Input is a vague idea; the pipeline path turns it into a spec with ideate and
then resolves that spec. Bare arm runs a direct prompt. Judge compares the final
usable artifact set.

---

## Single-Command Invocation

### User experience

```bash
npx devlyn-cli benchmark            # n=1 smoke, all fixtures
npx devlyn-cli benchmark F2 F5      # specific fixtures only
npx devlyn-cli benchmark --judge-only --run-id <id>   # re-judge without re-running
```

Output on completion:

```
Benchmark Suite Run — 2026-04-23T12:00Z (v3.6)
Judge: codex CLI flagship, xhigh, blind (model recorded in run history)

Fixture                         variant (L2)  solo_claude (L1)  bare (L0)  variant-solo_claude  Verdict
F1-cli-trivial-flag             95            92                88         +3                   PASS
F2-cli-medium-subcommand        92            86                81         +6                   PASS
F3-backend-contract-risk        89            80                72         +9                   PASS
F4-web-browser-design           87            83                79         +4                   PASS
F5-fix-loop-red-green           91            78                65         +13                  PASS
F6-dep-audit-native-module      88            82                70         +6                   PASS
F7-out-of-scope-trap            94            85                73         +9                   PASS
F8-known-limit-ambiguous        78            79                79         -1                   EXPECTED (known-limit)
F9-e2e-ideate-to-resolve        90            84                68         +6                   PASS
---------------------------------------------------------
Suite average variant (L2) score:       89.3
Suite average solo_claude (L1) score:   83.2
Suite average bare (L0) score:          75.0
Suite average variant-solo_claude margin: +6.1  (pair-evidence floor: +5 on eligible fixtures)
Hard-floor violations:        0
Regression vs shipped:       n/a (first run of v3.6)
SHIP-GATE VERDICT: ✅ PASS
```

### Runner orchestration

`run-suite.sh`:

1. Generate run-id `<ISO>-<sha>-<branch>`
2. For each fixture × each arm (`variant`/L2, `solo_claude`/L1, `bare`/L0): parallelizable via `xargs -P`
   - `run-fixture.sh --fixture FX --arm variant` → writes `results/<run-id>/FX/variant/*`
3. For each fixture: `judge.sh FX <run-id>` → writes `results/<run-id>/FX/judge.json`
4. `compile-report.py <run-id>` → writes `report.md` + `summary.json`
5. `ship-gate.py <run-id>` → exit 0 (PASS) / 1 (FAIL). Prints verdict to stdout.
6. If PASS and `--bless` flag: copy `summary.json` → `history/baselines/shipped.json`
7. Always: append `history/runs/<run-id>.json` + update `latest.json`

### `run-fixture.sh` contract

- Creates fresh temp copy of `test-repo/` at `/tmp/bench-<run-id>-<fixture>-<arm>/`
- Applies `setup.sh` if present
- Copies `spec.md` for `variant`/`solo_claude` or `task.txt` for `bare` as the prompt
- Invokes `/devlyn:resolve --spec` for `variant`, `/devlyn:resolve --spec --engine claude --no-pair --no-risk-probes` for `solo_claude`, or bare Claude for `bare` via isolated Agent
- Captures: `diff.patch`, `changed-files.txt`, `transcript.txt`, `timing.json`
- Runs `expected.json::verification_commands`, writes pass/fail per command to `verify.json`
- Writes `result.json` with aggregate: exit code, duration, files changed, verification score

### `judge.sh` contract

- Reads `results/<run-id>/<fixture>/{variant,solo_claude,bare}/{diff.patch,verify.json}` + fixture's `spec.md` + `expected.json`
- Builds a blind prompt: labels arms A and B randomly per fixture (seed recorded)
- Invokes isolated Codex (current flagship — no model hardcode) with RUBRIC.md
- Writes `judge.json`: per-axis scores, winner, margin, critical findings, disqualifiers
- Idempotent: re-running overwrites the same `judge.json`

---

## LLM-Upgrade Resilience

Three mechanisms:

1. **No hardcoded models.** Judge invocation omits `-m`, so it inherits
   whichever flagship the CLI currently ships. The blind judge is isolated from
   user config/rules/hooks so local agent instructions cannot contaminate the
   judgment. Same for agents — they run against whatever Claude Code
   session-model the caller has. Model provenance is captured in `result.json`
   per run.

2. **Margin as primary signal, absolute score as secondary.** When models
   improve, all arms tend to get better. Pairwise margins remain the stable
   signal: `solo_claude`-`bare` (L1-L0) measures solo harness value,
   pair-`solo_claude` (L2-L1) measures pair value on eligible fixtures, and
   `variant`-`bare` (L2-L0) remains the legacy suite signal. Ship gates are
   defined on margin (`>= +5`) and regression (`-3 or worse`), not absolute
   score.

3. **Fixture difficulty gradient.** F1 (trivial) is expected to saturate near
   100 quickly as models improve — that's fine, it still catches catastrophic
   regressions. F5/F9 (stress/E2E) have enough depth that even a near-perfect
   model won't 100-zero bare. If any fixture saturates (all compared gated arms
   > 95 for two consecutive versions), we replace it with a harder one and
   document the swap in `history/runs/<ts>-fixture-rotation.json`.

---

## Ship Gates (from RUBRIC.md)

Hard floors (any single failure blocks ship):

- **No silent-catch / fabricated verification / skipped required test in variant.** Judge flags this as disqualifier.
- **Variant may not lose any fixture by more than −5** versus previous shipped version (per-fixture regression floor).
- **At least 7 gated, headroom-available fixtures** must have margin ≥ +5
  (suite coverage).
- **F9 (E2E) must PASS** — novice-flow contract.

Soft gates (trigger rollback discussion):

- Suite average margin drop > 3 vs last shipped.
- Any fixture with margin ≤ 0 that previously had margin > +5.
- Critical-finding catch-rate decrease vs the last shipped comparable arm.

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
2. Parallel run safety — can we run the selected fixture set × 3 arms concurrently without
   rate-limit / lockfile conflicts? **Proposal**: default sequential with
   `--parallel N` flag. Default `N=1` for safety; the user can opt in.
3. Token accounting — Claude Code doesn't expose subagent totals reliably.
   **Proposal**: capture wall time as primary efficiency metric; token
   estimate as best-effort secondary. Do not gate ship on token math alone.
