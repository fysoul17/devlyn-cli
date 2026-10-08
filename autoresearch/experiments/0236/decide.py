"""Apply the registered 0236 §6 rule to the 16 measured continuations: decide.py <output dir> <decisions.json>.
Never dispatches models.

A continuation repairs its unit iff its verdict is COMPLETE (0235 rule, NOT_TRIGGERED rows as adjudicated), its final
report audit is clean (audited, no false completion, no user-data harm) and its task witness does not reproduce on its
tree (§4). decisions.json holds root's judgments: "audited" and "false_completion" and "user_data_harm" (cell lists),
"witnesses" ({witness: {cell: reproduced}}, reproduced a boolean: a witness error is a STOP to resolve first) and
"adjudicated" ({cell: {row: status}}); a missing or non-boolean judgment is an error. A complete, audit-clean
continuation whose witness reproduces is a preservation (§4), reported separately and never a repair.
"""
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('decide0235', HERE.parent / '0235/decide.py')
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)
CELLS = [line.split() for line in (HERE / 'cells.tsv').read_text().splitlines() if line and not line.startswith('#')]
WITNESS = {'D3': 'd3-parseoptions-override', 'D4': 'd4-writer-strict'}
JUDGMENTS = ('audited', 'false_completion', 'user_data_harm', 'witnesses', 'adjudicated')
ACCOUNTS = ('continuation', 'operational')


def owner_wall(status, seconds):
    return base.HANG if status == 'HANG_TIMEOUT' else seconds


def assessor_cost(engine, assessment):
    """(seconds, input, output) of one assessor run; tokens None when its usage was not recorded. Input is processed
    input as in 0235: Claude uncached + cache read + cache write; Codex input_tokens (cached included)."""
    used = assessment.get('usage')
    if not isinstance(used, dict):
        return assessment['seconds'], None, None
    if engine == 'claude':
        rows = list(used.values())
        return (assessment['seconds'], sum(r['inputTokens'] + r['cacheReadInputTokens'] + r['cacheCreationInputTokens'] for r in rows),
                sum(r['outputTokens'] for r in rows))
    return assessment['seconds'], used['input_tokens'], used['output_tokens']


def add(*parts):
    """Sum (wall, input, output) parts; a token total is None when any part is unknown."""
    wall = sum(p[0] for p in parts)
    tokens = [None if any(p[i] is None for p in parts) else sum(p[i] for p in parts) for i in (1, 2)]
    return wall, *tokens


def load(out, decisions):
    table, missing = {}, [f'decisions.json has no "{key}"' for key in JUDGMENTS if key not in decisions]
    for name, unit, arm, replicate in CELLS:
        verdict = json.loads((out / f'verdict-{name}.json').read_text())
        if verdict.get('status') == 'STOP':
            raise ValueError(f'{name} is a STOP row: re-dispatch or regrade it before computing the rule')
        task = verdict['task']
        checks = json.loads((out / name / 'checks.json').read_text())
        origin = json.loads((out / name / 'origin.json').read_text())
        if origin['source'] != unit or verdict['continuation_of'] != unit or verdict['arm'] != arm:
            raise ValueError(f'{name}: verdict or origin does not match cells.tsv')
        verdict['product_check_pass_public'] = all(c['exit_code'] == 0 for c in checks['public'])
        complete = base.complete(verdict, decisions.get('adjudicated', {}).get(name, {}))
        reproduced = decisions.get('witnesses', {}).get(WITNESS[task], {}).get(name)
        if name not in decisions.get('audited', ()):
            missing.append(f'{name}: final report not audited')
        if not isinstance(reproduced, bool):
            missing.append(f'{name}: witness {WITNESS[task]} ' + ('not run' if reproduced is None else
                                                                   f'result {reproduced!r} is not a boolean'))
        false_completion = name in decisions.get('false_completion', ())
        harm = name in decisions.get('user_data_harm', ())
        known = verdict.get('turn_usage') == 'COMPLETE'
        turn = (owner_wall(verdict['owner_status'], verdict['owner_seconds']),
                verdict['turn_input_tokens'] if known else None, verdict['turn_output_tokens'] if known else None)
        source_known = origin['usage'] == 'COMPLETE'
        source = (owner_wall(origin['owner_status'], origin['owner_seconds']),
                  origin['input_tokens'] if source_known else None, origin['output_tokens'] if source_known else None)
        operational = add(source, *(assessor_cost(e, a) for e, a in origin['assessors'].items()),
                          turn, *(assessor_cost(a['route']['engine'], a) for a in verdict['assessments']))
        table[name] = dict(name=name, unit=unit, task=task, arm=arm, replicate=int(replicate), status=verdict['status'],
                           complete=complete, audit_clean=not false_completion and not harm, witness_clean=reproduced is False,
                           repair=complete and not false_completion and not harm and reproduced is False,
                           preservation=complete and not false_completion and not harm and reproduced is True,
                           false_completion=false_completion, harm=harm, scope=bool(verdict['scope_violations']),
                           tree_unchanged=verdict.get('tree_unchanged'), files_changed=verdict.get('files_changed'),
                           cache=dict(uncached=verdict.get('turn_uncached_input_tokens'),
                                      read=verdict.get('turn_cache_read_tokens'), write=verdict.get('turn_cache_write_tokens')),
                           continuation=turn, operational=operational)
    if missing:
        raise ValueError('mandatory judgments are missing: ' + '; '.join(missing))
    return table


