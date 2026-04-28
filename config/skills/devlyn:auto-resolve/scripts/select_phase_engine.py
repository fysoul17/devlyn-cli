#!/usr/bin/env python3
"""Per-phase engine selector — code-enforced routing (iter-0020).

Reads `.devlyn/pipeline.state.json` and applies the routing rules from
`references/engine-routing.md` plus per-fixture-class overrides
introduced in iter-0020. Writes `state.route.build_engine_override`
when an override fires. Prints the selected engine name on stdout
(`claude` / `codex` / `bash` / `native`) so the orchestrator can
deterministically dispatch BUILD without relying on prompt-body
interpretation.

Why this script exists (Codex R1 iter-0020 verdict): hard acceptance #3
requires "deterministic short-circuit/abort enforced in code (not
prompt-only)." Encoding the override in SKILL.md prose alone repeats
the iter-0008 / iter-0014 lesson that prompt-body contracts get
silently bypassed by the orchestrator. A small script invoked from
PHASE 1 closes that gap.

Usage:
    python3 select_phase_engine.py --phase build [--engine auto]

Args:
    --phase: one of {build, eval, fix_loop, critic, docs}.
    --engine: forwarded user flag value (auto|claude|codex). Defaults
              to "auto" (matches SKILL.md PHASE 0 step 1 default).

Outputs:
    stdout: the resolved engine name (one of claude/codex/native/bash)
    stderr: a `[select-engine] ...` log line summarizing the decision

Exit codes:
    0: engine resolved successfully
    2: invocation error (missing state, unknown phase, etc.)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Default routing per references/engine-routing.md (Pipeline Phase Routing
# table for auto-resolve). Mirrored here so the orchestrator does not have
# to interpret prose at runtime. If the table changes, sync this map.
DEFAULT_ROUTING: dict[str, dict[str, str]] = {
    "build":    {"auto": "codex",  "codex": "codex", "claude": "claude"},
    "eval":     {"auto": "claude", "codex": "claude", "claude": "claude"},
    "fix_loop": {"auto": "codex",  "codex": "codex", "claude": "claude"},
    "critic":   {"auto": "claude", "codex": "claude", "claude": "claude"},
    "docs":     {"auto": "claude", "codex": "codex", "claude": "claude"},
}

# Per-fixture-class overrides (iter-0020). Maps {phase: {fixture_class:
# engine}}. Override fires only when state.source.fixture_class matches
# AND user --engine == "auto" (explicit user choice always wins).
FIXTURE_CLASS_OVERRIDES: dict[str, dict[str, str]] = {
    "build": {
        # iter-0020: F9 evidence — Codex BUILD on novice flow regresses
        # L2-L1=-21 vs Claude BUILD with material wall premium. Silent-
        # catch DQ recurs across runs. Treat as not-prompt-fixable until
        # disproven. Layer-cost-justified narrow defense.
        "e2e": "claude",
    },
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def select_engine(phase: str, engine_flag: str, fixture_class: str | None
                  ) -> tuple[str, dict | None]:
    """Return (engine, override_record) for the given phase.

    override_record is non-None only when a per-fixture-class override
    fired; the orchestrator should then write it to
    state.route.build_engine_override (or analogous field).
    """
    table = DEFAULT_ROUTING.get(phase)
    if table is None:
        raise SystemExit(f"[select-engine] error: unknown phase '{phase}'")
    base = table.get(engine_flag)
    if base is None:
        raise SystemExit(f"[select-engine] error: unknown engine flag '{engine_flag}'")

    # Override only when user did not explicitly pin the engine.
    if engine_flag != "auto":
        return (base, None)
    overrides = FIXTURE_CLASS_OVERRIDES.get(phase) or {}
    override_engine = overrides.get(fixture_class) if fixture_class else None
    if override_engine and override_engine != base:
        return (
            override_engine,
            {
                "at": now_iso(),
                "phase": phase,
                "from": base,
                "to": override_engine,
                "reason": f"fixture_class={fixture_class}",
                "source": "iter-0020",
            },
        )
    return (base, None)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--phase", required=True,
                    choices=list(DEFAULT_ROUTING.keys()))
    ap.add_argument("--engine", default="auto",
                    choices=["auto", "claude", "codex"])
    args = ap.parse_args()

    work = Path(os.environ.get("BENCH_WORKDIR") or os.getcwd())
    state_path = work / ".devlyn" / "pipeline.state.json"
    # iter-0020 Codex R2 #1: hard-fail on missing state. Silent default
    # weakens the "code-enforced" guarantee. By PHASE 1 spawn time, PHASE 0
    # has already initialized pipeline.state.json (see SKILL.md PHASE 0
    # step 3). Absence here is a contract violation.
    if not state_path.is_file():
        print(f"[select-engine] error: {state_path} not found "
              "(PHASE 0 must initialize state before BUILD selector runs)",
              file=sys.stderr)
        return 2
    try:
        state = json.loads(state_path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        print(f"[select-engine] cannot parse {state_path}: {e}", file=sys.stderr)
        return 2

    fixture_class = (state.get("source") or {}).get("fixture_class")
    engine, override = select_engine(args.phase, args.engine, fixture_class)

    if override is not None:
        # iter-0020 schema: per-phase override map at
        # state.route.engine_overrides (per pipeline-state.md "Route" §).
        # state.route exists by this point (PHASE 0 step 3 initializes it),
        # but defensive setdefault stays in case of mid-pipeline edits.
        route = state.setdefault("route", {})
        overrides_map = route.setdefault("engine_overrides", {})
        overrides_map[args.phase] = override
        state_path.write_text(json.dumps(state, indent=2) + "\n")

    decision_msg = (
        f"[select-engine] phase={args.phase} engine={engine}"
        f" (flag={args.engine}, fixture_class={fixture_class!r}"
        + (f", override={override['from']}→{override['to']}" if override else "")
        + ")"
    )
    print(decision_msg, file=sys.stderr)
    print(engine)
    return 0


if __name__ == "__main__":
    sys.exit(main())
