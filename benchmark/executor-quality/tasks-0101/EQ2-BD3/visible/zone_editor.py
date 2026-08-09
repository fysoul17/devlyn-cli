"""Public batch interface for DNS zone edits."""

from syntax_ranking import build_ranked_plan


def edit_zone(changes: list[dict]) -> dict:
    return build_ranked_plan(changes)
