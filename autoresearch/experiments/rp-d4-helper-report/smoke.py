"""Read native helper output and qualify Y smoke against observed call actions.

The helper deliberately does not persist its action record.  Only Y smoke gets
a read-only Python profile observer: it copies complete()'s return and local
actions without changing the helper, its result, or its receipt.  The inherited
cell seal covers the resulting cell/helper-actions files.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

OBSERVER = '''"""rp-d4 Y-smoke observer; never loaded in measured cells."""
import hashlib
import json
import os
from pathlib import Path
import sys

def install():
    target = Path(sys.argv[0]).resolve()
    if target.name != "task-complete.py":
        return
    config = json.loads((Path(__file__).parent / "helper-observer.json").read_text())
    helper_hash = hashlib.sha256(target.read_bytes()).hexdigest()
    if helper_hash != config["helper_sha256"]:
        raise RuntimeError("rp-d4 observer helper binding mismatch")
    sequence = 0
    def observe(frame, event, value):
        nonlocal sequence
        try:
            if (event != "return" or frame.f_code.co_name != "complete" or
                    Path(frame.f_code.co_filename).resolve() != target or not isinstance(value, dict)):
                return
            actions = frame.f_locals.get("actions")
            if not isinstance(actions, dict):
                return
            sequence += 1
            path = Path(config["records"]) / (str(os.getpid()) + "-" + str(sequence) + ".json")
            record = dict(schema="rp-d4-helper-call-v1", helper_sha256=helper_hash,
                          actions=actions, result=value)
            encoded = json.dumps(record, sort_keys=True)
            with path.open("x") as stream:
                stream.write(encoded + "\\n")
            path.chmod(0o600)
        except Exception:
            # Observation must not change the helper. Missing/invalid evidence
            # fails qualification against native stdout after the run.
            return
    sys.setprofile(observe)

install()
'''


def require(value, message):
    if not value:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text())


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def install_observer(out):
    """Materializer hook, before the inherited plan/baseline preparation seal.

    Caller prepends /harness to plan.env.PYTHONPATH only for a Codex Y smoke.
    The read-only harness files are bound through plan and baseline; verify
    those bindings immediately before launch and again at qualification.
    """
    out = Path(out)
    plan, baseline = (read(out / name) for name in ('plan.json', 'baseline.json'))
    require(plan['engine'] == 'codex' and plan['task'] == 'SM' and plan['arm'] == 'Y',
            'helper observer is restricted to Codex Y smoke')
    helpers = [name for name in baseline['installed_files'] if name.endswith('/skills/_shared/task-complete.py')]
    require(bool(helpers), 'installed helper unavailable to smoke observer')
    hashes = {digest(out / 'cell/work' / name) for name in helpers}
    require(len(hashes) == 1, 'installed helper mirrors differ')
    harness = out / 'harness'
    source, config_path = harness / 'sitecustomize.py', harness / 'helper-observer.json'
    require(not source.exists() and not config_path.exists(), 'helper observer already installed')
    source.write_text(OBSERVER)
    config = dict(helper_sha256=hashes.pop(), records='/cell/helper-actions')
    config_path.write_text(json.dumps(config, sort_keys=True) + '\n')
    (out / 'cell/helper-actions').mkdir(mode=0o700)
    binding = dict(helper_sha256=config['helper_sha256'], files={
        str(path.relative_to(out)): digest(path) for path in (source, config_path)})
    for name, record in (('plan.json', plan), ('baseline.json', baseline)):
        record['helper_observer'] = binding
        (out / name).write_text(json.dumps(record, indent=2) + '\n')
    return binding


def verify_observer(out):
    out = Path(out)
    plan, baseline = (read(out / name) for name in ('plan.json', 'baseline.json'))
    binding = plan.get('helper_observer')
    require(isinstance(binding, dict) and binding == baseline.get('helper_observer'),
            'helper observer binding differs')
    require(plan['engine'] == 'codex' and plan['task'] == 'SM' and plan['arm'] == 'Y',
            'helper observer is restricted to Codex Y smoke')
    require(set(binding['files']) == {'harness/sitecustomize.py', 'harness/helper-observer.json'},
            'helper observer file binding differs')
    require((out / 'harness/sitecustomize.py').read_text() == OBSERVER,
            'helper observer implementation changed')
    require(all(not (out / name).is_symlink() and digest(out / name) == expected
                for name, expected in binding['files'].items()), 'helper observer files changed')
    require(read(out / 'harness/helper-observer.json') == dict(
        helper_sha256=binding['helper_sha256'], records='/cell/helper-actions'),
        'helper observer configuration changed')
    require('/harness' in plan['env']['PYTHONPATH'].split(':'), 'helper observer not enabled')
    return binding


def render_cleanup(result, actions):
    """Independent rendering of DESIGN's per-call action/status table."""
    require(isinstance(actions, dict) and type(actions.get('ran')) is bool, 'missing helper action record')
    status, workspace, scratch = (result[key] for key in ('delivery_status', 'workspace_cleanup', 'scratch_cleanup'))
    require(isinstance(scratch, dict) and scratch.get('status') in ('CLEAN', 'RETAINED', 'NOT_OWNED'),
            'invalid helper scratch status')
    require(workspace is None or isinstance(workspace, dict) and workspace.get('status') == 'RETAINED',
            'invalid helper workspace status')
    expected_status = 'CLEANUP_PENDING' if status == 'COMPLETE' and (
        workspace is not None or scratch['status'] == 'RETAINED') else status
    require(result['status'] == expected_status, 'helper completion status disagrees')
    clauses = []
    if status == 'COMPLETE':
        if actions['ran']:
            require(type(actions.get('linked')) is bool, 'missing helper linked-worktree observation')
            for key, verb, resource in (('worktree_removed', 'removed', 'task worktree'),
                                        ('local_ref_deleted', 'deleted', 'local task branch'),
                                        ('remote_branch_deleted', 'deleted', 'remote task branch')):
                require(key in actions and (actions[key] is None or type(actions[key]) is bool),
                        'invalid helper resource action')
                if key == 'worktree_removed' and not actions['linked']:
                    require(actions[key] is None, 'in-place checkout has a removal action')
                    if workspace is None:
                        clauses.append('the in-place checkout is not a cleanup target')
                elif actions[key] is True:
                    clauses.append(f'{verb} the {resource}')
                elif workspace is None:
                    require(actions[key] is False, 'missing helper absence observation')
                    clauses.append(f'the {resource} was absent')
        if workspace is not None:
            clauses.append(f"workspace cleanup deferred: {workspace['reason']}; resume with {workspace['resume']}")
        elif not actions['ran']:
            clauses.append('the receipt already records workspace cleanup complete')
    else:
        require(not actions['ran'], 'workspace action contradicts delivery status')
        phrases = {'PR': 'workspace cleanup deferred: the PR is not merged',
                   'PENDING': 'workspace cleanup deferred: the PR is not merged',
                   'LOCAL_ONLY': 'workspace cleanup skipped: local-only delivery',
                   'FAILED': 'workspace cleanup skipped; publication skipped by this call'}
        require(status in phrases, 'unregistered helper completion status')
        clauses.append(phrases[status])
    if scratch['status'] == 'CLEAN':
        clauses.append('emptied the task scratch')
    elif scratch['status'] == 'RETAINED':
        clauses.append(f"scratch cleanup incomplete: {scratch['reason']}; resume with {scratch['resume']}")
    sentence = '; '.join(clauses)
    return sentence[0].upper() + sentence[1:] + '.'


