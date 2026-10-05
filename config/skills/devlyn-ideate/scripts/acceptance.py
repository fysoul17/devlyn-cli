#!/usr/bin/env python3
"""Loop acceptance: derive a task result from its committed source and evidence.

`run` executes the declared checks on the committed candidate; the executor may
call it before review. `accept` derives the drain result: it binds the contract,
requires the owned committed source, reuses the intact outcomes of a wholly clean
runner result for the same source and contract, executes the rest, evaluates
file/diff guards, confirms the source is unchanged and checks review records. A
malformed executor record fails acceptance with its reason. An executor's summary
verdict is never evidence. Protocol: ../references/loop.md.
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import subprocess
import sys
import tempfile
import unittest

SKILLS = Path(__file__).resolve().parents[2]
LOOP_DIR = ".devlyn/loop"
QUEUE = "docs/specs/queue.md"
SHA_RE = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
BLOCKERS = ("failed", "needs-review", "blocked-infrastructure")
REVIEW_KEYS = {"schema_version", "kind", "task", "engine", "model", "source_sha", "contract_sha256",
               "expected_sha256", "requirements", "findings"}
FINDING_KEYS = {"id", "binding", "disposition", "requirement", "summary", "reason"}
SUBMISSION_KEYS = {"schema_version", "task", "source_sha", "runner_results", "reviews", "findings", "cleanup",
                   "handoff", "assumptions", "blockers", "summary"}
PACKET_KEYS = {"task", "worktree", "branch", "inputs_sha", "allocation_base", "contract", "expected", "meta",
               "requirements", "review_requirements"}


class AcceptanceError(Exception):
    pass


@functools.lru_cache(maxsize=None)
def shared(name):
    return runpy.run_path(str(SKILLS / "_shared" / f"{name}.py"))


def git(work, *args, ok=(0,)):
    result = subprocess.run(["git", "-C", str(work), *args], capture_output=True)
    if result.returncode not in ok:
        raise AcceptanceError(f"git {' '.join(args[:2])}: {result.stderr.decode('utf-8', 'replace').strip()}")
    return result


def text(work, *args):
    return git(work, *args).stdout.decode("utf-8").strip()


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def read_json(path):
    try:
        return shared("expected-contract")["loads_strict_json"](Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise AcceptanceError(f"{path}: {exc}") from exc


def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def write_json(path, value):
    atomic_write(path, (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8"))


def load_packet(path):
    packet = read_json(path)
    if not isinstance(packet, dict) or PACKET_KEYS - set(packet):
        raise AcceptanceError(f"{path}: task packet lacks {sorted(PACKET_KEYS - set(packet if isinstance(packet, dict) else {}))}")
    return packet


def contract_digests(packet):
    return {key: packet[key]["sha256"] for key in ("contract", "expected", "meta")}


def relative(work, path):
    return Path(path).resolve().relative_to(Path(work).resolve()).as_posix()


def evidence_file(work, path, under=LOOP_DIR):
    candidate = Path(path) if Path(path).is_absolute() else Path(work) / path
    resolved = candidate.resolve()
    if not resolved.is_relative_to((Path(work) / under).resolve()) or not resolved.is_file():
        raise AcceptanceError(f"evidence must be a file under {under} in the task worktree: {path}")
    return resolved


def bound_contract(packet):
    """Return the committed expected contract after checking every input against the packet digests."""
    work = Path(packet["worktree"])
    raw = {}
    for key in ("contract", "expected", "meta"):
        rel = relative(work, packet[key]["path"])
        raw[key] = git(work, "show", f"{packet['inputs_sha']}:{rel}").stdout
        if sha256(raw[key]) != packet[key]["sha256"]:
            raise AcceptanceError(f"{rel} at the inputs commit differs from the task packet")
    contract = shared("expected-contract")
    try:
        expected = contract["loads_strict_json"](raw["expected"].decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise AcceptanceError(f"expected contract: {exc}") from exc
    error = contract["validate_expected_shape"](expected)
    if error:
        raise AcceptanceError(f"expected contract: {error}")
    return expected


def source_problems(packet, source):
    """The candidate must be the owned task commit, descend from the inputs, leave them untouched and be clean."""
    work = Path(packet["worktree"])
    if not SHA_RE.fullmatch(source) or git(work, "cat-file", "-e", source + "^{commit}", ok=(0, 1, 128)).returncode:
        return [f"candidate {source!r} is not a commit"]
    problems = []
    head = git(work, "symbolic-ref", "-q", "HEAD", ok=(0, 1)).stdout.decode("utf-8").strip()
    branch = text(work, "rev-parse", "refs/heads/" + packet["branch"])
    if (source, head) != (branch, "refs/heads/" + packet["branch"]):
        problems.append(f"candidate {source} is not the owned task commit checked out on its branch (branch {branch}, HEAD {head or 'detached'})")
    if git(work, "merge-base", "--is-ancestor", packet["inputs_sha"], source, ok=(0, 1)).returncode:
        problems.append(f"candidate {source} does not descend from the committed inputs")
    else:
        package = relative(work, packet["meta"]["path"]).rpartition("/")[0] + "/"
        edits = [path for path in changed_paths(work, packet["inputs_sha"], source) if path == QUEUE or path.startswith(package)]
        if edits:
            problems.append("candidate edits loop inputs: " + ", ".join(edits))
    if text(work, "status", "--porcelain", "--untracked-files=all"):
        problems.append("worktree has uncommitted or untracked changes (undeclared source delta)")
    return problems


def changed_paths(work, old, new):
    raw = git(work, "diff", "--name-only", "-z", "--no-renames", old, new).stdout
    return [path.decode("utf-8", "surrogateescape") for path in raw.split(b"\0") if path]


def evaluate(command, outcome, combined):
    if outcome["kind"] != "exit":
        return False, outcome["kind"]
    expected_exit = command.get("exit_code", 0)
    if outcome["exit_code"] != expected_exit:
        return False, f"exit {outcome['exit_code']}, expected {expected_exit}"
    missing = [value for value in command.get("stdout_contains", []) if value.encode("utf-8") not in combined]
    if missing:
        return False, f"output lacks {missing!r}"
    found = [value for value in command.get("stdout_not_contains", []) if value.encode("utf-8") in combined]
    if found:
        return False, f"output contains forbidden {found!r}"
    return True, None


def execute(work, command, index, run_dir):
    timeout = shared("expected-contract")["verification_timeout_sec"](command)
    try:
        if "argv" in command:
            proc = subprocess.run(shared("platform-support")["native_argv"](command["argv"]), cwd=work,
                                  capture_output=True, timeout=timeout)
        else:
            proc = subprocess.run(command["cmd"], cwd=work, shell=True, capture_output=True, timeout=timeout)
        out, err = proc.stdout, proc.stderr
        outcome = ({"kind": "exit", "exit_code": proc.returncode} if proc.returncode >= 0
                   else {"kind": "signal", "signal": -proc.returncode})
    except subprocess.TimeoutExpired as exc:
        out, err, outcome = exc.stdout or b"", exc.stderr or b"", {"kind": "timeout", "timeout_sec": timeout}
    except OSError as exc:
        out, err, outcome = b"", str(exc).encode("utf-8"), {"kind": "spawn_error", "error": str(exc)}
    record = {"index": index, "outcome": outcome}
    for name, raw in (("stdout", out), ("stderr", err)):
        path = run_dir / f"cmd-{index}.{name}"
        path.write_bytes(raw)
        record[name] = {"path": relative(work, path), "sha256": sha256(raw), "bytes": len(raw)}
    record["passed"], record["reason"] = evaluate(command, outcome, out + err)
    return record


def new_run_dir(work):
    runs = Path(work) / LOOP_DIR / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    number = 1 + max((int(path.name) for path in runs.iterdir() if path.name.isdigit()), default=0)
    run_dir = runs / str(number)
    run_dir.mkdir()
    return run_dir


def intact(work, record):
    try:
        return all(sha256(evidence_file(work, record[name]["path"]).read_bytes()) == record[name]["sha256"]
                   for name in ("stdout", "stderr"))
    except (AcceptanceError, KeyError, TypeError, OSError):
        return False


def reusable(packet, source, paths):
    """Passed outcomes of wholly clean runner results (no reasons, so no failed check or source change during
    the checks) for this exact source and contract, with intact raw streams."""
    work = Path(packet["worktree"])
    reused = {}
    for path in paths:
        result_path = evidence_file(work, path)
        result = read_json(result_path)
        if not isinstance(result, dict) or (result.get("kind"), result.get("task"), result.get("source_sha"), result.get("contract"),
                                            result.get("reasons")) != ("loop-checks", packet["task"], source, contract_digests(packet), []):
            continue
        records = result.get("commands")
        if not isinstance(records, list) or not all(isinstance(record, dict) and type(record.get("index")) is int for record in records):
            raise AcceptanceError(f"runner result {relative(work, result_path)} has malformed command records")
        for record in records:
            if record.get("passed") is True and intact(work, record):
                reused.setdefault(record["index"], dict(record, reused_from=relative(work, result_path)))
    return reused


def run_checks(packet, expected, reused):
    work = Path(packet["worktree"])
    records, run_dir = [], None
    for index, command in enumerate(expected.get("verification_commands", [])):
        if index in reused:
            records.append(reused[index])
            continue
        run_dir = run_dir or new_run_dir(work)
        records.append(execute(work, command, index, run_dir))
    for record, command in zip(records, expected.get("verification_commands", [])):
        record["command"] = {key: command[key] for key in ("cmd", "argv") if key in command}
        record["contract_refs"] = command.get("contract_refs", [])
    return records, run_dir


def guard_results(packet, expected, source):
    work, inputs = Path(packet["worktree"]), packet["inputs_sha"]
    contract = shared("expected-contract")
    diff = git(work, "diff", "--no-color", "--no-ext-diff", inputs, source).stdout.decode("utf-8", "surrogateescape")
    changed = set(changed_paths(work, inputs, source))
    results = []
    for index, pattern in enumerate(expected.get("forbidden_patterns", [])):
        try:
            matched = re.search(pattern["pattern"], contract["slice_diff_to_files"](diff, pattern.get("files") or [])) is not None
        except re.error as exc:
            raise AcceptanceError(f"forbidden_patterns/{index} is not a valid regex: {exc}") from exc
        results.append({"rule": f"forbidden_patterns/{index}", "subject": pattern["description"], "passed": not matched,
                        "blocking": pattern["severity"] == "disqualifier"})
    for path in expected.get("required_files", []):
        present = git(work, "cat-file", "-e", f"{source}:{path}", ok=(0, 1, 128)).returncode == 0
        results.append({"rule": "required_files", "subject": path, "passed": present, "blocking": True})
    for path in expected.get("forbidden_files", []):
        results.append({"rule": "forbidden_files", "subject": path, "passed": path not in changed, "blocking": True})
    deps = contract["count_deps_in_diff"](git(work, "diff", inputs, source, "--", "package.json").stdout.decode("utf-8", "replace"))
    limit = expected.get("max_deps_added", 0)
    results.append({"rule": "max_deps_added", "subject": f"{deps} added, limit {limit}", "passed": deps <= limit, "blocking": True})
    return results


def review_problem(packet, record, source):
    """(problem, malformed): a malformed record fails acceptance; a well-formed record bound elsewhere does not count."""
    if not isinstance(record, dict) or not REVIEW_KEYS <= set(record) <= REVIEW_KEYS | {"summary"}:
        return f"review record keys must be {sorted(REVIEW_KEYS)} (optional summary)", True
    if (record["schema_version"], record["kind"]) != (1, "devlyn-review"):
        return "review record is not a schema 1 devlyn-review", True
    if not all(isinstance(record[key], str) and record[key].strip() for key in ("engine", "model")):
        return "review record must name its engine and model", True
    if not isinstance(record["requirements"], list) or not all(req in packet["requirements"] for req in record["requirements"]):
        return "review requirements must name task requirement IDs", True
    findings = record["findings"]
    if not isinstance(findings, list) or not all(
            isinstance(f, dict) and {"id", "binding", "disposition"} <= set(f) <= FINDING_KEYS and isinstance(f["id"], str)
            and isinstance(f["binding"], bool) and f["disposition"] in ("open", "resolved", "rejected")
            and (f["disposition"] != "rejected" or (isinstance(f.get("reason"), str) and f["reason"].strip()))
            for f in findings):
        return "findings need id, boolean binding and disposition open|resolved|rejected (rejected needs a reason)", True
    if record["task"] != packet["task"]:
        return f"review is for task {record['task']!r}, not {packet['task']}", False
    if record["source_sha"] != source:
        return f"review is bound to source {record['source_sha']}, not {source}", False
    if (record["contract_sha256"], record["expected_sha256"]) != (packet["contract"]["sha256"], packet["expected"]["sha256"]):
        return "review is bound to a different contract", False
    return None, False


def review_results(packet, paths, source):
    work = Path(packet["worktree"])
    counted, ignored = [], []
    for path in paths:
        try:
            record_path = evidence_file(work, path, ".devlyn")
            raw = record_path.read_bytes()
            record = shared("expected-contract")["loads_strict_json"](raw.decode("utf-8"))
            problem, malformed = review_problem(packet, record, source)
        except (AcceptanceError, OSError, UnicodeError, ValueError) as exc:
            problem, malformed = str(exc), True
        if malformed:
            raise AcceptanceError(f"malformed review record {path}: {problem}")
        if problem:
            ignored.append({"path": str(path), "reason": problem})
            continue
        counted.append({"path": relative(work, record_path), "sha256": sha256(raw), "engine": record["engine"],
                        "model": record["model"], "requirements": record["requirements"],
                        "open_binding_findings": [f["id"] for f in record["findings"] if f["binding"] and f["disposition"] == "open"]})
    return counted, ignored


def check_submission(packet, submission):
    if not isinstance(submission, dict) or not {"schema_version", "task", "source_sha"} <= set(submission) <= SUBMISSION_KEYS:
        raise AcceptanceError(f"submission keys must include schema_version, task, source_sha and stay within {sorted(SUBMISSION_KEYS)}")
    if (submission["schema_version"], submission["task"]) != (1, packet["task"]) or not isinstance(submission["source_sha"], str):
        raise AcceptanceError("submission is not schema 1 for this task with a string source_sha")
    for key in ("runner_results", "reviews", "assumptions"):
        value = submission.get(key, [])
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise AcceptanceError(f"submission {key} must be a list of strings")
    blockers = submission.get("blockers", [])
    if not isinstance(blockers, list) or not all(
            isinstance(b, dict) and set(b) == {"kind", "detail"} and b["kind"] in BLOCKERS and isinstance(b["detail"], str) and b["detail"].strip()
            for b in blockers):
        raise AcceptanceError(f"submission blockers must be {{kind, detail}} with kind in {sorted(BLOCKERS)}")


def result_shell(packet, kind, source):
    return {"schema_version": 1, "kind": kind, "task": packet["task"], "source_sha": source,
            "inputs_sha": packet["inputs_sha"], "allocation_base": packet["allocation_base"],
            "contract": contract_digests(packet), "commands": [], "guards": []}


def check_reasons(result):
    reasons = [f"failed: command {r['index']} ({', '.join(r['contract_refs']) or 'no refs'}) {r['reason']}"
               for r in result["commands"] if not r["passed"]]
    return reasons + [f"failed: guard {g['rule']} {g['subject']}" for g in result["guards"] if g["blocking"] and not g["passed"]]


def run(packet_path, source=None):
    """Executor-side runner: checks on the committed candidate, before review."""
    packet = load_packet(packet_path)
    work = Path(packet["worktree"])
    source = source or text(work, "rev-parse", "HEAD")
    expected = bound_contract(packet)
    problems = source_problems(packet, source)
    if problems:
        raise AcceptanceError("; ".join(problems))
    result = result_shell(packet, "loop-checks", source)
    result["commands"], run_dir = run_checks(packet, expected, {})
    result["guards"] = guard_results(packet, expected, source)
    result["reasons"] = check_reasons(result) + [f"failed: source changed during checks: {p}" for p in source_problems(packet, source)]
    path = (run_dir or new_run_dir(work)) / "result.json"
    write_json(path, result)
    return path, result


def accept(packet_path, submission_path, failure=None):
    """Drain-side derivation; writes .devlyn/loop/acceptance.json for task-complete custody. A drain-recorded
    `failure` (changed inputs, an unobservable interrupted execution) fails the task without its submission."""
    packet = load_packet(packet_path)
    work = Path(packet["worktree"])
    result = result_shell(packet, "loop", text(work, "rev-parse", "refs/heads/" + packet["branch"]))
    result.update(reviews=[], ignored_reviews=[], assumptions=[], reasons=[failure] if failure else [])
    try:
        if not failure:
            submission = read_json(submission_path)
            check_submission(packet, submission)
            result["assumptions"] = submission.get("assumptions", [])
            if submission.get("blockers"):
                result["reasons"] = [f"{b['kind']}: {b['detail']}" for b in submission["blockers"]]
            else:
                derive(packet, submission, result)
    except AcceptanceError as exc:
        result["reasons"].append(f"failed: {exc}")
    result["verdict"] = "FAILED" if result["reasons"] else "ACCEPTED"
    result["evidence"] = sorted({r[name]["path"] for r in result["commands"] for name in ("stdout", "stderr")}
                                | {review["path"] for review in result["reviews"]})
    write_json(work / LOOP_DIR / "acceptance.json", result)
    return result


def derive(packet, submission, result):
    source = submission["source_sha"]
    expected = bound_contract(packet)
    problems = source_problems(packet, source)
    if problems:
        result["reasons"] += [f"failed: {problem}" for problem in problems]
        return
    result["source_sha"] = source
    result["commands"], _ = run_checks(packet, expected, reusable(packet, source, submission.get("runner_results", [])))
    result["guards"] = guard_results(packet, expected, source)
    result["reasons"] += check_reasons(result)
    result["reasons"] += [f"failed: source changed during checks: {p}" for p in source_problems(packet, source)]
    result["reviews"], result["ignored_reviews"] = review_results(packet, submission.get("reviews", []), source)
    covered = {req for review in result["reviews"] for req in review["requirements"]}
    missing = [req for req in packet["review_requirements"] if req not in covered]
    if missing:
        result["reasons"].append("failed: required review coverage missing for " + ", ".join(missing))
    unresolved = [finding for review in result["reviews"] for finding in review["open_binding_findings"]]
    if unresolved:
        result["reasons"].append("failed: unresolved binding review findings " + ", ".join(unresolved))


class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="devlyn-acceptance ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.work = self.root / "work tree"
        env = {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": str(self.root / "gitconfig"), "GIT_AUTHOR_NAME": "Fixture",
               "GIT_AUTHOR_EMAIL": "fixture@example.invalid", "GIT_COMMITTER_NAME": "Fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid"}
        self.saved = {key: os.environ.get(key) for key in env}
        os.environ.update(env)
        self.addCleanup(lambda: [os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v) for k, v in self.saved.items()])
        subprocess.run(["git", "init", "-q", "--initial-branch=main", str(self.work)], check=True)
        self.write(".gitignore", ".devlyn/\n")
        self.commit("base")
        self.g("switch", "-q", "-c", "devlyn/l/t")
        self.commands = [
            {"argv": [sys.executable, "-c", "import pathlib; print(pathlib.Path('product.txt').read_text())"],
             "stdout_contains": ["ready"], "contract_refs": ["R1"]},
            {"cmd": "echo shell-ok", "stdout_contains": ["shell-ok"], "contract_refs": ["R1"]},
        ]

    def g(self, *args):
        return text(self.work, *args)

    def write(self, rel, data):
        path = self.work / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data, encoding="utf-8")

    def commit(self, message):
        self.g("add", "-A")
        self.g("commit", "-q", "-m", message)
        return self.g("rev-parse", "HEAD")

    def inputs(self, expected=None, review=()):
        base = self.g("rev-parse", "HEAD")
        files = {"docs/specs/l/meta.md": "# meta\n", "docs/specs/l/t/spec.md": "# task R1 R2\n",
                 "docs/specs/l/t/spec.expected.json": json.dumps(expected or {"verification_commands": self.commands}),
                 QUEUE: "- [ ] l.t [T](docs/specs/l/t/spec.md)\n"}
        for rel, data in files.items():
            self.write(rel, data)
        inputs = self.commit("inputs")
        digest = {rel: sha256((self.work / rel).read_bytes()) for rel in files}
        self.packet = {"task": "l.t", "worktree": str(self.work), "branch": "devlyn/l/t", "inputs_sha": inputs, "allocation_base": base,
                       "contract": {"path": str(self.work / "docs/specs/l/t/spec.md"), "sha256": digest["docs/specs/l/t/spec.md"]},
                       "expected": {"path": str(self.work / "docs/specs/l/t/spec.expected.json"), "sha256": digest["docs/specs/l/t/spec.expected.json"]},
                       "meta": {"path": str(self.work / "docs/specs/l/meta.md"), "sha256": digest["docs/specs/l/meta.md"]},
                       "requirements": ["R1", "R2"], "review_requirements": list(review)}
        self.packet_path = self.root / "packet.json"
        self.packet_path.write_text(json.dumps(self.packet), encoding="utf-8")

    def product(self, body="ready"):
        self.write("product.txt", body)
        return self.commit("product")

    def review(self, source, name="review.json", **changes):
        record = {"schema_version": 1, "kind": "devlyn-review", "task": "l.t", "engine": "codex", "model": "fixture-model",
                  "source_sha": source, "contract_sha256": self.packet["contract"]["sha256"],
                  "expected_sha256": self.packet["expected"]["sha256"], "requirements": ["R2"], "findings": [], **changes}
        self.write(f".devlyn/reviews/{name}", json.dumps(record))
        return f".devlyn/reviews/{name}"

    def submit(self, source, **fields):
        path = self.root / "submission.json"
        path.write_text(json.dumps({"schema_version": 1, "task": "l.t", "source_sha": source, **fields}), encoding="utf-8")
        return accept(self.packet_path, path)

    def test_accepts_owned_source_with_checks_and_bound_review(self):
        self.inputs(review=["R2"])
        source = self.product()
        result = self.submit(source, reviews=[self.review(source)])
        self.assertEqual((result["verdict"], result["reasons"]), ("ACCEPTED", []))
        self.assertEqual(json.loads((self.work / LOOP_DIR / "acceptance.json").read_text(encoding="utf-8"))["source_sha"], source)
        self.assertIn(".devlyn/reviews/review.json", result["evidence"])
        for path in result["evidence"]:
            self.assertTrue((self.work / path).is_file(), path)

    def test_command_assertions_timeout_and_spawn_failure(self):
        python = sys.executable
        self.inputs({"verification_commands": [
            {"argv": [python, "-c", "raise SystemExit(3)"], "contract_refs": ["R1"]},
            {"argv": [python, "-c", "print('nope')"], "stdout_contains": ["yes"], "contract_refs": ["R1"]},
            {"argv": [python, "-c", "print('secret')"], "stdout_not_contains": ["secret"], "contract_refs": ["R1"]},
            {"argv": [python, "-c", "import time; time.sleep(5)"], "timeout_sec": 1, "contract_refs": ["R2"]},
            {"argv": ["devlyn-missing-binary-for-test"], "contract_refs": ["R2"]},
        ]})
        result = self.submit(self.product())
        self.assertEqual(result["verdict"], "FAILED")
        self.assertEqual([r["outcome"]["kind"] for r in result["commands"]], ["exit", "exit", "exit", "timeout", "spawn_error"])
        self.assertEqual([bool(r["reason"]) for r in result["commands"]], [True] * 5)
        self.assertIn("exit 3, expected 0", " ".join(result["reasons"]))
        self.assertTrue(all((self.work / r["stdout"]["path"]).is_file() for r in result["commands"]))

    def test_source_and_contract_binding(self):
        self.inputs()
        source = self.product()
        self.write("untracked.txt", "delta")
        self.assertIn("undeclared source delta", " ".join(self.submit(source)["reasons"]))
        (self.work / "untracked.txt").unlink()
        self.g("checkout", "-q", "--detach", source)
        self.assertIn("is not the owned task commit", " ".join(self.submit(source)["reasons"]))
        self.g("switch", "-q", "devlyn/l/t")
        self.assertIn("is not the owned task commit", " ".join(self.submit(self.packet["inputs_sha"])["reasons"]))
        self.write("docs/specs/l/t/spec.md", "# weakened\n")
        weakened = self.commit("weaken")
        self.assertIn("candidate edits loop inputs: docs/specs/l/t/spec.md", " ".join(self.submit(weakened)["reasons"]))
        self.packet["contract"]["sha256"] = "0" * 64
        self.packet_path.write_text(json.dumps(self.packet), encoding="utf-8")
        self.assertIn("differs from the task packet", " ".join(self.submit(weakened)["reasons"]))

    def test_review_binding_and_findings(self):
        self.inputs(review=["R2"])
        first = self.product()
        stale = self.review(first, "stale.json")
        source = self.product("ready again")
        for reviews, message in (
            ([stale], "required review coverage missing for R2"),
            ([self.review(source, "contract.json", expected_sha256="0" * 64)], "required review coverage missing for R2"),
            ([self.review(source, "rejected.json", findings=[{"id": "F1", "binding": True, "disposition": "rejected"}])], "malformed review record"),
            ([self.review(source, "open.json", findings=[{"id": "F2", "binding": True, "disposition": "open"}])], "unresolved binding review findings F2"),
        ):
            result = self.submit(source, reviews=reviews)
            self.assertEqual(result["verdict"], "FAILED")
            self.assertIn(message, " ".join(result["reasons"]))
        result = self.submit(source, reviews=[stale, self.review(source, findings=[{"id": "F3", "binding": False, "disposition": "open"}])])
        self.assertEqual(result["verdict"], "ACCEPTED")
        self.assertEqual([item["path"] for item in result["ignored_reviews"]], [stale])

    def test_runner_result_with_a_source_change_is_never_reused(self):
        mutate = [sys.executable, "-c", "import pathlib; p = pathlib.Path('product.txt'); p.write_text(p.read_text() + '!'); print('ok')"]
        self.inputs({"verification_commands": [{"argv": mutate, "stdout_contains": ["ok"], "contract_refs": ["R1", "R2"]}]})
        source = self.product()
        path, checks = run(self.packet_path)
        self.assertTrue(checks["commands"][0]["passed"])
        self.assertIn("failed: source changed during checks", " ".join(checks["reasons"]))
        self.g("checkout", "--", "product.txt")
        result = self.submit(source, runner_results=[relative(self.work, path)])
        self.assertEqual(result["verdict"], "FAILED")
        self.assertNotIn("reused_from", result["commands"][0])
        self.assertIn("failed: source changed during checks", " ".join(result["reasons"]))

    def test_malformed_executor_records_fail_with_a_named_reason(self):
        self.inputs(review=["R2"])
        source = self.product()
        malformed = self.review(source, "malformed.json", requirements=[{"id": "R2"}])
        result = self.submit(source, reviews=[malformed])
        self.assertEqual(result["verdict"], "FAILED")
        self.assertIn(f"malformed review record {malformed}", " ".join(result["reasons"]))
        path, _ = run(self.packet_path)
        checks = json.loads(path.read_text(encoding="utf-8"))
        del checks["commands"][0]["index"]
        path.write_text(json.dumps(checks), encoding="utf-8")
        result = self.submit(source, runner_results=[relative(self.work, path)], reviews=[self.review(source)])
        self.assertEqual(result["verdict"], "FAILED")
        self.assertIn("malformed command records", " ".join(result["reasons"]))
        blocked = self.submit(source, blockers=[{"kind": ["failed"], "detail": "unhashable kind"}])
        self.assertEqual(blocked["verdict"], "FAILED")
        self.assertIn("submission blockers must be", " ".join(blocked["reasons"]))

    def test_reuses_intact_runner_results_and_reexecutes_altered_evidence(self):
        counter = [sys.executable, "-c", "import pathlib; p = pathlib.Path('.devlyn/count'); p.parent.mkdir(exist_ok=True); "
                   "p.write_text(str(int(p.read_text()) + 1) if p.exists() else '1'); print('counted')"]
        self.inputs({"verification_commands": [{"argv": counter, "stdout_contains": ["counted"], "contract_refs": ["R1", "R2"]}]})
        source = self.product()
        path, checks = run(self.packet_path)
        self.assertEqual(checks["reasons"], [])
        runner = relative(self.work, path)
        self.assertEqual(self.submit(source, runner_results=[runner])["commands"][0]["reused_from"], runner)
        self.assertEqual((self.work / ".devlyn/count").read_text(), "1")
        (self.work / checks["commands"][0]["stdout"]["path"]).write_text("altered", encoding="utf-8")
        result = self.submit(source, runner_results=[runner])
        self.assertNotIn("reused_from", result["commands"][0])
        self.assertEqual(((self.work / ".devlyn/count").read_text(), result["verdict"]), ("2", "ACCEPTED"))

    def test_guards_and_blockers(self):
        self.inputs({"verification_commands": self.commands, "required_files": ["missing.txt"], "forbidden_files": ["product.txt"],
                     "forbidden_patterns": [{"pattern": "rea+dy", "description": "no ready", "severity": "disqualifier"},
                                            {"pattern": "ready", "description": "warn only", "severity": "warning"}]})
        source = self.product()
        result = self.submit(source)
        failed = {g["rule"] for g in result["guards"] if not g["passed"]}
        self.assertEqual(failed, {"forbidden_patterns/0", "forbidden_patterns/1", "required_files", "forbidden_files"})
        self.assertNotIn("warn only", " ".join(result["reasons"]))
        blocked = self.submit(source, blockers=[{"kind": "needs-review", "detail": "Which store wins?"}])
        self.assertEqual((blocked["verdict"], blocked["reasons"], blocked["commands"]), ("FAILED", ["needs-review: Which store wins?"], []))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    actions = parser.add_subparsers(dest="action")
    runner = actions.add_parser("run")
    runner.add_argument("--packet", required=True)
    runner.add_argument("--source")
    acceptance = actions.add_parser("accept")
    acceptance.add_argument("--packet", required=True)
    acceptance.add_argument("--submission", required=True)
    args = parser.parse_args()
    if args.self_test:
        result = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(AcceptanceTests))
        if result.wasSuccessful():
            print(f"acceptance self-test: PASS ({result.testsRun} tests)")
        return 0 if result.wasSuccessful() else 1
    if args.action is None:
        parser.error("run or accept is required")
    try:
        if args.action == "run":
            path, result = run(args.packet, args.source)
            output = {"status": "CHECKED", "result": str(path), "passed": not result["reasons"], "reasons": result["reasons"]}
        else:
            result = accept(args.packet, args.submission)
            output = {"status": result["verdict"], "result": str(Path(load_packet(args.packet)["worktree"]) / LOOP_DIR / "acceptance.json"),
                      "reasons": result["reasons"]}
        print(json.dumps(output, sort_keys=True))
        return 0
    except (AcceptanceError, OSError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, sort_keys=True))
        return 1


if __name__ == "__main__":
    shared("platform-support")["configure_utf8"]()
    sys.exit(main())
