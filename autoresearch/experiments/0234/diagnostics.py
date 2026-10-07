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


# A peer launch runs the wrapper or `claude -p` as a command; naming the wrapper in `cat`/`sed`/`grep` is not a launch
# (0234 SMOKE: `sed -n 1,40p .../codex-monitored.sh` was counted as a turn).
CODEX_LAUNCH = re.compile(r'(?:^|[;&|({]\s*|\n\s*|\bbash\s+|\bsh\s+|=\S+\s+)(?:\S*/)?codex-monitored\.sh\b')
CLAUDE_LAUNCH = re.compile(r'(?:^|[;&|({]\s*|\n\s*|\btimeout\s+(?:-k\s+\S+\s+)?\S+\s+|=\S+\s+)(?:\S*/)?claude\s+-p\b')


# A script that runs the CLI as an argument list, e.g. subprocess.run(['claude', '-p', ...]) (0234 SMOKE r2).
ARGV_LAUNCH = re.compile(r'''[\[(,]\s*['"](?:\S*/)?(claude|codex-monitored\.sh|bash)['"]\s*,\s*['"](-p|[^'"]*codex-monitored\.sh)['"]''')


def launch_engine(command):
    """The peer engine a shell command launches, or None when it only mentions one."""
    if CODEX_LAUNCH.search(command):
        return 'codex'
    if CLAUDE_LAUNCH.search(command):
        return 'claude'
    match = ARGV_LAUNCH.search(command)
    if match:
        return 'claude' if match.group(1) == 'claude' else 'codex'
    return None


RESUME_VALUE_OPTIONS = {'-c', '--config', '-m', '--model', '--enable', '--disable', '-i', '--image', '-p', '--profile'}


def output_envelope(text):
    """The last Claude result envelope printed in a tool output, or None."""
    found = None
    for line in (text or '').splitlines():
        line = line.strip()
        if line.startswith('{'):
            try:
                value = json.loads(line)
            except ValueError:
                continue
            if isinstance(value, dict) and value.get('type') == 'result' and value.get('session_id'):
                found = value
    return found


def resume_target(command):
    """The session argument of `codex-monitored.sh resume [options] <id> [prompt]`, skipping option values."""
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if 'resume' not in tokens:
        # `/bin/sh -lc "<command>"` keeps the whole command in one token; look inside it.
        inner = [token for token in tokens if 'resume' in token and token != command]
        return next((found for found in map(resume_target, inner) if found), None)
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


def without_heredocs(command):
    """A shell command without its here-document bodies, whose prose (`-> 13.5`) is not a redirection."""
    lines, kept, terminator = command.split('\n'), [], None
    for line in lines:
        if terminator is not None:
            if line.strip() == terminator:
                terminator = None
            continue
        kept.append(line)
        match = re.search(r"<<-?\s*['\"]?(\w+)['\"]?", line)
        if match:
            terminator = match.group(1)
    return '\n'.join(kept)


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
        targets = re.findall(r'(?:>>?|\btee\s+(?:-a\s+)?)\s*([\w./-]+)', without_heredocs(content))
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


def attach_call_times(ordered, out, inv, plan):
    """Codex JSON items omit timestamps: bind them to the owner's trace by command preview (idempotent)."""
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


def peer_traces(out, inv):
    """Distinct owner-launched Codex traces in start order: a copied trace directory is the same trace."""
    launched, seen, found = set(inv['owner_launched_codex']), set(), []
    for rollout in inv['rollouts']:
        if rollout.get('rollout_id') not in launched:
            continue
        try:
            started = json.loads((out / 'cell/trace' / rollout['trace'] / 'manifest.json').read_text()).get('started_at_unix_ms')
        except (OSError, ValueError, KeyError):
            started = None
        key = (rollout['rollout_id'], started, frozenset(rollout['inferences']))
        if key in seen:
            continue
        seen.add(key)
        found.append(dict(rollout_id=rollout['rollout_id'], started=started, status=rollout.get('status'),
                          used=bool(rollout['inferences'])))
    return sorted(found, key=lambda t: (t['started'] is None, t['started'] or 0))


def launch_count(command):
    """Individual peer launches in one shell command."""
    return len(CODEX_LAUNCH.findall(command)) + len([m for m in ARGV_LAUNCH.finditer(command) if m.group(1) != 'claude'])


def ms(value):
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp() * 1000 if value else None
    except (ValueError, TypeError, AttributeError):
        return None


def match_codex_launches(calls, traces, slack=5000):
    """One-to-one: each Codex peer launch takes the earliest unused trace that started inside its call window
    (or, without a window, the earliest unused trace after the previous match). Returns (bound per call, unbound)."""
    unused, bound, unbound, floor = list(traces), [], 0, None
    for call in calls:
        mine = []
        begin, end = ms(call.get('start')), ms(call.get('end'))
        for _ in range(max(launch_count(text_of(call)), 1)):
            pick = next((t for t in unused if t['started'] is not None and begin is not None and end is not None
                         and begin - slack <= t['started'] <= end + slack), None)
            if pick is None and (begin is None or end is None):
                pick = next((t for t in unused if floor is None or t['started'] is None or t['started'] >= floor), None)
            if pick is None:
                unbound += 1
                continue
            unused.remove(pick)
            mine.append(pick)
            floor = pick['started'] if pick['started'] is not None else floor
        bound.append(mine)
    return bound, unbound


def bind_codex_turns(peers, calls, traces, inv, plan):
    """Codex peer turns take their session and native status from their own trace, never a neighbour's."""
    codex_peers = [p for p in peers if p['engine'] == 'codex']
    bound, _ = match_codex_launches(calls, traces)
    route = plan.get('peer_route')
    for peer, mine, call in zip(codex_peers, bound, calls):
        trace = mine[0] if mine else None
        native = (inv['seated'].get(trace['rollout_id']) or {}) if trace else {}
        status = trace['status'] if trace else None
        ok = (peer['successful'] is not False and peer['exit_status'] in (None, 0) and not peer['background']
              and (peer['tool_return'] is not None or call.get('returned')) and status == 'completed' and trace['used'])
        peer.update(session=trace['rollout_id'] if trace else peer['session'], native_status=status,
                    model=native.get('model') if trace else peer['model'],
                    effort=native.get('effort') if trace else peer['effort'],
                    successful=True if ok else (False if peer['successful'] is False or status not in (None, 'completed')
                                                else None))
        peer['completed'] = peer['successful'] is True
        peer['route_match'] = ((route['engine'] == 'codex' and peer['model'] == route['model']
                                and peer['effort'] == route['effort']) if route and peer['model'] and peer['effort'] else None)


def peer_turns(ordered, out, plan):
    """Best-effort pair process observations, joined to native session evidence by explicit ids."""
    inv = evidence.inventory(out, plan)
    attach_call_times(ordered, out, inv, plan)
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
        engine = launch_engine(command)
        if not engine:
            continue
        call['_peer_engine'] = engine
        session = None
        if engine == 'claude':
            # The turn's own result envelope binds the session first (an id held in a shell variable is not literal).
            capture = redirected_capture(out, command)
            try:
                session = json.loads(capture.read_text(errors='replace')).get('session_id') if capture else None
            except ValueError:
                session = None
            if not session:
                session = (output_envelope(call['output']) or {}).get('session_id')
            if not session:
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
            printed = output_envelope(call['output']) if capture is None else None
            if matched is None and printed is not None:
                matched = dict(is_error=printed.get('is_error'))
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
    bind_codex_turns(peers, [c for c in ordered if c.get('_peer_engine') == 'codex'], peer_traces(out, inv), inv, plan)
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
