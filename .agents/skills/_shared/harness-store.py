"""Release identity and queue resource checks. Readers never write or create locks.

The release verifier is CLI-1's bin/release.js, not a second manifest verifier.
A Codex projection has .devlyn-harness-projection.json at its plugin root:
{schemaVersion: 1, release: ReleaseRef, source: "native/codex/plugins/devlyn"}.
Its complete regular-file tree (except that marker) must match that release subtree.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import subprocess
import sys

PROJECTION = ".devlyn-harness-projection.json"
CODEX_SOURCE = "native/codex/plugins/devlyn"


class HarnessError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise HarnessError(message)


def read_json(path):
    try:
        return json.loads(Path(path).read_bytes())
    except (OSError, ValueError) as exc:
        raise HarnessError(f"{path}: {exc}") from exc


def file_identity(path):
    path = Path(path)
    info = path.lstat()
    require(path.is_file() and not path.is_symlink() and info.st_nlink == 1, f"not a regular resource: {path}")
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def release_ref(value):
    require(isinstance(value, dict) and set(value) == {"package", "version", "digest", "root"}
            and value["package"] == "devlyn-cli"
            and all(isinstance(value[k], str) and value[k] and "\0" not in value[k] for k in ("version", "digest", "root"))
            and re.fullmatch(r"[a-f0-9]{64}", value["digest"]) and Path(value["root"]).is_absolute(), "malformed release reference")
    return value


def verify_release(root):
    root = Path(root)
    # As harness-status verifies it: an npm-installed package keeps npm's own .bin shims, which are checked.
    script = "const r=require(process.argv[1]);r.runJson(()=>r.verifyRelease(process.argv[2],{npmInstall:true}));"
    try:
        node = runpy.run_path(str(Path(__file__).with_name("platform-support.py")))["managed_node"]() or "node"
        result = subprocess.run([node, "-e", script, str(root / "bin/release.js"), str(root)], capture_output=True, text=True, encoding="utf-8")
    except (OSError, ValueError) as exc:
        raise HarnessError(f"release verifier could not start: {exc}") from exc
    require(result.returncode == 0, f"release verification failed: {root}: {result.stderr.strip()}")
    try:
        release = release_ref(json.loads(result.stdout)["data"]["release"])
    except (KeyError, ValueError, TypeError) as exc:
        raise HarnessError(f"invalid release verifier result: {root}: {exc}") from exc
    manifest = read_json(root / "release.json")
    defaults = file_identity(root / manifest["principles"]["defaults"])
    return {"schemaVersion": 1, "release": release, "defaults": defaults}


def walk_error(error):
    raise error  # os.walk otherwise silently skips unreadable projection directories.


def resolve(skills):
    """Resolve only this invoking skill's real ancestry; never search another install."""
    skill = (Path(skills) / "devlyn-ideate").resolve()
    for parent in (skill, *skill.parents):
        marker = parent / PROJECTION
        if marker.exists() or marker.is_symlink():
            file_identity(marker)
            projection = read_json(marker)
            require(isinstance(projection, dict) and set(projection) == {"schemaVersion", "release", "source"}
                    and type(projection["schemaVersion"]) is int and projection["schemaVersion"] == 1
                    and projection["source"] == CODEX_SOURCE, f"malformed projection: {marker}")
            ref = release_ref(projection["release"])
            binding = verify_release(ref["root"])
            require(binding["release"] == ref, f"projection release changed: {marker}")
            source = Path(ref["root"]) / CODEX_SOURCE
            require(skill == parent / "skills/devlyn-ideate", f"unexpected projection skill: {skill}")
            expected = {p.relative_to(source) for p in source.rglob("*") if p.is_file()}
            actual = set()
            for directory, dirs, files in os.walk(parent, onerror=walk_error):
                for name in dirs:
                    require(not (Path(directory) / name).is_symlink(), f"projection directory link: {directory}/{name}")
                for name in files:
                    file = Path(directory) / name
                    if file == marker:
                        continue
                    rel = file.relative_to(parent)
                    actual.add(rel)
                    require(rel in expected and file_identity(file)["sha256"] == file_identity(source / rel)["sha256"]
                            and (os.name == "nt" or bool(file.stat().st_mode & 0o111) == bool((source / rel).stat().st_mode & 0o111)),
                            f"projection resource changed: {file}")
            require(actual == expected, f"projection file list changed: {parent}")
            return binding
        manifest = parent / "release.json"
        if (manifest.exists() or manifest.is_symlink()) and skill in [parent / p / "devlyn-ideate" for p in
                ("config/skills", "native/claude/skills", CODEX_SOURCE + "/skills")]:
            return verify_release(parent)
    return None


