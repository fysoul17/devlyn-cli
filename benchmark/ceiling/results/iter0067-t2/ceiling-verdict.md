# Ceiling Verdict

Claim shape: current devlyn stack (sonnet orchestrator + codex executor) vs codex bare/copycat, matched wall

Verdict: **FAIL-pilot**

## Per-Task Rows

| task | status | selected B | selected C | A resolved | B resolved | C resolved | N | wall ratio |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| SW3-django-13315 | VALID | B1 | C1 | True | True | True | 3 | 6.396 |
| SW4-django-13321 | VALID | B1 | C1 | False | False | False | 3 | 9.686 |
| SW5-django-13401 | VALID | B1 | C1 | True | True | True | 3 | 8.904 |

## Loss Conditions

- LC1 stack vs bare: A=2 vs best-B=2.
- LC2 moat: objective_moat=False; ranked_axes_mode=certified-panel; ranked_counts={'A_win': 3, 'C_win': 16, 'tie': 1, 'total': 20}.
- LC3 mean wall ratio: 8.328677087942788.
- LC4 invalid reasons: none.

## Leave-One-Out

- Excluding SW3-django-13315: objective sums are A=1, best-B=1, best-C=1; LC1 relation A==B, objective moat relation A<=C.
- Excluding SW4-django-13321: objective sums are A=2, best-B=2, best-C=2; LC1 relation A==B, objective moat relation A<=C.
- Excluding SW5-django-13401: objective sums are A=1, best-B=1, best-C=1; LC1 relation A==B, objective moat relation A<=C.
- FS1-schedule-max-runs was not part of this run subset; FS1 leave-one-out sensitivity is not computable.
