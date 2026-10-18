"""Frozen rp-d8 slots; smoke never contributes to measured outcomes."""

PAIRS = [('Z0', 'XY'), ('Z0', 'YX'), ('BV', 'XY'), ('Z0', 'XY'),
         ('Z0', 'YX'), ('BV', 'YX'), ('Z0', 'XY'), ('Z0', 'YX')]
SCHEDULE = [(f'm{2 * pair + offset + 1:02}', task, 'claude')
            for pair, (task, _) in enumerate(PAIRS) for offset in range(2)] + [
    ('g01', 'BV', 'codex'), ('g02', 'Z0', 'codex'), ('g03', 'BV', 'claude'),
    ('g04', 'Z0', 'claude'), ('g05', 'Z0', 'claude'), ('g06', 'BV', 'claude'),
    ('g07', 'BV', 'claude'), ('g08', 'Z0', 'claude')]
ARMS = dict(zip((row[0] for row in SCHEDULE), ''.join(order for _, order in PAIRS) + 'Y' * 8))


def smoke_slots(attempt=1):
    if type(attempt) is not int or attempt not in (1, 2):
        raise ValueError('smoke_attempt must be 1 or 2')
    prefix = 'smoke' if attempt == 1 else 'smoke2'
    return [(prefix + '-' + engine, 'SM', engine) for engine in ('claude', 'codex')]


def arm_for(name):
    if name in ARMS:
        return ARMS[name]
    if name not in {row[0] for attempt in (1, 2) for row in smoke_slots(attempt)}:
        raise ValueError('unregistered rp-d8 slot')
    return 'Y'


def effort_for(name):
    arm_for(name)
    return 'high'


def paired_slot(name):
    if name not in ARMS or not name.startswith('m'):
        raise ValueError('only measured slots have a paired control')
    index = int(name[1:])
    return f'm{index + 1 if index % 2 else index - 1:02}'
