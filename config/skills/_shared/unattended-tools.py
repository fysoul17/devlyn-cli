#!/usr/bin/env python3
"""Launch-only tool restrictions for delegated Codex and drain Claude children."""
from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import tempfile


PLATFORM = runpy.run_path(str(Path(__file__).with_name("platform-support.py")))
LOADS = runpy.run_path(str(Path(__file__).with_name("expected-contract.py")))["loads_strict_json"]
CODEX_FEATURES = ("apps", "plugins", "remote_plugin", "computer_use", "browser_use",
                  "browser_use_external", "in_app_browser")


class PolicyError(ValueError):
    pass


def deny_names(engine):
    path = Path.home() / ".devlyn/unattended-tools.json"
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    except (OSError, UnicodeError) as exc:
        raise PolicyError(f"unattended tools: cannot read {path}: {exc}") from exc
    try:
        value = LOADS(raw)
        if not isinstance(value, dict) or set(value) - {"codex", "claude"}:
            raise ValueError("expected an object with codex/claude server-name arrays")
        for names in value.values():
            if not isinstance(names, list) or any(not isinstance(n, str) or not n.strip() for n in names):
                raise ValueError("codex/claude must be arrays of nonempty server names")
        return value.get(engine, [])
    except ValueError as exc:
        raise PolicyError(f"unattended tools: invalid {path}: {exc}") from exc


def probe(command, cwd, label, env=None):
    try:
        result = subprocess.run(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, encoding="utf-8", timeout=30)
    except (OSError, UnicodeError, subprocess.TimeoutExpired) as exc:
        raise PolicyError(f"unattended tools: {label} failed: {exc}") from exc
    if result.returncode:
        raise PolicyError(f"unattended tools: {label} exited {result.returncode}: {result.stderr.strip()}")
    return result.stdout


def listed(command, cwd, label, key, env=None):
    raw = probe(command, cwd, label, env)
    try:
        value = LOADS(raw)
        if not isinstance(value, list) or any(
            not isinstance(item, dict) or not isinstance(item.get(key), str) or not item[key].strip()
            or not isinstance(item.get("enabled"), bool) for item in value
        ):
            raise ValueError(f"expected an array of objects with {key} and boolean enabled")
        return value
    except ValueError as exc:
        raise PolicyError(f"unattended tools: malformed {label} output: {exc}") from exc


def codex_launch(binary, argv, *, cwd=None, env=None, native=None):
    denied = {"node_repl", "computer-use", *deny_names("codex")}
    if native is None:
        resolved = shutil.which(binary)
        if resolved is None:
            raise PolicyError(f"unattended tools: Codex executable unavailable: {binary}")
        native = PLATFORM["native_argv"]([str(Path(resolved).absolute())])
    cwd, config, profile = cwd or Path.cwd(), [], []
    # Only configuration inputs belong in discovery; prompt/model/output arguments do not.
    values = {"-c", "--config", "-p", "--profile", "--enable", "--disable", "-C", "--cd",
              "-m", "--model", "-s", "--sandbox", "-o", "--output-last-message", "--output-schema",
              "--color", "--add-dir", "-i", "--image", "--local-provider", "--thread-source",
              "--cyber-access-program"}
    index = 0
    while index < len(argv) and argv[index] != "--":
        token = argv[index]
        if token[:2] in {"-c", "-C", "-p"} and len(token) > 2:
            key, equal, value = token[:2], "=", token[2:]
            if value.startswith("="):
                value = value[1:]
        else:
            key, equal, value = token.partition("=")
        if key in values:
            if not equal:
                index += 1
                if index == len(argv):
                    raise PolicyError(f"unattended tools: {key} requires a value")
                value = argv[index]
            if key in {"-C", "--cd"}:
                cwd = Path(value).absolute()
            elif key in {"-p", "--profile"}:
                profile.extend([key, value])
            elif key in {"-c", "--config", "--enable", "--disable"}:
                config.extend([key, value])
        elif token in {"--ignore-user-config", "--strict-config"}:
            config.append(token)
        index += 1
    shutdown = [part for feature in CODEX_FEATURES for part in ("--disable", feature)]
    try:
        # Codex 0.164 accepts profiles on mcp, but not on features list.
        raw = probe([*native, "features", "list", *shutdown, *config], cwd, "Codex feature preflight", env)
        states = {}
        for row in raw.splitlines():
            fields = row.split()
            if fields and fields[0] in CODEX_FEATURES:
                if len(fields) < 3 or fields[-1] not in {"true", "false"} or fields[0] in states:
                    raise PolicyError(f"unattended tools: malformed Codex feature row: {row}")
                states[fields[0]] = fields[-1]
        unsafe = [name for name in CODEX_FEATURES if states.get(name) != "false"]
        if unsafe:
            raise PolicyError(f"unattended tools: Codex features not disabled: {', '.join(unsafe)}")
    except PolicyError as exc:
        version = probe([*native, "--version"], cwd, "Codex version", env).strip()
        raise PolicyError(f"{exc} (Codex version: {version})") from exc
    command = [*native, *profile, "mcp", "list", "--json"]
    servers = listed([*command, *shutdown, *config], cwd, "Codex mcp list --json", "name", env)
    targeted = {s["name"] for s in servers} & denied
    overrides = []
    for name in sorted(targeted):
        if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
            raise PolicyError(f"unattended tools: cannot safely override Codex server: {name!r}")
        overrides.extend(["-c", f"mcp_servers.{name}.enabled=false"])
    # Match launch order: caller overrides come after the policy. Refuse a conflict.
    verification = listed([*command, *shutdown, *overrides, *config], cwd,
                          "Codex mcp list --json verification", "name", env)
    disabled = {s["name"] for s in verification if not s["enabled"]}
    unsafe = (targeted - disabled) | {s["name"] for s in verification if s["enabled"] and s["name"] in denied}
    if unsafe:
        raise PolicyError(f"unattended tools: Codex MCP overrides did not disable: {', '.join(sorted(unsafe))}")
    return [*shutdown, *overrides, *argv]


