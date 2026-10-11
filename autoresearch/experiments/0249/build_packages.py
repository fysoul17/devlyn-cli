"""Pack the verified 4.2.5 integration with unchanged 0247 treatment bytes.

Reuse the history-aware builder. Its four-arm archive format is retained for
the existing staging verifier; only A/B/S are eligible in this confirmation.
No model call, source-checkout edit or new helper behavior.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
BASE = 'd1f170ed3bd57441b95ea525156e80644543acb1'
spec = importlib.util.spec_from_file_location('builder0238_425', HERE.parent / '0238/build_packages.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)


def build(destination, toolchain, source):
    source = source.resolve()
    head = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if head != BASE:
        raise ValueError('integration checkout must retain the registered 4.2.5 base')
    legacy.BASE, legacy.REPO, legacy.HERE = BASE, source, HERE.parent / '0247'
    result = legacy.build(destination, toolchain)
    result.update(builder_adapter_sha256=legacy.sha(Path(__file__)), source_repository=str(source),
                  selected_confirmation_arms=['A', 'B', 'S'],
                  treatment_source=str(HERE.parent / '0247'))
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
