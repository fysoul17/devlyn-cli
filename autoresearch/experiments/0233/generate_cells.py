"""Freeze the registered 0233 dispatch order; no execution occurs here."""
from itertools import permutations
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARMS = ('A', 'B', 'C')
CONFIGS = ('claude', 'codex')
ORDERS = [''.join(p) for p in permutations(ARMS)]


def blocks(tasks):
    return [(task, config) for task in tasks for config in CONFIGS]


def panel(tasks, repeats, prefix):
    groups = blocks(tasks)
    rows = []
    for replicate in range(1, repeats + 1):
        ordered = groups if replicate == 1 else list(reversed(groups))
        for task, config in ordered:
            index = groups.index((task, config)) // 2 + (2 if config == 'codex' else 0)
            arms = ORDERS[index % 6]
            if replicate == 2:
                arms = arms[::-1]
            for arm in arms:
                rows.append((f'{prefix}{len(rows)+1:02d}-{task}-{config}-{arm}-r{replicate}', task, arm, config, replicate))
    return rows


def render(rows):
    return ''.join(' '.join(map(str, row)) + '\n' for row in rows)


def generate():
    measured = (panel(('D3', 'D4', 'I0185', 'B5'), 2, 'd')
                + panel(('E1', 'E2'), 1, 'e')
                + panel(('F10', 'F11'), 2, 'c'))
    screening = [(f's{n:02d}-{task}-{config}-{arm}-r{replicate}', task, arm, config, replicate)
                 for n, (task, config, replicate, arm) in enumerate(
                     ((task, config, rep, arm) for task in ('F10', 'F11') for config in CONFIGS
                      for rep in (1, 2) for arm in ('A', 'B')), 1)]
    smoke = [(f'smoke-{config}-{arm}', 'SMOKE', arm, config) for config in CONFIGS for arm in ARMS]
    return {'cells.tsv': measured, 'screening.tsv': screening, 'smoke.tsv': smoke}


if __name__ == '__main__':
    for name, rows in generate().items():
        (HERE / name).write_text(render(rows))
