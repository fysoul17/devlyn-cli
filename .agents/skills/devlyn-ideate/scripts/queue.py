#!/usr/bin/env python3
"""Ideate loop driver: package validation, the queue, locks, reconciliation and the serial drain.

`check` validates a loop package, `add` appends its tasks (or materializes one
legacy row), `status` shows the reconciled queue and `drain -- <argv>` runs each
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
import unittest

SKILLS = Path(__file__).resolve().parents[2]
QUEUE = "docs/specs/queue.md"
HEADER = b"# Intent Queue\n\n"
SENTINEL = "<!-- devlyn:verification -->"
ID = r"[a-z0-9][a-z0-9-]{0,62}"
SHA_RE = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
JSON_FENCE_RE = re.compile(r"(?ms)^```json[ \t]*\n(.*?)\n```[ \t]*$")
ROW_RE = re.compile(r"- \[(?P<mark>[ xF])\] (?P<text>.*)")
ITEM_RE = re.compile(rf"(?P<identity>(?P<loop>{ID})\.(?P<task>{ID})) \[(?P<title>(?:[^\]\\\n]|\\.)*)\]"
                     r"\(docs/specs/(?P=loop)/(?P=task)/spec\.md\)(?P<rest>(?: — .*)?)")
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


def load_expected(path, requirements, review):
    data = read_json(path)

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


def load_task(anchor, manifest, entry):
    loop_id, task = manifest["loop_id"], entry["id"]
    path = anchor / "docs/specs" / loop_id / task / "spec.md"
    front, body = frontmatter(read_text(path), path)

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
    if front["kind"] not in KINDS:
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
    expected_path = path.with_name("spec.expected.json")
    return {"id": task, "title": front["title"], "kind": front["kind"], "requirements": requirements, "review": review,
            "depends_on": entry["depends_on"], "expected": load_expected(expected_path, requirements, review)}


def load_package(anchor, loop_id):
    meta = anchor / "docs/specs" / loop_id / "meta.md"
    text = read_text(meta)
    require_sections(sections(text, meta), META_SECTIONS, meta)
    fences = JSON_FENCE_RE.findall(text)
    require(len(fences) == 1, f"{meta}: needs exactly one fenced json manifest, found {len(fences)}")
    try:
        manifest = shared("expected-contract")["loads_strict_json"](fences[0])
    except ValueError as exc:
        raise LoopError(f"{meta}: manifest is not strict JSON: {exc}") from exc
    check_manifest(anchor, manifest, loop_id, meta)
    return {"loop_id": loop_id, "meta_text": text, "manifest": manifest,
            "tasks": {entry["id"]: load_task(anchor, manifest, entry) for entry in manifest["tasks"]}}


def package_of(anchor, meta):
    meta = Path(meta).resolve()
    loop_id = meta.parent.name
    require(meta.name == "meta.md" and meta.parent.parent == anchor / "docs/specs", f"package must be <repo>/docs/specs/<loop-id>/meta.md: {meta}")
    return load_package(anchor, loop_id)


def escape(title):
    return title.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


def row_line(identity, title):
    loop, task = identity.split(".")
    return f"- [ ] {identity} [{escape(title)}](docs/specs/{loop}/{task}/spec.md)"


def parse_queue(data):
    try:
        lines = data.decode("utf-8").split("\n")
    except UnicodeError as exc:
        raise LoopError(f"{QUEUE} is not UTF-8: {exc}") from exc
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
    require(not duplicates, f"{QUEUE}: duplicate queue identity: {', '.join(duplicates)}")
    return rows


def transition(before, identity, mark, suffix=""):
    """The only legal transition: the identity's pending row becomes [x] or [F] with every other byte unchanged."""
    row = next((row for row in parse_queue(before) if row["identity"] == identity), None)
    require(row is not None and row["mark"] == " ", f"{identity} has no pending queue row to transition")
    lines = before.split(b"\n")
    ending = b"\r" if lines[row["index"]].endswith(b"\r") else b""
    lines[row["index"]] = f"- [{mark}] {row['text']}{suffix}".encode("utf-8") + ending
    return b"\n".join(lines)


