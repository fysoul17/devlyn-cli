"""Apply the registered 0235 §5 rule to eight measured cells. Never dispatches models."""
from fractions import Fraction
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
CELLS = [line.split() for line in (HERE / 'cells.tsv').read_text().splitlines() if line and not line.startswith('#')]
HANG = 5400
JUDGMENTS = ('audited', 'false_completion', 'user_data_harm', 'adjudicated', 'severe', 'witnesses')

def complete(verdict, adjudicated):
    """COMPLETE after adjudicating only NOT_TRIGGERED rows (0224 rule 1)."""
    if verdict['status'] != 'ADJUDICATE':
        return verdict['status'] == 'COMPLETE'
    rows = {r['id']: (adjudicated.get(r['id']) if r['status'] == 'NOT_TRIGGERED' else r['status']) for r in verdict['oracle']}
    if None in rows.values():
        raise ValueError(f'{verdict["cell"]}: NOT_TRIGGERED row without a recorded adjudication')
    assessed = all(a['complete'] for a in verdict['assessments']) and not any(a['severe'] for a in verdict['assessments'])
    return all(v == 'PASS' for v in rows.values()) and assessed and not verdict['scope_violations'] and verdict['product_check_pass_public']


def rows(verdict, adjudicated, checks):
    """Pass/fail per public check and oracle row, NOT_TRIGGERED rows as adjudicated."""
    passed = {f'public:{i}': c['exit_code'] == 0 for i, c in enumerate(checks['public'])}
    for row in verdict['oracle']:
        status = adjudicated.get(row['id']) if row['status'] == 'NOT_TRIGGERED' else row['status']
        passed[row['id']] = status == 'PASS'
    return passed


def audit_gaps(name, verdict, decisions):
    gaps = [] if name in decisions.get('audited', ()) else [f'{name}: final report not audited']
    recorded = decisions.get('severe', {}).get(name, {})
    for assessment in verdict.get('assessments', ()):
        for index, _ in enumerate(assessment.get('severe_findings', ())):
            key = f'{assessment["route"]["engine"]}:{index}'
            entry = recorded.get(key) or {}
            witness = decisions.get('witnesses', {}).get(entry.get('witness'), {})
            if entry.get('disposition') == 'not_reproduced':
                continue
            if entry.get('disposition') != 'reproduced' or witness.get(name) is not True:
                gaps.append(f'{name}: severe finding {key} needs a disposition, and a reproduced one a witness that reproduces on this tree')
    return gaps


def sums(cells):
    """S and the six-cell sums; a usage sum is complete only when every cell's usage is COMPLETE."""
    group = dict(S=sum(c['complete'] for c in cells), wall=sum(Fraction(c['wall']) for c in cells))
    for key in ('input', 'output'):
        group[key] = sum(c[key] or 0 for c in cells)
        group[key + '_complete'] = all(c['usage'] and c[key] is not None for c in cells)
    return group


def cost_at_most(mine, theirs, key):
    """Registration §5: unknown usage on either arm leaves condition 6 unmet."""
    if theirs['S'] > 0 and mine['S'] == 0:
        return False
    if not mine.get(key + '_complete', True) or not theirs.get(key + '_complete', True):
        return None
    if theirs['S'] == 0:
        return Fraction(mine[key]) <= Fraction(5, 4) * Fraction(theirs[key])
    return Fraction(mine[key]) / mine['S'] <= Fraction(theirs[key]) / theirs['S']


def every(values):
    values = list(values)
    return False if False in values else None if None in values else True


def quality(cells, candidate, reference):
    found = {}
    for task in sorted({c['task'] for c in cells}):
        mine = [c for c in cells if c['task'] == task and c['arm'] == candidate]
        theirs = {c['replicate']: c for c in cells if c['task'] == task and c['arm'] == reference}
        count = lambda group, key: sum(c['rows'].get(key, False) for c in group)
        keys = set().union(*(c['rows'] for c in mine + list(theirs.values())))
        found[task] = dict(
            safe=not any(c['scope'] or c['false_completion'] or c['harm'] for c in mine),
            completion=sum(c['complete'] for c in mine) >= sum(c['complete'] for c in theirs.values()),
            rows=all(count(mine, key) >= count(theirs.values(), key) for key in keys),
            severe=all(c['reproduced'] <= theirs[c['replicate']]['reproduced'] for c in mine))
    return found


