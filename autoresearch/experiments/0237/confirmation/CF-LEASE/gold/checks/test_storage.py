import tempfile
import unittest
from pathlib import Path
from parcel import Store, enqueue, get_job

class StorageSmoke(unittest.TestCase):
    def test_reopen_and_payload_snapshot(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'outbox.sqlite'
            payload = {'parts': ['one']}
            with Store(path) as store:
                enqueue(store, 'p-2', payload, 0)
            payload['parts'].append('two')
            with Store(path) as reopened:
                first = get_job(reopened, 'p-2')
                first.payload['parts'].append('three')
                self.assertEqual(get_job(reopened, 'p-2').payload, {'parts': ['one']})
