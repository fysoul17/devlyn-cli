"""Freeze 0256's two-arm registered order; no execution occurs here."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARMS = ('A', 'B')
CONFIGS = ('claude', 'codex')


def panel(tasks, repeats, prefix):
    blocks = [(task, config, t, c) for t, task in enumerate(tasks)
              for c, config in enumerate(CONFIGS)]
    rows = []
    for replicate in range(1, repeats + 1):
        ordered = blocks if replicate == 1 else reversed(blocks)
        for task, config, t, c in ordered:
            arms = ARMS if (t + c) % 2 == 0 else ARMS[::-1]
            if replicate == 2:
                arms = arms[::-1]
            for arm in arms:
                rows.append((f'{prefix}{len(rows)+1:02d}-{task}-{config}-{arm}-r{replicate}',
                             task, arm, config, replicate))
    return rows


def render(rows):
    return ''.join(' '.join(map(str, row)) + '\n' for row in rows)


def generate():
    measured = (panel(('D3', 'D4', 'I0185', 'B5'), 2, 'd')
                + panel(('E1', 'E2'), 1, 'e')
                + panel(('F10', 'F11'), 2, 'c'))
    smoke = [(f'smoke-{config}-{arm}', 'SMOKE', arm, config)
             for config in CONFIGS for arm in ARMS]
    return {'cells.tsv': measured, 'smoke.tsv': smoke}


if __name__ == '__main__':
    for name, rows in generate().items():
        (HERE / name).write_text(render(rows))
