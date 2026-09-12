"""Temporary observation of the unchanged gone-PID fixture boundary."""
import hashlib
import json
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
        if args[0][-2:] == ['-c', 'pass']:
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
            record = {'pid': pid, 'handle': handle, 'open_error': error if not handle else None}
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
suite = unittest.TestSuite([case('test_stale_list_gone_and_different_job_identity')])
with patch.object(case, 'setUp', observe_setup):
    result = unittest.TextTestRunner(verbosity=2).run(suite)
Path('0150-observations.json').write_text(json.dumps({
    'driver_sha256': hashlib.sha256(driver.read_bytes()).hexdigest(),
    'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
    'observations': observations}, indent=2) + '\n', encoding='utf-8')
raise SystemExit(not result.wasSuccessful())
