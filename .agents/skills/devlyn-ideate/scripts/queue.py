#!/usr/bin/env python3
"""Ideate loop driver: package validation, the queue, locks, reconciliation and the serial drain.

`check` validates a loop package, `add` captures it with its queue rows (which may
replace one legacy row), `status` shows the reconciled queue and `drain -- <argv>` runs each
eligible task through allocation, committed inputs, one host-supplied executor
exchange, evidence-derived acceptance, the terminal transition and delivery.
Protocol and commands: ../references/loop.md; formats: ../references/package-format.md.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime
import functools
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import shlex
import subprocess
import sys
import tempfile
import time
import unittest

SKILLS = Path(__file__).resolve().parents[2]
QUEUE = "docs/specs/queue.md"  # The legacy queue: read for materialize, never written.
CAPTURES = "refs/devlyn/captures/"
SENTINEL = "<!-- devlyn:verification -->"
ID = r"[a-z0-9][a-z0-9-]{0,62}"
SHA_RE = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
JSON_FENCE_RE = re.compile(r"(?ms)^```json[ \t]*\n(.*?)\n```[ \t]*$")
ROW_RE = re.compile(r"- \[(?P<mark>[ xF])\] (?P<text>.*)")
ITEM_RE = re.compile(rf"(?P<identity>(?P<loop>{ID})\.(?P<task>{ID})) \[(?P<title>(?:[^\]\\\n]|\\.)*)\]"
                     r"\(docs/specs/(?P=loop)/(?P=task)/spec\.md\)(?P<rest>(?: — .*)?)")
REPLACES_RE = re.compile(r"<!-- replaces docs/specs/queue\.md row \(occurrence ([1-9][0-9]*)\): (- \[ \] .*) -->")
REQUIREMENT_RE = re.compile(r"[-*] (R[1-9][0-9]*): \S")
META_SECTIONS = ("Intent", "Constraints and exclusions", "Tasks", "Overall acceptance", "Execution policy",
                 "Decisions and assumptions")
TASK_SECTIONS = ("Context and goal", "Requirements", "Scope and constraints", "Out of scope", "Prerequisite inputs",
                 "Verification", "Deliverable and cleanup")
MANIFEST_KEYS = {"schema_version", "loop_id", "base_ref", "base_sha", "delivery", "tasks", "integration_task_id"}
FRONTMATTER_KEYS = {"id", "loop_id", "title", "kind", "review_requirements", "complexity"}
KINDS = {"feature", "spike", "prototype"}
UNSUPPORTED = {"process_evidence": "phase process obligations", "required_risk_probe_requirements": "risk-probe obligations",
               "tier_a_waivers": "benchmark scope waivers", "spec_output_files": "benchmark scope surfaces"}
SETTLED = {"LOCAL_ONLY", "COMPLETE", "FAILED"}
OBLIGATIONS = [
    "Work only in this worktree on its owned branch under the installed methodology; never edit the loop package or docs/specs/queue.md.",
    "Commit the final candidate on the owned branch; leave no uncommitted or untracked source and remove residue the change created.",
    "Run `runner` on the committed candidate; review records must bind engine, model, that source and both contract digests.",
    "Write `submission` and exit; report a blocker instead of weakening acceptance.",
]


class LoopError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise LoopError(message)


@functools.lru_cache(maxsize=None)
def shared(name):
    return runpy.run_path(str(SKILLS / "_shared" / f"{name}.py"))


@functools.lru_cache(maxsize=None)
def acceptance():
    return runpy.run_path(str(Path(__file__).with_name("acceptance.py")))


def git_run(cwd, *args, data=None, env=None, ok=(0,)):
    result = subprocess.run(["git", "-C", str(cwd), *args], input=data, capture_output=True, env=env)
    require(result.returncode in ok, f"git {' '.join(args[:2])}: {result.stderr.decode('utf-8', 'replace').strip()}")
    return result


def git(cwd, *args, **kwargs):
    return git_run(cwd, *args, **kwargs).stdout.decode("utf-8").strip()


def show(cwd, rev, path):
    result = git_run(cwd, "cat-file", "blob", f"{rev}:{path}", ok=(0, 128))
    return result.stdout if result.returncode == 0 else None


def ancestor(cwd, old, new):
    return git_run(cwd, "merge-base", "--is-ancestor", old, new, ok=(0, 1)).returncode == 0


def read_text(path):
    try:
        return Path(path).read_bytes().decode("utf-8").replace("\r\n", "\n")
    except (OSError, UnicodeError) as exc:
        raise LoopError(f"{path}: {exc}") from exc


def read_json(path):
    try:
        return shared("expected-contract")["loads_strict_json"](read_text(path))
    except ValueError as exc:
        raise LoopError(f"{path}: {exc}") from exc


def write_json(path, value):
    acceptance()["write_json"](path, value)


def ref_value(cwd, ref):
    return git_run(cwd, "rev-parse", "--verify", "--quiet", ref, ok=(0, 1)).stdout.decode("utf-8").strip()


def progress(identity, event):
    print(f"devlyn-loop: {identity}: {event}", file=sys.stderr, flush=True)


def repository(path):
    anchor = Path(git(Path(path), "rev-parse", "--show-toplevel")).resolve()
    return anchor, Path(git(anchor, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve()


@contextlib.contextmanager
def lock(common, name, *, blocking):
    """Native locks on the common Gitdir: drain.lock for a controller's lifetime, queue.lock for short mutations."""
    directory = common / "devlyn-loops"
    directory.mkdir(exist_ok=True)
    with contextlib.ExitStack() as stack:
        try:
            stack.enter_context(shared("platform-support")["file_lock"](directory / name, blocking=blocking))
        except BlockingIOError as exc:
            raise LoopError(f"another drain is active for this repository ({directory / name})") from exc
        yield


def sections(text, path):
    found, current, fence = {}, None, False
    for line in text.split("\n"):
        fence ^= line.startswith("```")
        match = None if fence else re.fullmatch(r"## +(\S.*?)\s*", line)
        if match:
            current = match.group(1)
            require(current not in found, f"{path}: duplicate section '## {current}'")
            found[current] = []
        elif current is not None:
            found[current].append(line)
    return {name: "\n".join(lines).strip() for name, lines in found.items()}


def require_sections(found, names, path):
    missing = [name for name in names if not found.get(name)]
    require(not missing, f"{path}: missing or empty section(s): " + ", ".join(f"'## {name}'" for name in missing))


def frontmatter(text, path):
    end = text.find("\n---\n", 3)
    require(text.startswith("---\n") and end > 0, f"{path}: must start with a --- frontmatter block closed by ---")
    values = {}
    for line in filter(str.strip, text[4:end].split("\n")):
        key, separator, value = (part.strip() for part in line.partition(":"))
        require(separator and re.fullmatch(r"[a-z_]+", key) and key not in values, f"{path}: invalid or duplicate frontmatter line {line!r}")
        values[key] = ([item.strip().strip("\"'") for item in value[1:-1].split(",") if item.strip()]
                       if value.startswith("[") and value.endswith("]") else value.strip("\"'"))
    return values, text[end + 5:]


def find_cycle(graph):
    state, stack = {}, []

    def visit(node):
        state[node] = "open"
        stack.append(node)
        for dep in graph[node]:
            if state.get(dep) == "open":
                return stack[stack.index(dep):] + [dep]
            if dep not in state and (cycle := visit(dep)):
                return cycle
        state[node] = "done"
        stack.pop()
        return None

    return next((cycle for node in graph if node not in state and (cycle := visit(node))), None)


def closure(graph, node):
    seen, todo = set(), list(graph[node])
    while todo:
        dep = todo.pop()
        if dep not in seen:
            seen.add(dep)
            todo.extend(graph[dep])
    return seen


def check_manifest(anchor, manifest, loop_id, meta):
    def fail(message):
        raise LoopError(f"{meta}: manifest {message}")

    if not isinstance(manifest, dict) or set(manifest) != MANIFEST_KEYS:
        fail("keys must be exactly " + ", ".join(sorted(MANIFEST_KEYS)))
    if manifest["schema_version"] != 1 or isinstance(manifest["schema_version"], bool):
        fail("schema_version must be 1")
    if manifest["loop_id"] != loop_id or not re.fullmatch(ID, loop_id):
        fail(f"loop_id must equal its directory name and match {ID}")
    base_ref, base_sha = manifest["base_ref"], manifest["base_sha"]
    if not isinstance(base_ref, str) or not base_ref or git_run(anchor, "check-ref-format", "refs/heads/" + base_ref, ok=(0, 1)).returncode:
        fail("base_ref must be a branch name")
    if not isinstance(base_sha, str) or not SHA_RE.fullmatch(base_sha) or git_run(anchor, "cat-file", "-e", base_sha + "^{commit}", ok=(0, 1, 128)).returncode:
        fail("base_sha must name an exact commit in this repository")
    if manifest["delivery"] not in {"auto", "pr", "local-only"}:
        fail("delivery must be auto, pr or local-only")
    tasks = manifest["tasks"]
    if not isinstance(tasks, list) or not tasks:
        fail("tasks must be a non-empty list")
    order = []
    for entry in tasks:
        if not isinstance(entry, dict) or set(entry) != {"id", "spec", "depends_on"}:
            fail("tasks need exactly id, spec and depends_on")
        task, deps = entry["id"], entry["depends_on"]
        if not isinstance(task, str) or not re.fullmatch(ID, task) or task in order:
            fail(f"task id {task!r} must be unique and match {ID}")
        if entry["spec"] != f"{task}/spec.md":
            fail(f"task {task} spec link must be {task}/spec.md")
        if not isinstance(deps, list) or not all(isinstance(dep, str) for dep in deps) or len(set(deps)) != len(deps):
            fail(f"task {task} depends_on must list distinct task ids")
        order.append(task)
    graph = {entry["id"]: entry["depends_on"] for entry in tasks}
    for task, deps in graph.items():
        if unknown := [dep for dep in deps if dep not in graph]:
            fail(f"task {task} depends on unknown task(s): {', '.join(unknown)}")
    if cycle := find_cycle(graph):
        fail("dependency cycle: " + " -> ".join(cycle))
    for task, deps in graph.items():
        if late := [dep for dep in deps if order.index(dep) > order.index(task)]:
            fail(f"task {task} must be listed after its dependencies: {', '.join(late)}")
    final = manifest["integration_task_id"]
    if final != order[-1] or set(order[:-1]) - closure(graph, final):
        fail("integration_task_id must name the last task, which depends directly or transitively on every other task")


def package_bytes(anchor, rev, rel):
    """A package file's bytes in its loop's capture `rev`, or in the checkout when the loop has no record; None if absent."""
    if rev is not None:
        return show(anchor, rev, rel)
    return (anchor / rel).read_bytes() if (anchor / rel).is_file() else None


def package_text(anchor, rev, rel):
    """A package file's text and the label that names it in errors."""
    label = anchor / rel if rev is None else f"{rev}:{rel}"
    data = package_bytes(anchor, rev, rel)
    require(data is not None, f"{label}: no such file")
    try:
        return data.decode("utf-8").replace("\r\n", "\n"), label
    except UnicodeError as exc:
        raise LoopError(f"{label}: {exc}") from exc


