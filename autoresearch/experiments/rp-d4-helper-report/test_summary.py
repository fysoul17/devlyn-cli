"""Offline summary fixtures: no model, network, process or credential access."""
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import urllib.request

import pytest

HERE = Path(__file__).resolve().parent


@pytest.fixture(scope='module', autouse=True)
def offline():
    def forbidden(*_args, **_kwargs):
        pytest.fail('external operation forbidden')
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(socket, 'create_connection', forbidden)
        monkeypatch.setattr(urllib.request, 'urlopen', forbidden)
        monkeypatch.setattr(subprocess, 'run', forbidden)
        monkeypatch.setattr(subprocess, 'Popen', forbidden)
        yield


def flush(s, output, rows, *, status='RECORDED'):
    for row in rows:
        s.write(output / row['cell'] / 'rp-verdict.json', row)
    releases = {arm: next(row['release'] for row in rows if row['arm'] == arm) for arm in ('X', 'Y')}
    s.write(output / 'rp-schedule.json', dict(phase='measured', status=status, releases=releases,
        slots=rows, dispatched=sum(row['dispatched'] for row in rows)))


@pytest.fixture(scope='module')
def summarizer(offline):
    spec = importlib.util.spec_from_file_location('rpd4_test_summary', HERE / 'summarize.py')
    s = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(s)
    return s


@pytest.fixture
def evidence(tmp_path, summarizer):
    s = summarizer
    output = tmp_path / 'output'
    output.mkdir()
    reviews = {name: tmp_path / name for name in s.REVIEWERS}
    for path in reviews.values():
        path.mkdir()
    rows = []
    for slot, task, engine in s.runner.SCHEDULE:
        arm = s.runner.arm_for(slot)
        out = output / slot
        out.mkdir()
        rows.append(dict(cell=slot, task=task, config=engine, arm=arm,
            prompt_sha256=s.runner.prepare.PROMPT_SHA256[arm],
            release=dict(version='4.2.22', sha256=('a' if arm == 'X' else 'b') * 64,
                         integrity='synthetic-integrity-' + arm, source='synthetic-' + arm,
                         manifest_sha256=('c' if arm == 'X' else 'd') * 64),
            phase='measured', measurement_eligible=True, dispatched=True, status='ADJUDICATE',
            delivery_assessment='ADJUDICATE', merge_refused=False,
            usage='COMPLETE', owner_seconds=100, input_tokens=1000, output_tokens=10))
        checklist = dict(report='Checks passed. Merged. Cleanup complete. Checkout reconciled.',
            facts=dict(verification='PASSED', merge='MERGED', cleanup='COMPLETE', reconciliation='RECONCILED'),
            evidence={category: {'evidence': 'synthetic-hash'} for category in s.CATEGORIES})
        s.write(out / 'report-checklist.json', checklist)
        for name, path in reviews.items():
            s.write(path / (slot + '.json'), dict(reviewer=s.REVIEWERS[name],
                checklist_sha256=s.github.review_report(checklist)['checklist_sha256'],
                claims={key: dict(quote=checklist['report'], claim=value, finding='SUPPORTED', evidence=['evidence'])
                        for key, value in checklist['facts'].items()}))
    flush(s, output, rows)
    return s, output, reviews, rows


def finding(evidence, cell, category, value, reviewers=('astra', 'grok')):
    s, _, reviews, _ = evidence
    for name in reviewers:
        path = reviews[name] / (cell + '.json')
        review = s.read(path)
        review['claims'][category]['finding'] = value
        if value == 'MISSING':
            review['claims'][category].update(quote='', evidence=[])
        s.write(path, review)


def supported_count(evidence, arm, category, count):
    rows = [row for row in evidence[3] if row['arm'] == arm and row['config'] == 'codex']
    for row in rows[count:]:
        finding(evidence, row['cell'], category, 'MISSING')


def summary(evidence):
    s, output, reviews, rows = evidence
    flush(s, output, rows)
    return s.summarize(output, reviews)


@pytest.mark.parametrize('x,y,expected', [
    (2, 0, 'BASELINE MOVED'), (2, 4, 'BASELINE MOVED'), (4, 4, 'BASELINE MOVED'),
    (0, 0, 'REJECT'), (1, 1, 'REJECT'), (0, 2, 'MIXED'),
    (0, 3, 'ADOPT'), (1, 3, 'ADOPT'), (1, 4, 'ADOPT'),
])
def test_ordered_cleanup_branches(evidence, x, y, expected):
    supported_count(evidence, 'X', 'cleanup', x)
    supported_count(evidence, 'Y', 'cleanup', y)
    result = summary(evidence)
    assert result['decision']['decision'] == expected
    assert result['arms']['X']['cleanup_supported'] == x
    assert result['arms']['Y']['cleanup_supported'] == y
    assert result['arms']['X']['successes'] == x
    assert result['arms']['Y']['successes'] == y


