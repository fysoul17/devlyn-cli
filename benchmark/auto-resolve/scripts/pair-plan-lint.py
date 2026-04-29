#!/usr/bin/env python3
"""
pair-plan-lint.py — validate a `pair-plan.json` against its registry and
the `pair-plan-schema.md` hard rules.

Inputs:
  --plan <path>      path to pair-plan.json (required)
  --registry <path>  override registry path (default: resolved from
                     plan.source.canonical_id_registry_path)
  --quiet            suppress stderr human summary

Output:
  stdout — `{"ok": bool, "errors": [{code, message, ...}, ...]}` (machine-readable)
  stderr — short human summary unless --quiet (skipped on --quiet)

Exit code:
  0 on pass, 1 on fail.

Schema source: config/skills/_shared/pair-plan-schema.md (iter-0022 ship).
"""
import argparse
import copy
import hashlib
import json
import pathlib
import sys

SCHEMA_VERSION = "1"
AUTHORITY_ORDER_CANONICAL = [
    "spec.md",
    "expected.json/rubric",
    "phase prompt",
    "model preference",
]
REQUIRED_TOP_LEVEL = [
    "schema_version",
    "plan_status",
    "planning_mode",
    "source",
    "authority_order",
    "rounds",
    "accepted_invariants",
    "rejected_alternatives",
    "unresolved",
    "escalated_to_user",
    "model_stamps",
]
REQUIRED_SOURCE_FIELDS = [
    "spec_path",
    "spec_sha256",
    "rubric_path",
    "rubric_sha256",
    "canonical_id_registry_path",
    "canonical_id_registry_sha256",
]


# ---------------------------------------------------------------------------
# JSON loading with strict-keys.
# ---------------------------------------------------------------------------
def _strict_pairs(pairs):
    keys = [k for k, _ in pairs]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate key in pair-plan.json")
    return dict(pairs)


def load_strict_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f, object_pairs_hook=_strict_pairs)


