"""0237's serial, single-cell adapter over the frozen 0233 apparatus.

run|prepare <runtime.json> <name> <task> <A|B|C> <claude|codex>
assess <runtime.json> <name> is a separate, optional model expense.
Exit 0: deterministic outcome recorded; 2: STOP; 3: auth refused before dispatch.
No quota probe or assessor model is launched by prepare or run's preflight.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import tomllib

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
_spec = importlib.util.spec_from_file_location('delivery0237', HERE / 'delivery.py')
delivery = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(delivery)


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_frame():
    spec = importlib.util.spec_from_file_location('frame0237', HERE.parent / '0233/run_cell.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Runner:
    def __init__(self, runtime_path, tasks_path=None):
        self.runtime_path = Path(runtime_path).resolve()
        self.runtime = read(self.runtime_path)
        self.tasks_path = Path(tasks_path if tasks_path is not None else
                               self.runtime.get('tasks_file', HERE / 'tasks.json')).resolve()
        self.tasks = read(self.tasks_path)
        self.frame = load_frame()
        m = self.frame
        for module in (m.prepare, m.check, m.check.base, m.assess, m.cell_run.evidence, m.usage.evidence):
            module.TASKS = self.tasks
        m.prepare.HERE = self.tasks_path.parent
        m.prepare.source = self.source
        m.prepare.native_prompt = self.native_prompt
        m.check.SECONDS = m.check.base.SECONDS = self.tasks['watchdog_seconds']['evaluator']
        self.original_evaluate = m.check.evaluate
        m.check.evaluate = self.evaluate
        self.packet = m.prepare.packet

    def task(self, task_id):
        return next(task for task in self.tasks['tasks'] if task['id'] == task_id)

    def native_prompt(self, caller):
        return ((HERE.parent / '0232/common.txt').read_text() + '\n' +
                (HERE / 'local-delivery.txt').read_text() +
                '\nCALLER CONTRACT\n' + json.dumps(caller, indent=2))

    def source(self, task, runtime, work, base):
        if 'source_dir' not in task and 'eq3_dir' not in task:
            return base.source(task, runtime, work)
        root = Path(runtime.get('source_root', REPO))
        source = root / task.get('eq3_dir', task.get('source_dir', ''))
        target = work
        if 'eq3_dir' in task:
            source, target = source / 'visible', work / 'visible'
        shutil.copytree(source, target, symlinks=True)
        if self.packet.content(self.packet.tree(work)) != task['source_sha256']:
            raise ValueError(task['id'] + ': registered source changed')
        git = self.frame.prepare.git
        git(work, 'init', '-q', '-b', 'main')
        for key, value in (('user.name', 'Participant'), ('user.email', 'participant@localhost'),
                           ('commit.gpgsign', 'false')):
            git(work, 'config', key, value)
        git(work, 'add', '-A')
        if (work / 'node_modules').exists():
            git(work, 'add', '-f', '-A', 'node_modules')
        git(work, 'commit', '-qm', 'registered participant inputs')
        with (work / '.git/info/exclude').open('a') as stream:
            stream.write('.devlyn/\n')

    def inputs(self):
        """Prospective seals include imported implementation, prompts and every control tree."""
        paths = {self.runtime_path, self.tasks_path, Path(__file__), HERE.parent / '0232/common.txt',
                 HERE / 'delivery.py', HERE / 'local-delivery.txt'}
        paths.update(HERE.parent / path for path in ('0211/packet.py', '0210/native_accounting.py', '0208/accounting.py'))
        for iteration in ('0222', '0232', '0233'):
            paths.update((HERE.parent / iteration).glob('*.py'))
        if self.runtime.get('models_cache'):
            paths.add(Path(self.runtime['models_cache']))
        paths.add(Path(self.runtime['control'] + '.manifest.json'))
        return {str(path): digest(path) for path in sorted(paths)}

    def validate(self, name):
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', name):
            raise ValueError('cell name must be one safe path component')
        if not re.fullmatch(r'sha256:[a-f0-9]{64}', self.runtime['image']):
            raise ValueError('image must be its exact sha256 identity, never a mutable tag')
        if self.tasks['watchdog_seconds']['owner'] != 5400:
            raise ValueError('0237 owner watchdog must be 5400 seconds')
        manifest = read(self.runtime['control'] + '.manifest.json')
        if set(manifest['manifests']) != {'public', 'oracle', 'packages'}:
            raise ValueError('control manifest must seal public, oracle and packages')
        if not self.frame.control_unchanged(self.runtime):
            raise ValueError('control changed')
        actual = subprocess.check_output(['docker', 'image', 'inspect', self.runtime['image'], '--format', '{{.Id}}'], text=True).strip()
        if actual != self.runtime['image']:
            raise ValueError('image identity mismatch')

    def prepare(self, name, task, arm, config):
        self.validate(name)
        prospective = self.inputs()
        out = self.frame.prepare.prepare(self.runtime, name, task, arm, config)
        plan = read(out / 'plan.json')
        # Keep project instructions/skills enabled while excluding account-synced context.
        settings = out / 'home/.claude/settings.json'
        write(settings, dict(syncClaudeAiSkills=False, syncClaudeAiPlugins=False))
        plan['env']['ENABLE_CLAUDEAI_MCP_SERVERS'] = 'false'
        if config == 'claude':
            plan['argv'][1:1] = ['--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}']
        elif config == 'codex':
            codex_config = out / 'home/.codex/config.toml'
            text = codex_config.read_text()
            inherited = '[projects."/work"]'
            if (text.count(inherited) != 1 or tomllib.loads(text).get('projects') !=
                    {'/work': {'trust_level': 'trusted'}}):
                raise ValueError('unexpected inherited Codex project trust')
            cwd = plan['argv'][plan['argv'].index('-C') + 1]
            codex_config.write_text(text.replace(inherited, '[projects.' + json.dumps(cwd) + ']'))
        write(out / 'plan.json', plan)
        boot = ['plan.json', 'baseline.json', 'prompt.txt', 'home/.claude/settings.json']
        if (out / 'home/.codex/config.toml').exists():
            boot.append('home/.codex/config.toml')
        write(out / 'seal.json', dict(inputs=prospective, image=self.runtime['image'],
                                      prepared={name: digest(out / name) for name in boot}))
        self.unchanged(out)
        return out

    def unchanged(self, out):
        seal = read(out / 'seal.json')
        if self.inputs() != seal['inputs'] or not self.frame.control_unchanged(self.runtime):
            raise ValueError('prospective inputs or control changed')
        if any(digest(out / name) != value for name, value in seal['prepared'].items()):
            raise ValueError('prepared cell changed')
        if not self.frame.harness_unchanged(out, read(out / 'baseline.json')):
            raise ValueError('harness changed')

    def evaluate(self, work, task_id, runtime):
        task = self.task(task_id)
        if 'eq3_dir' not in task:
            return self.original_evaluate(work, task_id, runtime)
        check = self.frame.check
        public = [check.in_image(runtime, work, ['sh', '-c',
                  'mkdir /tmp/public-work && cp -a /cell/work/. /tmp/public-work/ && cd /tmp/public-work && ' + cmd])
                  for cmd in task['public_checks']]
        for result in public:
            check.base.last_json(result)
        result = check.in_image(runtime, work, ['python3', '-B',
                   f'/control/autoresearch/eq3/{task_id}/oracle.py', '/cell/work/visible'])
        decoded = check.base.last_json(result)
        if decoded is None:
            if result['exit_code'] == 0:
                raise ValueError('EQ3 oracle returned malformed JSON')
            rows = [dict(id=name, status='FAIL') for name in task['oracle']]
        else:
            manifestations = decoded.get('manifestations')
            if (not isinstance(manifestations, list)
                    or any(not isinstance(row, dict) or type(row.get('passed')) is not bool
                           or not isinstance(row.get('id'), str) for row in manifestations)
                    or sorted(row['id'] for row in manifestations) != sorted(task['oracle'])):
                raise ValueError('EQ3 oracle manifestation coverage mismatch')
            rows = [dict(id=row['id'], status='PASS' if row['passed'] else 'FAIL') for row in manifestations]
        return dict(public=public, rows=rows, raw=[result])

    def preflight(self):
        """Copies host credentials and verifies the account through profile, never an inference."""
        Path(self.runtime['auth']).mkdir(parents=True, exist_ok=True, mode=0o700)
        return self.frame.base.snapshot_auth(self.runtime)

    def boot_expectation(self, arm, config):
        phase = self.runtime.get('phase')
        if phase not in ('smoke', 'measured'):
            raise ValueError('runtime phase must be smoke or measured')
        expected = self.runtime.get('boot_catalogs', {}).get(config, {}).get(arm)
        if config == 'claude' and phase == 'measured' and expected is None:
            raise ValueError('measured Claude requires boot_catalogs.claude.' + arm)
        if expected is not None and (not isinstance(expected, dict)
                or set(expected) != {'skills', 'plugins', 'mcp_servers'}
                or any(not isinstance(value, list) for value in expected.values())):
            raise ValueError('boot catalog must explicitly list skills, plugins and mcp_servers')
        return expected

    def boot_catalogs(self, out, config):
        if config != 'claude':
            return None  # Codex does not emit Claude's startup catalog; native session evidence is retained.
        rows = [event for event in self.frame.cell_run.lines(out / 'run/stdout')
                if event.get('type') == 'system' and event.get('subtype') == 'init']
        if len(rows) != 1 or any(not isinstance(rows[0].get(key), list)
                                 for key in ('skills', 'plugins', 'mcp_servers')):
            raise ValueError('Claude startup catalog missing or ambiguous')
        return {key: sorted(rows[0][key], key=lambda value: json.dumps(value, sort_keys=True))
                for key in ('skills', 'plugins', 'mcp_servers')}

    def run(self, name, task, arm, config):
        self.validate(name)
        expected_catalogs = self.boot_expectation(arm, config)
        output = Path(self.runtime['output'])
        output.mkdir(parents=True, exist_ok=True)
        verdict = output / f'verdict-{name}.json'
        if verdict.exists() or (output / name).exists():
            raise ValueError('cell already exists; preserve it and choose a new registered identity')
        venue, blocked = self.preflight()
        if blocked:
            write(output / f'not-dispatched-{name}.json', dict(reason=blocked))
            return 3
        out = self.prepare(name, task, arm, config)
        record = dict(cell=name, task=task, arm=arm, config=config, venue=venue,
                      phase=self.runtime['phase'], measurement_eligible=self.runtime['phase'] == 'measured',
                      assessment='NOT_REQUESTED', input_tokens=None, output_tokens=None, usage='UNKNOWN')
        started = time.monotonic()
        try:
            owner = self.frame.cell_run.run(out, self.runtime)
            record.update(owner_status=owner['owner_status'], owner_seconds=owner['seconds'],
                          identity=owner['identity'], teardown=owner['teardown'])
            sealed, errors = self.frame.seal_after_teardown(out)
            record['evidence_manifest_sha256'] = sealed
            usage = self.frame.usage.record(out)
            record['usage'] = usage['completeness']
            record['usage_gaps'] = usage['gaps']
            if usage['completeness'] == 'COMPLETE':
                record.update(input_tokens=usage['input_tokens'], output_tokens=usage['output_tokens'])
            else:
                record['known_usage_lower_bound'] = {key: usage[key] for key in ('input_tokens', 'output_tokens')}
            if owner['teardown'] != 'CLEAN' or errors:
                raise ValueError('teardown or evidence collection failed: ' + str(errors))
            if owner['identity']['status'] != 'MATCH':
                raise ValueError('model identity ' + owner['identity']['status'])
            record['cross_engine_sessions'] = [session for session in owner['identity'].get('owner_launched_sessions', [])
                                               if session.get('engine') != config]
            if record['cross_engine_sessions']:
                raise ValueError('S1 solo protocol: owner launched another engine')
            if usage['completeness'] != 'COMPLETE':
                raise ValueError('whole-run usage ' + usage['completeness'])
            record['boot_catalogs'] = self.boot_catalogs(out, config)
            if expected_catalogs is not None:
                expected_catalogs = {key: sorted(value, key=lambda item: json.dumps(item, sort_keys=True))
                                     for key, value in expected_catalogs.items()}
                if record['boot_catalogs'] != expected_catalogs:
                    raise ValueError('boot catalog contamination or drift')
            quota = self.frame.quota.classify(out)
            record['quota'] = quota
            if quota['execution']:
                raise ValueError('authentication or quota fault during execution')
            self.unchanged(out)
            record['snapshot'] = self.frame.locate.locate(out)
            evaluator_start = time.monotonic()
            checked = self.frame.check.check(out, self.runtime)
            delivered = delivery.check(out, record['snapshot'], self.frame.locate, self.packet)
            write(out / 'delivery.json', delivered)
            record.update(checked, source_check_pass=checked['product_check_pass'],
                          delivery=delivered, delivery_pass=delivered['passed'],
                          deterministic_seconds=time.monotonic() - evaluator_start)
            record['status'] = ('PRODUCT_INCOMPLETE' if not delivered['passed'] or owner['owner_status'] != 'EXITED_0'
                                else 'ADJUDICATE' if checked['adjudication_needed']
                                else 'CHECKS_PASS' if checked['product_check_pass']
                                else 'PRODUCT_INCOMPLETE')
            # This digest protects later assessment of exactly the source whose checks were recorded.
            write(out / 'checked.json', dict(snapshot=self.packet.tree(out / 'snapshot'),
                                             checks_sha256=digest(out / 'checks.json'),
                                             delivery_sha256=digest(out / 'delivery.json')))
        except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError) as exc:
            record.update(status='STOP', reason=f'{type(exc).__name__}: {exc}')
        record['run_and_checks_seconds'] = time.monotonic() - started
        write(verdict, record)
        return 2 if record['status'] == 'STOP' else 0

    def assess(self, name):
        self.validate(name)
        out = Path(self.runtime['output']) / name
        self.unchanged(out)
        checked = read(out / 'checked.json')
        if (checked['snapshot'] != self.packet.tree(out / 'snapshot')
                or checked['checks_sha256'] != digest(out / 'checks.json')
                or checked['delivery_sha256'] != digest(out / 'delivery.json')):
            raise ValueError('checked source or evidence changed before assessment')
        if (out / 'assessment').exists():
            raise ValueError('assessment already exists; preserve its original expense and result')
        _, blocked = self.preflight()
        if blocked:
            write(out / 'assessment-not-dispatched.json', dict(reason=blocked))
            return 3
        start = time.monotonic()
        records = self.frame.assess.assess(out, self.runtime)
        write(out / 'assessment-summary.json', dict(
            seconds=time.monotonic() - start, records=records, account='research-only; excluded from owner usage',
            status='STOP' if self.frame.base.unassessed(records) else 'ASSESSED'))
        return 2 if self.frame.base.unassessed(records) else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest='action', required=True)
    for name in ('run', 'prepare', 'assess'):
        action = actions.add_parser(name)
        action.add_argument('runtime', type=Path)
        action.add_argument('name')
        if name != 'assess':
            action.add_argument('task')
            action.add_argument('arm', choices=('A', 'B', 'C'))
            action.add_argument('config', choices=('claude', 'codex'))
    args = parser.parse_args()
    try:
        runner = Runner(args.runtime)
        if args.action == 'assess':
            return runner.assess(args.name)
        if args.action == 'prepare':
            print(runner.prepare(args.name, args.task, args.arm, args.config))
            return 0
        return runner.run(args.name, args.task, args.arm, args.config)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError) as exc:
        print(json.dumps(dict(status='STOP', reason=f'{type(exc).__name__}: {exc}')), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
