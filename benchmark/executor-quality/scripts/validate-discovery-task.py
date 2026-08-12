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
    **{f"EQ3P-{prefix}1": category for prefix, category in PREFIX_CLASSES.items()},
    **{
        f"EQ3-{prefix}{number}": category
        for prefix, category in PREFIX_CLASSES.items()
        for number in range(1, 9)
    },
}
TASK_FIELDS = {
    "id", "class", "goal", "invariant", "visible_files", "edit_site_dir",
    "contract_artifacts", "contract_tokens_a", "contract_tokens_b",
    "outcome_tokens_a", "outcome_tokens_b",
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


def leakage_and_topology(task_dir: Path, task: dict[str, object], paths: list[Path], edit_site: Path, entries: list[dict[str, object]]) -> None:
    hidden = task_dir / "hidden"
    forbidden = {str(item["id"]) for item in entries}
    forbidden.update(path.stem for path in hidden.rglob("*") if path.is_file() and len(path.stem) >= 4)
    forbidden.update(assertion_literals(hidden / "oracle.py"))
    scans = [("goal", str(task["goal"]))]
    scans += [(path.relative_to(task_dir / "visible").as_posix(), path.read_text(encoding="utf-8")) for path in paths]
    for label, text in scans:
        for value in forbidden:
            if value.casefold() in text.casefold():
                raise ValidationError(f"leakage: {label} contains hidden token {value!r}")
    if not 24 <= len(paths) <= 60:
        raise ValidationError("topology: visible file count must be 24-60")
    visible = task_dir / "visible"
    modules = [path for path in visible.iterdir() if path.is_dir() and not path.is_symlink() and any(
        file.is_file() and file in paths for file in path.rglob("*")
    )]
    if len(modules) < 4:
        raise ValidationError("topology: at least four top-level modules are required")
    index = task_index(str(task["id"]))
    code_suffixes = {".py", ".js", ".mjs", ".cjs"}
    edit_code = [path for path in paths if is_under(path, edit_site) and path.suffix in code_suffixes]
    if index % 2:
        if not edit_code or any(path.suffix != ".py" for path in edit_code):
            raise ValidationError("topology: odd task edit site must contain only Python code")
        if any(path.suffix in {".js", ".mjs", ".cjs"} or path.name == "package.json" for path in paths):
            raise ValidationError("topology: odd task visible tree must exclude Node files")
        for path in edit_code:
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except SyntaxError as exc:
                raise ValidationError(f"topology: edit-site Python cannot parse: {path.relative_to(visible)}") from exc
            for statement in tree.body:
                modules = []
                if isinstance(statement, ast.Import):
                    modules = [alias.name for alias in statement.names]
                elif isinstance(statement, ast.ImportFrom):
                    modules = [statement.module] if statement.module else []
                for module in modules:
                    if module and module.split(".", 1)[0] not in sys.stdlib_module_names and not visible_local_module(visible, module):
                        raise ValidationError(f"topology: edit-site Python imports non-stdlib non-local module {module!r}")
    elif not edit_code or any(path.suffix not in {".js", ".mjs", ".cjs"} for path in edit_code):
        raise ValidationError("topology: even task edit site must contain only Node code")
    elif not any(path.name == "package.json" for path in paths) or any(path.suffix == ".py" for path in paths):
        raise ValidationError("topology: even task visible tree requires package.json and excludes Python")
    artifacts = [visible_file(task_dir, item, "contract artifact") for item in task["contract_artifacts"]]
    for artifact in artifacts:
        if directory_distance(edit_site, artifact.parent) < 2:
            raise ValidationError("topology: contract artifact directory distance must be at least 2")
    contract_a = token_set(task["contract_tokens_a"], "contract_tokens_a", 3)
    contract_b = token_set(task["contract_tokens_b"], "contract_tokens_b", 3)
    artifact_text = [path.read_text(encoding="utf-8") for path in artifacts]
    for tokens, content, label in ((contract_a, artifact_text[0], "a"), (contract_b, artifact_text[1], "b")):
        if not all(has_token(content, token) for token in tokens):
            raise ValidationError(f"topology: contract token set {label} is absent from its artifact")
    edit_parts = [path.relative_to(visible).as_posix() for path in paths if is_under(path, edit_site)]
    edit_text = "\n".join(path.read_text(encoding="utf-8") for path in paths if is_under(path, edit_site))
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


def is_under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def visible_local_module(visible: Path, module: str) -> bool:
    location = visible.joinpath(*module.split("."))
    return location.with_suffix(".py").is_file() or (location / "__init__.py").is_file()


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
        leakage_and_topology(task_dir, task, paths, edit_site, entries)
        complementarity(task_dir, task)
        vectors(task_dir, entries, self_test)
        return task, []
    except (OSError, UnicodeDecodeError, subprocess.SubprocessError, ValidationError) as exc:
        return None, [one_line(exc)]


def patch(before: str, after: str, path: str) -> str:
    return "".join(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True), f"a/{path}", f"b/{path}"))


