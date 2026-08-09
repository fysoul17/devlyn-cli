"""Ordering policy for encoder-feed entries."""


def rank_submissions(submissions: list[dict]) -> list[dict]:
    indexed = enumerate(submissions)
    ordered = sorted(indexed, key=lambda item: (-item[1]["priority"], item[0]))
    return [submission for _, submission in ordered]