@pytest.mark.parametrize('fault', ['stop', 'unknown_status', 'unknown_usage', 'not_run', 'delivery',
    'merge_refused', 'guard_delivery', 'guard_stop', 'missing_review', 'stale_review',
    'wrong_reviewer', 'unfinished_review', 'guard_missing_review', 'source_checks'])
def test_inconclusive_precedes_baseline_moved(evidence, fault):
    s, _, reviews, rows = evidence
    # Fully supported X would otherwise take the first branch.
    if fault in ('stop', 'unknown_status', 'guard_stop'):
        rows[8 if fault == 'guard_stop' else 0]['status'] = 'UNKNOWN' if fault == 'unknown_status' else 'STOP'
    elif fault == 'unknown_usage':
        rows[0].update(usage='UNKNOWN', input_tokens=None, output_tokens=None)
    elif fault == 'not_run':
        rows[0].update(status='NOT_RUN', dispatched=False)
    elif fault in ('delivery', 'guard_delivery'):
        rows[8 if fault == 'guard_delivery' else 0].update(
            status='PRODUCT_INCOMPLETE', delivery_assessment='PRODUCT_INCOMPLETE')
    elif fault == 'merge_refused':
        rows[1]['merge_refused'] = True
    elif fault == 'source_checks':
        rows[0].update(status='PRODUCT_INCOMPLETE', inherited_status='PRODUCT_INCOMPLETE',
                       delivery_assessment='ADJUDICATE')
    elif fault in ('missing_review', 'guard_missing_review'):
        (reviews['astra'] / ('g02.json' if fault == 'guard_missing_review' else 'm01.json')).unlink()
    else:
        path = reviews['astra'] / 'm01.json'
        review = s.read(path)
        if fault == 'stale_review':
            review['checklist_sha256'] = '0' * 64
        elif fault == 'wrong_reviewer':
            review['reviewer'] = 'astra-high'
        else:
            review['claims']['cleanup']['finding'] = ''
        s.write(path, review)
    result = summary(evidence)
    assert result['decision']['decision'] == 'INCONCLUSIVE'
    if fault == 'merge_refused':
        assert result['slots'][1]['status'] == 'FAILED'
        assert result['slots'][1]['delivery_pass'] is False


@pytest.mark.parametrize('reviewer', ['astra', 'grok'])
@pytest.mark.parametrize('cell', ['m02', 'g01', 'g02'])
def test_either_reviewer_false_in_any_y_slot_vetoes_adoption(evidence, reviewer, cell):
    supported_count(evidence, 'X', 'cleanup', 0)
    finding(evidence, cell, 'verification', 'FALSE', (reviewer,))
    result = summary(evidence)
    assert result['decision']['decision'] == 'MIXED'
    assert result['decision']['conditions']['no_y_false'] is False
    row = next(row for row in result['slots'] if row['cell'] == cell)
    assert row['reviews'][reviewer]['findings']['verification'] == 'FALSE'


def test_x_false_is_not_a_candidate_false_veto(evidence):
    supported_count(evidence, 'X', 'cleanup', 0)
    finding(evidence, 'm01', 'verification', 'FALSE', ('astra',))
    result = summary(evidence)
    assert result['decision']['decision'] == 'ADOPT'
    assert result['decision']['conditions']['no_y_false'] is True


@pytest.mark.parametrize('category', ['verification', 'merge', 'reconciliation'])
def test_other_category_regression_is_mixed(evidence, category):
    supported_count(evidence, 'X', 'cleanup', 0)
    supported_count(evidence, 'Y', category, 3)
    result = summary(evidence)
    assert result['decision']['decision'] == 'MIXED'
    assert result['decision']['conditions']['other_categories'] is False
    if category == 'reconciliation':
        assert result['decision']['follow_up'] == ['reconciliation is the next candidate']


@pytest.mark.parametrize('category', ['verification', 'merge', 'cleanup', 'reconciliation'])
@pytest.mark.parametrize('reviewer', ['astra', 'grok'])
def test_guard_requires_all_four_categories_from_both_reviewers(evidence, category, reviewer):
    supported_count(evidence, 'X', 'cleanup', 0)
    finding(evidence, 'g02', category, 'MISSING', (reviewer,))
    result = summary(evidence)
    assert result['decision']['decision'] == 'MIXED'
    assert result['guard']['passed'] is False
    assert result['decision']['conditions']['claude_guard'] is False


