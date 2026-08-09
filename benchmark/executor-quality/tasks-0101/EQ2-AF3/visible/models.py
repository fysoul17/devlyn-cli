"""Input normalization for gradebook rows."""


def normalize_row(row: dict) -> dict:
    return {
        "student": row.get("student"),
        "score": row.get("score"),
        "rank": row.get("rank"),
    }
