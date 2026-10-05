"""Apply the 0232 rule (record §6, owner decision O4): decide.py <out> <decisions.json>. Reads verdicts; never dispatches.

decisions.json holds root's recorded judgments ("Before any rule is computed"), all mandatory:
{"audited": [every measured cell: its final report was audited], "false_completion": [cells], "user_data_harm": [cells],
 "adjudicated": {"<cell>": {"<row>": "PASS"|"FAIL"}},
 "severe": {"<cell>": {"<assessor engine>:<index>": {"disposition": "reproduced"|"not_reproduced", "witness": "<id>"}}}
   for every severe assessor finding (a reproduced one names its concrete witness),
 "witnesses": {"<id>": {"<cell>": true|false}}: each witness applied to a tree}

Per configuration, over each arm's six cells: S = completed cells; W (owner seconds, a hang counts 5400), I (processed
input, cache counted once) and O (output) are sums over all six cells, failures included; per-success cost = sum / S.
A candidate against a reference:
- quality, per task: the candidate's completion count and each public-check and oracle-row pass count are at least the
  reference's; no candidate cell has a false completion, scope violation or user-data harm; every HIGH/CRITICAL
  witness reproduced on a candidate tree also reproduces on the reference tree of the same replicate;
- resources, per success: W, I and O each at most factor x the reference's. A reference with S = 0 has an unbounded
  per-success cost: the tests pass with the reason "dominance over a zero-success incumbent", never as a percentage.
  Candidate usage that is not COMPLETE leaves its test inconclusive; a reference's PARTIAL sum is a lower bound, so it
  can prove a test but never disprove one.
Admission (I against A, the last admitted rung): quality, W, I and O not higher, and at least one of completion count,
W, I and O strictly better. Replacement of the incumbent F needs admission and the F comparison (owner O1 per success:
quality, W at most 0.70 x F's, I and O not higher); both outcomes are reported. A candidate with S = 0 earns no claim
(NO_CLAIM). If I is not admitted, A stays the admitted rung. Each configuration decides separately; methodology (I's
compliance, F's obligations) is reported, never part of the rule.
"""
from fractions import Fraction
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
CELLS = [line.split() for line in (HERE / 'cells.tsv').read_text().splitlines() if line and not line.startswith('#')]
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
                           usage=verdict.get('usage') == 'COMPLETE',
                           methodology=(verdict.get('compliance') or {}).get('compliant') if arm == 'I' else
                           (verdict.get('obligations') or {}).get('satisfied') if arm == 'F' else None)
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
    """Raw sums with per-success costs, and each cell's methodology record (I's compliance, F's obligations)."""
    group = sums(cells)
    per = {key: float(group[key] / group['S']) if group['S'] else None for key in ('wall', 'input', 'output')}
    return dict(group, wall=float(group['wall']), per_success=per, methodology={c['name']: c['methodology'] for c in cells})


def config_rule(table, config):
    cells = [c for c in table.values() if c['config'] == config]
    admission = compare(cells, 'I', 'A', 1, strict=True)
    against = compare(cells, 'I', 'F', Fraction(7, 10), strict=False)
    outcomes = (admission['outcome'], against['outcome'])
    joint = 'NO_CLAIM' if 'NO_CLAIM' in outcomes else OUTCOME[every({v: k for k, v in OUTCOME.items()}[o] for o in outcomes)]
    return dict(admitted='I' if admission['outcome'] == 'PASS' else 'A', admission=admission,
                replacement=dict(against, comparison=against['outcome'], admission=admission['outcome'], outcome=joint),
                sums={arm: report([c for c in cells if c['arm'] == arm]) for arm in ('A', 'I', 'F')})


def main(out, decisions_path):
    decisions = json.loads(Path(decisions_path).read_text())
    table = load(Path(out), decisions)
    result = {config: config_rule(table, config) for config in ('claude', 'codex')}
    token = 'LIVE:' + ';'.join(f'{c}=admitted:{result[c]["admitted"]},replaces_F:{result[c]["replacement"]["outcome"]}'
                               for c in ('claude', 'codex'))
    outcome = dict(token=token, configs=result)
    print(json.dumps(outcome, indent=2))
    return outcome


if __name__ == '__main__':
    main(*sys.argv[1:3])
