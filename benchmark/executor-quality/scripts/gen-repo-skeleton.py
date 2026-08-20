#!/usr/bin/env python3
"""Generate deterministic non-treatment repository mass for an EQ4 task fixture.

Usage:
    gen-repo-skeleton.py --params PARAMS.json --out TASK_DIR
    gen-repo-skeleton.py --self-test

``PARAMS.json`` must be a JSON object with exactly these fields (no unknown
or omitted fields):

* ``task_id``: non-empty string used with ``seed`` for SHA-256 choices.
* ``seed``: non-negative integer used with ``task_id`` for SHA-256 choices.
* ``package_roots``: non-empty, distinct list of ASCII-safe relative
  directories below ``visible/``; each task supplies its own neutral roots.
* ``package_count``: positive integer number of package directories.
* ``modules_per_package``: positive integer number of ``.py`` modules in
  each package directory.
* ``module_bytes``: integer at least 256; each non-``__init__`` module is at
  least this many ASCII bytes of valid Python (the value is a minimum, not an
  exact size).
* ``data_file_count``: non-negative integer number of line-structured
  ``.txt`` files.
* ``data_file_bytes``: non-negative integer; when ``data_file_count`` is
  positive it must be at least 24, and each data file is at least this many
  ASCII bytes.
* ``edit_site_dir``: a safe, non-empty output-relative directory path.
* ``contract_artifacts``: exactly two distinct safe, non-empty
  output-relative file paths.
* ``decoy_artifacts``: a list of distinct safe, non-empty output-relative
  file paths.
* ``contract_paths``: exactly two non-empty node lists, one for each contract
  artifact. Every node is a safe, non-empty output-relative path.
* ``banned_tokens``: a list of distinct, case-insensitive whole-word tokens.

The output is a task-directory root. Files live beneath the supplied
``package_roots`` under ``visible/`` and ``generator-inventory.json`` lives at
the output root. The inventory is canonical compact JSON of the form
``{"files":[{"path":"...","sha256":"..."},...]}``; entries are sorted by
relative path and intentionally omit the inventory itself. Before any output
directory is created, the generator plans every byte in memory and refuses if
any planned file is under ``edit_site_dir``, equals a contract or decoy
artifact, is any contract-path node, contains a banned token under the
whole-word, case-folded semantics used by validate-discovery-task.py, or uses
a self-label in an emitted path or byte sequence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import py_compile
import re
import shutil
import sys
import tempfile
from pathlib import Path


TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)
SELF_LABEL_RE = re.compile(
    r"(?:generated|inert|filler|skeleton|padding|synthetic|placeholder)\w*",
    re.IGNORECASE,
)
NEUTRAL_WORDS = (
    "amber",
    "anchor",
    "apricot",
    "atlas",
    "birch",
    "cobalt",
    "copper",
    "delta",
    "elm",
    "ember",
    "falcon",
    "fern",
    "glacier",
    "harbor",
    "iris",
    "juniper",
    "keystone",
    "lagoon",
    "maple",
    "meadow",
    "meridian",
    "northstar",
    "onyx",
    "orbit",
    "pebble",
    "quartz",
    "raven",
    "river",
    "saffron",
    "spruce",
    "thistle",
    "topaz",
    "umbra",
    "valley",
    "willow",
    "zephyr",
)
PARAMETER_FIELDS = {
    "task_id",
    "seed",
    "package_roots",
    "package_count",
    "modules_per_package",
    "module_bytes",
    "data_file_count",
    "data_file_bytes",
    "edit_site_dir",
    "contract_artifacts",
    "decoy_artifacts",
    "contract_paths",
    "banned_tokens",
}
COMMON_PYTHON_IDIOM_LINES = frozenset({"from __future__ import annotations"})
DATA_RECORD_SHAPES = (
    "entry={name}; amount={value}; proof={digest}",
    "{name} | measure={value} | hash={digest}",
    "slot:{name} payload:{value} token:{digest}",
)


class GeneratorError(ValueError):
    """The requested repository mass cannot avoid a treatment surface."""


def canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def safe_relative(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise GeneratorError(f"{label}: must be a non-empty string")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value or value in {".", ""}:
        raise GeneratorError(f"{label}: unsafe relative path {value!r}")
    return value


def nonnegative_int(value: object, label: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise GeneratorError(f"{label}: must be an integer >= {minimum}")
    return value


def path_list(value: object, label: str, *, exactly: int | None = None) -> list[str]:
    if not isinstance(value, list) or (exactly is not None and len(value) != exactly):
        size = f"exactly {exactly}" if exactly is not None else "a list"
        raise GeneratorError(f"{label}: must be {size}")
    paths = [safe_relative(item, f"{label}[{index}]") for index, item in enumerate(value)]
    if len(set(paths)) != len(paths):
        raise GeneratorError(f"{label}: paths must be unique")
    return paths


def visible_package_roots(value: object) -> list[str]:
    roots = path_list(value, "package_roots")
    if not roots:
        raise GeneratorError("package_roots: must be a non-empty list")
    for index, root in enumerate(roots):
        parts = Path(root).parts
        if not root.isascii() or len(parts) < 2 or parts[0] != "visible":
            raise GeneratorError(f"package_roots[{index}]: must be an ASCII-safe directory below visible/")
    return roots


def validate_params(raw: object) -> dict[str, object]:
    if not isinstance(raw, dict) or set(raw) != PARAMETER_FIELDS:
        missing = sorted(PARAMETER_FIELDS - set(raw)) if isinstance(raw, dict) else sorted(PARAMETER_FIELDS)
        extra = sorted(set(raw) - PARAMETER_FIELDS) if isinstance(raw, dict) else []
        raise GeneratorError(f"params: fields must exactly match schema; missing={missing}, extra={extra}")

    task_id = raw["task_id"]
    if not isinstance(task_id, str) or not task_id.strip():
        raise GeneratorError("task_id: must be a non-empty string")
    seed = nonnegative_int(raw["seed"], "seed")
    package_roots = visible_package_roots(raw["package_roots"])
    package_count = nonnegative_int(raw["package_count"], "package_count", 1)
    modules_per_package = nonnegative_int(raw["modules_per_package"], "modules_per_package", 1)
    module_bytes = nonnegative_int(raw["module_bytes"], "module_bytes", 256)
    data_file_count = nonnegative_int(raw["data_file_count"], "data_file_count")
    data_file_bytes = nonnegative_int(raw["data_file_bytes"], "data_file_bytes")
    if data_file_count and data_file_bytes < 24:
        raise GeneratorError("data_file_bytes: must be >= 24 when data_file_count is positive")

    edit_site_dir = safe_relative(raw["edit_site_dir"], "edit_site_dir")
    contract_artifacts = path_list(raw["contract_artifacts"], "contract_artifacts", exactly=2)
    decoy_artifacts = path_list(raw["decoy_artifacts"], "decoy_artifacts")
    contract_paths_raw = raw["contract_paths"]
    if not isinstance(contract_paths_raw, list) or len(contract_paths_raw) != len(contract_artifacts):
        raise GeneratorError("contract_paths: must contain one non-empty node list per contract artifact")
    contract_paths: list[list[str]] = []
    for index, nodes in enumerate(contract_paths_raw):
        if not isinstance(nodes, list) or not nodes:
            raise GeneratorError(f"contract_paths[{index}]: must be a non-empty list")
        node_paths = [safe_relative(node, f"contract_paths[{index}][{node_index}]") for node_index, node in enumerate(nodes)]
        if len(set(node_paths)) != len(node_paths):
            raise GeneratorError(f"contract_paths[{index}]: nodes must be unique")
        contract_paths.append(node_paths)

    banned_tokens_raw = raw["banned_tokens"]
    if not isinstance(banned_tokens_raw, list):
        raise GeneratorError("banned_tokens: must be a list")
    banned_tokens: list[str] = []
    for index, token in enumerate(banned_tokens_raw):
        if not isinstance(token, str) or TOKEN_RE.fullmatch(token) is None:
            raise GeneratorError(f"banned_tokens[{index}]: must be one non-empty whole-word token")
        banned_tokens.append(token)
    if len({token.casefold() for token in banned_tokens}) != len(banned_tokens):
        raise GeneratorError("banned_tokens: tokens must be unique case-insensitively")

    return {
        "task_id": task_id,
        "seed": seed,
        "package_roots": package_roots,
        "package_count": package_count,
        "modules_per_package": modules_per_package,
        "module_bytes": module_bytes,
        "data_file_count": data_file_count,
        "data_file_bytes": data_file_bytes,
        "edit_site_dir": edit_site_dir,
        "contract_artifacts": contract_artifacts,
        "decoy_artifacts": decoy_artifacts,
        "contract_paths": contract_paths,
        "banned_tokens": banned_tokens,
    }


def choice_digest(task_id: str, seed: int, role: str, index: int) -> str:
    return sha256_bytes(canonical_json([task_id, seed, role, index]))


def name_for(task_id: str, seed: int, role: str, index: int) -> str:
    digest = choice_digest(task_id, seed, role, index)
    first = NEUTRAL_WORDS[int(digest[:8], 16) % len(NEUTRAL_WORDS)]
    second = NEUTRAL_WORDS[int(digest[8:16], 16) % len(NEUTRAL_WORDS)]
    return f"{first}_{second}_{digest[:16]}"


def root_for(task_id: str, seed: int, roots: list[str], role: str, index: int) -> str:
    digest = choice_digest(task_id, seed, role, index)
    return roots[int(digest[16:24], 16) % len(roots)]


def module_variant(task_id: str, seed: int, fingerprint: str, role: str, module_name: str) -> str:
    digest = sha256_bytes(canonical_json([task_id, seed, fingerprint, role, module_name]))
    first = NEUTRAL_WORDS[int(digest[:8], 16) % len(NEUTRAL_WORDS)]
    second = NEUTRAL_WORDS[int(digest[8:16], 16) % len(NEUTRAL_WORDS)]
    return f"{first}_{second}_{digest[:16]}"


def package_init_bytes(package_id: str) -> bytes:
    return f'"""Namespace for {package_id}."""\n'.encode("ascii")


def function_block(task_id: str, seed: int, module_name: str, index: int) -> list[str]:
    function_name = name_for(task_id, seed, f"function:{module_name}", index)
    function_prefix = name_for(task_id, seed, f"function-prefix:{module_name}", 0)
    key_name = name_for(task_id, seed, f"function-key:{module_name}", index)
    baseline_name = name_for(task_id, seed, f"function-baseline:{module_name}", index)
    digest = choice_digest(task_id, seed, f"value:{module_name}", index)
    value = int(digest[:8], 16) % 1_000_000
    return [
        f"def {function_prefix}_{function_name}(records: dict[str, int]) -> tuple[str, int]:",
        f"    {key_name} = {function_name!r}",
        f"    {baseline_name} = {value}",
        f"    return {key_name}, records.get({key_name}, {baseline_name})",
        "",
    ]


def module_content(task_id: str, seed: int, fingerprint: str, module_name: str, minimum: int) -> bytes:
    catalog_name = name_for(task_id, seed, f"catalog:{module_name}", 0)
    module_docstring = module_variant(task_id, seed, fingerprint, "module-docstring", module_name)
    catalog_symbol = module_variant(task_id, seed, fingerprint, "catalog-symbol", module_name).upper()
    lines = [
        f'"""{module_docstring}."""',
        "",
        "from __future__ import annotations",
        "",
        f"{catalog_symbol} = {{",
        f"    {catalog_name!r}: {int(choice_digest(task_id, seed, 'catalog-value', 0)[:8], 16) % 1_000_000},",
        "}",
        "",
    ]
    index = 0
    while len(("\n".join(lines) + "\n").encode("ascii")) < minimum:
        lines.extend(function_block(task_id, seed, module_name, index))
        index += 1
    return ("\n".join(lines) + "\n").encode("ascii")


def data_content(task_id: str, seed: int, index: int, minimum: int) -> bytes:
    lines: list[str] = []
    record = 0
    while len(("\n".join(lines) + "\n").encode("ascii")) < minimum:
        record_name = name_for(task_id, seed, f"record:{index}", record)
        digest = choice_digest(task_id, seed, f"record-value:{index}", record)
        shape = DATA_RECORD_SHAPES[int(digest[20:28], 16) % len(DATA_RECORD_SHAPES)]
        lines.append(shape.format(
            name=record_name,
            value=int(digest[:8], 16) % 1_000_000,
            digest=digest[:20],
        ))
        record += 1
    return ("\n".join(lines) + "\n").encode("ascii")


def under(path: str, directory: str) -> bool:
    path_parts = Path(path).parts
    directory_parts = Path(directory).parts
    return path_parts[:len(directory_parts)] == directory_parts


def contains_token(content: bytes, token: str) -> bool:
    words = {word.casefold() for word in TOKEN_RE.findall(content.decode("ascii"))}
    return token.casefold() in words


def contains_self_label(value: str) -> bool:
    return SELF_LABEL_RE.search(value) is not None


def plan_files(params: dict[str, object]) -> list[tuple[str, bytes]]:
    fingerprint = sha256_bytes(canonical_json(params))
    task_id = str(params["task_id"])
    seed = int(params["seed"])
    package_roots = list(params["package_roots"])
    package_count = int(params["package_count"])
    modules_per_package = int(params["modules_per_package"])
    requested_module_bytes = int(params["module_bytes"])
    data_file_count = int(params["data_file_count"])
    requested_data_bytes = int(params["data_file_bytes"])
    files: list[tuple[str, bytes]] = [
        (f"{root}/__init__.py", package_init_bytes(root)) for root in package_roots
    ]

    for package_index in range(package_count):
        root = root_for(task_id, seed, package_roots, "package-root", package_index)
        package_name = name_for(task_id, seed, "package", package_index)
        package_dir = f"{root}/{package_name}"
        files.append((f"{package_dir}/__init__.py", package_init_bytes(package_dir)))
        for module_index in range(modules_per_package):
            absolute_index = package_index * modules_per_package + module_index
            module_name = name_for(task_id, seed, "module", absolute_index)
            files.append((
                f"{package_dir}/{module_name}.py",
                module_content(task_id, seed, fingerprint, module_name, requested_module_bytes),
            ))
    for data_index in range(data_file_count):
        root = root_for(task_id, seed, package_roots, "data-root", data_index)
        data_name = name_for(task_id, seed, "data", data_index)
        files.append((
            f"{root}/records/{data_name}.txt",
            data_content(task_id, seed, data_index, requested_data_bytes),
        ))

    files.sort(key=lambda item: item[0])
    inventory = canonical_json({"files": [
        {"path": path, "sha256": sha256_bytes(content)} for path, content in files
    ]})
    files.append(("generator-inventory.json", inventory))
    return files


def validate_plan(params: dict[str, object], files: list[tuple[str, bytes]]) -> None:
    paths = [path for path, _ in files]
    if len(set(paths)) != len(paths):
        raise GeneratorError("planned output paths are not unique")
    excluded = set(params["contract_artifacts"]) | set(params["decoy_artifacts"])
    excluded.update(node for path in params["contract_paths"] for node in path)
    edit_site_dir = str(params["edit_site_dir"])
    for path, content in files:
        if under(path, edit_site_dir) or path in excluded:
            raise GeneratorError(f"refusing treatment-bearing output path: {path}")
        if not path.isascii() or contains_self_label(path):
            raise GeneratorError(f"refusing self-label output path: {path}")
        try:
            text = content.decode("ascii")
        except UnicodeDecodeError as exc:
            raise GeneratorError(f"refusing non-ASCII output bytes: {path}") from exc
        if contains_self_label(text):
            raise GeneratorError(f"refusing self-label output bytes: {path}")
        for token in params["banned_tokens"]:
            if contains_token(content, token):
                raise GeneratorError(f"refusing banned token {token!r} in planned file: {path}")


def write_files(files: list[tuple[str, bytes]], out_dir: Path, fingerprint: str) -> None:
    if out_dir.exists() or out_dir.is_symlink():
        raise GeneratorError(f"out: path already exists: {out_dir}")
    if not out_dir.parent.is_dir() or out_dir.parent.is_symlink():
        raise GeneratorError(f"out: parent must be a real directory: {out_dir.parent}")
    staging = out_dir.parent / f".{out_dir.name}.stage-{fingerprint}"
    if staging.exists() or staging.is_symlink():
        raise GeneratorError(f"out: deterministic staging path already exists: {staging}")
    try:
        staging.mkdir()
        for path, content in files:
            destination = staging / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
        os.replace(staging, out_dir)
    except OSError as exc:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
        raise GeneratorError(f"out: write failed: {exc}") from exc


def generate(raw_params: object, out_dir: Path) -> None:
    params = validate_params(raw_params)
    files = plan_files(params)
    validate_plan(params, files)
    write_files(files, out_dir, sha256_bytes(canonical_json(params)))


def load_params(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GeneratorError(f"params: cannot read JSON: {exc}") from exc


def sample_params() -> dict[str, object]:
    return {
        "task_id": "EQ4-SELFTEST",
        "seed": 105,
        "package_roots": ["visible/amber", "visible/cobalt"],
        "package_count": 12,
        "modules_per_package": 10,
        "module_bytes": 16_000,
        "data_file_count": 4,
        "data_file_bytes": 25_000,
        "edit_site_dir": "visible/treatment/engine",
        "contract_artifacts": [
            "visible/contracts/consumer.py",
            "visible/tests/system/test_contract.py",
        ],
        "decoy_artifacts": ["visible/treatment/decoys/decoy_00.py"],
        "contract_paths": [
            [
                "visible/treatment/engine/adapter.py",
                "visible/domain/service.py",
                "visible/contracts/consumer.py",
            ],
            [
                "visible/treatment/engine/adapter.py",
                "visible/domain/service.py",
                "visible/tests/system/test_contract.py",
            ],
        ],
        "banned_tokens": ["forbidden"],
    }


def tree_bytes(root: Path) -> list[tuple[str, bytes]]:
    return sorted(
        (path.relative_to(root).as_posix(), path.read_bytes())
        for path in root.rglob("*")
        if path.is_file()
    )


def verify_inventory(root: Path) -> None:
    raw = json.loads((root / "generator-inventory.json").read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or set(raw) != {"files"} or not isinstance(raw["files"], list):
        raise GeneratorError("self-test: inventory schema is invalid")
    listed = raw["files"]
    expected_paths = sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name != "generator-inventory.json"
    )
    listed_paths = [entry.get("path") if isinstance(entry, dict) else None for entry in listed]
    if listed_paths != expected_paths:
        raise GeneratorError("self-test: inventory is incomplete or unsorted")
    for entry in listed:
        if set(entry) != {"path", "sha256"}:
            raise GeneratorError("self-test: inventory entry schema is invalid")
        content = (root / entry["path"]).read_bytes()
        if hashlib.sha256(content).hexdigest() != entry["sha256"]:
            raise GeneratorError(f"self-test: inventory digest mismatch for {entry['path']}")


def expect_refusal(params: dict[str, object], out_dir: Path) -> None:
    try:
        generate(params, out_dir)
    except GeneratorError:
        if out_dir.exists() or out_dir.is_symlink():
            raise GeneratorError("self-test: refusal touched the output directory")
        return
    raise GeneratorError("self-test: expected refusal did not fire")


def visible_regular_files(root: Path) -> list[Path]:
    visible = root / "visible"
    return sorted(path for path in visible.rglob("*") if path.is_file() and not path.is_symlink())


def verify_shared_exact_lines(root: Path) -> None:
    modules = [
        path for path in visible_regular_files(root)
        if path.suffix == ".py" and path.name != "__init__.py"
    ]
    if not modules:
        raise GeneratorError("self-test: expected generated non-__init__ Python modules")
    occurrences: dict[str, int] = {}
    for path in modules:
        lines = {
            line.strip() for line in path.read_text(encoding="ascii").splitlines()
            if len(line.strip()) >= 8
        }
        for line in lines:
            occurrences[line] = occurrences.get(line, 0) + 1
    shared = sorted(
        line for line, count in occurrences.items()
        if count * 2 >= len(modules) and line not in COMMON_PYTHON_IDIOM_LINES
    )
    if shared:
        raise GeneratorError(f"self-test: shared exact marker lines: {shared!r}")


def self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="gen-repo-skeleton-") as temporary:
        root = Path(temporary)
        params = sample_params()
        first_parent = root / "first"
        second_parent = root / "second"
        first_parent.mkdir()
        second_parent.mkdir()
        first = first_parent / "task"
        second = second_parent / "task"
        generate(params, first)
        generate(params, second)
        if tree_bytes(first) != tree_bytes(second):
            raise GeneratorError("self-test: identical params produced different trees")
        print("SELF-TEST determinism: PASS")

        exclusion = dict(params)
        exclusion["edit_site_dir"] = str(params["package_roots"][0])
        expect_refusal(exclusion, root / "refusal-edit-directory")
        print("SELF-TEST edit-directory refusal / untouched out: PASS")

        collision = dict(params)
        planned_visible_path = next(path for path, _ in plan_files(validate_params(params)) if path.startswith("visible/"))
        collision["contract_artifacts"] = [planned_visible_path, params["contract_artifacts"][1]]
        expect_refusal(collision, root / "refusal-contract-collision")
        print("SELF-TEST contract-artifact collision / untouched out: PASS")

        banned = dict(params)
        banned["banned_tokens"] = ["namespace"]
        expect_refusal(banned, root / "refusal-banned")
        print("SELF-TEST banned-token refusal / untouched out: PASS")

        verify_inventory(first)
        print("SELF-TEST inventory completeness + digest: PASS")

        verify_shared_exact_lines(first)
        print("SELF-TEST shared exact-marker law: PASS")

        visible_files = visible_regular_files(first)
        visible_bytes = sum(path.stat().st_size for path in visible_files)
        if len(visible_files) < 120 or visible_bytes < 2_000_000:
            raise GeneratorError(
                f"self-test: visible mass target missed ({len(visible_files)} files, {visible_bytes} bytes)"
            )
        print(
            "SELF-TEST visible mass reachability: PASS "
            f"(visible files={len(visible_files)}, visible bytes={visible_bytes})"
        )

        compiled = root / "compiled"
        compiled.mkdir()
        for path in visible_files:
            if path.suffix == ".py":
                cfile = compiled / f"{sha256_bytes(path.read_bytes())}.pyc"
                py_compile.compile(str(path), cfile=str(cfile), doraise=True)
        print("SELF-TEST Python compilation: PASS")
    print("SELF-TEST: PASS")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--params", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        if args.params is not None or args.out is not None:
            parser.error("--self-test cannot be combined with --params or --out")
    elif args.params is None or args.out is None:
        parser.error("--params and --out are required unless --self-test is used")
    return args


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        if args.self_test:
            self_test()
        else:
            generate(load_params(args.params), args.out)
            print(f"GENERATED: {args.out}")
    except GeneratorError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
