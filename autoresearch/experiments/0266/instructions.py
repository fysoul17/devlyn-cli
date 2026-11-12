"""Seal the launch of every 0266 package and assert each cell against it: instructions.py seal|seal-forms <runtime.json>.

Packages (DESIGN "Arms"): B, the published devlyn-cli 4.3.31, and C-K1, C-K2, C-K3 (control.py). Both arms launch
through `devlyn run` with the cell's package mounted read-only at /install; each cell is asserted against its own
package's seal.

seal (before SMOKE; DESIGN Q2: no model call, no credential mounted): each package's identity (B: the tarball's sha256
and npm integrity from the control manifest and the unpacked tree against the tarball; every package: its tree sha256
and release digest against control.PINS, package.json's version, and for C its comparison with B, control.compare),
the pinned CLI versions, the session text `devlyn run` plans from each package for a cell HOME (the release's runtime
principles and skill catalog) with the candidate sentences it holds (C: its own exactly once and no other; B: none of
the three), and the launch probe:
- For each package x engine x base tree (TREES), a cell is prepared exactly as run_cell prepares it (under scratch,
  never output/) and its argv runs in the cell's own container (cell.create_argv) with recording shims first on PATH:
  a shim passes `--version` and Codex's `app-server` to the pinned binary and, for any other call, records its argv,
  environment and the bytes of every file its argv names, then exits 0. Sealed per package x engine x tree: the argv
  with the run folder normalised (raw beside it), the sha256 of its plan files (Claude's appended file, Codex's
  developer_instructions; each must equal the package's session text), the devlyn projection Codex's CODEX_HOME
  holds, the status line and the release digest.
- Control: B's argv with --strict-mcp-config must stop with run-argument-unsupported and hand the engine nothing.
- Codex model input without a model call: `codex debug prompt-input <prompt>` through `devlyn run` for every package,
  and raw once per tree (the reference), from a fresh copy of the cell HOME, with `remote_plugin = false` (O10). A
  package's input shows its session text once, the devlyn plugin's skills and no plugin skill root but devlyn's, and
  otherwise the reference's skills and AGENTS.md blocks; the reference shows none of devlyn's.
- Reader control: a fixture HOME with a foreign plugin in plugins/cache, a marketplace entry in config.toml and a
  ~/.codex/AGENTS.md is flagged on all three by the model-input reader; the clean HOME passes.
Writes <output>.parent/instructions.seal.json with qualification PENDING; any failed expectation writes nothing.

seal-forms (after SMOKE): from smoke-<engine>-B, its status line, its HOME release digest, Claude's devlyn plugin entry
in the init event, Codex's projection folder and where Codex's first owner request carries the session text; each
that the launch probe also saw must equal its SMOKE seal. smoke-<engine>-C (C-K3) must show the same plugin entry and
location against K3's probe. Then check() on all four SMOKE cells; PASS only when each has a finished verdict and
passes, and Codex B's usage is COMPLETE with no session besides the owner's (DESIGN Q7).

check(cell, plan, seal): DESIGN "Per-cell assertions" for the cell's package, tied to the launch probe's seal for its
package, engine and task tree; [] passes, otherwise '<assertion>: <detail>'.

Shapes read: run/stderr lines (`devlyn run` writes its status line, or `devlyn run: <code> <params>` when it refuses,
bin/harness-run.js); Claude's system/init events in run/stdout (plugins [{name, path, source}], built-ins with path
'builtin' as in every 0257 cell; mcp_servers); Codex's owner thread (run/stdout thread.started) and its first
inference_started request payload under cell/trace (0257 codex_form; 0232 trace schema 1); Codex's model input (a
skills block listing `<plugin>:<skill>` entries and its skill roots, AGENTS.md blocks), as `codex debug prompt-input`
0.164.0 renders it (0265's fixtures/cell/prompt-input-*.json). A missing or ambiguous shape is a violation, never an
empty match; seal-forms says what it looked for and what it found.
"""
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import uuid

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('control0266i', HERE / 'control.py')
control = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(control)
ENGINES = ('claude', 'codex')
ARMS = ('B', 'C')
PACKAGES = control.PACKAGES
TREES = ('SMOKE', 'D3', 'D4', 'B5', 'F10', 'F11')
VERSION = '4.3.31'
CLI = {'claude': '2.1.322', 'codex': '0.164.0'}
CHANNELS = {'claude': ('append-system-prompt-file', 'plugin-dir'),
            'codex': ('developer_instructions', 'session-plugin')}