def claude_namespace(name):
    # Claude Code's MCP tool-name normalization preserves ASCII letters, digits, '_' and '-'.
    normalized = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
    if name.startswith("claude.ai "):
        normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized


@contextlib.contextmanager
def claude_launch(argv, cwd):
    denied = deny_names("claude")
    native = PLATFORM["native_argv"]([argv[0]], cwd=cwd)
    # Refuse configuration inputs we cannot verify. Do not consume or rewrite prompt values.
    for index, token in enumerate(argv[1:], 1):
        key, equal, value = token.partition("=")
        if key in {"--settings", "--setting-sources", "--plugin-dir", "--plugin-url", "--chrome"}:
            raise PolicyError(f"unattended tools: Claude {key} is not supported for drain executors")
        if key != "--add-dir":
            continue
        directories = [value] if equal else []
        for directory in argv[index + 1:]:
            if directory.startswith("-"):
                break
            directories.append(directory)
        if not directories:
            raise PolicyError("unattended tools: Claude --add-dir requires a directory")
        for directory in directories:
            for filename in ("settings.json", "settings.local.json"):
                path = Path(cwd) / Path(directory).expanduser() / ".claude" / filename
                try:
                    raw = path.read_text(encoding="utf-8")
                except FileNotFoundError:
                    continue
                except (OSError, UnicodeError) as exc:
                    raise PolicyError(f"unattended tools: cannot read Claude --add-dir settings {path}: {exc}") from exc
                try:
                    settings = LOADS(raw)
                    if not isinstance(settings, dict):
                        raise ValueError("expected a settings object")
                    if "enabledPlugins" in settings:
                        raise ValueError("enabledPlugins cannot be verified for --add-dir")
                except ValueError as exc:
                    raise PolicyError(f"unattended tools: Claude --add-dir settings {path}: {exc}") from exc
    env = {**os.environ, "ENABLE_CLAUDEAI_MCP_SERVERS": "false"}
    plugins = listed([*native, "--no-chrome", "plugin", "list", "--json"], cwd, "Claude plugin list --json", "id", env)
    targeted = {p["id"] for p in plugins if p["enabled"]}
    # Claude 2.1.314 recognizes disableClaudeAiConnectors; also override settings.env.
    settings = {"syncClaudeAiPlugins": False, "disableClaudeAiConnectors": True,
                "env": {"ENABLE_CLAUDEAI_MCP_SERVERS": "false"},
                "enabledPlugins": dict.fromkeys(sorted(targeted), False)}
    with tempfile.TemporaryDirectory(prefix="devlyn-unattended-") as temporary:
        path = Path(temporary) / "settings.json"
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(settings, stream, ensure_ascii=False)
        options = ["--settings", str(path)]
        if denied:
            options.append("--disallowedTools=" + ",".join("mcp__" + claude_namespace(n) for n in denied))
        options.append("--no-chrome")
        verification = listed([*native, *options, "plugin", "list", "--json"], cwd,
                              "Claude plugin list --json verification", "id", env)
        enabled = sorted({p["id"] for p in verification if p["enabled"]})
        if enabled:
            raise PolicyError(f"unattended tools: Claude plugin overrides did not disable: {', '.join(enabled)}; check managed settings")
        yield [argv[0], *options, *argv[1:]], env
