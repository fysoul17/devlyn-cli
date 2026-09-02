#!/usr/bin/env python3
"""Capture frozen iter-0112 usage evidence from Claude Code's usage endpoint."""

from __future__ import annotations

import argparse
import contextlib
import datetime
import hashlib
import io
import json
import math
import pathlib
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request


HERE = pathlib.Path(__file__).resolve().parent
FIXTURE = HERE.parent / "fixtures-0112/usage-endpoint-20260902-0840KST.raw.json"
JITTER_FIXTURE = HERE.parent / "fixtures-0112/usage-jitter-B-20260902-1055KST.raw.json"
ENDPOINT = "https://api.anthropic.com/api/oauth/usage"
USAGE_FIELDS = ("source", "meter_id", "observed_at", "value", "attested_by", "used_percent", "display_resolution_percent", "reset_at", "panel_sha256", "auxiliary")


class CaptureViolation(ValueError):
    pass


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def parse_timestamp(value: object, field: str) -> datetime.datetime:
    if not isinstance(value, str):
        raise CaptureViolation(f"{field}-invalid")
    try:
        parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CaptureViolation(f"{field}-invalid") from exc
    if parsed.tzinfo is None:
        raise CaptureViolation(f"{field}-invalid")
    return parsed.astimezone(datetime.timezone.utc)


def canonical_reset_at(value: object) -> str:
    parsed = parse_timestamp(value, "resets-at")
    rounded = parsed.replace(second=0, microsecond=0)
    if parsed.second >= 30:
        rounded += datetime.timedelta(minutes=1)
    return (rounded + datetime.timedelta(minutes=1)).isoformat()


def percentage(value: object, field: str) -> int:
    if type(value) is not int or not 0 <= value <= 100:
        raise CaptureViolation(f"{field}-invalid")
    return value


def auxiliary_percent(limits: list[object], predicate) -> int | None:
    matches = [limit for limit in limits if isinstance(limit, dict) and predicate(limit)]
    if len(matches) > 1:
        raise CaptureViolation("auxiliary-ambiguous")
    return None if not matches else percentage(matches[0].get("percent"), "auxiliary-percent")


def build_evidence(body: bytes, server_date: str | None, completed_at: datetime.datetime, token: bytes) -> bytes:
    if token in body:
        raise CaptureViolation("token-in-body")
    try:
        response = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CaptureViolation("response-json-invalid") from exc
    if not isinstance(response, dict) or not isinstance(response.get("limits"), list) or not isinstance(response.get("seven_day"), dict):
        raise CaptureViolation("response-shape-invalid")
    limits = response["limits"]
    weekly_all = [limit for limit in limits if isinstance(limit, dict) and limit.get("kind") == "weekly_all"]
    if len(weekly_all) != 1:
        raise CaptureViolation("weekly-all-ambiguous")
    weekly = weekly_all[0]
    used_percent = percentage(weekly.get("percent"), "weekly-all-percent")
    seven_day = response["seven_day"]
    utilization = seven_day.get("utilization")
    if type(utilization) not in (int, float) or not math.isfinite(utilization) or not float(utilization).is_integer() or int(utilization) != used_percent:
        raise CaptureViolation("seven-day-utilization-mismatch")
    raw_reset_at = weekly.get("resets_at")
    if not isinstance(raw_reset_at, str) or seven_day.get("resets_at") != raw_reset_at:
        raise CaptureViolation("reset-at-mismatch")
    if "locked_reason" not in seven_day or seven_day["locked_reason"] is not None or ("locked_reason" in weekly and weekly["locked_reason"] is not None):
        raise CaptureViolation("locked-reason")
    reset_at = canonical_reset_at(raw_reset_at)
    fable_percent = auxiliary_percent(limits, lambda limit: limit.get("kind") == "weekly_scoped" and isinstance(limit.get("scope"), dict) and isinstance(limit["scope"].get("model"), dict) and limit["scope"]["model"].get("display_name") == "Fable")
    session_percent = auxiliary_percent(limits, lambda limit: limit.get("kind") == "session")
    observed_at = completed_at.astimezone(datetime.timezone.utc).isoformat()
    value = json.dumps({"weekly_all": weekly, "seven_day_resets_at": raw_reset_at, "server_date": server_date, "raw_sha256": hashlib.sha256(body).hexdigest()}, separators=(",", ":"))
    evidence = {"source": "usage", "meter_id": "current_week_all_models", "observed_at": observed_at, "value": value, "attested_by": f"usage-capture-0112.py sha256={hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()}", "used_percent": used_percent, "display_resolution_percent": 1, "reset_at": reset_at, "panel_sha256": hashlib.sha256(body).hexdigest(), "auxiliary": {"current_week_fable_percent": fable_percent, "current_session_percent": session_percent}}
    if tuple(evidence) != USAGE_FIELDS:
        raise CaptureViolation("evidence-fields-invalid")
    return canonical_bytes(evidence)


