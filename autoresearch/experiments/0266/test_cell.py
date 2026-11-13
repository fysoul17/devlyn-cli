"""Offline tests of 0266's arms and packages, the launch probe and seal of every package, the per-cell assertions
(every cell against its own package's seal, with the delivered candidate sentences) and run_cell. Fakes stand in for
Docker and credentials. The shapes are 0265's fixtures (fixtures/cell: Codex 0.164.0's real model input, the init
event, the status lines, a release.json), moved to 4.3.31 and to each package at test time: the session text of C-K<n>
is B's with its sentence inserted (control.insert), and each package's release.json differs in one file digest, so
each has its own release digest and status line. 0265's cell.py, assess.py and check.py, unchanged, are tested in
0265."""
import base64
import contextlib
import copy
import datetime
import fcntl
import hashlib
import importlib.util
import inspect
import io
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
import threading
import time
import tomllib
import unittest
from unittest import mock
import uuid

HERE = Path(__file__).resolve().parent
PRIOR = HERE.parent / '0265'


def load(name, path=None):
    spec = importlib.util.spec_from_file_location('test_0266_cell_' + name, path or HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


prepare, run_cell, instructions = (load(name) for name in ('prepare', 'run_cell', 'instructions'))
control = instructions.control
runtime_tests = load('test_runtime')  # its synthetic package, re-derived as release.js derives it


def moved(text):
    """A 0265 fixture's text moved to 4.3.31 (the release root, the marketplace and the projection carry the version)."""
    return text.replace('4.3.30', '4.3.31').replace('4-3-30', '4-3-31')


SHAPES = json.loads(moved((PRIOR / 'fixtures/cell/shapes.json').read_text()))
OWNER = {engine: prepare.TASKS['routes'][engine]['owner'] for engine in prepare.CONFIGS}
INPUT = {name: json.loads(moved((PRIOR / f'fixtures/cell/prompt-input-{name}.json').read_text()))
         for name in ('A', 'B', 'control')}  # A: the raw reference input; B: through devlyn run
TEXT = INPUT['B'][2]['content'][0]['text']  # devlyn run's developer_instructions, where Codex 0.164.0 puts it
PACKAGES = instructions.PACKAGES
CANDIDATES = tuple(control.CANDIDATES)
TEXTS = {'B': TEXT, **{k: control.insert(TEXT, k) for k in CANDIDATES}}
ARM = {package: 'B' if package == 'B' else 'C' for package in PACKAGES}


def release_manifest(package):
    """A 4.3.31 release.json per package: 0265's fixture with one file digest of its own, its digest recomputed."""
    manifest = json.loads((PRIOR / 'fixtures/cell/release.json').read_text())
    manifest['version'] = '4.3.31'
    manifest['files'][0]['sha256'] = f'{PACKAGES.index(package):064x}'
    manifest['digest']['value'] = hashlib.sha256(instructions.canonical(
        {k: v for k, v in manifest.items() if k != 'digest'}).encode()).hexdigest()
    return manifest


RELEASES = {package: release_manifest(package) for package in PACKAGES}
DIGEST = {package: RELEASES[package]['digest']['value'] for package in PACKAGES}
STATUS = {package: {engine: SHAPES['status_lines'][engine].replace('@53a2f9f2', f'@{DIGEST[package][:8]}')
                    for engine in prepare.CONFIGS} for package in PACKAGES}
DEVLYN_SKILLS = ['devlyn:devlyn-engines', 'devlyn:devlyn-ideate']
CODEX_TOML = '''model = "gpt-6-astra"
model_reasoning_effort = "high"
approval_policy = "never"
sandbox_mode = "danger-full-access"
web_search = "disabled"
[features]
rollout_budget = false
apps = false
remote_plugin = false
hooks = false
shell_snapshot = false
[features.multi_agent_v2]
enabled = true
expose_spawn_agent_model_overrides = false
[agents]
default_subagent_model = "gpt-6-sol"
default_subagent_reasoning_effort = "high"
max_concurrent_threads_per_session = 4
[projects."/cell/work"]
trust_level = "trusted"
'''


def request(items):
    return {'model': 'gpt-6-astra', 'input': copy.deepcopy(items)}


def raw_request():
    return request(INPUT['A'])


def package_request(package='B', text=None):
    body = request(INPUT['B'])
    body['input'][2]['content'][0]['text'] = TEXTS[package] if text is None else text
    return body


CURATED_ROOT = f'{instructions.HOME}/.codex/plugins/cache/openai-curated-remote/github/1.0.0/skills'
PROFILE = {'account': {'uuid': 'a'}, 'organization': {'uuid': 'o'}}
SECRETS = ('fake-id-token', 'fake-access-token', 'fake-refresh-token', 'fake-claude-token')


def codex_auth_file(path, days=2.0, account='fake-codex-account', **fields):
    """A made-up Codex auth.json, last renewed `days` ago (None: no last_refresh), as Codex writes it (UTC, `Z`)."""
    login = dict(OPENAI_API_KEY=None, tokens=dict(id_token='fake-id-token', access_token='fake-access-token',
                                                  refresh_token='fake-refresh-token', account_id=account))
    if days is not None:
        login['last_refresh'] = datetime.datetime.fromtimestamp(
            time.time() - days * 86400, datetime.timezone.utc).isoformat().replace('+00:00', 'Z')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(login | fields))
    return path


def fake_logins(root):
    """The keychain's Claude login (made-up, an hour and a half left), HOME at root/home and the profile endpoint."""
    stack = contextlib.ExitStack()
    raw = json.dumps({'claudeAiOauth': {'expiresAt': (time.time() + 5400) * 1000, 'accessToken': 'fake-claude-token'}})
    stack.enter_context(mock.patch.object(run_cell.subprocess, 'run',
                                          return_value=subprocess.CompletedProcess([], 0, stdout=raw)))
    stack.enter_context(mock.patch.object(run_cell.Path, 'home', return_value=root / 'home'))
    urlopen = stack.enter_context(mock.patch.object(run_cell.urllib.request, 'urlopen',
                                                    side_effect=lambda *_a, **_k: io.StringIO(json.dumps(PROFILE))))
    return stack, urlopen


def with_plugin(body, root, skill):
    """A request whose skills block lists one more plugin: its skill root and one skill under it."""
    part = next(part for item in body['input'] for part in item.get('content', [])
                if '<skills_instructions>' in part.get('text', ''))
    part['text'] = part['text'].replace('### Available skills\n', f'- `r9` = `{root}`\n### Available skills\n').replace(
        '\n</skills_instructions>', f'\n- {skill}: A plugin skill. (file: r9/x/SKILL.md)\n</skills_instructions>')
    return body


def moved_text(package):
    body = package_request(package)
    body['input'].append({'type': 'message', 'role': 'user', 'content': [body['input'][2]['content'].pop(0)]})
    return body


def without_devlyn_skills(package):
    body = package_request(package)
    body['input'][2]['content'][1]['text'] = INPUT['A'][2]['content'][0]['text']
    return body


