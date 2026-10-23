"""0257 pooled B/A decision. Frozen endpoints, exact Fisher/Holm and Wilson-MOVER sign reading."""
import json
import math
from fractions import Fraction
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
CELLS = [line.split() for line in (HERE / 'cells.tsv').read_text().splitlines() if line and not line.startswith('#')]
PANELS = {'development': ('D3', 'D4', 'I0185', 'B5'), 'easy': ('E1', 'E2'),
          'confirmation': ('F10', 'F11')}
ENDPOINTS = json.loads((HERE / 'endpoints.json').read_text())
BINDING = {w for task in ENDPOINTS['development'].values() for w in task['witnesses']}
HANG = 5400
JUDGMENTS = ('audited', 'false_completion', 'user_data_harm', 'adjudicated', 'severe', 'witnesses')


def validate_endpoints():
    """Fail on invented, omitted or duplicate frozen row IDs before reading an outcome."""
    source = json.loads((HERE.parent / '0233/tasks.json').read_text())
    oracle_source = (HERE.parent / '0233/oracle.js').read_text()
    tasks = {task['id']: task for task in source['tasks']}
    observed = json.loads((HERE / 'fixtures/endpoint-ids.json').read_text())
    # The D oracle's six/four IDs are defined in 0207/calibrate.py, invoked by 0222/check.py.
    d_rows = {'D3': {f'D3.{i}' for i in range(1, 7)},
              'D4': {'D4.1-2', 'D4.3', 'D4.4', 'D4.5'}}
    for panel, expected in (('development', 43), ('confirmation', 11)):
        family = ENDPOINTS[panel]
        if set(family) != set(PANELS[panel]):
            raise ValueError(f'{panel}: endpoint tasks differ from frozen panel')
        count = 0
        for task, group in family.items():
            actual = {f'public:{i}' for i in range(len(tasks[task]['public_checks']))}
            actual |= d_rows[task] if task in d_rows else set(tasks[task]['oracle'])
            if set(observed[task]['oracle_ids']) != actual - {key for key in actual if key.startswith('public:')}:
                raise ValueError(f'{task}: 0256 verdict row IDs disagree with frozen endpoints')
            if group['completion'] != ['complete'] or set(group['rows']) != actual or len(group['rows']) != len(actual):
                raise ValueError(f'{task}: endpoint row ID missing, invented or duplicated')
            if task in ('B5', 'F10', 'F11') and any(f"'{row}'" not in oracle_source
                                                     for row in group['rows'] if not row.startswith('public:')):
                raise ValueError(f'{task}: endpoint row absent from 0233/oracle.js')
            if task in ('D3', 'B5', 'F10', 'F11') and group['witnesses']:
                raise ValueError(f'{task}: unexpected binding witness')
            count += 1 + len(group['rows']) + len(group['witnesses'])
        if count != expected:
            raise ValueError(f'{panel}: expected {expected} endpoints, got {count}')
    frozen = json.loads((HERE.parent / '0256/results/decisions.json').read_text())['witnesses']
    if not BINDING <= set(frozen):
        raise ValueError('binding witness absent from 0256 decisions')
    return True


def fisher(a, b, n, adverse='lower'):
    """One-sided exact hypergeometric p for B successes; adverse=upper for defects."""
    if adverse not in ('lower', 'upper') or not 0 <= a <= n or not 0 <= b <= n:
        raise ValueError('invalid Fisher counts')
    if (adverse == 'lower' and b >= a) or (adverse == 'upper' and b <= a):
        return 1.0
    total = a + b
    low, high = max(0, total - n), min(n, total)
    denominator = math.comb(2 * n, n)
    relevant = range(low, b + 1) if adverse == 'lower' else range(b, high + 1)
    return sum(math.comb(total, x) * math.comb(2 * n - total, n - x)
               for x in relevant) / denominator


def holm(raw):
    """Monotone Holm adjusted p values, preserving the endpoint insertion order."""
    result = {}
    previous = 0.0
    for rank, (key, p) in enumerate(sorted(raw.items(), key=lambda item: item[1])):
        previous = max(previous, min(1.0, (len(raw) - rank) * p))
        result[key] = previous
    return {key: result[key] for key in raw}


