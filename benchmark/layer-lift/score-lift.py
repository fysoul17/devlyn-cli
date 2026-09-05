#!/usr/bin/env python3
"""Frozen iter-0113 layer-lift quality and efficiency scorer."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import random
import re
import shutil
import sys
import tempfile
from fractions import Fraction
from typing import Any, Iterable


REPO = pathlib.Path("/Users/aipalm/Documents/GitHub/devlyn-cli")
HERE = REPO / "benchmark/layer-lift"
DEFAULT_PARAMS = HERE / "registered-params.json"
DEFAULT_PANEL = HERE / "panel-quick.json"
SCRIPTS_PATH = HERE / "scripts.sha256"
PARAMS_PIN_SHA256 = "f339e7629683303aa8ae94c4770f6231cdf150c8bbebff626d2970d4e2970f3c"
ARMS = ("L0", "L1", "L2")
CLASS_RE = re.compile(r"^EQ3-(AF|BD|MI|UA)[1-8]$")
TERMINALS = {"BARE", "PASS", "PASS_WITH_ISSUES", "NEEDS_WORK", "TIMEOUT"}
APPARATUS_FILES = (
    "benchmark/ceiling/scripts/claude-isolation.py",
    "benchmark/layer-lift/README.md",
    "benchmark/layer-lift/panel-quick.json",
    "benchmark/layer-lift/run-lift-panel.py",
    "benchmark/layer-lift/score-lift.py",
)
PARAMS_PIN_FILES = {
    "benchmark/layer-lift/run-lift-panel.py",
    "benchmark/layer-lift/score-lift.py",
}
PARAMS_PIN_LINE = re.compile(rb'(?m)^PARAMS_PIN_SHA256 = "[^"\r\n]*"\r?\n')


class ScoreError(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    return sha256_bytes(path.read_bytes())


def normalized_apparatus_sha256(root: pathlib.Path = REPO) -> str:
    digest = hashlib.sha256()
    for relative in sorted(APPARATUS_FILES):
        data = (root / relative).read_bytes()
        if relative in PARAMS_PIN_FILES:
            data, count = PARAMS_PIN_LINE.subn(b'PARAMS_PIN_SHA256 = "TBD-FREEZE"\n', data)
            if count != 1:
                raise ScoreError(f"apparatus params-pin line count differs: {relative}")
        digest.update(relative.encode("utf-8") + b"\0")
        digest.update(sha256_bytes(data).encode("ascii") + b"\n")
    return digest.hexdigest()


def validate_apparatus(params: dict[str, Any], root: pathlib.Path = REPO) -> None:
    if normalized_apparatus_sha256(root) != params.get("apparatus_sha256"):
        raise ScoreError("normalized apparatus digest mismatch")


def reject_constant(token: str) -> None:
    raise ValueError(f"invalid JSON numeric constant: {token}")


def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def strict_json(raw: bytes) -> object:
    return json.loads(raw, parse_constant=reject_constant, object_pairs_hook=reject_duplicates)


def read_object(path: pathlib.Path) -> dict[str, Any]:
    value = strict_json(path.read_bytes())
    if not isinstance(value, dict):
        raise ScoreError(f"JSON object required: {path}")
    return value


def canonical_json(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def frac(value: object, label: str = "fraction") -> Fraction:
    if not isinstance(value, str) or re.fullmatch(r"-?[0-9]+/[1-9][0-9]*", value) is None:
        raise ScoreError(f"{label} must be an a/b string")
    result = Fraction(value)
    return result


def fraction_json(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def task_class(task: str) -> str:
    match = CLASS_RE.fullmatch(task)
    if match is None:
        raise ScoreError(f"invalid task id: {task}")
    return match.group(1)


def percentile(sorted_values: list[Fraction], probability: Fraction) -> Fraction:
    if not sorted_values:
        raise ScoreError("percentile requires values")
    position = probability * (len(sorted_values) - 1)
    lower = position.numerator // position.denominator
    upper = -(-position.numerator // position.denominator)
    if lower == upper:
        return sorted_values[lower]
    weight = position - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def median(values: list[int]) -> Fraction:
    if not values:
        raise ScoreError("median requires values")
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return Fraction(ordered[middle])
    return Fraction(ordered[middle - 1] + ordered[middle], 2)


def ceil_fraction(value: Fraction) -> int:
    return -(-value.numerator // value.denominator)


def grouped_bootstrap(
    values: dict[str, Fraction],
    *,
    seed: int,
    resamples: int,
) -> tuple[Fraction, list[Fraction]]:
    classes: dict[str, list[Fraction]] = {}
    for task, value in values.items():
        classes.setdefault(task_class(task), []).append(value)
    if set(classes) != {"AF", "BD", "MI", "UA"} or any(not group for group in classes.values()):
        raise ScoreError("bootstrap requires non-empty AF/BD/MI/UA strata")
    point = sum(
        (sum(group, Fraction()) / len(group) for _, group in sorted(classes.items())),
        Fraction(),
    ) / 4
    rng = random.Random(seed)
    samples: list[Fraction] = []
    for _ in range(resamples):
        class_means = []
        for cls in sorted(classes):
            group = classes[cls]
            class_means.append(
                sum((group[rng.randrange(len(group))] for _ in range(len(group))), Fraction()) / len(group)
            )
        samples.append(sum(class_means, Fraction()) / 4)
    samples.sort()
    return point, [percentile(samples, Fraction(1, 40)), percentile(samples, Fraction(39, 40))]


def q_decision(low: Fraction, high: Fraction, delta: Fraction) -> str:
    if low > delta:
        return "LIFT"
    if low > -delta and high < delta:
        return "NULL"
    if high < -delta:
        return "HARM"
    return "INCONCLUSIVE"


def e_decision(low: Fraction, high: Fraction) -> str:
    if low > 0:
        return "EFFICIENT"
    if high < 0:
        return "INEFFICIENT"
    return "INCONCLUSIVE"


def decision_record(values: dict[str, Fraction], params: dict[str, Any], quality: bool) -> dict[str, Any]:
    point, ci = grouped_bootstrap(
        values,
        seed=int(params["bootstrap"]["seed"]),
        resamples=int(params["bootstrap"]["resamples"]),
    )
    decision = q_decision(ci[0], ci[1], Fraction(params["delta"])) if quality else e_decision(ci[0], ci[1])
    return {
        "point": fraction_json(point),
        "ci": [fraction_json(ci[0]), fraction_json(ci[1])],
        "decision": decision,
    }


def derive_panel(calibrator: pathlib.Path) -> dict[str, Any]:
    payload = read_object(calibrator)
    if payload.get("engine") != "claude-sonnet-5":
        raise ScoreError("calibrator engine mismatch")
    q_cal = payload.get("q_cal")
    if not isinstance(q_cal, dict) or len(q_cal) != 32:
        raise ScoreError("calibrator q_cal must contain 32 rows")
    ranked: dict[str, list[tuple[Fraction, str]]] = {cls: [] for cls in ("AF", "BD", "MI", "UA")}
    for task, value in q_cal.items():
        if not isinstance(task, str) or not isinstance(value, str):
            raise ScoreError("calibrator entry shape mismatch")
        ranked[task_class(task)].append((abs(Fraction(value) - Fraction(1, 2)), task))
    return {
        "calibrator_sha256": sha256_file(calibrator),
        "rule": "per class, 3 ids minimizing exact Fraction abs(q_cal - 1/2); ties lexical id",
        "tasks": {cls: [task for _, task in sorted(ranked[cls])[:3]] for cls in sorted(ranked)},
    }


def panel_tasks(params: dict[str, Any], panel_name: str, panel: dict[str, Any] | None = None) -> list[str]:
    if panel_name == "quick":
        payload = panel if panel is not None else read_object(DEFAULT_PANEL)
        tasks = payload.get("tasks")
        if not isinstance(tasks, dict):
            raise ScoreError("quick panel tasks missing")
        return [task for cls in sorted(tasks) for task in tasks[cls]]
    manifest = read_object(pathlib.Path(params["corpus"]["manifest_path"]))
    tasks = manifest.get("tasks")
    if not isinstance(tasks, dict) or len(tasks) != 32:
        raise ScoreError("full corpus task map missing")
    return sorted(tasks)


def validate_scripts_manifest(path: pathlib.Path = SCRIPTS_PATH) -> list[str]:
    errors: list[str] = []
    expected_targets = {
        target.resolve()
        for target in HERE.iterdir()
        if target.is_file() and target != SCRIPTS_PATH and target.name != "drain-quick.py"
    } | {
        (REPO / "benchmark/ceiling/scripts/claude-isolation.py").resolve(),
        pathlib.Path("/Users/aipalm/.local/share/nx01/iter0102/freeze/candidate-manifest.json").resolve(),
    }
    seen: set[pathlib.Path] = set()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [f"scripts manifest unreadable: {exc}"]
    if not lines:
        return ["scripts manifest empty"]
    for number, line in enumerate(lines, 1):
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if match is None:
            errors.append(f"scripts manifest line {number} malformed")
            continue
        expected, name = match.groups()
        target = pathlib.Path(name)
        if not target.is_absolute():
            target = REPO / target
        target = target.resolve()
        if target in seen:
            errors.append(f"scripts manifest duplicate target: {name}")
        seen.add(target)
        try:
            if sha256_file(target) != expected:
                errors.append(f"scripts manifest digest mismatch: {name}")
        except OSError as exc:
            errors.append(f"scripts manifest target unreadable: {name}: {exc}")
    missing = expected_targets - seen
    extra = seen - expected_targets
    if missing or extra:
        errors.append(
            "scripts manifest target set mismatch: "
            f"missing={[str(item) for item in sorted(missing)]}, "
            f"extra={[str(item) for item in sorted(extra)]}"
        )
    return errors


def frozen_errors(params_path: pathlib.Path, params: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if PARAMS_PIN_SHA256 == "TBD-FREEZE":
        errors.append("registered-params pin is TBD-FREEZE")
    else:
        try:
            if sha256_file(params_path) != PARAMS_PIN_SHA256:
                errors.append("registered-params pin mismatch")
        except OSError as exc:
            errors.append(f"registered-params unreadable: {exc}")
    try:
        validate_apparatus(params)
    except (OSError, ScoreError) as exc:
        errors.append(str(exc))
    errors.extend(validate_scripts_manifest())
    checks = (
        (params["corpus"]["manifest_path"], params["corpus"]["manifest_sha256"], "corpus manifest"),
        (params["calibrator"]["path"], params["calibrator"]["sha256"], "calibrator"),
        (params["claude"]["binary_path"], params["claude"]["binary_sha256"], "Claude binary"),
        (params["pair"]["codex_binary_path"], params["pair"]["codex_binary_sha256"], "Codex binary"),
    )
    for raw_path, expected, label in checks:
        try:
            if sha256_file(pathlib.Path(raw_path)) != expected:
                errors.append(f"{label} digest mismatch")
        except OSError as exc:
            errors.append(f"{label} unreadable: {exc}")
    try:
        manifest = read_object(pathlib.Path(params["corpus"]["manifest_path"]))
        tree = sha256_bytes(json.dumps(manifest["tasks"], sort_keys=True, separators=(",", ":")).encode())
        if tree != params["corpus"]["tree_sha256"]:
            errors.append("corpus tree digest mismatch")
    except (OSError, KeyError, ScoreError):
        errors.append("corpus tree cannot be verified")
    try:
        derived = derive_panel(pathlib.Path(params["calibrator"]["path"]))
        if derived != read_object(DEFAULT_PANEL):
            errors.append("quick panel derivation mismatch")
    except (OSError, ScoreError, ValueError):
        errors.append("quick panel cannot be re-derived")
    return errors


REQUIRED_FIELDS = {
    "run_id", "attempt", "arm", "task", "class", "rep", "topup",
    "model_requested", "model_attested", "surface_close_ran",
    "surface_model_attested", "pair_model_attested", "pair_effort_attested",
    "pair_cli_version_attested", "pair_judge_ran", "pair_timeout", "codex_tokens_total",
    "terminal", "f_tree", "f_ship",
    "manifestations_total", "manifestations_failed", "catastrophic",
    "incomplete", "infra_invalid", "infra_reason", "wall_ms",
    "output_tokens", "output_tokens_total",
    "verification_bullets", "fix_round_ran", "diff_changed_by_pair",
    "prompt_sha256", "goal_sha256", "staged_intervention_sha256",
    "claude_binary_sha256", "started_at", "finished_at",
}


def validate_row(row: object, number: int) -> list[str]:
    label = f"row {number}"
    if not isinstance(row, dict):
        return [f"{label}: object required"]
    errors: list[str] = []
    missing = REQUIRED_FIELDS - set(row)
    extra = set(row) - REQUIRED_FIELDS
    if missing or extra:
        return [f"{label}: schema fields differ (missing={sorted(missing)}, extra={sorted(extra)})"]
    if row["arm"] not in ARMS:
        errors.append(f"{label}: invalid arm")
    try:
        expected_class = task_class(row["task"])
        if row["class"] != expected_class:
            errors.append(f"{label}: class mismatch")
    except (ScoreError, TypeError):
        errors.append(f"{label}: invalid task")
    for key in ("attempt", "rep", "manifestations_total", "manifestations_failed", "wall_ms"):
        if type(row[key]) is not int or row[key] < 0:
            errors.append(f"{label}: {key} must be a non-negative int")
    timeout = row["terminal"] == "TIMEOUT"
    usage_unknown = timeout or row["pair_timeout"] is True
    for key in ("output_tokens_total", "codex_tokens_total"):
        if usage_unknown:
            if row[key] is not None:
                errors.append(f"{label}: timed-out usage requires null {key}")
        elif type(row[key]) is not int or row[key] < 0:
            errors.append(f"{label}: {key} must be a non-negative int")
    if type(row["attempt"]) is int and row["attempt"] not in {1, 2, 3}:
        errors.append(f"{label}: attempt must be 1, 2, or 3")
    if type(row["rep"]) is int and row["rep"] < 1:
        errors.append(f"{label}: rep must be positive")
    for key in ("topup", "surface_close_ran", "pair_timeout", "catastrophic", "incomplete", "infra_invalid"):
        if type(row[key]) is not bool:
            errors.append(f"{label}: {key} must be boolean")
    try:
        tree = frac(row["f_tree"], f"{label} f_tree")
        ship = frac(row["f_ship"], f"{label} f_ship")
        if not (0 <= tree <= 1 and 0 <= ship <= 1):
            errors.append(f"{label}: f_tree/f_ship outside [0,1]")
        terminal = row["terminal"]
        terminal_ok = terminal in TERMINALS or (isinstance(terminal, str) and terminal.startswith("BLOCKED:"))
        if not terminal_ok:
            errors.append(f"{label}: invalid terminal")
        if row["arm"] == "L0" and terminal == "BARE" and row["incomplete"] is False and ship != tree:
            errors.append(f"{label}: L0 f_ship must equal f_tree")
        if row["arm"] == "L0" and terminal not in {"BARE", "TIMEOUT"}:
            errors.append(f"{label}: L0 terminal must be BARE or TIMEOUT")
        if row["arm"] != "L0" and terminal == "BARE":
            errors.append(f"{label}: harness terminal cannot be BARE")
        if row["arm"] != "L0" and terminal in {"PASS", "PASS_WITH_ISSUES"} and row["incomplete"] is False and ship != tree:
            errors.append(f"{label}: passing harness f_ship must equal f_tree")
        if (terminal == "TIMEOUT" or (isinstance(terminal, str) and terminal.startswith("BLOCKED:"))) and ship != 1:
            errors.append(f"{label}: BLOCKED/TIMEOUT f_ship must be 1/1")
        if row["arm"] != "L0" and terminal == "NEEDS_WORK" and ship != 1:
            errors.append(f"{label}: NEEDS_WORK f_ship must be 1/1")
        if row["incomplete"] is True and row["infra_invalid"] is False and ship != 1:
            errors.append(f"{label}: clean incomplete row f_ship must be 1/1")
    except ScoreError as exc:
        errors.append(str(exc))
    output = row["output_tokens"]
    if not isinstance(output, dict) or set(output) != {"parent", "surface_close"}:
        errors.append(f"{label}: output_tokens shape mismatch")
    else:
        component_sum = 0
        for key in ("parent", "surface_close"):
            values = output[key]
            if not isinstance(values, dict) or any(type(value) is not int or value < 0 for value in values.values()):
                errors.append(f"{label}: output_tokens.{key} malformed")
            else:
                component_sum += sum(values.values())
        if type(row["codex_tokens_total"]) is int:
            component_sum += row["codex_tokens_total"]
        if type(row["output_tokens_total"]) is int and component_sum != row["output_tokens_total"]:
            errors.append(f"{label}: output token total mismatch")
    total, failed = row["manifestations_total"], row["manifestations_failed"]
    if type(total) is int and type(failed) is int and (failed > total or failed < 0):
        errors.append(f"{label}: manifestation counts invalid")
    if type(total) is int and type(failed) is int and total > 0:
        try:
            if frac(row["f_tree"]) != Fraction(failed, total):
                errors.append(f"{label}: f_tree does not match manifestation counts")
        except ScoreError:
            pass
    if row["infra_invalid"] is True and not isinstance(row["infra_reason"], str):
        errors.append(f"{label}: infra-invalid row requires infra_reason")
    if row["infra_invalid"] is False and row["infra_reason"] is not None:
        errors.append(f"{label}: clean row cannot carry infra_reason")
    if row["arm"] == "L0" and row["verification_bullets"] is not None:
        errors.append(f"{label}: L0 verification_bullets must be null")
    if row["arm"] != "L0" and (type(row["verification_bullets"]) is not int or row["verification_bullets"] < 0):
        errors.append(f"{label}: harness verification_bullets must be non-negative int")
    if row["arm"] == "L2":
        if type(row["fix_round_ran"]) is not bool or not (
            row["diff_changed_by_pair"] is None or type(row["diff_changed_by_pair"]) is bool
        ):
            errors.append(f"{label}: L2 fix diagnostics malformed")
    elif row["fix_round_ran"] is not None or row["diff_changed_by_pair"] is not None:
        errors.append(f"{label}: non-L2 fix diagnostics must be null")
    pair_fields = ("pair_model_attested", "pair_effort_attested", "pair_cli_version_attested")
    ran = row["pair_judge_ran"]
    if ran is not None and type(ran) is not bool:
        errors.append(f"{label}: pair_judge_ran must be boolean or null")
    if row["arm"] == "L2" and row["infra_invalid"] is False:
        if timeout:
            if ran is False:
                errors.append(f"{label}: TIMEOUT cannot establish pair not-run")
        elif type(ran) is not bool:
            errors.append(f"{label}: clean L2 requires boolean pair_judge_ran")
        if ran is False and (
            row["terminal"] in {"PASS", "PASS_WITH_ISSUES", "TIMEOUT"}
            or row["f_ship"] != "1/1" or any(row[key] is not None for key in pair_fields)
            or row["codex_tokens_total"] != 0 or row["pair_timeout"] is not False
        ):
            errors.append(f"{label}: pair not-run contradicts outcome or evidence")
    if row["arm"] != "L2":
        if ran is not None:
            errors.append(f"{label}: non-L2 pair_judge_ran must be null")
        expected_codex = None if usage_unknown else 0
        if any(row[key] is not None for key in pair_fields) or row["pair_timeout"] is not False or row["codex_tokens_total"] != expected_codex:
            errors.append(f"{label}: non-L2 pair attestation must be empty")
    return errors


def load_rows(path: pathlib.Path) -> tuple[list[dict[str, Any]], str]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ScoreError(f"rows unreadable: {exc}") from exc
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    for number, line in enumerate(raw.splitlines(), 1):
        if not line:
            errors.append(f"row line {number}: blank")
            continue
        try:
            value = strict_json(line)
        except (ValueError, UnicodeError) as exc:
            errors.append(f"row line {number}: {exc}")
            continue
        row_errors = validate_row(value, number)
        errors.extend(row_errors)
        if isinstance(value, dict):
            rows.append(value)
    if errors:
        raise ScoreError("; ".join(errors))
    return rows, sha256_bytes(raw)


def latest(rows: Iterable[dict[str, Any]]) -> dict[tuple[str, str, int], dict[str, Any]]:
    result: dict[tuple[str, str, int], dict[str, Any]] = {}
    for row in rows:
        key = (row["arm"], row["task"], row["rep"])
        prior = result.get(key)
        if prior is None or row["attempt"] > prior["attempt"]:
            result[key] = row
    return result


def expected_base(tasks: list[str], params: dict[str, Any]) -> list[tuple[str, str, int]]:
    return [
        (arm, task, rep)
        for arm in ARMS
        for task in tasks
        for rep in range(1, int(params["base_reps"][arm]) + 1)
    ]


def mean(values: Iterable[Fraction]) -> Fraction:
    materialized = list(values)
    if not materialized:
        raise ScoreError("mean requires values")
    return sum(materialized, Fraction()) / len(materialized)


def per_task_arm(latest_rows: dict[tuple[str, str, int], dict[str, Any]], tasks: list[str], params: dict[str, Any]) -> dict[str, dict[str, Fraction]]:
    return {
        arm: {
            task: mean(
                frac(latest_rows[(arm, task, rep)]["f_ship"])
                for rep in range(1, int(params["base_reps"][arm]) + 1)
            )
            for task in tasks
        }
        for arm in ARMS
    }


def efficiency_dimension(
    *,
    cheaper: str,
    expensive: str,
    n: int,
    tasks: list[str],
    all_latest: dict[tuple[str, str, int], dict[str, Any]],
    arm_rates: dict[str, dict[str, Fraction]],
    params: dict[str, Any],
) -> dict[str, Any]:
    values: dict[str, Fraction] = {}
    complete = True
    available_by_task: dict[str, int] = {}
    for task in tasks:
        contiguous: list[Fraction] = []
        for rep in range(1, n + 1):
            row = all_latest.get((cheaper, task, rep))
            if row is None or row.get("infra_invalid") is True:
                break
            contiguous.append(frac(row["f_ship"]))
        available_by_task[task] = len(contiguous)
        if len(contiguous) < n:
            complete = False
        if not contiguous:
            raise ScoreError(f"no cheaper-arm repetitions for {cheaper}/{task}")
        values[task] = min(contiguous) - arm_rates[expensive][task]
    record = decision_record(values, params, quality=False)
    if not complete:
        high = Fraction(record["ci"][1])
        record["decision"] = "INEFFICIENT" if high < 0 else "NEEDS_TOPUP"
    record["n"] = n
    record["complete"] = complete
    record["available_by_task"] = available_by_task
    record["per_task"] = {task: fraction_json(value) for task, value in sorted(values.items())}
    return record


def aggregate_efficiency(wall: dict[str, Any], tokens: dict[str, Any]) -> str:
    decisions = {wall["decision"], tokens["decision"]}
    if decisions == {"EFFICIENT"}:
        return "EFFICIENT"
    if "INEFFICIENT" in decisions:
        return "INEFFICIENT"
    if "NEEDS_TOPUP" in decisions:
        return "NEEDS_TOPUP"
    return "INCONCLUSIVE"


def score(
    rows: list[dict[str, Any]],
    params: dict[str, Any],
    *,
    panel_name: str,
    panel: dict[str, Any],
    rows_sha256: str,
    params_sha256: str,
    run_metadata: dict[str, Any],
    injected_frozen_errors: list[str] | None = None,
) -> dict[str, Any]:
    if injected_frozen_errors:
        raise ScoreError("runner is not frozen: " + "; ".join(injected_frozen_errors))
    tasks = panel_tasks(params, panel_name, panel)
    identity_errors: list[str] = []
    goal_digests: dict[str, set[str]] = {}
    histories: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    for row in rows:
        histories.setdefault((row["arm"], row["task"], row["rep"]), []).append(row)
        if row["task"] not in tasks:
            identity_errors.append(f"row outside registered panel: {(row['arm'], row['task'], row['rep'])}")
        if not isinstance(row["run_id"], str) or not row["run_id"].startswith(f"{run_metadata['run_id']}:a"):
            identity_errors.append(f"row run_id differs from run metadata: {row['run_id']!r}")
        if row["model_requested"] != run_metadata["model"]:
            identity_errors.append(f"row model differs from run metadata: {row['run_id']}")
        if row["infra_invalid"] is False:
            if row["claude_binary_sha256"] != params["claude"]["binary_sha256"]:
                identity_errors.append(f"row Claude binary digest mismatch: {row['run_id']}")
            if row["arm"] == "L0":
                if row["staged_intervention_sha256"] is not None:
                    identity_errors.append(f"L0 row carries a staged-intervention digest: {row['run_id']}")
                if row["prompt_sha256"] != row["goal_sha256"]:
                    identity_errors.append(f"L0 prompt/goal digest mismatch: {row['run_id']}")
            elif row["staged_intervention_sha256"] != params["harness"]["staged_intervention_sha256"]:
                identity_errors.append(f"harness staged-intervention digest mismatch: {row['run_id']}")
            if row["model_attested"] != row["model_requested"] and not (
                row["terminal"] == "TIMEOUT" and row["model_attested"] is None
            ):
                identity_errors.append(f"parent model attestation mismatch: {row['run_id']}")
            if row["surface_close_ran"] is True and row["surface_model_attested"] != "claude-sonnet-5":
                identity_errors.append(f"surface model attestation mismatch: {row['run_id']}")
            if row["surface_close_ran"] is False and row["surface_model_attested"] is not None:
                identity_errors.append(f"surface model attestation without a run: {row['run_id']}")
            if row["arm"] == "L2" and row["terminal"] != "TIMEOUT" and row["pair_judge_ran"] is True:
                if (
                    row["pair_model_attested"] != params["pair"]["model_id"]
                    or row["pair_effort_attested"] != params["pair"]["effective_effort"]
                    or row["pair_cli_version_attested"] != params["pair"]["codex_cli_version"]
                ):
                    identity_errors.append(f"L2 pair stderr attestation mismatch: {row['run_id']}")
            if row["arm"] == "L2" and row["terminal"] == "TIMEOUT":
                observed_pair = tuple(row[field] for field in (
                    "pair_model_attested", "pair_effort_attested", "pair_cli_version_attested",
                ))
                expected_pair = (
                    params["pair"]["model_id"], params["pair"]["effective_effort"],
                    params["pair"]["codex_cli_version"],
                )
                if observed_pair != (None, None, None) and observed_pair != expected_pair:
                    identity_errors.append(f"L2 timeout pair stderr attestation mismatch: {row['run_id']}")
            goal_digests.setdefault(row["task"], set()).add(row["goal_sha256"])
        base_limit = int(params["base_reps"][row["arm"]])
        if row["topup"] is False and row["rep"] > base_limit:
            identity_errors.append(f"non-topup row exceeds base reps: {row['run_id']}")
        if row["topup"] is True and (row["arm"] == "L2" or row["rep"] <= base_limit):
            identity_errors.append(f"invalid topup arm/rep: {row['run_id']}")
    identity_errors.extend(
        f"goal bytes differ across arms/reps: {task}"
        for task, digests in sorted(goal_digests.items())
        if len(digests) != 1
    )
    for key, history in histories.items():
        attempts = sorted(row["attempt"] for row in history)
        if len(attempts) != len(set(attempts)):
            identity_errors.append(f"duplicate attempt for cell: {key}")
            continue
        by_attempt = {row["attempt"]: row for row in history}
        if 1 not in by_attempt:
            identity_errors.append(f"cell lacks attempt 1: {key}")
        for attempt in attempts:
            if attempt > 1 and (
                attempt - 1 not in by_attempt
                or by_attempt[attempt - 1]["infra_invalid"] is not True
            ):
                identity_errors.append(f"retry does not replace prior infra-invalid row: {key} attempt {attempt}")
    if identity_errors:
        raise ScoreError("; ".join(identity_errors))
    base_latest = latest(row for row in rows if row["topup"] is False)
    all_latest = latest(rows)
    expected = expected_base(tasks, params)
    l0_expected = [key for key in expected if key[0] == "L0"]
    l0_ready = all(key in base_latest and base_latest[key]["infra_invalid"] is False for key in l0_expected)
    if l0_ready:
        l0_mean = mean(frac(base_latest[key]["f_ship"]) for key in l0_expected)
        if l0_mean < Fraction(params["saturation_threshold"]):
            return {
                "terminal_kind": "PANEL_SATURATED",
                "panel_saturated": True,
                "l0_mean_f_ship": fraction_json(l0_mean),
                "inputs": {
                    "rows_sha256": rows_sha256,
                    "params_sha256": params_sha256,
                    "panel_sha256": sha256_bytes(canonical_json(panel)),
                    "run_metadata_sha256": sha256_bytes(canonical_json(run_metadata)),
                },
                "model": run_metadata["model"],
                "panel": panel_name,
                "run_id": run_metadata["run_id"],
            }
    missing = [key for key in expected if key not in base_latest]
    invalid = [key for key in expected if key in base_latest and base_latest[key]["infra_invalid"] is True]
    invalid.extend(
        key
        for key, row in all_latest.items()
        if row["topup"] is True and row["infra_invalid"] is True
    )
    if invalid or missing:
        parts = []
        if invalid:
            parts.append(f"infra-invalid rows excluded: {invalid}")
        if missing:
            parts.append(f"missing base rows: {missing}")
        raise ScoreError("; ".join(parts))
    base_rows = [base_latest[key] for key in expected]
    rates = per_task_arm(base_latest, tasks, params)
    d1 = {task: rates["L0"][task] - rates["L1"][task] for task in tasks}
    d2 = {task: rates["L1"][task] - rates["L2"][task] for task in tasks}
    q1 = decision_record(d1, params, quality=True)
    q2 = decision_record(d2, params, quality=True)

    wall_medians = {
        arm: median([row["wall_ms"] for row in base_rows if row["arm"] == arm])
        for arm in ARMS
    }
    unknown_tokens = {
        arm: sorted(
            row["run_id"]
            for row in base_rows
            if row["arm"] == arm and row["output_tokens_total"] is None
        )
        for arm in ARMS
    }
    token_sums = {
        arm: None if unknown_tokens[arm] else sum(
            row["output_tokens_total"] for row in base_rows if row["arm"] == arm
        )
        for arm in ARMS
    }
    token_means = {
        arm: None if token_sums[arm] is None else Fraction(
            token_sums[arm], sum(row["arm"] == arm for row in base_rows),
        )
        for arm in ARMS
    }
    if any(value <= 0 for value in wall_medians.values()):
        raise ScoreError("efficiency wall denominator is zero")
    if any(value <= 0 for value in token_sums.values() if value is not None):
        raise ScoreError("efficiency token denominator is zero")
    n1_wall = ceil_fraction(wall_medians["L1"] / wall_medians["L0"])
    m2_wall = ceil_fraction(wall_medians["L2"] / wall_medians["L1"])
    e1_wall = efficiency_dimension(
        cheaper="L0", expensive="L1", n=n1_wall, tasks=tasks,
        all_latest=all_latest, arm_rates=rates, params=params,
    )
    e2_wall = efficiency_dimension(
        cheaper="L1", expensive="L2", n=m2_wall, tasks=tasks,
        all_latest=all_latest, arm_rates=rates, params=params,
    )
    e1_base_unknown = sorted(unknown_tokens["L0"] + unknown_tokens["L1"])
    e2_base_unknown = sorted(unknown_tokens["L1"] + unknown_tokens["L2"])
    if e1_base_unknown:
        n1_tok = None
        e1_tok = {"decision": "INCONCLUSIVE", "unknown_timeout_rows": e1_base_unknown}
    else:
        n1_tok = ceil_fraction(token_means["L1"] / token_means["L0"])
        e1_unknown = sorted(
            row["run_id"]
            for task in tasks
            for rep in range(1, n1_tok + 1)
            if (row := all_latest.get(("L0", task, rep))) is not None
            and row["output_tokens_total"] is None
        )
        e1_tok = (
            {"decision": "INCONCLUSIVE", "unknown_timeout_rows": e1_unknown}
            if e1_unknown else efficiency_dimension(
                cheaper="L0", expensive="L1", n=n1_tok, tasks=tasks,
                all_latest=all_latest, arm_rates=rates, params=params,
            )
        )
    if e2_base_unknown:
        m2_tok = None
        e2_tok = {"decision": "INCONCLUSIVE", "unknown_timeout_rows": e2_base_unknown}
    else:
        m2_tok = ceil_fraction(token_means["L2"] / token_means["L1"])
        e2_unknown = sorted(
            row["run_id"]
            for task in tasks
            for rep in range(1, m2_tok + 1)
            if (row := all_latest.get(("L1", task, rep))) is not None
            and row["output_tokens_total"] is None
        )
        e2_tok = (
            {"decision": "INCONCLUSIVE", "unknown_timeout_rows": e2_unknown}
            if e2_unknown else efficiency_dimension(
                cheaper="L1", expensive="L2", n=m2_tok, tasks=tasks,
                all_latest=all_latest, arm_rates=rates, params=params,
            )
        )
    e1 = aggregate_efficiency(e1_wall, e1_tok)
    e2 = aggregate_efficiency(e2_wall, e2_tok)
    topup: dict[str, Any] | None = None
    if e1 == "NEEDS_TOPUP":
        needed = max(item["n"] for item in (e1_wall, e1_tok) if item["decision"] == "NEEDS_TOPUP")
        topup = {"leg": "E1", "n": needed}
    elif e2 == "NEEDS_TOPUP":
        needed = max(item["n"] for item in (e2_wall, e2_tok) if item["decision"] == "NEEDS_TOPUP")
        topup = {"leg": "E2", "n": needed}

    per_task = {
        task: {
            "class": task_class(task),
            "f_L0": fraction_json(rates["L0"][task]),
            "f_L1": fraction_json(rates["L1"][task]),
            "f_L2": fraction_json(rates["L2"][task]),
            "d1": fraction_json(d1[task]),
            "d2": fraction_json(d2[task]),
        }
        for task in tasks
    }
    token_breakdown: dict[str, Any] = {}
    for arm in ARMS:
        parent: dict[str, int] = {}
        surface: dict[str, int] = {}
        codex_total: int | None = 0
        for row in base_rows:
            if row["arm"] != arm:
                continue
            for model, count in row["output_tokens"]["parent"].items():
                parent[model] = parent.get(model, 0) + count
            for model, count in row["output_tokens"]["surface_close"].items():
                surface[model] = surface.get(model, 0) + count
            if row["codex_tokens_total"] is None:
                codex_total = None
            elif codex_total is not None:
                codex_total += row["codex_tokens_total"]
        token_breakdown[arm] = {
            "parent": parent,
            "surface_close": surface,
            "codex_total": codex_total,
            "total": token_sums[arm],
        }
    harness_rows = [row for row in base_rows if row["arm"] != "L0"]
    l2_rows = [row for row in base_rows if row["arm"] == "L2"]
    l2_by_task = {task: [row for row in l2_rows if row["task"] == task] for task in tasks}
    diff_changed_by_task = {
        task: (
            True if any(row["diff_changed_by_pair"] is True for row in task_rows)
            else None if any(row["diff_changed_by_pair"] is None for row in task_rows)
            else False
        )
        for task, task_rows in l2_by_task.items()
    }
    diagnostics = {
        "verification_bullets_median": fraction_json(median([row["verification_bullets"] for row in harness_rows])),
        "fix_round_ran": {
            "count": sum(any(row["fix_round_ran"] is True for row in task_rows) for task_rows in l2_by_task.values()),
            "panel_size": len(tasks),
        },
        "diff_changed_by_pair": {
            "count": sum(changed is True for changed in diff_changed_by_task.values()),
            "unknown_count": sum(changed is None for changed in diff_changed_by_task.values()),
            "panel_size": len(tasks),
        },
        "pair_timeout_count": sum(row["pair_timeout"] is True for row in l2_rows),
    }
    return {
        "terminal_kind": "NEEDS_TOPUP" if topup else "LIFT",
        "panel_saturated": False,
        "model": run_metadata["model"],
        "panel": panel_name,
        "run_id": run_metadata["run_id"],
        "inputs": {
            "rows_sha256": rows_sha256,
            "params_sha256": params_sha256,
            "panel_sha256": sha256_bytes(canonical_json(panel)),
            "corpus_manifest_sha256": params["corpus"]["manifest_sha256"],
            "corpus_tree_sha256": params["corpus"]["tree_sha256"],
            "calibrator_sha256": params["calibrator"]["sha256"],
            "claude_binary_sha256": params["claude"]["binary_sha256"],
            "codex_binary_sha256": params["pair"]["codex_binary_sha256"],
            "staged_intervention_sha256": params["harness"]["staged_intervention_sha256"],
            "apparatus_sha256": params["apparatus_sha256"],
            "run_metadata_sha256": sha256_bytes(canonical_json(run_metadata)),
        },
        "Q1": q1,
        "Q2": q2,
        "E1": {"decision": e1, "wall": e1_wall, "tokens": e1_tok},
        "E2": {"decision": e2, "wall": e2_wall, "tokens": e2_tok},
        "ratios": {
            "N1_wall": n1_wall,
            "N1_tok": n1_tok,
            "M2_wall": m2_wall,
            "M2_tok": m2_tok,
            "wall_medians_ms": {arm: fraction_json(value) for arm, value in wall_medians.items()},
            "output_token_sums": token_sums,
        },
        "topup": topup,
        "per_task": per_task,
        "token_breakdown": token_breakdown,
        "diagnostics": diagnostics,
    }


def write_verdict(verdict: dict[str, Any], path: pathlib.Path) -> tuple[dict[str, Any], str]:
    without = dict(verdict)
    without.pop("receipt", None)
    receipt = sha256_bytes(canonical_json(without))
    final = dict(without)
    final["receipt"] = receipt
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(final))
    return final, receipt


def terminal_line(verdict: dict[str, Any], receipt: str, rows_path: pathlib.Path) -> str:
    if verdict["terminal_kind"] == "PANEL_SATURATED":
        return "PANEL_SATURATED"
    if verdict["terminal_kind"] == "NEEDS_TOPUP":
        topup = verdict["topup"]
        return (
            "NEEDS_TOPUP "
            f"python3 benchmark/layer-lift/run-lift-panel.py topup "
            f"--model {verdict['model']} --panel {verdict['panel']} "
            f"--out {rows_path.parent} --run-id {verdict['run_id']} "
            f"--leg {topup['leg']} --n {topup['n']}"
        )
    return (
        f"LIFT-0113: Q1={verdict['Q1']['decision']} E1={verdict['E1']['decision']} "
        f"Q2={verdict['Q2']['decision']} E2={verdict['E2']['decision']} "
        f"M={verdict['model']} panel={verdict['panel']} receipt={receipt}"
    )


def fixture_params() -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    tasks = ["EQ3-AF1", "EQ3-BD1", "EQ3-MI1", "EQ3-UA1"]
    panel = {"calibrator_sha256": "0" * 64, "rule": "fixture", "tasks": {cls: [f"EQ3-{cls}1"] for cls in ("AF", "BD", "MI", "UA")}}
    params = {
        "base_reps": {"L0": 2, "L1": 1, "L2": 1},
        "bootstrap": {"seed": 20260903, "resamples": 2000},
        "delta": "3/20",
        "saturation_threshold": "1/10",
        "corpus": {"manifest_path": "/fixture", "manifest_sha256": "1" * 64, "tree_sha256": "2" * 64},
        "calibrator": {"path": "/fixture", "sha256": "3" * 64},
        "claude": {"binary_path": "/fixture", "binary_sha256": "5" * 64},
        "harness": {"staged_intervention_sha256": "6" * 64},
        "pair": {
            "model_id": "gpt-fixture", "effective_effort": "medium",
            "codex_cli_version": "0.fixture", "codex_binary_sha256": "7" * 64,
        },
        "apparatus_sha256": "9" * 64,
    }
    return params, panel, tasks


def fixture_row(
    arm: str,
    task: str,
    rep: int,
    ship: Fraction,
    *,
    attempt: int = 1,
    topup: bool = False,
    infra: bool = False,
    wall: int = 10,
    tokens: int = 10,
    terminal: str | None = None,
    tree: Fraction | None = None,
) -> dict[str, Any]:
    terminal = terminal or ("BARE" if arm == "L0" else "PASS")
    tree = ship if tree is None else tree
    if terminal == "TIMEOUT" or terminal.startswith("BLOCKED:"):
        ship = Fraction(1)
    row = {
        "run_id": f"fixture:a{attempt}:{arm}:{task}:r{rep}", "attempt": attempt,
        "arm": arm, "task": task, "class": task_class(task), "rep": rep,
        "topup": topup, "model_requested": "claude-fixture", "model_attested": "claude-fixture",
        "surface_close_ran": False, "surface_model_attested": None,
        "pair_judge_ran": True if arm == "L2" else None,
        "pair_model_attested": "gpt-fixture" if arm == "L2" else None,
        "pair_effort_attested": "medium" if arm == "L2" else None,
        "pair_cli_version_attested": "0.fixture" if arm == "L2" else None,
        "pair_timeout": terminal == "TIMEOUT" and arm == "L2",
        "codex_tokens_total": None if terminal == "TIMEOUT" else 0,
        "terminal": terminal, "f_tree": fraction_json(tree), "f_ship": fraction_json(ship),
        "manifestations_total": tree.denominator, "manifestations_failed": tree.numerator,
        "catastrophic": False, "incomplete": False, "infra_invalid": infra,
        "infra_reason": "fixture infra" if infra else None, "wall_ms": wall,
        "output_tokens": {"parent": {"claude-fixture": tokens}, "surface_close": {}},
        "output_tokens_total": None if terminal == "TIMEOUT" else tokens,
        "verification_bullets": None if arm == "L0" else 1,
        "fix_round_ran": False if arm == "L2" else None,
        "diff_changed_by_pair": False if arm == "L2" else None,
        "prompt_sha256": "8" * 64, "goal_sha256": "8" * 64,
        "staged_intervention_sha256": None if arm == "L0" else "6" * 64,
        "claude_binary_sha256": "5" * 64,
        "started_at": "2026-09-03T00:00:00Z", "finished_at": "2026-09-03T00:00:01Z",
    }
    return row


def fixture_rows(value: Fraction = Fraction(1, 2)) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    params, panel, tasks = fixture_params()
    rows = []
    for task in tasks:
        rows.extend([fixture_row("L0", task, 1, value), fixture_row("L0", task, 2, value)])
        rows.append(fixture_row("L1", task, 1, value))
        rows.append(fixture_row("L2", task, 1, value))
    return params, panel, rows


def invoke_fixture(rows: list[dict[str, Any]], params: dict[str, Any], panel: dict[str, Any], errors: list[str] | None = None) -> dict[str, Any]:
    return score(
        rows, params, panel_name="quick", panel=panel,
        rows_sha256="a" * 64, params_sha256="b" * 64,
        run_metadata={"model": "claude-fixture", "panel": "quick", "run_id": "fixture"},
        injected_frozen_errors=errors,
    )


def self_test_a15() -> None:
    params, panel, rows = fixture_rows()
    index = next(i for i, row in enumerate(rows) if row["arm"] == "L2")
    retained = fixture_row("L2", rows[index]["task"], 1, Fraction(1), terminal="BLOCKED:fixture")
    retained.update(pair_judge_ran=False, pair_model_attested=None, pair_effort_attested=None,
                    pair_cli_version_attested=None)
    rows[index] = retained
    assert validate_row(retained, 1) == []
    result = invoke_fixture(rows, params, panel)
    assert result["per_task"][retained["task"]]["f_L2"] == "1/1"
    for value in (None, 0, 1, "false"):
        assert validate_row({**retained, "pair_judge_ran": value}, 1), value
    missing = dict(retained)
    del missing["pair_judge_ran"]
    assert validate_row(missing, 1)
    for patch in ({"terminal": "PASS"}, {"terminal": "PASS_WITH_ISSUES"}, {"terminal": "TIMEOUT"},
                  {"pair_model_attested": "gpt-fixture"}, {"pair_effort_attested": "medium"},
                  {"pair_cli_version_attested": "0.fixture"}, {"codex_tokens_total": 1}, {"pair_timeout": True}):
        assert validate_row({**retained, **patch}, 1), patch
    for arm in ("L0", "L1"):
        assert validate_row({**fixture_row(arm, "EQ3-AF1", 1, Fraction(1)), "pair_judge_ran": False}, 1)
    for value in (True, None):
        timeout = fixture_row("L2", retained["task"], 1, Fraction(1), terminal="TIMEOUT")
        timeout["pair_judge_ran"] = value
        assert validate_row(timeout, 1) == []
        invoke_fixture([timeout if i == index else row for i, row in enumerate(rows)], params, panel)
        assert validate_row({**timeout, "pair_judge_ran": False}, 1)
    for patch in ({"pair_judge_ran": True}, {"pair_judge_ran": True, "pair_model_attested": "wrong"},
                  {"terminal": "TIMEOUT", "pair_judge_ran": None, "pair_model_attested": "wrong",
                   "codex_tokens_total": None, "output_tokens_total": None}):
        try:
            invoke_fixture([{**retained, **patch} if i == index else row for i, row in enumerate(rows)], params, panel)
        except ScoreError as exc:
            assert "attestation mismatch" in str(exc)
        else:
            raise AssertionError(patch)
    retry = {**retained, "attempt": 2, "run_id": retained["run_id"].replace(":a1:", ":a2:")}
    try:
        invoke_fixture(rows + [retry], params, panel)
    except ScoreError as exc:
        assert "retry does not replace" in str(exc)
    else:
        raise AssertionError("retained product failure was replaced")
    rows[index] = {**retained, "infra_invalid": True, "infra_reason": "engine unavailable"}
    invoke_fixture(rows + [retry], params, panel)
    print("a15-score strict carrier, retained failure, identity, TIMEOUT, replacement: PASS")

    for repetitions in ({"L0": 4, "L1": 1, "L2": 1}, {"L0": 4, "L1": 4, "L2": 4}, {"L0": 1, "L1": 4, "L2": 1}):
        for ratio in (2, 8):
            params, panel, tasks = fixture_params()
            params["base_reps"] = repetitions
            rows = [fixture_row(arm, task, rep, Fraction(1, 2), tokens={"L0": 10, "L1": 10 * ratio, "L2": 10 * ratio * ratio}[arm])
                    for task in tasks for arm in ARMS for rep in range(1, repetitions[arm] + 1)]
            # Split the same within-run total across parent, SURFACE_CLOSE, and pair usage.
            for row in rows:
                if row["arm"] != "L0":
                    row["surface_close_ran"] = True
                    row["surface_model_attested"] = "claude-sonnet-5"
                    row["output_tokens"]["surface_close"] = {"claude-sonnet-5": 3}
                    row["output_tokens"]["parent"]["claude-fixture"] -= 3
                if row["arm"] == "L2":
                    row["codex_tokens_total"] = 7
                    row["output_tokens"]["parent"]["claude-fixture"] -= 7
                assert validate_row(row, 1) == []
            result = invoke_fixture(rows, params, panel)
            assert result["ratios"]["N1_tok"] == ratio and result["ratios"]["M2_tok"] == ratio
            assert result["ratios"]["N1_wall"] == result["ratios"]["M2_wall"] == 1
            totals = {arm: sum(row["output_tokens_total"] for row in rows if row["arm"] == arm) for arm in ARMS}
            assert result["ratios"]["output_token_sums"] == totals
            topups = [fixture_row(arm, task, rep, Fraction(1, 2), topup=True, tokens=9999)
                      for task in tasks for arm in ("L0", "L1") for rep in range(repetitions[arm] + 1, ratio + 1)]
            topped = invoke_fixture(rows + topups, params, panel)
            assert topped["ratios"] == result["ratios"] and topped["Q1"] == result["Q1"] and topped["Q2"] == result["Q2"]
            timeout = fixture_row("L1", tasks[0], 1, Fraction(1), terminal="TIMEOUT")
            unknown = invoke_fixture([timeout if (row["arm"], row["task"], row["rep"]) == ("L1", tasks[0], 1) else row for row in rows], params, panel)
            assert unknown["ratios"]["N1_tok"] is None and unknown["ratios"]["M2_tok"] is None
            assert unknown["E1"]["tokens"]["decision"] == unknown["E2"]["tokens"]["decision"] == "INCONCLUSIVE"
            print("a15-score", repetitions, "per-run ratio", ratio, "N1_tok=M2_tok=" + str(ratio), "topups/unknown: PASS")


def self_test() -> int:
    self_test_a15()
    names: list[str] = []

    params_registered = read_object(DEFAULT_PARAMS)
    validate_apparatus(params_registered)
    with tempfile.TemporaryDirectory(prefix="score-apparatus-") as raw:
        root = pathlib.Path(raw)
        for relative in APPARATUS_FILES:
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO / relative, destination)
        launcher = root / "benchmark/ceiling/scripts/claude-isolation.py"
        launcher.write_bytes(launcher.read_bytes() + b"# drift\n")
        try:
            validate_apparatus(params_registered, root)
        except ScoreError as exc:
            assert "apparatus digest mismatch" in str(exc)
        else:
            raise AssertionError("score accepted normalized apparatus drift")
    names.append("normalized-apparatus-digest-refusal")

    delta = Fraction(3, 20)
    values = [Fraction(-3, 10), -delta, Fraction(-1, 10), Fraction(0), Fraction(1, 10), delta, Fraction(3, 10)]
    for low in values:
        for high in values:
            if low > high:
                continue
            flags = [
                low > delta,
                low > -delta and high < delta,
                high < -delta,
                not (low > delta or (low > -delta and high < delta) or high < -delta),
            ]
            assert sum(flags) == 1
            assert q_decision(low, high, delta) in {"LIFT", "NULL", "HARM", "INCONCLUSIVE"}
    names.append("q-decision-partition")

    params, panel, rows = fixture_rows()
    # Complete EFFICIENT/INEFFICIENT/INCONCLUSIVE plus incomplete monotone/top-up paths.
    assert e_decision(Fraction(1, 10), Fraction(1, 5)) == "EFFICIENT"
    assert e_decision(Fraction(-1, 5), Fraction(-1, 10)) == "INEFFICIENT"
    assert e_decision(Fraction(-1, 10), Fraction(1, 10)) == "INCONCLUSIVE"
    # Reach both incomplete branches through the production dimension function.
    tasks = [task for cls in sorted(panel["tasks"]) for task in panel["tasks"][cls]]
    base_latest = latest(rows)
    arm_rates = per_task_arm(base_latest, tasks, params)
    need = efficiency_dimension(cheaper="L0", expensive="L1", n=3, tasks=tasks, all_latest=base_latest, arm_rates=arm_rates, params=params)
    assert need["decision"] == "NEEDS_TOPUP"
    harmed_rows = [dict(row, f_ship="0/1") if row["arm"] == "L0" else row for row in rows]
    harmed_latest = latest(harmed_rows)
    harmed_rates = per_task_arm(harmed_latest, tasks, params)
    monotone = efficiency_dimension(cheaper="L0", expensive="L1", n=3, tasks=tasks, all_latest=harmed_latest, arm_rates=harmed_rates, params=params)
    assert monotone["decision"] == "INEFFICIENT"
    assert aggregate_efficiency(
        {"decision": "INEFFICIENT"}, {"decision": "NEEDS_TOPUP"}
    ) == "INEFFICIENT"
    assert aggregate_efficiency(
        {"decision": "EFFICIENT"}, {"decision": "EFFICIENT"}
    ) == "EFFICIENT"
    names.append("efficiency-and-monotone-topup-patterns")

    blocked = fixture_row("L1", "EQ3-AF1", 1, Fraction(1, 3), terminal="BLOCKED:fixture", tree=Fraction(1, 3))
    timeout = fixture_row("L2", "EQ3-AF1", 1, Fraction(2, 3), terminal="TIMEOUT", tree=Fraction(2, 3))
    l0_timeout = fixture_row("L0", "EQ3-AF1", 1, Fraction(1, 4), terminal="TIMEOUT", tree=Fraction(1, 4))
    l0_timeout["model_attested"] = None
    assert blocked["f_ship"] == timeout["f_ship"] == l0_timeout["f_ship"] == "1/1"
    assert blocked["f_tree"] == "1/3" and timeout["f_tree"] == "2/3"
    assert timeout["output_tokens_total"] is None and timeout["codex_tokens_total"] is None
    assert l0_timeout["output_tokens_total"] is None and l0_timeout["codex_tokens_total"] is None
    assert validate_row(blocked, 1) == [] and validate_row(timeout, 2) == []
    assert validate_row(l0_timeout, 3) == []
    names.append("blocked-timeout-ship-channel")

    params, panel, rows = fixture_rows()
    l1_timeout = fixture_row(
        "L1", "EQ3-AF1", 1, Fraction(1, 2), terminal="TIMEOUT", tree=Fraction(1, 2),
    )
    rows = [
        l1_timeout if (row["arm"], row["task"], row["rep"]) == ("L1", "EQ3-AF1", 1) else row
        for row in rows
    ]
    result = invoke_fixture(rows, params, panel)
    timeout_id = l1_timeout["run_id"]
    assert result["per_task"]["EQ3-AF1"]["f_L1"] == "1/1"
    assert result["E1"]["tokens"] == {
        "decision": "INCONCLUSIVE", "unknown_timeout_rows": [timeout_id],
    }
    assert result["E2"]["tokens"] == {
        "decision": "INCONCLUSIVE", "unknown_timeout_rows": [timeout_id],
    }
    assert result["ratios"]["N1_tok"] is None and result["ratios"]["M2_tok"] is None
    assert "unknown_timeout_rows" not in result["E1"]["wall"]
    names.append("timeout-unknown-token-leg-inconclusive")

    params, panel, rows = fixture_rows()
    tasks = [task for cls in sorted(panel["tasks"]) for task in panel["tasks"][cls]]
    for row in rows:
        if row["arm"] == "L1":
            row["output_tokens"] = {"parent": {"claude-fixture": 50}, "surface_close": {}}
            row["output_tokens_total"] = 50
    topups = [
        fixture_row(
            "L0", task, rep, Fraction(1, 2), topup=True,
            terminal="TIMEOUT" if task == tasks[0] and rep == 3 else None,
        )
        for task in tasks for rep in range(3, 6)
    ]
    rows.extend(topups)
    result = invoke_fixture(rows, params, panel)
    assert result["ratios"]["N1_tok"] == 5
    assert result["E1"]["tokens"] == {
        "decision": "INCONCLUSIVE",
        "unknown_timeout_rows": [topups[0]["run_id"]],
    }
    names.append("topup-timeout-token-leg-inconclusive")

    params, panel, rows = fixture_rows()
    rows[0]["model_attested"] = None
    try:
        invoke_fixture(rows, params, panel)
    except ScoreError as exc:
        assert "parent model attestation mismatch" in str(exc)
    else:
        raise AssertionError("clean missing model attestation was scored")
    names.append("missing-parent-attestation-unscorable")

    params, panel, rows = fixture_rows()
    rows[0]["incomplete"] = True
    rows[0]["f_ship"] = "1/1"
    assert validate_row(rows[0], 1) == []
    result = invoke_fixture(rows, params, panel)
    assert result["per_task"][rows[0]["task"]]["f_L0"] == "3/4"
    names.append("clean-incomplete-ship-penalty")

    params, panel, rows = fixture_rows()
    rows[0]["infra_invalid"] = True
    rows[0]["infra_reason"] = "fixture"
    try:
        invoke_fixture(rows, params, panel)
        raise AssertionError("infra-invalid fixture scored")
    except ScoreError as exc:
        assert "infra-invalid rows excluded" in str(exc)
    names.append("infra-invalid-excluded-and-reported")

    params, panel, rows = fixture_rows()
    old = rows[0]
    old["infra_invalid"] = True
    old["infra_reason"] = "first attempt"
    replacement = fixture_row("L0", old["task"], old["rep"], Fraction(3, 4), attempt=2)
    rows.append(replacement)
    result = invoke_fixture(rows, params, panel)
    assert result["per_task"][old["task"]]["f_L0"] == "5/8"
    names.append("latest-attempt-wins")

    params, panel, rows = fixture_rows()
    baseline = invoke_fixture(rows, params, panel)["Q1"]
    for task in [task for cls in sorted(panel["tasks"]) for task in panel["tasks"][cls]]:
        rows.append(fixture_row("L0", task, 3, Fraction(0), topup=True))
    assert invoke_fixture(rows, params, panel)["Q1"] == baseline
    names.append("topup-excluded-from-quality")

    params, panel, rows = fixture_rows()
    tasks = [task for cls in sorted(panel["tasks"]) for task in panel["tasks"][cls]]
    params["base_reps"]["L2"] = 2
    rows.extend(fixture_row("L2", task, 2, Fraction(1, 2)) for task in tasks)
    l2_by_task = {
        task: [row for row in rows if row["arm"] == "L2" and row["task"] == task]
        for task in tasks
    }
    assert all(len(task_rows) == 2 for task_rows in l2_by_task.values())
    for row in l2_by_task[tasks[0]]:
        row["fix_round_ran"] = True
    l2_by_task[tasks[0]][0]["diff_changed_by_pair"] = True
    l2_by_task[tasks[0]][1]["diff_changed_by_pair"] = None
    l2_by_task[tasks[1]][0].update(
        pair_timeout=True,
        codex_tokens_total=None, output_tokens_total=None,
    )
    l2_by_task[tasks[2]][0]["diff_changed_by_pair"] = None
    assert validate_row(l2_by_task[tasks[1]][0], 1) == []
    diagnostics = invoke_fixture(rows, params, panel)["diagnostics"]
    assert diagnostics == {
        "verification_bullets_median": "1/1",
        "fix_round_ran": {"count": 1, "panel_size": 4},
        "diff_changed_by_pair": {"count": 1, "unknown_count": 1, "panel_size": 4},
        "pair_timeout_count": 1,
    }
    names.append("registered-diagnostics-summary")

    values_by_task = {
        "EQ3-AF1": Fraction(0), "EQ3-AF2": Fraction(1),
        "EQ3-BD1": Fraction(1, 4), "EQ3-BD2": Fraction(1, 4),
        "EQ3-MI1": Fraction(1, 2), "EQ3-MI2": Fraction(1, 2),
        "EQ3-UA1": Fraction(3, 4), "EQ3-UA2": Fraction(3, 4),
    }
    first = grouped_bootstrap(values_by_task, seed=20260903, resamples=2000)
    second = grouped_bootstrap(values_by_task, seed=20260903, resamples=2000)
    assert first == second and first[0] == Fraction(1, 2) and first[1][0] < first[1][1]
    names.append("stratified-bootstrap-determinism-and-mixture")

    params, panel, rows = fixture_rows()
    try:
        invoke_fixture(rows, params, panel, ["synthetic digest mismatch"])
        raise AssertionError("digest mismatch scored")
    except ScoreError as exc:
        assert "runner is not frozen" in str(exc)
    names.append("digest-mismatch-refusal-through-score")

    params, panel, rows = fixture_rows(Fraction(0))
    result = invoke_fixture(rows, params, panel)
    assert result["terminal_kind"] == "PANEL_SATURATED"
    names.append("saturation-terminal")

    params, panel, rows = fixture_rows(Fraction(0))
    l0_only = [row for row in rows if row["arm"] == "L0"]
    invalid_l1 = fixture_row("L1", "EQ3-AF1", 1, Fraction(1), infra=True)
    result = invoke_fixture([*l0_only, invalid_l1], params, panel)
    assert result["terminal_kind"] == "PANEL_SATURATED"
    names.append("saturation-before-other-arms")

    print(f"PASS score-lift self-test {len(names)}/{len(names)}: {', '.join(names)}")
    return 0


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="iter-0113 scorer; real score refuses until TBD-FREEZE pins are replaced")
    ap.add_argument("--self-test", action="store_true")
    sub = ap.add_subparsers(dest="command")
    score_parser = sub.add_parser("score")
    score_parser.add_argument("--rows", required=True, type=pathlib.Path)
    score_parser.add_argument("--params", required=True, type=pathlib.Path)
    score_parser.add_argument("--out", required=True, type=pathlib.Path)
    return ap


def main() -> int:
    args = parser().parse_args()
    try:
        validate_apparatus(read_object(DEFAULT_PARAMS))
        if args.self_test:
            return self_test()
        if args.command != "score":
            raise ScoreError("choose --self-test or score")
        params = read_object(args.params)
        errors = frozen_errors(args.params, params)
        if errors:
            raise ScoreError("runner is not frozen: " + "; ".join(errors))
        rows, rows_digest = load_rows(args.rows)
        metadata_path = args.rows.parent / "run-metadata.json"
        metadata = read_object(metadata_path)
        panel_name = metadata.get("panel")
        if panel_name not in {"quick", "full"}:
            raise ScoreError("run metadata panel invalid")
        panel = read_object(DEFAULT_PANEL)
        metadata_pins = {
            "params_sha256": sha256_file(args.params),
            "apparatus_sha256": params["apparatus_sha256"],
        }
        mismatched_metadata = [
            key for key, expected in metadata_pins.items() if metadata.get(key) != expected
        ]
        if mismatched_metadata:
            raise ScoreError(f"run metadata digest mismatch: {mismatched_metadata}")
        verdict = score(
            rows, params, panel_name=panel_name, panel=panel,
            rows_sha256=rows_digest, params_sha256=sha256_file(args.params),
            run_metadata=metadata,
        )
        final, receipt = write_verdict(verdict, args.out)
        print(f"pair_timeouts={final.get('diagnostics', {}).get('pair_timeout_count', 0)}")
        print(terminal_line(final, receipt, args.rows))
        return 0
    except (OSError, ValueError, KeyError, ScoreError) as exc:
        print(f"UNSCORED: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
