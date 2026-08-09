"""Route expense requests to eligible reviewers."""

from models import RoutedExpense
from priority import order_requests
from reviewers import choose_reviewer
from role_gate import is_authorized


def route_expenses(requests, grants, reviewers):
    loads = {reviewer.name: 0 for reviewer in reviewers}
    routed = []
    for request in requests:
        reviewer = choose_reviewer(reviewers, request, loads)
        loads[reviewer.name] += 1
        routed.append(
            RoutedExpense(request.request_id, reviewer.name, loads[reviewer.name])
        )
    return routed
