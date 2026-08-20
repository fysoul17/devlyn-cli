#!/usr/bin/env python3
"""Standalone validator for the 0102 discovery-task fixture contract."""

from __future__ import annotations

import argparse
import ast
import difflib
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path


CLASSES = {
    "unsupported_assumption",
    "missed_repo_invariant",
    "absent_failure_mode",
    "broken_dependency",
}
PREFIX_CLASSES = {
    "UA": "unsupported_assumption",
    "MI": "missed_repo_invariant",
    "AF": "absent_failure_mode",
    "BD": "broken_dependency",
}
REGISTERED_IDS = {
    **{f"EQ4P-{prefix}1": category for prefix, category in PREFIX_CLASSES.items()},
    **{
        f"EQ4-{prefix}{number}": category
        for prefix, category in PREFIX_CLASSES.items()
        for number in range(1, 9)
    },
}
TASK_FIELDS = {
    "id", "class", "goal", "invariant", "visible_files", "edit_site_dir",
    "contract_artifacts", "contract_tokens_a", "contract_tokens_b",
    "outcome_tokens_a", "outcome_tokens_b",
    "dependency_edges", "contract_paths", "decoy_artifacts",
}
BINDING_FIELDS = {"file", "sha256", "quote"}
MANIFEST_FIELDS = {"id", "class", "invariant", "contract_bindings"}
ROLES = ("local-a", "local-b", "remote-a", "remote-b", "restore")
GENERIC_LITERALS = {"manifestations", "passed", "python3", "true", "false"}
TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)


class ValidationError(ValueError):
    """A fixture violates one named discovery-task law."""


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        print(f"ARGUMENT: {message}", file=sys.stderr)
        raise SystemExit(1)


def one_line(value: object) -> str:
    return " ".join(str(value).split())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path, label: str) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"{label}: cannot read JSON: {exc}") from exc


