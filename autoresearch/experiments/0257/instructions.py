"""Seal and assert the instruction bytes actually loaded by the pinned owner CLIs.

Observed 0256 shape assumptions (Claude Code 2.1.281 / Codex 0.156.1): Claude's
owner UUID is run/stdout's first system.session_id; its project transcript is
home/.claude/projects/*/<UUID>.jsonl and contains one attachment whose
attachment.type is 'instructions', with files [{path,content}] after Claude's
comment stripping and trimming. Codex's owner thread ID is run/stdout's
thread.started.thread_id; cell/trace/**/trace.jsonl holds an inference_started
for that thread, whose request_payload.path is relative to the trace directory;
its first input user message contains '# AGENTS.md instructions for /cell/work',
'<INSTRUCTIONS>\\n', the content, then '\\n</INSTRUCTIONS>'. These shapes
were read from d02-D3-claude-B-r1 and d03-D3-codex-B-r1 0256 evidence. A
missing or ambiguous shape is an assertion violation, never an empty match.
SMOKE B seals its own observed form after its run; before forms are sealed,
SMOKE B can check only installed bytes. seal-forms rechecks all four preserved
SMOKE sessions before qualification proceeds to measured cells.
"""
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
SKIP = 'shipped instruction template in devlyn-cli source checkout'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_record(path):
    if not path.is_file():
        raise ValueError(f'missing sealed instruction file: {path}')
    data = path.read_bytes()
    return dict(sha256=digest(data), bytes=base64.b64encode(data).decode('ascii'))


def root(runtime):
    return Path(runtime['output']).parent


