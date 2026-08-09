"""Data carried between the approval router and its collaborators."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ExpenseRequest:
    request_id: str
    submitter: str
    cost_center: str
    amount_cents: int
    urgency: int
    submitted_at: int


@dataclass(frozen=True)
class RoutedExpense:
    request_id: str
    reviewer: str
    reviewer_slot: int
