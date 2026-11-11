"""Seal B's devlyn-cli 4.3.30 launch and assert each cell against it: instructions.py seal|seal-forms <runtime.json>.

seal (before SMOKE, no model): the package identity (the tarball's sha256 and npm integrity from the control
manifest, the unpacked tree against the tarball, package.json's version, the digest its release.json declares), the
pinned CLI versions, and the session text `devlyn run` plans for a cell HOME (the release's runtime principles and
skill catalog: Codex's developer_instructions, Claude's appended system prompt). Writes
<output>.parent/instructions.seal.json with qualification PENDING.

seal-forms (after SMOKE): from smoke-<engine>-B, its status line, its HOME release digest, Claude's devlyn plugin entry
in the init event, Codex's projection folder and where Codex's first owner request carries the session text. Then
check() on all four SMOKE cells; PASS only when each has a finished verdict and passes.

check(cell, plan, seal): DESIGN "Per-cell assertions" for the cell's arm; [] passes, otherwise '<assertion>: <detail>'.

Shapes read: run/stderr lines (`devlyn run` writes its status line, or `devlyn run: <code> <params>` when it refuses,
bin/harness-run.js); Claude's system/init events in run/stdout (plugins [{name, path, source}], built-ins with path
'builtin' as in every 0257 cell; mcp_servers); Codex's owner thread (run/stdout thread.started) and its first
inference_started request payload under cell/trace (0257 codex_form; 0232 trace schema 1). A missing or ambiguous
shape is a violation, never an empty match; seal-forms says what it looked for and what it found.
"""
import hashlib
import json
from pathlib import Path
import re
import sys
import tomllib

ENGINES = ('claude', 'codex')
ARMS = ('A', 'B')
VERSION = '4.3.30'
TARBALL_SHA256 = '139ec4cb86a1d82ea5617e35de564b509f9247ba89c0fc43f7946730127b2970'
INTEGRITY = 'sha512-1qehRZd7iA5mwf15rXzjfmAEX6MHjMwD1c52wN6eJgmg489WKnq57LQMCZRH/7LgixPeePIV/oy2fDq/sT6ISg=='
RELEASE_DIGEST = '53a2f9f2d3d8cf8cf43391dd92224aa5190e331f0a993649d0a06256ca6a417d'
CLI = {'claude': '2.1.322', 'codex': '0.164.0'}
CHANNELS = {'claude': ('append-system-prompt-file', 'plugin-dir'),
            'codex': ('developer_instructions', 'session-plugin')}
HOME = '/home/participant'
RELEASE_ROOT = f'{HOME}/.devlyn/cli/releases/devlyn-cli/{VERSION}'
PROJECTION = f'plugins/cache/devlyn-harness-v{VERSION.replace(".", "-")}/devlyn/{VERSION}'  # under CODEX_HOME
PREAMBLE = 'The following Devlyn instructions are defaults for this session.'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def root(runtime):
    return Path(runtime['output']).parent


def lines(path):
    """JSON objects of a JSON-lines file; other lines are skipped."""
    found = []
    for line in path.read_text(errors='replace').splitlines():
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict):
            found.append(value)
    return found


def canonical(value):
    """bin/release.js canonical(): sorted keys, no whitespace, JSON.stringify scalars."""
    if isinstance(value, list):
        return '[' + ','.join(canonical(item) for item in value) + ']'
    if isinstance(value, dict):
        return '{' + ','.join(json.dumps(key, ensure_ascii=False) + ':' + canonical(value[key])
                              for key in sorted(value)) + '}'
    return json.dumps(value, ensure_ascii=False)


def release_record(path):
    """A release.json's version and digest, the digest recomputed as release.js manifestDigest does."""
    manifest = json.loads(path.read_text())
    declared = manifest.get('digest') or {}
    body = {key: value for key, value in manifest.items() if key != 'digest'}
    if declared.get('algorithm') != 'sha256' or digest(canonical(body).encode()) != declared.get('value'):
        raise ValueError(f'{path.name}: its digest does not match its contents')
    return dict(version=manifest.get('version'), digest=declared['value'])


