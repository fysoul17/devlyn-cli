"""0208 accounting with the observed 0.155.1 native fork-context boundary."""
import importlib.util
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / '0208/accounting.py'
spec = importlib.util.spec_from_file_location('base_accounting', BASE)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
AccountingError = base.AccountingError


class Rollouts(base.Rollouts):
    def _event(self, state, event, now):
        payload = event['payload']
        if state['session'] is None and event['type'] == 'session_meta' and payload.get('forked_from_id'):
            parent = payload['source']['subagent']['thread_spawn']['parent_thread_id']
            if payload['forked_from_id'] != parent or payload.get('parent_thread_id') != parent:
                raise AccountingError('inconsistent native fork parent')
            cleaned = dict(payload)
            del cleaned['forked_from_id']
            super()._event(state, dict(event, payload=cleaned), now)
            state.update(copying=True, inherited_sessions=set(), inherited_turns=set())
            return
        if state.get('copying'):
            kind = payload.get('type')
            if event['type'] == 'event_msg' and kind == 'thread_settings_applied':
                if payload.get('thread_id') != state['session']:
                    raise AccountingError('fork boundary belongs to another thread')
                state['copying'] = False
                return
            if event['type'] == 'session_meta':
                state['inherited_sessions'].add(payload['id'])
            elif event['type'] == 'turn_context' or event['type'] == 'event_msg' and kind in ('task_started', 'task_complete'):
                state['inherited_turns'].add(payload['turn_id'])
            elif event['type'] not in ('response_item', 'world_state'):
                # In particular, never silently discard copied usage counters.
                raise AccountingError('unsupported event before native fork boundary')
            return
        super()._event(state, event, now)

    def finish(self, now):
        result = super().finish(now)
        for state in self.files.values():
            if 'copying' not in state:
                continue
            ancestors, turns = set(), set()
            parent = self.sessions[state['session']]['parent']
            while parent is not None:
                ancestors.add(parent)
                turns.update(self.sessions[parent]['turns'])
                parent = self.sessions[parent]['parent']
            if (state['copying'] or not state['inherited_sessions'] <= ancestors or
                    not state['inherited_turns'] <= turns):
                self.failure = 'unverified native inherited context'
                raise AccountingError(self.failure)
        return result
