"""Mechanical adoption and unchanged rp-d1 report grading on synthetic slots."""
import pytest

from test_rpd2_pack import load

s = load('summarize')


def counts(successes=2, seconds=100, tokens=1000):
    return s.aggregate([dict(status='SUCCESS' if i < successes else 'FAILED', dispatched=True,
                             owner_seconds=seconds, input_tokens=tokens, output_tokens=10, usage='COMPLETE')
                        for i in range(4)])


def arms(x=2, y=2):
    return dict(X=dict(claude=counts(), codex=counts(x)), Y=dict(claude=counts(), codex=counts(y)))


@pytest.mark.parametrize('x,y,decision,quality,cost', [
    (0, 1, 'ADOPT', 'IMPROVED', 'NO_BASELINE'),
    (0, 0, 'REJECT', 'UNCHANGED', 'NO_BASELINE'),
    (1, 0, 'REJECT', 'WORSE', 'NO_BASELINE'),
    (2, 3, 'ADOPT', 'IMPROVED', 'IMPROVED'),
    (3, 2, 'REJECT', 'WORSE', 'WORSE'),
    (2, 2, 'REJECT', 'UNCHANGED', 'UNCHANGED'),
])
def test_quality_and_zero_success_rules(x, y, decision, quality, cost):
    result = s.adoption(arms(x, y))
    assert result['decision'] == decision
    assert [row['status'] for row in result['rows'] if row['engine'] == 'codex'] == [quality, cost]
    if cost == 'NO_BASELINE':
        assert 'no baseline' in result['rows'][-1]['reason']


@pytest.mark.parametrize('metric', s.METRICS)
def test_each_cost_metric_can_improve_or_veto_adoption(metric):
    value = arms()
    value['Y']['codex']['cost_per_success'][metric] -= 1
    assert s.adoption(value)['decision'] == 'ADOPT'
    value['Y']['claude']['cost_per_success'][metric] += 1
    assert s.adoption(value)['decision'] == 'REJECT'
    assert metric in s.adoption(value)['rows'][1]['reason']


@pytest.mark.parametrize('arm', ['X', 'Y'])
def test_unknown_compared_usage_or_wall_blocks_adoption(arm):
    value = arms(2, 3)
    value[arm]['claude']['completeness'] = 'UNKNOWN'
    assert s.adoption(value)['decision'] == 'INCONCLUSIVE'
    assert s.adoption(value)['rows'][1]['status'] == 'UNKNOWN'
    value[arm]['claude']['completeness'] = 'COMPLETE'
    value[arm]['claude']['wall_completeness'] = 'UNKNOWN'
    assert s.adoption(value)['decision'] == 'INCONCLUSIVE'
    value[arm]['claude']['wall_completeness'] = 'COMPLETE'
    value[arm]['claude']['cost_per_success']['input_tokens'] = None
    assert s.adoption(value)['decision'] == 'INCONCLUSIVE'


def test_unknown_usage_on_no_baseline_row_is_not_an_infinite_cost():
    value = arms(0, 1)
    value['X']['codex']['completeness'] = 'UNKNOWN'
    value['X']['codex']['cost_per_success'] = dict.fromkeys(s.METRICS)
    assert s.adoption(value)['decision'] == 'ADOPT'


@pytest.mark.parametrize('field', ['pending', 'not_assessed', 'attempts_dispatched'])
def test_unresolved_or_incomplete_schedule_is_inconclusive(field):
    value = arms(2, 3)
    value['Y']['codex'][field] = 1
    result = s.adoption(value)
    assert result['decision'] == 'INCONCLUSIVE'
    assert all(row['status'] == 'UNKNOWN' for row in result['rows'][-2:])


@pytest.fixture
def evidence(tmp_path):
    output = tmp_path / 'output'
    output.mkdir()
    reviews = {name: tmp_path / name for name in s.REVIEWERS}
    for path in reviews.values():
        path.mkdir()
    records = []
    for slot, task, engine in s.runner.SCHEDULE:
        out = output / slot
        out.mkdir()
        records.append(dict(cell=slot, task=task, config=engine, arm=s.runner.arm_for(slot),
            phase='measured', measurement_eligible=True, dispatched=True, status='ADJUDICATE',
            usage='COMPLETE', owner_seconds=100, input_tokens=1000, output_tokens=10))
        checklist = dict(report='Checks passed. Merged. Cleanup pending. Checkout reconciled.',
            facts=dict(verification='PASSED', merge='MERGED', cleanup='CLEANUP_PENDING', reconciliation='RECONCILED'),
            evidence={category: {'evidence': 'sha'} for category in s.github.CATEGORIES})
        s.write(out / 'report-checklist.json', checklist)
        for name, path in reviews.items():
            s.write(path / (slot + '.json'), dict(reviewer=s.REVIEWERS[name],
                checklist_sha256=s.github.review_report(checklist)['checklist_sha256'],
                claims={key: dict(quote=checklist['report'], claim=value, finding='SUPPORTED', evidence=['evidence'])
                        for key, value in checklist['facts'].items()}))
    flush(output, records)
    return output, reviews, records


