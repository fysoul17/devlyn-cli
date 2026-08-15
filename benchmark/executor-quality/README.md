# Executor quality

This instrument measures design and implementation failures made by the main-AI executor on small, self-contained coding tasks. Each task has one visible-contract behavioral invariant and a hidden, deterministic oracle with multiple independent manifestations. The cohort scorer compares `claude-opus-5` with `claude-fable-5` using the paired per-task difference in manifestation-failure rate.

This corpus-build stage retains the complete 12-task iteration 0100 corpus: three tasks per taxonomy class. The iteration 0101 hard corpus in `tasks-0101/` currently admits `EQ2-UA1`, `EQ2-UA2`, `EQ2-UA3`, `EQ2-UA4`, `EQ2-UA5`, `EQ2-UA6`, `EQ2-UA7`, `EQ2-UA8`, `EQ2-MI1`, `EQ2-MI2`, `EQ2-MI3`, `EQ2-MI4`, `EQ2-MI5`, `EQ2-MI6`, `EQ2-MI7`, `EQ2-MI8`, `EQ2-AF1`, `EQ2-AF2`, `EQ2-AF3`, `EQ2-AF4`, `EQ2-AF5`, `EQ2-AF6`, `EQ2-AF7`, `EQ2-AF8`, `EQ2-BD1`, `EQ2-BD2`, `EQ2-BD3`, `EQ2-BD4`, `EQ2-BD5`, `EQ2-BD6`, `EQ2-BD7`, and `EQ2-BD8`; `validate-hard-task.py` wraps the frozen validator, and `score-calibration.py` scores the calibration band. It does not run scored arms, seal either complete corpus, or integrate the cell with seat recertification.

The iteration 0102 pilot stage in `tasks-0102-pilot/` admits `EQ3P-UA1`, `EQ3P-MI1`, `EQ3P-AF1`, and `EQ3P-BD1`; standalone `validate-discovery-task.py` validates its prototypes, and `score-pilot.py` scores its pilot ledger. These prototypes are discarded instruments; the corpus lives in `tasks-0102/`, authored by later batches.

The iteration 0102 corpus stage in `tasks-0102/` currently admits `EQ3-UA1`, `EQ3-UA2`, `EQ3-UA3`, `EQ3-UA4`, `EQ3-UA5`, `EQ3-MI1`, `EQ3-MI2`, `EQ3-MI3`, `EQ3-MI4`, `EQ3-MI5`, `EQ3-AF1`, `EQ3-AF2`, `EQ3-AF3`, `EQ3-AF4`, `EQ3-AF5`, `EQ3-BD1`, `EQ3-BD2`, `EQ3-BD3`, `EQ3-BD4`, and `EQ3-BD5`; standalone `validate-discovery-task.py` validates its tasks, and `score-calibration.py` and `score-cohort.py` gate the EQ3 set.

## Validate the instrument

Run the validator self-test and admit each exemplar from the repository root:

```bash
python3 benchmark/executor-quality/scripts/validate-task.py --self-test
for t in EQ-UA1 EQ-UA2 EQ-UA3 EQ-MI1 EQ-MI2 EQ-MI3 EQ-AF1 EQ-AF2 EQ-AF3 EQ-BD1 EQ-BD2 EQ-BD3; do python3 benchmark/executor-quality/scripts/validate-task.py --task benchmark/executor-quality/tasks/$t || exit 1; done
python3 benchmark/executor-quality/scripts/validate-hard-task.py --self-test
for t in EQ2-UA1 EQ2-UA2 EQ2-UA3 EQ2-UA4 EQ2-UA5 EQ2-UA6 EQ2-UA7 EQ2-UA8 EQ2-MI1 EQ2-MI2 EQ2-MI3 EQ2-MI4 EQ2-MI5 EQ2-MI6 EQ2-MI7 EQ2-MI8 EQ2-AF1 EQ2-AF2 EQ2-AF3 EQ2-AF4 EQ2-AF5 EQ2-AF6 EQ2-AF7 EQ2-AF8 EQ2-BD1 EQ2-BD2 EQ2-BD3 EQ2-BD4 EQ2-BD5 EQ2-BD6 EQ2-BD7 EQ2-BD8; do python3 benchmark/executor-quality/scripts/validate-hard-task.py --task benchmark/executor-quality/tasks-0101/$t || exit 1; done
for t in EQ3-UA1 EQ3-UA2 EQ3-UA3 EQ3-UA4 EQ3-UA5 EQ3-MI1 EQ3-MI2 EQ3-MI3 EQ3-MI4 EQ3-MI5 EQ3-AF1 EQ3-AF2 EQ3-AF3 EQ3-AF4 EQ3-AF5 EQ3-BD1 EQ3-BD2 EQ3-BD3 EQ3-BD4 EQ3-BD5; do python3 benchmark/executor-quality/scripts/validate-discovery-task.py --task benchmark/executor-quality/tasks-0102/$t || exit 1; done
python3 benchmark/executor-quality/scripts/score-calibration.py --self-test
python3 benchmark/executor-quality/scripts/score-cohort.py --self-test
```

Task validation checks structure, visible-contract bindings, hidden-ground-truth leakage, and the no-op/gold/symptom patch semantics in fresh temporary copies. It requires Python 3 and the POSIX `patch` utility; even-index EQ2 and EQ3 fixtures additionally require Node ≥20.

## Score a cohort

```bash
python3 benchmark/executor-quality/scripts/score-cohort.py --ledger <ledger.jsonl>
```

The default validity gate requires the frozen 128-row matrix: two exact engine IDs, 32 EQ3 tasks, and two reps. For a pilot ledger, pass `--expected-tasks N`; all other validity and attestation rules remain binding. A valid cohort prints one deterministic JSON verdict. An invalid or infrastructure-invalid cohort prints `UNSCORED` and exits 3.

## Binding rules

The preregistered corpus, arm-isolation, metric, bootstrap, terminal-precedence, freeze, and rerun rules are canonical in [iteration 0100](../../autoresearch/iterations/0100-main-ai-executor-quality.md) and [iteration 0101](../../autoresearch/iterations/0101-executor-quality-hard-corpus.md). This guide summarizes operation only; changes to the instrument must preserve those registrations.