def merge_rows(base, order, include):
    """Replace or insert `include` rows in `base`, placing new rows after the nearest earlier queued row."""
    lines = base.split(b"\n")
    for position, identity in enumerate(order):
        if identity not in include:
            continue
        where = {row["identity"]: row["index"] for row in parse_queue(b"\n".join(lines)) if row["identity"]}
        line = include[identity].encode("utf-8")
        if identity in where:
            lines[where[identity]] = line
            continue
        earlier = [where[i] for i in order[:position] if i in where]
        later = [where[i] for i in order[position + 1:] if i in where]
        at = max(earlier) + 1 if earlier else min(later) if later else len(lines) - (lines[-1] == b"")
        lines.insert(at, line)
    return b"\n".join(lines)


def one_line(text):
    text = " ".join(text.split())
    return text if len(text) <= 200 else text[:199] + "…"


def branch_of(identity):
    return "devlyn/" + identity.replace(".", "/")


def receipt_path(common, identity):
    return common / "devlyn-completion" / hashlib.sha256(branch_of(identity).encode()).hexdigest()[:24] / "receipt.json"


def task_complete(action, **values):
    helper = shared("task-complete")
    try:
        return helper[action](argparse.Namespace(**values))
    except (helper["CompletionError"], OSError, KeyError, TypeError, ValueError) as exc:
        raise LoopError(f"task-complete {action}: {exc}") from exc


def derive_state(anchor, common, row, claims):
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
        require(recovery == receipt["publish_sha"], f"{identity}: recovery ref {receipt['recovery_ref']} is {recovery or 'missing'}, receipt binds {receipt['publish_sha']}")
        if receipt.get("queue"):
            marks = [r["mark"] for r in parse_queue(show(anchor, receipt["publish_sha"], QUEUE) or b"") if r["identity"] == identity]
            require(marks == ["x" if result == "accepted" else "F"], f"{identity}: terminal commit {receipt['publish_sha']} does not carry its {result} mark")
    packet = path.parent / "packet.json"
    if not result and packet.exists():
        bound = read_json(packet)
        for key in ("contract", "expected"):
            current = anchor / Path(bound[key]["path"]).relative_to(bound["worktree"])
            if not current.is_file() or hashlib.sha256(current.read_bytes()).hexdigest() != bound[key]["sha256"]:
                # Drain fails this task alone; the revision is planned as a new task.
                state["inputs_changed"] = (f"inputs-changed: {current.relative_to(anchor).as_posix()} changed after its inputs were "
                                           "committed; plan the revision as a new task")
                break
    state.update(kind=result or "active", path=path, receipt=receipt)
    return state


def view(anchor, common, local_only=False):
    """Reconcile the queue with every receipt and recovery ref before anything is selected."""
    with lock(common, "queue.lock", blocking=True):
        queue = anchor / QUEUE
        data = queue.read_bytes() if queue.exists() else b""
    claims, unreadable = {}, []
    for path in sorted((common / "devlyn-completion").glob("*/receipt.json")):
        try:
            receipt = read_json(path)
            claims.setdefault(receipt["task"], []).append((path, receipt))
        except (LoopError, KeyError, TypeError) as exc:
            unreadable.append(f"{path}: {exc}")
    v = {"anchor": anchor, "common": common, "data": data, "rows": parse_queue(data), "packages": {}, "states": {},
         "unreadable": unreadable, "local_only": local_only}
    for row in v["rows"]:
        if row["identity"]:
            state = v["states"][row["identity"]] = derive_state(anchor, common, row, claims.get(row["identity"], []))
            if state["kind"] in {"pending", "active"} and row["loop"] not in v["packages"]:
                v["packages"][row["loop"]] = load_package(anchor, row["loop"])
            if row["loop"] in v["packages"]:
                require(row["task"] in v["packages"][row["loop"]]["tasks"], f"{row['identity']} is not a task of loop {row['loop']}")
    for row in v["rows"]:
        state = v["states"].get(row["identity"])
        for dep in v["packages"][row["loop"]]["tasks"][row["task"]]["depends_on"] if state and state["kind"] == "pending" else []:
            dep_state = v["states"].get(f"{row['loop']}.{dep}")
            require(dep_state is not None, f"{row['identity']} depends on {row['loop']}.{dep}, which is not queued")
            if dep_state["kind"] in {"failed", "blocked"}:
                state.update(kind="blocked", blocker=f"{row['loop']}.{dep}", root=dep_state.get("root") or dep_state)
                break
    return v