def sign_interval(counts):
    """Equal-weight Wilson-MOVER equation in DESIGN; counts maps task to A/B counts out of 16."""
    z = 1.96
    terms = []
    for pair in counts.values():
        values = {}
        for arm in ('A', 'B'):
            s = pair[arm]
            if not 0 <= s <= 16:
                raise ValueError('D requires sixteen slots per task and arm')
            den = 16 + z * z
            mid = (s + z * z / 2) / den
            half = z * math.sqrt(s * (16 - s) / 16 + z * z / 4) / den
            values[arm] = (s / 16, mid - half, mid + half)
        (pa, la, ua), (pb, lb, ub) = values['A'], values['B']
        terms.append((pb - pa, (pb - lb)**2 + (ua - pa)**2,
                      (ub - pb)**2 + (pa - la)**2))
    if len(terms) != 4:
        raise ValueError('D requires four development tasks')
    d = sum(t[0] for t in terms) / 4
    lo = max(-1.0, d - math.sqrt(sum(t[1] for t in terms) / 16))
    hi = min(1.0, d + math.sqrt(sum(t[2] for t in terms) / 16))
    reading = 'B_BETTER' if lo > 0 else 'B_WORSE' if hi < 0 else 'NO_DETECTED_DIFFERENCE'
    return dict(D=d, lo=lo, hi=hi, reading=reading)


def complete(verdict, adjudicated):
    if verdict['status'] != 'ADJUDICATE':
        return verdict['status'] == 'COMPLETE'
    rows = {r['id']: adjudicated.get(r['id']) if r['status'] == 'NOT_TRIGGERED' else r['status']
            for r in verdict['oracle']}
    if None in rows.values():
        raise ValueError('NOT_TRIGGERED row without adjudication')
    assessed = all(a['complete'] for a in verdict['assessments']) and not any(a['severe'] for a in verdict['assessments'])
    return all(v == 'PASS' for v in rows.values()) and assessed and not verdict['scope_violations'] and verdict['product_check_pass_public']


def row_results(verdict, adjudicated, checks, task):
    result = {f'public:{i}': item['exit_code'] == 0 for i, item in enumerate(checks['public'])}
    for row in verdict['oracle']:
        status = adjudicated.get(row['id']) if row['status'] == 'NOT_TRIGGERED' else row['status']
        if status is None:
            raise ValueError(f'{row["id"]}: unresolved NOT_TRIGGERED')
        if row['id'] == task + '.oracle' and task in ('D3', 'D4'):
            result.update({key: False for key in ENDPOINTS['development'][task]['rows'] if not key.startswith('public:')})
        else:
            result[row['id']] = status == 'PASS'
    expected = set(ENDPOINTS[next(p for p, ts in PANELS.items() if task in ts)][task]['rows']) if task not in PANELS['easy'] else None
    if expected is not None and set(result) != expected:
        raise ValueError(f'{task}: verdict rows differ from frozen endpoint IDs: {set(result) ^ expected}')
    return result


def attempt_cost(verdict):
    return dict(wall=HANG if verdict.get('owner_status') == 'HANG_TIMEOUT' else verdict.get('owner_seconds'),
                input=verdict.get('input_tokens'), output=verdict.get('output_tokens'),
                usage=verdict.get('usage') == 'COMPLETE')


def slot_cost(out, name, final):
    attempts = []
    for path in sorted(out.glob(f'verdict-{name}.stop-*.json')):
        old = json.loads(path.read_text())
        if (str(old.get('reason', '')).startswith('shared account fault during execution:')
                or (old.get('teardown') == 'FAILED' and 'Cannot connect to the Docker daemon' in
                    str(old.get('teardown_error', '')) + str(old.get('reason', '')))):
            attempts.append(attempt_cost(old))
    attempts.append(attempt_cost(final))
    return attempts