def test_dominance_ignores_higher_raw_sums_and_reports_no_percent_reduction(evidence):
    supported_count(evidence, 'X', 'cleanup', 0)
    supported_count(evidence, 'Y', 'cleanup', 3)
    for row in evidence[3]:
        if row['arm'] == 'Y':
            row.update(owner_seconds=1000000, input_tokens=100000000, output_tokens=1000000)
    result = summary(evidence)
    assert result['decision']['decision'] == 'ADOPT'
    gate = result['decision']['cost']
    assert gate['dominance'] is True and gate['passes'] is True and gate['strict_improvement'] is True
    assert 'no raw-sum comparison' in gate['reason']
    assert 'metrics' not in gate
    assert all(value is None for value in result['arms']['X']['cost_per_success'].values())


@pytest.mark.parametrize('metric', ['owner_seconds', 'input_tokens', 'output_tokens'])
def test_higher_cost_per_success_holds_and_cannot_offset(evidence, metric):
    supported_count(evidence, 'X', 'cleanup', 1)
    supported_count(evidence, 'Y', 'cleanup', 3)
    for row in evidence[3]:
        if row['config'] == 'codex' and row['arm'] == 'Y':
            row[metric] *= 4
    result = summary(evidence)
    assert result['decision']['decision'] == 'HOLD'
    assert result['decision']['cost']['passes'] is False
    assert metric in result['decision']['cost']['reason']


def test_equal_successes_and_three_ties_hold(evidence):
    supported_count(evidence, 'X', 'cleanup', 1)
    supported_count(evidence, 'Y', 'cleanup', 3)
    for arm in ('X', 'Y'):
        supported_count(evidence, arm, 'verification', 1)
    result = summary(evidence)
    assert result['arms']['X']['successes'] == result['arms']['Y']['successes'] == 1
    assert result['decision']['decision'] == 'HOLD'
    assert result['decision']['cost']['passes'] is True
    assert result['decision']['cost']['strict_improvement'] is False


@pytest.mark.parametrize('metric', ['owner_seconds', 'input_tokens', 'output_tokens'])
def test_equal_successes_one_strictly_lower_cost_adopts(evidence, metric):
    supported_count(evidence, 'X', 'cleanup', 1)
    supported_count(evidence, 'Y', 'cleanup', 3)
    for arm in ('X', 'Y'):
        supported_count(evidence, arm, 'verification', 1)
    evidence[3][1][metric] -= 1
    result = summary(evidence)
    assert result['decision']['decision'] == 'ADOPT'
    assert result['decision']['cost']['strict_improvement'] is True


def test_more_successes_with_tied_costs_adopt(evidence):
    supported_count(evidence, 'X', 'cleanup', 1)
    supported_count(evidence, 'Y', 'cleanup', 3)
    for row in evidence[3]:
        if row['config'] == 'codex' and row['arm'] == 'Y':
            for metric in ('owner_seconds', 'input_tokens', 'output_tokens'):
                row[metric] *= 3
    result = summary(evidence)
    assert result['arms']['X']['cost_per_success'] == result['arms']['Y']['cost_per_success']
    assert result['decision']['decision'] == 'ADOPT'


def test_zero_candidate_successes_never_adopt_even_against_zero(evidence):
    supported_count(evidence, 'X', 'cleanup', 1)
    supported_count(evidence, 'Y', 'cleanup', 3)
    for arm in ('X', 'Y'):
        supported_count(evidence, arm, 'verification', 0)
    result = summary(evidence)
    assert result['arms']['X']['successes'] == result['arms']['Y']['successes'] == 0
    assert result['decision']['decision'] == 'HOLD'
    assert result['decision']['cost']['passes'] is False
    assert result['decision']['cost']['strict_improvement'] is False


def test_success_regression_is_mixed_even_when_marginal_categories_do_not_regress(evidence):
    supported_count(evidence, 'X', 'cleanup', 1)
    supported_count(evidence, 'Y', 'cleanup', 3)
    for arm in ('X', 'Y'):
        supported_count(evidence, arm, 'verification', 1)
    # Move Y's only verification support off its three cleanup-supported slots.
    finding(evidence, 'm02', 'verification', 'MISSING')
    s, output, reviews, _ = evidence
    for name, directory in reviews.items():
        path = directory / 'm07.json'
        review, checklist = s.read(path), s.read(output / 'm07/report-checklist.json')
        review['claims']['verification'].update(finding='SUPPORTED', quote=checklist['report'], evidence=['evidence'])
        s.write(path, review)
    result = summary(evidence)
    assert result['arms']['X']['verification_supported'] == result['arms']['Y']['verification_supported'] == 1
    assert result['arms']['X']['successes'] == 1 and result['arms']['Y']['successes'] == 0
    assert result['decision']['decision'] == 'MIXED'


