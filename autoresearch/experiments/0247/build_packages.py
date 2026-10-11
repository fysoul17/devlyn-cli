"""Pack the integrated 4.2.4 solo baseline with 0247 native JSONL answer framing.

No model call. The caller explicitly selects the verified integration checkout;
the old 0238 builder and all previously built packages remain untouched.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
BASE = '85004d8b3424488cb65bd593ea2d7354998ddb87'
spec = importlib.util.spec_from_file_location('builder0238_integrated', HERE.parent / '0238/build_packages.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)


def build(destination, toolchain, source):
    source = source.resolve()
    head = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if head != BASE:
        raise ValueError('integration checkout must retain the registered 4.2.4 base')
    legacy.BASE, legacy.REPO, legacy.HERE = BASE, source, HERE
    result = legacy.build(destination, toolchain)
    result.update(builder_adapter_sha256=legacy.sha(Path(__file__)), source_repository=str(source))
    (destination / 'packages.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--toolchain', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    result = build(args.destination.resolve(), args.toolchain.resolve(), args.source)
    print(json.dumps({arm: row['sha256'] for arm, row in result['packages'].items()}))
