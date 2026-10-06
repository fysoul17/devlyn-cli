#!/usr/bin/env python3
"""Outer-owner delivery and recoverable cleanup (task-completion spec, R1–7).

No phase/state writer, staging, scheduler, or implicit adoption. See
_shared/task-completion.md for the owner acceptance contract.
"""
from __future__ import annotations

import argparse
import contextlib
import functools
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest


class CompletionError(Exception):
    pass


class WritersUnobservable(CompletionError):
    """Writer cessation cannot be observed here, so owned resources are retained, never deleted."""


class WriterActive(CompletionError):
    """An observed process still uses the owned files: wait for it or stop it, then resume."""


def require(condition, message):
    if not condition:
        raise CompletionError(message)


def command(argv, *, cwd=None, ok=(0,)):
    result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    require(result.returncode in ok, f"{shlex.join(argv[:4])}: {result.stderr.strip() or result.stdout.strip()}")
    return result.stdout.removesuffix("\n")


def git(work, *args):
    return command(["git", "-C", str(work), *args])


@functools.lru_cache(maxsize=None)
def shared(name):
    return runpy.run_path(str(Path(__file__).with_name(name + ".py")))


def read_json(path):
    require(stat.S_ISREG(path.lstat().st_mode), f"JSON must be a nonsymlink regular file: {path}")
    return shared("expected-contract")["loads_strict_json"](path.read_text(encoding="utf-8"))


def atomic_json(path, value):
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".receipt-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        if os.name != "nt":
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        Path(temporary).unlink(missing_ok=True)


def safe_path(root, relative):
    require(root == root.resolve(), f"custody/workspace root traverses a symlink: {root}")
    p = Path(relative)
    require(not p.is_absolute() and p.parts and ".." not in p.parts, f"unsafe relative path: {relative}")
    result = root / p
    require(result.resolve().is_relative_to(root.resolve()), f"path escapes custody: {relative}")
    for ancestor in [result, *result.parents]:
        if ancestor == root:
            break
        require(not ancestor.is_symlink(), f"symlink is not owned evidence: {relative}")
    return result


def file_record(path):
    mode = path.lstat().st_mode
    require(stat.S_ISREG(mode), f"evidence is not a regular file: {path}")
    raw = path.read_bytes()
    return {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "mode": stat.S_IMODE(mode)}


def snapshot_files(root, paths):
    result = {}
    for relative in paths:
        p = safe_path(root, relative)
        if p.is_dir():
            for child in sorted(p.rglob("*")):
                rel = str(child.relative_to(root))
                safe_path(root, rel)
                if not child.is_dir():
                    result[rel] = file_record(child)
        else:
            result[str(Path(relative))] = file_record(p)
    require(result, "acceptance has no evidence files")
    return result


def verify_files(root, files):
    for relative, expected in files.items():
        require(file_record(safe_path(root, relative)) == expected, f"evidence bytes/mode changed: {relative}")


