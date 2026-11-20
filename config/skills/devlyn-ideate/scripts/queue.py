#!/usr/bin/env python3
"""Ideate loop driver: package validation, the queue, locks, reconciliation and the serial drain.

`check` validates a loop package, `add` captures it with its queue rows (which may
replace one legacy row), `withdraw` takes back a queued loop none of whose tasks has
started and that replaced no legacy row, `status` shows the reconciled queue and `drain -- <argv>` runs each
eligible task through allocation, committed inputs, one host-supplied executor
exchange, evidence-derived acceptance, the terminal transition and delivery.
Protocol and commands: ../references/loop.md; formats: ../references/package-format.md.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime
import errno
import functools
import hashlib
import itertools
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
SETTLED = {"LOCAL_ONLY", "COMPLETE", "FAILED", "CLOSED"}
OBLIGATIONS = [
    "Work only in this worktree on its owned branch under the installed methodology; never edit the loop package or docs/specs/queue.md.",
    "Commit any source changes on the owned branch; when none are needed, use inputs_sha without creating an empty commit. Leave no uncommitted or untracked source and remove residue the change created.",
    "Run `runner` on the committed candidate; review records must bind engine, model, that source and both contract digests.",
    "Write `submission` as executor.md says and exit; never weaken acceptance.",
]


class LoopError(Exception):
    pass


class Waiting(LoopError):
    """The task cannot proceed now: it waits with this reason while independent work continues."""


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


def skill_diagnostics(anchor):
    running = SKILLS / ".devlyn-install.json"
    markers = dict.fromkeys([running, *(anchor / host / "skills/.devlyn-install.json" for host in (".claude", ".agents"))])
    versions, errors = {}, {}
    for marker in markers:
        try:
            data = json.loads(marker.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or not isinstance(data.get("version"), (str, type(None))):
                raise ValueError("install marker must be an object with a string or null version")
            versions[marker] = data.get("version")
        except FileNotFoundError:
            continue  # Global-only and source checkouts need no repository install marker.
        except (OSError, ValueError, RecursionError) as exc:
            errors[marker] = str(exc)
    skill = {"root": str(SKILLS), "version": versions.get(running)}
    warnings = []
    for marker in markers:
        if marker in errors:
            detail = f"unreadable: {errors[marker]}"
        elif running not in errors and marker in versions and versions[marker] != skill["version"]:
            detail = f"version {json.dumps(versions[marker])}"
        else:
            continue
        warnings.append(f"Running skill {skill['root']} (version {json.dumps(skill['version'])}); "
                        f"install marker {marker} ({detail}); run npx devlyn-cli@latest update.")
    return {"skill": skill, "warnings": warnings}


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
def lock(common, name, *, blocking, busy="a drain or a withdraw is running in this repository"):
    """Native locks on the common Gitdir: drain.lock for a controller's lifetime or a withdraw, queue.lock for short mutations."""
    directory = common / "devlyn-loops"
    directory.mkdir(exist_ok=True)
    with contextlib.ExitStack() as stack:
        try:
            stack.enter_context(shared("platform-support")["file_lock"](directory / name, blocking=blocking))
        except BlockingIOError as exc:
            raise LoopError(f"{busy} ({directory / name})") from exc
        yield


def harness_call(name, *args, **kwargs):
    helper = shared("harness-store")
    try:
        return helper[name](*args, **kwargs)
    except helper["HarnessError"] as exc:
        raise LoopError(str(exc)) from exc


def enforce_binding(common, anchor=None):
    binding = harness_call("read_binding", common)
    try:
        harness_call("check_binding", binding, harness_call("resolve", SKILLS))
    except (LoopError, OSError) as exc:
        # A queue that settled outside queue.py (its last delivery finished through task-complete.py) keeps a binding no
        # work needs: another release drops it instead of refusing. Callers outside the queue lock pass `anchor`.
        if binding and anchor is not None and release_settled_binding(anchor, common, interrupted_add=True):
            return enforce_binding(common)
        if binding:
            line = shared("storage-client")["queue_handoff"](common, binding)
            argv = harness_call("recovery_argv", binding, sys.argv[1:]) if line is None else None
            error = LoopError(f"{exc}; {line}" if line is not None else f"{exc}; recovery argv: {json.dumps(argv, ensure_ascii=False)}")
            error.handoff = line
            raise error from exc
        raise
    return binding


def unfinished(v):
    if v["unreadable"] or counts(v)["legacy_pending"]:
        return True
    for state in v["states"].values():
        receipt = state["receipt"]
        # A blocked task waits on a failed prerequisite for good, as drain counts it: it holds no binding.
        if state.get("invalid") or state["kind"] in {"pending", "active"} or receipt and (
                not receipt.get("queue") or receipt.get("delivery") not in SETTLED):
            return True
    # An interrupted capture with no add record is still resumable work.
    refs = git(v["anchor"], "for-each-ref", "--format=%(refname)", CAPTURES).splitlines()
    return any(ref.removeprefix(CAPTURES) not in v["records"] for ref in refs)


def bindable(anchor, common):
    """Whether a first add may bind its release: the queue reads and holds no unfinished work. A queue that cannot be read
    is not proven settled, so the add captures unbound, as its skill source adds, and status and drain report why."""
    try:
        return not unfinished(view(anchor, common, pure=True))
    except (LoopError, OSError):
        return False


def release_settled_binding(anchor, common, *, interrupted_add=False):
    """Remove the binding once nothing needs it. The bound release keeps one from an interrupted first add (no record
    yet) so its retry rebinds the same identity; another release (`interrupted_add`) drops that too, since a binding
    published before its capture captured nothing. Returns whether it was removed."""
    with lock(common, "queue.lock", blocking=True):
        if not harness_call("read_binding", common):
            return False
        v = view(anchor, common, pure=True)
        if unfinished(v) or not (v["records"] or interrupted_add):
            return False
        (common / "devlyn-loops/harness.json").unlink()
        return True


def refuse_other_release(common, anchor=None):
    """Withdraw's refusal of a queue another release bound, made before enforce_binding hands out that release's argv or
    handoff: a release older than withdraw has none. As there, a caller outside the queue lock first drops a binding no
    work needs."""
    binding = harness_call("read_binding", common)
    if not binding or (invoking := harness_call("resolve", SKILLS)) and invoking["release"] == binding["release"] or (
            anchor is not None and release_settled_binding(anchor, common, interrupted_add=True)):
        return
    release = binding["release"]
    raise LoopError(f"this queue is bound to devlyn-cli {release['version']} at {release['root']}; withdraw waits until that "
                    "release's queue settles")


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
    require(rows and all(row["identity"] and row["loop"] == loop for row in rows), f"{label}: every row must be a task row of loop {loop}")
    targets = [(int(m[1]), m[2]) for line in data.decode("utf-8").split("\n") if (m := REPLACES_RE.fullmatch(line.removesuffix("\r")))]
    require(len(targets) <= 1, f"{label}: replaces more than one legacy row")
    return rows, targets[0] if targets else None


def one_line(text):
    text = " ".join(text.split())
    return text if len(text) <= 200 else text[:199] + "…"


def branch_of(identity):
    return "devlyn/" + identity.replace(".", "/")


def receipt_path(common, identity):
    key = hashlib.sha256(branch_of(identity).encode()).hexdigest()[:24]
    root = common / 'devlyn-completion'
    active = root / key / 'receipt.json'
    if active.exists():
        return active
    retired = sorted((root / 'retired').glob(key + '.*/receipt.json'))
    if len(retired) > 1:
        delivered = []
        for path in retired:
            receipt = read_json(path)
            require(isinstance(receipt, dict), f'{path}: malformed retired receipt')
            if receipt.get('delivery') == 'COMPLETE':
                delivered.append(path)
        require(len(delivered) <= 1, f'conflicting delivered receipts for {identity}: {delivered}')
        if delivered:
            return delivered[0]
    return retired[-1] if retired else active


def seen(path, *, entries=False):
    """What withdraw sees at `path`: whether it exists, a dangling link included, or with `entries` the paths in it. Where
    it or a folder above it is missing (ENOENT, ENOTDIR) it sees nothing; any other error refuses, naming the path, where
    exists, is_file and glob would answer no."""
    try:
        found = list(path.iterdir()) if entries else [os.lstat(path)]
    except (FileNotFoundError, NotADirectoryError):
        found = []
    except OSError as exc:
        raise LoopError(f"{path} cannot be read ({exc.strerror or exc}), so withdraw cannot tell what it holds; withdraw changes "
                        "nothing until it can") from exc
    return found if entries else bool(found)


