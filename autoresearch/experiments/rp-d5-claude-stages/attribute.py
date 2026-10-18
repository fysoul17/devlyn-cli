"""Frozen rp-d5 descriptive stages on 0254's audited native receipt rows.

No transcript token accounting or timestamp-derived stage wall partition occurs here.
"""
import argparse
import ast
from collections import defaultdict
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import posixpath
import re
import shlex

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


audit = load('audit0254_rpd5', HERE.parent / '0254/audit.py')
diagnostics = load('diagnostics0234_rpd5', HERE.parent / '0234/diagnostics.py')
COUNTERS = audit.COUNTERS
STAGES = ('Orient', 'Explore', 'Edit', 'Verify', 'Deliver', 'After delivery', 'Report', 'Mixed', 'Other')
PRIMARY = {'write', 'check', 'deliver', 'orient', 'look'}
EXCLUDED = ('.devlyn/', '/tmp/', '/private/tmp/', '$TMPDIR/', 'tmp/')
REDIRECT = re.compile(r'(?:>>?|\btee\s+(?:-a\s+)?)\s*([\w./-]+)')
EXIT = re.compile(r'(?:Exit code:|exit code |Process exited with code )\s*(-?\d+)', re.I)
ASSIGNMENT = re.compile(r'^[A-Za-z_][A-Za-z_0-9]*=')
INTERPRETERS = {'python', 'python3', 'node', 'bash', 'sh', 'ruby', 'perl'}
CONSUME = {
    'head': {'-n', '--lines'}, 'tail': {'-n', '--lines'}, 'sed': {'-n'},
    'rg': {'-g', '--glob', '-t', '--type', '-A', '--after-context', '-B', '--before-context',
           '-C', '--context', '-e', '--regexp', '-f', '--file', '-m', '--max-count'},
    'grep': {'-e', '--regexp', '-f', '--file', '-m', '--max-count', '-A', '--after-context',
             '-B', '--before-context', '-C', '--context'},
    'git': {'-n', '--max-count'},
}


def excluded(path):
    return path == '/dev/null' or path.startswith(EXCLUDED) or '/.devlyn/' in path


def path_kind(value, worktree='/cell/work', task_worktrees=()):
    """Lexical cell paths; no dependence on the operator host's filesystem."""
    if not isinstance(value, str) or any(char in value for char in ('$', '~')):
        return None
    normalized = posixpath.normpath(posixpath.join(worktree, value))
    # task-complete allocates sibling worktrees below <repo>.devlyn.noindex/.
    roots = (worktree, worktree.rstrip('/') + '.devlyn.noindex', *task_worktrees)
    root = next((r.rstrip('/') for r in roots if normalized == r.rstrip('/')
                 or normalized.startswith(r.rstrip('/') + '/')), None)
    if root is None:
        return None
    relative = posixpath.relpath(normalized, root)
    parts = relative.split('/')
    return 'orient' if parts[-1] in ('CLAUDE.md', 'AGENTS.md') or 'skills' in parts[:-1] else 'look'


