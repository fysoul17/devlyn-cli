"""Priority ordering for approval requests."""


def order_requests(requests):
    return sorted(requests, key=lambda request: (-request.urgency, request.submitted_at))