def task_directories(common, identity):
    """Every receipt directory of the task, a link included: the active one, then retired, then moved, the order in which
    task-complete.py moves one, and a path once seen is kept, so a directory moving meanwhile is seen at least once."""
    root, key = common / "devlyn-completion", hashlib.sha256(branch_of(identity).encode()).hexdigest()[:24]
    return [*([root / key] if seen(root / key) else []),
            *(path for folder in ("retired", "moved") for path in seen(root / folder, entries=True) if path.name.startswith(key + "."))]


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
    record, as in a fresh clone, from the checkout's tracked queue files in loop-id order. A claim matching no row replaces
    nothing; a row two loops claim is hidden, neither loop taking its place."""
    legacy = anchor / QUEUE
    raw = [row for row in parse_queue(legacy.read_bytes() if legacy.exists() else b"") if not row["identity"]]
    loops = {loop: parse_loop(show(anchor, added["commit"], loop_queue(loop)), loop, f"{CAPTURES}{loop}:{loop_queue(loop)}")
             for loop, added in recorded.items()}
    tracked = set(filter(None, git(anchor, "ls-files", "-z", "--", ":(glob)docs/specs/*/queue.md").split("\0")))
    head = ref_value(anchor, "HEAD")
    if head:
        tracked.update(rel for rel in git(anchor, "ls-tree", "-r", "-z", "--name-only", head, "--", "docs/specs").split("\0")
                       if re.fullmatch(r"docs/specs/[^/]+/queue\.md", rel))
    for rel in sorted(tracked, key=lambda rel: rel.split("/")[2]):
        loop, data, read_error = rel.split("/")[2], None, None
        if loop in recorded:
            continue
        try:
            data = (anchor / rel).read_bytes() if (anchor / rel).is_file() else None
        except OSError as exc:
            read_error = exc
        # A directory name alone proves nothing. A task row in the checkout or HEAD proves this is a loop queue; HEAD
        # keeps that proof when the checkout loses its rows or cannot be read. Only a proven queue is parsed or blocks.
        known = False
        for candidate in (data, show(anchor, head, rel) if head else None):
            for line in (candidate or b"").decode("utf-8", errors="replace").splitlines():
                match = ROW_RE.fullmatch(line)
                item = ITEM_RE.fullmatch(match["text"].rstrip()) if match else None
                if item and item["loop"] == loop and bool(item["rest"]) == (match["mark"] == "F"):
                    known = True
        if known:
            if read_error is not None:
                raise LoopError(f"{anchor / rel}: {read_error}") from read_error
            loops[loop] = parse_loop(data, loop, anchor / rel)
    claims = {}
    for loop, (_, target) in loops.items():
        if target:
            claims.setdefault(target, []).append(loop)
    placed = {}
    for (occurrence, line), owners in claims.items():
        matches = [row["index"] for row in raw if row["line"] == line]
        if len(matches) >= occurrence:
            placed[matches[occurrence - 1]] = owners[0] if len(owners) == 1 else None
    rows = []
    for row in raw:
        rows += [row] if row["index"] not in placed else loops[placed[row["index"]]][0] if placed[row["index"]] else []
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
        try:
            if not (root / "docs/specs").is_dir():
                continue
            untracked = set(filter(None, git(root, "ls-files", "--others", "-z", "--", "docs/specs").split("\0")))
        except (LoopError, OSError) as exc:
            notes.append(f"package cleanup retained: {root}: {exc}")
            continue
        for loop, added in recorded.items():
            package = f"docs/specs/{loop}/"
            if added["origin"] != origin or not any(rel.startswith(package) for rel in untracked):
                continue
            try:
                states = package_state(root, added["commit"], loop)
            except (LoopError, OSError) as exc:
                notes.append(f"package cleanup retained: {root / package}: {exc}")
                continue
            for rel, state in states.items():
                if rel in untracked and state == "different":
                    notes.append(f"{root / rel}: kept, it differs from the captured package {CAPTURES}{loop}")
                elif rel in untracked and state == "equal":
                    try:
                        (root / rel).unlink()
                    except OSError as exc:
                        notes.append(f"package cleanup retained: {root / rel}: {exc}")
            for directory, _, _ in os.walk(root / package, topdown=False):
                try:
                    os.rmdir(directory)
                except OSError as exc:
                    if exc.errno not in {errno.ENOTEMPTY, errno.EEXIST, errno.ENOENT}:
                        notes.append(f"package cleanup retained: {directory}: {exc}")
    return notes


def task_complete(action, *, exclude_receipts=(), warnings=None, **values):
    helper = shared("task-complete")
    try:
        # Preserve the previous-receipt sweep, excluding only queue-invalid owners.
        options = {"exclude_receipts": exclude_receipts} if action == "allocate" else {}
        if action in {"allocate", "complete"}:
            options["warnings"] = warnings
        return helper[action](argparse.Namespace(**values), **options)
    except (helper["CompletionError"], OSError, KeyError, TypeError, ValueError) as exc:
        # Inherited helper containment includes these three programming-error types; the controller boundary is narrower.
        details = getattr(exc, "storage_error", {})
        context = f"; receipt={details.get('receipt')}; resume={details.get('resume')}" if details else ""
        raise LoopError(f"task-complete {action}: {exc}{context}") from exc


def derive_state(anchor, common, row, claims, rev):
    identity = row["identity"]
    state = {"kind": {" ": "pending", "x": "accepted", "F": "failed"}[row["mark"]], "receipt": None, "path": None}
    require(len(claims) <= 1, f"conflicting receipts for {identity}: {', '.join(str(path) for path, _ in claims)}")
    if not claims:
        path = receipt_path(common, identity)
        if path.parent.exists() or path.parent.is_symlink():
            state.update(kind="pending", barrier=True,
                         invalid=f"receipt missing at {path}; allocation ownership cannot be verified; inspect {path.parent} and any "
                                 f"{branch_of(identity)} branch/worktree, remove only confirmed interrupted-allocation artifacts, then drain again")
        return state
    path, receipt = claims[0]
    require(isinstance(receipt, dict), f"receipt {path} is not an object")
    require(receipt.get("task") == identity and receipt.get("branch") == branch_of(identity) and path == receipt_path(common, identity)
            and path == path.resolve(),
            f"receipt {path} claims {identity} from branch {receipt.get('branch')!r}; conflicting ownership, inspect it")
    require(receipt.get("allocation") in ("owned", "allocating", "managed_pending", "managed_owned"),
            f"receipt {path}: missing or malformed allocation checkpoint")
    if receipt["allocation"] == "allocating":
        # Never adopted, and no executor ran: the task waits until the user removes what the allocation left.
        state["kind"] = "pending"
        state["invalid"] = (f"allocation did not finish ({path}); remove its worktree {receipt.get('worktree')} and branch "
                            f"{receipt['branch']} if present, delete {path.parent}, then drain again")
        return state
    require(all(isinstance(receipt.get(key), str) and receipt[key] and "\0" not in receipt[key] for key in
                ("id", "baseline", "worktree", "common_gitdir", "recovery_ref")), f"receipt {path}: malformed allocation fields")
    archived = path.parent.parent == common / 'devlyn-completion/retired'
    directory_id = receipt['id'] + '.' + receipt.get('storage', {}).get('request', {}).get('operation_id', '') if archived else receipt['id']
    require(not archived or receipt.get('storage', {}).get('removal_finished') and (
        receipt.get('status') == 'ABANDONED' or receipt.get('delivery') in {'COMPLETE', 'LOCAL_ONLY', 'FAILED', 'CLOSED'}),
        f'{path}: nonterminal retired receipt')
    require(receipt["common_gitdir"] == str(common) and directory_id == path.parent.name,
            f"receipt {path}: conflicting common Gitdir/id binding")
    recovery = "refs/devlyn/completed/" + receipt["id"]
    allowed = {recovery}
    if receipt['allocation'] in ('managed_pending', 'managed_owned'):
        allowed.add(recovery + '.' + receipt.get('storage', {}).get('request', {}).get('operation_id', ''))
    require(receipt["recovery_ref"] in allowed, f"receipt {path}: conflicting recovery ref ownership")
    for key in ("delivery", "product", "pr_url", "base", "remote"):
        require(key not in receipt or receipt[key] is None or isinstance(receipt[key], str), f"receipt {path}: malformed {key}")
    for key in ("acceptance", "queue", "merge", "workspace_cleanup", "scratch_cleanup"):
        require(key not in receipt or isinstance(receipt[key], dict), f"receipt {path}: malformed {key}")
    if receipt.get("merge"):
        merge = receipt["merge"].get("mergeCommit")
        require(isinstance(merge, dict) and isinstance(merge.get("oid"), str) and SHA_RE.fullmatch(merge["oid"]),
                f"receipt {path}: malformed merge binding")
    for key in ("workspace_cleanup", "scratch_cleanup"):
        if value := receipt.get(key):
            require(isinstance(value.get("status"), str) and (key != "workspace_cleanup" and not value.get("reason") or
                    isinstance(value.get("reason"), str) and isinstance(value.get("resume"), str)), f"receipt {path}: malformed {key}")
    require(not receipt.get("acceptance") or isinstance(receipt["acceptance"], dict)
            and all(isinstance(receipt.get(key), str) and SHA_RE.fullmatch(receipt[key]) for key in ("source_sha", "publish_sha"))
            and isinstance(receipt["acceptance"].get("inputs_sha"), str)
            and isinstance(receipt["acceptance"].get("reasons"), list)
            and all(isinstance(reason, str) for reason in receipt["acceptance"]["reasons"]), f"receipt {path}: malformed acceptance binding")
    require(not receipt.get("queue") or isinstance(receipt["queue"], dict)
            and all(isinstance(receipt["queue"].get(key), str) and "\0" not in receipt["queue"][key] for key in ("file", "commit")),
            f"receipt {path}: malformed terminal binding")
    if receipt.get("acceptance"):
        verdict = receipt["acceptance"].get("verdict")
        require(verdict in ("ACCEPTED", "FAILED"), f"receipt {path}: malformed acceptance verdict")
        require(receipt.get("product") is None or receipt["product"] == verdict,
                f"receipt {path}: inconsistent acceptance verdict/product")
        require(isinstance(receipt.get("files"), dict) and receipt["files"], f"receipt {path}: malformed bound files")
        for key in ("assumptions", "reasons"):
            value = receipt["acceptance"].get(key, [])
            require(isinstance(value, list) and all(isinstance(item, str) for item in value), f"receipt {path}: malformed acceptance {key}")
    result = None if not receipt.get("acceptance") else "failed" if receipt["acceptance"]["verdict"] == "FAILED" else "accepted"
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
        require(result != "failed" or receipt["acceptance"]["reasons"], f"receipt {path}: failed acceptance has no reason")
    packet = path.parent / "packet.json"
    if packet.exists():
        bound = read_json(packet)
        require(isinstance(bound, dict) and not acceptance()["PACKET_KEYS"] - bound.keys(), f"{packet}: malformed task packet")
        harness_call("packet_schema", bound)
        require(bound["worktree"] == receipt["worktree"] and bound["task"] == identity and bound["branch"] == receipt["branch"]
                and bound["allocation_base"] == receipt["baseline"],
                f"{packet}: conflicting packet ownership")
        original = common / 'devlyn-completion' / receipt['id'] / 'receipt.json' if archived else path
        for key, expected in (("receipt", original), ("scratch", original.parent / "scratch"), ("submission", original.parent / "submission.json"),
                              ("evidence_dir", Path(receipt["worktree"]) / ".devlyn/loop")):
            require(bound.get(key) == str(expected), f"{packet}: malformed or conflicting {key} path")
        require(isinstance(bound["inputs_sha"], str) and SHA_RE.fullmatch(bound["inputs_sha"]), f"{packet}: malformed inputs commit")
        require(bound.get("delivery") in ("local-only", "auto", "pr"), f"{packet}: malformed delivery")
        for key in ("requirements", "review_requirements"):
            require(isinstance(bound[key], list) and all(isinstance(item, str) for item in bound[key]), f"{packet}: malformed {key}")
        for key in ("contract", "expected", "meta"):
            entry = bound[key]
            require(isinstance(entry, dict) and isinstance(entry.get("path"), str) and isinstance(entry.get("sha256"), str)
                    and re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]), f"{packet}: malformed {key} binding")
            candidate = Path(entry["path"])
            require("\0" not in entry["path"] and candidate.is_absolute() and candidate.is_relative_to(Path(bound["worktree"]))
                    and ".." not in candidate.parts,
                    f"{packet}: {key} path escapes its worktree: {candidate}")
            rel = candidate.relative_to(bound["worktree"]).as_posix()
            current = package_bytes(anchor, rev, rel) if not result else None
            if not result and key != "meta" and (current is None or hashlib.sha256(current).hexdigest() != bound[key]["sha256"]):
                # Drain fails this task alone; the revision is planned as a new task.
                state["inputs_changed"] = f"inputs-changed: {rel} changed after its inputs were committed; plan the revision as a new task"
    state.update(kind=result or "active", path=path, receipt=receipt)
    return state


def view(anchor, common, local_only=False, *, pure=False):
    """Reconcile the queue with every receipt and recovery ref before anything is selected."""
    with contextlib.nullcontext() if pure else lock(common, "queue.lock", blocking=True):
        if not pure:
            enforce_binding(common)
        recorded = records(common)
        cleanup = [] if pure else clean(common, recorded)
        rows = queue_view(anchor, recorded)
    claims, unreadable, damaged = {}, [], {}
    canonical = {receipt_path(common, row["identity"]): row["identity"] for row in rows if row["identity"]}
    branches = {branch_of(identity): identity for identity in canonical.values()}
    for path in sorted([*(common / "devlyn-completion").glob("*/receipt.json"),
                        *(path for path in canonical if path.parent.parent.name == "retired")]):
        try:
            receipt = read_json(path)
            require(isinstance(receipt, dict), f"{path}: malformed receipt identity")
            task, branch = receipt.get("task"), receipt.get("branch")
            implicated = {task if isinstance(task, str) else None, canonical.get(path),
                          branches.get(branch) if isinstance(branch, str) else None} - {None}
            require(implicated, f"{path}: malformed receipt identity")
            for identity in implicated:
                claims.setdefault(identity, []).append((path, receipt))
        except (LoopError, OSError) as exc:
            unreadable.append(f"{path}: {exc}")
            if identity := canonical.get(path):
                damaged[identity] = str(exc)
    v = {"anchor": anchor, "common": common, "rows": rows, "records": recorded, "packages": {}, "manifests": {}, "states": {},
         "unreadable": unreadable, "cleanup": cleanup, "local_only": local_only, "pure": pure}
    errors = {}
    for row in v["rows"]:
        if row["identity"]:
            identity = row["identity"]
            try:
                require(identity not in damaged, damaged.get(identity))
                state = derive_state(anchor, common, row, claims.get(identity, []), capture(v, row["loop"]))
            except (LoopError, OSError) as exc:
                # No acceptance/frontier may be inferred from conflicting evidence. Its possible writer or carrier
                # still holds the loop barrier, even when no trustworthy receipt can be retained in the view.
                state = {"kind": "pending", "receipt": None, "path": None, "barrier": True,
                         "invalid": f"recovery conflict: {exc}; inspect and restore {identity}'s verified state, then drain again"}
            v["states"][identity] = state
            # A changed active task needs no current package text; a validation failure stops only its own task.
            if "invalid" not in state and (state["kind"] == "pending" or state["kind"] == "active" and "inputs_changed" not in state):
                loop = row["loop"]
                if loop not in v["packages"] and loop not in errors:
                    try:
                        v["packages"][loop] = load_package(anchor, loop, capture(v, loop))
                    except (LoopError, OSError) as exc:
                        errors[loop] = str(exc)
                package = v["packages"].get(loop)
                if problem := errors.get(loop) or package["invalid"].get(row["task"]) or (
                        None if row["task"] in package["tasks"] else f"{row['identity']} is not a task of loop {loop}"):
                    state["invalid"] = problem
    for row in v["rows"]:
        state = v["states"].get(row["identity"])
        for dep in v["packages"][row["loop"]]["tasks"][row["task"]]["depends_on"] if state and state["kind"] == "pending" and "invalid" not in state else []:
            dep_state = v["states"].get(f"{row['loop']}.{dep}")
            if dep_state is None:
                state["invalid"] = (f"{row['identity']} depends on {row['loop']}.{dep}, which is not queued; restore the authoritative "
                                    "queue from verified state or plan the continuation as a new loop, then drain again")
                break
            if dep_state["kind"] in {"failed", "blocked"}:
                state.update(kind="blocked", blocker=f"{row['loop']}.{dep}", root=dep_state.get("root") or dep_state)
                break
    v["invalid_receipts"] = {path for identity, state in v["states"].items() if "invalid" in state
                             for path in (receipt_path(common, identity), *(path for path, _ in claims.get(identity, [])))}
    return v


def capture(v, loop):
    """The commit holding the loop's captured package, or None for a loop with no record (its checkout's files)."""
    return v["records"][loop]["commit"] if loop in v["records"] else None


def published(v, loop):
    """Why --local-only leaves an auto/pr loop to a normal drain: a task of it already has a pushed PR (loop.md, Commands)."""
    for identity, state in v["states"].items():
        if identity.split(".")[0] == loop and state["receipt"] and state["receipt"].get("pushed"):
            url = state["receipt"].get("pr_url") or state["receipt"]["branch"]
            return f"{identity} already has a pushed PR {url}, so --local-only never runs loop {loop}; drain without --local-only"
    return None


def is_local(v, loop):
    added, package = v["records"].get(loop), v["packages"].get(loop)
    delivery = added["delivery"] if added else package and package["manifest"]["delivery"]
    return (v["local_only"] and not published(v, loop) or delivery == "local-only"
            or any(s["receipt"] and s["receipt"].get("local_only") for i, s in v["states"].items() if i.split(".")[0] == loop))


def delivered(receipt):
    return receipt.get("delivery") == "COMPLETE" or bool(receipt.get("merge"))


def carrier(v, loop):
    """The auto/pr task whose undelivered, unfailed PR carries the loop's package, which its base lacked (loop.md step 2)."""
    return None if is_local(v, loop) else next((
        row["identity"] for row in v["rows"] if row.get("loop") == loop and (state := v["states"][row["identity"]])["receipt"]
        and state["kind"] != "failed" and not delivered(state["receipt"]) and show(v["anchor"], state["receipt"]["baseline"], loop_queue(loop)) is None), None)


def waiting(v, row):
    # Eligibility precedes selection, so its task-local reads cannot reach advance's exception boundary.
    try:
        return wait_reason(v, row)
    except (LoopError, OSError) as exc:
        return f"allocation blocked: {exc}; inspect and repair {row['identity']}'s starting state, then drain again"


def wait_reason(v, row):
    if invalid := v["states"][row["identity"]].get("invalid"):
        return invalid
    if barrier := recovery_barrier(v, row):
        return barrier
    local = is_local(v, row["loop"])
    if v["local_only"] and not local:
        return published(v, row["loop"])
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


def recovery_barrier(v, row):
    return next((f"waiting for {identity} (recovery conflict), since its possible writer or package carrier holds this loop"
                 for identity, state in v["states"].items() if identity != row["identity"]
                 and identity.split(".")[0] == row["loop"] and state.get("barrier")), None)


