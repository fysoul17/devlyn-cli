#!/usr/bin/env python3
"""Offline checks for campaign behavior after rejected palette changes."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path


INVARIANT = (
    "Rejected palette replacement preserves the dependent campaign preview and "
    "theme version exactly as they were before the request."
)


def load_components(workdir: Path):
    sys.path.insert(0, str(workdir))
    try:
        sys.modules.pop("campaign", None)
        sys.modules.pop("theme", None)
        theme_module = importlib.import_module("theme")
        campaign_module = importlib.import_module("campaign")
        return theme_module, campaign_module
    finally:
        sys.path.pop(0)


def run_case(theme_module, campaign_module, updates: dict[str, str]) -> bool:
    theme = theme_module.Theme(
        {"accent": "#336699", "background": "#ffffff"}
    )
    before_tokens = dict(theme.tokens)
    before_version = theme.version
    before_preview = campaign_module.render_banner(theme)
    try:
        result = campaign_module.preview_update(theme, updates)
    except Exception:
        return False
    return (
        result.get("status") == "rejected"
        and result.get("version") == before_version
        and result.get("preview") == before_preview
        and theme.tokens == before_tokens
        and theme.version == before_version
    )


def main() -> None:
    workdir = Path(sys.argv[1])
    theme_module, campaign_module = load_components(workdir)
    invalid_first = run_case(
        theme_module,
        campaign_module,
        {"border": "#101010", "accent": "#112233"},
    )
    invalid_late = run_case(
        theme_module,
        campaign_module,
        {"accent": "#112233", "background": "blue"},
    )
    print(
        json.dumps(
            {
                "manifestations": [
                    {"id": "preview_bad_first", "invariant": INVARIANT, "passed": invalid_first},
                    {"id": "preview_bad_late", "invariant": INVARIANT, "passed": invalid_late},
                ]
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
