"""Prospective peer capability and invocation-provenance repairs over frozen 0241."""
import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


legacy = load('runner0241_direct_helper', HERE.parent / '0241/runner.py')
base_policy = load('policy0242', HERE / 'policy.py')
# Reuse 0240's peer-descendant check; replace its base check before evaluation.
# The imported chain is private to this adapter; no historical module file changes.
legacy.legacy.base_policy = base_policy
policy = legacy.policy
policy.route_for, policy.receipts = base_policy.route_for, base_policy.receipts
read, write, digest, delivery = legacy.read, legacy.write, legacy.digest, legacy.delivery
discovery, BaseRunner = legacy.discovery, legacy.Runner


class Runner(BaseRunner):
    def inputs(self):
        result = super().inputs()
        paths = [HERE / name for name in ('runner.py', 'peer.py', 'policy.py', 'build_packages.py',
                 'results/stage.py', 'guides/H.md', 'guides/P.md', 'guides/S.md')]
        result.update({str(path): digest(path) for path in paths})
        return result


if __name__ == '__main__':
    legacy.legacy.legacy.Runner = Runner
    sys.exit(legacy.legacy.legacy.main())
