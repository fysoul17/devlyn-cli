"""Freeze 0265's schedule: one serial lane per config, core then screen; no execution occurs here."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARMS = ('A', 'B')
CONFIGS = ('claude', 'codex')
PANELS = (('B5', 'F10'), ('D3', 'D4', 'F11'))  # core, then screen


def generate():
    measured = []

    def block(task, config, replicate):
        arms = ARMS if replicate % 2 else ARMS[::-1]
        for arm in arms:
            measured.append((f'c{len(measured) + 1:03d}-{task}-{config}-{arm}-r{replicate}',
                             task, arm, config, replicate))

    for config in CONFIGS:
        for panel in PANELS:
            for replicate in range(1, 9):
                for task in panel:
                    block(task, config, replicate)
    smoke = [(f'smoke-{config}-{arm}', 'SMOKE', arm, config)
             for config in CONFIGS for arm in ARMS]
    return {'cells.tsv': measured, 'smoke.tsv': smoke}


def render(rows):
    return ''.join('\t'.join(map(str, row)) + '\n' for row in rows)


if __name__ == '__main__':
    for name, rows in generate().items():
        (HERE / name).write_text(render(rows))