def shell_commands(text):
    """Split only outside quotes; retain which lexical words contained quotes."""
    commands, current, quote, escaped = [], [], None, False
    for offset, char in enumerate(text):
        if escaped:
            current.append(char)
            escaped = False
        elif char == '\\' and quote != "'":
            current.append(char)
            escaped = True
        elif quote:
            current.append(char)
            if char == quote:
                quote = None
        elif char in ('"', "'"):
            current.append(char)
            quote = char
        elif (char in ';\n' or char == '|' and not (offset > 0 and text[offset - 1] == '>') or
              char == '&' and (text[offset:offset + 2] == '&&' or offset > 0 and text[offset - 1] == '&')):
            if current:
                commands.append(''.join(current))
                current = []
        else:
            current.append(char)
    if current:
        commands.append(''.join(current))
    parsed = []
    for command in commands:
        # Preserve quote provenance independently of shlex's unquoting.
        raw, words, quote, escaped = [], [], None, False
        skip = 0
        for offset, char in enumerate(command + ' '):
            if skip:
                skip -= 1
                continue
            if escaped:
                raw.append(char)
                escaped = False
            elif char == '\\' and quote != "'":
                raw.append(char)
                escaped = True
            elif quote:
                raw.append(char)
                if char == quote:
                    quote = None
            elif char in ('"', "'"):
                raw.append(char)
                quote = char
            elif char in '<>':
                prefix = ''.join(raw)
                if prefix and not prefix.isdigit() and prefix != '&':
                    words.append(prefix)
                raw = []
                operator = re.match(r'(?:<<<|<<-?|<>|>>?|<)[&|]?', command[offset:]).group()
                words.append(('&' if prefix == '&' else '') + operator)
                skip = len(operator) - 1
            elif char.isspace():
                if raw:
                    words.append(''.join(raw))
                    raw = []
            else:
                raw.append(char)
        operands, redirect = [], False
        for word in words:
            if redirect:
                redirect = False
            elif re.fullmatch(r'(?:&>>?|<<<|<<-?|<>|>>?|<)[&|]?', word):
                redirect = True
            else:
                operands.append(word)
        if redirect or quote:
            raise ValueError('incomplete shell redirection or quote')
        words = operands
        tokens = [shlex.split(word)[0] for word in words]
        index = 0
        while index < len(tokens):
            token = tokens[index]
            if ASSIGNMENT.match(token):
                index += 1
                continue
            if any(q in words[index] for q in ('"', "'")):
                break
            if token in ('sudo', 'command', 'nohup', 'time', 'env'):
                index += 1
            else:
                break
        if index < len(tokens):
            quoted = any(q in words[index] for q in ('"', "'"))
            parsed.append((None if quoted else tokens[index], tokens[index + 1:], command))
    return parsed


def read_paths(command, args, worktree, task_worktrees):
    if command == 'find':
        paths = []
        for token in args:
            if token.startswith('-') or token in ('!', '('):
                break
            paths.append(token)
    else:
        paths, index, pattern = [], 0, False
        while index < len(args):
            token = args[index]
            option = token.split('=', 1)[0]
            if option in CONSUME.get(command, set()):
                if option in ('-e', '--regexp', '-f', '--file'):
                    pattern = True
                index += 1 if '=' in token else 2
                continue
            if token.startswith('-'):
                # Attached short-option values are consumed too.
                if any(token.startswith(flag) and len(token) > len(flag)
                       for flag in CONSUME.get(command, set()) if len(flag) == 2):
                    if token[:2] in ('-e', '-f'):
                        pattern = True
                index += 1
                continue
            paths.append(token)
            index += 1
        if command in ('rg', 'grep') and not pattern:
            paths = paths[1:]
    if command == 'git':
        # Revision-shaped bare tokens (HEAD, hashes, ranges) are not paths.
        # Relative file paths are recognized by slash/dot or task-file existence
        # supplied by syntax; ambiguous bare revision names remain revisions.
        paths = [p for p in paths if path_kind(p, worktree, task_worktrees) is not None
                 and (p in ('.', '..') or '/' in p or '.' in p and '..' not in p)]
    kinds = {path_kind(p, worktree, task_worktrees) for p in paths}
    return 'look' if not kinds or kinds == {'look'} else 'orient' if kinds == {'orient'} else None


def script_invocation(command, args):
    if command in INTERPRETERS:
        for token in args:
            if token in ('-c', '-m', '-', '<<') or token.startswith('<<'):
                return None, []
            if token.startswith('-'):
                continue
            return posixpath.basename(token), args[args.index(token) + 1:]
        return None, []
    return command, args


