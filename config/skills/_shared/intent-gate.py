#!/usr/bin/env python3
"""/devlyn:intent evidence gate: the single writer of .devlyn/intent/ and the only path to PASS.

start → scope → edit/delegate → commit → check/review (repeat after any change) → finish.
Evidence is keyed to the exact source (HEAD commit + worktree tree); finish accepts only
evidence for the current source. No phase lifecycle; models run only via delegate/review.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time

sys.dont_write_bytecode = True
SHARED = Path(__file__).resolve().parent
PLATFORM = runpy.run_path(str(SHARED / "platform-support.py"))
VALUE_FLAGS = {"--goal-file", "--spec", "--verify-only", "--engine", "--role-config", "--max-rounds"}
BOOL_FLAGS = {"--pair-verify", "--no-pair"}
MARKER = "DEVLYN_INTENT_PROCESS"
STREAM_GRACE = 5


class Blocked(Exception):
    pass


def block(reason, detail=""):
    raise Blocked(f"BLOCKED:{reason}" + (f": {detail}" if detail else ""))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git(work, *args, env=None, raw=False, stdin=None):
    proc = subprocess.run(["git", *args], cwd=work, capture_output=True, env=env, input=stdin)
    if proc.returncode != 0:
        block("git", f"git {' '.join(args[:3])}: {proc.stderr.decode(errors='replace').strip()}")
    return proc.stdout if raw else proc.stdout.decode().strip()


def loads(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def constant(token):
        raise ValueError(f"invalid JSON constant: {token}")

    return json.loads(raw, object_pairs_hook=unique, parse_constant=constant)


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".")
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
    os.replace(tmp, path)


def tree(work):
    """Tree id of HEAD plus every tracked and untracked non-ignored path outside .devlyn/."""
    index = work / ".devlyn/intent" / f".index-{os.getpid()}-{time.time_ns()}"
    env = {**os.environ, "GIT_INDEX_FILE": str(index)}
    try:
        git(work, "read-tree", "HEAD", env=env)
        git(work, "add", "-A", "--", ".", env=env)
        git(work, "rm", "-r", "-q", "--cached", "--ignore-unmatch", "--", ".devlyn", env=env)
        return git(work, "write-tree", env=env)
    finally:
        index.unlink(missing_ok=True)


def source(work):
    """Evidence key: the exact commit and worktree. A commit changes it, so evidence follows the commit."""
    return git(work, "rev-parse", "HEAD") + ":" + tree(work)


def changed(work, old, new):
    out = git(work, "diff", "--name-only", "-z", "--no-renames", old, new, "--", ".", ":(exclude).devlyn", raw=True)
    return sorted(p.decode() for p in out.split(b"\0") if p)


def blobs(work, tree_id, paths):
    """{path: "mode object"} in a tree; a deleted path maps to None."""
    found = {path: None for path in paths}
    if paths:
        out = git(work, "ls-tree", "-r", "-z", tree_id, "--", *paths, env={**os.environ, "GIT_LITERAL_PATHSPECS": "1"}, raw=True)
        for entry in out.split(b"\0"):
            if entry:
                meta, _, path = entry.decode().partition("\t")
                mode, _, obj = meta.split()
                found[path] = f"{mode} {obj}"
    return found


def glob_regex(pattern):
    parts, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**", i):
            parts.append(".*")
            i += 2
        else:
            parts.append({"*": "[^/]*", "?": "[^/]"}.get(pattern[i], re.escape(pattern[i])))
            i += 1
    return re.compile("".join(parts) + r"\Z")


def in_scope(path, patterns):
    return any(glob_regex(p).match(path) for p in patterns)


class Run:
    def __init__(self, work):
        self.work = Path(work).resolve()
        self.dir = self.work / ".devlyn/intent"
        self.path = self.dir / "run.json"

    def load(self, open_only=False):
        if not self.path.is_file():
            block("no-intent-run", "run `intent-gate.py start` first")
        state = loads(self.path.read_bytes())
        if open_only and state.get("verdict"):
            block("run-finished", state["verdict"]["verdict"])
        return state

    def save(self, state):
        atomic_write(self.path, (json.dumps(state, indent=2, sort_keys=True) + "\n").encode())

    def update(self, mutate):
        with PLATFORM["file_lock"](self.dir / ".lock", blocking=True):
            state = self.load(open_only=True)
            result = mutate(state)
            self.save(state)
            return result


def parse_args(tokens):
    values, flags, goal = {}, set(), []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token in VALUE_FLAGS:
            if token in values or i + 1 >= len(tokens) or tokens[i + 1].startswith("--"):
                block("invalid-flags", f"{token} needs exactly one value")
            values[token] = tokens[i + 1]
            i += 2
        elif token in BOOL_FLAGS:
            flags.add(token)
            i += 1
        elif token.startswith("--"):
            block("invalid-flags", f"unsupported flag {token}")
        else:
            goal.append(token)
            i += 1
    if {"--pair-verify", "--no-pair"} <= flags:
        block("invalid-flags", "--pair-verify and --no-pair are mutually exclusive")
    if "--verify-only" in values and "--spec" not in values:
        block("invalid-flags", "--verify-only requires --spec")
    if sum([bool(goal), "--goal-file" in values, "--spec" in values]) != 1:
        block("invalid-flags", "give exactly one of a goal, --goal-file or --spec")
    rounds = values.get("--max-rounds", "4")
    if not rounds.isdigit() or int(rounds) < 1:
        block("invalid-flags", "--max-rounds must be a positive integer")
    return values, flags, " ".join(goal), int(rounds)


def spec_verify():
    return runpy.run_path(str(SHARED / "spec-verify-check.py"))


def spec_contract(spec_path):
    """Return (expected file record, expected data, required checks) from the sibling or inline carrier."""
    svc = spec_verify()
    sibling = spec_path.with_name("spec.expected.json")
    if sibling.is_file():
        data, error = svc["load_expected_contract"](sibling)
        error = error or svc["validate_expected_against_sibling_spec"](spec_path, data)
        record = {"path": str(sibling), "sha256": sha(sibling.read_bytes())}
    else:
        found, block_text = svc["extract_verification_block"](spec_path.read_text(encoding="utf-8"))
        if not found:
            return None, None, []
        record, error, data = None, None, None
        try:
            data = svc["loads_strict_json"](block_text or "")
            error = svc["validate_inline_shape"](data)
        except ValueError as exc:
            error = str(exc)
    if error:
        block("invalid-spec-expected", error)
    required = [{"cmd": c["cmd"], "exit_code": c.get("exit_code", 0), "timeout_sec": c.get("timeout_sec", 60),
                 "stdout_contains": c.get("stdout_contains", []), "stdout_not_contains": c.get("stdout_not_contains", [])}
                for c in data.get("verification_commands", [])]
    return record, data, required


def resolve_roles(work, owner, values, flags):
    role_config = runpy.run_path(str(SHARED / "role-config.py"))
    try:
        run_input = None
        if "--role-config" in values:
            config, pin = role_config["read_config"](Path(values["--role-config"]), run=True)
            run_input = {**pin, "value": config}
        roles = role_config["resolve"](work, owner, flag_engine=values.get("--engine"), run_input=run_input,
                                       no_pair="--no-pair" in flags)
        for role, entry in roles["roles"].items():
            if entry.get("engine"):
                entry["argv"] = role_config["options"](entry, role)["argv"]
    except ValueError as exc:
        message = str(exc)
        raise Blocked(message if message.startswith("BLOCKED:") else f"BLOCKED:invalid-engine-config: {message}")
    if "--pair-verify" in flags and not roles["roles"]["pair_judge"].get("engine"):
        block("pair-unavailable", "--pair-verify needs an available OTHER engine")
    for role in ("primary_judge", "pair_judge"):
        engine = roles["roles"][role].get("engine")
        if engine and engine not in ("claude", "codex"):
            block("unsupported-review-engine", f"{role}={engine}; intent reviews run on claude or codex")
        if engine and shutil.which(engine) is None:
            block(f"{engine}-unavailable", f"{role} engine is not installed")
    worker = roles["roles"]["worker"]
    delegate = worker["engine"] != owner or bool(worker.get("model_requested") or worker.get("effort_requested"))
    if delegate and worker["engine"] != "codex":
        block("unsupported-delegation", f"worker={worker['engine']} under a {owner} owner; a Claude worker runs natively")
    if delegate and shutil.which("codex") is None:
        block("codex-unavailable", "the pinned codex worker is not installed")
    return roles, delegate


def cmd_start(args):
    work = Path.cwd().resolve()
    if Path(git(work, "rev-parse", "--show-toplevel")).resolve() != work:
        block("invalid-workdir", "run from the repository root")
    run = Run(work)
    run.dir.mkdir(parents=True, exist_ok=True)
    values, flags, goal, max_rounds = parse_args(args.tokens)
    with PLATFORM["file_lock"](run.dir / ".lock", blocking=True):
        if run.path.is_file():
            previous = loads(run.path.read_bytes())
            if not previous.get("verdict"):
                block("unfinished-run", f"{previous['run_id']} has no verdict; finish it first")
            archive = run.dir / "runs" / previous["run_id"]
            archive.mkdir(parents=True)
            for item in list(run.dir.iterdir()):
                if item.name not in ("runs", ".lock"):
                    item.rename(archive / item.name)
        verify_only = "--verify-only" in values
        if not verify_only and git(work, "status", "--porcelain", "--untracked-files=no", "--", ".", ":(exclude).devlyn"):
            block("worktree-dirty", "commit or stash tracked changes before an intent run")
        roles, delegate = resolve_roles(work, args.owner, values, flags)
        run_id = "in-" + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"-{os.getpid()}"
        contract, expected, required = {}, None, []
        if goal:
            atomic_write(run.dir / "goal.txt", goal.encode())
            contract["goal"] = {"path": str(run.dir / "goal.txt"), "sha256": sha(goal.encode())}
        for flag, key in (("--goal-file", "goal"), ("--spec", "spec")):
            if flag in values:
                path = (work / values[flag]).resolve()
                if not path.is_file():
                    block("invalid-flags", f"{flag} file not found: {values[flag]}")
                contract[key] = {"path": str(path), "sha256": sha(path.read_bytes())}
        if "spec" in contract:
            contract["expected"], expected, required = spec_contract(Path(contract["spec"]["path"]))
        if verify_only:
            ref = values["--verify-only"]
            supplied = Path(ref) if Path(ref).is_absolute() else work / ref
            patch = supplied.read_bytes() if supplied.is_file() else git(
                work, "diff", "--binary", "--no-ext-diff", "--src-prefix=a/", "--dst-prefix=b/", ref, raw=True)
            atomic_write(run.dir / "external-diff.patch", patch)
        untracked = git(work, "ls-files", "--others", "--exclude-standard", "-z", "--", ".", ":(exclude).devlyn", raw=True)
        state = {
            "version": 1, "run_id": run_id, "started_at": now(), "owner": args.owner,
            "mode": "verify-only" if verify_only else "spec" if "spec" in contract else "goal",
            "base_sha": git(work, "rev-parse", "HEAD"), "start_tree": tree(work), "max_rounds": max_rounds,
            "contract": contract, "expected": expected, "required_checks": required,
            "preexisting_untracked": sorted(p.decode() for p in untracked.split(b"\0") if p),
            "roles": roles, "delegate_required": delegate, "scope": None,
            "checks": [], "retired": [], "delegations": [], "reviews": [], "verdict": None,
        }
        run.save(state)
    pair = roles["roles"]["pair_judge"]
    print(json.dumps({"run_id": run_id, "mode": state["mode"], "delegate_required": delegate,
                      "primary": roles["roles"]["primary_judge"]["engine"],
                      "pair": pair.get("engine") or pair.get("skipped_reason"),
                      "required_checks": [c["cmd"] for c in required]}))


def cmd_scope(args):
    run = Run(Path.cwd())

    def mutate(state):
        if state["mode"] == "verify-only":
            block("invalid-flags", "verify-only runs have no scope")
        if state["scope"] is not None:
            block("scope-already-bound", "scope is bound once and never widened")
        for pattern in args.paths:
            if pattern.startswith("/") or ".." in pattern.split("/") or pattern.split("/")[0] == ".devlyn":
                block("invalid-scope", pattern)
        edits = changed(run.work, state["start_tree"], tree(run.work))
        if edits:
            block("scope-after-edit", "bind scope before the first change: " + ", ".join(edits[:5]))
        state["scope"] = sorted({p + "**" if p.endswith("/") else p for p in args.paths})
        return state["scope"]

    print(json.dumps({"scope": run.update(mutate)}))


def pending(work):
    """Uncommitted paths (tracked, staged or untracked) outside .devlyn/."""
    out = git(work, "status", "--porcelain", "-z", "--no-renames", "--untracked-files=all", "--", ".",
              ":(exclude).devlyn", raw=True)
    return [entry[3:].decode() for entry in out.split(b"\0") if entry]


def owned_changes(run, state):
    preexisting = set(state["preexisting_untracked"])
    return [p for p in changed(run.work, state["start_tree"], tree(run.work)) if p not in preexisting]


def cmd_commit(args):
    """Scoped commit of this run's own changes; everything else stays out of the commit."""
    run = Run(Path.cwd())

    def mutate(state):
        if state["scope"] is None:
            block("scope-unbound", "bind scope first")
        preexisting = set(state["preexisting_untracked"])
        touched = sorted(preexisting & set(changed(run.work, state["start_tree"], tree(run.work))))
        paths = [p for p in pending(run.work) if p not in preexisting]
        if touched:
            block("non-owned-change", ", ".join(touched))
        outside = [p for p in paths if not in_scope(p, state["scope"])]
        if outside:
            block("scope", ", ".join(outside))
        if not paths:
            return None
        staged = git(run.work, "diff", "--cached", "--name-only", "-z", "--no-renames", raw=True)
        foreign = sorted({p.decode() for p in staged.split(b"\0") if p} - set(paths))
        if foreign:
            block("staged-outside-run", ", ".join(foreign))
        git(run.work, "add", "-A", "--pathspec-from-file=-", "--pathspec-file-nul",
            env={**os.environ, "GIT_LITERAL_PATHSPECS": "1"}, stdin="".join(p + "\0" for p in paths).encode())
        git(run.work, "commit", "-q", "-m", args.message)
        return git(run.work, "rev-parse", "HEAD")

    print(json.dumps({"commit": run.update(mutate)}))