HOME = '/home/participant'
RELEASE_ROOT = f'{HOME}/.devlyn/cli/releases/devlyn-cli/{VERSION}'
MARKET = f'devlyn-harness-v{VERSION.replace(".", "-")}'
PROJECTION = f'plugins/cache/{MARKET}/devlyn/{VERSION}'  # under CODEX_HOME
DEVLYN_ROOT = f'{HOME}/.codex/{PROJECTION}/skills'  # the skill root Codex lists for devlyn's session plugin
PREAMBLE = 'The following Devlyn instructions are defaults for this session.'
DEVLYN = ['node', '/install/package/bin/devlyn.js', 'run']
RUN_FOLDER = re.compile(r'/tmp/devlyn-run-[^/\s]+')  # os.tmpdir()/devlyn-run-XXXXXX, harness-run.js
REFUSED = 'devlyn run: run-argument-unsupported {{"engine":"{engine}","argument":"--strict-mcp-config"}}'
SHIM = r'''#!/usr/bin/env python3
"""0266 Q2 recording shim: --version and Codex's app-server go to the pinned binary; any other call is recorded."""
import base64, json, os, sys, uuid
name, argv = os.path.basename(sys.argv[0]), sys.argv[1:]
real = {'claude': '/usr/local/bin/claude', 'codex': '/usr/local/bin/codex'}[name]
if argv == ['--version'] or (name == 'codex' and argv[:1] == ['app-server']):
    os.execv(real, [real, *argv])
files = {}
for arg in argv:
    try:
        with open(arg, 'rb') as handle:
            files[arg] = base64.b64encode(handle.read()).decode()
    except OSError:  # not a file: an option, a value or the prompt
        pass
with open(f'/q2/records/{name}-{uuid.uuid4().hex}.json', 'x') as out:
    json.dump(dict(argv=argv, env=dict(os.environ), files=files), out)
'''


def digest(data):
    return hashlib.sha256(data).hexdigest()


def root(runtime):
    return Path(runtime['output']).parent


