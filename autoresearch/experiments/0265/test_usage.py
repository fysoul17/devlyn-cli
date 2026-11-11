"""DESIGN Q7 offline: Codex B's `codex app-server` config read in model identity and usage accounting.

Fixtures (fixtures/usage/) are real evidence, no model call:
- appserver-evidence.json: every path `devlyn run codex` 4.3.30 left in a SMOKE codex-B cell in the 0265 image with
  the pinned Codex (no credential; a recording shim stood in for the owner). It holds no trace, no rollout and no
  file the readers parse: the config read starts no thread.
- appserver-thread/: the real trace of an app-server session that did start a thread (thread/start, no turn): the
  shape a model seat added to that evidence takes. It starts before the owner, as the config read does.
- owner/: an owner session of real shape for 0257 d008-D4-codex-B-r1 (its announced stream and archived usage; the
  trace and rollout in Codex's own row and payload shapes, d008's totals split over two inferences).

The identity is the one the apparatus records (X/cell.py) and record_usage is the module run_cell.py loads.
"""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
FIX = HERE / 'fixtures/usage'


def load(name, path):
    spec = importlib.util.spec_from_file_location('test_0265_usage_' + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cell = load('cell', HERE / 'cell.py')
usage = load('record_usage', next(p for p in (HERE / 'record_usage.py', HERE.parent / '0256/record_usage.py')
                                  if p.is_file()))  # run_cell.load's order
EVIDENCE = json.loads((FIX / 'appserver-evidence.json').read_text())
OWNER = '01a164d6-b795-7022-847b-14d9289c22db'
APP = '01a1c90c-63cc-7d93-bfc1-9c6f9e946cf2'


class AppServerSession(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)

    def cell_out(self, name, appserver=True, owner=False, seat=False, inference=False):
        """A finished codex-B cell from the fixtures: the app-server evidence, the owner session, an app-server seat."""
        out = self.root / name
        for path in EVIDENCE['dirs'] if appserver else ('cell/trace', 'home/.codex'):
            (out / path).mkdir(parents=True, exist_ok=True)
        for path in EVIDENCE['files'] if appserver else ():
            (out / path).touch()
        (out / 'plan.json').write_text(json.dumps(EVIDENCE['plan']))
        (out / 'run').mkdir()
        (out / 'run/stdout').write_text('')
        if owner:
            shutil.copytree(FIX / 'owner', out, dirs_exist_ok=True, ignore=shutil.ignore_patterns('usage-0257.json'))
        if seat or inference:
            shutil.copytree(FIX / 'appserver-thread', out / 'cell/trace', dirs_exist_ok=True)
        if inference:  # the seat then ran one inference, in the owner trace's row and payload shapes
            trace = next((out / 'cell/trace').glob(f'trace-*-{APP}'))
            rows = [json.loads(line) for line in (trace / 'trace.jsonl').read_text().splitlines()]
            (trace / 'payloads/3.json').write_text(json.dumps(dict(response_id='resp_app', upstream_request_id=None,
                                                                   token_usage=dict(input_tokens=900, cached_input_tokens=0,
                                                                                    cache_write_input_tokens=0, output_tokens=12,
                                                                                    reasoning_output_tokens=0, total_tokens=912))))
            rows += [dict(rows[-1], seq=4, thread_id=APP, codex_turn_id='turn-app', payload=dict(
                         type='inference_started', inference_call_id='call-app', thread_id=APP, codex_turn_id='turn-app',
                         model='gpt-6-astra', provider_name='OpenAI')),
                     dict(rows[-1], seq=5, thread_id=APP, codex_turn_id='turn-app', payload=dict(
                         type='inference_completed', inference_call_id='call-app', response_id='resp_app',
                         upstream_request_id=None, response_payload=dict(raw_payload_id='raw_payload:3', kind=dict(
                             type='inference_response'), path='payloads/3.json')))]
            (trace / 'trace.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in rows))
        return out

    def read(self, out):
        return cell.identity(out, EVIDENCE['plan']), usage.record(out)

    def test_evidence_holds_nothing_the_readers_count(self):
        """What the config read leaves: CODEX_HOME state and B's release in HOME, no trace, rollout or record."""
        files = EVIDENCE['files']
        self.assertEqual(EVIDENCE['status_line'], 'devlyn: codex 0.164.0 | release 4.3.30@53a2f9f2 (package) | '
                         'principles=configured:developer_instructions | skills=configured:session-plugin')
        self.assertFalse([p for p in files if p.startswith(('cell/trace/', 'home/.codex/sessions/', 'home/.claude/projects/'))])
        self.assertTrue(any(p.startswith('home/.codex/state_') for p in files))  # the app-server ran in this CODEX_HOME
        self.assertEqual({p.split('/.devlyn/')[0] for p in files if '/.devlyn/' in p}, {'home'})
        self.assertFalse([p for p in files if p.endswith(('.stderr', '.output.json', '.jsonl')) or '.invocation.' in p
                          or '/verify-judge.r' in p])

    def test_a_appserver_evidence_alone(self):
        ident, used = self.read(self.cell_out('a'))
        self.assertEqual((ident['owner'], ident['status'], ident['owner_launched_sessions'], ident['codex_seats']),
                         ('UNKNOWN', 'UNKNOWN', [], {}))
        self.assertEqual((used['completeness'], used['input_tokens'], used['output_tokens'], used['gaps']),
                         ('UNKNOWN', 0, 0, ['owner thread missing']))

    def test_b_usage_is_the_announced_owner_session_alone(self):
        """Allowed: the evidence plus the owner reads MATCH, and usage is COMPLETE and equal to the owner session's
        alone, which is also 0257's archived d008 usage."""
        alone = self.read(self.cell_out('owner', appserver=False, owner=True))
        ident, used = self.read(self.cell_out('b', owner=True))
        self.assertEqual((ident['owner'], ident['status'], ident['violations'], ident['gaps']), ('MATCH', 'MATCH', [], []))
        self.assertEqual(ident['owner_launched_sessions'], [])
        self.assertEqual(ident['codex_seats'], {OWNER: ['owner', 'gpt-6-astra', 'high']})
        self.assertEqual((used['completeness'], used['gaps']), ('COMPLETE', []))
        self.assertEqual(used, alone[1])
        archived = json.loads((FIX / 'owner/usage-0257.json').read_text())
        self.assertEqual({k: used[k] for k in ('input_tokens', 'output_tokens', 'codex')},
                         {k: archived[k] for k in ('input_tokens', 'output_tokens', 'codex')})

    def test_c_appserver_model_seat_reads_mismatch(self):
        """Violating: an app-server session holding a model seat, beside the same owner."""
        out = self.cell_out('c-seat', owner=True, seat=True)
        started = {json.loads(m.read_text())['rollout_id']: json.loads(m.read_text())['started_at_unix_ms']
                   for m in (out / 'cell/trace').glob('trace-*/manifest.json')}
        self.assertLess(started[APP], started[OWNER])  # it starts before the owner, as the config read does
        ident, used = self.read(out)
        self.assertEqual(ident['status'], 'MISMATCH', ident)
        self.assertTrue(any(APP in v for v in ident['violations']), ident['violations'])
        self.assertEqual(used['completeness'], 'PARTIAL')  # its usage is never silently absorbed either
        self.assertIn(f'owner-launched Codex session {APP} has no traced inference usage', used['gaps'])

    def test_a_session_the_owner_launched_stays_listed(self):
        """Allowed: the same session started after the owner is one the owner launched, listed as 0233 lists it."""
        out = self.cell_out('owner-launched', owner=True, seat=True)
        manifest = next((out / 'cell/trace').glob(f'trace-*-{APP}')) / 'manifest.json'
        owner = json.loads(next((out / 'cell/trace').glob(f'trace-*-{OWNER}/manifest.json')).read_text())
        manifest.write_text(json.dumps(dict(json.loads(manifest.read_text()),
                                            started_at_unix_ms=owner['started_at_unix_ms'] + 1)))
        ident, _ = self.read(out)
        self.assertEqual((ident['status'], ident['violations']), ('MATCH', []), ident)
        self.assertEqual([s['session'] for s in ident['owner_launched_sessions']], [APP])

    def test_c_appserver_inference_reads_mismatch(self):
        """Violating: that session also ran an inference; its tokens would otherwise join the owner's sum."""
        ident, used = self.read(self.cell_out('c-inference', owner=True, inference=True))
        self.assertEqual(ident['status'], 'MISMATCH', ident)
        self.assertTrue(any(APP in v for v in ident['violations']), ident['violations'])
        self.assertEqual((used['completeness'], used['input_tokens'], used['output_tokens']), ('PARTIAL', 314325 + 900, 4822 + 12))


if __name__ == '__main__':
    unittest.main()
