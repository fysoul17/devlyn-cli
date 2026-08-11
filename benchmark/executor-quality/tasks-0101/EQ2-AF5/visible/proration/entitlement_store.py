"""Durable subscription plan-entitlement windows."""

from copy import deepcopy

from .errors import EntitlementWriteError


class EntitlementStore:
    def __init__(
        self,
        windows: dict[str, list[dict[str, object]]],
        fail_after_replace: set[str] | None = None,
    ) -> None:
        self.windows = deepcopy(windows)
        self.write_calls = 0
        self.fail_after_replace = set(fail_after_replace or set())

    def snapshot(self) -> tuple[dict[str, list[dict[str, object]]], int]:
        return deepcopy(self.windows), self.write_calls

    def restore(self, snapshot: tuple[dict[str, list[dict[str, object]]], int]) -> None:
        self.windows, self.write_calls = deepcopy(snapshot[0]), snapshot[1]

    def current_plan(self, subscription_id: str) -> str:
        return str(self.windows[subscription_id][-1]["plan"])

    def replace_tail(self, subscription_id: str, new_plan: str, effective_day: int) -> None:
        timeline = self.windows[subscription_id]
        current = timeline[-1]
        cycle_end = int(current["end_day"])
        current["end_day"] = effective_day
        timeline.append({"plan": new_plan, "start_day": effective_day, "end_day": cycle_end})
        self.write_calls += 1
        if subscription_id in self.fail_after_replace:
            raise EntitlementWriteError(subscription_id)