def survivors(marker):
    """PIDs still carrying this invocation's environment marker (POSIX). Windows jobs kill the whole tree."""
    needle = f"{MARKER}={marker}".encode()
    if sys.platform.startswith("linux"):
        found = []
        for entry in Path("/proc").iterdir():
            if entry.name.isdigit():
                try:
                    if needle in (entry / "environ").read_bytes().split(b"\0"):
                        found.append(int(entry.name))
                except OSError:
                    continue
        return found
    if sys.platform == "darwin":
        out = subprocess.run(["ps", "-A", "-E", "-ww", "-o", "pid=,command="], capture_output=True).stdout
        return [int(line.split()[0]) for line in out.splitlines() if needle in line.split()]
    return []


def subreaper():
    """Linux: orphaned descendants reparent to this process, so none can escape unseen (setsid, cleared env,
    redirected streams). Elsewhere the marker scan and the pipes are best-effort; Windows jobs kill the tree."""
    if not sys.platform.startswith("linux"):
        return False
    import ctypes
    return ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0) == 0  # PR_SET_CHILD_SUBREAPER


def orphans():
    found = []
    for entry in Path("/proc").iterdir():
        if entry.name.isdigit():
            try:
                if int((entry / "stat").read_text().rpartition(")")[2].split()[1]) == os.getpid():
                    found.append(int(entry.name))
            except (OSError, ValueError, IndexError):
                continue
    return found


def reap(marker, reaping):
    """Kill every surviving descendant; return how many were found."""
    killed = 0
    for _ in range(10):
        pids = set(survivors(marker)) | (set(orphans()) if reaping else set())
        if not pids:
            break
        killed += len(pids)
        for pid in pids:
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
        if reaping:
            for pid in pids:
                try:
                    os.waitpid(pid, 0)
                except ChildProcessError:
                    pass
        time.sleep(0.1)
    return killed