def read_binding(common):
    path = Path(common) / "devlyn-loops/harness.json"
    if not path.exists() and not path.is_symlink():
        return None
    file_identity(path)
    binding = read_json(path)
    require(isinstance(binding, dict) and set(binding) == {"schemaVersion", "release", "defaults"}
            and type(binding["schemaVersion"]) is int and binding["schemaVersion"] == 1, f"incompatible queue binding: {path}")
    release_ref(binding["release"])
    resource(binding["defaults"])
    return binding


def resource(value):
    require(isinstance(value, dict) and set(value) == {"path", "sha256"}
            and isinstance(value["path"], str) and "\0" not in value["path"] and Path(value["path"]).is_absolute()
            and isinstance(value["sha256"], str) and re.fullmatch(r"[a-f0-9]{64}", value["sha256"]), "malformed resource binding")


def recovery_argv(binding, argv):
    return [sys.executable, str(Path(binding["release"]["root"]) / "config/skills/devlyn-ideate/scripts/queue.py"), *argv]


def check_binding(binding, invoking):
    if binding is None:
        return
    require(invoking is not None and binding["release"] == invoking["release"], "queue-release-mismatch")
    require(binding == invoking, "queue defaults changed; restore the bound release")


def packet_schema(packet):
    require(isinstance(packet, dict), "task packet must be an object")
    version = packet.get("schema_version", 1)
    require(type(version) is int and version in (1, 2), f"incompatible task packet version: {version!r}")
    if version == 1:
        return
    require("harness" in packet and isinstance(packet.get("methodology"), dict), "malformed packet v2 harness/methodology")
    methodology = packet["methodology"]
    require(set(methodology) == {"defaults", "projectInstructions"} and isinstance(methodology["projectInstructions"], list),
            "malformed packet v2 methodology")
    for entry in methodology["projectInstructions"]:
        resource(entry)
    if packet["harness"] is None:
        defaults = methodology["defaults"]
        require(packet.get("workerPrompt") is None and (defaults is None or (isinstance(defaults, dict) and defaults.get("source") == "skill")),
                "legacy packet has release resources")
        if defaults is not None:
            resource({k: v for k, v in defaults.items() if k != "source"})
        return
    release_ref(packet["harness"])
    defaults = methodology["defaults"]
    require(isinstance(defaults, dict) and defaults.get("source") == "release", "packet has no verified release defaults source")
    resource({k: v for k, v in defaults.items() if k != "source"})
    resource(packet.get("workerPrompt"))


def verify_packet(packet, path, skills):
    packet_schema(packet)
    if packet.get("schema_version", 1) == 1:
        return  # Preserve v1 execution without upgrading its resources.
    receipt = packet.get("receipt")
    require(isinstance(receipt, str) and "\0" not in receipt and Path(receipt).is_absolute()
            and Path(receipt).name == "receipt.json" and Path(receipt).parent.parent.name == "devlyn-completion"
            and Path(receipt) == Path(path).with_name("receipt.json"),
            "malformed packet receipt path")
    binding = read_binding(Path(receipt).parent.parent.parent)
    if packet["harness"] is None:
        require(binding is None, "bound task packet has no harness/defaults source")
        # An unbound installation's own defaults change with its normal updates: never gate acceptance or delivery on
        # their bytes (queue.py checks only their presence, before a spawn).
        return
    require(binding is not None, "packet queue binding is missing; restore harness.json")
    invoking = resolve(skills)
    ref = packet["harness"]
    require(invoking is not None and invoking["release"] == ref,
            f"packet-release-mismatch; use {Path(ref['root']) / 'config/skills/devlyn-ideate/scripts/queue.py'}")
    check_binding(binding, invoking)
    defaults = {"source": "release", **binding["defaults"]}
    require(packet["methodology"]["defaults"] == defaults, "packet defaults differ from queue binding")
    expected_runner = [str(Path(ref["root"]) / "config/skills/devlyn-ideate/scripts/acceptance.py"),
                       "run", "--packet", str(path)]
    require(isinstance(packet.get("runner"), list) and packet["runner"][1:] == expected_runner, "packet runner differs from bound release")
    prompt = packet["workerPrompt"]
    require(prompt["path"] == str(Path(path).parent / "worker-prompt.md") and file_identity(prompt["path"]) == prompt,
            "worker prompt changed or missing; restore the bound resource")
    for entry in packet["methodology"]["projectInstructions"]:
        name = Path(entry["path"]).name
        require(name in ("CLAUDE.md", "AGENTS.md") and entry["path"] == str(Path(packet["worktree"]) / name),
                "project instruction path escapes packet worktree")
        committed = subprocess.run(["git", "-C", packet["worktree"], "cat-file", "blob", f"{packet['inputs_sha']}:{name}"], capture_output=True)
        require(committed.returncode == 0 and hashlib.sha256(committed.stdout).hexdigest() == entry["sha256"],
                f"project instruction differs from inputs commit: {name}")