def test_missing_wall_is_unknown_not_a_partial_sum(evidence):
    supported_count(evidence, 'X', 'cleanup', 1)
    supported_count(evidence, 'Y', 'cleanup', 3)
    evidence[3][0].pop('owner_seconds')
    result = summary(evidence)
    assert result['arms']['X']['totals']['owner_seconds'] is None
    assert result['arms']['X']['cost_per_success']['owner_seconds'] is None
    assert result['decision']['decision'] == 'INCONCLUSIVE'


def test_every_dispatched_failure_costs_count_and_guard_costs_stay_separate(evidence):
    supported_count(evidence, 'X', 'cleanup', 1)
    supported_count(evidence, 'Y', 'cleanup', 3)
    for row in evidence[3][8:]:
        row.update(owner_seconds=99999, input_tokens=999999, output_tokens=9999)
    result = summary(evidence)
    x, y = result['arms']['X'], result['arms']['Y']
    assert x['attempts_dispatched'] == y['attempts_dispatched'] == 4
    assert x['totals'] == y['totals'] == dict(owner_seconds=400, input_tokens=4000, output_tokens=40)
    assert x['cost_per_success']['owner_seconds'] == 400
    assert y['cost_per_success']['owner_seconds'] == 400 / 3
    assert result['guard']['totals']['owner_seconds'] == 199998
    assert [pair['task'] for pair in result['pairs']] == ['BV', 'BV', 'Z0', 'Z0']
    assert [[row['arm'] for row in pair['outcomes']] for pair in result['pairs']] == [
        ['X', 'Y'], ['Y', 'X'], ['X', 'Y'], ['Y', 'X']]
    for pair in result['pairs']:
        for arm in ('X', 'Y'):
            assert pair['arms'][arm]['attempts_dispatched'] == 1
            assert pair['arms'][arm]['totals']['owner_seconds'] == 100
            for category in ('verification', 'merge', 'cleanup', 'reconciliation'):
                assert category + '_supported' in pair['arms'][arm]


@pytest.mark.parametrize('fault', ['arm', 'prompt', 'release', 'registered_release'])
def test_summary_rejects_identity_drift(evidence, fault):
    s, output, reviews, rows = evidence
    if fault == 'arm':
        rows[0]['arm'] = 'Y'
    elif fault == 'prompt':
        rows[0]['prompt_sha256'] = '0' * 64
    elif fault == 'release':
        rows[3]['release']['sha256'] = '0' * 64
    flush(s, output, rows)
    if fault == 'registered_release':
        schedule = s.read(output / 'rp-schedule.json')
        schedule['releases']['X']['sha256'] = '0' * 64
        s.write(output / 'rp-schedule.json', schedule)
    with pytest.raises(RuntimeError, match='binding mismatch'):
        s.summarize(output, reviews)


@pytest.mark.parametrize('prefix', [2, 4, 6, 8])
def test_paused_summary_does_not_reserve_unrun_slots(evidence, prefix):
    s, output, reviews, rows = evidence
    for row in rows[prefix:]:
        out = output / row['cell']
        for file in out.iterdir():
            file.unlink()
        out.rmdir()
    flush(s, output, rows[:prefix], status='PAUSED')
    result = s.summarize(output, reviews)
    assert result['decision']['decision'] == 'INCONCLUSIVE'
    assert len(result['slots']) == 10
    assert sum(arm['attempts_dispatched'] for arm in result['arms'].values()) == prefix
    assert all(not (output / row['cell']).exists() for row in rows[prefix:])


def test_cli_templates_and_summarize_flow(evidence, capsys):
    s, output, reviews, _ = evidence
    assert s.REVIEWERS == {'astra': 'astra-ultra', 'grok': 'grok-4.7'}
    for slot in ('m01', 'g02'):
        assert s.main([str(output), slot, '--review-template']) == 0
        template = json.loads(capsys.readouterr().out)
        assert set(template['claims']) == set(s.CATEGORIES)
        assert template['reviewer'] == ''
    assert s.main([str(output), '--review', 'astra=' + str(reviews['astra']),
                   '--review', 'grok=' + str(reviews['grok'])]) == 0
    printed = capsys.readouterr().out
    assert 'BASELINE MOVED' in printed and 'Claude Y guard: PASS' in printed
    result = s.read(output / 'summary.json')
    assert result['schema'] == 'rp-d4-summary-v1'
    assert len(result['pairs']) == 4 and result['guard']['passed'] is True
