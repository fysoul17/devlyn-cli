"""Temporary fixed-count observation of real Windows enrollment failure."""
import json
from pathlib import Path
import runpy
import subprocess
import sys
import unittest
from unittest.mock import patch

case = runpy.run_path(str(Path(__file__).with_name('test-windows-portability.py')))['NativeOwnershipTests']
observations = []

class Observe(case):
    def test_enrollment(self):
        kernel = self.scope['_kernel']
        actual = kernel.DuplicateHandle
        original_kill = subprocess.Popen.kill
        original_wait = subprocess.Popen.wait
        row = {'sample': len(observations)}
        observations.append(row)
        def state(child):
            return {'returncode': child.returncode,
                    'wait': self.kernel.WaitForSingleObject(self.retain(child.pid), 0)}
        def kill(child):
            row['before_kill'] = state(child)
            result = original_kill(child)
            row['after_kill'] = state(child)
            return result
        def wait(child, *args, **kwargs):
            result = original_wait(child, *args, **kwargs)
            row['after_wait'] = state(child)
            return result
        with patch.object(kernel, 'DuplicateHandle', lambda source, job, target, out, access, inherit, options:
                          actual(source, job, target, out, 4, inherit, 0)), \
             patch.object(subprocess.Popen, 'kill', kill), patch.object(subprocess.Popen, 'wait', wait):
            with self.assertRaises(OSError) as error:
                self.platform['run_process'](self.command, subprocess.DEVNULL, 1)
        row['error'] = str(error.exception)
        row['final_waits'] = [self.kernel.WaitForSingleObject(h, 0) for h in self.handles.values()]
        self.assertFalse(self.leader.exists()); self.assertFalse(self.ticks.exists())
        self.assert_all_ceased()

assert sys.platform == 'win32'
controlled = []
for label, source_root in [('baseline', Path('baseline').resolve()), ('candidate', None)]:
    case.setUp.__globals__['PACKAGE_ROOT'] = source_root
    check = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([
        case('test_cached_exit_code_still_requires_native_cessation')]))
    controlled.append({'source': label, 'successful': check.wasSuccessful(),
                       'failures': [trace for _, trace in check.failures],
                       'errors': [trace for _, trace in check.errors]})
case.setUp.__globals__['PACKAGE_ROOT'] = None
suite = unittest.TestSuite(Observe('test_enrollment') for _ in range(200))
result = unittest.TextTestRunner(verbosity=1).run(suite)
Path('0160-observations.json').write_text(json.dumps({'controlled': controlled, 'samples': observations,
    'failures': [trace for _, trace in result.failures], 'errors': [trace for _, trace in result.errors],
    'tests_run': result.testsRun}, indent=2), encoding='utf-8')
print(json.dumps({'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors)}))
