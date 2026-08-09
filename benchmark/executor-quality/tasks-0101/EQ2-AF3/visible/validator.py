"""Validation rules for one gradebook row."""

from errors import ERROR_PRIORITY


def row_issues(row: dict) -> list[str]:
    issues: list[str] = []
    student = row["student"]
    if not isinstance(student, str) or not student.strip():
        issues.append("student")
    score = row["score"]
    if not isinstance(score, int) or isinstance(score, bool) or not 0 <= score <= 100:
        issues.append("score")
    rank = row["rank"]
    if not isinstance(rank, int) or isinstance(rank, bool) or rank < 0:
        issues.append("rank")
    return issues


def choose_issue(row: dict) -> str | None:
    issues = row_issues(row)
    return issues[-1] if issues else None
