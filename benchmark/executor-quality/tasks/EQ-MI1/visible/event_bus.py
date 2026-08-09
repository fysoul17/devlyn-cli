"""A small in-process event dispatcher."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


Handler = Callable[[Any], None]
_handlers: list[tuple[str, int, int, Handler]] = []


def clear_handlers() -> None:
    """Remove all registered handlers."""
    _handlers.clear()


def register(name: str, priority: int, handler: Handler) -> None:
    """Register a handler, retaining registration order for ties."""
    _handlers.append((name, priority, len(_handlers), handler))


def dispatch(event: Any) -> None:
    """Invoke every handler in the documented order."""
    ordered = sorted(_handlers, key=lambda item: (-item[1], item[2]))
    for _, _, _, handler in ordered:
        handler(event)
