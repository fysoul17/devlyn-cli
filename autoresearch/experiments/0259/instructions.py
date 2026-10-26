"""Seal offline B/C installs and the Claude instruction forms observed in SMOKE."""
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import tempfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('control0259', HERE / 'control.py')
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)
SKILLS = ('.agents/skills/_shared/runtime-principles.md',
          '.claude/skills/_shared/runtime-principles.md')
WITNESS = HERE / 'results/witnesses/d3-parseoptions-override.js'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_record(path):
    if not path.is_file():
        raise ValueError(f'missing sealed instruction file: {path}')
    data = path.read_bytes()
    return dict(sha256=digest(data), bytes=base64.b64encode(data).decode('ascii'))


def root(runtime):
    return Path(runtime['output']).parent


def prior_seal(runtime):
    prior_runtime = json.loads(Path(runtime['prior_runtime']).read_text())
    return json.loads((root(prior_runtime) / 'instructions.seal.json').read_text())


def seal(runtime_path, install_fn=None):
    """Run each arm's installer on an empty offline Git tree in the registered image."""
    spec = importlib.util.spec_from_file_location('prepare0259', HERE / 'prepare.py')
    prepare = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prepare)
    install_fn = install_fn or prepare.install
    runtime = json.loads(Path(runtime_path).read_text())
    path = root(runtime) / 'instructions.seal.json'
    if path.exists():
        raise ValueError(f'instruction seal already exists: {path}')
    old = prior_seal(runtime)['files']['claude']
    sealed = {'files': {}, 'forms': {}, 'witness_sha256': digest(WITNESS.read_bytes())}
    for arm in ('B', 'C'):
        with tempfile.TemporaryDirectory(prefix='instructions-seal-', dir=runtime['scratch']) as temp:
            work, home = Path(temp) / 'work', Path(temp) / 'home'
            work.mkdir()
            home.mkdir()
            prepare.git(work, 'init', '-q', '-b', 'main')
            prepare.git(work, 'config', 'user.name', 'Seal')
            prepare.git(work, 'config', 'user.email', 'seal@localhost')
            prepare.git(work, 'commit', '--allow-empty', '-qm', 'empty source')
            install_fn(runtime, work, home, 'claude', arm)
            sealed['files'][arm] = {name: file_record(work / name)
                                    for name in ('CLAUDE.md', 'AGENTS.md', *SKILLS)}
    for name in ('CLAUDE.md', 'AGENTS.md'):
        if sealed['files']['B'][name] != old[name]:
            raise ValueError(f'B {name} differs from 0257 installer seal')
    path.write_text(json.dumps(sealed, indent=2) + '\n')
    return path


def owner_id(out):
    for line in (out / 'run/stdout').read_text().splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get('type') == 'system' and isinstance(event.get('session_id'), str):
            return event['session_id']
    raise ValueError('Claude owner session_id missing from run/stdout')


def claude_form(out):
    files = list((out / 'home/.claude/projects').rglob(owner_id(out) + '.jsonl'))
    if len(files) != 1:
        raise ValueError('Claude owner transcript missing or ambiguous')
    attachments = []
    for line in files[0].read_text().splitlines():
        event = json.loads(line)
        attachment = event.get('attachment') or {}
        if event.get('type') == 'attachment' and attachment.get('type') == 'instructions':
            attachments.append(attachment['files'])
    if len(attachments) != 1:
        raise ValueError('expected one Claude instruction attachment')
    paths = [item['path'] for item in attachments[0]]
    if len(paths) != len(set(paths)):
        raise ValueError('duplicate Claude instruction attachment path')
    result = {Path(item['path']).name: item['content'] for item in attachments[0]
              if item['path'] in ('/cell/work/CLAUDE.md', '/cell/work/AGENTS.md')}
    if set(result) != {'CLAUDE.md', 'AGENTS.md'}:
        raise ValueError('Claude instruction attachment lacks CLAUDE.md or AGENTS.md')
    return result


def matches_edit(before, after, name):
    return control.apply_edit(before, name) == after


def normalized_agents(data):
    text = data.decode('utf8')
    if len(re.findall(r'sha256=[0-9a-f]{64}', text)) != 1:
        raise ValueError('expected one managed-block digest')
    return re.sub(r'sha256=[0-9a-f]{64}', 'sha256=<digest>', text)