def open_modes(text):
    """Find open's mode argument even when its file argument is an expression."""
    modes = []
    for match in re.finditer(r'\bopen\s*\(', text):
        arguments, current, depth, quote, escaped = [], [], 0, None, False
        for char in text[match.end():]:
            if escaped:
                current.append(char)
                escaped = False
            elif char == '\\' and quote:
                current.append(char)
                escaped = True
            elif quote:
                current.append(char)
                if char == quote:
                    quote = None
            elif char in ('"', "'"):
                current.append(char)
                quote = char
            elif char in '([{':
                current.append(char)
                depth += 1
            elif char == ')' and depth == 0:
                arguments.append(''.join(current).strip())
                break
            elif char in ')]}':
                current.append(char)
                depth -= 1
            elif char == ',' and depth == 0:
                arguments.append(''.join(current).strip())
                current = []
            else:
                current.append(char)
        keyword = next((arg.split('=', 1)[1].strip() for arg in arguments if re.match(r'^mode\s*=', arg)), None)
        if keyword is not None:
            modes.append(keyword)
        elif len(arguments) > 1 and '=' not in arguments[1]:
            modes.append(arguments[1])
    return modes


def bash_predicates(command, *, worktree='/cell/work', task_worktrees=(), check_scripts=()):
    pipeline = diagnostics.without_heredocs(command)
    try:
        commands = shell_commands(pipeline)
    except ValueError:
        return set(), False
    predicates, complete = set(), False
    def in_process(text):
        write = bool(re.search(r'\bwrite_(?:text|bytes)\s*\(', text))
        dynamic_open = False
        for mode in open_modes(text):
            try:
                literal = ast.parse(mode, mode='eval').body
            except (SyntaxError, ValueError):
                literal = None
            if isinstance(literal, ast.Constant) and isinstance(literal.value, str):
                write |= literal.value.startswith(('w', 'a', 'x'))
            else:
                dynamic_open = True
        return write, dynamic_open

    # Keep heredoc text associated with its own launching command. A write in
    # one Python invocation cannot clear another invocation's unknown mutation.
    payloads, terminator, payload = defaultdict(list), None, []
    for line in command.split('\n'):
        if terminator is not None:
            if line.strip() == terminator:
                payloads[terminator].append('\n'.join(payload))
                terminator, payload = None, []
            else:
                payload.append(line)
            continue
        match = re.search(r"<<-?\s*['\"]?(\w+)['\"]?", line)
        if match:
            terminator = match.group(1)
    in_process_write, dynamic_open = in_process(command)
    if in_process_write or any(not excluded(p) for p in REDIRECT.findall(pipeline)):
        predicates.add('write')
    if dynamic_open:
        predicates.add('unknown')
    for invoked, args, raw in commands:
        if invoked is None:
            continue
        word = posixpath.basename(invoked)
        own = set()
        script, script_args = script_invocation(word, args)
        if word in ('tee', 'patch') or word == 'git' and args[:1] == ['apply']:
            own.add('write')
        if word == 'sed' and any(a in ('-i', '--in-place') or a.startswith('-i') for a in args):
            own.add('write')
        if word in ('cp', 'mv', 'rm'):
            paths = [a for a in args if not a.startswith('-')]
            for path in paths:
                if excluded(path):
                    continue
                if path_kind(path, worktree, task_worktrees) == 'look':
                    own.add('write')
                else:
                    own.add('unknown')
        if word == 'pytest' or word in ('python', 'python3') and any(
                args[i:i + 2] == ['-m', 'pytest'] for i in range(len(args))):
            own.add('check')
        if script in {posixpath.basename(p) for p in check_scripts}:
            own.add('check')
        if script == 'task-complete.py':
            own.add('deliver')
            complete |= 'complete' in script_args
        if word == 'gh' or word == 'git' and args and args[0] in (
                'add', 'commit', 'push', 'fetch', 'merge', 'worktree', 'branch'):
            own.add('deliver')
        if word in ('cat', 'ls', 'head', 'tail', 'rg', 'grep', 'find') or word == 'sed' and '-n' in args:
            kind = read_paths(word, args, worktree, task_worktrees)
            if kind:
                own.add(kind)
        if word == 'git' and args:
            if args[0] == 'status':
                own.add('look')
            elif args[0] in ('diff', 'log', 'show'):
                kind = read_paths('git', args[1:], worktree, task_worktrees)
                if kind:
                    own.add(kind)
        match = re.search(r"<<-?\s*['\"]?(\w+)['\"]?", raw)
        bodies = payloads[match.group(1)] if match else []
        full = raw + ('\n' + bodies.pop(0) if bodies else '')
        local_write, _ = in_process(full)
        if (word in INTERPRETERS or word.endswith(('.py', '.js', '.sh', '.rb', '.pl'))
                or '/' in invoked) and not own and not local_write:
            own.add('unknown')
        predicates.update(own)
    return predicates, complete