def check_call(result, actions, resources):
    require(result.get('cleanup') == render_cleanup(result, actions), 'helper cleanup sentence is not entailed by call actions')
    require(all(type(resources.get(key)) is bool for key in
                ('worktree_exists', 'worktree_registered', 'local_branch', 'remote_branch')) and
            isinstance(resources.get('scratch_files'), list), 'final cleanup resource record is incomplete')
    if actions['ran']:
        for action, fields in (('worktree_removed', ('worktree_exists', 'worktree_registered')),
                               ('local_ref_deleted', ('local_branch',)),
                               ('remote_branch_deleted', ('remote_branch',))):
            if action == 'worktree_removed' and not actions['linked']:
                continue
            # False licenses "was absent" only when workspace cleanup completed.
            claimed = actions[action] is True or (actions[action] is False and result['workspace_cleanup'] is None)
            require(not claimed or all(resources[field] is False for field in fields),
                    'helper cleanup claim contradicts final resource record')
    require(result['scratch_cleanup']['status'] != 'CLEAN' or resources['scratch_files'] == [],
            'helper scratch claim contradicts final resource record')
    return result['cleanup']


def safe_file(out, relative):
    path = Path(relative)
    require(not path.is_absolute() and '..' not in path.parts and bool(path.parts), 'unsafe helper evidence path')
    target = out / path
    require(not target.is_symlink() and target.is_file() and target.resolve().is_relative_to(out.resolve()),
            'unsafe helper evidence file')
    return target


