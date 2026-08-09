# Executor quality

This instrument measures design and implementation failures made by the main-AI executor on small, self-contained coding tasks. Each task has one visible-contract behavioral invariant and a hidden, deterministic oracle with multiple independent manifestations. The cohort scorer compares `claude-opus-5` with `claude-fable-5` using the paired per-task difference in manifestation-failure rate.

This corpus-build stage contains three exemplar tasks only. It does not run scored arms, seal the complete 12-task corpus, or integrate the cell with seat recertification.

## Validate the instrument

Run the validator self-test and admit each exemplar from the repository root:

```bash
python3 benchmark/executor-quality/scripts/validate-task.py --self-test
python3 benchmark/executor-quality/scripts/validate-task.py --task benchmark/executor-quality/tasks/EQ-UA1
python3 benchmark/executor-quality/scripts/validate-task.py --task benchmark/executor-quality/tasks/EQ-MI1
python3 benchmark/executor-quality/scripts/validate-task.py --task benchmark/executor-quality/tasks/EQ-AF1
python3 benchmark/executor-quality/scripts/score-cohort.py --self-test
```

Task validation checks structure, visible-contract bindings, hidden-ground-truth leakage, and the no-op/gold/symptom patch semantics in fresh temporary copies. It requires Python 3 and the POSIX `patch` utility.

## Score a cohort

```bash
python3 benchmark/executor-quality/scripts/score-cohort.py --ledger <ledger.jsonl>
```

The default validity gate requires the frozen 48-row matrix: two exact engine IDs, 12 tasks, and two reps. For a pilot ledger, pass `--expected-tasks N`; all other validity and attestation rules remain binding. A valid cohort prints one deterministic JSON verdict. An invalid or infrastructure-invalid cohort prints `UNSCORED` and exits 3.

## Binding rules

The preregistered corpus, arm-isolation, metric, bootstrap, terminal-precedence, freeze, and rerun rules are canonical in [iteration 0100](../../autoresearch/iterations/0100-main-ai-executor-quality.md). This guide summarizes operation only; changes to the instrument must preserve that registration.
