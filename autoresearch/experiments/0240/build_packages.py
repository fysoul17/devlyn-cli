"""Build the single-peer packages through unchanged 0238 history-aware packing."""
import argparse
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('builder0238_single_peer', HERE.parent / '0238/build_packages.py')
legacy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(legacy)
legacy.HERE = HERE


def build(dest, toolchain):
    result = legacy.build(dest, toolchain)
    result['builder_adapter_sha256'] = legacy.sha(Path(__file__))
    (dest / 'packages.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--toolchain', type=Path, required=True)
    args = parser.parse_args()
    result = build(args.destination.resolve(), args.toolchain.resolve())
    print(json.dumps({arm: record['sha256'] for arm, record in result['packages'].items()}))
