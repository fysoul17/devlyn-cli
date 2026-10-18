"""Count installed task-completion.md and bind unchanged installed root instructions.

The CLI calls Claude count_tokens with host keychain OAuth, never printed.
Registration requires both counts to decrease or tie and identical root files.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('pack_gate_rpd8', HERE / 'pack.py')
pack = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pack)
require = pack.require
NAMES = ('task-completion.md', 'CLAUDE.md', 'AGENTS.md')


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def managed_block(raw):
    body = (b'Project-specific instructions outside this managed block take precedence over these defaults.\n\n'
            + raw.replace(b'\r\n', b'\n').removesuffix(b'\n') + b'\n')
    return (b'<!-- devlyn:instructions:begin sha256=' + sha256(body).encode() + b' -->\n' + body
            + b'<!-- devlyn:instructions:end -->\n')


def expected_hashes(arms_file):
    arms = pack.verify_arms(Path(arms_file))
    expected = {name: [] for name in NAMES}
    for arm in ('X', 'Y'):
        archive = Path(arms_file).parent / arms[arm]['tarball']
        expected['task-completion.md'].append({sha256(pack.content(archive))})
        for name in ('CLAUDE.md', 'AGENTS.md'):
            hashes = {sha256(managed_block(pack.content(archive, name)))}
            if name == 'CLAUDE.md':
                hashes.add(sha256(b'@AGENTS.md\n'))
            expected[name].append(hashes)
    return expected


def validate(record, arms_file):
    """Revalidate a registration record before staging or dispatch."""
    require(record.get('schema') == 'rp-d8-token-gate-v1' and record.get('passed') is True and
            record.get('arms_sha256') == sha256(Path(arms_file).read_bytes()) and set(record.get('rows', {})) == set(NAMES),
            'token gate missing pack binding or pass')
    expected = expected_hashes(arms_file)
    for name in NAMES:
        row = record['rows'][name]
        hashes = row.get('sha256')
        require(isinstance(hashes, list) and len(hashes) == 2 and
                all(isinstance(value, str) and re.fullmatch('[a-f0-9]{64}', value) and value in allowed
                    for value, allowed in zip(hashes, expected[name])), 'token gate installed-file binding mismatch')
        if name == 'task-completion.md':
            for tokenizer in ('claude', 'o200k'):
                counts = row.get(tokenizer)
                require(isinstance(counts, list) and len(counts) == 2 and
                        all(type(value) is int and value >= 0 for value in counts) and counts[1] <= counts[0],
                        'token gate exceeds X or has invalid counts')
        else:
            require(row.get('identical') is True and hashes[0] == hashes[1],
                    'installed CLAUDE.md/AGENTS.md differ between arms')
    return record


def evaluate(arms_file, paths, claude_count, encoding):
    """Callbacks make count decisions testable without credentials or network."""
    require(set(paths) == set(NAMES), 'all three installed file pairs are required')
    expected = expected_hashes(arms_file)
    rows = {}
    for name in NAMES:
        pair = [Path(path) for path in paths[name]]
        require(len(pair) == 2 and all(path.is_file() and not path.is_symlink() for path in pair),
                'installed inputs must be regular files')
        raw = [path.read_bytes() for path in pair]
        hashes = [sha256(value) for value in raw]
        require(all(value in allowed for value, allowed in zip(hashes, expected[name])),
                'installed file differs from verified arm')
        row = dict(sha256=hashes, bytes=[len(value) for value in raw])
        if name == 'task-completion.md':
            bodies = [value.decode('utf-8') for value in raw]
            row.update(claude=[claude_count(body) for body in bodies],
                       o200k=[len(encoding.encode(body)) for body in bodies])
            require(all(type(value) is int and value >= 0 for tokenizer in ('claude', 'o200k')
                        for value in row[tokenizer]), 'tokenizer returned invalid counts')
        else:
            row['identical'] = raw[0] == raw[1]
        rows[name] = row
    passed = (all(rows['task-completion.md'][key][1] <= rows['task-completion.md'][key][0]
                  for key in ('claude', 'o200k')) and all(rows[name]['identical'] for name in NAMES[1:]))
    return dict(schema='rp-d8-token-gate-v1', arms_sha256=sha256(Path(arms_file).read_bytes()), rows=rows, passed=passed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('x_task', type=Path)
    parser.add_argument('y_task', type=Path)
    parser.add_argument('x_claude', type=Path)
    parser.add_argument('y_claude', type=Path)
    parser.add_argument('x_agents', type=Path)
    parser.add_argument('y_agents', type=Path)
    parser.add_argument('--arms', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    # Keep the inherited OAuth endpoint and encoding. Imports do not count or
    # obtain credentials; only this explicit operator command does either.
    spec = importlib.util.spec_from_file_location('gate_rpd6_rpd8', HERE.parent / 'rp-d6-claude-delivery/rendered_gate.py')
    counter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(counter)
    raw = subprocess.run(['security', 'find-generic-password', '-s', 'Claude Code-credentials', '-w'],
                         capture_output=True, text=True, check=True).stdout
    token = json.loads(raw)['claudeAiOauth']['accessToken']
    result = evaluate(args.arms, {
        'task-completion.md': [args.x_task, args.y_task],
        'CLAUDE.md': [args.x_claude, args.y_claude],
        'AGENTS.md': [args.x_agents, args.y_agents],
    }, lambda text: counter.claude_tokens(text, token), counter.tiktoken.get_encoding('o200k_base'))
    pack.write(args.output, result)
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