def next_task(v, attempted):
    """Earliest unsettled receipt first, then the earliest eligible pending row in physical order."""
    for row in v["rows"]:
        state = v["states"].get(row["identity"])
        if state and state["receipt"] and row["identity"] not in attempted and "invalid" not in state and not recovery_barrier(v, row) and (
                state["kind"] == "active" or not state["receipt"].get("queue") or state["receipt"].get("delivery") not in SETTLED):
            return row
    return next((row for row in v["rows"] if row["identity"] not in attempted and v["states"].get(row["identity"], {}).get("kind") == "pending"
                 and waiting(v, row) is None), None)


def annotate(v, refused):
    """Name each task's wait: a pending task's reason from waiting(), else why this drain did not advance it, else what an
    active task's executor left."""
    for row in v["rows"]:
        state = v["states"].get(row["identity"])
        if state and (reason := refused.get(row["identity"]) or state["kind"] == "pending" and waiting(v, row)
                     or recovery_barrier(v, row) or executor_left_nothing(state)):
            state["waiting"] = reason


def executor_left_nothing(state):
    """What an active task's executor left when its execution log ends in a start that failed, or in an exit while no
    submission is in place and the drain retired none that run wrote; nothing for a start, which may still be running."""
    if state["kind"] != "active" or {"invalid", "inputs_changed"} & state.keys() or (state["path"].parent / "submission.json").exists():
        return None
    folder = state["path"].parent
    try:
        events = [line.partition(" ")[::2] for line in (folder / "executions.log").read_bytes().decode("utf-8").splitlines()]
        last = events[-1][1] if events else ""
        code, starts = re.fullmatch(r"exit (-?\d+) \(pid \d+\)", last), [when for when, event in events if event == "start"]
        # A retired submission covers the one run that wrote it, after that run's start.
        if code and starts and any(path.stat().st_mtime >= datetime.datetime.fromisoformat(starts[-1]).timestamp()
                                   for path in folder.glob("submission.retired-*.json")):
            return None
    except (OSError, UnicodeError, ValueError):
        return None  # Nothing ran yet, or a history the drain refuses, naming it, when it reads it.
    if code:
        return (f"its executor last exited {code[1]} (run {sum(event.startswith('exit ') for _, event in events)}) and left nothing to "
                f"accept (output: {Path(state['receipt']['worktree']) / '.devlyn/loop'})")
    if last.startswith("not started: "):
        return f"its executor could not start ({last.removeprefix('not started: ')})"
    return None


def frontier(v, loop):
    """The loop's accepted task whose source contains every other accepted source. A local loop builds one history, though
    not always in row order: a task whose unfinished allocation was removed starts again from a later row's source. Without
    one, as after a fork by an older build, it is the last accepted row, and allocate's prerequisite check names the fork."""
    accepted = [v["states"][row["identity"]] for row in v["rows"] if row.get("loop") == loop
                and v["states"][row["identity"]]["kind"] == "accepted" and v["states"][row["identity"]]["receipt"]]
    return next((tip for tip in reversed(accepted) if all(ancestor(v["anchor"], state["receipt"]["source_sha"], tip["receipt"]["source_sha"])
                                                          for state in accepted)), accepted[-1] if accepted else None)


def local_start(v, loop):
    """The commit a local loop's next task starts from, and why it waits instead (loop.md steps 2-3): none while a task of
    the loop is active, so no two tasks start from one frontier; else its latest accepted source; else the start its
    first allocation fixed, kept in that receipt; else the HEAD of the branch it was added on, which must descend from
    the manifest base_sha."""
    if active := next((identity for identity, state in v["states"].items() if identity.split(".")[0] == loop and state["kind"] == "active"), None):
        return None, f"waiting for {active} (active), since a local loop runs one task at a time"
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
        if drift := package_drift(v, loop, start, branch):
            return start, drift
    if drift := instruction_drift(v["anchor"], start, pure=v.get("pure", False)):
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


def require_merged(v, row, base, *, allocated=False):
    """auto/pr: every prerequisite's delivered commit must be in the base, before allocation and before every execution."""
    for dep in v["packages"][row["loop"]]["tasks"][row["task"]]["depends_on"]:
        receipt = v["states"][f"{row['loop']}.{dep}"]["receipt"] or {}
        merge = ((receipt.get("merge") or {}).get("mergeCommit") or {}).get("oid")
        kind = "merge"
        if not receipt.get("merge") and receipt.get("delivery") == "COMPLETE":
            merge = receipt.get("publish_sha")
            kind = "commit"
        remedy = ("retain this allocation and plan the continuation as a new loop, or perform verified recovery of a never-executed allocation"
                  if allocated else f"restore that {kind} on origin/{manifest_of(v, row['loop'])['base_ref']}, then drain again")
        require(merge and ancestor(v["anchor"], merge, base),
                f"{row['identity']}: {'allocated baseline' if allocated else 'base'} {base} lacks prerequisite {row['loop']}.{dep}'s "
                f"delivered {kind} {merge}; {remedy}")


def package_drift(v, loop, start, where):
    """Why a task of a recorded loop cannot start at `start` (loop.md step 3): it holds the loop's queue file, so the task
    would bind its copy of the package, and that copy differs from the capture."""
    added = v["records"].get(loop)
    if added is None or show(v["anchor"], start, loop_queue(loop)) is None:
        return None
    files = [rel for rel in git(v["anchor"], "diff", "--name-only", "--no-renames", "--diff-filter=DMT", added["commit"], start, "--",
                                f"docs/specs/{loop}").splitlines() if rel != loop_queue(loop)]
    return (f"{where} holds another version of loop {loop}'s package (differing from {CAPTURES}{loop}: {', '.join(files)}), so its tasks "
            f"cannot run their captured contracts there; plan the work as a new loop, or restore those files on {where} to the captured "
            "bytes") if files else None


def instruction_drift(anchor, rev, *, pure=False):
    """The installed instruction files whose content at `rev` differs from the anchor checkout's (both absent is equal): a
    task starting at `rev` would run without them. Git compares them as `git status` does: a link by its target, line endings
    under the checkout's conversion rules, and an untracked or ignored file as one still to commit."""
    names = ("CLAUDE.md", "AGENTS.md")
    # Git's porcelain diff refreshes the index independently of GIT_OPTIONAL_LOCKS.
    options = ("-c", "diff.autoRefreshIndex=false") if pure else ()
    differ = git(anchor, *options, "diff", "--name-only", "--no-renames", rev, "--", *names).split("\n")
    differ += git(anchor, "ls-files", "--others", "--", *names).split("\n")
    return ", ".join(name for name in names if name in differ)


def allocate(v, row, opts):
    """Allocate the task's owned worktree, or return why it waits: origin names no GitHub repository, its base is not the
    default, or its refreshed remote base holds another version of the loop's package or lacks the checkout's instructions
    (waiting() checks a local start before selection)."""
    identity, loop, task = row["identity"], row["loop"], row["task"]
    package = v["packages"][loop]
    manifest = package["manifest"]
    anchor, common = v["anchor"], v["common"]
    deps = [v["states"][f"{loop}.{dep}"] for dep in package["tasks"][task]["depends_on"]]
    values = {"repo": str(anchor), "task": identity, "branch": branch_of(identity), "repository": None,
              "base": manifest["base_ref"], "remote": "origin", "worktree": str(opts.worktree_root / loop / task),
              "local_base": None, "from_receipt": None, "start": None,
              "keep_root": str(opts.keep_root) if opts.keep_root else None}
    if is_local(v, loop):
        tip, start = frontier(v, loop), local_start(v, loop)[0]
        for dep in deps:
            require(ancestor(anchor, dep["receipt"]["source_sha"], start),
                    f"{identity}: prerequisite source {dep['receipt']['source_sha']} is not in the accepted frontier {start}; plan an integration task")
        values["from_receipt" if tip else "local_base"] = str(tip["path"]) if tip else start
    else:
        helper = shared("task-complete")
        origin = git_run(anchor, "config", "--get", "remote.origin.url", ok=(0, 1)).stdout.decode("utf-8").strip()
        try:
            values["repository"] = helper["repository_from_url"](origin)
        except helper["CompletionError"]:
            return (f"{manifest['delivery']} delivery needs an origin remote of the form https://github.com/<owner>/<repo>, "
                    "git@github.com:<owner>/<repo> or ssh://git@github.com/<owner>/<repo>; set one, or drain with --local-only")
        try:
            default = helper["repository_info"](values["repository"])["defaultBranchRef"]["name"]
        except (helper["CompletionError"], OSError, KeyError, TypeError, ValueError) as exc:
            return f"cannot check delivery repository: {exc}"
        if manifest["base_ref"] != default:
            return (f"{manifest['delivery']} delivery base {manifest['base_ref']} is not the repository's default branch {default}; "
                    f"plan the loop on {default}, or drain with --local-only")
        try:
            start = helper["remote_base"]({"common_gitdir": str(common), "remote": "origin", "base": manifest["base_ref"]})
        except (helper["CompletionError"], OSError) as exc:
            raise LoopError(f"cannot refresh origin/{manifest['base_ref']}: {exc}; restore remote access or the base ref, "
                            "then drain again; the next drain retries") from exc
        values["start"] = start
        require_merged(v, row, start)
        if drift := package_drift(v, loop, start, f"origin/{manifest['base_ref']}"):
            return drift
    if values["start"] and (drift := instruction_drift(anchor, start)):
        return (f"the installed instructions ({drift}) in this checkout differ from those in its start commit {start}, so it would run "
                f"without them; commit them and push them to origin/{manifest['base_ref']}")
    result = task_complete("allocate", exclude_receipts=v["invalid_receipts"], warnings=opts.warnings, **values)
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
        "schema_version": 2, "task": identity, "title": spec["title"], "kind": spec["kind"],
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
    instructions = packet["methodology"]
    binding = harness_call("read_binding", v["common"])
    if binding:
        defaults = {"source": "release", **binding["defaults"]}
    else:
        # An unbound queue's executor still gets the principles: the invoking skill's own copy.
        own = SKILLS / "_shared/runtime-principles.md"
        defaults = {"source": "skill", **harness_call("file_identity", own)} if own.is_file() else None
    if defaults is None and not instructions:
        raise Waiting(f"{identity}: no principles reach its executor — neither CLAUDE.md/AGENTS.md at the inputs commit nor "
                      f"{SKILLS / '_shared/runtime-principles.md'}; reinstall devlyn-cli to restore that file, then drain again")
    packet.update(harness=binding["release"] if binding else None,
                  methodology={"defaults": defaults, "projectInstructions": instructions}, workerPrompt=None)
    if binding:
        harness_call("check_binding", binding, harness_call("resolve", SKILLS))
        bound_skills = Path(binding["release"]["root"]) / "config/skills"
        packet["runner"][1] = str(bound_skills / "devlyn-ideate/scripts/acceptance.py")
        prompt = path.parent / "worker-prompt.md"
        body = (f"Execute task packet {packet_path}: you were started to implement it, so you are its executor. "
                f"Work only in {worktree} on its owned branch.\n"
                f"Read {binding['defaults']['path']} and apply it as defaults; explicit user and native owner/project instructions win, except a Devlyn managed block (devlyn:instructions markers), which these defaults replace.\n"
                f"Set DEVLYN_SKILL_DIR={bound_skills / 'devlyn-ideate'} and DEVLYN_SHARED_DIR={bound_skills / '_shared'}.\n"
                f"Follow {bound_skills / 'devlyn-ideate/references/executor.md'}: meet the packet obligations and write "
                f"{packet['submission']} as it says. Never push, open a pull request or merge.\n")
        acceptance()["atomic_write"](prompt, body.encode("utf-8"))
        packet["workerPrompt"] = harness_call("file_identity", prompt)
    write_json(packet_path, packet)
    return packet_path, packet


def record(log, event):
    """Append one execution event durably, before the drain acts on it."""
    with log.open("a", encoding="utf-8") as stream:
        stream.write(f"{datetime.datetime.now(datetime.timezone.utc).isoformat()} {event}\n")
        stream.flush()
        os.fsync(stream.fileno())


