"""Offline tests of 0265's arms, cell, per-cell assertions and assessors. Fakes stand in for Docker and credentials."""
import copy
import fcntl
import hashlib
import importlib.util
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
TEXT = (instructions.PREAMBLE + ' Explicit user and native owner/project instructions take precedence.\n\n'
        '# Project Instructions\n\nSeven rules.\n\nDevlyn session skill catalog (read the absolute file to invoke):\n'
        f"This session's _shared folder is {instructions.RELEASE_ROOT}/config/skills/_shared.\n"
        'Use that absolute folder wherever the Devlyn defaults name _shared/.')
CODEX_TOML = '''model = "gpt-6-astra"
model_reasoning_effort = "high"
approval_policy = "never"
sandbox_mode = "danger-full-access"
web_search = "disabled"
[features]
rollout_budget = false
apps = false
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


def message(role, text):
    return {'type': 'message', 'role': role, 'content': [{'type': 'input_text', 'text': text}]}


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


def b_request(text=TEXT):
    request = copy.deepcopy(SHAPES['codex_request'])
    request['input'].insert(4, message('developer', text))
    return request


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
        write_request(out, b_request() if arm == 'B' else SHAPES['codex_request'],
                      later=SHAPES['codex_request'])
        if arm == 'B':
            folder = out / 'home/.codex' / instructions.PROJECTION
            (folder / '.codex-plugin').mkdir(parents=True)
            (folder / '.codex-plugin/plugin.json').write_text('{"name": "devlyn"}\n')
            (folder / '.devlyn-harness-projection.json').write_text('{"schemaVersion": 1}\n')
    plan = dict(name=out.name, task='SMOKE', arm=arm, config=engine)
    (out / 'plan.json').write_text(json.dumps(plan))
    return out, plan


def pending_seal():
    return dict(package=dict(version='4.3.30', release_digest=instructions.RELEASE_DIGEST), cli=instructions.CLI,
                session_text=TEXT, forms={}, qualification=dict(status='PENDING'))


def sealed(root):
    seal = pending_seal()
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
    'no_text': lambda out, engine: write_request(out, SHAPES['codex_request']),
    'text_twice': lambda out, engine: write_request(out, dict(b_request(), instructions=TEXT)),
    'text': lambda out, engine: write_request(out, b_request()),
    'preamble': lambda out, engine: write_request(out, b_request(instructions.PREAMBLE + ' another version')),
    'moved_text': lambda out, engine: write_request(out, dict(
        SHAPES['codex_request'], input=SHAPES['codex_request']['input'] + [message('user', TEXT)])),
    'no_request': lambda out, engine: shutil.rmtree(out / 'cell/trace'),
    'foreign_plugin': lambda out, engine: (
        (out / 'home/.codex/plugins/cache/foreign/x/1.0/.codex-plugin').mkdir(parents=True),
        (out / 'home/.codex/plugins/cache/foreign/x/1.0/.codex-plugin/plugin.json').write_text('{}')),
    'devlyn_projection': lambda out, engine: (
        (out / 'home/.codex' / instructions.PROJECTION).mkdir(parents=True),
        (out / 'home/.codex' / instructions.PROJECTION / '.devlyn-harness-projection.json').write_text('{}')),
    'marketplace': lambda out, engine: (out / 'home/.codex/config.toml').write_text(
        (out / 'home/.codex/config.toml').read_text() + '[marketplaces.x]\nsource_type = "local"\nsource = "/x"\n'),
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
    ('codex', 'B', 'no_request', 'codex-request'),
    ('codex', 'A', 'foreign_plugin', 'codex-home'), ('codex', 'A', 'devlyn_projection', 'codex-home'),
    ('codex', 'A', 'marketplace', 'codex-home'), ('codex', 'B', 'no_projection', 'codex-home'),
    ('codex', 'B', 'altered_projection', 'codex-home'),
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
            self.assertEqual(instructions.check(out, plan, pending_seal()), ['forms: claude form unsealed'])
            self.assertTrue(instructions.check(out, dict(plan, arm='C'), sealed(Path(temp))))

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
                (output / f'verdict-{out.name}.json').write_text(json.dumps({'status': 'COMPLETE'}))
        (root / 'instructions.seal.json').write_text(json.dumps(pending_seal()))
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

    def test_a_violation_or_stop_verdict_refuses_qualification(self):
        with tempfile.TemporaryDirectory() as temp:
            output, _ = self.smoke(Path(temp))
            MUTATIONS['plugin'](output / 'smoke-claude-A', 'claude')
            self.assert_refused(Path(temp), r'SMOKE qualification failed: smoke-claude-A: claude-init: A init plugins')
        with tempfile.TemporaryDirectory() as temp:
            output, _ = self.smoke(Path(temp))
            (output / 'verdict-smoke-codex-A.json').write_text(json.dumps({'status': 'STOP', 'reason': 'locator: x'}))
            self.assert_refused(Path(temp), r'smoke-codex-A: verdict is STOP \(locator: x\)')

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
            seal = json.loads(Path(instructions.seal(runtime)).read_text())
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
                with self.assertRaisesRegex(ValueError, 'tarball identity|differs from its tarball|B package is 4.3.29'):
                    instructions.seal(runtime)
                self.assertFalse((Path(temp) / 'instructions.seal.json').exists())


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
                        text.replace('[projects."/work"]', '[projects."/elsewhere"]')):
            with mock.patch.object(prepare.base, 'codex_toml', return_value=variant):
                with self.assertRaisesRegex(ValueError, 'still disables plugins|inherited Codex project trust'):
                    prepare.codex_config(OWNER['codex'])
        self.assertEqual(prepare.codex_config(OWNER['codex']), CODEX_TOML)

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
                     'strict_config_check.py'):
            text = (HERE / name).read_text()
            for pattern in banned:
                self.assertIsNone(re.search(pattern, text), (name, pattern))
        text = (HERE / 'prepare.py').read_text()
        for flag in ('--strict-mcp-config', '--strict-config', '--mcp-config'):  # refused by devlyn run 4.3.30
            self.assertFalse(flag in text, flag)
        self.assertEqual((prepare.ARMS, prepare.CONFIGS), (('A', 'B'), ('claude', 'codex')))
        self.assertFalse(hasattr(run_cell, 'codex_limits') or hasattr(run_cell, 'claude_limits_with_account'))


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
            return argv, json.loads((out / 'run/result.json').read_text()), str(root / 'control/packages/B'), record

    def test_install_mount_only_for_b(self):
        b, _, install, _ = self.owner('B', {'OOMKilled': False, 'ExitCode': 0})
        a, _, _, _ = self.owner('A', {'OOMKilled': False, 'ExitCode': 0})
        self.assertIn(f'type=bind,src={install},dst=/install,readonly', b)
        self.assertEqual(b[b.index('sha256:image'):], ['sha256:image', 'claude', '-p', 'x'])
        self.assertFalse([value for value in a if '/install' in value])
        targets = lambda argv: [value.split('dst=')[1] for value in argv if 'dst=' in value]
        self.assertEqual(targets(b), targets(a) + ['/install,readonly'])

    def test_container_end_is_recorded(self):
        _, result, _, record = self.owner('A', {'OOMKilled': True, 'ExitCode': 137}, status_code=137)
        self.assertEqual(result['container'], {'oom_killed': True, 'exit_code': 137})
        self.assertEqual((record['owner_status'], record['teardown']), ('EXITED_NONZERO', 'CLEAN'))


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
        cases = [({'oom_killed': True, 'exit_code': 0}, 'EXITED_0', True),
                 ({'oom_killed': True, 'exit_code': 137}, 'HANG_TIMEOUT', True),
                 ({'oom_killed': False, 'exit_code': 137}, 'EXITED_NONZERO', True),
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
            (root / 'home/.codex').mkdir(parents=True)
            (root / 'home/.codex/auth.json').write_text('{"fake": true}')
            runtime = {'output': str(root), 'auth': str(root / 'auth')}
            profile = {'account': {'uuid': 'a'}, 'organization': {'uuid': 'o'}}
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


class RunFlow(unittest.TestCase):
    def run_cell(self, root, *, task='D3', arm='B', config='claude', stderr='', stdout='', teardown='CLEAN',
                 container=None, violations=()):
        output = root / 'output'
        output.mkdir()
        runtime = dict(output=str(output), auth=str(root / 'auth'), control=str(root / 'control'), image='image',
                       models_cache=str(root / 'models'), scratch=str(root / 'scratch'),
                       check_lock=str(root / 'check.lock'))
        (root / 'auth').mkdir()
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
            return out
        owner = dict(owner_status='EXITED_0', seconds=1, teardown=teardown, teardown_error='survived',
                     identity={'status': 'MATCH'}, container=container or {'oom_killed': False, 'exit_code': 0})
        venue = dict(account=['dispatch', 'org'], token_seconds_left=5000)
        checks = dict(product_check_pass=True, oracle={}, scope_violations=[], adjudication_needed=False)
        held = []

        def locked_check(*_):
            with open(runtime['check_lock'], 'a') as probe:
                try:
                    fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    held.append(True)
            return checks
        patches = dict(instructions=mock.patch.object(run_cell.instructions, 'check', return_value=list(violations)),
                       locate=mock.patch.object(run_cell.locate, 'locate', return_value={}),
                       check=mock.patch.object(run_cell.check, 'check', side_effect=locked_check),
                       assess=mock.patch.object(run_cell.assess, 'assess', return_value=[]),
                       limits=mock.patch.object(run_cell, 'claude_limits', side_effect=AssertionError('window read')))
        with mock.patch.object(run_cell, 'image_identity', return_value=True), \
                mock.patch.object(run_cell, 'preflight', return_value=(venue, None)), \
                mock.patch.object(run_cell, 'control_unchanged', return_value=True), \
                mock.patch.object(run_cell.prepare, 'prepare', side_effect=prepared), \
                mock.patch.object(run_cell.subprocess, 'check_output', return_value='commit'), \
                mock.patch.object(run_cell.cell_run, 'run', return_value=owner), \
                mock.patch.object(run_cell, 'seal_after_teardown', return_value=('seal', [])), \
                mock.patch.object(run_cell.usage, 'record',
                                  return_value=dict(completeness='COMPLETE', input_tokens=1, output_tokens=1)), \
                mock.patch.object(run_cell.quota, 'classify', return_value={'execution': []}), \
                mock.patch.object(run_cell.diagnostics, 'record', return_value={}), \
                mock.patch.object(run_cell, 'harness_unchanged', return_value=True), \
                mock.patch.object(run_cell, 'assessment_snapshot', return_value=(dict(account=['a', 'o']), None)):
            mocks = {name: patch.start() for name, patch in patches.items()}
            try:
                code = run_cell.run(runtime_path, 'cell-1', task, arm, config, expected_account=venue['account'])
            finally:
                mock.patch.stopall()
        verdict = json.loads((output / 'verdict-cell-1.json').read_text())
        return code, verdict, mocks, output / 'cell-1', held

    def assert_not_graded(self, mocks):
        for name in ('instructions', 'locate', 'check', 'assess'):
            mocks[name].assert_not_called()

    def test_launch_fault_stops_without_checks_or_assessors(self):
        with tempfile.TemporaryDirectory() as temp:
            code, verdict, mocks, _, _ = self.run_cell(Path(temp), stderr=SHAPES['status_lines']['refused'] + '\n')
            self.assertEqual((code, verdict['status']), (2, 'STOP'))
            self.assertEqual(verdict['reason'],
                             'B launch fault: run-argument-unsupported {"engine":"codex","argument":"-C"}')
            self.assert_not_graded(mocks)

    def test_memory_kill_stops_without_checks_or_assessors(self):
        with tempfile.TemporaryDirectory() as temp:
            code, verdict, mocks, _, _ = self.run_cell(Path(temp), arm='A', container={'oom_killed': True,
                                                                                     'exit_code': 137})
            self.assertEqual(verdict['reason'], 'memory kill: OOMKilled=True exit_code=137 owner EXITED_0')
            self.assert_not_graded(mocks)

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
            self.assertEqual(verdict['claude_account_before'], ['dispatch', 'org'])
            mocks['limits'].assert_not_called()
            args = mocks['instructions'].call_args.args
            self.assertEqual((args[0], args[1]['arm'], args[2]['qualification']['status']), (out, 'B', 'PASS'))
            seal = json.loads((out / 'seal.json').read_text())
            self.assertEqual({name: entry['path'] for name, entry in seal['modules'].items()}, {
                'prepare': '0265/prepare.py', 'cell': '0265/cell.py', 'record_usage': '0256/record_usage.py',
                'locate': '0233/locate.py', 'check': '0233/check.py', 'assess': '0265/assess.py',
                'quota': '0265/quota.py', 'diagnostics': '0233/diagnostics.py',
                'run_cell0222': '0222/run_cell.py', 'instructions': '0265/instructions.py'})
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
        with tempfile.TemporaryDirectory() as temp:
            code, verdict, mocks, _, _ = self.run_cell(Path(temp), violations=['status-line: B stderr has []'])
            self.assertEqual((code, verdict['reason']), (2, 'instruction assertion: status-line: B stderr has []'))
            for name in ('locate', 'check', 'assess'):
                mocks[name].assert_not_called()

    def test_arms_and_configs_guard(self):
        for arm, config in (('C', 'claude'), ('A', 'grok')):
            with self.assertRaisesRegex(ValueError, 'arm A/B and config claude/codex'):
                run_cell.run('/nonexistent/runtime.json', 'x', 'D3', arm, config)


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


class StrictConfig(unittest.TestCase):
    def test_configs_add_exactly_two_unknown_keys(self):
        allowed, violating = strict.configs()
        self.assertEqual(allowed, CODEX_TOML)
        parsed, loose = tomllib.loads(allowed), tomllib.loads(violating)
        self.assertIs(loose.pop(strict.UNKNOWN[0]), True)
        self.assertIs(loose['features'].pop(strict.UNKNOWN[1]), True)
        self.assertEqual(loose, parsed)

    def check(self, answers):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'models.json').write_text('{}')
            runtime = root / 'runtime.json'
            runtime.write_text(json.dumps(dict(image='sha256:image', scratch=str(root), auth=str(root / 'auth'),
                                               models_cache=str(root / 'models.json'))))
            calls, configs = [], []

            def runner(argv):
                calls.append(argv)
                if argv[:2] == ['docker', 'run']:
                    home = next(v for v in argv if v.endswith('dst=/home/probe')).split('src=')[1].split(',dst=')[0]
                    configs.append(Path(home, '.codex/config.toml').read_text())
                    return answers[len(configs) - 1]
                return 0, '', ''
            printed = io.StringIO()
            with mock.patch('sys.stdout', printed):
                code = strict.main(runtime, runner)
            return code, calls, configs, printed.getvalue()

    def test_pass_when_the_file_loads_and_the_violating_one_fails_at_load(self):
        code, calls, configs, printed = self.check([(0, '[]', ''), (1, '', 'Error: unknown field `zz_unknown_top_0265`')])
        self.assertEqual(code, 0)
        self.assertEqual(configs, list(strict.configs()))
        for argv in calls:
            self.assertEqual(argv[argv.index('--network') + 1], 'none')
            self.assertEqual(argv[-5:], ['codex', '--strict-config', 'debug', 'prompt-input', 'Reply OK.'])
            self.assertFalse([value for value in argv if 'auth.json' in value or 'codex.json' in value])
        self.assertTrue(printed.startswith('PASS'))

    def test_fail_when_the_0265_file_does_not_load_or_fails_for_another_reason(self):
        self.assertEqual(self.check([(1, '', 'Error: unknown field `rollout_budget`'), (1, '', 'x')])[0], 1)
        self.assertEqual(self.check([(0, '', ''), (1, '', 'network unreachable')])[0], 1)

    def test_undecided_prints_the_exec_commands_without_running_them(self):
        for answers in ([(1, '', 'Error: `--strict-config` is not supported for `codex debug`\n')] * 2,
                        [(2, '', "error: unexpected argument '--strict-config' found")] * 2,
                        [(0, '', ''), (0, '', '')]):
            code, calls, _, printed = self.check(answers)
            self.assertEqual(code, 3)
            self.assertEqual(len(calls), 2)
            self.assertFalse([argv for argv in calls if 'exec' in argv])
            commands = [line for line in printed.splitlines() if line.startswith('docker run')]
            self.assertEqual(len(commands), 2)
            for command in commands:
                self.assertIn('codex exec --strict-config --json --skip-git-repo-check', command)

    def test_a_timed_out_run_is_removed(self):
        code, calls, _, _ = self.check([(None, '', 'timed out after 180 s'), (1, '', 'zz_unknown_feature_0265')])
        self.assertEqual(code, 1)
        self.assertEqual(calls[1][:3], ['docker', 'rm', '-f'])


if __name__ == '__main__':
    unittest.main()