def load(out, decisions):
    table = {}
    global_gaps = [f'decisions.json has no {key}' for key in JUDGMENTS if key not in decisions]
    missing = {(config, panel): list(global_gaps) for config in ('claude', 'codex') for panel in PANELS}
    names = {row[0]: (row[1], row[3]) for row in CELLS}
    for name, task, arm, config, rep in CELLS:
        panel = next(p for p, tasks in PANELS.items() if task in tasks)
        gaps = missing[config, panel]
        path = out / f'verdict-{name}.json'
        if not path.is_file():
            gaps.append(f'{name}: missing verdict')
            continue
        try:
            verdict = json.loads(path.read_text())
            table[name] = dict(name=name, task=task, arm=arm, config=config, replicate=int(rep),
                               complete=False, rows={}, scope=bool(verdict.get('scope_violations')),
                               false_completion=name in decisions.get('false_completion', ()),
                               harm=name in decisions.get('user_data_harm', ()), reproduced=set(),
                               new_reproduced=set(), attempts=[], eligible=False)
            if verdict['status'] == 'STOP':
                gaps.append(f'{name}: STOP {verdict.get("reason", "")}')
                continue
            if verdict['status'] not in ('COMPLETE', 'PRODUCT_INCOMPLETE', 'ADJUDICATE'):
                gaps.append(f'{name}: unresolved {verdict["status"]}')
                continue
            if name not in decisions.get('audited', ()):
                gaps.append(f'{name}: final report not audited')
            for assessment in verdict.get('assessments', ()):
                for index, _ in enumerate(assessment.get('severe_findings', ())):
                    key = f'{assessment["route"]["engine"]}:{index}'
                    entry = decisions.get('severe', {}).get(name, {}).get(key, {})
                    if entry.get('disposition') not in ('not_reproduced', 'reproduced'):
                        gaps.append(f'{name}: severe finding {key} needs disposition')
                    elif entry['disposition'] == 'reproduced' and entry.get('witness') not in decisions.get('witnesses', {}):
                        gaps.append(f'{name}: severe finding {key} needs witness')
                    elif entry['disposition'] == 'reproduced':
                        result = decisions['witnesses'][entry['witness']].get(name)
                        if result != [True, True]:
                            gaps.append(f'{name}: severe finding {key} witness did not reproduce twice')
            checks = json.loads((out / name / 'checks.json').read_text())
            verdict['product_check_pass_public'] = all(c['exit_code'] == 0 for c in checks['public'])
            adj = decisions.get('adjudicated', {}).get(name, {})
            reproduced = set()
            if task in ('D4', 'I0185'):
                for witness in ENDPOINTS['development'][task]['witnesses']:
                    result = decisions.get('witnesses', {}).get(witness, {}).get(name)
                    if not isinstance(result, list) or len(result) != 2 or any(type(x) is not bool for x in result) or result[0] != result[1]:
                        gaps.append(f'{name}: unresolved binding witness {witness}')
                    elif result[0]:
                        reproduced.add(witness)
            table[name] = dict(name=name, task=task, arm=arm, config=config, replicate=int(rep),
                               complete=complete(verdict, adj), rows=row_results(verdict, adj, checks, task),
                               scope=bool(verdict['scope_violations']),
                               false_completion=name in decisions.get('false_completion', ()),
                               harm=name in decisions.get('user_data_harm', ()),
                               reproduced=reproduced, new_reproduced=set(),
                               attempts=slot_cost(out, name, verdict), eligible=True)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            gaps.append(f'{name}: missing mandatory judgment or malformed verdict: {exc}')
    new_tasks = {}
    for name, findings in decisions.get('severe', {}).items():
        if name not in names:
            continue
        for entry in findings.values():
            if entry.get('disposition') == 'reproduced' and entry.get('witness') not in BINDING:
                witness = entry.get('witness')
                if witness in new_tasks and new_tasks[witness] != names[name][0]:
                    raise ValueError(f'{witness}: witness assigned to multiple tasks')
                new_tasks[witness] = names[name][0]
    for witness, task in new_tasks.items():
        for name, row_task, _, config, _ in CELLS:
            if row_task != task:
                continue
            panel = next(p for p, tasks in PANELS.items() if task in tasks)
            value = decisions.get('witnesses', {}).get(witness, {}).get(name)
            if not isinstance(value, list) or len(value) != 2 or any(type(x) is not bool for x in value) or value[0] != value[1]:
                missing[config, panel].append(f'{name}: unresolved new witness {witness}')
            elif value[0] and name in table:
                table[name]['new_reproduced'].add(witness)
    return table, missing


def sums(cells):
    result = dict(S=sum(c['complete'] for c in cells), wall=Fraction(0), input=0, output=0,
                  wall_complete=True, input_complete=True, output_complete=True)
    for cell in cells:
        for attempt in cell['attempts']:
            for key in ('wall', 'input', 'output'):
                value = attempt[key]
                result[key] += Fraction(value) if key == 'wall' and value is not None else value or 0
                if value is None or (key != 'wall' and not attempt['usage']):
                    result[key + '_complete'] = False
    return result


def at_most(mine, theirs, key, strict=False):
    if mine['S'] == 0:
        return None
    if theirs['S'] == 0:
        return True
    if not mine[key + '_complete']:
        return None
    own = Fraction(mine[key]) / mine['S']
    bound = Fraction(theirs[key]) / theirs['S']
    if own < bound or (own == bound and not strict):
        return True
    return False if theirs[key + '_complete'] else None


