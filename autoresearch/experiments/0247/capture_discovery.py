"""Claude terminal candidates from payload fields or an observed capture producer.

Filenames alone never imply model work. Receipts and legacy dispatches retain
missing/malformed carriers. Literal shell redirects are a bounded convenience;
the inherited native launch/session/accounting gates still cover other forms.
"""
import json
import importlib.util
from pathlib import Path
import posixpath
import re
import shlex

_spec = importlib.util.spec_from_file_location('diagnostics0241', Path(__file__).resolve().parents[1] / '0234/diagnostics.py')
diagnostics = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(diagnostics)


def literal_redirects(command):
    """Literal stdout paths on simple Claude -p commands, including env/timeout.

No expansion or evaluation: echoed examples, Python bodies and dynamic paths
are not interpreted as literal shell dispatches. Native evidence remains required.
"""
    try:
        lexer = shlex.shlex(diagnostics.without_heredocs(command), posix=True, punctuation_chars=';&|()<>')
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        return []
    segments, current = [], []
    for token in tokens:
        if token and all(c in ';&|()' for c in token):
            segments.append(current); current = []
        else:
            current.append(token)
    segments.append(current)
    found = []
    for segment in segments:
        index = 0
        if segment and Path(segment[0]).name == 'env':
            index += 1
        while index < len(segment) and re.fullmatch(r'[A-Za-z_][\w]*=.*', segment[index]):
            index += 1
        if index < len(segment) and Path(segment[index]).name == 'timeout':
            index += 1
            if segment[index:index + 1] == ['-k']:
                index += 2
            if index >= len(segment) or not re.fullmatch(r'[\d.]+[smhd]?', segment[index]):
                continue
            index += 1
        if (index + 1 >= len(segment) or Path(segment[index]).name != 'claude'
                or segment[index + 1] != '-p'):
            continue
        for position in range(index + 2, len(segment) - 1):
            if segment[position] not in ('>', '>>'):
                continue
            if segment[position - 1].isdigit() and segment[position - 1] != '1':
                continue
            target = segment[position + 1]
            if not any(c in target for c in '$`*?[]~') and target != '/dev/null':
                found.append(target)
    return found


def redirected_paths(out, target):
    """Retain all materialized/custody copies; preserve a missing literal path."""
    out = Path(out).resolve()
    path = Path(target)
    if path.is_absolute():
        path = Path(posixpath.normpath(target))
        mounts = {'/cell': out / 'cell', '/tmp': out / 'tmp', '/home/participant': out / 'home', '/work': out / 'cell/work'}
        mount = next((name for name in mounts if path.is_relative_to(name)), None)
        if mount is None:
            raise ValueError('unsupported Claude capture mount: ' + target)
        primary = mounts[mount] / path.relative_to(mount)
    else:
        primary = out / 'cell/work' / path
    if not primary.resolve().is_relative_to(out.resolve()):
        raise ValueError('Claude capture escapes retained evidence: ' + target)
    relative = (str(primary.resolve().relative_to(out.resolve()))
                if path.is_absolute() or '..' in path.parts else str(path))
    copies = {path for name in ('cell', 'tmp', 'home')
              for path in (out / name).rglob(Path(target).name)
              if path.is_file() and (str(path.relative_to(out)).endswith('/' + relative)
                                    or str(path.relative_to(out)) == relative)}
    if copies:
        return copies
    return {primary.resolve()}


def terminal_candidate(value):
    """Unbound summaries need a terminal payload/accounting field, even if null.

    Declared carriers bypass this heuristic and remain fail closed. Actual
    invocations still require producer/session binding in the inherited gates.
    """
    return (isinstance(value, dict) and value.get('type') == 'result'
            and bool(value.get('session_id'))
            and any(key in value for key in ('modelUsage', 'usage', 'result', 'errors')))


def claude_envelopes(out, *, evidence):
    out = Path(out).resolve()
    expected, order, outputs = set(), {}, []
    unreadable, found = [], {}
    roots = [out / name for name in evidence.WRITABLE]
    for root in roots:
        for path in sorted(root.rglob('attempt.json')):
            if not path.resolve().is_relative_to(out.resolve()):
                continue  # Never read host files through unbound task symlinks.
            try:
                value = json.loads(path.read_text())
            except (OSError, ValueError):
                continue  # Native sessions without valid receipts remain unbound.
            if (not isinstance(value, dict) or value.get('schema') != 'devlyn-peer-v1'
                    or value.get('engine') != 'claude'):
                continue
            capture = value.get('capture')
            if not isinstance(capture, str) or not capture or Path(capture).name != capture or capture in ('.', '..'):
                unreadable.append(str(path.relative_to(out)) + ': invalid Claude capture declaration')
                continue
            expected.add(path.with_name(capture))
    for (_, _, _, engine), copies in evidence.attempted(out)['judges'].items():
        if engine == 'claude':
            expected.update(copies)
    for when, event in enumerate(evidence.lines(out / 'run/stdout')):
        commands = []
        for block in (event.get('message') or {}).get('content', ()):
            if not isinstance(block, dict):
                continue
            if block.get('type') == 'tool_use':
                commands.append(str((block.get('input') or {}).get('command', '')))
            elif block.get('type') == 'tool_result':
                content = block.get('content')
                text = content if isinstance(content, str) else '\n'.join(
                    str(part.get('text', '')) for part in content or () if isinstance(part, dict))
                outputs.append((f'run/stdout#{when:06d}-{block.get("tool_use_id")}', text, when))
        item = event.get('item') or {}
        if isinstance(item, dict):
            detail = item.get('input') or {}
            commands.append(str(item.get('command') or (detail.get('command', '') if isinstance(detail, dict) else detail)))
            if event.get('type') == 'item.completed' and item.get('aggregated_output'):
                outputs.append((f'run/stdout#{when:06d}-{item.get("id")}', str(item['aggregated_output']), when))
        for command in commands:
            for target in literal_redirects(command):
                try:
                    paths = redirected_paths(out, target)
                except ValueError as exc:
                    unreadable.append(str(exc))
                    continue
                for path in paths:
                    expected.add(path); order[path] = when
    # Search content, not names. Expected carriers may use any extension.
    candidates = expected | {path for root in roots for path in root.rglob('*.json*')
                             if path.is_file() and path.suffix in ('.json', '.jsonl')}
    for path in sorted(candidates):
        if not path.resolve().is_relative_to(out.resolve()):
            if path in expected:
                unreadable.append(str(path.relative_to(out)) + ': capture escapes retained evidence')
            continue
        try:
            value = json.loads(path.read_text(errors='replace'))
        except (OSError, ValueError):
            if path in expected:
                unreadable.append(str(path.relative_to(out)))
            continue
        if not isinstance(value, dict) or value.get('type') != 'result' or not value.get('session_id'):
            if path in expected:
                unreadable.append(str(path.relative_to(out)))
            continue
        if path in expected or terminal_candidate(value):
            evidence.add_envelope(found, value, str(path.relative_to(out)), order=order.get(path))
    for where, text, when in outputs:
        for line in text.split('\n'):
            try:
                value = json.loads(line)
            except ValueError:
                continue
            if terminal_candidate(value):
                evidence.add_envelope(found, value, where, any_source=True, order=when)
    def turn(entry):
        match = re.search(r'(?:peer|turn)[-_]?(\d+)', Path(entry['path']).name)
        return (entry['order'] is None, entry['order'] or 0, int(match.group(1)) if match else -1, entry['path'])
    return {session: sorted(entries, key=turn) for session, entries in found.items()}, sorted(set(unreadable))
