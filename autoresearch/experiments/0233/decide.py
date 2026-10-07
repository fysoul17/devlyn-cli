"""Apply 0232 §6 dominance separately to development, easy and eligible confirmation panels.

Screening determines headroom; easy tripwires are reported only. No model is dispatched.
"""
from fractions import Fraction
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
CELLS = [line.split() for line in (HERE / 'cells.tsv').read_text().splitlines() if line and not line.startswith('#')]
SCREENING = [line.split() for line in (HERE / 'screening.tsv').read_text().splitlines() if line and not line.startswith('#')]
PANELS = {'development': {'D3', 'D4', 'I0185', 'B5'}, 'easy': {'E1', 'E2'},
          'confirmation': {'F10', 'F11'}}
HANG = 5400
JUDGMENTS = ('audited', 'false_completion', 'user_data_harm', 'adjudicated', 'severe', 'witnesses')
OUTCOME = {True: 'PASS', False: 'FAIL', None: 'INCONCLUSIVE'}


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


def eligibility(out):
    """A task/config has headroom when any of its four A/B screening cells misses completion or an oracle row."""
    eligible = {}
    for task in PANELS['confirmation']:
        for config in ('claude', 'codex'):
            names = [name for name, t, _, c, _ in SCREENING if t == task and c == config]
            if len(names) != 4:
                raise ValueError(f'{task}/{config}: expected four screening cells')
            verdicts = [json.loads((out / f'verdict-{name}.json').read_text()) for name in names]
            if any(v['status'] == 'STOP' for v in verdicts):
                raise ValueError(f'{task}/{config}: screening STOP')
            eligible[(task, config)] = any(v['status'] != 'COMPLETE' or
                                           any(row['status'] != 'PASS' for row in v['oracle']) for v in verdicts)
    return eligible


def load(out, decisions, eligible):
    table, missing = {}, [f'decisions.json has no "{key}"' for key in JUDGMENTS if key not in decisions]
    for name, task, arm, config, replicate in CELLS:
        if task in PANELS['confirmation'] and not eligible[(task, config)]:
            skipped = out / f'verdict-{name}.json'
            if not skipped.is_file() or json.loads(skipped.read_text()).get('status') != 'NOT_RUN':
                missing.append(f'{name}: ineligible confirmation cell must be recorded NOT_RUN')
            continue
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


def sums(cells):
    """S and the six-cell sums; a usage sum is complete only when every cell's usage is COMPLETE."""
    group = dict(S=sum(c['complete'] for c in cells), wall=sum(Fraction(c['wall']) for c in cells))
    for key in ('input', 'output'):
        group[key] = sum(c[key] or 0 for c in cells)
        group[key + '_complete'] = all(c['usage'] and c[key] is not None for c in cells)
    return group


def at_most(mine, theirs, key, factor=1, strict=False):
    """Whether the candidate's per-success cost is at most (strict: below) factor x the reference's: True, False, or
    None when missing usage leaves it open. Wall is always known. The candidate has S > 0."""
    if theirs['S'] == 0:
        return True
    if not mine.get(key + '_complete', True):
        return None
    own, bound = Fraction(mine[key]) / mine['S'], factor * Fraction(theirs[key]) / theirs['S']
    if own < bound or (own == bound and not strict):
        return True
    return False if theirs.get(key + '_complete', True) else None


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


def compare(cells, candidate, reference, wall_factor, strict):
    mine, theirs = (sums([c for c in cells if c['arm'] == arm]) for arm in (candidate, reference))
    result = dict(candidate=candidate, reference=reference, quality=quality(cells, candidate, reference))
    if mine['S'] == 0:
        return dict(result, outcome='NO_CLAIM')
    if theirs['S'] == 0:
        result['reason'] = 'dominance over a zero-success incumbent'
    result['tests'] = dict(wall=at_most(mine, theirs, 'wall', wall_factor), input=at_most(mine, theirs, 'input'),
                           output=at_most(mine, theirs, 'output'))
    conditions = [all(all(q.values()) for q in result['quality'].values()), *result['tests'].values()]
    if strict:
        lower = [mine['S'] > theirs['S'], *(at_most(mine, theirs, key, strict=True) for key in ('wall', 'input', 'output'))]
        result['strictly_better'] = True if True in lower else None if None in lower else False
        conditions.append(result['strictly_better'])
    return dict(result, outcome=OUTCOME[every(conditions)])


