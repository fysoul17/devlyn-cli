#!/usr/bin/env python3
"""Offline checks for the checkout behavior that depends on rate normalization."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path


INVARIANT = (
    "Checkout options are ordered by earliest delivery estimate with service-code "
    "tie-breaking, independent of carrier response order."
)


def load_checkout(workdir: Path):
    sys.path.insert(0, str(workdir))
    try:
        sys.modules.pop("checkout", None)
        sys.modules.pop("rates", None)
        return importlib.import_module("checkout")
    finally:
        sys.path.pop(0)


def run_case(module, raw_quotes: list[dict], expected_services: list[str]) -> bool:
    try:
        result = module.build_checkout(raw_quotes)
    except Exception:
        return False
    services = [option.get("service_code") for option in result.get("options", [])]
    recommended = result.get("recommended")
    return services == expected_services and recommended == expected_services[0]


def main() -> None:
    workdir = Path(sys.argv[1])
    checkout = load_checkout(workdir)
    eta_mix = run_case(
        checkout,
        [
            {"service_code": "ground", "eta_days": 5, "price_cents": 700},
            {"service_code": "express", "eta_days": 2, "price_cents": 1500},
        ],
        ["express", "ground"],
    )
    eta_tie = run_case(
        checkout,
        [
            {"service_code": "zeta", "eta_days": 3, "price_cents": 900},
            {"service_code": "alpha", "eta_days": 3, "price_cents": 1100},
        ],
        ["alpha", "zeta"],
    )
    print(
        json.dumps(
            {
                "manifestations": [
                    {"id": "flow_eta_mix", "invariant": INVARIANT, "passed": eta_mix},
                    {"id": "flow_eta_tie", "invariant": INVARIANT, "passed": eta_tie},
                ]
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