def package_identity(runtime):
    control = Path(runtime['control'])
    b = json.loads(Path(str(control) + '.manifest.json').read_text())['packages']['B']
    if b['sha256'] != TARBALL_SHA256 or b['integrity'] != INTEGRITY:
        raise ValueError('B registry tarball identity mismatch')
    package = control / 'packages/B/package'
    expected = {name.removeprefix('package/'): value for name, value in b['files'].items()}
    if {str(p.relative_to(package)): digest(p.read_bytes()) for p in package.rglob('*') if p.is_file()} != expected:
        raise ValueError('B unpacked package differs from its tarball')
    version = json.loads((package / 'package.json').read_text())['version']
    release = release_record(package / 'release.json')
    if version != VERSION or release != dict(version=VERSION, digest=RELEASE_DIGEST):
        raise ValueError(f'B package is {version}, release {release}; expected {VERSION}@{RELEASE_DIGEST}')
    return dict(tarball_sha256=b['sha256'], integrity=b['integrity'], version=version, release_digest=release['digest'])


def session_text(package):
    """harness-activation.js joinText(defaults, skillCatalog(release)) for the release a cell HOME materializes;
    rebuilt equal, byte for byte, to the 2026-11-11 probe's appended file and developer_instructions."""
    skills = RELEASE_ROOT + '/config/skills'
    catalog = '\n'.join(['Devlyn session skill catalog (read the absolute file to invoke):',
                         *(f'{name}: {skills}/{name}/SKILL.md' for name in ('devlyn-ideate', 'devlyn-engines')),
                         f"This session's _shared folder is {skills}/_shared.",
                         'Use that absolute folder wherever the Devlyn defaults name _shared/.'])
    principles = (Path(package) / 'config/skills/_shared/runtime-principles.md').read_text(encoding='utf-8')
    return principles + '\n\n' + catalog


def seal(runtime_path):
    runtime = json.loads(Path(runtime_path).read_text())
    path = root(runtime) / 'instructions.seal.json'
    if path.exists():
        raise ValueError(f'instruction seal already exists: {path}')
    sealed = dict(package=package_identity(runtime), cli=CLI,
                  session_text=session_text(Path(runtime['control']) / 'packages/B/package'),
                  forms={}, qualification=dict(status='PENDING'))
    path.write_text(json.dumps(sealed, indent=2) + '\n')
    return path


def devlyn_lines(out):
    return [line for line in (out / 'run/stderr').read_text(errors='replace').splitlines()
            if line.startswith(('devlyn: ', 'devlyn run: '))]


def status_pattern(engine, version):
    principles, skills = CHANNELS[engine]
    return re.compile(rf'devlyn: {engine} {re.escape(version)} \| release {re.escape(VERSION)}@([0-9a-f]{{8}}) '
                      rf'\(package\) \| principles=configured:{re.escape(principles)} '
                      rf'\| skills=configured:{re.escape(skills)}')


def home_release(out):
    found = sorted((out / 'home/.devlyn/cli/releases').rglob('release.json'))
    if len(found) != 1:
        raise ValueError(f'expected one ~/.devlyn/cli/releases/**/release.json, found {len(found)}')
    record = release_record(found[0])
    if record['version'] != VERSION:
        raise ValueError(f'HOME release is {record["version"]}')
    return record['digest']


def inits(out):
    found = [e for e in lines(out / 'run/stdout') if e.get('type') == 'system' and e.get('subtype') == 'init']
    if not found:
        raise ValueError('no system/init event in run/stdout')
    for event in found:
        if not isinstance(event.get('plugins'), list) or not all(isinstance(p, dict) for p in event['plugins']):
            raise ValueError('init event without a plugins list')
    return found


def own_plugins(event):
    return [plugin for plugin in event['plugins'] if plugin.get('path') != 'builtin']


def projection(out):
    folder = out / 'home/.codex' / PROJECTION
    if not folder.is_dir():
        raise ValueError(f'CODEX_HOME has no {PROJECTION}')
    return {str(p.relative_to(folder)): digest(p.read_bytes()) for p in sorted(folder.rglob('*')) if p.is_file()}


def plugin_paths(out):
    """Plugins and marketplaces in a cell's CODEX_HOME: config.toml tables and any file under a folder named for one."""
    home = out / 'home/.codex'
    config = tomllib.loads((home / 'config.toml').read_text())
    found = [f'config.toml [{key}]' for key in ('plugins', 'marketplaces') if key in config]
    return found + [str(p.relative_to(home)) for p in sorted(home.rglob('*')) if p.is_file() and any(
        re.search('plugin|marketplace', part, re.I) for part in p.relative_to(home).parts[:-1])]


