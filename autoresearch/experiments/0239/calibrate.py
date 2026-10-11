"""Offline selected-runtime installation and evaluator check; no authentication or models."""
import importlib.util
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('init_runner', HERE.parent / '0237/runner-init-v1.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def main(runtime):
    runner = module.Runner(runtime)
    dest = runtime.parent / 'calibration'
    dest.mkdir(exist_ok=False)
    records, prepared = [], {}
    for name, task, arm in (('cal-b-config', 'CFG-LIFE', 'B'),
                            ('cal-c-config', 'CFG-LIFE', 'C'),
                            ('cal-b-short', 'FG-SHORT', 'B'),
                            ('cal-b-long', 'FG-LONG', 'B')):
        out = runner.prepare(name, task, arm, 'claude')
        work = out / 'cell/work'
        package = Path(runner.runtime['control']) / 'packages' / arm / 'package'
        installed = work / '.claude/skills/_shared'
        for file in ('task-completion.md', 'task-complete.py'):
            if (installed / file).read_bytes() != (package / 'config/skills/_shared' / file).read_bytes():
                raise ValueError('installed payload mismatch: ' + name + '/' + file)
        runner.unchanged(out)
        prepared[name] = out
        records.append({'name': name, 'task': task, 'arm': arm,
                        'guide_sha256': module.frozen.digest(installed / 'task-completion.md'),
                        'seal_sha256': module.frozen.digest(out / 'seal.json')})
    b, c = (prepared['cal-' + arm + '-config'] / 'cell/work' for arm in ('b', 'c'))
    for file in ('AGENTS.md', 'CLAUDE.md'):
        if (b / file).read_bytes() != (c / file).read_bytes():
            raise ValueError('installed root differs: ' + file)
    controls = []
    for variant, expected in (('gold', 12), ('visible', 1)):
        work = dest / variant
        shutil.copytree(HERE / 'fixtures/CFG-LIFE' / variant, work / 'visible')
        result = runner.evaluate(work, 'CFG-LIFE', runner.runtime)
        module.frozen.write(dest / (variant + '-raw.json'), result)
        passes = [row['id'] for row in result['rows'] if row['status'] == 'PASS']
        if len(passes) != expected or any(row['exit_code'] != 0 for row in result['public']):
            raise ValueError('unexpected evaluator control: ' + variant)
        if variant == 'visible' and passes != ['schema-errors-retain-include-chain']:
            raise ValueError('baseline failure pattern changed')
        controls.append({'variant': variant, 'passes': passes, 'public_exit': 0})
    for out in prepared.values():
        runner.unchanged(out)
    report = {'prepared': records, 'controls': controls, 'status': 'PASS',
              'native_calls': 0, 'auth_calls': 0, 'runtime_sha256': module.frozen.digest(runtime)}
    module.frozen.write(dest / 'result.json', report)
    print(json.dumps(report))


if __name__ == '__main__':
    main(Path(sys.argv[1]).resolve())