def run_bounded(work, argv, seconds, out_base, stdin_file=None, env=None):
    """Run through run-bounded.py (tree kill, 124 on timeout). Termination is affirmative when no descendant
    survives the reap and none still holds the output pipes."""
    marker = out_base.name
    reaping = subreaper()
    command = [sys.executable, str(SHARED / "run-bounded.py"), str(seconds)]
    if stdin_file:
        command += ["--stdin-file", str(stdin_file), "--record-transport"]
    streams = {}
    started = time.monotonic()
    proc = subprocess.Popen([*command, "--", *argv], cwd=work, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            stdin=subprocess.DEVNULL, env={**(env or os.environ), MARKER: marker})

    def drain(name, pipe):
        streams[name] = b"".join(iter(lambda: pipe.read(65536), b""))

    readers = [threading.Thread(target=drain, args=(n, p), daemon=True)
               for n, p in (("stdout", proc.stdout), ("stderr", proc.stderr))]
    for reader in readers:
        reader.start()
    code = proc.wait()
    elapsed = time.monotonic() - started
    leaked = reap(marker, reaping)
    deadline = time.monotonic() + STREAM_GRACE
    for reader in readers:
        reader.join(max(0, deadline - time.monotonic()))
    terminated = not survivors(marker) and not (reaping and orphans()) and not any(r.is_alive() for r in readers)
    record = {"exit": code, "timed_out": code == 124 and elapsed >= seconds, "terminated": terminated,
              "termination_evidence": "subreaper" if reaping else "job" if os.name == "nt" else "marker+pipes",
              "leaked_killed": leaked, "duration_ms": int(elapsed * 1000)}
    for name in ("stdout", "stderr"):
        raw = streams.get(name, b"")
        path = out_base.with_name(out_base.name + "." + name)
        atomic_write(path, raw)
        record[name] = {"path": str(path.relative_to(work)), "sha256": sha(raw)}
    return record, streams.get("stdout", b""), streams.get("stderr", b"")