def is_local(v, loop):
    package = v["packages"].get(loop)
    return (v["local_only"] or (package is not None and package["manifest"]["delivery"] == "local-only")
            or any(s["receipt"] and s["receipt"].get("local_only") for i, s in v["states"].items() if i.split(".")[0] == loop))


def delivered(receipt):
    return receipt.get("delivery") == "COMPLETE" or bool(receipt.get("merge"))


def waiting(v, row):
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
    return None


def next_task(v, attempted):
    """Earliest unsettled receipt first, then the earliest eligible pending row in physical order."""
    for row in v["rows"]:
        state = v["states"].get(row["identity"])
        if state and state["receipt"] and row["identity"] not in attempted and (
                state["kind"] == "active" or not state["receipt"].get("queue") or state["receipt"].get("delivery") not in SETTLED):
            return row
    return next((row for row in v["rows"] if row["identity"] not in attempted and v["states"].get(row["identity"], {}).get("kind") == "pending"
                 and waiting(v, row) is None), None)


def annotate(v):
    for row in v["rows"]:
        state = v["states"].get(row["identity"])
        if state and state["kind"] == "pending" and (reason := waiting(v, row)):
            state["waiting"] = reason


def frontier(v, loop):
    accepted = [v["states"][row["identity"]] for row in v["rows"] if row.get("loop") == loop
                and v["states"][row["identity"]]["kind"] == "accepted" and v["states"][row["identity"]]["receipt"]]
    return accepted[-1] if accepted else None


def terminal_line(v, identity):
    state = v["states"][identity]
    row = next(row for row in v["rows"] if row["identity"] == identity)
    if state["kind"] == "blocked":
        root = state["root"]["receipt"]
        return f"- [F] {row['text']} — blocked-prerequisite:{state['blocker']} (receipt {root['id'] if root else 'none'})"
    if state["kind"] in {"accepted", "failed"} and state["receipt"] and state["receipt"].get("queue"):
        terminal = parse_queue(show(v["anchor"], state["receipt"]["publish_sha"], QUEUE) or b"")
        return next(r["line"] for r in terminal if r["identity"] == identity)
    return None


def build_tree(worktree, parent, files):
    with tempfile.TemporaryDirectory(prefix="devlyn-loop-index-") as temp:
        env = {**os.environ, "GIT_INDEX_FILE": str(Path(temp) / "index")}
        git(worktree, "read-tree", parent, env=env)
        for rel, data in files.items():
            blob = git(worktree, "hash-object", "-w", "--stdin", data=data)
            git(worktree, "update-index", "--add", "--cacheinfo", f"100644,{blob},{rel}", env=env)
        return git(worktree, "write-tree", env=env)


def commit_files(worktree, branch, parent, files, message, *, checkout):
    commit = git(worktree, "commit-tree", build_tree(worktree, parent, files), "-p", parent, "-m", message)
    git(worktree, "update-ref", "refs/heads/" + branch, commit, parent)
    if checkout:
        sync(worktree, branch, parent, commit)
    return commit


