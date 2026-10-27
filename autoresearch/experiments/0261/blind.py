"""Blind audit packets: blind.py packets <runtime.json> <out-dir>.

Only packets/ is handed to reviewers. label-map.json stays with root until judgments
are committed; its sha256 is printed. An existing output directory is never reused.
Transcripts come exclusively from run/stdout (Claude stream-json); no home/auth reads.
A STOP before grading has no checks/snapshot: explicitly mark absent checks and copy
its preserved cell and tmp end trees, excluding trace/Git/managed/dependency content.
Assessor-only regrades share the same owner evidence and are identified as such.
Symlinks are recorded as link text in symlinks.json, never followed or copied as links.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('blind_control0261', HERE / 'control.py')
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)
CELLS = [line.split() for line in (HERE / 'cells.tsv').read_text().splitlines() if line]
EXCLUDED = {'AGENTS.md', 'CLAUDE.md', '.agents', '.claude', '.devlyn-install.json',
            'node_modules', 'home', 'auth', '.git', 'trace'}


def credential_path(path):
    """Shared exclusion for tree paths and path tokens in tool inputs."""
    parts = str(path).replace('\\', '/').lower().split('/')
    return any(part in ('home', 'auth', '.codex', '.claude', '~', '$home', '${home}',
                        'auth.json', 'credentials') or part.startswith('.credentials') or
               part.endswith(('.pem', '.key')) or 'keychain' in part for part in parts)


def protected_input(value):
    if isinstance(value, dict):
        return any(protected_input(v) for v in value.values())
    if isinstance(value, list):
        return any(protected_input(v) for v in value)
    if not isinstance(value, str):
        return False
    # Include quoted paths/commands, argv arrays, Windows separators and shell operators.
    if any(credential_path(token) for token in re.split(r'''[\s'";|&()<>=]+''', value)):
        return True
    return bool(re.search(r'\bsecurity\s+find-generic-password\b', value) or
                re.search(r'''(?:^|[\s;|&(/'"])(?:env|printenv)(?=$|[\s;|&)'"])''', value) or
                # Bare set dumps variables; set with options/arguments does not.
                re.search(r'''(?:^|[;|&(\n'"])\s*set(?=\s*(?:$|[;|)\n]|&&|\d*[<>]|['"](?:$|[\s;|&)])))''', value))


def read(path):
    """No source links, including ancestor links, may lead outside preserved evidence."""
    path = Path(path).absolute()
    if credential_path(path):
        raise ValueError(f'forbidden evidence path: {path}')
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise ValueError(f'symlink evidence path: {path}')
    return path.read_bytes()


def redact(data, identities=()):
    # Remove the insertion, including its joining space: a C-only marker would reveal the arm.
    data = data.replace((' ' + control.SENTENCE).encode(), b'').replace(control.SENTENCE.encode(), b'')
    data = re.sub(rb'sha256=[0-9a-f]{64}', b'sha256=[redacted]', data)
    data = re.sub(rb'\binstall [BC]\b', b'install [arm redacted]', data)
    for old, new in sorted(identities, key=lambda pair: len(pair[0]), reverse=True):
        data = data.replace(old.encode(), new.encode())
    return data


def transcript(path):
    """Retain all assistant text and tool calls/results, in order, without system metadata."""
    selected, hidden = [], set()
    for number, line in enumerate(read(path).decode('utf8').splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except ValueError as exc:
            raise ValueError(f'{path}: malformed transcript line {number}') from exc
        content = (event.get('message') or {}).get('content', [])
        if isinstance(content, str):
            content = [{'type': 'text', 'text': content}]
        for block in content:
            kind = block.get('type')
            if kind not in ('text', 'tool_use', 'tool_result'):
                continue
            # A tool reading protected paths must not leak its returned bytes into a packet.
            if kind == 'tool_use' and protected_input(block.get('input', {})):
                hidden.add(block['id'])
                selected.append({'type': 'excluded_tool', 'reason': 'credential/environment evidence excluded'})
            elif kind == 'tool_result' and block.get('tool_use_id') in hidden:
                selected.append({'type': 'excluded_result', 'reason': 'credential/environment evidence excluded'})
            elif event.get('type') == 'assistant' or kind == 'tool_result':
                selected.append(block)
        if event.get('type') == 'result' and isinstance(event.get('result'), str):
            selected.append({'type': 'completion', 'text': event['result']})
    return selected


def copy_tree(source, target, identities):
    if source.is_symlink() or not source.is_dir():
        raise ValueError(f'end tree missing or symlink: {source}')
    links = {}
    target.mkdir(parents=True)
    def walk_error(error):
        raise error

    for directory, dirs, files in os.walk(source, followlinks=False, onerror=walk_error):
        dirs[:] = sorted(name for name in dirs if name not in EXCLUDED and not credential_path(name))
        for name in [*dirs, *sorted(files)]:
            if name in EXCLUDED or credential_path(name):
                continue
            path = Path(directory) / name
            relative = path.relative_to(source)
            if path.is_symlink():
                link = os.readlink(path)
                if not credential_path(link) and not any(part in EXCLUDED for part in Path(link).parts):
                    links[str(relative)] = link
                if name in dirs:
                    dirs.remove(name)
                continue
            if path.is_dir():
                continue
            if not path.is_file():
                raise ValueError(f'non-regular end-tree file: {path}')
            dest = target / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(redact(read(path), identities))
    if links:
        (target / 'symlinks.json').write_bytes(redact(json.dumps(links, indent=2).encode(), identities))


def packets(runtime_path, out_dir):
    runtime = json.loads(read(runtime_path))
    source = Path(runtime['output'])
    destination = Path(out_dir)
    # Reserve the entire destination before writing; this also protects the one-time map.
    destination.mkdir(parents=True, exist_ok=False, mode=0o700)
    mapping = {}
    for row in CELLS:
        while True:
            label = secrets.token_hex(12)
            if label not in mapping:
                break
        mapping[label] = row[0]
    map_path = destination / 'label-map.json'
    with map_path.open('xb') as stream:
        stream.write((json.dumps(mapping, indent=2, sort_keys=True) + '\n').encode())
    identities = [(name, label) for label, name in mapping.items()]
    identities.append((str(source), '[runtime]'))
    witnesses = json.loads(read(source / 'witnesses.json'))
    packet_root = destination / 'packets'
    packet_root.mkdir()
    # Random order prevents directory creation order from revealing the alternating schedule.
    for label in sorted(mapping):
        name = mapping[label]
        packet = packet_root / label
        packet.mkdir()
        verdict = json.loads(read(source / f'verdict-{name}.json'))
        if verdict.get('status') not in ('COMPLETE', 'PRODUCT_INCOMPLETE', 'ADJUDICATE'):
            raise ValueError(f'{name}: verdict attempt unresolved')
        (packet / 'prompt.txt').write_bytes(redact(read(source / name / 'prompt.txt'), identities))
        paired = {w: values[name] for w, values in witnesses.items() if name in values}
        if not paired:
            raise ValueError(f'{name}: witness results missing')
        (packet / 'witnesses.json').write_bytes(redact(json.dumps(paired, indent=2).encode(), identities))
        archives = sorted(source.glob(f'verdict-{name}.stop-*.json'),
                          key=lambda p: int(p.stem.rsplit('.stop-', 1)[1]))
        paths = [*archives, source / f'verdict-{name}.json']
        for index, verdict_path in enumerate(paths, 1):
            attempt_name = verdict_path.stem.removeprefix('verdict-')
            record = json.loads(read(verdict_path))
            attempt = source / attempt_name
            shared = False
            if not attempt.is_dir():
                if str(record.get('reason', '')).startswith(('assessment failed', 'assessor produced', 'assessment held:')):
                    attempt = source / name
                    shared = True
                else:
                    raise ValueError(f'{attempt_name}: archived attempt directory missing')
            target = packet / f'attempt-{index:02d}'
            target.mkdir()
            (target / 'final.txt').write_bytes(redact(read(attempt / 'final.txt'), identities))
            evidence = transcript(attempt / 'run/stdout')
            (target / 'transcript.json').write_bytes(redact(json.dumps(evidence, indent=2, ensure_ascii=False).encode(), identities))
            checks = attempt / 'checks.json'
            if checks.is_file():
                data = read(checks)
            elif record['status'] == 'STOP':
                data = b'{"unavailable": "STOP before grading; no checks were recorded"}\n'
            else:
                raise ValueError(f'{attempt_name}: checks missing')
            (target / 'checks.json').write_bytes(redact(data, identities))
            snapshot = attempt / 'snapshot'
            if snapshot.is_dir():
                copy_tree(snapshot, target / 'tree', identities)
                tree_kind = 'graded snapshot'
            elif record['status'] == 'STOP':
                copy_tree(attempt / 'cell', target / 'tree/cell', identities)
                copy_tree(attempt / 'tmp', target / 'tree/tmp', identities)
                tree_kind = 'preserved STOP end trees; no graded snapshot'
            else:
                raise ValueError(f'{attempt_name}: end tree missing')
            (target / 'evidence.json').write_text(json.dumps(dict(
                shared_owner_execution=shared, tree=tree_kind, verdict_attempt=index == len(paths)), indent=2) + '\n')
    sha256 = hashlib.sha256(map_path.read_bytes()).hexdigest()
    print(f'label-map.json sha256={sha256}')
    return map_path


if __name__ == '__main__':
    if len(sys.argv) != 4 or sys.argv[1] != 'packets':
        raise SystemExit(__doc__)
    packets(*sys.argv[2:])