def load_expected(text, path, requirements, review):
    try:
        data = shared("expected-contract")["loads_strict_json"](text)
    except ValueError as exc:
        raise LoopError(f"{path}: {exc}") from exc

    def fail(message):
        raise LoopError(f"{path}: {message}")

    for key, label in UNSUPPORTED.items():
        if isinstance(data, dict) and key in data:
            fail(f"{key} ({label}) is unsupported by loop acceptance; translate it into verification_commands or review_requirements without weakening it")
    if error := shared("expected-contract")["validate_expected_shape"](data):
        fail(error)
    commands = data.get("verification_commands", [])
    for index, command in enumerate(commands):
        refs = command.get("contract_refs", [])
        if not refs or any(ref not in requirements for ref in refs):
            fail(f"verification_commands[{index}].contract_refs must name requirement IDs of this task")
    for index, pattern in enumerate(data.get("forbidden_patterns", [])):
        try:
            re.compile(pattern["pattern"])
        except re.error as exc:
            fail(f"forbidden_patterns[{index}] is not a valid regex: {exc}")
    if data.get("pure_design") is True:
        if commands or set(review) != set(requirements):
            fail("pure_design permits no verification_commands and needs review_requirements covering every requirement")
    elif not commands:
        fail("runtime tasks need verification_commands; a pure_design task declares it with full review coverage")
    covered = {ref for command in commands for ref in command["contract_refs"]} | set(review)
    if uncovered := [req for req in requirements if req not in covered]:
        fail("requirement(s) without command or review coverage: " + ", ".join(uncovered))
    return data


def load_task(anchor, manifest, entry, rev):
    loop_id, task = manifest["loop_id"], entry["id"]
    text, path = package_text(anchor, rev, f"docs/specs/{loop_id}/{task}/spec.md")
    front, body = frontmatter(text, path)

    def fail(message):
        raise LoopError(f"{path}: {message}")

    if "status" in front:
        fail("status is queue state, not contract; remove it from the frontmatter")
    if unknown := sorted(set(front) - FRONTMATTER_KEYS):
        fail(f"unknown frontmatter key(s): {', '.join(unknown)}")
    if missing := sorted(FRONTMATTER_KEYS - {"complexity"} - set(front)):
        fail(f"missing frontmatter key(s): {', '.join(missing)}")
    if (front["id"], front["loop_id"]) != (task, loop_id):
        fail("frontmatter id and loop_id must match the manifest")
    if not isinstance(front["title"], str) or not front["title"]:
        fail("title must be a non-empty line")
    if not isinstance(front["kind"], str) or front["kind"] not in KINDS:
        fail("kind must be feature, spike or prototype")
    review = front["review_requirements"]
    if not isinstance(review, list):
        fail("review_requirements must be a list such as [R2] or []")
    found = sections(body, path)
    require_sections(found, TASK_SECTIONS, path)
    if not re.search(rf"(?m)^{re.escape(SENTINEL)}\n## +Verification[ \t]*$", body):
        fail(f"'## Verification' must directly follow the {SENTINEL} sentinel line")
    requirements = [m.group(1) for line in found["Requirements"].split("\n") if (m := REQUIREMENT_RE.match(line))]
    if not requirements or len(set(requirements)) != len(requirements):
        fail("Requirements need unique stable IDs written as '- R1: <obligation>'")
    if unknown := [req for req in review if req not in requirements]:
        fail(f"review_requirements name unknown requirement(s): {', '.join(unknown)}")
    expected, expected_path = package_text(anchor, rev, f"docs/specs/{loop_id}/{task}/spec.expected.json")
    return {"id": task, "title": front["title"], "kind": front["kind"], "requirements": requirements, "review": review,
            "depends_on": entry["depends_on"], "expected": load_expected(expected, expected_path, requirements, review)}


def load_manifest(anchor, loop_id, rev=None):
    """The loop's meta.md text and its validated manifest, from its capture `rev` or, without a record, the checkout."""
    text, meta = package_text(anchor, rev, f"docs/specs/{loop_id}/meta.md")
    require_sections(sections(text, meta), META_SECTIONS, meta)
    fences = JSON_FENCE_RE.findall(text)
    require(len(fences) == 1, f"{meta}: needs exactly one fenced json manifest, found {len(fences)}")
    try:
        manifest = shared("expected-contract")["loads_strict_json"](fences[0])
    except ValueError as exc:
        raise LoopError(f"{meta}: manifest is not strict JSON: {exc}") from exc
    check_manifest(anchor, manifest, loop_id, meta)
    return text, manifest


def load_package(anchor, loop_id, rev=None):
    """The manifest and each task's contract, or under `invalid` the task's validation error."""
    text, manifest = load_manifest(anchor, loop_id, rev)
    tasks, invalid = {}, {}
    for entry in manifest["tasks"]:
        try:
            tasks[entry["id"]] = load_task(anchor, manifest, entry, rev)
        except LoopError as exc:
            invalid[entry["id"]] = str(exc)
    return {"loop_id": loop_id, "meta_text": text, "manifest": manifest, "tasks": tasks, "invalid": invalid}


def package_of(anchor, meta):
    meta = Path(meta).resolve()
    loop_id = meta.parent.name
    require(meta.name == "meta.md" and meta.parent.parent == anchor / "docs/specs", f"package must be <repo>/docs/specs/<loop-id>/meta.md: {meta}")
    package = load_package(anchor, loop_id)
    if package["invalid"]:
        raise LoopError(next(iter(package["invalid"].values())))
    return package


def escape(title):
    return title.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


def row_line(identity, title):
    loop, task = identity.split(".")
    return f"- [ ] {identity} [{escape(title)}](docs/specs/{loop}/{task}/spec.md)"


def parse_queue(data, label=QUEUE):
    try:
        lines = data.decode("utf-8").split("\n")
    except UnicodeError as exc:
        raise LoopError(f"{label} is not UTF-8: {exc}") from exc
    rows = []
    for index, raw in enumerate(lines):
        match = ROW_RE.fullmatch(raw.removesuffix("\r"))
        if not match:
            continue
        row = {"index": index, "line": match.group(0), "mark": match["mark"], "text": match["text"].rstrip(), "identity": None}
        # Only a row matching the full loop-row grammar is a loop row; any other row is a legacy row.
        item = ITEM_RE.fullmatch(row["text"])
        if item and bool(item["rest"]) == (match["mark"] == "F"):
            row.update(identity=item["identity"], loop=item["loop"], task=item["task"], rest=item["rest"])
        rows.append(row)
    identities = [row["identity"] for row in rows if row["identity"]]
    duplicates = sorted({identity for identity in identities if identities.count(identity) > 1})
    require(not duplicates, f"{label}: duplicate queue identity: {', '.join(duplicates)}")
    return rows


def with_rows(data, lines):
    """`data` with each identity's row replaced by `lines[identity]`, every other byte unchanged."""
    out = data.split(b"\n")
    for row in parse_queue(data):
        if row["identity"] in lines:
            ending = b"\r" if out[row["index"]].endswith(b"\r") else b""
            out[row["index"]] = lines[row["identity"]].encode("utf-8") + ending
    return b"\n".join(out)


def transition(before, identity, mark, suffix=""):
    """The only legal transition: the identity's pending row becomes [x] or [F] with every other byte unchanged."""
    row = next((row for row in parse_queue(before) if row["identity"] == identity), None)
    require(row is not None and row["mark"] == " ", f"{identity} has no pending queue row to transition")
    return with_rows(before, {identity: f"- [{mark}] {row['text']}{suffix}"})


def loop_queue(loop):
    return f"docs/specs/{loop}/queue.md"


def loop_rows(loop, package, target):
    """The queue file add generates for a loop: the legacy row it replaces, if any, then a row per task in manifest
    order, each line one blank line from the next (package-format.md, Queue rows)."""
    lines = [f"<!-- replaces {QUEUE} row (occurrence {target['occurrence']}): {target['line']} -->"] if target else []
    lines += [row_line(f"{loop}.{task['id']}", task["title"]) for task in package["tasks"].values()]
    return ("\n\n".join(lines) + "\n").encode("utf-8")


def parse_loop(data, loop, label):
    """A loop's queue file: its rows, each a task row of the loop, and the legacy row it replaces as (occurrence, line)."""
    require(data is not None, f"{label}: no such file")
    rows = parse_queue(data, label)
    require(all(row["identity"] and row["loop"] == loop for row in rows), f"{label}: every row must be a task row of loop {loop}")
    targets = [(int(m[1]), m[2]) for line in data.decode("utf-8").split("\n") if (m := REPLACES_RE.fullmatch(line.removesuffix("\r")))]
    require(len(targets) <= 1, f"{label}: replaces more than one legacy row")
    return rows, targets[0] if targets else None


def one_line(text):
    text = " ".join(text.split())
    return text if len(text) <= 200 else text[:199] + "…"


def branch_of(identity):
    return "devlyn/" + identity.replace(".", "/")


def receipt_path(common, identity):
    return common / "devlyn-completion" / hashlib.sha256(branch_of(identity).encode()).hexdigest()[:24] / "receipt.json"


def added_path(common, loop):
    return common / "devlyn-loops" / loop / "added.json"


def records(common):
    """Each loop's add record, in add order."""
    found = []
    for path in (common / "devlyn-loops").glob("*/added.json"):
        added = read_json(path)
        require(isinstance(added, dict) and added.get("loop_id") == path.parent.name and type(added.get("sequence")) is int
                and all(isinstance(added.get(key), str) for key in ("delivery", "commit", "origin", "branch")), f"{path}: malformed add record")
        found.append(added)
    return {added["loop_id"]: added for added in sorted(found, key=lambda added: added["sequence"])}


def queue_view(anchor, recorded):
    """The rows status and drain read (loop.md step 1): the legacy queue's raw rows in file order, a row that one loop
    replaces shown as that loop's rows in its place; then the other recorded loops in add order; then the loops without a
    record, as in a fresh clone, from the checkout's tracked queue files in loop-id order. A legacy row claimed by more than
    one loop, or a claim matching no row, replaces nothing."""
    legacy = anchor / QUEUE
    raw = [row for row in parse_queue(legacy.read_bytes() if legacy.exists() else b"") if not row["identity"]]
    loops = {loop: parse_loop(show(anchor, added["commit"], loop_queue(loop)), loop, f"{CAPTURES}{loop}:{loop_queue(loop)}")
             for loop, added in recorded.items()}
    for rel in sorted(filter(None, git(anchor, "ls-files", "-z", "--", ":(glob)docs/specs/*/queue.md").split("\0"))):
        loop, data = rel.split("/")[2], (anchor / rel).read_bytes() if (anchor / rel).is_file() else None
        # A file holding no task row of its directory's loop is not a loop's queue file.
        if loop not in recorded and data and any(row.get("loop") == loop for row in parse_queue(data, anchor / rel)):
            loops[loop] = parse_loop(data, loop, anchor / rel)
    claims = {}
    for loop, (_, target) in loops.items():
        if target:
            claims.setdefault(target, []).append(loop)
    placed = {}
    for (occurrence, line), owners in claims.items():
        matches = [row["index"] for row in raw if row["line"] == line]
        if len(owners) == 1 and len(matches) >= occurrence:
            placed[matches[occurrence - 1]] = owners[0]
    rows = []
    for row in raw:
        rows += loops[placed[row["index"]]][0] if row["index"] in placed else [row]
    return rows + [row for loop, (own, _) in loops.items() if loop not in placed.values() for row in own]


def package_state(cwd, commit, loop):
    """Each package file of the capture `commit` as the checkout `cwd` holds it: missing, equal (line endings aside) or
    different."""
    states = {}
    for rel in filter(None, git(cwd, "ls-tree", "-r", "-z", "--name-only", commit).split("\0")):
        if rel != loop_queue(loop):
            data = (cwd / rel).read_bytes() if (cwd / rel).is_file() else None
            states[rel] = ("missing" if data is None else "equal" if data.replace(b"\r\n", b"\n") == show(cwd, commit, rel).replace(b"\r\n", b"\n")
                           else "different")
    return states


