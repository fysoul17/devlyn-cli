"""Read-only native Claude receipt accounting; never rewrites prior verdicts."""
import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import re

COUNTERS = ('input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens',
            'output_tokens', 'thinking_tokens')
AGGREGATE_KEYS = ('inputTokens', 'cacheCreationInputTokens', 'cacheReadInputTokens',
                  'outputTokens', 'thinkingTokens')
STOPS = {'end_turn', 'tool_use'}
BODY = Path('home/.claude/api-bodies')
PROJECTS = Path('home/.claude/projects')


class EvidenceError(ValueError):
    """Diagnostics identify failed invariants, never include body contents."""


def require(condition, message):
    if not condition:
        raise EvidenceError(message)


def object_pairs(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, 'duplicate JSON key')
        value[key] = item
    return value


def invalid_constant(_):
    raise EvidenceError('non-finite JSON number')


def decode(raw):
    return json.loads(raw.decode('utf-8'), object_pairs_hook=object_pairs,
                      parse_constant=invalid_constant)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def usage(value, *, terminal=True):
    require(isinstance(value, dict), 'usage is not an object')
    result = {key: value[key] for key in COUNTERS[:-1] if key in value}
    if 'output_tokens_details' in value:
        details = value['output_tokens_details']
        require(isinstance(details, dict), 'invalid thinking counter object')
        if 'thinking_tokens' in details:
            result['thinking_tokens'] = details['thinking_tokens']
    require(all(type(v) is int and v >= 0 for v in result.values()), 'invalid token counter')
    require(not terminal or set(result) == set(COUNTERS), 'terminal counters incomplete')
    if 'thinking_tokens' in result and 'output_tokens' in result:
        require(result['thinking_tokens'] <= result['output_tokens'], 'thinking exceeds output')
    return result


def message_usage(message):
    stop = message.get('stop_reason')
    require(stop is None or stop in STOPS, 'invalid stop reason')
    if stop is not None or 'usage' in message:
        return usage(message.get('usage'), terminal=stop is not None)
    return None


