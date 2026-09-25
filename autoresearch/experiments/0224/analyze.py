"""Apply the frozen 0224 rules: analyze.py <screen-out> <decisions.json>. Reads verdicts and usage; never dispatches.

decisions.json holds root's recorded judgments (DESIGN "Before any rule is computed"):
{"adjudicated": {"<cell>": {"<row>": "PASS"|"FAIL"}}, "false_completion": [cells], "reproduced_severe": [cells]}
"""
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
CELLS = [line.split() for line in (HERE / 'cells.tsv').read_text().splitlines() if line and not line.startswith('#')]


def output_tokens(usage):
    """Output tokens over every recorded model; a lower bound when usage is PARTIAL."""
    total = sum(t['output'] for key in ('codex', 'claude_result', 'claude_nested') for t in (usage.get(key) or {}).values())
    for call in usage.get('reviews') or ():
        u = call.get('usage')
        if isinstance(u, dict):
            total += u['output_tokens'] if 'output_tokens' in u else sum(m.get('outputTokens', 0) for m in u.values())
    return total


def complete(verdict, adjudicated):
    """COMPLETE after adjudicating only NOT_TRIGGERED rows; any other failure keeps the cell incomplete."""
    if verdict['status'] != 'ADJUDICATE':
        return verdict['status'] == 'COMPLETE'
    rows = {r['id']: (adjudicated.get(r['id']) if r['status'] == 'NOT_TRIGGERED' else r['status'])
            for r in verdict['oracle']}
    if None in rows.values():
        raise ValueError(f'{verdict["cell"]}: NOT_TRIGGERED row without a recorded adjudication')
    assessed = all(a['complete'] for a in verdict['assessments']) and not any(a['severe'] for a in verdict['assessments'])
    return all(v == 'PASS' for v in rows.values()) and assessed and not verdict['scope_violations'] and all(
        c['exit_code'] == 0 for c in json.loads((Path(verdict['_dir']) / verdict['cell'] / 'checks.json').read_text())['public'])


def main(out, decisions):
    table = {}
    for name, task, arm, config in CELLS:
        verdict = json.loads((out / f'verdict-{name}.json').read_text())
        if verdict['status'] == 'STOP':
            raise ValueError(f'{name} is a STOP row; resolve it per DESIGN before analysis')
        usage = json.loads((out / name / 'usage.json').read_text())
        table[task, arm, config] = dict(
            cell=name, done=complete(dict(verdict, _dir=str(out)), decisions['adjudicated'].get(name, {})),
            wall=verdict['owner_seconds'], output=output_tokens(usage), usage=usage['completeness'],
            scope=bool(verdict['scope_violations']), disagree=verdict['assessor_disagreement'])
    tasks, outcome = ('I0185', 'D4'), {}
    for x in ("B'", 'C'):
        for k in ('claude', 'codex'):
            cells = [table[t, x, k] for t in tasks]
            loss = any((table[t, 'A', k]['done'] or table[t, 'F', k]['done']) and not table[t, x, k]['done'] for t in tasks)
            block = any(c['scope'] or c['cell'] in decisions['false_completion'] or c['cell'] in decisions['reproduced_severe']
                        for c in cells)
            quality = any(table[t, x, k]['done'] and not table[t, 'A', k]['done'] for t in tasks)
            efficiency = any(table[t, x, k]['done'] and table[t, 'F', k]['done'] and (
                table[t, x, k]['wall'] <= 0.7 * table[t, 'F', k]['wall'] or
                (table[t, x, k]['usage'] == 'COMPLETE' and table[t, x, k]['output'] <= 0.7 * table[t, 'F', k]['output']))
                for t in tasks)
            outcome[x, k] = dict(loss=loss, block=block, quality=quality, efficiency=efficiency,
                                 go=(quality or efficiency) and not loss and not block)
    for k in ('claude', 'codex'):  # coupling: a live B' keeps C unless C is blocked
        if outcome["B'", k]['go'] and not outcome['C', k]['block']:
            outcome['C', k]['go'] = True
    token = 'SCREEN:' + ';'.join(f'{x}=' + (','.join(k for k in ('claude', 'codex') if outcome[x, k]['go']) or 'none')
                                 for x in ("B'", 'C'))
    print(json.dumps(dict(cells={'/'.join(key): row for key, row in table.items()},
                          rules={'/'.join(key): row for key, row in outcome.items()}, token=token), indent=1))


if __name__ == '__main__':
    main(Path(sys.argv[1]), json.loads(Path(sys.argv[2]).read_text()))
