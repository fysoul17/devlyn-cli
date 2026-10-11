"""Prospective pair identity/receipt policy. Native evidence, never requested argv, proves identity."""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text())


def route_for(tasks, config, arm):
    if arm in ('A', 'B', 'S'):
        return None
    owner = tasks['routes'][config]['owner']
    route = tasks['routes'][config]['peer_routes'][arm]
    if not all(isinstance(route.get(k), str) and route[k] for k in ('engine', 'model', 'effort')):
        raise ValueError('peer route must explicitly name engine, model and effort')
    if arm == 'H' and any(route[k] != owner[k] for k in ('engine', 'model', 'effort')):
        raise ValueError('H must use the exact owner engine/model/effort')
    if arm == 'P' and route['engine'] == owner['engine']:
        raise ValueError('P must use the other engine')
    if arm not in ('H', 'P') or route['engine'] not in ('claude', 'codex'):
        raise ValueError('unregistered pair arm/engine')
    if route['engine'] == 'codex' and not all(route.get(k) for k in ('child_model', 'child_effort')):
        raise ValueError('Codex peer native-child route must be explicit')
    return route


def receipts(out, evidence):
    found, gaps = {}, []
    for root in (out / name for name in ('cell', 'tmp', 'home')):
        for path in sorted(root.rglob('attempt.json')):
            try:
                attempt = read(path)
            except (OSError, ValueError):
                continue  # unrelated task files; native sessions still require a bound receipt below
            if not isinstance(attempt, dict) or attempt.get('schema') != 'devlyn-peer-v1':
                continue
            key = (attempt.get('started_ns'), attempt.get('capture'))
            if not isinstance(key[0], int) or not isinstance(key[1], str) or Path(key[1]).name != key[1]:
                gaps.append('invalid peer attempt ' + str(path.relative_to(out)))
                continue
            entry = dict(attempt=attempt, completion=None, session=None, path=str(path.relative_to(out)))
            try:
                entry['completion'] = read(path.with_name('completion.json'))
                capture = path.with_name(key[1])
                if attempt['engine'] == 'claude':
                    result = read(capture)
                    entry['session'] = result.get('session_id') if result.get('type') == 'result' else None
                else:
                    ids = {row['thread_id'] for row in evidence.lines(capture) if row.get('type') == 'thread.started'}
                    entry['session'] = next(iter(ids)) if len(ids) == 1 else None
                entry['capture_bytes'] = capture.read_bytes()
            except (OSError, ValueError, KeyError, TypeError) as exc:
                gaps.append(f'peer attempt {key[0]} incomplete: {type(exc).__name__}')
            previous = found.setdefault(key, entry)
            if {k: v for k, v in previous.items() if k != 'path'} != {k: v for k, v in entry.items() if k != 'path'}:
                gaps.append(f'conflicting peer receipt copies {key[0]}')
    return sorted(found.values(), key=lambda row: row['attempt']['started_ns']), gaps


def ancestor(thread, parents, owners, peers):
    """Resolve a native descendant to its independent root; cycles/unknown parents stay unknown."""
    seen = set()
    while thread and thread not in seen:
        if thread in owners:
            return 'owner', thread
        if thread in peers:
            return 'peer', thread
        seen.add(thread)
        thread = parents.get(thread)
    return 'unknown', None


