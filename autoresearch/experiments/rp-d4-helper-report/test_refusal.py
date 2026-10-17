"""Offline refusal detection against raw native evidence, independent of its shape."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('refusal_rpd4_test', HERE / 'smoke.py')
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)

REFUSED = json.dumps(dict(merge_refused='synthetic refusal', status='PR'), sort_keys=True)
SUCCESS = json.dumps(dict(status='COMPLETE'), sort_keys=True)
CARRIERS = ('run/stdout', 'cell/trace/trace-owner/trace.jsonl',
            'cell/trace/trace-owner/payloads/result.json', 'cell/trace/trace-owner/inference.response',
            'home/.codex/sessions/owner.jsonl', 'home/.claude/projects/work/owner.jsonl',
            'home/.claude/api-bodies/owner.request.json', 'home/.claude/api-bodies/owner.response.json')


def seal(out, files):
    files = {'run/stdout': b'{}\n'} | files
    for name, raw in files.items():
        path = out / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    (out / 'evidence.manifest.json').write_text(json.dumps(dict(
        files={name: hashlib.sha256(raw).hexdigest() for name, raw in files.items()}, failures=[])))


@pytest.mark.parametrize('carrier', CARRIERS)
@pytest.mark.parametrize('escapes', range(3))
def test_refusal_anywhere_in_native_bytes(tmp_path, carrier, escapes):
    output = REFUSED
    for _ in range(escapes):
        output = json.dumps(output)
    # Neither UTF-8 nor a JSON document is needed to recognize the helper's bytes.
    seal(tmp_path, {carrier: b'\xff diagnostic\n' + output.encode() + b'\n' + SUCCESS.encode()})
    assert s.merge_refused(tmp_path) is True


@pytest.mark.parametrize('engine', ['codex', 'claude'])
@pytest.mark.parametrize('shape', ['nested', 'split_poll', 'batched_poll', 'code_mode'])
def test_native_envelopes_and_later_polling_chunks_keep_refusal(tmp_path, engine, shape):
    launch = json.dumps(dict(session_id=42, output='helper diagnostic\n'))
    if shape == 'nested':
        outputs = [json.dumps(dict(text='delivery', result={'output': REFUSED}))]
    elif shape == 'split_poll':
        # The process emits its whole JSON line in a later poll using a variable ID.
        outputs = [launch, '', json.dumps(dict(output=REFUSED, exit_code=0))]
    elif shape == 'batched_poll':
        outputs = [launch, json.dumps([dict(output='other process ready'), dict(output=REFUSED)])]
    else:
        outputs = [json.dumps([dict(status='fulfilled', value={'output': REFUSED})])]
    rows = []
    for index, output in enumerate(outputs + [SUCCESS]):
        if engine == 'codex':
            rows.append(dict(type='item.completed', item=dict(id=str(index), aggregated_output=output)))
        else:
            rows.append(dict(type='user', message={'content': [dict(
                type='tool_result', tool_use_id=str(index), content=[dict(type='text', text=output)])]}))
    seal(tmp_path, {'run/stdout': ''.join(json.dumps(row) + '\n' for row in rows).encode()})
    assert s.merge_refused(tmp_path) is True


@pytest.mark.parametrize('source_root', ['config', '.agents'])
@pytest.mark.parametrize('name', ['task-complete.py', 'task-completion.md'])
def test_real_helper_source_and_instructions_do_not_trigger(tmp_path, source_root, name):
    # Use the real shipped and installed bytes, including the helper's self-tests.
    source = (HERE.parents[2] / source_root / 'skills/_shared' / name).read_text()
    assert 'merge_refused' in source
    outputs = [source, '\n'.join(f'{n}:{line}' for n, line in enumerate(source.splitlines(), 1)
                                if 'merge_refused' in line)]
    for output in outputs:  # cat/inspection and rg output, raw and in code-mode envelopes
        for escapes in range(3):
            encoded = output
            for _ in range(escapes):
                encoded = json.dumps({'output': encoded})
            seal(tmp_path, {'run/stdout': encoded.encode()})
            assert s.merge_refused(tmp_path) is False


@pytest.mark.parametrize('carrier', CARRIERS)
@pytest.mark.parametrize('fault', ['missing', 'unreadable', 'changed'])
def test_evidence_failure_is_not_hidden_by_an_earlier_refusal(tmp_path, monkeypatch, carrier, fault):
    seal(tmp_path, {'run/stdout': REFUSED.encode(), carrier: REFUSED.encode()})
    path = tmp_path / carrier
    if fault == 'missing':
        path.unlink()
    elif fault == 'changed':
        path.write_bytes(b'changed')
    else:
        read_bytes = Path.read_bytes
        def unreadable(target):
            if target == path:
                raise PermissionError('synthetic unreadable native evidence')
            return read_bytes(target)
        monkeypatch.setattr(Path, 'read_bytes', unreadable)
    with pytest.raises((OSError, ValueError)):
        s.merge_refused(tmp_path)


@pytest.mark.parametrize('fault', ['missing_manifest', 'unlisted_stdout', 'empty_stdout', 'failed_seal'])
def test_missing_or_failed_evidence_is_rejected(tmp_path, fault):
    seal(tmp_path, {'run/stdout': b'' if fault == 'empty_stdout' else b'{}\n'})
    manifest = tmp_path / 'evidence.manifest.json'
    if fault == 'missing_manifest':
        manifest.unlink()
    elif fault in ('unlisted_stdout', 'failed_seal'):
        record = json.loads(manifest.read_text())
        if fault == 'unlisted_stdout':
            record['files'].pop('run/stdout')
        else:
            record['failures'].append('synthetic unreadable file during sealing')
        manifest.write_text(json.dumps(record))
    with pytest.raises((OSError, ValueError)):
        s.merge_refused(tmp_path)
