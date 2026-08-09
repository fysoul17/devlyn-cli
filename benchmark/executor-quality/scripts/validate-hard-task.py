#!/usr/bin/env python3
"""Validate one registered hard executor-quality task fixture."""

from __future__ import annotations

import argparse
import ast
import difflib
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path


ID_TO_PAIR = {
    "EQ2-UA1": "OR",
    "EQ2-UA2": "OI",
    "EQ2-UA3": "OA",
    "EQ2-UA4": "OE",
    "EQ2-UA5": "RI",
    "EQ2-UA6": "RA",
    "EQ2-UA7": "RE",
    "EQ2-UA8": "IE",
    "EQ2-MI1": "OR",
    "EQ2-MI2": "OI",
    "EQ2-MI3": "OA",
    "EQ2-MI4": "RI",
    "EQ2-MI5": "RE",
    "EQ2-MI6": "IA",
    "EQ2-MI7": "IE",
    "EQ2-MI8": "AE",
    "EQ2-AF1": "OR",
    "EQ2-AF2": "OA",
    "EQ2-AF3": "OE",
    "EQ2-AF4": "RI",
    "EQ2-AF5": "RA",
    "EQ2-AF6": "IA",
    "EQ2-AF7": "IE",
    "EQ2-AF8": "AE",
    "EQ2-BD1": "OI",
    "EQ2-BD2": "OA",
    "EQ2-BD3": "OE",
    "EQ2-BD4": "RI",
    "EQ2-BD5": "RA",
    "EQ2-BD6": "RE",
    "EQ2-BD7": "IA",
    "EQ2-BD8": "AE",
}
AXIS_NAMES = {
    "O": "ordering",
    "R": "rollback",
    "I": "idempotency",
    "A": "auth-order",
    "E": "error-priority",
}
ROLE_IDS = {"axis1-a", "axis1-b", "axis2-a", "axis2-b", "interaction"}
GENERIC_ORACLE_LITERALS = {
    "manifestations",
    "invariant",
    "passed",
    "true",
    "false",
    "python3",
}
FROZEN_VALIDATOR = Path(__file__).with_name("validate-task.py")


class ValidationError(ValueError):
    """A hard-corpus contract failed."""


class FrozenValidationError(ValidationError):
    """The frozen validator rejected the fixture."""

    def __init__(self, stdout: str, stderr: str) -> None:
        super().__init__(stderr or stdout or "frozen validator failed without output")
        self.stdout = stdout
        self.stderr = stderr


def load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read {path.name}: {exc}") from exc


def oracle_assertion_literals(oracle_path: Path) -> set[str]:
    try:
        tree = ast.parse(oracle_path.read_text(encoding="utf-8"), filename=str(oracle_path))
    except (OSError, UnicodeDecodeError, SyntaxError) as exc:
        raise ValidationError(f"cannot parse oracle.py for leakage scan: {exc}") from exc
    roots: list[ast.AST] = [node.test for node in ast.walk(tree) if isinstance(node, ast.Assert)]
    roots.extend(node for node in ast.walk(tree) if isinstance(node, ast.Compare))
    literals: set[str] = set()
    for root in roots:
        for node in ast.walk(root):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                value = node.value.strip()
                if len(value) >= 12 and value.lower() not in GENERIC_ORACLE_LITERALS:
                    literals.add(value)
    return literals