def sync(worktree, branch, parent, commit):
    """Move a checkout that was clean at `parent` to `commit`; refuses rather than overwrite local edits."""
    if git_run(worktree, "symbolic-ref", "-q", "HEAD", ok=(0, 1)).stdout.decode("utf-8").strip() == "refs/heads/" + branch:
        git(worktree, "read-tree", "-m", "-u", parent, commit)


def input_files(v, row, receipt, local):
    anchor, worktree, loop = v["anchor"], Path(receipt["worktree"]), row["loop"]
    rels = [f"docs/specs/{loop}/meta.md", f"docs/specs/{loop}/{row['task']}/spec.md", f"docs/specs/{loop}/{row['task']}/spec.expected.json"]
    files = {rel: (anchor / rel).read_bytes() for rel in rels}
    include = {row["identity"]: row["line"]}
    for other in v["rows"] if local else []:
        if other["identity"] and other.get("loop") == loop and other["identity"] != row["identity"]:
            if line := terminal_line(v, other["identity"]):
                include[other["identity"]] = line
    order = [r["identity"] for r in v["rows"] if r["identity"]]
    files[QUEUE] = merge_rows(show(worktree, receipt["baseline"], QUEUE) or HEADER, order, include)
    return files


def require_merged(v, row, base):
    """auto/pr: every prerequisite's merge commit must be in the base, before allocation and before every execution."""
    for dep in v["packages"][row["loop"]]["tasks"][row["task"]]["depends_on"]:
        receipt = v["states"][f"{row['loop']}.{dep}"]["receipt"] or {}
        merge = ((receipt.get("merge") or {}).get("mergeCommit") or {}).get("oid")
        require(merge and ancestor(v["anchor"], merge, base), f"{row['identity']}: base {base} lacks the delivered prerequisite merge {merge}")


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
    identity, loop, task = row["identity"], row["loop"], row["task"]
    package = v["packages"][loop]
    manifest = package["manifest"]
    anchor, common = v["anchor"], v["common"]
    deps = [v["states"][f"{loop}.{dep}"] for dep in package["tasks"][task]["depends_on"]]
    values = {"repo": str(anchor), "task": identity, "branch": branch_of(identity), "repository": None,
              "base": manifest["base_ref"], "remote": "origin", "worktree": str(opts.worktree_root / loop / task),
              "local_base": None, "from_receipt": None}
    if is_local(v, loop):
        tip = frontier(v, loop)
        start = tip["receipt"]["source_sha"] if tip else manifest["base_sha"]
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
        require_merged(v, row, start)
    require(evidence_ignored(anchor, common, start),
            f"{identity}: .devlyn/ is not ignored in its start commit {start}, so loop evidence would dirty task source; commit a "
            f"`.devlyn/` entry to .gitignore in the base the task starts from, or add `.devlyn/` to {common / 'info' / 'exclude'}")
    result = task_complete("allocate", **values)
    progress(identity, f"allocated {result['worktree']}")


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


def ensure_submission(identity, packet_path, packet, executor):
    """Run the executor once unless its submission exists; returns a drain-recorded failure reason, else None."""
    submission = Path(packet["submission"])
    if submission.exists():
        return None
    worktree = Path(packet["worktree"])
    attempts = submission.with_name("executions.log")
    if attempts.exists():
        helper = shared("task-complete")
        try:
            helper["stopped_writers"](worktree)
        except helper["WritersUnobservable"] as exc:
            return f"interrupted-unobservable: an interrupted executor may still be writing ({exc})"
        except helper["CompletionError"] as exc:
            raise LoopError(f"{identity}: an earlier executor may still be writing ({exc}); stop it, then drain again") from exc
    argv = [part.replace("{packet}", str(packet_path)) for part in executor]
    output = Path(packet["evidence_dir"])
    output.mkdir(parents=True, exist_ok=True)
    try:
        # Files, never a pipe: a wrapper such as codex-monitored.sh refuses a piped stdout.
        with (output / "executor.stdout").open("ab") as stdout, (output / "executor.stderr").open("ab") as stderr:
            child = subprocess.Popen(shared("platform-support")["native_argv"](argv), cwd=worktree, stdout=stdout, stderr=stderr)
    except OSError as exc:
        raise LoopError(f"executor could not start: {exc}") from exc
    with attempts.open("a", encoding="utf-8") as log:
        log.write(f"{datetime.datetime.now(datetime.timezone.utc).isoformat()} executor pid {child.pid} started\n")
    progress(identity, f"executing; output in {output}")
    code = child.wait()
    if not submission.exists():
        write_json(submission, {"schema_version": 1, "task": identity, "source_sha": packet["inputs_sha"],
                                "summary": "recorded by the drain, not the executor",
                                "blockers": [{"kind": "blocked-infrastructure", "detail": f"executor exited {code} without a submission"}]})
    return None


