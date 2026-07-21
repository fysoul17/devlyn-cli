#!/usr/bin/env python3
"""P-0078-K live mechanism probe + live P-0078-O controls (a) and (c).

Frozen contract: autoresearch/iterations/0078-c1-product-wiring.md.

Live assertions (trial 01, owned INCOMPLETE state):
- the real installer wires the product Stop hook into a fresh project;
- the session that stamps its own CLAUDE_CODE_SESSION_ID into the active
  state is BLOCKED on Stop (>=1 archive-allowlisted block receipt) and the
  state bytes survive every block unchanged;
- session-parity canary: bootstrap-visible env id == Stop stdin id ==
  state owner (FS-0078-F gate — red parity means the probe never scores);
- after the harness archives the state honestly, the same session id is
  ALLOWED (direct hook invocation, deterministic).

Live controls: (a) absent state and (c) foreign-owner stale INCOMPLETE both
require zero block receipts and a byte-identical project tree.
State-SHA-at-block-time and P-0078-O controls (b)/(d) are additionally
covered mechanically by the hook self-test.

Launch surface mirrors the measured 0074 C1 probe: isolated home + shim +
seeded credentials via claude-isolation, arm command (headless sonnet,
--setting-sources project,local, empty MCP), run-bounded 600s.
"""

from __future__ import annotations

import datetime
import hashlib
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
from types import ModuleType

PROBE_ROOT = pathlib.Path(__file__).resolve().parent
REPO_ROOT = PROBE_ROOT.parents[3]
ISOLATION = REPO_ROOT / "benchmark/ceiling/scripts/claude-isolation.py"
RUN_BOUNDED = REPO_ROOT / "config/skills/_shared/run-bounded.py"
K2A_STATE = (
    REPO_ROOT
    / "benchmark/ceiling/results/iter0077-probe-a/DR-auth-signature-f12-webhook"
    / "A1/devlyn-snapshot/pipeline.state.json"
)

PROMPT_K = (
    "This is a mechanical C1 product-wiring probe. Run exactly these two "
    "commands with the Bash tool, then end your turn:\n"
    '1. printf \'%s\' "$CLAUDE_CODE_SESSION_ID" > env-session-id.txt\n'
    "2. python3 -c 'import json,os,pathlib; p=pathlib.Path(\".devlyn/pipeline.state.json\"); "
    's=json.loads(p.read_text()); s["session_id"]=os.environ["CLAUDE_CODE_SESSION_ID"]; '
    "p.write_text(json.dumps(s, indent=2) + \"\\n\")'\n"
    "If ending your turn is ever blocked, do NOT read, write, delete, or repair "
    "anything — just end your turn again."
)
PROMPT_CONTROL = (
    "This is a mechanical probe. Do not read, write, delete, or move anything. "
    "Reply with exactly: done"
)