def report(cells):
    """Raw sums and per-success costs; unknown token sums retain only labeled lower bounds."""
    group = sums(cells)
    known = dict(wall=True, input=group.pop('input_complete'), output=group.pop('output_complete'))
    for key in ('input', 'output'):
        if not known[key]:
            group[key + '_lower_bound'], group[key] = group[key], None
    per = {key: float(group[key] / group['S']) if group['S'] and known[key] else None for key in known}
    return dict(group, wall=float(group['wall']), per_success=per)


def load(out, decisions):
    table, missing = {}, [f'decisions.json has no "{key}"' for key in JUDGMENTS if key not in decisions]
    for name, task, arm, config, replicate in CELLS:
        verdict = json.loads((out / f'verdict-{name}.json').read_text())
        if verdict.get('status') == 'STOP':
            raise ValueError(f'{name} is a STOP row: re-dispatch or regrade it before computing the rule')
        missing += audit_gaps(name, verdict, decisions)
        checks = json.loads((out / name / 'checks.json').read_text())
        verdict['product_check_pass_public'] = all(c['exit_code'] == 0 for c in checks['public'])
        adjudicated = decisions.get('adjudicated', {}).get(name, {})
        table[name] = dict(name=name, task=task, arm=arm, config=config, replicate=int(replicate),
                           complete=complete(verdict, adjudicated), rows=rows(verdict, adjudicated, checks),
                           scope=bool(verdict['scope_violations']), false_completion=name in decisions.get('false_completion', ()),
                           harm=name in decisions.get('user_data_harm', ()),
                           reproduced={w for w, trees in decisions.get('witnesses', {}).items() if trees.get(name) is True},
                           wall=HANG if verdict['owner_status'] == 'HANG_TIMEOUT' else verdict['owner_seconds'],
                           input=verdict.get('input_tokens'), output=verdict.get('output_tokens'),
                           usage=verdict.get('usage') == 'COMPLETE')
    if missing:
        raise ValueError('mandatory judgments are missing: ' + '; '.join(missing))
    return table


def rule(table, decisions):
    cells = list(table.values())
    r_cells = [c for c in cells if c['arm'] == 'R']
    b_cells = [c for c in cells if c['arm'] == 'B']
    q = quality(cells, 'R', 'B')
    r, b = sums(r_cells), sums(b_cells)
    cost = every(cost_at_most(r, b, key) for key in ('wall', 'input', 'output'))
    # Scope is a registered REJECT veto; include it in the safety gate so ADVANCE and REJECT stay exclusive.
    advance = dict(
        r_completes_all=len(r_cells) == 4 and r['S'] == 4,
        b_at_most_two_each_task_incomplete=b['S'] <= 2 and all(
            any(not c['complete'] for c in b_cells if c['task'] == task) for task in ('D3', 'D4')),
        rows=all(q[task]['rows'] for task in ('D3', 'D4')),
        no_false_completion_harm_or_scope=not any(c['scope'] or c['false_completion'] or c['harm'] for c in r_cells),
        witnessed=all(q[task]['severe'] for task in ('D3', 'D4')),
        cost=cost)
    reject = dict(r_completions_at_most_b=r['S'] <= b['S'],
                  r_safety_failure=any(c['scope'] or c['false_completion'] or c['harm'] for c in r_cells))
    advances = all(value is True for value in advance.values())
    rejects = any(value is True for value in reject.values())
    if advances and rejects:
        raise ValueError('ADVANCE and REJECT both hold')
    outcome = 'ADVANCE' if advances else 'REJECT' if rejects else 'INCONCLUSIVE'
    return dict(token='0235:claude=R/B:' + outcome, outcome=outcome, advance=advance, reject=reject,
                quality=q, completions={arm: {task: sum(c['complete'] for c in group if c['task'] == task)
                                            for task in ('D3', 'D4')}
                                        for arm, group in (('B', b_cells), ('R', r_cells))},
                sums={'B': report(b_cells), 'R': report(r_cells)}, final_report=decisions.get('final_report', {}))


def main(out, decisions_path):
    decisions = json.loads(Path(decisions_path).read_text())
    out = Path(out)
    result = rule(load(out, decisions), decisions)
    (out / 'decision.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    main(*sys.argv[1:3])
