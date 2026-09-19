"""Prepare fresh workflow-only tasks; no target-model calibration or ranking."""
from pathlib import Path
import json
import shutil
import subprocess
import sys

R = Path(__file__).resolve().parents[3]
H = Path(__file__).resolve().parent
E = R / '.devlyn/0187'

DURATION = '''def format_duration(milliseconds):
    return str(milliseconds) + "ms"


def parse_duration(text):
    raise NotImplementedError("duration parser requested")
'''
STREAM = '''class ParseError(ValueError):
    def __init__(self, line, reason):
        self.line = line
        self.reason = reason
        super().__init__(f"line {line}: {reason}")


class Decoder:
    def __init__(self, max_line_bytes=1048576):
        self.max_line_bytes = max_line_bytes

    def feed(self, chunk):
        raise NotImplementedError("incremental decoder requested")

    def finish(self):
        raise NotImplementedError("incremental decoder requested")
'''


def main():
    for case, name, source in [('root', 'duration', DURATION), ('filter', 'stream', STREAM)]:
        target = E / 'inputs' / case
        (target / 'tests').mkdir(parents=True, exist_ok=False)
        (target / (name + '.py')).write_text(source)
        shutil.copyfile(H / ('test_' + name + '.py'), target / 'tests/test_acceptance.py')
        (target / '.gitignore').write_text('.devlyn/\n.agents/\n__pycache__/\n*.pyc\n')
        command = '/opt/homebrew/bin/python3 -B -m unittest discover -s tests -v'
        request = (H / (name + '.md')).read_text().replace('python3 -B -m unittest', '/opt/homebrew/bin/python3 -B -m unittest')
        (target / 'spec.md').write_text(request)
        (target / 'spec.expected.json').write_text(json.dumps({
            'required_files': [name + '.py'],
            'forbidden_files': ['spec.md', 'spec.expected.json', '.gitignore', 'tests/test_acceptance.py'],
            'verification_commands': [{'cmd': command, 'exit_code': 0, 'timeout_sec': 90}]
        }, indent=2) + '\n')
    shutil.copyfile(Path.home() / '.codex/models_cache.json', E / 'models_cache.json')
    shutil.copyfile(R / '.devlyn/0179/catalog-setting.txt', E / 'catalog-setting.txt')
    print('Prepared two fresh synthetic tasks; root/filter are legacy runner case IDs only.')


if __name__ == '__main__':
    main()