def write_fixture(root: Path, identifier: str) -> None:
    """Write the smallest legal fixture used solely by --self-test."""
    visible, hidden, patches = root / "visible", root / "hidden", root / "patches"
    for directory in (visible / "edit", visible / "contracts", visible / "guides", visible / "support", hidden, patches):
        directory.mkdir(parents=True, exist_ok=True)
    is_node = task_index(identifier) % 2 == 0
    engine_name = "engine.js" if is_node else "engine.py"
    base, symptom, gold = "STATE = 0\n", "STATE = 1\n", "STATE = 2\n"
    (visible / "edit" / engine_name).write_text(base, encoding="utf-8")
    alpha = "azurine bellwether cinderly outcomea sparkone sparktwo\n"
    beta = "dovetail emberline farsight outcomeb sparkthree\n"
    (visible / "contracts" / "alpha.md").write_text(alpha, encoding="utf-8")
    (visible / "guides" / "beta.md").write_text(beta, encoding="utf-8")
    for number in range(20):
        directory = (visible / "support") if number < 18 else (visible / "guides")
        (directory / f"record{number}.txt").write_text("ordinary support record " * 8 + "\n", encoding="utf-8")
    if is_node:
        (visible / "support" / "package.json").write_text('{"private":true}\n', encoding="utf-8")
    else:
        (visible / "support" / "runner.txt").write_text("python fixture helper\n", encoding="utf-8")
    artifacts = ["visible/contracts/alpha.md", "visible/guides/beta.md"]
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
    }
    (root / "task.json").write_text(json.dumps(task, indent=2) + "\n", encoding="utf-8")
    entries = [{"id": role, "class": task["class"], "invariant": invariant, "contract_bindings": bindings} for role in ROLES]
    (hidden / "manifests.json").write_text(json.dumps({"manifestations": entries}, indent=2) + "\n", encoding="utf-8")
    oracle = """import json, pathlib, sys
state = (pathlib.Path(sys.argv[1]) / 'edit' / '%s').read_text().strip()
level = int(state.split('=')[1])
print(json.dumps({'manifestations': [
 {'id':'local-a','passed':level >= 1}, {'id':'local-b','passed':level >= 1},
 {'id':'remote-a','passed':level >= 2}, {'id':'remote-b','passed':level >= 2}, {'id':'restore','passed':level >= 2}]}))
""" % engine_name
    (hidden / "oracle.py").write_text(oracle, encoding="utf-8")
    (patches / "gold.patch").write_text(patch(base, gold, f"edit/{engine_name}"), encoding="utf-8")
    (patches / "symptom.patch").write_text(patch(base, symptom, f"edit/{engine_name}"), encoding="utf-8")
    noop = (visible / "support" / "record0.txt").read_text(encoding="utf-8")
    (patches / "noop.patch").write_text(patch(noop, noop + "unchanged\n", "support/record0.txt"), encoding="utf-8")


