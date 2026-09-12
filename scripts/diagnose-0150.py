"""Temporary observation of the unchanged gone-PID fixture boundary."""
import hashlib
import json
from pathlib import Path
import runpy
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

    def observed_open(access, inherit, pid):
        handle = native_open(access, inherit, pid)
        error = self.ctypes.get_last_error()
        if access == 0x101000:
            record = {'pid': pid, 'handle': handle, 'open_error': error if not handle else None}
            if handle:
                record['wait_result'] = self.kernel.WaitForSingleObject(handle, 0)
                self.assertTrue(self.kernel.CloseHandle(handle))
            observations.append(record)
            print('GONE-PROBE ' + json.dumps(record), flush=True)
            self.ctypes.set_last_error(error)
        return handle

    observer = patch.object(self.kernel, 'OpenProcess', observed_open)
    observer.start(); self.addCleanup(observer.stop)


assert sys.platform == 'win32'
suite = unittest.TestSuite(case('test_stale_list_gone_and_different_job_identity') for _ in range(20))
with patch.object(case, 'setUp', observe_setup):
    result = unittest.TextTestRunner(verbosity=2).run(suite)
Path('0150-observations.json').write_text(json.dumps({
    'driver_sha256': hashlib.sha256(driver.read_bytes()).hexdigest(),
    'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
    'observations': observations}, indent=2) + '\n', encoding='utf-8')
raise SystemExit(not result.wasSuccessful())
