"""Reported transcript observations; never used by grading or admission."""
import json
from pathlib import Path
import re

GUIDE = '_shared/failure-paths.md'
DELIVERY = '_shared/task-completion.md'
EDIT_TOOLS = {'Edit', 'Write', 'MultiEdit', 'NotebookEdit', 'apply_patch'}
SUBCOMMANDS = {'allocate', 'complete', 'accept', 'attach', 'clean-scratch'}
GUIDE_HEADING = '# Changes that hold state or resources'


def read_jsonl(path):
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(errors='replace').splitlines():
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def calls(rows, engine):
    """Ordered owner calls from Claude stream JSON or Codex JSON items (with completion exit codes)."""
    found, by_id = [], {}
    for event in rows:
        if engine == 'claude':
            message = event.get('message') or {}
            for block in message.get('content', ()) if event.get('type') == 'assistant' else ():
                if block.get('type') != 'tool_use':
                    continue
                call = dict(tool=block.get('name'), input=block.get('input') or {}, id=block.get('id'), exit_code=None,
                            output='', error=False)
                found.append(call)
                by_id[call['id']] = call
            for block in message.get('content', ()) if event.get('type') == 'user' else ():
                if block.get('type') == 'tool_result' and block.get('tool_use_id') in by_id:
                    content = block.get('content')
                    value = content if isinstance(content, str) else json.dumps(content)
                    by_id[block['tool_use_id']].update(output=value, error=block.get('is_error', False))
                    match = re.search(r'(?:Exit code:|exit code |Process exited with code )\s*(-?\d+)', value, re.I)
                    if match:
                        by_id[block['tool_use_id']]['exit_code'] = int(match.group(1))
        else:
            item = event.get('item') or event.get('payload') or {}
            if event.get('type') == 'item.started' and isinstance(item, dict):
                name = item.get('tool') or item.get('name') or item.get('type')
                call = dict(tool=name, input=item.get('input') or item, id=item.get('id'), exit_code=None,
                            output='', error=False)
                found.append(call)
                by_id[call['id']] = call
            if event.get('type') == 'item.completed' and item.get('id') in by_id:
                by_id[item['id']]['exit_code'] = item.get('exit_code')
                by_id[item['id']]['output'] = item.get('aggregated_output') or ''
    return found


def text_of(call):
    value = call['input']
    if isinstance(value, dict):
        return '\n'.join(str(value.get(key, '')) for key in ('file_path', 'path', 'command', 'cmd', 'patch', 'text'))
    return str(value)


def paths(call):
    content = text_of(call)
    if call['tool'] == 'file_change':  # Codex JSON reports its patch edits as file_change items
        value = call['input']
        return [str(c.get('path', '')) for c in value.get('changes', ())] if isinstance(value, dict) else []
    if call['tool'] in EDIT_TOOLS:
        found = re.findall(r'^\*\*\* (?:Add|Update|Delete) File:\s*(.+)$', content, re.M)
        if found:
            return found
        value = call['input']
        return [str(value.get('file_path') or value.get('path') or '')] if isinstance(value, dict) else []
    if call['tool'] in ('command_execution', 'exec_command', 'Bash', 'shell_command'):
        if re.search(r'(?:>|\btee\b|\bsed\s+-i\b|\bwrite_text\b|\bapply_patch\b|\bcp\s|\bmv\s)', content):
            return re.findall(r'(?:>|File:|\bto\s+)\s*([\w./-]+)', content) or [content]
    return []


def is_test(path):
    return bool(re.search(r'(^|/)(?:tests?|__tests__)/|(?:\.test\.|test_)', path))


def read_call(call, filename):
    value = text_of(call)
    return filename in value and (call['tool'] in ('Read', 'read_file', 'command_execution', 'exec_command', 'Bash', 'shell_command')
                                  or re.search(r'\b(?:cat|sed|rg|less|head|tail)\b', value))


def successful_guide_read(call):
    return (read_call(call, GUIDE) and not call['error'] and
            call['exit_code'] in (None, 0) and GUIDE_HEADING in call['output'])


def summarize(rows, engine, arm):
    ordered = calls(rows, engine)
    first_any = next((i for i, call in enumerate(ordered, 1) if paths(call)), None)
    first_non_test = next((i for i, call in enumerate(ordered, 1) if any(not is_test(p) for p in paths(call))), None)
    mentioned = [(i, call) for i, call in enumerate(ordered, 1) if read_call(call, GUIDE)]
    guide = [(i, call) for i, call in mentioned if successful_guide_read(call)]
    delivery = [(i, call) for i, call in enumerate(ordered, 1) if read_call(call, DELIVERY)]
    executions = []
    for i, call in enumerate(ordered, 1):
        command = text_of(call)
        if 'task-complete.py' in command and call['tool'] in ('Bash', 'command_execution', 'exec_command', 'shell_command'):
            match = re.search(r'task-complete\.py[^\n]*?\s(' + '|'.join(SUBCOMMANDS) + r')\b', command)
            executions.append(dict(position=i, subcommand=match.group(1) if match else 'UNKNOWN',
                                   exit_code=call['exit_code'], tool=call['tool']))
    def observation(entries):
        return [dict(position=i, tool=call['tool'], id=call['id']) for i, call in entries]
    return dict(guide_read=dict(status='absent' if arm in ('A', 'B') else 'read' if guide else 'mentioned' if mentioned else 'unread',
                                calls=observation(mentioned), first_edit_any=first_any,
                                first_edit_non_test=first_non_test,
                                before_first_edit_any=bool(guide and (first_any is None or guide[0][0] < first_any)),
                                before_first_edit_non_test=bool(guide and (first_non_test is None or guide[0][0] < first_non_test))),
                delivery_read=dict(read=bool(delivery), calls=observation(delivery), task_complete=executions))


def record(out):
    plan = json.loads((out / 'plan.json').read_text())
    rows = read_jsonl(out / 'run/stdout')
    if plan['engine'] == 'codex':
        roots = {event['thread_id'] for event in rows if event.get('type') == 'thread.started'}
        traced = []
        for folder in sorted((out / 'cell/trace').glob('trace-*')):
            try:
                manifest = json.loads((folder / 'manifest.json').read_text())
            except (OSError, ValueError):
                continue
            if manifest.get('root_thread_id') not in roots:
                continue
            for event in read_jsonl(folder / manifest.get('raw_event_log', 'trace.jsonl')):
                payload = event.get('payload') or {}
                if payload.get('type') != 'protocol_event_observed' or payload.get('event_type') not in ('item.started', 'item.completed'):
                    continue
                ref = (payload.get('event_payload') or {}).get('path')
                if not ref:
                    continue
                try:
                    observed = json.loads((folder / ref).read_text())
                except (OSError, ValueError):
                    continue
                if observed.get('thread_id') in (None, *roots):
                    traced.append(observed)
        if calls(traced, 'codex'):
            rows = traced
    result = summarize(rows, plan['engine'], plan['arm'])
    (out / 'diagnostics.json').write_text(json.dumps(result, indent=2) + '\n')
    return result
