"""Apply the frozen 0231 rule: decide.py <out> <decisions.json>. Reads verdicts; never dispatches.

decisions.json holds root's recorded judgments ("Before any rule is computed"), all mandatory:
{"audited": [every measured cell: its final report was audited], "false_completion": [cells],
 "adjudicated": {"<cell>": {"<row>": "PASS"|"FAIL"}},
 "severe": {"<cell>": {"<assessor engine>:<index>": "reproduced"|"not_reproduced"}} for every severe assessor finding,
 "reproduced": {"<cell>": [witness ids reproduced against that cell's tree]}}
Eligibility per (task, config) over two replicates: counts for completion and rows (owner decision 2026-10-04),
the concrete witness compared within each adjacent pair, obligations per candidate cell. A test is proven, disproved
(only against complete evidence) or unresolved.
"""
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
CELLS = [line.split() for line in (HERE / 'cells.tsv').read_text().splitlines() if line and not line.startswith('#')]
WALL_RATIO, WALL_OUTPUT_RATIO, OUTPUT_RATIO, HANG = 0.85, 1.10, 0.75, 5400


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
            if recorded.get(key) not in ('reproduced', 'not_reproduced'):
                gaps.append(f'{name}: severe finding {key} has no recorded disposition')
    return gaps


def load(out, decisions):
    table, missing = {}, []
    for name, task, arm, config, replicate in CELLS:
        verdict = json.loads((out / f'verdict-{name}.json').read_text())
        if verdict.get('status') == 'STOP':
            raise ValueError(f'{name} is a STOP row: re-dispatch or regrade it before computing the rule')
        missing += audit_gaps(name, verdict, decisions)
        checks = json.loads((out / name / 'checks.json').read_text())
        verdict['product_check_pass_public'] = all(c['exit_code'] == 0 for c in checks['public'])
        adjudicated = decisions.get('adjudicated', {}).get(name, {})
        table[name] = dict(task=task, arm=arm, config=config, replicate=int(replicate),
                           complete=complete(verdict, adjudicated), rows=rows(verdict, adjudicated, checks),
                           scope=bool(verdict['scope_violations']), false_completion=name in decisions.get('false_completion', ()),
                           reproduced=set(decisions.get('reproduced', {}).get(name, ())),
                           obligations=bool((verdict.get('obligations') or {}).get('satisfied')),
                           wall=HANG if verdict['owner_status'] == 'HANG_TIMEOUT' else verdict['owner_seconds'],
                           output=verdict.get('output_tokens'), usage=verdict.get('usage'))
    if missing:
        raise ValueError('mandatory judgments are missing: ' + '; '.join(missing))
    return table


def config_rule(table, config):
    cells = {n: c for n, c in table.items() if c['config'] == config}
    tasks = sorted({c['task'] for c in cells.values()})
    eligibility = {}
    for task in tasks:
        arms = {arm: [c for c in cells.values() if c['task'] == task and c['arm'] == arm] for arm in ('control', 'candidate')}
        pairs = {c['replicate']: {arm: next(x for x in arms[arm] if x['replicate'] == c['replicate']) for arm in arms}
                 for c in arms['candidate']}
        row_ids = set().union(*(c['rows'] for c in arms['control'] + arms['candidate']))
        count = lambda arm, key: sum(c['rows'].get(key, False) for c in arms[arm])
        eligibility[task] = dict(
            rule1=not any(c['false_completion'] or c['scope'] for c in arms['candidate']),
            rule2=sum(c['complete'] for c in arms['candidate']) >= sum(c['complete'] for c in arms['control']),
            rule3=all(count('candidate', key) >= count('control', key) for key in row_ids),
            rule4=all(p['candidate']['reproduced'] <= p['control']['reproduced'] for p in pairs.values()),
            rule5=all(c['obligations'] for c in arms['candidate']),
            pairs={r: dict(candidate_complete=p['candidate']['complete'], control_complete=p['control']['complete'])
                   for r, p in sorted(pairs.items())})
    eligible = all(all(v for k, v in e.items() if k.startswith('rule')) for e in eligibility.values())
    sums = {}
    for arm in ('control', 'candidate'):
        group = [c for c in cells.values() if c['arm'] == arm]
        sums[arm] = dict(wall=sum(c['wall'] for c in group), output=sum(c['output'] or 0 for c in group),
                         complete_usage=all(c['usage'] == 'COMPLETE' and c['output'] is not None for c in group))
    candidate, control = sums['candidate'], sums['control']

    def status(factor):  # the control's recorded output is a valid lower bound; only complete evidence disproves
        if not candidate['complete_usage']:
            return 'unresolved'
        if candidate['output'] <= factor * control['output']:
            return 'proven'
        return 'disproved' if control['complete_usage'] else 'unresolved'
    wall_test = 'disproved' if candidate['wall'] > WALL_RATIO * control['wall'] else status(WALL_OUTPUT_RATIO)
    output_test = status(OUTPUT_RATIO)
    outcome = ('REJECTED' if not eligible else 'ADOPTED' if 'proven' in (wall_test, output_test) else
               'REJECTED' if (wall_test, output_test) == ('disproved', 'disproved') else 'INCONCLUSIVE')
    return dict(outcome=outcome, eligible=eligible, eligibility=eligibility, sums=sums, wall_test=wall_test,
                output_test=output_test, wall_ratio=candidate['wall'] / control['wall'] if control['wall'] else None,
                output_ratio=candidate['output'] / control['output'] if control['output'] else None)


def main(out, decisions_path):
    decisions = json.loads(Path(decisions_path).read_text())
    table = load(Path(out), decisions)
    result = {config: config_rule(table, config) for config in ('claude', 'codex')}
    token = 'LIVE:' + ';'.join(f'{config}={result[config]["outcome"]}' for config in ('claude', 'codex'))
    release = all(result[c]['outcome'] == 'ADOPTED' for c in result)
    report = dict(token=token, bundle_eligible_for_delivery=release, configs=result)
    print(json.dumps(report, indent=2, default=sorted))
    return report


if __name__ == '__main__':
    main(*sys.argv[1:3])