def load(name):
    """This folder's module, else 0265's (a module 0266 does not change stays 0265's)."""
    path = HERE / f'{name}.py'
    path = path if path.is_file() else HERE.parent / '0265' / path.name
    spec = importlib.util.spec_from_file_location(f'{name}0266i', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


canonical = control.canonical  # bin/release.js canonical()


def release_record(path):
    """A release.json's version and digest, the digest recomputed as release.js manifestDigest does."""
    manifest = json.loads(path.read_text())
    declared = manifest.get('digest') or {}
    body = {key: value for key, value in manifest.items() if key != 'digest'}
    if declared.get('algorithm') != 'sha256' or digest(canonical(body).encode()) != declared.get('value'):
        raise ValueError(f'{path.name}: its digest does not match its contents')
    return dict(version=manifest.get('version'), digest=declared['value'])


def column(package):
    """The schedule arm column that prepares a cell of this package (prepare.arm_package)."""
    return 'B' if package == 'B' else f'C-{package}'


def sentences(package, text):
    """DESIGN "Apparatus": what a package delivers as principles holds its own candidate sentence exactly once and no
    other (C), or none of the three (B). [] passes."""
    found, expected = control.sentence_counts(text), {k: int(k == package) for k in control.CANDIDATES}
    return [] if found == expected else [f'{package} delivers the candidate sentences {found}, expected {expected}']


def package_identity(runtime):
    """Every package against its pin (control.PINS: tree sha256, release digest), its control manifest record and its
    version; B's tarball against its sha256 and npm integrity and its unpacked tree against the tarball; each C
    package's comparison with B (control.compare) equal to the one the control build recorded."""
    folder = Path(runtime['control'])
    recorded = json.loads(Path(str(folder) + '.manifest.json').read_text())['packages']
    b = recorded['B']
    if b['sha256'] != control.TARBALL_SHA256 or b['integrity'] != control.INTEGRITY:
        raise ValueError('B registry tarball identity mismatch')
    unpacked = folder / 'packages/B/package'
    expected = {name.removeprefix('package/'): value for name, value in b['files'].items()}
    if {str(p.relative_to(unpacked)): digest(p.read_bytes()) for p in unpacked.rglob('*') if p.is_file()} != expected:
        raise ValueError('B unpacked package differs from its tarball')
    identity = {}
    for name in PACKAGES:
        package = folder / 'packages' / name / 'package'
        tree, release_digest = control.PINS[name]
        version = json.loads((package / 'package.json').read_text())['version']
        release = release_record(package / 'release.json')
        if (control.tree_sha256(package), recorded[name]['tree_sha256'], version, release) != (
                tree, tree, VERSION, dict(version=VERSION, digest=release_digest)):
            raise ValueError(f'package {name} is {version}, release {release}; expected {VERSION}@{release_digest} '
                             f'with tree {tree}')
        identity[name] = dict(tree_sha256=tree, version=version, release_digest=release_digest)
        if name == 'B':
            identity[name].update(tarball_sha256=b['sha256'], integrity=b['integrity'])
        else:
            comparison = control.compare(unpacked, package, name)
            if comparison != recorded[name]['comparison']:
                raise ValueError(f'package {name}: its comparison with B differs from the control build\'s')
            identity[name].update(sentence=control.CANDIDATES[name][1], comparison=comparison)
    return identity


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


def devlyn_skills(package):
    """The skills of devlyn's Codex plugin as Codex names them in the model input: devlyn:<skill>."""
    skills = Path(package) / 'native/codex/plugins/devlyn/skills'
    return sorted(f'devlyn:{p.parent.name}' for p in skills.glob('*/SKILL.md'))


# Readers shared by the launch probe and the per-cell assertions.

def devlyn_lines(stderr):
    return [line for line in stderr.splitlines() if line.startswith(('devlyn: ', 'devlyn run: '))]


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


def model_input(request, text):
    """What a Codex model input carries (a request payload, or {'input': <debug prompt-input list>}): the session
    text's count and location, its first sentence's count, the skills, plugin skills (<plugin>:<skill>) and skill roots
    of its skills block, and each AGENTS.md block's sha256."""
    hits, count = text_hits(request, text)
    found = dict(session_text=count, location=location(request, *hits[0], text) if count == 1 else None,
                 preamble=sum(value.count(PREAMBLE) for _, value in strings(request)), skills=[], skill_roots=[],
                 agents_md=[])
    for _, value in strings(request):
        if '<skills_instructions>' in value:
            section = None
            for line in value[value.index('<skills_instructions>'):].splitlines():
                if line.startswith('### '):
                    section = line[4:]
                elif line.startswith('- ') and section == 'Skill roots':
                    found['skill_roots'].append(line.split(' = ', 1)[-1].strip('`'))
                elif line.startswith('- ') and section == 'Available skills':
                    found['skills'].append(line[2:].split(': ', 1)[0])
        if value.startswith('# AGENTS.md instructions'):
            found['agents_md'].append(digest(value.encode()))
    found['plugin_skills'] = sorted(skill for skill in found['skills'] if ':' in skill)
    found['skills'], found['skill_roots'] = sorted(found['skills']), sorted(found['skill_roots'])
    return found


def plugin_roots(found):
    """The skill roots a plugin gives (under a plugins/ folder); Codex's own system skills root is none."""
    return [root for root in found['skill_roots'] if '/plugins/' in root]


def input_violations(label, found):
    """DESIGN "Per-cell assertions" for a Codex model input: a package's input (label B or C) carries its session text
    exactly once and no plugin skill root but devlyn's; the raw reference input (label 'raw', Q2 only) carries neither
    the session text nor its first sentence and no plugin skill root."""
    problems = []
    if label == 'raw' and (found['session_text'] or found['preamble']):
        problems.append(f'raw carries the session text {found["session_text"]} time(s), its first sentence '
                        f'{found["preamble"]} time(s)')
    if label != 'raw' and found['session_text'] != 1:
        problems.append(f'{label} carries the session text {found["session_text"]} time(s)')
    expected = [] if label == 'raw' else [DEVLYN_ROOT]
    if plugin_roots(found) != expected:
        problems.append(f'{label} plugin skill roots {plugin_roots(found)}, expected {expected}')
    return problems


def probe_violations(label, found, clean, devlyn):
    """Q2's reading of a Codex model input: the per-cell rule, the plugin skills by name (raw none, a package devlyn's)
    and the AGENTS.md blocks of the clean raw input of the same tree."""
    problems = input_violations(label, found)
    expected = [] if label == 'raw' else devlyn
    if found['plugin_skills'] != expected:
        problems.append(f'{label} plugin skills {found["plugin_skills"]}, expected {expected}')
    if found['agents_md'] != clean['agents_md']:
        problems.append(f'{label} AGENTS.md blocks {found["agents_md"]}, clean raw {clean["agents_md"]}')
    return problems


# The launch probe (DESIGN Q2).

def normalise(argv):
    return [RUN_FOLDER.sub('/tmp/devlyn-run-*', arg) for arg in argv]


def codex_settings(args):
    """devlyn run's `-c key=value` pairs for Codex, parsed as Codex parses them (TOML)."""
    if len(args) % 2 or args[::2] != ['-c'] * (len(args) // 2):
        raise ValueError(f'Codex plan arguments are not -c pairs: {normalise(args)[:6]!r}')
    settings = {}
    for setting in args[1::2]:
        settings.update(tomllib.loads(setting))
    return settings


def launch(engine, plan, out, run, text, release_digest):
    """One cell under the shims: one status line, the engine called once with devlyn's plan and then O unchanged, the
    plan files equal to the package's session text, the HOME release equal to the package's."""
    code, _, stderr, records = run
    said = devlyn_lines(stderr)
    match = status_pattern(engine, CLI[engine]).fullmatch(said[0]) if len(said) == 1 else None
    if code != 0 or not match or len(records) != 1:
        raise ValueError(f'{plan["name"]}: exit {code}, devlyn lines {said!r}, {len(records)} engine call(s)')
    raw, owner = records[0]['argv'], plan['argv'][4:]
    if raw[len(raw) - len(owner):] != owner:
        raise ValueError(f'{plan["name"]}: the engine was not handed O after the plan')
    planned, argv = raw[:len(raw) - len(owner)], normalise(raw)
    release = home_release(out)
    if release != release_digest or match.group(1) != release[:8]:
        raise ValueError(f'{plan["name"]}: HOME release {release}, status line {match.group(1)}, package '
                         f'{release_digest}')
    sealed = dict(status_line=said[0], release_digest=release, argv=argv, raw_argv=raw)
    if engine == 'claude':
        expected = ['--plugin-dir', f'{RELEASE_ROOT}/native/claude', '--append-system-prompt-file',
                    '/tmp/devlyn-run-*/devlyn-instructions.md']
        if argv[:len(planned)] != expected:
            raise ValueError(f'{plan["name"]}: plan arguments {argv[:len(planned)]!r}, expected {expected!r}')
        appended = base64.b64decode(records[0]['files'].get(raw[3], ''))
        if appended != text.encode():
            raise ValueError(f'{plan["name"]}: the appended file ({len(appended)} bytes) is not the session text')
        sealed.update(plugin_dir=expected[1], plan_files={expected[3]: digest(appended)})
    else:
        expected = dict(marketplaces={MARKET: dict(source_type='local', source=f'{RELEASE_ROOT}/native/codex')},
                        plugins={f'devlyn@{MARKET}': dict(enabled=True)}, developer_instructions=text)
        if codex_settings(planned) != expected:
            raise ValueError(f'{plan["name"]}: Codex plan settings differ from the session plan')
        files = projection(out)
        if not {'.codex-plugin/plugin.json', '.devlyn-harness-projection.json'} <= set(files):
            raise ValueError(f'{plan["name"]}: projection lacks its manifest or marker: {sorted(files)[:5]!r}')
        sealed.update(plan_files={'developer_instructions': digest(text.encode())},
                      projection=dict(path=PROJECTION, files=files))
    return sealed


def refusal(engine, run):
    """The violating launch control: --strict-mcp-config stops with run-argument-unsupported and no engine call."""
    code, _, stderr, records = run
    said = [line for line in stderr.splitlines() if line.strip()]
    if code != 2 or said != [REFUSED.format(engine=engine)] or records:
        raise ValueError(f'{engine} --strict-mcp-config: exit {code}, stderr {said!r}, {len(records)} engine call(s)')
    return dict(exit=code, stderr=said, engine_calls=0)


def plant(home):
    """The reader control's fixture HOME: a foreign plugin in plugins/cache, its marketplace entry (with the plugin
    enabled) in config.toml, and a ~/.codex/AGENTS.md."""
    market = home / 'foreign-market'
    source = market / 'plugins/other'
    (source / '.codex-plugin').mkdir(parents=True)
    (source / 'skills/foreign-skill').mkdir(parents=True)
    (market / '.agents/plugins').mkdir(parents=True)
    (market / '.agents/plugins/marketplace.json').write_text(json.dumps(dict(
        name='foreign-market', plugins=[dict(name='other', source=dict(source='local', path='./plugins/other'))])))
    (source / '.codex-plugin/plugin.json').write_text(json.dumps(dict(name='other', version='1.0.0', skills='./skills/')))
    (source / 'skills/foreign-skill/SKILL.md').write_text('---\nname: foreign-skill\ndescription: A foreign skill.\n---\n')
    shutil.copytree(source, home / '.codex/plugins/cache/foreign-market/other/1.0.0')
    with (home / '.codex/config.toml').open('a') as config:
        config.write(f'\n[marketplaces.foreign-market]\nsource_type = "local"\nsource = "{HOME}/foreign-market"\n'
                     '\n[plugins."other@foreign-market"]\nenabled = true\n')
    (home / '.codex/AGENTS.md').write_text('FOREIGN-AGENTS-RULE: answer in French.\n')


def reader_control(clean, planted, devlyn):
    """Each plant flagged by the model-input reader on the fixture HOME's input; nothing on the clean HOME's."""
    if probe_violations('raw', clean, clean, devlyn):
        raise ValueError('reader control: the clean HOME is flagged')
    given = probe_violations('raw', planted, clean, devlyn)
    flags = {plant: [problem for problem in given if needle in problem] for plant, needle in (
        ('foreign plugin', 'other:foreign-skill'), ('marketplace entry', '/plugins/cache/foreign-market'),
        ('AGENTS.md', 'AGENTS.md'))}
    if not all(flags.values()):
        raise ValueError(f'reader control: not every plant is flagged: {flags}')
    return flags


def container(cell, plan, command, binds=(), env=None, timeout=300):
    """One command in the cell's own container (cell.create_argv: its mounts, limits and working folder; no
    credential), removed with its /tmp volume afterwards. Returns (exit code, stdout, stderr)."""
    tag = uuid.uuid4().hex
    name, volume = 'devlyn-0266-q2-' + tag, 'devlyn-0266-q2-tmp-' + tag
    cell.docker('volume', 'create', '--label', 'devlyn.task=0266-q2', volume)
    try:
        cell.docker(*cell.create_argv(plan, name, volume, cell.mounts(plan) + list(binds), env or plan['env'],
                                      command))
        try:
            done = subprocess.run(['docker', 'start', '-a', name], capture_output=True, timeout=timeout)
        finally:
            cell.docker('rm', '-f', name)
    finally:
        cell.docker('volume', 'rm', '-f', volume)
    return done.returncode, done.stdout.decode(errors='replace'), done.stderr.decode(errors='replace')


def launch_probe(runtime, texts):
    """DESIGN Q2 in the image for every package; scratch only, removed afterwards. Returns the seal's launch, control
    and reference fields."""
    prepare, cell = load('prepare'), load('cell')
    devlyn = devlyn_skills(Path(runtime['control']) / 'packages/B/package')
    sealed = {name: dict(package) for name, package in package_identity(runtime).items()}
    env = json.loads(cell.docker('image', 'inspect', runtime['image'], '--format', '{{json .Config.Env}}'))
    path = next(item[len('PATH='):] for item in env if item.startswith('PATH='))
    work = Path(tempfile.mkdtemp(prefix='q2-probe-', dir=runtime['scratch']))
    try:
        shim = work / 'shim'
        shim.mkdir()
        for engine in ENGINES:
            (shim / engine).write_text(SHIM)
            (shim / engine).chmod(0o755)

        def shimmed(plan, label, command=None):
            records = work / 'records' / label
            records.mkdir(parents=True)
            run = container(cell, plan, command or plan['argv'], [(shim, '/q2/shim', True), (records, '/q2/records', False)],
                            dict(plan['env'], PATH=f'/q2/shim:{path}'))
            return (*run, [json.loads(p.read_text()) for p in sorted(records.glob('*.json'))])

        def copy(home, label):
            return Path(shutil.copytree(home, work / 'homes' / label, symlinks=True))

        def debug(plan, home, raw):
            """`codex debug prompt-input` through devlyn run or raw in the cell's container with this HOME."""
            command = ([] if raw else DEVLYN) + ['codex', 'debug', 'prompt-input', plan['argv'][-1]]
            code, stdout, stderr = container(cell, dict(plan, home=str(home)), command)
            if code != 0:
                raise ValueError(f'{plan["name"]} debug prompt-input: exit {code}: {stderr[-400:]}')
            text = texts['B'] if raw else texts[plan['package']]
            return dict(input=model_input(dict(input=json.loads(stdout)), text), status=devlyn_lines(stderr))

        launch_seal, cells, fresh = {name: {engine: {} for engine in ENGINES} for name in PACKAGES}, {}, {}
        for name in PACKAGES:
            for engine in ENGINES:
                for tree in TREES:
                    out = prepare.prepare(dict(runtime, output=str(work / 'cells')), f'q2-{name}-{engine}-{tree}', tree,
                                          column(name), engine)
                    plan = json.loads((out / 'plan.json').read_text())
                    cells[name, engine, tree] = out, plan
                    fresh[name, engine, tree] = copy(out / 'home', f'fresh-{name}-{engine}-{tree}')
                    launch_seal[name][engine][tree] = launch(engine, plan, out, shimmed(plan, f'{name}-{engine}-{tree}'),
                                                             texts[name], sealed[name]['release_digest'])
        controls = {}
        for engine in ENGINES:  # the violating launch control; the design's argv above is the allowed one
            plan = cells['B', engine, 'SMOKE'][1]
            controls[f'{engine} --strict-mcp-config'] = refusal(engine, shimmed(
                plan, f'{engine}-strict', plan['argv'][:4] + ['--strict-mcp-config'] + plan['argv'][4:]))

        reference = {}
        for tree in TREES:  # Codex model input, no model call: the raw reference, then every package
            plan = cells['B', 'codex', tree][1]
            raw = debug(plan, copy(fresh['B', 'codex', tree], f'debug-{tree}-raw'), raw=True)
            problems = probe_violations('raw', raw['input'], raw['input'], devlyn)
            problems += [f'raw status lines {raw["status"]!r}'] if raw['status'] else []
            for name in PACKAGES:
                plan = cells[name, 'codex', tree][1]
                found = debug(plan, copy(fresh[name, 'codex', tree], f'debug-{tree}-{name}'), raw=False)
                given, base = found['input'], raw['input']
                problems += [f'{name}: {problem}' for problem in probe_violations(name, given, base, devlyn)]
                if found['status'] != [launch_seal[name]['codex'][tree]['status_line']]:
                    problems.append(f'{name} status lines {found["status"]!r}')
                if (given['skill_roots'] != sorted(base['skill_roots'] + [DEVLYN_ROOT])
                        or given['skills'] != sorted(base['skills'] + devlyn)):
                    problems.append(f'{name} skills {given["skills"]} at {given["skill_roots"]}, raw {base["skills"]} '
                                    f'at {base["skill_roots"]}')
                launch_seal[name]['codex'][tree]['model_input'] = given
            if problems:
                raise ValueError(f'Codex model input, {tree}: ' + '; '.join(problems))
            reference[tree] = raw['input']

        planted = copy(fresh['B', 'codex', 'SMOKE'], 'reader')
        plant(planted)
        controls['reader'] = reader_control(reference['SMOKE'], debug(cells['B', 'codex', 'SMOKE'][1], planted,
                                                                      raw=True)['input'], devlyn)
        return dict(packages=sealed, launch=launch_seal, controls=controls, reference_input=reference,
                    devlyn_skills=devlyn)
    finally:
        shutil.rmtree(work)


def seal(runtime_path):
    runtime = json.loads(Path(runtime_path).read_text())
    path = root(runtime) / 'instructions.seal.json'
    if path.exists():
        raise ValueError(f'instruction seal already exists: {path}')
    texts = {name: session_text(Path(runtime['control']) / 'packages' / name / 'package') for name in PACKAGES}
    problems = [problem for name, text in texts.items() for problem in sentences(name, text)]
    if problems:
        raise ValueError('; '.join(problems))
    sealed = dict(cli=CLI, session_text=texts, **launch_probe(runtime, texts), forms={},
                  qualification=dict(status='PENDING'))
    path.write_text(json.dumps(sealed, indent=2) + '\n')
    return path


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


def observed_form(out, engine, sealed, package):
    """One engine's form, read from a SMOKE cell of the package; what the launch probe also saw must equal its SMOKE
    seal for that package."""
    found = [line for line in devlyn_lines((out / 'run/stderr').read_text(errors='replace'))
             if line.startswith('devlyn: ')]
    pattern = status_pattern(engine, sealed['cli'][engine])
    match = pattern.fullmatch(found[0]) if len(found) == 1 else None
    if not match:
        raise ValueError(f'{out.name}: looked for one stderr line matching {pattern.pattern}; found {found!r}')
    release = home_release(out)
    expected = sealed['packages'][package]['release_digest']
    if release != expected or match.group(1) != release[:8]:
        raise ValueError(f'{out.name}: HOME release digest {release} and status line digest {match.group(1)}; '
                         f'package {package} release {expected}')
    probe = sealed['launch'][package][engine]['SMOKE']
    differs = [] if (found[0], release) == (probe['status_line'], probe['release_digest']) else ['status line or digest']
    form = dict(status_line=found[0])
    if engine == 'claude':
        plugins = inits(out)[0]['plugins']
        under = [p for p in plugins if str(p.get('path', '')).startswith(HOME + '/.devlyn/')]
        if len(under) != 1 or under[0].get('name') != 'devlyn':
            raise ValueError(f'{out.name}: looked for one init plugin named devlyn under {HOME}/.devlyn/; '
                             f'the init plugins are {plugins!r}')
        form['plugin'] = under[0]
        differs += [] if under[0]['path'] == probe['plugin_dir'] else [f'plugin path, probe {probe["plugin_dir"]}']
    else:
        form['projection'] = dict(path=PROJECTION, files=projection(out))
        form['location'] = session_location(out, sealed['session_text'][package])
        differs += [] if form['projection'] == probe['projection'] else ['projection']
        differs += ([] if form['location'] == probe['model_input']['location'] else
                    [f'session text location {form["location"]}, probe {probe["model_input"]["location"]}'])
    if differs:
        raise ValueError(f'{out.name}: SMOKE differs from the launch probe\'s SMOKE seal: {"; ".join(differs)}')
    return form


SMOKE_PACKAGES = {'B': 'B', 'C': 'K3'}  # generate_cells.py: SMOKE's C is C-K3; SMOKE says nothing about a candidate
SHARED = {'claude': ('plugin',), 'codex': ('location',)}  # the form fields every package shares, which check() reads


def seal_forms(runtime_path):
    runtime = json.loads(Path(runtime_path).read_text())
    path = root(runtime) / 'instructions.seal.json'
    sealed = json.loads(path.read_text())
    if sealed.get('forms') or sealed.get('qualification', {}).get('status') != 'PENDING':
        raise ValueError('owner forms already sealed')
    output = Path(runtime['output'])
    observed = {engine: {arm: observed_form(output / f'smoke-{engine}-{arm}', engine, sealed, package)
                         for arm, package in SMOKE_PACKAGES.items()} for engine in ENGINES}
    sealed['forms'] = {engine: {key: observed[engine]['B'][key] for key in SHARED[engine]} for engine in ENGINES}
    failures = [f'smoke-{engine}-C: {key} {observed[engine]["C"][key]!r}, B {observed[engine]["B"][key]!r}'
                for engine in ENGINES for key in SHARED[engine] if observed[engine]['C'][key] != observed[engine]['B'][key]]
    for engine in ENGINES:
        for arm, package in SMOKE_PACKAGES.items():
            name = f'smoke-{engine}-{arm}'
            try:
                verdict = json.loads((output / f'verdict-{name}.json').read_text())
                plan = json.loads((output / name / 'plan.json').read_text())
            except (OSError, ValueError) as exc:
                failures.append(f'{name}: SMOKE evidence unreadable: {exc}')
                continue
            if verdict.get('status') == 'STOP':
                failures.append(f'{name}: verdict is STOP ({verdict.get("reason")})')
            launched = (verdict.get('identity') or {}).get('owner_launched_sessions')
            if engine == 'codex' and (verdict.get('usage') != 'COMPLETE' or launched != []):
                # DESIGN Q7: Codex's usage is COMPLETE and is the announced owner session's alone (both arms now go
                # through devlyn run, whose wrapper starts `codex app-server` before the owner)
                failures.append(f'{name}: usage {verdict.get("usage")}, sessions besides the owner {launched}')
            if (plan.get('task'), plan.get('arm'), plan.get('package'), plan.get('config')) != (
                    'SMOKE', arm, package, engine):
                failures.append(f'{name}: plan is {plan.get("task")} {plan.get("arm")} {plan.get("package")} '
                                f'{plan.get("config")}')
                continue
            failures += [f'{name}: {violation}' for violation in check(output / name, plan, sealed)]
    if failures:
        raise ValueError('SMOKE qualification failed: ' + '; '.join(failures))
    sealed['qualification'] = dict(status='PASS', cells=[f'smoke-{engine}-{arm}' for engine in ENGINES
                                                         for arm in SMOKE_PACKAGES])
    path.write_text(json.dumps(sealed, indent=2) + '\n')
    return path


def status_row(out, plan, form, probe, seal):
    found = devlyn_lines((out / 'run/stderr').read_text(errors='replace'))
    return [] if found == [probe['status_line']] else [f'stderr has {found!r}, sealed {[probe["status_line"]]!r}']


def home_row(out, plan, form, probe, seal):
    release = home_release(out)
    return [] if release == probe['release_digest'] else [f'HOME release digest {release}, sealed '
                                                          f'{probe["release_digest"]}']


def init_row(out, plan, form, probe, seal):
    problems = []
    for event in inits(out):
        if event.get('mcp_servers') != []:
            problems.append(f'mcp_servers {event.get("mcp_servers")!r}')
        own = own_plugins(event)
        if own != [form['plugin']]:
            problems.append(f'init plugins {own!r}, sealed {[form["plugin"]]!r}')
    return list(dict.fromkeys(problems))


def codex_home_row(out, plan, form, probe, seal):
    return [] if projection(out) == probe['projection']['files'] else [
        f'{PROJECTION} differs from the launch probe\'s seal']


def request_row(out, plan, form, probe, seal):
    """The package's session text once, where SMOKE sealed it, and no plugin skill root but devlyn's; and, across the
    whole first request, the package's own candidate sentence exactly once and no other (B: none of the three)."""
    request = first_owner_request(out)
    found = model_input(request, seal['session_text'][plan['package']])
    problems = input_violations(plan['arm'], found)
    if found['session_text'] == 1 and found['location'] != form['location']:
        problems.append(f'session text sits at {found["location"]}, sealed {form["location"]}')
    counts = {candidate: sum(value.count(sentence) for _, value in strings(request))
              for candidate, (_, sentence) in control.CANDIDATES.items()}
    expected = {candidate: int(candidate == plan['package']) for candidate in control.CANDIDATES}
    return problems + ([] if counts == expected else [f'candidate sentences {counts}, expected {expected}'])


def models_row(out, plan, form, probe, seal):
    identity = json.loads((out / 'run/result.json').read_text()).get('identity') or {}
    return ([] if identity.get('status') == 'MATCH' and identity.get('owner') == 'MATCH' else
            [f'identity {identity.get("status")}, owner {identity.get("owner")}'])


def check(cell, plan, seal):
    """Every per-cell assertion of DESIGN for the cell's package and engine, against SMOKE's forms and the launch
    probe's seal for the cell's package and task tree; [] passes. Each row is read on its own, so one unreadable row
    never hides another."""
    out, arm, package, engine = Path(cell), plan.get('arm'), plan.get('package'), plan['config']
    if engine not in ENGINES or (arm, package) not in {('B', 'B')} | {('C', k) for k in control.CANDIDATES}:
        return [f'arm {arm}, package {package} or config {engine} unsupported']
    form = seal.get('forms', {}).get(engine)
    if not form:
        return [f'forms: {engine} form unsealed']
    probe = seal.get('launch', {}).get(package, {}).get(engine, {}).get(plan.get('task'))
    if not probe:
        return [f'launch: no launch probe seal for {package} {engine} {plan.get("task")}']
    rows = [('status-line', status_row), ('devlyn-home', home_row)]
    rows += ([('claude-init', init_row)] if engine == 'claude' else
             [('codex-home', codex_home_row), ('codex-request', request_row)])
    rows.append(('models', models_row))
    violations = []
    for name, row in rows:
        try:
            violations += [f'{name}: {detail}' for detail in row(out, plan, form, probe, seal)]
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