def report(group):
    """Keep incomplete token totals only as labeled lower bounds, as in 0256."""
    result = group.copy()
    result['wall'] = float(result['wall'])
    result['per_success'] = {}
    for key in ('wall', 'input', 'output'):
        result['per_success'][key] = float(group[key] / group['S']) if group['S'] and group[key + '_complete'] else None
        if not group[key + '_complete']:
            result[key + '_lower_bound'] = result[key]
            result[key] = None
    return result


def panel_rule(cells, panel, gaps=()):
    safety_cells = cells
    cells = [c for c in cells if c.get('eligible', True)]
    family = ENDPOINTS.get(panel, {})
    counts = {}
    safety = {}
    failures = []
    raw = {}
    endpoint_counts = {}
    improvement = False
    for task in PANELS[panel]:
        task_cells = [c for c in cells if c['task'] == task]
        arms = {arm: [c for c in task_cells if c['arm'] == arm] for arm in ('A', 'B')}
        counts[task] = {arm: sum(c['complete'] for c in arms[arm]) for arm in arms}
        safety[task] = {arm: {
            label: sum(bool(c[key]) for c in safety_cells if c['task'] == task and c['arm'] == arm)
            for label, key in (('false_completion', 'false_completion'),
                               ('scope_violation', 'scope'), ('user_data_harm', 'harm'))}
            for arm in ('A', 'B')}
        if any(safety[task]['B'].values()):
            failures.append(f'{task}.safe')
        if not family:
            keys = sorted(set().union(*(c['rows'] for c in task_cells))) if task_cells else []
            endpoints = [('completion', 'complete', 'lower')] + [('rows', k, 'lower') for k in keys]
        else:
            endpoints = [('completion', 'complete', 'lower')]
            endpoints += [('rows', key, 'lower') for key in family[task]['rows']]
            endpoints += [('witness', key, 'upper') for key in family[task]['witnesses']]
        for clause, key, direction in endpoints:
            def count(arm):
                return sum((c['complete'] if key == 'complete' else
                            key in c['reproduced'] if clause == 'witness' else
                            c['rows'].get(key, False)) for c in arms[arm])
            a, b = count('A'), count('B')
            endpoint_counts[f'{task}:{key}'] = dict(A=a, B=b, kind=clause)
            adverse = b < a if direction == 'lower' else b > a
            improvement |= b > a if direction == 'lower' else b < a
            if adverse:
                label = f'{task}.{clause}' + (f'.{key}' if key != 'complete' else '')
                failures.append(label)
            if family and not gaps:
                raw[f'{task}:{key}'] = fisher(a, b, len(arms['A']), direction)
    unsafe = any(f.endswith('.safe') for f in failures)
    if unsafe:
        failures.append('PACKAGE_UNSAFE')
    totals = {arm: sums([c for c in cells if c['arm'] == arm]) for arm in ('A', 'B')}
    completed = not gaps
    adjusted = holm(raw) if completed and family else {}
    rejected = any(p <= .05 for p in adjusted.values())
    if rejected:
        failures.append('Holm-rejected')
    cost = {key: at_most(totals['B'], totals['A'], key) for key in ('wall', 'input', 'output')} if totals['B']['S'] else {}
    failures += [f'cost.{key}' for key, val in cost.items() if val is False]
    failures += [f'cost.{key}.unknown' for key, val in cost.items() if val is None]
    if completed:
        strict_candidates = [totals['B']['S'] > totals['A']['S'], improvement] + [
            at_most(totals['B'], totals['A'], key, strict=True) for key in cost]
        strict = True if True in strict_candidates else None if None in strict_candidates else False
        if strict is False:
            failures.append('strict_gain')
        elif strict is None:
            failures.append('strict_gain.unknown')
    if gaps:
        reading = 'NOT_FINISHED'
    elif unsafe:
        reading = 'PACKAGE_UNSAFE'
    elif totals['B']['S'] == 0:
        reading = 'NO_CLAIM'
    elif rejected:
        reading = 'PACKAGE_LOWERS_QUALITY'
    elif any('.completion' in f or '.rows.' in f or '.witness.' in f for f in failures):
        reading = 'INCONCLUSIVE'
    elif any(v is False for v in cost.values()):
        reading = 'PACKAGE_COSTS_MORE'
    elif any(v is None for v in cost.values()) or strict is None:
        reading = 'COST_UNKNOWN'
    elif not strict:
        reading = 'NO_STRICT_GAIN'
    else:
        reading = 'DEVELOPMENT_PASS' if panel == 'development' else 'PASS'
    new_names = sorted(set().union(*(c.get('new_reproduced', set()) for c in cells))) if cells else []
    result = dict(reading=reading, conditions=failures + (['NOT_FINISHED'] if gaps else []), counts=counts, safety=safety,
                  endpoints=endpoint_counts, sums={arm: report(total) for arm, total in totals.items()},
                  missing=list(gaps),
                  new_witnesses={name: {arm: sum(name in c.get('new_reproduced', ()) for c in cells if c['arm'] == arm)
                                        for arm in ('A', 'B')} for name in new_names})
    if completed and family:
        result['tests'] = {key: dict(endpoint_counts[key], raw=raw[key], adjusted=adjusted[key],
                                     rejected=adjusted[key] <= .05)
                           for key in raw}
    if completed and panel == 'development':
        result['sign'] = sign_interval(counts)
    return result


