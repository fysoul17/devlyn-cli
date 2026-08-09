from __future__ import annotations

import unittest

import event_bus


class EventBusTests(unittest.TestCase):
    def setUp(self) -> None:
        event_bus.clear_handlers()

    def test_dispatches_by_descending_priority(self) -> None:
        calls: list[str] = []
        event_bus.register("low", 10, lambda event: calls.append(f"low:{event}"))
        event_bus.register("high", 100, lambda event: calls.append(f"high:{event}"))

        event_bus.dispatch("ready")

        self.assertEqual(calls, ["high:ready", "low:ready"])

    def test_registration_order_breaks_priority_ties(self) -> None:
        calls: list[str] = []
        event_bus.register("first", 50, lambda event: calls.append("first"))
        event_bus.register("second", 50, lambda event: calls.append("second"))

        event_bus.dispatch("ignored")

        self.assertEqual(calls, ["first", "second"])


if __name__ == "__main__":
    unittest.main()