def write_request(out, request, later=None):
    """The owner's trace: its first inference request, and optionally a later one."""
    trace = out / 'cell/trace/trace-1-owner'
    shutil.rmtree(trace, ignore_errors=True)
    (trace / 'payloads').mkdir(parents=True)
    rows = [{'seq': 0, 'thread_id': 'owner', 'payload': {'type': 'thread_started', 'thread_id': 'owner'}}]
    for seq, body in ((1, request), (7, later)):
        if body is None:
            continue
        (trace / f'payloads/{seq}.json').write_text(json.dumps(body))
        rows.append({'seq': seq, 'thread_id': 'owner', 'payload': {
            'type': 'inference_started', 'thread_id': 'owner', 'request_payload': {'path': f'payloads/{seq}.json'}}})
    (trace / 'trace.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in rows) + '{"torn')


def write_release(out, package):
    release = out / 'home/.devlyn/cli/releases/devlyn-cli/4.3.31'
    release.mkdir(parents=True, exist_ok=True)
    (release / 'release.json').write_text(json.dumps(RELEASES[package], indent=2) + '\n')


def write_projection(home, package):
    folder = home / '.codex' / instructions.PROJECTION
    (folder / '.codex-plugin').mkdir(parents=True, exist_ok=True)
    (folder / '.codex-plugin/plugin.json').write_text('{"name": "devlyn"}\n')
    (folder / '.devlyn-harness-projection.json').write_text(json.dumps({'schemaVersion': 1, 'package': package}) + '\n')


def make_cell(root, engine, package):
    """A SMOKE-shaped cell of the package that passes every assertion against that package's seal."""
    arm = ARM[package]
    out = root / f'smoke-{engine}-{arm}'
    (out / 'run').mkdir(parents=True)
    (out / 'home/.codex').mkdir(parents=True)
    (out / 'home/.codex/models_cache.json').write_text('{}')
    (out / 'run/stderr').write_text('an unrelated engine warning\n' + STATUS[package][engine] + '\n')
    (out / 'run/result.json').write_text(json.dumps({'identity': {'status': 'MATCH', 'owner': 'MATCH'}}))
    write_release(out, package)
    if engine == 'claude':
        init = copy.deepcopy(SHAPES['claude_init'])
        init['plugins'].append(SHAPES['devlyn_plugin'])
        (out / 'run/stdout').write_text(json.dumps(init) + '\n' + json.dumps({'type': 'result', 'result': 'done'}) + '\n')
    else:
        (out / 'home/.codex/config.toml').write_text(prepare.codex_config(OWNER['codex']))
        (out / 'run/stdout').write_text(json.dumps({'type': 'thread.started', 'thread_id': 'owner'}) + '\n')
        write_request(out, package_request(package), later=raw_request())
        for name in ('.tmp/plugins/plugins/x/.codex-plugin/plugin.json', '.tmp/plugins.sha',  # Codex's own caches (O10)
                     'plugins/cache/openai-curated-remote/github/1.0.0/.codex-plugin/plugin.json'):
            (out / 'home/.codex' / name).parent.mkdir(parents=True, exist_ok=True)
            (out / 'home/.codex' / name).write_text('{}')
        write_projection(out / 'home', package)
    plan = dict(name=out.name, task='SMOKE', arm=arm, package=package, config=engine)
    (out / 'plan.json').write_text(json.dumps(plan))
    return out, plan


def probe_seal(root):
    """The launch probe's fields of a seal for the SMOKE and D3 trees of every package, as `seal` writes them."""
    launch = {}
    for package in PACKAGES:
        for engine in prepare.CONFIGS:
            out, _ = make_cell(Path(tempfile.mkdtemp(dir=root)), engine, package)
            entry = dict(status_line=STATUS[package][engine], release_digest=DIGEST[package])
            if engine == 'claude':
                entry['plugin_dir'] = SHAPES['devlyn_plugin']['path']
            else:
                entry.update(projection=dict(path=instructions.PROJECTION, files=instructions.projection(out)),
                             model_input=instructions.model_input(package_request(package), TEXTS[package]))
            launch.setdefault(package, {})[engine] = {tree: copy.deepcopy(entry) for tree in ('SMOKE', 'D3')}
    reference = {tree: instructions.model_input(raw_request(), TEXT) for tree in ('SMOKE', 'D3')}
    return dict(launch=launch, devlyn_skills=DEVLYN_SKILLS, reference_input=reference)


def pending_seal(root):
    packages = {package: dict(version='4.3.31', release_digest=DIGEST[package], tree_sha256=f'{package}-tree')
                for package in PACKAGES}
    return dict(packages=packages, cli=instructions.CLI, session_text=TEXTS, **probe_seal(root), forms={},
                qualification=dict(status='PENDING'))


def sealed(root):
    seal = pending_seal(root)
    seal['forms'] = {engine: {key: instructions.observed_form(make_cell(root / 'seal', engine, 'B')[0], engine, seal,
                                                              'B')[key] for key in instructions.SHARED[engine]}
                     for engine in prepare.CONFIGS}
    return seal


def rewrite_release(out, change, recompute):
    path = next((out / 'home/.devlyn/cli/releases').rglob('release.json'))
    manifest = json.loads(path.read_text())
    change(manifest)
    if recompute:
        body = {k: v for k, v in manifest.items() if k != 'digest'}
        manifest['digest']['value'] = hashlib.sha256(instructions.canonical(body).encode()).hexdigest()
    path.write_text(json.dumps(manifest, indent=2) + '\n')


def edit_stderr(out, old, new):
    path = out / 'run/stderr'
    text = path.read_text()
    assert old in text, old
    path.write_text(text.replace(old, new))


def edit_init(out, change, count=1):
    init = copy.deepcopy(next(json.loads(line) for line in (out / 'run/stdout').read_text().splitlines()
                              if '"init"' in line))
    events = [copy.deepcopy(init) for _ in range(count)]
    change(events[-1])
    (out / 'run/stdout').write_text(''.join(json.dumps(e) + '\n' for e in events))


def other(package):
    return {'B': 'K3', 'K1': 'K2', 'K2': 'K3', 'K3': 'K1'}[package]


FOREIGN = {'name': 'other', 'path': '/home/participant/.claude/plugins/other', 'source': 'other@market'}
MUTATIONS = {  # mutation(out, engine, package)
    'no_status': lambda out, engine, p: (out / 'run/stderr').write_text('an unrelated engine warning\n'),
    'two_status': lambda out, engine, p: (out / 'run/stderr').write_text((STATUS[p][engine] + '\n') * 2),
    'other_version': lambda out, engine, p: edit_stderr(out, f'{engine} {instructions.CLI[engine]} ', f'{engine} 9.9.9 '),
    'other_digest': lambda out, engine, p: edit_stderr(out, f'@{DIGEST[p][:8]}', '@00000000'),
    'other_package_status': lambda out, engine, p: (out / 'run/stderr').write_text(STATUS[other(p)][engine] + '\n'),
    'principles_unavailable': lambda out, engine, p: (out / 'run/stderr').write_text(re.sub(
        r'principles=configured:\S+', 'principles=unavailable', (out / 'run/stderr').read_text())),
    'refused': lambda out, engine, p: (out / 'run/stderr').write_text(SHAPES['status_lines']['refused'] + '\n'),
    'altered_release': lambda out, engine, p: rewrite_release(
        out, lambda m: m['files'][0].update(sha256='f' * 64), recompute=False),
    'other_release': lambda out, engine, p: rewrite_release(
        out, lambda m: m['files'][0].update(sha256='f' * 64), recompute=True),
    'other_package_release': lambda out, engine, p: write_release(out, other(p)),
    'no_release': lambda out, engine, p: next((out / 'home/.devlyn').rglob('release.json')).unlink(),
    'no_plugin': lambda out, engine, p: edit_init(out, lambda e: e['plugins'].pop()),
    'second_init_without_plugin': lambda out, engine, p: edit_init(out, lambda e: e['plugins'].pop(), count=2),
    'foreign_plugin_init': lambda out, engine, p: edit_init(out, lambda e: e['plugins'].append(FOREIGN)),
    'mcp': lambda out, engine, p: edit_init(out, lambda e: e.update(mcp_servers=[{'name': 'x', 'status': 'connected'}])),
    'no_init': lambda out, engine, p: (out / 'run/stdout').write_text(json.dumps({'type': 'result'}) + '\n'),
    'no_text': lambda out, engine, p: write_request(out, raw_request()),
    'text_twice': lambda out, engine, p: write_request(out, dict(package_request(p), instructions=TEXTS[p])),
    'other_package_text': lambda out, engine, p: write_request(out, package_request(other(p))),
    'sentence_added': lambda out, engine, p: write_request(out, dict(
        package_request(p), instructions=control.CANDIDATES[other(p) if p == 'B' else p][1])),
    'moved_text': lambda out, engine, p: write_request(out, moved_text(p)),
    'no_devlyn_skills': lambda out, engine, p: write_request(out, without_devlyn_skills(p)),
    'foreign_skill': lambda out, engine, p: write_request(out, with_plugin(package_request(p), CURATED_ROOT,
                                                                           'github:github')),
    'no_request': lambda out, engine, p: shutil.rmtree(out / 'cell/trace'),
    'foreign_plugin': lambda out, engine, p: (
        (out / 'home/.codex/plugins/cache/foreign/x/1.0/.codex-plugin').mkdir(parents=True),
        (out / 'home/.codex/plugins/cache/foreign/x/1.0/.codex-plugin/plugin.json').write_text('{}')),
    'marketplace': lambda out, engine, p: (out / 'home/.codex/config.toml').write_text(
        (out / 'home/.codex/config.toml').read_text() + '[marketplaces.x]\nsource_type = "local"\nsource = "/x"\n'),
    'no_projection': lambda out, engine, p: shutil.rmtree(out / 'home/.codex/plugins'),
    'altered_projection': lambda out, engine, p: (
        out / 'home/.codex' / instructions.PROJECTION / '.codex-plugin/plugin.json').write_text('{"name": "x"}\n'),
    'other_package_projection': lambda out, engine, p: write_projection(out / 'home', other(p)),
    'mismatch': lambda out, engine, p: (out / 'run/result.json').write_text(json.dumps(
        {'identity': {'status': 'MISMATCH', 'owner': 'MISMATCH'}})),
    'unverified': lambda out, engine, p: (out / 'run/result.json').write_text(json.dumps(
        {'identity': {'status': 'UNVERIFIED', 'owner': 'MATCH'}})),
}
# (engine, mutation, the one assertion it must fail): DESIGN "Per-cell assertions", run on B and on each C package.
CASES = [
    *[(e, m, 'status-line') for e in prepare.CONFIGS
      for m in ('no_status', 'two_status', 'other_version', 'other_digest', 'other_package_status',
                'principles_unavailable', 'refused')],
    *[(e, m, 'devlyn-home') for e in prepare.CONFIGS
      for m in ('altered_release', 'other_release', 'other_package_release', 'no_release')],
    *[('claude', m, 'claude-init') for m in ('no_plugin', 'second_init_without_plugin', 'foreign_plugin_init', 'mcp',
                                             'no_init')],
    *[('codex', m, 'codex-request') for m in ('no_text', 'text_twice', 'other_package_text', 'sentence_added',
                                              'moved_text', 'no_devlyn_skills', 'foreign_skill', 'no_request')],
    *[('codex', m, 'codex-home') for m in ('no_projection', 'altered_projection', 'other_package_projection')],
    *[(e, m, 'models') for e in prepare.CONFIGS for m in ('mismatch', 'unverified')],
]


class Assertions(unittest.TestCase):
    def test_sealed_forms_pass_every_package_and_engine(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seal = sealed(root)
            self.assertEqual(seal['forms']['claude'], dict(plugin=SHAPES['devlyn_plugin']))
            self.assertEqual(seal['forms']['codex'], dict(location=dict(
                path='input/*/content/*/text', role='developer', type='input_text', whole=True)))
            for engine in prepare.CONFIGS:
                for package in PACKAGES:
                    out, plan = make_cell(root / 'cells' / package, engine, package)
                    self.assertEqual(instructions.check(out, plan, seal), [], (engine, package))

    def test_each_violation_fails_exactly_its_assertion_in_both_arms(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seal = sealed(root)
            for package in ('B', 'K2'):
                for number, (engine, mutation, expected) in enumerate(CASES):
                    out, plan = make_cell(root / package / str(number), engine, package)
                    MUTATIONS[mutation](out, engine, package)
                    violations = instructions.check(out, plan, seal)
                    self.assertEqual({v.split(':', 1)[0] for v in violations}, {expected},
                                     (package, engine, mutation, violations))

    def test_the_delivered_sentences(self):
        # A C cell's request holds its sentence exactly once and no other; a B cell's holds none of the three.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seal = sealed(root)
            for package in PACKAGES:
                out, plan = make_cell(root / package, 'codex', package)
                found = instructions.model_input(instructions.first_owner_request(out), TEXTS[package])
                self.assertEqual(found['session_text'], 1)
                self.assertEqual(control.sentence_counts(json.dumps(instructions.first_owner_request(out),
                                                                    ensure_ascii=False)),
                                 {k: int(k == package) for k in CANDIDATES})
                MUTATIONS['sentence_added'](out, 'codex', package)  # B: K3's sentence once; C: its own twice
                added = 'K3' if package == 'B' else package
                counts = dict({k: int(k == package) for k in CANDIDATES}, **{added: 1 + (package != 'B')})
                self.assertEqual(instructions.check(out, plan, seal), [
                    f'codex-request: candidate sentences {counts}, expected {({k: int(k == package) for k in CANDIDATES})}'])
        self.assertEqual(instructions.sentences('B', TEXTS['B']), [])
        self.assertEqual(instructions.sentences('K1', TEXTS['K1']), [])
        self.assertEqual(len(instructions.sentences('K2', TEXTS['K1'])), 1)
        self.assertEqual(len(instructions.sentences('B', TEXTS['K3'])), 1)

    def test_a_cell_is_held_to_its_own_package(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seal = sealed(root)
            for engine in prepare.CONFIGS:
                out, plan = make_cell(root / engine, engine, 'K1')
                violations = instructions.check(out, dict(plan, package='K2'), seal)
                expected = {'status-line', 'devlyn-home'} | ({'codex-home', 'codex-request'} if engine == 'codex'
                                                             else set())
                self.assertEqual({v.split(':', 1)[0] for v in violations}, expected, (engine, violations))

    def test_unsealed_forms_and_unknown_arm_or_package_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            out, plan = make_cell(Path(temp), 'claude', 'B')
            self.assertEqual(instructions.check(out, plan, pending_seal(Path(temp))), ['forms: claude form unsealed'])
            seal = sealed(Path(temp))
            for change in (dict(arm='C-K3'), dict(package='K4'), dict(arm='C', package='B'), dict(arm='B', package='K1')):
                self.assertEqual(instructions.check(out, dict(plan, **change), seal),
                                 [f'arm {change.get("arm", "B")}, package {change.get("package", "B")} or config '
                                  'claude unsupported'])

    def test_cells_are_tied_to_the_launch_probe_of_their_package_and_tree(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seal = sealed(root)
            changes = [  # (engine, change to the D3 probe seal, the assertions it must fail)
                ('claude', lambda p: p.update(status_line=p['status_line'].replace('2.1.322', '2.1.321')),
                 {'status-line'}),
                ('codex', lambda p: p.update(release_digest='0' * 64), {'devlyn-home'}),
                ('codex', lambda p: p['projection']['files'].update({'skills/x/SKILL.md': '0' * 64}), {'codex-home'})]
            for engine in prepare.CONFIGS:
                for package in PACKAGES:  # allowed: the cell's own package's own tree's seal
                    out, plan = make_cell(root / f'd3-{engine}-{package}', engine, package)
                    self.assertEqual(instructions.check(out, dict(plan, task='D3'), seal), [], (engine, package))
                    self.assertEqual(instructions.check(out, dict(plan, task='F11'), seal),
                                     [f'launch: no launch probe seal for {package} {engine} F11'])
            for number, (engine, change, expected) in enumerate(changes):
                for package in ('B', 'K3'):
                    altered = copy.deepcopy(seal)
                    change(altered['launch'][package][engine]['D3'])
                    out, plan = make_cell(root / f'change-{number}-{package}', engine, package)
                    violations = instructions.check(out, dict(plan, task='D3'), altered)
                    self.assertEqual({v.split(':', 1)[0] for v in violations}, expected, (number, package, violations))
                    self.assertEqual(instructions.check(out, plan, altered), [], (number, package))  # SMOKE's holds
                    other_package = 'K1'
                    out, plan = make_cell(root / f'change-{number}-{package}-{other_package}', engine, other_package)
                    self.assertEqual(instructions.check(out, dict(plan, task='D3'), altered), [])  # its own seal holds

    def test_codex_own_plugin_files_pass_in_both_arms(self):
        # O10: Codex downloads its own curated plugins into CODEX_HOME in both arms; only devlyn's files are read.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seal = sealed(root)
            for package in ('B', 'K3'):
                out, plan = make_cell(root / package, 'codex', package)
                for mutation in ('foreign_plugin', 'marketplace'):
                    MUTATIONS[mutation](out, 'codex', package)
                self.assertEqual(instructions.check(out, plan, seal), [], package)

    def test_release_digest_port_matches_release_js(self):
        for package in PACKAGES:
            with tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / 'release.json'
                path.write_text(json.dumps(RELEASES[package]))
                self.assertEqual(instructions.release_record(path), dict(version='4.3.31', digest=DIGEST[package]))
        record = instructions.release_record(PRIOR / 'fixtures/cell/release.json')  # 4.3.30's real file
        self.assertEqual(record['digest'], '53a2f9f2d3d8cf8cf43391dd92224aa5190e331f0a993649d0a06256ca6a417d')
        self.assertEqual(len(set(DIGEST.values())), 4)


class SealForms(unittest.TestCase):
    def smoke(self, root):
        output = root / 'output'
        for engine in prepare.CONFIGS:
            for package in ('B', 'K3'):
                out, _ = make_cell(output, engine, package)
                (output / f'verdict-{out.name}.json').write_text(json.dumps(
                    {'status': 'COMPLETE', 'usage': 'COMPLETE', 'identity': {'owner_launched_sessions': []}}))
        (root / 'instructions.seal.json').write_text(json.dumps(pending_seal(root)))
        runtime = root / 'runtime.json'
        runtime.write_text(json.dumps({'output': str(output)}))
        return output, runtime

    def test_pass_seals_the_shared_forms_and_qualifies(self):
        with tempfile.TemporaryDirectory() as temp:
            output, runtime = self.smoke(Path(temp))
            instructions.seal_forms(runtime)
            seal = json.loads((Path(temp) / 'instructions.seal.json').read_text())
            self.assertEqual(seal['qualification'], dict(status='PASS', cells=[
                'smoke-claude-B', 'smoke-claude-C', 'smoke-codex-B', 'smoke-codex-C']))
            self.assertEqual(seal['forms'], dict(claude=dict(plugin=SHAPES['devlyn_plugin']), codex=dict(location=dict(
                path='input/*/content/*/text', role='developer', type='input_text', whole=True))))
            with self.assertRaisesRegex(ValueError, 'already sealed'):
                instructions.seal_forms(runtime)

    def assert_refused(self, root, pattern):
        before = (root / 'instructions.seal.json').read_text()
        with self.assertRaisesRegex(ValueError, pattern):
            instructions.seal_forms(root / 'runtime.json')
        self.assertEqual((root / 'instructions.seal.json').read_text(), before)

    def test_status_line_shape_mismatch_names_what_it_looked_for(self):
        with tempfile.TemporaryDirectory() as temp:
            output, _ = self.smoke(Path(temp))
            MUTATIONS['no_status'](output / 'smoke-claude-C', 'claude', 'K3')
            self.assert_refused(Path(temp), r"smoke-claude-C: looked for one stderr line matching .*found \[\]")

    def test_smoke_c_is_k3_and_must_match_its_probe(self):
        with tempfile.TemporaryDirectory() as temp:
            output, _ = self.smoke(Path(temp))
            MUTATIONS['other_package_status'](output / 'smoke-codex-C', 'codex', 'K3')
            MUTATIONS['other_package_release'](output / 'smoke-codex-C', 'codex', 'K3')
            self.assert_refused(Path(temp), r"smoke-codex-C: HOME release digest .* package K3 release")

    def test_plugin_shape_mismatch_lists_the_init_plugins(self):
        with tempfile.TemporaryDirectory() as temp:
            output, _ = self.smoke(Path(temp))
            MUTATIONS['no_plugin'](output / 'smoke-claude-B', 'claude', 'B')
            self.assert_refused(Path(temp), r"looked for one init plugin named devlyn .*agents-md@builtin")

    def test_session_text_shape_mismatch_reports_where_the_first_sentence_is(self):
        with tempfile.TemporaryDirectory() as temp:
            output, _ = self.smoke(Path(temp))
            write_request(output / 'smoke-codex-B', package_request(text='<developer_instructions>\n' + TEXT.rstrip('.')))
            self.assert_refused(Path(temp), r"found it 0 time\(s\).*'role': 'developer'.*'starts_at': 25, "
                                            r"'first_difference': " + str(len(TEXT) - 1))

    def test_c_must_share_b_s_plugin_and_location(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.smoke(root)
            seal = json.loads((root / 'instructions.seal.json').read_text())
            moved_location = request(INPUT['B'])
            moved_location['input'].append({'type': 'message', 'role': 'user',
                                            'content': [moved_location['input'][2]['content'].pop(0)]})
            moved_location['input'][-1]['content'][0]['text'] = TEXTS['K3']
            write_request(root / 'output/smoke-codex-C', moved_location)
            seal['launch']['K3']['codex']['SMOKE']['model_input'] = instructions.model_input(moved_location, TEXTS['K3'])
            (root / 'instructions.seal.json').write_text(json.dumps(seal))
            self.assert_refused(root, r"smoke-codex-C: location .*'role': 'user'.*, B .*'role': 'developer'")

    def test_smoke_forms_must_equal_the_launch_probe(self):
        changes = [
            (lambda launch: launch['B']['claude']['SMOKE'].update(status_line=STATUS['B']['codex']),
             r'smoke-claude-B: SMOKE differs from the launch probe.s SMOKE seal: status line or digest'),
            (lambda launch: launch['K3']['claude']['SMOKE'].update(plugin_dir='/elsewhere'),
             r'smoke-claude-C: .*plugin path, probe /elsewhere'),
            (lambda launch: launch['K3']['codex']['SMOKE']['projection']['files'].update({'x': '0'}),
             r'smoke-codex-C: SMOKE differs .*: projection'),
            (lambda launch: launch['B']['codex']['SMOKE']['model_input']['location'].update(role='user'),
             r"session text location .*'role': 'developer'.*probe .*'role': 'user'")]
        for change, pattern in changes:
            with self.subTest(pattern=pattern), tempfile.TemporaryDirectory() as temp:
                self.smoke(Path(temp))
                seal = json.loads((Path(temp) / 'instructions.seal.json').read_text())
                change(seal['launch'])
                (Path(temp) / 'instructions.seal.json').write_text(json.dumps(seal))
                self.assert_refused(Path(temp), pattern)

    def test_a_violation_or_stop_verdict_refuses_qualification(self):
        with tempfile.TemporaryDirectory() as temp:
            output, _ = self.smoke(Path(temp))
            MUTATIONS['mcp'](output / 'smoke-claude-C', 'claude', 'K3')
            self.assert_refused(Path(temp), r'SMOKE qualification failed: smoke-claude-C: claude-init: mcp_servers')
        with tempfile.TemporaryDirectory() as temp:
            output, _ = self.smoke(Path(temp))
            (output / 'verdict-smoke-codex-C.json').write_text(json.dumps({'status': 'STOP', 'reason': 'locator: x'}))
            self.assert_refused(Path(temp), r'smoke-codex-C: verdict is STOP \(locator: x\)')
        with tempfile.TemporaryDirectory() as temp:
            output, _ = self.smoke(Path(temp))
            plan = json.loads((output / 'smoke-claude-C/plan.json').read_text())
            (output / 'smoke-claude-C/plan.json').write_text(json.dumps(dict(plan, package='K2')))
            self.assert_refused(Path(temp), r'smoke-claude-C: plan is SMOKE C K2 claude')

    def test_codex_usage_must_be_the_owner_session_alone_in_both_arms(self):
        """DESIGN Q7: Codex's usage COMPLETE, and no session besides the owner (devlyn run's app-server read starts
        none), now in both arms: both launch through devlyn run."""
        for name in ('smoke-codex-B', 'smoke-codex-C'):
            for verdict, pattern in (
                    (dict(usage='PARTIAL', identity=dict(owner_launched_sessions=[])), r"usage PARTIAL, sessions"),
                    (dict(usage='COMPLETE', identity=dict(owner_launched_sessions=[dict(engine='codex', session='s')])),
                     rf"{name}: usage COMPLETE, sessions besides the owner \[\{{'engine': 'codex'")):
                with self.subTest(name=name, pattern=pattern), tempfile.TemporaryDirectory() as temp:
                    output, runtime = self.smoke(Path(temp))
                    (output / f'verdict-{name}.json').write_text(json.dumps(dict(status='COMPLETE', **verdict)))
                    self.assert_refused(Path(temp), pattern)
        with tempfile.TemporaryDirectory() as temp:
            output, runtime = self.smoke(Path(temp))
            (output / 'verdict-smoke-claude-C.json').write_text(json.dumps(dict(status='COMPLETE', usage='PARTIAL')))
            instructions.seal_forms(runtime)

    def control_tree(self, root):
        """A control tree of synthetic packages (test_runtime's stand-in) pinned and recorded as the control build
        records them."""
        packages = root / 'control/packages'
        package = runtime_tests.synthetic_package(packages / 'B')
        (package / 'package.json').write_text(json.dumps({'name': 'devlyn-cli', 'version': '4.3.31'}))
        runtime_tests.derive(package, runtime_tests.TEMPLATE)  # release.json lists package.json too
        files = {'package/' + str(p.relative_to(package)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in package.rglob('*') if p.is_file()}
        record = dict(B=dict(sha256='tarball', integrity='sha512-x', files=files, tree_sha256=control.tree_sha256(package),
                             release_digest=control.release(package)['digest']['value']))
        for candidate in CANDIDATES:
            record[candidate] = runtime_tests.fake_candidate(packages, candidate, 'image')
        (root / 'control.manifest.json').write_text(json.dumps(dict(packages=record)))
        (root / 'output').mkdir()
        runtime = root / 'runtime.json'
        runtime.write_text(json.dumps({'output': str(root / 'output'), 'control': str(root / 'control')}))
        pins = {name: (entry['tree_sha256'], entry['release_digest']) for name, entry in record.items()}
        return runtime, pins

    def test_package_identity_every_package_against_its_pin(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime, pins = self.control_tree(Path(temp))
            with mock.patch.multiple(control, PINS=pins, TARBALL_SHA256='tarball', INTEGRITY='sha512-x'):
                identity = instructions.package_identity(json.loads(runtime.read_text()))
                self.assertEqual(set(identity), set(PACKAGES))
                self.assertEqual(identity['B'], dict(tree_sha256=pins['B'][0], version='4.3.31',
                                                     release_digest=pins['B'][1], tarball_sha256='tarball',
                                                     integrity='sha512-x'))
                self.assertEqual(identity['K2']['comparison']['files'], list(control.PRINCIPLE_FILES))
                self.assertEqual(identity['K2']['sentence'], control.CANDIDATES['K2'][1])
                for change, pattern in (  # in this order: the second keeps the first's change
                        (lambda: (Path(temp) / 'control/packages/K1/package/bin/devlyn.js').write_text('x'),
                         'package K1 is 4.3.31'),
                        (lambda: (Path(temp) / 'control/packages/B/package/bin/devlyn.js').write_text('x'),
                         'B unpacked package differs from its tarball')):
                    with self.subTest(pattern=pattern):
                        change()
                        with self.assertRaisesRegex(ValueError, pattern):
                            instructions.package_identity(json.loads(runtime.read_text()))
            with mock.patch.multiple(control, PINS=pins, TARBALL_SHA256='other', INTEGRITY='sha512-x'), \
                    self.assertRaisesRegex(ValueError, 'B registry tarball identity mismatch'):
                instructions.package_identity(json.loads(runtime.read_text()))

    def test_seal_records_every_package_its_session_text_and_pending(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for package in PACKAGES:
                folder = root / 'control/packages' / package / 'package/config/skills/_shared'
                folder.mkdir(parents=True)
                (folder / 'runtime-principles.md').write_text(control.insert(
                    instructions.PREAMBLE + ' Rules.\n2. **No overengineering** — x.\n7. **Production ready** — y.\n',
                    package) if package != 'B' else instructions.PREAMBLE + ' Rules.\n2. **No overengineering** — x.\n'
                    '7. **Production ready** — y.\n')
            (root / 'output').mkdir()
            runtime = root / 'runtime.json'
            runtime.write_text(json.dumps({'output': str(root / 'output'), 'control': str(root / 'control')}))
            probed = dict(packages={'B': {}}, launch={'probe': 'fields'}, controls={}, reference_input={},
                          devlyn_skills=[])
            with mock.patch.object(instructions, 'launch_probe', return_value=probed) as probe:
                seal = json.loads(Path(instructions.seal(runtime)).read_text())
            self.assertEqual(probe.call_args.args[1], seal['session_text'])
            self.assertEqual({key: seal[key] for key in probed}, probed)
            self.assertEqual(seal['cli'], {'claude': '2.1.322', 'codex': '0.164.0'})
            self.assertEqual(seal['qualification'], {'status': 'PENDING'})
            self.assertEqual(set(seal['session_text']), set(PACKAGES))
            for package, text in seal['session_text'].items():
                self.assertEqual(control.sentence_counts(text), {k: int(k == package) for k in CANDIDATES})
            catalog = instructions.RELEASE_ROOT + '/config/skills'
            self.assertTrue(seal['session_text']['B'].endswith(
                f"This session's _shared folder is {catalog}/_shared.\n"
                'Use that absolute folder wherever the Devlyn defaults name _shared/.'))
            with self.assertRaisesRegex(ValueError, 'already exists'):
                instructions.seal(runtime)
            (root / 'instructions.seal.json').unlink()
            path = root / 'control/packages/K2/package/config/skills/_shared/runtime-principles.md'
            path.write_text(path.read_text() + control.CANDIDATES['K1'][1])  # K2 delivering K1's sentence too
            with mock.patch.object(instructions, 'launch_probe', side_effect=AssertionError('probe ran')), \
                    self.assertRaisesRegex(ValueError, 'K2 delivers the candidate sentences'):
                instructions.seal(runtime)
            self.assertFalse((root / 'instructions.seal.json').exists())


O = {engine: prepare.owner_argv(engine, OWNER[engine], 'do the task now') for engine in prepare.CONFIGS}
RUN_FOLDER = '/tmp/devlyn-run-Ab12Cd'


def planned(engine, text=TEXT):
    """What devlyn run hands the engine before O (the 2026-11-11 probe and the Q2 probe saw this)."""
    if engine == 'claude':
        return ['--plugin-dir', f'{instructions.RELEASE_ROOT}/native/claude', '--append-system-prompt-file',
                f'{RUN_FOLDER}/devlyn-instructions.md']
    market = instructions.MARKET
    return ['-c', f'marketplaces={{"{market}"={{"source_type"="local","source"="{instructions.RELEASE_ROOT}/native/codex"}}}}',
            '-c', f'plugins={{"devlyn@{market}"={{"enabled"=true}}}}',
            '-c', 'developer_instructions=' + json.dumps(text, ensure_ascii=False)]


def engine_call(engine, package='B', text=None, **change):
    """One shim record: the engine's argv, environment and the files its argv names."""
    text = TEXTS[package] if text is None else text
    argv = planned(engine, text) + O[engine]
    files = {argv[3]: base64.b64encode(text.encode()).decode()} if engine == 'claude' else {}
    env = dict(HOME=instructions.HOME, HOSTNAME='h', DEVLYN_NODE='/usr/local/bin/node')
    return dict(dict(argv=argv, env=env, files=files), **change)


class LaunchProbe(unittest.TestCase):
    """DESIGN Q2's guards, each violating and allowed, on the shapes the 2026-11-11 probe saw, for B and a C."""

    def cell(self, root, engine, package):
        out, _ = make_cell(root, engine, package)
        plan = dict(name=out.name, argv=instructions.DEVLYN + [engine, *O[engine]])
        return out, plan

    def test_a_launch_is_sealed_and_each_departure_refused(self):
        for package in ('B', 'K2'):
            with tempfile.TemporaryDirectory() as temp:
                for engine in prepare.CONFIGS:
                    out, plan = self.cell(Path(temp) / engine, engine, package)
                    status, text, release = STATUS[package][engine], TEXTS[package], DIGEST[package]
                    call = engine_call(engine, package)
                    sealed = instructions.launch(engine, plan, out, (0, '', f'noise\n{status}\n', [call]), text, release)
                    self.assertEqual(sealed['argv'], instructions.normalise(planned(engine, text)) + O[engine])
                    self.assertEqual(sealed['raw_argv'][-len(O[engine]):], O[engine])
                    self.assertEqual((sealed['status_line'], sealed['release_digest']), (status, release))
                    self.assertEqual(list(sealed['plan_files'].values()), [hashlib.sha256(text.encode()).hexdigest()])
                    if engine == 'claude':
                        self.assertEqual(list(sealed['plan_files']), ['/tmp/devlyn-run-*/devlyn-instructions.md'])
                    else:
                        self.assertEqual(set(sealed['projection']['files']),
                                         {'.codex-plugin/plugin.json', '.devlyn-harness-projection.json'})
                    departures = [(1, f'{status}\n', [call]), (0, '', [call]), (0, f'{status}\n{status}\n', [call]),
                                  (0, f'{status}\n' + SHAPES['status_lines']['refused'] + '\n', [call]),
                                  (0, f'{status}\n', [call, call]), (0, f'{status}\n', []),
                                  (0, f'{status}\n', [dict(call, argv=call['argv'][:-1] + ['another prompt'])]),
                                  (0, f'{status}\n', [engine_call(engine, package, text=text + ' ')]),
                                  (0, f'{status}\n', [engine_call(engine, other(package))]),  # another package's text
                                  (0, STATUS[other(package)][engine] + '\n', [call])]  # another package's release
                    if engine == 'claude':
                        departures.append((0, f'{status}\n', [dict(call, argv=['--plugin-dir', '/x'] + call['argv'][2:])]))
                    else:
                        departures.append((0, f'{status}\n', [dict(call, argv=['-c', 'model="x"'] + call['argv'])]))
                    for number, (code, stderr, records) in enumerate(departures):
                        with self.subTest(package=package, engine=engine, departure=number):
                            with self.assertRaisesRegex(ValueError, f'^{plan["name"]}: '):
                                instructions.launch(engine, plan, out, (code, '', stderr, records), text, release)
                    write_release(out, other(package))
                    with self.assertRaisesRegex(ValueError, 'HOME release'):
                        instructions.launch(engine, plan, out, (0, '', f'{status}\n', [call]), text, release)
            with tempfile.TemporaryDirectory() as temp:
                out, plan = self.cell(Path(temp), 'codex', package)
                (out / 'home/.codex' / instructions.PROJECTION / '.devlyn-harness-projection.json').unlink()
                with self.assertRaisesRegex(ValueError, 'projection lacks'):
                    instructions.launch('codex', plan, out, (0, '', STATUS[package]['codex'] + '\n',
                                                             [engine_call('codex', package)]), TEXTS[package],
                                        DIGEST[package])

    def test_strict_mcp_config_control(self):
        for engine in prepare.CONFIGS:
            refused = instructions.REFUSED.format(engine=engine)
            self.assertEqual(json.loads(refused.split(' ', 3)[3]), {'engine': engine, 'argument': '--strict-mcp-config'})
            self.assertEqual(instructions.refusal(engine, (2, '', refused + '\n', [])),
                             dict(exit=2, stderr=[refused], engine_calls=0))
            for run in ((0, '', '', [engine_call(engine)]), (2, '', refused + '\n', [engine_call(engine)]),
                        (2, '', SHAPES['status_lines']['refused'] + '\n', []), (2, '', '', [])):
                with self.subTest(engine=engine, run=run[0]), \
                        self.assertRaisesRegex(ValueError, f'^{engine} --strict-mcp-config: '):
                    instructions.refusal(engine, run)

    def test_model_input_reader_on_real_codex_output(self):
        found = {name: instructions.model_input(dict(input=items), TEXT) for name, items in INPUT.items()}
        system = ['imagegen', 'openai-docs', 'skill-creator', 'skill-installer']
        self.assertEqual(found['A'], dict(session_text=0, location=None, preamble=0, skills=system, plugin_skills=[],
                                          skill_roots=[f'{instructions.HOME}/.codex/skills/.system'], agents_md=[]))
        self.assertEqual((found['B']['session_text'], found['B']['plugin_skills'], found['B']['agents_md']),
                         (1, DEVLYN_SKILLS, []))
        self.assertEqual(found['B']['location'], dict(path='input/*/content/*/text', role='developer',
                                                      type='input_text', whole=True))
        self.assertEqual(found['B']['skill_roots'], sorted(found['A']['skill_roots'] + [instructions.DEVLYN_ROOT]))
        self.assertEqual((found['control']['plugin_skills'], len(found['control']['agents_md'])),
                         (['other:foreign-skill'], 1))
        raw = found['A']
        self.assertEqual(instructions.input_violations('raw', raw), [])  # the reference reading
        for arm in ('B', 'C'):
            self.assertEqual(instructions.input_violations(arm, found['B']), [])  # the per-cell rule
            self.assertEqual(len(instructions.input_violations(arm, raw)), 2)
        self.assertEqual(len(instructions.input_violations('raw', found['control'])), 1)
        self.assertEqual(len(instructions.input_violations('raw', found['B'])), 2)
        self.assertEqual(instructions.probe_violations('raw', raw, raw, DEVLYN_SKILLS), [])  # Q2's reading
        self.assertEqual(instructions.probe_violations('K1', found['B'], raw, DEVLYN_SKILLS), [])
        self.assertEqual(len(instructions.probe_violations('raw', found['control'], raw, DEVLYN_SKILLS)), 3)
        extra = dict(found['B'], plugin_skills=DEVLYN_SKILLS + ['devlyn:extra'])  # a skill the package does not have
        self.assertEqual(len(instructions.probe_violations('B', extra, raw, DEVLYN_SKILLS)), 1)
        k3 = instructions.model_input(package_request('K3'), TEXTS['K3'])
        self.assertEqual((k3['session_text'], instructions.model_input(package_request('K3'), TEXT)['session_text']),
                         (1, 0))

    def test_reader_control_flags_each_plant_and_passes_the_clean_home(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            (home / '.codex').mkdir()
            (home / '.codex/config.toml').write_text(CODEX_TOML)
            instructions.plant(home)
            config = tomllib.loads((home / '.codex/config.toml').read_text())
            self.assertEqual((config['marketplaces']['foreign-market']['source'], config['plugins']),
                             (f'{instructions.HOME}/foreign-market', {'other@foreign-market': {'enabled': True}}))
            self.assertTrue((home / '.codex/plugins/cache/foreign-market/other/1.0.0/.codex-plugin/plugin.json').is_file())
            self.assertTrue((home / '.codex/AGENTS.md').is_file())
        clean = instructions.model_input(dict(input=INPUT['A']), TEXT)
        planted = instructions.model_input(dict(input=INPUT['control']), TEXT)  # Codex 0.164.0 on such a HOME
        flags = instructions.reader_control(clean, planted, DEVLYN_SKILLS)
        self.assertEqual(set(flags), {'foreign plugin', 'marketplace entry', 'AGENTS.md'})
        self.assertTrue(all(flags.values()))
        with self.assertRaisesRegex(ValueError, 'not every plant'):  # a reader blind to AGENTS.md
            instructions.reader_control(clean, dict(planted, agents_md=[]), DEVLYN_SKILLS)
        with self.assertRaisesRegex(ValueError, 'clean HOME is flagged'):
            instructions.reader_control(planted, planted, DEVLYN_SKILLS)

    def test_normalise_and_settings(self):
        self.assertEqual(instructions.normalise([f'{RUN_FOLDER}/devlyn-instructions.md', '-p']),
                         ['/tmp/devlyn-run-*/devlyn-instructions.md', '-p'])
        self.assertEqual(instructions.codex_settings(planned('codex'))['developer_instructions'], TEXT)
        for args in (['-c'], ['--config', 'a=1'], ['-c', 'a=1', 'exec']):
            with self.assertRaisesRegex(ValueError, 'not -c pairs'):
                instructions.codex_settings(args)


class LaunchProbeRun(unittest.TestCase):
    """launch_probe's wiring with a fake container in place of Docker: every package x engine x tree prepared and run,
    the controls and Codex's model input (raw and per package) read, scratch removed; any failure writes no seal."""

    def fake(self, root, broken=None):
        runs = []

        def prepared(runtime, name, tree, column, engine):
            arm, package = prepare.arm_package(runtime, column)
            out = Path(runtime['output']) / name
            (out / 'home/.codex').mkdir(parents=True)
            (out / 'home/.claude').mkdir()
            if engine == 'codex':
                (out / 'home/.codex/config.toml').write_text(CODEX_TOML)
            (out / 'plan.json').write_text(json.dumps(dict(
                name=name, task=tree, arm=arm, package=package, config=engine, home=str(out / 'home'),
                argv=instructions.DEVLYN + [engine, *O[engine]], env=dict(HOME=instructions.HOME))))
            return out

        def materialize(home, package, codex):
            write_release(home.parent, package)
            if codex:
                write_projection(home, package)
                (home / '.codex/.tmp').mkdir(exist_ok=True)
                (home / '.codex/.tmp/plugins.sync.lock').write_text('')

        def container(_cell, plan, command, binds=(), env=None, timeout=300):
            home, engine, package = Path(plan['home']), plan['config'], plan['package']
            runs.append((plan['name'], command[:6]))
            records = next((Path(src) for src, dst, _ in binds if dst == '/q2/records'), None)
            status = STATUS[package][engine] + '\n'
            if '--strict-mcp-config' in command and broken != f'strict {engine}':
                return 2, '', instructions.REFUSED.format(engine=engine) + '\n'
            if 'prompt-input' in command:
                raw = command[0] == 'codex'
                if not raw:
                    materialize(home, package, True)
                planted = (home / '.codex/AGENTS.md').exists()
                if planted or raw:
                    return 0, json.dumps(INPUT['control' if planted else 'A']), ''
                shown = package_request(other(package) if broken == f'debug {plan["task"]} {package}' else package)
                return 0, json.dumps(shown['input']), status
            call = engine_call(engine, package)
            if broken == f'launch {package} {engine} {plan["task"]}':
                call['argv'] = call['argv'] + ['--extra']
            materialize(home, package, engine == 'codex')
            (records / f'{engine}-1.json').write_text(json.dumps(call))
            return 0, '', status

        cell = mock.Mock(docker=mock.Mock(return_value=json.dumps(['LANG=C', 'PATH=/usr/local/bin:/usr/bin'])))
        modules = dict(prepare=mock.Mock(prepare=prepared), cell=cell)
        package = root / 'control/packages/B/package/native/codex/plugins/devlyn/skills'
        for skill in ('devlyn-engines', 'devlyn-ideate', '_shared'):
            (package / skill).mkdir(parents=True, exist_ok=True)
            if skill != '_shared':
                (package / skill / 'SKILL.md').write_text('---\n')
        (root / 'scratch').mkdir(exist_ok=True)
        runtime = dict(output=str(root / 'output'), control=str(root / 'control'), scratch=str(root / 'scratch'),
                       image='sha256:image')
        identity = {name: dict(release_digest=DIGEST[name], tree_sha256=f'{name}-tree') for name in PACKAGES}
        return runtime, runs, [mock.patch.object(instructions, 'load', side_effect=lambda name: modules[name]),
                               mock.patch.object(instructions, 'container', side_effect=container),
                               mock.patch.object(instructions, 'package_identity', return_value=identity)]

    def probe(self, root, broken=None):
        runtime, runs, patches = self.fake(root, broken)
        for patch in patches:
            patch.start()
        try:
            return instructions.launch_probe(runtime, TEXTS), runs
        finally:
            mock.patch.stopall()
            self.assertEqual(list((root / 'scratch').iterdir()), [])

    def test_every_package_engine_and_tree_is_probed_and_sealed(self):
        with tempfile.TemporaryDirectory() as temp:
            sealed, runs = self.probe(Path(temp))
        self.assertEqual(set(sealed), {'packages', 'launch', 'controls', 'reference_input', 'devlyn_skills'})
        self.assertEqual({package: {engine: list(trees) for engine, trees in engines.items()}
                          for package, engines in sealed['launch'].items()},
                         {package: {engine: list(instructions.TREES) for engine in prepare.CONFIGS}
                          for package in PACKAGES})
        self.assertEqual(sealed['devlyn_skills'], DEVLYN_SKILLS)
        self.assertEqual(set(sealed['controls']), {'claude --strict-mcp-config', 'codex --strict-mcp-config', 'reader'})
        self.assertEqual(list(sealed['reference_input']), list(instructions.TREES))
        for package in PACKAGES:
            for engine in prepare.CONFIGS:
                for tree, entry in sealed['launch'][package][engine].items():
                    self.assertEqual(entry['argv'][:len(planned(engine))],
                                     instructions.normalise(planned(engine, TEXTS[package])))
                    self.assertEqual((entry['status_line'], entry['release_digest']),
                                     (STATUS[package][engine], DIGEST[package]))
                    self.assertNotIn('a', entry)  # no raw arm A
                    if engine == 'codex':
                        self.assertEqual(entry['model_input']['plugin_skills'], DEVLYN_SKILLS)
                        self.assertEqual(entry['model_input']['session_text'], 1)
        kinds = [('strict' if '--strict-mcp-config' in command else 'debug' if 'prompt-input' in command else 'launch')
                 for _, command in runs]
        self.assertEqual({kind: kinds.count(kind) for kind in set(kinds)}, dict(launch=48, strict=2, debug=6 + 24 + 1))

    def test_a_failed_expectation_raises_and_cleans_scratch(self):
        for broken, pattern in (('launch K2 codex F11', 'q2-K2-codex-F11: the engine was not handed O'),
                                ('strict codex', 'codex --strict-mcp-config: exit 0, .*1 engine call'),
                                ('debug D4 K1', 'Codex model input, D4: K1: K1 carries the session text 0')):
            with self.subTest(broken=broken), tempfile.TemporaryDirectory() as temp:
                with self.assertRaisesRegex(ValueError, pattern):
                    self.probe(Path(temp), broken)


class Arms(unittest.TestCase):
    def runtime(self, root):
        return dict(output=str(root / 'output'), control=str(root / 'control'), image='sha256:image',
                    auth=str(root / 'auth'), sources=str(root / 'sources'))

    def prepared(self, root, column, config):
        out = prepare.prepare(self.runtime(root), f'smoke-{config}-{column}', 'SMOKE', column, config)
        return out, json.loads((out / 'plan.json').read_text())

    def test_argv_install_watchdog_and_config_byte_for_byte(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for config in prepare.CONFIGS:
                for column, package in (('B', 'B'), ('C-K1', 'K1'), ('C-K2', 'K2'), ('C-K3', 'K3')):
                    out, plan = self.prepared(root, column, config)
                    prompt = (out / 'prompt.txt').read_text()
                    owner = (['-p', '--model', 'claude-opus-5-5', '--effort', 'high', '--permission-mode',
                              'bypassPermissions', '--output-format', 'stream-json', '--verbose', prompt]
                             if config == 'claude' else ['exec', '--json', '--skip-git-repo-check', prompt])
                    self.assertEqual(plan['argv'], ['node', '/install/package/bin/devlyn.js', 'run', config] + owner)
                    self.assertEqual((plan['arm'], plan['package']), (ARM[package], package))
                    self.assertEqual(plan['install'], str(root / 'control/packages' / package))
                    self.assertEqual(json.loads((out / 'baseline.json').read_text())['package'], package)
                    self.assertEqual(plan['wall_seconds'], 2700)
                    config_toml = out / 'home/.codex/config.toml'
                    if config == 'codex':
                        self.assertEqual(config_toml.read_text(), CODEX_TOML)
                    else:
                        self.assertFalse(config_toml.exists())

    def go(self, root, candidate='K2', package_sha256=None, decision='GO'):
        (root / 'instructions.seal.json').write_text(json.dumps(dict(packages={
            k: dict(tree_sha256=f'{k}-tree') for k in PACKAGES})))
        (root / 'screen-decision.json').write_text(json.dumps(dict(
            decision=decision, candidate=candidate, package_sha256=package_sha256 or f'{candidate}-tree')))

    def test_the_registered_c_takes_its_package_from_a_go(self):
        # DESIGN "Stage S": C of the registered run is the screen decision's candidate, only on a GO whose package is
        # the sealed one; anything else refuses before any write.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runtime = self.runtime(root)
            for setup, pattern in (
                    (lambda: None, 'no screen decision and instruction seal'),
                    (lambda: self.go(root, decision='STOP'), 'the screen decision is STOP, not GO'),
                    (lambda: self.go(root, decision='UNDECIDED', candidate=None), 'the screen decision is UNDECIDED'),
                    (lambda: self.go(root, package_sha256='K3-tree'), "the screen decision's K2 package K3-tree is "
                                                                       'not the sealed one'),
                    (lambda: self.go(root, candidate='B'), 'not GO with a candidate')):
                with self.subTest(pattern=pattern):
                    setup()
                    with self.assertRaisesRegex(ValueError, pattern):
                        prepare.prepare(runtime, 'c002-F10-claude-C-r1', 'F10', 'C', 'claude')
                    self.assertFalse((root / 'output').exists())
            self.go(root)
            self.assertEqual(prepare.arm_package(runtime, 'C'), ('C', 'K2'))
            out, plan = self.prepared(root, 'C', 'claude')
            self.assertEqual((plan['arm'], plan['package'], plan['install']), ('C', 'K2', str(root / 'control/packages/K2')))

    def test_codex_config_refuses_a_plugins_line_or_other_trust(self):
        text = prepare.base.codex_toml(OWNER['codex'])
        for variant in (text.replace('plugins = false\n', 'plugins = false \n'),
                        text.replace('plugins = false\n', 'plugins = true\n'),
                        text.replace('plugins = false\n', ''),  # O10: Codex's remote plugins would stay on
                        text.replace('[projects."/work"]', '[projects."/elsewhere"]')):
            with mock.patch.object(prepare.base, 'codex_toml', return_value=variant):
                with self.assertRaisesRegex(ValueError, 'still disables plugins or leaves remote plugins on|'
                                                        'inherited Codex project trust'):
                    prepare.codex_config(OWNER['codex'])
        self.assertEqual(prepare.codex_config(OWNER['codex']), CODEX_TOML)

    def test_other_tasks_arms_and_configs_are_refused_before_any_write(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = dict(output=str(Path(temp) / 'output'))
            for task, column, config, pattern in (('I0185', 'B', 'claude', '0266 cells are'),
                                                  ('D3', 'B', 'grok', '0266 cells are'),
                                                  ('SMOKE', 'A', 'claude', "arm 'A'"),
                                                  ('SMOKE', 'C-K4', 'codex', "arm 'C-K4'"),
                                                  ('SMOKE', 'K1', 'codex', "arm 'K1'")):
                with self.assertRaisesRegex(ValueError, pattern):
                    prepare.prepare(runtime, 'x', task, column, config)
            self.assertFalse((Path(temp) / 'output').exists())

    def test_no_raw_arm_or_installer_code_path_remains(self):
        banned = [r'I0185', r'\bINSTALL\b', r'\binstall\(', r'skills_present', r'install_output', r"== 'A'",
                  r'launch_a', r'env_patch', r'devlyn_files', r'instructions\.pre', r'codex_limits',
                  r'claude_limits_with_account', r'claude_limits_(before|after)', r"'E1'", r"'E2'", r'B launch fault']
        for name in ('prepare.py', 'run_cell.py', 'instructions.py', 'driver.py', 'decide.py'):
            text = (HERE / name).read_text()
            for pattern in banned:
                self.assertIsNone(re.search(pattern, text), (name, pattern))
        text = (HERE / 'prepare.py').read_text()
        for flag in ('--strict-mcp-config', '--strict-config', '--mcp-config'):  # refused by devlyn run
            self.assertFalse(flag in text, flag)
        self.assertEqual((prepare.ARMS, prepare.CONFIGS, prepare.PACKAGES), (('B', 'C'), ('claude', 'codex'),
                                                                             control.PACKAGES))
        self.assertFalse((HERE / 'strict_config_check.py').exists() or (HERE / 'rehearse_memory.py').exists())

    def test_removed_entry_points_and_parameters(self):
        self.assertNotIn('__main__', (PRIOR / 'assess.py').read_text())
        self.assertEqual(set(run_cell.check.ROWS), {'B5', 'F10', 'F11'})
        self.assertIs(inspect.signature(run_cell.claude_limits).parameters['access_token'].default,
                      inspect.Parameter.empty)
        self.assertEqual(list(inspect.signature(run_cell.assessment_snapshot).parameters), ['runtime'])
        self.assertNotIn('venue', inspect.signature(run_cell.grade).parameters)
        self.assertFalse(hasattr(run_cell, 'diagnostics') or 'diagnostics' in run_cell.MODULES)

    def test_every_cell_mounts_its_package_read_only(self):
        for package in PACKAGES:
            plan = dict(cell='/c', home='/h', control='/k', harness='/hn', install=f'/control/packages/{package}')
            self.assertIn((Path(f'/control/packages/{package}'), '/install', True), run_cell.cell_run.mounts(plan))


class VerdictWrite(unittest.TestCase):
    def test_a_verdict_is_written_whole_or_not_at_all(self):
        # Second re-check (MEDIUM): write_verdict goes through a temp file and os.replace. Violating: a write that
        # dies half way leaves the earlier verdict intact, never a partial one, and reports a STOP. Allowed: a normal
        # write replaces the verdict and leaves no temp file.
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'verdict-c001.json'
            self.assertEqual(run_cell.write_verdict(path, dict(status='COMPLETE', n=1)), 0)
            self.assertEqual(json.loads(path.read_text()), dict(status='COMPLETE', n=1))
            with mock.patch.object(run_cell.os, 'replace', side_effect=OSError('disk full')), \
                    contextlib.redirect_stderr(io.StringIO()) as err:
                self.assertEqual(run_cell.write_verdict(path, dict(status='COMPLETE', n=2)), 2)
            self.assertIn('VERDICT_UNWRITTEN', err.getvalue())
            self.assertEqual(json.loads(path.read_text()), dict(status='COMPLETE', n=1))
            self.assertEqual(run_cell.write_verdict(path, dict(status='STOP', reason='x')), 2)
            self.assertEqual(json.loads(path.read_text())['status'], 'STOP')
            self.assertEqual(sorted(p.name for p in Path(temp).iterdir() if not p.name.startswith('.')),
                             ['verdict-c001.json'])


class PreserveTmp(unittest.TestCase):
    """Amendment 2: 0266's copy of a cell's /tmp volume (run_cell.preserve_tmp), which 0265's cell.py and driver.py's
    recovery call, against a fake Docker at subprocess.run. CopyProof runs it on the pinned image."""
    COMMAND = (r"set -o pipefail; cd /src && find . \( -type p -o -type s -o -type b -o -type c \) -printf "
               r"'left_out\0%y\0%m\0%p\0' && find . -type d ! -perm -u+x -printf 'made_searchable\0%y\0%m\0%p\0' "
               r"&& find . -type d -print0 | (cd /dst && xargs -0 -r mkdir -p --) && find . ! \( -type p -o -type s "
               r"-o -type b -o -type c \) -print0 | tar --null --no-unquote --verbatim-files-from --no-recursion -T - "
               r"-cf - | tar -C /dst -xpf - && find . -type d ! -perm -u+x -print0 | (cd /dst && xargs -0 -r chmod "
               r"u+x --)")

    def cell(self, root):
        out = root / 'cell'
        (out / 'run').mkdir(parents=True)
        (out / 'tmp').mkdir()
        return out

    def preserve(self, out, listing=b'', fails=None):
        """preserve_tmp('vol', out/tmp, 'image'): the copy prints listing, or raises fails, and notes what tmp held
        when it started; `docker volume rm` answers as Docker does. Returns (Docker's calls as (argv, keyword
        arguments), tmp's entries at the copy, the exception raised or None)."""
        calls, held = [], []

        def docker(argv, **kwargs):
            calls.append((argv, kwargs))
            if argv[:2] != ['docker', 'run']:
                return subprocess.CompletedProcess(argv, 0, stdout=argv[-1] + '\n', stderr='')
            held.extend(sorted(p.name for p in (out / 'tmp').iterdir()))
            if fails:
                raise fails
            return subprocess.CompletedProcess(argv, 0, stdout=listing, stderr=b'')
        with mock.patch.object(run_cell.subprocess, 'run', side_effect=docker):
            try:
                run_cell.preserve_tmp('vol', out / 'tmp', 'image')
            except (subprocess.SubprocessError, OSError, ValueError) as exc:
                return calls, held, exc
        return calls, held, None

    def test_the_copy_leaves_special_files_out_makes_directories_first_and_then_removes_the_volume(self):
        """Violating (the old copy): `tar -cf - .` reaches every FIFO and, run as root, creates each directory with
        its recorded mode at once; the host mount refuses a FIFO without owner read or write and a directory without
        owner read, and tar cannot write into a read-only one. Allowed: one container, its output read as bytes, in
        five steps: list the FIFOs, sockets and device nodes, which are left out; list the directories without owner
        search; make every directory in /dst; copy everything else (both type filters, names read NUL-separated and
        verbatim); give the listed directories owner search. Then the volume is removed."""
        with tempfile.TemporaryDirectory() as temp:
            out = self.cell(Path(temp))
            calls, _, error = self.preserve(out)
            self.assertIsNone(error)
            self.assertEqual(calls, [
                (['docker', 'run', '--rm', '--network', 'none', '--user', '0', '--mount',
                  'type=volume,src=vol,dst=/src,readonly', '--mount', f'type=bind,src={out / "tmp"},dst=/dst',
                  '--entrypoint', 'bash', 'image', '-c', self.COMMAND], dict(capture_output=True, check=True, timeout=600)),
                (['docker', 'volume', 'rm', 'vol'], dict(capture_output=True, text=True, check=True, timeout=60))])
            self.assertFalse((out / 'run/tmp-copy.json').exists())

    def test_what_the_copy_changed_is_listed_in_run_and_a_stale_list_is_removed(self):
        """The copy's NUL-separated records (kind, type letter, octal mode, path) become run/tmp-copy.json: the
        special files left out and the directories made searchable, a name that is not UTF-8 or holds a newline among
        them. Either list alone writes the file; a copy that changed nothing leaves none, an earlier one removed."""
        listing = (b'left_out\x00p\x00200\x00./exp/tmp79kh78r5/fifo_noperm\x00left_out\x00s\x00755\x00./cc-socks/s\x00'
                   b'made_searchable\x00d\x000\x00./locked\x00left_out\x00p\x000\x00./-new\nline \\ caf\xe9\x00'
                   b'made_searchable\x00d\x00600\x00./locked/-T\x00')
        with tempfile.TemporaryDirectory() as temp:
            out = self.cell(Path(temp))
            calls, _, error = self.preserve(out, listing)
            self.assertIsNone(error)
            self.assertEqual(json.loads((out / 'run/tmp-copy.json').read_text()), dict(
                left_out=[dict(type='p', mode='200', path='./exp/tmp79kh78r5/fifo_noperm'),
                          dict(type='s', mode='755', path='./cc-socks/s'),
                          dict(type='p', mode='0', path=os.fsdecode(b'./-new\nline \\ caf\xe9'))],
                made_searchable=[dict(mode='0', path='./locked'), dict(mode='600', path='./locked/-T')]))
            self.assertEqual(calls[-1][0], ['docker', 'volume', 'rm', 'vol'])
            calls, _, error = self.preserve(out, b'made_searchable\x00d\x00600\x00./dir-600\x00')
            self.assertIsNone(error)
            self.assertEqual(json.loads((out / 'run/tmp-copy.json').read_text()),
                             dict(left_out=[], made_searchable=[dict(mode='600', path='./dir-600')]))
            calls, _, error = self.preserve(out)
            self.assertIsNone(error)
            self.assertFalse((out / 'run/tmp-copy.json').exists())

    def test_what_a_failed_copy_left_is_removed_before_the_copy(self):
        """c069: the failed copy left its part in tmp, half-made FIFO nodes among it, and a failed copy can leave
        directories the host user cannot enter. Violating: the copy starts over it, or emptying it fails on such a
        directory or follows a link out of tmp. Allowed: tmp is emptied (a real FIFO, a nested folder, a file,
        directories of mode 000 holding a file, links to a folder outside tmp whose target stays as it was) and keeps
        its own mode."""
        with tempfile.TemporaryDirectory() as temp:
            out = self.cell(Path(temp))
            tmp, outside = out / 'tmp', Path(temp) / 'outside'
            outside.mkdir()
            (outside / 'kept').write_text('kept')
            outside.chmod(0o750)
            (tmp / 'exp/nested').mkdir(parents=True)
            (tmp / 'exp/nested/e.py').write_text('x')
            os.mkfifo(tmp / 'exp/fifo_noperm', 0o200)
            (tmp / 'editor.txt~').write_text('x')
            (tmp / 'link').symlink_to(outside)
            (tmp / 'locked/inner').mkdir(parents=True)
            (tmp / 'locked/inner/in').write_text('x')
            (tmp / 'locked/link').symlink_to(outside)
            (tmp / 'locked/inner').chmod(0)
            (tmp / 'locked').chmod(0)
            tmp.chmod(0o1777)
            calls, held, error = self.preserve(out)
            self.assertIsNone(error)
            self.assertEqual(held, [])
            self.assertEqual(stat.S_IMODE(tmp.stat().st_mode), 0o1777)
            self.assertEqual((stat.S_IMODE(outside.stat().st_mode), [p.name for p in outside.iterdir()],
                              (outside / 'kept').read_text()), (0o750, ['kept'], 'kept'))

    def test_a_failed_copy_raises_and_keeps_the_volume(self):
        """0265's cell.py records a teardown failure from what the copy raises (driver.py's recovery stops both
        lanes): a copy that fails or times out, or whose list cannot be read, removes no volume and writes no list."""
        refused = subprocess.CalledProcessError(2, ['docker', 'run'], b'',
                                                b'tar: ./exp/fifo: Cannot mkfifo: Permission denied\n')
        for fails, listing, raised in ((refused, b'', subprocess.CalledProcessError),
                                       (subprocess.TimeoutExpired(['docker', 'run'], 600), b'', subprocess.TimeoutExpired),
                                       (None, b'left_out\x00p\x00200\x00./exp/fifo', ValueError),
                                       (None, b'left_out\x00p\x00200\x00', ValueError),
                                       (None, b'other\x00p\x00200\x00./exp/fifo\x00', ValueError)):
            with self.subTest(raised=raised.__name__, listing=listing), tempfile.TemporaryDirectory() as temp:
                out = self.cell(Path(temp))
                calls, _, error = self.preserve(out, listing, fails)
                self.assertIsInstance(error, raised)
                self.assertEqual([argv[:2] for argv, _ in calls], [['docker', 'run']])
                self.assertFalse((out / 'run/tmp-copy.json').exists())

    def test_0265s_cell_and_the_recovery_take_this_copy_and_the_closed_modules_stay(self):
        """0265's run() and driver.py's recovery (cell.cell_run.preserve_tmp) resolve the name in 0266's loaded copy
        of 0265's cell.py, which now holds this function; 0233's own preserve_tmp is untouched, and both closed files
        keep the bytes every 0266 cell's seal.json records under `imported`."""
        self.assertIs(run_cell.cell_run.preserve_tmp, run_cell.preserve_tmp)
        self.assertIsNot(run_cell.cell_run.legacy.preserve_tmp, run_cell.preserve_tmp)
        self.assertEqual(list(inspect.signature(run_cell.preserve_tmp).parameters), ['volume', 'dest', 'image'])
        self.assertEqual({name: hashlib.sha256((HERE.parent / name).read_bytes()).hexdigest()
                          for name in ('0233/cell.py', '0265/cell.py')},
                         {'0233/cell.py': '06c2258058acb4c69371b0a7ad342e1c57939bbe562fa97143a8530cc4247a4b',
                          '0265/cell.py': '117868cfaa49d96e117e81399c0db0eb80f936f0f66dd3653b419bdbf72f525c'})


@unittest.skipUnless(os.environ.get('NX01_0266_COPY_PROOF'),
                     'the copy proof on the pinned image: set NX01_0266_COPY_PROOF to runtime-smoke.json')
class CopyProof(unittest.TestCase):
    """Amendment 2's proof of the copy on the pinned image, run by the orchestrator (volumes and containers, no model),
    in two parts. Each fills a scratch volume as a cell's user fills /tmp, copies it into a folder under the runtime
    root's scratch/ (a host path Docker shares) and lists both sides as a root container sees them. The ordinary
    volume: the old copy (0233's) and this one give the same tree, and the old copy shows what the mount itself makes
    of a mode. The special volume: what the mount refuses (special files, directories without owner read or search, a
    read-only directory that holds a file) and names that look like options."""
    ORDINARY = r'''
import os, subprocess
os.chdir('/tmp')
subprocess.run(['git', 'init', '-q', 'repo'], check=True)
with open('repo/a.txt', 'w') as stream:
    stream.write('a\n')
subprocess.run(['git', '-C', 'repo', 'add', 'a.txt'], check=True)
subprocess.run(['git', '-C', 'repo', '-c', 'user.name=proof', '-c', 'user.email=proof@example.invalid', 'commit',
                '-qm', 'one'], check=True)
os.makedirs('tree/700/750')
with open('tree/700/750/deep', 'w') as stream:
    stream.write('deep')
for name, mode in (('file-000', 0), ('file-200', 0o200), ('file-400', 0o400), ('file-444', 0o444),
                   ('file-600', 0o600), ('file-644', 0o644), ('file-755', 0o755)):
    with open(name, 'w') as stream:
        stream.write(name)
    os.chmod(name, mode)
with open('hard-a', 'w') as stream:
    stream.write('linked')
os.link('hard-a', 'hard-b')
os.symlink('file-644', 'to-file')
os.symlink('tree', 'to-dir')
os.symlink('/tmp/absent', 'dangling')
os.symlink('loop', 'loop')
os.chmod('tree/700/750', 0o750)
os.chmod('tree/700', 0o700)
for top, folders, names in os.walk('.', topdown=False):
    for name in folders + names:
        path = os.path.join(top, name)
        if os.lstat(path).st_uid == os.getuid():  # the volume starts with the image's /tmp, which is another user's
            os.utime(path, (1_000_000_000, 1_000_000_000), follow_symlinks=False)
'''
    SPECIAL = r'''
import os, socket
os.chdir('/tmp')
os.makedirs('dir-000/nested-000')
for path, body in (('dir-000/inside', 'inside'), ('dir-000/nested-000/inside', 'nested')):
    with open(path, 'w') as stream:
        stream.write(body)
for name, mode in (('fifo-200', 0o200), ('fifo-644', 0o644), ('-fifo \\ 000\n', 0),
                   ('dir-000/nested-000/fifo-600', 0o600)):
    os.mkfifo(name)
    os.chmod(name, mode)
socket.socket(socket.AF_UNIX).bind('socket')
for name, mode, body in (('file-200', 0o200, 'a'), ('file-000', 0, 'bb'), ('file-444', 0o444, 'ccc'),
                         ('-dash', 0o644, 'dddd'), ('-T', 0o644, 'eeeee'), ('--null', 0o644, 'ffffff'),
                         ('back\\slash', 0o644, 'g'), ('new\nline', 0o644, 'hh'), ('a space', 0o644, 'iii')):
    with open(name, 'w') as stream:
        stream.write(body)
    os.chmod(name, mode)
for folder in ('dir-555', 'dir-600', '-dirdash'):
    os.mkdir(folder)
    with open(folder + '/in', 'w') as stream:
        stream.write(folder)
os.mkdir('dir-300')
os.symlink('/tmp/absent', 'dangling')
os.symlink('loop', 'loop')
os.symlink('dir-000', 'to-dir-000')
with open('hard-a', 'w') as stream:
    stream.write('linked')
os.link('hard-a', 'hard-b')
for folder, mode in (('dir-000/nested-000', 0), ('dir-000', 0), ('dir-555', 0o555), ('dir-600', 0o600),
                     ('dir-300', 0o300)):
    os.chmod(folder, mode)
'''
    LIST = r'''
import hashlib, json, os, stat, sys
TYPES = {stat.S_IFREG: 'f', stat.S_IFDIR: 'd', stat.S_IFLNK: 'l', stat.S_IFIFO: 'p', stat.S_IFSOCK: 's',
         stat.S_IFBLK: 'b', stat.S_IFCHR: 'c'}


def refuse(error):
    raise error


def entry(path):
    status = os.lstat(path)
    kind, digest = TYPES[stat.S_IFMT(status.st_mode)], None
    if kind == 'f':
        with open(path, 'rb') as stream:
            digest = hashlib.sha256(stream.read()).hexdigest()
    return dict(type=kind, mode=format(stat.S_IMODE(status.st_mode), 'o'), owner=[status.st_uid, status.st_gid],
                links=status.st_nlink, size=status.st_size, mtime=status.st_mtime_ns, inode=status.st_ino,
                target=os.readlink(path) if kind == 'l' else None, sha256=digest)


os.chdir(sys.argv[1])
paths = ['.'] + [os.path.join(top, name) for top, folders, names in os.walk('.', onerror=refuse)
                 for name in folders + names]
print(json.dumps({path: entry(path) for path in paths}))
'''
    TREE = ('type', 'mode', 'owner', 'links', 'size', 'mtime', 'target', 'sha256')  # what both copies keep alike

    def docker(self, *args, timeout=120):
        return subprocess.run(['docker', *args], capture_output=True, check=True, timeout=timeout).stdout

    def listing(self, image, mount, root):
        """Every entry under root as a root container sees it: {path as find prints it: its fields (LIST)}."""
        return json.loads(self.docker('run', '--rm', '--network', 'none', '--user', '0', '--mount', mount,
                                      '--entrypoint', 'python3', image, '-c', self.LIST, root))

    def volume(self, image, fill):
        """A scratch volume (its own name and label, removed when the test ends) filled by fill as the cell's user
        (the image's own, as a cell's owner runs) with the volume at /tmp, as in a cell; returns it and its listing."""
        volume = 'devlyn-0266-copy-proof-' + uuid.uuid4().hex
        self.addCleanup(self.docker, 'volume', 'rm', '-f', volume)
        self.docker('volume', 'create', '--label', 'devlyn.task=0266-copy-proof', volume)
        self.docker('run', '--rm', '--network', 'none', '--mount', f'type=volume,src={volume},dst=/tmp',
                    '--entrypoint', 'python3', image, '-c', fill)
        return volume, self.listing(image, f'type=volume,src={volume},dst=/src,readonly', '/src')

    def copy(self, preserve, volume, image, cell):
        """preserve(volume, cell/tmp, image) in a cell's layout (tmp/ beside run/); returns tmp's listing."""
        (cell / 'run').mkdir(parents=True)
        (cell / 'tmp').mkdir()
        self.assertIsNone(preserve(volume, cell / 'tmp', image))
        return self.listing(image, f'type=bind,src={cell / "tmp"},dst=/dst,readonly', '/dst')

    def gone(self, volume):
        return self.docker('volume', 'ls', '-q', '--filter', f'name=^{volume}$').strip() == b''

    def test_the_copy_on_the_pinned_image(self):
        runtime = json.loads(Path(os.environ['NX01_0266_COPY_PROOF']).read_text())
        image, legacy = runtime['image'], run_cell.cell_run.legacy  # 0233's cell.py: its preserve_tmp is the old copy
        real = legacy.docker

        def keep(*args, **kwargs):  # the old copy without its volume removal, so that the new copy reads the volume too
            return None if args[:2] == ('volume', 'rm') else real(*args, **kwargs)

        def refuse(error):
            raise error
        with tempfile.TemporaryDirectory(dir=runtime['scratch'], prefix='copy-proof-') as temp:
            # The ordinary volume: the old copy and this one give the same tree.
            volume, ordinary = self.volume(image, self.ORDINARY)
            with mock.patch.object(legacy, 'docker', keep):
                old = self.copy(legacy.preserve_tmp, volume, image, Path(temp) / 'old')
            new = self.copy(run_cell.preserve_tmp, volume, image, Path(temp) / 'new')
            self.assertEqual(set(old), set(ordinary))
            self.assertEqual({path: [entry[field] for field in self.TREE] for path, entry in new.items()},
                             {path: [entry[field] for field in self.TREE] for path, entry in old.items()})
            self.assertFalse((Path(temp) / 'new/run/tmp-copy.json').exists())
            self.assertTrue(self.gone(volume))
            mount = {}  # what the mount itself makes of a mode, which the old copy gives too (a 444 file read as 400)
            for path, entry in ordinary.items():
                self.assertEqual(mount.setdefault((entry['type'], entry['mode']), old[path]['mode']), old[path]['mode'],
                                 path)

            # The special volume: what the copy leaves out or makes searchable is listed, every other entry is copied.
            volume, source = self.volume(image, self.SPECIAL)
            special = {path for path, entry in source.items() if entry['type'] in ('p', 's', 'b', 'c')}
            closed = {path for path, entry in source.items()
                      if entry['type'] == 'd' and not int(entry['mode'], 8) & 0o100}
            self.assertEqual(sorted((source[path]['type'], source[path]['mode']) for path in special),
                             [('p', '0'), ('p', '200'), ('p', '600'), ('p', '644'), ('s', source['./socket']['mode'])])
            self.assertEqual(sorted(source[path]['mode'] for path in closed), ['0', '0', '600'])
            copied = self.copy(run_cell.preserve_tmp, volume, image, Path(temp) / 'special')
            self.assertTrue(self.gone(volume))
            record = json.loads((Path(temp) / 'special/run/tmp-copy.json').read_text())
            self.assertEqual(sorted((entry['type'], entry['mode'], entry['path']) for entry in record['left_out']),
                             sorted((source[path]['type'], source[path]['mode'], path) for path in special))
            self.assertEqual(sorted((entry['mode'], entry['path']) for entry in record['made_searchable']),
                             sorted((source[path]['mode'], path) for path in closed))
            kept = {path: entry for path, entry in source.items() if path not in special}
            self.assertEqual(set(copied), set(kept))
            for path, entry in kept.items():  # a listed directory gains exactly the owner search bit
                mode = (format(int(entry['mode'], 8) | 0o100, 'o') if path in closed
                        else mount.get((entry['type'], entry['mode']), entry['mode']))
                self.assertEqual([copied[path][field] for field in ('type', 'mode', 'sha256')],
                                 [entry['type'], mode, entry['sha256']], path)
                if entry['type'] != 'd':  # a directory's size is the file system's
                    self.assertEqual(copied[path]['size'], entry['size'], path)
            self.assertEqual([copied['./hard-a'][field] for field in ('inode', 'links')],
                             [copied['./hard-b']['inode'], 2])  # one file, two names
            host = Path(temp) / 'special/tmp'
            for top, folders, names in os.walk(host, onerror=refuse):  # no FIFO or socket on the host
                for name in folders + names:
                    self.assertNotIn(stat.S_IFMT(os.lstat(os.path.join(top, name)).st_mode),
                                     (stat.S_IFIFO, stat.S_IFSOCK), os.path.join(top, name))
            for path, entry in kept.items():  # the host user opens every regular file
                if entry['type'] == 'f':
                    self.assertEqual(hashlib.sha256((host / path).read_bytes()).hexdigest(), entry['sha256'], path)


class Rules(unittest.TestCase):
    def evidence(self, root, stderr='', stdout='', rollout=False):
        out = root / 'cell'
        (out / 'run').mkdir(parents=True)
        (out / 'run/stderr').write_text(stderr)
        (out / 'run/stdout').write_text(stdout)
        if rollout:
            (out / 'home/.codex/sessions/2026').mkdir(parents=True)
            (out / 'home/.codex/sessions/2026/rollout.jsonl').write_text('{}\n')
        return out

    def test_launch_fault_rule(self):
        refused = SHAPES['status_lines']['refused']
        cases = [  # (arm, stderr, stdout, rollout, fault)
            ('B', refused + '\n', '', False, 'run-argument-unsupported {"engine":"codex","argument":"-C"}'),
            ('B', 'engine noise\n' + refused + '\n', 'not json\n', False,
             'run-argument-unsupported {"engine":"codex","argument":"-C"}'),
            ('B', SHAPES['status_lines']['codex'] + '\ndevlyn run: run-engine-failed {"engine":"codex"}\n', '', False,
             None),
            ('B', refused + '\n', json.dumps(SHAPES['claude_init']) + '\n', False, None),
            ('B', refused + '\n', json.dumps({'type': 'thread.started', 'thread_id': 't'}) + '\n', False, None),
            ('B', refused + '\n', '', True, None),
            ('B', 'ERROR: something else\n', '', False, None),
            ('C', refused + '\n', '', False, 'run-argument-unsupported {"engine":"codex","argument":"-C"}'),
        ]  # both arms launch through devlyn run, so a refusal is a launch fault in either
        for number, (arm, stderr, stdout, rollout, fault) in enumerate(cases):
            with tempfile.TemporaryDirectory() as temp:
                out = self.evidence(Path(temp), stderr, stdout, rollout)
                self.assertEqual(run_cell.launch_fault(out, {'arm': arm}), fault, number)

    def test_memory_kill_rule(self):
        # O3: the flag, the owner's 137 and no watchdog, all three; the flag alone or 137 alone is the cell's outcome.
        cases = [({'oom_killed': True, 'exit_code': 137}, 'EXITED_NONZERO', True),
                 ({'oom_killed': True, 'exit_code': 137}, 'HANG_TIMEOUT', False),
                 ({'oom_killed': True, 'exit_code': 0}, 'EXITED_0', False),
                 ({'oom_killed': True, 'exit_code': 1}, 'EXITED_NONZERO', False),
                 ({'oom_killed': False, 'exit_code': 137}, 'EXITED_NONZERO', False),
                 ({'oom_killed': None, 'exit_code': 137}, 'EXITED_NONZERO', False),
                 ({'oom_killed': False, 'exit_code': 137}, 'HANG_TIMEOUT', False),
                 ({'oom_killed': False, 'exit_code': 1}, 'EXITED_NONZERO', False),
                 ({'oom_killed': False, 'exit_code': 0}, 'EXITED_0', False),
                 (None, 'EXITED_0', False)]
        for state, status, killed in cases:
            owner = dict(owner_status=status, **({'container': state} if state else {}))
            self.assertEqual(bool(run_cell.memory_kill(owner)), killed, (state, status))
        self.assertEqual(run_cell.memory_kill({'owner_status': 'EXITED_NONZERO',
                                               'container': {'oom_killed': True, 'exit_code': 137}}),
                         'OOMKilled=True exit_code=137 owner EXITED_NONZERO')

    def test_check_lock_waits_for_a_holder_and_is_released_on_an_exception(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = {'check_lock': str(Path(temp) / 'check.lock')}
            entered, results = threading.Event(), []
            holder = open(runtime['check_lock'], 'a')
            fcntl.flock(holder, fcntl.LOCK_EX)
            with mock.patch.object(run_cell.check, 'check', side_effect=lambda *_: entered.set() or {'checked': True}):
                worker = threading.Thread(target=lambda: results.append(run_cell.checked(Path(temp), runtime)))
                worker.start()
                self.assertFalse(entered.wait(0.5))
                fcntl.flock(holder, fcntl.LOCK_UN)
                holder.close()
                worker.join(5)
            self.assertEqual(results, [{'checked': True}])
            with mock.patch.object(run_cell.check, 'check', side_effect=run_cell.check.NoVerdict('oracle crashed')):
                with self.assertRaises(run_cell.check.NoVerdict):
                    run_cell.checked(Path(temp), runtime)
            with open(runtime['check_lock'], 'a') as probe:
                fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)  # raises BlockingIOError if still held

    def test_token_guard_and_disk_floor(self):
        self.assertEqual(run_cell.MIN_TOKEN_SECONDS, 3600)
        self.assertEqual(run_cell.HEADROOM_BYTES, 16 * 2**30)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'auth').mkdir()
            codex_auth_file(root / 'home/.codex/auth.json')
            runtime = {'output': str(root), 'auth': str(root / 'auth')}
            profile = PROFILE
            for left, blocked in ((3590, True), (3700, False)):
                raw = json.dumps({'claudeAiOauth': {'expiresAt': (time.time() + left) * 1000, 'accessToken': 'fake'}})
                with mock.patch.object(run_cell.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, stdout=raw)), \
                        mock.patch.object(run_cell.Path, 'home', return_value=root / 'home'), \
                        mock.patch.object(run_cell.urllib.request, 'urlopen',
                                          side_effect=lambda *_a, **_k: io.StringIO(json.dumps(profile))):
                    identity, reason = run_cell.snapshot_auth(runtime)
                self.assertEqual(reason is not None, blocked, left)
            identity = dict(account=['a', 'o'], token_seconds_left=4000)
            for free, blocked in ((run_cell.HEADROOM_BYTES - 1, True), (run_cell.HEADROOM_BYTES, False)):
                with mock.patch.object(run_cell.shutil, 'disk_usage', return_value=mock.Mock(free=free)), \
                        mock.patch.object(run_cell, 'snapshot_auth', return_value=(identity, None)), \
                        mock.patch.object(run_cell, 'claude_limits', side_effect=AssertionError('no window read')):
                    venue, reason = run_cell.preflight(runtime, expected_account=['a', 'o'])
                self.assertEqual(reason is not None, blocked, free)
                self.assertEqual(venue, None if blocked else identity)


class CodexLogin(unittest.TestCase):
    """DESIGN Operations "Codex login" (O15): the snapshot copies the login the runtime names (codex_auth), else the
    host default, only while its last renewal is under seven days old, and records its account by fingerprint. Every
    login here is a made-up file."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.auth = self.root / 'auth'
        self.auth.mkdir()
        self.default = codex_auth_file(self.root / 'home/.codex/auth.json', account='default-account-id')
        self.named = codex_auth_file(self.root / 'registered/auth.json', account='named-account-id')
        stack, self.urlopen = fake_logins(self.root)
        self.enterContext(stack)

    def runtime(self, codex_auth=None, **fields):
        return dict(auth=str(self.auth), output=str(self.root / 'output'), codex_auth=codex_auth, **fields)

    def copies(self):
        return sorted(p.name for p in self.auth.iterdir())

    def test_the_named_login_is_copied_and_the_default_is_not(self):
        venue, blocked = run_cell.snapshot_auth(self.runtime(str(self.named)))
        self.assertIsNone(blocked)
        copy_ = self.auth / 'codex.json'
        self.assertEqual(copy_.read_bytes(), self.named.read_bytes())
        self.assertNotEqual(copy_.read_bytes(), self.default.read_bytes())
        self.assertEqual(oct(copy_.stat().st_mode & 0o777), '0o600')  # umask 077, as before
        self.assertEqual(venue['codex_account'], run_cell.base.fingerprint('named-account-id'))
        self.assertFalse([value for value in ('named-account-id', *SECRETS) if value in json.dumps(venue)])

    def test_the_default_is_used_when_the_field_is_null_or_absent(self):
        for runtime in (self.runtime(None), dict(auth=str(self.auth))):
            with self.subTest(runtime=runtime):
                for path in self.auth.iterdir():
                    path.unlink()
                venue, blocked = run_cell.snapshot_auth(runtime)
                self.assertIsNone(blocked)
                self.assertEqual((self.auth / 'codex.json').read_bytes(), self.default.read_bytes())
                self.assertEqual(venue['codex_account'], run_cell.base.fingerprint('default-account-id'))
        codex_auth_file(self.default, account=None)  # a login without an account id: recorded as null
        self.assertIsNone(run_cell.snapshot_auth(self.runtime())[0]['codex_account'])

    def test_the_renewal_guard(self):
        self.assertEqual(run_cell.CODEX_LOGIN_MAX_AGE_SECONDS, 7 * 86400)
        literal = 'Codex login (codex_auth) '
        prefix = re.escape(literal)
        cases = (('2 days old', dict(days=2), None),
                 ('a minute ahead of this clock', dict(days=-60 / 86400), None),
                 ('7.5 days old', dict(days=7.5), prefix + r'last renewed 7\.5 days ago; limit 7 days'),
                 ('no last_refresh', dict(days=None), prefix + 'has no last_refresh'),
                 ('unparseable', dict(last_refresh='last tuesday'),
                  prefix + 'last_refresh is not an ISO-8601 time with a time zone'),
                 ('no time zone', dict(last_refresh='2026-11-09T10:00:00'),
                  prefix + 'last_refresh is not an ISO-8601 time with a time zone'),
                 ('a day in the future', dict(days=-1), prefix + r'last renewed 86\d{3} s in the future; limit 300 s'))
        for label, fields, reason in cases:
            with self.subTest(label):
                for path in self.auth.iterdir():
                    path.unlink()
                self.urlopen.reset_mock()
                login = codex_auth_file(self.root / f'{label}.json', **fields)
                venue, blocked = run_cell.snapshot_auth(self.runtime(str(login)))
                if reason is None:
                    self.assertIsNone(blocked)
                    self.assertEqual((self.auth / 'codex.json').read_bytes(), login.read_bytes())
                else:
                    self.assertIsNone(venue)
                    self.assertRegex(blocked, '^' + reason + '$')
                    self.assertEqual(self.copies(), [])  # blocked before either copy and the profile check
                    self.urlopen.assert_not_called()
        (self.root / 'not-json.json').write_text('not json')
        for path, reason in ((self.root / 'absent.json', literal + 'unreadable: No such file or directory'),
                             (self.root / 'not-json.json', literal + 'is not JSON')):
            self.assertEqual(run_cell.snapshot_auth(self.runtime(str(path))), (None, reason))
        self.assertEqual(self.copies(), [])

    def test_a_blocked_snapshot_holds_the_driver_with_no_verdict(self):
        """The real driver and run_cell: preflight's blocked path exits 3 (not dispatched, its reason on file), the
        driver waits 60 s to try again, and nothing is prepared, recorded as a verdict or latched."""
        driver = load('driver')  # loads this folder's run_cell, as the lanes do
        old = codex_auth_file(self.root / 'registered-old/auth.json', days=7.6)
        (self.root / 'instructions.seal.json').write_text(json.dumps(
            {'forms': {'claude': {}, 'codex': {}}, 'qualification': {'status': 'PASS'}}))
        runtime_path = self.root / 'runtime-codex.json'
        runtime_path.write_text(json.dumps(self.runtime(
            str(old), lane='codex', renewal_lock=str(self.root / 'renewal.lock'), check_lock=str(self.root / 'check.lock'),
            caps={'seven_day': 95, 'five_hour': 95}, image='sha256:test', image_tarball=str(self.root / 'image.tar'))))
        row = next(r for r in driver.rows([str(HERE / 'cells.tsv')]) if r[3] == 'codex')
        lane = driver.Driver(runtime_path, [row])
        self.addCleanup(lane.lock.close)

        class Waited(BaseException):  # ends the loop at its first wait as an interrupt would: no lane-end latch
            pass
        with mock.patch.object(driver.Driver, 'ready', return_value=True), \
                mock.patch.object(driver.cell, 'image_identity', return_value=True), \
                mock.patch.object(driver.cell.shutil, 'disk_usage',
                                  return_value=mock.Mock(free=driver.cell.HEADROOM_BYTES)), \
                mock.patch.object(driver.time, 'sleep', side_effect=Waited) as sleep:
            with self.assertRaises(Waited):
                lane.run()
        output = self.root / 'output'
        self.assertEqual(sleep.call_args.args, (60,))
        self.assertEqual(sorted(p.name for p in output.iterdir() if p.name.startswith('verdict-') or p.is_dir()), [])
        self.assertEqual(json.loads((output / f'not-dispatched-{row[0]}.json').read_text()),
                         {'reason': 'Codex login (codex_auth) last renewed 7.6 days ago; limit 7 days'})
        log = [json.loads(line) for line in (output / 'driver-codex.log').read_text().splitlines()]
        self.assertEqual([(e['event'], e.get('cell'), e.get('rc')) for e in log], [('run', row[0], 3)])
        self.assertEqual(self.copies(), [])
        self.urlopen.assert_not_called()

    def test_an_assessment_takes_a_fresh_copy_under_the_same_guard(self):
        """A regrade can come long after its cell's copy: the assessors' snapshot copies the login again, or holds."""
        for name in ('claude.json', 'codex.json'):
            (self.auth / name).write_text('earlier copy')
        old = codex_auth_file(self.root / 'old.json', days=7.5)
        self.assertEqual(run_cell.assessment_snapshot(self.runtime(str(old))),
                         (None, 'Codex login (codex_auth) last renewed 7.5 days ago; limit 7 days'))
        self.assertEqual([(self.auth / n).read_text() for n in ('claude.json', 'codex.json')], ['earlier copy'] * 2)
        fresh, blocked = run_cell.assessment_snapshot(self.runtime(str(self.named)))
        self.assertIsNone(blocked)
        self.assertEqual((self.auth / 'codex.json').read_bytes(), self.named.read_bytes())
        self.assertEqual(fresh['codex_account'], run_cell.base.fingerprint('named-account-id'))


CODEX_CACHES = {  # Codex's own caches as a real 0.164.0 session leaves them (Part D's evidence), run_cell.PRUNED's roots
    'home/.codex/.tmp/plugins/plugins/github/.codex-plugin/plugin.json': '{"name": "github"}',
    'home/.codex/.tmp/plugins.sync.lock': '',
    'home/.codex/plugins/cache/openai-curated-remote/github/1.0.0/skills/gh/SKILL.md': '# gh\n',
    'home/.codex/plugins/.remote-plugin-install-staging/pages/plugin.json': '{}'}
CODEX_KEPT = {  # what a Codex cell's HOME holds besides them; none of it is pruned
    f'home/.codex/{instructions.PROJECTION}/.codex-plugin/plugin.json': '{"name": "devlyn"}\n',
    'home/.codex/sessions/2026/11/11/rollout-1.jsonl': '{}\n', 'home/.codex/state_5.sqlite': 'sqlite',
    'home/.codex/skills/.system/imagegen/SKILL.md': '# imagegen\n', 'home/.codex/.tmpfile': 'not the .tmp root',
    'home/.codex/plugins/cache/openai-curated-remote-other/x.json': '{}'}


SELECTED = dict(kind='anchor', path='cell/work', changed=['cell/work'], duplicates=[], candidates=[],
                rule='changed-product')  # locate.locate's selection, as the fake writes it
SCOPE = (['add_one.py', 'notes.txt'], ['notes.txt'])  # check.scope's (changed, scope violations)


def write_codex_home(out):
    for path, text in (CODEX_CACHES | CODEX_KEPT).items():
        (out / path).parent.mkdir(parents=True, exist_ok=True)
        (out / path).write_text(text)
    (out / 'home/.codex/.tmp/plugins/current').symlink_to('plugins')  # a link is counted, never followed


def tree_files(out):
    return sorted(str(p.relative_to(out)) for p in out.rglob('*') if p.is_symlink() or not p.is_dir())


def pruned_roots():
    """pruned.json's roots for write_codex_home's caches: files (a symlink counted, not followed), bytes, symlinks."""
    sizes = {root: sum(len(text) for path, text in CODEX_CACHES.items() if path.startswith(root + '/'))
             for root in run_cell.PRUNED}
    return {run_cell.PRUNED[0]: dict(files=3, bytes=sizes[run_cell.PRUNED[0]] + len('plugins'),
                                     symlinks={'home/.codex/.tmp/plugins/current': 'plugins'}),
            run_cell.PRUNED[1]: dict(files=1, bytes=sizes[run_cell.PRUNED[1]], symlinks={}),
            run_cell.PRUNED[2]: dict(files=1, bytes=sizes[run_cell.PRUNED[2]], symlinks={})}


class RunFlow(unittest.TestCase):
    def run_cell(self, root, *, task='D3', arm='B', config='claude', stderr='', stdout='', teardown='CLEAN',
                 container=None, violations=(), caches=False, assessed=None, snapshot=None, expected=None,
                 owner_status='EXITED_0', execution=(), located=None, ran=None, token_left=5000, identity='MATCH',
                 patched=None):
        """run_cell.run with every outside effect faked. caches: the cell's HOME holds Codex's caches; assessed: the
        assessors' side effect; snapshot: the cell's own credential read (preflight is then the real one); expected:
        the account the driver's ready() approved (default the dispatching venue's); execution: quota.py's execution
        faults; located: locate.locate's side effect (default: it writes snapshot/ and snapshot.json); ran: cell.run's
        side effect in place of its record; token_left: seconds left on the made-up Claude login copy preflight left
        in the auth folder; identity: the owner's model identity status; patched: further patchers by name, started
        over the defaults (a name of the defaults replaces that one)."""
        output = root / 'output'
        output.mkdir()
        runtime = dict(output=str(output), auth=str(root / 'auth'), control=str(root / 'control'), image='image',
                       models_cache=str(root / 'models'), scratch=str(root / 'scratch'),
                       check_lock=str(root / 'check.lock'))
        (root / 'auth').mkdir()
        (root / 'auth/claude.json').write_text(json.dumps({'claudeAiOauth': {
            'expiresAt': (time.time() + token_left) * 1000, 'accessToken': 'fake'}}))
        (root / 'models').write_text('models')
        (root / 'control.manifest.json').write_text(json.dumps({'packages': {
            package: {'tree_sha256': f'{package}-tree'} for package in PACKAGES}}))
        seal = {'forms': {'claude': {}, 'codex': {}}, 'qualification': {'status': 'PASS'}}
        (root / 'instructions.seal.json').write_text(json.dumps(seal))
        runtime_path = root / 'runtime.json'
        runtime_path.write_text(json.dumps(runtime))

        def prepared(_runtime, name, task_, arm_, config_):
            out = output / name
            (out / 'home/.claude').mkdir(parents=True)
            (out / 'home/.codex').mkdir()
            (out / 'run').mkdir()
            for path in ('prompt.txt', 'baseline.json', 'home/.claude/settings.json', 'home/.codex/config.toml'):
                (out / path).write_text('{}')
            (out / 'plan.json').write_text(json.dumps(dict(name=name, task=task_, arm=arm_, config=config_)))
            (out / 'run/stderr').write_text(stderr)
            (out / 'run/stdout').write_text(stdout)
            if caches:
                write_codex_home(out)
            return out
        owner = dict(owner_status=owner_status, seconds=1, teardown=teardown, teardown_error='survived',
                     identity={'status': identity}, container=container or {'oom_killed': False, 'exit_code': 0})
        venue = dict(account=['dispatch', 'org'], token_seconds_left=5000, codex_account='codexaccount')
        checks = dict(product_check_pass=True, oracle={}, scope_violations=[], adjudication_needed=False)
        held = []

        def locked_check(*_):
            with open(runtime['check_lock'], 'a') as probe:
                try:
                    fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    held.append(True)
            return checks
        def locate(out):
            (out / 'snapshot').mkdir()
            (out / 'snapshot.json').write_text(json.dumps(SELECTED))
            return SELECTED
        patches = dict(instructions=mock.patch.object(run_cell.instructions, 'check', return_value=list(violations)),
                       locate=mock.patch.object(run_cell.locate, 'locate', side_effect=located or locate),
                       check=mock.patch.object(run_cell.check, 'check', side_effect=locked_check),
                       scope=mock.patch.object(run_cell.check, 'scope', return_value=SCOPE),
                       ran=mock.patch.object(run_cell.cell_run, 'run', return_value=owner, side_effect=ran),
                       assess=mock.patch.object(run_cell.assess, 'assess', return_value=[], side_effect=assessed),
                       limits=mock.patch.object(run_cell, 'claude_limits', side_effect=AssertionError('window read')))
        if snapshot is None:
            patches['preflight'] = mock.patch.object(run_cell, 'preflight', return_value=(venue, None))
        else:
            patches['preflight'] = mock.patch.object(run_cell, 'snapshot_auth', return_value=(snapshot, None))
            patches['disk'] = mock.patch.object(run_cell.shutil, 'disk_usage',
                                                return_value=mock.Mock(free=run_cell.HEADROOM_BYTES))
        patches.update(patched or {})
        with mock.patch.object(run_cell, 'image_identity', return_value=True), \
                mock.patch.object(run_cell, 'control_unchanged', return_value=True), \
                mock.patch.object(run_cell.prepare, 'prepare', side_effect=prepared), \
                mock.patch.object(run_cell.subprocess, 'check_output', return_value='commit'), \
                mock.patch.object(run_cell, 'seal_after_teardown', return_value=('seal', [])), \
                mock.patch.object(run_cell.usage, 'record',
                                  return_value=dict(completeness='COMPLETE', input_tokens=1, output_tokens=1)), \
                mock.patch.object(run_cell.quota, 'classify', return_value={'execution': list(execution)}), \
                mock.patch.object(run_cell, 'harness_unchanged', return_value=True), \
                mock.patch.object(run_cell, 'assessment_snapshot', return_value=(dict(account=['a', 'o']), None)):
            mocks = {name: patch.start() for name, patch in patches.items()}
            try:
                code = run_cell.run(runtime_path, 'cell-1', task, arm, config,
                                    expected_account=expected or venue['account'])
            finally:
                mock.patch.stopall()
        path = output / 'verdict-cell-1.json'
        verdict = json.loads(path.read_text()) if path.is_file() else None
        return code, verdict, mocks, output / 'cell-1', held

    def assert_not_graded(self, mocks, *, evidence=False):
        """No assertion, check or assessor ran; the graded tree and scope (locate, check.scope) only with evidence."""
        for name in ('instructions', 'check', 'assess', *(() if evidence else ('locate', 'scope'))):
            mocks[name].assert_not_called()
        if evidence:
            mocks['locate'].assert_called_once()
            mocks['scope'].assert_called_once()

    def test_launch_fault_stops_without_checks_or_assessors(self):
        with tempfile.TemporaryDirectory() as temp:
            code, verdict, mocks, _, _ = self.run_cell(Path(temp), stderr=SHAPES['status_lines']['refused'] + '\n')
            self.assertEqual((code, verdict['status']), (2, 'STOP'))
            self.assertEqual(verdict['reason'],
                             'launch fault: run-argument-unsupported {"engine":"codex","argument":"-C"}')
            self.assert_not_graded(mocks)
            self.assertIs(verdict['owner_ran'], False)  # H2: no owner ran, so no tree or scope is kept
            self.assertFalse({'snapshot', 'scope_violations', 'changed', 'scope_error'} & set(verdict))

    def test_memory_kill_stops_without_checks_or_assessors(self):
        with tempfile.TemporaryDirectory() as temp:
            code, verdict, mocks, out, _ = self.run_cell(Path(temp), arm='C-K3', container={'oom_killed': True,
                                                                                       'exit_code': 137})
            self.assertEqual(verdict['reason'], 'memory kill: OOMKilled=True exit_code=137 owner EXITED_0')
            self.assert_not_graded(mocks, evidence=True)
            self.assert_stop_evidence(verdict, out, mocks)

    def assert_stop_evidence(self, verdict, out, mocks):
        """H2: a STOP whose owner ran and whose teardown is proved keeps its graded tree and its scope (check.scope, no
        container), in the verdict and in a checks.json of the scope fields alone."""
        self.assertEqual((verdict['status'], verdict['owner_ran']), ('STOP', True))
        self.assertEqual((verdict['snapshot'], verdict['changed'], verdict['scope_violations']),
                         (SELECTED, SCOPE[0], SCOPE[1]))
        self.assertNotIn('scope_error', verdict)
        self.assertEqual(json.loads((out / 'checks.json').read_text()),
                         dict(scope_violations=SCOPE[1], changed=SCOPE[0]))
        self.assertEqual(json.loads((out / 'snapshot.json').read_text()), SELECTED)
        mocks['scope'].assert_called_once_with(out)

    def test_a_shared_account_fault_keeps_its_tree_and_scope(self):
        """H2, allowed: a shared account fault (a quota fault among them) is redispatched, so its tree and scope are
        kept before its STOP is written."""
        for kind in ('quota', 'authentication'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp:
                code, verdict, mocks, out, _ = self.run_cell(Path(temp), config='codex', owner_status='EXITED_NONZERO',
                                                             execution=[{'kind': kind}])
                self.assertEqual((code, verdict['reason']), (2, f'shared account fault during execution: {kind}'))
                self.assert_not_graded(mocks, evidence=True)
                self.assert_stop_evidence(verdict, out, mocks)

    def test_a_tree_locate_cannot_choose_leaves_scope_null_and_no_snapshot(self):
        """H2, violating: locate refuses (two differing trees, or a copy that failed part way): scope_violations is
        null with the reason, the verdict has no snapshot and a partial copy is moved out of the graders' way."""
        def refused(out):
            (out / 'snapshot').mkdir()
            raise run_cell.locate.LocatorError('more than one changed product tree: cell/work, tmp/x')
        with tempfile.TemporaryDirectory() as temp:
            code, verdict, mocks, out, _ = self.run_cell(Path(temp), arm='C-K3', located=refused,
                                                         container={'oom_killed': True, 'exit_code': 137})
            self.assertEqual((code, verdict['status'], verdict['owner_ran']), (2, 'STOP', True))
            self.assertEqual((verdict['scope_violations'], verdict['scope_error']),
                             (None, 'more than one changed product tree: cell/work, tmp/x'))
            self.assertFalse({'snapshot', 'changed'} & set(verdict))
            self.assertEqual(((out / 'snapshot').exists(), (out / 'snapshot.partial').is_dir(),
                              (out / 'checks.json').exists()), (False, True, False))
            mocks['scope'].assert_not_called()

    def test_every_stop_whose_owner_ran_keeps_its_tree_and_scope(self):
        """Re-check MEDIUM 3 (DESIGN "Attempts"), allowed: once its teardown is proved, every STOP whose owner ran keeps
        its graded tree and scope result, the STOPs the driver latches included. An evaluator STOP keeps the tree
        locate already chose (locate runs once); an assessor STOP keeps the full checks.json and records the scope it
        holds, with no scope-only rewrite."""
        def owner_then_failure(out, _runtime):
            (out / 'run/result.json').write_text(json.dumps(dict(owner_status='EXITED_0', teardown='CLEAN')))
            raise OSError(5, 'Input/output error')
        cases = {'harness changed': lambda: dict(patched={'harness': mock.patch.object(
                     run_cell, 'harness_unchanged', return_value=False)}),
                 'model identity mismatch': lambda: dict(identity='MISMATCH'),
                 'instruction assertion: status-line: x': lambda: dict(violations=['status-line: x']),
                 'evidence collection failed: home/x: unreadable': lambda: dict(patched={'seal': mock.patch.object(
                     run_cell, 'seal_after_teardown', return_value=(None, ['home/x: unreadable']))}),
                 'cell setup failed: OSError: [Errno 5] Input/output error': lambda: dict(ran=owner_then_failure),
                 'evaluator produced no verdict: check container survived teardown': lambda: dict(patched={
                     'check': mock.patch.object(run_cell.check, 'check',
                                                side_effect=run_cell.check.NoVerdict('check container survived teardown'))})}
        for reason, options in cases.items():
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as temp:
                code, verdict, mocks, out, _ = self.run_cell(Path(temp), **options())
                self.assertEqual((code, verdict['reason']), (2, reason))
                self.assert_stop_evidence(verdict, out, mocks)
                mocks['locate'].assert_called_once()
                mocks['assess'].assert_not_called()
        with tempfile.TemporaryDirectory() as temp:
            code, verdict, mocks, out, _ = self.run_cell(Path(temp), assessed=RuntimeError('seat timed out'))
            self.assertEqual((code, verdict['reason'], verdict['scope_violations']),
                             (2, 'assessment failed: seat timed out', []))
            self.assertEqual(verdict['snapshot'], SELECTED)
            self.assertNotIn('changed', verdict)
            mocks['scope'].assert_not_called()

    def test_a_stop_whose_teardown_is_not_proved_keeps_what_it_has_and_says_so(self):
        """Re-check MEDIUM 3, violating: a teardown that failed proves nothing, so no tree is chosen (locate never
        runs): scope_violations null and scope_error says why; driver.py's recovery of a Docker loss, once it has
        proved the teardown, then takes the tree and scope and drops that scope_error. Evidence that cannot be read is
        said the same way, and the STOP is still written."""
        with tempfile.TemporaryDirectory() as temp:
            code, verdict, mocks, out, _ = self.run_cell(Path(temp), teardown='FAILED')
            self.assertEqual((code, verdict['reason'], verdict['owner_ran']), (2, 'teardown failed: survived', True))
            self.assertEqual((verdict['scope_violations'], verdict['scope_error']),
                             (None, 'not taken: the teardown is not proved'))
            self.assertNotIn('snapshot', verdict)
            self.assert_not_graded(mocks)

            def chosen(out):
                (out / 'snapshot').mkdir()
                (out / 'snapshot.json').write_text(json.dumps(SELECTED))
                return SELECTED
            with mock.patch.object(run_cell.locate, 'locate', side_effect=chosen), \
                    mock.patch.object(run_cell.check, 'scope', return_value=SCOPE) as scope:
                self.assert_stop_evidence(run_cell.stop_evidence(out, verdict), out, dict(scope=scope))
        with tempfile.TemporaryDirectory() as temp:
            code, verdict, mocks, out, _ = self.run_cell(Path(temp), identity='MISMATCH',
                                                         located=OSError(13, 'Permission denied'))
            self.assertEqual((code, verdict['reason']), (2, 'model identity mismatch'))
            self.assertEqual((verdict['scope_violations'], verdict['scope_error']), (None, '[Errno 13] Permission denied'))
            self.assertNotIn('snapshot', verdict)

    def test_owner_ran_on_every_verdict(self):
        """H2: false for a STOP before the cell, true for a final verdict and for a STOP after the owner ran. Rewritten
        for re-check MEDIUM 3: a STOP the driver latches (here an instruction assertion) keeps its graded tree and
        scope like any other once its teardown is proved; before, it kept neither."""
        with tempfile.TemporaryDirectory() as temp:
            code, verdict, _, out, _ = self.run_cell(Path(temp))
            self.assertEqual((code, verdict['status'], verdict['owner_ran']), (0, 'COMPLETE', True))
        with tempfile.TemporaryDirectory() as temp:
            code, verdict, mocks, out, _ = self.run_cell(Path(temp), violations=['status-line: x'])
            self.assertEqual((code, verdict['owner_ran']), (2, True))
            self.assert_stop_evidence(verdict, out, mocks)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'output').mkdir()
            runtime = root / 'runtime.json'
            runtime.write_text(json.dumps(dict(output=str(root / 'output'), control=str(root / 'control'))))
            verdict_path = root / 'output/verdict-cell-1.json'
            self.assertEqual(run_cell.run(runtime, 'cell-1', 'D3', 'C-K3', 'claude'), 2)
            self.assertEqual({k: v for k, v in json.loads(verdict_path.read_text()).items() if k != 'cell'},
                             dict(status='STOP', owner_ran=False, reason='instruction assertion: seal missing'))
            verdict_path.unlink()
            (root / 'instructions.seal.json').write_text(json.dumps({'forms': {'claude': {}, 'codex': {}}}))
            with mock.patch.object(run_cell, 'image_identity', return_value=True), \
                    mock.patch.object(run_cell, 'preflight', return_value=(dict(account=['a', 'o']), None)), \
                    mock.patch.object(run_cell, 'control_unchanged', return_value=False):
                self.assertEqual(run_cell.run(runtime, 'cell-1', 'D3', 'C-K3', 'claude'), 2)
            self.assertEqual({k: v for k, v in json.loads(verdict_path.read_text()).items() if k != 'cell'},
                             dict(status='STOP', owner_ran=False, reason='control changed'))

    def test_a_container_that_could_not_be_set_up_is_a_stop(self):
        """H4, DESIGN Faults: cell.run raised (it removed what it had made): a STOP with its teardown, no owner."""
        def failed(out, _runtime):
            (out / 'run/result.json').write_text(json.dumps(dict(owner_status=None, teardown='CLEAN')))
            raise subprocess.CalledProcessError(1, ['docker', 'create'])
        with tempfile.TemporaryDirectory() as temp:
            code, verdict, mocks, _, _ = self.run_cell(Path(temp), ran=failed)
            self.assertEqual((code, verdict['status'], verdict['owner_ran'], verdict['teardown']),
                             (2, 'STOP', False, 'CLEAN'))
            self.assertTrue(verdict['reason'].startswith('cell setup failed: CalledProcessError: '), verdict)
            self.assert_not_graded(mocks)
            driver = load('driver')  # neither regraded nor redispatched: the driver latches both lanes on it
            self.assertFalse(verdict['reason'].startswith(driver.REGRADE + driver.ONCE + (driver.LAUNCH_FAULT,)))

    def test_a_created_container_without_its_record_is_taken_to_have_run(self):
        """Third re-check (MEDIUM): cell.run raised and left no result.json. Violating (before): owner_ran was false
        whatever had happened. Now a container that was created (run/started.json) is taken to have run its owner,
        so its evidence is required (scope_error says the teardown is not proved); allowed: nothing was created, so
        no owner ran."""
        def created(out, _runtime):
            (out / 'run/started.json').write_text('{}')
            raise OSError(28, 'No space left on device')

        def not_created(_out, _runtime):
            raise OSError(28, 'No space left on device')
        with tempfile.TemporaryDirectory() as temp:
            code, verdict, mocks, _, _ = self.run_cell(Path(temp), ran=created)
            self.assertEqual((code, verdict['status'], verdict['owner_ran'], verdict['scope_violations']),
                             (2, 'STOP', True, None))
            self.assertIn('teardown is not proved', verdict['scope_error'])
        with tempfile.TemporaryDirectory() as temp:
            code, verdict, mocks, _, _ = self.run_cell(Path(temp), ran=not_created)
            self.assertEqual((code, verdict['status'], verdict['owner_ran']), (2, 'STOP', False))
            self.assertNotIn('scope_error', verdict)

    def test_the_token_life_is_read_again_after_prepare(self):
        """CG4 (DESIGN "Token guard"): prepare has no time limit, so the Claude login copy the cell would mount is read
        again before the owner starts. Violating: less than the watchdog plus 300 s left: nothing starts, the prepared
        folder is gone, not-dispatched says why, exit 3 (the driver's retry after 60 s), no verdict. Allowed: enough
        left starts the owner."""
        self.assertEqual(run_cell.START_TOKEN_SECONDS, 3000)
        with tempfile.TemporaryDirectory() as temp:
            code, verdict, mocks, out, _ = self.run_cell(Path(temp), token_left=2940)
            self.assertEqual((code, verdict, out.exists()), (3, None, False))
            mocks['ran'].assert_not_called()
            reason = json.loads((Path(temp) / 'output/not-dispatched-cell-1.json').read_text())['reason']
            self.assertRegex(reason, r'^Claude login copy expires in 29\d\ds after prepare, below 3000s$')
        with tempfile.TemporaryDirectory() as temp:
            code, verdict, mocks, out, _ = self.run_cell(Path(temp), token_left=3060)
            self.assertEqual((code, verdict['status']), (0, 'COMPLETE'))
            mocks['ran'].assert_called_once()
            self.assertFalse((Path(temp) / 'output/not-dispatched-cell-1.json').exists())

    def test_an_owner_at_the_watchdog_is_never_complete(self):
        """M6: HANG_TIMEOUT reads PRODUCT_INCOMPLETE though every check and assessor passes (they still run), and so
        does its regrade; an owner that exited reads what its checks and assessors say."""
        for status, expected in (('HANG_TIMEOUT', 'PRODUCT_INCOMPLETE'), ('EXITED_0', 'COMPLETE'),
                                 ('EXITED_NONZERO', 'COMPLETE')):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as temp:
                code, verdict, mocks, _, _ = self.run_cell(Path(temp), arm='C-K3', owner_status=status)
                self.assertEqual((code, verdict['status'], verdict['product_check_pass']), (0, expected, True))
                mocks['check'].assert_called_once()
                mocks['assess'].assert_called_once()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _, verdict, _, out, _ = self.run_cell(root, arm='C-K3', owner_status='HANG_TIMEOUT',
                                                  assessed=RuntimeError('seat timed out'))
            self.assertEqual(verdict['reason'], 'assessment failed: seat timed out')
            (out / 'checks.json').write_text(json.dumps(dict(product_check_pass=True, oracle={}, scope_violations=[],
                                                             adjudication_needed=False)))
            with mock.patch.object(run_cell, 'assessment_snapshot', return_value=(dict(account=['a', 'o']), None)), \
                    mock.patch.object(run_cell.assess, 'assess', return_value=[]):
                self.assertEqual(run_cell.regrade(root / 'runtime.json', 'cell-1'), 0)
            self.assertEqual(json.loads((root / 'output/verdict-cell-1.json').read_text())['status'],
                             'PRODUCT_INCOMPLETE')

    def test_an_unproved_assessor_teardown_is_its_own_stop_and_never_regraded(self):
        """H3: violating, a seat container whose removal is unproved stops without a regrade (the driver latches it);
        allowed, any other seat failure stays an assessment failure the driver regrades."""
        driver = load('driver')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            code, verdict, _, _, _ = self.run_cell(root, assessed=run_cell.assess.TeardownUnproved(
                'cannot prove container x is gone'))
            self.assertEqual((code, verdict['reason']), (2, 'assessor teardown unproved: cannot prove container x is gone'))
            self.assertFalse(verdict['reason'].startswith(driver.REGRADE))
            with self.assertRaisesRegex(SystemExit, 'only an assessor STOP is regraded'):
                run_cell.regrade(root / 'runtime.json', 'cell-1')
        with tempfile.TemporaryDirectory() as temp:
            _, verdict, _, _, _ = self.run_cell(Path(temp), assessed=RuntimeError('seat timed out'))
            self.assertTrue(verdict['reason'].startswith(driver.REGRADE), verdict['reason'])

    def test_an_oom_flag_whose_owner_went_on_is_graded_and_recorded(self):
        for container, oom in (({'oom_killed': True, 'exit_code': 0}, True), ({'oom_killed': True, 'exit_code': 1}, True),
                               ({'oom_killed': False, 'exit_code': 137}, False),
                               ({'oom_killed': False, 'exit_code': 0}, False)):
            with self.subTest(container=container), tempfile.TemporaryDirectory() as temp:
                code, verdict, mocks, _, _ = self.run_cell(Path(temp), arm='C-K3', container=container)
                self.assertEqual((code, verdict['status'], verdict['oom_killed']), (0, 'COMPLETE', oom))
                mocks['assess'].assert_called_once()
        with tempfile.TemporaryDirectory() as temp:  # a memory kill records the flag on its STOP too
            _, verdict, _, _, _ = self.run_cell(Path(temp), arm='C-K3', container={'oom_killed': True, 'exit_code': 137})
            self.assertEqual((verdict['status'], verdict['oom_killed']), ('STOP', True))

    def test_a_teardown_failure_outranks_a_launch_fault(self):
        with tempfile.TemporaryDirectory() as temp:
            _, verdict, _, _, _ = self.run_cell(Path(temp), teardown='FAILED',
                                                stderr=SHAPES['status_lines']['refused'] + '\n')
            self.assertEqual(verdict['reason'], 'teardown failed: survived')

    def test_graded_cell_holds_the_check_lock_reads_no_window_and_seals_modules(self):
        with tempfile.TemporaryDirectory() as temp:
            code, verdict, mocks, out, held = self.run_cell(
                Path(temp), stderr=SHAPES['status_lines']['claude'] + '\n',
                stdout=json.dumps(SHAPES['claude_init']) + '\n')
            self.assertEqual((code, verdict['status']), (0, 'COMPLETE'))
            self.assertEqual(held, [True])
            self.assertFalse({key for key in verdict if key.startswith('claude_limits')})
            self.assertEqual((verdict['claude_account_before'], verdict['codex_account']),
                             (['dispatch', 'org'], 'codexaccount'))
            mocks['limits'].assert_not_called()
            args = mocks['instructions'].call_args.args
            self.assertEqual((args[0], args[1]['arm'], args[2]['qualification']['status']), (out, 'B', 'PASS'))
            seal = json.loads((out / 'seal.json').read_text())
            loaded = {name: next(f'{folder}/{name}.py' for folder in ('0266', '0265', '0256', '0233')  # load's order
                                 if (HERE.parent / folder / f'{name}.py').is_file())
                      for name in ('prepare', 'cell', 'record_usage', 'locate', 'check', 'assess', 'quota',
                                   'instructions')}  # no diagnostics: nothing in 0266 reads them
            self.assertEqual({name: entry['path'] for name, entry in seal['modules'].items()},
                             dict(loaded, run_cell0222='0222/run_cell.py'))
            self.assertEqual({name for name, path in loaded.items() if path.startswith('0266/')}, {'prepare',
                                                                                                 'instructions'})
            self.assertEqual({name for name, path in loaded.items() if path.startswith('0265/')},
                             {'cell', 'locate', 'check', 'assess', 'quota'})  # unchanged, loaded from 0265
            self.assertEqual((seal['package'], seal['package_sha256']), ('B', 'B-tree'))
            self.assertIn('0265/cell.py', seal['imported'])
            self.assertNotIn('0237/cell-init-v1.py', seal['imported'])
            self.assertEqual(seal['endpoints_sha256'], run_cell.digest(HERE / 'endpoints.json'))

    def test_smoke_is_asserted_by_seal_forms_not_inline_and_c_records_its_package(self):
        with tempfile.TemporaryDirectory() as temp:
            code, verdict, mocks, out, _ = self.run_cell(Path(temp), task='SMOKE', arm='C-K3', config='codex')
            self.assertEqual(code, 0)
            mocks['instructions'].assert_not_called()
            seal = json.loads((out / 'seal.json').read_text())
            self.assertEqual((seal['package'], seal['package_sha256']), ('K3', 'K3-tree'))
            self.assertEqual((verdict['arm'], verdict['package']), ('C', 'K3'))

    def test_assertion_failure_stops_before_checks(self):
        """Rewritten for re-check MEDIUM 3: no check or assessor runs after a failed assertion, but its graded tree is
        chosen (locate, once) for its scope result; before, locate did not run either."""
        with tempfile.TemporaryDirectory() as temp:
            code, verdict, mocks, _, _ = self.run_cell(Path(temp), violations=['status-line: B stderr has []'])
            self.assertEqual((code, verdict['reason']), (2, 'instruction assertion: status-line: B stderr has []'))
            for name in ('check', 'assess'):
                mocks[name].assert_not_called()
            mocks['locate'].assert_called_once()

    def test_arms_and_configs_guard(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = Path(temp) / 'runtime.json'
            runtime.write_text(json.dumps(dict(output=str(Path(temp) / 'output'))))
            for column, config, pattern in (('A', 'claude', "arm 'A'"), ('C-K3', 'grok', 'config claude/codex'),
                                            ('C', 'claude', 'no screen decision')):
                with self.assertRaisesRegex(ValueError, pattern):
                    run_cell.run(runtime, 'x', 'D3', column, config)
            self.assertFalse((Path(temp) / 'output').exists())

    def test_a_slot_runs_only_as_its_own_row_says(self):
        # F1b: a name of cells.tsv, screen.tsv or smoke.tsv with another task, arm column or engine is refused before
        # anything is written; a name in none of them is not a slot of 0266.
        with tempfile.TemporaryDirectory() as temp:
            runtime = Path(temp) / 'runtime.json'
            runtime.write_text(json.dumps(dict(output=str(Path(temp) / 'output'))))
            for name, task, column, config in (('c002-F10-claude-C-r1', 'F10', 'C-K1', 'claude'),
                                               ('s01-F10-claude-K1-r1', 'F10', 'C-K2', 'claude'),
                                               ('smoke-codex-C', 'SMOKE', 'B', 'codex'),
                                               ('c001-F10-claude-B-r1', 'F10', 'B', 'codex')):
                with self.subTest(name=name), self.assertRaisesRegex(ValueError, f'{name} is the slot '):
                    run_cell.run(runtime, name, task, column, config)
            self.assertFalse((Path(temp) / 'output').exists())
            self.assertEqual(run_cell.schedule_row('s01-F10-claude-K1-r1'), ('F10', 'C-K1', 'claude'))
            self.assertIsNone(run_cell.schedule_row('cell-1'))
        with tempfile.TemporaryDirectory() as temp:  # the right row passes the check (and goes on to the seal)
            root = Path(temp)
            (root / 'output').mkdir()
            runtime = root / 'runtime.json'
            runtime.write_text(json.dumps(dict(output=str(root / 'output'))))
            self.assertEqual(run_cell.run(runtime, 's01-F10-claude-K1-r1', 'F10', 'C-K1', 'claude'), 2)
            self.assertEqual(json.loads((root / 'output/verdict-s01-F10-claude-K1-r1.json').read_text())['reason'],
                             'instruction assertion: seal missing')

    def test_a_graded_cell_loses_codex_caches_only_and_records_them(self):
        """D-b, allowed: once a measured cell's verdict is written and is not a STOP, exactly run_cell.PRUNED leaves
        it, in both arms, and pruned.json records each root's files (a symlink counted, not followed), bytes and
        symlinks, marked removed. The same cell held at a STOP (violating) keeps every file."""
        expected = dict(removed=True, roots=pruned_roots())
        for arm in ('B', 'C-K1'):
            with self.subTest(arm=arm), tempfile.TemporaryDirectory() as temp, \
                    tempfile.TemporaryDirectory() as held:
                code, verdict, _, stopped, _ = self.run_cell(Path(held), arm=arm, config='codex', caches=True,
                                                             violations=['codex-home: x'])
                self.assertEqual((code, verdict['status']), (2, 'STOP'))
                before = tree_files(stopped)
                self.assertFalse((stopped / 'pruned.json').exists())
                code, verdict, _, out, _ = self.run_cell(Path(temp), arm=arm, config='codex', caches=True)
                self.assertEqual((code, verdict['status']), (0, 'COMPLETE'))
                self.assertEqual(json.loads((out / 'pruned.json').read_text()), expected)
                self.assertTrue({'snapshot.json', 'checks.json'} <= set(before))  # the STOP keeps its tree and scope
                self.assertEqual(tree_files(out), sorted(  # the fake check.check writes no checks.json
                    [p for p in before if not p.startswith(tuple(r + '/' for r in run_cell.PRUNED))
                     and p != 'checks.json'] + ['pruned.json']))
                for path, text in CODEX_KEPT.items():
                    self.assertEqual((out / path).read_text(), text)
                self.assertTrue((out / 'home/.codex/plugins/cache').is_dir())
                self.assertEqual(run_cell.prune(out), expected)  # a second call changes nothing
                self.assertEqual(json.loads((out / 'pruned.json').read_text()), expected)

    def test_a_cell_without_codex_caches_and_a_smoke_task_cell(self):
        """D-b: a Claude cell has none of the roots and gets a record with none (allowed, idempotent); a SMOKE-task
        cell keeps its caches, since seal-forms asserts SMOKE's CODEX_HOME after the verdict."""
        with tempfile.TemporaryDirectory() as temp:
            code, _, _, out, _ = self.run_cell(Path(temp), arm='C-K3', config='claude')
            empty = dict(removed=True, roots={})
            self.assertEqual((code, json.loads((out / 'pruned.json').read_text())), (0, empty))
            files = tree_files(out)
            self.assertEqual(run_cell.prune(out), empty)
            self.assertEqual(tree_files(out), files)
        with tempfile.TemporaryDirectory() as temp:
            code, _, _, out, _ = self.run_cell(Path(temp), task='SMOKE', arm='C-K3', config='codex', caches=True)
            self.assertEqual(code, 0)
            self.assertFalse((out / 'pruned.json').exists())
            self.assertTrue(all((out / path).exists() for path in CODEX_CACHES))

    def test_prune_never_follows_a_link_and_records_what_it_could_not_remove(self):
        """D-b, violating: a root reached through a symlinked folder (the session controls its HOME) is left with an
        error, and so is a root that cannot be removed; the files outside the cell stay and nothing raises."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            outside = root / 'outside/cache/openai-curated-remote'
            outside.mkdir(parents=True)
            (outside / 'keep.txt').write_text('not the cell\'s')
            out = root / 'cell-1'
            (out / 'home/.codex/.tmp/locked').mkdir(parents=True)
            (out / 'home/.codex/plugins').symlink_to(root / 'outside')
            (out / 'home/.codex/.tmp/locked/file').write_text('x')
            (out / 'home/.codex/.tmp/locked').chmod(0o500)
            try:
                with mock.patch('sys.stderr', io.StringIO()) as printed:
                    record = run_cell.prune(out)
            finally:
                (out / 'home/.codex/.tmp/locked').chmod(0o700)
            roots = record['roots']
            self.assertEqual(roots[run_cell.PRUNED[1]], {'error': 'not removed: reached through a symbolic link'})
            self.assertEqual(roots[run_cell.PRUNED[0]]['files'], 1)
            self.assertTrue(roots[run_cell.PRUNED[0]]['error'].startswith('not removed: '))
            self.assertEqual(sorted(roots), sorted(run_cell.PRUNED[:2]))
            self.assertIs(record['removed'], False)  # a root left in place keeps the mark visible
            self.assertTrue((outside / 'keep.txt').is_file())
            self.assertEqual(len(printed.getvalue().splitlines()), 2)
            self.assertEqual(json.loads((out / 'pruned.json').read_text()), record)

    def test_pruned_json_is_written_before_any_removal_and_marked_after(self):
        """M5, allowed: pruned.json lists every root (files, bytes, symlinks with their targets) marked removed: false
        before the first removal, and is replaced atomically with removed: true once all are gone. Violating: a removal
        cut short leaves the false mark and the list, and a later call keeps them as they are."""
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'cell-1'
            write_codex_home(out)
            seen, replaced = [], []
            real_rmtree, real_replace = shutil.rmtree, run_cell.os.replace

            def rmtree(path, *args, **kwargs):
                seen.append(json.loads((out / 'pruned.json').read_text()))
                return real_rmtree(path, *args, **kwargs)

            def replace(source, target):
                replaced.append((Path(source).parent, Path(target)))
                return real_replace(source, target)
            with mock.patch.object(run_cell.shutil, 'rmtree', side_effect=rmtree), \
                    mock.patch.object(run_cell.os, 'replace', side_effect=replace):
                record = run_cell.prune(out)
            self.assertEqual(seen, [dict(removed=False, roots=pruned_roots())] * len(run_cell.PRUNED))
            self.assertEqual(record, dict(removed=True, roots=pruned_roots()))
            self.assertEqual(json.loads((out / 'pruned.json').read_text()), record)
            self.assertEqual(replaced, [(out, out / 'pruned.json')] * 2)
            self.assertEqual([p.name for p in out.iterdir() if p.name.startswith('.')], [])
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'cell-1'
            write_codex_home(out)
            with mock.patch.object(run_cell.shutil, 'rmtree', side_effect=KeyboardInterrupt), \
                    self.assertRaises(KeyboardInterrupt):
                run_cell.prune(out)
            left = dict(removed=False, roots=pruned_roots())
            self.assertEqual(json.loads((out / 'pruned.json').read_text()), left)
            self.assertEqual(run_cell.prune(out), left)
            self.assertTrue(all((out / path).exists() for path in CODEX_CACHES))

    def test_assessor_stop_keeps_the_caches_and_its_regrade_prunes_and_reads_a_pruned_cell(self):
        """D-b: an assessor STOP is not pruned; its regrade grades from the preserved evidence and then prunes, and a
        regrade of a cell that was already pruned grades the same."""
        for pruned_first in (False, True):
            with self.subTest(pruned_first=pruned_first), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                code, verdict, _, out, _ = self.run_cell(root, arm='B', config='codex', caches=True,
                                                         assessed=RuntimeError('seat timed out'))
                self.assertEqual((code, verdict['reason']), (2, 'assessment failed: seat timed out'))
                self.assertTrue(all((out / path).exists() for path in CODEX_CACHES))
                (out / 'checks.json').write_text(json.dumps(dict(product_check_pass=True, oracle={},
                                                                 scope_violations=[], adjudication_needed=False)))
                if pruned_first:
                    run_cell.prune(out)
                recorded = (out / 'pruned.json').read_text() if pruned_first else None
                with mock.patch.object(run_cell, 'assessment_snapshot', return_value=(dict(account=['a', 'o']), None)), \
                        mock.patch.object(run_cell.assess, 'assess', return_value=[]) as assessed:
                    code = run_cell.regrade(root / 'runtime.json', 'cell-1')
                assessed.assert_called_once()
                verdict = json.loads((root / 'output/verdict-cell-1.json').read_text())
                self.assertEqual((code, verdict['status'], verdict['regraded']['after']), (0, 'COMPLETE', 'stop-1'))
                self.assertFalse([path for path in CODEX_CACHES if (out / path).exists()])
                self.assertEqual(json.loads((out / 'pruned.json').read_text()), dict(removed=True, roots=pruned_roots()))
                if recorded:
                    self.assertEqual((out / 'pruned.json').read_text(), recorded)

    def test_a_login_changed_after_ready_is_not_dispatched_and_a_dispatch_records_its_account(self):
        """D-c: the cell's own credential read finds another account than the driver's ready() approved (the owner's
        app switched the login in between): no verdict, nothing prepared, exit 3 with the reason on file, so the
        driver's next ready() approves the new login. With the approved account the verdict records it."""
        with tempfile.TemporaryDirectory() as temp:
            code, verdict, _, out, _ = self.run_cell(Path(temp), snapshot=dict(account=['other', 'org'],
                                                                             token_seconds_left=5000,
                                                                             codex_account='codexaccount'))
            self.assertEqual((code, verdict), (3, None))
            self.assertFalse(out.exists())
            self.assertEqual(json.loads((Path(temp) / 'output/not-dispatched-cell-1.json').read_text()),
                             {'reason': 'account changed after reserve check'})
        with tempfile.TemporaryDirectory() as temp:
            code, verdict, _, _, _ = self.run_cell(Path(temp), snapshot=dict(account=['dispatch', 'org'],
                                                                           token_seconds_left=5000,
                                                                           codex_account='codexaccount'))
            self.assertEqual((code, verdict['claude_account_before'], verdict['assessor_account']),
                             (0, ['dispatch', 'org'], ['a', 'o']))

    def test_the_verdict_records_the_codex_fingerprint_and_no_account_id_or_token(self):
        """O15: the dispatching snapshot's Codex account, by fingerprint, beside the Claude account; neither the
        account id nor any token of either login reaches the verdict or the cell's seal."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            named = codex_auth_file(root / 'registered/auth.json', account='named-account-id')
            (root / 'snapshot').mkdir()
            stack, _ = fake_logins(root)
            with stack:
                venue, blocked = run_cell.snapshot_auth(dict(auth=str(root / 'snapshot'), codex_auth=str(named)))
            self.assertIsNone(blocked)
            code, verdict, _, out, _ = self.run_cell(root, arm='C-K3', config='codex', snapshot=venue,
                                                     expected=venue['account'])
            self.assertEqual((code, verdict['claude_account_before'], verdict['codex_account']),
                             (0, venue['account'], run_cell.base.fingerprint('named-account-id')))
            for text in ((root / 'output/verdict-cell-1.json').read_text(), (out / 'seal.json').read_text()):
                self.assertFalse([value for value in ('named-account-id', *SECRETS) if value in text])