def ensure_submission(identity, packet_path, packet, executor, checkout=None):
    """Run the executor once unless its submission exists; returns a drain-recorded failure reason, else None. An
    executor that exits without writing its submission raises Waiting: the task stays active and the next drain runs it
    again.

    An attempt's start is recorded before the spawn and its exit after the wait, so a start without an exit may have
    left a live executor: drain observes once and waits if it is active. Only established cessation permits adoption
    or another execution. Where writers cannot be observed the task fails as interrupted-unobservable. A submission
    blocked only by infrastructure is retired once its writers are observed to have stopped, and the task waits to run
    again; where they cannot be observed, it fails the task with its blocker."""
    harness_call("verify_packet", packet, packet_path, SKILLS)
    submission = Path(packet["submission"])
    worktree = Path(packet["worktree"])
    log = submission.with_name("executions.log")
    try:
        events = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    except UnicodeDecodeError as exc:
        raise LoopError(f"{log} is not UTF-8: {exc}; restore the execution history before draining again") from exc
    if events and events[-1].partition(" ")[2] == "start":
        helper = shared("task-complete")
        try:
            helper["stopped_writers"](worktree)
        except helper["WritersUnobservable"] as exc:
            return f"interrupted-unobservable: an interrupted executor may still be writing ({exc})"
        except helper["WriterActive"] as exc:
            raise Waiting(f"interrupted execution still active: {exc}; wait for or stop the named writer, then drain again") from exc
        except (helper["CompletionError"], OSError) as exc:
            raise LoopError(f"cannot establish that an interrupted execution stopped: {exc}; repair writer observation, then drain again") from exc
    if submission.exists():
        return retire_retryable(packet, submission)
    defaults = packet["methodology"].get("defaults") if packet.get("schema_version") == 2 else None
    if packet.get("harness") is None and defaults and not Path(defaults["path"]).is_file():
        # An installation's own copy moves with its updates; only its absence matters, and only before a spawn.
        raise Waiting(f"{identity}: its principles file {defaults['path']} is gone; reinstall devlyn-cli to restore it, then drain again")
    argv = [part.replace("{packet}", str(packet_path)) for part in executor]
    if any("{worktree_git_dir}" in part for part in argv):  # Optional: a Codex executor lists it as a writable root.
        git_dir = git(worktree, "rev-parse", "--path-format=absolute", "--git-dir")
        argv = [part.replace("{worktree_git_dir}", git_dir) for part in argv]
    output = Path(packet["evidence_dir"])
    output.mkdir(parents=True, exist_ok=True)
    record(log, "start")
    with contextlib.ExitStack() as stack:
        try:
            env = None
            claude_names = {"claude", "claude.exe", "claude.cmd", "claude.bat"}
            if Path(argv[0]).name.lower() in claude_names:
                argv, env = stack.enter_context(shared("unattended-tools")["claude_launch"](argv, worktree))
            else:
                paths = [Path(part.replace("\\", "/")) for part in argv]
                node_wrapper = any(path.name.lower() in {"node", "node.exe"} for path in paths)
                for part, path in zip(argv, paths):
                    if path.name.lower() in claude_names or (path.name.lower() == "cli.js" and
                            (node_wrapper or any("claude" in parent.lower() for parent in path.parts[:-1]))):
                        raise ValueError(f"unattended tools: wrapped Claude or ambiguous Node CLI executor {argv[0]!r} via {part!r} is unsupported; "
                                         "invoke claude directly as argv[0]")
            # Files, never a pipe: a wrapper such as codex-monitored.sh refuses a piped stdout; stdin is empty, never the driver's.
            with (output / "executor.stdout").open("ab") as stdout, (output / "executor.stderr").open("ab") as stderr:
                if checkout is not None:
                    # Who builds and who reviews is pinned for the checkout this drain runs in; the task's own
                    # worktree holds no pin. Written beside the packet at every start, as a later drain may run in
                    # another checkout, and never into a prompt: a prompt is kept, and its placeholders are filled in.
                    acceptance()["atomic_write"](Path(packet_path).with_name("drain-checkout"), str(checkout).encode("utf-8"))
                child = subprocess.Popen(shared("platform-support")["native_argv"](argv, cwd=worktree), cwd=worktree, stdin=subprocess.DEVNULL,
                                         stdout=stdout, stderr=stderr, env=env)
        except (OSError, ValueError) as exc:
            record(log, f"not started: {one_line(str(exc))}")
            raise LoopError(f"executor could not start: {exc}; restore the configured executable, permissions or task workspace; "
                            "the next drain retries") from exc
        progress(identity, f"executing; output in {output}")
        code = child.wait()
    record(log, f"exit {code} (pid {child.pid})")
    if not submission.exists():
        raise Waiting(f"executor exited {code} without a submission (see executor.stdout and executor.stderr in {output}); "
                      "the next drain runs it again")
    return retire_retryable(packet, submission)


def retire_retryable(packet, submission):
    """Adopt a stopped executor's submission, unless only infrastructure blocks it (a kind earlier instructions offered):
    once its writers are observed to have stopped, that one is kept under a retired name, so no later drain adopts it,
    and the task waits for the next drain. While a writer is active it waits in place."""
    if acceptance()["infrastructure_causes"](packet, submission) is None:
        return None
    helper = shared("task-complete")
    try:
        helper["stopped_writers"](Path(packet["worktree"]))
    except helper["WriterActive"] as exc:
        raise Waiting(f"executor reported a cause a later run can clear, but a writer is still active: {exc}; wait for or "
                      "stop the named writer (an editor or shell open in the task worktree counts), then drain again") from exc
    except (helper["CompletionError"], OSError):
        return None  # Unobservable: another run could start beside a live writer, so the blocker fails the task.
    causes = acceptance()["infrastructure_causes"](packet, submission)  # As it stands now: a writer may have replaced it.
    if causes is None:
        return None
    retired = next(path for number in itertools.count(1)
                   if not (path := submission.with_name(f"submission.retired-{number}.json")).exists())
    submission.rename(retired)
    raise Waiting(f"executor reported a cause a later run can clear: {'; '.join(map(one_line, causes))} (see {retired}); "
                  "the next drain runs it again")


def terminal_queue(cwd, receipt, identity):
    """The loop queue file of this bound result's only legal terminal transition: its row becomes [x] or [F] — <reason>."""
    failed = receipt["acceptance"]["verdict"] == "FAILED"
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
    failed = receipt["acceptance"]["verdict"] == "FAILED"
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
    state = v["states"][identity]
    state["phase"] = "allocation"
    path = receipt_path(v["common"], identity)
    local = is_local(v, row["loop"])
    if opts.local_only and not local:
        return published(v, row["loop"])
    if not path.exists() and (refused := allocate(v, row, opts)):
        return refused
    receipt = read_json(path)
    if receipt.get('status') == 'ABANDONED':
        if refused := allocate(v, row, opts):
            return refused
        path = receipt_path(v['common'], identity)
        receipt = read_json(path)
    accepted = receipt.get('acceptance') or receipt.get('pushed') or receipt.get('pr_number')
    if receipt.get('allocation') in ('managed_pending', 'managed_owned') and not accepted:
        require('removal_request' not in receipt.get('storage', {}),
                'allocation fenced; run ' + shared('task-complete')['receipt_resume'](
                    'recover-storage', path, receipt, flags=['--for-removal']))
    if receipt.get('allocation') == 'managed_pending' and not accepted:
        task_complete('recover_storage', receipt=str(path), for_removal=False,
                      operation_id=receipt.get('storage', {}).get('request', {}).get('operation_id'))
        receipt = read_json(path)
    if receipt.get("acceptance") and (path.parent / "packet.json").exists():
        harness_call("verify_packet", read_json(path.parent / "packet.json"), path.parent / "packet.json", SKILLS, accepted_receipt=receipt)
    if not receipt.get("acceptance"):
        state["phase"] = "inputs"
        failure = v["states"][identity].get("inputs_changed")
        if not failure and not receipt.get("local_only"):
            require_merged(v, row, receipt["baseline"], allocated=True)
        packet_path, packet = ensure_packet(v, row, path, receipt)
        state["phase"] = "executor"
        failure = failure or ensure_submission(identity, packet_path, packet, opts.executor, checkout=v["anchor"])
        state["phase"] = "acceptance"
        try:
            result = acceptance()["accept"](packet_path, packet["submission"], failure)
        except acceptance()["AcceptanceError"] as exc:
            raise LoopError(f"{identity}: acceptance could not run: {exc}") from exc
        progress(identity, result["verdict"].lower() + "".join(f"; {reason}" for reason in result["reasons"][:3]))
        state["phase"] = "custody binding"
        task_complete("accept", receipt=str(path), acceptance=str(Path(packet["worktree"]) / ".devlyn/loop/acceptance.json"))
        progress(identity, "bound")
    state["phase"] = "terminal transition"
    if not read_json(path).get("queue"):
        settle(v, row, path)
    receipt = read_json(path)
    state["phase"] = "delivery"
    if receipt.get("delivery") not in SETTLED:
        packet = read_json(path.parent / "packet.json")
        # The plan's mode seeds the first delivery call; a later per-task --mode persists in the receipt.
        result = task_complete("complete", warnings=opts.warnings, receipt=str(path), acceptance=None,
                               operation_id=receipt.get("storage", {}).get("request", {}).get("operation_id"),
                               mode=None if local or receipt.get("mode_override") else packet["delivery"], local_only=local, writers_stopped=True)
        progress(identity, f"delivery {result['status']}")
        if result.get("merge_refused"):
            return f"merge refused: {result['merge_refused']}; a person merges the PR"
        if waits := result.get("merge_waits"):
            return f"merge waits: PR is {waits} ({'GitHub has not computed its mergeability yet' if waits == 'UNKNOWN' else 'required checks or reviews not passing yet'}); drain again later, or merge it"
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
        branch, worktree, resume = None, None, None
        try:
            worktree = receipt["worktree"] if receipt.get("worktree") and Path(receipt["worktree"]).exists() else None
            if receipt.get("branch") and ref_value(v["anchor"], "refs/heads/" + receipt["branch"]):
                branch = receipt["branch"]
            if receipt.get("acceptance") and receipt.get("delivery") not in SETTLED:
                if receipt.get("queue"):
                    binding = harness_call("read_binding", v["common"])
                    skills = Path(binding["release"]["root"]) / "config/skills" if binding else SKILLS
                    argv = [sys.executable, str(skills / "_shared/task-complete.py"), "complete", "--receipt", str(state["path"])]
                    if operation := receipt.get("storage", {}).get("request", {}).get("operation_id"):
                        argv += ["--operation-id", operation]
                    if receipt.get("writers_released"):
                        argv.append("--writers-stopped")
                    if not receipt.get("local_only") and not receipt.get("mode_override"):
                        argv += ["--mode", read_json(state["path"].parent / "packet.json")["delivery"]]
                    resume = shlex.join(argv)
                else:
                    resume = "drain again: the terminal commit is not attached yet"
        except (LoopError, OSError) as exc:
            diagnostic = (f"task summary unavailable: {row['identity']} worktree {receipt.get('worktree')}, "
                          f"branch {receipt.get('branch')}: {exc}; repair access and drain again")
            if diagnostic not in v["cleanup"]:
                v["cleanup"].append(diagnostic)
        item.update(allocation_base=receipt.get("baseline"), **{"source" if state["kind"] == "accepted" else "candidate": receipt.get("source_sha")},
                    terminal=(receipt.get("queue") or {}).get("commit"), delivery=receipt.get("delivery"), pr=receipt.get("pr_url"),
                    resume=resume,
                    assumptions=acceptance_record.get("assumptions", []),
                    questions=[r.removeprefix("needs-review: ") for r in acceptance_record.get("reasons", []) if r.startswith("needs-review: ")],
                    worktree=worktree,
                    cleanup=f"{c['status']} — {c['reason']}; resume: {c['resume']}" if (c := receipt.get("workspace_cleanup")) else None,
                    branch=branch,
                    recovery_ref=receipt.get("recovery_ref"),
                    custody=str(Path(state["path"]).parent / "custody") if receipt.get("files") else None,
                    scratch=(f"{c['status']} — {c['reason']}; resume: {c['resume']}" if (c := receipt.get("scratch_cleanup") or {}).get("reason")
                             else c.get("status", "NOT_CLEANED")))
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
        if loop not in v["records"]:
            return None
        branch, target = v["records"][loop]["branch"], receipt["branch"]
    else:
        if not delivered(receipt):
            return None
        branch, target = receipt["base"], f"{receipt['remote']}/{receipt['base']}"
    # Prepare any merge without touching the anchor, then land by protected fast-forward.
    # Several loops still apply in either order, including after merge, squash or rebase delivery.
    command = shlex.join(["python3", str(SKILLS / "_shared" / "bring-in.py"), "--repo", str(v["anchor"]),
                          "--branch", branch, "--target", target])
    return f"{branch}: {command}"


def write_reports(v, status, reason, warnings):
    paths = []
    for loop in dict.fromkeys(row["loop"] for row in v["rows"] if row["identity"]):
        path = v["common"] / "devlyn-loops" / loop / "drain-report.md"
        try:
            items = [summary(v, row) for row in v["rows"] if row.get("loop") == loop]
            lines = [f"# Drain report — {loop}", "", f"- Generated: {datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')}",
                     f"- Queue: {f'{CAPTURES}{loop}:{loop_queue(loop)}' if loop in v['records'] else v['anchor'] / loop_queue(loop)}",
                     f"- Drain: {status}" + (f" — {reason}" if reason else ""), f"- Whole-loop acceptance: {loop_acceptance(v, loop, items)}",
                     *([f"- Bring into {line}"] if (line := bring_in(v, loop)) else []), ""]
            if warnings:
                lines += ["## Warnings", "", *(f"- {warning}" for warning in warnings), ""]
            try:
                meta, _ = load_manifest(v["anchor"], loop, capture(v, loop))
                decisions = sections(
                    JSON_FENCE_RE.sub("", meta),
                    v["anchor"] / f"docs/specs/{loop}/meta.md",
                )["Decisions and assumptions"] or "None recorded."
            except (LoopError, OSError) as exc:
                decisions = f"Unavailable: {exc}"
            lines += ["## Package decisions and assumptions", "", decisions, ""]
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
            acceptance()["atomic_write"](path, "\n".join(lines).encode("utf-8"))
            paths.append(str(path))
        except (LoopError, OSError) as exc:
            v["cleanup"].append(f"report unavailable: {path}: {exc}; repair access and drain again")
    return paths


def counts(v):
    kinds = [state["kind"] for state in v["states"].values()]
    return {kind: kinds.count(kind) for kind in ("pending", "active", "accepted", "failed", "blocked")} | {
        "legacy_pending": sum(1 for row in v["rows"] if not row["identity"] and row["mark"] == " ")}


def prune_parents(v, root):
    """Retry empty-parent cleanup for completed, verified receipts; the drain alone knows this boundary."""
    for identity, state in v["states"].items():
        receipt = state["receipt"]
        if not receipt or receipt.get("delivery") != "COMPLETE" or not receipt.get("linked"):
            continue
        work = Path(receipt["worktree"])
        expected = root.joinpath(*identity.split("."))
        if work != expected:
            continue
        parent = work.parent
        helper = shared("task-complete")
        try:
            if work.exists():
                continue
            require(work == helper["resolve_for_pruning"](work) and not work.is_symlink() and not parent.is_symlink(),
                    f"symlink or escape at {work}")
            retained = helper["prune_empty_parents"](receipt, parent, root)
            require(retained is None, retained)
        except (LoopError, OSError, helper["CompletionError"]) as exc:
            v["cleanup"].append(f"parent cleanup retained: {parent}: {exc}; remove it when empty or drain again")


