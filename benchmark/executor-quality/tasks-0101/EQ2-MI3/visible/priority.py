"""Stable priority ordering for room requests."""


def order_requests(requests):
    return sorted(
        requests,
        key=lambda request: (-request.priority, request.submitted_at),
    )