def custody(work, destination, files):
    destination.mkdir(exist_ok=True)
    for relative, expected in files.items():
        source = safe_path(work, relative)
        target = safe_path(destination, relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            # Interrupted partial copies are diagnosed, never silently overwritten.
            with source.open("rb") as incoming, target.open("xb") as outgoing:
                shutil.copyfileobj(incoming, outgoing)
                outgoing.flush()
                os.fsync(outgoing.fileno())
            target.chmod(expected["mode"])
        require(file_record(target) == expected, f"custody copy mismatch; retain original: {relative}")
    verify_files(work, files)
    verify_files(destination, files)
    atomic_json(destination.parent / "manifest.json", files)


def gref(receipt, *args):
    return command(["git", "--git-dir", receipt["common_gitdir"], *args])


def ref_sha(receipt, ref):
    return command(["git", "--git-dir", receipt["common_gitdir"], "rev-parse", "--verify", "--quiet", ref], ok=(0, 1)) or None


def registrations(receipt):
    rows = {}
    for raw in gref(receipt, "worktree", "list", "--porcelain", "-z").split("\0\0"):
        row = dict(field.partition(" ")[::2] for field in raw.split("\0") if field)
        if "worktree" in row:
            rows[str(Path(row["worktree"]).resolve())] = row
    return rows


def remote_url(receipt):
    values = [gref(receipt, "remote", "get-url", "--all", receipt["remote"]),
              gref(receipt, "remote", "get-url", "--push", "--all", receipt["remote"])]
    # --get-url expands insteadOf; compare the stored literal remote config as
    # well, while preserving Git's normal transport configuration.
    literal = gref(receipt, "config", "--get-all", "remote." + receipt["remote"] + ".url")
    urls = {"literal": literal, "fetch": values[0], "push": values[1]}
    require(all(repository_from_url(url).lower() == receipt["repository"].lower() for url in urls.values()), "repository differs from remote")
    return urls


def repository_from_url(url):
    match = re.fullmatch(r"(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?", url)
    require(match is not None, "remote must unambiguously identify one GitHub repository")
    return match.group(1)


def policy(receipt, override):
    config = subprocess.run(["git", "--git-dir", receipt["common_gitdir"], "config", "--local", "--get-all", "devlyn.completionMode"], capture_output=True, text=True, encoding="utf-8")
    require(config.returncode in {0, 1}, "cannot read local completion policy: " + config.stderr.strip())
    require(config.returncode == 1 or config.stdout in {"auto\n", "pr\n"}, "invalid local devlyn.completionMode; use auto|pr")
    value = config.stdout.strip() if config.returncode == 0 else None
    require(override is None or override in {"auto", "pr"}, "invalid task mode; use auto|pr")
    return override or value or "auto"


def allocate(args):
    work = Path(git(Path(args.repo).resolve(), "rev-parse", "--show-toplevel")).resolve()
    common = Path(git(work, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve()
    require(args.task.strip(), "task identity is required")
    git(work, "check-ref-format", "refs/heads/" + args.branch)
    git(work, "check-ref-format", "refs/heads/" + args.base)
    require(args.branch != args.base and args.branch not in {"main", "master"}, "cannot own a base/default branch")
    require(re.fullmatch(r"[A-Za-z0-9_.-]+", args.remote), "unsafe remote name")
    receipt = {"task": args.task, "repository": args.repository, "remote": args.remote,
               "base": args.base, "branch": args.branch, "common_gitdir": str(common),
               "anchor": str(work), "linked": True, "allocation": "allocating"}
    require(not ref_sha(receipt, "refs/heads/"+args.branch), "existing branch cannot be adopted")
    local = local_baseline(receipt, args)
    if local:
        receipt["local_only"] = True  # Local work needs no remote: nothing is fetched or pushed.
    else:
        policy(receipt, None)
        receipt["remote_url"] = remote_url(receipt)
        require("\n" not in receipt["remote_url"]["push"] and receipt["remote_url"]["push"] == receipt["remote_url"]["fetch"], "split/multiple remote URLs are unsupported")
    receipt["baseline"] = local or exact_commit(receipt, args.start, "--start") or remote_base(receipt)
    target = Path(args.worktree).absolute()
    require(target == target.resolve(), "worktree path must not traverse symlinks")
    require(not target.exists() and all(not target.is_relative_to(p) and not p.is_relative_to(target) for p in map(Path, registrations(receipt))), "linked worktree must be an absent path disjoint from every registered worktree")
    receipt["worktree"] = str(target)
    key = hashlib.sha256(args.branch.encode()).hexdigest()[:24]
    directory = common / "devlyn-completion" / key
    directory.mkdir(parents=True, exist_ok=False)
    path = directory / "receipt.json"
    receipt["id"] = key
    receipt["recovery_ref"] = "refs/devlyn/completed/" + key
    scratch = directory / "scratch"
    scratch.mkdir()
    receipt["scratch_identity"] = workspace_identity(scratch, directory)
    # Persist prospective intent BEFORE native creation. An interrupted allocation
    # stays visibly incomplete; a later call may not adopt whatever now exists.
    atomic_json(path, receipt)
    gref(receipt, "worktree", "add", "-b", args.branch, str(target), receipt["baseline"])
    receipt["worktree_gitdir"] = git(target, "rev-parse", "--absolute-git-dir")
    receipt["worktree_identity"] = workspace_identity(target, Path(receipt["worktree_gitdir"]))
    receipt["allocation"] = "owned"
    atomic_json(path, receipt)
    return {"status": "ALLOCATED", "receipt": str(path), "worktree": str(target), "scratch": str(scratch),
            "reconciled": [] if local else reconcile(common, path, work)}


def exact_commit(receipt, value, flag):
    require(value is None or re.fullmatch(r"[0-9a-f]{40,64}", value) and ref_sha(receipt, value+"^{commit}") == value,
            f"{flag} must name an exact local commit")
    return value


def local_baseline(receipt, args):
    """A local loop starts from its recorded base commit or a receipt-bound accepted predecessor, never a fetch."""
    require(sum(map(bool, (args.local_base, args.from_receipt, args.start))) <= 1, "use one of --local-base, --from-receipt or --start")
    if args.from_receipt:
        with locked_receipt(Path(args.from_receipt).absolute(), blocking=False) as predecessor:
            require(predecessor["common_gitdir"] == receipt["common_gitdir"], "predecessor receipt belongs to another repository")
            require(predecessor.get("acceptance") and predecessor.get("product") != "FAILED", "predecessor has no accepted result")
            require(ref_sha(predecessor, predecessor["recovery_ref"]) == predecessor["publish_sha"], "predecessor recovery ref changed")
            gref(predecessor, "merge-base", "--is-ancestor", predecessor["source_sha"], predecessor["publish_sha"])
            receipt["allocated_from"] = {"receipt": predecessor["id"], "source_sha": predecessor["source_sha"]}
            return predecessor["source_sha"]
    return exact_commit(receipt, args.local_base, "--local-base")


def refuse_retired_pipeline(receipt, path, supplied, local, flags):
    """Refuse an unbound acceptance of an archived resolve run before anything is written: binding its archive
    needed the retired helpers. An unreadable acceptance is not classified here; binding reports it as before."""
    if receipt.get("acceptance") or not supplied:
        return
    acceptance_path = Path(supplied).absolute()
    try:
        acceptance = read_json(acceptance_path)
    except (CompletionError, OSError, ValueError):
        return
    if not isinstance(acceptance, dict) or acceptance.get("kind") != "pipeline":
        return
    command = shlex.join(["python3", "package/config/skills/_shared/task-complete.py", "complete", "--receipt", str(path),
                          "--acceptance", str(acceptance_path), *(["--local-only"] if local else []), *flags])
    raise CompletionError(
        "pipeline acceptance (an archived resolve run) was retired after devlyn-cli 4.1.0; nothing was changed. Finish the run "
        f"with that release: run `npm pack devlyn-cli@4.1.0`, extract the tarball, then run `{command}` there. "
        + ("That local-only completion ends as LOCAL_ONLY without binding the acceptance, as every 4.1.0 local-only completion did."
           if local else "That completion binds the pipeline acceptance before publishing; delivery of a receipt it binds then "
           "resumes with this helper."))


def bind_acceptance(receipt, path, supplied):
    work = Path(receipt["worktree"])
    if receipt.get("acceptance"):
        if supplied:
            require(file_record(Path(supplied))["sha256"] == receipt["acceptance_digest"], "acceptance changed; resume with the original acceptance")
        verify_files(path.parent / "custody", receipt["files"])
        return
    require(supplied, "first completion requires explicit root acceptance")
    acceptance_path = Path(supplied).absolute()
    require(acceptance_path.is_relative_to(work), "acceptance must be a regular file in its task checkout")
    safe_path(work, str(acceptance_path.relative_to(work)))
    acceptance = read_json(acceptance_path)
    require(acceptance.get("task") == receipt["task"], "acceptance belongs to another task")
    sha = acceptance.get("source_sha")
    require(isinstance(sha, str) and re.fullmatch(r"[0-9a-f]{40,64}", sha), "acceptance must name an exact commit")
    require(gref(receipt, "rev-parse", sha+"^{commit}") == sha, "source is not a commit")
    gref(receipt, "merge-base", "--is-ancestor", receipt["baseline"], sha)
    # A failed loop result is never published, so its checkout stays as the executor left it (as in attach).
    failed = acceptance.get("kind") == "loop" and acceptance.get("verdict") == "FAILED"
    require(ref_sha(receipt, "refs/heads/"+receipt["branch"]) == sha and (failed or git(work, "rev-parse", "HEAD") == sha),
            "unverified source delta or changed task ref")
    paths = [str(acceptance_path.relative_to(work))]
    kind = acceptance.get("kind")
    if kind == "direct":
        checks = acceptance.get("checks")
        require(isinstance(checks, list) and checks, "direct acceptance must name actual root-accepted checks")
        for check in checks:
            require(isinstance(check.get("command"), str) and check["command"].strip(), "direct check must name its command")
            paths.append(check["evidence"])
    elif kind == "loop":
        require(acceptance.get("verdict") in {"ACCEPTED", "FAILED"}, "loop result verdict must be ACCEPTED or FAILED")
        evidence = acceptance.get("evidence")
        require(isinstance(evidence, list) and all(isinstance(p, str) for p in evidence), "loop result must list its evidence files")
        paths.extend(evidence)
    else:
        raise CompletionError("acceptance kind must be direct|loop")
    files = snapshot_files(work, paths)
    custody(work, path.parent / "custody", files)
    recovery = ref_sha(receipt, receipt["recovery_ref"])
    require(recovery in {None, sha}, "recovery ref changed")
    if recovery is None:
        gref(receipt, "update-ref", receipt["recovery_ref"], sha, "0"*len(sha))
    receipt.update(acceptance=acceptance, acceptance_digest=file_record(acceptance_path)["sha256"], source_sha=sha, publish_sha=sha, files=files)
    if acceptance.get("verdict") == "FAILED":
        # Failed results keep custody and a recovery ref, but never become a frontier or a publishable product.
        receipt["product"] = "FAILED"
    atomic_json(path, receipt)


def queue_commit(receipt, work, queue, source):
    safe_path(work, queue["file"])
    commit = queue["commit"]
    require(gref(receipt, "rev-list", "--parents", "-n", "1", commit).split() == [commit, source], "queue commit must be directly atop verified source with one parent")
    require(gref(receipt, "diff-tree", "--no-commit-id", "--name-only", "-r", "-z", commit).strip("\0") == queue["file"], "queue commit must change exactly the declared queue file")


def accept(args):
    """Bind a result's source and evidence custody before terminal metadata or any delivery decision."""
    path = Path(args.receipt).absolute()
    with locked_receipt(path) as receipt:
        refuse_retired_pipeline(receipt, path, args.acceptance, receipt.get("local_only"), [])
        bind_acceptance(receipt, path, args.acceptance)
        return {"status": "FAILED" if receipt.get("product") == "FAILED" else "ACCEPTED", "receipt": str(path),
                "source_sha": receipt["source_sha"], "recovery_ref": receipt["recovery_ref"]}


def attach(args):
    """Attach the queue-only terminal commit to an already bound result; the recovery ref moves with it."""
    path = Path(args.receipt).absolute()
    queue = {"commit": args.commit, "file": args.file}
    with locked_receipt(path) as receipt:
        require(receipt.get("acceptance"), "bind the result before attaching its terminal commit")
        if receipt.get("queue") != queue:
            require(not receipt.get("queue"), "a different terminal commit is already attached")
            work = Path(receipt["worktree"])
            queue_commit(receipt, work, queue, receipt["source_sha"])
            # A failed result is never published, so its checkout stays as left; a publishable one must be checked out.
            require(ref_sha(receipt, "refs/heads/"+receipt["branch"]) == args.commit
                    and (receipt.get("product") == "FAILED" or git(work, "rev-parse", "HEAD") == args.commit),
                    "task ref and HEAD must be the terminal commit")
            recovery = ref_sha(receipt, receipt["recovery_ref"])
            require(recovery in {receipt["source_sha"], args.commit}, "recovery ref changed")
            if recovery != args.commit:
                gref(receipt, "update-ref", receipt["recovery_ref"], args.commit, receipt["source_sha"])
            receipt.update(queue=queue, publish_sha=args.commit)
            atomic_json(path, receipt)
        return {"status": "ATTACHED", "receipt": str(path), "source_sha": receipt["source_sha"], "terminal_sha": args.commit}


PR_FIELDS = "number,url,headRefName,baseRefName,headRefOid,headRepository,headRepositoryOwner,isCrossRepository,state,mergedAt,mergeCommit,autoMergeRequest"


def gh(receipt, *args):
    return command(["gh", *args, "--repo", "github.com/"+receipt["repository"]])


def repo_policy(receipt):
    info = json.loads(command(["gh", "repo", "view", "github.com/"+receipt["repository"], "--json", "nameWithOwner,url,defaultBranchRef,mergeCommitAllowed"]))
    require(info["nameWithOwner"].lower() == receipt["repository"].lower() and info["url"].lower() == "https://github.com/"+receipt["repository"].lower(), "GitHub repository identity changed")
    require(info["defaultBranchRef"]["name"] == receipt["base"] and receipt["branch"] != info["defaultBranchRef"]["name"], "base/default branch changed; retain resources")
    return info


def remote_base(receipt):
    # Never write FETCH_HEAD: a concurrent `git pull` in the anchor would merge ours.
    tracking = "refs/remotes/" + receipt["remote"] + "/" + receipt["base"]
    gref(receipt, "fetch", "--no-tags", "--no-write-fetch-head", receipt["remote"], "+refs/heads/" + receipt["base"] + ":" + tracking)
    return gref(receipt, "rev-parse", "--verify", tracking)


def remote_head(receipt, branch):
    rows = gref(receipt, "ls-remote", "--heads", receipt["remote"], "refs/heads/"+branch).splitlines()
    require(len(rows) <= 1, "ambiguous remote ref")
    return rows[0].split()[0] if rows else None


def validate_pr(receipt, pr):
    owner, name = receipt["repository"].split("/")
    require(pr["url"].lower() == f"https://github.com/{receipt['repository']}/pull/{pr['number']}".lower(), "PR repository mismatch")
    require(pr["headRefName"] == receipt["branch"] and pr["baseRefName"] == receipt["base"] and pr["headRefOid"] == receipt["publish_sha"], "PR head/base/commit changed")
    require(not pr["isCrossRepository"] and pr["headRepository"]["name"].lower() == name.lower() and pr["headRepositoryOwner"]["login"].lower() == owner.lower(), "PR head repository differs")
    require(pr["state"] in {"OPEN", "MERGED"}, "PR is closed without merge; retain task")


def workspace_identity(work, gitdir):
    return [[p.stat().st_dev, p.stat().st_ino] for p in (work, gitdir)]


def inspect_workspace(receipt):
    work = Path(receipt["worktree"])
    row = registrations(receipt).get(str(work))
    require(row and "locked" not in row and "prunable" not in row and "detached" not in row, "worktree missing, detached or locked; retain and inspect registration")
    expected = "refs/heads/" + receipt["branch"]
    require(row.get("branch") == expected, "foreign worktree branch; retain workspace")
    require(git(work, "rev-parse", "--absolute-git-dir") == receipt["worktree_gitdir"] and str(Path(git(work, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve()) == receipt["common_gitdir"], "worktree Gitdir ownership changed")
    require(workspace_identity(work, Path(receipt["worktree_gitdir"])) == receipt["worktree_identity"], "worktree/registration was replaced; receipt no longer owns it")
    require(git(work, "rev-parse", "HEAD") == receipt.get("publish_sha", receipt["baseline"]), "task HEAD changed")
    require(not git(work, "status", "--porcelain", "--untracked-files=all"), "dirty/untracked workspace; retain files and commit only accepted scope")


def outside(work):
    require(not Path.cwd().resolve().is_relative_to(work), "caller cwd is inside removable worktree; yield it and resume from outside")
    require(not Path(__file__).resolve().is_relative_to(work), "invoke the installed helper outside the removable worktree so resume remains available")


def removable(receipt, work):
    inspect_workspace(receipt)
    verify_files(work, receipt["files"])
    # Git lists a nested repository or worktree under an ignored path as `dir/`;
    # native removal would delete it with its uncommitted work.
    nested = [p for p in git(work, "ls-files", "--others", "--ignored", "--exclude-standard", "-z").split("\0") if p.endswith("/")]
    require(not nested, "nested repository or worktree inside the task tree: " + ", ".join(nested) + "; retain")
    stopped_writers(work)


def stopped_writers(work):
    outside(work)
    # The owner assertion covers its actual children; an OS observation catches
    # other currently open files/cwds, not future writers or a universal lease.
    if sys.platform == "darwin":
        result = subprocess.run(["lsof", "-Fpn", "+D", str(work)], capture_output=True, text=True, encoding="utf-8")
        if result.returncode not in {0, 1} or result.stderr.strip():
            raise WritersUnobservable("writer observation unavailable; retain tree and inspect writers")
        pid = None
        for line in result.stdout.splitlines():
            if line.startswith("p"):
                pid = int(line[1:])
            elif line.startswith("n") and pid != os.getpid():
                raise WriterActive(f"active process {pid} uses task files; stop/yield actual writers before resume")
    elif sys.platform.startswith("linux"):
        for process in Path("/proc").iterdir():
            if not process.name.isdigit() or int(process.name) == os.getpid():
                continue
            try:
                links = [process / "cwd", *(process / "fd").iterdir()]
                for link in links:
                    try:
                        target = Path(os.readlink(link))
                    except FileNotFoundError:
                        if link == process / "cwd":
                            break
                        continue
                    if target.is_absolute() and target.is_relative_to(work):
                        raise WriterActive(f"active process {process.name} uses task files; stop/yield it before resume")
            except FileNotFoundError:
                continue  # Process exited during observation.
            except PermissionError as exc:
                raise WritersUnobservable("unknown process access; retain tree until writer cessation can be established") from exc
    else:
        raise WritersUnobservable("writer observation unsupported on this platform; retain workspace")


def scratch_mounts():
    if sys.platform.startswith("linux"):
        rows = Path("/proc/self/mountinfo").read_text(encoding="utf-8").splitlines()
        paths = []
        for line in rows:
            fields = line.split()
            require(len(fields) >= 6, "cannot parse mount table; retain scratch")
            paths.append(re.sub(r"\\([0-7]{3})", lambda m: chr(int(m[1], 8)), fields[4]))
    elif sys.platform == "darwin":
        paths = []
        for line in command(["mount"]).splitlines():
            description, separator, options = line.rpartition(" (")
            candidates = [description[match.end():] for match in re.finditer(" on ", description)]
            require(separator and options.endswith(")") and candidates, "cannot parse mount table; retain scratch")
            # Darwin prints literal paths. Consider every possible separator so
            # ' on ' in a device or directory name can only cause retention.
            paths.extend(candidates)
    else:
        raise CompletionError("mount observation unsupported; retain scratch")
    return [Path(value).resolve() for value in paths]


def raise_walk_error(error):
    raise error


def clean_scratch(receipt, path, writers_stopped):
    """Empty the owned build directory; keep its identity across resume/reuse."""
    scratch = path.parent / "scratch"
    if "scratch_identity" not in receipt:
        return {"status": "NOT_OWNED"}
    require(writers_stopped, "stop/yield scratch writers, then use --writers-stopped")
    require(scratch == scratch.resolve() and scratch.is_dir(), "owned scratch missing or redirected; retain and inspect")
    identity = receipt["scratch_identity"]
    require(workspace_identity(scratch, path.parent) == identity, "scratch directory was replaced; retain")
    require(shutil.rmtree.avoids_symlink_attacks, "safe scratch removal unsupported on this platform; retain")
    require(not any(mount.is_relative_to(scratch) for mount in scratch_mounts()), "scratch contains a mounted filesystem; retain")
    stopped_writers(scratch)
    size = 0
    for directory, dirs, files in os.walk(scratch, followlinks=False, onerror=raise_walk_error):
        require(not any(name.casefold() == ".git" for name in dirs + files), "scratch contains Git recovery data; move it to retained custody before cleanup")
        for name in dirs + files:
            item = Path(directory) / name
            info = item.lstat()
            require(info.st_dev == identity[0][0], "scratch contains a mounted filesystem; retain")
            size += info.st_size if stat.S_ISREG(info.st_mode) else 0
    stopped_writers(scratch)
    require(workspace_identity(scratch, path.parent) == identity, "scratch changed before removal; retain")
    require(not any(mount.is_relative_to(scratch) for mount in scratch_mounts()), "scratch mount appeared before removal; retain")
    for item in scratch.iterdir():
        if item.is_dir() and not item.is_symlink():
            shutil.rmtree(item)
        else:
            item.unlink()
    require(workspace_identity(scratch, path.parent) == identity and not any(scratch.iterdir()), "scratch changed during cleanup; retain and inspect")
    result = {"status": "CLEAN", "logical_bytes_removed": size}
    receipt["scratch_cleanup"] = result
    atomic_json(path, receipt)
    return result


def clean_scratch_command(args):
    path = Path(args.receipt).absolute()
    with locked_receipt(path) as receipt:
        result = clean_scratch(receipt, path, args.writers_stopped)
        return {"status": "SCRATCH_CLEAN" if result["status"] == "CLEAN" else "SCRATCH_NOT_OWNED",
                "receipt": str(path), "scratch_cleanup": result, "product_verdict_unchanged": True}


def cleanup(receipt, path, pr):
    require(pr["state"] == "MERGED" and pr.get("mergedAt") and pr.get("mergeCommit", {}).get("oid"), "actual matching merge evidence is required")
    sha = receipt["publish_sha"]
    branch_ref = "refs/heads/" + receipt["branch"]
    # The recovery ref keeps the accepted commit reachable, so squash and
    # rebase merges need only the merge commit on base.
    require(ref_sha(receipt, receipt["recovery_ref"]) == sha, "recovery reachability changed; retain resources")
    verify_files(path.parent / "custody", receipt["files"])
    require(read_json(path.parent / "manifest.json") == receipt["files"], "custody manifest changed")
    gref(receipt, "merge-base", "--is-ancestor", pr["mergeCommit"]["oid"], remote_base(receipt))
    gref(receipt, "merge-base", "--is-ancestor", receipt["source_sha"], sha)
    work = Path(receipt["worktree"])
    local = ref_sha(receipt, branch_ref)
    require(local in {None, sha}, "local task ref changed; retain")
    if receipt["linked"]:
        if work.exists():
            require(receipt.get("writers_released"), "wait actual children, stop/yield known writers, then resume with --writers-stopped")
            require(work != Path(receipt["anchor"]) and work != Path(receipt["common_gitdir"]).parent, "cannot remove retained/main checkout")
            removable(receipt, work)
            devlyn = safe_path(work, ".devlyn")
            if devlyn.exists():
                require(devlyn.is_dir(), ".devlyn records must be a directory; retain tree")
                paths = [str((Path(directory) / name).relative_to(work))
                         for directory, dirs, files in os.walk(devlyn, onerror=raise_walk_error)
                         for name in files + [name for name in dirs if (Path(directory) / name).is_symlink()]]
                if paths:
                    records = snapshot_files(work, paths)
                    destination = path.parent / "records"
                    if not destination.exists():
                        with tempfile.TemporaryDirectory(prefix=".records-", dir=path.parent) as temporary:
                            shutil.copytree(devlyn, Path(temporary) / ".devlyn", symlinks=True)
                            verify_files(Path(temporary), records)
                            Path(temporary).rename(destination)
                    verify_files(destination, records)
                    verify_files(work, records)
            removable(receipt, work)
            gref(receipt, "worktree", "remove", str(work))
        else:
            require(str(work) not in registrations(receipt), "missing worktree is still registered; retain")
    checked_out = [p for p, row in registrations(receipt).items() if row.get("branch") == branch_ref]
    require(not checked_out, "task branch is still checked out at " + ", ".join(checked_out) + "; switch it off the task branch before cleanup")
    # Check ownership/ref identity once more immediately before each deletion.
    repo_policy(receipt)
    require(remote_url(receipt) == receipt["remote_url"], "remote changed before deletion")
    remote = remote_head(receipt, receipt["branch"])
    require(remote in {None, sha}, "remote branch changed after merge; retain ref")
    if remote == sha:
        # Deletion with an exact lease is the remote compare-and-delete primitive;
        # product publication above never uses force or a lease.
        gref(receipt, "push", f"--force-with-lease={branch_ref}:{sha}", receipt["remote"], ":"+branch_ref)
    if ref_sha(receipt, branch_ref) is not None:
        require(all(row.get("branch") != branch_ref for row in registrations(receipt).values()), "task branch became checked out; retain ref")
        gref(receipt, "update-ref", "-d", branch_ref, sha)
    receipt.pop("workspace_cleanup", None)
    receipt["status"] = "COMPLETE"
    atomic_json(path, receipt)


@contextlib.contextmanager
def locked_receipt(path, *, blocking=True):
    require(path.name == "receipt.json" and path.parent.parent.name == "devlyn-completion" and path == path.resolve(), "receipt must be its original external nonsymlink path")
    require(not (path.parent / "lock").is_symlink(), "receipt lock must not be a symlink")
    with contextlib.ExitStack() as stack:
        try:
            stack.enter_context(shared("platform-support")["file_lock"](path.parent / "lock", blocking=blocking))
        except (ImportError, OSError, AttributeError) as exc:
            raise CompletionError(f"receipt lock unavailable: {path}: {exc}") from exc
        receipt = read_json(path)
        require(path == Path(receipt["common_gitdir"]) / "devlyn-completion" / receipt["id"] / "receipt.json", "receipt/common Gitdir binding mismatch")
        require(receipt["id"] == hashlib.sha256(receipt["branch"].encode()).hexdigest()[:24] and receipt["branch"] not in {receipt["base"], "main", "master"}, "receipt branch ownership changed")
        require(receipt["allocation"] == "owned", "allocation was interrupted; no historical adoption is permitted")
        yield receipt


def completion_result(receipt, path, status):
    if receipt.get("delivery") != status:
        receipt["delivery"] = status  # Phase-independent checkpoint: the latest delivery outcome.
        atomic_json(path, receipt)
    released = receipt.get("writers_released", False)
    resume = shlex.join([sys.executable, str(Path(__file__).resolve()), "complete", "--receipt", str(path)] +
                        (["--writers-stopped"] if released else []))
    scratch = {"status": "NOT_OWNED"}
    if "scratch_identity" in receipt:
        try:
            scratch = clean_scratch(receipt, path, released)
        except (CompletionError, OSError, ValueError, KeyError, TypeError, IndexError) as error:
            scratch = {"status": "RETAINED", "reason": str(error), "resume": shlex.join([
                sys.executable, str(Path(__file__).resolve()), "clean-scratch", "--receipt", str(path), "--writers-stopped"])}
            receipt["scratch_cleanup"] = scratch
            try:
                atomic_json(path, receipt)
            except OSError as record_error:
                scratch["record_error"] = str(record_error)
    retained = scratch["status"] == "RETAINED" or "workspace_cleanup" in receipt
    return {"status": "CLEANUP_PENDING" if status == "COMPLETE" and retained else status,
            "delivery_status": status, "receipt": str(path), "pr": receipt.get("pr_url"), "resume": resume,
            "acceptance": (receipt.get("acceptance") or {}).get("kind"), "product_verdict_unchanged": True,
            "scratch_path": str(path.parent / "scratch") if "scratch_identity" in receipt else None,
            "scratch_cleanup": scratch, "workspace_cleanup": receipt.get("workspace_cleanup")}


def reconcile(common, allocated, anchor):
    results = []
    for path in sorted((common / "devlyn-completion").glob("*/receipt.json")):
        if path == allocated:
            continue
        try:
            receipt = read_json(path)
            if receipt.get("allocation") != "owned" or not receipt.get("acceptance") or not receipt.get("pr_number") or receipt.get("local_only"):
                continue
            if receipt.get("status") == "COMPLETE" and (not receipt.get("writers_released") or "scratch_identity" not in receipt or receipt.get("scratch_cleanup", {}).get("status") == "CLEAN"):
                continue
            with locked_receipt(path, blocking=False) as receipt:
                if receipt.get("status") == "COMPLETE":
                    if receipt.get("writers_released") and "scratch_identity" in receipt and receipt.get("scratch_cleanup", {}).get("status") != "CLEAN":
                        results.append(completion_result(receipt, path, "COMPLETE"))
                    continue
                if not receipt.get("acceptance") or not receipt.get("pr_number") or receipt.get("local_only"):
                    continue
                pr = json.loads(gh(receipt, "pr", "view", str(receipt["pr_number"]), "--json", PR_FIELDS))
                if pr["state"] != "MERGED":
                    continue
                validate_pr(receipt, pr)
                require(not receipt["linked"] or Path(receipt["worktree"]) != anchor, "cannot clean the current allocation's anchor checkout: " + str(anchor))
                require(remote_url(receipt) == receipt["remote_url"], "remote URL changed since allocation")
                repo_policy(receipt)
                receipt["merge"] = pr
                atomic_json(path, receipt)
                cleanup(receipt, path, pr)
                results.append(completion_result(receipt, path, "COMPLETE"))
        except (Exception, SystemExit) as error:
            results.append({"receipt": str(path), "status": "RETAINED", "reason": str(error)})
    return results


def complete(args):
    path = Path(args.receipt).absolute()
    with locked_receipt(path) as receipt:
        local = args.local_only or receipt.get("local_only")
        refuse_retired_pipeline(receipt, path, args.acceptance, local, [*(["--mode", args.mode] if args.mode and not local else []),
                                                                       *(["--writers-stopped"] if args.writers_stopped else [])])
        if args.writers_stopped:
            if receipt["linked"]:
                outside(Path(receipt["worktree"]))
            receipt["writers_released"] = True
            atomic_json(path, receipt)
        def result(status):
            return completion_result(receipt, path, status)
        if receipt.get("product") == "FAILED":
            return result("FAILED")
        if args.local_only or receipt.get("local_only"):
            require(not receipt.get("pushed"), f"{receipt['task']} already has a pushed PR {receipt.get('pr_url') or receipt['branch']}; "
                    "--local-only cannot rewrite its delivery, resume it without --local-only")
            receipt["local_only"] = True
            atomic_json(path, receipt)
            if args.acceptance or receipt.get("acceptance"):
                # Persist acceptance custody before the local-only return.
                if not receipt.get("acceptance"):
                    inspect_workspace(dict(receipt, publish_sha=ref_sha(receipt, "refs/heads/"+receipt["branch"])))
                bind_acceptance(receipt, path, args.acceptance)
            return result("LOCAL_ONLY")
        mode = policy(receipt, args.mode or receipt.get("mode_override"))
        if args.mode:
            receipt["mode_override"] = args.mode
            atomic_json(path, receipt)
        require(remote_url(receipt) == receipt["remote_url"], "remote URL changed since allocation")
        if receipt.get("status") == "COMPLETE":
            verify_files(path.parent / "custody", receipt["files"])
            return result("COMPLETE")
        if not receipt.get("acceptance"):
            # Before first binding the owner has committed the product; inspect
            # uses the actual branch head until acceptance pins its exact SHA.
            current = dict(receipt, publish_sha=ref_sha(receipt, "refs/heads/"+receipt["branch"]))
            inspect_workspace(current)
        bind_acceptance(receipt, path, args.acceptance)
        info = repo_policy(receipt)
        if receipt.get("pr_number"):
            pr = json.loads(gh(receipt, "pr", "view", str(receipt["pr_number"]), "--json", PR_FIELDS))
        else:
            prs = json.loads(gh(receipt, "pr", "list", "--head", receipt["branch"], "--base", receipt["base"], "--state", "all", "--json", PR_FIELDS))
            require(len(prs) <= 1, "multiple PRs for task head/base; retain and resolve ambiguity")
            pr = prs[0] if prs else None
        if pr:
            validate_pr(receipt, pr)
        actual = remote_head(receipt, receipt["branch"])
        if not pr or pr["state"] != "MERGED":
            inspect_workspace(receipt)
            verify_files(Path(receipt["worktree"]), receipt["files"])
            require(actual in {None, receipt["publish_sha"]}, "remote task head changed; refusing to overwrite or merge")
            require(actual is not None or (not pr and not receipt.get("pushed")), "published task ref disappeared; retain and inspect")
            if actual is None:
                gref(receipt, "push", receipt["remote"], receipt["publish_sha"]+":refs/heads/"+receipt["branch"])
            receipt["pushed"] = True
            atomic_json(path, receipt)
            if pr is None:
                gh(receipt, "pr", "create", "--head", receipt["branch"], "--base", receipt["base"], "--title", receipt["task"], "--body", "Accepted task commit: " + receipt["publish_sha"])
                prs = json.loads(gh(receipt, "pr", "list", "--head", receipt["branch"], "--base", receipt["base"], "--state", "all", "--json", PR_FIELDS))
                require(len(prs) == 1, "created PR could not be reconciled; resume from receipt")
                pr = prs[0]
                validate_pr(receipt, pr)
        receipt.update(pr_number=pr["number"], pr_url=pr["url"])
        atomic_json(path, receipt)
        if mode == "pr" and pr["state"] == "OPEN":
            if pr.get("autoMergeRequest"):
                gh(receipt, "pr", "merge", str(pr["number"]), "--disable-auto")
                pr = json.loads(gh(receipt, "pr", "view", str(pr["number"]), "--json", PR_FIELDS))
                validate_pr(receipt, pr)
                require(not pr.get("autoMergeRequest"), "auto-merge request remains on owned PR; retain and inspect")
            if pr["state"] == "OPEN":
                return result("PR")
        if pr["state"] != "MERGED":
            inspect_workspace(receipt)
            verify_files(Path(receipt["worktree"]), receipt["files"])
            require(remote_head(receipt, receipt["branch"]) == receipt["publish_sha"], "remote head race before merge")
            refused = None
            if not pr.get("autoMergeRequest"):
                try:
                    require(info["mergeCommitAllowed"], "repository disallows merge commits")
                    gh(receipt, "pr", "merge", str(pr["number"]), "--auto", "--merge", "--match-head-commit", receipt["publish_sha"])
                except CompletionError as error:
                    refused = str(error)
            pr = json.loads(gh(receipt, "pr", "view", str(pr["number"]), "--json", PR_FIELDS))
            validate_pr(receipt, pr)
            if pr["state"] != "MERGED":
                # Merge only when the repository allows it; a refused request leaves the PR for a person.
                return dict(result("PR"), merge_refused=refused) if refused and not pr.get("autoMergeRequest") else result("PENDING")
        receipt["merge"] = pr
        atomic_json(path, receipt)
        try:
            cleanup(receipt, path, pr)
        except WritersUnobservable as error:
            # Conservative retention: the merge settles delivery; workspace, task refs and custody stay, reported.
            receipt["workspace_cleanup"] = {"status": "RETAINED", "reason": str(error), "resume": shlex.join([
                sys.executable, str(Path(__file__).resolve()), "complete", "--receipt", str(path)])}
            atomic_json(path, receipt)
        return result("COMPLETE")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    actions = parser.add_subparsers(dest="action")
    allocation = actions.add_parser("allocate")
    allocation.add_argument("--repo", default=".")
    for name in ("task", "branch", "repository", "base"):
        allocation.add_argument("--"+name, required=True)
    allocation.add_argument("--remote", default="origin")
    allocation.add_argument("--worktree", required=True)
    allocation.add_argument("--local-base")
    allocation.add_argument("--from-receipt")
    allocation.add_argument("--start")
    binding = actions.add_parser("accept")
    binding.add_argument("--receipt", required=True)
    binding.add_argument("--acceptance", required=True)
    attachment = actions.add_parser("attach")
    attachment.add_argument("--receipt", required=True)
    attachment.add_argument("--commit", required=True)
    attachment.add_argument("--file", default="docs/specs/queue.md")
    completion = actions.add_parser("complete")
    completion.add_argument("--receipt", required=True)
    completion.add_argument("--acceptance")
    completion.add_argument("--mode", choices=("auto", "pr"))
    completion.add_argument("--local-only", "--no-push", action="store_true")
    completion.add_argument("--writers-stopped", action="store_true")
    scratch_cleanup = actions.add_parser("clean-scratch")
    scratch_cleanup.add_argument("--receipt", required=True)
    scratch_cleanup.add_argument("--writers-stopped", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if args.action is None:
        parser.error("allocate, accept, attach, complete or clean-scratch is required")
    try:
        result = {"allocate": allocate, "accept": accept, "attach": attach,
                  "clean-scratch": clean_scratch_command, "complete": complete}[args.action](args)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (CompletionError, OSError, ValueError, KeyError, TypeError, IndexError, SystemExit) as exc:
        result = {"status": "BLOCKED", "reason": str(exc)}
        if args.action != "allocate":
            result["receipt"] = str(Path(args.receipt).absolute())
        if args.action in {"complete", "clean-scratch"}:
            result["resume"] = shlex.join([sys.executable, str(Path(__file__).resolve()), args.action, "--receipt", result["receipt"], *(["--writers-stopped"] if args.writers_stopped else [])])
        print(json.dumps(result, sort_keys=True))
        return 1


def self_test(names=None):
    suite = (unittest.TestSuite(CompletionTests(name) for name in names) if names
             else unittest.defaultTestLoader.loadTestsFromTestCase(CompletionTests))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if result.wasSuccessful():
        print(f"task-complete self-test: PASS ({result.testsRun} isolated tests)")
    return 0 if result.wasSuccessful() else 1


# Fixtures use real Git and isolated config. Wrappers translate only transport
# to the local bare remote and inject interruption AFTER real effects; gh is fake.
FAKE_GH = r'''#!/usr/bin/env python3
import json, os, pathlib, subprocess, sys
p = pathlib.Path(os.environ['FIXTURE_GH'])
d = json.loads(p.read_text(encoding="utf-8")); a = sys.argv[1:]
prs = d.setdefault('prs', [])  # PR number n is prs[n-1]; several may be open at once.
def save(): p.write_text(json.dumps(d), encoding="utf-8")
def remote(ref):
    r = subprocess.run([os.environ['REAL_GIT'], '--git-dir', d['bare'], 'rev-parse', '--verify', ref], capture_output=True, text=True, encoding="utf-8")
    return r.stdout.strip() if r.returncode == 0 else None
if a[:2] == ['repo', 'view']:
    assert a[2:] == ['github.com/test/project', '--json', 'nameWithOwner,url,defaultBranchRef,mergeCommitAllowed'], 'unsupported gh repo view arguments: '+str(a)
    print(json.dumps({'nameWithOwner':'test/project', 'url':'https://github.com/test/project', 'defaultBranchRef':{'name':d.get('default_branch','main')}, 'mergeCommitAllowed':d.get('merge_allowed',True)}))
elif a[:2] == ['pr', 'list']:
    assert '--repo' in a and a[a.index('--repo')+1] == 'github.com/test/project'
    print(json.dumps([pr for pr in prs if pr['headRefName'] == a[a.index('--head')+1]]))
elif a[:2] == ['pr', 'create']:
    d['creates'] = d.get('creates',0)+1
    head = a[a.index('--head')+1]; base = a[a.index('--base')+1]
    assert not [pr for pr in prs if pr['headRefName'] == head], 'duplicate PR'
    url = 'https://github.com/test/project/pull/%d' % (len(prs)+1)
    prs.append({'number':len(prs)+1,'url':url,'headRefName':head,'baseRefName':base,'headRefOid':remote('refs/heads/'+head),'headRepository':{'name':'project','owner':{'login':'test'}}, 'headRepositoryOwner':{'login':'test'},'isCrossRepository':False,'state':'OPEN','mergedAt':None,'mergeCommit':None,'autoMergeRequest':None})
    save()
    print(url)
    if d.pop('interrupt_create',False): save(); sys.exit(1)
elif a[:2] == ['pr', 'view']:
    print(json.dumps(prs[int(a[2])-1]))
elif a[:2] == ['pr', 'merge'] and '--disable-auto' in a:
    d['disables'] = d.get('disables',0)+1
    prs[int(a[2])-1]['autoMergeRequest'] = None
    save()
elif a[:2] == ['pr', 'merge']:
    assert '--admin' not in a and '--delete-branch' not in a
    assert '--auto' in a and '--merge' in a and '--match-head-commit' in a
    pr = prs[int(a[2])-1]
    sha = a[a.index('--match-head-commit')+1]
    assert sha == remote('refs/heads/'+pr['headRefName'])
    d['merges'] = d.get('merges',0)+1
    if not d.get('auto_allowed',True) and d.get('pending'):
        save(); print('repository disallows auto merge',file=sys.stderr); sys.exit(1)
    if d.get('pending'):
        pr['autoMergeRequest'] = {'enabledAt':'now'}
    else:
        g = [os.environ['REAL_GIT'],'--git-dir',d['bare']]
        base = remote('refs/heads/main')
        # A three-way merge into the current base, as GitHub makes it; a conflicting PR does not merge.
        merged = subprocess.run(g+['merge-tree','--write-tree',base,sha],capture_output=True,text=True,encoding="utf-8")
        if merged.returncode:
            save(); print('pull request is not mergeable: '+merged.stdout,file=sys.stderr); sys.exit(1)
        parents = ['-p',base] if d.get('squash') else ['-p',base,'-p',sha]
        merge = subprocess.check_output(g+['commit-tree',merged.stdout.split()[0],*parents,'-m','merge fixture'],text=True, encoding="utf-8").strip()
        subprocess.check_call(g+['update-ref','refs/heads/main',merge,base])
        pr.update(state='MERGED',mergedAt='now',mergeCommit={'oid':merge})
    save()
    if d.pop('interrupt_merge',False): save(); sys.exit(1)
else:
    raise SystemExit('unexpected gh arguments: '+str(a))
'''

GIT_DISPATCH = r'''#!/bin/sh
for arg do
    case "$arg" in push|fetch|ls-remote|remove) exec python3 "$0.py" "$@";; esac
done
exec "$REAL_GIT" "$@"
'''


GIT_WRAPPER = r'''#!/usr/bin/env python3
import json, os, pathlib, subprocess, sys
a = sys.argv[1:]
p = pathlib.Path(os.environ['FIXTURE_GH']); d = json.loads(p.read_text(encoding="utf-8"))
if 'push' in a and any(x.startswith('--force-with-lease=') for x in a) and d.pop('remote_delete_race',False):
    subprocess.check_call([os.environ['REAL_GIT'],'--git-dir',d['bare'],'update-ref','refs/heads/'+d['prs'][0]['headRefName'],d['race_sha']])
    p.write_text(json.dumps(d), encoding="utf-8")
for operation in ('push', 'fetch', 'ls-remote'):
    if operation in a and 'origin' in a:
        prefix = a[:a.index(operation)]
        url = subprocess.check_output([os.environ['REAL_GIT'], *prefix, 'remote', 'get-url', *(['--push'] if operation == 'push' else []), '--all', 'origin'], text=True, encoding="utf-8").strip()
        if url in {'https://github.com/test/project.git', 'git@github.com:test/project.git', 'ssh://git@github.com/test/project.git'}:
            a[a.index('origin')] = d['bare']
        break
r = subprocess.run([os.environ['REAL_GIT'],*a])
event = 'delete' if 'push' in a and any(x.startswith(':refs/') for x in a) else 'push' if 'push' in a else 'remove' if 'worktree' in a and 'remove' in a else None
if r.returncode == 0 and event:
    d = json.loads(p.read_text(encoding="utf-8")); d[event+'s'] = d.get(event+'s',0)+1
    fail = d.pop('interrupt_'+event,False); p.write_text(json.dumps(d), encoding="utf-8")
    if fail: sys.exit(1)
sys.exit(r.returncode)
'''


class CompletionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="devlyn-completion-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.work = self.root / "work"
        self.bare = self.root / "remote.git"
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.data = self.root / "gh.json"
        self.data.write_text(json.dumps({"bare": str(self.bare)}), encoding="utf-8")
        self.env = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": str(self.root / "gitconfig"),
                    "GIT_AUTHOR_NAME": "Fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
                    "GIT_COMMITTER_NAME": "Fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
                    "FIXTURE_GH": str(self.data), "REAL_GIT": shutil.which("git"),
                    "GIT_CONFIG_COUNT": "0", "GIT_ALLOW_PROTOCOL": "file"}
        for key in list(self.env):
            if key in {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR"}:
                del self.env[key]
        for name, body in (("gh", FAKE_GH), ("git.py", GIT_WRAPPER), ("git", GIT_DISPATCH)):
            path = self.bin / name
            path.write_text(body, encoding="utf-8")
            path.chmod(0o755)
        self.env["PATH"] = str(self.bin) + os.pathsep + os.environ["PATH"]
        self.run_cmd(["git", "init", "--bare", "--initial-branch=main", str(self.bare)])
        self.run_cmd(["git", "init", "--initial-branch=main", str(self.work)])
        (self.work / ".gitignore").write_text(".devlyn/\nignored/\nnode_modules/\n.env\n", encoding="utf-8")
        (self.work / "product").write_text("baseline\n", encoding="utf-8")
        self.g("add", ".")
        self.g("commit", "-m", "baseline")
        self.g("remote", "add", "origin", "https://github.com/test/project.git")
        self.g("push", "origin", "main")
        self.configure(pushs=0)

    def run_cmd(self, args, *, cwd=None, success=True):
        r = subprocess.run(args, cwd=cwd or self.root, env=self.env, capture_output=True, text=True, encoding="utf-8")
        if success:
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        return r

    def g(self, *args, work=None):
        return self.run_cmd(["git", "-C", str(work or self.work), *args]).stdout.strip()

    def configure(self, **values):
        d = json.loads(self.data.read_text(encoding="utf-8")); d.update(values)
        self.data.write_text(json.dumps(d), encoding="utf-8")

    def cli(self, *args, success=True, cwd=None):
        r = self.run_cmd([sys.executable, str(Path(__file__).resolve()), *map(str, args)], success=success, cwd=cwd)
        return json.loads(r.stdout), r

    def allocate(self, name="fixture", base="main"):
        args = ["allocate", "--repo", self.work, "--task", name, "--branch", "task/"+name, "--repository", "test/project", "--base", base,
                "--worktree", self.root / ("linked" if name == "fixture" else name)]
        result, _ = self.cli(*args)
        self.receipt = Path(result["receipt"])
        self.task = Path(result["worktree"])
        return result

    def allocate_legacy(self):
        common = Path(self.g("rev-parse", "--absolute-git-dir"))
        key = hashlib.sha256(b"task/fixture").hexdigest()[:24]
        receipt = {"task": "fixture", "repository": "test/project", "remote": "origin", "base": "main", "branch": "task/fixture",
                   "common_gitdir": str(common), "anchor": str(self.work), "linked": False, "allocation": "owned",
                   "baseline": self.g("rev-parse", "HEAD"), "worktree": str(self.work), "id": key,
                   "recovery_ref": "refs/devlyn/completed/"+key, "worktree_gitdir": str(common),
                   "remote_url": dict.fromkeys(("literal", "fetch", "push"), "https://github.com/test/project.git")}
        self.receipt = common / "devlyn-completion" / key / "receipt.json"
        self.receipt.parent.mkdir(parents=True)
        scratch = self.receipt.parent / "scratch"
        scratch.mkdir()
        receipt["scratch_identity"] = workspace_identity(scratch, self.receipt.parent)
        self.g("switch", "-c", "task/fixture")
        receipt["worktree_identity"] = workspace_identity(self.work, common)
        self.receipt.write_text(json.dumps(receipt), encoding="utf-8")
        self.task = self.work

    def merge_pr(self):
        self.configure(pending=False)
        self.run_cmd(["gh", "pr", "merge", "1", "--auto", "--merge", "--match-head-commit", self.sha])

    def anchor_state(self, work=None):
        work = work or self.work
        return (self.g("symbolic-ref", "HEAD", work=work), self.g("rev-parse", "HEAD", work=work),
                self.g("status", "--porcelain", "--untracked-files=all", work=work), (work / "product").read_bytes(),
                (Path(self.g("rev-parse", "--absolute-git-dir", work=work)) / "index").read_bytes())

    def test_allocate_base_with_same_named_tag(self):
        self.g("tag", "main")
        result = self.allocate()
        self.assertEqual(result["status"], "ALLOCATED")
        self.assertEqual(json.loads(self.receipt.read_text(encoding="utf-8"))["base"], "main")

    def test_allocate_base_preserves_unicode_whitespace(self):
        base = "main\u00a0"
        self.g("switch", "-c", base)
        self.g("push", "origin", "HEAD:refs/heads/"+base)
        result = self.allocate(base=base)
        self.assertEqual(result["status"], "ALLOCATED")
        self.assertEqual(json.loads(self.receipt.read_text(encoding="utf-8"))["base"], base)

    def assert_base_identity_rejected(self, actual, base):
        result, process = self.cli("allocate", "--repo", self.work, "--task", "fixture",
            "--branch", "task/fixture", "--repository", "test/project", "--base", base, "--worktree", self.root / "linked", success=False)
        self.assertNotEqual(process.returncode, 0)
        self.assertIn("refs/heads/"+base, result["reason"])
        head = self.run_cmd(["git", "-C", str(self.work), "symbolic-ref", "HEAD"]).stdout
        self.assertEqual(head, "refs/heads/" + actual + "\n")
        self.assertFalse((self.work / ".git/devlyn-completion").exists())
        self.assertNotEqual(self.run_cmd(["git", "-C", str(self.work), "show-ref", "--verify",
            "refs/heads/task/fixture"], success=False).returncode, 0)

    def test_allocate_rejects_trimmed_base_alias(self):
        self.g("switch", "-c", "main\u00a0")
        self.g("push", "origin", "HEAD:refs/heads/main\u00a0")
        self.run_cmd(["git", "--git-dir", str(self.bare), "update-ref", "-d", "refs/heads/main"])
        self.assert_base_identity_rejected("main\u00a0", "main")

    def test_allocate_rejects_short_base_alias(self):
        self.g("branch", "heads/main")
        self.g("tag", "main")
        self.assert_base_identity_rejected("main", "heads/main")

    def test_allocate_uses_remote_base_with_dirty_foreign_anchor(self):
        baseline = self.g("rev-parse", "main")
        (self.work / "product").write_text("remote advance\n", encoding="utf-8")
        self.g("commit", "-am", "remote advance")
        self.g("push", "origin", "main")
        remote = self.g("rev-parse", "main")
        self.g("switch", "-c", "busy")
        (self.work / "product").write_text("local advance\n", encoding="utf-8")
        self.g("commit", "-am", "local advance")
        ahead = self.g("rev-parse", "HEAD")
        (self.work / "product").write_text("busy edits\n", encoding="utf-8")
        (self.work / "untracked").write_bytes(b"owner data")
        for name, local in (("behind", baseline), ("ahead", ahead)):
            self.g("update-ref", "refs/heads/main", local)
            before = self.anchor_state()
            result = self.allocate(name)
            self.assertEqual(result["status"], "ALLOCATED")
            self.assertEqual(json.loads(self.receipt.read_text())["baseline"], remote)
            self.assertEqual(self.g("rev-parse", "HEAD", work=self.task), remote)
            self.assertEqual(self.anchor_state(), before)
            self.assertEqual((self.work / "untracked").read_bytes(), b"owner data")
            self.assertFalse((self.work / ".git" / "FETCH_HEAD").exists())

    @unittest.skipUnless(sys.platform == "darwin" or sys.platform.startswith("linux"), "writer observation requires POSIX")
    def test_disposable_scratch_cleans_for_local_only_and_preserves_source(self):
        result = self.allocate()
        scratch = Path(result["scratch"])
        (scratch / "target").mkdir()
        (scratch / "target" / "object").write_bytes(b"rebuildable")
        (self.task / "uncommitted-work").write_text("preserve")
        result, _ = self.cli("complete", "--receipt", self.receipt, "--local-only", "--writers-stopped")
        self.assertEqual(result["status"], "LOCAL_ONLY")
        self.assertFalse(any(scratch.iterdir()))
        self.assertEqual((self.task / "uncommitted-work").read_text(), "preserve")
        self.assertEqual(result["scratch_cleanup"]["logical_bytes_removed"], 11)
        result, _ = self.cli("clean-scratch", "--receipt", self.receipt, "--writers-stopped")
        self.assertEqual(result["status"], "SCRATCH_CLEAN")

    @unittest.skipUnless(sys.platform == "darwin" or sys.platform.startswith("linux"), "writer observation requires POSIX")
    def test_scratch_rejects_active_writer_and_requires_owner_assertion(self):
        scratch = Path(self.allocate()["scratch"])
        result, _ = self.cli("clean-scratch", "--receipt", self.receipt, success=False)
        self.assertIn("--writers-stopped", result["reason"])
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"], cwd=scratch)
        try:
            result, _ = self.cli("clean-scratch", "--receipt", self.receipt, "--writers-stopped", success=False)
            self.assertIn("active process", result["reason"])
            self.assertTrue(scratch.is_dir())
        finally:
            child.terminate()
            child.wait(timeout=5)
        self.cli("clean-scratch", "--receipt", self.receipt, "--writers-stopped")

    def test_linux_writer_scan_continues_after_vanished_fd(self):
        from unittest.mock import patch
        process = Path("/proc") / str(os.getpid() + 1)
        vanished, active = process / "fd/0", process / "fd/1"
        iterdir, readlink = Path.iterdir, os.readlink
        def entries(path):
            if path == Path("/proc"):
                return iter([process])
            if path == process / "fd":
                return iter([vanished, active])
            return iterdir(path)
        def target(path, *args, **kwargs):
            if path == process / "cwd":
                return str(self.root)
            if path == vanished:
                raise FileNotFoundError(path)
            if path == active:
                return str(self.work / "product")
            return readlink(path, *args, **kwargs)
        with patch.object(sys, "platform", "linux"), patch.object(Path, "iterdir", entries), patch.object(os, "readlink", target):
            with self.assertRaisesRegex(WriterActive, "active process " + process.name):
                stopped_writers(self.work)

    @unittest.skipUnless(sys.platform == "darwin" or sys.platform.startswith("linux"), "writer observation requires POSIX")
    def test_scratch_rejects_redirect_and_git_data_but_does_not_follow_child_links(self):
        scratch = Path(self.allocate()["scratch"])
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "keep").write_text("source")
        retained = scratch.with_name("retained")
        scratch.rename(retained)
        scratch.symlink_to(outside, target_is_directory=True)
        result, _ = self.cli("clean-scratch", "--receipt", self.receipt, "--writers-stopped", success=False)
        self.assertIn("redirected", result["reason"])
        scratch.unlink()
        retained.rename(scratch)
        (scratch / ".GiT").write_text("gitdir: elsewhere")
        result, _ = self.cli("clean-scratch", "--receipt", self.receipt, "--writers-stopped", success=False)
        self.assertIn("Git recovery data", result["reason"])
        (scratch / ".GiT").unlink()
        (scratch / "external-link").symlink_to(outside, target_is_directory=True)
        self.cli("clean-scratch", "--receipt", self.receipt, "--writers-stopped")
        self.assertEqual((outside / "keep").read_text(), "source")

    @unittest.skipUnless(sys.platform == "darwin" or sys.platform.startswith("linux"), "writer observation requires POSIX")
    def test_scratch_reuse_and_partial_cleanup_keep_original_identity(self):
        scratch = Path(self.allocate()["scratch"])
        (scratch / "first-build").write_bytes(b"first")
        self.cli("clean-scratch", "--receipt", self.receipt, "--writers-stopped")
        (scratch / "resumed-build").write_bytes(b"next")
        result, _ = self.cli("clean-scratch", "--receipt", self.receipt, "--writers-stopped")
        self.assertEqual(result["scratch_cleanup"]["logical_bytes_removed"], 4)
        self.assertFalse(any(scratch.iterdir()))
        scratch.rename(scratch.with_name("original"))
        scratch.mkdir()
        (scratch / "foreign").write_text("preserve")
        result, _ = self.cli("clean-scratch", "--receipt", self.receipt, "--writers-stopped", success=False)
        self.assertIn("replaced", result["reason"])
        self.assertIn("--writers-stopped", result["resume"])
        self.assertEqual((scratch / "foreign").read_text(), "preserve")

    @unittest.skipUnless(sys.platform == "darwin" or sys.platform.startswith("linux"), "writer observation requires POSIX")
    def test_scratch_refusal_does_not_block_local_only_delivery(self):
        scratch = Path(self.allocate()["scratch"])
        (scratch / ".git").mkdir()
        result, _ = self.cli("complete", "--receipt", self.receipt, "--local-only", "--writers-stopped")
        self.assertEqual(result["status"], "LOCAL_ONLY")
        self.assertEqual(result["scratch_cleanup"]["status"], "RETAINED")
        self.assertIn("Git recovery data", result["scratch_cleanup"]["reason"])
        self.assertEqual(json.loads(self.receipt.read_text())["scratch_cleanup"]["status"], "RETAINED")
        self.assertTrue((scratch / ".git").is_dir())

    @unittest.skipUnless(sys.platform == "darwin" or sys.platform.startswith("linux"), "writer observation requires POSIX")
    def test_scratch_refusal_reports_delivery_separately(self):
        scratch = Path(self.allocate()["scratch"])
        self.accept()
        (scratch / ".git").mkdir()
        result, _ = self.cli("complete", "--receipt", self.receipt, "--acceptance", self.acceptance, "--writers-stopped", "--mode", "auto")
        self.assertEqual(result["status"], "CLEANUP_PENDING")
        self.assertEqual(result["delivery_status"], "COMPLETE")
        self.assertEqual(result["scratch_cleanup"]["status"], "RETAINED")
        self.assertIn("--writers-stopped", result["scratch_cleanup"]["resume"])
        self.assertIn("--writers-stopped", result["resume"])
        (scratch / ".git").rmdir()
        result, _ = self.cli("complete", "--receipt", self.receipt, "--writers-stopped")
        self.assertEqual(result["status"], "COMPLETE")

    @unittest.skipUnless(sys.platform == "darwin" or sys.platform.startswith("linux"), "writer observation requires POSIX")
    def test_scratch_mount_and_scan_failure_preserve_contents(self):
        from unittest.mock import patch
        scratch = Path(self.allocate()["scratch"])
        (scratch / "keep").write_text("retained")
        receipt = json.loads(self.receipt.read_text())
        with patch.dict(clean_scratch.__globals__, {"scratch_mounts": lambda: [scratch / "same-device-bind"]}):
            with self.assertRaisesRegex(CompletionError, "mounted filesystem"):
                clean_scratch(receipt, self.receipt, True)
        def failed_walk(*args, **kwargs):
            kwargs["onerror"](PermissionError("unreadable subtree"))
        with patch.object(os, "walk", failed_walk):
            with self.assertRaisesRegex(PermissionError, "unreadable subtree"):
                clean_scratch(receipt, self.receipt, True)
        self.assertEqual((scratch / "keep").read_text(), "retained")

    def test_scratch_mount_table_parsing_preserves_ambiguous_literal_paths(self):
        from unittest.mock import patch
        target = "/task/scratch/name on inside\\040literal"
        with patch.object(sys, "platform", "darwin"), patch.dict(scratch_mounts.__globals__, {
            "command": lambda args: "device on source on " + target + " (local, journaled)",
        }):
            self.assertIn(Path(target).resolve(), scratch_mounts())
        alias = self.root / "scratch-alias"
        alias.symlink_to(self.root, target_is_directory=True)
        with patch.object(sys, "platform", "darwin"), patch.dict(scratch_mounts.__globals__, {
            "command": lambda args: "device on " + str(alias / "mounted") + " (local)",
        }):
            self.assertEqual(scratch_mounts(), [(self.root / "mounted").resolve()])
        with patch.object(sys, "platform", "linux"), patch.object(Path, "read_text", return_value="truncated row"):
            with self.assertRaisesRegex(CompletionError, "cannot parse mount table"):
                scratch_mounts()

    def accept(self):
        (self.task / "product").write_text("accepted\n", encoding="utf-8")
        self.g("add", "product", work=self.task)
        self.g("commit", "-m", "scoped task", work=self.task)
        self.sha = self.g("rev-parse", "HEAD", work=self.task)
        evidence = self.task / ".devlyn"
        evidence.mkdir(exist_ok=True)
        (evidence / "checks.txt").write_text("actual fixture check: accepted bytes\n", encoding="utf-8")
        a = {"kind": "direct", "task": "fixture", "source_sha": self.sha,
             "checks": [{"command": "fixture byte assertion", "evidence": ".devlyn/checks.txt"}]}
        self.assertEqual((self.task / "product").read_text(encoding="utf-8"), "accepted\n")
        self.acceptance = evidence / "acceptance.json"
        self.acceptance.write_text(json.dumps(a), encoding="utf-8")

    def complete(self, *args, success=True, cwd=None, acceptance=True):
        command_args = ["complete", "--receipt", self.receipt]
        if acceptance:
            command_args += ["--acceptance", self.acceptance]
        return self.cli(*command_args, *args, success=success, cwd=cwd)

    def test_reject_repository_rewrite_before_allocation(self):
        intended = "https://github.com/test/project.git"
        destination = "https://github.com/test/other.git"
        self.g("config", "url." + destination + ".insteadOf", intended)
        self.assertEqual(self.g("config", "--get", "remote.origin.url"), intended)
        self.assertEqual(self.g("remote", "get-url", "--all", "origin"), destination)
        self.assertEqual(self.g("remote", "get-url", "--push", "--all", "origin"), destination)
        local_refs = self.g("show-ref")
        remote_refs = self.run_cmd(["git", "--git-dir", str(self.bare), "show-ref"]).stdout
        server = self.data.read_bytes()
        result, r = self.cli("allocate", "--repo", self.work, "--task", "fixture", "--branch", "task/fixture", "--repository", "test/project", "--base", "main", "--worktree", self.root / "linked", success=False)
        self.assertEqual(self.g("show-ref"), local_refs, r.stdout)
        self.assertEqual(self.run_cmd(["git", "--git-dir", str(self.bare), "show-ref"]).stdout, remote_refs)
        self.assertEqual(self.data.read_bytes(), server)
        self.assertEqual(self.g("branch", "--show-current"), "main")
        self.assertFalse((self.root / "linked").exists())
        self.assertFalse((self.work / ".git/devlyn-completion").exists())
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("repository differs from remote", result["reason"])

    def test_same_repository_transport_alias(self):
        intended = "https://github.com/test/project.git"
        alias = "git@github.com:test/project.git"
        self.g("config", "url." + alias + ".insteadOf", intended)
        self.allocate(); self.accept()
        self.assertEqual(json.loads(self.receipt.read_text(encoding="utf-8"))["remote_url"], {"literal": intended, "fetch": alias, "push": alias})
        result, _ = self.complete("--mode", "pr")
        self.assertEqual(result["status"], "PR")
        self.assertEqual(self.g("ls-remote", "origin", "refs/heads/task/fixture").split()[0], self.sha)
        d = json.loads(self.data.read_text(encoding="utf-8"))
        self.assertEqual((d["pushs"], d.get("merges", 0), d["prs"][0]["autoMergeRequest"]), (1, 0, None))

    def test_pr_mode_disables_only_owned_auto_merge(self):
        self.allocate(); self.accept()
        self.configure(pending=True)
        result, _ = self.complete("--mode", "auto")
        self.assertEqual(result["status"], "PENDING")
        result, _ = self.complete("--mode", "pr")
        self.assertEqual(result["status"], "PR")
        d = json.loads(self.data.read_text(encoding="utf-8"))
        self.assertEqual((d["disables"], d["prs"][0]["autoMergeRequest"]), (1, None))
        self.configure(prs=[dict(d["prs"][0], isCrossRepository=True, autoMergeRequest={"enabledAt": "now"})])
        _, r = self.complete("--mode", "pr", success=False)
        self.assertIn("PR head repository differs", json.loads(r.stdout)["reason"])
        d = json.loads(self.data.read_text(encoding="utf-8"))
        self.assertEqual((d["disables"], d["prs"][0]["autoMergeRequest"]), (1, {"enabledAt": "now"}))

    def test_remote_rewrite_after_allocation_is_rejected(self):
        self.allocate(); self.accept()
        self.g("config", "url.git@github.com:test/project.git.insteadOf", "https://github.com/test/project.git")
        local_refs = self.g("show-ref")
        remote_refs = self.run_cmd(["git", "--git-dir", str(self.bare), "show-ref"]).stdout
        server = self.data.read_bytes()
        result, r = self.complete(success=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("remote URL changed since allocation", result["reason"])
        self.assertEqual(self.g("show-ref"), local_refs)
        self.assertEqual(self.run_cmd(["git", "--git-dir", str(self.bare), "show-ref"]).stdout, remote_refs)
        self.assertEqual(self.data.read_bytes(), server)
        self.assertTrue(self.task.exists())

    def test_reject_previously_bound_repository_rewrite(self):
        self.allocate(); self.accept()
        destination = "https://github.com/test/other.git"
        self.g("config", "url." + destination + ".insteadOf", "https://github.com/test/project.git")
        # Reproduce a receipt the old literal-only allocation check accepted.
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        receipt["remote_url"].update(fetch=destination, push=destination)
        self.receipt.write_text(json.dumps(receipt), encoding="utf-8")
        local_refs = self.g("show-ref")
        remote_refs = self.run_cmd(["git", "--git-dir", str(self.bare), "show-ref"]).stdout
        server = self.data.read_bytes()
        result, r = self.complete(success=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("repository differs from remote", result["reason"])
        self.assertEqual(self.g("show-ref"), local_refs)
        self.assertEqual(self.run_cmd(["git", "--git-dir", str(self.bare), "show-ref"]).stdout, remote_refs)
        self.assertEqual(self.data.read_bytes(), server)
        self.assertTrue(self.task.exists())

    def test_pr_pending_and_retry(self):
        self.allocate(); self.accept()
        result, _ = self.complete("--mode", "pr")
        self.assertEqual(result["status"], "PR")
        self.assertTrue(self.task.exists())
        self.configure(pending=True)
        for _ in range(2):
            result, _ = self.complete("--mode", "auto")
            self.assertEqual(result["status"], "PENDING")
        d = json.loads(self.data.read_text(encoding="utf-8"))
        self.assertEqual((d["creates"], d["merges"], d["pushs"]), (1, 1, 1))

    def test_legacy_in_place_retains_checked_out_branch_then_retires_refs(self):
        self.allocate_legacy(); self.accept()
        (self.task / "ignored").mkdir()
        (self.task / "ignored" / "user.txt").write_text("retain me", encoding="utf-8")
        self.complete("--mode", "pr", "--writers-stopped")
        self.merge_pr()
        before = self.anchor_state()
        receipt, task = self.receipt, self.task
        result = self.allocate("next")
        self.assertEqual(result["reconciled"][0]["status"], "RETAINED")
        self.assertIn(str(task), result["reconciled"][0]["reason"])
        self.assertIn("switch", result["reconciled"][0]["reason"])
        self.assertEqual(self.anchor_state(), before)
        self.assertNotEqual(self.g("branch", "--list", "task/fixture"), "")
        self.assertEqual(self.g("ls-remote", "origin", "refs/heads/task/fixture").split()[0], self.sha)
        self.g("switch", "main")
        (self.work / "product").write_text("owner edits\n", encoding="utf-8")
        (self.work / "untracked").write_bytes(b"owner data")
        before = self.anchor_state()
        result = self.allocate("retired")
        self.assertEqual([(row["receipt"], row["status"]) for row in result["reconciled"]], [(str(receipt), "COMPLETE")])
        self.assertEqual(self.anchor_state(), before)
        self.assertEqual((self.work / "untracked").read_bytes(), b"owner data")
        self.assertEqual((task / "ignored/user.txt").read_text(encoding="utf-8"), "retain me")
        self.assertEqual(self.g("branch", "--list", "task/fixture"), "")
        self.assertEqual(self.g("ls-remote", "origin", "refs/heads/task/fixture"), "")
        self.receipt, self.task = receipt, task
        again, _ = self.complete(acceptance=False)
        self.assertEqual(again["status"], "COMPLETE")

    def test_pr_mode_cleans_after_human_merge(self):
        self.allocate(); self.accept()
        self.complete("--mode", "pr")
        self.merge_pr()
        before = self.data.read_bytes()
        result, _ = self.complete("--mode", "pr", "--writers-stopped")
        self.assertEqual(result["status"], "COMPLETE")
        self.assertFalse(self.task.exists())
        self.assertEqual(self.g("branch", "--list", "task/fixture"), "")
        self.assertEqual(self.g("ls-remote", "origin", "refs/heads/task/fixture"), "")
        saved, current = json.loads(before), json.loads(self.data.read_bytes())
        self.assertEqual((current["merges"], current.get("disables", 0)), (saved["merges"], saved.get("disables", 0)))

    @unittest.skipUnless(sys.platform == "darwin" or sys.platform.startswith("linux"), "writer observation requires POSIX")
    def test_nested_repository_or_worktree_retains_tree(self):
        self.allocate(); self.accept()
        _, r = self.cli("allocate", "--repo", self.work, "--task", "inner", "--branch", "task/inner", "--repository", "test/project",
                        "--base", "main", "--worktree", self.task / "ignored" / "inner", success=False)
        self.assertIn("disjoint from every registered worktree", json.loads(r.stdout)["reason"])
        nested = self.task / "ignored" / "nested"
        self.g("worktree", "add", "-b", "nested/work", str(nested), "main")
        (nested / "product").write_text("unsaved nested work\n", encoding="utf-8")
        clone = self.task / "ignored" / "clone"
        self.run_cmd(["git", "init", "--initial-branch=main", str(clone)])
        for remove in (lambda: self.g("worktree", "remove", "--force", str(nested)), lambda: shutil.rmtree(clone)):
            _, r = self.complete("--mode", "auto", "--writers-stopped", success=False)
            self.assertIn("nested repository or worktree", json.loads(r.stdout)["reason"])
            self.assertTrue(self.task.exists())
            self.assertNotEqual(self.g("branch", "--list", "task/fixture"), "")
            if nested.exists():
                self.assertEqual((nested / "product").read_text(encoding="utf-8"), "unsaved nested work\n")
            remove()
        result, _ = self.complete("--mode", "auto", "--writers-stopped")
        self.assertEqual(result["status"], "COMPLETE")
        self.assertFalse(self.task.exists())

    @unittest.skipUnless(sys.platform == "darwin" or sys.platform.startswith("linux"), "writer observation requires POSIX")
    def test_default_mode_merges_when_possible_and_cleans(self):
        self.allocate(); self.accept()
        result, _ = self.complete("--writers-stopped")
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(json.loads(self.data.read_text(encoding="utf-8")).get("merges"), 1)
        self.assertFalse(self.task.exists())
        self.assertEqual(self.g("branch", "--list", "task/fixture"), "")

    def test_unobservable_writers_settle_a_merged_delivery_and_retain_the_workspace(self):
        from unittest.mock import patch
        self.allocate(); self.accept()
        self.complete("--mode", "pr", "--writers-stopped")
        self.merge_pr()
        args = argparse.Namespace(receipt=str(self.receipt), acceptance=None, mode=None, local_only=False, writers_stopped=False)
        with patch.object(sys, "platform", "win32"), patch.dict(os.environ, self.env):
            result = complete(args)
        self.assertEqual((result["status"], result["delivery_status"]), ("CLEANUP_PENDING", "COMPLETE"))
        self.assertIn("writer observation unsupported", result["workspace_cleanup"]["reason"])
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertEqual((receipt["delivery"], receipt.get("status")), ("COMPLETE", None))
        self.assertTrue(self.task.exists())
        self.assertNotEqual(self.g("branch", "--list", "task/fixture"), "")
        self.assertEqual(self.g("ls-remote", "origin", "refs/heads/task/fixture").split()[0], self.sha)

    def test_release_is_refused_from_inside_the_task_tree(self):
        self.allocate(); self.accept()
        _, r = self.complete("--mode", "pr", "--writers-stopped", cwd=self.task, success=False)
        self.assertIn("caller cwd is inside", json.loads(r.stdout)["reason"])
        self.assertNotIn("writers_released", json.loads(self.receipt.read_text(encoding="utf-8")))

    @unittest.skipUnless(sys.platform == "darwin" or sys.platform.startswith("linux"), "writer observation requires POSIX")
    def test_squash_merge_cleans_and_recovery_ref_keeps_commit(self):
        self.allocate(); self.accept()
        result, _ = self.complete("--mode", "pr", "--writers-stopped")
        self.assertEqual(result["status"], "PR")
        bare = ["git", "--git-dir", str(self.bare)]
        base = self.run_cmd(bare + ["rev-parse", "refs/heads/main"]).stdout.strip()
        tree = self.run_cmd(bare + ["rev-parse", self.sha + "^{tree}"]).stdout.strip()
        squash = self.run_cmd(bare + ["commit-tree", tree, "-p", base, "-m", "squash fixture"]).stdout.strip()
        self.run_cmd(bare + ["update-ref", "refs/heads/main", squash, base])
        pr = json.loads(self.data.read_text(encoding="utf-8"))["prs"][0]
        self.configure(prs=[dict(pr, state="MERGED", mergedAt="now", mergeCommit={"oid": squash})])
        result, _ = self.complete()
        self.assertEqual(result["status"], "COMPLETE")
        self.assertFalse(self.task.exists())
        self.assertEqual(self.g("branch", "--list", "task/fixture"), "")
        self.assertEqual(self.g("ls-remote", "origin", "refs/heads/task/fixture"), "")
        self.assertEqual(self.g("rev-parse", json.loads(self.receipt.read_text(encoding="utf-8"))["recovery_ref"]), self.sha)
        self.assertFalse((self.work / ".git" / "FETCH_HEAD").exists())

    def test_linked_ignored_output_disposed_and_records_preserved(self):
        self.allocate(); self.accept()
        for relative, raw in (("node_modules/x", b"build"), (".env", b"SECRET=value\n"), (".devlyn/runs/extra/log", b"extra\x00bytes\n")):
            path = self.task / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            path.chmod(0o640)
        records = snapshot_files(self.task, [".devlyn"])
        (self.task / "untracked").write_bytes(b"owner data")
        _, process = self.complete("--mode", "auto", "--writers-stopped", success=False)
        self.assertNotEqual(process.returncode, 0)
        self.assertTrue(self.task.exists())
        self.assertEqual((self.task / "untracked").read_bytes(), b"owner data")
        self.assertNotEqual(self.g("branch", "--list", "task/fixture"), "")
        (self.task / "untracked").unlink()
        result, _ = self.complete("--mode", "auto", "--writers-stopped")
        self.assertEqual(result["status"], "COMPLETE")
        self.assertFalse(self.task.exists())
        verify_files(self.receipt.parent / "records", records)
        self.assertEqual(snapshot_files(self.receipt.parent / "records", [".devlyn"]), records)
        self.assertEqual(self.g("branch", "--list", "task/fixture"), "")
        self.assertEqual(self.g("ls-remote", "origin", "refs/heads/task/fixture"), "")

    def test_reconcile_released_merge_and_retains_without_release(self):
        self.allocate(); self.accept()
        result, _ = self.complete("--mode", "pr")
        self.assertEqual(result["status"], "PR")
        receipt, task = self.receipt, self.task
        self.merge_pr()
        result = self.allocate("unreleased")
        self.assertEqual(len(result["reconciled"]), 1)
        self.assertEqual(result["reconciled"][0]["status"], "RETAINED")
        self.assertIn("writers", result["reconciled"][0]["reason"])
        self.assertTrue(task.exists())
        self.assertNotEqual(self.g("branch", "--list", "task/fixture"), "")
        self.assertEqual(self.g("ls-remote", "origin", "refs/heads/task/fixture").split()[0], self.sha)
        # Reopen only the fixture PR to exercise the owner's pre-merge release.
        d = json.loads(self.data.read_text())
        self.configure(prs=[dict(d["prs"][0], state="OPEN", mergedAt=None, mergeCommit=None)])
        self.receipt, self.task = receipt, task
        result, _ = self.complete("--mode", "pr", "--writers-stopped")
        self.assertEqual(result["status"], "PR")
        self.assertTrue(json.loads(receipt.read_text())["writers_released"])
        self.merge_pr()
        server = json.loads(self.data.read_text())
        result = self.allocate("released")
        self.assertEqual([(row["receipt"], row["status"]) for row in result["reconciled"]], [(str(receipt), "COMPLETE")])
        self.assertFalse(task.exists())
        self.assertEqual(self.g("branch", "--list", "task/fixture"), "")
        self.assertEqual(self.g("ls-remote", "origin", "refs/heads/task/fixture"), "")
        current = json.loads(self.data.read_text())
        self.assertEqual((current["pushs"], current["creates"], current["merges"], current.get("disables", 0)),
                         (server["pushs"], server["creates"], server["merges"], server.get("disables", 0)))

    def test_reconcile_checks_repo_policy_before_cleanup(self):
        self.allocate(); self.accept()
        self.complete("--mode", "pr", "--writers-stopped")
        self.merge_pr()
        receipt, task = self.receipt, self.task
        self.configure(default_branch="changed")
        result = self.allocate("next")
        self.assertEqual([(row["receipt"], row["status"]) for row in result["reconciled"]], [(str(receipt), "RETAINED")])
        self.assertIn("base/default branch changed", result["reconciled"][0]["reason"])
        self.assertTrue(task.exists())
        self.assertEqual(self.g("rev-parse", "task/fixture"), self.sha)
        self.assertEqual(self.g("ls-remote", "origin", "refs/heads/task/fixture").split()[0], self.sha)

    def test_reconcile_skips_open_and_unaccepted_and_retains_in_use_tree(self):
        self.allocate(); self.accept()
        self.complete("--mode", "pr", "--writers-stopped")
        receipt, task = self.receipt, self.task
        before = receipt.read_bytes()
        result = self.allocate("unaccepted")
        self.assertEqual(result["reconciled"], [])
        self.assertEqual(receipt.read_bytes(), before)
        unaccepted, unaccepted_tree = self.receipt, self.task
        saved = json.loads(unaccepted.read_text())
        saved.update(pr_number=1, writers_released=True)
        unaccepted.write_text(json.dumps(saved))
        unaccepted_before = unaccepted.read_bytes()
        pr = json.loads(self.data.read_text())["prs"][0]
        self.configure(prs=[dict(pr, state="CLOSED")])
        result = self.allocate("closed")
        self.assertEqual(result["reconciled"], [])
        self.assertEqual(receipt.read_bytes(), before)
        self.assertTrue(task.exists())
        self.configure(prs=[pr])
        self.merge_pr()
        self.g("worktree", "lock", str(task))
        result = self.allocate("locked")
        self.assertEqual(len(result["reconciled"]), 1)
        self.assertEqual(result["reconciled"][0]["status"], "RETAINED")
        self.assertIn("locked", result["reconciled"][0]["reason"])
        self.assertTrue(task.exists())
        self.g("worktree", "unlock", str(task))
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"], cwd=task)
        try:
            result = self.allocate("active")
            self.assertEqual(len(result["reconciled"]), 1)
            self.assertEqual(result["reconciled"][0]["status"], "RETAINED")
            self.assertIn("active process", result["reconciled"][0]["reason"])
            self.assertTrue(task.exists())
            self.assertIsNone(child.poll())
        finally:
            child.terminate(); child.wait(timeout=5)
        self.assertNotEqual(self.g("branch", "--list", "task/fixture"), "")
        self.assertEqual(self.g("ls-remote", "origin", "refs/heads/task/fixture").split()[0], self.sha)
        self.assertEqual(unaccepted.read_bytes(), unaccepted_before)
        self.assertTrue(unaccepted_tree.exists())

    def test_reconcile_already_retired_tree_and_branch(self):
        self.allocate(); self.accept()
        self.complete("--mode", "pr", "--writers-stopped")
        self.merge_pr()
        receipt, task = self.receipt, self.task
        self.g("worktree", "remove", str(task))
        self.g("update-ref", "-d", "refs/heads/task/fixture", self.sha)
        before = self.anchor_state()
        result = self.allocate("next")
        self.assertEqual([(row["receipt"], row["status"]) for row in result["reconciled"]], [(str(receipt), "COMPLETE")])
        self.assertFalse(task.exists())
        self.assertEqual(self.g("branch", "--list", "task/fixture"), "")
        self.assertEqual(self.g("ls-remote", "origin", "refs/heads/task/fixture"), "")
        self.assertEqual(self.anchor_state(), before)

    def test_reconcile_never_removes_allocation_anchor(self):
        self.allocate(); self.accept()
        self.complete("--mode", "pr", "--writers-stopped")
        self.merge_pr()
        before = self.anchor_state(self.task)
        result, _ = self.cli("allocate", "--repo", self.task, "--task", "next", "--branch", "task/next",
            "--repository", "test/project", "--base", "main", "--worktree", self.root / "next")
        self.assertEqual(result["status"], "ALLOCATED")
        self.assertEqual(len(result["reconciled"]), 1)
        self.assertEqual(result["reconciled"][0]["status"], "RETAINED")
        self.assertIn("anchor", result["reconciled"][0]["reason"])
        self.assertEqual(self.anchor_state(self.task), before)
        self.assertNotEqual(self.g("branch", "--list", "task/fixture"), "")
        self.assertEqual(self.g("ls-remote", "origin", "refs/heads/task/fixture").split()[0], self.sha)

    def test_reconcile_reports_scratch_cleanup_pending(self):
        scratch = Path(self.allocate()["scratch"])
        self.accept()
        self.complete("--mode", "pr", "--writers-stopped")
        self.merge_pr()
        receipt, task = self.receipt, self.task
        (scratch / "object").write_bytes(b"rebuildable")
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"], cwd=scratch)
        try:
            result = self.allocate("next")
            self.assertEqual(len(result["reconciled"]), 1)
            row = result["reconciled"][0]
            self.assertEqual((row["status"], row["delivery_status"]), ("CLEANUP_PENDING", "COMPLETE"))
            self.assertEqual(row["scratch_cleanup"]["status"], "RETAINED")
            self.assertIn("active process", row["scratch_cleanup"]["reason"])
            self.assertEqual((scratch / "object").read_bytes(), b"rebuildable")
            self.assertIsNone(child.poll())
        finally:
            child.terminate(); child.wait(timeout=5)
        self.assertFalse(task.exists())
        self.assertEqual(self.g("branch", "--list", "task/fixture"), "")
        self.assertEqual(self.g("ls-remote", "origin", "refs/heads/task/fixture"), "")
        self.configure(default_branch="changed")
        server = json.loads(self.data.read_text())
        result = self.allocate("retry")
        self.assertEqual([(row["receipt"], row["status"]) for row in result["reconciled"]], [(str(receipt), "COMPLETE")])
        self.assertFalse(any(scratch.iterdir()))
        self.assertEqual(json.loads(self.data.read_text()), server)
        self.assertEqual(self.allocate("later")["reconciled"], [])

    def test_reconcile_retries_unattempted_scratch_cleanup(self):
        scratch = Path(self.allocate()["scratch"])
        self.accept()
        self.complete("--mode", "auto", "--writers-stopped")
        receipt = self.receipt
        saved = json.loads(receipt.read_text())
        del saved["scratch_cleanup"]
        receipt.write_text(json.dumps(saved))
        (scratch / "object").write_bytes(b"rebuildable")
        result = self.allocate("next")
        self.assertEqual([(row["receipt"], row["status"]) for row in result["reconciled"]], [(str(receipt), "COMPLETE")])
        self.assertFalse(any(scratch.iterdir()))

    def test_reconcile_retains_busy_receipt_without_waiting(self):
        self.allocate(); self.accept()
        self.complete("--mode", "pr", "--writers-stopped")
        self.merge_pr()
        code = "import pathlib, runpy, sys, time\nwith runpy.run_path(sys.argv[1])['file_lock'](pathlib.Path(sys.argv[2]), blocking=True):\n print('locked', flush=True)\n time.sleep(30)\n"
        child = subprocess.Popen([sys.executable, "-c", code, str(Path(__file__).resolve().with_name("platform-support.py")),
                                  str(self.receipt.parent / "lock")], stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(), "locked")
            process = subprocess.run([sys.executable, str(Path(__file__).resolve()), "allocate", "--repo", str(self.work),
                "--task", "next", "--branch", "task/next", "--repository", "test/project", "--base", "main",
                "--worktree", str(self.root / "next")], cwd=self.root, env=self.env, capture_output=True, text=True, timeout=10)
            self.assertEqual(process.returncode, 0, process.stdout+process.stderr)
            result = json.loads(process.stdout)
            self.assertEqual(result["status"], "ALLOCATED")
            self.assertEqual(len(result["reconciled"]), 1)
            self.assertEqual(result["reconciled"][0]["status"], "RETAINED")
            self.assertIn("lock", result["reconciled"][0]["reason"])
            self.assertTrue(self.task.exists())
            self.assertNotEqual(self.g("branch", "--list", "task/fixture"), "")
            self.assertEqual(self.g("ls-remote", "origin", "refs/heads/task/fixture").split()[0], self.sha)
            self.assertIsNone(child.poll())
        finally:
            child.terminate(); child.wait(timeout=5)
            child.stdout.close()

    def test_reconcile_retains_malformed_receipt_without_failing_allocation(self):
        self.allocate()
        receipt, task = self.receipt, self.task
        receipt.write_text("[]", encoding="utf-8")
        result = self.allocate("next")
        self.assertEqual(result["status"], "ALLOCATED")
        self.assertTrue(self.task.exists())
        self.assertEqual(len(result["reconciled"]), 1)
        self.assertEqual(result["reconciled"][0]["status"], "RETAINED")
        self.assertEqual(result["reconciled"][0]["receipt"], str(receipt))
        self.assertTrue(result["reconciled"][0]["reason"])
        self.assertEqual(receipt.read_text(), "[]")
        self.assertTrue(task.exists())
        self.assertNotEqual(self.g("branch", "--list", "task/fixture"), "")

    def test_records_refuse_symlink_nonregular_and_tampered_resume(self):
        self.allocate(); self.accept()
        self.complete("--mode", "pr", "--writers-stopped")
        self.merge_pr()
        other = self.root / "owner-file"
        other.write_bytes(b"owner data")
        link = self.task / ".devlyn/link"
        link.symlink_to(other)
        result, _ = self.complete(success=False)
        self.assertIn("path escapes custody", result["reason"])
        self.assertTrue(self.task.exists())
        self.assertTrue(link.is_symlink())
        self.assertEqual(other.read_bytes(), b"owner data")
        link.unlink()
        if hasattr(os, "mkfifo"):
            os.mkfifo(link)
            result, _ = self.complete(success=False)
            self.assertIn("regular file", result["reason"])
            self.assertTrue(self.task.exists())
            link.unlink()
        saved = self.receipt.parent / "records/.devlyn"
        shutil.copytree(self.task / ".devlyn", saved)
        (saved / "checks.txt").write_bytes(b"tampered copy")
        result, _ = self.complete(success=False)
        self.assertIn("bytes/mode changed", result["reason"])
        self.assertEqual((saved / "checks.txt").read_bytes(), b"tampered copy")
        self.assertTrue(self.task.exists())
        self.assertNotEqual(self.g("branch", "--list", "task/fixture"), "")
        self.assertEqual(self.g("ls-remote", "origin", "refs/heads/task/fixture").split()[0], self.sha)
        shutil.copy2(self.task / ".devlyn/checks.txt", saved / "checks.txt")
        result, _ = self.complete()
        self.assertEqual(result["status"], "COMPLETE")
        self.assertFalse(self.task.exists())

    def test_linked_custody_and_interrupted_removal(self):
        self.allocate(); self.accept()
        self.configure(interrupt_remove=True)
        result, r = self.complete("--writers-stopped", "--mode", "auto", success=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(self.task.exists())
        saved = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertNotIn("cleanup_started", saved)
        recovered = self.receipt.parent / "custody" / ".devlyn/checks.txt"
        self.assertEqual(hashlib.sha256(recovered.read_bytes()).hexdigest(), saved["files"][".devlyn/checks.txt"]["sha256"])
        result, _ = self.complete("--writers-stopped", acceptance=False)
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(self.g("show", saved["recovery_ref"]+":product"), "accepted")

    def test_reject_invalid_policy_before_push(self):
        self.allocate(); self.accept()
        for value in ("typo", "", " auto"):
            self.g("config", "--local", "devlyn.completionMode", value)
            _, r = self.complete("--mode", "pr", success=False)
            self.assertNotEqual(r.returncode, 0)
        result, _ = self.complete("--local-only")
        self.assertEqual(result["status"], "LOCAL_ONLY")
        self.assertEqual(json.loads(self.data.read_text(encoding="utf-8")).get("creates", 0), 0)

    def test_unverified_descendant_is_never_merged(self):
        self.allocate(); self.accept()
        result, _ = self.complete("--mode", "pr")
        self.assertEqual(result["status"], "PR")
        (self.task / "product").write_text("unverified", encoding="utf-8")
        self.g("add", "product", work=self.task)
        self.g("commit", "-m", "unverified", work=self.task)
        _, r = self.complete(success=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(json.loads(self.data.read_text(encoding="utf-8")).get("merges", 0), 0)

    def test_interrupted_external_effects(self):
        self.allocate(); self.accept()
        for effect in ("push", "create"):
            self.configure(**{"interrupt_"+effect: True})
            _, r = self.complete("--writers-stopped", "--mode", "auto", success=False)
            self.assertNotEqual(r.returncode, 0)
        # A merge command that fails after merging is judged by the PR state, not its exit code.
        self.configure(interrupt_merge=True)
        result, _ = self.complete("--writers-stopped")
        self.assertEqual(result["status"], "COMPLETE")
        d = json.loads(self.data.read_text(encoding="utf-8"))
        self.assertEqual((d["pushs"], d["creates"], d["merges"]), (1, 1, 1))

    def test_retains_dirty_locked_and_active_tree(self):
        self.allocate(); self.accept()
        for case in ("no-yield", "dirty", "untracked", "locked", "cwd"):
            path = self.task / ("product" if case == "dirty" else "unknown")
            if case in {"dirty", "untracked"}:
                path.parent.mkdir(exist_ok=True); path.write_text("do not delete", encoding="utf-8")
            if case == "locked": self.g("worktree", "lock", str(self.task))
            with self.subTest(case=case):
                _, r = self.complete("--mode", "auto", *([] if case == "no-yield" else ["--writers-stopped"]), cwd=self.task if case == "cwd" else None, success=False)
                self.assertNotEqual(r.returncode, 0)
                self.assertTrue(self.task.exists())
                self.assertNotEqual(self.g("branch", "--list", "task/fixture"), "")
            if case == "untracked": path.unlink()
            if case == "dirty": path.write_text("accepted\n", encoding="utf-8")
            if case == "locked": self.g("worktree", "unlock", str(self.task))

    def test_no_adoption_and_remote_head_race(self):
        _, r = self.cli("allocate", "--repo", self.work, "--task", "foreign", "--branch", "main", "--repository", "test/project", "--base", "main", "--worktree", self.root / "foreign", success=False)
        self.assertNotEqual(r.returncode, 0)
        self.allocate(); self.accept()
        self.complete("--mode", "pr")
        self.run_cmd(["git", "--git-dir", str(self.bare), "update-ref", "refs/heads/task/fixture", self.g("rev-parse", "main")])
        _, r = self.complete(success=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(json.loads(self.data.read_text(encoding="utf-8")).get("merges",0), 0)

    def test_concurrent_completions(self):
        self.allocate(); self.accept(); self.configure(pending=True)
        args = [sys.executable, str(Path(__file__).resolve()), "complete", "--receipt", str(self.receipt), "--acceptance", str(self.acceptance), "--mode", "auto"]
        procs = [subprocess.Popen(args, cwd=self.root, env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8") for _ in range(2)]
        for proc in procs:
            out, err = proc.communicate(timeout=30)
            self.assertEqual(proc.returncode, 0, out+err)
        d = json.loads(self.data.read_text(encoding="utf-8"))
        self.assertEqual((d["pushs"], d["creates"], d["merges"]), (1,1,1))

    def test_custody_failure_and_evidence_tamper(self):
        self.allocate(); self.accept()
        bad = self.receipt.parent / "custody/.devlyn/checks.txt"
        bad.parent.mkdir(parents=True)
        bad.write_text("partial interrupted copy", encoding="utf-8")
        _, r = self.complete("--writers-stopped", success=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertTrue(self.task.exists())
        self.assertEqual((self.task / ".devlyn/checks.txt").read_text(encoding="utf-8"), "actual fixture check: accepted bytes\n")
        self.assertEqual(self.g("ls-remote", "origin", "refs/heads/task/fixture"), "")
        bad.unlink()  # Owner repairs only the identified corrupt fixture copy.
        self.complete("--mode", "pr")
        (self.task / ".devlyn/checks.txt").write_text("altered after acceptance", encoding="utf-8")
        _, r = self.complete("--mode", "auto", success=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(json.loads(self.data.read_text(encoding="utf-8")).get("merges",0), 0)

    def test_actual_foreign_writer_and_registration(self):
        self.allocate(); self.accept()
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"], cwd=self.task)
        try:
            _, r = self.complete("--writers-stopped", "--mode", "auto", success=False)
            self.assertNotEqual(r.returncode, 0)
            self.assertTrue(self.task.exists())
            self.assertIn("active process", json.loads(r.stdout)["reason"])
        finally:
            child.terminate(); child.wait(timeout=5)
        # A foreign branch in the same registered tree never inherits ownership.
        self.g("switch", "-c", "foreign", work=self.task)
        _, r = self.complete("--writers-stopped", success=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertTrue(self.task.exists())
        self.assertNotEqual(self.g("branch", "--list", "task/fixture"), "")

    def test_remote_compare_delete_race(self):
        self.allocate(); self.accept()
        race = self.g("rev-parse", "main")
        self.configure(remote_delete_race=True, race_sha=race)
        _, r = self.complete("--writers-stopped", "--mode", "auto", success=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.g("ls-remote", "origin", "refs/heads/task/fixture").split()[0], race)
        self.assertNotEqual(self.g("branch", "--list", "task/fixture"), "")

    def test_policy_and_local_only_persist(self):
        self.allocate(); self.accept()
        self.configure(merge_allowed=False)
        result, _ = self.complete()
        self.assertEqual((result["status"], result["merge_refused"]), ("PR", "repository disallows merge commits"))
        d = json.loads(self.data.read_text(encoding="utf-8"))
        self.assertEqual((d.get("pushs", 0), d.get("merges", 0)), (1, 0))
        self.complete("--mode", "pr")
        result, _ = self.complete()
        self.assertEqual(result["status"], "PR")
        self.assertNotIn("merge_refused", result)
        self.configure(merge_allowed=True, auto_allowed=False, pending=True)
        result, _ = self.complete("--mode", "auto")
        self.assertEqual(result["status"], "PR")
        self.assertIn("disallows auto merge", result["merge_refused"])
        self.assertTrue(self.task.exists())
        # Local-only cannot rewrite the delivery of a pushed PR; a local allocation keeps it (test_local_chain_*).
        result, _ = self.complete("--no-push", success=False)
        self.assertIn("fixture already has a pushed PR https://github.com/test/project/pull/1", result["reason"])
        self.assertNotIn("local_only", json.loads(self.receipt.read_text(encoding="utf-8")))

    def test_pipeline_acceptance_is_refused_with_recovery_instruction(self):
        # Binding an archived resolve run needed the retired helpers. Whatever completion flags come with it,
        # it is refused before the receipt, a ref or the worktree changes, with the 4.1.0 command that finishes
        # it in the requested delivery mode; it never becomes direct acceptance.
        self.allocate(); self.accept()
        self.acceptance.write_text(json.dumps({"kind": "pipeline", "task": "fixture", "source_sha": self.sha,
                                               "run_id": "fixture-run"}), encoding="utf-8")
        def state():
            return (self.receipt.read_bytes(), self.g("show-ref"), self.g("rev-parse", "HEAD", work=self.task),
                    self.g("status", "--porcelain", "--untracked-files=all", work=self.task),
                    sorted(p.name for p in self.receipt.parent.iterdir() if p.name != "lock"))
        before = state()
        publish, local = "binds the pipeline acceptance before publishing", "ends as LOCAL_ONLY without binding"
        for flags, outcome in (((), publish), (("--mode", "pr"), publish), (("--mode", "auto", "--writers-stopped"), publish),
                               (("--local-only",), local), (("--local-only", "--writers-stopped"), local)):
            with self.subTest(flags=flags):
                result, r = self.complete(*flags, success=False)
                self.assertEqual((r.returncode, result["status"]), (1, "BLOCKED"))
                self.assertEqual(state(), before)
                self.assertIn("`npm pack devlyn-cli@4.1.0`", result["reason"])
                self.assertIn(shlex.join(["complete", "--receipt", str(self.receipt), "--acceptance", str(self.acceptance), *flags]) + "`",
                              result["reason"])
                self.assertIn(outcome, result["reason"])
        result, r = self.cli("accept", "--receipt", self.receipt, "--acceptance", self.acceptance, success=False)
        self.assertEqual((r.returncode, result["status"]), (1, "BLOCKED"))
        self.assertEqual(state(), before)
        self.assertIn(publish, result["reason"])
        self.assertNotIn(json.loads(before[0])["recovery_ref"], before[1])
        self.assertEqual(json.loads(self.data.read_text(encoding="utf-8")).get("pushs", 0), 0)

    def test_bound_pipeline_receipt_resumes_delivery(self):
        # A receipt an earlier release bound to a resolve run keeps its custody; delivery resumes here.
        self.allocate(); self.accept()
        self.cli("accept", "--receipt", self.receipt, "--acceptance", self.acceptance)
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        receipt["acceptance"] = {"kind": "pipeline", "task": "fixture", "source_sha": self.sha, "run_id": "fixture-run"}
        self.receipt.write_text(json.dumps(receipt), encoding="utf-8")
        result, _ = self.complete("--writers-stopped", "--mode", "auto", acceptance=False)
        self.assertEqual((result["status"], result["acceptance"]), ("COMPLETE", "pipeline"))
        self.assertFalse(self.task.exists())
        self.assertEqual(self.g("show", receipt["recovery_ref"] + ":product"), "accepted")

    def test_legacy_in_place_resume_does_not_overwrite_ignored_collision(self):
        self.allocate_legacy(); self.accept()
        self.complete("--mode", "pr", "--writers-stopped")
        self.merge_pr()
        self.g("switch", "main")
        user_file = self.task / "ignored/user.txt"
        user_file.parent.mkdir()
        user_file.write_text("retained user data", encoding="utf-8")
        before = self.anchor_state()
        self.configure(interrupt_delete=True)
        _, r = self.complete(acceptance=False, success=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.anchor_state(), before)
        other = self.root / "advance"
        self.run_cmd(["git", "clone", str(self.bare), str(other)])
        (other / "ignored").mkdir()
        (other / "ignored/user.txt").write_text("new upstream tracked file", encoding="utf-8")
        self.g("add", "-f", "ignored/user.txt", work=other)
        self.g("commit", "-m", "upstream collision", work=other)
        self.g("push", "origin", "main", work=other)
        result, _ = self.complete(acceptance=False)
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(self.anchor_state(), before)
        self.assertEqual(user_file.read_text(encoding="utf-8"), "retained user data")
        self.assertEqual(self.g("branch", "--list", "task/fixture"), "")
        self.assertEqual(self.g("ls-remote", "origin", "refs/heads/task/fixture"), "")

    def test_replaced_tree_and_unsafe_custody(self):
        self.allocate(); self.accept()
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        (self.receipt.parent / "custody").symlink_to(elsewhere, target_is_directory=True)
        _, r = self.complete(success=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(list(elsewhere.iterdir()), [])
        (self.receipt.parent / "custody").unlink()
        old = self.root / "old-tree"
        self.task.rename(old)
        shutil.copytree(old, self.task)
        _, r = self.complete(success=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("replaced", json.loads(r.stdout)["reason"])
        self.assertTrue(self.task.exists())
        self.assertEqual(json.loads(self.data.read_text(encoding="utf-8")).get("pushs",0), 0)

    def allocate_local(self, name, **source):
        args = ["allocate", "--repo", self.work, "--task", name, "--branch", "task/"+name, "--repository", "test/project",
                "--base", "main", "--worktree", self.root / name]
        for key, value in source.items():
            args += ["--" + key.replace("_", "-"), value]
        result, _ = self.cli(*args)
        self.receipt, self.task = Path(result["receipt"]), Path(result["worktree"])
        return result

    def loop_result(self, verdict="ACCEPTED"):
        (self.task / "product").write_text(verdict.lower() + "\n", encoding="utf-8")
        self.g("add", "product", work=self.task)
        self.g("commit", "-m", "loop source", work=self.task)
        self.sha = self.g("rev-parse", "HEAD", work=self.task)
        stream = self.task / ".devlyn/loop/runs/1/cmd-0.stdout"
        stream.parent.mkdir(parents=True, exist_ok=True)
        stream.write_text("check output\n", encoding="utf-8")
        self.acceptance = self.task / ".devlyn/loop/acceptance.json"
        self.acceptance.write_text(json.dumps({"kind": "loop", "task": json.loads(self.receipt.read_text())["task"], "source_sha": self.sha,
                                               "verdict": verdict, "evidence": [".devlyn/loop/runs/1/cmd-0.stdout"]}), encoding="utf-8")
        return self.cli("accept", "--receipt", self.receipt, "--acceptance", self.acceptance)[0]

    def terminal(self):
        (self.task / "queue.md").write_text("- [x] fixture\n", encoding="utf-8")
        self.g("add", "queue.md", work=self.task)
        self.g("commit", "-m", "terminal", work=self.task)
        commit = self.g("rev-parse", "HEAD", work=self.task)
        return commit, self.cli("attach", "--receipt", self.receipt, "--commit", commit, "--file", "queue.md")[0]

    def test_local_chain_starts_from_accepted_source_not_terminal_commit(self):
        base = self.g("rev-parse", "main")
        other = self.root / "advance"  # The remote advances; a local allocation never fetches it.
        self.run_cmd(["git", "clone", str(self.bare), str(other)])
        (other / "product").write_text("remote advance\n", encoding="utf-8")
        self.g("commit", "-am", "remote advance", work=other)
        self.g("push", "origin", "main", work=other)
        self.configure(pushs=0)
        result = self.allocate_local("first", local_base=base)
        receipt = json.loads(self.receipt.read_text())
        self.assertEqual((result["reconciled"], receipt["baseline"], receipt["local_only"]), ([], base, True))
        self.assertNotEqual(self.run_cmd(["git", "-C", str(self.work), "rev-parse", "--verify", "--quiet", "refs/remotes/origin/main"], success=False).returncode, 0)
        self.assertEqual(self.loop_result()["status"], "ACCEPTED")
        source = self.sha
        terminal, _ = self.terminal()
        receipt = json.loads(self.receipt.read_text())
        self.assertEqual((receipt["source_sha"], receipt["publish_sha"], self.g("rev-parse", receipt["recovery_ref"])), (source, terminal, terminal))
        first = self.receipt
        self.allocate_local("second", from_receipt=first)
        second = json.loads(self.receipt.read_text())
        self.assertEqual((second["baseline"], second["allocated_from"]["source_sha"], self.g("rev-parse", "HEAD", work=self.task)), (source, source, source))
        self.receipt = first
        result, _ = self.complete("--mode", "auto", acceptance=False)
        self.assertEqual(result["status"], "LOCAL_ONLY")
        self.assertEqual(json.loads(self.data.read_text()).get("pushs", 0), 0)

    def test_local_allocation_refuses_unaccepted_failed_or_inexact_sources(self):
        self.allocate_local("pending", local_base=self.g("rev-parse", "main"))
        predecessor = self.receipt
        args = ["allocate", "--repo", self.work, "--task", "next", "--branch", "task/next", "--repository", "test/project",
                "--base", "main", "--worktree", self.root / "next"]
        for state in ("pending", "failed"):
            if state == "failed":
                self.assertEqual(self.loop_result("FAILED")["status"], "FAILED")
            result, _ = self.cli(*args, "--from-receipt", predecessor, success=False)
            self.assertIn("predecessor has no accepted result", result["reason"])
        result, _ = self.cli(*args, "--local-base", "main", success=False)
        self.assertIn("exact local commit", result["reason"])
        self.assertEqual(self.g("branch", "--list", "task/next"), "")
        self.assertFalse((self.root / "next").exists())

    def test_remote_allocation_starts_from_an_exact_commit(self):
        # An ideate loop's first task starts from add's local commit, which its PR then carries.
        (self.work / "product").write_text("added locally\n", encoding="utf-8")
        self.g("commit", "-qam", "devlyn loop: add fixture")
        start = self.g("rev-parse", "HEAD")
        args = ["allocate", "--repo", self.work, "--task", "first", "--branch", "task/first", "--repository", "test/project",
                "--base", "main", "--worktree", self.root / "first"]
        for extra, reason in ((["--start", "main"], "--start must name an exact local commit"),
                              (["--start", start, "--local-base", start], "use one of --local-base, --from-receipt or --start")):
            self.assertIn(reason, self.cli(*args, *extra, success=False)[0]["reason"])
        result, _ = self.cli(*args, "--start", start)
        receipt = json.loads(Path(result["receipt"]).read_text(encoding="utf-8"))
        self.assertEqual((receipt["baseline"], receipt.get("local_only"), self.g("rev-parse", "HEAD", work=Path(result["worktree"]))),
                         (start, None, start))

    def test_failed_loop_result_keeps_custody_and_recovery_but_never_publishes(self):
        self.allocate()
        self.assertEqual(self.loop_result("FAILED")["status"], "FAILED")
        receipt = json.loads(self.receipt.read_text())
        self.assertEqual((receipt["product"], self.g("rev-parse", receipt["recovery_ref"])), ("FAILED", self.sha))
        self.assertTrue((self.receipt.parent / "custody/.devlyn/loop/runs/1/cmd-0.stdout").is_file())
        terminal, _ = self.terminal()
        self.assertEqual(self.g("rev-parse", receipt["recovery_ref"]), terminal)
        result, _ = self.complete("--mode", "auto", acceptance=False)
        self.assertEqual(result["status"], "FAILED")
        d = json.loads(self.data.read_text())
        self.assertEqual((d.get("pushs", 0), d.get("creates", 0)), (0, 0))

    def test_bind_requires_the_source_checkout_only_for_a_publishable_result(self):
        for verdict in ("ACCEPTED", "FAILED"):
            with self.subTest(verdict=verdict):
                self.allocate(verdict.lower() + "-detached")
                (self.task / "product").write_text("source\n", encoding="utf-8")
                self.g("add", "product", work=self.task)
                self.g("commit", "-m", "loop source", work=self.task)
                sha = self.g("rev-parse", "HEAD", work=self.task)
                self.g("checkout", "-q", "--detach", "HEAD~1", work=self.task)  # The executor left HEAD at another commit.
                acceptance = self.task / ".devlyn/loop/acceptance.json"
                acceptance.parent.mkdir(parents=True, exist_ok=True)
                (self.task / ".devlyn/loop/out.txt").write_text("check output\n", encoding="utf-8")
                acceptance.write_text(json.dumps({"kind": "loop", "task": json.loads(self.receipt.read_text())["task"], "source_sha": sha,
                                                  "verdict": verdict, "evidence": [".devlyn/loop/out.txt"]}), encoding="utf-8")
                result, _ = self.cli("accept", "--receipt", self.receipt, "--acceptance", acceptance, success=False)
                self.assertEqual(result["status"], "FAILED" if verdict == "FAILED" else "BLOCKED", result)

    def test_attach_requires_the_terminal_checkout_only_for_a_publishable_result(self):
        for verdict in ("ACCEPTED", "FAILED"):
            with self.subTest(verdict=verdict):
                self.allocate(verdict.lower())
                self.loop_result(verdict)
                (self.task / "queue.md").write_text("- [x] fixture\n", encoding="utf-8")
                self.g("add", "queue.md", work=self.task)
                self.g("commit", "-m", "terminal", work=self.task)
                terminal = self.g("rev-parse", "HEAD", work=self.task)
                self.g("checkout", "-q", "--detach", self.sha, work=self.task)  # The task ref is terminal; HEAD stays at the source.
                result, _ = self.cli("attach", "--receipt", self.receipt, "--commit", terminal, "--file", "queue.md", success=False)
                self.assertEqual(result["status"], "ATTACHED" if verdict == "FAILED" else "BLOCKED", result)

    def test_local_only_completion_binds_acceptance_custody(self):
        self.allocate(); self.accept()
        result, _ = self.complete("--local-only")
        self.assertEqual(result["status"], "LOCAL_ONLY")
        receipt = json.loads(self.receipt.read_text())
        self.assertEqual((receipt["source_sha"], self.g("rev-parse", receipt["recovery_ref"])), (self.sha, self.sha))
        verify_files(self.receipt.parent / "custody", receipt["files"])

    def test_attach_binds_only_a_queue_only_commit_and_publishes_it_with_the_source(self):
        self.allocate(); self.loop_result()
        source = self.sha
        (self.task / "product").write_text("unaccepted\n", encoding="utf-8")
        (self.task / "queue.md").write_text("- [x] fixture\n", encoding="utf-8")
        self.g("add", "product", "queue.md", work=self.task)
        self.g("commit", "-m", "mixed", work=self.task)
        result, _ = self.cli("attach", "--receipt", self.receipt, "--commit", self.g("rev-parse", "HEAD", work=self.task),
                             "--file", "queue.md", success=False)
        self.assertIn("exactly the declared queue file", result["reason"])
        self.g("reset", "--hard", source, work=self.task)
        terminal, attached = self.terminal()
        self.assertEqual(attached["status"], "ATTACHED")
        self.assertEqual(self.cli("attach", "--receipt", self.receipt, "--commit", terminal, "--file", "queue.md")[0]["status"], "ATTACHED")
        receipt = json.loads(self.receipt.read_text())
        self.assertEqual((receipt["source_sha"], receipt["publish_sha"]), (source, terminal))
        result, _ = self.complete("--mode", "pr", acceptance=False)
        self.assertEqual(result["status"], "PR")
        self.assertEqual(json.loads(self.data.read_text())["prs"][0]["headRefOid"], terminal)


if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).with_name("platform-support.py")))["configure_utf8"]()
    sys.exit(main())