def settle(v, row, receipt_file):
    """Create (or adopt) the queue-only terminal commit atop the bound source, then attach it."""
    identity = row["identity"]
    receipt = read_json(receipt_file)
    worktree, source, branch = Path(receipt["worktree"]), receipt["source_sha"], receipt["branch"]
    failed = receipt.get("product") == "FAILED"
    suffix = f" — {one_line(receipt['acceptance']['reasons'][0])} (receipt {receipt['id']})" if failed else ""
    with lock(v["common"], "queue.lock", blocking=True):
        after = transition(show(worktree, receipt["acceptance"]["inputs_sha"], QUEUE) or b"", identity, "F" if failed else "x", suffix)
        head = git(worktree, "rev-parse", "refs/heads/" + branch)
        if head == source:
            commit = commit_files(worktree, branch, source, {QUEUE: after}, f"devlyn loop: {identity} {'failed' if failed else 'accepted'}",
                                  checkout=not failed)
        else:
            require(git(worktree, "rev-parse", head + "^") == source and show(worktree, head, QUEUE) == after
                    and git(worktree, "diff", "--name-only", source, head) == QUEUE,
                    f"{identity}: owned branch moved past the bound source without its terminal transition; inspect {worktree}")
            commit = head
            if not failed:
                sync(worktree, branch, source, commit)
        progress(identity, f"terminal {commit}")
        task_complete("attach", receipt=str(receipt_file), commit=commit, file=QUEUE)
    progress(identity, "attached")


def advance(v, row, opts):
    """Run or resume one task from its durable state; never replays a bound result."""
    identity = row["identity"]
    path = receipt_path(v["common"], identity)
    if not path.exists():
        allocate(v, row, opts)
    receipt = read_json(path)
    if not receipt.get("acceptance"):
        if not receipt.get("local_only"):
            require_merged(v, row, receipt["baseline"])
        packet_path, packet = ensure_packet(v, row, path, receipt)
        failure = v["states"][identity].get("inputs_changed") or ensure_submission(identity, packet_path, packet, opts.executor)
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
        result = task_complete("complete", receipt=str(path), acceptance=None, mode=None if local else packet["delivery"],
                               local_only=local, writers_stopped=True)
        progress(identity, f"delivery {result['status']}")


def summary(v, row):
    state = v["states"][row["identity"]]
    receipt = state["receipt"] or {}
    item = {"identity": row["identity"], "result": state["kind"], "receipt": str(state["path"]) if state["path"] else None}
    if state["kind"] == "failed":
        item["reason"] = row["rest"].lstrip(" —") if row["mark"] == "F" else (receipt.get("acceptance") or {}).get("reasons", ["failed"])[0]
    if state["kind"] == "blocked":
        item["reason"] = f"blocked-prerequisite:{state['blocker']}"
    if state.get("waiting") or state.get("inputs_changed"):
        item["reason"] = state.get("waiting") or state["inputs_changed"]
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


