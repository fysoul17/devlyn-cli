from __future__ import annotations

import unittest

from conflict_reporter import ConflictReporter
from models import Conflict


class ConflictReporterTests(unittest.TestCase):
    def test_published_report_is_found_in_same_snapshot(self) -> None:
        reporter = ConflictReporter()
        report = reporter.publish("r1", 3, Conflict(0, "room", "b1"))

        self.assertEqual(reporter.find("r1", 3), report)
        self.assertEqual(reporter.reports("r1"), (report,))
        self.assertEqual(reporter.notification_count, 1)


if __name__ == "__main__":
    unittest.main()