def owner_thread(out):
    for event in lines(out / 'run/stdout'):
        if event.get('type') == 'thread.started' and isinstance(event.get('thread_id'), str):
            return event['thread_id']
    raise ValueError('owner thread_id missing from run/stdout')


def first_owner_request(out):
    thread = owner_thread(out)
    starts = []
    for trace in sorted((out / 'cell/trace').rglob('trace.jsonl')):
        for event in lines(trace):
            payload = event.get('payload') or {}
            if event.get('thread_id') == thread and payload.get('type') == 'inference_started':
                starts.append((event['seq'], trace.parent / payload['request_payload']['path']))
    if not starts:
        raise ValueError('Codex owner inference request missing')
    return json.loads(min(starts)[1].read_text())


def strings(value, path=()):
    """Every string in a request payload with its path."""
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from strings(item, path + (key,))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from strings(item, path + (index,))


def location(request, path, value, text):
    """Where a string sits, independent of list positions: its path, the message role and the content part type."""
    message = request['input'][path[1]] if path[:1] == ('input',) and len(path) > 1 else {}
    part = (message['content'][path[3]] if len(path) > 3 and path[2] == 'content' and isinstance(path[3], int)
            else {})
    return dict(path='/'.join('*' if isinstance(step, int) else step for step in path),
                role=message.get('role'), type=part.get('type'), whole=value == text)


def text_hits(request, text):
    hits = [(path, value) for path, value in strings(request) if text in value]
    return hits, sum(value.count(text) for _, value in hits)


def session_location(out, text):
    request = first_owner_request(out)
    hits, count = text_hits(request, text)
    if count == 1:
        return location(request, *hits[0], text)
    near = []
    for path, value in strings(request):
        start = value.find(PREAMBLE)
        if start >= 0:
            tail = value[start:]
            first = next((i for i, (a, b) in enumerate(zip(tail, text)) if a != b), min(len(tail), len(text)))
            near.append(dict(location(request, path, value, text), length=len(value), starts_at=start,
                             first_difference=first))
    raise ValueError(f'{out.name}: looked for the planned session text ({len(text)} chars) once in the first owner '
                     f'request; found it {count} time(s); strings holding its first sentence: {near}')


def observed_form(out, engine, sealed):
    """One engine's form, read from its SMOKE B cell."""
    found = [line for line in devlyn_lines(out) if line.startswith('devlyn: ')]
    pattern = status_pattern(engine, sealed['cli'][engine])
    match = pattern.fullmatch(found[0]) if len(found) == 1 else None
    if not match:
        raise ValueError(f'{out.name}: looked for one stderr line matching {pattern.pattern}; found {found!r}')
    release = home_release(out)
    if release != sealed['package']['release_digest'] or match.group(1) != release[:8]:
        raise ValueError(f'{out.name}: HOME release digest {release} and status line digest {match.group(1)}; '
                         f'package release {sealed["package"]["release_digest"]}')
    form = dict(status_line=found[0])
    if engine == 'claude':
        plugins = inits(out)[0]['plugins']
        under = [p for p in plugins if str(p.get('path', '')).startswith(HOME + '/.devlyn/')]
        if len(under) != 1 or under[0].get('name') != 'devlyn':
            raise ValueError(f'{out.name}: looked for one init plugin named devlyn under {HOME}/.devlyn/; '
                             f'the init plugins are {plugins!r}')
        form['plugin'] = under[0]
    else:
        form['projection'] = dict(path=PROJECTION, files=projection(out))
        form['location'] = session_location(out, sealed['session_text'])
    return form


def seal_forms(runtime_path):
    runtime = json.loads(Path(runtime_path).read_text())
    path = root(runtime) / 'instructions.seal.json'
    sealed = json.loads(path.read_text())
    if sealed.get('forms') or sealed.get('qualification', {}).get('status') != 'PENDING':
        raise ValueError('owner forms already sealed')
    output = Path(runtime['output'])
    sealed['forms'] = {engine: observed_form(output / f'smoke-{engine}-B', engine, sealed) for engine in ENGINES}
    failures = []
    for engine in ENGINES:
        for arm in ARMS:
            name = f'smoke-{engine}-{arm}'
            try:
                verdict = json.loads((output / f'verdict-{name}.json').read_text())
                plan = json.loads((output / name / 'plan.json').read_text())
            except (OSError, ValueError) as exc:
                failures.append(f'{name}: SMOKE evidence unreadable: {exc}')
                continue
            if verdict.get('status') == 'STOP':
                failures.append(f'{name}: verdict is STOP ({verdict.get("reason")})')
            if (plan.get('task'), plan.get('arm'), plan.get('config')) != ('SMOKE', arm, engine):
                failures.append(f'{name}: plan is {plan.get("task")} {plan.get("arm")} {plan.get("config")}')
                continue
            failures += [f'{name}: {violation}' for violation in check(output / name, plan, sealed)]
    if failures:
        raise ValueError('SMOKE qualification failed: ' + '; '.join(failures))
    sealed['qualification'] = dict(status='PASS', cells=[f'smoke-{engine}-{arm}' for engine in ENGINES for arm in ARMS])
    path.write_text(json.dumps(sealed, indent=2) + '\n')
    return path