def write_reports(v, status, reason):
    paths = []
    for loop in dict.fromkeys(row["loop"] for row in v["rows"] if row["identity"]):
        items = [summary(v, row) for row in v["rows"] if row.get("loop") == loop]
        whole = ("ACCEPTED" if all(item["result"] == "accepted" for item in items)
                 else "INCOMPLETE — " + ", ".join(f"{item['identity']} {item['result']}" for item in items if item["result"] != "accepted"))
        lines = [f"# Drain report — {loop}", "", f"- Generated: {datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')}",
                 f"- Queue: {v['anchor'] / QUEUE}", f"- Drain: {status}" + (f" — {reason}" if reason else ""),
                 f"- Whole-loop acceptance: {whole}", ""]
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
        attempted, last, status, reason = set(), None, "DRAINED", None
        try:
            while True:
                last = view(anchor, common, args.local_only)
                row = next_task(last, attempted)
                if row is None:
                    break
                attempted.add(row["identity"])
                advance(last, row, args)
            if any(state["kind"] in {"pending", "active"} for state in last["states"].values()) or counts(last)["legacy_pending"]:
                status = "WAITING"
        except (LoopError, OSError) as exc:
            status, reason = "BLOCKED", str(exc)
            with contextlib.suppress(LoopError, OSError):
                last = view(anchor, common, args.local_only)
        if last is None:
            return {"status": status, "reason": reason}
        annotate(last)
        return {"status": status, "reason": reason, "reports": write_reports(last, status, reason), "counts": counts(last),
                "tasks": [summary(last, row) for row in last["rows"] if row["identity"]]}


def status(args):
    anchor, common = repository(args.repo)
    v = view(anchor, common, args.local_only)
    row = next_task(v, set())
    annotate(v)
    tasks = [summary(v, r) for r in v["rows"] if r["identity"]]
    return {"status": "OK", "queue": str(anchor / QUEUE), "counts": counts(v), "next": row["identity"] if row else None,
            "blockers": [f"{t['identity']}: {t['reason']}" for t in tasks if t.get("reason") and t["result"] in {"pending", "active", "blocked"}]
            + [f"legacy row {r['index'] + 1} needs planning: {r['text']}" for r in v["rows"] if not r["identity"] and r["mark"] == " "]
            + [f"unreadable receipt {item}" for item in v["unreadable"]],
            "delivery": [t for t in tasks if t.get("resume")]}


