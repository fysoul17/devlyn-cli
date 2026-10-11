"""Post-run trace audit of the registered transport criteria; never changes raw verdicts."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ref(item):
    return {'line': item[0], 'timestamp': item[1].get('timestamp')}


def audit(cell, output):
    events = [json.loads(line) for line in (cell / 'run/stdout').read_text().splitlines()]
    uses, returns, final_text = [], {}, []
    for number, row in enumerate(events, 1):
        for block in row.get('message', {}).get('content', []):
            item = (number, row, block)
            if block.get('type') == 'tool_use':
                uses.append(item)
            if block.get('type') == 'tool_result':
                returns[block['tool_use_id']] = item
            if (block.get('type') == 'text' and row.get('type') == 'assistant'
                    and not row.get('parent_tool_use_id')):
                final_text.append(item)
    agents = [item for item in uses if item[2]['name'] == 'Agent']
    assert len(agents) == 1
    launch = agents[0]
    agent_id = launch[2]['id']
    assert launch[2]['input']['run_in_background'] is False
    started = [row for row in events if row.get('subtype') == 'task_started'
               and row.get('tool_use_id') == agent_id]
    assert len(started) == 1 and started[0]['is_backgrounded'] is False
    received = returns[agent_id]
    done = received[1]['tool_use_result']
    assert done['status'] == 'completed'
    payload = json.loads(done['content'][0]['text'])
    assert payload == read(cell / 'snapshot/receipt.json')
    scenario = read(cell / 'snapshot/scenario.json')
    children = [item for item in uses if item[1].get('parent_tool_use_id') == agent_id]
    assert len(children) == len(scenario['parts']) == len(payload['parts'])
    previous, parts = launch[0], []
    for child, part, saved in zip(children, scenario['parts'], payload['parts']):
        args = child[2]['input']
        assert child[2]['name'] == 'Bash'
        assert args['command'] == f"python3 -B /cell/work/child_gate.py {part['part']}"
        assert args['timeout'] == 360000 and args['run_in_background'] is False
        result = returns[child[2]['id']]
        assert result[2].get('is_error') is False
        gate = json.loads(result[2]['content'].splitlines()[-1])
        assert gate == saved and gate['elapsed_seconds'] >= part['wait_seconds']
        assert previous < child[0] < result[0] < received[0]
        previous = result[0]
        parts.append({'call': ref(child), 'result': ref(result), 'gate': gate})
    if scenario['id'] == 'FG-LONG':
        assert done['totalDurationMs'] > 600000
    written = next(item for item in uses if item[2]['name'] == 'Write'
                   and item[2]['input'].get('file_path') == '/cell/work/receipt.json')
    commit = next(item for item in uses if item[0] > written[0] and item[2]['name'] == 'Bash'
                  and ' commit -q ' in item[2]['input'].get('command', ''))
    assert received[0] < written[0] < commit[0] < final_text[-1][0]
    stats = events[-1]['subagent_stats']
    assert (stats['completed'] == stats['spawned'] == stats['requested']['foreground'] == 1
            and stats['started_in_background'] == 0 and not any(stats['killed'].values()))
    totals, identities, seen = {'input': 0, 'output': 0}, [], set()
    for native in sorted((cell / 'home/.claude/projects').rglob('*.jsonl')):
        messages = {}
        for line in native.read_text().splitlines():
            row = json.loads(line)
            message = row.get('message', {})
            if row.get('type') == 'assistant' and message.get('role') == 'assistant':
                assert row.get('effort') == 'max' and message['model'] == 'claude-opus-5-5'
                messages[message['id']] = message
        for key, message in messages.items():
            assert key not in seen and message.get('stop_reason') in ('tool_use', 'end_turn')
            seen.add(key)
            usage = message['usage']
            totals['input'] += sum(usage.get(k, 0) for k in
                                   ('input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens'))
            totals['output'] += usage['output_tokens']
        identities.append({'path': str(native.relative_to(cell)), 'sha256': sha(native),
                           'model': 'claude-opus-5-5', 'effort': 'max',
                           'terminal_messages': len(messages)})
    verdict = read(cell.parent / ('verdict-' + cell.name + '.json'))
    assert totals == {'input': verdict['input_tokens'], 'output': verdict['output_tokens']}
    assert (verdict['status'] == 'CHECKS_PASS' and verdict['identity']['status'] == 'MATCH'
            and verdict['usage'] == 'COMPLETE' and verdict['teardown'] == 'CLEAN')
    assert not (cell / 'run/stderr').read_text()
    manifest = read(cell / 'evidence.manifest.json')
    assert not manifest['failures']
    for name, expected in manifest['files'].items():
        assert sha(cell / name) == expected, name
    result = {'status': 'TRANSPORT_PASS', 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'cell': cell.name, 'audit_source_sha256': sha(Path(__file__)),
              'sequence': {'launch': ref(launch), 'parts': parts,
                           'parent_receives_terminal_child': ref(received),
                           'receipt_write': ref(written), 'commit_command': ref(commit),
                           'owner_final': ref(final_text[-1])},
              'child_duration_ms': done['totalDurationMs'], 'subagent_stats': stats,
              'native_identity_and_accounting': identities, 'independently_summed_usage': totals,
              'retained_evidence_entries_matched': len(manifest['files']), 'verdict': verdict}
    with output.open('x') as stream:
        stream.write(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: result[k] for k in ('status', 'cell', 'child_duration_ms',
                                           'independently_summed_usage', 'sequence')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cell', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    audit(args.cell.resolve(), args.output.resolve())