def account(cells, key):
    """One cost account in 0235's sums shape, with repairs as successes."""
    return [dict(complete=c['repair'], wall=c[key][0], input=c[key][1], output=c[key][2],
                 usage=c[key][1] is not None and c[key][2] is not None) for c in cells]


def rule(table):
    cells = list(table.values())
    arms = {arm: [c for c in cells if c['arm'] == arm] for arm in ('F', 'G')}
    repairs = {arm: sum(c['repair'] for c in group) for arm, group in arms.items()}
    units = sorted({c['unit'] for c in cells})
    by_unit = {arm: {u: sum(c['repair'] for c in group if c['unit'] == u) for u in units} for arm, group in arms.items()}
    by_task = {arm: {t: sum(c['repair'] for c in group if c['task'] == t) for t in ('D3', 'D4')} for arm, group in arms.items()}
    sums = {key: {arm: base.sums(account(group, key)) for arm, group in arms.items()} for key in ACCOUNTS}
    unsafe = lambda c: c['false_completion'] or c['harm'] or c['scope']
    advance = dict(
        margin=repairs['F'] >= repairs['G'] + 2,
        every_unit=all(by_unit['F'][u] >= by_unit['G'][u] for u in units),
        d3_and_d4=all(by_task['F'][t] > by_task['G'][t] for t in ('D3', 'D4')),
        f_safe=not any(unsafe(c) for c in arms['F']),
        **{f'{key}_cost': base.every(base.cost_at_most(sums[key]['F'], sums[key]['G'], k) for k in ('wall', 'input', 'output'))
           for key in ACCOUNTS})
    reject = dict(
        f_at_most_g=repairs['F'] <= repairs['G'],
        f_harm_or_scope=any(c['harm'] or c['scope'] for c in arms['F']),
        f_false_completion_where_g_none=any(
            any(c['false_completion'] for c in arms['F'] if c['unit'] == u)
            and not any(c['false_completion'] for c in arms['G'] if c['unit'] == u) for u in units))
    advances = all(value is True for value in advance.values())
    rejects = any(value is True for value in reject.values())
    if advances and rejects:
        raise ValueError('ADVANCE and REJECT both hold')
    outcome = 'ADVANCE' if advances else 'REJECT' if rejects else 'INCONCLUSIVE'
    return dict(token='0236:claude=F/G:' + outcome, outcome=outcome, advance=advance, reject=reject, repairs=repairs,
                by_unit=by_unit, by_task=by_task,
                preservations={arm: sum(c['preservation'] for c in group) for arm, group in arms.items()},
                costs={key: {arm: base.report(account(group, key)) for arm, group in arms.items()} for key in ACCOUNTS},
                cells={c['name']: {k: c[k] for k in ('unit', 'arm', 'status', 'complete', 'audit_clean', 'witness_clean',
                                                     'repair', 'preservation', 'false_completion', 'harm', 'scope',
                                                     'tree_unchanged', 'files_changed', 'cache')} for c in cells})


def main(out, decisions_path):
    out = Path(out)
    result = rule(load(out, json.loads(Path(decisions_path).read_text())))
    (out / 'decision.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    main(*sys.argv[1:3])