def posix_relative(value: object, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValidationError(f"{label}: path must be a non-empty string")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise ValidationError(f"{label}: unsafe path {value!r}")
    if not path.parts or path.parts[0] != "visible":
        raise ValidationError(f"{label}: path must be under visible/: {value}")
    return path


def visible_file(task_dir: Path, value: object, label: str) -> Path:
    relative = posix_relative(value, label)
    path = task_dir / relative
    if path.is_symlink() or not path.is_file() or not stat.S_ISREG(path.stat().st_mode):
        raise ValidationError(f"{label}: visible file is missing or not regular: {value}")
    try:
        path.resolve().relative_to((task_dir / "visible").resolve())
    except ValueError as exc:
        raise ValidationError(f"{label}: path escapes visible/: {value}") from exc
    return path


def visible_dir(task_dir: Path, value: object, label: str) -> Path:
    relative = posix_relative(value, label)
    path = task_dir / relative
    if path.is_symlink() or not path.is_dir():
        raise ValidationError(f"{label}: edit_site_dir is missing or not a directory")
    try:
        path.resolve().relative_to((task_dir / "visible").resolve())
    except ValueError as exc:
        raise ValidationError(f"{label}: edit_site_dir escapes visible/") from exc
    return path


def regular_tree(task_dir: Path) -> None:
    if task_dir.is_symlink() or not task_dir.is_dir():
        raise ValidationError("task directory must be a real directory")
    for path in task_dir.rglob("*"):
        if path.is_symlink():
            raise ValidationError(f"unsafe symlink in task tree: {path.relative_to(task_dir)}")
        if path.is_file() and not stat.S_ISREG(path.stat().st_mode):
            raise ValidationError(f"non-regular file in task tree: {path.relative_to(task_dir)}")
        if not path.is_file() and not path.is_dir():
            raise ValidationError(f"non-regular path in task tree: {path.relative_to(task_dir)}")


def token_set(value: object, label: str, minimum: int) -> set[str]:
    if not isinstance(value, list) or len(value) < minimum or any(
        not isinstance(item, str) or TOKEN_RE.fullmatch(item) is None for item in value
    ):
        raise ValidationError(f"{label}: must contain at least {minimum} non-empty strings")
    folded = {item.casefold() for item in value}
    if len(folded) != len(value):
        raise ValidationError(f"{label}: tokens must be unique case-insensitively")
    return folded


def words(text: str) -> set[str]:
    return {word.casefold() for word in TOKEN_RE.findall(text)}


def has_token(text: str, token: str) -> bool:
    return token.casefold() in words(text)


def binding(task_dir: Path, value: object, label: str) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != BINDING_FIELDS:
        raise ValidationError(f"{label}: binding must contain exactly file, sha256, quote")
    path = visible_file(task_dir, value["file"], label)
    digest, quote = value["sha256"], value["quote"]
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise ValidationError(f"{label}: sha256 must be 64 lowercase hex characters")
    if digest != sha256(path):
        raise ValidationError(f"{label}: sha256 mismatch for {value['file']}")
    if not isinstance(quote, str) or not quote:
        raise ValidationError(f"{label}: quote must be non-empty")
    try:
        if quote not in path.read_text(encoding="utf-8"):
            raise ValidationError(f"{label}: quote is absent from {value['file']}")
    except UnicodeDecodeError as exc:
        raise ValidationError(f"{label}: bound file is not UTF-8") from exc
    return {key: value[key] for key in ("file", "sha256", "quote")}


def parse_task(task_dir: Path) -> tuple[dict[str, object], list[Path], Path]:
    required = [
        task_dir / "task.json", task_dir / "hidden" / "oracle.py", task_dir / "hidden" / "manifests.json",
        *(task_dir / "patches" / name for name in ("gold.patch", "noop.patch", "symptom.patch")),
    ]
    missing = [str(path.relative_to(task_dir)) for path in required if not path.is_file()]
    if missing:
        raise ValidationError(f"required files missing: {', '.join(missing)}")
    regular_tree(task_dir)
    raw = load_json(task_dir / "task.json", "task.json")
    if not isinstance(raw, dict) or set(raw) != TASK_FIELDS:
        raise ValidationError("task.json: fields must exactly match the discovery schema")
    for key in ("id", "class", "goal", "invariant", "edit_site_dir"):
        if not isinstance(raw[key], str) or not raw[key].strip():
            raise ValidationError(f"task.json: {key} must be a non-empty string")
    if raw["id"] != task_dir.name or raw["id"] not in REGISTERED_IDS:
        raise ValidationError("task.json: id must equal a registered directory name")
    if raw["class"] not in CLASSES or REGISTERED_IDS[raw["id"]] != raw["class"]:
        raise ValidationError("task.json: class does not match the embedded id table")
    files = raw["visible_files"]
    if not isinstance(files, list) or any(not isinstance(item, str) for item in files) or len(set(files)) != len(files):
        raise ValidationError("task.json: visible_files must be unique strings")
    paths = [visible_file(task_dir, item, "task.json visible_files") for item in files]
    actual = sorted(
        path.relative_to(task_dir).as_posix() for path in (task_dir / "visible").rglob("*")
        if path.is_file() and not path.is_symlink()
    )
    if sorted(files) != actual:
        raise ValidationError("task.json: visible_files must exhaust visible regular files")
    edit_site = visible_dir(task_dir, raw["edit_site_dir"], "task.json")
    artifacts = raw["contract_artifacts"]
    if not isinstance(artifacts, list) or len(artifacts) != 2 or any(not isinstance(item, str) for item in artifacts):
        raise ValidationError("task.json: contract_artifacts must be an ordered length-2 path array")
    if len(set(artifacts)) != 2:
        raise ValidationError("task.json: contract_artifacts must be distinct")
    # Bindings carry quotes in manifests; artifacts are validated here for safe existence and later against them.
    for artifact in artifacts:
        visible_file(task_dir, artifact, "task.json contract_artifacts")
    token_set(raw["contract_tokens_a"], "contract_tokens_a", 3)
    token_set(raw["contract_tokens_b"], "contract_tokens_b", 3)
    outcomes_a = token_set(raw["outcome_tokens_a"], "outcome_tokens_a", 1)
    outcomes_b = token_set(raw["outcome_tokens_b"], "outcome_tokens_b", 1)
    if outcomes_a & outcomes_b or len(outcomes_a | outcomes_b) < 3:
        raise ValidationError("task.json: outcome token sets must be disjoint with union size at least 3")
    return raw, paths, edit_site


def assertion_literals(oracle: Path) -> set[str]:
    try:
        tree = ast.parse(oracle.read_text(encoding="utf-8"), filename=str(oracle))
    except (OSError, UnicodeDecodeError, SyntaxError) as exc:
        raise ValidationError(f"oracle.py: cannot parse leakage literals: {exc}") from exc
    roots = [node.test for node in ast.walk(tree) if isinstance(node, ast.Assert)]
    roots += [node for node in ast.walk(tree) if isinstance(node, ast.Compare)]
    return {
        value.strip() for root in roots for node in ast.walk(root)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
        for value in [node.value] if len(value.strip()) >= 12 and value.casefold() not in GENERIC_LITERALS
    }


def manifests(task_dir: Path, task: dict[str, object]) -> list[dict[str, object]]:
    raw = load_json(task_dir / "hidden" / "manifests.json", "manifests.json")
    if not isinstance(raw, dict) or set(raw) != {"manifestations"} or not isinstance(raw["manifestations"], list):
        raise ValidationError("manifests.json: root must contain exactly manifestations")
    items = raw["manifestations"]
    if len(items) != 5:
        raise ValidationError("manifests.json: must contain exactly five manifestations")
    if [item.get("id") if isinstance(item, dict) else None for item in items] != list(ROLES):
        raise ValidationError("manifests.json: roles must be the five registered roles in order")
    expected: list[dict[str, str]] | None = None
    for index, item in enumerate(items):
        label = f"manifests.json manifestation[{index}]"
        if not isinstance(item, dict) or set(item) != MANIFEST_FIELDS:
            raise ValidationError(f"{label}: fields must exactly match the manifest schema")
        if item["class"] != task["class"] or item["invariant"] != task["invariant"]:
            raise ValidationError(f"{label}: class or invariant differs from task.json")
        values = item["contract_bindings"]
        if not isinstance(values, list) or len(values) != 2:
            raise ValidationError(f"{label}: contract_bindings must have exactly two entries")
        checked = [binding(task_dir, value, f"{label} binding[{position}]") for position, value in enumerate(values)]
        if [value["file"] for value in checked] != task["contract_artifacts"]:
            raise ValidationError(f"{label}: binding order must match task contract_artifacts")
        if expected is None:
            expected = checked
        elif checked != expected:
            raise ValidationError(f"{label}: contract_bindings diverge from the ordered shared set")
    return items


def registered_path(value: object, label: str) -> str:
    return posix_relative(value, label).as_posix()


def structural_dependency_edges(task_dir: Path, value: object) -> None:
    if not isinstance(value, list):
        raise ValidationError("dependency_edges: must be a list")
    for index, edge in enumerate(value):
        if not isinstance(edge, list) or len(edge) != 2:
            raise ValidationError(f"dependency_edges[{index}]: must be a [source, target] pair")
        source = visible_file(task_dir, edge[0], f"dependency_edges[{index}] source")
        target = visible_file(task_dir, edge[1], f"dependency_edges[{index}] target")
        if source == target:
            raise ValidationError(f"dependency_edges[{index}]: endpoints must be distinct visible files")


def structural_contract_paths(task_dir: Path, value: object, artifacts: list[Path]) -> set[str]:
    if not isinstance(value, list) or len(value) != len(artifacts):
        raise ValidationError("contract_paths: must contain one non-empty path per contract artifact")
    path_nodes: set[str] = set()
    for index, raw_path in enumerate(value):
        if not isinstance(raw_path, list) or not raw_path:
            raise ValidationError(f"contract_paths[{index}]: must contain a non-empty path of visible files")
        for node in raw_path:
            path_nodes.add(
                visible_file(task_dir, node, f"contract_paths[{index}] node")
                .relative_to(task_dir)
                .as_posix()
            )
    return path_nodes


def decoy_artifacts(task_dir: Path, task: dict[str, object], edit_site: Path, artifacts: list[Path], path_nodes: set[str]) -> tuple[list[Path], set[str]]:
    raw = task["decoy_artifacts"]
    if not isinstance(raw, dict) or set(raw) != {"modules", "tokens"}:
        raise ValidationError("decoy_artifacts: must contain exactly modules and tokens")
    modules = raw["modules"]
    if not isinstance(modules, list) or len(modules) < 10 or any(not isinstance(item, str) for item in modules):
        raise ValidationError("decoy_artifacts: modules must list at least ten paths")
    if modules != sorted(set(modules)):
        raise ValidationError("decoy_artifacts: modules must be sorted and duplicate-free")
    decoys = [visible_file(task_dir, item, "decoy_artifacts module") for item in modules]
    artifact_names = {path.relative_to(task_dir).as_posix() for path in artifacts}
    decoy_names = {path.relative_to(task_dir).as_posix() for path in decoys}
    if decoy_names & (artifact_names | path_nodes):
        raise ValidationError("decoy_artifacts: a decoy must not be a contract artifact or contract-path node")
    all_tokens = token_set(task["contract_tokens_a"], "contract_tokens_a", 3) | token_set(task["contract_tokens_b"], "contract_tokens_b", 3)
    tokens = token_set(raw["tokens"], "decoy_artifacts tokens", 1)
    if not tokens <= all_tokens:
        raise ValidationError("decoy_artifacts: tokens must be contract tokens")
    artifact_distances = [directory_distance(edit_site, artifact.parent) for artifact in artifacts]
    decoy_hits: set[tuple[str, str]] = set()
    observed_tokens: set[str] = set()
    for decoy in decoys:
        if directory_distance(edit_site, decoy.parent) > 2 or not all(directory_distance(edit_site, decoy.parent) < distance for distance in artifact_distances):
            raise ValidationError("decoy_artifacts: every decoy must be within distance 2 and strictly closer than each contract artifact")
        text = decoy.read_text(encoding="utf-8")
        hits = {token for token in all_tokens if has_token(text, token)}
        if not hits:
            raise ValidationError("decoy_artifacts: every decoy must contain a contract-token hit")
        name = decoy.relative_to(task_dir).as_posix()
        decoy_hits.update((name, token) for token in hits)
        observed_tokens.update(hits)
    if tokens != observed_tokens:
        raise ValidationError("decoy_artifacts: tokens must exactly register all decoy contract-token hits")
    artifact_hits = {
        (artifact.relative_to(task_dir).as_posix(), token)
        for artifact in artifacts for token in all_tokens if has_token(artifact.read_text(encoding="utf-8"), token)
    }
    if len(decoy_hits) <= len(artifact_hits):
        raise ValidationError("decoy_artifacts: distinct decoy hits must exceed contract-artifact hits")
    return decoys, tokens


def generator_inventory(task_dir: Path, task: dict[str, object], edit_site: Path, artifacts: list[Path], decoys: list[Path], path_nodes: set[str]) -> None:
    inventory = task_dir / "generator-inventory.json"
    if inventory.is_symlink() or not inventory.is_file() or not stat.S_ISREG(inventory.stat().st_mode):
        raise ValidationError("generator-inventory: must be a regular file")
    raw = load_json(inventory, "generator-inventory.json")
    if not isinstance(raw, dict) or set(raw) != {"files"} or not isinstance(raw["files"], list):
        raise ValidationError("generator-inventory: root must contain exactly files")
    entries = raw["files"]
    previous = ""
    forbidden = {artifact.relative_to(task_dir).as_posix() for artifact in artifacts} | {decoy.relative_to(task_dir).as_posix() for decoy in decoys} | path_nodes
    edit_relative = edit_site.relative_to(task_dir).as_posix()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256"}:
            raise ValidationError(f"generator-inventory[{index}]: must contain exactly path and sha256")
        path_value = entry["path"]
        if path_value == "generator-inventory.json":
            raise ValidationError("generator-inventory: inventory must not list itself")
        path_name = registered_path(path_value, f"generator-inventory[{index}] path")
        if path_name <= previous:
            raise ValidationError("generator-inventory: entries must be sorted and duplicate-free")
        previous = path_name
        path = visible_file(task_dir, path_name, f"generator-inventory[{index}] path")
        digest = entry["sha256"]
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None or digest != sha256(path):
            raise ValidationError(f"generator-inventory[{index}]: sha256 mismatch")
        if path_name == edit_relative or path_name.startswith(edit_relative + "/") or path_name in forbidden:
            raise ValidationError("generator-inventory: payload inventory lists treatment-bearing path")


def leakage_and_topology(task_dir: Path, task: dict[str, object], paths: list[Path], edit_site: Path, entries: list[dict[str, object]]) -> tuple[list[Path], set[str]]:
    hidden = task_dir / "hidden"
    forbidden = {str(item["id"]) for item in entries}
    forbidden.update(path.stem for path in hidden.rglob("*") if path.is_file() and len(path.stem) >= 4)
    forbidden.update(assertion_literals(hidden / "oracle.py"))
    scans = [("goal", str(task["goal"]))]
    python_paths = [path for path in paths if path.suffix == ".py"]
    scans += [(path.relative_to(task_dir / "visible").as_posix(), path.read_text(encoding="utf-8")) for path in python_paths]
    for label, text in scans:
        for value in forbidden:
            if value.casefold() in text.casefold():
                raise ValidationError(f"leakage: {label} contains hidden token {value!r}")
    if len(paths) < 120:
        raise ValidationError("topology: visible file count must be at least 120")
    if sum(path.stat().st_size for path in paths) < 2_000_000:
        raise ValidationError("topology: visible source bytes must be at least 2000000")
    visible = task_dir / "visible"
    modules = [path for path in visible.iterdir() if path.is_dir() and not path.is_symlink() and any(
        file.is_file() and file.suffix == ".py" and file in python_paths for file in path.rglob("*")
    )]
    if len(modules) < 4:
        raise ValidationError("topology: at least four top-level modules are required")
    structural_dependency_edges(task_dir, task["dependency_edges"])
    artifacts = [visible_file(task_dir, item, "contract artifact") for item in task["contract_artifacts"]]
    for artifact in artifacts:
        if directory_distance(edit_site, artifact.parent) < 4:
            raise ValidationError("topology: contract artifact directory distance must be at least 4")
    path_nodes = structural_contract_paths(task_dir, task["contract_paths"], artifacts)
    decoys, decoy_tokens = decoy_artifacts(task_dir, task, edit_site, artifacts, path_nodes)
    generator_inventory(task_dir, task, edit_site, artifacts, decoys, path_nodes)
    contract_a = token_set(task["contract_tokens_a"], "contract_tokens_a", 3)
    contract_b = token_set(task["contract_tokens_b"], "contract_tokens_b", 3)
    artifact_text = [path.read_text(encoding="utf-8") for path in artifacts]
    for tokens, content, label in ((contract_a, artifact_text[0], "a"), (contract_b, artifact_text[1], "b")):
        if not all(has_token(content, token) for token in tokens):
            raise ValidationError(f"topology: contract token set {label} is absent from its artifact")
    edit_parts = [path.relative_to(visible).as_posix() for path in python_paths if is_under(path, edit_site)]
    edit_text = "\n".join(path.read_text(encoding="utf-8") for path in python_paths if is_under(path, edit_site))
    blocked = contract_a | contract_b
    if any(has_token(str(task["goal"]), token) or any(has_token(part, token) for part in edit_parts) or has_token(edit_text, token) for token in blocked):
        raise ValidationError("topology: contract token leaked into goal or edit-site path/content")
    if any(item in str(task["goal"]) for item in task["contract_artifacts"]):
        raise ValidationError("topology: goal must not contain a contract artifact path")
    all_bytes = sum(path.stat().st_size for path in paths)
    edit_bytes = sum(path.stat().st_size for path in paths if is_under(path, edit_site))
    if all_bytes == 0 or edit_bytes * 100 > all_bytes * 30:
        raise ValidationError("topology: edit-site byte share exceeds 30%")
    changed = patch_paths(task_dir / "patches" / "symptom.patch")
    edit_relative = edit_site.relative_to(visible).as_posix()
    if not changed or any(path != edit_relative and not path.startswith(edit_relative + "/") for path in changed):
        raise ValidationError("topology: symptom.patch modifies outside edit_site_dir")
    return decoys, decoy_tokens


def is_under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def directory_distance(left: Path, right: Path) -> int:
    first, second = left.resolve().parts, right.resolve().parts
    common = 0
    while common < min(len(first), len(second)) and first[common] == second[common]:
        common += 1
    return len(first) + len(second) - 2 * common


def patch_paths(path: Path) -> set[str]:
    values: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(("--- ", "+++ ")):
            name = line[4:].split("\t", 1)[0]
            if name == "/dev/null" or not re.fullmatch(r"[ab]/[^\s]+", name):
                raise ValidationError("topology: symptom.patch has an unsafe patch path")
            values.add(name[2:])
    return values


def snapshot(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        if path.is_file():
            result[relative] = f"file:{sha256(path)}"
        elif path.is_dir():
            metadata = path.stat()
            result[relative] = f"dir:{metadata.st_mtime_ns}:{metadata.st_size}"
        else:
            metadata = path.lstat()
            result[relative] = f"other:{metadata.st_mtime_ns}:{metadata.st_size}"
    return result


def run_oracle(task_dir: Path, workdir: Path, entries: list[dict[str, object]], self_test: bool = False) -> dict[str, bool]:
    before = snapshot(workdir)
    environment = os.environ.copy()
    if self_test:
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        result = subprocess.run(
            [sys.executable, str(task_dir / "hidden" / "oracle.py"), str(workdir)], text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=30, env=environment,
        )
    except subprocess.TimeoutExpired as exc:
        raise ValidationError("oracle execution timed out") from exc
    if before != snapshot(workdir):
        raise ValidationError("oracle mutation residue in workdir")
    if result.returncode != 0:
        raise ValidationError(f"oracle execution failed: {one_line(result.stderr or result.stdout or result.returncode)}")
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValidationError("oracle output is not one JSON object") from exc
    if not isinstance(data, dict) or set(data) != {"manifestations"} or not isinstance(data["manifestations"], list):
        raise ValidationError("oracle output root must exactly contain manifestations")
    results = data["manifestations"]
    expected = [str(item["id"]) for item in entries]
    if len(results) != 5 or [item.get("id") if isinstance(item, dict) else None for item in results] != expected:
        raise ValidationError("oracle results must contain the five manifest ids in order")
    if any(not isinstance(item, dict) or set(item) != {"id", "passed"} or not isinstance(item["passed"], bool) for item in results):
        raise ValidationError("oracle result fields must exactly be id and passed")
    return {str(item["id"]): bool(item["passed"]) for item in results}


def apply_patch(task_dir: Path, workdir: Path, name: str) -> None:
    executable = shutil.which("patch")
    if executable is None:
        raise ValidationError("patch utility is unavailable")
    result = subprocess.run(
        [executable, "-p1", "--forward", "--batch", "-i", str(task_dir / "patches" / name)], cwd=workdir,
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=30,
    )
    if result.returncode != 0:
        raise ValidationError(f"patch application failed for {name}: {one_line(result.stderr or result.stdout)}")


def case(task_dir: Path, entries: list[dict[str, object]], patch: str | None, self_test: bool) -> dict[str, bool]:
    with tempfile.TemporaryDirectory(prefix="discovery-validator-") as temporary:
        workdir = Path(temporary) / "visible"
        shutil.copytree(task_dir / "visible", workdir)
        if patch:
            apply_patch(task_dir, workdir, patch)
        return run_oracle(task_dir, workdir, entries, self_test)


def vectors(task_dir: Path, entries: list[dict[str, object]], self_test: bool) -> None:
    cases = {name: case(task_dir, entries, patch, self_test) for name, patch in (
        ("no-patch", None), ("noop", "noop.patch"), ("gold", "gold.patch"), ("symptom", "symptom.patch"),
    )}
    if not all(cases["gold"][role] for role in ROLES):
        raise ValidationError("pass-vector: gold.patch must be TTTTT")
    if [cases["symptom"][role] for role in ROLES] != [True, True, False, False, False]:
        raise ValidationError("pass-vector: symptom.patch must be TTFFF")
    for name in ("no-patch", "noop"):
        if cases[name]["local-a"] or cases[name]["local-b"]:
            raise ValidationError(f"pass-vector: {name} must fail both local roles")


def neutralization_replacement(tokens: set[str]) -> str:
    attempt = 0
    while True:
        candidate = "zz" + hashlib.sha256(("\0".join(sorted(tokens)) + f":{attempt}").encode()).hexdigest()
        if candidate.casefold() not in tokens:
            return candidate
        attempt += 1


def assert_neutralized_tokens(visible: Path, tokens: set[str]) -> None:
    for path in visible.rglob("*"):
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            if any(has_token(text, token) for token in tokens):
                raise ValidationError(f"neutralization: registered decoy token survives in {path.relative_to(visible)}")


def neutralize_decoys(task_dir: Path, task: dict[str, object], entries: list[dict[str, object]], tokens: set[str], self_test: bool) -> None:
    baseline = {name: case(task_dir, entries, patch_name, self_test) for name, patch_name in (
        ("no-patch", None), ("noop", "noop.patch"), ("gold", "gold.patch"), ("symptom", "symptom.patch"),
    )}
    contract_tokens = token_set(task["contract_tokens_a"], "contract_tokens_a", 3) | token_set(task["contract_tokens_b"], "contract_tokens_b", 3)
    reserved = contract_tokens | tokens
    replacement = neutralization_replacement(reserved)
    if replacement.casefold() in reserved:
        raise ValidationError("neutralization: replacement token collides with a registered token")
    with tempfile.TemporaryDirectory(prefix="discovery-validator-neutralization-") as temporary:
        root = Path(temporary) / task_dir.name
        shutil.copytree(task_dir, root)
        for target in (root / "visible").rglob("*"):
            if not target.is_file():
                continue
            text = target.read_text(encoding="utf-8")
            neutralized = TOKEN_RE.sub(
                lambda match: replacement if match.group(0).casefold() in tokens else match.group(0), text,
            )
            target.write_text(neutralized, encoding="utf-8")
        assert_neutralized_tokens(root / "visible", tokens)
        neutralized_cases = {name: case(root, entries, patch_name, self_test) for name, patch_name in (
            ("no-patch", None), ("noop", "noop.patch"), ("gold", "gold.patch"), ("symptom", "symptom.patch"),
        )}
    if baseline != neutralized_cases:
        raise ValidationError("neutralization: decoy-token removal must preserve every smoke-case vector")


def complementarity(task_dir: Path, task: dict[str, object]) -> None:
    artifacts = [visible_file(task_dir, value, "contract artifact") for value in task["contract_artifacts"]]
    texts = [path.read_text(encoding="utf-8") for path in artifacts]
    first = token_set(task["outcome_tokens_a"], "outcome_tokens_a", 1)
    second = token_set(task["outcome_tokens_b"], "outcome_tokens_b", 1)
    union = first | second
    if not all(has_token(texts[0], token) for token in first) or not all(has_token(texts[1], token) for token in second):
        raise ValidationError("complementarity: outcome tokens are absent from their assigned artifact")
    if all(has_token(texts[1], token) for token in first) or all(has_token(texts[0], token) for token in second):
        raise ValidationError("complementarity: token sets must each retain a token absent from the other artifact")
    if any(all(has_token(text, token) for token in union) for text in texts):
        raise ValidationError("complementarity: neither artifact may contain the complete union")
    if not all(has_token(str(task["invariant"]), token) for token in union):
        raise ValidationError("complementarity: invariant must contain every outcome token")


def validate(task_dir: Path, self_test: bool = False) -> tuple[dict[str, object] | None, list[str]]:
    try:
        task, paths, edit_site = parse_task(task_dir)
        entries = manifests(task_dir, task)
        decoys, decoy_tokens = leakage_and_topology(task_dir, task, paths, edit_site, entries)
        complementarity(task_dir, task)
        vectors(task_dir, entries, self_test)
        neutralize_decoys(task_dir, task, entries, decoy_tokens, self_test)
        return task, []
    except (OSError, UnicodeDecodeError, subprocess.SubprocessError, ValidationError) as exc:
        return None, [one_line(exc)]


def patch(before: str, after: str, path: str) -> str:
    return "".join(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True), f"a/{path}", f"b/{path}"))


