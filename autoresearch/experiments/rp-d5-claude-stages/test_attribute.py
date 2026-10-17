"""Frozen stage oracle: synthetic native receipts, never a live model or account."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

import pytest

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


a = load('rpd5_attribute_test', HERE / 'attribute.py')
fixtures = load('rpd5_0254_fixtures', HERE.parent / '0254/test_audit.py')


def tool(name, value, identifier='toolu_stage'):
    return dict(type='tool_use', id=identifier, name=name, input=value)


def bash(command, identifier='toolu_stage'):
    return tool('Bash', {'command': command}, identifier)


def row(*calls, identifier='row', usage=None):
    return dict(row_id=identifier, usage=usage or dict(zip(a.COUNTERS, (2, 10, 7, 40, 30))), calls=list(calls))


def capture(tmp_path, calls, result=None, effort='max'):
    fixture = fixtures.Capture(tmp_path)
    for path in (fixtures.CHILD_FILE,):
        fixture.files[path][0]['message']['content'] = deepcopy(calls)
    fixture.files[fixture.indexed_file(2, 'response')]['content'] = deepcopy(calls)
    if result is not None:
        fixture.files[fixtures.CHILD_FILE].append(dict(type='user', sessionId=fixtures.SESSION,
            message=dict(role='user', content=[dict(type='tool_result', tool_use_id=calls[0]['id'], content=result)])))
    for entry in fixture.files[fixtures.BODY + '/index.jsonl']:
        fixture.files[fixtures.BODY + '/' + entry['request_file']]['output_config']['effort'] = effort
    fixture.files['run/result.json'] = dict(seconds=321.25, owner_status='EXITED_0')
    return fixture


def analyze(fixture, **kwargs):
    digest = fixture.seal()
    return a.analyze(fixture.out, manifest_sha256=digest, expected_effort='max', account=fixtures.ACCOUNT, **kwargs)


# Each tuple is an explicit frozen expectation, not a second implementation.
BASH_ORACLE = [
    ("python3 - <<'PY'\np.write_text('x')\nPY", 'Edit', {'write'}),
    ("python3 - <<'PY'\nprint('cp a b')\nPY", 'Other', {'unknown'}),
    ('''python3 -c 'open(p, "w")' ''', 'Edit', {'write'}),
    ('''python3 -c 'open(p, "rb")' ''', 'Other', {'unknown'}),
    ("python3 -c 'open(p, mode)'", 'Other', {'unknown'}),
    ('echo hello 2>&1', 'Other', set()),
    ('echo hello >/dev/null', 'Other', set()),
    ('echo hello >/tmp/x', 'Other', set()),
    ('rm /tmp/x', 'Other', set()),
    ('sudo cp a b', 'Edit', {'write'}),
    ('sed -i.bak f', 'Edit', {'write'}),
    ('dispatch', 'Other', set()),
    ('cat .agents/skills/_shared/task-complete.py', 'Orient', {'orient'}),
    ('python3 .agents/skills/_shared/task-complete.py allocate', 'Deliver', {'deliver'}),
    ('rg is_expired src/expiry/__init__.py', 'Explore', {'look'}),
    ('rg "is_expired|stale" src/expiry/__init__.py', 'Explore', {'look'}),
    ("rg -g '*.py' is_expired src/expiry/__init__.py", 'Explore', {'look'}),
    ('rg -n "def complete|merge_refused" .agents/skills/_shared/task-complete.py', 'Orient', {'orient'}),
    ('grep -n deadline src/limitcli/__init__.py', 'Explore', {'look'}),
    ('head -n 40 src/expiry/__init__.py', 'Explore', {'look'}),
    ("sed -n '1,40p' CLAUDE.md", 'Orient', {'orient'}),
    ('ls -la', 'Explore', {'look'}),
    ('cat CLAUDE.md src/expiry/__init__.py', 'Other', set()),
    ('git diff HEAD', 'Explore', {'look'}),
    ('git log -n 5', 'Explore', {'look'}),
    ("find . -name '*.py'", 'Explore', {'look'}),
    ('cat x && sed -i s/a/b/ x', 'Mixed', {'look', 'write'}),
    ('python3 fix.py', 'Other', {'unknown'}),
    ("python3 -c 'print(1); cp a b'", 'Other', {'unknown'}),
    ('python3 -B -m pytest -q', 'Verify', {'check'}),
    ('pytest -q', 'Verify', {'check'}),
    ('git status', 'Explore', {'look'}),
    ('gh pr view', 'Deliver', {'deliver'}),
    ('git add src/a.py && git commit -m done', 'Deliver', {'deliver'}),
    ('git apply /tmp/patch', 'Edit', {'write'}),
    ('patch -p1 < /tmp/patch', 'Edit', {'write'}),
    ('tee /tmp/x', 'Edit', {'write'}),
    ('echo hello > src/a.py', 'Edit', {'write'}),
    ('echo hello > .devlyn/state', 'Other', set()),
    ('rm /outside/x', 'Other', {'unknown'}),
    ('cp /outside/x src/a.py', 'Edit', {'unknown', 'write'}),
    ('command env MODE="safe" nohup time cp a b', 'Edit', {'write'}),
    ("'cp' a b", 'Other', set()),
    ('cat "unterminated', 'Other', set()),
    ('git diff -- CLAUDE.md', 'Orient', {'orient'}),
    ('git show /outside/file', 'Explore', {'look'}),
    ('rg -e is_expired -A 2 src/expiry/__init__.py', 'Explore', {'look'}),
    ('rg --glob=*.md --regexp=complete AGENTS.md', 'Orient', {'orient'}),
    ('grep -f /tmp/patterns AGENTS.md', 'Orient', {'orient'}),
    ('tail -n 40 CLAUDE.md', 'Orient', {'orient'}),
    ("python3 -c 'print(1)' && python3 -c 'p.write_text(1)'", 'Edit', {'write', 'unknown'}),
    ("python3 -c 'print(1)' && python3 - <<'PY'\np.write_text('x')\nPY", 'Edit', {'write', 'unknown'}),
    ("python3 - <<'PY'\nprint(1)\nPY\npython3 - <<'PY'\np.write_text('x')\nPY", 'Edit', {'write', 'unknown'}),
    ('''python3 -c 'open(Path(p), "w")' ''', 'Edit', {'write'}),
    ('''python3 -c 'open(p, encoding="UTF-8")' ''', 'Other', {'unknown'}),
    ('./fix', 'Other', {'unknown'}),
]


@pytest.mark.parametrize('command,label,predicates', BASH_ORACLE)
def test_frozen_bash_oracle_on_audited_child_receipt(tmp_path, command, label, predicates):
    result = analyze(capture(tmp_path, [bash(command)]))
    assert result['status'] == 'MATCH', result['gaps']
    observed = result['rows'][1]
    assert observed['stage'] == label
    assert set(observed['predicates']) == predicates
    assert result['totals']['output_tokens'] == 139
    assert result['rows'][0]['stage'] == 'Other'  # Agent does not take its child's class.
    assert observed['agent_id'] == fixtures.CHILD


@pytest.mark.parametrize('calls,label', [
    ([tool('Grep', {'pattern': 'x'})], 'Explore'),
    ([tool('Glob', {'pattern': '**/*.py'})], 'Explore'),
    ([tool('Read', {'file_path': '/cell/work'})], 'Explore'),
    ([tool('Read', {'file_path': '/cell/work/AGENTS.md'})], 'Orient'),
    ([tool('Read', {'file_path': '/cell/work/.agents/skills/_shared/task-completion.md'})], 'Orient'),
    ([tool('Read', {'file_path': 'x'}, 'read'), tool('Edit', {'file_path': 'x'}, 'edit')], 'Mixed'),
    ([tool('NotebookEdit', {'notebook_path': 'x.ipynb'})], 'Edit'),
    ([tool('Write', {'file_path': 'x', 'content': 'x'})], 'Edit'),
    ([tool('Read', {'file_path': '/outside/x'})], 'Other'),
    ([tool('Read', {'file_path': '/cell/work.devlyn.noindex/task/src/a.py'})], 'Explore'),
    ([tool('Read', {'file_path': '/cell/work.devlyn.noindex/task/AGENTS.md'})], 'Orient'),
])
def test_frozen_native_tool_oracle(tmp_path, calls, label):
    result = analyze(capture(tmp_path, calls))
    assert result['status'] == 'MATCH', result['gaps']
    assert result['rows'][1]['stage'] == label


def test_look_after_unknown_remains_explore_but_split_is_unsupported():
    rows, flags = a.classify_rows([row(bash("python3 -c 'print(1)'"), identifier='unknown'),
                                 row(tool('Read', {'file_path': 'x'}), identifier='look'),
                                 row(tool('Edit', {'file_path': 'x'}), identifier='edit')])
    assert [r['stage'] for r in rows] == ['Other', 'Explore', 'Edit']
    assert flags['explore_verify_supported'] is False
    assert rows[0]['mutation_unknown'] is True


def test_first_write_in_mixed_opens_verify_and_late_unknown_does_not_break_split():
    rows, flags = a.classify_rows([
        row(bash('cat x && sed -i s/a/b/ x'), identifier='mixed'),
        row(bash('python3 fix.py'), identifier='unknown'),
        row(tool('Read', {'file_path': 'x'}), identifier='look')])
    assert [r['stage'] for r in rows] == ['Mixed', 'Other', 'Verify']
    assert flags['first_write_row'] == 'mixed'
    assert flags['explore_verify_supported'] is True


def complete(status, identifier, delivery=None, trailer=''):
    call = bash('python3 .agents/skills/_shared/task-complete.py complete', identifier)
    call.update(returned=True, output=json.dumps(dict(status=status, delivery_status=delivery)) + trailer)
    return row(call, identifier=identifier)


@pytest.mark.parametrize('status', ['PR', 'PENDING', 'LOCAL_ONLY', 'FAILED', 'BLOCKED'])
def test_noncomplete_states_do_not_open_boundary(status):
    rows, flags = a.classify_rows([complete(status, 'pending'),
        row(tool('Read', {'file_path': 'x'}), identifier='pre'),
        complete('COMPLETE', 'done', trailer='\nLocal commit: abc123'),
        row(tool('Read', {'file_path': 'x'}), identifier='post'), row(identifier='report')])
    assert [r['stage'] for r in rows] == ['Deliver', 'Explore', 'Deliver', 'After delivery', 'Report']
    assert flags['delivery_boundary_row'] == 'done'


@pytest.mark.parametrize('delivery,expected', [('COMPLETE', 'After delivery'), ('PENDING', 'Explore')])
def test_cleanup_pending_requires_complete_delivery(delivery, expected):
    rows, _ = a.classify_rows([complete('CLEANUP_PENDING', 'done', delivery=delivery),
                              row(tool('Read', {'file_path': 'x'}), identifier='post')])
    assert rows[1]['stage'] == expected


@pytest.mark.parametrize('additional,predicate', [('cat x', 'look'), ('pytest -q', 'check')])
def test_complete_invoking_mixed_row_opens_boundary_for_next_row(additional, predicate):
    invoking = complete('COMPLETE', 'mixed')
    invoking['calls'][0]['input']['command'] += ' && ' + additional
    rows, flags = a.classify_rows([invoking, row(tool('Read', {'file_path': 'x'}), identifier='post')])
    assert rows[0]['stage'] == 'Mixed'
    assert set(rows[0]['predicates']) == {'deliver', predicate}
    assert rows[1]['stage'] == 'After delivery'
    assert flags['delivery_boundary_row'] == 'mixed'


def test_unparseable_complete_marks_boundary_and_later_rows_other_but_report_precedence():
    call = bash('python3 .agents/skills/_shared/task-complete.py complete')
    call.update(returned=True, output='not JSON')
    rows, flags = a.classify_rows([row(call, identifier='boundary'),
        row(tool('Edit', {'file_path': 'x'}), identifier='post'), row(identifier='last')])
    assert [r['stage'] for r in rows] == ['Other', 'Other', 'Report']
    assert flags['unparseable_complete_row'] == 'boundary'


def test_last_no_tool_is_report_earlier_no_tool_is_other():
    rows, _ = a.classify_rows([row(identifier='earlier'), row(identifier='last')])
    assert [r['stage'] for r in rows] == ['Other', 'Report']


def test_earlier_no_tool_after_delivery_is_still_other():
    rows, _ = a.classify_rows([complete('COMPLETE', 'done'), row(identifier='earlier'), row(identifier='last')])
    assert [r['stage'] for r in rows] == ['Deliver', 'Other', 'Report']


@pytest.mark.parametrize('output,exit_code', [('Exit code: 3', 3), ('exit code -1', -1),
    ('Process exited with code 5', 5), ('no exit code', None)])
def test_result_join_scrapes_exit_code_from_project_jsonl(tmp_path, output, exit_code):
    result = analyze(capture(tmp_path, [bash('pytest -q')], output))
    assert result['rows'][1]['calls'][0]['exit_code'] == exit_code
    assert result['rows'][1]['calls'][0]['returned'] is True


def test_json_encoded_result_and_trailer_are_decoded(tmp_path):
    fixture = capture(tmp_path, [bash('python3 .agents/skills/_shared/task-complete.py complete')],
                      {'status': 'COMPLETE'})
    result = analyze(fixture)
    assert result['flags']['delivery_boundary_row'] == 'msg_synthetic_2'


def test_reconciliation_stage_sum_first_row_and_symmetric_sensitivity(tmp_path):
    result = analyze(capture(tmp_path, [tool('Edit', {'file_path': 'x'})]))
    assert result['status'] == 'MATCH'
    assert result['owner_seconds'] == 321.25
    assert result['totals']['turns'] == 3
    for key in a.COUNTERS:
        assert sum(r['usage'][key] for r in result['rows']) == result['audit']['totals'][key]
        assert sum(s[key] for s in result['stages']) == result['audit']['totals'][key]
        assert result['sensitivity'][key] == result['totals'][key] - result['first_row'][key]
    assert result['totals']['marginal_tokens'] == 139 + 50
    assert result['sensitivity']['turns'] == 2
    assert result['cache_read_series'] == [dict(row_id=f'msg_synthetic_{i}', cache_read_input_tokens=n)
                                           for i, n in enumerate((0, 0, 7), 1)]
    assert result['flags']['low_coverage'] is True  # parent Agent is Other, 1/3.
    text = a.markdown(result)
    assert 'context only' in text and 'shared and non-additive' in text


def test_row_sum_mismatch_is_unknown_even_when_auditor_reports_match(tmp_path):
    fixture = capture(tmp_path, [bash('pytest -q')])
    original = a.audit.audit
    def changed(*args, **kwargs):
        report = original(*args, **kwargs)
        report['messages'][0]['usage']['input_tokens'] += 1
        return report
    with patch.object(a.audit, 'audit', changed):
        result = analyze(fixture)
    assert result['status'] == 'UNKNOWN'
    assert result['totals'] is result['sensitivity'] is result['first_row'] is None
    assert result['rows'] == result['stages'] == []
    assert result['gaps'] == ['attribution row sums do not reconcile']


def test_auditor_refusal_never_uses_partial_receipts(tmp_path):
    fixture = capture(tmp_path, [bash('pytest -q')])
    fixture.result()['modelUsage'][fixtures.MODEL]['outputTokens'] += 1
    result = analyze(fixture)
    assert result['status'] == 'UNKNOWN'
    assert result['totals'] is None and result['rows'] == []


def test_effort_mismatch_stops_even_when_auditor_refuses_earlier(tmp_path):
    fixture = capture(tmp_path, [bash('pytest -q')], effort='high')
    fixture.result()['is_error'] = True
    result = analyze(fixture)
    assert result['effort_binding'] == 'STOP'
    assert result['status'] == 'UNKNOWN'


def test_effort_binding_accepts_high_in_all_requests(tmp_path):
    fixture = capture(tmp_path, [bash('pytest -q')], effort='high')
    digest = fixture.seal()
    result = a.analyze(tmp_path, manifest_sha256=digest, expected_effort='high', account=fixtures.ACCOUNT)
    assert result['status'] == result['effort_binding'] == 'MATCH'


def test_repeats_use_complete_canonical_inputs_and_intervening_rows():
    same = tool('Read', {'file_path': 'x', 'offset': 1, 'limit': 20})
    reordered = tool('Read', {'limit': 20, 'offset': 1, 'file_path': 'x'})
    rows, _ = a.classify_rows([row(same, identifier='r1'),
        row(tool('Write', {'file_path': 'x'}), identifier='r2'),
        row(bash('python3 fix.py'), identifier='r3'), row(reordered, identifier='r4'),
        row(tool('Read', {'file_path': 'x', 'offset': 2, 'limit': 20}), identifier='r5')])
    repeated = a.repeats(rows)
    assert len(repeated) == 1
    assert [r['row_id'] for r in repeated[0]['occurrences']] == ['r1', 'r4']
    last = repeated[0]['occurrences'][1]
    assert last['intervening_write'] and last['intervening_unknown']
    assert last['tokens_label'] == 'shared and non-additive'
    assert last['enclosing_row_tokens'] == rows[3]['usage']


def test_heredoc_payload_is_part_of_repeat_identity():
    rows, _ = a.classify_rows([row(bash("python3 - <<'PY'\nprint(1)\nPY"), identifier='one'),
        row(bash("python3 - <<'PY'\nprint(2)\nPY"), identifier='two')])
    assert a.repeats(rows) == []


def test_repeat_flags_write_between_calls_within_one_enclosing_row():
    rows, _ = a.classify_rows([row(tool('Read', {'file_path': 'x'}, 'first'),
        tool('Write', {'file_path': 'x'}, 'write'), tool('Read', {'file_path': 'x'}, 'second'))])
    repeat = a.repeats(rows)[0]
    assert repeat['occurrences'][1]['intervening_write'] is True
    assert repeat['occurrences'][0]['enclosing_row_tokens'] == repeat['occurrences'][1]['enclosing_row_tokens']


def test_tool_identity_comes_from_response_not_transcript_snapshot(tmp_path):
    fixture = capture(tmp_path, [tool('Read', {'file_path': 'x'})])
    fixture.files[fixtures.CHILD_FILE][0]['message']['content'] = [tool('Write', {'file_path': 'x'})]
    result = analyze(fixture)
    assert result['status'] == 'MATCH'
    assert result['rows'][1]['stage'] == 'Explore'


def test_audited_index_order_is_preserved_without_timestamp_sort(tmp_path):
    fixture = capture(tmp_path, [tool('Read', {'file_path': 'x'})])
    index = fixture.files[fixtures.BODY + '/index.jsonl']
    index[0], index[1] = index[1], index[0]
    result = analyze(fixture)
    assert result['status'] == 'MATCH'
    assert [r['row_id'] for r in result['rows']] == ['msg_synthetic_2', 'msg_synthetic_1', 'msg_synthetic_3']
    assert result['first_row']['cache_creation_input_tokens'] == 10


def test_nonbash_result_preserves_is_error(tmp_path):
    fixture = capture(tmp_path, [tool('Read', {'file_path': 'x'})], 'missing file')
    fixture.files[fixtures.CHILD_FILE][-1]['message']['content'][0]['is_error'] = True
    result = analyze(fixture)
    assert result['rows'][1]['calls'][0]['error'] is True
    assert result['rows'][1]['calls'][0]['exit_code'] is None


def test_unknown_low_coverage_threshold_is_strict():
    fixture_rows = [row(bash('dispatch'), identifier='other')] + [
        row(tool('Read', {'file_path': 'x'}), identifier=f'look-{i}') for i in range(4)]
    rows, _ = a.classify_rows(fixture_rows)
    assert sum(r['stage'] == 'Other' for r in rows) / len(rows) == .2


def test_check_script_execution_not_mention_and_external_task_root():
    context = dict(check_scripts=['checks/run.py'], task_worktrees=['/tmp/task-worktree'])
    rows, _ = a.classify_rows([row(bash('python3 checks/run.py'), identifier='check'),
        row(bash('cat checks/run.py'), identifier='read'),
        row(tool('Read', {'file_path': '/tmp/task-worktree/src/a.py'}), identifier='worktree')], **context)
    assert [r['stage'] for r in rows] == ['Verify', 'Explore', 'Explore']


def test_default_expectations_use_bound_inherited_verdict(tmp_path):
    fixture = capture(tmp_path, [bash('pytest -q')])
    digest = fixture.seal()
    inherited = tmp_path.parent / ('verdict-' + tmp_path.name + '.json')
    inherited.write_text(json.dumps(dict(evidence_manifest_sha256=digest, owner_seconds=321.25)))
    (tmp_path / 'rp-verdict.json').write_text(json.dumps(dict(effort='max', account=[fixtures.ACCOUNT],
        inherited_verdict_sha256=hashlib.sha256(inherited.read_bytes()).hexdigest())))
    assert a.analyze(tmp_path)['status'] == 'MATCH'
    inherited.write_text(json.dumps(dict(evidence_manifest_sha256=digest, owner_seconds=999)))
    assert a.analyze(tmp_path)['status'] == 'UNKNOWN'