def self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="discovery-validator-self-test-") as temporary:
        base = Path(temporary) / "EQ3P-UA1"
        write_fixture(base, "EQ3P-UA1")
        node = Path(temporary) / "EQ3-UA2"
        write_fixture(node, "EQ3-UA2")
        for name, root in (("valid-python", base), ("valid-node", node)):
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
            "divergent-bindings": lambda root: json_update(root / "hidden" / "manifests.json", lambda data: data["manifestations"][1]["contract_bindings"].reverse()),
            "goal-token-leakage": lambda root: json_update(root / "task.json", lambda data: data.update({"goal": "azurine leaked"})),
            "oracle-non-json": lambda root: (root / "hidden" / "oracle.py").write_text("print('not json')\n", encoding="utf-8"),
            "oracle-nonzero": lambda root: (root / "hidden" / "oracle.py").write_text("raise SystemExit(2)\n", encoding="utf-8"),
            "patch-apply": lambda root: (root / "patches" / "gold.patch").write_text("bad patch\n", encoding="utf-8"),
            "file-count": lambda root: remove_files(root),
            "modules": lambda root: collapse_module(root),
            "distance": lambda root: move_artifact_near_edit(root),
            "byte-share": lambda root: (root / "visible" / "edit" / "engine.py").write_text("STATE = 0\n" * 10000, encoding="utf-8"),
            "language-parity": lambda root: rename_engine(root),
            "language-decoy": lambda root: language_decoy(root),
            "third-party-import": lambda root: (root / "visible" / "edit" / "engine.py").write_text("import requests\nSTATE = 0\n", encoding="utf-8"),
            "even-python-leak": lambda root: even_python_leak(root),
            "token-path-scan": lambda root: rename_token_path(root),
            "symptom-locality": lambda root: (root / "patches" / "symptom.patch").write_text(patch("x\n", "y\n", "support/record0.txt"), encoding="utf-8"),
            "artifact-role-order": lambda root: json_update(root / "hidden" / "manifests.json", lambda data: data["manifestations"].__setitem__(2, {**data["manifestations"][2], "id": "remote-b"})),
            "oracle-mutation": lambda root: (root / "hidden" / "oracle.py").write_text("import pathlib,sys,json\np=pathlib.Path(sys.argv[1]);(p/'changed').write_text('x');print(json.dumps({'manifestations':[{'id':x,'passed':False} for x in ['local-a','local-b','remote-a','remote-b','restore']]}))\n", encoding="utf-8"),
            "complementarity": lambda root: defeat_complementarity(root),
        }
        language_diagnostics = {
            "language-decoy": "odd task edit site must contain only Python code",
            "third-party-import": "imports non-stdlib non-local module",
            "even-python-leak": "even task visible tree requires package.json and excludes Python",
        }
        for name, change in scenarios.items():
            source = node if name == "even-python-leak" else base
            root = Path(temporary) / name / source.name
            shutil.copytree(source, root)
            change(root)
            _, errors = validate(root, self_test=True)
            if not errors:
                raise AssertionError(f"{name}: expected a fail-closed diagnostic")
            if name in language_diagnostics and not any(language_diagnostics[name] in error for error in errors):
                raise AssertionError(f"{name}: expected language diagnostic, got {errors}")
        # Vector failures exercise the individual gold, symptom, pristine, and noop clauses.
        for name, replacement in (("gold-vector", "level >= 3"), ("symptom-vector", "level >= 0"), ("pristine-vector", "level >= 0"), ("noop-vector", "level >= 0")):
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


def json_update(path: Path, update: object) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not callable(update):
        raise TypeError("json update must be callable")
    update(data)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def move_artifact_near_edit(root: Path) -> None:
    source, target = root / "visible" / "contracts" / "alpha.md", root / "visible" / "edit" / "alpha.md"
    source.rename(target)
    json_update(root / "task.json", lambda data: data["contract_artifacts"].__setitem__(0, "visible/edit/alpha.md"))
    json_update(root / "hidden" / "manifests.json", lambda data: [entry["contract_bindings"][0].update({"file": "visible/edit/alpha.md", "sha256": sha256(target)}) for entry in data["manifestations"]])


def task_index(identifier: str) -> int:
    match = re.search(r"(\d+)$", identifier)
    if match is None:
        raise ValueError(f"registered id lacks an index: {identifier}")
    return int(match.group(1))


def refresh_files(root: Path) -> None:
    json_update(root / "task.json", lambda data: data.update({"visible_files": sorted(
        path.relative_to(root).as_posix() for path in (root / "visible").rglob("*") if path.is_file()
    )}))


def make_symlink(root: Path) -> None:
    (root / "visible" / "support" / "link.txt").symlink_to("record0.txt")
    refresh_files(root)


def remove_files(root: Path) -> None:
    for path in sorted((root / "visible" / "support").glob("record*.txt"))[:2]:
        path.unlink()
    refresh_files(root)


def collapse_module(root: Path) -> None:
    destination = root / "visible" / "guides"
    for path in (root / "visible" / "support").iterdir():
        if path.is_file():
            path.rename(destination / path.name)
    refresh_files(root)


def rename_engine(root: Path) -> None:
    (root / "visible" / "edit" / "engine.py").rename(root / "visible" / "edit" / "engine.txt")
    refresh_files(root)


def language_decoy(root: Path) -> None:
    (root / "visible" / "edit" / "engine.py").rename(root / "visible" / "edit" / "engine.js")
    (root / "visible" / "support" / "decoy.py").write_text("STATE = 0\n", encoding="utf-8")
    refresh_files(root)


def even_python_leak(root: Path) -> None:
    (root / "visible" / "support" / "stray.py").write_text("STATE = 0\n", encoding="utf-8")
    refresh_files(root)


def rename_token_path(root: Path) -> None:
    (root / "visible" / "edit" / "engine.py").rename(root / "visible" / "edit" / "azurine.py")
    refresh_files(root)


def defeat_complementarity(root: Path) -> None:
    alpha = root / "visible" / "contracts" / "alpha.md"
    alpha.write_text(alpha.read_text(encoding="utf-8") + "outcomeb sparkthree\n", encoding="utf-8")
    json_update(root / "hidden" / "manifests.json", lambda data: [
        entry["contract_bindings"][0].update({"sha256": sha256(alpha)}) for entry in data["manifestations"]
    ])


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
