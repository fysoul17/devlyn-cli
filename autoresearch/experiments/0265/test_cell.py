"""Offline tests of 0265's arms, cell, launch probe, per-cell assertions and assessors. Fakes stand in for Docker and
credentials; Codex's model input is real 0.164.0 output (fixtures/cell/prompt-input-*.json)."""
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
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import threading
import time
import tomllib
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location('test_0265_cell_' + name, HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


prepare, cell, run_cell, instructions, assess, strict = (
    load(name) for name in ('prepare', 'cell', 'run_cell', 'instructions', 'assess', 'strict_config_check'))
SHAPES = json.loads((HERE / 'fixtures/cell/shapes.json').read_text())
RELEASE = HERE / 'fixtures/cell/release.json'
OWNER = {engine: prepare.TASKS['routes'][engine]['owner'] for engine in prepare.CONFIGS}
INPUT = {name: json.loads((HERE / f'fixtures/cell/prompt-input-{name}.json').read_text())
         for name in ('A', 'B', 'control')}
TEXT = INPUT['B'][2]['content'][0]['text']  # devlyn run 4.3.30's developer_instructions, where Codex 0.164.0 puts it
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


def a_request():
    return request(INPUT['A'])


def b_request(text=TEXT):
    body = request(INPUT['B'])
    body['input'][2]['content'][0]['text'] = text
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


def moved_text():
    body = b_request()
    body['input'].append({'type': 'message', 'role': 'user', 'content': [body['input'][2]['content'].pop(0)]})
    return body


def b_without_devlyn_skills():
    body = b_request()
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


def make_cell(root, engine, arm):
    """A SMOKE-shaped cell that passes every assertion for its arm."""
    out = root / f'smoke-{engine}-{arm}'
    (out / 'run').mkdir(parents=True)
    (out / 'home/.codex').mkdir(parents=True)
    (out / 'home/.codex/models_cache.json').write_text('{}')
    (out / 'run/stderr').write_text('an unrelated engine warning\n' +
                                    (SHAPES['status_lines'][engine] + '\n' if arm == 'B' else ''))
    (out / 'run/result.json').write_text(json.dumps({'identity': {'status': 'MATCH', 'owner': 'MATCH'}}))
    if arm == 'B':
        release = out / 'home/.devlyn/cli/releases/devlyn-cli/4.3.30'
        release.mkdir(parents=True)
        shutil.copyfile(RELEASE, release / 'release.json')
    if engine == 'claude':
        init = copy.deepcopy(SHAPES['claude_init'])
        if arm == 'B':
            init['plugins'].append(SHAPES['devlyn_plugin'])
        (out / 'run/stdout').write_text(json.dumps(init) + '\n' + json.dumps({'type': 'result', 'result': 'done'}) + '\n')
    else:
        (out / 'home/.codex/config.toml').write_text(prepare.codex_config(OWNER['codex']))
        (out / 'run/stdout').write_text(json.dumps({'type': 'thread.started', 'thread_id': 'owner'}) + '\n')
        write_request(out, b_request() if arm == 'B' else a_request(), later=a_request())
        for name in ('.tmp/plugins/plugins/x/.codex-plugin/plugin.json', '.tmp/plugins.sha',  # Codex's own caches (O10)
                     'plugins/cache/openai-curated-remote/github/1.0.0/.codex-plugin/plugin.json'):
            (out / 'home/.codex' / name).parent.mkdir(parents=True, exist_ok=True)
            (out / 'home/.codex' / name).write_text('{}')
        if arm == 'B':
            folder = out / 'home/.codex' / instructions.PROJECTION
            (folder / '.codex-plugin').mkdir(parents=True)
            (folder / '.codex-plugin/plugin.json').write_text('{"name": "devlyn"}\n')
            (folder / '.devlyn-harness-projection.json').write_text('{"schemaVersion": 1}\n')
    plan = dict(name=out.name, task='SMOKE', arm=arm, config=engine)
    (out / 'plan.json').write_text(json.dumps(plan))
    return out, plan


def probe_seal(root):
    """The launch probe's fields of a seal for the SMOKE and D3 trees, as `seal` writes them."""
    launch = {}
    for engine in prepare.CONFIGS:
        out, _ = make_cell(Path(tempfile.mkdtemp(dir=root)), engine, 'B')
        entry = dict(status_line=SHAPES['status_lines'][engine], release_digest=instructions.RELEASE_DIGEST)
        if engine == 'claude':
            entry['plugin_dir'] = SHAPES['devlyn_plugin']['path']
        else:
            entry.update(projection=dict(path=instructions.PROJECTION, files=instructions.projection(out)),
                         model_input={arm: instructions.model_input(body, TEXT)
                                      for arm, body in (('A', a_request()), ('B', b_request()))})
        launch[engine] = {tree: copy.deepcopy(entry) for tree in ('SMOKE', 'D3')}
    return dict(launch=launch, devlyn_skills=DEVLYN_SKILLS)


def pending_seal(root):
    return dict(package=dict(version='4.3.30', release_digest=instructions.RELEASE_DIGEST), cli=instructions.CLI,
                session_text=TEXT, **probe_seal(root), forms={}, qualification=dict(status='PENDING'))


def sealed(root):
    seal = pending_seal(root)
    seal['forms'] = {engine: instructions.observed_form(make_cell(root / 'seal', engine, 'B')[0], engine, seal)
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


FOREIGN = {'name': 'other', 'path': '/home/participant/.claude/plugins/other', 'source': 'other@market'}
MUTATIONS = {
    'no_status': lambda out, engine: (out / 'run/stderr').write_text('an unrelated engine warning\n'),
    'two_status': lambda out, engine: (out / 'run/stderr').write_text(
        (SHAPES['status_lines'][engine] + '\n') * 2),
    'other_version': lambda out, engine: edit_stderr(out, f'{engine} {instructions.CLI[engine]} ',
                                                     f'{engine} 9.9.9 '),
    'other_digest': lambda out, engine: edit_stderr(out, '@53a2f9f2', '@00000000'),
    'principles_unavailable': lambda out, engine: (out / 'run/stderr').write_text(re.sub(
        r'principles=configured:\S+', 'principles=unavailable', (out / 'run/stderr').read_text())),
    'status': lambda out, engine: (out / 'run/stderr').write_text(SHAPES['status_lines'][engine] + '\n'),
    'refused': lambda out, engine: (out / 'run/stderr').write_text(SHAPES['status_lines']['refused'] + '\n'),
    'devlyn_home': lambda out, engine: (out / 'home/.devlyn/cli').mkdir(parents=True),
    'altered_release': lambda out, engine: rewrite_release(
        out, lambda m: m['files'][0].update(sha256='0' * 64), recompute=False),
    'other_release': lambda out, engine: rewrite_release(
        out, lambda m: m['files'][0].update(sha256='0' * 64), recompute=True),
    'no_release': lambda out, engine: next((out / 'home/.devlyn').rglob('release.json')).unlink(),
    'no_plugin': lambda out, engine: edit_init(out, lambda e: e['plugins'].pop()),
    'plugin': lambda out, engine: edit_init(out, lambda e: e['plugins'].append(SHAPES['devlyn_plugin'])),
    'second_init_plugin': lambda out, engine: edit_init(
        out, lambda e: e['plugins'].append(SHAPES['devlyn_plugin']), count=2),
    'foreign_plugin_init': lambda out, engine: edit_init(out, lambda e: e['plugins'].append(FOREIGN)),
    'mcp': lambda out, engine: edit_init(out, lambda e: e.update(mcp_servers=[{'name': 'x', 'status': 'connected'}])),
    'no_init': lambda out, engine: (out / 'run/stdout').write_text(json.dumps({'type': 'result'}) + '\n'),
    'no_text': lambda out, engine: write_request(out, a_request()),
    'text_twice': lambda out, engine: write_request(out, dict(b_request(), instructions=TEXT)),
    'text': lambda out, engine: write_request(out, b_request()),
    'preamble': lambda out, engine: write_request(out, b_request(instructions.PREAMBLE + ' another version')),
    'moved_text': lambda out, engine: write_request(out, moved_text()),
    'no_devlyn_skills': lambda out, engine: write_request(out, b_without_devlyn_skills()),
    'devlyn_skills': lambda out, engine: write_request(out, with_plugin(
        a_request(), instructions.DEVLYN_ROOT, 'devlyn:devlyn-ideate')),
    'foreign_skill': lambda out, engine: write_request(out, with_plugin(
        b_request() if (out / 'home/.devlyn').exists() else a_request(), CURATED_ROOT, 'github:github')),
    'no_request': lambda out, engine: shutil.rmtree(out / 'cell/trace'),
    'foreign_plugin': lambda out, engine: (
        (out / 'home/.codex/plugins/cache/foreign/x/1.0/.codex-plugin').mkdir(parents=True),
        (out / 'home/.codex/plugins/cache/foreign/x/1.0/.codex-plugin/plugin.json').write_text('{}')),
    'devlyn_projection': lambda out, engine: (
        (out / 'home/.codex' / instructions.PROJECTION).mkdir(parents=True),
        (out / 'home/.codex' / instructions.PROJECTION / '.devlyn-harness-projection.json').write_text('{}')),
    'marketplace': lambda out, engine: (out / 'home/.codex/config.toml').write_text(
        (out / 'home/.codex/config.toml').read_text() + '[marketplaces.x]\nsource_type = "local"\nsource = "/x"\n'),
    'devlyn_marketplace': lambda out, engine: (out / 'home/.codex/config.toml').write_text(
        (out / 'home/.codex/config.toml').read_text() + f'[marketplaces.{instructions.MARKET}]\nsource_type = "local"\n'
        'source = "/x"\n'),
    'no_projection': lambda out, engine: shutil.rmtree(out / 'home/.codex/plugins'),
    'altered_projection': lambda out, engine: (
        out / 'home/.codex' / instructions.PROJECTION / '.codex-plugin/plugin.json').write_text('{"name": "x"}\n'),
    'mismatch': lambda out, engine: (out / 'run/result.json').write_text(json.dumps(
        {'identity': {'status': 'MISMATCH', 'owner': 'MISMATCH'}})),
    'unverified': lambda out, engine: (out / 'run/result.json').write_text(json.dumps(
        {'identity': {'status': 'UNVERIFIED', 'owner': 'MATCH'}})),
}
# (engine, arm, mutation, the one assertion it must fail): DESIGN Q1's violating list, both arms and engines.
CASES = [
    *[(e, 'B', m, 'status-line') for e in prepare.CONFIGS
      for m in ('no_status', 'two_status', 'other_version', 'other_digest', 'principles_unavailable')],
    *[(e, 'A', m, 'status-line') for e in prepare.CONFIGS for m in ('status', 'refused')],
    *[(e, 'A', 'devlyn_home', 'devlyn-home') for e in prepare.CONFIGS],
    *[(e, 'B', m, 'devlyn-home') for e in prepare.CONFIGS for m in ('altered_release', 'other_release', 'no_release')],
    ('claude', 'B', 'no_plugin', 'claude-init'), ('claude', 'B', 'foreign_plugin_init', 'claude-init'),
    ('claude', 'A', 'plugin', 'claude-init'), ('claude', 'A', 'second_init_plugin', 'claude-init'),
    ('claude', 'A', 'mcp', 'claude-init'), ('claude', 'B', 'mcp', 'claude-init'),
    ('claude', 'A', 'no_init', 'claude-init'), ('claude', 'B', 'no_init', 'claude-init'),
    ('codex', 'B', 'no_text', 'codex-request'), ('codex', 'B', 'text_twice', 'codex-request'),
    ('codex', 'B', 'moved_text', 'codex-request'), ('codex', 'A', 'text', 'codex-request'),
    ('codex', 'A', 'preamble', 'codex-request'), ('codex', 'A', 'no_request', 'codex-request'),
    ('codex', 'B', 'no_request', 'codex-request'), ('codex', 'B', 'no_devlyn_skills', 'codex-request'),
    ('codex', 'A', 'devlyn_skills', 'codex-request'), ('codex', 'A', 'foreign_skill', 'codex-request'),
    ('codex', 'B', 'foreign_skill', 'codex-request'),
    ('codex', 'A', 'devlyn_projection', 'codex-home'), ('codex', 'A', 'devlyn_marketplace', 'codex-home'),
    ('codex', 'B', 'no_projection', 'codex-home'), ('codex', 'B', 'altered_projection', 'codex-home'),
    *[(e, a, m, 'models') for e in prepare.CONFIGS for a in prepare.ARMS for m in ('mismatch', 'unverified')],
]


class Assertions(unittest.TestCase):
    def test_sealed_forms_pass_both_arms_and_engines(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seal = sealed(root)
            self.assertEqual(seal['forms']['claude']['plugin'], SHAPES['devlyn_plugin'])
            self.assertEqual(seal['forms']['codex']['location'],
                             dict(path='input/*/content/*/text', role='developer', type='input_text', whole=True))
            for engine in prepare.CONFIGS:
                for arm in prepare.ARMS:
                    out, plan = make_cell(root / 'cells', engine, arm)
                    self.assertEqual(instructions.check(out, plan, seal), [], (engine, arm))

    def test_each_violation_fails_exactly_its_assertion(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seal = sealed(root)
            for number, (engine, arm, mutation, expected) in enumerate(CASES):
                out, plan = make_cell(root / str(number), engine, arm)
                MUTATIONS[mutation](out, engine)
                violations = instructions.check(out, plan, seal)
                self.assertEqual({v.split(':', 1)[0] for v in violations}, {expected},
                                 (engine, arm, mutation, violations))

    def test_unsealed_forms_and_unknown_arm_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            out, plan = make_cell(Path(temp), 'claude', 'B')
            self.assertEqual(instructions.check(out, plan, pending_seal(Path(temp))), ['forms: claude form unsealed'])
            self.assertTrue(instructions.check(out, dict(plan, arm='C'), sealed(Path(temp))))

    def test_cells_are_tied_to_the_launch_probe_of_their_tree(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seal = sealed(root)
            changes = [  # (engine, arms, change to the D3 probe seal, the assertions it must fail)
                ('claude', 'B', lambda p: p.update(status_line=p['status_line'].replace('2.1.322', '2.1.321')),
                 {'status-line'}),
                ('codex', 'B', lambda p: p.update(release_digest='0' * 64), {'devlyn-home'}),
                ('codex', 'B', lambda p: p['projection']['files'].update({'skills/x/SKILL.md': '0' * 64}),
                 {'codex-home'})]
            for engine in prepare.CONFIGS:
                for arm in prepare.ARMS:  # allowed: the cell's own tree's seal
                    out, plan = make_cell(root / f'd3-{engine}-{arm}', engine, arm)
                    self.assertEqual(instructions.check(out, dict(plan, task='D3'), seal), [], (engine, arm))
                    self.assertEqual(instructions.check(out, dict(plan, task='F11'), seal),
                                     [f'launch: no launch probe seal for {engine} F11'])
            for number, (engine, arms, change, expected) in enumerate(changes):
                other = copy.deepcopy(seal)
                change(other['launch'][engine]['D3'])
                for arm in arms:
                    out, plan = make_cell(root / f'change-{number}-{arm}', engine, arm)
                    violations = instructions.check(out, dict(plan, task='D3'), other)
                    self.assertEqual({v.split(':', 1)[0] for v in violations}, expected, (number, arm, violations))
                    self.assertEqual(instructions.check(out, plan, other), [], (number, arm))  # SMOKE's seal holds

    def test_codex_own_plugin_files_pass_in_both_arms(self):
        # O10: Codex downloads its own curated plugins into CODEX_HOME in both arms; only devlyn's files are read.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seal = sealed(root)
            for arm in prepare.ARMS:
                out, plan = make_cell(root / arm, 'codex', arm)
                for mutation in ('foreign_plugin', 'marketplace'):
                    MUTATIONS[mutation](out, 'codex')
                self.assertEqual(instructions.check(out, plan, seal), [], arm)
            home = root / 'A/smoke-codex-A/home/.codex'
            self.assertEqual(instructions.devlyn_files(home), [])
            (home / '.devlyn-harness-projection.json').write_text('{}')
            self.assertEqual(instructions.devlyn_files(home), ['.devlyn-harness-projection.json'])

    def test_release_digest_port_matches_release_js(self):
        record = instructions.release_record(RELEASE)
        self.assertEqual(record, dict(version='4.3.30', digest=instructions.RELEASE_DIGEST))
        for engine in prepare.CONFIGS:
            self.assertIn(f'release 4.3.30@{instructions.RELEASE_DIGEST[:8]} (package)', SHAPES['status_lines'][engine])


class SealForms(unittest.TestCase):
    def smoke(self, root):
        output = root / 'output'
        for engine in prepare.CONFIGS:
            for arm in prepare.ARMS:
                out, _ = make_cell(output, engine, arm)
                (output / f'verdict-{out.name}.json').write_text(json.dumps(
                    {'status': 'COMPLETE', 'usage': 'COMPLETE', 'identity': {'owner_launched_sessions': []}}))
        (root / 'instructions.seal.json').write_text(json.dumps(pending_seal(root)))
        runtime = root / 'runtime.json'
        runtime.write_text(json.dumps({'output': str(output)}))
        return output, runtime

    def test_pass_seals_forms_and_qualifies(self):
        with tempfile.TemporaryDirectory() as temp:
            output, runtime = self.smoke(Path(temp))
            instructions.seal_forms(runtime)
            seal = json.loads((Path(temp) / 'instructions.seal.json').read_text())
            self.assertEqual(seal['qualification']['status'], 'PASS')
            self.assertEqual(seal['forms']['claude']['status_line'], SHAPES['status_lines']['claude'])
            self.assertEqual(seal['forms']['codex']['projection']['path'], instructions.PROJECTION)
            self.assertEqual(set(seal['forms']['codex']['projection']['files']),
                             {'.codex-plugin/plugin.json', '.devlyn-harness-projection.json'})
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
            MUTATIONS['no_status'](output / 'smoke-claude-B', 'claude')
            self.assert_refused(Path(temp), r"smoke-claude-B: looked for one stderr line matching .*found \[\]")

    def test_plugin_shape_mismatch_lists_the_init_plugins(self):
        with tempfile.TemporaryDirectory() as temp:
            output, _ = self.smoke(Path(temp))
            MUTATIONS['no_plugin'](output / 'smoke-claude-B', 'claude')
            self.assert_refused(Path(temp), r"looked for one init plugin named devlyn .*agents-md@builtin")

    def test_session_text_shape_mismatch_reports_where_the_first_sentence_is(self):
        with tempfile.TemporaryDirectory() as temp:
            output, _ = self.smoke(Path(temp))
            write_request(output / 'smoke-codex-B', b_request('<developer_instructions>\n' + TEXT.rstrip('.')))
            self.assert_refused(Path(temp), r"found it 0 time\(s\).*'role': 'developer'.*'starts_at': 25, "
                                            r"'first_difference': " + str(len(TEXT) - 1))

    def test_smoke_forms_must_equal_the_launch_probe(self):
        changes = [
            (lambda launch: launch['claude']['SMOKE'].update(status_line=SHAPES['status_lines']['codex']),
             r'smoke-claude-B: SMOKE differs from the launch probe.s SMOKE seal: status line or digest'),
            (lambda launch: launch['claude']['SMOKE'].update(plugin_dir='/elsewhere'), r'plugin path, probe /elsewhere'),
            (lambda launch: launch['codex']['SMOKE']['projection']['files'].update({'x': '0'}),
             r'smoke-codex-B: SMOKE differs .*: projection'),
            (lambda launch: launch['codex']['SMOKE']['model_input']['B']['location'].update(role='user'),
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
            MUTATIONS['plugin'](output / 'smoke-claude-A', 'claude')
            self.assert_refused(Path(temp), r'SMOKE qualification failed: smoke-claude-A: claude-init: A init plugins')
        with tempfile.TemporaryDirectory() as temp:
            output, _ = self.smoke(Path(temp))
            (output / 'verdict-smoke-codex-A.json').write_text(json.dumps({'status': 'STOP', 'reason': 'locator: x'}))
            self.assert_refused(Path(temp), r'smoke-codex-A: verdict is STOP \(locator: x\)')

    def test_codex_b_usage_must_be_the_owner_session_alone(self):
        """DESIGN Q7: Codex B's usage COMPLETE, and no session besides the owner (the app-server read starts none);
        the other SMOKE cells are not held to it."""
        for verdict, pattern in (
                (dict(usage='PARTIAL', identity=dict(owner_launched_sessions=[])), r"usage PARTIAL, sessions .* \[\]"),
                (dict(usage='COMPLETE', identity=dict(owner_launched_sessions=[dict(engine='codex', session='s')])),
                 r"smoke-codex-B: usage COMPLETE, sessions besides the owner \[\{'engine': 'codex'")):
            with self.subTest(pattern=pattern), tempfile.TemporaryDirectory() as temp:
                output, runtime = self.smoke(Path(temp))
                (output / 'verdict-smoke-codex-B.json').write_text(json.dumps(dict(status='COMPLETE', **verdict)))
                self.assert_refused(Path(temp), pattern)
        with tempfile.TemporaryDirectory() as temp:
            output, runtime = self.smoke(Path(temp))
            (output / 'verdict-smoke-codex-A.json').write_text(json.dumps(dict(status='COMPLETE', usage='PARTIAL')))
            instructions.seal_forms(runtime)

    def control(self, root, version='4.3.30', tarball=None):
        package = root / 'control/packages/B/package'
        (package / 'config/skills/_shared').mkdir(parents=True)
        (package / 'package.json').write_text(json.dumps({'name': 'devlyn-cli', 'version': version}))
        shutil.copyfile(RELEASE, package / 'release.json')
        (package / 'config/skills/_shared/runtime-principles.md').write_text(instructions.PREAMBLE + ' Rules.\n')
        files = {'package/' + str(p.relative_to(package)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in package.rglob('*') if p.is_file()}
        (root / 'control.manifest.json').write_text(json.dumps({'packages': {'B': dict(
            sha256=tarball or instructions.TARBALL_SHA256, integrity=instructions.INTEGRITY, files=files)}}))
        (root / 'output').mkdir()
        runtime = root / 'runtime.json'
        runtime.write_text(json.dumps({'output': str(root / 'output'), 'control': str(root / 'control')}))
        return package, runtime

    def test_seal_records_package_identity_session_text_and_pending(self):
        with tempfile.TemporaryDirectory() as temp:
            _, runtime = self.control(Path(temp))
            probed = dict(launch={'probe': 'fields'}, controls={}, devlyn_skills=[])
            with mock.patch.object(instructions, 'launch_probe', return_value=probed) as probe:
                seal = json.loads(Path(instructions.seal(runtime)).read_text())
            self.assertEqual(probe.call_args.args[1], seal['session_text'])
            self.assertEqual({key: seal[key] for key in probed}, probed)
            self.assertEqual(seal['package'], dict(tarball_sha256=instructions.TARBALL_SHA256,
                                                   integrity=instructions.INTEGRITY, version='4.3.30',
                                                   release_digest=instructions.RELEASE_DIGEST))
            self.assertEqual(seal['cli'], {'claude': '2.1.322', 'codex': '0.164.0'})
            self.assertEqual(seal['qualification'], {'status': 'PENDING'})
            root = instructions.RELEASE_ROOT + '/config/skills'
            self.assertEqual(seal['session_text'], instructions.PREAMBLE + ' Rules.\n\n\n' + '\n'.join([
                'Devlyn session skill catalog (read the absolute file to invoke):',
                f'devlyn-ideate: {root}/devlyn-ideate/SKILL.md', f'devlyn-engines: {root}/devlyn-engines/SKILL.md',
                f"This session's _shared folder is {root}/_shared.",
                'Use that absolute folder wherever the Devlyn defaults name _shared/.']))
            with self.assertRaisesRegex(ValueError, 'already exists'):
                instructions.seal(runtime)

    def test_seal_refuses_another_tarball_altered_tree_or_version(self):
        for case in ('tarball', 'tree', 'version'):
            with tempfile.TemporaryDirectory() as temp:
                package, runtime = self.control(Path(temp), version='4.3.29' if case == 'version' else '4.3.30',
                                                tarball='0' * 64 if case == 'tarball' else None)
                if case == 'tree':
                    (package / 'config/skills/_shared/runtime-principles.md').write_text('edited\n')
                with self.assertRaisesRegex(ValueError, 'tarball identity|differs from its tarball|B package is 4.3.29'), \
                        mock.patch.object(instructions, 'launch_probe', side_effect=AssertionError('probe ran')):
                    instructions.seal(runtime)
                self.assertFalse((Path(temp) / 'instructions.seal.json').exists())


O = {engine: prepare.owner_argv(engine, OWNER[engine], 'do the task now') for engine in prepare.CONFIGS}
RUN_FOLDER = '/tmp/devlyn-run-Ab12Cd'


def planned(engine, text=TEXT):
    """What devlyn run 4.3.30 hands the engine before O (the 2026-11-11 probe and the Q2 probe saw this)."""
    if engine == 'claude':
        return ['--plugin-dir', f'{instructions.RELEASE_ROOT}/native/claude', '--append-system-prompt-file',
                f'{RUN_FOLDER}/devlyn-instructions.md']
    market = instructions.MARKET
    return ['-c', f'marketplaces={{"{market}"={{"source_type"="local","source"="{instructions.RELEASE_ROOT}/native/codex"}}}}',
            '-c', f'plugins={{"devlyn@{market}"={{"enabled"=true}}}}',
            '-c', 'developer_instructions=' + json.dumps(text, ensure_ascii=False)]


def engine_call(engine, arm, text=TEXT, **change):
    """One shim record: the engine's argv, environment and the files its argv names."""
    argv = (planned(engine, text) if arm == 'B' else []) + O[engine]
    files = {argv[3]: base64.b64encode(text.encode()).decode()} if engine == 'claude' and arm == 'B' else {}
    env = dict(HOME=instructions.HOME, HOSTNAME=arm, **({'DEVLYN_NODE': '/usr/local/bin/node'} if arm == 'B' else {}))
    return dict(dict(argv=argv, env=env, files=files), **change)


class LaunchProbe(unittest.TestCase):
    """DESIGN Q2's guards, each violating and allowed, on the shapes the 2026-11-11 probe saw."""

    def cell(self, root, engine, arm):
        out, _ = make_cell(root, engine, arm)
        plan = dict(name=out.name, argv=(instructions.DEVLYN if arm == 'B' else []) + [engine, *O[engine]])
        return out, plan

    def test_b_launch_is_sealed_and_each_departure_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            for engine in prepare.CONFIGS:
                out, plan = self.cell(Path(temp) / engine, engine, 'B')
                status = SHAPES['status_lines'][engine]
                sealed = instructions.launch_b(engine, plan, out, (0, '', f'noise\n{status}\n', [engine_call(engine, 'B')]),
                                               TEXT)
                self.assertEqual(sealed['argv'], instructions.normalise(planned(engine)) + O[engine])
                self.assertEqual(sealed['raw_argv'][-len(O[engine]):], O[engine])
                self.assertEqual((sealed['status_line'], sealed['release_digest']), (status, instructions.RELEASE_DIGEST))
                self.assertEqual(list(sealed['plan_files'].values()), [hashlib.sha256(TEXT.encode()).hexdigest()])
                if engine == 'claude':
                    self.assertEqual(list(sealed['plan_files']), ['/tmp/devlyn-run-*/devlyn-instructions.md'])
                else:
                    self.assertEqual(set(sealed['projection']['files']),
                                     {'.codex-plugin/plugin.json', '.devlyn-harness-projection.json'})
                call = engine_call(engine, 'B')
                departures = [(1, f'{status}\n', [call]), (0, '', [call]), (0, f'{status}\n{status}\n', [call]),
                              (0, f'{status}\n' + SHAPES['status_lines']['refused'] + '\n', [call]),
                              (0, f'{status}\n', [call, call]), (0, f'{status}\n', []),
                              (0, f'{status}\n', [dict(call, argv=call['argv'][:-1] + ['another prompt'])]),
                              (0, f'{status}\n', [engine_call(engine, 'B', text=TEXT + ' ')])]
                if engine == 'claude':
                    departures.append((0, f'{status}\n', [dict(call, argv=['--plugin-dir', '/x'] + call['argv'][2:])]))
                else:
                    departures.append((0, f'{status}\n', [dict(call, argv=['-c', 'model="x"'] + call['argv'])]))
                for number, (code, stderr, records) in enumerate(departures):
                    with self.subTest(engine=engine, departure=number):
                        with self.assertRaisesRegex(ValueError, f'^{plan["name"]}: '):
                            instructions.launch_b(engine, plan, out, (code, '', stderr, records), TEXT)
                rewrite_release(out, lambda m: m['files'][0].update(sha256='0' * 64), recompute=True)
                with self.assertRaisesRegex(ValueError, 'HOME release'):
                    instructions.launch_b(engine, plan, out, (0, '', f'{status}\n', [call]), TEXT)
            (Path(temp) / 'codex/smoke-codex-B/home/.codex' / instructions.PROJECTION /
             '.devlyn-harness-projection.json').unlink()
            shutil.copyfile(RELEASE, next((Path(temp) / 'codex/smoke-codex-B/home/.devlyn').rglob('release.json')))
            with self.assertRaisesRegex(ValueError, 'projection lacks'):
                instructions.launch_b('codex', self.cell(Path(temp) / 'again', 'codex', 'B')[1],
                                      Path(temp) / 'codex/smoke-codex-B',
                                      (0, '', SHAPES['status_lines']['codex'] + '\n', [engine_call('codex', 'B')]), TEXT)

    def test_a_is_handed_exactly_o_with_nothing_devlyn(self):
        with tempfile.TemporaryDirectory() as temp:
            for engine in prepare.CONFIGS:
                out, plan = self.cell(Path(temp) / engine, engine, 'A')
                sealed = instructions.launch_a(engine, plan, out, (0, '', '', [engine_call(engine, 'A')]))
                self.assertEqual(sealed['argv'], O[engine])
                call = engine_call(engine, 'A')
                if engine == 'codex':
                    MUTATIONS['devlyn_projection'](out, engine)
                    with self.assertRaisesRegex(ValueError, 'devlyn in A'):
                        instructions.launch_a(engine, plan, out, (0, '', '', [call]))
                    shutil.rmtree(out / 'home/.codex/plugins/cache' / instructions.MARKET)
                for run in ((0, '', '', [dict(call, argv=call['argv'] + ['--verbose'])]), (0, '', '', []),
                            (0, '', SHAPES['status_lines'][engine] + '\n', [call]), (1, '', '', [call]),
                            (0, '', '', [dict(call, env=dict(call['env'], DEVLYN_NODE='/usr/local/bin/node'))])):
                    with self.subTest(engine=engine, run=run[1:3]), \
                            self.assertRaisesRegex(ValueError, f'^{plan["name"]}: '):
                        instructions.launch_a(engine, plan, out, run)
                (out / 'home/.devlyn').mkdir()
                with self.assertRaisesRegex(ValueError, 'devlyn in A'):
                    instructions.launch_a(engine, plan, out, (0, '', '', [call]))

    def test_strict_mcp_config_control(self):
        for engine in prepare.CONFIGS:
            refused = instructions.REFUSED.format(engine=engine)
            self.assertEqual(json.loads(refused.split(' ', 3)[3]), {'engine': engine, 'argument': '--strict-mcp-config'})
            self.assertEqual(instructions.refusal(engine, (2, '', refused + '\n', [])),
                             dict(exit=2, stderr=[refused], engine_calls=0))
            for run in ((0, '', '', [engine_call(engine, 'B')]), (2, '', refused + '\n', [engine_call(engine, 'B')]),
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
        self.assertEqual(found['B']['skill_roots'], sorted(found['A']['skill_roots'] + [
            f'{instructions.HOME}/.codex/{instructions.PROJECTION}/skills']))
        self.assertEqual((found['control']['plugin_skills'], len(found['control']['agents_md'])),
                         (['other:foreign-skill'], 1))
        self.assertEqual(instructions.plugin_roots(found['control']),
                         [f'{instructions.HOME}/.codex/plugins/cache/foreign-market'])
        a = found['A']
        self.assertEqual(instructions.input_violations('A', a), [])  # the per-cell rule
        self.assertEqual(instructions.input_violations('B', found['B']), [])
        self.assertEqual(len(instructions.input_violations('A', found['control'])), 1)
        self.assertEqual(len(instructions.input_violations('B', a)), 2)
        self.assertEqual(len(instructions.input_violations('A', found['B'])), 2)
        self.assertEqual(instructions.probe_violations('A', a, a, DEVLYN_SKILLS), [])  # Q2's reading
        self.assertEqual(instructions.probe_violations('B', found['B'], a, DEVLYN_SKILLS), [])
        self.assertEqual(len(instructions.probe_violations('A', found['control'], a, DEVLYN_SKILLS)), 3)
        extra = dict(found['B'], plugin_skills=DEVLYN_SKILLS + ['devlyn:extra'])  # a skill the package does not have
        self.assertEqual(len(instructions.probe_violations('B', extra, a, DEVLYN_SKILLS)), 1)

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

    def test_normalise_settings_and_environment_patch(self):
        self.assertEqual(instructions.normalise([f'{RUN_FOLDER}/devlyn-instructions.md', '-p']),
                         ['/tmp/devlyn-run-*/devlyn-instructions.md', '-p'])
        self.assertEqual(instructions.codex_settings(planned('codex'))['developer_instructions'], TEXT)
        for args in (['-c'], ['--config', 'a=1'], ['-c', 'a=1', 'exec']):
            with self.assertRaisesRegex(ValueError, 'not -c pairs'):
                instructions.codex_settings(args)
        self.assertEqual(instructions.env_patch(dict(HOME='/h', HOSTNAME='b', DEVLYN_NODE='/n', GONE=None),
                                                dict(HOME='/h', HOSTNAME='a', GONE='x')),
                         dict(DEVLYN_NODE='/n', GONE=None))


class LaunchProbeRun(unittest.TestCase):
    """launch_probe's wiring with a fake container in place of Docker: every engine x tree x arm prepared and run, the
    controls and Codex's model input read, scratch removed; any failure writes no seal."""

    def fake(self, root, broken=None):
        runs = []

        def prepared(runtime, name, tree, arm, engine):
            out = Path(runtime['output']) / name
            (out / 'home/.codex').mkdir(parents=True)
            (out / 'home/.claude').mkdir()
            if engine == 'codex':
                (out / 'home/.codex/config.toml').write_text(CODEX_TOML)
            argv = (instructions.DEVLYN if arm == 'B' else []) + [engine, *O[engine]]
            (out / 'plan.json').write_text(json.dumps(dict(name=name, task=tree, arm=arm, config=engine, argv=argv,
                                                           home=str(out / 'home'), env=dict(HOME=instructions.HOME))))
            return out

        def materialize(home, codex):
            release = home / '.devlyn/cli/releases/devlyn-cli/4.3.30'
            release.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(RELEASE, release / 'release.json')
            if codex:
                folder = home / '.codex' / instructions.PROJECTION
                (folder / '.codex-plugin').mkdir(parents=True, exist_ok=True)
                (folder / '.codex-plugin/plugin.json').write_text('{}')
                (folder / '.devlyn-harness-projection.json').write_text('{}')
                (home / '.codex/.tmp').mkdir(exist_ok=True)
                (home / '.codex/.tmp/plugins.sync.lock').write_text('')

        def container(_cell, plan, command, binds=(), env=None, timeout=300):
            home, engine, arm = Path(plan['home']), plan['config'], plan['arm']
            runs.append((plan['name'], command[:6]))
            records = next((Path(src) for src, dst, _ in binds if dst == '/q2/records'), None)
            status = SHAPES['status_lines'][engine] + '\n'
            if '--strict-mcp-config' in command and broken != f'strict {engine}':
                return 2, '', instructions.REFUSED.format(engine=engine) + '\n'
            if 'prompt-input' in command:
                if arm == 'B':
                    materialize(home, True)
                planted = (home / '.codex/AGENTS.md').exists()
                items = INPUT['control' if planted else 'A' if arm == 'A' or broken == f'debug {plan["task"]}' else 'B']
                return 0, json.dumps(items), status if arm == 'B' else ''
            call = engine_call(engine, arm)
            if broken == f'A {engine} {plan["task"]}' and arm == 'A':
                call['argv'] = call['argv'] + ['--extra']
            if arm == 'B':
                materialize(home, engine == 'codex')
            (records / f'{engine}-1.json').write_text(json.dumps(call))
            return 0, '', status if arm == 'B' else ''

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
        return runtime, runs, [mock.patch.object(instructions, 'load', side_effect=lambda name: modules[name]),
                               mock.patch.object(instructions, 'container', side_effect=container)]

    def probe(self, root, broken=None):
        runtime, runs, patches = self.fake(root, broken)
        for patch in patches:
            patch.start()
        try:
            return instructions.launch_probe(runtime, TEXT), runs
        finally:
            mock.patch.stopall()
            self.assertEqual(list((root / 'scratch').iterdir()), [])

    def test_every_engine_tree_and_arm_is_probed_and_sealed(self):
        with tempfile.TemporaryDirectory() as temp:
            sealed, runs = self.probe(Path(temp))
        self.assertEqual(set(sealed), {'launch', 'controls', 'devlyn_skills'})
        self.assertEqual({engine: list(trees) for engine, trees in sealed['launch'].items()},
                         {engine: list(instructions.TREES) for engine in prepare.CONFIGS})
        self.assertEqual(sealed['devlyn_skills'], DEVLYN_SKILLS)
        self.assertEqual(set(sealed['controls']), {'claude --strict-mcp-config', 'codex --strict-mcp-config', 'reader'})
        for engine in prepare.CONFIGS:
            for tree, entry in sealed['launch'][engine].items():
                self.assertEqual(entry['a']['argv'], O[engine])
                self.assertEqual(entry['env_patch'], dict(DEVLYN_NODE='/usr/local/bin/node'))
                self.assertEqual(entry['argv'][:len(planned(engine))], instructions.normalise(planned(engine)))
                if engine == 'codex':
                    self.assertEqual(entry['model_input']['B']['plugin_skills'], DEVLYN_SKILLS)
                    self.assertEqual(entry['model_input']['A']['plugin_skills'], [])
        kinds = [('strict' if '--strict-mcp-config' in command else 'debug' if 'prompt-input' in command else 'launch')
                 for _, command in runs]
        self.assertEqual({kind: kinds.count(kind) for kind in set(kinds)}, dict(launch=24, strict=2, debug=12 + 1))

    def test_a_failed_expectation_raises_and_cleans_scratch(self):
        for broken, pattern in (('A codex F11', 'q2-codex-F11-A: .*exactly O'),
                                ('strict codex', 'codex --strict-mcp-config: exit 0, .*1 engine call'),
                                ('debug D4', 'Codex model input, D4: B carries the session text 0')):
            with self.subTest(broken=broken), tempfile.TemporaryDirectory() as temp:
                with self.assertRaisesRegex(ValueError, pattern):
                    self.probe(Path(temp), broken)


class Arms(unittest.TestCase):
    def prepared(self, root, arm, config):
        runtime = dict(output=str(root / 'output'), control=str(root / 'control'), image='sha256:image',
                       auth=str(root / 'auth'), sources=str(root / 'sources'))
        out = prepare.prepare(runtime, f'smoke-{config}-{arm}', 'SMOKE', arm, config)
        return out, json.loads((out / 'plan.json').read_text())

    def test_argv_install_watchdog_and_config_byte_for_byte(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for config in prepare.CONFIGS:
                for arm in prepare.ARMS:
                    out, plan = self.prepared(root, arm, config)
                    prompt = (out / 'prompt.txt').read_text()
                    owner = (['-p', '--model', 'claude-opus-5-5', '--effort', 'high', '--permission-mode',
                              'bypassPermissions', '--output-format', 'stream-json', '--verbose', prompt]
                             if config == 'claude' else ['exec', '--json', '--skip-git-repo-check', prompt])
                    wrapper = [] if arm == 'A' else ['node', '/install/package/bin/devlyn.js', 'run']
                    self.assertEqual(plan['argv'], wrapper + [config] + owner)
                    self.assertEqual(plan['install'], str(root / 'control/packages/B') if arm == 'B' else None)
                    self.assertEqual(plan['wall_seconds'], 2700)
                    self.assertFalse((out / 'instructions.pre.json').exists())
                    self.assertNotIn('instructions_pre_sha256', json.loads((out / 'baseline.json').read_text()))
                    config_toml = out / 'home/.codex/config.toml'
                    if config == 'codex':
                        self.assertEqual(config_toml.read_text(), CODEX_TOML)
                        self.assertNotIn('plugins', tomllib.loads(CODEX_TOML)['features'])
                    else:
                        self.assertFalse(config_toml.exists())

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
        self.assertIs(tomllib.loads(CODEX_TOML)['features']['remote_plugin'], False)

    def test_other_tasks_arms_and_configs_are_refused_before_any_write(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = dict(output=str(Path(temp) / 'output'))
            for task, arm, config in (('I0185', 'A', 'claude'), ('E1', 'B', 'codex'), ('SMOKE', 'C', 'claude'),
                                      ('D3', 'A', 'grok')):
                with self.assertRaisesRegex(ValueError, '0265 cells are'):
                    prepare.prepare(runtime, 'x', task, arm, config)
            self.assertFalse((Path(temp) / 'output').exists())

    def test_no_installer_i0185_or_arm_c_code_path_remains(self):
        banned = [r'I0185', r'\bINSTALL\b', r'\binstall\(', r'skills_present', r'install_output', r"'C'",
                  r'instructions\.pre', r'codex_limits', r'claude_limits_with_account', r'claude_limits_(before|after)',
                  r"'E1'", r"'E2'"]
        for name in ('prepare.py', 'cell.py', 'run_cell.py', 'instructions.py', 'assess.py', 'quota.py',
                     'strict_config_check.py', 'check.py'):
            text = (HERE / name).read_text()
            for pattern in banned:
                self.assertIsNone(re.search(pattern, text), (name, pattern))
        text = (HERE / 'prepare.py').read_text()
        for flag in ('--strict-mcp-config', '--strict-config', '--mcp-config'):  # refused by devlyn run 4.3.30
            self.assertFalse(flag in text, flag)
        self.assertEqual((prepare.ARMS, prepare.CONFIGS), (('A', 'B'), ('claude', 'codex')))
        self.assertFalse(hasattr(run_cell, 'codex_limits') or hasattr(run_cell, 'claude_limits_with_account'))

    def test_removed_entry_points_and_parameters(self):
        """Astra's removable list: no assess.py command line (it bypassed the guarded credential snapshot), no E1/E2
        rows, no stored-token fallback for the usage read, no unused venue, no diagnostics nothing in 0265 reads."""
        self.assertNotIn('__main__', (HERE / 'assess.py').read_text())
        self.assertEqual(set(run_cell.check.ROWS), {'B5', 'F10', 'F11'})
        self.assertIs(inspect.signature(run_cell.claude_limits).parameters['access_token'].default,
                      inspect.Parameter.empty)
        self.assertEqual(list(inspect.signature(run_cell.assessment_snapshot).parameters), ['runtime'])
        self.assertNotIn('venue', inspect.signature(run_cell.grade).parameters)
        self.assertFalse(hasattr(run_cell, 'diagnostics') or 'diagnostics' in run_cell.MODULES)


class Cell(unittest.TestCase):
    def owner(self, arm, state, status_code=0):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            out = root / 'cell-1'
            for folder in ('home/.claude', 'home/.codex', 'cell', 'harness', 'tmp'):
                (out / folder).mkdir(parents=True)
            (root / 'auth').mkdir()
            (root / 'auth/claude.json').write_text('{"fake": true}')
            (root / 'auth/codex.json').write_text('{"fake": true}')
            plan = dict(name='cell-1', engine='claude', image='sha256:image', cell=str(out / 'cell'),
                        home=str(out / 'home'), control=str(root / 'control/public'), harness=str(out / 'harness'),
                        tmp=str(out / 'tmp'), env={'HOME': '/home/participant'}, argv=['claude', '-p', 'x'],
                        wall_seconds=5, install=str(root / 'control/packages/B') if arm == 'B' else None)
            (out / 'plan.json').write_text(json.dumps(plan))

            def docker(*args, timeout=60):
                if args[0] == 'create':
                    return 'cid'
                if args[0] == 'inspect':
                    return json.dumps([{'State': dict(state, Running=False, Pid=0)}])
                return ''
            popen = mock.Mock()
            popen.return_value.wait.return_value = status_code
            with mock.patch.object(cell, 'docker', side_effect=docker), \
                    mock.patch.object(cell.subprocess, 'Popen', popen), \
                    mock.patch.object(cell, 'preserve_tmp'), \
                    mock.patch.object(cell, 'identity', return_value={'status': 'MATCH'}):
                record = cell.run(out, dict(auth=str(root / 'auth'), scratch=str(root / 'scratch')))
            argv = json.loads((out / 'run/started.json').read_text())['create_argv']
            return argv, json.loads((out / 'run/result.json').read_text()), str(root / 'control/packages/B'), record, plan

    def test_install_mount_only_for_b(self):
        b, _, install, _, _ = self.owner('B', {'OOMKilled': False, 'ExitCode': 0})
        a, _, _, _, _ = self.owner('A', {'OOMKilled': False, 'ExitCode': 0})
        self.assertIn(f'type=bind,src={install},dst=/install,readonly', b)
        self.assertEqual(b[b.index('sha256:image'):], ['sha256:image', 'claude', '-p', 'x'])
        self.assertFalse([value for value in a if '/install' in value])
        targets = lambda argv: [value.split('dst=')[1] for value in argv if 'dst=' in value]
        self.assertEqual(targets(b), targets(a) + ['/install,readonly'])

    def test_the_probe_container_is_the_cell_container_without_credentials(self):
        for arm in prepare.ARMS:
            argv, _, _, _, plan = self.owner(arm, {'OOMKilled': False, 'ExitCode': 0})
            volume = argv[argv.index('--mount') + 1].split('src=')[1].split(',')[0]
            probe = cell.create_argv(plan, argv[argv.index('--name') + 1], volume, cell.mounts(plan), plan['env'],
                                     plan['argv'])
            secret = [i for i, value in enumerate(argv) if value == '--mount' and any(
                f'dst={dst}' in argv[i + 1] for dst in ('/home/participant/.codex/auth.json',
                                                        '/home/participant/.claude/.credentials.json'))]
            self.assertEqual(len(secret), 2)
            self.assertEqual(probe, [value for i, value in enumerate(argv) if i not in secret and i - 1 not in secret])

    def test_container_end_is_recorded(self):
        _, result, _, record, _ = self.owner('A', {'OOMKilled': True, 'ExitCode': 137}, status_code=137)
        self.assertEqual(result['container'], {'oom_killed': True, 'exit_code': 137})
        self.assertEqual((record['owner_status'], record['teardown']), ('EXITED_NONZERO', 'CLEAN'))


class CellLifecycle(unittest.TestCase):
    """H4 (a): cell.run makes the credential copy, the /tmp volume and the container inside the lifecycle whose finally
    removes them. Docker is a fake that holds volumes and containers; each violating case raises at one step."""

    def lifecycle(self, fail=None):
        """cell.run with Docker failing at `fail` (copy, volume, argv, create, create-made, start or None); returns
        (the exception raised or None, result.json, what Docker still holds, whether the credential copy remains)."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            out = root / 'cell-1'
            for folder in ('home/.claude', 'home/.codex', 'cell', 'harness', 'tmp'):
                (out / folder).mkdir(parents=True)
            (root / 'auth').mkdir()
            if fail != 'copy':
                (root / 'auth/claude.json').write_text('{"fake": true}')
            (root / 'auth/codex.json').write_text('{"fake": true}')
            if fail == 'leftover':  # a credential copy a killed run of this cell left in scratch
                (root / 'scratch/credentials/cell-1').mkdir(parents=True)
                (root / 'scratch/credentials/cell-1/claude.json').write_text('{"stale": true}')
            plan = dict(name='cell-1', engine='claude', image='sha256:image', cell=str(out / 'cell'),
                        home=str(out / 'home'), control=str(root / 'control/public'), harness=str(out / 'harness'),
                        tmp=str(out / 'tmp'), env={}, argv=['claude', '-p', 'x'], wall_seconds=5, install=None)
            (out / 'plan.json').write_text(json.dumps(plan))
            volumes, containers = set(), {}
            refused = subprocess.CalledProcessError(1, ['docker'], stderr='Error response from daemon: refused')

            def docker(*args, timeout=60):
                if args[:2] == ('volume', 'create'):
                    if fail == 'volume':
                        raise refused
                    volumes.add(args[-1])
                elif args[0] == 'create':
                    name = args[args.index('--name') + 1]
                    if fail in ('create', 'create-made'):
                        if fail == 'create-made':  # the daemon made it, then its answer was lost
                            containers[name] = dict(Running=False, Pid=0, OOMKilled=False, ExitCode=0)
                        raise subprocess.TimeoutExpired(['docker', 'create'], 60)
                    containers[name] = dict(Running=False, Pid=0, OOMKilled=False, ExitCode=0)
                    return name
                elif args[0] == 'ps':
                    return next((n for n in containers if args[-1] == f'name=^/{n}$'), '')
                elif args[0] == 'inspect':
                    return json.dumps([{'State': containers[args[1]]}])
                elif args[0] == 'rm':
                    del containers[args[1]]
                return ''

            def preserve(volume, dest, image):  # copies the volume into the cell, then removes it, as cell.py's does
                volumes.discard(volume)

            def popen(argv, **_kwargs):
                if fail == 'start':
                    raise OSError('docker start could not be run')
                return mock.Mock(**{'wait.return_value': 0})
            argv = mock.patch.object(cell, 'create_argv', side_effect=ValueError('bad plan')) if fail == 'argv' else \
                contextlib.nullcontext()
            raised = None
            removal = mock.patch.object(cell.shutil, 'rmtree', side_effect=PermissionError('scratch is read-only')) \
                if fail == 'removal' else contextlib.nullcontext()
            if fail == 'record':  # the run folder cannot take result.json: its write raises, the removal still runs
                real_write = Path.write_text

                def write(path, *args, **kwargs):
                    if path.name == 'result.json':
                        raise OSError('no space left on device')
                    return real_write(path, *args, **kwargs)
                removal = mock.patch.object(Path, 'write_text', write)
            with mock.patch.object(cell, 'docker', side_effect=docker), argv, removal, \
                    mock.patch.object(cell.subprocess, 'Popen', side_effect=popen), \
                    mock.patch.object(cell, 'preserve_tmp', side_effect=preserve), \
                    mock.patch.object(cell, 'identity', return_value={'status': 'MATCH'}):
                try:
                    cell.run(out, dict(auth=str(root / 'auth'), scratch=str(root / 'scratch')))
                except (OSError, ValueError, subprocess.SubprocessError) as exc:
                    raised = exc
            written = out / 'run/result.json'
            result = json.loads(written.read_text()) if written.is_file() else None
            return raised, result, (volumes, containers), (root / 'scratch/credentials/cell-1').exists()

    def test_nothing_survives_an_exception_at_any_step(self):
        cases = {'copy': FileNotFoundError, 'volume': subprocess.CalledProcessError, 'argv': ValueError,
                 'create': subprocess.TimeoutExpired, 'create-made': subprocess.TimeoutExpired, 'start': OSError}
        for fail, kind in cases.items():
            with self.subTest(fail=fail):
                raised, result, held, copy_left = self.lifecycle(fail)
                self.assertIsInstance(raised, kind)  # the exception still ends the cell
                self.assertEqual((held, copy_left), ((set(), {}), False))
                self.assertEqual((result['teardown'], result['owner_status']), ('CLEAN', None))

    def test_a_copy_left_by_a_killed_run_is_removed_and_ends_the_cell(self):
        # Re-check finding (Grok): the credential folder is made inside the lifecycle, so a leftover is an error the
        # finally still cleans up; before, mkdir raised outside the try and the stale copy stayed in scratch.
        raised, result, held, copy_left = self.lifecycle('leftover')
        self.assertIsInstance(raised, FileExistsError)
        self.assertEqual((held, copy_left), ((set(), {}), False))
        self.assertEqual((result['teardown'], result['owner_status']), ('CLEAN', None))

    def test_the_record_survives_a_credential_copy_that_cannot_be_removed(self):
        # Re-check finding (Grok): result.json is written before the removal, and a failed removal is a failed
        # teardown with its reason, never a lost record. The allowed case is the clean run below.
        raised, result, held, copy_left = self.lifecycle('removal')
        self.assertIsNone(raised)
        self.assertTrue(copy_left)
        self.assertEqual((result['teardown'], result['owner_status']), ('FAILED', 'EXITED_0'))
        self.assertIn('credential copy not removed: scratch is read-only', result['teardown_error'])

    def test_a_record_that_cannot_be_written_still_removes_the_credential_copy(self):
        # Second re-check (MEDIUM): the record is written first, but inside a try whose finally removes the copy, so a
        # failed write ends the cell with its error and leaves no copy. The allowed case is the clean run below.
        raised, result, held, copy_left = self.lifecycle('record')
        self.assertIsInstance(raised, OSError)
        self.assertIn('no space left on device', str(raised))
        self.assertEqual((result, held, copy_left), (None, (set(), {}), False))

    def test_a_cell_that_runs_is_torn_down_the_same_way(self):
        raised, result, held, copy_left = self.lifecycle()
        self.assertIsNone(raised)
        self.assertEqual((held, copy_left), ((set(), {}), False))
        self.assertEqual((result['teardown'], result['owner_status'], result['container']),
                         ('CLEAN', 'EXITED_0', {'oom_killed': False, 'exit_code': 0}))


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
            ('A', refused + '\n', '', False, None),
        ]
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
        (root / 'control.manifest.json').write_text(json.dumps({'packages': {'B': {'sha256': 'package'}}}))
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
                             'B launch fault: run-argument-unsupported {"engine":"codex","argument":"-C"}')
            self.assert_not_graded(mocks)
            self.assertIs(verdict['owner_ran'], False)  # H2: no owner ran, so no tree or scope is kept
            self.assertFalse({'snapshot', 'scope_violations', 'changed', 'scope_error'} & set(verdict))

    def test_memory_kill_stops_without_checks_or_assessors(self):
        with tempfile.TemporaryDirectory() as temp:
            code, verdict, mocks, out, _ = self.run_cell(Path(temp), arm='A', container={'oom_killed': True,
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
            code, verdict, mocks, out, _ = self.run_cell(Path(temp), arm='A', located=refused,
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
            self.assertEqual(run_cell.run(runtime, 'cell-1', 'D3', 'A', 'claude'), 2)
            self.assertEqual({k: v for k, v in json.loads(verdict_path.read_text()).items() if k != 'cell'},
                             dict(status='STOP', owner_ran=False, reason='instruction assertion: seal missing'))
            verdict_path.unlink()
            (root / 'instructions.seal.json').write_text(json.dumps({'forms': {'claude': {}, 'codex': {}}}))
            with mock.patch.object(run_cell, 'image_identity', return_value=True), \
                    mock.patch.object(run_cell, 'preflight', return_value=(dict(account=['a', 'o']), None)), \
                    mock.patch.object(run_cell, 'control_unchanged', return_value=False):
                self.assertEqual(run_cell.run(runtime, 'cell-1', 'D3', 'A', 'claude'), 2)
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
                code, verdict, mocks, _, _ = self.run_cell(Path(temp), arm='A', owner_status=status)
                self.assertEqual((code, verdict['status'], verdict['product_check_pass']), (0, expected, True))
                mocks['check'].assert_called_once()
                mocks['assess'].assert_called_once()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _, verdict, _, out, _ = self.run_cell(root, arm='A', owner_status='HANG_TIMEOUT',
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
                code, verdict, mocks, _, _ = self.run_cell(Path(temp), arm='A', container=container)
                self.assertEqual((code, verdict['status'], verdict['oom_killed']), (0, 'COMPLETE', oom))
                mocks['assess'].assert_called_once()
        with tempfile.TemporaryDirectory() as temp:  # a memory kill records the flag on its STOP too
            _, verdict, _, _, _ = self.run_cell(Path(temp), arm='A', container={'oom_killed': True, 'exit_code': 137})
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
            loaded = {name: next(f'{folder}/{name}.py' for folder in ('0265', '0256', '0233')  # run_cell.load's order
                                 if (HERE.parent / folder / f'{name}.py').is_file())
                      for name in ('prepare', 'cell', 'record_usage', 'locate', 'check', 'assess', 'quota',
                                   'instructions')}  # no diagnostics: nothing in 0265 reads them
            self.assertEqual({name: entry['path'] for name, entry in seal['modules'].items()},
                             dict(loaded, run_cell0222='0222/run_cell.py'))
            self.assertTrue(all(loaded[name].startswith('0265/') for name in ('prepare', 'cell', 'assess', 'quota',
                                                                                'instructions')))
            self.assertEqual(seal['package_sha256'], 'package')
            self.assertNotIn('0237/cell-init-v1.py', seal['imported'])
            self.assertEqual(seal['endpoints_sha256'], run_cell.digest(HERE / 'endpoints.json'))

    def test_smoke_is_asserted_by_seal_forms_not_inline_and_a_has_no_package(self):
        with tempfile.TemporaryDirectory() as temp:
            code, verdict, mocks, out, _ = self.run_cell(Path(temp), task='SMOKE', arm='A', config='codex')
            self.assertEqual(code, 0)
            mocks['instructions'].assert_not_called()
            self.assertIsNone(json.loads((out / 'seal.json').read_text())['package_sha256'])

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
        for arm, config in (('C', 'claude'), ('A', 'grok')):
            with self.assertRaisesRegex(ValueError, 'arm A/B and config claude/codex'):
                run_cell.run('/nonexistent/runtime.json', 'x', 'D3', arm, config)

    def test_a_graded_cell_loses_codex_caches_only_and_records_them(self):
        """D-b, allowed: once a measured cell's verdict is written and is not a STOP, exactly run_cell.PRUNED leaves
        it, in both arms, and pruned.json records each root's files (a symlink counted, not followed), bytes and
        symlinks, marked removed. The same cell held at a STOP (violating) keeps every file."""
        expected = dict(removed=True, roots=pruned_roots())
        for arm in prepare.ARMS:
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
            code, _, _, out, _ = self.run_cell(Path(temp), arm='A', config='claude')
            empty = dict(removed=True, roots={})
            self.assertEqual((code, json.loads((out / 'pruned.json').read_text())), (0, empty))
            files = tree_files(out)
            self.assertEqual(run_cell.prune(out), empty)
            self.assertEqual(tree_files(out), files)
        with tempfile.TemporaryDirectory() as temp:
            code, _, _, out, _ = self.run_cell(Path(temp), task='SMOKE', arm='A', config='codex', caches=True)
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
            code, verdict, _, out, _ = self.run_cell(root, arm='A', config='codex', snapshot=venue,
                                                     expected=venue['account'])
            self.assertEqual((code, verdict['claude_account_before'], verdict['codex_account']),
                             (0, venue['account'], run_cell.base.fingerprint('named-account-id')))
            for text in ((root / 'output/verdict-cell-1.json').read_text(), (out / 'seal.json').read_text()):
                self.assertFalse([value for value in ('named-account-id', *SECRETS) if value in text])


class Assessors(unittest.TestCase):
    def assess_with(self, one):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'checks.json').write_text('{}')

            def tree(_out, scratch):
                (scratch / 'work').mkdir()
                return scratch / 'work'
            with mock.patch.object(assess, 'review_tree', side_effect=tree), \
                    mock.patch.object(assess.packet, 'packet', return_value=({}, 'PACKET')), \
                    mock.patch.object(assess, 'one', side_effect=one):
                return assess.assess(root, {'scratch': str(root)})

    def test_seats_run_at_once_and_keep_their_order(self):
        both = threading.Barrier(2, timeout=5)

        def one(_out, _runtime, route, prompt):
            both.wait()  # a serial runner would never reach the second seat
            time.sleep(0.3 if route == assess.TASKS['assessors'][0] else 0)
            return {'route': route}
        records = self.assess_with(one)
        self.assertEqual([r['route'] for r in records], assess.TASKS['assessors'])

    def test_a_failing_seat_raises_after_the_other_finished(self):
        finished = []

        def one(_out, _runtime, route, prompt):
            if route == assess.TASKS['assessors'][0]:
                raise RuntimeError('first seat failed')
            time.sleep(0.3)
            finished.append(route['engine'])
            return {}
        with self.assertRaisesRegex(RuntimeError, 'first seat failed'):
            self.assess_with(one)
        self.assertEqual(finished, [assess.TASKS['assessors'][1]['engine']])

    def test_an_unproved_teardown_outranks_the_other_seats_failure(self):
        """H3: whichever seat's container is unproved, assess() raises that, never the other seat's plain failure."""
        for unproved in assess.TASKS['assessors']:
            def one(_out, _runtime, route, prompt, unproved=unproved):
                if route == unproved:
                    raise assess.TeardownUnproved('cannot prove container y is gone')
                raise RuntimeError('seat timed out')
            with self.subTest(seat=unproved['engine']), self.assertRaises(assess.TeardownUnproved):
                self.assess_with(one)

    def test_record_dir_is_honoured(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            out = root / 'cell'
            out.mkdir()
            (root / 'auth').mkdir()
            (root / 'auth/claude.json').write_text('{"fake": true}')
            runtime = dict(scratch=str(root), auth=str(root / 'auth'), image='sha256:image')
            route = assess.TASKS['assessors'][0]

            def docker(argv, stdin, stdout, stderr, timeout):
                stdout.write(json.dumps({'type': 'result', 'result': '{"complete": true, "findings": []}',
                                         'modelUsage': {}}).encode() + b'\n')
                return subprocess.CompletedProcess(argv, 0)
            with mock.patch.object(assess.subprocess, 'run', side_effect=docker), mock.patch.object(assess, 'reap'):
                record = assess.one(out, runtime, route, 'PROMPT', record_dir=root / 'judge/claude')
                default = assess.one(out, runtime, route, 'PROMPT')
            self.assertEqual(sorted(p.name for p in (root / 'judge/claude').iterdir()),
                             ['prompt.txt', 'result.json', 'stderr', 'stdout'])
            self.assertEqual((root / 'judge/claude/prompt.txt').read_text(), 'PROMPT')
            self.assertTrue(record['complete'])
            self.assertEqual(default, json.loads((out / f'assessment/{route["engine"]}/result.json').read_text()))
            self.assertEqual(sorted(p.name for p in (out / 'assessment').iterdir()), [route['engine']])


class Scope(unittest.TestCase):
    def test_scope_is_the_check_phases_reading_without_a_container(self):
        """H2: check.scope is the scope check.check records (snapshot against baseline.json, the task's allowed
        paths), read with no container. Violating: an added or deleted path outside the allowed ones; allowed: a change
        to an allowed path is only a change."""
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            snapshot = out / 'snapshot'
            snapshot.mkdir()
            for name, text in (('add_one.py', 'def add_one(x):\n    return x + 1\n'), ('README.md', 'readme\n')):
                (snapshot / name).write_text(text)
            (out / 'baseline.json').write_text(json.dumps(dict(task='SMOKE',
                                                               files=run_cell.check.packet.tree(snapshot))))
            self.assertEqual(run_cell.check.scope(out), ([], []))
            (snapshot / 'add_one.py').write_text('changed\n')
            (snapshot / 'notes.txt').write_text('new\n')
            (snapshot / 'README.md').unlink()
            self.assertEqual(run_cell.check.scope(out),
                             (['README.md', 'add_one.py', 'notes.txt'], ['README.md', 'notes.txt']))
            with mock.patch.object(run_cell.check, 'evaluate', return_value=dict(public=[], rows=[], raw=[])):
                seal = run_cell.check.check(out, {})
            self.assertEqual((seal['changed'], seal['scope_violations']), run_cell.check.scope(out))


class DockerAnswers(unittest.TestCase):
    """O9: Docker 29 answers "error: no such object" in lower case. The check container's and an assessor's teardown
    proofs read it in any letter case; any other inspect failure is still no proof."""

    def answers(self, inspect, rm=''):
        def run(argv, **kwargs):
            if argv[1] == 'inspect':
                return subprocess.CompletedProcess(argv, 1, '', inspect)
            return subprocess.CompletedProcess(argv, 1 if argv[1] == 'rm' and rm else 0, 'ok', rm if argv[1] == 'rm' else '')
        return mock.patch.object(subprocess, 'run', side_effect=run)

    def survives(self):
        """Docker still answers for the container after its removal: inspect succeeds every time."""
        return mock.patch.object(subprocess, 'run', side_effect=lambda argv, **kwargs: subprocess.CompletedProcess(
            argv, 0, '[{"Id": "x"}]' if argv[1] == 'inspect' else 'ok', ''))

    def test_check_container_teardown(self):
        check, runtime = run_cell.check, {'control': '/control', 'image': 'sha256:image'}
        self.assertEqual(Path(check.__file__), HERE / 'check.py')  # run_cell's load order picks 0265's copy
        for stderr in ('error: no such object: x', 'Error: No such object: x'):
            with self.subTest(stderr=stderr), self.answers(stderr):
                self.assertEqual(check.in_image(runtime, Path('/work'), ['true'])['exit_code'], 0)
        for stderr in ('permission denied', 'Cannot connect to the Docker daemon at unix:///var/run/docker.sock'):
            with self.subTest(stderr=stderr), self.answers(stderr), self.assertRaisesRegex(check.NoVerdict, 'cannot verify'):
                check.in_image(runtime, Path('/work'), ['true'])
        with self.survives(), self.assertRaisesRegex(check.NoVerdict, 'check container survived teardown'):
            check.in_image(runtime, Path('/work'), ['true'])

    def test_assessor_container_reaped(self):
        self.assertEqual((Path(assess.__file__), Path(run_cell.assess.__file__)), (HERE / 'assess.py',) * 2)
        for stderr in ('error: no such object: x', 'Error: No such object: x'):
            with self.subTest(stderr=stderr), self.answers(stderr, 'Error response from daemon: no such container: x'):
                assess.reap('x')
        for stderr in ('permission denied', 'Cannot connect to the Docker daemon at unix:///var/run/docker.sock'):
            with self.subTest(stderr=stderr), self.answers(stderr), \
                    self.assertRaisesRegex(assess.TeardownUnproved, 'cannot prove container x'):
                assess.reap('x')
        with self.answers('error: no such object: x', 'permission denied'), \
                self.assertRaisesRegex(assess.TeardownUnproved, 'cannot prove container x'):  # the removal failed otherwise
            assess.reap('x')
        with self.survives(), self.assertRaisesRegex(assess.TeardownUnproved, 'cannot prove container x'):
            assess.reap('x')

    def test_a_teardown_proof_that_raises_is_an_unproved_teardown(self):
        """Re-check HIGH 1: both seats failed (their `docker run` could not be run), then the proof of each seat
        container's removal raised. Violating: a timeout or an OS error from `docker rm` or from `docker inspect` is
        the STOP `assessor teardown unproved: …`, which the driver never regrades. Allowed: a proved removal after the
        same failed seats stays an ordinary assessor fault, which the driver regrades."""
        driver = load('driver')
        errors = {'timeout': lambda argv: subprocess.TimeoutExpired(argv, 60),
                  'os error': lambda argv: OSError(5, 'Input/output error')}

        def graded(call=None, error=None):
            def docker(argv, **kwargs):
                if argv[1] == 'run':
                    raise OSError(2, 'No such file or directory', 'docker')
                if argv[1] == call:
                    raise error(argv)
                if argv[1] == 'inspect':
                    return subprocess.CompletedProcess(argv, 1, '', 'error: no such object: x')
                return subprocess.CompletedProcess(argv, 0, '', '')
            with tempfile.TemporaryDirectory() as temp:
                out, auth = Path(temp) / 'cell', Path(temp) / 'auth'
                out.mkdir()
                auth.mkdir()
                (out / 'checks.json').write_text('{}')
                for name in ('claude.json', 'codex.json'):
                    (auth / name).write_text('{"fake": true}')
                runtime = dict(scratch=temp, auth=str(auth), image='sha256:image')

                def tree(_out, scratch):
                    (scratch / 'work').mkdir()
                    return scratch / 'work'
                with mock.patch.object(run_cell.assess, 'review_tree', side_effect=tree), \
                        mock.patch.object(run_cell.assess.packet, 'packet', return_value=({}, 'PACKET')), \
                        mock.patch.object(subprocess, 'run', side_effect=docker):
                    return run_cell.grade(out, runtime, dict(owner_status='EXITED_0'), dict(scope_violations=[]),
                                          assessment_venue=dict(account=['a', 'o']))
        for call in ('rm', 'inspect'):
            for label, error in errors.items():
                with self.subTest(call=call, error=label):
                    record = graded(call, error)
                    self.assertEqual(record['status'], 'STOP')
                    self.assertRegex(record['reason'], r'^assessor teardown unproved: cannot prove container '
                                                       r'devlyn-0231-assess-[0-9a-f]{32} is gone: '
                                                       r'(TimeoutExpired|OSError): ')
                    self.assertFalse(record['reason'].startswith(driver.REGRADE))
        record = graded()
        self.assertEqual((record['status'], record['reason']),
                         ('STOP', "assessment failed: [Errno 2] No such file or directory: 'docker'"))
        self.assertTrue(record['reason'].startswith(driver.REGRADE))


class StrictConfig(unittest.TestCase):
    def test_configs_add_exactly_two_unknown_keys(self):
        allowed, violating = strict.configs()
        self.assertEqual(allowed, CODEX_TOML)
        parsed, loose = tomllib.loads(allowed), tomllib.loads(violating)
        self.assertIs(loose.pop(strict.UNKNOWN[0]), True)
        self.assertIs(loose['features'].pop(strict.UNKNOWN[1]), True)
        self.assertEqual(loose, parsed)


if __name__ == '__main__':
    unittest.main()
