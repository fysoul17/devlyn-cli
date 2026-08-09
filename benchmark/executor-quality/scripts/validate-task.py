#!/usr/bin/env python3
"""Validate one executor-quality task fixture or exercise the gate itself."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


CLASSES = {
    "unsupported_assumption",
    "missed_repo_invariant",
    "broken_dependency",
    "absent_failure_mode",
}
TASK_FIELDS = {"id", "class", "invariant", "goal", "visible_files", "contract_excerpt"}
BINDING_FIELDS = {"file", "sha256", "quote"}
MANIFEST_FIELDS = {"id", "invariant", "class", "contract_excerpt"}
GENERIC_ORACLE_LITERALS = {
    "manifestations",
    "invariant",
    "passed",
    "true",
    "false",
    "python3",
}


class ValidationError(ValueError):
    """A named fixture contract failed."""


class ExitOneParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        print(f"ARGUMENT: {message}", file=sys.stderr)
        raise SystemExit(1)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def one_line(value: object) -> str:
    return " ".join(str(value).split())


def load_json(path: Path, label: str) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"{label}: cannot read JSON: {exc}") from exc


def safe_visible_file(task_dir: Path, relative: object, label: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise ValidationError(f"{label}: file must be a non-empty string")
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts or rel.as_posix() != relative:
        raise ValidationError(f"{label}: unsafe path {relative!r}")
    if not rel.parts or rel.parts[0] != "visible":
        raise ValidationError(f"{label}: path must be under visible/: {relative}")
    candidate = task_dir / rel
    if candidate.is_symlink() or not candidate.is_file():
        raise ValidationError(f"{label}: visible file is missing or not regular: {relative}")
    try:
        candidate.resolve().relative_to((task_dir / "visible").resolve())
    except ValueError as exc:
        raise ValidationError(f"{label}: path escapes visible/: {relative}") from exc
    return candidate


def validate_binding(task_dir: Path, value: object, label: str) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != BINDING_FIELDS:
        raise ValidationError(f"{label}: binding must contain exactly file, sha256, quote")
    path = safe_visible_file(task_dir, value["file"], label)
    expected = value["sha256"]
    if not isinstance(expected, str) or re.fullmatch(r"[0-9a-f]{64}", expected) is None:
        raise ValidationError(f"{label}: sha256 must be 64 lowercase hex characters")
    actual = sha256_file(path)
    if actual != expected:
        raise ValidationError(f"{label}: sha256 mismatch for {value['file']}")
    quote = value["quote"]
    if not isinstance(quote, str) or not quote:
        raise ValidationError(f"{label}: quote must be a non-empty string")
    try:
        contents = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError(f"{label}: bound file is not UTF-8: {value['file']}") from exc
    if quote not in contents:
        raise ValidationError(f"{label}: quote is absent from {value['file']}")
    return {key: str(value[key]) for key in BINDING_FIELDS}


def structural_checks(task_dir: Path) -> tuple[dict[str, object], list[Path]]:
    required_files = [
        task_dir / "task.json",
        task_dir / "hidden" / "oracle.py",
        task_dir / "hidden" / "manifests.json",
        task_dir / "patches" / "gold.patch",
        task_dir / "patches" / "symptom.patch",
        task_dir / "patches" / "noop.patch",
    ]
    missing = [str(path.relative_to(task_dir)) for path in required_files if not path.is_file()]
    if missing:
        raise ValidationError(f"required files missing: {', '.join(missing)}")
    raw = load_json(task_dir / "task.json", "task.json")
    if not isinstance(raw, dict) or set(raw) != TASK_FIELDS:
        raise ValidationError(
            "task.json: fields must be exactly id, class, invariant, goal, "
            "visible_files, contract_excerpt"
        )
    for key in ("id", "invariant", "goal"):
        if not isinstance(raw[key], str) or not raw[key].strip():
            raise ValidationError(f"task.json: {key} must be a non-empty string")
    if raw["class"] not in CLASSES:
        raise ValidationError(f"task.json: class must be one of {sorted(CLASSES)}")
    visible_files = raw["visible_files"]
    if not isinstance(visible_files, list) or not 5 <= len(visible_files) <= 15:
        raise ValidationError("task.json: visible_files must contain 5-15 paths")
    if any(not isinstance(value, str) for value in visible_files) or len(set(visible_files)) != len(visible_files):
        raise ValidationError("task.json: visible_files must be unique strings")
    paths = [safe_visible_file(task_dir, value, "task.json visible_files") for value in visible_files]
    actual_visible = sorted(
        path.relative_to(task_dir).as_posix()
        for path in (task_dir / "visible").rglob("*")
        if path.is_file() and not path.is_symlink()
    )
    if sorted(visible_files) != actual_visible:
        raise ValidationError("task.json: visible_files must list every regular file under visible/")
    validate_binding(task_dir, raw["contract_excerpt"], "task.json contract_excerpt")
    return raw, paths


def load_manifests(task_dir: Path, task: dict[str, object]) -> list[dict[str, object]]:
    raw = load_json(task_dir / "hidden" / "manifests.json", "manifests.json")
    if not isinstance(raw, dict) or set(raw) != {"manifestations"}:
        raise ValidationError("manifests.json: root must contain exactly manifestations")
    manifestations = raw["manifestations"]
    if not isinstance(manifestations, list) or len(manifestations) < 2:
        raise ValidationError("manifests.json: manifestations must contain at least two entries")
    seen: set[str] = set()
    for index, item in enumerate(manifestations):
        label = f"manifests.json manifestation[{index}]"
        if not isinstance(item, dict) or set(item) != MANIFEST_FIELDS:
            raise ValidationError(f"{label}: fields must be exactly id, invariant, class, contract_excerpt")
        identifier = item["id"]
        if not isinstance(identifier, str) or not identifier or identifier in seen:
            raise ValidationError(f"{label}: id must be a unique non-empty string")
        seen.add(identifier)
        if item["invariant"] != task["invariant"]:
            raise ValidationError(f"{label}: invariant does not match task.json")
        if item["class"] != task["class"]:
            raise ValidationError(f"{label}: class does not match task.json")
        validate_binding(task_dir, item["contract_excerpt"], f"{label} contract_excerpt")
    return manifestations


def oracle_assertion_literals(oracle_path: Path) -> set[str]:
    try:
        tree = ast.parse(oracle_path.read_text(encoding="utf-8"), filename=str(oracle_path))
    except (OSError, UnicodeDecodeError, SyntaxError) as exc:
        raise ValidationError(f"oracle.py: cannot parse for leakage scan: {exc}") from exc
    literals: set[str] = set()
    candidate_roots: list[ast.AST] = [node.test for node in ast.walk(tree) if isinstance(node, ast.Assert)]
    candidate_roots.extend(node for node in ast.walk(tree) if isinstance(node, ast.Compare))
    for root in candidate_roots:
        for node in ast.walk(root):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                value = node.value.strip()
                if len(value) >= 12 and value.lower() not in GENERIC_ORACLE_LITERALS:
                    literals.add(value)
    return literals


def conformance_checks(
    task_dir: Path, task: dict[str, object], visible_paths: list[Path]
) -> list[dict[str, object]]:
    manifests = load_manifests(task_dir, task)
    tokens = {str(item["id"]) for item in manifests}
    tokens.update(
        path.stem
        for path in (task_dir / "hidden").rglob("*")
        if path.is_file() and len(path.stem) >= 4
    )
    tokens.update(oracle_assertion_literals(task_dir / "hidden" / "oracle.py"))
    for path in visible_paths:
        relative = path.relative_to(task_dir / "visible").as_posix()
        try:
            contents = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ValidationError(f"leakage: visible file is not UTF-8: visible/{relative}") from exc
        haystack = f"{relative}\n{contents}".lower()
        leaked = sorted(token for token in tokens if token.lower() in haystack)
        if leaked:
            raise ValidationError(f"leakage: visible/{relative} contains hidden token {leaked[0]!r}")
    return manifests


def run_oracle(task_dir: Path, workdir: Path, manifests: list[dict[str, object]]) -> list[dict[str, object]]:
    completed = subprocess.run(
        [sys.executable, str(task_dir / "hidden" / "oracle.py"), str(workdir)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    if completed.returncode != 0:
        detail = one_line(completed.stderr or completed.stdout or f"exit {completed.returncode}")
        raise ValidationError(f"oracle execution failed: {detail}")
    try:
        output = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"oracle output is not one JSON object: {exc}") from exc
    if not isinstance(output, dict) or set(output) != {"manifestations"}:
        raise ValidationError("oracle output root must contain exactly manifestations")
    results = output["manifestations"]
    if not isinstance(results, list) or len(results) != len(manifests):
        raise ValidationError("oracle output manifestation count differs from manifests.json")
    expected = {(item["id"], item["invariant"]) for item in manifests}
    actual: set[tuple[object, object]] = set()
    for index, result in enumerate(results):
        if not isinstance(result, dict) or set(result) != {"id", "invariant", "passed"}:
            raise ValidationError(f"oracle manifestation[{index}] has invalid fields")
        if not isinstance(result["passed"], bool):
            raise ValidationError(f"oracle manifestation[{index}].passed must be boolean")
        actual.add((result["id"], result["invariant"]))
    if actual != expected or len(actual) != len(results):
        raise ValidationError("oracle manifestations do not match manifests.json")
    return results


def apply_patch(task_dir: Path, workdir: Path, name: str) -> None:
    executable = shutil.which("patch")
    if executable is None:
        raise ValidationError("patch utility is unavailable")
    completed = subprocess.run(
        [executable, "-p1", "--forward", "--batch", "-i", str(task_dir / "patches" / name)],
        cwd=workdir,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    if completed.returncode != 0:
        detail = one_line(completed.stderr or completed.stdout or f"exit {completed.returncode}")
        raise ValidationError(f"patch application failed for {name}: {detail}")


def smoke_case(
    task_dir: Path,
    manifests: list[dict[str, object]],
    patch_name: str | None,
) -> list[dict[str, object]]:
    with tempfile.TemporaryDirectory(prefix="executor-quality-smoke-") as temporary:
        workdir = Path(temporary) / "visible"
        shutil.copytree(task_dir / "visible", workdir)
        if patch_name is not None:
            apply_patch(task_dir, workdir, patch_name)
        return run_oracle(task_dir, workdir, manifests)


def smoke_checks(task_dir: Path, manifests: list[dict[str, object]]) -> None:
    cases = {
        "no_patch": smoke_case(task_dir, manifests, None),
        "noop.patch": smoke_case(task_dir, manifests, "noop.patch"),
        "gold.patch": smoke_case(task_dir, manifests, "gold.patch"),
        "symptom.patch": smoke_case(task_dir, manifests, "symptom.patch"),
    }
    if all(result["passed"] for result in cases["no_patch"]):
        raise ValidationError("no patch unexpectedly passes all manifestations")
    if all(result["passed"] for result in cases["noop.patch"]):
        raise ValidationError("noop.patch unexpectedly passes all manifestations")
    if not all(result["passed"] for result in cases["gold.patch"]):
        raise ValidationError("gold.patch does not pass all manifestations")
    symptom = cases["symptom.patch"]
    if not any(result["passed"] for result in symptom) or not any(not result["passed"] for result in symptom):
        raise ValidationError("symptom.patch must pass at least one and fail at least one manifestation")


def validate_task(task_dir: Path) -> list[str]:
    errors: list[str] = []
    try:
        task, visible_paths = structural_checks(task_dir)
    except (OSError, ValidationError) as exc:
        return [f"STRUCTURAL: {one_line(exc)}"]
    try:
        manifests = conformance_checks(task_dir, task, visible_paths)
    except (OSError, ValidationError) as exc:
        return [f"CONFORMANCE: {one_line(exc)}"]
    try:
        smoke_checks(task_dir, manifests)
    except (OSError, subprocess.SubprocessError, ValidationError) as exc:
        errors.append(f"SMOKE: {one_line(exc)}")
    return errors


def unified_patch(before: str, after: str, path: str) -> str:
    import difflib

    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
    )


def write_synthetic_task(root: Path) -> None:
    visible = root / "visible"
    hidden = root / "hidden"
    patches = root / "patches"
    visible.mkdir(parents=True)
    hidden.mkdir()
    patches.mkdir()
    contract = "Both primary and secondary requests are accepted.\n"
    base_engine = '"""Request classifier."""\n\n\ndef classify(value):\n    return "rejected"\n'
    symptom_engine = (
        '"""Request classifier."""\n\n\ndef classify(value):\n'
        '    return "accepted" if value == "primary" else "rejected"\n'
    )
    gold_engine = (
        '"""Request classifier."""\n\n\ndef classify(value):\n'
        '    return "accepted" if value in {"primary", "secondary"} else "rejected"\n'
    )
    files = {
        "contract.md": contract,
        "engine.py": base_engine,
        "README.md": "Run `python3 test_engine.py`.\n",
        "test_engine.py": "from engine import classify\nassert classify('unknown') == 'rejected'\n",
        "config.json": '{"mode":"strict"}\n',
    }
    for name, contents in files.items():
        (visible / name).write_text(contents, encoding="utf-8")
    invariant = "Every supported request kind is accepted."
    contract_binding = {
        "file": "visible/contract.md",
        "sha256": sha256_file(visible / "contract.md"),
        "quote": contract.strip(),
    }
    task = {
        "id": "SYNTHETIC",
        "class": "unsupported_assumption",
        "invariant": invariant,
        "goal": "Make the classifier satisfy its visible contract. Run python3 test_engine.py.",
        "visible_files": [f"visible/{name}" for name in sorted(files)],
        "contract_excerpt": contract_binding,
    }
    (root / "task.json").write_text(json.dumps(task, indent=2) + "\n", encoding="utf-8")
    manifest_entries = [
        {
            "id": identifier,
            "invariant": invariant,
            "class": "unsupported_assumption",
            "contract_excerpt": contract_binding,
        }
        for identifier in ("primary-path", "secondary-path")
    ]
    (hidden / "manifests.json").write_text(
        json.dumps({"manifestations": manifest_entries}, indent=2) + "\n", encoding="utf-8"
    )
    oracle = f'''#!/usr/bin/env python3
import importlib.util
import json
import pathlib
import sys

assert "ORACLE_ONLY_SENTINEL" != ""
workdir = pathlib.Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("fixture_engine", workdir / "engine.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
invariant = {invariant!r}
print(json.dumps({{"manifestations": [
    {{"id": "primary-path", "invariant": invariant, "passed": module.classify("primary") == "accepted"}},
    {{"id": "secondary-path", "invariant": invariant, "passed": module.classify("secondary") == "accepted"}},
]}}))
'''
    (hidden / "oracle.py").write_text(oracle, encoding="utf-8")
    (patches / "gold.patch").write_text(unified_patch(base_engine, gold_engine, "engine.py"), encoding="utf-8")
    (patches / "symptom.patch").write_text(
        unified_patch(base_engine, symptom_engine, "engine.py"), encoding="utf-8"
    )
    noop_after = base_engine.replace("Request classifier.", "Request classifier. No behavior change.")
    (patches / "noop.patch").write_text(unified_patch(base_engine, noop_after, "engine.py"), encoding="utf-8")


def refresh_visible_files(root: Path) -> None:
    task_path = root / "task.json"
    task = json.loads(task_path.read_text(encoding="utf-8"))
    task["visible_files"] = sorted(
        path.relative_to(root).as_posix() for path in (root / "visible").rglob("*") if path.is_file()
    )
    task_path.write_text(json.dumps(task, indent=2) + "\n", encoding="utf-8")


def expect_failure(root: Path, expected: str) -> None:
    errors = validate_task(root)
    if not errors or expected not in "\n".join(errors):
        raise AssertionError(f"expected failure containing {expected!r}, got {errors!r}")


def self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="executor-quality-validator-") as temporary:
        base = Path(temporary)
        valid = base / "valid"
        write_synthetic_task(valid)
        errors = validate_task(valid)
        if errors:
            raise AssertionError(f"valid synthetic task failed: {errors}")

        leaked = base / "leaked"
        shutil.copytree(valid, leaked)
        (leaked / "visible" / "README.md").write_text("ORACLE_ONLY_SENTINEL\n", encoding="utf-8")
        refresh_visible_files(leaked)
        expect_failure(leaked, "leakage")

        stale = base / "stale-hash"
        shutil.copytree(valid, stale)
        (stale / "visible" / "contract.md").write_text("Changed bytes.\n", encoding="utf-8")
        expect_failure(stale, "sha256 mismatch")

        absent = base / "missing-excerpt"
        shutil.copytree(valid, absent)
        task = json.loads((absent / "task.json").read_text(encoding="utf-8"))
        task["contract_excerpt"]["quote"] = "This quote is absent."
        (absent / "task.json").write_text(json.dumps(task), encoding="utf-8")
        expect_failure(absent, "quote is absent")

        strawman = base / "strawman-symptom"
        shutil.copytree(valid, strawman)
        shutil.copyfile(strawman / "patches" / "noop.patch", strawman / "patches" / "symptom.patch")
        expect_failure(strawman, "symptom.patch must pass at least one")

        partial_gold = base / "partial-gold"
        shutil.copytree(valid, partial_gold)
        shutil.copyfile(partial_gold / "patches" / "symptom.patch", partial_gold / "patches" / "gold.patch")
        expect_failure(partial_gold, "gold.patch does not pass all")


def main() -> int:
    parser = ExitOneParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--task", type=Path)
    group.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        try:
            self_test()
        except (AssertionError, OSError, subprocess.SubprocessError, ValidationError) as exc:
            print(f"SELF_TEST: {exc}", file=sys.stderr)
            return 1
        print("SELF_TEST_OK: 5 fail-closed scenarios and 1 valid end-to-end task")
        return 0
    errors = validate_task(args.task.resolve())
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(f"TASK_OK: {args.task}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
