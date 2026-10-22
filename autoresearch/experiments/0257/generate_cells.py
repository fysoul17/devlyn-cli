"""Freeze 0257's serial, task-blocked schedule; no execution occurs here."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARMS = ('A', 'B')
CONFIGS = ('claude', 'codex')


def generate():
    measured = []
    counts = {'e': 0, 'd': 0, 'c': 0}

    def block(task, config, replicate, prefix):
        arms = ARMS if replicate % 2 else ARMS[::-1]
        for arm in arms:
            counts[prefix] += 1
            measured.append((f'{prefix}{counts[prefix]:03d}-{task}-{config}-{arm}-r{replicate}',
                             task, arm, config, replicate))

    for task in ('E1', 'E2'):
        for config in CONFIGS:
            block(task, config, 1, 'e')
    for replicate in range(1, 17):
        for task in ('D3', 'D4', 'I0185', 'B5'):
            for config in CONFIGS:
                block(task, config, replicate, 'd')
        if replicate % 2 == 0:
            for task in ('F10', 'F11'):
                for config in CONFIGS:
                    block(task, config, replicate // 2, 'c')
    smoke = [(f'smoke-{config}-{arm}', 'SMOKE', arm, config)
             for config in CONFIGS for arm in ARMS]
    return {'cells.tsv': measured, 'smoke.tsv': smoke}


def render(rows):
    return ''.join(' '.join(map(str, row)) + '\n' for row in rows)


if __name__ == '__main__':
    for name, rows in generate().items():
        (HERE / name).write_text(render(rows))
