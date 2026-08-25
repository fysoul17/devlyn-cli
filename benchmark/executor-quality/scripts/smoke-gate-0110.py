#!/usr/bin/env python3
"""Fail-closed registered-smoke gate for iter-0110."""
import argparse
import json
import pathlib


GROWTH_TOKENS = 4096
MINIMUM_FOOTPRINT = 2 * GROWTH_TOKENS
LEG_NAMES = ("custody", "growth", "attestation", "harvest")


def verdict(passed, reason=None, **details):
    result = {"passed": passed}
    if reason is not None:
        result["reason"] = reason
    result.update(details)
    return result


def failed_input(reason):
    return {
        "legs": {
            name: verdict(False, "session-input-invalid", detail=reason)
            for name in LEG_NAMES
        },
        "discriminability": verdict(False, "session-input-invalid", detail=reason),
        "verdict": "FAIL",
    }


def read_rows(path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        rows.append(json.loads(line))
    return rows


def is_context(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def non_carried_window(boundary):
    entries = boundary.get("usage_entries")
    if not isinstance(entries, list):
        return None, "usage-entries-malformed"
    contexts = []
    for entry in entries:
        if not isinstance(entry, dict):
            return None, "usage-entry-malformed"
        carried = entry.get("carried", False)
        if not isinstance(carried, bool):
            return None, "usage-entry-carried-malformed"
        if carried:
            continue
        context = entry.get("effective_context")
        if not is_context(context):
            return None, "effective-context-malformed"
        contexts.append(context)
    if not contexts:
        return None, "no-non-carried-usage"
    return (contexts[0], contexts[-1]), None


def custody_adjacency(rows, custody):
    if not isinstance(custody, dict) or not isinstance(custody.get("links"), list):
        return False, "custody-links-malformed"
    links = custody["links"]
    if len(links) != len(rows):
        return False, "custody-link-count-mismatch"
    previous_reported = None
    for position, (row, link) in enumerate(zip(rows, links), start=1):
        if not isinstance(row, dict) or not isinstance(link, dict):
            return False, "custody-link-malformed"
        if link.get("position_index") != position:
            return False, "custody-link-position-mismatch"
        launched = row.get("launched_resume_id")
        reported = row.get("reported_session_id")
        if link.get("launched_resume_id") != launched or link.get("reported_session_id") != reported:
            return False, "custody-row-link-mismatch"
        if launched != previous_reported:
            return False, "custody-adjacency-mismatch"
        if not isinstance(reported, str) or not reported:
            return False, "custody-reported-id-missing"
        previous_reported = reported
    return True, None


def evaluate(rows, boundaries, custody):
    if not isinstance(rows, list) or not isinstance(boundaries, list):
        return failed_input("rows or boundary ledger is malformed")

    custody_ok = len(rows) >= 2
    custody_reason = None if custody_ok else "fewer-than-two-rows"
    for position, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            custody_ok, custody_reason = False, "row-malformed"
            break
        if row.get("custody_ok") is not True or row.get("custody_broken") is not False:
            custody_ok, custody_reason = False, "custody-broken"
            break
        if position >= 2 and (
            not isinstance(row.get("launched_resume_id"), str)
            or not row["launched_resume_id"]
        ):
            custody_ok, custody_reason = False, "resume-missing"
            break
    if custody_ok:
        custody_ok, custody_reason = custody_adjacency(rows, custody)

    attestation_ok = bool(rows)
    attestation_reason = None if attestation_ok else "zero-rows"
    for row in rows:
        if not isinstance(row, dict):
            attestation_ok, attestation_reason = False, "row-malformed"
            break
        requested = row.get("engine_requested")
        attested = row.get("engine_attested")
        if not isinstance(requested, str) or not requested or attested != requested:
            attestation_ok, attestation_reason = False, "engine-attestation-mismatch"
            break
        if row.get("infra_invalid") is not False or row.get("catastrophic") is not False:
            attestation_ok, attestation_reason = False, "infra-or-catastrophic"
            break

    harvest_ok = len(boundaries) == len(rows) and len(boundaries) >= 2
    harvest_reason = None if harvest_ok else "boundary-row-count-mismatch"
    valid_boundaries = []
    if harvest_ok:
        for position, boundary in enumerate(boundaries, start=1):
            row = rows[position - 1]
            if not isinstance(row, dict):
                harvest_ok, harvest_reason = False, "row-malformed"
                break
            if not isinstance(boundary, dict):
                harvest_ok, harvest_reason = False, "boundary-malformed"
                break
            if boundary.get("position_index") != position or row.get("position_index") != position:
                harvest_ok, harvest_reason = False, "boundary-position-mismatch"
                break
            if boundary.get("records_invalid") is not False:
                harvest_ok, harvest_reason = False, "records-invalid"
                break
            count = boundary.get("unique_request_count")
            if not isinstance(count, int) or isinstance(count, bool) or count < 1:
                harvest_ok, harvest_reason = False, "zero-unique-requests"
                break
            valid_boundaries.append(boundary)

    windows = []
    window_error = None
    if harvest_ok:
        for boundary in valid_boundaries:
            window, window_error = non_carried_window(boundary)
            if window_error is not None:
                break
            windows.append(window)

    discriminability_checks = []
    if window_error is not None:
        discriminability = verdict(False, window_error)
    elif len(windows) < 2:
        discriminability = verdict(False, "fewer-than-two-valid-boundaries")
    else:
        for position, (first, last) in enumerate(windows[:-1], start=1):
            footprint = last - first
            discriminability_checks.append(
                {"position_index": position, "first_effective_context": first, "last_effective_context": last, "footprint": footprint}
            )
        discriminating = all(item["footprint"] >= MINIMUM_FOOTPRINT for item in discriminability_checks)
        discriminability = verdict(
            discriminating,
            None if discriminating else "fixture-non-discriminating",
            checks=discriminability_checks,
        )

    if not discriminability["passed"]:
        growth = verdict(False, discriminability.get("reason"))
    elif window_error is not None or len(windows) < 2:
        growth = verdict(False, "fewer-than-two-valid-boundaries")
    else:
        growth_checks = []
        for position, ((first, _), (next_first, _)) in enumerate(zip(windows, windows[1:]), start=1):
            growth_checks.append(
                {
                    "from_position_index": position,
                    "to_position_index": position + 1,
                    "first_effective_context": first,
                    "next_first_effective_context": next_first,
                    "required_minimum": first + GROWTH_TOKENS,
                }
            )
        growth_passed = all(
            item["next_first_effective_context"] >= item["required_minimum"]
            for item in growth_checks
        )
        growth = verdict(growth_passed, None if growth_passed else "growth-under-minimum", checks=growth_checks)

    legs = {
        "custody": verdict(custody_ok, custody_reason),
        "growth": growth,
        "attestation": verdict(attestation_ok, attestation_reason),
        "harvest": verdict(harvest_ok, harvest_reason),
    }
    passed = discriminability["passed"] and all(leg["passed"] for leg in legs.values())
    return {"legs": legs, "discriminability": discriminability, "verdict": "PASS" if passed else "FAIL"}


def row(position, **overrides):
    value = {
        "position_index": position,
        "custody_ok": True,
        "custody_broken": False,
        "launched_resume_id": None if position == 1 else f"session-{position - 1}",
        "reported_session_id": f"session-{position}",
        "engine_requested": "claude-sonnet-5",
        "engine_attested": "claude-sonnet-5",
        "infra_invalid": False,
        "catastrophic": False,
    }
    value.update(overrides)
    return value


def boundary(position, first, last, **overrides):
    value = {
        "position_index": position,
        "records_invalid": False,
        "unique_request_count": 2,
        "usage_entries": [
            {"request_id": f"request-{position}-first", "effective_context": first},
            {"request_id": f"request-{position}-last", "effective_context": last},
        ],
    }
    value.update(overrides)
    return value


def custody(rows):
    return {
        "links": [
            {
                "position_index": row["position_index"],
                "launched_resume_id": row["launched_resume_id"],
                "reported_session_id": row["reported_session_id"],
            }
            for row in rows
        ]
    }


def self_test():
    rows = [row(1), row(2)]
    second = boundary(2, 14_200, 16_000)
    second["usage_entries"].insert(
        0,
        {"request_id": "request-1-last", "effective_context": 18_300, "carried": True},
    )
    passing = evaluate(rows, [boundary(1, 10_000, 18_300), second], custody(rows))
    assert passing["verdict"] == "PASS"
    assert passing["legs"]["growth"]["checks"][0]["next_first_effective_context"] == 14_200

    reset = evaluate(rows, [boundary(1, 10_000, 18_300), boundary(2, 10_000, 16_000)], custody(rows))
    assert reset["verdict"] == "FAIL"
    assert reset["discriminability"]["passed"] is True
    assert reset["legs"]["growth"]["reason"] == "growth-under-minimum"

    non_discriminating = evaluate(rows, [boundary(1, 10_000, 15_000), boundary(2, 14_200, 16_000)], custody(rows))
    assert non_discriminating["verdict"] == "FAIL"
    assert non_discriminating["discriminability"]["reason"] == "fixture-non-discriminating"

    broken_rows = [row(1), row(2, custody_ok=False, custody_broken=True)]
    broken_custody = evaluate(broken_rows, [boundary(1, 10_000, 18_300), boundary(2, 14_200, 16_000)], custody(broken_rows))
    assert broken_custody["verdict"] == "FAIL"
    assert broken_custody["legs"]["custody"]["reason"] == "custody-broken"
    unrelated = custody(rows)
    unrelated_rows = [row(1), row(2, launched_resume_id="unrelated-session")]
    unrelated["links"][1]["launched_resume_id"] = "unrelated-session"
    adjacency_fail = evaluate(unrelated_rows, [boundary(1, 10_000, 18_300), boundary(2, 14_200, 16_000)], unrelated)
    assert adjacency_fail["verdict"] == "FAIL"
    assert adjacency_fail["legs"]["custody"]["reason"] == "custody-adjacency-mismatch"
    print("PASS smoke-gate-0110 self-test: pass, reset, discriminability, custody adjacency")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--session-dir")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.session_dir:
        result = failed_input("--session-dir is required unless --self-test is used")
    else:
        session_dir = pathlib.Path(args.session_dir)
        try:
            rows = read_rows(session_dir / "rows.jsonl")
            ledger = json.loads((session_dir / "boundary-ledger.json").read_text(encoding="utf-8"))
            boundaries = ledger["boundaries"]
            custody_payload = json.loads((session_dir / "custody.json").read_text(encoding="utf-8"))
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            result = failed_input(str(exc))
        else:
            result = evaluate(rows, boundaries, custody_payload)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