# ---------------------------------------------------------------------------
# Hash helpers.
# ---------------------------------------------------------------------------
def file_sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def canonical_pre_stamp_sha256(plan):
    pre = copy.deepcopy(plan)
    pre["model_stamps"] = {}
    s = json.dumps(
        pre,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Individual checks (each returns a list of error dicts).
# ---------------------------------------------------------------------------
PLAN_STATUS_VALID = {"final", "blocked", "draft"}
PLANNING_MODE_VALID = {"solo", "pair"}
ACCEPTED_INVARIANT_REQUIRED_FIELDS = ("id", "source_refs", "operational_check", "authority")


def check_top_level_shape(plan):
    errs = []
    if not isinstance(plan, dict):
        return [{"code": "plan_not_object", "message": "pair-plan.json root must be a JSON object"}]
    for f in REQUIRED_TOP_LEVEL:
        if f not in plan:
            errs.append({"code": "missing_top_level_field", "field": f,
                         "message": f"required top-level field missing: {f}"})
    if plan.get("schema_version") != SCHEMA_VERSION:
        errs.append({"code": "schema_version_mismatch",
                     "expected": SCHEMA_VERSION,
                     "got": plan.get("schema_version"),
                     "message": f"schema_version must be {SCHEMA_VERSION!r}"})
    if plan.get("plan_status") not in PLAN_STATUS_VALID:
        errs.append({"code": "plan_status_invalid",
                     "got": plan.get("plan_status"),
                     "message": f"plan_status must be one of {sorted(PLAN_STATUS_VALID)}"})
    if plan.get("planning_mode") not in PLANNING_MODE_VALID:
        errs.append({"code": "planning_mode_invalid",
                     "got": plan.get("planning_mode"),
                     "message": f"planning_mode must be one of {sorted(PLANNING_MODE_VALID)}"})
    return errs


def check_accepted_invariants_shape(plan):
    """Each accepted_invariants[] item MUST carry id + source_refs + operational_check + authority.
    A plan with empty/missing operational_check has nothing for BUILD/EVAL/CRITIC to enforce."""
    errs = []
    for i, item in enumerate(plan.get("accepted_invariants") or []):
        if not isinstance(item, dict):
            errs.append({"code": "accepted_invariant_not_object",
                         "index": i,
                         "message": f"accepted_invariants[{i}] is not a JSON object"})
            continue
        for f in ACCEPTED_INVARIANT_REQUIRED_FIELDS:
            if f not in item or item[f] in (None, "", []):
                errs.append({"code": "accepted_invariant_missing_field",
                             "index": i,
                             "id": item.get("id"),
                             "field": f,
                             "message": f"accepted_invariants[{i}].{f} missing or empty"})
    return errs


def check_registry_shape(registry):
    """Lint MUST reject unsorted required_invariants and unknown top-level fields per schema doc."""
    errs = []
    allowed = {"schema_version", "fixture_id", "generated_at", "generated_from", "required_invariants"}
    extra = sorted(set(registry.keys()) - allowed)
    if extra:
        errs.append({"code": "registry_unknown_field",
                     "fields": extra,
                     "message": f"canonical_id_registry.json has unknown top-level fields: {extra}"})
    inv = registry.get("required_invariants") or []
    ids = [e.get("id") for e in inv]
    if ids != sorted(ids):
        errs.append({"code": "registry_unsorted",
                     "message": "required_invariants[] must be sorted lexicographically by id"})
    return errs


def check_authority_order(plan):
    if plan.get("authority_order") != AUTHORITY_ORDER_CANONICAL:
        return [{"code": "authority_order_drift",
                 "expected": AUTHORITY_ORDER_CANONICAL,
                 "got": plan.get("authority_order"),
                 "message": "authority_order must be the canonical 4-string snapshot"}]
    return []


def check_unresolved_status(plan):
    unresolved = plan.get("unresolved") or []
    status = plan.get("plan_status")
    if len(unresolved) > 0 and status not in ("blocked", "draft"):
        return [{"code": "unresolved_with_final_status",
                 "unresolved_count": len(unresolved),
                 "plan_status": status,
                 "message": "unresolved is non-empty but plan_status is not 'blocked' or 'draft'"}]
    return []


def check_escalated_status(plan):
    escalated = plan.get("escalated_to_user") or []
    status = plan.get("plan_status")
    errs = []
    if escalated:
        if status in ("blocked", "draft"):
            return errs
        for i, item in enumerate(escalated):
            if "user_resolution" not in item:
                errs.append({"code": "escalated_without_resolution",
                             "index": i,
                             "id": item.get("id"),
                             "message": "escalated_to_user[] item missing user_resolution while plan_status is final"})
    return errs


def check_planning_mode_rounds(plan):
    mode = plan.get("planning_mode")
    rounds = plan.get("rounds") or []
    if mode == "pair" and len(rounds) < 1:
        return [{"code": "pair_mode_no_rounds",
                 "message": "planning_mode=pair requires rounds.length >= 1"}]
    if mode == "solo" and len(rounds) != 0:
        return [{"code": "solo_mode_with_rounds",
                 "message": "planning_mode=solo requires rounds.length == 0"}]
    return []


def check_accepted_ids_in_registry(plan, registry):
    registry_ids = {e["id"] for e in registry.get("required_invariants", [])}
    errs = []
    for i, item in enumerate(plan.get("accepted_invariants") or []):
        rid = item.get("id")
        if rid not in registry_ids:
            errs.append({"code": "accepted_id_not_in_registry",
                         "index": i,
                         "id": rid,
                         "message": f"accepted_invariants[{i}].id={rid!r} not present in registry"})
    return errs


def check_registry_coverage(plan, registry):
    """Every registry required_invariants[].id must be accounted for in a final plan.

    Coverage is enforced only when plan_status == "final" — draft / blocked
    plans are allowed to have un-decided ids in `unresolved[]` (Hard Rule #1
    in pair-plan-schema.md) without tripping coverage. `unresolved[]` items
    of shape `{id, note}` count as accounted-for at the structural level.
    """
    if plan.get("plan_status") != "final":
        return []
    registry_ids = [e["id"] for e in registry.get("required_invariants", [])]
    accepted = {item.get("id") for item in (plan.get("accepted_invariants") or [])}
    rejected_conflicts = set()
    for item in plan.get("rejected_alternatives") or []:
        for cid in item.get("conflicts_with_ids", []) or []:
            rejected_conflicts.add(cid)
    escalated = {item.get("id") for item in (plan.get("escalated_to_user") or [])}
    unresolved = {item.get("id") for item in (plan.get("unresolved") or []) if isinstance(item, dict)}
    accounted = accepted | rejected_conflicts | escalated | unresolved
    errs = []
    for rid in registry_ids:
        if rid not in accounted:
            errs.append({"code": "missing_required_id",
                         "id": rid,
                         "message": f"registry id {rid!r} is not in accepted_invariants, rejected_alternatives.conflicts_with_ids, escalated_to_user, or unresolved"})
    return errs


def check_model_stamps(plan):
    stamps = plan.get("model_stamps") or {}
    errs = []
    for who in ("claude", "codex"):
        s = stamps.get(who)
        if not isinstance(s, dict):
            errs.append({"code": "stamp_missing", "who": who,
                         "message": f"model_stamps.{who} missing or not an object"})
            continue
        if s.get("status") not in ("sign", "block"):
            errs.append({"code": "stamp_status_invalid", "who": who,
                         "got": s.get("status"),
                         "message": f"model_stamps.{who}.status must be 'sign' or 'block'"})
        if "signed_plan_sha256" not in s:
            errs.append({"code": "stamp_sha_missing", "who": who,
                         "message": f"model_stamps.{who}.signed_plan_sha256 missing"})
    if plan.get("plan_status") == "final":
        for who in ("claude", "codex"):
            s = stamps.get(who) or {}
            if s.get("status") != "sign":
                errs.append({"code": "final_with_non_sign_stamp",
                             "who": who,
                             "status": s.get("status"),
                             "message": f"plan_status=final requires model_stamps.{who}.status=sign"})
    return errs


def check_signed_pre_stamp_sha(plan):
    expected = canonical_pre_stamp_sha256(plan)
    stamps = plan.get("model_stamps") or {}
    claude_sha = (stamps.get("claude") or {}).get("signed_plan_sha256")
    codex_sha = (stamps.get("codex") or {}).get("signed_plan_sha256")
    errs = []
    if claude_sha != codex_sha:
        errs.append({"code": "stamp_sha_disagree",
                     "claude_sha": claude_sha,
                     "codex_sha": codex_sha,
                     "message": "model_stamps.{claude,codex}.signed_plan_sha256 must be byte-identical"})
    for who, sha in [("claude", claude_sha), ("codex", codex_sha)]:
        if sha is not None and sha != expected:
            errs.append({"code": "stamp_sha_mismatch_canonical",
                         "who": who,
                         "got": sha,
                         "expected": expected,
                         "message": f"model_stamps.{who}.signed_plan_sha256 does not equal canonical pre-stamp sha"})
    return errs


def check_source_file_shas(plan, plan_path):
    """Each source.<x>_sha256 must equal the raw-bytes sha256 of the referenced file."""
    src = plan.get("source") or {}
    plan_dir = pathlib.Path(plan_path).resolve().parent
    errs = []
    pairs = [
        ("spec_path", "spec_sha256"),
        ("expected_path", "expected_sha256"),
        ("rubric_path", "rubric_sha256"),
        ("canonical_id_registry_path", "canonical_id_registry_sha256"),
    ]
    for path_field, sha_field in pairs:
        # expected_path is optional only when expected.json is genuinely absent;
        # rubric/registry/spec are always required.
        if path_field == "expected_path" and path_field not in src:
            continue
        if path_field not in src:
            errs.append({"code": "source_path_missing",
                         "field": path_field,
                         "message": f"source.{path_field} missing"})
            continue
        if sha_field not in src:
            errs.append({"code": "source_sha_missing",
                         "field": sha_field,
                         "message": f"source.{sha_field} missing"})
            continue
        path_str = src[path_field]
        path_abs = _resolve_repo_path(path_str, plan_dir)
        if path_abs is None:
            errs.append({"code": "source_path_unreadable",
                         "field": path_field,
                         "path": str(path_abs),
                         "message": f"source.{path_field} resolves to a path that does not exist"})
            continue
        actual = file_sha256(path_abs)
        if actual != src[sha_field]:
            errs.append({"code": "source_sha_drift",
                         "field": sha_field,
                         "expected": src[sha_field],
                         "actual": actual,
                         "path": str(path_abs),
                         "message": f"source.{sha_field} does not match raw-bytes sha of {path_str}"})
    return errs


# ---------------------------------------------------------------------------
# Path resolution — repo-relative paths in plan/source live in the repo,
# but the plan itself can be anywhere (e.g. /tmp during tests). Try three
# anchors in order: absolute path → git-root ancestor of plan_dir → cwd.
# Returns the first existing absolute path, or None if no anchor yields one.
# ---------------------------------------------------------------------------
def _git_root_ancestor(start):
    s = pathlib.Path(start).resolve()
    while s != s.parent:
        if (s / ".git").exists():
            return s
        s = s.parent
    return None


def _resolve_repo_path(path_str, plan_dir):
    p = pathlib.Path(path_str)
    if p.is_absolute():
        return p if p.exists() else None
    candidates = []
    repo_root = _git_root_ancestor(plan_dir)
    if repo_root is not None:
        candidates.append((repo_root / p).resolve())
    candidates.append((pathlib.Path.cwd() / p).resolve())
    candidates.append((plan_dir / p).resolve())
    seen = set()
    for c in candidates:
        if c in seen:
            continue
        seen.add(c)
        if c.exists():
            return c
    return None


def resolve_registry_from_plan(plan, plan_path):
    src = plan.get("source") or {}
    p = src.get("canonical_id_registry_path")
    if p is None:
        return None
    plan_dir = pathlib.Path(plan_path).resolve().parent
    return _resolve_repo_path(p, plan_dir)


# ---------------------------------------------------------------------------
# Top-level lint.
# ---------------------------------------------------------------------------
def lint(plan_path, registry_override=None):
    try:
        plan = load_strict_json(plan_path)
    except json.JSONDecodeError as e:
        return {"ok": False, "errors": [{"code": "plan_invalid_json",
                                          "message": f"plan parse error: {e}"}]}
    except ValueError as e:
        return {"ok": False, "errors": [{"code": "plan_duplicate_keys",
                                          "message": str(e)}]}
    except FileNotFoundError:
        return {"ok": False, "errors": [{"code": "plan_not_found",
                                          "message": f"plan file not found: {plan_path}"}]}

    # top-level shape first; skip downstream checks if shape is broken
    shape_errs = check_top_level_shape(plan)
    if shape_errs:
        return {"ok": False, "errors": shape_errs}

    # resolve registry
    if registry_override:
        registry_path = pathlib.Path(registry_override).resolve()
    else:
        registry_path = resolve_registry_from_plan(plan, plan_path)
    if registry_path is None or not registry_path.exists():
        return {"ok": False, "errors": [{
            "code": "registry_unreachable",
            "registry_path": str(registry_path) if registry_path else None,
            "message": "could not resolve canonical_id_registry; provide --registry or fix source.canonical_id_registry_path",
        }]}
    try:
        registry = load_strict_json(registry_path)
    except (json.JSONDecodeError, ValueError) as e:
        return {"ok": False, "errors": [{"code": "registry_invalid",
                                          "registry_path": str(registry_path),
                                          "message": str(e)}]}

    errors = []
    errors += check_registry_shape(registry)
    errors += check_authority_order(plan)
    errors += check_accepted_invariants_shape(plan)
    errors += check_unresolved_status(plan)
    errors += check_escalated_status(plan)
    errors += check_planning_mode_rounds(plan)
    errors += check_accepted_ids_in_registry(plan, registry)
    errors += check_registry_coverage(plan, registry)
    errors += check_model_stamps(plan)
    errors += check_signed_pre_stamp_sha(plan)
    errors += check_source_file_shas(plan, plan_path)

    return {"ok": not errors, "errors": errors,
            "registry_path": str(registry_path)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--registry", default=None,
                    help="Override registry path (default: source.canonical_id_registry_path)")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    verdict = lint(args.plan, registry_override=args.registry)

    print(json.dumps(verdict, indent=2, sort_keys=True))
    if not args.quiet:
        if verdict["ok"]:
            print(f"pair-plan-lint: PASS — {args.plan} (registry: {verdict.get('registry_path')})", file=sys.stderr)
        else:
            print(f"pair-plan-lint: FAIL — {args.plan} ({len(verdict['errors'])} error(s))", file=sys.stderr)
            for e in verdict["errors"]:
                print(f"  [{e.get('code')}] {e.get('message')}", file=sys.stderr)

    sys.exit(0 if verdict["ok"] else 1)


if __name__ == "__main__":
    main()