def sealed_file(out, relative, files):
    path = safe_file(out, relative)
    require(files.get(str(relative)) == digest(path), 'helper evidence is missing or changed after sealing')
    return path


def read_jsonl(path):
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    require(all(isinstance(row, dict) for row in rows), 'invalid native transcript event')
    return rows


def tool_results(rows, engine):
    """Keep every native result, including outputs without a captured start."""
    started = {}
    for event in rows:
        if engine == 'claude':
            message = event.get('message') or {}
            for block in message.get('content', ()):
                if not isinstance(block, dict):
                    continue
                if event.get('type') == 'assistant' and block.get('type') == 'tool_use':
                    started[block['id']] = (block.get('name', ''), block.get('input') or {})
                elif event.get('type') == 'user' and block.get('type') == 'tool_result':
                    identifier = block['tool_use_id']
                    tool, input_ = started.get(identifier, ('', {}))
                    content = block.get('content')
                    yield dict(id=identifier, tool=tool, input=input_,
                               output=content if isinstance(content, str) else json.dumps(content))
        else:
            item = event.get('item') or event.get('payload') or {}
            if event.get('type') == 'item.started':
                started[item['id']] = (item.get('tool') or item.get('name') or item.get('type', ''),
                                       item.get('input') or item)
            elif event.get('type') == 'item.completed':
                tool, input_ = started.get(item['id'], (item.get('tool') or item.get('name') or
                                                       item.get('type', ''), item.get('input') or item))
                output = item.get('aggregated_output') or ''
                require(isinstance(output, str), 'invalid native tool output')
                yield dict(id=item['id'], tool=tool, input=input_, output=output)


def native_calls(out, *, sealed=False):
    """Native stdout JSON plus owner protocol-event payloads (the inherited carriers)."""
    out = Path(out)
    plan = read(out / 'plan.json')
    manifest = read(out / 'evidence.manifest.json') if sealed else None
    if sealed:
        require(not manifest.get('failures'), 'helper evidence seal failed')
    files = manifest['files'] if manifest else {}
    path_for = lambda relative: sealed_file(out, relative, files) if sealed else safe_file(out, relative)
    stream = read_jsonl(path_for('run/stdout'))
    require(bool(stream), 'native transcript is empty')
    calls = list(tool_results(stream, plan['engine']))
    if plan['engine'] == 'codex':
        roots = {event['thread_id'] for event in stream if event.get('type') == 'thread.started'}
        # stdout may omit large payloads; preserve its completed calls and add
        # the fuller owner payload by id, rejecting conflicting completions.
        by_id = {call['id']: call for call in calls}
        for folder in sorted((out / 'cell/trace').glob('trace-*')):
            metadata = read(path_for(str(folder.relative_to(out) / 'manifest.json')))
            if metadata.get('root_thread_id') not in roots:
                continue
            rows = []
            events = read_jsonl(path_for(str(folder.relative_to(out) / metadata.get('raw_event_log', 'trace.jsonl'))))
            for event in events:
                payload = event.get('payload') or {}
                if payload.get('type') != 'protocol_event_observed' or payload.get('event_type') not in ('item.started', 'item.completed'):
                    continue
                reference = (payload.get('event_payload') or {}).get('path')
                require(isinstance(reference, str), 'helper protocol payload reference missing')
                observed = read(path_for(str(folder.relative_to(out) / reference)))
                if observed.get('thread_id') in (None, *roots):
                    rows.append(observed)
            for call in tool_results(rows, 'codex'):
                old = by_id.get(call['id'])
                require(old is None or not old['output'] or not call['output'] or old['output'] == call['output'],
                        'native helper output carriers disagree')
                if old is None or call['output']:
                    by_id[call['id']] = call
        calls = list(by_id.values())
    return calls


