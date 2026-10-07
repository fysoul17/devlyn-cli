"""Freeze all 0234 slots before screening; gated rows are recorded NOT_RUN later."""
from itertools import permutations
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
POOL = ('I0185', 'F16', 'F23', 'F25', 'F10', 'F11')
CONFIGS = ('claude', 'codex')
DEVELOPMENT_ORDER = {'claude': ('ABHP', 'PHBA'), 'codex': ('HAPB', 'BPAH')}


def render(rows):
    return ''.join(' '.join(map(str, row)) + '\n' for row in rows)


def generate():
    screening = [(f's{n:02d}-{task}-{config}-B-r1', task, 'B', config, 1)
                 for n, (task, config) in enumerate(((t, c) for t in POOL for c in CONFIGS), 1)]
    development, confirmation = [], []
    for index, task in enumerate(POOL):
        for config in CONFIGS:
            block = index * 2 + CONFIGS.index(config)
            for arm in 'ABHP':  # storage slots only; dispatch order depends on screened eligibility rank
                development.append((f'd{len(development)+1:02d}-{task}-{config}-{arm}-r1', task, arm, config, 1))
                if task == 'I0185' and arm == 'A':
                    development.append((f'd{len(development)+1:02d}-{task}-{config}-A-r2', task, 'A', config, 2))
            for rep in (1, 2):
                order = list(permutations('ABP'))[block % 6]
                if rep == 2:
                    order = order[::-1]
                for arm in order:
                    confirmation.append((f'c{len(confirmation)+1:02d}-{task}-{config}-{arm}-r{rep}', task, arm, config, rep))
    easy = []
    for task, config in ((t, c) for t in ('E1', 'E2') for c in CONFIGS):
        for arm in (('B', 'P') if (('E1', 'E2').index(task) + CONFIGS.index(config)) % 2 == 0 else ('P', 'B')):
            easy.append((f'e{len(easy)+1:02d}-{task}-{config}-{arm}-r1', task, arm, config, 1))
    smoke = [(f'smoke-{config}-{arm}', 'S2', arm, config)
             for index, config in enumerate(CONFIGS)
             for arm in (('H', 'P') if index % 2 == 0 else ('P', 'H'))]
    return {'screening.tsv': screening, 'cells.tsv': development + confirmation + easy, 'smoke.tsv': smoke}


def dispatch_order(out):
    """Resolve the two development block slots only after screening; cells.tsv freezes identities, not execution order."""
    import decide
    selected = decide.selected_tasks(out)
    rows = generate()['cells.tsv']
    ordered = []
    for config in CONFIGS:
        for slot, task in enumerate(selected[config]['development']):
            block = [row for row in rows if row[1] == task and row[3] == config and row[0].startswith('d')]
            for arm in DEVELOPMENT_ORDER[config][slot]:
                ordered.extend(row for row in block if row[2] == arm)
        for task in selected[config]['confirmation']:
            ordered.extend(row for row in rows if row[1] == task and row[3] == config and row[0].startswith('c'))
    ordered.extend(row for row in rows if row[0].startswith('e'))
    return ordered


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--dispatch-order':
        print(render(dispatch_order(Path(sys.argv[2]))), end='')
    else:
        for name, rows in generate().items():
            (HERE / name).write_text(render(rows))