def clean(common, recorded):
    """Remove each recorded loop's untracked package originals that equal its capture from the checkout that added it,
    keeping and naming any other copy; returns what remains to report (package-format.md, Commands)."""
    notes = []
    for origin in dict.fromkeys(added["origin"] for added in recorded.values()):
        root = Path(origin)
        if not (root / "docs/specs").is_dir():
            continue
        untracked = set(filter(None, git(root, "ls-files", "--others", "-z", "--", "docs/specs").split("\0")))
        for loop, added in recorded.items():
            package = f"docs/specs/{loop}/"
            if added["origin"] != origin or not any(rel.startswith(package) for rel in untracked):
                continue
            for rel, state in package_state(root, added["commit"], loop).items():
                if rel in untracked and state == "different":
                    notes.append(f"{root / rel}: kept, it differs from the captured package {CAPTURES}{loop}")
                elif rel in untracked and state == "equal":
                    try:
                        (root / rel).unlink()
                    except OSError as exc:
                        notes.append(f"{root / rel}: incomplete cleanup: {exc}")
            for directory, _, _ in os.walk(root / package, topdown=False):
                with contextlib.suppress(OSError):
                    os.rmdir(directory)
    return notes


def task_complete(action, **values):
    helper = shared("task-complete")
    try:
        return helper[action](argparse.Namespace(**values))
    except (helper["CompletionError"], OSError, KeyError, TypeError, ValueError) as exc:
        raise LoopError(f"task-complete {action}: {exc}") from exc


def derive_state(anchor, common, row, claims, rev):
    identity = row["identity"]
    state = {"kind": {" ": "pending", "x": "accepted", "F": "failed"}[row["mark"]], "receipt": None, "path": None}
    require(len(claims) <= 1, f"conflicting receipts for {identity}: {', '.join(str(path) for path, _ in claims)}")
    if not claims:
        return state
    path, receipt = claims[0]
    require(receipt.get("branch") == branch_of(identity) and path == receipt_path(common, identity),
            f"receipt {path} claims {identity} from branch {receipt.get('branch')!r}; conflicting ownership, inspect it")
    require(receipt.get("allocation") == "owned", f"{identity}: allocation was interrupted ({path}); uncertain ownership blocks adoption, inspect it")
    result = None if not receipt.get("acceptance") else "failed" if receipt.get("product") == "FAILED" else "accepted"
    require(row["mark"] == " " or result == state["kind"],
            f"conflicting terminal state for {identity}: queue row [{row['mark']}] but receipt {path} is {result or 'unbound'}")
    if result:
        recovery = ref_value(anchor, receipt["recovery_ref"])
        # Or an attachment interrupted after moving the recovery ref, before saving the receipt; drain completes it.
        require(recovery == receipt["publish_sha"] or not receipt.get("queue") and bool(recovery)
                and is_terminal(anchor, receipt, identity, recovery),
                f"{identity}: recovery ref {receipt['recovery_ref']} is {recovery or 'missing'}, receipt binds {receipt['publish_sha']}")
        if receipt.get("queue"):
            marks = [r["mark"] for r in parse_queue(show(anchor, receipt["publish_sha"], receipt["queue"]["file"]) or b"") if r["identity"] == identity]
            require(marks == ["x" if result == "accepted" else "F"], f"{identity}: terminal commit {receipt['publish_sha']} does not carry its {result} mark")
    packet = path.parent / "packet.json"
    if not result and packet.exists():
        bound = read_json(packet)
        for key in ("contract", "expected"):
            rel = Path(bound[key]["path"]).relative_to(bound["worktree"]).as_posix()
            current = package_bytes(anchor, rev, rel)
            if current is None or hashlib.sha256(current).hexdigest() != bound[key]["sha256"]:
                # Drain fails this task alone; the revision is planned as a new task.
                state["inputs_changed"] = f"inputs-changed: {rel} changed after its inputs were committed; plan the revision as a new task"
                break
    state.update(kind=result or "active", path=path, receipt=receipt)
    return state


def view(anchor, common, local_only=False):
    """Reconcile the queue with every receipt and recovery ref before anything is selected."""
    with lock(common, "queue.lock", blocking=True):
        recorded = records(common)
        cleanup = clean(common, recorded)
        rows = queue_view(anchor, recorded)
    claims, unreadable = {}, []
    for path in sorted((common / "devlyn-completion").glob("*/receipt.json")):
        try:
            receipt = read_json(path)
            claims.setdefault(receipt["task"], []).append((path, receipt))
        except (LoopError, KeyError, TypeError) as exc:
            unreadable.append(f"{path}: {exc}")
    v = {"anchor": anchor, "common": common, "rows": rows, "records": recorded, "packages": {}, "manifests": {}, "states": {},
         "unreadable": unreadable, "cleanup": cleanup, "local_only": local_only}
    errors = {}
    for row in v["rows"]:
        if row["identity"]:
            state = v["states"][row["identity"]] = derive_state(anchor, common, row, claims.get(row["identity"], []), capture(v, row["loop"]))
            # A changed active task needs no current package text; a validation failure stops only its own task.
            if state["kind"] == "pending" or state["kind"] == "active" and "inputs_changed" not in state:
                loop = row["loop"]
                if loop not in v["packages"] and loop not in errors:
                    try:
                        v["packages"][loop] = load_package(anchor, loop, capture(v, loop))
                    except LoopError as exc:
                        errors[loop] = str(exc)
                package = v["packages"].get(loop)
                if problem := errors.get(loop) or package["invalid"].get(row["task"]) or (
                        None if row["task"] in package["tasks"] else f"{row['identity']} is not a task of loop {loop}"):
                    state["invalid"] = problem
    for row in v["rows"]:
        state = v["states"].get(row["identity"])
        for dep in v["packages"][row["loop"]]["tasks"][row["task"]]["depends_on"] if state and state["kind"] == "pending" and "invalid" not in state else []:
            dep_state = v["states"].get(f"{row['loop']}.{dep}")
            require(dep_state is not None, f"{row['identity']} depends on {row['loop']}.{dep}, which is not queued")
            if dep_state["kind"] in {"failed", "blocked"}:
                state.update(kind="blocked", blocker=f"{row['loop']}.{dep}", root=dep_state.get("root") or dep_state)
                break
    return v


def capture(v, loop):
    """The commit holding the loop's captured package, or None for a loop with no record (its checkout's files)."""
    return v["records"][loop]["commit"] if loop in v["records"] else None


def is_local(v, loop):
    added, package = v["records"].get(loop), v["packages"].get(loop)
    delivery = added["delivery"] if added else package and package["manifest"]["delivery"]
    return (v["local_only"] or delivery == "local-only"
            or any(s["receipt"] and s["receipt"].get("local_only") for i, s in v["states"].items() if i.split(".")[0] == loop))


def delivered(receipt):
    return receipt.get("delivery") == "COMPLETE" or bool(receipt.get("merge"))


def carrier(v, loop):
    """The auto/pr task whose undelivered, unfailed PR carries the loop's package, which its base lacked (loop.md step 2)."""
    return None if is_local(v, loop) else next((
        row["identity"] for row in v["rows"] if row.get("loop") == loop and (state := v["states"][row["identity"]])["receipt"]
        and state["kind"] != "failed" and not delivered(state["receipt"]) and show(v["anchor"], state["receipt"]["baseline"], loop_queue(loop)) is None), None)


def waiting(v, row):
    if invalid := v["states"][row["identity"]].get("invalid"):
        return invalid
    local = is_local(v, row["loop"])
    for dep in v["packages"][row["loop"]]["tasks"][row["task"]]["depends_on"]:
        identity = f"{row['loop']}.{dep}"
        state = v["states"][identity]
        if state["kind"] != "accepted":
            return f"waiting for {identity} ({state['kind']})"
        if not state["receipt"]:
            return f"prerequisite {identity} has no receipt-bound accepted source"
        if not local and not delivered(state["receipt"]):
            return f"awaiting delivery of {identity}"
    if local:
        return local_start(v, row["loop"])[1]
    if plan := carrier(v, row["loop"]):
        return f"awaiting delivery of {plan}, whose PR carries its loop's package"
    return None


def next_task(v, attempted):
    """Earliest unsettled receipt first, then the earliest eligible pending row in physical order."""
    for row in v["rows"]:
        state = v["states"].get(row["identity"])
        if state and state["receipt"] and row["identity"] not in attempted and "invalid" not in state and (
                state["kind"] == "active" or not state["receipt"].get("queue") or state["receipt"].get("delivery") not in SETTLED):
            return row
    return next((row for row in v["rows"] if row["identity"] not in attempted and v["states"].get(row["identity"], {}).get("kind") == "pending"
                 and waiting(v, row) is None), None)


def annotate(v, refused):
    """Name each task's wait: a pending task's reason from waiting(), else why this drain did not advance it."""
    for row in v["rows"]:
        state = v["states"].get(row["identity"])
        if state and (reason := state["kind"] == "pending" and waiting(v, row) or refused.get(row["identity"])):
            state["waiting"] = reason


def frontier(v, loop):
    accepted = [v["states"][row["identity"]] for row in v["rows"] if row.get("loop") == loop
                and v["states"][row["identity"]]["kind"] == "accepted" and v["states"][row["identity"]]["receipt"]]
    return accepted[-1] if accepted else None


def local_start(v, loop):
    """The commit a local loop's next task starts from, and why it waits instead (loop.md step 3): its latest accepted
    source; else the start its first allocation fixed, kept in that receipt; else the HEAD of the branch it was added on,
    which must descend from the manifest base_sha."""
    tip, added = frontier(v, loop), v["records"].get(loop)
    fixed = next((state["receipt"]["baseline"] for identity, state in v["states"].items() if identity.split(".")[0] == loop
                  and state["receipt"] and not {"remote_url", "allocated_from"} & set(state["receipt"])), None)
    remedy = "restore them to their bytes at that commit, or plan the remaining work as a new loop"
    if tip or fixed:
        start = tip["receipt"]["source_sha"] if tip else fixed
    elif added is None:
        return None, f"{loop} has no add record in this repository, so no branch to start it from; drain it where it was added"
    else:
        branch, base = added["branch"], manifest_of(v, loop)["base_sha"]
        start, remedy = ref_value(v["anchor"], "refs/heads/" + branch), f"commit them on {branch}, or restore them to their bytes at that commit"
        if not start or not ancestor(v["anchor"], base, start):
            where = f"is at {start}, which does not descend from the manifest base_sha {base}" if start else "no longer exists"
            return None, f"{branch}, the branch {loop} was added on, {where}; bring {base} into {branch}, or plan the work as a new loop"
    if drift := instruction_drift(v["anchor"], start):
        return start, f"the installed instructions ({drift}) in this checkout differ from those in its start commit {start}, so it would run without them; {remedy}"
    return start, None


def terminal_line(v, identity):
    state = v["states"][identity]
    row = next(row for row in v["rows"] if row["identity"] == identity)
    if state["kind"] == "blocked":
        root = state["root"]["receipt"]
        return f"- [F] {row['text']} — blocked-prerequisite:{state['blocker']} (receipt {root['id'] if root else 'none'})"
    if state["kind"] in {"accepted", "failed"} and state["receipt"] and state["receipt"].get("queue"):
        terminal = parse_queue(show(v["anchor"], state["receipt"]["publish_sha"], state["receipt"]["queue"]["file"]) or b"")
        return next(r["line"] for r in terminal if r["identity"] == identity)
    return None


