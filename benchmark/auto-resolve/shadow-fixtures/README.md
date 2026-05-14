# Shadow fixtures

Frozen task suite for **bare-vs-solo_claude categorical reliability measurement**,
parallel to the active golden `F*` fixtures under `../fixtures/`.

## Why this exists

User direction 2026-04-30: real-project trial too expensive and not
bare-comparable; instead generate small-but-tricky tasks inside the benchmark
and run bare-vs-solo_claude on them. Codex deep R0 verdict: option (c) —
frozen shadow suite alongside the then-current golden F1-F9 set, hybrid
generation (LLM proposes → Codex/human curates → frozen).

## How this differs from `../fixtures/`

| | Golden (`../fixtures/F*`) | Shadow (`./S*`) |
|---|---|---|
| Purpose | Release-decision ship-gate | Categorical reliability measurement |
| Auto-discovered by `run-suite.sh` default | Yes | No |
| Discovery trigger | always | `--suite shadow` flag |
| Feeds `ship-gate.py` | Yes | No (per `--suite` segregation) |
| Frozen at iter? | Yes | Yes |

Shadow runs are read-only signals: they redirect work but cannot bless Mission 1
by themselves. Active golden `F*` fixtures and pair-evidence audits control
release.

## Current contents

- `S1-cli-lang-flag` remains available for shadow runner and packaging smoke checks.
- `S2-cli-inventory-reservation`, `S3-cli-ticket-assignment`,
  `S4-cli-return-routing`, `S5-cli-credit-grant-ledger`, and
  `S6-cli-refund-window-ledger` are calibrated shadow controls: real headroom
  runs showed solo saturation, so they are recorded in
  `../scripts/pair-rejected-fixtures.sh`.

Older planning notes mentioned larger v0/v1/decision-grade shadow suite sizes;
those are not the active contents of this directory.

## Task naming

`S<N>-<slug>/` — uppercase `S` prefix differentiates from golden `F` prefix. Discovery globs `shadow-fixtures/S*/`.

## Running the shadow suite

```bash
bash benchmark/auto-resolve/scripts/run-suite.sh --suite shadow --dry-run    # list shadow tasks
```

`run-suite.sh --suite shadow` is dry-run only. Use the score-focused headroom
and pair candidate runners below with explicit `S*` ids for real provider
measurement. Default `--suite golden` keeps active golden `F*` behavior
unchanged.

## Candidate calibration

Shadow fixtures can be targeted by the score-focused candidate runners with an
explicit `S*` id before promotion to golden fixtures:

```bash
npx devlyn-cli benchmark headroom --dry-run --min-fixtures 1 S1-cli-lang-flag
npx devlyn-cli benchmark pair --dry-run --min-fixtures 1 S1-cli-lang-flag
```

Use the dry-run form for cheap argument, packaging, and fixture-shape checks
while drafting new solo<pair candidates. Use non-dry-run headroom/pair only for
explicitly named `S*` candidates with a solo-headroom hypothesis. Shadow results
remain read-only signals: promote a validated `S*` task to an active `F*`
fixture before counting it as golden pair evidence.

`S1-cli-lang-flag` is only the dry-run smoke target for this path. Do not spend
real provider calls on S1; its `trivial` metadata makes it a packaging/runner
shape check, not a solo<pair evidence candidate.

Before real provider measurement, each new pair-candidate shadow fixture needs a
solo-headroom hypothesis in `spec.md`: name the visible behavior a capable
`solo_claude` baseline is expected to miss, and the observable command from
`expected.json` that exposes it. If the hypothesis is only "the task is hard",
rework the candidate instead of measuring it. `lint-shadow-fixtures.sh` and the
candidate runners enforce this as an actionable hypothesis: the fixture
`spec.md` must contain `solo-headroom hypothesis`, `solo_claude`, `miss`, and a
backticked observable command matching `expected.json`, with the backticked line
itself containing `miss` and framed as the command/observable that exposes it.

Each new unmeasured high-risk shadow candidate also needs a `## Solo ceiling avoidance`
section in `NOTES.md` before provider spend. Name how the fixture is
different from the calibrated solo-saturated controls (`S2`-`S6`) and why that
difference is expected to preserve `solo_claude` headroom. If the note cannot
name a concrete difference, rework the candidate instead of measuring it.

If real shadow headroom shows the fixture is solo-saturated or otherwise fails
candidate headroom, record the run id and scores in that fixture's `NOTES.md`
under `Calibration status`, and add the `S*` id to
`../scripts/pair-rejected-fixtures.sh`. `bash scripts/lint-shadow-fixtures.sh`
fails when `NOTES.md` records a headroom gate `FAIL` that is not in the rejected
registry. Use `--allow-rejected-fixtures` only for diagnostics, not for new
pair-evidence spending.

## File layout per task

Each `S<N>-<slug>/` directory contains the standard 6 fixture files per `../fixtures/SCHEMA.md`:

- `metadata.json` — id / category / difficulty / timeout / browser / intent
- `spec.md` — resolve-ready spec
- `task.txt` — bare-arm input
- `expected.json` — verification_commands + forbidden_patterns + required_files
- `setup.sh` — deterministic starting state (empty if no setup needed)
- `NOTES.md` — why this fixture exists, retirement criteria

Plus the task-specific failure-class trap encoded in `expected.json.forbidden_patterns` and the spec's Constraints/Out-of-Scope sections.

## Lint

`bash scripts/lint-shadow-fixtures.sh` runs schema validity + structural checks
across all shadow tasks. Must pass before any bare/solo/pair measurement.
