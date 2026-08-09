"""Input normalization for transcode submissions."""


def normalize_submission(submission: dict) -> dict:
    return {
        "id": str(submission["id"]),
        "asset": str(submission["asset"]),
        "priority": int(submission["priority"]),
    }
