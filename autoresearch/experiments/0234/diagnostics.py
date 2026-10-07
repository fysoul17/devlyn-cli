"""Reported transcript observations; never used by grading or admission."""
import json
from pathlib import Path
import re
import shlex
import importlib.util
from datetime import datetime, timezone

GUIDE = '_shared/pair.md'
DELIVERY = '_shared/task-completion.md'
EDIT_TOOLS = {'Edit', 'Write', 'MultiEdit', 'NotebookEdit', 'apply_patch'}
SUBCOMMANDS = {'allocate', 'complete', 'accept', 'attach', 'clean-scratch'}
GUIDE_HEADING = '# Pair reasoning'
_spec = importlib.util.spec_from_file_location('evidence0234d', Path(__file__).with_name('evidence.py'))
evidence = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(evidence)


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


def redirected_capture(out, command):
    match = re.search(r'>\s*([\w./-]+\.jsonl?)', command)
    if not match:
        return None
    relative = match.group(1).lstrip('./')
    found = [p for root in (out / 'cell', out / 'tmp') for p in root.rglob(Path(relative).name)
             if p.is_file() and str(p).endswith(relative)]
    if not found or len({p.read_bytes() for p in found}) > 1:
        return None
    return found[0]


RESUME_VALUE_OPTIONS = {'-c', '--config', '-m', '--model', '--enable', '--disable', '-i', '--image', '-p', '--profile'}


def resume_target(command):
    """The session argument of `codex-monitored.sh resume [options] <id> [prompt]`, skipping option values."""
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if 'resume' not in tokens:
        return None
    rest = tokens[tokens.index('resume') + 1:]
    index = 0
    while index < len(rest):
        token = rest[index]
        if token in RESUME_VALUE_OPTIONS:
            index += 2
        elif token.startswith('-'):
            index += 1
        else:
            return token if re.fullmatch(r'[\w-]+', token) else None
    return None


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
                            output='', error=False, start=event.get('timestamp'), end=None, returned=False)
                found.append(call)
                by_id[call['id']] = call
            for block in message.get('content', ()) if event.get('type') == 'user' else ():
                if block.get('type') == 'tool_result' and block.get('tool_use_id') in by_id:
                    content = block.get('content')
                    value = content if isinstance(content, str) else json.dumps(content)
                    by_id[block['tool_use_id']].update(output=value, error=block.get('is_error', False),
                                                       end=event.get('timestamp'), returned=True)
                    match = re.search(r'(?:Exit code:|exit code |Process exited with code )\s*(-?\d+)', value, re.I)
                    if match:
                        by_id[block['tool_use_id']]['exit_code'] = int(match.group(1))
        else:
            item = event.get('item') or event.get('payload') or {}
            if event.get('type') == 'item.started' and isinstance(item, dict):
                name = item.get('tool') or item.get('name') or item.get('type')
                call = dict(tool=name, input=item.get('input') or item, id=item.get('id'), exit_code=None,
                            output='', error=False, start=event.get('timestamp'), end=None, returned=False)
                found.append(call)
                by_id[call['id']] = call
            if event.get('type') == 'item.completed' and item.get('id') in by_id:
                by_id[item['id']]['exit_code'] = item.get('exit_code')
                by_id[item['id']]['output'] = item.get('aggregated_output') or ''
                by_id[item['id']]['end'] = event.get('timestamp')
                by_id[item['id']]['returned'] = True
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
        targets = re.findall(r'(?:>>?|\btee\s+(?:-a\s+)?)\s*([\w./-]+)', content)
        edited = [p for p in targets if p != '/dev/null' and not p.startswith(('.devlyn/', '/tmp/', '/private/tmp/',
                                                                             '$TMPDIR/', 'tmp/')) and '/.devlyn/' not in p]
        if edited:
            return edited
        if re.search(r'\bsed\s+-i\b|\bwrite_text\b|\bapply_patch\b|\bcp\s|\bmv\s', content):
            return [content]
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