def status_row(out, arm, form, seal):
    found = devlyn_lines(out)
    if arm == 'A':
        return [f'A stderr has {found!r}'] if found else []
    return [] if found == [form['status_line']] else [f'B stderr has {found!r}, sealed {[form["status_line"]]!r}']


def home_row(out, arm, form, seal):
    if arm == 'A':
        present = (out / 'home/.devlyn').exists() or (out / 'home/.devlyn').is_symlink()
        return ['A HOME has .devlyn'] if present else []
    release = home_release(out)
    expected = seal['package']['release_digest']
    return [] if release == expected else [f'B HOME release digest {release}, sealed {expected}']


def init_row(out, arm, form, seal):
    problems = []
    for event in inits(out):
        if event.get('mcp_servers') != []:
            problems.append(f'mcp_servers {event.get("mcp_servers")!r}')
        own = own_plugins(event)
        if arm == 'A' and own:
            problems.append(f'A init plugins {own!r}')
        elif arm == 'B' and own != [form['plugin']]:
            problems.append(f'B init plugins {own!r}, sealed {[form["plugin"]]!r}')
    return list(dict.fromkeys(problems))


def codex_home_row(out, arm, form, seal):
    if arm == 'A':
        found = plugin_paths(out)
        return [f'A CODEX_HOME has {len(found)} plugin or marketplace entries: {found[:5]!r}'] if found else []
    sealed = form['projection']
    return [] if projection(out) == sealed['files'] else [f'B {sealed["path"]} differs from the SMOKE seal']


def request_row(out, arm, form, seal):
    request = first_owner_request(out)
    text = seal['session_text']
    hits, count = text_hits(request, text)
    if arm == 'A':
        preamble = sum(value.count(PREAMBLE) for _, value in strings(request))
        return [f'A first owner request carries the session text {count} time(s), its first sentence {preamble} '
                f'time(s)'] if count or preamble else []
    if count != 1:
        return [f'B first owner request carries the session text {count} time(s)']
    found = location(request, *hits[0], text)
    return [] if found == form['location'] else [f'B session text sits at {found}, sealed {form["location"]}']


def models_row(out, arm, form, seal):
    identity = json.loads((out / 'run/result.json').read_text()).get('identity') or {}
    return ([] if identity.get('status') == 'MATCH' and identity.get('owner') == 'MATCH' else
            [f'identity {identity.get("status")}, owner {identity.get("owner")}'])


def check(cell, plan, seal):
    """Every per-cell assertion of DESIGN for the cell's arm and engine; [] passes. Each row is read on its own, so
    one unreadable row never hides another."""
    out, arm, engine = Path(cell), plan['arm'], plan['config']
    if arm not in ARMS or engine not in ENGINES:
        return [f'arm {arm} or config {engine} unsupported']
    form = seal.get('forms', {}).get(engine)
    if not form:
        return [f'forms: {engine} form unsealed']
    rows = [('status-line', status_row), ('devlyn-home', home_row)]
    rows += ([('claude-init', init_row)] if engine == 'claude' else
             [('codex-home', codex_home_row), ('codex-request', request_row)])
    rows.append(('models', models_row))
    violations = []
    for name, row in rows:
        try:
            violations += [f'{name}: {detail}' for detail in row(out, arm, form, seal)]
        except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
            violations.append(f'{name}: evidence unreadable: {exc}')
    return violations


if __name__ == '__main__':
    command, runtime_path = sys.argv[1:3]
    if command == 'seal':
        print(seal(runtime_path))
    elif command == 'seal-forms':
        print(seal_forms(runtime_path))
    else:
        raise SystemExit(__doc__)
