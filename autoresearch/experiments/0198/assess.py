"""Seal-checked external assessment, with anonymous output before arm decoding."""
from pathlib import Path
import importlib.util
import json
import random

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
E = REPO / '.devlyn/0198'


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def assess():
    runner = module('runner0198', HERE / 'run.py')
    checks = module('checks0198', HERE / 'check.py')
    runner.registered()
    finals = json.loads((E / 'FINAL-SEALED.json').read_text())
    initials = json.loads((E / 'INITIAL-SEALED.json').read_text())
    products = [(name + '-initial', Path(info['work']), info['seal']) for name, info in initials.items()]
    products += [(name, runner.WORKS / name, seal) for name, seal in finals.items()]
    random.Random(198).shuffle(products)
    baseline = runner.prior.seal(E / 'input')
    answers, mapping = {}, {}
    for i, (name, product, seal) in enumerate(products):
        label = f'product-{i + 1}'
        assert runner.prior.seal(product) == seal, 'unsealed product: ' + label
        result = checks.check(product)
        regression_rows = checks.regression(product)
        result['rows'] += regression_rows
        result['total'] += len(regression_rows)
        result['passed_checks'] += sum(r['passed'] for r in regression_rows)
        result['passed'] = all(r['passed'] for r in result['rows'])
        assert runner.prior.seal(product) == seal, 'oracle mutated product: ' + label
        current = runner.prior.seal(product)
        delta = sorted(p for p in set(baseline) | set(current) if baseline.get(p) != current.get(p) and not p.startswith('.devlyn/'))
        result['changed_paths'] = delta
        result['scope_pass'] = all(p in ('config/skills/_shared/resolve-bootstrap.py', 'tests/test_regression.py') for p in delta)
        result['oracle_complete'] = result['passed'] and result['scope_pass']
        answers[label] = result
        mapping[label] = name
        runner.native.put(E / 'assessment' / (label + '.json'), result)
        print(json.dumps(dict(label=label, passed=result['passed'], checks=result['passed_checks'], scope=result['scope_pass'])), flush=True)
    runner.native.put(E / 'assessment/results.blind.json', answers)
    runner.native.put(E / 'assessment/mapping.json', mapping)


if __name__ == '__main__':
    assess()