def build_tree(worktree, parent, files):
    """The tree of `parent` (or of nothing) with `files`, built in a temporary index so no checkout changes."""
    with tempfile.TemporaryDirectory(prefix="devlyn-loop-index-") as temp:
        env = {**os.environ, "GIT_INDEX_FILE": str(Path(temp) / "index")}
        git(worktree, "read-tree", parent or "--empty", env=env)
        for rel, data in files.items():
            blob = git(worktree, "hash-object", "-w", "--stdin", data=data)
            git(worktree, "update-index", "--add", "--cacheinfo", f"100644,{blob},{rel}", env=env)
        return git(worktree, "write-tree", env=env)


def commit_files(worktree, branch, parent, files, message, *, checkout):
    """Commit `files` atop `parent` on `branch`; when `parent` already carries them there is no commit to make."""
    tree = build_tree(worktree, parent, files)
    if tree == git(worktree, "rev-parse", parent + "^{tree}"):
        return parent
    commit = git(worktree, "commit-tree", tree, "-p", parent, "-m", message)
    git(worktree, "update-ref", "refs/heads/" + branch, commit, parent)
    if checkout:
        sync(worktree, branch, parent, commit)
    return commit


def sync(worktree, branch, parent, commit):
    """Move a checkout that was clean at `parent` to `commit`; refuses rather than overwrite local edits."""
    if git_run(worktree, "symbolic-ref", "-q", "HEAD", ok=(0, 1)).stdout.decode("utf-8").strip() == "refs/heads/" + branch:
        git(worktree, "read-tree", "-m", "-u", parent, commit)


def input_files(v, row, receipt, local):
    """The task's scoped inputs (loop.md step 4). A base lacking the loop's package gets the package directory from the
    capture, its queue file's settled rows keeping their marks; otherwise a local task gets the base's queue file with the
    loop's settled rows, and an auto/pr task nothing, so its PR changes only its own row."""
    loop, rel = row["loop"], loop_queue(row["loop"])
    data, files = show(Path(receipt["worktree"]), receipt["baseline"], rel), {}
    if data is None:
        package = [f"docs/specs/{loop}/meta.md", *(f"docs/specs/{loop}/{entry['id']}/{name}" for entry in v["packages"][loop]["manifest"]["tasks"]
                                                   for name in ("spec.md", "spec.expected.json")), rel]
        files = {path: package_bytes(v["anchor"], capture(v, loop), path) for path in package}
        require(None not in files.values(), f"{row['identity']}: the package of loop {loop} is incomplete in this checkout")
        data = files[rel]
    if local or files:
        data = with_rows(data, {other["identity"]: line for other in v["rows"] if other.get("loop") == loop
                                and other["identity"] != row["identity"] and (line := terminal_line(v, other["identity"]))})
    files[rel] = data
    return files


def require_merged(v, row, base):
    """auto/pr: every prerequisite's merge commit must be in the base, before allocation and before every execution."""
    for dep in v["packages"][row["loop"]]["tasks"][row["task"]]["depends_on"]:
        receipt = v["states"][f"{row['loop']}.{dep}"]["receipt"] or {}
        merge = ((receipt.get("merge") or {}).get("mergeCommit") or {}).get("oid")
        require(merge and ancestor(v["anchor"], merge, base), f"{row['identity']}: base {base} lacks the delivered prerequisite merge {merge}")


def instruction_drift(anchor, rev):
    """The installed instruction files whose content at `rev` differs from the anchor checkout's (both absent is equal): a
    task starting at `rev` would run without them. Git compares them as `git status` does: a link by its target, line endings
    under the checkout's conversion rules, and an untracked or ignored file as one still to commit."""
    names = ("CLAUDE.md", "AGENTS.md")
    differ = git(anchor, "diff", "--name-only", "--no-renames", rev, "--", *names).split("\n")
    differ += git(anchor, "ls-files", "--others", "--", *names).split("\n")
    return ", ".join(name for name in names if name in differ)


def evidence_ignored(anchor, common, start):
    """Whether a checkout of `start` ignores .devlyn/: its .gitignore files on that path, info/exclude, core.excludesFile."""
    with tempfile.TemporaryDirectory(prefix="devlyn-loop-ignore-") as temp:
        for rel in (".gitignore", ".devlyn/.gitignore", ".devlyn/loop/.gitignore"):
            if (rules := show(anchor, start, rel)) is not None:
                (Path(temp) / rel).parent.mkdir(parents=True, exist_ok=True)
                (Path(temp) / rel).write_bytes(rules)
        return git_run(temp, "--git-dir", str(common), "--work-tree", temp, "check-ignore", "-q", "--no-index",
                       ".devlyn/loop/evidence", ok=(0, 1)).returncode == 0


def allocate(v, row, opts):
    """Allocate the task's owned worktree, or return why it waits: its refreshed remote base lacks the checkout's
    instructions (waiting() checks a local start before selection)."""
    identity, loop, task = row["identity"], row["loop"], row["task"]
    package = v["packages"][loop]
    manifest = package["manifest"]
    anchor, common = v["anchor"], v["common"]
    deps = [v["states"][f"{loop}.{dep}"] for dep in package["tasks"][task]["depends_on"]]
    values = {"repo": str(anchor), "task": identity, "branch": branch_of(identity), "repository": None,
              "base": manifest["base_ref"], "remote": "origin", "worktree": str(opts.worktree_root / loop / task),
              "local_base": None, "from_receipt": None, "start": None}
    if is_local(v, loop):
        tip, start = frontier(v, loop), local_start(v, loop)[0]
        for dep in deps:
            require(ancestor(anchor, dep["receipt"]["source_sha"], start),
                    f"{identity}: prerequisite source {dep['receipt']['source_sha']} is not in the accepted frontier {start}; plan an integration task")
        values["from_receipt" if tip else "local_base"] = str(tip["path"]) if tip else start
    else:
        helper = shared("task-complete")
        try:
            values["repository"] = helper["repository_from_url"](git(anchor, "config", "--get", "remote.origin.url"))
        except (LoopError, helper["CompletionError"]) as exc:
            raise LoopError(f"{identity}: {manifest['delivery']} delivery needs an origin remote naming one GitHub repository: {exc}") from exc
        try:
            start = helper["remote_base"]({"common_gitdir": str(common), "remote": "origin", "base": manifest["base_ref"]})
        except helper["CompletionError"] as exc:
            raise LoopError(f"{identity}: cannot refresh base {manifest['base_ref']}: {exc}") from exc
        values["start"] = start
        require_merged(v, row, start)
    require(evidence_ignored(anchor, common, start),
            f"{identity}: .devlyn/ is not ignored in its start commit {start}, so loop evidence would dirty task source; commit a "
            f"`.devlyn/` entry to .gitignore in the base the task starts from, or add `.devlyn/` to {common / 'info' / 'exclude'}")
    if values["start"] and (drift := instruction_drift(anchor, start)):
        return (f"the installed instructions ({drift}) in this checkout differ from those in its start commit {start}, so it would run "
                f"without them; commit them and push them to origin/{manifest['base_ref']}")
    result = task_complete("allocate", **values)
    progress(identity, f"allocated {result['worktree']}")
    return None


def ensure_packet(v, row, path, receipt):
    """Commit this task's scoped inputs on the owned branch, then write the executor's task packet."""
    packet_path = path.parent / "packet.json"
    if packet_path.exists():
        return packet_path, read_json(packet_path)
    identity, loop, task = row["identity"], row["loop"], row["task"]
    worktree, baseline, branch = Path(receipt["worktree"]), receipt["baseline"], receipt["branch"]
    local = bool(receipt.get("local_only"))
    files = input_files(v, row, receipt, local)
    head = git(worktree, "rev-parse", "refs/heads/" + branch)
    if head == baseline:
        inputs = commit_files(worktree, branch, baseline, files, f"devlyn loop: inputs for {identity}", checkout=True)
    else:
        require(git(worktree, "rev-parse", head + "^") == baseline and git(worktree, "rev-parse", head + "^{tree}") == build_tree(worktree, baseline, files),
                f"{identity}: owned branch has commits that are not its scoped inputs; inspect {worktree}")
        inputs = head
        sync(worktree, branch, baseline, inputs)
    progress(identity, f"inputs {inputs}")
    package = v["packages"][loop]
    spec = package["tasks"][task]

    def identity_of(rel):
        return {"path": str(worktree / rel), "sha256": hashlib.sha256(show(worktree, inputs, rel)).hexdigest()}

    packet = {
        "schema_version": 1, "task": identity, "title": spec["title"], "kind": spec["kind"],
        "worktree": str(worktree), "branch": branch, "receipt": str(path), "scratch": str(path.parent / "scratch"),
        "allocation_base": baseline, "inputs_sha": inputs,
        "contract": identity_of(f"docs/specs/{loop}/{task}/spec.md"),
        "expected": identity_of(f"docs/specs/{loop}/{task}/spec.expected.json"),
        "meta": identity_of(f"docs/specs/{loop}/meta.md"),
        "requirements": spec["requirements"], "review_requirements": spec["review"],
        "shared_constraints": sections(package["meta_text"], "meta.md")["Constraints and exclusions"],
        "dependencies": [{"task": f"{loop}.{dep}", "receipt": str(state["path"]), "source_sha": state["receipt"]["source_sha"]}
                         for dep in spec["depends_on"] if (state := v["states"][f"{loop}.{dep}"])["receipt"]],
        "methodology": [identity_of(name) for name in ("CLAUDE.md", "AGENTS.md") if show(worktree, inputs, name) is not None],
        "delivery": "local-only" if local else package["manifest"]["delivery"],
        "evidence_dir": str(worktree / ".devlyn" / "loop"),
        "submission": str(path.parent / "submission.json"),
        "runner": [sys.executable, str(Path(__file__).with_name("acceptance.py")), "run", "--packet", str(packet_path)],
        "obligations": OBLIGATIONS,
    }
    write_json(packet_path, packet)
    return packet_path, packet


def record(log, event):
    """Append one execution event durably, before the drain acts on it."""
    with log.open("a", encoding="utf-8") as stream:
        stream.write(f"{datetime.datetime.now(datetime.timezone.utc).isoformat()} {event}\n")
        stream.flush()
        os.fsync(stream.fileno())


def ensure_submission(identity, packet_path, packet, executor):
    """Run the executor once unless its submission exists; returns a drain-recorded failure reason, else None.

    An attempt's start is recorded before the spawn and its exit after the wait, so a start without an exit may have
    left a live executor: drain waits until no process uses the worktree, then adopts its submission or runs the
    executor again. Where writers cannot be observed the task fails as interrupted-unobservable."""
    submission = Path(packet["submission"])
    worktree = Path(packet["worktree"])
    log = submission.with_name("executions.log")
    events = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    if events and events[-1].partition(" ")[2] == "start":
        helper = shared("task-complete")
        reported = False
        while True:
            try:
                helper["stopped_writers"](worktree)
                break
            except helper["WritersUnobservable"] as exc:
                return f"interrupted-unobservable: an interrupted executor may still be writing ({exc})"
            except helper["WriterActive"] as exc:
                if not reported:
                    progress(identity, f"waiting for an interrupted execution to stop ({exc})")
                reported = True
                time.sleep(2)
            except helper["CompletionError"] as exc:
                raise LoopError(f"{identity}: cannot establish that an interrupted execution stopped ({exc})") from exc
    if submission.exists():
        return None
    argv = [part.replace("{packet}", str(packet_path)) for part in executor]
    if any("{worktree_git_dir}" in part for part in argv):  # Optional: a Codex executor lists it as a writable root.
        git_dir = git(worktree, "rev-parse", "--path-format=absolute", "--git-dir")
        argv = [part.replace("{worktree_git_dir}", git_dir) for part in argv]
    output = Path(packet["evidence_dir"])
    output.mkdir(parents=True, exist_ok=True)
    record(log, "start")
    try:
        # Files, never a pipe: a wrapper such as codex-monitored.sh refuses a piped stdout; stdin is empty, never the driver's.
        with (output / "executor.stdout").open("ab") as stdout, (output / "executor.stderr").open("ab") as stderr:
            child = subprocess.Popen(shared("platform-support")["native_argv"](argv, cwd=worktree), cwd=worktree, stdin=subprocess.DEVNULL,
                                     stdout=stdout, stderr=stderr)
    except OSError as exc:
        record(log, f"not started: {one_line(str(exc))}")
        raise LoopError(f"executor could not start: {exc}") from exc
    progress(identity, f"executing; output in {output}")
    code = child.wait()
    if not submission.exists():
        write_json(submission, {"schema_version": 1, "task": identity, "source_sha": packet["inputs_sha"],
                                "summary": "recorded by the drain, not the executor",
                                "blockers": [{"kind": "blocked-infrastructure", "detail": f"executor exited {code} without a submission"}]})
    record(log, f"exit {code} (pid {child.pid})")
    return None


