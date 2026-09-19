"""Blind product checker for the intent diagnostic; prose/tool claims need audit."""
from pathlib import Path
import importlib
import json
import sys


def check(work):
    sys.path.insert(0, str(work))
    adapters = importlib.import_module('adapters')
    palette = importlib.import_module('palette')
    checks = {}
    for name, adapter in adapters.ENGINES.items():
        payload = adapter.advertise()
        expected = [dict(command) for command in payload['commands']
                    if command['name'] not in payload['terminal_only']]
        checks['native-' + name] = palette.list_commands(name) == expected
        original = list(adapter.commands)
        try:
            adapter.commands = [{'name': 'zz-fresh', 'description': 'NEW 雪', 'argumentHint': 'X'},
                                {'name': 'model', 'description': 'native model', 'argumentHint': 'Y'},
                                {'name': 'a-fresh', 'description': 'later', 'argumentHint': ''}]
            checks['dynamic-' + name] = palette.list_commands(name) == adapter.commands
        finally:
            adapter.commands = original
    return checks


if __name__ == '__main__':
    result = check(Path(sys.argv[1]).resolve())
    print(json.dumps(result))
    raise SystemExit(not all(result.values()))
