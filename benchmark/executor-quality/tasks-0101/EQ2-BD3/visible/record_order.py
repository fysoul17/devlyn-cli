"""Deployment processing order for zone changes."""


def order_changes(changes: list[dict]) -> list[tuple[int, dict]]:
    def key(item: tuple[int, dict]) -> tuple[int, int]:
        source, change = item
        priority = change["priority"]
        sortable = priority if isinstance(priority, int) and not isinstance(priority, bool) else 0
        return (-sortable, source)

    return sorted(enumerate(changes), key=key)
