"""Prospective native Claude accounting closure; never rewrites raw captures.

The inherited recorder retains all reported costs. This guard requires terminal
per-message evidence for the same session totals, including peers and resumes.
An unbound interrupted request remains UNKNOWN even when a later turn succeeds.
"""
from collections import defaultdict
import hashlib
from pathlib import Path


COUNTERS = dict(input_tokens='inputTokens', cache_read_input_tokens='cacheReadInputTokens',
                cache_creation_input_tokens='cacheCreationInputTokens', output_tokens='outputTokens')


def audit(out, evidence, peer_receipts):
    out = Path(out)
    gaps, sources, errors = [], {}, []
    messages, parents = {}, defaultdict(set)
    stream = evidence.lines(out / 'run/stdout')
    envelopes, unreadable = evidence.claude_envelopes(out)
    gaps += [f'unreadable result {path}' for path in unreadable]
    # Reuse the receipt inventory, including incomplete invocations and resumes.
    # A stream-only retry need not have a corresponding native transcript error.
    captures = {out / 'run/stdout'}
    for receipt in peer_receipts:
        attempt = receipt['attempt']
        if attempt.get('engine') == 'claude':
            captures.add((out / receipt['path']).with_name(attempt['capture']))
    for event in stream:
        if event.get('type') == 'result' and event.get('session_id'):
            evidence.add_envelope(envelopes, event, 'run/stdout', any_source=True)

    aggregates = {}
    for session, entries in envelopes.items():
        totals = aggregates.setdefault(session, {})
        for entry in entries:
            for model, usage in entry['usage'].items():
                model = model.split('[')[0]
                values = {key: usage.get(native, usage.get(key)) for key, native in COUNTERS.items()}
                if 'thinkingTokens' in usage:
                    values['thinking_tokens'] = usage['thinkingTokens']
                if not all(type(value) is int and value >= 0 for value in values.values()):
                    gaps.append(f'{session}: result lacks nonnegative integer counters')
                    continue
                target = totals.setdefault(model, {})
                for key, value in values.items():
                    target[key] = max(target.get(key, 0), value)

    for path in sorted((out / 'home/.claude/projects').rglob('*.jsonl')):
        relative = str(path.relative_to(out))
        sources[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        for line, event in enumerate(evidence.lines(path), 1):
            session = event.get('sessionId')
            parent = event.get('parentSessionId')
            if parent and parent != session:
                parents[session].add(parent)
            if event.get('type') == 'system' and event.get('subtype') == 'api_error':
                errors.append(dict(session=session, request_id=event.get('requestId'),
                                   path=relative, line=line))
            message = event.get('message') or {}
            if (event.get('type') != 'assistant' or event.get('isApiErrorMessage')
                    or message.get('model') == '<synthetic>'):
                continue
            if not session or not message.get('id'):
                gaps.append(f'{relative}:{line}: assistant lacks session/message identity')
                continue
            key = (session, message['id'])
            previous = messages.get(key)
            if previous and previous['request_id'] != event.get('requestId'):
                gaps.append(f'{relative}:{line}: message has conflicting request identities')
            messages[key] = dict(message=message, request_id=event.get('requestId'),
                                 path=relative, line=line)

    def accounting_root(session):
        seen = set()
        while session not in aggregates and len(parents[session]) == 1 and session not in seen:
            seen.add(session)
            session = next(iter(parents[session]))
        return session

    terminal, closed_requests, terminal_count = {}, set(), 0
    for (session, message_id), record in messages.items():
        message = record['message']
        root = accounting_root(session)
        model = str(message.get('model')).split('[')[0]
        usage = message.get('usage') or {}
        values = {key: usage.get(key) for key in COUNTERS}
        if not message.get('stop_reason') or not all(type(v) is int and v >= 0 for v in values.values()):
            gaps.append(f'{session}/{message_id}: no terminal message usage')
            continue
        terminal_count += 1
        if record['request_id']:
            closed_requests.add((session, record['request_id']))
        total = terminal.setdefault(root, {}).setdefault(model, dict.fromkeys(COUNTERS, 0))
        for key, value in values.items():
            total[key] += value
        thinking = (usage.get('output_tokens_details') or {}).get('thinking_tokens')
        if 'thinking_tokens' in aggregates.get(root, {}).get(model, {}):
            if type(thinking) is not int or thinking < 0:
                gaps.append(f'{session}/{message_id}: no terminal reasoning counter')
            else:
                total['thinking_tokens'] = total.get('thinking_tokens', 0) + thinking

    comparisons = {}
    for session in aggregates.keys() | terminal.keys():
        comparisons[session] = {}
        for model in aggregates.get(session, {}).keys() | terminal.get(session, {}).keys():
            reported = aggregates.get(session, {}).get(model)
            reconstructed = terminal.get(session, {}).get(model)
            matches = bool(reported and reconstructed) and reported == reconstructed
            comparisons[session][model] = dict(reported=reported, terminal=reconstructed, matches=matches)
            if not matches:
                gaps.append(f'{session}/{model}: native aggregate does not reconcile with terminal messages')

    # A successful retry's different request ID cannot close the interrupted one.
    # Explicitly bound terminal evidence can close an error; anonymous errors cannot.
    for error in errors:
        bound = bool(error['request_id']) and (error['session'], error['request_id']) in closed_requests
        error['terminal_request_bound'] = bound
        if not bound:
            gaps.append(f"{error['path']}:{error['line']}: API error without terminal request usage")
    retries = []
    for path in sorted(captures):
        relative = str(path.relative_to(out))
        if not path.is_file():
            gaps.append(f'{relative}: missing invocation capture')
            continue
        sources[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        for line, event in enumerate(evidence.lines(path), 1):
            if event.get('type') != 'system' or event.get('subtype') != 'api_retry':
                continue
            session, request = event.get('session_id'), event.get('requestId')
            bound = bool(request) and (session, request) in closed_requests
            retries.append(dict(session=session, request_id=request, path=relative,
                                line=line, terminal_request_bound=bound))
            if not bound:
                gaps.append(f'{relative}:{line}: stream retry lacks terminal request binding')

    gaps = sorted(set(gaps))
    return dict(schema='0238-claude-accounting-v1', status='UNKNOWN' if gaps else 'MATCH',
                gaps=gaps, sources=sources, sessions=comparisons, api_errors=errors,
                stream_retries=retries, terminal_message_count=terminal_count,
                unknown_residual=(dict(input_tokens=None, output_tokens=None, reasoning_tokens=None)
                                  if gaps else None),
                scope='Native emitted accounting, not provider billing. Thinking is already in output; '
                      'progress estimates are never counted. All reported costs remain in inherited usage.')