def call_predicates(call, **context):
    name, value = call['name'], call['input']
    if name in ('Edit', 'Write', 'NotebookEdit'):
        return {'write'}, False
    if name in ('Read', 'Grep', 'Glob'):
        path = value.get('file_path', value.get('path', '.'))
        kind = path_kind(path, context.get('worktree', '/cell/work'), context.get('task_worktrees', ()))
        return {kind} if kind else set(), False
    if name == 'Bash':
        return bash_predicates(value.get('command', ''), **context)
    return set(), False


def completion_status(output):
    """Decode from every opening brace; trailers and pretty JSON are allowed."""
    decoder = json.JSONDecoder()
    for match in re.finditer(r'\{', output):
        try:
            value, _ = decoder.raw_decode(output[match.start():])
        except ValueError:
            continue
        if isinstance(value, dict) and isinstance(value.get('status'), str):
            return value['status'], value.get('delivery_status')
    return None


def classify_rows(rows, **context):
    """Rows are already in index order. Return annotated copies, never reorder."""
    classified = []
    for row in rows:
        calls, predicates = [], set()
        for call in row['calls']:
            found, complete = call_predicates(call, **context)
            predicates.update(found)
            calls.append(dict(call, predicates=sorted(found), complete=complete))
        classified.append(dict(row, calls=calls, predicates=sorted(predicates),
                               mutation_unknown='unknown' in predicates, write='write' in predicates))
    first_write = next((i for i, row in enumerate(classified) if row['write']), None)
    last_text = next((i for i in range(len(classified) - 1, -1, -1) if not classified[i]['calls']), None)
    boundary, unparseable = None, None
    for index, row in enumerate(classified):
        primary = set(row['predicates']) & PRIMARY
        if index == last_text:
            stage = 'Report'
        elif not row['calls']:
            stage = 'Other'
        elif unparseable is not None:
            stage = 'Other'
        elif boundary is not None:
            stage = 'After delivery'
        elif len(primary) >= 2:
            stage = 'Mixed'
        else:
            stage = next((label for key, label in (
                ('orient', 'Orient'), ('write', 'Edit'), ('check', 'Verify'), ('deliver', 'Deliver'),
                ('look', 'Explore' if first_write is None or index < first_write else 'Verify'))
                          if key in primary), 'Other')
        if boundary is None and unparseable is None:
            for call in row['calls']:
                if not call['complete']:
                    continue
                result = completion_status(call.get('output', '')) if call.get('returned') else None
                if result is None:
                    unparseable = index
                    stage = 'Other'
                    break
                if result[0] == 'COMPLETE' or result == ('CLEANUP_PENDING', 'COMPLETE'):
                    boundary = index
                    break
        row['stage'] = stage
    unsupported = any(row['mutation_unknown'] and (first_write is None or i < first_write)
                      for i, row in enumerate(classified))
    other_share = sum(row['stage'] == 'Other' for row in classified) / len(classified)
    return classified, dict(other_turn_share=other_share, low_coverage=other_share > .2,
        explore_verify_supported=not unsupported, first_write_row=
        classified[first_write]['row_id'] if first_write is not None else None,
        delivery_boundary_row=classified[boundary]['row_id'] if boundary is not None else None,
        unparseable_complete_row=classified[unparseable]['row_id'] if unparseable is not None else None)