def flush(output, records):
    for row in records:
        s.write(output / row['cell'] / 'rp-verdict.json', row)
    s.write(output / 'rp-schedule.json', dict(phase='measured', slots=records,
        dispatched=sum(row['dispatched'] for row in records)))


def test_summary_groups_all_dispatched_costs_and_reuses_both_reviewers(evidence, capsys):
    output, reviews, records = evidence
    records[0]['status'] = 'PRODUCT_INCOMPLETE'
    flush(output, records)
    result = s.summarize(output, reviews)
    assert result['arms']['X']['claude']['successes'] == 3
    assert result['arms']['X']['claude']['attempts_dispatched'] == 4
    assert result['arms']['X']['claude']['totals'] == dict(owner_seconds=400, input_tokens=4000, output_tokens=40)
    assert result['arms']['X']['claude']['cost_per_success']['owner_seconds'] == 400 / 3
    assert result['adoption']['decision'] == 'ADOPT'
    assert result['arms']['Y']['claude']['successes'] == 4
    assert s.main([str(output), '--review', 'astra=' + str(reviews['astra']), '--review', 'grok=' + str(reviews['grok'])]) == 0
    assert 'ADOPT' in capsys.readouterr().out
    assert s.read(output / 'summary.json') == result
    slot = records[1]['cell']
    path = reviews['grok'] / (slot + '.json')
    review = s.read(path)
    review['claims']['cleanup'].update(finding='MISSING', quote='', evidence=[])
    s.write(path, review)
    result = s.summarize(output, reviews)
    assert result['slots'][1]['status'] == 'FAILED'
    (reviews['astra'] / (slot + '.json')).unlink()
    assert s.summarize(output, reviews)['slots'][1]['status'] == 'FAILED'
    path.unlink()
    assert s.summarize(output, reviews)['adoption']['decision'] == 'INCONCLUSIVE'


def test_unknown_usage_and_missing_wall_keep_totals_honest(evidence):
    output, reviews, records = evidence
    records[0].update(usage='UNKNOWN', input_tokens=None, output_tokens=None)
    records[1].pop('owner_seconds')
    flush(output, records)
    result = s.summarize(output, reviews)
    x, y = (result['arms'][arm]['claude'] for arm in ('X', 'Y'))
    assert x['totals'] == dict(owner_seconds=400, input_tokens=None, output_tokens=None)
    assert x['cost_per_success'] == dict.fromkeys(s.METRICS)
    assert y['totals']['owner_seconds'] is None
    assert y['totals']['input_tokens'] == 4000
    assert result['adoption']['decision'] == 'INCONCLUSIVE'


def test_template_and_schedule_arm_validation(evidence):
    output, _, records = evidence
    template = s.review_template(output, 'm01')
    assert set(template['claims']) == set(s.github.CATEGORIES)
    records[0]['arm'] = 'Y'
    flush(output, records)
    with pytest.raises(RuntimeError, match='arm mismatch'):
        s.measured_records(output)
    records[0]['arm'] = 'X'
    flush(output, records[:-1])
    with pytest.raises(RuntimeError, match='schedule differs'):
        s.measured_records(output)


def test_reevaluator_uses_sixteen_slot_census_without_mutating_raw(evidence, tmp_path):
    output, _, records = evidence
    for row in records:
        row.update(dispatched=False, status='NOT_RUN')
    flush(output, records)
    e = load('reevaluate')
    before = e.census(output)
    report = e.reevaluate(output, tmp_path / 'corrections')
    assert report['status'] == 'COMPLETE'
    assert report['raw_census'] == dict(before=before, after=before, unchanged=True)
    assert e.census(output) == before
    assert len(e.legacy.summary.measured_records(output)) == 16


@pytest.mark.parametrize('mismatch', ['arm', 'schedule'])
def test_reevaluator_reports_mismatch_diagnostic(evidence, tmp_path, capsys, mismatch):
    output, _, records = evidence
    if mismatch == 'arm':
        records[0]['arm'] = 'Y'
    else:
        records.pop()
    flush(output, records)
    e = load('reevaluate')
    dest = tmp_path / 'corrections'
    with pytest.raises(SystemExit) as stopped:
        e.main([str(output), str(dest)])
    assert stopped.value.code == 2
    diagnostic = 'arm mismatch' if mismatch == 'arm' else 'schedule differs'
    assert diagnostic in capsys.readouterr().err
    report = s.read(dest / 'reevaluation.json')
    assert report['status'] == 'FAILED'
    assert diagnostic in report['error']
    assert report['raw_census']['unchanged']