def add(args):
    anchor, common = repository(Path(args.package).resolve().parent)
    package = package_of(anchor, args.package)
    loop = package["loop_id"]
    rows = [row_line(f"{loop}.{task['id']}", task["title"]) for task in package["tasks"].values()]
    queue = anchor / QUEUE
    with lock(common, "queue.lock", blocking=True):
        data = queue.read_bytes() if queue.exists() else None
        existing = parse_queue(data or b"")
        identities = [f"{loop}.{task}" for task in package["tasks"]]
        clash = sorted({row["identity"] for row in existing} & set(identities))
        require(not clash, f"task identity already queued: {', '.join(clash)}; plan revised work under new IDs")
        if args.materialize:
            target = next((row for row in existing if row["index"] == args.materialize - 1), None)
            require(target is not None and target["identity"] is None and target["mark"] == " ",
                    f"{QUEUE} line {args.materialize} is not a pending legacy row")
            intent = " ".join(sections(package["meta_text"], "meta.md")["Intent"].split())
            require(" ".join(target["text"].split()) in intent, "meta.md '## Intent' must reproduce the legacy row's intent verbatim")
            lines = data.split(b"\n")
            ending = b"\r" if lines[target["index"]].endswith(b"\r") else b""
            lines[target["index"]:target["index"] + 1] = [row.encode("utf-8") + ending for row in rows]
            acceptance()["atomic_write"](queue, b"\n".join(lines))
        elif data is None:
            queue.parent.mkdir(parents=True, exist_ok=True)
            queue.write_bytes(HEADER + "".join(row + "\n" for row in rows).encode("utf-8"))
        else:
            with queue.open("ab") as stream:
                stream.write((b"" if data.endswith(b"\n") or not data else b"\n") + "".join(row + "\n" for row in rows).encode("utf-8"))
    return {"status": "ADDED", "queue": str(queue), "tasks": identities}


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

    def test_rows_transitions_and_metadata_merge(self):
        queue = (HEADER + f"- [x] old intent\n{row_line('a.t1', 'Same')}\n- [ ] legacy intent\n{row_line('a.t2', 'Same')}\n".encode())
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
        order = ["a.t1", "a.t2", "a.t3"]
        merged = merge_rows(HEADER + b"- [x] keep\n" + row_line("a.t3", "C").encode() + b"\n",
                            order, {"a.t1": "- [x] " + row_line("a.t1", "A")[6:], "a.t2": row_line("a.t2", "B")})
        self.assertEqual([r["identity"] for r in parse_queue(merged)], [None, "a.t1", "a.t2", "a.t3"])
        self.assertTrue(merged.startswith(HEADER + b"- [x] keep\n"))

    def test_add_is_literal_atomic_and_materializes_legacy_rows(self):
        package = {path: path.read_bytes() for path in (self.anchor / "docs/specs/inv").rglob("*") if path.is_file()}
        queue = self.anchor / QUEUE
        self.assertEqual(self.cli("add", self.meta)["tasks"], ["inv.t1", "inv.t2"])
        expected = HEADER + f"{row_line('inv.t1', 'Interface 인터페이스')}\n{row_line('inv.t2', 'Consumer [app]')}\n".encode()
        self.assertEqual(queue.read_bytes(), expected)
        self.assertIn("already queued: inv.t1, inv.t2", self.cli("add", self.meta, code=1)["reason"])
        self.assertEqual(queue.read_bytes(), expected)
        self.assertEqual({path: path.read_bytes() for path in package}, package)
        queue.write_bytes(expected + b"- [ ] Make   the  report weekly")
        second = write_package(self.anchor, "rep", [("t1", [], "Weekly", self.tasks[0][3])], intent="Wrong intent.")
        self.assertIn("reproduce the legacy row's intent", self.cli("add", second, "--materialize", 5, code=1)["reason"])
        write_package(self.anchor, "rep", [("t1", [], "Weekly", self.tasks[0][3])], intent="User asked: make the report weekly.")
        self.assertIn("not a pending legacy row", self.cli("add", second, "--materialize", 3, code=1)["reason"])
        self.assertIn("reproduce", self.cli("add", second, "--materialize", 5, code=1)["reason"])
        write_package(self.anchor, "rep", [("t1", [], "Weekly", self.tasks[0][3])], intent="User asked: Make the report weekly.")
        self.cli("add", second, "--materialize", 5)
        self.assertEqual(queue.read_bytes(), expected + row_line("rep.t1", "Weekly").encode())

    def test_handwritten_marks_never_satisfy_dependencies(self):
        queue = self.anchor / QUEUE
        for delivery in ("local-only", "auto"):
            with self.subTest(delivery=delivery):
                queue.unlink(missing_ok=True)
                self.cli("add", write_package(self.anchor, "hw", self.tasks, delivery=delivery))
                queue.write_bytes(queue.read_bytes().replace(b"- [ ] hw.t1", b"- [x] hw.t1"))
                status = self.cli("status")
                self.assertEqual(status["next"], None)
                self.assertIn("hw.t2: prerequisite hw.t1 has no receipt-bound accepted source", status["blockers"])

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
                        self.assertFalse((linked / QUEUE).exists())
                        held.stdin.close()
                        self.assertEqual(waiter.wait(timeout=30), 0, waiter.stderr.read())
                    else:
                        out, _ = waiter.communicate(timeout=30)
                        self.assertEqual(waiter.returncode, 1)
                        self.assertIn("another drain is active", json.loads(out)["reason"])
                        held.stdin.close()
        self.assertEqual(parse_queue((linked / QUEUE).read_bytes())[0]["identity"], "inv.t1")


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
