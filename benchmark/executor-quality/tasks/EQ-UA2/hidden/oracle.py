#!/usr/bin/env python3
"""Check authorization-before-lookup behavior in an isolated directory."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


INVARIANT = (
    "Artifact retrieval authorizes the caller before catalog lookup, so a caller lacking read "
    "access receives the same access_denied response whether the requested key exists or not."
)
DENIED = {"error": "access_denied"}


def check_case(workdir: Path, key: str) -> bool:
    with tempfile.TemporaryDirectory(prefix="eq-ua2-case-") as temporary:
        root = Path(temporary)
        catalog_path = root / "catalog.json"
        grants_path = root / "grants.json"
        catalog_path.write_text(
            json.dumps({"release.tar": {"bytes": 3, "digest": "abc"}}),
            encoding="utf-8",
        )
        grants_path.write_text(json.dumps({"reader": ["read"]}), encoding="utf-8")

        completed = subprocess.run(
            [
                sys.executable,
                str(workdir / "cli.py"),
                "retrieve",
                str(catalog_path),
                str(grants_path),
                "blocked",
                key,
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
        return completed.returncode == 1 and payload == DENIED


def main() -> None:
    workdir = Path(sys.argv[1]).resolve()
    known = check_case(workdir, "release.tar")
    unknown = check_case(workdir, "unlisted.tar")
    print(
        json.dumps(
            {
                "manifestations": [
                    {
                        "id": "sealed-known-ref",
                        "invariant": INVARIANT,
                        "passed": known,
                    },
                    {
                        "id": "sealed-unknown-ref",
                        "invariant": INVARIANT,
                        "passed": unknown,
                    },
                ]
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