def terminal_queue(cwd, receipt, identity):
    """The loop queue file of this bound result's only legal terminal transition: its row becomes [x] or [F] — <reason>."""
    failed = receipt.get("product") == "FAILED"
    suffix = f" — {one_line(receipt['acceptance']['reasons'][0])} (receipt {receipt['id']})" if failed else ""
    rel = loop_queue(identity.split(".")[0])
    return transition(show(cwd, receipt["acceptance"]["inputs_sha"], rel) or b"", identity, "F" if failed else "x", suffix)


def is_terminal(cwd, receipt, identity, commit):
    """Whether `commit` is that transition: its sole parent is the bound source and its only change is the row."""
    source, rel = receipt["source_sha"], loop_queue(identity.split(".")[0])
    return (git(cwd, "rev-list", "--parents", "-n", "1", commit).split() == [commit, source]
            and git(cwd, "diff", "--name-only", source, commit) == rel and show(cwd, commit, rel) == terminal_queue(cwd, receipt, identity))


def settle(v, row, receipt_file):
    """Create (or adopt) the queue-only terminal commit atop the bound source, then attach it."""
    identity = row["identity"]
    receipt = read_json(receipt_file)
    worktree, source, branch = Path(receipt["worktree"]), receipt["source_sha"], receipt["branch"]
    failed = receipt.get("product") == "FAILED"
    with lock(v["common"], "queue.lock", blocking=True):
        head = git(worktree, "rev-parse", "refs/heads/" + branch)
        if head == source:
            commit = commit_files(worktree, branch, source, {loop_queue(row["loop"]): terminal_queue(worktree, receipt, identity)},
                                  f"devlyn loop: {identity} {'failed' if failed else 'accepted'}", checkout=not failed)
        else:
            require(is_terminal(worktree, receipt, identity, head),
                    f"{identity}: owned branch moved past the bound source without its terminal transition; inspect {worktree}")
            commit = head
            if not failed:
                sync(worktree, branch, source, commit)
        progress(identity, f"terminal {commit}")
        task_complete("attach", receipt=str(receipt_file), commit=commit, file=loop_queue(row["loop"]))
    progress(identity, "attached")


def advance(v, row, opts):
    """Run or resume one task from its durable state; never replays a bound result. Returns why it waits instead."""
    identity = row["identity"]
    path = receipt_path(v["common"], identity)
    if not path.exists() and (refused := allocate(v, row, opts)):
        return refused
    receipt = read_json(path)
    if not receipt.get("acceptance"):
        failure = v["states"][identity].get("inputs_changed")
        if not failure and not receipt.get("local_only"):
            require_merged(v, row, receipt["baseline"])
        packet_path, packet = ensure_packet(v, row, path, receipt)
        failure = failure or ensure_submission(identity, packet_path, packet, opts.executor)
        try:
            result = acceptance()["accept"](packet_path, packet["submission"], failure)
        except acceptance()["AcceptanceError"] as exc:
            raise LoopError(f"{identity}: acceptance could not run: {exc}") from exc
        progress(identity, result["verdict"].lower() + "".join(f"; {reason}" for reason in result["reasons"][:3]))
        task_complete("accept", receipt=str(path), acceptance=str(Path(packet["worktree"]) / ".devlyn/loop/acceptance.json"))
        progress(identity, "bound")
    if not read_json(path).get("queue"):
        settle(v, row, path)
    receipt = read_json(path)
    if receipt.get("delivery") not in SETTLED:
        packet = read_json(path.parent / "packet.json")
        local = opts.local_only or bool(receipt.get("local_only")) or packet["delivery"] == "local-only"
        if local and receipt.get("pushed"):
            return (f"{identity} already has a pushed PR {receipt.get('pr_url') or receipt['branch']}, which --local-only never rewrites; "
                    "drain without --local-only to deliver it")
        result = task_complete("complete", receipt=str(path), acceptance=None, mode=None if local else packet["delivery"],
                               local_only=local, writers_stopped=True)
        progress(identity, f"delivery {result['status']}")
    return None


def summary(v, row):
    state = v["states"][row["identity"]]
    receipt = state["receipt"] or {}
    item = {"identity": row["identity"], "result": state["kind"], "receipt": str(state["path"]) if state["path"] else None}
    if state["kind"] == "failed":
        item["reason"] = row["rest"].lstrip(" —") if row["mark"] == "F" else (receipt.get("acceptance") or {}).get("reasons", ["failed"])[0]
    if state["kind"] == "blocked":
        item["reason"] = f"blocked-prerequisite:{state['blocker']}"
    if reason := state.get("waiting") or state.get("inputs_changed") or state.get("invalid"):
        item["reason"] = reason
    if receipt:
        acceptance_record = receipt.get("acceptance") or {}
        item.update(allocation_base=receipt.get("baseline"), **{"source" if state["kind"] == "accepted" else "candidate": receipt.get("source_sha")},
                    terminal=(receipt.get("queue") or {}).get("commit"), delivery=receipt.get("delivery"), pr=receipt.get("pr_url"),
                    resume=None if not receipt.get("acceptance") or receipt.get("delivery") in SETTLED
                    else shlex.join([sys.executable, str(SKILLS / "_shared/task-complete.py"), "complete", "--receipt", str(state["path"])])
                    if receipt.get("queue") else "drain again: the terminal commit is not attached yet",
                    assumptions=acceptance_record.get("assumptions", []),
                    questions=[r.removeprefix("needs-review: ") for r in acceptance_record.get("reasons", []) if r.startswith("needs-review: ")],
                    worktree=receipt["worktree"] if receipt.get("worktree") and Path(receipt["worktree"]).exists() else None,
                    cleanup=f"{c['status']} — {c['reason']}; resume: {c['resume']}" if (c := receipt.get("workspace_cleanup")) else None,
                    branch=receipt.get("branch"), recovery_ref=receipt.get("recovery_ref"),
                    custody=str(Path(state["path"]).parent / "custody") if receipt.get("files") else None,
                    scratch=(receipt.get("scratch_cleanup") or {}).get("status", "NOT_CLEANED"))
    return item


def manifest_of(v, loop):
    """The loop's manifest, read once per view."""
    if loop not in v["manifests"]:
        v["manifests"][loop] = v["packages"][loop]["manifest"] if loop in v["packages"] else load_manifest(v["anchor"], loop, capture(v, loop))[1]
    return v["manifests"][loop]


def loop_acceptance(v, loop, items):
    """Whole-loop acceptance over the manifest's complete task set: every task, the integration task last, needs
    receipt-backed acceptance. A manifest task missing from this queue joins `items` as not yet run."""
    try:
        manifest = manifest_of(v, loop)
    except LoopError as exc:
        return f"INCOMPLETE — manifest unreadable: {exc}"
    found, gaps = {item["identity"]: item for item in items}, []
    for identity in (f"{loop}.{entry['id']}" for entry in manifest["tasks"]):
        if identity not in found:
            items.append(found.setdefault(identity, {"identity": identity, "result": "not yet run"}))
        if found[identity]["result"] != "accepted":
            gaps.append(f"{identity} {found[identity]['result']}")
        elif not found[identity].get("receipt"):
            gaps.append(f"{identity} accepted without a receipt")
    return "INCOMPLETE — " + ", ".join(gaps) if gaps else "ACCEPTED"


def bring_in(v, loop):
    """The command that brings the loop's accepted work into the branch it was added on (loop.md step 11)."""
    tip = frontier(v, loop)
    if tip is None:
        return None
    receipt = tip["receipt"]
    if receipt.get("local_only"):
        # It fast-forwards when it can and merges otherwise, so the commands of several local loops apply in any order.
        return f"{v['records'][loop]['branch']}: git merge --ff {receipt['branch']}" if loop in v["records"] else None
    if not delivered(receipt):
        return None
    base, tracking = receipt["base"], f"{receipt['remote']}/{receipt['base']}"
    # The anchor holds no loop commit, so merge, squash and rebase delivery all fast-forward it unless it has commits of its own.
    if git_run(v["anchor"], "merge-base", "--is-ancestor", "refs/heads/" + base, "refs/remotes/" + tracking, ok=(0, 1, 128)).returncode == 0:
        return f"{base}: git pull --ff-only {receipt['remote']} {base}"
    return f"{base}: git merge {tracking} ({base} has commits {tracking} lacks, so this merges instead of fast-forwarding)"


def write_reports(v, status, reason):
    paths = []
    for loop in dict.fromkeys(row["loop"] for row in v["rows"] if row["identity"]):
        items = [summary(v, row) for row in v["rows"] if row.get("loop") == loop]
        lines = [f"# Drain report — {loop}", "", f"- Generated: {datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')}",
                 f"- Queue: {f'{CAPTURES}{loop}:{loop_queue(loop)}' if loop in v['records'] else v['anchor'] / loop_queue(loop)}",
                 f"- Drain: {status}" + (f" — {reason}" if reason else ""), f"- Whole-loop acceptance: {loop_acceptance(v, loop, items)}",
                 *([f"- Bring into {line}"] if (line := bring_in(v, loop)) else []), ""]
        labels = (("result", "Product"), ("reason", "Reason"), ("receipt", "Receipt"), ("custody", "Evidence custody"),
                  ("recovery_ref", "Recovery ref"), ("allocation_base", "Allocation base"), ("source", "Accepted source"), ("candidate", "Unaccepted source"),
                  ("terminal", "Terminal commit"), ("delivery", "Delivery"), ("pr", "PR"), ("resume", "Resume"),
                  ("assumptions", "Assumptions"), ("questions", "Unresolved questions"), ("worktree", "Retained worktree"),
                  ("cleanup", "Workspace cleanup"),
                  ("branch", "Branch"), ("scratch", "Scratch cleanup"))
        for item in items:
            lines += [f"## {item['identity']}", ""]
            lines += [f"- {label}: {'; '.join(value) if isinstance(value, list) else value}"
                      for key, label in labels if (value := item.get(key)) not in (None, [], "")]
            lines.append("")
        path = v["common"] / "devlyn-loops" / loop / "drain-report.md"
        acceptance()["atomic_write"](path, "\n".join(lines).encode("utf-8"))
        paths.append(str(path))
    return paths


def counts(v):
    kinds = [state["kind"] for state in v["states"].values()]
    return {kind: kinds.count(kind) for kind in ("pending", "active", "accepted", "failed", "blocked")} | {
        "legacy_pending": sum(1 for row in v["rows"] if not row["identity"] and row["mark"] == " ")}


