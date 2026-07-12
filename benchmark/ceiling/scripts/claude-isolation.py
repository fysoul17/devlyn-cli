#!/usr/bin/env python3
"""Shared fail-closed launcher for measured Claude benchmark paths."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any


CLAUDE_ENV_KEYS = tuple(
    sorted(
        (
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC",
            "CLAUDE_CONFIG_DIR",
            "CODEX_HOME",
            "DISABLE_AUTOUPDATER",
            "GIT_CONFIG_GLOBAL",
            "GIT_CONFIG_NOSYSTEM",
            "HOME",
            "LANG",
            "LC_ALL",
            "NPM_CONFIG_CACHE",
            "NPM_CONFIG_USERCONFIG",
            "PATH",
            "TERM",
            "TMPDIR",
            "TZ",
        )
    )
)
AUTH_ERROR_MARKERS = ("not logged in", "authentication_error", "authentication failed")


class IsolationError(RuntimeError):
    """The structural isolation contract could not be established."""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def resolve_direct_binary(name: str, explicit: str | None = None) -> Path:
    candidates = [Path(explicit)] if explicit else [
        Path(part) / name for part in os.environ.get("PATH", "").split(os.pathsep) if part
    ]
    for candidate in candidates:
        if not candidate.is_file() or not os.access(candidate, os.X_OK):
            continue
        if ".superset" in candidate.parts:
            continue
        resolved = candidate.resolve()
        if name == "codex" and resolved.name == "codex.js":
            package_root = resolved.parent.parent
            native = sorted(
                path
                for path in (package_root / "node_modules" / "@openai").glob(
                    "codex-*/vendor/*/bin/codex*"
                )
                if path.is_file() and os.access(path, os.X_OK)
            )
            if native:
                resolved = native[0].resolve()
        if ".superset" not in resolved.parts:
            # Keep Claude's non-Superset executable symlink so its directory
            # contains a callable `claude` for nested pipeline invocations.
            return candidate.parent.resolve() / candidate.name if name == "claude" else resolved
    raise IsolationError(f"direct non-Superset {name} CLI not found")


def frozen_path(claude_binary: Path, codex_binary: Path) -> str:
    node = shutil.which("node")
    candidates = [claude_binary.parent, codex_binary.parent]
    if node:
        candidates.append(Path(node).resolve().parent)
    candidates.extend(Path(value) for value in ("/usr/bin", "/bin", "/usr/sbin", "/sbin"))
    unique: list[str] = []
    for candidate in candidates:
        rendered = str(candidate.resolve())
        if ".superset" in Path(rendered).parts:
            raise IsolationError(f"Superset path forbidden in frozen PATH: {rendered}")
        if rendered not in unique:
            unique.append(rendered)
    return os.pathsep.join(unique)


def prepare_home(home: Path, codex_home: Path) -> None:
    (home / ".claude").mkdir(parents=True, exist_ok=True)
    (home / "t").mkdir(parents=True, exist_ok=True)
    (home / "n").mkdir(parents=True, exist_ok=True)
    (home / ".npmrc").touch()
    codex_home.mkdir(parents=True, exist_ok=True)
    config = codex_home / "config.toml"
    if not config.exists():
        config.write_text(
            'model = "gpt-5.6-terra"\nmodel_reasoning_effort = "xhigh"\n',
            encoding="utf-8",
        )
    auth = codex_home / "auth.json"
    if not auth.exists():
        source = Path(
            os.environ.get(
                "CEILING_TEST_AUTH_JSON",
                str(
                    Path(os.environ.get("CEILING_REAL_HOME", str(Path.home())))
                    / ".codex/auth.json"
                ),
            )
        )
        if not source.is_file():
            raise IsolationError(f"Codex auth file missing: {source}")
        shutil.copyfile(source, auth)
        auth.chmod(0o600)


def seed_credentials(config_dir: Path) -> tuple[Path, str]:
    credentials = config_dir / ".credentials.json"
    test_source = os.environ.get("CEILING_TEST_CLAUDE_CREDENTIALS")
    if test_source:
        source = Path(test_source)
        if not source.is_file():
            raise IsolationError(f"Claude credentials seed missing: {source}")
        blob = source.read_bytes()
        mechanism = "test-file"
    else:
        try:
            completed = subprocess.run(
                ["/usr/bin/security", "find-generic-password", "-s", "Claude Code-credentials", "-w"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise IsolationError(f"Claude Keychain credentials read failed: {exc}") from exc
        if completed.returncode != 0:
            error = completed.stderr.decode("utf-8", errors="replace").strip()
            raise IsolationError(f"Claude Keychain credentials read failed: {error}")
        blob = completed.stdout.rstrip(b"\n")
        mechanism = "macos-keychain-blob"
    if not blob:
        raise IsolationError("Claude credentials seed was empty")
    credentials.unlink(missing_ok=True)
    descriptor = os.open(credentials, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(blob)
    return credentials, mechanism


def isolated_environment(home: Path, codex_home: Path, path_value: str) -> dict[str, str]:
    values = {
        "PATH": path_value,
        "HOME": str(home),
        "CLAUDE_CONFIG_DIR": str(home / ".claude"),
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        "DISABLE_AUTOUPDATER": "1",
        "CODEX_HOME": str(codex_home),
        "TERM": "dumb",
        "LANG": "en_US.UTF-8",
        "LC_ALL": "en_US.UTF-8",
        "TZ": "UTC",
        "TMPDIR": str(home / "t"),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "NPM_CONFIG_USERCONFIG": str(home / ".npmrc"),
        "NPM_CONFIG_CACHE": str(home / "n"),
    }
    if tuple(sorted(values)) != CLAUDE_ENV_KEYS:
        raise IsolationError("Claude environment allowlist drift")
    return values


def user_memory_markers(path: Path | None) -> list[str]:
    if path is None or not path.is_file():
        return []
    return sorted(
        {
            line.strip()
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
            if len(line.strip()) >= 24
        }
    )


def user_memory_hits(text: str, path: Path | None) -> list[str]:
    return [marker for marker in user_memory_markers(path) if marker in text]


def command_for(mode: str, claude_binary: Path, prompt: str | None, debug_file: Path | None) -> list[str]:
    if mode == "version":
        return [str(claude_binary), "--version"]
    if mode == "shell-canary":
        return ["/bin/zsh", "-lc", "printf isolation-ok"]
    if prompt is None:
        raise IsolationError(f"{mode} requires a prompt")
    command = [str(claude_binary), "-p", prompt]
    if mode in {"arm", "canary-a"}:
        command.extend(
            [
                "--dangerously-skip-permissions",
                "--effort",
                "xhigh",
                "--setting-sources",
                "project,local",
                "--strict-mcp-config",
                "--mcp-config",
                '{"mcpServers":{}}',
                "--model",
                "sonnet",
                "--output-format",
                "json",
            ]
        )
        if debug_file is not None:
            command.extend(["--debug-file", str(debug_file)])
    elif mode in {"judge", "canary-judge"}:
        command.extend(
            [
                "--model",
                "sonnet",
                "--strict-mcp-config",
                "--mcp-config",
                '{"mcpServers":{}}',
                "--dangerously-skip-permissions",
                "--output-format",
                "json",
            ]
        )
    else:
        raise IsolationError(f"unsupported Claude launch mode: {mode}")
    return command


def write_metadata(
    path: Path | None,
    *,
    home: Path,
    codex_home: Path,
    claude_binary: Path,
    codex_binary: Path,
    path_value: str,
    version: str,
    auth_mechanism: str,
    credentials_seeded: bool,
) -> dict[str, Any]:
    payload = {
        "direct_claude": {
            "path": str(claude_binary),
            "sha256": sha256_file(claude_binary),
            "version": version,
            "requested_model": "sonnet",
            "superset_wrapper": False,
        },
        "direct_codex": {
            "path": str(codex_binary),
            "sha256": sha256_file(codex_binary),
            "superset_wrapper": False,
        },
        "home": str(home),
        "claude_config_dir": str(home / ".claude"),
        "claude_env_keys": list(CLAUDE_ENV_KEYS),
        "claude_env_keys_sha256": sha256_bytes("\n".join(CLAUDE_ENV_KEYS).encode()),
        "frozen_path": path_value,
        "auth_mechanism": auth_mechanism,
        "credentials_seeded": credentials_seeded,
    }
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def launch_claude(
    *,
    mode: str,
    home: Path,
    codex_home: Path,
    workdir: Path,
    prompt: str | None,
    debug_file: Path | None,
    metadata_out: Path | None,
    user_memory_file: Path | None,
    timeout_seconds: int | None = None,
) -> subprocess.CompletedProcess[str]:
    claude_binary = resolve_direct_binary("claude", os.environ.get("CEILING_TEST_CLAUDE_BIN"))
    codex_binary = resolve_direct_binary("codex", os.environ.get("CEILING_TEST_CODEX_BIN"))
    prepare_home(home, codex_home)
    path_value = frozen_path(claude_binary, codex_binary)
    environment = isolated_environment(home, codex_home, path_value)
    credentials: Path | None = None
    mechanism = "macos-keychain-blob"
    try:
        try:
            credentials, mechanism = seed_credentials(home / ".claude")
        except IsolationError:
            write_metadata(
                metadata_out,
                home=home,
                codex_home=codex_home,
                claude_binary=claude_binary,
                codex_binary=codex_binary,
                path_value=path_value,
                version="unavailable",
                auth_mechanism=mechanism,
                credentials_seeded=False,
            )
            raise
        version_result = subprocess.run(
            [str(claude_binary), "--version"],
            cwd=workdir,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=30,
        )
        version = (version_result.stdout or version_result.stderr).strip().splitlines()
        if version_result.returncode != 0 or not version:
            raise IsolationError("direct Claude CLI version probe failed")
        metadata = write_metadata(
            metadata_out,
            home=home,
            codex_home=codex_home,
            claude_binary=claude_binary,
            codex_binary=codex_binary,
            path_value=path_value,
            version=version[0],
            auth_mechanism=mechanism,
            credentials_seeded=True,
        )
        if metadata["direct_claude"]["superset_wrapper"] or ".superset" in path_value:
            raise IsolationError("Superset wrapper reached isolated Claude launch")
        command = command_for(mode, claude_binary, prompt, debug_file)
        proc = subprocess.Popen(
            command,
            cwd=workdir,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        previous_handlers: dict[int, Any] = {}

        def forward(signum: int, _frame: Any) -> None:
            if proc.poll() is None:
                proc.send_signal(signum)

        for signum in (signal.SIGTERM, signal.SIGINT):
            previous_handlers[signum] = signal.signal(signum, forward)
        try:
            try:
                stdout, stderr = proc.communicate(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                proc.terminate()
                try:
                    proc.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.communicate()
                raise
        finally:
            for signum, handler in previous_handlers.items():
                signal.signal(signum, handler)
        combined = stdout + "\n" + stderr
        hits = user_memory_hits(combined, user_memory_file)
        if hits:
            raise IsolationError("user-memory-leak:" + sha256_bytes("\n".join(hits).encode()))
        if any(marker in combined.casefold() for marker in AUTH_ERROR_MARKERS):
            raise IsolationError("Claude authentication failure")
        if mode in {"arm", "canary-a", "judge", "canary-judge"} and proc.returncode == 0:
            try:
                wrapper = json.loads(stdout)
            except json.JSONDecodeError as exc:
                raise IsolationError("Claude JSON result wrapper missing") from exc
            usage = wrapper.get("modelUsage") or wrapper.get("usage")
            if not isinstance(usage, dict) or not usage or not all(
                "sonnet" in str(model).casefold() for model in usage
            ):
                raise IsolationError(
                    f"runtime model is not sonnet: "
                    f"{sorted(usage) if isinstance(usage, dict) else usage!r}"
                )
        return subprocess.CompletedProcess(command, proc.returncode, stdout, stderr)
    finally:
        if credentials is not None:
            credentials.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    launch = subparsers.add_parser("launch")
    launch.add_argument(
        "--mode",
        required=True,
        choices=("arm", "judge", "canary-a", "canary-judge", "version", "shell-canary"),
    )
    launch.add_argument("--home", required=True, type=Path)
    launch.add_argument("--codex-home", required=True, type=Path)
    launch.add_argument("--workdir", required=True, type=Path)
    launch.add_argument("--prompt-file", type=Path)
    launch.add_argument("--debug-file", type=Path)
    launch.add_argument("--metadata-out", type=Path)
    launch.add_argument("--user-memory-file", type=Path)
    launch.add_argument("--timeout-seconds", type=int)
    scan = subparsers.add_parser("scan-user-memory")
    scan.add_argument("--transcript", required=True, type=Path)
    scan.add_argument("--user-memory-file", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "scan-user-memory":
        text = args.transcript.read_text(encoding="utf-8", errors="replace")
        hits = user_memory_hits(text, args.user_memory_file)
        print(json.dumps({"family": "user-memory-leak", "hits": hits}, sort_keys=True))
        return 3 if hits else 0
    prompt = args.prompt_file.read_text(encoding="utf-8") if args.prompt_file else None
    try:
        result = launch_claude(
            mode=args.mode,
            home=args.home.resolve(),
            codex_home=args.codex_home.resolve(),
            workdir=args.workdir.resolve(),
            prompt=prompt,
            debug_file=args.debug_file.resolve() if args.debug_file else None,
            metadata_out=args.metadata_out.resolve() if args.metadata_out else None,
            user_memory_file=args.user_memory_file.resolve() if args.user_memory_file else None,
            timeout_seconds=args.timeout_seconds,
        )
    except (IsolationError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"CLAUDE_ISOLATION_ERROR: {exc}", file=sys.stderr)
        return 78
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