def seal(runtime_path):
    """Run B's real offline installer in fresh empty Git trees inside the registered image."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('prepare0257', HERE / 'prepare.py')
    prepare = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prepare)
    runtime = json.loads(Path(runtime_path).read_text())
    sealed = {'files': {}, 'forms': {}}
    for config in ('claude', 'codex'):
        with tempfile.TemporaryDirectory(prefix='instructions-seal-', dir=runtime['scratch']) as temp:
            temp = Path(temp)
            work, home = temp / 'work', temp / 'home'
            work.mkdir()
            home.mkdir()
            prepare.git(work, 'init', '-q', '-b', 'main')
            prepare.git(work, 'config', 'user.name', 'Seal')
            prepare.git(work, 'config', 'user.email', 'seal@localhost')
            prepare.git(work, 'commit', '--allow-empty', '-qm', 'empty source')
            prepare.install(runtime, work, home, config, 'B')
            names = ('CLAUDE.md', 'AGENTS.md') if config == 'claude' else ('AGENTS.md',)
            sealed['files'][config] = {name: file_record(work / name) for name in names}
    path = root(runtime) / 'instructions.seal.json'
    if path.exists():
        raise ValueError(f'instruction seal already exists: {path}')
    path.write_text(json.dumps(sealed, indent=2) + '\n')
    return path


def owner_id(out, config):
    target = 'system' if config == 'claude' else 'thread.started'
    key = 'session_id' if config == 'claude' else 'thread_id'
    for line in (out / 'run/stdout').read_text().splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get('type') == target and isinstance(event.get(key), str):
            return event[key]
    raise ValueError(f'{config}: owner {key} missing from run/stdout')


def claude_form(out):
    session = owner_id(out, 'claude')
    files = list((out / 'home/.claude/projects').rglob(session + '.jsonl'))
    if len(files) != 1:
        raise ValueError('Claude owner transcript missing or ambiguous')
    attachments = []
    for line in files[0].read_text().splitlines():
        event = json.loads(line)
        attachment = event.get('attachment') or {}
        if event.get('type') == 'attachment' and attachment.get('type') == 'instructions':
            attachments.append(attachment['files'])
    if len(attachments) > 1:
        raise ValueError('multiple Claude instruction attachments')
    if not attachments:
        return {}
    return {Path(item['path']).name: item['content'] for item in attachments[0]
            if item['path'] in ('/cell/work/CLAUDE.md', '/cell/work/AGENTS.md')}


def codex_form(out):
    thread = owner_id(out, 'codex')
    traces = list((out / 'cell/trace').rglob('trace.jsonl'))
    requests = []
    for trace in traces:
        for line in trace.read_text().splitlines():
            event = json.loads(line)
            payload = event.get('payload') or {}
            if event.get('thread_id') != thread or payload.get('type') != 'inference_started':
                continue
            path = trace.parent / payload['request_payload']['path']
            requests.append((event['seq'], json.loads(path.read_text())))
    if not requests:
        raise ValueError('Codex owner inference request missing')
    request = min(requests, key=lambda pair: pair[0])[1]
    user = next((message for message in request['input'] if message.get('role') == 'user'), None)
    if user is None:
        raise ValueError('Codex first owner request lacks user message')
    text = '\n'.join(part['text'] for part in user['content'] if part.get('type') == 'input_text')
    marker = '# AGENTS.md instructions for /cell/work\n\n<INSTRUCTIONS>\n'
    if marker not in text:
        return None
    if text.count(marker) != 1 or text.count('\n</INSTRUCTIONS>') != 1:
        raise ValueError('Codex AGENTS instruction wrapper ambiguous')
    return text.split(marker, 1)[1].split('\n</INSTRUCTIONS>', 1)[0]


def seal_forms(runtime_path):
    runtime = json.loads(Path(runtime_path).read_text())
    path = root(runtime) / 'instructions.seal.json'
    sealed = json.loads(path.read_text())
    if sealed.get('forms'):
        raise ValueError('owner instruction forms already sealed')
    output = Path(runtime['output'])
    sealed['forms'] = {'claude': claude_form(output / 'smoke-claude-B'),
                       'codex': codex_form(output / 'smoke-codex-B')}
    if set(sealed['forms']['claude']) != {'CLAUDE.md', 'AGENTS.md'} or not sealed['forms']['codex']:
        raise ValueError('SMOKE B did not load expected instructions')
    for config in ('claude', 'codex'):
        for arm in ('A', 'B'):
            name = f'smoke-{config}-{arm}'
            out = output / name
            try:
                violations = check(out, json.loads((out / 'plan.json').read_text()),
                                   json.loads((out / 'instructions.pre.json').read_text()), sealed)
            except (OSError, ValueError, KeyError, TypeError) as exc:
                raise ValueError(f'{name}: SMOKE qualification evidence unreadable: {exc}') from exc
            if violations:
                raise ValueError(f'{name}: ' + '; '.join(violations))
    sealed['qualification'] = {'status': 'PASS', 'cells': [f'smoke-{config}-{arm}'
                               for config in ('claude', 'codex') for arm in ('A', 'B')]}
    path.write_text(json.dumps(sealed, indent=2) + '\n')
    return path


def check(cell, plan, evidence, seal):
    """Return every instruction-load violation; caller turns a non-empty list into STOP."""
    out = Path(cell)
    task, config, arm = plan['task'], plan['config'], plan['arm']
    source, installed = evidence['source'], evidence['installed']
    violations = []
    def bad(message):
        violations.append(message)
    if task == 'I0185' and source != installed:
        bad('I0185 source instruction hashes changed')
    if arm == 'B' and task == 'I0185':
        if SKIP not in evidence['install_output']:
            bad('I0185 installer skip line missing')
        if not evidence['skills']:
            bad('I0185 installed skills missing')
    elif arm == 'B':
        files = seal.get('files', {}).get(config, {})
        for name, expected in files.items():
            if installed.get(name) != expected['sha256']:
                bad(f'{name} installed bytes differ from seal')
        if not files:
            bad(f'{config} instruction file seal missing')
    else:
        if source.get('AGENTS.md') != installed.get('AGENTS.md'):
            bad('A has installer-written AGENTS.md')
        if task != 'I0185' and installed.get('AGENTS.md') == seal.get('files', {}).get('codex', {}).get('AGENTS.md', {}).get('sha256'):
            bad('A has sealed AGENTS.md')
    try:
        if config == 'claude':
            form = claude_form(out)
            if arm == 'B' and task != 'I0185':
                expected = seal.get('forms', {}).get('claude')
                if expected is None and plan['name'] != 'smoke-claude-B':
                    bad('Claude form seal missing')
                elif expected is not None and form != expected:
                    bad('Claude instruction attachment differs from seal')
            elif any(value in seal.get('forms', {}).get('claude', {}).values() for value in form.values()):
                bad('A or I0185 received sealed Claude attachment')
        else:
            form = codex_form(out)
            if arm == 'B' and task != 'I0185':
                expected = seal.get('forms', {}).get('codex')
                if expected is None and plan['name'] != 'smoke-codex-B':
                    bad('Codex form seal missing')
                elif expected is not None and form != expected:
                    bad('Codex first owner request differs from seal')
            elif form == seal.get('forms', {}).get('codex') and form is not None:
                bad('A or I0185 received sealed Codex instruction')
    except (OSError, KeyError, TypeError, ValueError) as exc:
        bad(f'{config} owner instruction evidence unreadable: {exc}')
    return violations


if __name__ == '__main__':
    command, runtime = sys.argv[1:3]
    if command == 'seal':
        print(seal(runtime))
    elif command == 'seal-forms':
        print(seal_forms(runtime))
    else:
        raise SystemExit(__doc__)