def drain(args):
    anchor, common = repository(args.repo)
    require(any("{packet}" in part for part in args.executor), "executor argv must contain {packet}, replaced by the task packet path")
    args.worktree_root = Path(args.worktree_root).resolve() if args.worktree_root else anchor.parent / f"{anchor.name}.devlyn"
    with lock(common, "drain.lock", blocking=False):
        attempted, last, status, reason, refused = set(), None, "DRAINED", None, {}
        try:
            while True:
                last = view(anchor, common, args.local_only)
                row = next_task(last, attempted)
                if row is None:
                    break
                attempted.add(row["identity"])
                if wait := advance(last, row, args):
                    refused[row["identity"]] = wait
            if any(state["kind"] in {"pending", "active"} for state in last["states"].values()) or counts(last)["legacy_pending"] or refused:
                status = "WAITING"
        except (LoopError, OSError) as exc:
            status, reason = "BLOCKED", str(exc)
            with contextlib.suppress(LoopError, OSError):
                last = view(anchor, common, args.local_only)
        if last is None:
            return {"status": status, "reason": reason}
        annotate(last, refused)
        return {"status": status, "reason": reason, "reports": write_reports(last, status, reason), "counts": counts(last),
                "tasks": [summary(last, row) for row in last["rows"] if row["identity"]], "cleanup": last["cleanup"]}


def status(args):
    anchor, common = repository(args.repo)
    v = view(anchor, common, args.local_only)
    row = next_task(v, set())
    annotate(v, {})
    tasks = [summary(v, r) for r in v["rows"] if r["identity"]]
    return {"status": "OK", "counts": counts(v), "next": row["identity"] if row else None,
            "blockers": [f"{t['identity']}: {t['reason']}" for t in tasks if t.get("reason") and t["result"] in {"pending", "active", "blocked"}]
            + [f"legacy row {r['index'] + 1} needs planning: {r['text']}" for r in v["rows"] if not r["identity"] and r["mark"] == " "]
            + [f"unreadable receipt {item}" for item in v["unreadable"]],
            "delivery": [t for t in tasks if t.get("resume")], "cleanup": v["cleanup"]}


def legacy_target(anchor, number):
    """The pending legacy row on line `number` of the legacy queue, as add records it: its exact text and its occurrence
    among equal rows, line endings aside; None for any other line."""
    path = anchor / QUEUE
    rows = parse_queue(path.read_bytes() if path.exists() else b"")
    row = next((row for row in rows if row["index"] == number - 1 and row["identity"] is None and row["mark"] == " "), None)
    return row and {"line": row["line"], "occurrence": sum(other["line"] == row["line"] for other in rows if other["index"] <= row["index"])}


def added_result(anchor, added, notes):
    loop, ref = added["loop_id"], added["capture"]
    rows, _ = parse_loop(show(anchor, added["commit"], loop_queue(loop)), loop, f"{ref}:{loop_queue(loop)}")
    return {"status": "ADDED", "tasks": [row["identity"] for row in rows], "capture": ref, "commit": added["commit"], "cleanup": notes,
            "message": f"The package is now held immutably at {ref}; inspect it with `git show {ref}:docs/specs/{loop}/meta.md`. "
                       "A revision needs a new loop id."}


def add(args):
    """Capture the package and its queue rows under refs/devlyn/captures/<loop>, record the add, then remove the untracked
    originals equal to the capture (package-format.md, Commands); the branch, index and tracked files stay as they are."""
    meta = Path(args.package).resolve()
    anchor, common = repository(next(path for path in meta.parents if path.is_dir()))
    loop = meta.parent.name
    ref, package_dir = CAPTURES + loop, f"docs/specs/{loop}"
    require(meta.name == "meta.md" and meta.parent.parent == anchor / "docs/specs" and re.fullmatch(ID, loop),
            f"package must be <repo>/docs/specs/<loop-id>/meta.md: {meta}")
    with lock(common, "queue.lock", blocking=True):
        recorded = records(common)
        notes = clean(common, recorded)
        target = legacy_target(anchor, args.materialize) if args.materialize else None
        if loop in recorded:
            # This package's add, also one interrupted after its record or whose originals are gone, is reported as it is.
            added = recorded[loop]
            differ = [rel for rel, state in package_state(anchor, added["commit"], loop).items() if state == "different"]
            require(not differ and target == added.get("materialize"),
                    f"loop id {loop} was already added with another package ({', '.join(differ) or '--materialize differs'}); it is held at "
                    f"{ref}, so plan revised work as a new loop")
            return added_result(anchor, added, notes)
        interrupted = (f"{ref} holds the capture of an interrupted add of {loop} that differs from the checkout; inspect it with `git show "
                       f"{ref}`, then restore that package or delete the ref with `git update-ref -d {ref}`, and add again")
        if captured := ref_value(anchor, ref):
            require(all(state == "equal" for state in package_state(anchor, captured, loop).values()), interrupted)
        package = package_of(anchor, meta)
        manifest = package["manifest"]
        local = manifest["delivery"] == "local-only"
        require(show(anchor, "HEAD", loop_queue(loop)) is None, f"loop id {loop} is already used by {loop_queue(loop)}; plan revised work as a new loop")
        if tracked := git(anchor, "diff", "--name-only", "--no-renames", "--diff-filter=MDT", "HEAD", "--", package_dir):
            raise LoopError(f"{package_dir} is committed with different content ({', '.join(tracked.splitlines())}); add never captures a "
                            "revision of committed package files, so plan it as a new loop")
        branch = git_run(anchor, "symbolic-ref", "-q", "--short", "HEAD", ok=(0, 1)).stdout.decode("utf-8").strip()
        require(branch, f"add records the branch the loop is added on, but HEAD is detached in {anchor}")
        if drift := instruction_drift(anchor, head := git(anchor, "rev-parse", "HEAD")):
            # Tasks start from committed state: a local loop from this branch, auto/pr from the pushed base.
            raise LoopError(f"the installed instructions ({drift}) in this checkout differ from those in HEAD {head}, so the loop's tasks would "
                            f"run without them; commit {'them' if local else 'and push them'}, then add the loop")
        if staged := git(anchor, "diff", "--cached", "--name-only", "--no-renames", "HEAD", "--", package_dir):
            raise LoopError(f"the index holds package changes HEAD lacks ({', '.join(staged.splitlines())}); add leaves the index as it is, "
                            f"so unstage them with `git restore --staged -- {package_dir}` and add again")
        if args.materialize:
            pending = {row["index"] for row in queue_view(anchor, recorded) if row["identity"] is None and row["mark"] == " "}
            require(target and args.materialize - 1 in pending, f"{QUEUE} line {args.materialize} is not a pending legacy row")
            intent = " ".join(sections(package["meta_text"], "meta.md")["Intent"].split())
            require(" ".join(target["line"][6:].split()) in intent, "meta.md '## Intent' must reproduce the legacy row's intent verbatim")
        paths = [f"{package_dir}/meta.md", *(f"{package_dir}/{task}/{name}" for task in package["tasks"] for name in ("spec.md", "spec.expected.json"))]
        files = {rel: package_bytes(anchor, None, rel) for rel in paths} | {loop_queue(loop): loop_rows(loop, package, target)}
        tree = build_tree(anchor, None, files)
        if captured:
            require(tree == git(anchor, "rev-parse", captured + "^{tree}"), interrupted)
        else:
            # The ref keeps the commit, its tree and blobs from garbage collection once the originals are gone.
            captured = git(anchor, "commit-tree", tree, "-m", f"devlyn loop: capture {loop}")
            git(anchor, "update-ref", ref, captured, "0" * len(captured))
        added = {"schema_version": 1, "loop_id": loop, "delivery": manifest["delivery"], "capture": ref, "commit": captured, "tree": tree,
                 "origin": str(anchor), "branch": branch, "sequence": max((other["sequence"] for other in recorded.values()), default=0) + 1,
                 **({"materialize": target} if target else {})}
        write_json(added_path(common, loop), added)
        notes += clean(common, {loop: added})
    return added_result(anchor, added, notes)


def check(args):
    anchor, _ = repository(Path(args.package).resolve().parent)
    package = package_of(anchor, args.package)
    return {"status": "VALID", "loop_id": package["loop_id"], "tasks": [f"{package['loop_id']}.{task}" for task in package["tasks"]]}


# Self-test fixtures: a valid two-task package, then one mutation per rejected shape.
META = """# Loop {loop}

## Intent

{intent}

## Constraints and exclusions

Standard library only.

## Tasks

T1 builds the interface; T2 consumes it.

```json
{manifest}
```

## Overall acceptance

R1 of t2 checks the assembled product.

## Execution policy

Installed methodology; autonomous question policy; delivery as declared.

## Decisions and assumptions

None beyond the task contracts.
"""
SPEC = """---
id: {task}
loop_id: {loop}
title: {title}
kind: feature
review_requirements: [{review}]
---
# {title}

## Context and goal

Fixture.

## Requirements

- R1: {requirement}
- R2: The code stays small.

## Scope and constraints

Only the declared files.

## Out of scope

Nothing else.

## Prerequisite inputs

{inputs}

<!-- devlyn:verification -->
## Verification

The declared commands.

## Deliverable and cleanup

Keep the product; no residue.
"""


