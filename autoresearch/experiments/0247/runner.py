"""Prospective LF record framing and consistent native startup catalogs."""
from functools import partial
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


legacy = load('runner0245_jsonl_catalogs', HERE.parent / '0245/runner.py')
discovery = load('capture0247', HERE / 'capture_discovery.py')
read, write, digest = legacy.read, legacy.write, legacy.digest


def objects(text):
    """Preserve tolerant dict-row decoding, framed on JSONL's LF only."""
    out = []
    for line in text.split('\n'):
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict):
            out.append(value)
    return out


def lines(path):
    return objects(path.read_text(errors='replace')) if path.is_file() else []


def cell_lines(path):
    return objects(path.read_text(errors='replace')) if path.exists() else []


def events(path):
    return objects(path.read_text(errors='replace'))


class Runner(legacy.Runner):
    def __init__(self, runtime_path, tasks_path=None):
        super().__init__(runtime_path, tasks_path)
        evidence = self.frame.cell_run.evidence
        if self.frame.usage.evidence is not evidence:
            raise ValueError('identity and usage must share one evidence inventory')
        evidence.lines = lines
        self.frame.cell_run.lines = cell_lines
        self.frame.cell_run.legacy.lines = cell_lines
        self.frame.usage.base.events = events
        evidence.claude_envelopes = partial(discovery.claude_envelopes, evidence=evidence)

    def boot_catalogs(self, out, config):
        if config != 'claude':
            return None
        rows = [event for event in self.frame.cell_run.lines(out / 'run/stdout')
                if event.get('type') == 'system' and event.get('subtype') == 'init']
        keys = ('skills', 'plugins', 'mcp_servers')
        if not rows or any(
                any(not isinstance(row.get(key), list) for key in keys)
                or any(not isinstance(row.get(key), str) or not row[key].strip()
                       for key in ('session_id', 'model')) for row in rows):
            raise ValueError('Claude startup catalog missing or malformed')
        if len({(row['session_id'], row['model']) for row in rows}) != 1:
            raise ValueError('Claude startup identity conflicts')
        catalogs = [{key: sorted(row[key], key=lambda value: json.dumps(value, sort_keys=True))
                     for key in keys} for row in rows]
        if any(catalog != catalogs[0] for catalog in catalogs[1:]):
            raise ValueError('Claude startup catalogs conflict')
        return catalogs[0]

    def inputs(self):
        result = super().inputs()
        paths = [HERE / name for name in ('runner.py', 'peer.py', 'capture_discovery.py',
                 'build_packages.py', 'results/stage.py', 'guides/H.md', 'guides/P.md', 'guides/S.md')]
        result.update({str(path): digest(path) for path in paths})
        return result


if __name__ == '__main__':
    legacy.legacy.legacy.legacy.legacy.legacy.Runner = Runner
    sys.exit(legacy.legacy.legacy.legacy.legacy.legacy.main())
