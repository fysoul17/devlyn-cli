"""Offline within-task effort comparison over retained, sealed rp-d5 evidence."""
import argparse
import importlib.util
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


attribute = load('attribute_rpd5_summary', HERE / 'attribute.py')
SCHEDULE = [('c01', 'BV', 'max'), ('c02', 'BV', 'high'),
            ('c03', 'Z0', 'high'), ('c04', 'Z0', 'max')]
COUNTERS = ('input_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens',
            'output_tokens', 'thinking_tokens')
METRICS = ('turns', *COUNTERS, 'total_input_tokens', 'marginal_tokens')


def read(path):
    return json.loads(Path(path).read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def measured_records(output):
    """A paused prefix is visible; unattempted slots remain unknown, never zero."""
    schedule = read(output / 'rp-schedule.json')
    require(schedule['phase'] == 'measured', 'only measured output may be summarized')
    rows = schedule['slots']
    expected = [(slot, task, 'claude') for slot, task, _ in SCHEDULE]
    actual = [(row['cell'], row['task'], row['config']) for row in rows]
    require(actual == expected or (schedule['status'] == 'PAUSED' and
            0 < len(rows) < 4 and actual == expected[:len(rows)]), 'invalid slot order')
    release = None
    account = None
    for row, (slot, _, effort) in zip(rows, SCHEDULE):
        require(row == read(output / slot / 'rp-verdict.json'), 'schedule/verdict mismatch')
        require(row['phase'] == 'measured' and row['measurement_eligible'] is True and
                type(row['dispatched']) is bool, 'invalid measured verdict')
        require(row['status'] in ('PASS', 'ADJUDICATE', 'PRODUCT_INCOMPLETE',
                                 'STOP', 'UNKNOWN', 'NOT_RUN'), 'invalid verdict status')
        require(row.get('effort') == effort, 'slot effort differs from frozen schedule')
        require(row['dispatched'] or row['status'] in ('STOP', 'UNKNOWN', 'NOT_RUN'),
                'undispatched slot has a delivery outcome')
        if row['dispatched']:
            require(row['status'] != 'NOT_RUN', 'NOT_RUN slot was dispatched')
            require(row.get('arm') == 'X', 'only registry arm X is measured')
            require(isinstance(row.get('release'), dict) and row['release'].get('version') == '4.2.22',
                    'missing registered release identity')
            release = release or row['release']
            require(row['release'] == release, 'release changed between slots')
            require(isinstance(row.get('account'), list) and len(row['account']) == 2,
                    'missing Claude account identity')
            account = account or row['account']
            require(row['account'] == account, 'Claude account changed between slots')
    require(schedule['dispatched'] == sum(row['dispatched'] for row in rows),
            'dispatch count mismatch')
    for slot, task, effort in SCHEDULE[len(rows):]:
        require(not (output / slot).exists(), 'unrecorded attempt after paused prefix')
        rows.append(dict(cell=slot, task=task, config='claude', effort=effort,
                         dispatched=False, status='NOT_RUN', delivery_assessment='NOT_ASSESSED'))
    return rows


def delivery_outcome(record):
    if not record['dispatched'] or record['status'] in ('STOP', 'UNKNOWN', 'NOT_RUN'):
        return 'UNKNOWN'
    if (record['status'] in ('PASS', 'ADJUDICATE') and
            record.get('delivery_assessment') in ('PASS', 'ADJUDICATE') and
            record.get('inherited_status') not in ('PRODUCT_INCOMPLETE', 'STOP', 'UNKNOWN') and
            record.get('merge_refused') is False):
        return 'PASS'
    if record.get('merge_refused') is None:
        return 'UNKNOWN'
    return 'FAIL'


def metrics(totals):
    if totals is None:
        return {key: None for key in METRICS}
    return {**{key: totals[key] for key in METRICS if key != 'total_input_tokens'},
            'total_input_tokens': sum(totals[key] for key in COUNTERS[:3])}


def delta(maximum, high):
    return {key: maximum[key] - high[key] if maximum[key] is not None and high[key] is not None
            else None for key in maximum}


def compare(task, slots):
    maximum = next(row for row in slots if row['task'] == task and row['effort'] == 'max')
    high = next(row for row in slots if row['task'] == task and row['effort'] == 'high')
    raw = delta(maximum['metrics'], high['metrics'])
    raw['owner_seconds'] = (maximum['owner_seconds'] - high['owner_seconds']
                            if all(number(row['owner_seconds']) for row in (maximum, high)) else None)
    sensitivity = delta(maximum['sensitivity'], high['sensitivity'])
    same = (maximum['delivery_outcome'] == high['delivery_outcome']
            if all(row['delivery_outcome'] != 'UNKNOWN' for row in (maximum, high)) else None)
    conditions = dict(more_terminal_turns=raw['turns'] > 0 if raw['turns'] is not None else None,
                      more_thinking_tokens=raw['thinking_tokens'] > 0 if raw['thinking_tokens'] is not None else None,
                      same_delivery_outcome=same)
    prediction = ('UNKNOWN' if None in conditions.values() else
                  'PASS' if all(conditions.values()) else 'FAIL')
    both_delivered = all(row['delivery_outcome'] == 'PASS' for row in (maximum, high))
    costs = ('owner_seconds', 'total_input_tokens', 'output_tokens')
    if not both_delivered:
        efficiency = dict(eligible=False, conclusion='WITHHELD',
                          reason='both slots must pass delivery')
    elif any(raw[key] is None for key in costs):
        efficiency = dict(eligible=False, conclusion='UNKNOWN',
                          reason='complete wall and token evidence is required')
    else:
        differences = [raw[key] for key in costs]
        conclusion = ('TIED' if all(value == 0 for value in differences) else
                      'HIGH_LOWER' if all(value >= 0 for value in differences) else
                      'MAX_LOWER' if all(value <= 0 for value in differences) else 'TRADEOFF')
        efficiency = dict(eligible=True, conclusion=conclusion,
                          reason='observed wall, total input and output for two delivered slots; one observation per effort')
    return dict(task=task, max_slot=maximum['cell'], high_slot=high['cell'],
                delta_direction='max minus high', raw=raw, sensitivity=sensitivity,
                sensitivity_scope='exclude each slot first receipt; no wall split',
                prediction=dict(status=prediction, **conditions), efficiency=efficiency)


def summarize(output):
    output = Path(output)
    slots = []
    for record in measured_records(output):
        analysis = attribute.analyze(output / record['cell'], expected_effort=record['effort']) if record['dispatched'] else None
        known = (analysis is not None and analysis['status'] == 'MATCH' and
                 record['status'] not in ('STOP', 'UNKNOWN') and record.get('usage') == 'COMPLETE')
        if analysis is not None and not known:
            analysis = dict(status='UNKNOWN', gaps=analysis.get('gaps', []) +
                            ['slot verdict does not establish complete accounting'],
                            effort_binding=analysis.get('effort_binding'),
                            owner_seconds=analysis.get('owner_seconds'), totals=None, sensitivity=None)
        slots.append(dict(cell=record['cell'], task=record['task'], effort=record['effort'],
                          dispatched=record['dispatched'], runner_status=record['status'],
                          delivery_outcome=delivery_outcome(record), merge_refused=record.get('merge_refused'),
                          accounting='MATCH' if known else 'UNKNOWN',
                          owner_seconds=analysis.get('owner_seconds') if analysis else None,
                          metrics=metrics(analysis['totals'] if known else None),
                          sensitivity=metrics(analysis['sensitivity'] if known else None), analysis=analysis))
    comparisons = [compare(task, slots) for task in ('BV', 'Z0')]
    statuses = [row['prediction']['status'] for row in comparisons]
    return dict(schema='rp-d5-summary-v1', slots=slots, comparisons=comparisons,
                prediction='UNKNOWN' if 'UNKNOWN' in statuses else 'PASS' if statuses == ['PASS', 'PASS'] else 'FAIL',
                limits='One slot per task per effort. Wall includes model latency. Repeats and marginal tokens are descriptive, not proven savings.')


def display(value):
    return 'UNKNOWN' if value is None else str(value).replace('|', '\\|').replace('\n', ' ')


def table(headers, rows):
    return ['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join('---' for _ in headers) + ' |',
            *['| ' + ' | '.join(display(value) for value in row) + ' |' for row in rows]]


def markdown(summary):
    lines = ['rp-d5 measured effort comparison', '', 'All deltas are max minus high.', '']
    lines += table(['Slot', 'Task', 'Effort', 'Delivery', 'Accounting', 'Owner wall s', 'Turns',
                    'Uncached input', 'Cache read', 'Cache write', 'Output', 'Thinking', 'Marginal'],
                   [[row['cell'], row['task'], row['effort'], row['delivery_outcome'], row['accounting'],
                     row['owner_seconds'], *(row['metrics'][key] for key in ('turns', *COUNTERS, 'marginal_tokens'))]
                    for row in summary['slots']])
    for row in summary['slots']:
        lines += ['', row['cell'] + ' attribution', '']
        if row['accounting'] != 'MATCH':
            lines += ['UNKNOWN: no reconciled stage or token figures are claimed.']
        else:
            lines += [attribute.markdown(row['analysis'])]
    lines += ['', 'Within-task deltas', '']
    headers = ['Task', 'View', 'Wall s', 'Turns', 'Uncached', 'Cache read', 'Cache write',
               'Output', 'Thinking', 'Total input', 'Marginal']
    rows = []
    for pair in summary['comparisons']:
        for view in ('raw', 'sensitivity'):
            values = pair[view]
            rows.append([pair['task'], view, values.get('owner_seconds') if view == 'raw' else 'not partitioned',
                         *(values[key] for key in METRICS)])
    lines += table(headers, rows)
    lines += ['', 'Sensitivity excludes the first receipt of every slot symmetrically. Wall is slot-only.', '']
    lines += table(['Task', 'Prediction', 'More turns', 'More thinking', 'Same delivery', 'Efficiency'],
                   [[pair['task'], pair['prediction']['status'], pair['prediction']['more_terminal_turns'],
                     pair['prediction']['more_thinking_tokens'], pair['prediction']['same_delivery_outcome'],
                     pair['efficiency']['conclusion'] + ': ' + pair['efficiency']['reason']]
                    for pair in summary['comparisons']])
    lines += ['', 'Frozen prediction: ' + summary['prediction'], '', summary['limits']]
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--json', type=Path, help='write derived summary JSON outside sealed slot evidence')
    args = parser.parse_args(argv)
    result = summarize(args.output)
    if args.json:
        require(not args.json.resolve().is_relative_to(args.output.resolve()),
                'write derived summaries outside the retained evidence tree')
        with args.json.open('x') as stream:
            stream.write(json.dumps(result, indent=2) + '\n')
    print(markdown(result), end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