def write_package(anchor, loop, tasks, *, delivery="local-only", base=None, intent="Ship the fixture.", review="R2"):
    """tasks: [(task_id, depends_on, title, verification_commands)] -> meta path."""
    base = base or git(anchor, "rev-parse", "HEAD")
    manifest = {"schema_version": 1, "loop_id": loop, "base_ref": "main", "base_sha": base, "delivery": delivery,
                "tasks": [{"id": task, "spec": f"{task}/spec.md", "depends_on": deps} for task, deps, _, _ in tasks],
                "integration_task_id": tasks[-1][0]}
    root = anchor / "docs/specs" / loop
    for task, deps, title, commands in tasks:
        (root / task).mkdir(parents=True, exist_ok=True)
        (root / task / "spec.md").write_text(SPEC.format(task=task, loop=loop, title=title, review=review, requirement=f"{title} works.",
                                                         inputs=", ".join(deps) or "None."), encoding="utf-8")
        (root / task / "spec.expected.json").write_text(json.dumps({"verification_commands": commands}, indent=2), encoding="utf-8")
    (root / "meta.md").write_text(META.format(loop=loop, intent=intent, manifest=json.dumps(manifest, indent=2)), encoding="utf-8")
    return root / "meta.md"


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="devlyn-queue ✓ ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.env = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": str(self.root / "gitconfig"),
                    "GIT_AUTHOR_NAME": "Fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
                    "GIT_COMMITTER_NAME": "Fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid"}
        self.anchor = self.root / "repo"
        subprocess.run(["git", "init", "-q", "--initial-branch=main", str(self.anchor)], check=True, env=self.env)
        (self.anchor / ".gitignore").write_text(".devlyn/\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.anchor), "add", "."], check=True, env=self.env)
        subprocess.run(["git", "-C", str(self.anchor), "commit", "-qm", "base"], check=True, env=self.env)
        command = {"argv": [sys.executable, "-c", "pass"], "contract_refs": ["R1"]}
        self.tasks = [("t1", [], "Interface 인터페이스", [command]), ("t2", ["t1"], "Consumer [app]", [command])]
        self.meta = write_package(self.anchor, "inv", self.tasks)

    def cli(self, *args, cwd=None, code=0):
        result = subprocess.run([sys.executable, str(Path(__file__).resolve()), *map(str, args)], cwd=cwd or self.anchor,
                                env=self.env, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def rejected(self, message, mutate):
        root = self.anchor / "docs/specs/inv"
        saved = {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}
        mutate(root)
        try:
            with self.assertRaises(LoopError) as caught:
                package_of(self.anchor, self.meta)
            self.assertIn(message, str(caught.exception))
        finally:
            for path in root.rglob("*"):
                if path.is_file() and path not in saved:
                    path.unlink()
            for path, data in saved.items():
                path.write_bytes(data)

    def edit(self, rel, old, new):
        def mutate(root):
            path = root / rel
            text = path.read_text(encoding="utf-8")
            self.assertIn(old, text)
            path.write_text(text.replace(old, new, 1), encoding="utf-8")
        return mutate

    def test_package_validation(self):
        self.assertEqual(self.cli("check", self.meta)["tasks"], ["inv.t1", "inv.t2"])
        manifest = json.loads(JSON_FENCE_RE.search((self.anchor / "docs/specs/inv/meta.md").read_text(encoding="utf-8")).group(1))
        dumped = json.dumps(manifest, indent=2)

        def manifest_edit(change):
            data = json.loads(dumped)
            change(data)
            return self.edit("meta.md", dumped, json.dumps(data, indent=2))

        cases = [
            ("exactly one fenced json manifest", self.edit("meta.md", "## Overall acceptance", "```json\n{}\n```\n\n## Overall acceptance")),
            ("manifest is not strict JSON", self.edit("meta.md", '"schema_version": 1', '"schema_version": 1, "schema_version": 1')),
            ("keys must be exactly", manifest_edit(lambda m: m.pop("delivery"))),
            ("must be unique", manifest_edit(lambda m: m["tasks"][1].update(id="t1", spec="t1/spec.md"))),
            ("depends on unknown task(s): t9", manifest_edit(lambda m: m["tasks"][1].update(depends_on=["t9"]))),
            ("dependency cycle: t1 -> t2 -> t1", manifest_edit(lambda m: m["tasks"][0].update(depends_on=["t2"]))),
            ("spec link must be t2/spec.md", manifest_edit(lambda m: m["tasks"][1].update(spec="t1/spec.md"))),
            ("integration_task_id must name the last task", manifest_edit(lambda m: m.update(integration_task_id="t1"))),
            ("integration_task_id must name the last task", manifest_edit(lambda m: m["tasks"][1].update(depends_on=[]))),
            ("base_sha must name an exact commit", manifest_edit(lambda m: m.update(base_sha="0" * 40))),
            ("missing or empty section(s): '## Execution policy'", self.edit("meta.md", "## Execution policy", "## Policy")),
            ("status is queue state", self.edit("t1/spec.md", "kind: feature", "kind: feature\nstatus: planned")),
            ("kind must be feature, spike or prototype", self.edit("t1/spec.md", "kind: feature", "kind: [feature]")),
            ("must directly follow", self.edit("t1/spec.md", "<!-- devlyn:verification -->\n", "")),
            ("unique stable IDs", self.edit("t1/spec.md", "- R2: The code", "- R1: The code")),
            ("review_requirements name unknown requirement(s): R7", self.edit("t1/spec.md", "review_requirements: [R2]", "review_requirements: [R7]")),
            ("process_evidence (phase process obligations) is unsupported", self.edit("t1/spec.expected.json", '"verification_commands"', '"process_evidence": [], "verification_commands"')),
            ("contract_refs must name requirement IDs", self.edit("t1/spec.expected.json", '"R1"', '"R9"')),
            ("without command or review coverage: R2", self.edit("t1/spec.md", "review_requirements: [R2]", "review_requirements: []")),
            ("pure_design permits no verification_commands", self.edit("t1/spec.expected.json", '"verification_commands"', '"pure_design": true, "verification_commands"')),
        ]
        for message, mutate in cases:
            with self.subTest(message=message):
                self.rejected(message, mutate)

    def test_rows_and_transitions(self):
        queue = (b"# Intent Queue\n\n" + f"- [x] old intent\n{row_line('a.t1', 'Same')}\n- [ ] legacy intent\n{row_line('a.t2', 'Same')}\n".encode())
        rows = parse_queue(queue)
        self.assertEqual([row["identity"] for row in rows], [None, "a.t1", None, "a.t2"])
        after = transition(queue, "a.t2", "F", " — failed: check (receipt 1)")
        self.assertEqual([r["mark"] for r in parse_queue(after)], ["x", " ", " ", "F"])
        self.assertEqual(after.replace(b"- [F] a.t2 [Same](docs/specs/a/t2/spec.md) \xe2\x80\x94 failed: check (receipt 1)", b""),
                         queue.replace(row_line("a.t2", "Same").encode(), b""))
        for bad, message in ((lambda: transition(after, "a.t2", "x"), "no pending queue row"),
                             (lambda: parse_queue(queue + row_line("a.t1", "Dup").encode()), "duplicate queue identity: a.t1")):
            with self.assertRaisesRegex(LoopError, re.escape(message)):
                bad()
        self.assertEqual(parse_queue(row_line("a.t1", "[x] tricky \\ title").encode())[0]["identity"], "a.t1")
        # A row that does not fully match the loop-row grammar is a legacy row; trailing whitespace is tolerated.
        legacy = [b"- [ ] package.json [bump lodash](https://github.com/x/y/issues/3)", b"- [ ] a.t3 [T](docs/specs/a/t9/spec.md)",
                  b"- [x] a.t4 [T](docs/specs/a/t4/spec.md) trailing words", b"- [F] a.t5 [T](docs/specs/a/t5/spec.md)"]
        self.assertEqual([row["identity"] for row in parse_queue(b"\n".join(legacy))], [None] * 4)
        spaced = row_line("a.t1", "T").encode() + b" \t\n"
        self.assertEqual(parse_queue(spaced)[0]["identity"], "a.t1")
        self.assertEqual([(r["identity"], r["mark"]) for r in parse_queue(transition(spaced, "a.t1", "F", " — failed: x (receipt 1)"))], [("a.t1", "F")])

    def test_add_captures_the_package_and_materializes_legacy_rows(self):
        """Q, C. Prediction: add makes no commit and leaves the legacy queue, the index and every tracked file as they were;
        it points refs/devlyn/captures/inv at a commit holding exactly the package and docs/specs/inv/queue.md, its rows one
        blank line apart, records the add and removes the untracked originals; a retry reports that capture, also after the
        originals are gone; --materialize records the replaced legacy row's exact text and its occurrence among equal rows,
        line endings aside, in the loop's queue file, and status shows the loop's rows in that row's place; a different
        package under a used loop id is refused, also once committed. Before: add appended the rows to docs/specs/queue.md
        and committed them with the package."""
        package = {path.relative_to(self.anchor).as_posix(): path.read_bytes() for path in (self.anchor / "docs/specs/inv").rglob("*") if path.is_file()}
        legacy = b"# Intent Queue\n\n- [ ] Make   the  report weekly\r\n- [x] done\n- [ ] Make   the  report weekly\n"
        (self.anchor / QUEUE).write_bytes(legacy)
        git(self.anchor, "add", QUEUE, env=self.env)
        git(self.anchor, "commit", "-qm", "legacy queue", env=self.env)
        head, common, ref = git(self.anchor, "rev-parse", "HEAD"), Path(git(self.anchor, "rev-parse", "--path-format=absolute", "--git-common-dir")), "refs/devlyn/captures/inv"
        added = self.cli("add", self.meta)
        rows = f"{row_line('inv.t1', 'Interface 인터페이스')}\n\n{row_line('inv.t2', 'Consumer [app]')}\n".encode()
        self.assertEqual((added["tasks"], added["capture"], added["commit"]), (["inv.t1", "inv.t2"], ref, git(self.anchor, "rev-parse", ref)))
        self.assertIn(f"git show {ref}:docs/specs/inv/meta.md", added["message"])
        self.assertEqual({rel: show(self.anchor, ref, rel) for rel in git(self.anchor, "ls-tree", "-r", "--name-only", ref).splitlines()},
                         package | {"docs/specs/inv/queue.md": rows})
        self.assertEqual((git(self.anchor, "rev-parse", "HEAD"), git(self.anchor, "status", "--porcelain", "--untracked-files=all"),
                          (self.anchor / QUEUE).read_bytes(), (self.anchor / "docs/specs/inv").exists()), (head, "", legacy, False))
        self.assertEqual(read_json(added_path(common, "inv")), {
            "schema_version": 1, "loop_id": "inv", "delivery": "local-only", "capture": ref, "commit": added["commit"],
            "tree": git(self.anchor, "rev-parse", ref + "^{tree}"), "origin": str(self.anchor), "branch": "main", "sequence": 1})
        self.assertEqual(self.cli("add", self.meta)["commit"], added["commit"])  # a retry, the originals gone
        self.assertEqual(transition(rows, "inv.t1", "x"), rows.replace(b"- [ ] inv.t1", b"- [x] inv.t1"))
        second = write_package(self.anchor, "rep", [("t1", [], "Weekly", self.tasks[0][3])], intent="Wrong intent.")
        self.assertIn("reproduce the legacy row's intent", self.cli("add", second, "--materialize", 5, code=1)["reason"])
        write_package(self.anchor, "rep", [("t1", [], "Weekly", self.tasks[0][3])], intent="User asked: make the report weekly.")
        self.assertIn("not a pending legacy row", self.cli("add", second, "--materialize", 4, code=1)["reason"])
        self.assertIn("reproduce", self.cli("add", second, "--materialize", 5, code=1)["reason"])
        write_package(self.anchor, "rep", [("t1", [], "Weekly", self.tasks[0][3])], intent="User asked: Make the report weekly.")
        self.cli("add", second, "--materialize", 5)
        self.assertEqual(show(self.anchor, "refs/devlyn/captures/rep", "docs/specs/rep/queue.md"),
                         b"<!-- replaces docs/specs/queue.md row (occurrence 2): - [ ] Make   the  report weekly -->\n\n" + row_line("rep.t1", "Weekly").encode() + b"\n")
        status = self.cli("status")
        self.assertEqual((status["next"], (self.anchor / QUEUE).read_bytes()), ("rep.t1", legacy))
        self.assertEqual([blocker for blocker in status["blockers"] if blocker.startswith("legacy")], ["legacy row 3 needs planning: Make   the  report weekly"])
        write_package(self.anchor, "inv", [("t9", [], "Other", self.tasks[0][3])])
        for commit in (False, True):  # Revised work under a used loop id is refused, also once the revision is committed.
            if commit:
                git(self.anchor, "add", "docs/specs/inv", env=self.env)
                git(self.anchor, "commit", "-qm", "revise inv", env=self.env)
            self.assertIn("loop id inv was already added with another package (docs/specs/inv/meta.md", self.cli("add", self.meta, code=1)["reason"])

    def test_add_refuses_without_writing(self):
        """C. Each refusal leaves HEAD, the index, the files, refs and records as they were: a revised package under a used
        loop id, a detached HEAD, package files committed with other content, a loop id a committed queue file already uses,
        and package changes in the index, which add asks to unstage rather than losing them (Prediction for the last;
        before: add committed the index's draft beside the checkout's text)."""
        self.cli("add", self.meta)
        common = Path(git(self.anchor, "rev-parse", "--path-format=absolute", "--git-common-dir"))

        def g(*args):
            subprocess.run(["git", "-C", str(self.anchor), *args], check=True, env=self.env, capture_output=True)

        def edit_committed():
            g("add", "docs/specs/trk")
            g("commit", "-qm", "commit the package by hand")
            spec = self.anchor / "docs/specs/trk/t1/spec.md"
            spec.write_text(spec.read_text(encoding="utf-8").replace(" works.", " works for every caller."), encoding="utf-8")

        def stage_draft():
            spec = self.anchor / "docs/specs/stg/t1/spec.md"
            final = spec.read_bytes()
            spec.write_bytes(final.replace(b"Fixture.", b"Draft."))
            g("add", "docs/specs/stg/t1/spec.md")
            spec.write_bytes(final)

        def commit_queue():
            (self.anchor / "docs/specs/usd/queue.md").write_text(row_line("usd.t1", "Interface 인터페이스") + "\n", encoding="utf-8")
            g("add", "docs/specs/usd/queue.md")
            g("commit", "-qm", "a loop brought in from elsewhere")

        def state():
            return (git(self.anchor, "rev-parse", "HEAD"), git(self.anchor, "ls-files", "-s"), git(self.anchor, "for-each-ref"),
                    git(self.anchor, "status", "--porcelain", "--untracked-files=all"), sorted(path.name for path in (common / "devlyn-loops").iterdir()))
        for loop, tasks, prepare, message in (
                ("inv", [("t9", [], "Other", self.tasks[0][3])], lambda: None, "loop id inv was already added with another package"),
                ("dt", self.tasks[:1], lambda: g("checkout", "-q", "--detach"), "HEAD is detached"),
                ("trk", self.tasks[:1], edit_committed, "docs/specs/trk is committed with different content (docs/specs/trk/t1/spec.md)"),
                ("usd", self.tasks[:1], commit_queue, "loop id usd is already used by docs/specs/usd/queue.md"),
                ("stg", self.tasks[:1], stage_draft, "the index holds package changes HEAD lacks (docs/specs/stg/t1/spec.md); add leaves "
                 "the index as it is, so unstage them with `git restore --staged -- docs/specs/stg` and add again")):
            with self.subTest(loop=loop):
                meta = write_package(self.anchor, loop, tasks)
                prepare()
                before = state()
                self.assertIn(message, self.cli("add", meta, code=1)["reason"])
                self.assertEqual(state(), before)
                g("checkout", "-q", "main")
        self.assertIn("Draft.", git(self.anchor, "show", ":docs/specs/stg/t1/spec.md"))

    def test_cleanup_reports_what_it_cannot_remove(self):
        """C. Prediction: an original that cannot be unlinked stays and is reported as incomplete cleanup; the next cleanup
        removes it. Before: add committed the package and removed nothing."""
        from unittest import mock
        saved = {path: path.read_bytes() for path in (self.anchor / "docs/specs/inv").rglob("*") if path.is_file()}
        self.cli("add", self.meta)
        for path, data in saved.items():  # The originals as a crash before cleanup leaves them.
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        common = Path(git(self.anchor, "rev-parse", "--path-format=absolute", "--git-common-dir"))
        with mock.patch.object(Path, "unlink", side_effect=PermissionError("unlink denied")):
            notes = clean(common, records(common))
        self.assertEqual((sorted(notes), all(path.exists() for path in saved)), (sorted(f"{path}: incomplete cleanup: unlink denied" for path in saved), True))
        self.assertEqual((clean(common, records(common)), any(path.exists() for path in saved)), ([], False))

    def test_a_legacy_row_is_replaced_only_by_its_one_exact_claim(self):
        """Q. Prediction: a loop's queue file hides the legacy row whose exact text and occurrence it records, line endings
        aside, showing the loop's rows in its place; a claim on a missing occurrence, and a row two loops claim, replace
        nothing, so no other row disappears; loops without a record follow in loop-id order. Before: the first row equal
        to the recorded text was replaced, whatever its occurrence."""
        (self.anchor / QUEUE).write_bytes(b"# Intent Queue\n\n- [ ] alpha\r\n- [ ] alpha\n- [ ] beta\n")
        for loop, occurrence, line in (("one", 2, "- [ ] alpha"), ("two", 1, "- [ ] beta"), ("three", 1, "- [ ] beta"), ("four", 3, "- [ ] alpha")):
            (self.anchor / "docs/specs" / loop).mkdir(parents=True)
            (self.anchor / loop_queue(loop)).write_text(f"<!-- replaces {QUEUE} row (occurrence {occurrence}): {line} -->\n\n{row_line(f'{loop}.t1', 'T')}\n",
                                                         encoding="utf-8")
        git(self.anchor, "add", "docs/specs", env=self.env)
        self.assertEqual([(row["identity"], row["index"]) for row in queue_view(self.anchor, {})],
                         [(None, 2), ("one.t1", 2), (None, 4), ("four.t1", 2), ("three.t1", 2), ("two.t1", 2)])

    def test_handwritten_marks_never_satisfy_dependencies(self):
        """A loop without a record here, as in a fresh clone, is read from its tracked queue file, after the recorded loops
        and in loop-id order; a hand-written [x] there is no receipt-bound acceptance, so its dependent waits and whole-loop
        acceptance names the gap."""
        self.cli("add", self.meta)
        for loop in ("hw", "gw"):
            write_package(self.anchor, loop, self.tasks)
            rows = "\n\n".join(row_line(f"{loop}.{task}", title) for task, _, title, _ in self.tasks)
            (self.anchor / loop_queue(loop)).write_text(rows.replace(f"- [ ] {loop}.t1", f"- [x] {loop}.t1") + "\n", encoding="utf-8")
        git(self.anchor, "add", "docs/specs", env=self.env)
        git(self.anchor, "commit", "-qm", "loops brought in", env=self.env)
        status = self.cli("status")
        self.assertEqual((status["next"], status["blockers"]), ("inv.t1", [
            "inv.t2: waiting for inv.t1 (pending)", "gw.t2: prerequisite gw.t1 has no receipt-bound accepted source",
            "hw.t2: prerequisite hw.t1 has no receipt-bound accepted source"]))
        self.cli("drain", "--", sys.executable, "-c", "pass", "{packet}")
        report = Path(git(self.anchor, "rev-parse", "--path-format=absolute", "--git-common-dir")) / "devlyn-loops/hw/drain-report.md"
        self.assertIn("- Whole-loop acceptance: INCOMPLETE — hw.t1 accepted without a receipt, hw.t2 pending", report.read_text(encoding="utf-8"))

    def test_common_gitdir_locks_span_worktrees(self):
        linked = self.root / "linked tree"
        subprocess.run(["git", "-C", str(self.anchor), "worktree", "add", "-q", "-b", "side", str(linked)], check=True, env=self.env)
        write_package(linked, "inv", self.tasks)
        common = Path(git(self.anchor, "rev-parse", "--path-format=absolute", "--git-common-dir"))
        holder = [sys.executable, "-c", "import pathlib, runpy, sys; lock = runpy.run_path(sys.argv[1])['file_lock'];\n"
                  "with lock(pathlib.Path(sys.argv[2]), blocking=True):\n print('held', flush=True); sys.stdin.read()",
                  str(SKILLS / "_shared/platform-support.py")]
        (common / "devlyn-loops").mkdir(exist_ok=True)
        for name, args, check in (("queue.lock", ["add", linked / "docs/specs/inv/meta.md"], "waits"),
                                  ("drain.lock", ["drain", "--", "executor", "{packet}"], "refuses")):
            with subprocess.Popen(holder + [str(common / "devlyn-loops" / name)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True) as held:
                self.assertEqual(held.stdout.readline().strip(), "held")
                with subprocess.Popen([sys.executable, str(Path(__file__).resolve()), *map(str, args)], cwd=linked, env=self.env,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8") as waiter:
                    if check == "waits":
                        with self.assertRaises(subprocess.TimeoutExpired):
                            waiter.wait(timeout=1.5)
                        self.assertFalse(added_path(common, "inv").exists())
                        held.stdin.close()
                        self.assertEqual(waiter.wait(timeout=30), 0, waiter.stderr.read())
                    else:
                        out, _ = waiter.communicate(timeout=30)
                        self.assertEqual(waiter.returncode, 1)
                        self.assertIn("another drain is active", json.loads(out)["reason"])
                        held.stdin.close()
        self.assertEqual((read_json(added_path(common, "inv"))["origin"], read_json(added_path(common, "inv"))["branch"]), (str(linked), "side"))

    def test_a_crash_on_either_side_of_the_spawn_never_starts_a_second_executor(self):
        """The attempt's start is durable before the spawn, so a resumed drain observes writers first: it waits while
        an executor lives and adopts its submission, runs the executor once when none did, and fails the task where
        writers cannot be observed."""
        from unittest import mock
        helper = shared("task-complete")
        work, records = self.root / "work", self.root / "records"
        work.mkdir()
        records.mkdir()
        packet = {"worktree": str(work), "submission": str(records / "submission.json"), "inputs_sha": "0" * 40,
                  "evidence_dir": str(work / ".devlyn/loop")}
        spawns, checks = [], []

        class Crash(BaseException):
            """The controller dies here."""

        class Child:
            pid = 4242

            def wait(self):
                return 0

        def spawn(argv, **kwargs):
            spawns.append(argv)
            return Child()

        def crash_after_spawn(argv, **kwargs):
            spawns.append(argv)
            raise Crash

        def crash_before_spawn(argv, **kwargs):
            raise Crash

        def drain(popen, observe=lambda count: None):
            def stopped_writers(path):
                checks.append(path)
                observe(len(checks))
            with mock.patch.dict(helper, {"stopped_writers": stopped_writers}), mock.patch("subprocess.Popen", popen), \
                    mock.patch("time.sleep"):
                return ensure_submission("l.t", records / "packet.json", packet, ["executor", "{packet}"])

        def survivor(count):
            if count < 3:
                raise helper["WriterActive"]("active process 4242 uses task files")
            Path(packet["submission"]).write_text('{"by": "executor"}', encoding="utf-8")

        def unobservable(count):
            raise helper["WritersUnobservable"]("writer observation unsupported on this platform; retain workspace")

        for crash, observe, outcome in ((crash_after_spawn, survivor, (1, 3, None)), (crash_before_spawn, lambda count: None, (1, 1, None)),
                                        (crash_before_spawn, unobservable, (0, 1, "interrupted-unobservable"))):
            with self.subTest(crash=crash.__name__, observe=getattr(observe, "__name__", "nothing")):
                spawns.clear()
                checks.clear()
                for path in records.iterdir():
                    path.unlink()
                with self.assertRaises(Crash):
                    drain(crash)
                failure = drain(spawn, observe)
                self.assertEqual((len(spawns), len(checks), failure and failure.split(":")[0]), outcome)
                if crash is crash_after_spawn:
                    self.assertEqual(read_json(Path(packet["submission"])), {"by": "executor"})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    actions = parser.add_subparsers(dest="action")
    for name in ("check", "add"):
        actions.add_parser(name).add_argument("package", help="<repo>/docs/specs/<loop-id>/meta.md")
    actions.choices["add"].add_argument("--materialize", type=int, metavar="LINE", help="replace this pending legacy row")
    for name in ("status", "drain"):
        action = actions.add_parser(name)
        action.add_argument("--repo", default=".")
        action.add_argument("--local-only", "--no-push", action="store_true")
    actions.choices["drain"].add_argument("--worktree-root")
    actions.choices["drain"].add_argument("executor", nargs="+", help="host executor argv after --; {packet} becomes the packet path")
    args = parser.parse_args()
    if args.self_test:
        result = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(QueueTests))
        if result.wasSuccessful():
            print(f"queue self-test: PASS ({result.testsRun} tests)")
        return 0 if result.wasSuccessful() else 1
    if args.action is None:
        parser.error("check, add, status or drain is required")
    try:
        result = {"check": check, "add": add, "status": status, "drain": drain}[args.action](args)
    except (LoopError, OSError) as exc:
        result = {"status": "BLOCKED", "reason": str(exc)}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 1 if result["status"] == "BLOCKED" else 0


if __name__ == "__main__":
    shared("platform-support")["configure_utf8"]()
    sys.exit(main())
