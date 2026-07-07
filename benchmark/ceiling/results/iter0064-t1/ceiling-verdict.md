# Ceiling Verdict

Claim shape: current devlyn stack (sonnet orchestrator + codex executor) vs codex bare/copycat, matched wall

Verdict: **FAIL-pilot**

## Per-Task Rows

| task | status | selected B | selected C | A resolved | B resolved | C resolved | N | wall ratio |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| SW1-django-13230 | VALID | B1 | C1 | True | False | False | 3 | 5.304 |
| SW2-django-13265 | VALID | B1 | C2 | True | False | False | 3 | 6.923 |
| FS1-schedule-max-runs | VALID | B1 | C1 | False | True | True | 1 | 0.736 |

## Loss Conditions

- LC1 stack vs bare: A=2 vs best-B=1.
- LC2 moat: objective_moat=True; ranked_axes_mode=low-confidence-annex; ranked_counts={'A_win': 0, 'C_win': 8, 'tie': 0, 'total': 8}.
- LC3 mean wall ratio: 4.320868851408265.
- LC4 invalid reasons: none.

## Leave-One-Out

- Excluding SW1-django-13230: objective sums are A=1, best-B=1, best-C=1; LC1 relation A==B, objective moat relation A<=C.
- Excluding SW2-django-13265: objective sums are A=1, best-B=1, best-C=1; LC1 relation A==B, objective moat relation A<=C.
- Excluding FS1-schedule-max-runs: objective sums are A=2, best-B=0, best-C=0; LC1 relation A>B, objective moat relation A>C.