def check(out, plan, tasks, evidence):
    inv = evidence.inventory(out, plan)
    route = route_for(tasks, plan['config'], plan['arm'])
    turns, gaps = receipts(out, evidence)
    violations, protocol = [], []
    roots = {'codex': set(), 'claude': set()}
    for turn in turns:
        attempt, completion, session = turn['attempt'], turn['completion'], turn['session']
        if route is None:
            violations.append('independent peer in solo arm')
        elif any(attempt.get(k) != route[k] for k in ('engine', 'model', 'effort')):
            violations.append('requested peer route differs from registration')
        if not session or not completion:
            gaps.append('peer attempt without completed native session evidence')
            continue
        if (completion.get('schema') != 'devlyn-peer-v1'
                or not isinstance(completion.get('ended_ns'), int)
                or completion['ended_ns'] <= attempt['started_ns']):
            gaps.append('peer completion has no valid attempt interval')
        engine = attempt['engine']
        if engine not in roots:
            violations.append('unregistered peer engine')
            continue
        roots[engine].add(session)
        if attempt.get('resume') and attempt['resume'] != session:
            violations.append('peer resumed a different session')
        if not completion.get('source_unchanged') or attempt.get('source_before') != completion.get('source_after'):
            protocol.append('source changed while peer reviewed it')

    owner_codex, owner_claude = inv['owner_threads'], {inv['claude_owner']['session']} - {None}
    parents = {thread: row.get('parent') for thread, row in inv['native'].items()}
    roles = {thread: ancestor(thread, parents, owner_codex, roots['codex']) for thread in inv['native']}
    for thread in inv['seated']:
        roles.setdefault(thread, ancestor(thread, parents, owner_codex, roots['codex']))
    for thread, (role, root) in roles.items():
        if role == 'unknown':
            gaps.append(f'unbound Codex session {thread}')
        elif role == 'peer' and route:
            if route['engine'] != 'codex':
                violations.append('Codex peer ran on an unregistered engine')
                continue
            want = route if thread == root else dict(model=route['child_model'], effort=route['child_effort'])
            native = inv['native'].get(thread, {})
            if native.get('models') != {want['model']} or native.get('efforts') != {want['effort']}:
                violations.append(f'Codex peer thread {thread} native model/effort mismatch or missing')

    # Every resumed process must carry its own native configuration and inference identity.
    traced_turns = set()
    for rollout in inv['rollouts']:
        root = rollout.get('rollout_id')
        role, peer_root = roles.get(root, ('unknown', None))
        if role != 'peer' or route is None or route['engine'] != 'codex':
            continue
        if root == peer_root:
            traced_turns.add((root, tuple(sorted(rollout['inferences']))))
        folder = out / 'cell/trace' / rollout['trace']
        manifest = read(folder / 'manifest.json')
        # The inherited parser keeps the latest configuration. Inspect every
        # configuration so a corrected final event cannot hide an earlier route.
        for event in evidence.lines(folder / manifest.get('raw_event_log', 'trace.jsonl')):
            payload = event.get('payload') or {}
            if payload.get('type') != 'protocol_event_observed' or payload.get('event_type') != 'session_configured':
                continue
            configured = evidence.traces._payload(folder, payload.get('event_payload'), gaps) or {}
            thread = configured.get('thread_id')
            role, parent = roles.get(thread, ('unknown', None))
            if role != 'peer':
                gaps.append('unbound configuration in peer trace')
                continue
            want = route if thread == parent else dict(model=route['child_model'], effort=route['child_effort'])
            if configured.get('model') != want['model'] or configured.get('reasoning_effort') != want['effort']:
                violations.append('Codex peer native configuration route mismatch or missing')
        for thread, observed in rollout['threads'].items():
            role, parent = roles.get(thread, ancestor(thread, parents, owner_codex, roots['codex']))
            if role != 'peer':
                gaps.append(f'unbound thread {thread} in peer trace')
                continue
            want = route if thread == parent else dict(model=route['child_model'], effort=route['child_effort'])
            if observed.get('model') != want['model'] or observed.get('effort') != want['effort']:
                violations.append(f'Codex peer turn {root}/{thread} trace identity mismatch or missing')
        for item in rollout['inferences'].values():
            thread = item['thread']
            want = route if thread == peer_root else dict(model=route['child_model'], effort=route['child_effort'])
            if item.get('model') != want['model']:
                violations.append(f'Codex peer inference on {thread} ran another model')
    for session in roots['codex']:
        if sum(turn['session'] == session for turn in turns) != sum(root == session for root, _ in traced_turns):
            gaps.append(f'Codex peer {session}: attempts and distinct native turns do not match')

    # Turn contexts also carry sandbox and per-turn effort. Sets alone would hide
    # a missing effort on one resume when another turn names the expected effort.
    for path in (out / 'home/.codex/sessions').rglob('*.jsonl'):
        rows = evidence.lines(path)
        meta = next((row['payload'] for row in rows if row.get('type') == 'session_meta'), {})
        thread = meta.get('id')
        role, root = roles.get(thread, ('unknown', None))
        if role != 'peer' or route is None or route['engine'] != 'codex':
            continue
        want = route if thread == root else dict(model=route['child_model'], effort=route['child_effort'])
        contexts = [row['payload'] for row in evidence.usage0222.own_events(rows) if row.get('type') == 'turn_context']
        if not contexts:
            gaps.append(f'Codex peer {thread} lacks own turn contexts')
        for row in contexts:
            if row.get('model') != want['model'] or row.get('effort') != want['effort']:
                violations.append(f'Codex peer {thread} turn-context route mismatch or missing')
            if (row.get('sandbox_policy') or {}).get('type') != 'read-only' or row.get('approval_policy') != 'never':
                violations.append(f'Codex peer {thread} is not read-only/never-approve')
        if any(row.get('type') == 'event_msg' and (row.get('payload') or {}).get('type') == 'model_reroute' for row in rows):
            violations.append(f'Codex peer {thread} rerouted')

    claude_parents = {}
    for session, row in inv['transcripts'].items():
        parents_ = row.get('parents', set())
        if len(parents_) > 1:
            gaps.append(f'ambiguous Claude ancestry {session}')
        claude_parents[session] = next(iter(parents_)) if len(parents_) == 1 else None
    claude_roles = {session: ancestor(session, claude_parents, owner_claude, roots['claude'])
                    for session in inv['transcripts']}
    for session, (role, root) in claude_roles.items():
        if role == 'unknown':
            gaps.append(f'unbound Claude session {session}')
        elif role == 'peer' and session != root:
            violations.append('Claude read-only peer launched a child')
    seen_claude, claude_times = set(), {}
    for path in (out / 'home/.claude/projects').rglob('*.jsonl'):
        for row in evidence.lines(path):
            if row.get('sessionId') not in roots['claude'] or row.get('type') != 'assistant' or row.get('isApiErrorMessage'):
                continue
            message = row.get('message') or {}
            if message.get('model') == '<synthetic>':
                continue
            seen_claude.add(row['sessionId'])
            try:
                stamp = int(datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00')).timestamp() * 10**9)
                claude_times.setdefault(row['sessionId'], set()).add(stamp)
            except (ValueError, KeyError, TypeError, AttributeError):
                gaps.append('Claude peer native message lacks timestamp')
            if route and (str(message.get('model')).split('[')[0] != route['model'] or row.get('effort') != route['effort']):
                violations.append('Claude peer native message route mismatch or missing')
            for block in message.get('content', ()):
                if isinstance(block, dict) and block.get('type') == 'tool_use' and block.get('name') not in ('Read', 'Grep', 'Glob'):
                    violations.append('Claude peer used an unregistered tool')
    gaps.extend(f'Claude peer {session} has no native message' for session in roots['claude'] - seen_claude)
    for turn in turns:
        if turn['attempt'].get('engine') != 'claude' or not turn['completion']:
            continue
        start = turn['attempt']['started_ns']
        end = turn['completion'].get('ended_ns', start)
        if not any(start - 10**6 <= stamp <= end + 10**6
                   for stamp in claude_times.get(turn['session'], ())):
            gaps.append('Claude peer attempt/resume lacks a native message in its interval')
    # Narrow recognition of the guide's explicit helper command. This is not a
    # general shell interpreter; independent native sessions remain mandatory
    # evidence even when a command is wrapped or launched indirectly.
    helper_calls = 0
    for event in evidence.lines(out / 'run/stdout'):
        commands = []
        for block in (event.get('message') or {}).get('content', ()):
            if isinstance(block, dict) and block.get('type') == 'tool_use':
                commands.append((block.get('input') or {}).get('command', ''))
        item = event.get('item') or {}
        if event.get('type') == 'item.completed' and item.get('type') == 'command_execution':
            commands.append(item.get('command', ''))
        for command in commands:
            helper_calls += len(re.findall(r'\bpython(?:3(?:\.\d+)?)?\s+["\']?[^\s"\']*peer\.py["\']?\s+--engine\b', str(command)))
    if helper_calls > len(turns):
        gaps.append('observed helper launch has no retained attempt receipt')
    intervals = [(turn['attempt']['started_ns'], turn['completion'].get('ended_ns', 0))
                 for turn in turns if turn['completion']]
    if any(a[1] > b[0] for a, b in zip(intervals, intervals[1:])):
        protocol.append('independent peer attempts overlapped')
    # Attempt availability is observed separately from product correctness.
    # A later completed call may recover an earlier failure; costs remain in
    # the unchanged whole-run native inventory and every attempt is retained.
    completed = [bool(turn['completion'] and turn['completion'].get('status') == 'EXITED'
                      and turn['completion'].get('exit_code') == 0) for turn in turns]
    validation = 'NOT_ACTIVATED' if not turns else 'COMPLETED' if completed[-1] else 'INCOMPLETE'
    failed = [turn['attempt']['started_ns'] for turn, success in zip(turns, completed) if not success]
    return dict(status='MISMATCH' if violations else 'UNVERIFIED' if gaps else 'MATCH',
                violations=sorted(set(violations)), gaps=sorted(set(gaps)),
                protocol_violations=sorted(set(protocol)), activated=bool(turns),
                validation_completion=validation, failed_attempts=failed,
                recovered=bool(failed) and validation == 'COMPLETED',
                turns=[{k: v for k, v in turn.items() if k != 'capture_bytes'} for turn in turns],
                codex_roles={k: list(v) for k, v in roles.items()},
                claude_roles={k: list(v) for k, v in claude_roles.items()})