def totals(rows):
    values = {key: sum(row['usage'][key] for row in rows) for key in COUNTERS}
    return dict(values, turns=len(rows), total_input_tokens=sum(values[k] for k in COUNTERS[:3]),
                marginal_tokens=values['output_tokens'] + values['cache_creation_input_tokens'])


def repeats(rows):
    operations = defaultdict(list)
    writes = []
    for index, row in enumerate(rows):
        for call_index, call in enumerate(row['calls']):
            canonical = json.dumps(call['input'], sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            position = (index, call_index)
            operations[(call['name'], canonical)].append((position, row, call))
            if 'write' in call['predicates']:
                writes.append(position)
    result = []
    for (name, canonical), occurrences in operations.items():
        if len(occurrences) < 2:
            continue
        shown = []
        previous = None
        for position, row, call in occurrences:
            between = rows[previous[0] + 1:position[0]] if previous is not None else []
            shown.append(dict(row_id=row['row_id'], tool_use_id=call['id'], stage=row['stage'],
                intervening_write=previous is not None and any(previous < p < position for p in writes),
                intervening_unknown=any(r['mutation_unknown'] for r in between),
                enclosing_row_tokens=dict(row['usage']), tokens_label='shared and non-additive'))
            previous = position
        result.append(dict(tool=name, canonical_input=canonical, occurrences=shown))
    return result


def read(path):
    return audit.decode(Path(path).read_bytes())


def sealed_read(out, relative, manifest, *, jsonl=False):
    path = out / relative
    audit.require(not path.is_symlink() and path.resolve().is_relative_to(out.resolve()), 'invalid attribution source')
    raw = path.read_bytes()
    audit.require(manifest['files'].get(str(relative)) == hashlib.sha256(raw).hexdigest(), 'attribution source seal mismatch')
    return [audit.decode(line) for line in raw.splitlines()] if jsonl else audit.decode(raw)


def effort_binding(out, manifest_sha256, expected_effort):
    """Check every sealed request even if the auditor refuses an earlier invariant."""
    try:
        path = Path(out) / 'evidence.manifest.json'
        audit.require(hashlib.sha256(path.read_bytes()).hexdigest() == manifest_sha256, 'manifest hash mismatch')
        manifest = read(path)
        requests = [p for p in manifest['files'] if p.startswith(str(audit.BODY) + '/') and p.endswith('.request.json')]
        audit.require(requests and expected_effort in ('high', 'max'), 'missing effort binding')
        for path in requests:
            request = sealed_read(Path(out), path, manifest)
            audit.require(request.get('output_config', {}).get('effort') == expected_effort, 'request effort mismatch')
        return 'MATCH'
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return 'STOP'


def analyze(out, *, manifest_sha256=None, expected_effort=None, account=None,
            model='claude-opus-5-5', worktree='/cell/work', task_worktrees=(), check_scripts=()):
    out = Path(out)
    result = dict(schema='rp-d5-attribution-v1', status='UNKNOWN', gaps=[], effort_binding='STOP',
                  totals=None, rows=[], stages=[], repeats=[], first_row=None, sensitivity=None,
                  cache_read_series=[], owner_seconds=None, flags={})
    try:
        verdict = read(out / 'rp-verdict.json') if (out / 'rp-verdict.json').exists() else {}
        inherited = out.parent / ('verdict-' + out.name + '.json')
        inherited_record = read(inherited) if inherited.exists() else {}
        inherited_bound = inherited.exists() and verdict.get('inherited_verdict_sha256') == hashlib.sha256(inherited.read_bytes()).hexdigest()
        if manifest_sha256 is None and inherited.exists():
            audit.require(inherited_bound, 'unbound inherited verdict')
            manifest_sha256 = inherited_record.get('evidence_manifest_sha256')
        manifest_sha256 = manifest_sha256 or verdict.get('evidence_manifest_sha256')
        expected_effort = expected_effort or verdict.get('effort')
        account = account or verdict.get('account')
        if isinstance(account, list):
            account = account[0] if account else None
        if expected_effort is None and (out / 'plan.json').exists():
            plan = read(out / 'plan.json')
            expected_effort = plan.get('effort')
        seconds = inherited_record.get('owner_seconds') if inherited_bound else None
        if type(seconds) in (int, float) and math.isfinite(seconds) and seconds >= 0:
            result['owner_seconds'] = seconds
        result['effort_binding'] = effort_binding(out, manifest_sha256, expected_effort)
        report = audit.audit(out, manifest_sha256=manifest_sha256, model=model,
                             effort=expected_effort, account=account)
        result['audit'] = report
        audit.require(report['status'] == 'MATCH', '0254 audit refused: ' + '; '.join(report['gaps']))
        audit.require(result['effort_binding'] == 'MATCH', 'effort binding failed')
        manifest = read(out / 'evidence.manifest.json')
        index = sealed_read(out, audit.BODY / 'index.jsonl', manifest, jsonl=True)
        receipts = report['messages']
        audit.require([r['message_id'] for r in receipts] == [r['message_id'] for r in index],
                      'audited receipt order mismatch')
        tool_results = {}
        for name in sorted(manifest['files']):
            if not name.startswith(str(audit.PROJECTS) + '/') or not name.endswith('.jsonl'):
                continue
            for event in sealed_read(out, name, manifest, jsonl=True):
                if event.get('type') != 'user':
                    continue
                content = event.get('message', {}).get('content', [])
                for block in content if isinstance(content, list) else []:
                    if block.get('type') != 'tool_result':
                        continue
                    value = block.get('content')
                    output = value if isinstance(value, str) else json.dumps(value)
                    match = EXIT.search(output)
                    item = dict(output=output, returned=True, error=block.get('is_error', False),
                                exit_code=int(match.group(1)) if match else None)
                    key = block['tool_use_id']
                    audit.require(key not in tool_results or tool_results[key] == item, 'conflicting tool result')
                    tool_results[key] = item
        rows, seen = [], set()
        for position, (receipt, entry) in enumerate(zip(receipts, index), 1):
            response = sealed_read(out, audit.BODY / entry['response_file'], manifest)
            calls = []
            for block in response.get('content', []):
                if block.get('type') != 'tool_use':
                    continue
                audit.require(isinstance(block.get('input'), dict) and isinstance(block.get('name'), str)
                              and isinstance(block.get('id'), str) and block['id'] not in seen,
                              'invalid or duplicate terminal tool call')
                seen.add(block['id'])
                joined = tool_results.get(block['id'], dict(output='', returned=False, error=False, exit_code=None))
                calls.append(dict(id=block['id'], name=block['name'], input=block['input'], **joined))
            # Tokens are the receipt's audited counters; no new token parsing.
            rows.append(dict(row_id=receipt['message_id'], index=position, agent_id=receipt['agent_id'],
                             request_id=receipt['request_id'], usage=dict(receipt['usage']), calls=calls))
        row_totals = totals(rows)
        audit.require(all(row_totals[key] == report['totals'][key] for key in COUNTERS),
                      'attribution row sums do not reconcile')
        rows, flags = classify_rows(rows, worktree=worktree, task_worktrees=task_worktrees, check_scripts=check_scripts)
        stages = [dict(stage=stage, **totals([r for r in rows if r['stage'] == stage])) for stage in STAGES]
        flags.update(mutation_unknown=any(r['mutation_unknown'] for r in rows))
        result.update(status='MATCH', totals=row_totals, rows=rows, stages=stages, repeats=repeats(rows),
            first_row=dict(row_id=rows[0]['row_id'], **rows[0]['usage']), sensitivity=totals(rows[1:]),
            cache_read_series=[dict(row_id=r['row_id'], cache_read_input_tokens=r['usage']['cache_read_input_tokens'])
                               for r in rows], flags=flags)
        if 'run/result.json' in manifest['files']:
            owner = sealed_read(out, 'run/result.json', manifest)
            seconds = owner.get('seconds')
            if type(seconds) in (int, float) and math.isfinite(seconds) and seconds >= 0:
                result['owner_seconds'] = seconds
        for row in rows:
            for call in row['calls']:
                # Results are used for classification, not published in analysis.
                call.pop('output')
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        detail = str(exc) if isinstance(exc, audit.EvidenceError) else type(exc).__name__
        result.update(status='UNKNOWN', gaps=[detail], totals=None, sensitivity=None, first_row=None,
                      rows=[], stages=[], repeats=[], cache_read_series=[])
    return result


def markdown(result):
    def show(value):
        return 'UNKNOWN' if value is None else str(value)
    lines = [f"Accounting: {result['status']}; effort binding: {result['effort_binding']}; "
             f"slot owner_seconds: {show(result['owner_seconds'])}."]
    if result['status'] != 'MATCH':
        return '\n'.join(lines + ['Gaps: ' + '; '.join(result['gaps'])])
    lines += ['', '| Stage | Turns | Uncached | Cache read (context only) | Cache write | Output | Thinking | Marginal |',
              '|---|---:|---:|---:|---:|---:|---:|---:|']
    keys = ('turns', 'input_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens',
            'output_tokens', 'thinking_tokens', 'marginal_tokens')
    for stage in result['stages']:
        lines.append('| ' + stage['stage'] + ' | ' + ' | '.join(show(stage[k]) for k in keys) + ' |')
    first = result['first_row']
    lines += ['', f"First row {first['row_id']}: cache write {first['cache_creation_input_tokens']}; "
              f"cache read {first['cache_read_input_tokens']}.",
              'Sensitivity (first row excluded): ' + json.dumps(result['sensitivity'], sort_keys=True) + '.',
              'Other share: ' + str(round(result['flags']['other_turn_share'] * 100, 2)) + '%; ' +
              'low-coverage: ' + str(result['flags']['low_coverage']) + '; Explore/Verify supported: ' +
              str(result['flags']['explore_verify_supported']) + '.', '',
              '| Row | Stage | Predicates | Mutation unknown | Cache read |', '|---|---|---|---|---:|']
    for row in result['rows']:
        lines.append(f"| {row['row_id']} | {row['stage']} | {', '.join(row['predicates']) or 'none'} | "
                     f"{row['mutation_unknown']} | {row['usage']['cache_read_input_tokens']} |")
    lines += ['', 'Repeats are descriptive; enclosing-row tokens are shared and non-additive.', '',
              '| Tool and canonical JSON input | Occurrence row / stage | Intervening write / unknown | Enclosing-row tokens (shared, non-additive) |',
              '|---|---|---|---|']
    for operation in result['repeats']:
        name = (operation['tool'] + ' ' + operation['canonical_input']).replace('|', '&#124;')
        for occurrence in operation['occurrences']:
            lines.append('| ' + name + ' | ' + occurrence['row_id'] + ' / ' + occurrence['stage'] +
                ' | ' + str(occurrence['intervening_write']) + ' / ' + str(occurrence['intervening_unknown']) +
                ' | ' + json.dumps(occurrence['enclosing_row_tokens'], sort_keys=True) + ' |')
    return '\n'.join(lines)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    parser.add_argument('--manifest-sha256')
    parser.add_argument('--expected-effort', choices=('max', 'high'))
    parser.add_argument('--account', help='Frozen 12-hex account hash, never credentials')
    parser.add_argument('--markdown', action='store_true')
    args = parser.parse_args()
    result = analyze(args.out, manifest_sha256=args.manifest_sha256, expected_effort=args.expected_effort,
                     account=args.account)
    print(markdown(result) if args.markdown else json.dumps(result, indent=2))
    raise SystemExit(0 if result['status'] == 'MATCH' else 2)
