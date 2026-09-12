"""Temporary observation of the unchanged gone-PID fixture boundary."""
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import unittest
from unittest.mock import patch

driver = Path(__file__).with_name('test-windows-portability.py')
case = runpy.run_path(str(driver))['NativeOwnershipTests']
setup = case.setUp
observations = []


def observe_setup(self):
    setup(self)
    native_open = self.kernel.OpenProcess
    native_close = self.kernel.CloseHandle
    probes = set()
    held = []
    initialize = subprocess.Popen.__init__

    def launch(child, *args, **kwargs):
        initialize(child, *args, **kwargs)
        if control == 'held' and args[0][-2:] == ['-c', 'pass']:
            handle = native_open(0x101001, False, child.pid)
            self.assertTrue(handle)
            held.append(handle)

    def observed_close(handle):
        result = native_close(handle)
        if result:
            probes.discard(handle)
        return result

    def observed_open(access, inherit, pid):
        handle = native_open(access, inherit, pid)
        error = self.ctypes.get_last_error()
        if access == 0x101000:
            if control in ('live', 'non87'):
                if handle:
                    self.assertTrue(native_close(handle))
                handle = native_open(access, inherit, os.getpid()) if control == 'live' else None
                error = 5 if control == 'non87' else self.ctypes.get_last_error()
            record = {'control': control, 'pid': pid, 'handle': handle, 'open_error': error if not handle else None,
                      'injected_pid': os.getpid() if control == 'live' else None}
            if handle:
                record['wait_result'] = self.kernel.WaitForSingleObject(handle, 0)
                probes.add(handle)
                while held:
                    self.assertTrue(native_close(held.pop()))
            observations.append(record)
            print('GONE-PROBE ' + json.dumps(record), flush=True)
            self.ctypes.set_last_error(error)
        return handle

    for observer in (patch.object(self.kernel, 'OpenProcess', observed_open),
                     patch.object(self.kernel, 'CloseHandle', observed_close),
                     patch.object(subprocess.Popen, '__init__', launch)):
        observer.start(); self.addCleanup(observer.stop)

    def cleanup():
        for handle in [*probes, *held]:
            self.assertTrue(native_close(handle))
    self.addCleanup(cleanup)


assert sys.platform == 'win32'
results = []
for control, repetitions in (('live', 1),):
    suite = unittest.TestSuite(case('test_stale_list_gone_and_different_job_identity') for _ in range(repetitions))
    with patch.object(case, 'setUp', observe_setup):
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    expected = 'gone-PID fixture refers to a live process' if control == 'live' else '5 != 87'
    accepted = result.wasSuccessful() if control in ('natural', 'held') else len(result.failures) == 1 and expected in result.failures[0][1]
    results.append({'control': control, 'tests_run': result.testsRun, 'expected_outcome': accepted,
                    'failures': [trace for _, trace in result.failures], 'errors': [trace for _, trace in result.errors]})
Path('0150-observations.json').write_text(json.dumps({
    'driver_sha256': hashlib.sha256(driver.read_bytes()).hexdigest(),
    'results': results, 'observations': observations}, indent=2) + '\n', encoding='utf-8')
raise SystemExit(not all(r['expected_outcome'] for r in results))