def drain(args):
    anchor, common = repository(args.repo)
    args.repo = anchor  # Preserve the repository root for failures reported by main.
    enforce_binding(common, anchor)
    diagnostics = skill_diagnostics(anchor)
    require(any("{packet}" in part for part in args.executor), "executor argv must contain {packet}, replaced by the task packet path")
    args.warnings = diagnostics["warnings"]
    args.keep_root = Path(args.worktree_root).resolve() if args.worktree_root else None
    args.worktree_root = args.keep_root or anchor.parent / ".devlyn-worktrees" / anchor.name
    with lock(common, "drain.lock", blocking=False):
        attempted, last, status, reason, refused = set(), None, "DRAINED", None, {}
        try:
            while True:
                last = view(anchor, common, args.local_only)
                row = next_task(last, attempted)
                if row is None:
                    break
                attempted.add(row["identity"])
                try:
                    wait = advance(last, row, args)
                except Waiting as exc:
                    wait = str(exc)
                except (LoopError, OSError) as exc:
                    phase = last["states"][row["identity"]].get("phase", "allocation")
                    wait = f"{phase} blocked: {exc}"
                    disk_blocked = phase == "allocation" and str(exc).startswith("task-complete allocate: BLOCKED:disk")
                    if disk_blocked:
                        status, reason = "BLOCKED", str(exc)
                    if not disk_blocked and phase in {"allocation", "inputs", "acceptance", "custody binding", "terminal transition"}:
                        wait += f"; inspect and repair {row['identity']}'s {phase} state, then drain again"
                if wait:
                    refused[row["identity"]] = wait
                    if status == "BLOCKED":
                        break
            if status == "BLOCKED" and reason and reason.startswith("task-complete allocate: BLOCKED:disk"):
                last = view(anchor, common, args.local_only)
            if status != "BLOCKED" and (any(state["kind"] in {"pending", "active"} for state in last["states"].values()) or counts(last)["legacy_pending"] or refused):
                status = "WAITING"
        except (LoopError, OSError) as exc:
            status, reason = "BLOCKED", str(exc)
            with contextlib.suppress(LoopError, OSError):
                last = view(anchor, common, args.local_only)
        if last is None:
            return {"status": status, "reason": reason, **diagnostics}
        annotate(last, refused)
        prune_parents(last, args.worktree_root)
        try:
            release_settled_binding(anchor, common)
        except (LoopError, OSError) as exc:
            last["cleanup"].append(f"queue binding not released: {exc}; the next status or drain retries")
        return {"status": status, "reason": reason, **diagnostics,
                "reports": write_reports(last, status, reason, diagnostics["warnings"]), "counts": counts(last),
                "tasks": [summary(last, row) for row in last["rows"] if row["identity"]], "cleanup": last["cleanup"]}


def status_summary(v):
    anchor = v["anchor"]
    row = next_task(v, set())
    annotate(v, {})
    tasks = [summary(v, r) for r in v["rows"] if r["identity"]]
    # A task without a resume is no pending delivery, so a cleanup it retained is named here with its own resume.
    retained = [f"{t['identity']}: {label} {t[key]}" for t in tasks if not t.get("resume")
                for key, field, label in (("cleanup", "workspace_cleanup", "workspace cleanup"), ("scratch", "scratch_cleanup", "scratch cleanup"))
                if ((v["states"][t["identity"]]["receipt"] or {}).get(field) or {}).get("reason")]
    return {"status": "OK", **skill_diagnostics(anchor), "counts": counts(v), "next": row["identity"] if row else None,
            "blockers": [f"{t['identity']}: {t['reason']}" for t in tasks if t.get("reason") and t["result"] in {"pending", "active", "blocked"}]
            + [f"legacy row {r['index'] + 1} needs planning: {r['text']}" for r in v["rows"] if not r["identity"] and r["mark"] == " "]
            + [f"unreadable receipt {item}" for item in v["unreadable"]],
            "delivery": [t for t in tasks if t.get("resume")], "cleanup": v["cleanup"] + retained}


def status(args):
    anchor, common = repository(args.repo)
    args.repo = anchor
    enforce_binding(common, anchor)
    result = status_summary(view(anchor, common, args.local_only))
    release_settled_binding(anchor, common)
    return result


def inspect(args):
    anchor, common = repository(args.repo)
    try:
        result = status_summary(view(anchor, common, pure=True))
    except (LoopError, OSError) as exc:
        result = {"status": "BLOCKED", "reason": str(exc), **skill_diagnostics(anchor)}
    binding_path = common / "devlyn-loops/harness.json"
    binding = None
    compatibility = {"compatible": True, "legacy": not (binding_path.exists() or binding_path.is_symlink()), "reasons": [], "recoveryArgv": None,
                     "taskPacket": {"inspect": [1, 2], "execute": [1, 2], "write": 2}, "queueBinding": {"read": [1, 1], "write": 1}}
    try:
        binding = read_json(binding_path) if not compatibility["legacy"] else None
        enforce_binding(common)
        for packet in (common / "devlyn-completion").glob("*/packet.json"):
            harness_call("packet_schema", read_json(packet))
    except (LoopError, OSError) as exc:
        compatibility.update(compatible=False, reasons=[str(exc)])
        try:
            valid = harness_call("read_binding", common)
            if hasattr(exc, "handoff"):
                line = exc.handoff
            else:
                line = shared("storage-client")["queue_handoff"](common, valid) if valid else None
            if valid and line is None:
                compatibility["recoveryArgv"] = harness_call("recovery_argv", valid, ["inspect", "--repo", str(anchor), "--json"])
        except (LoopError, OSError):
            pass  # The diagnostic above describes the malformed binding; no safe argv can be inferred.
    return {**result, "binding": binding, "compatibility": compatibility}


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
    enforce_binding(common, anchor)
    with lock(common, "queue.lock", blocking=True):
        enforce_binding(common)
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
        # The lock covers both first binding and first capture; an interrupted binding is authoritative on retry.
        if harness_call("read_binding", common) is None:
            invoking = harness_call("resolve", SKILLS)
            if invoking is not None and bindable(anchor, common):
                write_json(common / "devlyn-loops/harness.json", invoking)
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


def registered_worktree(admin):
    """A linked worktree as Git lists it: the folder whose .git the gitdir file of its administrative directory
    <common>/worktrees/<id> names, as an absolute path or one relative to that directory; while that file cannot be read
    or decoded, the directory itself."""
    try:
        gitdir = (admin / "gitdir").read_bytes().decode("utf-8").rstrip()
    except (OSError, UnicodeError):
        gitdir = ""
    if not gitdir:
        return f"the worktree registered at {admin}"
    folder = gitdir.removesuffix("/.git")
    return folder if os.path.isabs(folder) else os.path.realpath(admin / folder)


def tracked_places(anchor, common, rel):
    """Where this repository tracks `rel`: the HEAD of each registered worktree, each local branch none has checked out,
    and the index of each registered worktree, read through its administrative directory, so also while its folder is
    missing, with a pathspec anchored at the top, since `git -C <common>` runs inside the work tree once core.worktree
    names the folder that holds the Git directory, and with the file system monitor off, which Git would start for the
    Git directory it takes as the work tree and wait on. An administrative directory without an index is skipped; one that
    cannot be read refuses (seen), and so does an index git cannot read, naming its worktree. The HEADs and branches are
    read refusing whatever Git writes beside its answer, since it skips a ref or an object it cannot read with only a
    warning, after each folder under refs/heads is listed, a link included, which Git follows, since for-each-ref skips
    one it cannot list without a word. The listing goes depth first, so links that loop reach the system's own link
    limit at once and are refused (seen); breadth first, two such links would never end, nor does Git's own listing of
    them, which passes over a folder it cannot list."""

    def read(*args, **kwargs):
        result = git_run(anchor, *args, **kwargs)
        require(not result.stderr, f'git {args[0]} wrote "{" ".join(result.stderr.decode("utf-8", "replace").split())}" while reading '
                f"this repository's HEADs and branches, so withdraw cannot tell whether {rel} is tracked there; withdraw changes "
                "nothing until it can")
        return result.stdout.decode("utf-8").strip()
    # A gitdir file may hold any bytes, and the listed paths only name worktrees in a refusal.
    listing = git_run(anchor, "worktree", "list", "--porcelain", "-z").stdout.decode("utf-8", "replace")
    worktrees = [row for raw in listing.split("\0\0")
                 if "worktree" in (row := dict(field.partition(" ")[::2] for field in raw.split("\0") if field))]
    checked_out = {row.get("branch") for row in worktrees}
    folders = [common / "refs/heads"]  # Missing where every ref is packed or in a reftable; a ref file lists nothing.
    while folders:
        folders += seen(folders.pop(), entries=True)
    commits = [(f"HEAD of {row['worktree']}", row["HEAD"]) for row in worktrees if "HEAD" in row] + [
        (f"the branch {ref.removeprefix('refs/heads/')}", ref)
        for ref in read("for-each-ref", "--format=%(refname)", "refs/heads/").splitlines() if ref not in checked_out]
    kinds = read("cat-file", "--batch-check=%(objecttype)", data="".join(f"{rev}:{rel}\n" for _, rev in commits).encode())
    places = [place for (place, _), kind in zip(commits, kinds.split("\n")) if kind == "blob"]
    linked = sorted(admin for admin in seen(common / "worktrees", entries=True) if seen(admin / "index"))
    for name, admin in [(worktrees[0]["worktree"], common), *((registered_worktree(admin), admin) for admin in linked)]:
        listed = subprocess.run(["git", "-c", "core.fsmonitor=false", "-C", str(common), f"--git-dir={admin}", "ls-files", "--",
                                 f":(top,literal){rel}"], capture_output=True)
        require(listed.returncode == 0, f"the index of {name} cannot be read ({' '.join(listed.stderr.decode('utf-8', 'replace').split())}), "
                                        f"so withdraw cannot tell whether {rel} is tracked there; withdraw takes back only a loop held in its capture")
        if listed.stdout:
            places.append(f"the index of {name}")
    return places