def json_objects(text):
    decoder, position = json.JSONDecoder(), 0
    while position < len(text):
        start = text.find('{', position)
        if start < 0:
            return
        try:
            value, end = decoder.raw_decode(text, start)
        except ValueError:
            position = start + 1
            continue
        position = end
        if isinstance(value, dict):
            yield value
            for nested in value.values():
                if isinstance(nested, str):
                    yield from json_objects(nested)
                elif isinstance(nested, (dict, list)):
                    yield from json_objects(json.dumps(nested))


def continuation_input(call):
    """Literal native continuation identities; never infer them from output prose."""
    tool = call['tool'].rsplit('.', 1)[-1]
    value = call['input']
    field = {'write_stdin': 'session_id', 'wait': 'cell_id'}.get(tool)
    if field and isinstance(value, dict):
        identifier = value.get(field)
        return {(field, str(identifier))} if type(identifier) in (str, int) and str(identifier) else set()
    if tool not in ('exec',) or not isinstance(value, str):
        return set()
    identities = set()
    # A code-mode wrapper may itself poll a shell process. Match only literal
    # IDs in that named call's object argument, not arbitrary numbers in code.
    for argument in re.findall(r'\bwrite_stdin\s*\(\s*\{([^{}]*)\}', value):
        match = re.search(r'(?:^|,)\s*[\'\"]?session_id[\'\"]?\s*:\s*(\d+|"[^"\\]*"|\'[^\'\\]*\')\s*(?:,|$)', argument)
        if match:
            identities.add(('session_id', match[1].strip('\'"')))
    return identities


def continuation_output(text):
    identities = set()
    for value in json_objects(text):
        if 'receipt' in value or value.get('type') == 'result':
            continue
        for field in ('session_id', 'cell_id'):
            identifier = value.get(field)
            if type(identifier) in (str, int) and str(identifier):
                identities.add((field, str(identifier)))
    for pattern, field in ((r'\bScript running with cell ID ([A-Za-z0-9_-]+)', 'cell_id'),
                           (r'\bProcess running with session ID ([A-Za-z0-9_-]+)', 'session_id')):
        identities.update((field, match) for match in re.findall(pattern, text))
    return identities


def output_text(text):
    """Unwrap transport envelopes while retaining partial stdout for later polls."""
    if re.fullmatch(r'(?:Script running with cell ID|Process running with session ID) [A-Za-z0-9_-]+\s*', text):
        return ''
    try:
        value = json.loads(text)
    except ValueError:
        return text
    if isinstance(value, dict):
        for field in ('stdout', 'output', 'aggregated_output', 'content', 'text'):
            if field in value:
                content = value[field]
                return output_text(content if isinstance(content, str) else json.dumps(content))
        if set(value) & {'session_id', 'cell_id'}:
            return ''
    elif isinstance(value, list):
        return ''.join(output_text(json.dumps(item)) for item in value)
    return text