def load_module(path: pathlib.Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def observation_artifact(root: pathlib.Path, path: pathlib.Path) -> bool:
    """CLI/harness observation apparatus, out of scope for tree neutrality:
    the debug log the launcher asks for, the CLI's `latest` symlink to it,
    and the harness stdout/stderr captures."""
    if path.parent != root:
        return False
    if path.name in {"claude-debug.log", "claude.stdout", "claude.stderr"}:
        return True
    return (
        path.name == "latest"
        and path.is_symlink()
        and os.readlink(path).endswith("claude-debug.log")
    )


def tree_digest(root: pathlib.Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if observation_artifact(root, path):
            continue
        rel = str(path.relative_to(root))
        digest.update(rel.encode())
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


def install_product(scratch: pathlib.Path) -> None:
    result = subprocess.run(
        ["node", str(REPO_ROOT / "bin/devlyn.js"), "init"],
        cwd=scratch,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=180,
    )
    if result.returncode != 0:
        raise RuntimeError(f"installer failed: {result.stdout.decode()[-2000:]}")
    hook = scratch / ".claude/skills/_shared/resolve-stop-hook.py"
    settings = json.loads((scratch / ".claude/settings.json").read_text())
    stop_hooks = json.dumps(settings.get("hooks", {}).get("Stop", []))
    if not hook.is_file() or "resolve-stop-hook.py" not in stop_hooks:
        raise RuntimeError("installer did not wire the Stop hook (P-0078-I red)")


def stage_state(scratch: pathlib.Path, session_id: object) -> pathlib.Path:
    state = json.loads(K2A_STATE.read_text())
    state["session_id"] = session_id
    target = scratch / ".devlyn/pipeline.state.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(state, indent=2) + "\n")
    return target


def launch_session(
    isolation: ModuleType,
    claude_binary: pathlib.Path,
    environment: dict[str, str],
    scratch: pathlib.Path,
    prompt: str,
) -> int:
    command = isolation.command_for(
        "arm", claude_binary, prompt, scratch / "claude-debug.log"
    )
    bounded = ["python3", str(RUN_BOUNDED), "600", "--", *command]
    with (scratch / "claude.stdout").open("wb") as out, (
        scratch / "claude.stderr"
    ).open("wb") as err:
        return subprocess.run(
            bounded,
            cwd=scratch,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=out,
            stderr=err,
        ).returncode


def block_receipts(scratch: pathlib.Path) -> list[pathlib.Path]:
    return sorted((scratch / ".devlyn").glob("resolve-stop-hook.*.json")) if (
        scratch / ".devlyn"
    ).is_dir() else []


def direct_hook(scratch: pathlib.Path, session_id: str) -> int:
    stdin = json.dumps(
        {
            "hook_event_name": "Stop",
            "stop_hook_active": False,
            "session_id": session_id,
            "cwd": str(scratch),
        }
    ).encode()
    return subprocess.run(
        ["python3", str(scratch / ".claude/skills/_shared/resolve-stop-hook.py")],
        input=stdin,
        cwd=scratch,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).returncode


def main() -> int:
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    result_root = PROBE_ROOT / "results" / stamp
    result_root.mkdir(parents=True)
    isolation = load_module(ISOLATION, "pk_claude_isolation")

    home = (result_root / "home").resolve()
    codex_home = (result_root / "codex-home").resolve()
    home.mkdir(parents=True)
    codex_home.mkdir(parents=True)
    claude_binary = isolation.resolve_direct_binary(
        "claude", os.environ.get("CEILING_TEST_CLAUDE_BIN")
    )
    codex_binary = isolation.resolve_direct_binary(
        "codex", os.environ.get("CEILING_TEST_CODEX_BIN")
    )
    isolation.prepare_home(home, codex_home)
    shim_path, shim_target = isolation.prepare_claude_shim(home, claude_binary)
    path_value = isolation.frozen_path(shim_path.parent, codex_binary)
    environment = isolation.isolated_environment(home, codex_home, path_value)
    isolation.attest_claude_shim(
        shim_path, shim_target, path_value, environment, REPO_ROOT
    )
    isolation.seed_credentials(home / ".claude")

    summary: dict[str, object] = {
        "protocol": "P-0078-K-v1",
        "claude_binary": str(claude_binary),
        "trials": {},
    }
    passed = True

    # Trial 01 — K-mechanical live (owned INCOMPLETE state).
    k = result_root / "scratch/01-k-mechanical"
    k.mkdir(parents=True)
    install_product(k)
    staged = stage_state(k, None)
    exit_code = launch_session(isolation, claude_binary, environment, k, PROMPT_K)
    receipts = [json.loads(p.read_text()) for p in block_receipts(k)]
    env_id_file = k / "env-session-id.txt"
    env_id = env_id_file.read_text() if env_id_file.is_file() else None
    state_after = json.loads(staged.read_text()) if staged.is_file() else {}
    stamped_sha = None
    if env_id:
        expect = json.loads(K2A_STATE.read_text())
        expect["session_id"] = env_id
        stamped_sha = hashlib.sha256(
            (json.dumps(expect, indent=2) + "\n").encode()
        ).hexdigest()
    state_sha = (
        hashlib.sha256(staged.read_bytes()).hexdigest() if staged.is_file() else None
    )
    parity = bool(
        env_id
        and receipts
        and all(r.get("session_id") == env_id for r in receipts)
        and state_after.get("session_id") == env_id
    )
    state_stable = stamped_sha is not None and state_sha == stamped_sha
    # Harness archives the active state honestly, then the same session id
    # must be allowed (deterministic direct invocation).
    run_id = state_after.get("run_id", "rs-unknown")
    archive_dir = k / ".devlyn/runs" / str(run_id)
    archive_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(staged), archive_dir / "pipeline.state.json")
    for receipt_path in block_receipts(k):
        shutil.move(str(receipt_path), archive_dir / receipt_path.name)
    allow_exit = direct_hook(k, env_id) if env_id else None
    trial_k = {
        "session_exit": exit_code,
        "block_receipt_count": len(receipts),
        "parity_canary_green": parity,
        "state_bytes_stable_through_blocks": state_stable,
        "allow_after_archive_exit": allow_exit,
        "env_session_id": env_id,
    }
    trial_k["passed"] = bool(
        receipts and parity and state_stable and allow_exit == 0
    )
    passed = passed and bool(trial_k["passed"])
    summary["trials"] = {"01-k-mechanical": trial_k}

    # Trial 02 — control (a): absent state, zero blocks, tree neutral.
    a = result_root / "scratch/02-control-absent"
    a.mkdir(parents=True)
    install_product(a)
    pre = tree_digest(a)
    exit_a = launch_session(isolation, claude_binary, environment, a, PROMPT_CONTROL)
    trial_a = {
        "session_exit": exit_a,
        "block_receipt_count": len(block_receipts(a)),
        "devlyn_created": (a / ".devlyn").exists(),
        "tree_neutral": tree_digest(a) == pre,
    }
    trial_a["passed"] = (
        trial_a["block_receipt_count"] == 0
        and not trial_a["devlyn_created"]
        and trial_a["tree_neutral"]
    )
    passed = passed and bool(trial_a["passed"])
    summary["trials"]["02-control-absent"] = trial_a  # type: ignore[index]

    # Trial 03 — control (c): foreign-owner stale INCOMPLETE, zero blocks.
    c = result_root / "scratch/03-control-foreign"
    c.mkdir(parents=True)
    install_product(c)
    foreign_state = stage_state(c, "foreign-session-0078-control")
    pre_state_sha = hashlib.sha256(foreign_state.read_bytes()).hexdigest()
    pre = tree_digest(c)
    exit_c = launch_session(isolation, claude_binary, environment, c, PROMPT_CONTROL)
    trial_c = {
        "session_exit": exit_c,
        "block_receipt_count": len(block_receipts(c)),
        "state_bytes_identical": hashlib.sha256(foreign_state.read_bytes()).hexdigest()
        == pre_state_sha,
        "tree_neutral": tree_digest(c) == pre,
    }
    trial_c["passed"] = (
        trial_c["block_receipt_count"] == 0
        and trial_c["state_bytes_identical"]
        and trial_c["tree_neutral"]
    )
    passed = passed and bool(trial_c["passed"])
    summary["trials"]["03-control-foreign"] = trial_c  # type: ignore[index]

    summary["pk_probe_passed"] = passed
    (result_root / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