def audit(out, *, manifest_sha256, model, effort, account):
    """MATCH covers one successful owner and linked foreground children only.

    Caller-supplied expectations and the manifest digest must already be frozen.
    Identity/lifecycle/product gates outside this accounting scope remain required.
    """
    report = dict(schema='0254-native-receipts-v1', status='UNKNOWN', gaps=[],
                  totals=None, input_tokens=None, output_tokens=None, messages=[],
                  reported_aggregate=None, reported_owner_usage=None, sources={},
                  scope='One successful native owner and linked foreground children; '
                        'observations on UNKNOWN are not whole-run totals; '
                        'not provider billing or product acceptance.')
    try:
        reconcile(Path(out), manifest_sha256, model, effort, account, report)
    except (EvidenceError, OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        detail = str(exc) if isinstance(exc, EvidenceError) else type(exc).__name__
        report['gaps'] = [detail]
    return report


def sum_usage(rows):
    rows = list(rows)
    return {key: sum(row['usage'][key] for row in rows) for key in COUNTERS}


def reconcile(out, manifest_sha256, model, effort, account, report):
    sources = report['sources']
    require(text(model) and text(effort), 'missing model or effort expectation')
    require(isinstance(account, str) and re.fullmatch(r'[a-f0-9]{12}', account),
            'invalid account hash expectation')
    require(isinstance(manifest_sha256, str) and re.fullmatch(r'[a-f0-9]{64}', manifest_sha256),
            'invalid manifest hash expectation')
    manifest_path = out / 'evidence.manifest.json'
    require(manifest_path.is_file() and not manifest_path.is_symlink(), 'manifest not regular')
    raw = manifest_path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == manifest_sha256, 'manifest hash mismatch')
    manifest = decode(raw)
    require(manifest['failures'] == [] and isinstance(manifest['files'], dict), 'incomplete seal')
    sources['evidence.manifest.json'] = manifest_sha256
    for name in manifest['files']:
        relative = Path(name)
        require(not relative.is_absolute() and '..' not in relative.parts
                and relative.as_posix() == name, 'invalid sealed path')

    def regular_path(relative):
        path = out / relative
        require(not relative.is_absolute() and '..' not in relative.parts
                and path.resolve().is_relative_to(out.resolve())
                and not any((out / Path(*relative.parts[:n])).is_symlink()
                            for n in range(1, len(relative.parts) + 1)),
                'source not a regular in-root file')
        return path

    # Compare the frozen census, not just files still present at audit time.
    for root in (BODY, PROJECTS):
        actual = set()
        root_path = regular_path(root)
        require(root_path.is_dir(), 'missing native evidence directory')
        for directory, dirs, files in os.walk(root_path):
            for name in dirs + files:
                relative = (Path(directory) / name).relative_to(out)
                path = regular_path(relative)
                if name in files and (root == BODY or name.endswith(('.jsonl', '.meta.json'))):
                    require(path.is_file(), 'nonregular native evidence')
                    actual.add(relative.as_posix())
        sealed = {name for name in manifest['files'] if Path(name).is_relative_to(root)
                  and (root == BODY or name.endswith(('.jsonl', '.meta.json')))}
        require(actual == sealed, 'sealed native inventory mismatch')

    def read(relative, *, jsonl=False):
        relative = Path(relative)
        path = regular_path(relative)
        require(path.is_file(), 'source not a regular file')
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        require(manifest['files'].get(relative.as_posix()) == digest, 'source seal mismatch')
        sources[relative.as_posix()] = digest
        if jsonl:
            require(bool(data) and data.endswith(b'\n'), 'incomplete JSONL framing')
            rows = [decode(line) for line in data.split(b'\n')[:-1]]
            require(all(isinstance(row, dict) for row in rows), 'JSONL row is not an object')
            return rows
        value = decode(data)
        require(isinstance(value, dict), 'JSON source is not an object')
        return value

    stream = read('run/stdout', jsonl=True)
    results = [row for row in stream if row.get('type') == 'result']
    inits = [row for row in stream if row.get('type') == 'system' and row.get('subtype') == 'init']
    require(len(results) == len(inits) == 1, 'ambiguous owner invocation')
    result, init = results[0], inits[0]
    session = result.get('session_id')
    require(text(session) and init.get('session_id') == session and init.get('model') == model,
            'owner identity mismatch')
    require(result.get('is_error') is False and result.get('subtype') == 'success',
            'owner did not succeed')

    aggregate = result['modelUsage']
    require(isinstance(aggregate, dict) and set(aggregate) == {model},
            'unexpected aggregate model coverage')
    reported = {key: aggregate[model][native] for key, native in zip(COUNTERS, AGGREGATE_KEYS)}
    require(all(type(value) is int and value >= 0 for value in reported.values())
            and reported['thinking_tokens'] <= reported['output_tokens'],
            'invalid native aggregate counters')
    report['reported_aggregate'] = reported
    report['reported_owner_usage'] = usage(result['usage'])

    transcript_paths = sorted((out / PROJECTS).rglob('*.jsonl'))
    owners = [p for p in transcript_paths if 'subagents' not in p.relative_to(out / PROJECTS).parts]
    require(len(owners) == 1 and owners[0].stem == session, 'ambiguous owner transcript')
    owner = owners[0]
    messages, transcripts, agent_paths, uuids = defaultdict(list), {}, {}, {}
    events = list(stream)
    for path in transcript_paths:
        relative = path.relative_to(out)
        rows = read(relative, jsonl=True)
        transcripts[path] = rows
        events.extend(rows)
        agent = None
        if path != owner:
            require(path.parent == owner.with_suffix('') / 'subagents'
                    and path.stem.startswith('agent-'), 'unsupported child carrier')
            agent = path.stem.removeprefix('agent-')
            require(text(agent) and agent not in agent_paths, 'ambiguous child identity')
            agent_paths[agent] = path
        count = 0
        for row in rows:
            if row.get('type') != 'assistant':
                continue
            msg = row['message']
            require(isinstance(msg, dict) and row.get('sessionId') == session
                    and row.get('agentId') == agent and msg.get('model') == model,
                    'transcript identity mismatch')
            require(all(text(v) for v in (msg.get('id'), row.get('requestId'), row.get('uuid'))),
                    'incomplete transcript identity')
            message_usage(msg)
            identity = (msg['id'], row['requestId'], agent)
            require(uuids.setdefault(row['uuid'], identity) == identity, 'conflicting block UUID')
            messages[msg['id']].append((agent, row))
            count += 1
        require(count > 0, 'transcript has no inference anchor')

    expected_meta = {path.with_suffix('.meta.json') for path in agent_paths.values()}
    require(set((out / PROJECTS).rglob('*.meta.json')) == expected_meta,
            'orphan or missing child metadata')

    for row in events:
        if row.get('type') == 'user':
            content = row.get('message', {}).get('content')
            marker = '[Request interrupted by user]'
            require(content != [{'type': 'text', 'text': marker}],
                    'native interruption outside scope')
        require(row.get('type') != 'error' and not row.get('isApiErrorMessage')
                and row.get('subtype') not in ('api_error', 'api_retry'), 'error or retry outside scope')
        if row.get('subtype') == 'task_notification':
            require(row.get('status') == 'completed', 'child did not complete')
        if row.get('subtype') == 'task_updated' and 'status' in row.get('patch', {}):
            require(row['patch']['status'] in ('running', 'completed'), 'child cancellation or failure')

    index = read(BODY / 'index.jsonl', jsonl=True)
    require(index, 'empty receipt index')
    for key in ('request_id', 'message_id', 'message_uuid', 'request_file', 'response_file'):
        values = [row.get(key) for row in index]
        require(all(text(value) for value in values) and len(set(values)) == len(values),
                'missing or duplicate index identity')
    names = {'index.jsonl'}
    for row in index:
        for key, suffix in (('request_file', '.request.json'), ('response_file', '.response.json')):
            name = row[key]
            require(Path(name).name == name and name.endswith(suffix), 'invalid body filename')
            names.add(name)
        require(row['response_file'] == row['request_id'] + '.response.json', 'response request mismatch')
    require({p.name for p in (out / BODY).iterdir()} == names, 'orphan or missing body file')
    require(set(messages) == {row['message_id'] for row in index}, 'missing inference or transcript anchor')

    receipts, responses = report['messages'], {}
    for row in index:
        request, response = read(BODY / row['request_file']), read(BODY / row['response_file'])
        user = decode(request['metadata']['user_id'].encode('utf-8'))
        require(user['session_id'] == row['session_id'] == session
                and hashlib.sha256(user['account_uuid'].encode('utf-8')).hexdigest()[:12] == account,
                'request account or session mismatch')
        require(request['model'] == response['model'] == row['model'] == model
                and request['output_config']['effort'] == effort, 'request model or effort mismatch')
        require(response['type'] == 'message' and response['role'] == 'assistant'
                and response['id'] == row['message_id'] and response.get('stop_reason') in STOPS,
                'invalid terminal response identity or stop')
        values = usage(response['usage'])
        snapshots = messages[row['message_id']]
        agents = {agent for agent, _ in snapshots}
        require(len(agents) == 1, 'message has multiple carriers')
        agent = next(iter(agents))
        require(any(event['uuid'] == row['message_uuid'] for _, event in snapshots),
                'missing exact block anchor')
        terminal_count = 0
        for _, event in snapshots:
            require(event['requestId'] == row['request_id'], 'conflicting request identity')
            msg = event['message']
            if msg.get('stop_reason') is not None:
                require(msg['stop_reason'] == response['stop_reason'] and usage(msg['usage']) == values,
                        'terminal transcript conflicts with native receipt')
                terminal_count += 1
        expected_query = 'sdk'
        if agent is not None:
            meta = read(agent_paths[agent].relative_to(out).with_suffix('.meta.json'))
            require(text(meta.get('agentType')), 'missing child type')
            expected_query = 'agent:builtin:' + meta['agentType']
        require(row.get('query_source') == expected_query, 'query source and carrier disagree')
        responses[row['message_id']] = response
        receipts.append(dict(message_id=row['message_id'], request_id=row['request_id'],
                             message_uuid=row['message_uuid'], agent_id=agent, usage=values,
                             stop_reason=response['stop_reason'], source='native_terminal_body',
                             transcript_terminal=terminal_count > 0))

    by_message = {row['message_id']: row for row in receipts}
    for event in stream:
        if event.get('type') == 'assistant':
            msg = event['message']
            require(event.get('session_id') == session and msg.get('id') in by_message
                    and msg.get('model') == model, 'unbound stdout inference')
            row = by_message[msg['id']]
            identity = (msg['id'], row['request_id'], row['agent_id'])
            require(event.get('request_id') == row['request_id']
                    and uuids.get(event.get('uuid')) == identity
                    and event.get('agent_id') == row['agent_id'], 'stdout identity mismatch')
            parent = None
            if row['agent_id'] is not None:
                meta = read(agent_paths[row['agent_id']].relative_to(out).with_suffix('.meta.json'))
                parent = meta.get('toolUseId')
            require('parent_tool_use_id' in event and event['parent_tool_use_id'] == parent,
                    'stdout child parent mismatch')
            message_usage(msg)
            if msg.get('stop_reason') is not None:
                row = by_message[msg['id']]
                require(msg['stop_reason'] == row['stop_reason'] and usage(msg['usage']) == row['usage'],
                        'stdout terminal conflicts with native receipt')

    calls = {}
    for snapshots in messages.values():
        for agent, event in snapshots:
            for block in event['message'].get('content', []):
                if block.get('type') == 'tool_use' and block.get('name') == 'Agent':
                    require(agent is None and text(block.get('id')), 'unsupported nested child')
                    require(calls.setdefault(block['id'], block) == block, 'conflicting child launch')
                    require(block in responses[event['message']['id']]['content'],
                            'child launch conflicts with terminal body')
    linked_tools = set()
    for agent, path in agent_paths.items():
        meta = read(path.relative_to(out).with_suffix('.meta.json'))
        tool = meta.get('toolUseId')
        require(tool in calls and tool not in linked_tools and meta.get('spawnDepth') == 1
                and meta.get('requestShape') == 'foreground'
                and meta.get('requestNonInteractive') is True, 'unbound foreground child')
        linked_tools.add(tool)
        call = calls[tool]['input']
        require(call.get('subagent_type') == meta['agentType'] and call.get('run_in_background') is False,
                'child launch metadata mismatch')
        started = [r for r in stream if r.get('subtype') == 'task_started' and r.get('task_id') == agent]
        ended = [r for r in stream if r.get('subtype') == 'task_notification' and r.get('task_id') == agent]
        returned = [r for r in transcripts[owner] if isinstance(r.get('toolUseResult'), dict)
                    and r['toolUseResult'].get('agentId') == agent]
        require(len(started) == len(ended) == len(returned) == 1, 'incomplete child lifecycle')
        require(started[0].get('tool_use_id') == ended[0].get('tool_use_id') == tool
                and started[0].get('is_backgrounded') is False, 'child lifecycle identity mismatch')
        returned = returned[0]
        require(returned.get('sessionId') == session
                and returned['toolUseResult'].get('status') == 'completed'
                and returned['toolUseResult'].get('resolvedModel') == model
                and any(b.get('type') == 'tool_result' and b.get('tool_use_id') == tool
                        for b in returned['message']['content']), 'unbound child tool result')
        child_usage = sum_usage(r for r in receipts if r['agent_id'] == agent)
        child_result = returned['toolUseResult']
        require(usage(child_result.get('usage')) == child_usage
                and type(child_result.get('totalTokens')) is int
                and child_result['totalTokens'] == sum(child_usage[k] for k in COUNTERS[:4]),
                'child result aggregate mismatch')
    require(set(calls) == linked_tools, 'unaccounted child launch')
    bash_tools = {block['id'] for row in transcripts[owner] if row.get('type') == 'assistant'
                  for block in row['message'].get('content', [])
                  if block.get('type') == 'tool_use' and block.get('name') == 'Bash'
                  and text(block.get('id'))}
    shell_tasks = defaultdict(list)
    for row in stream:
        if row.get('subtype') in ('task_started', 'task_notification', 'task_updated'):
            require(text(row.get('task_id')) and row.get('session_id') == session,
                    'unbound task lifecycle')
            if row['task_id'] not in agent_paths:
                shell_tasks[row['task_id']].append(row)
    for rows in shell_tasks.values():
        started = [r for r in rows if r['subtype'] == 'task_started']
        ended = [r for r in rows if r['subtype'] == 'task_notification']
        require(len(started) == len(ended) == 1, 'unbound task lifecycle')
        tool = started[0].get('tool_use_id')
        require(started[0].get('task_type') == 'local_bash'
                and started[0].get('is_backgrounded') is False and tool in bash_tools
                and ended[0].get('tool_use_id') == tool and ended[0].get('status') == 'completed'
                and all(r.get('type') == 'system' and r.get('tool_use_id', tool) == tool for r in rows),
                'unbound task lifecycle')

    totals = sum_usage(receipts)
    require(reported == totals, 'whole native aggregate mismatch')
    require(report['reported_owner_usage'] == sum_usage(r for r in receipts if r['agent_id'] is None),
            'owner-only aggregate mismatch')
    report.update(status='MATCH', totals=totals,
                  input_tokens=sum(totals[key] for key in COUNTERS[:3]),
                  output_tokens=totals['output_tokens'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--model', required=True)
    parser.add_argument('--effort', required=True)
    parser.add_argument('--account', required=True, help='Frozen 12-hex SHA256 account prefix, not a credential')
    args = parser.parse_args()
    report = audit(args.out, manifest_sha256=args.manifest_sha256, model=args.model,
                   effort=args.effort, account=args.account)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['status'] == 'MATCH' else 2)
