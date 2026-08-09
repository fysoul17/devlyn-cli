"""Processing order for gradebook rows."""


def order_rows(rows: list[dict]) -> list[tuple[int, dict]]:
    return list(enumerate(rows))
