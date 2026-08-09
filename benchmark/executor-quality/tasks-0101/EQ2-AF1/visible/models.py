"""Input normalization for parking requests."""


def normalize_request(request: dict) -> dict:
    return {
        "id": str(request["id"]),
        "priority": int(request["priority"]),
        "slots": list(request["slots"]),
    }