def write_fixture(root: Path, identifier: str) -> None:
    """Write the smallest legal fixture used solely by --self-test."""
    visible, hidden, patches = root / "visible", root / "hidden", root / "patches"
    for directory in (
        visible / "edit", visible / "bridge", visible / "remote" / "alpha" / "contracts",
        visible / "remote" / "beta" / "guides", visible / "decoys", visible / "mass", hidden, patches,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    engine_name = "engine.py"
    base, symptom, gold = "STATE = 0\n", "STATE = 1\n", "STATE = 2\n"
    (visible / "edit" / engine_name).write_text(base, encoding="utf-8")
    (visible / "bridge" / "step_one.py").write_text("BRIDGE = True\n", encoding="utf-8")
    alpha = "ALPHA = 'azurine bellwether cinderly outcomea sparkone sparktwo'\n"
    beta = "BETA = 'dovetail emberline farsight outcomeb sparkthree'\n"
    alpha_path = visible / "remote" / "alpha" / "contracts" / "alpha.py"
    beta_path = visible / "remote" / "beta" / "guides" / "beta.py"
    alpha_path.write_text(alpha, encoding="utf-8")
    beta_path.write_text(beta, encoding="utf-8")
    decoy_tokens = ["azurine", "bellwether", "cinderly", "dovetail", "emberline", "farsight"]
    decoy_paths: list[str] = []
    for number in range(10):
        token = decoy_tokens[number % len(decoy_tokens)]
        path = visible / "decoys" / f"decoy{number:02}.py"
        path.write_text(f"DECOY = '{token}'\n", encoding="utf-8")
        decoy_paths.append(path.relative_to(root).as_posix())
    generated: list[str] = []
    for number in range(106):
        path = visible / "mass" / f"mass{number:03}.py"
        path.write_text("MASS = " + repr("ordinary generated support " * 1000) + "\n", encoding="utf-8")
        generated.append(path.relative_to(root).as_posix())
    artifacts = ["visible/remote/alpha/contracts/alpha.py", "visible/remote/beta/guides/beta.py"]
    bindings = [
        {"file": item, "sha256": sha256(root / item), "quote": quote}
        for item, quote in zip(artifacts, (alpha.strip(), beta.strip()))
    ]
    invariant = "azurine bellwether cinderly dovetail emberline farsight outcomea outcomeb sparkone sparktwo sparkthree compose the result."
    task = {
        "id": identifier, "class": REGISTERED_IDS[identifier], "goal": "Repair the ordinary edit component.",
        "invariant": invariant,
        "visible_files": sorted(path.relative_to(root).as_posix() for path in visible.rglob("*") if path.is_file()),
        "edit_site_dir": "visible/edit", "contract_artifacts": artifacts,
        "contract_tokens_a": ["azurine", "bellwether", "cinderly"],
        "contract_tokens_b": ["dovetail", "emberline", "farsight"],
        "outcome_tokens_a": ["outcomea", "sparkone", "sparktwo"],
        "outcome_tokens_b": ["outcomeb", "sparkthree"],
        "dependency_edges": [["visible/edit/engine.py", "visible/bridge/step_one.py"]],
        "contract_paths": [
            ["visible/bridge/step_one.py", artifacts[0]],
            ["visible/bridge/step_one.py", artifacts[1]],
        ],
        "decoy_artifacts": {"modules": decoy_paths, "tokens": decoy_tokens},
    }
    (root / "task.json").write_text(json.dumps(task, indent=2) + "\n", encoding="utf-8")
    entries = [{"id": role, "class": task["class"], "invariant": invariant, "contract_bindings": bindings} for role in ROLES]
    (hidden / "manifests.json").write_text(json.dumps({"manifestations": entries}, indent=2) + "\n", encoding="utf-8")
    oracle = """import json, pathlib, sys
state = (pathlib.Path(sys.argv[1]) / 'edit' / '%s').read_text().splitlines()[-1]
level = int(state.split('=')[1])
print(json.dumps({'manifestations': [
 {'id':'local-a','passed':level >= 1}, {'id':'local-b','passed':level >= 1},
 {'id':'remote-a','passed':level >= 2}, {'id':'remote-b','passed':level >= 2}, {'id':'restore','passed':level >= 2}]}))
""" % engine_name
    (hidden / "oracle.py").write_text(oracle, encoding="utf-8")
    (patches / "gold.patch").write_text(patch(base, gold, f"edit/{engine_name}"), encoding="utf-8")
    (patches / "symptom.patch").write_text(patch(base, symptom, f"edit/{engine_name}"), encoding="utf-8")
    noop = (visible / "mass" / "mass000.py").read_text(encoding="utf-8")
    (patches / "noop.patch").write_text(patch(noop, noop + "UNCHANGED = True\n", "mass/mass000.py"), encoding="utf-8")
    inventory = {"files": [{"path": path, "sha256": sha256(root / path)} for path in generated]}
    (root / "generator-inventory.json").write_text(json.dumps(inventory, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")


def self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="discovery-validator-self-test-") as temporary:
        base = Path(temporary) / "EQ4P-UA1"
        write_fixture(base, "EQ4P-UA1")
        other = Path(temporary) / "EQ4-UA2"
        write_fixture(other, "EQ4-UA2")
        for name, root in (("valid-fixture", base), ("valid-second-id", other)):
            _, errors = validate(root, self_test=True)
            if errors:
                raise AssertionError(f"{name}: expected green, got {errors}")
        for name, change in (
            ("visible-data-file", visible_data_file),
            ("neutralization-collision", neutralization_collision_fixture),
        ):
            root = Path(temporary) / name / base.name
            shutil.copytree(base, root)
            change(root)
            _, errors = validate(root, self_test=True)
            if errors:
                raise AssertionError(f"{name}: expected green, got {errors}")
        # The named scenarios are deliberately independent copies: each has to fail closed.
        scenarios = {
            "missing-required": lambda root: (root / "patches" / "gold.patch").unlink(),
            "bad-schema": lambda root: json_update(root / "task.json", lambda data: data.update({"extra": 1})),
            "path-escape": lambda root: json_update(root / "task.json", lambda data: data["visible_files"].__setitem__(0, "visible/../escape")),
            "symlink": lambda root: make_symlink(root),
            "incomplete-visible-files": lambda root: json_update(root / "task.json", lambda data: data["visible_files"].pop()),
            "binding-hash": lambda root: json_update(root / "hidden" / "manifests.json", lambda data: data["manifestations"][0]["contract_bindings"][0].update({"sha256": "0" * 64})),
            "wrong-roles": lambda root: json_update(root / "hidden" / "manifests.json", lambda data: data["manifestations"].__setitem__(0, {**data["manifestations"][0], "id": "wrong"})),
            "divergent-bindings": lambda root: json_update(root / "hidden" / "manifests.json", lambda data: data["manifestations"][1]["contract_bindings"][0].update({"quote": "azurine"})),
            "goal-token-leakage": lambda root: json_update(root / "task.json", lambda data: data.update({"goal": "azurine leaked"})),
            "oracle-non-json": lambda root: (root / "hidden" / "oracle.py").write_text("print('not json')\n", encoding="utf-8"),
            "oracle-nonzero": lambda root: (root / "hidden" / "oracle.py").write_text("raise SystemExit(2)\n", encoding="utf-8"),
            "patch-apply": lambda root: (root / "patches" / "gold.patch").write_text("bad patch\n", encoding="utf-8"),
            "file-count": lambda root: remove_files(root),
            "modules": lambda root: collapse_module(root),
            "distance": lambda root: move_artifact_near_edit(root),
            "byte-share": lambda root: inflate_edit(root),
            "token-path-scan": lambda root: rename_token_path(root),
            "symptom-locality": lambda root: (root / "patches" / "symptom.patch").write_text(patch("x\n", "y\n", "mass/mass000.py"), encoding="utf-8"),
            "artifact-role-order": lambda root: json_update(root / "hidden" / "manifests.json", lambda data: data["manifestations"].__setitem__(2, {**data["manifestations"][2], "id": "remote-b"})),
            "oracle-mutation": lambda root: (root / "hidden" / "oracle.py").write_text("import pathlib,sys,json\np=pathlib.Path(sys.argv[1]);(p/'changed').write_text('x');print(json.dumps({'manifestations':[{'id':x,'passed':False} for x in ['local-a','local-b','remote-a','remote-b','restore']]}))\n", encoding="utf-8"),
            "complementarity": lambda root: defeat_complementarity(root),
            "mass-bytes": lambda root: shrink_mass(root),
            "dependency-edge-shape": lambda root: json_update(root / "task.json", lambda data: data.update({"dependency_edges": [["visible/edit/engine.py"]]})),
            "contract-path-shape": lambda root: json_update(root / "task.json", lambda data: data["contract_paths"][0].clear()),
            "decoy-count": lambda root: json_update(root / "task.json", lambda data: data["decoy_artifacts"].update({"modules": data["decoy_artifacts"]["modules"][:-1]})),
            "decoy-path-node": lambda root: register_path_node_as_decoy(root),
            "decoy-distance": lambda root: move_decoy_far(root),
            "decoy-hit": lambda root: (root / "visible" / "decoys" / "decoy00.py").write_text("DECOY = 'ordinary'\n", encoding="utf-8"),
            "decoy-dominance": lambda root: saturate_artifact_hits(root),
            "decoy-token-registration": lambda root: json_update(root / "task.json", lambda data: data["decoy_artifacts"].update({"tokens": data["decoy_artifacts"]["tokens"][:-1]})),
            "neutralization": lambda root: make_decoy_semantic(root),
            "schema-missing-edges": lambda root: json_update(root / "task.json", lambda data: data.pop("dependency_edges")),
            "schema-missing-paths": lambda root: json_update(root / "task.json", lambda data: data.pop("contract_paths")),
            "schema-missing-decoys": lambda root: json_update(root / "task.json", lambda data: data.pop("decoy_artifacts")),
            "inventory-missing": lambda root: (root / "generator-inventory.json").unlink(),
            "inventory-digest": lambda root: json_update(root / "generator-inventory.json", lambda data: data["files"][0].update({"sha256": "0" * 64})),
            "inventory-edit": lambda root: inventory_add(root, "visible/edit/engine.py"),
            "inventory-contract": lambda root: inventory_add(root, "visible/remote/alpha/contracts/alpha.py"),
            "inventory-decoy": lambda root: inventory_add(root, "visible/decoys/decoy00.py"),
            "inventory-path-node": lambda root: inventory_add(root, "visible/bridge/step_one.py"),
            "inventory-self-listing": lambda root: inventory_add(root, "generator-inventory.json", "0" * 64),
        }
        diagnostics = {
            "missing-required": "required files missing",
            "bad-schema": "task.json: fields must exactly match the discovery schema",
            "path-escape": "task.json visible_files: unsafe path",
            "symlink": "unsafe symlink in task tree",
            "incomplete-visible-files": "task.json: visible_files must exhaust visible regular files",
            "binding-hash": "sha256 mismatch",
            "wrong-roles": "roles must be the five registered roles in order",
            "divergent-bindings": "contract_bindings diverge from the ordered shared set",
            "goal-token-leakage": "contract token leaked into goal or edit-site path/content",
            "oracle-non-json": "oracle output is not one JSON object",
            "oracle-nonzero": "oracle execution failed",
            "patch-apply": "patch application failed for gold.patch",
            "file-count": "visible file count must be at least 120",
            "modules": "at least four top-level modules are required",
            "distance": "contract artifact directory distance must be at least 4",
            "byte-share": "edit-site byte share exceeds 30%",
            "token-path-scan": "contract token leaked into goal or edit-site path/content",
            "symptom-locality": "symptom.patch modifies outside edit_site_dir",
            "artifact-role-order": "roles must be the five registered roles in order",
            "oracle-mutation": "oracle mutation residue in workdir",
            "complementarity": "token sets must each retain a token absent from the other artifact",
            "gold-vector": "pass-vector: gold.patch must be TTTTT",
            "symptom-vector": "pass-vector: symptom.patch must be TTFFF",
            "pristine-vector": "pass-vector: no-patch must fail both local roles",
            "noop-vector": "pass-vector: noop must fail both local roles",
            "mass-bytes": "visible source bytes must be at least 2000000",
            "dependency-edge-shape": "dependency_edges[0]: must be a [source, target] pair",
            "contract-path-shape": "contract_paths[0]: must contain a non-empty path",
            "decoy-count": "modules must list at least ten paths",
            "decoy-path-node": "must not be a contract artifact or contract-path node",
            "decoy-distance": "must be within distance 2 and strictly closer",
            "decoy-hit": "every decoy must contain a contract-token hit",
            "decoy-dominance": "distinct decoy hits must exceed contract-artifact hits",
            "decoy-token-registration": "tokens must exactly register all decoy contract-token hits",
            "neutralization": "decoy-token removal must preserve every smoke-case vector",
            "neutralization-residue": "registered decoy token survives",
            "schema-missing-edges": "fields must exactly match the discovery schema",
            "schema-missing-paths": "fields must exactly match the discovery schema",
            "schema-missing-decoys": "fields must exactly match the discovery schema",
            "inventory-missing": "generator-inventory: must be a regular file",
            "inventory-digest": "generator-inventory[0]: sha256 mismatch",
            "inventory-edit": "payload inventory lists treatment-bearing path",
            "inventory-contract": "payload inventory lists treatment-bearing path",
            "inventory-decoy": "payload inventory lists treatment-bearing path",
            "inventory-path-node": "payload inventory lists treatment-bearing path",
            "inventory-self-listing": "inventory must not list itself",
        }
        for name, change in scenarios.items():
            expected_diagnostic = diagnostics.get(name)
            if expected_diagnostic is None:
                raise AssertionError(f"{name}: self-test is missing an expected diagnostic")
            root = Path(temporary) / name / base.name
            shutil.copytree(base, root)
            change(root)
            _, errors = validate(root, self_test=True)
            if not errors:
                raise AssertionError(f"{name}: expected a fail-closed diagnostic")
            if not any(expected_diagnostic in error for error in errors):
                raise AssertionError(f"{name}: expected {expected_diagnostic!r}, got {errors}")
        expected_diagnostic = diagnostics["neutralization-residue"]
        residue = Path(temporary) / "neutralization-residue" / base.name
        shutil.copytree(base, residue)
        neutralization_collision_fixture(residue)
        registered = token_set(load_json(residue / "task.json", "task.json")["decoy_artifacts"]["tokens"], "decoy_artifacts tokens", 1)
        for path in (residue / "visible").rglob("*"):
            if path.is_file():
                text = path.read_text(encoding="utf-8")
                path.write_text(TOKEN_RE.sub(lambda match: "neutralized" if match.group(0).casefold() in registered else match.group(0), text), encoding="utf-8")
        try:
            assert_neutralized_tokens(residue / "visible", registered)
        except ValidationError as exc:
            if expected_diagnostic not in str(exc):
                raise AssertionError(f"neutralization-residue: unexpected diagnostic {exc}") from exc
        else:
            raise AssertionError("neutralization-residue: expected a fail-closed diagnostic")
        # Vector failures exercise the individual gold, symptom, pristine, and noop clauses.
        for name, replacement in (("gold-vector", "level >= 3"), ("symptom-vector", "level >= 0"), ("pristine-vector", "level >= 0"), ("noop-vector", "level >= 0")):
            expected_diagnostic = diagnostics.get(name)
            if expected_diagnostic is None:
                raise AssertionError(f"{name}: self-test is missing an expected diagnostic")
            root = Path(temporary) / name / base.name
            shutil.copytree(base, root)
            oracle = root / "hidden" / "oracle.py"
            text = oracle.read_text(encoding="utf-8")
            if name == "gold-vector":
                text = text.replace("level >= 2", replacement)
            elif name == "symptom-vector":
                text = text.replace("level >= 2", replacement)
            elif name == "pristine-vector":
                text = text.replace("level >= 1", replacement)
            else:
                (root / "patches" / "noop.patch").write_text(patch("STATE = 0\n", "STATE = 1\n", "edit/engine.py"), encoding="utf-8")
            oracle.write_text(text, encoding="utf-8")
            _, errors = validate(root, self_test=True)
            if not errors:
                raise AssertionError(f"{name}: expected a pass-vector failure")
            if not any(expected_diagnostic in error for error in errors):
                raise AssertionError(f"{name}: expected {expected_diagnostic!r}, got {errors}")


def json_update(path: Path, update: object) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not callable(update):
        raise TypeError("json update must be callable")
    update(data)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def move_artifact_near_edit(root: Path) -> None:
    source, target = root / "visible" / "remote" / "alpha" / "contracts" / "alpha.py", root / "visible" / "edit" / "alpha.py"
    source.rename(target)
    source.write_text("FILLER = 'ordinary support record'\n", encoding="utf-8")
    json_update(root / "task.json", lambda data: data["contract_artifacts"].__setitem__(0, "visible/edit/alpha.py"))
    refresh_files(root)
    json_update(root / "hidden" / "manifests.json", lambda data: [entry["contract_bindings"][0].update({"file": "visible/edit/alpha.py", "sha256": sha256(target)}) for entry in data["manifestations"]])


def refresh_files(root: Path) -> None:
    json_update(root / "task.json", lambda data: data.update({"visible_files": sorted(
        path.relative_to(root).as_posix() for path in (root / "visible").rglob("*") if path.is_file()
    )}))


def refresh_inventory(root: Path) -> None:
    inventory = root / "generator-inventory.json"
    json_update(inventory, lambda data: data.update({"files": [
        {"path": entry["path"], "sha256": sha256(root / entry["path"])}
        for entry in data["files"] if (root / entry["path"]).is_file()
    ]}))


def make_symlink(root: Path) -> None:
    (root / "visible" / "mass" / "link.py").symlink_to("mass000.py")
    refresh_files(root)


def remove_files(root: Path) -> None:
    for path in sorted((root / "visible" / "mass").glob("mass*.py"))[:2]:
        path.unlink()
    refresh_files(root)
    refresh_inventory(root)


def collapse_module(root: Path) -> None:
    destination = root / "visible" / "bridge"
    for directory in (root / "visible" / "decoys", root / "visible" / "mass"):
        for path in directory.iterdir():
            path.rename(destination / f"collapsed_{directory.name}_{path.name}")
        directory.rmdir()
    refresh_files(root)


def visible_data_file(root: Path) -> None:
    (root / "visible" / "mass" / "payload.txt").write_text("ordinary inert payload\n", encoding="utf-8")
    refresh_files(root)


def neutralization_collision_fixture(root: Path) -> None:
    alpha = root / "visible" / "remote" / "alpha" / "contracts" / "alpha.py"
    alpha.write_text(alpha.read_text(encoding="utf-8").replace("azurine", "neutralized"), encoding="utf-8")
    for number in (0, 6):
        path = root / "visible" / "decoys" / f"decoy{number:02}.py"
        path.write_text(path.read_text(encoding="utf-8").replace("azurine", "neutralized"), encoding="utf-8")
    json_update(root / "task.json", lambda data: data.update({
        "invariant": data["invariant"].replace("azurine", "neutralized"),
        "contract_tokens_a": ["neutralized", *data["contract_tokens_a"][1:]],
        "decoy_artifacts": {**data["decoy_artifacts"], "tokens": ["neutralized", *data["decoy_artifacts"]["tokens"][1:]]},
    }))
    task = load_json(root / "task.json", "task.json")
    assert isinstance(task, dict)

    def update_manifests(data: object) -> None:
        assert isinstance(data, dict)
        for entry in data["manifestations"]:
            entry["invariant"] = task["invariant"]
            entry["contract_bindings"][0].update({"sha256": sha256(alpha), "quote": alpha.read_text(encoding="utf-8").strip()})

    json_update(root / "hidden" / "manifests.json", update_manifests)


def rename_token_path(root: Path) -> None:
    (root / "visible" / "edit" / "engine.py").rename(root / "visible" / "edit" / "azurine.py")
    refresh_files(root)
    json_update(root / "task.json", lambda data: data.update({
        "dependency_edges": [["visible/edit/azurine.py" if node == "visible/edit/engine.py" else node for node in edge] for edge in data["dependency_edges"]],
    }))


def defeat_complementarity(root: Path) -> None:
    alpha = root / "visible" / "remote" / "alpha" / "contracts" / "alpha.py"
    alpha.write_text(alpha.read_text(encoding="utf-8") + "OUTCOMES = 'outcomeb sparkthree'\n", encoding="utf-8")
    json_update(root / "hidden" / "manifests.json", lambda data: [
        entry["contract_bindings"][0].update({"sha256": sha256(alpha)}) for entry in data["manifestations"]
    ])


def shrink_mass(root: Path) -> None:
    for path in sorted((root / "visible" / "mass").glob("mass*.py"))[:40]:
        path.write_text("MASS = 'small'\n", encoding="utf-8")


def inflate_edit(root: Path) -> None:
    (root / "visible" / "edit" / "engine.py").write_text(
        "import bridge.step_one\nSTATE = 0\n" + "FILLER = 'ordinary'\n" * 2_000_000,
        encoding="utf-8",
    )


def register_path_node_as_decoy(root: Path) -> None:
    json_update(root / "task.json", lambda data: data["decoy_artifacts"].update({
        "modules": sorted(["visible/bridge/step_one.py", *data["decoy_artifacts"]["modules"][1:]])
    }))


def move_decoy_far(root: Path) -> None:
    source = root / "visible" / "decoys" / "decoy00.py"
    target = root / "visible" / "remote" / "alpha" / "other" / "decoy00.py"
    target.parent.mkdir()
    source.rename(target)
    refresh_files(root)
    json_update(root / "task.json", lambda data: data["decoy_artifacts"].update({
        "modules": sorted(["visible/remote/alpha/other/decoy00.py" if value == "visible/decoys/decoy00.py" else value for value in data["decoy_artifacts"]["modules"]])
    }))


def saturate_artifact_hits(root: Path) -> None:
    for index, path in enumerate((
        root / "visible" / "remote" / "alpha" / "contracts" / "alpha.py",
        root / "visible" / "remote" / "beta" / "guides" / "beta.py",
    )):
        path.write_text(path.read_text(encoding="utf-8") + "TOKENS = 'azurine bellwether cinderly dovetail emberline farsight'\n", encoding="utf-8")
        json_update(root / "hidden" / "manifests.json", lambda data, index=index, path=path: [
            entry["contract_bindings"][index].update({"sha256": sha256(path)}) for entry in data["manifestations"]
        ])


def make_decoy_semantic(root: Path) -> None:
    oracle = root / "hidden" / "oracle.py"
    oracle.write_text(oracle.read_text(encoding="utf-8").replace(
        "level = int(state.split('=')[1])",
        "decoy = (pathlib.Path(sys.argv[1]) / 'decoys' / 'decoy00.py').read_text()\nlevel = int(state.split('=')[1])\nif 'azurine' not in decoy:\n level = -1",
    ), encoding="utf-8")


def inventory_add(root: Path, path: str, digest: str | None = None) -> None:
    def update(data: object) -> None:
        assert isinstance(data, dict)
        value = digest if digest is not None else sha256(root / path)
        data["files"].append({"path": path, "sha256": value})
        data["files"].sort(key=lambda entry: entry["path"])
    json_update(root / "generator-inventory.json", update)


def main() -> int:
    parser = Parser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--task", type=Path)
    group.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        try:
            self_test()
        except (AssertionError, OSError, ValidationError, subprocess.SubprocessError) as exc:
            print(f"SELF-TEST: {one_line(exc)}", file=sys.stderr)
            return 1
        print("SELF-TEST: PASS")
        return 0
    task, errors = validate(args.task.resolve())
    if errors:
        for error in errors:
            print(f"INVALID: {error}", file=sys.stderr)
        return 1
    assert task is not None
    print(task["id"], task["class"], task["edit_site_dir"], *task["contract_artifacts"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
