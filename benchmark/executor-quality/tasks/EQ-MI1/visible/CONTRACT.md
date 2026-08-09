# Event bus contract

Dispatch order is a standing invariant: handlers run in priority-descending order, and handlers registered earlier break ties within the same priority, no matter how the set of invoked handlers is chosen.

Features that select a subset of handlers must preserve this ordering contract.
