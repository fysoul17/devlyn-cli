from __future__ import annotations

import unittest

from replicas import CorruptReplica, RecordMissing, ReplicaUnavailable, read_replica


class ReplicaTests(unittest.TestCase):
    def test_returns_a_valid_record(self) -> None:
        record = {"value": "payload", "version": 3}

        self.assertIs(read_replica(lambda: record), record)

    def test_reports_a_missing_record(self) -> None:
        with self.assertRaises(RecordMissing):
            read_replica(lambda: None)

    def test_reports_a_corrupt_record(self) -> None:
        with self.assertRaises(CorruptReplica):
            read_replica(lambda: {"version": 3})

    def test_preserves_an_unavailable_failure(self) -> None:
        def unavailable() -> object:
            raise ReplicaUnavailable("offline")

        with self.assertRaises(ReplicaUnavailable):
            read_replica(unavailable)


if __name__ == "__main__":
    unittest.main()
