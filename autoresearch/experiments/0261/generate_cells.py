"""Freeze 0261's serial B/C, D4/F10 schedule; no execution occurs here."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARMS = ('B', 'C')


def generate():
    measured = []
    counts = {'d': 0, 'c': 0}

    def block(task, config, replicate, prefix):
        arms = ARMS if replicate % 2 else ARMS[::-1]
        for arm in arms:
            counts[prefix] += 1
            measured.append((f'{prefix}{counts[prefix]:03d}-{task}-{config}-{arm}-r{replicate}',
                             task, arm, config, replicate))

    for replicate in range(1, 17):
        block('D4', 'claude', replicate, 'd')
        block('F10', 'claude', replicate, 'c')
    smoke = [(f'smoke-claude-{arm}', 'SMOKE', arm, 'claude') for arm in ARMS]
    return {'cells.tsv': measured, 'smoke.tsv': smoke}


def render(rows):
    return ''.join(' '.join(map(str, row)) + '\n' for row in rows)


if __name__ == '__main__':
    for name, rows in generate().items():
        (HERE / name).write_text(render(rows))
