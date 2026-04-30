# Shadow fixtures

Frozen task suite for **bare-vs-L1 categorical reliability measurement**, parallel to the golden F1-F9 fixtures under `../fixtures/`.

## Why this exists

User direction 2026-04-30: real-project trial too expensive and not bare-comparable; instead generate small-but-tricky tasks inside the benchmark and run bare-vs-L1 on them. Codex deep R0 verdict: option (c) — frozen shadow suite alongside golden F1-F9, hybrid generation (LLM proposes → Codex/human curates → frozen).

## How this differs from `../fixtures/`

| | Golden (`../fixtures/F*`) | Shadow (`./S*`) |
|---|---|---|
| Purpose | Release-decision ship-gate | Categorical reliability measurement |
| Auto-discovered by `run-suite.sh` default | Yes | No |
| Discovery trigger | always | `--suite shadow` flag |
| Feeds `ship-gate.py` | Yes | No (per `--suite` segregation) |
| Frozen at iter? | Yes | Yes |

Shadow runs are read-only signals: they redirect work but cannot bless Mission 1 by themselves. F1-F9 still controls release.

## Suite versions

- **v0** (iter-0030 — this directory): 6 tasks, 1 per failure class. Mutations of F1-F9 reusing proven scaffolds.
- **v1** (iter-0033 candidate): 18 tasks (3 per class).
- **decision-grade** (iter-0035 candidate): 30 tasks (5 per class). Apply Codex 8-condition trust rule.

## Task naming

`S<N>-<slug>/` — uppercase `S` prefix differentiates from golden `F` prefix. Discovery globs `shadow-fixtures/S*/`.

## Running the shadow suite

```bash
bash benchmark/auto-resolve/scripts/run-suite.sh --suite shadow --dry-run    # list shadow tasks
bash benchmark/auto-resolve/scripts/run-suite.sh --suite shadow              # full run, n=1
bash benchmark/auto-resolve/scripts/run-suite.sh --suite shadow S1 S5        # specific shadow tasks
```

Default `--suite golden` keeps existing F1-F9 behavior unchanged.

## File layout per task

Each `S<N>-<slug>/` directory contains the standard 6 fixture files per `../fixtures/SCHEMA.md`:

- `metadata.json` — id / category / difficulty / timeout / browser / intent
- `spec.md` — auto-resolve-ready spec
- `task.txt` — bare-arm input
- `expected.json` — verification_commands + forbidden_patterns + required_files
- `setup.sh` — deterministic starting state (empty if no setup needed)
- `NOTES.md` — why this fixture exists, retirement criteria

Plus the task-specific failure-class trap encoded in `expected.json.forbidden_patterns` and the spec's Constraints/Out-of-Scope sections.

## Lint

`bash scripts/lint-shadow-fixtures.sh` runs schema validity + structural checks across all shadow tasks. Must pass before any L0/L1/L2 measurement.