def write_capture(prefix: pathlib.Path, body: bytes, server_date: str | None, completed_at: datetime.datetime, token: bytes) -> tuple[pathlib.Path, pathlib.Path]:
    raw_path = pathlib.Path(f"{prefix}.raw.json")
    evidence_path = pathlib.Path(f"{prefix}.json")
    evidence = build_evidence(body, server_date, completed_at, token)
    created: list[pathlib.Path] = []
    try:
        for path, payload in ((raw_path, body), (evidence_path, evidence)):
            with path.open("xb") as output:
                created.append(path)
                output.write(payload)
    except BaseException as exc:
        cleanup_failed = False
        for path in created:
            try:
                path.unlink()
            except OSError:
                cleanup_failed = True
        remaining = [path for path in created if path.exists()]
        if cleanup_failed or remaining:
            raise CaptureViolation("output-cleanup-failed") from exc
        if isinstance(exc, FileExistsError):
            raise CaptureViolation("output-exists") from exc
        raise CaptureViolation("output-failed") from exc
    return raw_path, evidence_path


def credential() -> bytes:
    try:
        result = subprocess.run(["security", "find-generic-password", "-s", "Claude Code-credentials", "-w"], check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as exc:
        raise CaptureViolation("credential-unavailable") from exc
    if result.returncode != 0:
        raise CaptureViolation("credential-unavailable")
    try:
        payload = json.loads(result.stdout)
        token = payload["claudeAiOauth"]["accessToken"]
    except (KeyError, TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CaptureViolation("credential-invalid") from exc
    if not isinstance(token, str):
        raise CaptureViolation("credential-invalid")
    try:
        return header_token(token.encode("ascii")).encode("ascii")
    except UnicodeError as exc:
        raise CaptureViolation("credential-invalid") from exc


def header_token(token: object) -> str:
    if not isinstance(token, bytes) or not token or any(byte < 0x21 or byte > 0x7e for byte in token):
        raise CaptureViolation("credential-invalid")
    return token.decode("ascii")


def request_for(token: bytes) -> urllib.request.Request:
    value = header_token(token)
    try:
        return urllib.request.Request(ENDPOINT, headers={"Authorization": f"Bearer {value}", "anthropic-beta": "oauth-2025-04-20", "User-Agent": "claude-cli/2.1.226", "Accept": "application/json"})
    except BaseException as exc:
        raise CaptureViolation("request-invalid") from exc


def fetch(token: bytes) -> tuple[bytes, str | None, datetime.datetime]:
    request = request_for(token)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            status = response.getcode()
            body = response.read()
            completed_at = datetime.datetime.now(datetime.timezone.utc)
            server_date = response.headers.get("Date")
    except urllib.error.HTTPError as exc:
        raise CaptureViolation("http-status") from exc
    except OSError as exc:
        raise CaptureViolation("request-failed") from exc
    if status != 200:
        raise CaptureViolation("http-status")
    return body, server_date, completed_at


def self_test() -> None:
    fixture = FIXTURE.read_bytes()
    fixed_clock = datetime.datetime(2026, 9, 2, 0, 40, tzinfo=datetime.timezone.utc)
    fixed_date = "Tue, 02 Sep 2026 00:40:00 GMT"
    token = b"fixture-token"
    payload = json.loads(fixture)
    weekly = next(limit for limit in payload["limits"] if limit["kind"] == "weekly_all")
    expected = {"source": "usage", "meter_id": "current_week_all_models", "observed_at": fixed_clock.isoformat(), "value": json.dumps({"weekly_all": weekly, "seven_day_resets_at": "2026-09-07T11:00:00.339216+00:00", "server_date": fixed_date, "raw_sha256": hashlib.sha256(fixture).hexdigest()}, separators=(",", ":")), "attested_by": f"usage-capture-0112.py sha256={hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()}", "used_percent": 5, "display_resolution_percent": 1, "reset_at": "2026-09-07T11:01:00+00:00", "panel_sha256": hashlib.sha256(fixture).hexdigest(), "auxiliary": {"current_week_fable_percent": 6, "current_session_percent": 11}}
    expected_bytes = canonical_bytes(expected)
    assert build_evidence(fixture, fixed_date, fixed_clock, token) == expected_bytes
    for fixture_path, expected_reset_at in ((FIXTURE, "2026-09-07T11:01:00+00:00"), (JITTER_FIXTURE, "2026-09-04T23:01:00+00:00")):
        fixture_payload = json.loads(fixture_path.read_bytes())
        fixture_weekly = next(limit for limit in fixture_payload["limits"] if limit["kind"] == "weekly_all")
        assert canonical_reset_at(fixture_weekly["resets_at"]) == expected_reset_at
    assert canonical_reset_at("2026-09-07T11:00:29.999+00:00") == "2026-09-07T11:01:00+00:00"
    assert canonical_reset_at("2026-09-07T11:00:30.000+00:00") == "2026-09-07T11:02:00+00:00"
    with tempfile.TemporaryDirectory(prefix="iter0112-usage-capture-") as temporary:
        root = pathlib.Path(temporary)
        raw_path, evidence_path = write_capture(root / "positive", fixture, fixed_date, fixed_clock, token)
        assert raw_path.read_bytes() == fixture and evidence_path.read_bytes() == expected_bytes
        assert sorted(path.name for path in root.glob("positive*")) == ["positive.json", "positive.raw.json"]
        def expect_refusal(name: str, body: bytes, expected_reason: str, test_token: bytes = token) -> None:
            try:
                write_capture(root / name, body, fixed_date, fixed_clock, test_token)
            except CaptureViolation as exc:
                assert str(exc) == expected_reason
            else:
                raise AssertionError(f"{name} accepted")
        def altered(change) -> bytes:
            candidate = json.loads(fixture)
            change(candidate)
            return json.dumps(candidate, separators=(",", ":")).encode()
        expect_refusal("two-weekly-all", altered(lambda candidate: candidate["limits"].append(dict(candidate["limits"][1]))), "weekly-all-ambiguous")
        expect_refusal("non-integer-percent", altered(lambda candidate: candidate["limits"][1].__setitem__("percent", 5.5)), "weekly-all-percent-invalid")
        expect_refusal("utilization-mismatch", altered(lambda candidate: candidate["seven_day"].__setitem__("utilization", 4.0)), "seven-day-utilization-mismatch")
        expect_refusal("raw-reset-mismatch", altered(lambda candidate: candidate["seven_day"].__setitem__("resets_at", "2026-09-07T12:00:00+00:00")), "reset-at-mismatch")
        expect_refusal("locked", altered(lambda candidate: candidate["seven_day"].__setitem__("locked_reason", "locked")), "locked-reason")
        expect_refusal("token-in-body", fixture + token, "token-in-body")
        existing_raw = root / "existing.raw.json"
        existing_raw.write_bytes(b"existing")
        expect_refusal("existing", fixture, "output-exists")
        assert existing_raw.read_bytes() == b"existing" and not (root / "existing.json").exists()
        collision = root / "collision.json"
        collision.write_bytes(b"existing")
        expect_refusal("collision", fixture, "output-exists")
        assert collision.read_bytes() == b"existing" and not (root / "collision.raw.json").exists()

        class FailingFile:
            def __init__(self, output) -> None:
                self.output = output

            def __enter__(self):
                return self

            def __exit__(self, *args) -> None:
                self.output.close()

            def write(self, _payload: bytes) -> int:
                raise OSError("injected-write-failure")

        def expect_write_failure(name: str, failure_number: int, fail_unlink: bool = False) -> None:
            original_open = pathlib.Path.open
            original_unlink = pathlib.Path.unlink
            writes = 0

            def failing_open(path: pathlib.Path, mode: str = "r", *args, **kwargs):
                nonlocal writes
                output = original_open(path, mode, *args, **kwargs)
                if mode == "xb":
                    writes += 1
                    if writes == failure_number:
                        return FailingFile(output)
                return output

            pathlib.Path.open = failing_open
            if fail_unlink:
                def failing_unlink(path: pathlib.Path, *args, **kwargs) -> None:
                    if path == root / f"{name}.raw.json":
                        raise OSError("injected-unlink-failure")
                    original_unlink(path, *args, **kwargs)
                pathlib.Path.unlink = failing_unlink
            try:
                expect_refusal(name, fixture, "output-cleanup-failed" if fail_unlink else "output-failed")
            finally:
                pathlib.Path.open = original_open
                pathlib.Path.unlink = original_unlink
            if fail_unlink:
                assert (root / f"{name}.raw.json").exists() and not (root / f"{name}.json").exists()
            else:
                assert not list(root.glob(f"{name}*"))

        expect_write_failure("first-write-failure", 1)
        expect_write_failure("second-write-failure", 2)
        expect_write_failure("cleanup-failure", 2, fail_unlink=True)
        sentinel = b"SENTINEL\r\nX"
        stdout, stderr = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                fetch(sentinel)
        except Exception as exc:
            exception_text = f"{type(exc).__name__}: {exc}"
        else:
            raise AssertionError("unsafe token accepted")
        assert sentinel.decode("ascii") not in stdout.getvalue() + stderr.getvalue() + exception_text
    print("PASS usage-capture-0112 self-test: canonical reset rounding, fixture evidence, meter continuity, refusals, exclusive and verified-cleanup outputs")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=pathlib.Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        if args.out is not None:
            parser.error("--self-test does not accept --out")
        try:
            self_test()
        except Exception:
            print("FAIL usage-capture-0112 self-test: failed", file=sys.stderr)
            return 1
        return 0
    if args.out is None:
        parser.error("--out is required unless --self-test is used")
    try:
        token = credential()
        body, server_date, completed_at = fetch(token)
        raw_path, evidence_path = write_capture(args.out, body, server_date, completed_at, token)
    except BaseException:
        print("FAIL usage-capture-0112: capture-failed", file=sys.stderr)
        return 2
    print(f"USAGE_CAPTURED: {raw_path} {evidence_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
