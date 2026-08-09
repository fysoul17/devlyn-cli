"""Authorization policy for expense submitters."""


def is_authorized(request, grants):
    submitter_grants = grants.get(request.submitter, {})
    ceiling = submitter_grants.get(request.cost_center)
    return ceiling is not None and request.amount_cents <= ceiling