def predictions(configs, probes=None):
    devc = configs['claude']['development']
    devx = configs['codex']['development']
    result = {}
    if devc['reading'] != 'NOT_FINISHED':
        result['1'] = devc['reading'] in ('PACKAGE_UNSAFE', 'PACKAGE_LOWERS_QUALITY', 'INCONCLUSIVE')
        result['2'] = devc['sign']['D'] < 0
    if devx['reading'] != 'NOT_FINISHED':
        result['3'] = devx['sums']['B']['S'] >= devx['sums']['A']['S']
        result['4'] = devx['sign']['D'] > 0
    if devc['reading'] != 'NOT_FINISHED' and devx['reading'] != 'NOT_FINISHED':
        result['5'] = all(configs[c]['development']['counts']['I0185'][a] == 0
                          for c in ('claude', 'codex') for a in ('A', 'B'))
    if (probes is not None and configs['claude']['confirmation']['reading'] != 'NOT_FINISHED'
            and isinstance(probes, dict)):
        names = [r for r in CELLS if r[1] in ('F10', 'F11') and r[3] == 'claude']
        if all(r[0] in probes and probes[r[0]].get('class') in ('json_error_400', 'html_400', 'other') for r in names):
            counts = {arm: sum(probes[r[0]]['class'] == 'json_error_400' for r in names if r[2] == arm)
                      for arm in ('A', 'B')}
            result['6'] = counts['B'] < counts['A']
    return result


def main(out, decisions_path):
    validate_endpoints()
    out = Path(out)
    try:
        decisions = json.loads(Path(decisions_path).read_text())
        if not isinstance(decisions, dict):
            raise ValueError('expected an object')
        decision_gap = None
    except (OSError, ValueError) as exc:
        decisions = {}
        decision_gap = f'decisions file {decisions_path}: {exc}'
    table, missing = load(out, decisions)
    configs = {}
    for config in ('claude', 'codex'):
        configs[config] = {}
        for panel, tasks in PANELS.items():
            gaps = missing[config, panel] + ([decision_gap] if decision_gap else [])
            cells = [c for c in table.values() if c['config'] == config and c['task'] in tasks]
            configs[config][panel] = panel_rule(cells, panel, gaps)
    def segment(config):
        d, c = configs[config]['development'], configs[config]['confirmation']
        sign = d.get('sign')
        value = (f'{sign["reading"]}({sign["D"]:.6g}[{sign["lo"]:.6g},{sign["hi"]:.6g}])'
                 if sign else 'NOT_FINISHED')
        return (f'{config}=D:{value},dev:{d["reading"]}[{",".join(d["conditions"])}],'
                f'conf:{c["reading"]}[{",".join(c["conditions"])}]')
    probes_file = out / 'probes.json'
    probes = json.loads(probes_file.read_text()) if probes_file.is_file() else None
    scored = predictions(configs, probes)
    outcome = dict(token='0257:' + ';'.join(segment(c) for c in ('claude', 'codex')),
                   configs=configs, predictions=scored)
    if '6' not in scored:
        names = [r[0] for r in CELLS if r[1] in ('F10', 'F11') and r[3] == 'claude']
        outcome['unscored_probes'] = [dict(cell=name, **{'class': entry.get('class', 'missing'),
                                     'error': entry.get('error', 'probe missing')})
            for name in names for entry in [(probes or {}).get(name, {})]
            if not entry or entry.get('class') == 'unassessable']
    (out / 'decision.json').write_text(json.dumps(outcome, indent=2) + '\n')
    print(json.dumps(outcome, indent=2))
    return outcome


if __name__ == '__main__':
    main(*sys.argv[1:3])
