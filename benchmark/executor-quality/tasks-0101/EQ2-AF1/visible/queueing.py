"""Queue policy for parking requests."""


def rank_requests(requests: list[dict]) -> list[tuple[int, dict]]:
    return list(enumerate(requests))
