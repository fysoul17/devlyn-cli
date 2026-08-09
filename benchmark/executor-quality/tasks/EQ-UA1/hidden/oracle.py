#!/usr/bin/env python3
"""Exercise atomic batch behavior against an isolated fixture copy."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


INVARIANT = (
    "Applying a batch of operations is all-or-nothing: if any operation in the batch would fail, "
    "the accounts file is left byte-identical to its pre-batch state and no operations are applied."
)


def check_case(workdir: Path, operations: list[dict[str, object]], failed_index: int) -> bool:
    with tempfile.TemporaryDirectory(prefix="eq-ua1-case-") as temporary:
        root = Path(temporary)
        accounts_path = root / "accounts.json"
        operations_path = root / "operations.json"
        before = '{\n  "savings": 20,\n  "checking": 100\n}\n'.encode()
        accounts_path.write_bytes(before)
        operations_path.write_text(json.dumps(operations), encoding="utf-8")

        completed = subprocess.run(
            [
                sys.executable,
                str(workdir / "cli.py"),
                "batch",
                str(accounts_path),
                str(operations_path),
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
        rejected = payload.get("rejected") if isinstance(payload, dict) else None
        return (
            completed.returncode == 1
            and accounts_path.read_bytes() == before
            and set(payload) == {"applied", "rejected"}
            and payload.get("applied") is None
            and isinstance(rejected, dict)
            and set(rejected) == {"index", "reason"}
            and rejected.get("index") == failed_index
            and isinstance(rejected.get("reason"), str)
            and bool(rejected.get("reason"))
        )


def main() -> None:
    workdir = Path(sys.argv[1]).resolve()
    insufficient = check_case(
        workdir,
        [
            {"account": "checking", "delta": 10},
            {"account": "savings", "delta": -25},
            {"account": "checking", "delta": 5},
        ],
        1,
    )
    unknown = check_case(
        workdir,
        [
            {"account": "checking", "delta": 10},
            {"account": "savings", "delta": 5},
            {"account": "ghost", "delta": 1},
        ],
        2,
    )
    print(
        json.dumps(
            {
                "manifestations": [
                    {
                        "id": "mid-batch-insufficient-funds",
                        "invariant": INVARIANT,
                        "passed": insufficient,
                    },
                    {
                        "id": "last-op-unknown-account",
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
