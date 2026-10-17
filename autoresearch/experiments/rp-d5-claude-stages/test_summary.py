"""Offline comparison oracles; no report reviewers or live boundaries."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import urllib.request

import pytest

HERE = Path(__file__).resolve().parent


@pytest.fixture
def summary(monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail('live boundary forbidden')
    for target, name in ((socket, 'create_connection'), (urllib.request, 'urlopen'),
                         (subprocess, 'run'), (subprocess, 'Popen')):
        monkeypatch.setattr(target, name, forbidden)
    spec = importlib.util.spec_from_file_location('rpd5_summary_test', HERE / 'summarize.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def counts(turns, uncached, read, write, output, thinking):
    return dict(turns=turns, input_tokens=uncached, cache_read_input_tokens=read,
                cache_creation_input_tokens=write, output_tokens=output,
                thinking_tokens=thinking, marginal_tokens=write + output)


@pytest.fixture
def evidence(tmp_path, monkeypatch, summary):
    rows, analyses = [], {}
    for slot, task, effort in summary.SCHEDULE:
        maximum = effort == 'max'
        totals = counts(5, 10, 100, 40, 80, 60) if maximum else counts(3, 6, 60, 20, 30, 10)
        first = counts(1, 2, 5, 10, 20, 10) if maximum else counts(1, 2, 5, 5, 10, 5)
        analyses[slot] = dict(status='MATCH', owner_seconds=50 if maximum else 30,
                              totals=totals, sensitivity={key: value - first[key] for key, value in totals.items()})
        rows.append(dict(cell=slot, task=task, effort=effort, config='claude', arm='X',
                         phase='measured', measurement_eligible=True, dispatched=True,
                         status='ADJUDICATE', inherited_status='PASS', delivery_assessment='ADJUDICATE',
                         merge_refused=False, usage='COMPLETE', account=['a' * 12, 'b' * 12],
                         release=dict(version='4.2.22', sha256='c' * 64)))
    monkeypatch.setattr(summary.attribute, 'analyze', lambda out, **_: deepcopy(analyses[out.name]))
    monkeypatch.setattr(summary.attribute, 'markdown', lambda result: 'Synthetic attribution table')
    return summary, tmp_path, rows, analyses


def flush(evidence, status='RECORDED'):
    summary, out, rows, _ = evidence
    for row in rows:
        path = out / row['cell'] / 'rp-verdict.json'
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(row))
    (out / 'rp-schedule.json').write_text(json.dumps(dict(phase='measured', status=status,
        slots=rows, dispatched=sum(row['dispatched'] for row in rows))))
    return summary.summarize(out)


def test_raw_symmetric_sensitivity_and_prediction(evidence):
    result = flush(evidence)
    assert result['prediction'] == 'PASS'
    for pair in result['comparisons']:
        assert pair['raw']['turns'] == 2
        assert pair['raw']['thinking_tokens'] == 50
        assert pair['raw']['total_input_tokens'] == 64
        assert pair['raw']['owner_seconds'] == 20
        assert pair['sensitivity']['turns'] == 2
        assert pair['sensitivity']['thinking_tokens'] == 45
        assert pair['sensitivity']['cache_creation_input_tokens'] == 15
        assert 'owner_seconds' not in pair['sensitivity']
        assert pair['efficiency']['conclusion'] == 'HIGH_LOWER'
    rendered = evidence[0].markdown(result)
    assert rendered.count('Synthetic attribution table') == 4
    assert 'not partitioned' in rendered


@pytest.mark.parametrize('failure', ['local_only', 'merge_refused', 'source_checks'])
def test_delivery_failure_keeps_costs_and_withholds_efficiency(evidence, failure):
    row = evidence[2][0]
    if failure == 'merge_refused':
        row['merge_refused'] = True
    elif failure == 'source_checks':
        row['inherited_status'] = 'PRODUCT_INCOMPLETE'
    else:
        row.update(status='PRODUCT_INCOMPLETE', delivery_assessment='PRODUCT_INCOMPLETE')
    result = flush(evidence)
    assert result['slots'][0]['delivery_outcome'] == 'FAIL'
    assert result['slots'][0]['metrics']['thinking_tokens'] == 60
    pair = result['comparisons'][0]
    assert pair['efficiency']['conclusion'] == 'WITHHELD'
    assert pair['prediction']['status'] == 'FAIL'
    assert result['comparisons'][1]['efficiency']['eligible'] is True


def test_same_failed_delivery_can_satisfy_prediction_without_efficiency(evidence):
    for row in evidence[2][:2]:
        row.update(status='PRODUCT_INCOMPLETE', delivery_assessment='PRODUCT_INCOMPLETE')
    pair = flush(evidence)['comparisons'][0]
    assert pair['prediction']['status'] == 'PASS'
    assert pair['efficiency']['eligible'] is False


@pytest.mark.parametrize('fault', ['STOP', 'UNKNOWN', 'usage', 'reconciliation'])
def test_unknown_numbers_never_establish_prediction_or_efficiency(evidence, fault):
    if fault in ('STOP', 'UNKNOWN'):
        evidence[2][0]['status'] = fault
    elif fault == 'usage':
        evidence[2][0]['usage'] = 'UNKNOWN'
    else:
        evidence[3]['c01'].update(status='UNKNOWN', totals=None, sensitivity=None)
    result = flush(evidence)
    assert result['prediction'] == 'UNKNOWN'
    assert all(value is None for value in result['slots'][0]['metrics'].values())
    assert all(value is None for value in result['slots'][0]['sensitivity'].values())
    assert result['slots'][0]['owner_seconds'] == 50
    assert result['comparisons'][0]['efficiency']['eligible'] is False
    assert evidence[0].markdown(result).count('Synthetic attribution table') == 3


def test_missing_wall_keeps_token_prediction_but_withholds_cost_conclusion(evidence):
    evidence[3]['c01']['owner_seconds'] = None
    result = flush(evidence)
    assert result['comparisons'][0]['prediction']['status'] == 'PASS'
    assert result['comparisons'][0]['raw']['owner_seconds'] is None
    assert result['comparisons'][0]['efficiency']['conclusion'] == 'UNKNOWN'


def test_equal_turns_or_thinking_fails_strict_prediction(evidence):
    evidence[3]['c01']['totals']['turns'] = 3
    evidence[3]['c04']['totals']['thinking_tokens'] = 10
    result = flush(evidence)
    assert result['prediction'] == 'FAIL'
    assert [pair['prediction']['status'] for pair in result['comparisons']] == ['FAIL', 'FAIL']


def test_paused_prefix_reports_remaining_slots_unknown(evidence):
    del evidence[2][1:]
    result = flush(evidence, status='PAUSED')
    assert len(result['slots']) == 4
    assert sum(row['dispatched'] for row in result['slots']) == 1
    assert result['prediction'] == 'UNKNOWN'
    assert result['slots'][1]['metrics']['turns'] is None


@pytest.mark.parametrize('fault', ['order', 'effort', 'release', 'account', 'verdict'])
def test_summary_refuses_rebound_schedule(evidence, fault):
    if fault == 'order':
        evidence[2][0], evidence[2][1] = evidence[2][1], evidence[2][0]
    elif fault == 'effort':
        evidence[2][1]['effort'] = 'max'
    elif fault == 'release':
        evidence[2][1]['release']['sha256'] = 'd' * 64
    elif fault == 'account':
        evidence[2][1]['account'] = ['c' * 12, 'b' * 12]
    else:
        flush(evidence)
        path = evidence[1] / 'c01/rp-verdict.json'
        row = json.loads(path.read_text())
        row['status'] = 'STOP'
        path.write_text(json.dumps(row))
        with pytest.raises(ValueError, match='schedule/verdict'):
            evidence[0].summarize(evidence[1])
        return
    with pytest.raises(ValueError):
        flush(evidence)


def test_real_sealed_receipts_survive_repository_deletion_and_feed_summary(summary, tmp_path):
    fixtures = summary.load('rpd5_summary_native_fixtures', HERE.parent / '0254/test_audit.py')
    rows = []
    for slot, task, effort in summary.SCHEDULE:
        out = tmp_path / slot
        capture = fixtures.Capture(out)
        capture.files['run/result.json'] = dict(seconds=42, owner_status='EXITED_0')
        for entry in capture.files[fixtures.BODY + '/index.jsonl']:
            capture.files[fixtures.BODY + '/' + entry['request_file']]['output_config']['effort'] = effort
        manifest = capture.seal()
        inherited = tmp_path / ('verdict-' + slot + '.json')
        inherited.write_text(json.dumps(dict(evidence_manifest_sha256=manifest, owner_seconds=42)))
        record = dict(cell=slot, task=task, effort=effort, config='claude', arm='X',
                      phase='measured', measurement_eligible=True, dispatched=True,
                      status='ADJUDICATE', inherited_status='PASS', delivery_assessment='ADJUDICATE',
                      merge_refused=False, usage='COMPLETE', account=[fixtures.ACCOUNT, 'b' * 12],
                      inherited_verdict_sha256=hashlib.sha256(inherited.read_bytes()).hexdigest(),
                      release=dict(version='4.2.22', sha256='c' * 64),
                      repository_cleanup=dict(status='DELETED', http_status=404))
        (out / 'rp-verdict.json').write_text(json.dumps(record))
        rows.append(record)
    (tmp_path / 'rp-schedule.json').write_text(json.dumps(dict(phase='measured', status='RECORDED',
                                                             slots=rows, dispatched=4)))
    before = {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob('*') if path.is_file()}
    result = summary.summarize(tmp_path)
    rendered = summary.markdown(result)
    assert all(row['accounting'] == 'MATCH' and row['owner_seconds'] == 42 for row in result['slots'])
    assert all(row['metrics']['turns'] == 3 and row['metrics']['total_input_tokens'] == 63
               for row in result['slots'])
    assert result['prediction'] == 'FAIL'  # Equal counts fail the strict frozen prediction.
    assert all(pair['efficiency']['conclusion'] == 'TIED' for pair in result['comparisons'])
    assert 'First row msg_synthetic_1' in rendered
    assert 'shared and non-additive' in rendered
    assert before == {path.relative_to(tmp_path): path.read_bytes()
                      for path in tmp_path.rglob('*') if path.is_file()}


def test_cli_refuses_writing_summary_into_retained_evidence(evidence):
    flush(evidence)
    with pytest.raises(ValueError, match='outside the retained evidence'):
        evidence[0].main([str(evidence[1]), '--json', str(evidence[1] / 'rp-schedule.json')])
