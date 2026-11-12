"""Freeze 0266's schedules (DESIGN "Stage S", "Stage R" Panel); no execution occurs here.

cells.tsv   the registered run, 176 rows <name> <task> <arm> <config> <replicate>: one serial lane per engine; a block
            is one (task, engine, replicate), its two arms back to back, B then C on odd replicates and C then B on
            even ones. Claude: for r = 1..16 the F10 block then the F11 block, then for r = 1..8 the B5, D3 and D4
            blocks. Codex: for r = 1..8 the B5, F10, F11 and D3 blocks. Arm C is the screen decision's candidate.
screen.tsv  the wording screen, 18 Claude rows <name> <task> C-K<n> claude <replicate>: per candidate 4 F10 and 2 F11
            cells, in six rounds of one cell per candidate (F10, F11, F10, F10, F11, F10), the candidates' order
            rotating each round, so no candidate runs all its cells first.
smoke.tsv   SMOKE, 0265's shape: both engines, arms B and C (C-K3's package; SMOKE says nothing about a candidate).
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARMS = ('B', 'C')
CANDIDATES = ('K1', 'K2', 'K3')
LANES = (('claude', ((16, ('F10', 'F11')), (8, ('B5', 'D3', 'D4')))),
         ('codex', ((8, ('B5', 'F10', 'F11', 'D3')),)))
ROUNDS = ('F10', 'F11', 'F10', 'F10', 'F11', 'F10')


def generate():
    measured = []
    for config, phases in LANES:
        for replicates, tasks in phases:
            for replicate in range(1, replicates + 1):
                for task in tasks:
                    for arm in (ARMS if replicate % 2 else ARMS[::-1]):
                        measured.append((f'c{len(measured) + 1:03d}-{task}-{config}-{arm}-r{replicate}',
                                         task, arm, config, replicate))
    screen, done = [], {}
    for number, task in enumerate(ROUNDS):
        for candidate in CANDIDATES[number % 3:] + CANDIDATES[:number % 3]:
            replicate = done[task, candidate] = done.get((task, candidate), 0) + 1
            screen.append((f's{len(screen) + 1:02d}-{task}-claude-{candidate}-r{replicate}', task, f'C-{candidate}',
                           'claude', replicate))
    smoke = [(f'smoke-{config}-{arm}', 'SMOKE', 'C-K3' if arm == 'C' else arm, config)
             for config in ('claude', 'codex') for arm in ARMS]
    return {'cells.tsv': measured, 'screen.tsv': screen, 'smoke.tsv': smoke}


def render(rows):
    return ''.join('\t'.join(map(str, row)) + '\n' for row in rows)


if __name__ == '__main__':
    for name, rows in generate().items():
        (HERE / name).write_text(render(rows))
