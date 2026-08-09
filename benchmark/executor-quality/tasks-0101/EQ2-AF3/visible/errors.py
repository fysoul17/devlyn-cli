"""Reporting order for rejected gradebook rows."""


ERROR_PRIORITY = {"student": 0, "score": 1, "rank": 2, "full": 3}


def rank_rejections(rejections: list[dict]) -> list[dict]:
    return list(rejections)
