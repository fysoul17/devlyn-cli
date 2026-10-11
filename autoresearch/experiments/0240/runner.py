"""Single-peer treatment over frozen 0238; owner routes and all base gates remain."""
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


legacy = load('runner0238_single_peer', HERE.parent / '0238/runner.py')
base_policy = legacy.policy
read, write, digest, delivery = legacy.read, legacy.write, legacy.digest, legacy.delivery


def check(out, plan, tasks, evidence):
    result = base_policy.check(out, plan, tasks, evidence)
    for engine in ('codex', 'claude'):
        for thread, (role, root) in result[engine + '_roles'].items():
            if role == 'peer' and thread != root:
                result['protocol_violations'].append(f'{engine} peer delegated to native child {thread}')
    result['protocol_violations'] = sorted(set(result['protocol_violations']))
    return result


# This private imported module is used only by this adapter; no historical file changes.
policy = SimpleNamespace(route_for=base_policy.route_for, receipts=base_policy.receipts, check=check)
legacy.policy = policy
BaseRunner = legacy.Runner


class Runner(BaseRunner):
    def inputs(self):
        result = super().inputs()
        paths = [HERE / name for name in ('runner.py', 'peer.py', 'build_packages.py',
                                         'results/stage.py', 'guides/H.md', 'guides/P.md', 'guides/S.md')]
        paths += [HERE.parent / '0238' / name for name in ('build_packages.py', 'results/stage.py')]
        result.update({str(path): digest(path) for path in paths})
        return result


if __name__ == '__main__':
    legacy.Runner = Runner
    sys.exit(legacy.main())
