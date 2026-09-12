"""Temporary native observation of the unchanged 0150 failing tests."""
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys
import unittest
from unittest.mock import patch

driver = Path(__file__).with_name('test-windows-portability.py')
scope = runpy.run_path(str(driver))
case = scope['NativeOwnershipTests']
gated, pids = case.gated_job, case.job_pids
observations = []


def identify(self):
    result = gated(self)
    job, _, work, _, _ = result
    self.identities = {job.child.pid: 'bootstrap', job.target_pid: 'B',
                       int((work / 'A.pid').read_text(encoding='utf-8')): 'A'}
    return result


def observe(self, job):
    result = pids(self, job)
    record = {'test': self.id(), 'pids': result, 'identities': self.identities,
              'wait_results': {str(pid): self.kernel.WaitForSingleObject(self.retain(pid), 0)
                               for pid in result}}
    observations.append(record)
    print('MEMBERSHIP ' + json.dumps(record), flush=True)
    return result


assert sys.platform == 'win32', 'Requires native Windows'
names = ('test_child_after_initial_observation_is_captured_and_pid_buffer_grows',
         'test_zero_barrier_rejects_freed_slot_and_current_count_control_admits')
results = []
if '--negative' in sys.argv:
    for control in ('bootstrap-retained', 'unexpected-member'):
        def inject(self, job):
            result = observe(self, job)
            extra = next(pid for pid, role in self.identities.items() if role == 'bootstrap') if control == 'bootstrap-retained' else os.getpid()
            return result if extra in result else [*result, extra]

        with patch.object(case, 'gated_job', identify), patch.object(case, 'job_pids', inject):
            result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([case(names[0])]))
        expected = 'fixture did not become ready' if control == 'bootstrap-retained' else 'Items in the first set but not the second'
        accepted = len(result.failures) == 1 and expected in result.failures[0][1]
        results.append({'control': control, 'expected_rejection': accepted,
                        'failures': [trace for _, trace in result.failures],
                        'cleanup_errors': [trace for _, trace in result.errors]})
else:
    suite = unittest.TestSuite(case(name) for _ in range(20) for name in names)
    with patch.object(case, 'gated_job', identify), patch.object(case, 'job_pids', observe):
        result = unittest.TextTestRunner(verbosity=2).run(suite)
Path('0150-observations.json').write_text(json.dumps({
    'driver_sha256': hashlib.sha256(driver.read_bytes()).hexdigest(),
    'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
    'observations': observations, 'controls': results}, indent=2) + '\n', encoding='utf-8')
raise SystemExit(not all(r['expected_rejection'] for r in results) if results else not result.wasSuccessful())
