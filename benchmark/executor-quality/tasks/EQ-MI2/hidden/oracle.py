#!/usr/bin/env python3
"""Check the hidden behavioral manifestations for EQ-MI2."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType


INVARIANT = (
    "A rejected playlist replacement leaves the playlist exactly as it was before "
    "the call, whether rejection comes from an unknown track or from exceeding the duration limit."
)


def load_playlist(workdir: Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, workdir / "playlist.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load playlist fixture")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def catalog_reject_preserves(workdir: Path) -> bool:
    playlist = load_playlist(workdir, "fixture_catalog")
    playlist.create_playlist("mix", ["old-a", "old-b"])
    try:
        accepted = playlist.replace_tracks(
            "mix", ["new-a", "lost"], {"new-a": 30}, 100
        )
    except (AttributeError, KeyError, TypeError):
        return False
    return accepted is False and playlist.get_tracks("mix") == ["old-a", "old-b"]


def limit_reject_preserves(workdir: Path) -> bool:
    playlist = load_playlist(workdir, "fixture_limit")
    playlist.create_playlist("mix", ["old-a", "old-b"])
    try:
        accepted = playlist.replace_tracks(
            "mix", ["new-a", "new-b"], {"new-a": 60, "new-b": 60}, 100
        )
    except (AttributeError, KeyError, TypeError):
        return False
    return accepted is False and playlist.get_tracks("mix") == ["old-a", "old-b"]


def main() -> None:
    workdir = Path(sys.argv[1]).resolve()
    print(
        json.dumps(
            {
                "manifestations": [
                    {
                        "id": "catalog-reject-preserves",
                        "invariant": INVARIANT,
                        "passed": catalog_reject_preserves(workdir),
                    },
                    {
                        "id": "limit-reject-preserves",
                        "invariant": INVARIANT,
                        "passed": limit_reject_preserves(workdir),
                    },
                ]
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