def report(cells):
    """Raw sums and per-success costs; unknown token sums retain only labeled lower bounds."""
    group = sums(cells)
    known = dict(wall=True, input=group.pop('input_complete'), output=group.pop('output_complete'))
    for key in ('input', 'output'):
        if not known[key]:
            group[key + '_lower_bound'], group[key] = group[key], None
    per = {key: float(group[key] / group['S']) if group['S'] and known[key] else None for key in known}
    return dict(group, wall=float(group['wall']), per_success=per)


def panel_rule(cells):
    return dict(comparisons={f'{candidate}/{reference}': compare(cells, candidate, reference, 1, strict=True)
                             for candidate, reference in (('B', 'A'), ('C', 'B'), ('C', 'A'))},
                sums={arm: report([c for c in cells if c['arm'] == arm]) for arm in ('A', 'B', 'C')})


def easy_tripwire(panel):
    b, c = (panel['sums'][arm] for arm in ('B', 'C'))
    if c['S'] < b['S']:
        return 'TRIGGERED:completion'
    for key in ('wall', 'input', 'output'):
        if b[key] is None or c[key] is None:
            return 'UNKNOWN:usage'
        if Fraction(c[key]) > Fraction(5, 4) * Fraction(b[key]):
            return 'TRIGGERED:' + key
    return 'CLEAR'


def config_rule(table, config, eligible):
    panels = {}
    for name, tasks in PANELS.items():
        cells = [c for c in table.values() if c['config'] == config and c['task'] in tasks]
        panels[name] = panel_rule(cells) if cells else dict(
            status='NO_HEADROOM', comparisons={pair: {'outcome': 'NO_HEADROOM'} for pair in ('B/A', 'C/B', 'C/A')},
            sums={arm: report([]) for arm in ('A', 'B', 'C')})
    panels['easy']['tripwire'] = easy_tripwire(panels['easy'])
    dev = panels['development']['comparisons']
    conf = panels['confirmation']
    # Confirmation judges C only (C/B and C/A); B/A there is reported, never gating. A zero-success C fails
    # confirmation when B or A completes there, and leaves it UNCONFIRMED when no arm does.
    sums_ = conf['sums']
    candidate = [conf['comparisons'][pair]['outcome'] for pair in ('C/B', 'C/A')]
    quality_failed = any(not all(conf['comparisons'][pair]['quality'][task].values())
                         for pair in ('C/B', 'C/A') for task in conf['comparisons'][pair].get('quality', {}))
    conf_status = ('NO_HEADROOM' if conf.get('status') == 'NO_HEADROOM' else
                   'FAIL' if quality_failed or 'FAIL' in candidate or
                   (sums_['C']['S'] == 0 and (sums_['B']['S'] or sums_['A']['S'])) else
                   'PASS' if candidate == ['PASS', 'PASS'] else 'UNCONFIRMED')
    admitted = (None if not dev['C/B']['outcome'] == dev['C/A']['outcome'] == 'PASS' or conf_status == 'FAIL' else
                'C' if conf_status == 'PASS' else 'C-unconfirmed')
    return dict(panels=panels, confirmation=conf_status, admitted=admitted,
                eligibility={task: eligible[(task, config)] for task in sorted(PANELS['confirmation'])})


def main(out, decisions_path):
    decisions = json.loads(Path(decisions_path).read_text())
    out = Path(out)
    eligible = eligibility(out)
    table = load(out, decisions, eligible)
    result = {config: config_rule(table, config, eligible) for config in ('claude', 'codex')}
    token = '0233:' + ';'.join(
        f'{c}=B/A:{result[c]["panels"]["development"]["comparisons"]["B/A"]["outcome"]},'
        f'C/B:{result[c]["panels"]["development"]["comparisons"]["C/B"]["outcome"]},'
        f'C/A:{result[c]["panels"]["development"]["comparisons"]["C/A"]["outcome"]},'
        f'conf:{result[c]["confirmation"]},adm:{result[c]["admitted"] or "none"}' for c in ('claude', 'codex'))
    outcome = dict(token=token, configs=result)
    (out / 'decision.json').write_text(json.dumps(outcome, indent=2) + '\n')
    print(json.dumps(outcome, indent=2))
    return outcome


if __name__ == '__main__':
    main(*sys.argv[1:3])