def receipt_matches(out, receipt, expected):
    for prefix, root in (('/cell', 'cell'), ('/tmp', 'tmp'), ('/home/participant', 'home')):
        if isinstance(receipt, str) and receipt.startswith(prefix + '/'):
            return (Path(out) / root / receipt[len(prefix) + 1:]).resolve() == expected.resolve()
    return False


def bind_receipt(out, receipt, expected):
    require(receipt_matches(out, receipt, expected), 'helper call belongs to a different receipt')


def complete_outputs(out, *, sealed=False):
    pending, streams = {}, []
    for call in native_calls(out, sealed=sealed):
        incoming = continuation_input(call)
        owners = {pending[identity] for identity in incoming if identity in pending}
        # Continuation identities only reassemble split stdout. Every native
        # output is scanned, even when its launch or polling code is unknown.
        if len(owners) == 1:
            owner = owners.pop()
        else:
            owner = len(streams)
            streams.append([])
        for identity in incoming:
            pending.pop(identity, None)
        streams[owner].append(output_text(call['output']))
        for identity in continuation_output(call['output']):
            pending[identity] = owner
    results = []
    receipt_file = None
    for stream in streams:
        for value in json_objects(''.join(stream)):
            if (not isinstance(value.get('receipt'), str) or not value['receipt'].startswith('/') or
                    value.get('delivery_status') not in ('COMPLETE', 'PR', 'PENDING', 'LOCAL_ONLY', 'FAILED') or
                    value.get('status') not in (value['delivery_status'], 'CLEANUP_PENDING') or
                    (value['status'] == 'CLEANUP_PENDING' and value['delivery_status'] != 'COMPLETE')):
                continue
            if receipt_file is None:
                receipt = read(Path(out) / 'report-checklist.json')['evidence']['cleanup']['receipt']
                require(isinstance(receipt, str), 'helper lacks an accepted receipt')
                receipt_file = safe_file(Path(out), receipt)
            if receipt_matches(out, value.get('receipt'), receipt_file):
                results.append(value)
    return results


def merge_refused(out):
    """Retain any refusal, including a refused call followed by successful delivery."""
    return any(result.get('merge_refused') is not None for result in complete_outputs(out))


def qualify(out):
    """Return a compact qualification receipt; all evidence must already be sealed."""
    out = Path(out)
    binding = verify_observer(out)
    checklist = read(out / 'report-checklist.json')
    resources = checklist['resources']
    receipt_relative = checklist['evidence']['cleanup']['receipt']
    require(isinstance(receipt_relative, str), 'smoke lacks an accepted helper receipt')
    receipt_file = safe_file(out, receipt_relative)
    manifest = read(out / 'evidence.manifest.json')
    require(not manifest.get('failures'), 'helper evidence seal failed')
    files = manifest['files']
    names = sorted(name for name in files if Path(name).parent == Path('cell/helper-actions'))
    actual = sorted(str(path.relative_to(out)) for path in (out / 'cell/helper-actions').iterdir())
    require(bool(names) and names == actual, 'helper action evidence missing or outside seal')
    observed = []
    for name in names:
        record = read(sealed_file(out, name, files))
        require(record.get('schema') == 'rp-d4-helper-call-v1' and record.get('helper_sha256') == binding['helper_sha256'],
                'helper action evidence binding differs')
        result = record['result']
        bind_receipt(out, result['receipt'], receipt_file)
        check_call(result, record['actions'], resources)
        observed.append(result)
    outputs = complete_outputs(out, sealed=True)
    key = lambda value: json.dumps(value, sort_keys=True, separators=(',', ':'))
    require(Counter(map(key, observed)) == Counter(map(key, outputs)), 'helper stdout and observed call records differ')
    require(not any('merge_refused' in result for result in outputs), 'smoke helper refused a merge')
    return dict(status='PASS', calls=len(observed), helper_sha256=binding['helper_sha256'],
                evidence_manifest_sha256=digest(out / 'evidence.manifest.json'),
                checklist_sha256=digest(out / 'report-checklist.json'),
                action_records={name: files[name] for name in names})