def qualify_pair(output, runtime, sealed, forms):
    b, c = forms['B'], forms['C']
    if b != prior_seal(runtime)['forms']['claude']:
        raise ValueError('B Claude form differs from 0257 form seal')
    if b['CLAUDE.md'] != c['CLAUDE.md'] or not matches_edit(b['AGENTS.md'], c['AGENTS.md'], 'Claude form AGENTS.md'):
        raise ValueError('Claude forms differ beyond the ordered edit')
    files = sealed['files']
    b_agents = base64.b64decode(files['B']['AGENTS.md']['bytes'])
    c_agents = base64.b64decode(files['C']['AGENTS.md']['bytes'])
    if not matches_edit(normalized_agents(b_agents), normalized_agents(c_agents), 'installed AGENTS.md'):
        raise ValueError('installed AGENTS.md differs beyond ordered edit and digest')
    for name in SKILLS:
        old = base64.b64decode(files['B'][name]['bytes']).decode('utf8')
        new = base64.b64decode(files['C'][name]['bytes']).decode('utf8')
        if not matches_edit(old, new, name):
            raise ValueError(f'{name} differs beyond the ordered edit')
    for arm in ('B', 'C'):
        for name in SKILLS:
            if file_record(output / f'smoke-claude-{arm}' / 'cell/work' / name) != files[arm][name]:
                raise ValueError(f'smoke-claude-{arm}: {name} differs from installer seal')


def seal_forms(runtime_path):
    runtime = json.loads(Path(runtime_path).read_text())
    path = root(runtime) / 'instructions.seal.json'
    sealed = json.loads(path.read_text())
    if sealed.get('forms'):
        raise ValueError('owner instruction forms already sealed')
    output = Path(runtime['output'])
    forms = {arm: claude_form(output / f'smoke-claude-{arm}') for arm in ('B', 'C')}
    qualify_pair(output, runtime, sealed, forms)
    sealed['forms'] = forms
    for arm in ('B', 'C'):
        name = f'smoke-claude-{arm}'
        out = output / name
        violations = check(out, json.loads((out / 'plan.json').read_text()),
                           json.loads((out / 'instructions.pre.json').read_text()), sealed)
        if violations:
            raise ValueError(f'{name}: ' + '; '.join(violations))
    sealed['qualification'] = {'status': 'PASS', 'cells': ['smoke-claude-B', 'smoke-claude-C']}
    path.write_text(json.dumps(sealed, indent=2) + '\n')
    return path


def check(cell, plan, evidence, seal):
    """Return instruction violations for this arm, including a wrong-arm match."""
    arm = plan['arm']
    if plan['config'] != 'claude' or arm not in ('B', 'C'):
        return ['unsupported instruction arm or config']
    other = 'C' if arm == 'B' else 'B'
    violations = []
    installed = evidence['installed']
    files = seal.get('files', {}).get(arm, {})
    other_files = seal.get('files', {}).get(other, {})
    for name in ('CLAUDE.md', 'AGENTS.md'):
        expected = files.get(name, {}).get('sha256')
        if not expected or installed.get(name) != expected:
            violations.append(f'{name} installed bytes differ from {arm} seal')
        if installed.get(name) == other_files.get(name, {}).get('sha256') and expected != other_files.get(name, {}).get('sha256'):
            violations.append(f'{name} matches wrong arm')
    if not evidence.get('skills'):
        violations.append('installed skills missing')
    for name in SKILLS:
        expected = files.get(name, {}).get('sha256')
        observed = evidence.get('skill_hashes', {}).get(name)
        if not expected or observed != expected:
            violations.append(f'{name} installed bytes differ from {arm} seal')
        if observed == other_files.get(name, {}).get('sha256') and expected != other_files.get(name, {}).get('sha256'):
            violations.append(f'{name} matches wrong arm')
    try:
        form = claude_form(Path(cell))
        expected = seal.get('forms', {}).get(arm)
        other_form = seal.get('forms', {}).get(other)
        if expected is None and plan['task'] != 'SMOKE':
            violations.append('Claude form seal missing')
        elif expected is not None and form != expected:
            violations.append('Claude instruction attachment differs from arm seal')
        if other_form is not None and form == other_form and expected != other_form:
            violations.append('Claude instruction attachment matches wrong arm')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        violations.append(f'Claude owner instruction evidence unreadable: {exc}')
    return violations


if __name__ == '__main__':
    command, runtime_path = sys.argv[1:3]
    if command == 'seal':
        print(seal(runtime_path))
    elif command == 'seal-forms':
        print(seal_forms(runtime_path))
    else:
        raise SystemExit(__doc__)