def peer_turns(ordered, out, plan):
    """Best-effort pair process observations, joined to native session evidence by explicit ids."""
    inv = evidence.inventory(out, plan)
    # Codex JSON items omit timestamps. Bind them to the owner's trace by command preview.
    if plan['engine'] == 'codex':
        timed = []
        for folder in (out / 'cell/trace').glob('trace-*'):
            manifest = json.loads((folder / 'manifest.json').read_text())
            if manifest.get('root_thread_id') not in inv['owner_threads']:
                continue
            started = {}
            for event in read_jsonl(folder / manifest.get('raw_event_log', 'trace.jsonl')):
                payload = event.get('payload') or {}
                if payload.get('type') == 'tool_call_started':
                    started[payload.get('tool_call_id')] = (payload.get('summary') or {}).get('input_preview', ''), event.get('wall_time_unix_ms')
                elif payload.get('type') == 'tool_call_ended' and payload.get('tool_call_id') in started:
                    preview, begin = started.pop(payload['tool_call_id'])
                    timed.append((preview, begin, event.get('wall_time_unix_ms')))
        for call in ordered:
            command = text_of(call)
            escaped_prefix = json.dumps(command[:60])[1:-1]
            match = next(((preview, begin, end) for preview, begin, end in timed
                          if command and (command[:60] in preview or escaped_prefix in preview)), None)
            if match:
                timed.remove(match)
                _, begin, end = match
                call['start'] = datetime.fromtimestamp(begin / 1000, timezone.utc).isoformat() if begin else None
                call['end'] = datetime.fromtimestamp(end / 1000, timezone.utc).isoformat() if end else None
    spans = {}
    for folder in (out / 'cell/trace').glob('trace-*'):
        try:
            manifest = json.loads((folder / 'manifest.json').read_text())
            events = read_jsonl(folder / manifest.get('raw_event_log', 'trace.jsonl'))
        except (OSError, ValueError):
            continue
        stamps = [e['wall_time_unix_ms'] for e in events if isinstance(e.get('wall_time_unix_ms'), (int, float))]
        session = manifest.get('root_thread_id')
        if session and stamps:
            spans.setdefault(session, []).append(min(stamps))
    for records in spans.values():
        records.sort()
    span_used, turn_index = {}, {}
    peers, commands, transcript_text = [], [], {}
    for position, call in enumerate(ordered, 1):
        command = text_of(call)
        if call['tool'] not in ('Bash', 'command_execution', 'exec_command', 'shell_command'):
            continue
        engine = ('codex' if 'codex-monitored.sh' in command else
                  'claude' if re.search(r'\bclaude\s+-p\b', command) else None)
        if not engine:
            continue
        session = None
        if engine == 'claude':
            match = re.search(r'--(?:session-id|resume)\s+([\w-]+)', command)
            session = match.group(1) if match else None
        else:
            # The turn's own capture binds the thread first; the command line is only a fallback (freeze a2).
            capture = redirected_capture(out, command)
            text = (call['output'] or '') + (capture.read_text(errors='replace') if capture else '')
            match = re.search(r'"thread_id"\s*:\s*"([\w-]+)"', text)
            session = match.group(1) if match else resume_target(command)
            if session in spans and (not call.get('start') or not call.get('end')):
                index = span_used.get(session, 0)
                if index < len(spans[session]):
                    begin = spans[session][index]
                    span_used[session] = index + 1
                    call['start'] = call.get('start') or datetime.fromtimestamp(begin / 1000, timezone.utc).isoformat()
        native = (inv['seated'].get(session) or inv['native'].get(session) or {}) if engine == 'codex' else inv['transcripts'].get(session, {})
        models = ({native.get('model')} if native.get('model') else native.get('models', set())) if engine == 'codex' else native.get('models', set())
        efforts = ({native.get('effort')} if native.get('effort') else native.get('efforts', set())) if engine == 'codex' else native.get('efforts', set())
        model = next(iter(models)) if len(models) == 1 else sorted(models) or None
        effort = next(iter(efforts)) if len(efforts) == 1 else sorted(efforts) or None
        route = plan.get('peer_route')
        index = turn_index.get(session, 0)
        turn_index[session] = index + 1
        native_status = None
        if engine == 'codex':
            rollouts = [r for r in inv['rollouts'] if r.get('rollout_id') == session]
            if index < len(rollouts):
                native_status = rollouts[index].get('status')
        elif session in inv['envelopes']:
            capture = redirected_capture(out, command)
            matched = next((e for e in inv['envelopes'][session] if capture and e['path'] == str(capture.relative_to(out))), None)
            if matched is None and capture is None and index < len(inv['envelopes'][session]):
                matched = inv['envelopes'][session][index]
            if matched is not None:
                native_status = 'failed' if matched['is_error'] else 'completed'
        if engine == 'claude' and native_status is None:
            capture = redirected_capture(out, command)
            if capture:
                try:
                    result = json.loads(capture.read_text())
                except ValueError:
                    result = {}
                if result.get('type') == 'result':
                    native_status = 'failed' if result.get('is_error') else 'completed'
        background = bool((isinstance(call.get('input'), dict) and call['input'].get('run_in_background') is True) or
                          re.search(r'(?<!&)&(?!&)\s|run_in_background|background\s*[:=]\s*true', command, re.I) or
                          re.search(r'Process running with session ID|running in background', call['output'], re.I))
        returned = call.get('returned', call.get('end') is not None)
        tool_ok = returned and not call.get('error') and call['exit_code'] in (None, 0)
        process_end = call.get('end') if returned and not background else None
        successful = (False if call.get('error') or call['exit_code'] not in (None, 0) or native_status == 'failed' else
                      True if tool_ok and native_status == 'completed' and not background else None)
        peer = dict(position=position, engine=engine, model=model, effort=effort, session=session,
                    start=call.get('start'), end=process_end, tool_return=call.get('end'),
                    background=background, exit_status=call['exit_code'],
                    native_status=native_status, successful=successful,
                    completed=successful is True,
                    route_match=(engine == route['engine'] and model == route['model'] and effort == route['effort'])
                    if route and model and effort else None)
        peers.append(peer)
        capture = call['output']
        file = redirected_capture(out, command)
        if file:
            capture += '\n' + file.read_text(errors='replace')
        if engine == 'claude' and session:
            if session not in transcript_text:
                transcript_text[session] = '\n'.join(
                    json.dumps((event.get('message') or {}).get('content', []))
                    for file in (out / 'home/.claude/projects').rglob('*.jsonl')
                    for event in read_jsonl(file)
                    if event.get('sessionId') == session and event.get('type') == 'assistant')
            capture += '\n' + transcript_text[session]
        commands.append(capture)
    seen = {p['session'] for p in peers if p['session']}
    first_edit = next((i for i, call in enumerate(ordered, 1) if paths(call)), None)
    first_peer = peers[0]['position'] if peers else None
    result = json.loads((out / 'run/result.json').read_text()) if (out / 'run/result.json').is_file() else {}
    owner_end = (result.get('ended_at') or result.get('started_at', 0) + result.get('seconds', 0)) if result else None
    def seconds(value):
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp() if value else None
        except (ValueError, TypeError):
            return None
    if isinstance(owner_end, str):
        owner_end = seconds(owner_end)
    running = []
    for peer in peers:
        start, end = seconds(peer['start']), seconds(peer['end'])
        if owner_end is None or start is None:
            running.append(None)
        elif start >= owner_end:
            running.append(False)
        elif end is not None:
            running.append(end > owner_end)
        elif peer['completed']:
            running.append(None)  # completion is proven, but its timestamp is missing
        else:
            running.append(True)
    ended_while_running = True if True in running else None if None in running else False if peers else None
    proposed = sorted(set(re.findall(r'\b(?:node|python3?|npm)\s+[^\n`]{3,120}', '\n'.join(commands))))
    last_edit = max((i for i, call in enumerate(ordered, 1) if paths(call)), default=0)
    executed = '\n'.join(text_of(call) for call in ordered[last_edit:])
    checks = out / 'checks.json'
    if checks.is_file():
        executed += '\n' + json.dumps(json.loads(checks.read_text()).get('public', []))
    return dict(turns=peers, launched=len(peers), completed=sum(p['completed'] for p in peers),
                continuity=(len(seen) == 1 and len(peers) > 1 and all(p['session'] for p in peers)) if peers else None,
                turn_count_over_three=len(peers) > 3,
                first_peer_relative_to_first_edit=('before' if first_edit is None or first_peer < first_edit else 'after') if peers else 'absent',
                owner_ended_while_peer_running=ended_while_running,
                counterexamples=[dict(command=p, final_source_runs=p in executed) for p in proposed] if proposed else 'unknown')


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
    result['peer'] = peer_turns(calls(rows, plan['engine']), out, plan)
    result['expected_applicability'] = plan['task'] not in ('E1', 'E2')
    (out / 'diagnostics.json').write_text(json.dumps(result, indent=2) + '\n')
    return result
