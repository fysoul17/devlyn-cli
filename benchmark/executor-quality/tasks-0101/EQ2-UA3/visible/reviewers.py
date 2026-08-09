"""Reviewer eligibility and load-aware selection."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Reviewer:
    name: str
    cost_centers: tuple[str, ...]


def choose_reviewer(reviewers, request, loads):
    eligible = [
        (position, reviewer)
        for position, reviewer in enumerate(reviewers)
        if request.cost_center in reviewer.cost_centers
    ]
    if not eligible:
        raise ValueError(f"no reviewer for cost center: {request.cost_center}")
    _, reviewer = min(eligible, key=lambda item: (loads[item[1].name], item[0]))
    return reviewer