def apply_symptom_patch(task_dir: Path, workdir: Path) -> None:
    executable = shutil.which("patch")
    if executable is None:
        raise ValidationError("patch utility is unavailable")
    completed = subprocess.run(
        [
            executable,
            "-p1",
            "--forward",
            "--batch",
            "-i",
            str(task_dir / "patches" / "symptom.patch"),
        ],
        cwd=workdir,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    if completed.returncode != 0:
        detail = " ".join((completed.stderr or completed.stdout).split())
        raise ValidationError(f"symptom.patch application failed: {detail}")


def symptom_vector(task_dir: Path) -> dict[str, bool]:
    with tempfile.TemporaryDirectory(prefix="executor-quality-hard-symptom-") as temporary:
        workdir = Path(temporary) / "visible"
        shutil.copytree(task_dir / "visible", workdir)
        apply_symptom_patch(task_dir, workdir)
        completed = subprocess.run(
            [sys.executable, str(task_dir / "hidden" / "oracle.py"), str(workdir)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
    if completed.returncode != 0:
        detail = " ".join((completed.stderr or completed.stdout).split())
        raise ValidationError(f"symptom oracle failed: {detail}")
    try:
        output = json.loads(completed.stdout)
        results = output["manifestations"]
        vector = {result["id"]: result["passed"] for result in results}
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ValidationError(f"symptom oracle returned invalid JSON: {exc}") from exc
    if set(vector) != ROLE_IDS or len(results) != len(ROLE_IDS) or any(
        not isinstance(value, bool) for value in vector.values()
    ):
        raise ValidationError("symptom oracle returned invalid manifestation roles")
    return vector


def invoke_frozen_validator(task_dir: Path) -> None:
    completed = subprocess.run(
        [sys.executable, str(FROZEN_VALIDATOR), "--task", str(task_dir)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=120,
    )
    if completed.returncode != 0:
        raise FrozenValidationError(completed.stdout, completed.stderr)


def validate_hard_task(task_dir: Path) -> tuple[str, str]:
    invoke_frozen_validator(task_dir)
    task = load_json(task_dir / "task.json")
    manifests = load_json(task_dir / "hidden" / "manifests.json")
    if not isinstance(task, dict) or not isinstance(manifests, dict):
        raise ValidationError("frozen validator admitted an invalid JSON shape")

    task_id = task["id"]
    if task_id != task_dir.name:
        raise ValidationError(f"task id {task_id!r} does not match directory name {task_dir.name!r}")
    if task_id not in ID_TO_PAIR:
        raise ValidationError(f"unregistered task id {task_id!r}")

    entries = manifests["manifestations"]
    role_ids = {entry["id"] for entry in entries}
    if role_ids != ROLE_IDS or len(entries) != len(ROLE_IDS):
        raise ValidationError(
            f"manifestation ids must be exactly {sorted(ROLE_IDS)}, got {sorted(role_ids)}"
        )
    visible_files = task["visible_files"]
    if not 10 <= len(visible_files) <= 15:
        raise ValidationError(f"visible_files must contain 10-15 paths, got {len(visible_files)}")

    tokens = set(role_ids)
    tokens.update(
        path.stem
        for path in (task_dir / "hidden").rglob("*")
        if path.is_file() and len(path.stem) >= 4
    )
    tokens.update(oracle_assertion_literals(task_dir / "hidden" / "oracle.py"))
    goal = task["goal"].lower()
    leaked = sorted(token for token in tokens if token.lower() in goal)
    if leaked:
        raise ValidationError(f"goal leakage: task.json goal contains hidden token {leaked[0]!r}")

    vector = symptom_vector(task_dir)
    expected = {role: role != "interaction" for role in ROLE_IDS}
    if vector != expected:
        actual = ", ".join(f"{role}={str(vector[role]).lower()}" for role in sorted(ROLE_IDS))
        raise ValidationError(f"symptom.patch has wrong pass-vector: {actual}")
    return task_id, ID_TO_PAIR[task_id]


def unified_patch(before: str, after: str, path: str) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
    )


def engine_source(values: tuple[bool, bool, bool, bool, bool]) -> str:
    return '"""Synthetic scheduler."""\n\nRESULTS = ' + repr(values) + "\n"


def write_synthetic_task(root: Path) -> None:
    visible = root / "visible"
    hidden = root / "hidden"
    patches = root / "patches"
    visible.mkdir(parents=True)
    hidden.mkdir()
    patches.mkdir()
    contract = "Requests preserve queue order, release failed reservations, and compose both rules.\n"
    base_engine = engine_source((False, False, False, False, False))
    symptom_engine = engine_source((True, True, True, True, False))
    gold_engine = engine_source((True, True, True, True, True))
    files = {
        "contract.md": contract,
        "engine.py": base_engine,
        "README.md": "Repair the scheduler and run `python3 test_engine.py`.\n",
        "test_engine.py": "from engine import RESULTS\nassert len(RESULTS) == 5\n",
        "config.json": '{"mode":"strict"}\n',
        "queue.py": "def pending():\n    return []\n",
        "release.py": "def available():\n    return True\n",
        "models.py": "PRIORITY_DEFAULT = 0\n",
        "storage.py": "def snapshot():\n    return {}\n",
        "errors.py": "class SchedulingError(Exception):\n    pass\n",
    }
    for name, contents in files.items():
        (visible / name).write_text(contents, encoding="utf-8")
    invariant = "Ordering and rollback hold independently and remain correct when composed."
    binding = {
        "file": "visible/contract.md",
        "sha256": hashlib.sha256((visible / "contract.md").read_bytes()).hexdigest(),
        "quote": contract.strip(),
    }
    task = {
        "id": root.name,
        "class": "unsupported_assumption",
        "invariant": invariant,
        "goal": "Repair the scheduler to satisfy its visible contract. Run python3 test_engine.py.",
        "visible_files": [f"visible/{name}" for name in sorted(files)],
        "contract_excerpt": binding,
    }
    (root / "task.json").write_text(json.dumps(task, indent=2) + "\n", encoding="utf-8")
    roles = ("axis1-a", "axis1-b", "axis2-a", "axis2-b", "interaction")
    entries = [
        {
            "id": role,
            "invariant": invariant,
            "class": task["class"],
            "contract_excerpt": binding,
        }
        for role in roles
    ]
    (hidden / "manifests.json").write_text(
        json.dumps({"manifestations": entries}, indent=2) + "\n", encoding="utf-8"
    )
    oracle = f'''#!/usr/bin/env python3
import importlib.util
import json
import pathlib
import sys

workdir = pathlib.Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("fixture_engine", workdir / "engine.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
roles = {roles!r}
invariant = {invariant!r}
print(json.dumps({{"manifestations": [
    {{"id": role, "invariant": invariant, "passed": passed}}
    for role, passed in zip(roles, module.RESULTS)
]}}))
'''
    (hidden / "oracle.py").write_text(oracle, encoding="utf-8")
    (patches / "gold.patch").write_text(
        unified_patch(base_engine, gold_engine, "engine.py"), encoding="utf-8"
    )
    (patches / "symptom.patch").write_text(
        unified_patch(base_engine, symptom_engine, "engine.py"), encoding="utf-8"
    )
    noop_engine = base_engine.replace("Synthetic scheduler.", "Synthetic scheduler. No behavior change.")
    (patches / "noop.patch").write_text(
        unified_patch(base_engine, noop_engine, "engine.py"), encoding="utf-8"
    )


def rewrite_json(path: Path, mutate: Callable[[dict[str, object]], object]) -> None:
    value = json.loads(path.read_text(encoding="utf-8"))
    mutate(value)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def rewrite_symptom(root: Path, values: tuple[bool, bool, bool, bool, bool]) -> None:
    base_engine = engine_source((False, False, False, False, False))
    (root / "patches" / "symptom.patch").write_text(
        unified_patch(base_engine, engine_source(values), "engine.py"), encoding="utf-8"
    )


def expect_failure(root: Path, expected: str) -> None:
    try:
        validate_hard_task(root)
    except ValidationError as exc:
        if expected not in str(exc):
            raise AssertionError(f"expected failure containing {expected!r}, got {exc!r}") from exc
    else:
        raise AssertionError(f"expected failure containing {expected!r}, task passed")


def self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="executor-quality-hard-validator-") as temporary:
        base = Path(temporary)
        valid = base / "EQ2-UA1"
        write_synthetic_task(valid)
        validate_hard_task(valid)

        unregistered = base / "EQ2-ZZ1"
        shutil.copytree(valid, unregistered)
        rewrite_json(unregistered / "task.json", lambda task: task.update(id=unregistered.name))
        expect_failure(unregistered, "unregistered task id")

        wrong_roles = base / "wrong-roles" / "EQ2-UA1"
        shutil.copytree(valid, wrong_roles)
        rewrite_json(
            wrong_roles / "hidden" / "manifests.json",
            lambda data: data["manifestations"][0].update(id="axis1-c"),
        )
        oracle_path = wrong_roles / "hidden" / "oracle.py"
        oracle_path.write_text(
            oracle_path.read_text(encoding="utf-8").replace("'axis1-a'", "'axis1-c'"),
            encoding="utf-8",
        )
        expect_failure(wrong_roles, "manifestation ids must be exactly")

        interaction_passes = base / "interaction-passes" / "EQ2-UA1"
        shutil.copytree(valid, interaction_passes)
        rewrite_symptom(interaction_passes, (False, True, True, True, True))
        expect_failure(interaction_passes, "wrong pass-vector")

        single_axis_fails = base / "single-axis-fails" / "EQ2-UA1"
        shutil.copytree(valid, single_axis_fails)
        rewrite_symptom(single_axis_fails, (False, True, True, True, False))
        expect_failure(single_axis_fails, "wrong pass-vector")

        nine_files = base / "nine-files" / "EQ2-UA1"
        shutil.copytree(valid, nine_files)
        (nine_files / "visible" / "storage.py").unlink()
        rewrite_json(
            nine_files / "task.json",
            lambda task: task.update(
                visible_files=[path for path in task["visible_files"] if path != "visible/storage.py"]
            ),
        )
        expect_failure(nine_files, "visible_files must contain 10-15")

        leaked_goal = base / "leaked-goal" / "EQ2-UA1"
        shutil.copytree(valid, leaked_goal)
        rewrite_json(
            leaked_goal / "task.json",
            lambda task: task.update(goal=task["goal"] + " Check axis1-a."),
        )
        expect_failure(leaked_goal, "goal leakage")


def main() -> int:
    parser = argparse.ArgumentParser()
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
        print("SELF_TEST_OK: 6 fail-closed scenarios and 1 valid end-to-end hard task")
        return 0

    task_dir = args.task.resolve()
    try:
        task_id, pair = validate_hard_task(task_dir)
    except FrozenValidationError as exc:
        sys.stdout.write(exc.stdout)
        sys.stderr.write(exc.stderr)
        return 1
    except (OSError, subprocess.SubprocessError, ValidationError) as exc:
        print(f"HARD: {' '.join(str(exc).split())}", file=sys.stderr)
        return 1
    print(
        f"TASK_OK: {task_id} pair={pair} "
        f"axis1={AXIS_NAMES[pair[0]]} axis2={AXIS_NAMES[pair[1]]}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
