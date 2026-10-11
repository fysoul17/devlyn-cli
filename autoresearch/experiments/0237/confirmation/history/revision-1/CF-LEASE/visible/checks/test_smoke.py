import unittest
from parcel import Store, enqueue, claim, complete, get_job, process_one, PayloadConflict

class Smoke(unittest.TestCase):
    def setUp(self):
        self.store = Store(':memory:')
        self.addCleanup(self.store.close)

    def test_normal_delivery(self):
        self.assertTrue(enqueue(self.store, 'p-1', {'to': 'archive'}, 10))
        self.assertIsNone(claim(self.store, 'worker', 9, 20))
        receipt = claim(self.store, 'worker', 10, 20)
        self.assertEqual(receipt.payload, {'to': 'archive'})
        self.assertEqual(receipt.attempt, 1)
        self.assertTrue(complete(self.store, receipt, 11))
        self.assertEqual(get_job(self.store, 'p-1').state, 'done')
        self.assertIsNone(claim(self.store, 'worker', 12, 20))

    def test_conflicting_payload_is_visible(self):
        enqueue(self.store, 'p-1', [1], 0)
        with self.assertRaises(PayloadConflict):
            enqueue(self.store, 'p-1', [2], 0)
        self.assertEqual(get_job(self.store, 'p-1').payload, [1])

    def test_worker_and_empty_queue(self):
        enqueue(self.store, 'p-1', {'to': 'archive'}, 0)
        handled = []
        self.assertEqual(process_one(self.store, 'worker', handled.append, lambda: 1).state, 'completed')
        self.assertEqual(handled, [{'to': 'archive'}])
        self.assertEqual(process_one(self.store, 'worker', handled.append, lambda: 2).state, 'idle')