def shell_argv(cmd):
    if os.name == "nt":
        return [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/s", "/c", cmd]
    return ["/bin/sh", "-c", cmd]


def stamp():
    return f"{time.time_ns()}-{os.getpid()}"


def cmd_check(args):
    run = Run(Path.cwd())
    state = run.load(open_only=True)
    required = next((r for r in state["required_checks"] if r["cmd"] == args.cmd), None)
    seconds = args.timeout or (required["timeout_sec"] if required else 1800)
    before = source(run.work)
    record, _, _ = run_bounded(run.work, shell_argv(args.cmd), seconds, run.dir / "checks" / stamp())
    record.update(cmd=args.cmd, source=before, source_after=source(run.work), at=now())
    run.update(lambda s: s["checks"].append(record))
    print(json.dumps({k: record[k] for k in ("exit", "timed_out", "terminated", "leaked_killed")}
                     | {"stdout": record["stdout"]["path"], "stderr": record["stderr"]["path"],
                        "source_changed_during_run": record["source"] != record["source_after"]}))


def cmd_retire(args):
    """Drop a superseded or invalid probe from the obligations, visibly. Required checks cannot be retired."""
    run = Run(Path.cwd())

    def mutate(state):
        if any(r["cmd"] == args.cmd for r in state["required_checks"]):
            block("required-check", "spec.expected verification commands cannot be retired")
        if not any(c["cmd"] == args.cmd for c in state["checks"]):
            block("unknown-check", args.cmd)
        state["retired"].append({"cmd": args.cmd, "reason": args.reason, "at": now()})

    run.update(mutate)
    print(json.dumps({"retired": args.cmd}))


IGNORED_OPTION = re.compile(r"(?im)^.*(?:model|effort).*\b(?:ignor\w*|clamp\w*|unsupported|not supported)\b")


def option(argv, flag):
    values = [argv[i + 1] for i, item in enumerate(argv[:-1]) if item == flag]
    return values[-1] if values else None


def authenticate(run, role, argv, stderr, sandbox, claude_model=None):
    """Return (model, effort, error) from native evidence. Codex: its header must show this worktree, the
    dispatched sandbox and effort; Claude: the result's model, with effort bound by the dispatched argv."""
    text = stderr.decode(errors="replace")
    if role["engine"] == "codex":
        diagnostics = text.partition("\nuser\n")[0]
        try:
            header = runpy.run_path(str(SHARED / "judge-role-evidence.py"))["codex_header"](text)
        except (ValueError, SystemExit) as exc:
            return None, None, f"codex header: {exc}"
        model, effort = header["model"], header["reasoning effort"]
        efforts = [c.split("=", 1)[1].strip('"') for c in (argv[i + 1] for i, a in enumerate(argv[:-1]) if a == "-c")
                   if c.startswith("model_reasoning_effort=")]
        if Path(header["workdir"]).resolve() != run.work or header["sandbox"].split()[0] != sandbox:
            return model, effort, f"observed workdir/sandbox {header['workdir']}/{header['sandbox']} differs from the run"
        if efforts and effort != efforts[-1]:
            return model, effort, f"native effort {effort} differs from dispatched {efforts[-1]}"
    else:
        diagnostics, model, effort = text, claude_model, option(argv, "--effort")
    if IGNORED_OPTION.search(diagnostics):
        return model, effort, "a native diagnostic rejected or ignored an explicit option"
    for want, got in ((role.get("model_requested"), model and model.split("[")[0]), (role.get("effort_requested"), effort)):
        if want and want != got:
            return model, effort, f"model mismatch: requested {role.get('model_requested')}/{role.get('effort_requested')}, observed {model}/{effort}"
    return model, effort, None


def cmd_delegate(args):
    run = Run(Path.cwd())
    state = run.load(open_only=True)
    if not state["delegate_required"]:
        block("delegation-not-configured", "the worker role is this owner; implement here")
    if state["scope"] is None:
        block("scope-unbound", "bind scope before delegating the edit")
    worker = state["roles"]["roles"]["worker"]
    prompt = Path(args.prompt_file).resolve()
    env = {**os.environ, "DEVLYN_CODEX_PROMPT_FILE": str(prompt), "CODEX_MONITORED_ALLOW_PIPED": "1"}
    argv = ["bash", str(SHARED / "codex-monitored.sh"), "-C", str(run.work), "-s", "workspace-write",
            "-c", "sandbox_workspace_write.network_access=false", *worker["argv"], "-"]
    before = tree(run.work)
    record, _, stderr = run_bounded(run.work, argv, args.timeout, run.dir / "delegations" / stamp(), env=env)
    model, effort, error = authenticate(run, worker, argv, stderr, "workspace-write")
    preexisting = set(state["preexisting_untracked"])
    record.update(prompt_sha256=sha(prompt.read_bytes()), model_requested=worker.get("model_requested"),
                  effort_requested=worker.get("effort_requested"), model_observed=model, effort_observed=effort,
                  identity_error=error, at=now())
    after = tree(run.work)
    record["paths"] = blobs(run.work, after, [p for p in changed(run.work, before, after) if p not in preexisting])
    run.update(lambda s: s["delegations"].append(record))
    print(json.dumps({k: record[k] for k in ("exit", "terminated", "model_observed", "identity_error", "paths")}
                     | {"stdout": record["stdout"]["path"]}))


def review_body():
    found = [p / "references/review.md" for p in SHARED.parent.glob("devlyn*intent") if (p / "references/review.md").is_file()]
    if len(found) != 1:
        block("shared-dir-unresolved", "devlyn:intent/references/review.md")
    return found[0].read_text(encoding="utf-8")


def tail(path, limit=6000):
    return path.read_bytes()[-limit:].decode(errors="replace")


def latest_checks(state, key):
    latest = {}
    for check in state["checks"]:
        if check["source"] == key and check["source_after"] == key:
            latest[check["cmd"]] = check
    return latest


def review_prompt(run, state, key):
    parts = [review_body(), "\n## Contract\n"]
    for name in ("goal", "spec", "expected"):
        item = state["contract"].get(name)
        if item:
            parts.append(f"\n### {name}: {item['path']}\n\n{Path(item['path']).read_text(errors='replace')}\n")
    if state["mode"] == "verify-only":
        parts.append("\n## Diff under review\n\n" + (run.dir / "external-diff.patch").read_text(errors="replace"))
    else:
        parts.append("\n## Authorized scope\n\n" + "\n".join(state["scope"]) + "\n")
        parts.append("\n## Diff of this run\n\n" + git(run.work, "diff", "--no-color", "--no-ext-diff",
                                                         state["start_tree"], key.split(":")[1]))
    parts.append("\n## Checks on this source\n")
    for check in latest_checks(state, key).values():
        parts.append(f"\n$ {check['cmd']}\nexit {check['exit']}{' (timed out)' if check['timed_out'] else ''}\n"
                     f"--- stdout (tail)\n{tail(run.work / check['stdout']['path'])}\n"
                     f"--- stderr (tail)\n{tail(run.work / check['stderr']['path'])}\n")
    for item in state["retired"]:
        parts.append(f"\nRetired by the owner: `{item['cmd']}` — {item['reason']}\n")
    return "".join(parts).encode()


def binding(finding):
    severity = str(finding.get("severity", "")).upper()
    return severity in ("CRITICAL", "HIGH") or (severity == "MEDIUM" and finding.get("verdict_binding") is True)


def judge(run, engine, record, stdout):
    """Return (status, findings, claude model, error). Only an exit-0, parsed, verdict-terminated reply can pass."""
    if record["timed_out"]:
        return "TIMEOUT", [], None, "reviewer timed out"
    if record["exit"] != 0:
        return "BLOCKED", [], None, f"reviewer exited {record['exit']}"
    model, text = None, stdout.decode(errors="replace")
    if engine == "claude":
        try:
            raw, model, _ = runpy.run_path(str(SHARED / "judge-role-evidence.py"))["claude_result"](stdout, 0)
        except (ValueError, SystemExit) as exc:
            return "BLOCKED", [], None, f"claude result: {exc}"
        text = raw.decode()
    try:
        findings, summary = runpy.run_path(str(SHARED / "judge-output-parser.py"))["collect_text"](
            text, run.work / record["stdout"]["path"])
    except SystemExit as exc:
        return "BLOCKED", [], model, f"unparseable review: {exc}"
    if summary is None:
        return "BLOCKED", findings, model, "review has no terminal verdict line"
    if any(binding(f) for f in findings) or summary["verdict"] in ("NEEDS_WORK", "FAIL"):
        return "NEEDS_WORK", findings, model, None
    if summary["verdict"] == "BLOCKED":
        return "BLOCKED", findings, model, "reviewer reported BLOCKED"
    return ("PASS_WITH_ISSUES" if findings else "PASS"), findings, model, None


def cmd_review(args):
    run = Run(Path.cwd())
    state = run.load(open_only=True)
    role = state["roles"]["roles"][args.role]
    if not role.get("engine") or role.get("skipped_reason"):
        block("pair-unavailable", role.get("skipped_reason") or "no OTHER engine")
    if state["mode"] != "verify-only" and state["scope"] is None:
        block("scope-unbound", "bind scope before review")
    key = source(run.work)
    rounds = {r["source"] for r in state["reviews"] if r["role"] == "primary_judge"} | {key}
    if args.role == "primary_judge" and len(rounds) > state["max_rounds"]:
        block("review-exhausted", f"max_rounds={state['max_rounds']}")
    name = stamp()
    base = run.dir / "reviews" / name
    prompt = base.with_name(name + ".prompt")
    atomic_write(prompt, review_prompt(run, state, key))
    if role["engine"] == "claude":
        argv = ["claude", "-p", "--output-format", "json", "--permission-mode", "dontAsk",
                "--tools", "Read,Grep,Glob", "--allowedTools", "Read,Grep,Glob", "--setting-sources", "project",
                "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}', *role["argv"]]
        record, stdout, stderr = run_bounded(run.work, argv, 600, base, stdin_file=prompt)
    else:
        env = {**os.environ, "DEVLYN_CODEX_PROMPT_FILE": str(prompt), "CODEX_MONITORED_ISOLATED": "1",
               "CODEX_MONITORED_TIMEOUT_SEC": "600", "CODEX_MONITORED_ALLOW_PIPED": "1"}
        effort = [] if role.get("effort_requested") else ["-c", "model_reasoning_effort=high"]
        argv = ["bash", str(SHARED / "codex-monitored.sh"), "-C", str(run.work), "-s", "read-only",
                *role["argv"], *effort, "-"]
        record, stdout, stderr = run_bounded(run.work, argv, 600, base, env=env)
        record["timed_out"] = record["timed_out"] or record["exit"] == 124
    status, findings, model, error = judge(run, role["engine"], record, stdout)
    effort_seen, identity_error = None, None
    if record["exit"] == 0 and not record["timed_out"]:
        model, effort_seen, identity_error = authenticate(run, role, argv, stderr, "read-only", model)
        if identity_error:
            status, error = "BLOCKED", identity_error
    findings_path = base.with_name(name + ".findings.jsonl")
    atomic_write(findings_path, "".join(json.dumps(f, sort_keys=True) + "\n" for f in findings).encode())
    record.update(role=args.role, engine=role["engine"], source=key, source_after=source(run.work), status=status,
                  error=error, model_requested=role.get("model_requested"), effort_requested=role.get("effort_requested"),
                  model_observed=model, effort_observed=effort_seen, identity_error=identity_error,
                  prompt_sha256=sha(prompt.read_bytes()), binding=sum(binding(f) for f in findings),
                  findings={"path": str(findings_path.relative_to(run.work)), "sha256": sha(findings_path.read_bytes())},
                  at=now())
    run.update(lambda s: s["reviews"].append(record))
    print(json.dumps({"status": status, "error": error, "model_observed": model, "findings": findings}, indent=2))


def meets(check, expectation, work):
    if check["timed_out"] or check["exit"] != expectation.get("exit_code", 0):
        return False
    out = (work / check["stdout"]["path"]).read_bytes().decode(errors="replace")
    return (all(s in out for s in expectation.get("stdout_contains", []))
            and not any(s in out for s in expectation.get("stdout_not_contains", [])))


def expected_findings(run, state):
    if not state["expected"]:
        return []
    devlyn = run.dir if state["mode"] == "verify-only" else run.dir / "no-external-diff"
    findings, _ = spec_verify()["expected_contract_findings"](
        state["expected"], Path(state["contract"]["expected"]["path"]) if state["contract"].get("expected") else None,
        run.work, devlyn, {"base_ref": {"sha": state["base_sha"]}}, 1)
    return [f for f in findings if f.get("blocking")]


def evaluate(run, state):
    """Return (verdict, reasons, notes, key). PASS only when every rule holds on the current source."""
    work, blocked, needed, notes = run.work, [], [], []
    key = source(work)
    for name, item in state["contract"].items():
        if item and (not Path(item["path"]).is_file() or sha(Path(item["path"]).read_bytes()) != item["sha256"]):
            blocked.append(f"contract-changed: {name}")
    if subprocess.run(["git", "merge-base", "--is-ancestor", state["base_sha"], "HEAD"], cwd=work).returncode != 0:
        blocked.append("base-moved")
    preexisting = set(state["preexisting_untracked"])
    touched = set(changed(work, state["start_tree"], key.split(":")[1])) | set(changed(work, state["base_sha"], "HEAD"))
    for path in sorted(preexisting & touched):
        blocked.append(f"non-owned-change: {path}")
    owned = owned_changes(run, state)
    if state["mode"] == "verify-only":
        if owned:
            blocked.append("verify-only-changed-source: " + ", ".join(owned[:5]))
    else:
        if state["scope"] is None:
            blocked.append("scope-unbound")
        elif not owned:
            blocked.append("implement-empty")
        else:
            blocked += [f"scope: {p}" for p in owned if not in_scope(p, state["scope"])]
        uncommitted = [p for p in pending(work) if p not in preexisting]
        if uncommitted:
            needed.append("uncommitted changes (run `intent-gate.py commit`): " + ", ".join(uncommitted[:5]))
    for kind in ("checks", "delegations", "reviews"):
        for item in state[kind]:
            for stream in [item["stdout"], item["stderr"]] + ([item["findings"]] if "findings" in item else []):
                path = work / stream["path"]
                if not path.is_file() or sha(path.read_bytes()) != stream["sha256"]:
                    blocked.append(f"evidence-changed: {stream['path']}")
            if not item["terminated"]:
                blocked.append(f"termination-failed: {kind} {item.get('cmd') or item['stdout']['path']}")
            if item.get("leaked_killed"):
                notes.append(f"{kind} left {item['leaked_killed']} process(es) running; killed: {item.get('cmd') or item['stdout']['path']}")
            if item.get("identity_error") and (kind == "delegations" or item["exit"] == 0):
                blocked.append(f"identity: {kind}: {item['identity_error']}")
            if item.get("termination_evidence") == "marker+pipes" and "termination is best-effort on this OS (no subreaper)" not in notes:
                notes.append("termination is best-effort on this OS (no subreaper)")
    if state["delegate_required"] and state["mode"] != "verify-only":
        produced = {}
        for d in state["delegations"]:
            if d["exit"] == 0 and not d["identity_error"]:
                produced.update(d["paths"])
        final = blobs(work, key.split(":")[1], owned)
        missing = [p for p in owned if p not in produced or produced[p] != final[p]]
        if not produced or missing:
            blocked.append("executor-not-used: the selected worker did not produce "
                           + (", ".join(missing[:5]) if produced else "any change"))
    latest = latest_checks(state, key)
    retired = {r["cmd"] for r in state["retired"]}
    required = {r["cmd"] for r in state["required_checks"]}
    pure_design = bool(state["expected"] and state["expected"].get("pure_design") is True)
    if state["mode"] != "verify-only" and not set(latest) - retired and not pure_design:
        needed.append("no check ran on the current source")
    for cmd in sorted({c["cmd"] for c in state["checks"]} - set(latest) - retired - required):
        needed.append(f"stale check (rerun on the current source or retire it): {cmd}")
    for expectation in state["required_checks"]:
        cmd = expectation["cmd"]
        check = latest.get(cmd)
        if check is None:
            needed.append(f"required check missing on the current source: {cmd}")
        elif not meets(check, expectation, work):
            needed.append(f"required check failed: {cmd} (exit {check['exit']}{', timed out' if check['timed_out'] else ''})")
    for cmd, check in latest.items():
        if cmd not in required and cmd not in retired and (check["exit"] != 0 or check["timed_out"]):
            needed.append(f"check failed: {cmd} (exit {check['exit']}{', timed out' if check['timed_out'] else ''})")
    for finding in expected_findings(run, state):
        needed.append(f"expected contract: {finding['rule_id']}: {finding['message']}")
    roles = state["roles"]["roles"]
    for role in ("primary_judge", "pair_judge"):
        if not roles[role].get("engine") or roles[role].get("skipped_reason"):
            notes.append(f"{role} skipped: {roles[role].get('skipped_reason')}")
            continue
        current = [r for r in state["reviews"] if r["role"] == role and r["source"] == key and r["source_after"] == key]
        status = current[-1]["status"] if current else None
        content = key.split(":")[1]
        if any(r["role"] == role and r["status"] == "NEEDS_WORK" and r["source"] == r["source_after"]
               and r["source"].split(":")[1] == content for r in state["reviews"]):
            status = "NEEDS_WORK"  # a retry or an empty commit on the same content never erases a binding finding
        if status is None:
            needed.append(f"{role} review missing on the current source")
        elif status == "NEEDS_WORK":
            needed.append(f"{role} review has binding findings")
        elif status == "TIMEOUT" and role == "pair_judge":
            notes.append("pair_judge TIMEOUT: the verdict rests on the primary review alone")
        elif status in ("BLOCKED", "TIMEOUT"):
            blocked.append(f"{role} review {status}: {current[-1]['error']}")
    for item in state["retired"]:
        notes.append(f"retired check: {item['cmd']} — {item['reason']}")
    verdict = "BLOCKED" if blocked else "NEEDS_WORK" if needed else "PASS"
    return verdict, blocked + needed, notes, key


def cmd_status(args):
    run = Run(Path.cwd())
    verdict, reasons, notes, key = evaluate(run, run.load())
    print(json.dumps({"verdict": verdict, "reasons": reasons, "notes": notes, "source": key}, indent=2))


def cmd_finish(args):
    run = Run(Path.cwd())

    def mutate(state):
        verdict, reasons, notes, key = evaluate(run, state)
        result = {"verdict": verdict, "reasons": reasons, "notes": notes, "source": key, "at": now(),
                  "source_sha": key.split(":")[0] if verdict == "PASS" and state["mode"] != "verify-only" else None}
        if result["source_sha"]:
            acceptance = {"kind": "direct", "task": args.task, "source_sha": result["source_sha"],
                          "checks": [{"command": c["cmd"], "evidence": c["stdout"]["path"]}
                                     for c in latest_checks(state, key).values()]}
            atomic_write(run.work / ".devlyn/acceptance.json", (json.dumps(acceptance, indent=2) + "\n").encode())
        state["verdict"] = result
        return result

    result = run.update(mutate)
    atomic_write(run.dir / "verdict.json", (json.dumps(result, indent=2) + "\n").encode())
    print(json.dumps(result, indent=2))
    return 0 if result["verdict"] == "PASS" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--self-test", action="store_true")
    sub = parser.add_subparsers(dest="command")
    start = sub.add_parser("start")
    start.add_argument("--owner", choices=("claude", "codex"), required=True)
    start.add_argument("tokens", nargs=argparse.REMAINDER)
    sub.add_parser("scope").add_argument("paths", nargs="+")
    sub.add_parser("commit").add_argument("--message", required=True)
    check = sub.add_parser("check")
    check.add_argument("--cmd", required=True)
    check.add_argument("--timeout", type=int)
    retire = sub.add_parser("retire")
    retire.add_argument("--cmd", required=True)
    retire.add_argument("--reason", required=True)
    delegate = sub.add_parser("delegate")
    delegate.add_argument("--prompt-file", required=True)
    delegate.add_argument("--timeout", type=int, default=5400)
    sub.add_parser("review").add_argument("--role", choices=("primary_judge", "pair_judge"), required=True)
    sub.add_parser("status")
    sub.add_parser("finish").add_argument("--task", required=True)
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if args.command == "start" and args.tokens[:1] == ["--"]:
        args.tokens = args.tokens[1:]
    handlers = {"start": cmd_start, "scope": cmd_scope, "commit": cmd_commit, "check": cmd_check,
                "retire": cmd_retire, "delegate": cmd_delegate, "review": cmd_review, "status": cmd_status,
                "finish": cmd_finish}
    if args.command not in handlers:
        parser.error("a command is required")
    try:
        return handlers[args.command](args) or 0
    except Blocked as exc:
        print(str(exc), file=sys.stderr)
        return 2


FAKE_CLAUDE = r"""#!/usr/bin/env python3
import json, os, sys
if sys.argv[1:] == ["--version"]:
    print("2.1.281 (Claude Code)"); sys.exit(0)
sys.stdin.read()
if os.environ.get("FAKE_CLAUDE_EDIT"):
    path, _, text = os.environ["FAKE_CLAUDE_EDIT"].partition(":")
    open(path, "w").write(text)
model = os.environ.get("FAKE_CLAUDE_MODEL", "claude-test-a")
print(json.dumps({"type": "result", "subtype": "success", "is_error": False, "stop_reason": "end_turn",
                  "session_id": "s1", "result": os.environ.get("FAKE_CLAUDE_REVIEW", "PASS"),
                  "modelUsage": {model + "[1m]": {"inputTokens": 1, "outputTokens": 1}}}))
"""
FAKE_CODEX = r"""#!/usr/bin/env python3
import os, pathlib, sys
if sys.argv[1:] == ["--version"]:
    print("codex-cli 0.156.1"); sys.exit(0)
sys.stdin.read()
args = sys.argv[1:]
sandbox = args[args.index("-s") + 1] if "-s" in args else "read-only"
sandbox += " [workdir, /tmp, $TMPDIR]" if sandbox == "workspace-write" else ""
effort = [a.split("=", 1)[1] for a in args if a.startswith("model_reasoning_effort=")]
sys.stderr.write(os.environ.get("FAKE_CODEX_WARN", "") + "OpenAI Codex v0.156.1\n--------\nworkdir: %s\nmodel: %s\n"
                 "provider: openai\nsandbox: %s\nreasoning effort: %s\nsession id: s2\n--------\nuser\nprompt\n"
                 % (os.environ.get("FAKE_CODEX_WORKDIR", os.getcwd()), os.environ.get("FAKE_CODEX_MODEL", "gpt-6-astra"),
                    sandbox, os.environ.get("FAKE_CODEX_EFFORT", effort[-1] if effort else "medium")))
edit = os.environ.get("FAKE_CODEX_EDIT")
if edit:
    path, _, text = edit.partition(":")
    pathlib.Path(path).write_text(text)
print(os.environ.get("FAKE_CODEX_REVIEW", "PASS"))
sys.exit(int(os.environ.get("FAKE_CODEX_EXIT", "0")))
"""
LEAK_REDIRECTED = ("python3 -c \"import os,time\nif os.fork()==0:\n os.setsid(); n=os.open(os.devnull,os.O_RDWR)"
                   "\n os.dup2(n,1); os.dup2(n,2); time.sleep(30)\"")
LEAK_UNMARKED = ("python3 -c \"import os\nif os.fork()==0:\n os.setsid(); os.execve('/bin/sleep',['sleep','30'],{})\"")
LEAK_HIDDEN = ("python3 -c \"import os\nif os.fork()==0:\n os.setsid(); n=os.open(os.devnull,os.O_RDWR); os.dup2(n,1); os.dup2(n,2)"
               "\n os.execve('/bin/sleep',['sleep','30'],{})\"")


def self_test():
    gate = Path(__file__).resolve()
    failures = []

    def expect(name, condition):
        print(("ok   " if condition else "FAIL ") + name, flush=True)
        if not condition:
            failures.append(name)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        fake = root / "bin"
        fake.mkdir()
        for name, body in (("claude", FAKE_CLAUDE), ("codex", FAKE_CODEX)):
            (fake / name).write_text(body)
            (fake / name).chmod(0o755)
        (root / "codex-home").mkdir()
        (root / "codex-home/models_cache.json").write_text(json.dumps({"client_version": "0.156.1", "models": [
            {"slug": s, "supported_reasoning_levels": [{"effort": "high"}, {"effort": "low"}]}
            for s in ("gpt-6-sol", "gpt-6-astra")]}))
        base_env = {k: v for k, v in os.environ.items() if not k.startswith("FAKE_")}
        base_env.update(PATH=f"{fake}{os.pathsep}{os.environ['PATH']}", CODEX_HOME=str(root / "codex-home"),
                        CODEX_MONITORED_HEARTBEAT="1")

        def repo(name, roles=None, files=None):
            work = root / name
            work.mkdir()
            for args in (("init", "-q", "-b", "main"), ("config", "user.email", "t@t"), ("config", "user.name", "t"),
                         ("config", "commit.gpgsign", "false")):
                subprocess.run(["git", *args], cwd=work, check=True)
            for path, text in {"app.txt": "broken\n", ".gitignore": ".devlyn/\n", **(files or {})}.items():
                (work / path).write_text(text)
            subprocess.run(["git", "add", "-A"], cwd=work, check=True)
            subprocess.run(["git", "commit", "-qm", "base"], cwd=work, check=True)
            if roles:
                (work / ".devlyn").mkdir()
                (work / ".devlyn/engines.json").write_text(json.dumps({"roles": roles}))
            return work

        def g(work, *args, env=None):
            return subprocess.run([sys.executable, str(gate), *args], cwd=work, capture_output=True, text=True,
                                  env={**base_env, **(env or {})})

        def status(work):
            return json.loads(g(work, "status").stdout)

        def reasons(work, text):
            return any(text in r for r in status(work)["reasons"])

        def evidence(work, cmd="grep -q fixed app.txt", env=None, pair_env=None):
            g(work, "check", "--cmd", cmd)
            g(work, "review", "--role", "primary_judge", env=env)
            g(work, "review", "--role", "pair_judge", env=pair_env or env)

        def happy(work, *tokens, env=None, pair_env=None, edit="fixed\n"):
            g(work, "start", "--owner", "claude", "--", *(tokens or ("fix", "app")))
            g(work, "scope", "app.txt")
            (work / "app.txt").write_text(edit)
            g(work, "commit", "--message", "fix app")
            evidence(work, env=env, pair_env=pair_env)

        # Stale evidence: a later edit or commit invalidates checks and reviews.
        work = repo("stale")
        happy(work)
        expect("committed change with fresh check and dual review passes", status(work)["verdict"] == "PASS")
        (work / "app.txt").write_text("fixed again\n")
        expect("an uncommitted later edit is not PASS", reasons(work, "uncommitted changes"))
        g(work, "commit", "--message", "again")
        expect("a new commit makes earlier checks and reviews stale",
               reasons(work, "primary_judge review missing") and reasons(work, "no check ran on the current source"))
        evidence(work)
        done = g(work, "finish", "--task", "t1")
        acceptance = json.loads((work / ".devlyn/acceptance.json").read_text())
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=work, capture_output=True, text=True).stdout.strip()
        expect("finish binds direct acceptance to the verified commit",
               done.returncode == 0 and acceptance == {**acceptance, "kind": "direct", "task": "t1", "source_sha": head})
        expect("a finished run refuses more evidence", "run-finished" in g(work, "check", "--cmd", "true").stderr)

        # Failed exit: the latest attempt on the current source decides.
        work = repo("exit")
        happy(work)
        g(work, "check", "--cmd", "exit 1")
        expect("a failing check on the current source is NEEDS_WORK", status(work)["verdict"] == "NEEDS_WORK")
        (work / ".devlyn/flag").write_text("")
        g(work, "check", "--cmd", "test -f .devlyn/flag")
        (work / ".devlyn/flag").unlink()
        g(work, "check", "--cmd", "test -f .devlyn/flag")
        expect("a later failure overrides an earlier pass on the same source", reasons(work, "check failed: test -f"))
        g(work, "retire", "--cmd", "exit 1", "--reason", "bad probe")
        g(work, "retire", "--cmd", "test -f .devlyn/flag", "--reason", "bad probe")
        expect("retired probes stop blocking and stay visible",
               status(work)["verdict"] == "PASS" and sum("retired check" in n for n in status(work)["notes"]) == 2)
        out = g(work, "finish", "--task", "t")
        expect("finish exit code follows the verdict", out.returncode == 0)
        work = repo("exit-finish")
        happy(work)
        g(work, "check", "--cmd", "exit 1")
        expect("a failed finish writes no acceptance", g(work, "finish", "--task", "t").returncode == 1
               and not (work / ".devlyn/acceptance.json").exists())

        # Scope: out-of-scope and late binding are refused.
        work = repo("scope")
        happy(work)
        (work / "other.txt").write_text("x\n")
        expect("commit refuses an out-of-scope path", "BLOCKED:scope" in g(work, "commit", "--message", "x").stderr)
        subprocess.run(["git", "add", "other.txt"], cwd=work, check=True)
        subprocess.run(["git", "commit", "-qm", "sneak"], cwd=work, check=True)
        expect("an out-of-scope commit blocks the verdict", reasons(work, "scope: other.txt"))
        expect("scope cannot be rebound or widened", "scope-already-bound" in g(work, "scope", "**").stderr)
        work = repo("scope-late")
        g(work, "start", "--owner", "claude", "--", "fix")
        (work / "app.txt").write_text("fixed\n")
        expect("scope bound after an edit is refused", "scope-after-edit" in g(work, "scope", "app.txt").stderr)

        # Model identity: reviewers and the selected executor.
        work = repo("model", roles={"primary_judge": {"engine": "claude", "model": "claude-test-a"}})
        happy(work, env={"FAKE_CLAUDE_MODEL": "claude-test-b"})
        expect("a reviewer on the wrong model blocks", status(work)["verdict"] == "BLOCKED" and reasons(work, "model mismatch"))
        work = repo("model-ok", roles={"primary_judge": {"engine": "claude", "model": "claude-test-a"}})
        happy(work)
        expect("a reviewer on the requested model (1m suffix) passes", status(work)["verdict"] == "PASS")

        def delegated(name, roles, env):
            work = repo(name, roles=roles)
            g(work, "start", "--owner", "claude", "--", "fix")
            g(work, "scope", "app.txt")
            (work / ".devlyn/delegate.prompt").write_text("fix app.txt")
            out = g(work, "delegate", "--prompt-file", ".devlyn/delegate.prompt", env={"FAKE_CODEX_EDIT": "app.txt:fixed\n", **env})
            g(work, "commit", "--message", "fix")
            evidence(work)
            return work, json.loads(out.stdout or "{}")

        work, out = delegated("delegate", {"worker": {"engine": "codex", "model": "gpt-6-sol"}}, {"FAKE_CODEX_MODEL": "gpt-6-astra"})
        expect("an executor on the wrong model blocks", bool(out.get("identity_error")) and reasons(work, "identity: delegations"))
        work, out = delegated("delegate-effort", {"worker": {"engine": "codex", "model": "gpt-6-sol", "effort": "high"}},
                              {"FAKE_CODEX_MODEL": "gpt-6-sol", "FAKE_CODEX_EFFORT": "low"})
        expect("an executor on the wrong effort blocks", bool(out.get("identity_error")) and status(work)["verdict"] == "BLOCKED")
        out = g(repo("effort-only", roles={"worker": {"engine": "codex", "effort": "high"}}), "start", "--owner", "claude", "--", "x")
        expect("an effort without a resolvable model fails closed at start", "unsupported-role-option" in out.stderr)
        work, out = delegated("delegate-ok", {"worker": {"engine": "codex", "model": "gpt-6-sol"}}, {"FAKE_CODEX_MODEL": "gpt-6-sol"})
        expect("a matching delegated executor can pass", status(work)["verdict"] == "PASS")
        work = repo("delegate-skip", roles={"worker": {"engine": "codex", "model": "gpt-6-sol"}})
        happy(work)
        expect("skipping the selected executor blocks", reasons(work, "executor-not-used"))
        work, _ = delegated("delegate-noop", {"worker": {"engine": "codex", "model": "gpt-6-sol"}},
                            {"FAKE_CODEX_MODEL": "gpt-6-sol", "FAKE_CODEX_EDIT": ""})
        (work / "app.txt").write_text("owner wrote this\n")
        g(work, "commit", "--message", "owner")
        evidence(work, cmd="true")
        expect("a no-op delegation does not cover the owner's own edit", reasons(work, "executor-not-used"))
        work, _ = delegated("delegate-overwrite", {"worker": {"engine": "codex", "model": "gpt-6-sol"}}, {"FAKE_CODEX_MODEL": "gpt-6-sol"})
        (work / "app.txt").write_text("fixed by the owner instead\n")
        g(work, "commit", "--message", "owner")
        evidence(work)
        expect("owner content replacing the executor's edit is refused", reasons(work, "executor-not-used: the selected worker did not produce app.txt"))
        work, _ = delegated("delegate-mode", {"worker": {"engine": "codex", "model": "gpt-6-sol"}}, {"FAKE_CODEX_MODEL": "gpt-6-sol"})
        (work / "app.txt").chmod(0o755)
        g(work, "commit", "--message", "mode")
        evidence(work)
        expect("an owner mode change after delegation is refused", reasons(work, "executor-not-used"))
        work = repo("verify-only-worker", roles={"worker": {"engine": "codex", "model": "gpt-6-sol"}}, files={"spec.md": "# s\n"})
        g(work, "start", "--owner", "claude", "--", "--verify-only", "HEAD", "--spec", "spec.md")
        g(work, "review", "--role", "primary_judge")
        g(work, "review", "--role", "pair_judge")
        expect("verify-only never requires the executor", status(work)["verdict"] == "PASS")
        work = repo("workdir")
        happy(work, pair_env={"FAKE_CODEX_WORKDIR": "/elsewhere"})
        expect("a codex header for another worktree blocks", reasons(work, "observed workdir/sandbox"))
        work = repo("ignored")
        happy(work, pair_env={"FAKE_CODEX_WARN": "warning: model override ignored\n"})
        expect("a native ignored-option diagnostic blocks", reasons(work, "ignored an explicit option"))
        fake_run = Run(root)
        role = {"engine": "claude", "model_requested": None, "effort_requested": "high"}
        expect("a Claude effort is bound by the dispatched argv",
               authenticate(fake_run, role, ["claude", "--effort", "high"], b"", "read-only", "m")[2] is None
               and authenticate(fake_run, role, ["claude", "--effort", "low"], b"", "read-only", "m")[2] is not None)

        # Non-owned: a pre-existing untracked file is never changed or committed by the run.
        work = repo("nonowned")
        (work / "notes.txt").write_text("user draft\n")
        g(work, "start", "--owner", "claude", "--", "fix")
        g(work, "scope", "**")
        (work / "app.txt").write_text("fixed\n")
        (work / "notes.txt").write_text("changed by the run\n")
        expect("commit refuses a changed pre-existing file", "non-owned-change" in g(work, "commit", "--message", "x").stderr)
        expect("a changed pre-existing file blocks the verdict", reasons(work, "non-owned-change: notes.txt"))
        (work / "notes.txt").write_text("user draft\n")
        g(work, "commit", "--message", "fix")
        evidence(work, cmd="true")
        g(work, "finish", "--task", "t")
        tracked = subprocess.run(["git", "ls-files", "notes.txt"], cwd=work, capture_output=True, text=True).stdout
        expect("the run commits only its own paths", tracked == "" and status(work)["verdict"] == "PASS")
        work = repo("prestaged")
        (work / "notes.txt").write_text("user draft\n")
        g(work, "start", "--owner", "claude", "--", "fix")
        g(work, "scope", "app.txt")
        subprocess.run(["git", "add", "notes.txt"], cwd=work, check=True)
        (work / "app.txt").write_text("fixed\n")
        expect("commit refuses a foreign staged file", "staged-outside-run" in g(work, "commit", "--message", "x").stderr)

        # Termination: escaped descendants, env-cleared pipe holders, timeout vs a natural 124.
        if os.name != "nt":
            linux = sys.platform.startswith("linux")
            work = repo("leak")
            happy(work)
            out = json.loads(g(work, "check", "--cmd", LEAK_REDIRECTED).stdout)
            expect("a detached, stream-redirected descendant is found and killed",
                   out["leaked_killed"] >= 1 and out["terminated"] and any("killed" in n for n in status(work)["notes"]))
            work = repo("term")
            happy(work)
            started = time.monotonic()
            out = json.loads(g(work, "check", "--cmd", LEAK_UNMARKED).stdout)
            expect("an env-cleared descendant holding the pipes is killed (Linux) or a termination failure",
                   (out["leaked_killed"] >= 1 and out["terminated"]) if linux else reasons(work, "termination-failed"))
            expect("pipe detection does not hang", time.monotonic() - started < 25)
            work = repo("hidden")
            happy(work)
            out = json.loads(g(work, "check", "--cmd", LEAK_HIDDEN).stdout)
            expect("a hidden descendant is reaped on Linux; elsewhere the limit is disclosed",
                   out["leaked_killed"] >= 1 if linux else any("best-effort" in n for n in status(work)["notes"]))
        work = repo("spec124", files={"spec.md": "# s\n", "spec.expected.json": json.dumps({"verification_commands": [
            {"cmd": "exit 124", "exit_code": 124}, {"cmd": "sleep 30", "exit_code": 124, "timeout_sec": 1},
            {"cmd": "cat app.txt", "stdout_contains": ["fixed"]}], "required_files": ["app.txt", "missing.txt"]})})
        happy(work, "--spec", "spec.md", edit="still broken\n")
        g(work, "check", "--cmd", "exit 124")
        g(work, "check", "--cmd", "sleep 30")
        g(work, "check", "--cmd", "cat app.txt")
        expect("a natural exit 124 meets exit_code 124", not reasons(work, "required check failed: exit 124"))
        expect("a watchdog timeout never meets exit_code 124", reasons(work, "required check failed: sleep 30"))
        expect("a stdout_contains miss fails", reasons(work, "required check failed: cat app.txt"))
        expect("expected required_files is enforced", reasons(work, "required-file-missing"))
        expect("required checks cannot be retired", "required-check" in g(work, "retire", "--cmd", "sleep 30", "--reason", "x").stderr)
        work = repo("dup", files={"spec.md": "# s\n", "spec.expected.json": json.dumps({"verification_commands": [
            {"cmd": "cat app.txt", "stdout_contains": ["absent"]}, {"cmd": "cat app.txt", "stdout_contains": ["fixed"]}]})})
        happy(work, "--spec", "spec.md")
        g(work, "check", "--cmd", "cat app.txt")
        expect("duplicate required commands keep every expectation", reasons(work, "required check failed: cat app.txt"))
        work = repo("tamper")
        happy(work)
        g(work, "check", "--cmd", "exit 1")
        failed = json.loads((work / ".devlyn/intent/run.json").read_text())["checks"][-1]["stdout"]["path"]
        (work / failed).write_text("PASS\n")
        expect("changed evidence bytes block", reasons(work, "evidence-changed"))
        work = repo("deleted-review")
        happy(work)
        review = json.loads((work / ".devlyn/intent/run.json").read_text())["reviews"][-1]["findings"]["path"]
        (work / review).unlink()
        expect("deleted review evidence blocks", reasons(work, "evidence-changed"))
        work = repo("retire-all")
        g(work, "start", "--owner", "claude", "--", "fix")
        g(work, "scope", "app.txt")
        (work / "app.txt").write_text("fixed\n")
        g(work, "commit", "--message", "fix")
        g(work, "check", "--cmd", "exit 1")
        g(work, "retire", "--cmd", "exit 1", "--reason", "x")
        g(work, "review", "--role", "primary_judge")
        g(work, "review", "--role", "pair_judge")
        expect("retiring the only check leaves no check", reasons(work, "no check ran on the current source"))

        # Review outcomes.
        work = repo("parse")
        happy(work, pair_env={"FAKE_CODEX_REVIEW": "looks fine to me"})
        expect("an unparseable review blocks", reasons(work, "pair_judge review BLOCKED"))
        work = repo("fail")
        happy(work, pair_env={"FAKE_CODEX_REVIEW": "FAIL"})
        expect("a bare FAIL verdict is NEEDS_WORK", reasons(work, "pair_judge review has binding findings"))
        work = repo("empty")
        happy(work, env={"FAKE_CLAUDE_REVIEW": ""})
        expect("an empty review blocks", reasons(work, "primary_judge review BLOCKED"))
        work = repo("medium")
        happy(work, pair_env={"FAKE_CODEX_REVIEW": '{"severity":"MEDIUM","verdict_binding":true,"message":"m"}\nNEEDS_WORK'})
        expect("a binding MEDIUM finding is NEEDS_WORK", status(work)["verdict"] == "NEEDS_WORK")
        work = repo("sticky")
        happy(work, env={"FAKE_CLAUDE_REVIEW": '{"severity":"HIGH","message":"m"}\nNEEDS_WORK'})
        g(work, "review", "--role", "primary_judge")
        g(work, "review", "--role", "pair_judge", env={"FAKE_CODEX_REVIEW": "NEEDS_WORK"})
        g(work, "review", "--role", "pair_judge", env={"FAKE_CODEX_EXIT": "124"})
        subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "empty"], cwd=work, check=True)
        evidence(work)
        expect("a retry or an empty commit never erases a binding finding",
               reasons(work, "primary_judge review has binding findings") and reasons(work, "pair_judge review has binding findings"))
        work = repo("unstable")
        happy(work)
        g(work, "review", "--role", "primary_judge", env={"FAKE_CLAUDE_REVIEW": "NEEDS_WORK", "FAKE_CLAUDE_EDIT": "app.txt:moved\n"})
        (work / "app.txt").write_text("fixed\n")
        g(work, "review", "--role", "primary_judge")
        expect("a finding from a review whose source changed mid-run does not bind the restored source",
               status(work)["verdict"] == "PASS")
        work = repo("pair-timeout")
        happy(work, pair_env={"FAKE_CODEX_EXIT": "124"})
        expect("a pair TIMEOUT leaves a disclosed primary-only PASS",
               status(work)["verdict"] == "PASS" and any("pair_judge TIMEOUT" in n for n in status(work)["notes"]))
        work = repo("primary-timeout", roles={"primary_judge": {"engine": "codex"}})
        happy(work, env={"FAKE_CODEX_EXIT": "124"})
        expect("a primary TIMEOUT blocks", reasons(work, "primary_judge review TIMEOUT"))
        work = repo("pair")
        g(work, "start", "--owner", "claude", "--", "fix")
        g(work, "scope", "app.txt")
        (work / "app.txt").write_text("fixed\n")
        g(work, "commit", "--message", "fix")
        g(work, "check", "--cmd", "true")
        g(work, "review", "--role", "primary_judge")
        expect("a required pair review cannot be skipped", reasons(work, "pair_judge review missing"))
        work = repo("nopair")
        happy(work, "--no-pair", "fix")
        expect("--no-pair skips an available pair and passes on the primary review",
               status(work)["verdict"] == "PASS" and "user_no_pair" in g(work, "review", "--role", "pair_judge").stderr)

        # Admission and contract.
        work = repo("contract", files={"goal.md": "fix app\n"})
        g(work, "start", "--owner", "claude", "--", "--goal-file", "goal.md")
        expect("an unfinished run refuses a second start", "unfinished-run" in g(work, "start", "--owner", "claude", "--", "x").stderr)
        (work / "goal.md").write_text("something else\n")
        expect("a changed contract blocks", reasons(work, "contract-changed: goal"))
        for flag in ("--risk-probes", "--no-risk-probes", "--bypass", "--perf", "--plan-only"):
            expect(f"{flag} is rejected", "BLOCKED:invalid-flags" in g(repo("flag" + flag), "start", "--owner", "claude", "--", flag, "x").stderr)
        work = repo("dirty")
        (work / "app.txt").write_text("uncommitted\n")
        expect("a dirty tracked baseline is refused", "worktree-dirty" in g(work, "start", "--owner", "claude", "--", "x").stderr)

        # Verify-only and pure design.
        work = repo("verify-only", files={"spec.md": "# spec\n"})
        (work / "app.txt").write_text("uncommitted change under review\n")
        g(work, "start", "--owner", "claude", "--", "--verify-only", "HEAD", "--spec", "spec.md")
        g(work, "review", "--role", "primary_judge")
        g(work, "review", "--role", "pair_judge")
        patch = (work / ".devlyn/intent/external-diff.patch").read_text()
        expect("verify-only reviews an uncommitted diff and passes on review", status(work)["verdict"] == "PASS"
               and "uncommitted change under review" in patch)
        (work / "app.txt").write_text("edited during review\n")
        expect("verify-only refuses source edits", reasons(work, "verify-only-changed-source"))
        work = repo("pure", files={"spec.md": "# s\n", "spec.expected.json": json.dumps({"verification_commands": [], "pure_design": True})})
        g(work, "start", "--owner", "claude", "--", "--spec", "spec.md")
        g(work, "scope", "app.txt")
        (work / "app.txt").write_text("fixed\n")
        g(work, "commit", "--message", "doc")
        g(work, "review", "--role", "primary_judge")
        g(work, "review", "--role", "pair_judge")
        expect("an explicit pure-design spec needs no check", status(work)["verdict"] == "PASS")
    print("intent-gate self-test: " + ("PASS" if not failures else f"{len(failures)} FAILED"))
    return 1 if failures else 0


if __name__ == "__main__":
    PLATFORM["configure_utf8"]()
    raise SystemExit(main())
