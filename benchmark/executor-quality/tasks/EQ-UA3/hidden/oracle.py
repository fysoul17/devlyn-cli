#!/usr/bin/env python3
"""Check validation priority against competing destination failures."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


INVARIANT = (
    "Publication planning validates the draft before destination checks, so invalid_draft wins "
    "when the channel is missing or the slug is already occupied."
)
INVALID = {"error": "invalid_draft"}


def check_case(
    workdir: Path, draft: dict[str, object], destinations: dict[str, object], channel: str
) -> bool:
    with tempfile.TemporaryDirectory(prefix="eq-ua3-case-") as temporary:
        root = Path(temporary)
        draft_path = root / "draft.json"
        destinations_path = root / "destinations.json"
        draft_path.write_text(json.dumps(draft), encoding="utf-8")
        destinations_path.write_text(json.dumps(destinations), encoding="utf-8")

        completed = subprocess.run(
            [
                sys.executable,
                str(workdir / "cli.py"),
                "plan",
                str(draft_path),
                str(destinations_path),
                channel,
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError:
            return False
        return completed.returncode == 1 and payload == INVALID


def main() -> None:
    workdir = Path(sys.argv[1]).resolve()
    missing = check_case(
        workdir,
        {"slug": "weekly-note"},
        {"news": []},
        "alerts",
    )
    occupied = check_case(
        workdir,
        {"title": "", "slug": "weekly-note"},
        {"news": ["weekly-note"]},
        "news",
    )
    print(
        json.dumps(
            {
                "manifestations": [
                    {
                        "id": "malformed-with-absent-route",
                        "invariant": INVARIANT,
                        "passed": missing,
                    },
                    {
                        "id": "malformed-with-reserved-name",
                        "invariant": INVARIANT,
                        "passed": occupied,
                    },
                ]
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
