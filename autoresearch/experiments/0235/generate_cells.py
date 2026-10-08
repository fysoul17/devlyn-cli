"""Freeze the registered 0235 dispatch order; no execution occurs here."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
MEASURED = (
    ('r01-D3-claude-B-r1', 'D3', 'B', 'claude', 1),
    ('r02-D3-claude-R-r1', 'D3', 'R', 'claude', 1),
    ('r03-D4-claude-R-r1', 'D4', 'R', 'claude', 1),
    ('r04-D4-claude-B-r1', 'D4', 'B', 'claude', 1),
    ('r05-D3-claude-R-r2', 'D3', 'R', 'claude', 2),
    ('r06-D3-claude-B-r2', 'D3', 'B', 'claude', 2),
    ('r07-D4-claude-B-r2', 'D4', 'B', 'claude', 2),
    ('r08-D4-claude-R-r2', 'D4', 'R', 'claude', 2),
)
SMOKE = (('s01-E1-claude-R', 'E1', 'R', 'claude'),)


def render(rows):
    return ''.join(' '.join(map(str, row)) + '\n' for row in rows)


def generate():
    return {'cells.tsv': MEASURED, 'smoke.tsv': SMOKE}


if __name__ == '__main__':
    for name, rows in generate().items():
        (HERE / name).write_text(render(rows))
