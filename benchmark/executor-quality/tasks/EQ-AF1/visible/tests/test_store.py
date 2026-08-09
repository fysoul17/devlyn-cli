from __future__ import annotations

import unittest

from store import JobStore


class JobStoreTests(unittest.TestCase):
    def test_records_a_new_job(self) -> None:
        store = JobStore()

        result = store.submit_job("job-1", {"kind": "email"})

        self.assertEqual(result, {"sequence": 1, "payload": {"kind": "email"}})
        self.assertEqual(store.records, {"job-1": result})
        self.assertEqual(store.total_processed, 1)

    def test_reuses_the_first_result_for_a_known_job(self) -> None:
        store = JobStore()
        first = store.submit_job("job-1", {"kind": "email"})

        repeated = store.submit_job("job-1", {"kind": "sms"})

        self.assertIs(repeated, first)
        self.assertEqual(store.records, {"job-1": first})
        self.assertEqual(store.total_processed, 1)


if __name__ == "__main__":
    unittest.main()