def withdraw(args):
    """Take back a queued loop none of whose tasks has started and that replaced no legacy row: its add record, then its
    folder in devlyn-loops, then its capture ref; a retry after an interruption finishes the rest. Under the drain lock,
    so no drain allocates it."""
    anchor, common = repository(args.repo)
    args.repo = anchor
    loop, notes = args.loop, []
    ref, rel = CAPTURES + loop, loop_queue(loop)
    require(re.fullmatch(ID, loop), f"loop id must match {ID}: {loop!r}")
    refuse_other_release(common, anchor)
    enforce_binding(common, anchor)
    busy = ("a drain or another withdraw is running in this repository; a loop cannot be withdrawn while a drain runs, and one "
            "added during a drain runs in it")
    with lock(common, "drain.lock", blocking=False, busy=busy), lock(common, "queue.lock", blocking=True):
        refuse_other_release(common)
        enforce_binding(common)
        added, captured = records(common).get(loop), ref_value(anchor, ref)
        # records() lists them with glob, which skips a folder it cannot read, so this loop's own record is looked at too.
        require(added or not seen(added_path(common, loop)), f"{common / 'devlyn-loops'} cannot be listed, so withdraw cannot read "
                f"the add record {added_path(common, loop)}; withdraw changes nothing until it can")
        commit = added["commit"] if added else captured
        rows, target = parse_loop(show(anchor, commit, rel), loop, f"{ref}:{rel}") if commit else ([], None)
        tasks = [row["identity"] for row in rows]
        if target:
            claim = f'the {QUEUE} row "{one_line(target[1])}" (occurrence {target[0]})'
            only = "withdraw takes back only a loop that replaced no legacy row"
            raise LoopError(f"loop {loop} was added in place of {claim}; {only}; it stays queued" if added else
                            f"the add of loop {loop} in place of {claim} stopped before its record; {only}; its capture stays at {ref}")
        # Without its record a loop is read from a tracked queue file (queue_view), so its rows would come back.
        places = tracked_places(anchor, common, rel)
        require(not places, f"{rel} is tracked in {', '.join(places)}, so loop {loop}'s rows would return without its add record; "
                            "withdraw takes back only a loop held in its capture")
        started = [f"{identity} at {path}" for identity in tasks for path in task_directories(common, identity)]
        require(not started, f"loop {loop} has a started task ({'; '.join(started)}); withdraw takes back only a loop none of whose "
                             "tasks has started")
        if added:
            require(captured == commit, f"{ref} is {captured or 'missing'}, but the add record of {loop} names {commit}")
            added_path(common, loop).unlink()
        if commit:
            folder = common / "devlyn-loops" / loop
            try:
                (folder / "drain-report.md").unlink(missing_ok=True)
                with contextlib.suppress(FileNotFoundError):
                    folder.rmdir()
            except OSError as exc:
                notes.append(f"loop folder retained: {folder}: {exc}; remove it")
            git(anchor, "update-ref", "-d", ref, commit)
    try:
        release_settled_binding(anchor, common, interrupted_add=True)
    except (LoopError, OSError) as exc:
        notes.append(f"queue binding not released: {exc}; withdraw {loop} again to release it")
    if not commit:
        return {"status": "BLOCKED", "reason": f"loop {loop} is not queued in this repository", "cleanup": notes}
    return {"status": "WITHDRAWN", "tasks": tasks, "commit": commit, "cleanup": notes,
            "message": f"`git show {commit}:docs/specs/{loop}/meta.md` shows the withdrawn package until Git prunes that commit. "
                       "Revised work is a new loop."}


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
        (self.root / "sitecustomize.py").write_text(
            "import importlib.machinery, importlib.util, pathlib, sys\n"
            "spec = importlib.machinery.PathFinder.find_spec('sitecustomize', [p for p in sys.path if pathlib.Path(p or '.').resolve() != pathlib.Path(__file__).resolve().parent])\n"
            "if spec is not None and spec.loader is not None:\n"
            "    spec.loader.exec_module(importlib.util.module_from_spec(spec))\n"
            "import shutil\nfrom types import SimpleNamespace\n"
            "shutil.disk_usage = lambda path: SimpleNamespace(total=100 * 1024**3, free=100 * 1024**3)\n",
            encoding="utf-8")
        # A commit's detached automatic maintenance would still write into .git while a test reads the tree.
        (self.root / "gitconfig").write_text("[maintenance]\n\tauto = false\n", encoding="utf-8")
        self.env = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": str(self.root / "gitconfig"),
                    "GIT_AUTHOR_NAME": "Fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
                    "GIT_COMMITTER_NAME": "Fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid"}
        self.env["PYTHONPATH"] = str(self.root) + os.pathsep + self.env.get("PYTHONPATH", "")
        self.env["PYTHONDONTWRITEBYTECODE"] = "1"
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

    def test_fixture_commit_starts_no_automatic_maintenance(self):
        # Its detached child would still write into .git while a test reads the tree or cleanup removes it.
        trace = self.root / "trace.json"
        subprocess.run(["git", "-C", str(self.anchor), "commit", "-q", "--allow-empty", "-m", "traced"], check=True,
                       env={**self.env, "GIT_TRACE2_EVENT": str(trace)})
        children = [line for line in trace.read_text(encoding="utf-8").splitlines() if '"event":"child_start"' in line]
        self.assertEqual(children, [])

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
        self.assertEqual((sorted(notes), all(path.exists() for path in saved)), (sorted(f"package cleanup retained: {path}: unlink denied" for path in saved), True))
        self.assertEqual((clean(common, records(common)), any(path.exists() for path in saved)), ([], False))

    def test_withdraw_takes_back_a_loop_none_of_whose_tasks_started(self):
        """D1. Prediction: withdrawing inv, added and never started, prints WITHDRAWN naming inv.t1, inv.t2 and the capture
        commit, and removes the add record, the capture ref and the loop's folder with its drain report, keeping
        devlyn-loops; the queue then holds no row of inv and nothing unfinished, and a second withdraw is refused as not
        queued. Before: argparse rejected withdraw."""
        added = self.cli("add", self.meta)
        common = Path(git(self.anchor, "rev-parse", "--path-format=absolute", "--git-common-dir"))
        (common / "devlyn-loops/inv/drain-report.md").write_text("# Drain report — inv\n", encoding="utf-8")
        result = self.cli("withdraw", "inv")
        self.assertEqual((result["status"], result["tasks"], result["commit"]), ("WITHDRAWN", ["inv.t1", "inv.t2"], added["commit"]))
        self.assertIn(f"git show {added['commit']}:docs/specs/inv/meta.md", result["message"])
        self.assertEqual((ref_value(self.anchor, "refs/devlyn/captures/inv"), sorted(path.name for path in (common / "devlyn-loops").iterdir())),
                         ("", ["drain.lock", "queue.lock"]))
        self.assertEqual((queue_view(self.anchor, records(common)), unfinished(view(self.anchor, common, pure=True))), ([], False))
        self.assertIn("loop inv is not queued in this repository", self.cli("withdraw", "inv", code=1)["reason"])

    def test_withdraw_refuses_without_changing_anything(self):
        """D1, E6. Prediction: each refusal leaves the add record and the drain report byte for byte, the capture ref, the
        loop's folder, HEAD and the index as they were: a task directory of either task, active, retired or moved, a dangling
        link included; a running drain or another withdraw, refused in withdraw's own words; a capture ref moved off the
        recorded commit, naming both; and the loop's queue file tracked in HEAD here, in the index here while core.worktree
        names this folder, in the index of the worktree the loop was added from, in HEAD and the index of a third worktree,
        in the index of a locked worktree whose folder is gone or holds only an empty directory, on a branch no worktree has
        checked out, or on the branch it was added on once that worktree is gone. Before: argparse rejected withdraw; then
        the third worktree and the other branch were withdrawn, and the busy refusal named only a drain; then the locked
        worktree without its folder was withdrawn, and with an empty directory there git's own failure was the refusal;
        then, with core.worktree set, the index here was read from inside the Git directory, where Git took the pathspec
        as .git/docs/..., and the loop was withdrawn."""
        import shutil
        linked, third, gone = self.root / "linked", self.root / "third", self.root / "gone"
        git(self.anchor, "worktree", "add", "-q", "-b", "side", str(linked), env=self.env)
        added = self.cli("add", write_package(linked, "inv", self.tasks))
        common = Path(git(self.anchor, "rev-parse", "--path-format=absolute", "--git-common-dir"))
        (common / "devlyn-loops/inv/drain-report.md").write_text("# Drain report — inv\n", encoding="utf-8")
        ref, rel, completion, head = "refs/devlyn/captures/inv", "docs/specs/inv/queue.md", common / "devlyn-completion", git(self.anchor, "rev-parse", "HEAD")
        key = {identity: hashlib.sha256(branch_of(identity).encode()).hexdigest()[:24] for identity in ("inv.t1", "inv.t2")}
        active, link = completion / key["inv.t1"], completion / key["inv.t2"]
        retired, moved = completion / "retired" / f"{key['inv.t2']}.operation", completion / "moved" / f"{key['inv.t1']}.operation"

        def state():
            return (git(self.anchor, "for-each-ref"), git(self.anchor, "rev-parse", "HEAD"), git(self.anchor, "ls-files", "-s"),
                    git(linked, "ls-files", "-s") if linked.exists() else None,
                    sorted((str(path.relative_to(common)), path.read_bytes() if path.is_file() else None)
                           for path in (common / "devlyn-loops").rglob("*") if path.suffix != ".lock"))

        def track(work, *commit):
            (work / rel).parent.mkdir(parents=True, exist_ok=True)
            (work / rel).write_text(row_line("inv.t1", "Interface") + "\n", encoding="utf-8")
            git(work, "add", rel, env=self.env)
            if commit:
                git(work, "commit", "-qm", "a queue file committed by hand", env=self.env)

        def untrack(work):
            git(work, "rm", "-q", "--cached", rel, env=self.env)
            (work / rel).unlink()

        def elsewhere(*start):
            git(self.anchor, "worktree", "add", "-q", *start, str(third), env=self.env)
            track(third, "commit")
            if start != ("--detach",):
                git(self.anchor, "worktree", "remove", "--force", str(third), env=self.env)

        def offline(empty):
            git(self.anchor, "worktree", "add", "-q", "--detach", str(gone), env=self.env)
            track(gone)
            git(self.anchor, "worktree", "lock", str(gone), env=self.env)
            shutil.rmtree(gone)
            if empty:
                gone.mkdir()

        def online():
            git(self.anchor, "worktree", "unlock", str(gone), env=self.env)
            if gone.exists():
                gone.rmdir()
            git(self.anchor, "worktree", "prune", env=self.env)

        def own_folder():  # A config that names the repository's own folder as its work tree.
            git(self.anchor, "config", "core.worktree", str(self.anchor), env=self.env)
            track(self.anchor)

        def no_worktree_config():
            untrack(self.anchor)
            git(self.anchor, "config", "--unset", "core.worktree", env=self.env)

        cases = [("active", lambda: active.mkdir(parents=True), active.rmdir, f"inv.t1 at {active}"),
                 ("retired", lambda: retired.mkdir(parents=True), retired.rmdir, f"inv.t2 at {retired}"),
                 ("moved", lambda: moved.mkdir(parents=True), moved.rmdir, f"inv.t1 at {moved}"),
                 ("ref", lambda: git(self.anchor, "update-ref", ref, head), lambda: git(self.anchor, "update-ref", ref, added["commit"]),
                  f"{ref} is {head}, but the add record of inv names {added['commit']}"),
                 ("HEAD here", lambda: track(self.anchor, "commit"), lambda: git(self.anchor, "reset", "-q", "--hard", head),
                  f"{rel} is tracked in HEAD of {self.anchor}"),
                 ("index here, core.worktree set", own_folder, no_worktree_config, f"{rel} is tracked in the index of {self.anchor}, so"),
                 ("index of origin", lambda: track(linked), lambda: untrack(linked), f"{rel} is tracked in the index of {linked}"),
                 ("third worktree", lambda: elsewhere("--detach"), lambda: git(self.anchor, "worktree", "remove", "--force", str(third), env=self.env),
                  f"{rel} is tracked in HEAD of {third}, the index of {third}, so"),
                 ("offline, empty folder", lambda: offline(True), online, f"{rel} is tracked in the index of {gone}, so"),
                 ("offline", lambda: offline(False), online, f"{rel} is tracked in the index of {gone}, so"),
                 ("other branch", lambda: elsewhere("-b", "elsewhere"), lambda: git(self.anchor, "branch", "-D", "elsewhere", env=self.env),
                  f"{rel} is tracked in the branch elsewhere, so")]
        if os.name != "nt":
            cases.append(("link", lambda: link.symlink_to(self.root / "nowhere"), link.unlink, f"inv.t2 at {link}"))
        for name, prepare, undo, message in cases:
            with self.subTest(case=name):
                prepare()
                before = state()
                self.assertIn(message, self.cli("withdraw", "inv", code=1)["reason"])
                self.assertEqual(state(), before)
                undo()
        with lock(common, "drain.lock", blocking=True):
            before = state()
            self.assertIn("a drain or another withdraw is running in this repository; a loop cannot be withdrawn while a drain runs, "
                          "and one added during a drain runs in it", self.cli("withdraw", "inv", code=1)["reason"])
            self.assertEqual(state(), before)
        track(linked, "commit")
        git(self.anchor, "worktree", "remove", "--force", str(linked), env=self.env)
        before = state()
        self.assertIn(f"{rel} is tracked in the branch side", self.cli("withdraw", "inv", code=1)["reason"])
        self.assertEqual(state(), before)

    def test_a_drain_started_during_a_withdraw_says_a_withdraw_may_hold_its_lock(self):
        """D1. Prediction: a drain started while a withdraw, paused inside its locks, holds drain.lock is refused, its
        reason naming a drain or a withdraw and the lock; the withdraw then finishes WITHDRAWN. Before: the reason said
        another drain was active, though only a withdraw ran."""
        import threading
        from unittest import mock
        self.cli("add", self.meta)
        common = Path(git(self.anchor, "rev-parse", "--path-format=absolute", "--git-common-dir"))
        inside, resume, result, real = threading.Event(), threading.Event(), {}, tracked_places

        def paused(*args):
            inside.set()
            resume.wait(60)
            return real(*args)

        with mock.patch.dict(withdraw.__globals__, tracked_places=paused):
            running = threading.Thread(target=lambda: result.update(withdraw(argparse.Namespace(repo=str(self.anchor), loop="inv"))))
            running.start()
            try:
                self.assertTrue(inside.wait(60))
                reason = self.cli("drain", "--", sys.executable, "-c", "pass", "{packet}", code=1)["reason"]
            finally:
                resume.set()
                running.join(60)
        self.assertEqual(reason, f"a drain or a withdraw is running in this repository ({common / 'devlyn-loops/drain.lock'})")
        self.assertEqual(result.get("status"), "WITHDRAWN")

    def test_withdraw_finishes_after_an_interruption_between_its_deletions(self):
        """D1. Prediction: a withdraw interrupted after it removed the add record, before the capture ref, leaves that ref,
        which still counts as unfinished work; the retry removes it and prints WITHDRAWN with the same tasks and commit.
        Before: there was no withdraw."""
        from unittest import mock
        added = self.cli("add", self.meta)
        common, real = Path(git(self.anchor, "rev-parse", "--path-format=absolute", "--git-common-dir")), git

        def interrupted(cwd, *args, **kwargs):
            if args[:2] == ("update-ref", "-d"):
                raise LoopError("interrupted before the capture ref")
            return real(cwd, *args, **kwargs)

        with mock.patch.dict(withdraw.__globals__, git=interrupted), self.assertRaisesRegex(LoopError, "interrupted before"):
            withdraw(argparse.Namespace(repo=str(self.anchor), loop="inv"))
        self.assertEqual((added_path(common, "inv").exists(), ref_value(self.anchor, "refs/devlyn/captures/inv"),
                          unfinished(view(self.anchor, common, pure=True))), (False, added["commit"], True))
        result = self.cli("withdraw", "inv")
        self.assertEqual((result["status"], result["tasks"], result["commit"]), ("WITHDRAWN", ["inv.t1", "inv.t2"], added["commit"]))
        self.assertEqual(ref_value(self.anchor, "refs/devlyn/captures/inv"), "")

    def test_withdraw_refuses_a_loop_that_replaced_a_legacy_row(self):
        """D1, E6. Prediction: a loop added with --materialize is refused, naming the row its capture replaced and that row's
        occurrence and saying the loop stays queued, while the row is in the legacy queue and once no file holds it; the
        capture an add stopped before its record left is refused, saying that add stopped before its record and where its
        capture stays; each refusal leaves the add record, the capture ref, the loop's folder, HEAD and the index byte for
        byte. A loop added without --materialize is withdrawn. Before: withdraw looked for the row only here, in the
        checkout the loop was added from and on the branch it was added on, and withdrew the loop once those no longer held
        it, though another worktree's legacy queue could still show the row, pending, to be planned again; then the refusal
        said withdrawing would bring the row back, which no file holding it, or a capture that never hid it, makes false;
        then it said that capture's loop was added and stays queued, though status shows its row pending and no loop."""
        from unittest import mock
        common = Path(git(self.anchor, "rev-parse", "--path-format=absolute", "--git-common-dir"))

        def state():
            return (git(self.anchor, "for-each-ref"), git(self.anchor, "rev-parse", "HEAD"), git(self.anchor, "ls-files", "-s"),
                    sorted((str(path.relative_to(common)), path.read_bytes() if path.is_file() else None)
                           for path in (common / "devlyn-loops").rglob("*") if path.suffix != ".lock"))

        def refused(loop, row, recorded=True):
            claim = f'the {QUEUE} row "{row}" (occurrence 1)'
            before = state()
            self.assertEqual(self.cli("withdraw", loop, code=1)["reason"],
                             f"loop {loop} was added in place of {claim}; withdraw takes back only a loop that replaced no legacy "
                             "row; it stays queued" if recorded else
                             f"the add of loop {loop} in place of {claim} stopped before its record; withdraw takes back only a "
                             f"loop that replaced no legacy row; its capture stays at refs/devlyn/captures/{loop}")
            self.assertEqual(state(), before)

        (self.anchor / QUEUE).write_text("# Intent Queue\n\n- [ ] Ship the fixture.\n- [ ] Ship the second fixture.\n", encoding="utf-8")
        self.cli("add", write_package(self.anchor, "rep", self.tasks[:1], intent="User asked: Ship the fixture."), "--materialize", 3)
        (common / "devlyn-loops/rep/drain-report.md").write_text("# Drain report — rep\n", encoding="utf-8")
        refused("rep", "- [ ] Ship the fixture.")
        (self.anchor / QUEUE).write_text("# Intent Queue\n\n- [ ] Ship the second fixture.\n", encoding="utf-8")
        refused("rep", "- [ ] Ship the fixture.")
        self.cli("add", self.meta)
        self.assertEqual(self.cli("withdraw", "inv")["tasks"], ["inv.t1", "inv.t2"])
        meta, real = write_package(self.anchor, "ref", self.tasks[:1], intent="User asked: Ship the second fixture."), write_json

        def stopped(path, value):
            if Path(path).name == "added.json":
                raise LoopError("stopped before the add record")
            real(path, value)

        with mock.patch.dict(os.environ, self.env), mock.patch.dict(add.__globals__, write_json=stopped), \
                self.assertRaisesRegex(LoopError, "stopped before"):
            add(argparse.Namespace(package=str(meta), materialize=3))
        self.assertEqual((bool(ref_value(self.anchor, "refs/devlyn/captures/ref")), added_path(common, "ref").exists()), (True, False))
        refused("ref", "- [ ] Ship the second fixture.", recorded=False)

    def test_withdraw_sees_a_task_directory_that_moves_while_it_looks(self):
        """D1, E6. Prediction: a task directory that task-complete moves into moved/, from the active path or from retired/,
        just after withdraw has listed moved/, still refuses the withdraw, naming where it was seen, and the add record and
        the capture ref stay. Before: withdraw listed retired/ and moved/ before it looked at the active path and dropped a
        listed path that had moved since, so it saw no directory and withdrew the loop."""
        from unittest import mock
        added = self.cli("add", self.meta)
        common = Path(git(self.anchor, "rev-parse", "--path-format=absolute", "--git-common-dir"))
        completion, key = common / "devlyn-completion", hashlib.sha256(branch_of("inv.t1").encode()).hexdigest()[:24]
        destination, real = completion / "moved" / f"{key}.operation", Path.iterdir
        destination.parent.mkdir(parents=True)
        for start in (completion / key, completion / "retired" / f"{key}.operation"):
            with self.subTest(start=start.parent.name):
                start.mkdir(parents=True)

                def iterdir(path):
                    found = list(real(path))
                    if path.name == "moved" and start.exists():
                        start.rename(destination)
                    return iter(found)

                with mock.patch.object(Path, "iterdir", iterdir), self.assertRaisesRegex(LoopError, re.escape(f"inv.t1 at {start}")):
                    withdraw(argparse.Namespace(repo=str(self.anchor), loop="inv"))
                self.assertEqual((added_path(common, "inv").exists(), ref_value(self.anchor, "refs/devlyn/captures/inv")), (True, added["commit"]))
                destination.rmdir()

    def test_withdraw_of_a_loop_it_does_not_hold_deletes_nothing(self):
        """D1. Prediction: a loop with no add record and no capture ref, committed only in a linked worktree, keeps its drain
        report and its folder under the common Gitdir: withdraw from this checkout refuses, naming that worktree's HEAD and
        index; once the worktree and its branch are gone the loop is not queued, and the report and folder still stay.
        Before: the first withdraw said not queued, and before f02e2c60 it deleted the report and the folder."""
        linked = self.root / "linked"
        git(self.anchor, "worktree", "add", "-q", "-b", "side", str(linked), env=self.env)
        write_package(linked, "rl", self.tasks[:1])
        rel = loop_queue("rl")
        (linked / rel).write_text(row_line("rl.t1", "Interface") + "\n", encoding="utf-8")
        git(linked, "add", "docs/specs/rl", env=self.env)
        git(linked, "commit", "-qm", "a loop committed without an add, as a fresh clone holds it", env=self.env)
        report = Path(git(self.anchor, "rev-parse", "--path-format=absolute", "--git-common-dir")) / "devlyn-loops/rl/drain-report.md"
        report.parent.mkdir(parents=True)
        report.write_text("# Drain report — rl\n", encoding="utf-8")
        self.assertIn(f"{rel} is tracked in HEAD of {linked}, the index of {linked}, so", self.cli("withdraw", "rl", code=1)["reason"])
        self.assertEqual(report.read_text(encoding="utf-8"), "# Drain report — rl\n")
        git(self.anchor, "worktree", "remove", "--force", str(linked), env=self.env)
        git(self.anchor, "branch", "-D", "side", env=self.env)
        self.assertIn("loop rl is not queued in this repository", self.cli("withdraw", "rl", code=1)["reason"])
        self.assertEqual((sorted(path.name for path in report.parent.iterdir()), report.read_text(encoding="utf-8")),
                         (["drain-report.md"], "# Drain report — rl\n"))

    def test_withdraw_reads_past_prunable_missing_and_bare_worktrees(self):
        """D1, E6. Prediction: withdraw prints WITHDRAWN beside a registered worktree whose folder stays without its .git
        file (Git lists it prunable), a locked worktree whose folder is gone, neither index holding the loop's queue
        file, a dangling symbolic ref under refs/heads, which Git lists nowhere, and, where links are made (not Windows),
        a link there that dangles, which Git skips, and one at a regular file holding a commit, which Git reads as a ref
        file, and in the linked worktree of a bare clone, whose bare row has no HEAD line and whose common Gitdir has no
        index. git ls-files run in either folder fails; without the HEAD check the bare row raises KeyError."""
        import shutil
        prunable, gone, bare, work = self.root / "prunable", self.root / "gone", self.root / "bare.git", self.root / "work"
        for path in (prunable, gone):
            git(self.anchor, "worktree", "add", "-q", "--detach", str(path), env=self.env)
        (prunable / ".git").unlink()
        git(self.anchor, "worktree", "lock", str(gone), env=self.env)
        shutil.rmtree(gone)
        git(self.anchor, "symbolic-ref", "refs/heads/dangle", "refs/heads/nowhere", env=self.env)
        if os.name != "nt":
            (self.root / "commit").write_text(git(self.anchor, "rev-parse", "main", env=self.env) + "\n", encoding="utf-8")
            for name, target in (("lost", self.root / "nowhere"), ("filed", self.root / "commit")):
                (self.anchor / ".git/refs/heads" / name).symlink_to(target)
        self.cli("add", self.meta)
        self.assertEqual(self.cli("withdraw", "inv")["status"], "WITHDRAWN")
        subprocess.run(["git", "clone", "-q", "--bare", str(self.anchor), str(bare)], check=True, env=self.env)
        git(bare, "worktree", "add", "-q", str(work), "main", env=self.env)
        self.cli("add", write_package(work, "inv", self.tasks), cwd=work)
        self.assertEqual(self.cli("withdraw", "inv", cwd=work)["status"], "WITHDRAWN")

    def test_withdraw_reads_each_registered_index_however_its_worktree_is_named(self):
        """D1, E6. Prediction: beside a registered worktree whose administrative gitdir file is missing, or holds bytes that
        are not UTF-8, a loop tracked nowhere is withdrawn, and with the loop's queue file staged in that worktree's index
        it is refused, naming the worktree by its administrative directory; a worktree whose gitdir file holds a relative
        path is named as `git worktree list` prints it; an index git cannot read is refused in one sentence naming its
        worktree and git's message; a file or an empty directory beside the administrative directories, which Git skips,
        is skipped too. No refusal changes the add record or the capture ref. Before: the missing file stopped every
        withdraw with a bare FileNotFoundError, the bytes raised an uncaught UnicodeDecodeError, and the unreadable index
        was refused in git's words alone; then the empty directory stopped every withdraw as an index git cannot read."""
        import shutil
        common = Path(git(self.anchor, "rev-parse", "--path-format=absolute", "--git-common-dir"))
        rel, work = loop_queue("inv"), self.root / "work"
        admin = common / "worktrees" / work.name
        admin.parent.mkdir()
        (admin.parent / ".DS_Store").write_bytes(b"")  # As a file manager leaves one.
        (admin.parent / "empty").mkdir()  # Git lists no worktree for it, and git worktree prune deletes it.

        def state():
            return (git(self.anchor, "for-each-ref"), sorted((str(path.relative_to(common)), path.read_bytes() if path.is_file() else None)
                                                             for path in (common / "devlyn-loops").rglob("*") if path.suffix != ".lock"))

        def by_admin():
            return f"the worktree registered at {admin}"

        def as_listed():
            return git(self.anchor, "worktree", "list", "--porcelain").split("\n\n")[1].splitlines()[0].removeprefix("worktree ")

        for name, options, damage, named in (("gitdir missing", (), lambda: (admin / "gitdir").unlink(), by_admin),
                                             ("gitdir not UTF-8", (), lambda: (admin / "gitdir").write_bytes(b"\xff\xfe/.git\n"), by_admin),
                                             ("gitdir relative", ("--relative-paths",), lambda: None, as_listed)):
            with self.subTest(case=name):
                if git_run(self.anchor, "worktree", "add", "-q", "--detach", *options, str(work), env=self.env, ok=(0, 129)).returncode:
                    self.skipTest("this git writes no relative gitdir file (git worktree add --relative-paths came in Git 2.48)")
                try:
                    damage()
                    self.cli("add", write_package(self.anchor, "inv", self.tasks))
                    self.assertEqual(self.cli("withdraw", "inv")["status"], "WITHDRAWN")
                    self.cli("add", write_package(self.anchor, "inv", self.tasks))
                    (work / rel).parent.mkdir(parents=True)
                    (work / rel).write_text(row_line("inv.t1", "Interface") + "\n", encoding="utf-8")
                    git(work, "add", rel, env=self.env)
                    before = state()
                    self.assertEqual(self.cli("withdraw", "inv", code=1)["reason"],
                                     f"{rel} is tracked in the index of {named()}, so loop inv's rows would return without its add "
                                     "record; withdraw takes back only a loop held in its capture")
                    self.assertEqual(state(), before)
                finally:
                    shutil.rmtree(admin)
                    shutil.rmtree(work)
        git(self.anchor, "worktree", "add", "-q", "--detach", str(work), env=self.env)
        (admin / "index").write_bytes(b"not an index")
        before = state()
        self.assertRegex(self.cli("withdraw", "inv", code=1)["reason"],
                         rf"^the index of {re.escape(str(work))} cannot be read \(fatal: .*index.*\), so withdraw cannot tell "
                         rf"whether {re.escape(rel)} is tracked there; withdraw takes back only a loop held in its capture$")
        self.assertEqual(state(), before)

    def test_withdraw_reads_each_index_without_a_file_system_monitor(self):
        """D1, E6. Prediction: with core.fsmonitor=true and one linked worktree, neither worktree's monitor running (as
        after a restart), withdraw prints WITHDRAWN within 60 s. Before: Git took the Git directory as the work tree of
        each index read, started a monitor for it and waited on it, so withdraw never returned and held its locks. The
        monitor is turned on after the setup, whose own checkout a starting monitor can hang. Withdraw runs as an owned
        tree (its own POSIX session or Windows job) ended whole within seconds, its output in files no monitor holds open."""
        probe = git_run(self.anchor, "fsmonitor--daemon", "status", env=self.env, ok=(0, 1, 128))
        if probe.returncode == 128:
            self.skipTest(f"no file system monitor here ({probe.stderr.decode('utf-8', 'replace').strip()})")
        linked = self.root / "linked"
        git(self.anchor, "worktree", "add", "-q", "--detach", str(linked), env=self.env)
        self.cli("add", self.meta)
        for work in (self.anchor, linked):
            self.addCleanup(git_run, work, "fsmonitor--daemon", "stop", env=self.env, ok=(0, 128))
        git(self.anchor, "config", "core.fsmonitor", "true", env=self.env)
        out, err = self.root / "withdraw.out", self.root / "withdraw.err"
        with out.open("wb") as stdout, err.open("wb") as stderr:
            code = shared("platform-support")["run_process"]([sys.executable, str(Path(__file__).resolve()), "withdraw", "inv"],
                                                             subprocess.DEVNULL, 60, on_timeout=None, cwd=self.anchor, env=self.env,
                                                             stdout=stdout, stderr=stderr)
        output = out.read_text(encoding="utf-8") + err.read_text(encoding="utf-8")
        self.assertIsNotNone(code, f"withdraw did not return within 60 s: {output}")
        self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["status"], "WITHDRAWN", output)

    def test_withdraw_refuses_while_it_cannot_read_a_place_that_may_hold_the_loop(self):
        """D1, E6. Prediction: withdraw refuses in one sentence naming the path, and changes nothing, while it cannot read
        the index of a linked worktree holding the staged queue file behind an administrative directory it cannot enter,
        <common>/worktrees itself, retired/ or moved/ holding a task's directory, devlyn-completion holding the active one,
        the loop's folder in devlyn-loops, or devlyn-loops, which the add records are listed from; and, for a branch that
        commits the queue file, its ref file, its ref folder, also one reached through a link, or its tree object, refused
        in Git's words or naming the folder. Before: is_file, lexists and glob each answered no on the permission error, so
        withdraw took back the loop, and in the loop folder and add records cases deleted its capture ref while its add
        record stayed; the unreadable worktrees folder alone was refused, in the system's words; then Git skipped the
        branch, with only a warning for the ref file and the tree object and silently for the folder, and the loop was
        withdrawn; then withdraw passed over a link, which Git follows, and took back the loop behind one."""
        probe = self.root / "probe"
        probe.mkdir(mode=0)
        try:
            os.listdir(probe)
            self.skipTest("this process reads a folder whose mode denies it (root, or Windows)")
        except PermissionError:
            pass
        finally:
            probe.chmod(0o700)
        common = Path(git(self.anchor, "rev-parse", "--path-format=absolute", "--git-common-dir"))
        rel, work, completion, loops = loop_queue("inv"), self.root / "work", common / "devlyn-completion", common / "devlyn-loops"
        key = {identity: hashlib.sha256(branch_of(identity).encode()).hexdigest()[:24] for identity in ("inv.t1", "inv.t2")}
        git(self.anchor, "worktree", "add", "-q", "--detach", str(work), env=self.env)
        (work / rel).parent.mkdir(parents=True)
        (work / rel).write_text(row_line("inv.t1", "Interface") + "\n", encoding="utf-8")

        def state():
            return (git(self.anchor, "for-each-ref"), git(work, "ls-files", "-s"), sorted(
                (str(path.relative_to(common)), path.read_bytes() if path.is_file() else None) for path in loops.rglob("*") if path.suffix != ".lock"))

        def restore(path, mode):  # A path its case removed since has nothing to restore.
            with contextlib.suppress(FileNotFoundError):
                path.chmod(mode)

        def unreadable(path):
            return f"{path} cannot be read ({os.strerror(errno.EACCES)}), so withdraw cannot tell what it holds; withdraw changes nothing until it can"

        staged = (lambda: git(work, "add", rel, env=self.env), lambda: git(work, "rm", "-q", "--cached", rel, env=self.env))
        cases = [("linked index", staged, common / "worktrees" / work.name, 0, unreadable(common / "worktrees" / work.name / "index")),
                 ("worktrees folder", staged, common / "worktrees", 0, unreadable(common / "worktrees"))]
        for name, folder, identity in (("retired", completion / "retired", "inv.t2"), ("moved", completion / "moved", "inv.t1"),
                                       ("active", completion, "inv.t1")):
            directory = completion / key[identity] if name == "active" else folder / f"{key[identity]}.operation"
            cases.append((name, (functools.partial(directory.mkdir, parents=True), directory.rmdir), folder, 0,
                          unreadable(directory if name == "active" else folder)))
        cases += [("loop folder", (lambda: None, lambda: None), loops / "inv", 0, unreadable(added_path(common, "inv"))),
                  ("add records", (lambda: None, lambda: None), loops, 0o300,
                   f"{loops} cannot be listed, so withdraw cannot read the add record {added_path(common, 'inv')}; withdraw "
                   "changes nothing until it can")]
        # A commit no worktree has checked out holding the queue file, made in a temporary index, for a branch per case.
        index = {**self.env, "GIT_INDEX_FILE": str(self.root / "held.index")}
        blob = git(self.anchor, "hash-object", "-w", "--stdin", data=(row_line("inv.t1", "Interface") + "\n").encode(), env=self.env)
        git(self.anchor, "update-index", "--add", "--cacheinfo", f"100644,{blob},{rel}", env=index)
        tree = git(self.anchor, "write-tree", env=index)
        held = git(self.anchor, "commit-tree", tree, "-m", "a queue file committed by hand", env=self.env)

        def branch(name):
            return lambda: git(self.anchor, "branch", name, held, env=self.env), lambda: git(self.anchor, "branch", "-q", "-D", name, env=self.env)

        def git_words(command, named):  # Git's own words vary with the locale; they name the ref or the object.
            return re.compile(rf'git {command} wrote ".*{re.escape(named)}.*" while reading this repository\'s HEADs and branches, so '
                              rf"withdraw cannot tell whether {re.escape(rel)} is tracked there; withdraw changes nothing until it can")
        outside, nest = self.root / "outside", common / "refs/heads/nest"  # A ref folder Git reaches through a link.
        behind = (lambda: (outside.mkdir(), (outside / "held").write_text(held + "\n", encoding="utf-8"), nest.symlink_to(outside)),
                  lambda: (nest.unlink(), (outside / "held").unlink(), outside.rmdir()))
        cases += [("branch ref file", branch("held"), common / "refs/heads/held", 0, git_words("for-each-ref", "refs/heads/held")),
                  ("branch ref folder", branch("nest/held"), nest, 0, unreadable(nest)),
                  ("branch ref folder behind a link", behind, outside, 0, unreadable(nest)),
                  ("tree object", branch("held"), common / "objects" / tree[:2] / tree[2:], 0, git_words("cat-file", tree))]
        for name, (prepare, undo), denied, mode, reason in cases:
            with self.subTest(case=name):
                self.cli("add", write_package(self.anchor, "inv", self.tasks))  # A retry once added: nothing changes.
                prepare()
                before, original = state(), denied.stat().st_mode & 0o7777
                self.addCleanup(restore, denied, original)  # Also when the case fails, so the folder can be removed.
                denied.chmod(mode)
                try:
                    refusal = self.cli("withdraw", "inv", code=1)["reason"]
                finally:  # Also when withdraw took the loop back, so the next case starts from its own state.
                    denied.chmod(original)
                    after = state()
                    undo()
                self.assertEqual(after, before)
                (self.assertRegex if isinstance(reason, re.Pattern) else self.assertEqual)(refusal, reason)

    def test_withdraw_reads_the_head_of_each_worktree_whose_listed_paths_decode_alike(self):
        """D1, E6. Prediction: beside two linked worktrees whose gitdir files name folders that differ only in a byte that
        is not UTF-8, the first listed with a HEAD that tracks the loop's queue file while no index holds it, withdraw is
        refused, naming that HEAD by the one name both paths decode to. Before: the two HEADs were kept under that one
        name, the second's in place of the first's, and the loop was withdrawn."""
        common = Path(git(self.anchor, "rev-parse", "--path-format=absolute", "--git-common-dir"))
        rel = loop_queue("inv")
        self.cli("add", self.meta)
        for name, byte in (("first", b"\xe8"), ("second", b"\xe9")):  # Git lists linked worktrees sorted by path.
            work = self.root / name
            git(self.anchor, "worktree", "add", "-q", "--detach", str(work), env=self.env)
            if name == "first":
                (work / rel).parent.mkdir(parents=True)
                (work / rel).write_text(row_line("inv.t1", "Interface") + "\n", encoding="utf-8")
                git(work, "add", rel, env=self.env)
                git(work, "commit", "-qm", "a queue file committed by hand", env=self.env)
                git(work, "rm", "-q", "--cached", rel, env=self.env)
            (common / "worktrees" / name / "gitdir").write_bytes(b"/x/caf" + byte + b"/.git\n")
        self.assertEqual(self.cli("withdraw", "inv", code=1)["reason"],
                         f"{rel} is tracked in HEAD of /x/caf�, so loop inv's rows would return without its add record; "
                         "withdraw takes back only a loop held in its capture")

    def test_a_legacy_row_is_replaced_only_by_its_one_exact_claim(self):
        """Q. Prediction: a loop's queue file hides the legacy row whose exact text and occurrence it records, line endings
        aside, showing the loop's rows in its place; a claim on a missing occurrence replaces nothing, so no other row
        disappears; a row two loops claim, as two clones each materializing it leave it, is hidden with neither loop in its
        place, so materializing it once more is refused; loops without a record follow in loop-id order, two-b after two.
        Before: the first row equal to the recorded text was replaced, whatever its occurrence; two-b came first, its queue
        file's path sorting before two's since '-' sorts before '/'; the row two loops claim stayed pending, and every
        further --materialize of it was added."""
        (self.anchor / QUEUE).write_bytes(b"# Intent Queue\n\n- [ ] alpha\r\n- [ ] alpha\n- [ ] beta\n")
        for loop, occurrence, line in (("one", 2, "- [ ] alpha"), ("two", 1, "- [ ] beta"), ("two-b", 1, "- [ ] beta"), ("four", 3, "- [ ] alpha")):
            (self.anchor / "docs/specs" / loop).mkdir(parents=True)
            (self.anchor / loop_queue(loop)).write_text(f"<!-- replaces {QUEUE} row (occurrence {occurrence}): {line} -->\n\n{row_line(f'{loop}.t1', 'T')}\n",
                                                         encoding="utf-8")
        git(self.anchor, "add", "docs/specs", env=self.env)
        self.assertEqual([(row["identity"], row["index"]) for row in queue_view(self.anchor, {})],
                         [(None, 2), ("one.t1", 2), ("four.t1", 2), ("two.t1", 2), ("two-b.t1", 2)])
        again = write_package(self.anchor, "rep", self.tasks[:1], intent="User asked: beta.")
        self.assertIn(f"{QUEUE} line 5 is not a pending legacy row", self.cli("add", again, "--materialize", 5, code=1)["reason"])

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
                        self.assertIn("a drain or a withdraw is running in this repository", json.loads(out)["reason"])
                        held.stdin.close()
        self.assertEqual((read_json(added_path(common, "inv"))["origin"], read_json(added_path(common, "inv"))["branch"]), (str(linked), "side"))

    def test_a_crash_on_either_side_of_the_spawn_never_starts_a_second_executor(self):
        """The attempt's start is durable before the spawn, so a resumed drain observes writers first: it waits while
        an executor lives and adopts its submission, runs the executor once when none did, and fails the task where
        writers cannot be observed. Prediction (H2): that one run exits 0 without writing a submission, so the task waits,
        naming the exit code and both output files, and no submission exists. Before: the drain wrote a stand-in submission
        with a blocked-infrastructure blocker, which made the task [F]."""
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
            with mock.patch.dict(helper, {"stopped_writers": stopped_writers}), mock.patch("subprocess.Popen", popen):
                try:
                    return ensure_submission("l.t", records / "packet.json", packet, ["executor", "{packet}"])
                except Waiting as exc:
                    return str(exc)

        def survivor(count):
            if count < 3:
                raise helper["WriterActive"]("active process 4242 uses task files")
            Path(packet["submission"]).write_text('{"by": "executor"}', encoding="utf-8")

        def unobservable(count):
            raise helper["WritersUnobservable"]("writer observation unsupported on this platform; retain workspace")

        output = Path(packet["evidence_dir"])
        for crash, observe, outcome in ((crash_after_spawn, survivor, (1, 3, None)),
                                        (crash_before_spawn, lambda count: None,
                                         (1, 1, f"executor exited 0 without a submission (see executor.stdout and executor.stderr in "
                                                f"{output}); the next drain runs it again")),
                                        (crash_before_spawn, unobservable, (0, 1, "interrupted-unobservable"))):
            with self.subTest(crash=crash.__name__, observe=getattr(observe, "__name__", "nothing")):
                spawns.clear()
                checks.clear()
                for path in records.iterdir():
                    path.unlink()
                with self.assertRaises(Crash):
                    drain(crash)
                failure = drain(spawn, observe)
                if crash is crash_after_spawn:
                    # One observation per invocation, without sleep or a second spawn while the writer lives.
                    self.assertEqual((len(spawns), len(checks)), (1, 1))
                    self.assertIn("interrupted execution still active", failure)
                    self.assertIn("interrupted execution still active", drain(spawn, observe))
                    failure = drain(spawn, observe)
                self.assertEqual((len(spawns), len(checks), failure and failure.partition(": ")[0]), outcome)
                self.assertEqual(Path(packet["submission"]).exists(), crash is crash_after_spawn)
                if crash is crash_after_spawn:
                    self.assertEqual(read_json(Path(packet["submission"])), {"by": "executor"})

    def test_a_submission_is_retired_only_as_it_stands_once_its_writers_stopped(self):
        """C5 review 2. Prediction: a writer that replaces an infrastructure-only submission with one carrying a product
        blocker and exits before the observation leaves that submission adopted (None) in place, so the task fails with
        its blockers, and nothing is retired. Before: the reading from before the observation retired it and the task
        ran again."""
        from unittest import mock
        submission = self.root / "submission.json"
        infrastructure = {"kind": "blocked-infrastructure", "detail": "registry unreachable"}
        product = {"kind": "failed", "detail": "notes format undecided"}

        def write(*blockers):
            submission.write_text(json.dumps({"schema_version": 1, "task": "l.t", "source_sha": "0" * 40, "blockers": blockers}),
                                  encoding="utf-8")
        write(infrastructure)
        with mock.patch.dict(shared("task-complete"), stopped_writers=lambda worktree: write(infrastructure, product)):
            self.assertIsNone(retire_retryable({"task": "l.t", "worktree": str(self.root)}, submission))
        self.assertEqual((read_json(submission)["blockers"], [path.name for path in self.root.glob("submission*")]),
                         ([infrastructure, product], ["submission.json"]))


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
    inspector = actions.add_parser("inspect")
    inspector.add_argument("--repo", default=".")
    inspector.add_argument("--json", action="store_true")
    remover = actions.add_parser("withdraw")
    remover.add_argument("--repo", default=".")
    remover.add_argument("loop", help="a queued loop none of whose tasks has started and that replaced no legacy row")
    actions.choices["drain"].add_argument("--worktree-root")
    actions.choices["drain"].add_argument("executor", nargs="+", help="host executor argv after --; {packet} becomes the packet path")
    args = parser.parse_args()
    if args.self_test:
        result = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(QueueTests))
        if result.wasSuccessful():
            print(f"queue self-test: PASS ({result.testsRun} tests)")
        return 0 if result.wasSuccessful() else 1
    if args.action is None:
        parser.error("check, add, withdraw, status, inspect or drain is required")
    if args.action == "inspect":
        os.environ["GIT_OPTIONAL_LOCKS"] = "0"  # git diff may otherwise refresh the index even with unchanged bytes.
    try:
        result = {"check": check, "add": add, "withdraw": withdraw, "status": status, "drain": drain, "inspect": inspect}[args.action](args)
    except (LoopError, OSError) as exc:
        result = {"status": "BLOCKED", "reason": str(exc)}
        if args.action in {"status", "drain"}:
            result.update(skill_diagnostics(Path(args.repo)))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 1 if result["status"] == "BLOCKED" else 0


if __name__ == "__main__":
    shared("platform-support")["configure_utf8"]()
    sys.exit(main())
