"""Incremental fresh Codex rollout accounting; not a participant launch gate.

The caller supplies an isolated, initially empty session directory. Native
dispatch completeness, provider delivery latency and external review accounting
remain admission obligations; a successful snapshot does not prove them.
"""
import json
from pathlib import Path


COUNTERS = ('input_tokens', 'cached_input_tokens', 'cache_write_input_tokens',
            'output_tokens', 'reasoning_output_tokens', 'total_tokens')


class AccountingError(ValueError):
    pass


class Rollouts:
    def __init__(self, root, owner, *, input_limit, output_limit, dispatch_limit,
                 stale_seconds, started):
        self.root, self.owner = Path(root), owner
        self.limits = input_limit, output_limit, dispatch_limit
        self.stale_seconds, self.started = stale_seconds, started
        self.files, self.sessions = {}, {}
        self.failure = None

    def poll(self, now):
        if self.failure:
            raise AccountingError(self.failure)
        try:
            return self._poll(now)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            self.failure = str(exc)
            raise AccountingError(self.failure) from exc

    def _poll(self, now):
        paths = set(self.root.rglob('*.jsonl'))
        if self.files.keys() - paths:
            raise AccountingError('rollout disappeared')
        for path in sorted(paths):
            stat = path.stat()
            identity = stat.st_dev, stat.st_ino
            state = self.files.setdefault(path, dict(identity=identity, offset=0,
                                                    pending=b'', session=None))
            if identity != state['identity'] or stat.st_size < state['offset']:
                raise AccountingError('rollout replaced or truncated')
            with path.open('rb') as stream:
                stream.seek(state['offset'])
                data = stream.read()
            state['offset'] += len(data)
            lines = (state['pending'] + data).split(b'\n')
            state['pending'] = lines.pop()
            for line in lines:
                self._event(state, json.loads(line), now)
        for sid, session in self.sessions.items():
            seen, ancestor = {sid}, session['parent']
            while ancestor is not None:
                if ancestor in seen:
                    raise AccountingError('cyclic lineage')
                seen.add(ancestor)
                if ancestor not in self.sessions:
                    raise AccountingError('missing parent: ' + ancestor)
                ancestor = self.sessions[ancestor]['parent']
            if self.owner not in seen:
                raise AccountingError('unrelated session: ' + sid)
            if (session['active'] or not session['turns']) and now - session['observed'] >= self.stale_seconds:
                raise AccountingError('stale active usage: ' + sid)
        if self.owner not in self.sessions and now - self.started >= self.stale_seconds:
            raise AccountingError('missing owner telemetry')
        totals = {key: sum(s['usage'][key] for s in self.sessions.values()) for key in COUNTERS}
        calls = sum(len(s['turns']) for s in self.sessions.values())
        input_limit, output_limit, dispatch_limit = self.limits
        exceeded = (totals['input_tokens'] > input_limit or
                    totals['output_tokens'] > output_limit or calls > dispatch_limit)
        result = dict(totals=totals, dispatches=calls, sessions=len(self.sessions),
                      exceeded=exceeded,
                      overshoot=dict(input_tokens=max(0, totals['input_tokens'] - input_limit),
                                     output_tokens=max(0, totals['output_tokens'] - output_limit),
                                     dispatches=max(0, calls - dispatch_limit)))
        if exceeded:
            self.failure = 'budget exceeded: ' + json.dumps(result, sort_keys=True)
        return result

    def _event(self, state, event, now):
        payload = event['payload']
        if event['type'] == 'session_meta':
            sid = payload['id']
            if state['session'] is not None or sid in self.sessions:
                raise AccountingError('duplicate session metadata')
            if payload.get('forked_from_id'):
                raise AccountingError('fork baseline not supported')
            source = payload['source']
            if sid == self.owner:
                if source != 'exec':
                    raise AccountingError('owner must be a fresh exec root')
                parent = None
            else:
                if not isinstance(source, dict):
                    raise AccountingError('non-native child lineage')
                parent = source['subagent']['thread_spawn']['parent_thread_id']
            self.sessions[sid] = dict(parent=parent, usage=dict.fromkeys(COUNTERS, 0),
                                      last=None, turns=set(), active=None, observed=now, measured=False)
            state['session'] = sid
            return
        if state['session'] is None:
            raise AccountingError('event before session metadata')
        if event['type'] != 'event_msg':
            return
        session = self.sessions[state['session']]
        kind = payload['type']
        if kind == 'task_started':
            turn = payload['turn_id']
            if not isinstance(turn, str) or not turn:
                raise AccountingError('invalid dispatch id')
            if session['active'] or turn in session['turns']:
                raise AccountingError('overlapping or replayed dispatch')
            session['turns'].add(turn)
            session.update(active=turn, observed=now, measured=False)
        elif kind == 'token_count' and payload.get('info') is not None:
            usage = payload['info']['total_token_usage']
            values = {key: usage[key] for key in COUNTERS}
            if any(type(v) is not int or v < 0 for v in values.values()):
                raise AccountingError('invalid token counter')
            if (values['total_tokens'] != values['input_tokens'] + values['output_tokens'] or
                    values['cached_input_tokens'] + values['cache_write_input_tokens'] > values['input_tokens'] or
                    values['reasoning_output_tokens'] > values['output_tokens']):
                raise AccountingError('unsupported counter semantics')
            previous = session['usage']
            last = {key: payload['info']['last_token_usage'][key] for key in COUNTERS}
            if any(type(v) is not int or v < 0 for v in last.values()):
                raise AccountingError('invalid last usage counter')
            if any(values[key] < previous[key] for key in COUNTERS):
                raise AccountingError('counter regression')
            if values != previous:
                if not session['active']:
                    raise AccountingError('usage without active dispatch')
                if any(values[key] - previous[key] != last[key] for key in COUNTERS):
                    raise AccountingError('unknown baseline or missing usage event')
                session.update(usage=values, last=last, observed=now, measured=True)
            elif session['last'] != last:
                raise AccountingError('inconsistent duplicate usage')
            # A repeated cumulative sample is not new usage or a liveness signal.
        elif kind in ('task_complete', 'turn_aborted'):
            if payload['turn_id'] != session['active'] or not session['measured']:
                raise AccountingError('terminal without measured dispatch')
            session['active'] = None

    def finish(self, now):
        result = self.poll(now)
        if (self.owner not in self.sessions or
                any(s['active'] or not s['turns'] for s in self.sessions.values()) or
                any(s['session'] is None or s['pending'] for s in self.files.values())):
            self.failure = 'incomplete terminal telemetry'
            raise AccountingError(self.failure)
        return result
