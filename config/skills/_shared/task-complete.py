#!/usr/bin/env python3
"""Outer-owner delivery and recoverable cleanup (task-completion spec, R1–7).

No phase/state writer, staging, scheduler, or implicit adoption. See
devlyn:resolve/references/task-completion.md for the owner acceptance contract.
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


def require(condition, message):
    if not condition:
        raise CompletionError(message)


def command(argv, *, cwd=None, ok=(0,)):
    result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    require(result.returncode in ok, f"{shlex.join(argv[:4])}: {result.stderr.strip() or result.stdout.strip()}")
    return result.stdout.strip()


def git(work, *args):
    return command(["git", "-C", str(work), *args])


@functools.lru_cache(maxsize=None)
def shared(name):
    return runpy.run_path(str(Path(__file__).with_name(name + ".py")))


def read_json(path):
    require(stat.S_ISREG(path.lstat().st_mode), f"JSON must be a nonsymlink regular file: {path}")
    return shared("archive_run")["loads_strict_json"](path.read_text(encoding="utf-8"))


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
               "anchor": str(work), "linked": bool(args.worktree), "allocation": "allocating"}
    policy(receipt, None)
    receipt["remote_url"] = remote_url(receipt)
    require("\n" not in receipt["remote_url"]["push"] and receipt["remote_url"]["push"] == receipt["remote_url"]["fetch"], "split/multiple remote URLs are unsupported")
    require(not ref_sha(receipt, "refs/heads/"+args.branch), "existing branch cannot be adopted")
    require(git(work, "symbolic-ref", "--short", "HEAD") == args.base, "allocate from the retained base checkout")
    require(not git(work, "status", "--porcelain", "--untracked-files=all"), "allocation requires clean tracked/untracked contents")
    receipt["baseline"] = git(work, "rev-parse", "HEAD")
    target = Path(args.worktree).absolute() if args.worktree else work
    require(target == target.resolve(), "worktree path must not traverse symlinks")
    if args.worktree:
        require(not target.exists() and not target.is_relative_to(work) and not work.is_relative_to(target), "linked worktree must be an absent disjoint path")
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
    if args.worktree:
        git(work, "worktree", "add", "-b", args.branch, str(target), receipt["baseline"])
    else:
        git(work, "switch", "-c", args.branch, receipt["baseline"])
    receipt["worktree_gitdir"] = git(target, "rev-parse", "--absolute-git-dir")
    receipt["worktree_identity"] = workspace_identity(target, Path(receipt["worktree_gitdir"]))
    receipt["allocation"] = "owned"
    atomic_json(path, receipt)
    return {"status": "ALLOCATED", "receipt": str(path), "worktree": str(target), "scratch": str(scratch)}


def pipeline_acceptance(work, acceptance, files, directory):
    run_id = acceptance["run_id"]
    require(re.fullmatch(r"[A-Za-z0-9_.-]+", run_id) and run_id not in {".", ".."}, "invalid intended run id")
    archive = safe_path(work, ".devlyn/runs/" + run_id)
    state_file = archive / "pipeline.state.json"
    classifier = shared("terminal-claim-check")
    classification, state = classifier["classify_state_bytes"](work, state_file, state_file.read_bytes(), archived=True)
    require(classification.status == "CLEAN" and state["run_id"] == run_id, "intended archive is not terminal CLEAN")
    require(state.get("mode") in {"spec", "free-form"}, "only normal archived runs may publish")
    require((state.get("source") or {}).get("type") in {"spec", "generated"}, "normal archive must bind its source contract")
    phases = state["phases"]
    success = {"PASS", "PASS_WITH_ISSUES"}
    verify = phases.get("verify") or {}
    final = phases.get("final_report") or {}
    require(verify.get("verdict") in success and final.get("verdict") == verify["verdict"], "archive did not finish successfully")
    require(not any(str((phase or {}).get("verdict", "")).startswith("BLOCKED") for phase in phases.values()), "blocked phase takes terminal precedence")
    for name in ("plan", "implement", "cleanup", "verify", "final_report", "build_gate"):
        if name == "build_gate" and "build-gate" in (state.get("bypasses") or []):
            continue
        phase = phases.get(name) or {}
        require(phase.get("completed_at") and phase.get("verdict") in success, f"required {name} evidence is incomplete")
    require(phases["cleanup"].get("post_sha") == acceptance["source_sha"], "accepted source must equal cleanup.post_sha")
    report_digest = shared("state-phase-write")["final_report_digest"](state, archive, str(archive / "final-report.md"))
    require(final.get("output_sha256") == report_digest and final.get("artifacts", {}).get("log_file") == ".devlyn/final-report.md", "final report binding mismatch")
    finish = read_json(archive / "finish-gate.summary.json")
    require(finish.get("mode") == state["mode"] and finish.get("exit") == 0 and finish.get("offenders") == 0 and not finish.get("skipped") and not finish.get("malformed"), "finish gate was not clean")
    require(read_json(archive / "verify-merge.summary.json").get("verdict") == verify["verdict"], "VERIFY summary disagrees with terminal result")
    # Existing evidence validators expect the pre-archive .devlyn layout. Rebuild
    # it in a temporary directory; never move or mutate the original archive.
    with tempfile.TemporaryDirectory(prefix="validate-", dir=directory) as tmp:
        reconstructed = Path(tmp)
        devlyn = reconstructed / ".devlyn"
        devlyn.mkdir()
        prefix = f".devlyn/runs/{run_id}/"
        for rel in files:
            if rel.startswith(prefix):
                dest = safe_path(devlyn, rel[len(prefix):])
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(safe_path(work, rel), dest)
        archive_module = shared("archive_run")
        try:
            for validator in ("dynamic_evidence_artifacts", "dynamic_invocation_artifacts", "dynamic_judge_role_artifacts"):
                archive_module[validator](devlyn, state)
        except archive_module["ArchiveError"] as exc:
            raise CompletionError(str(exc)) from exc
        evidence_module = shared("process-evidence")
        for carrier in state.get("process_evidence") or []:
            if carrier["round"] == (phases.get(carrier["phase"]) or {}).get("round"):
                require(evidence_module["bound_carrier_outcome"](reconstructed, carrier)["verdict"] == "PASS", "required process evidence failed")
        source = state.get("source") or {}
        if source.get("spec_path"):
            expected = Path(source["spec_path"]).with_name("spec.expected.json")
            original = safe_path(work, str(expected))
            if original.exists():
                dest = safe_path(reconstructed, str(expected))
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(original, dest)
                for phase in ("implement", "build_gate", "verify"):
                    obligations = evidence_module["declared_obligations"](reconstructed, state, phase)
                    if obligations:
                        carriers = [c for c in state.get("process_evidence") or [] if c.get("phase") == phase and c.get("round") == (phases.get(phase) or {}).get("round")]
                        require(len(carriers) == 1, f"missing/ambiguous current {phase} process evidence")
                        carrier = carriers[0]
                        evidence_module["validate_manifest"](reconstructed, carrier["manifest"]["path"], run_id, phase, carrier["round"], obligations)
        if evidence_module["mechanical_evidence_required"](reconstructed, state):
            require((devlyn / "spec-verify.results.json").is_file(), "required MECHANICAL results are missing")
        carrier = shared("verify-merge-findings")["mechanical_evidence_carrier"](devlyn)
        if carrier:
            require(evidence_module["bound_carrier_outcome"](reconstructed, carrier)["verdict"] == "PASS", "MECHANICAL checks did not pass")


def bind_acceptance(receipt, path, supplied):
    work = Path(receipt["worktree"])
    if receipt.get("acceptance"):
        if supplied:
            require(file_record(Path(supplied))["sha256"] == receipt["acceptance_digest"], "acceptance changed; resume with the original acceptance")
        verify_files(path.parent / "custody", receipt["files"])
        if work.exists() and not receipt.get("cleanup_started"):
            verify_files(work, receipt["files"])
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
    publish = sha
    queue = acceptance.get("queue")
    if queue:
        publish = queue["commit"]
        safe_path(work, queue["file"])
        require(gref(receipt, "rev-list", "--parents", "-n", "1", publish).split() == [publish, sha], "queue commit must be directly atop verified source with one parent")
        require(gref(receipt, "diff-tree", "--no-commit-id", "--name-only", "-r", "-z", publish).strip("\0") == queue["file"], "queue commit must change exactly the declared queue file")
    require(ref_sha(receipt, "refs/heads/"+receipt["branch"]) == publish and git(work, "rev-parse", "HEAD") == publish, "unverified source delta or changed task ref")
    paths = [str(acceptance_path.relative_to(work))]
    kind = acceptance.get("kind")
    if kind == "direct":
        checks = acceptance.get("checks")
        require(isinstance(checks, list) and checks, "direct acceptance must name actual root-accepted checks")
        for check in checks:
            require(isinstance(check.get("command"), str) and check["command"].strip(), "direct check must name its command")
            paths.append(check["evidence"])
    elif kind == "pipeline":
        paths.append(".devlyn/runs/" + acceptance["run_id"])
        state = read_json(safe_path(work, paths[-1]) / "pipeline.state.json")
        source = state.get("source") or {}
        for key in ("spec_path", "criteria_path"):
            if source.get(key):
                if key == "criteria_path" and source.get("type") == "generated":
                    require(source[key] == ".devlyn/criteria.generated.md", "generated criteria path is not canonical")
                    relative = f".devlyn/runs/{acceptance['run_id']}/criteria.generated.md"
                else:
                    relative = source[key]
                paths.append(relative)
                source_file = safe_path(work, relative)
                if relative == source[key]:
                    committed = subprocess.run(["git", "--git-dir", receipt["common_gitdir"], "show", sha+":"+relative], capture_output=True)
                    require(committed.returncode == 0 and committed.stdout == source_file.read_bytes(), "source contract changed since accepted commit")
                bound_digest = source.get(key.replace("_path", "_sha256"))
                require(file_record(source_file)["sha256"] == bound_digest, "source contract differs from run binding")
                source_path = Path(source[key])
                expected = str(source_path.with_name("spec.expected.json") if key == "spec_path" else source_path.with_suffix(".expected.json"))
                if safe_path(work, expected).exists():
                    paths.append(expected)
    else:
        raise CompletionError("acceptance kind must be direct|pipeline")
    files = snapshot_files(work, paths)
    if kind == "pipeline":
        pipeline_acceptance(work, acceptance, files, path.parent)
    custody(work, path.parent / "custody", files)
    recovery = ref_sha(receipt, receipt["recovery_ref"])
    require(recovery in {None, publish}, "recovery ref changed")
    if recovery is None:
        gref(receipt, "update-ref", receipt["recovery_ref"], publish, "0"*len(publish))
    receipt.update(acceptance=acceptance, acceptance_digest=file_record(acceptance_path)["sha256"], source_sha=sha, publish_sha=publish, files=files)
    atomic_json(path, receipt)


PR_FIELDS = "number,url,headRefName,baseRefName,headRefOid,headRepository,headRepositoryOwner,isCrossRepository,state,mergedAt,mergeCommit,autoMergeRequest"


def gh(receipt, *args):
    return command(["gh", *args, "--repo", "github.com/"+receipt["repository"]])


def repo_policy(receipt):
    info = json.loads(command(["gh", "repo", "view", "github.com/"+receipt["repository"], "--json", "nameWithOwner,url,defaultBranchRef,mergeCommitAllowed"]))
    require(info["nameWithOwner"].lower() == receipt["repository"].lower() and info["url"].lower() == "https://github.com/"+receipt["repository"].lower(), "GitHub repository identity changed")
    require(info["defaultBranchRef"]["name"] == receipt["base"] and receipt["branch"] != info["defaultBranchRef"]["name"], "base/default branch changed; retain resources")
    return info


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


def inspect_workspace(receipt, *, allow_returned=False):
    work = Path(receipt["worktree"])
    row = registrations(receipt).get(str(work))
    require(row and "locked" not in row and "prunable" not in row and "detached" not in row, "worktree missing, detached or locked; retain and inspect registration")
    expected = "refs/heads/" + receipt["branch"]
    returned = allow_returned and not receipt["linked"] and row.get("branch") == "refs/heads/"+receipt["base"] and receipt.get("cleanup_started")
    require(row.get("branch") == expected or returned, "foreign worktree branch; retain workspace")
    require(git(work, "rev-parse", "--absolute-git-dir") == receipt["worktree_gitdir"] and str(Path(git(work, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve()) == receipt["common_gitdir"], "worktree Gitdir ownership changed")
    require(workspace_identity(work, Path(receipt["worktree_gitdir"])) == receipt["worktree_identity"], "worktree/registration was replaced; receipt no longer owns it")
    if not returned:
        require(git(work, "rev-parse", "HEAD") == receipt.get("publish_sha", receipt["baseline"]), "task HEAD changed")
    require(not git(work, "status", "--porcelain", "--untracked-files=all"), "dirty/untracked workspace; retain files and commit only accepted scope")
    return returned


def stopped_writers(work, *, linked):
    require(not linked or not Path.cwd().resolve().is_relative_to(work), "caller cwd is inside removable worktree; yield it and resume from outside")
    require(not linked or not Path(__file__).resolve().is_relative_to(work), "invoke the installed helper outside the removable worktree so resume remains available")
    # The owner assertion covers its actual children; an OS observation catches
    # other currently open files/cwds, not future writers or a universal lease.
    if sys.platform == "darwin":
        result = subprocess.run(["lsof", "-Fpn", "+D", str(work)], capture_output=True, text=True, encoding="utf-8")
        require(result.returncode in {0, 1} and not result.stderr.strip(), "writer observation unavailable; retain tree and inspect writers")
        pid = None
        for line in result.stdout.splitlines():
            if line.startswith("p"):
                pid = int(line[1:])
            elif line.startswith("n") and pid != os.getpid():
                raise CompletionError(f"active process {pid} uses task files; stop/yield actual writers before resume")
    elif sys.platform.startswith("linux"):
        for process in Path("/proc").iterdir():
            if not process.name.isdigit() or int(process.name) == os.getpid():
                continue
            try:
                links = [process / "cwd", *(process / "fd").iterdir()]
                for link in links:
                    target = Path(os.readlink(link))
                    require(not target.is_absolute() or not target.is_relative_to(work), f"active process {process.name} uses task files; stop/yield it before resume")
            except FileNotFoundError:
                continue  # Process or fd exited during observation.
            except PermissionError as exc:
                raise CompletionError("unknown process access; retain tree until writer cessation can be established") from exc
    else:
        raise CompletionError("writer observation unsupported on this platform; retain workspace")


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
    stopped_writers(scratch, linked=True)
    size = 0
    for directory, dirs, files in os.walk(scratch, followlinks=False, onerror=raise_walk_error):
        require(not any(name.casefold() == ".git" for name in dirs + files), "scratch contains Git recovery data; move it to retained custody before cleanup")
        for name in dirs + files:
            item = Path(directory) / name
            info = item.lstat()
            require(info.st_dev == identity[0][0], "scratch contains a mounted filesystem; retain")
            size += info.st_size if stat.S_ISREG(info.st_mode) else 0
    stopped_writers(scratch, linked=True)
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


def cleanup(receipt, path, pr, writers_stopped):
    require(pr["state"] == "MERGED" and pr.get("mergedAt") and pr.get("mergeCommit", {}).get("oid"), "actual matching merge evidence is required")
    require(writers_stopped, "wait actual children, stop/yield known writers, then resume with --writers-stopped")
    sha = receipt["publish_sha"]
    branch_ref = "refs/heads/" + receipt["branch"]
    require(ref_sha(receipt, receipt["recovery_ref"]) == sha, "recovery reachability changed; retain resources")
    verify_files(path.parent / "custody", receipt["files"])
    require(read_json(path.parent / "manifest.json") == receipt["files"], "custody manifest changed")
    gref(receipt, "fetch", "--no-tags", receipt["remote"], "refs/heads/"+receipt["base"])
    base_sha = gref(receipt, "rev-parse", "FETCH_HEAD")
    gref(receipt, "merge-base", "--is-ancestor", pr["mergeCommit"]["oid"], base_sha)
    gref(receipt, "merge-base", "--is-ancestor", sha, pr["mergeCommit"]["oid"])
    gref(receipt, "merge-base", "--is-ancestor", receipt["source_sha"], sha)
    work = Path(receipt["worktree"])
    local = ref_sha(receipt, branch_ref)
    require(local == sha or (local is None and receipt.get("cleanup_started")), "local task ref changed; retain")
    if work.exists():
        returned = inspect_workspace(receipt, allow_returned=True)
        if not returned:
            verify_files(work, receipt["files"])
        if receipt["linked"]:
            require(work != Path(receipt["anchor"]) and work != Path(receipt["common_gitdir"]).parent, "cannot remove retained/main checkout")
            ignored = git(work, "ls-files", "--others", "--ignored", "--exclude-standard", "-z").split("\0")
            require(all(not p or p in receipt["files"] for p in ignored), "unknown ignored content; retain tree and arrange explicit custody outside this helper")
            stopped_writers(work, linked=True)
            inspect_workspace(receipt)
            verify_files(work, receipt["files"])
            receipt["cleanup_started"] = True
            atomic_json(path, receipt)
            gref(receipt, "worktree", "remove", str(work))
        else:
            # In-place ignored user data stays in the retained checkout. Native
            # switch --no-overwrite-ignore prevents a base file replacing it.
            stopped_writers(work, linked=False)
            base_ref = "refs/heads/" + receipt["base"]
            old_base = ref_sha(receipt, base_ref)
            require(old_base, "local base branch is missing")
            gref(receipt, "merge-base", "--is-ancestor", old_base, base_sha)
            receipt["cleanup_started"] = True
            atomic_json(path, receipt)
            inspect_workspace(receipt, allow_returned=True)
            if not returned:
                other = [row for p, row in registrations(receipt).items() if p != str(work) and row.get("branch") == base_ref]
                require(not other, "base checked out elsewhere; retain task checkout")
                gref(receipt, "update-ref", base_ref, base_sha, old_base)
                git(work, "switch", "--no-overwrite-ignore", receipt["base"])
            else:
                git(work, "merge", "--no-overwrite-ignore", "--ff-only", base_sha)
    else:
        require(receipt["linked"] and receipt.get("cleanup_started") and str(work) not in registrations(receipt), "missing/replaced worktree was not removed by this receipt")
    require(all(row.get("branch") != branch_ref for row in registrations(receipt).values()), "task branch is still checked out; retain ref")
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
    receipt["status"] = "COMPLETE"
    atomic_json(path, receipt)


@contextlib.contextmanager
def locked_receipt(path):
    require(path.name == "receipt.json" and path.parent.parent.name == "devlyn-completion" and path == path.resolve(), "receipt must be its original external nonsymlink path")
    require(not (path.parent / "lock").is_symlink(), "receipt lock must not be a symlink")
    with contextlib.ExitStack() as stack:
        try:
            stack.enter_context(shared("platform-support")["file_lock"](path.parent / "lock", blocking=True))
        except (ImportError, OSError, AttributeError) as exc:
            raise CompletionError(f"receipt lock unavailable: {path}: {exc}") from exc
        receipt = read_json(path)
        require(path == Path(receipt["common_gitdir"]) / "devlyn-completion" / receipt["id"] / "receipt.json", "receipt/common Gitdir binding mismatch")
        require(receipt["id"] == hashlib.sha256(receipt["branch"].encode()).hexdigest()[:24] and receipt["branch"] not in {receipt["base"], "main", "master"}, "receipt branch ownership changed")
        require(receipt["allocation"] == "owned", "allocation was interrupted; no historical adoption is permitted")
        yield receipt


def complete(args):
    path = Path(args.receipt).absolute()
    resume = shlex.join([sys.executable, str(Path(__file__).resolve()), "complete", "--receipt", str(path)] +
                        (["--writers-stopped"] if args.writers_stopped else []))
    with locked_receipt(path) as receipt:
        def result(status):
            scratch = {"status": "NOT_OWNED"}
            if "scratch_identity" in receipt:
                try:
                    scratch = clean_scratch(receipt, path, args.writers_stopped)
                except (CompletionError, OSError, ValueError, KeyError, TypeError, IndexError) as error:
                    scratch = {"status": "RETAINED", "reason": str(error), "resume": shlex.join([
                        sys.executable, str(Path(__file__).resolve()), "clean-scratch", "--receipt", str(path), "--writers-stopped"])}
                    receipt["scratch_cleanup"] = scratch
                    try:
                        atomic_json(path, receipt)
                    except OSError as record_error:
                        scratch["record_error"] = str(record_error)
            return {"status": "CLEANUP_PENDING" if status == "COMPLETE" and scratch["status"] == "RETAINED" else status,
                    "delivery_status": status, "receipt": str(path), "pr": receipt.get("pr_url"), "resume": resume,
                    "acceptance": (receipt.get("acceptance") or {}).get("kind"), "product_verdict_unchanged": True,
                    "scratch_path": str(path.parent / "scratch") if "scratch_identity" in receipt else None,
                    "scratch_cleanup": scratch}
        if args.local_only or receipt.get("local_only"):
            receipt["local_only"] = True
            atomic_json(path, receipt)
            return result("LOCAL_ONLY")
        mode = policy(receipt, args.mode or receipt.get("mode_override"))
        if args.mode:
            receipt["mode_override"] = args.mode
            atomic_json(path, receipt)
        require(remote_url(receipt) == receipt["remote_url"], "remote URL changed since allocation")
        if receipt.get("status") == "COMPLETE":
            verify_files(path.parent / "custody", receipt["files"])
            return result("COMPLETE")
        if not receipt.get("cleanup_started"):
            # Before first binding the owner has committed the product; inspect
            # uses the actual branch head until acceptance pins its exact SHA.
            current = dict(receipt, publish_sha=ref_sha(receipt, "refs/heads/"+receipt["branch"]))
            inspect_workspace(current)
        bind_acceptance(receipt, path, args.acceptance)
        if not receipt.get("cleanup_started"):
            inspect_workspace(receipt)
        info = repo_policy(receipt)
        if mode == "auto":
            require(info["mergeCommitAllowed"], "repository disallows merge commits; use pr mode or resolve policy with repository owner")
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
            require(actual in {None, receipt["publish_sha"]}, "remote task head changed; refusing to overwrite or merge")
            require(actual is not None or (not pr and not receipt.get("pushed")), "published task ref disappeared; retain and inspect")
            if actual is None:
                inspect_workspace(receipt)
                verify_files(Path(receipt["worktree"]), receipt["files"])
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
        if mode == "pr":
            return result("PR")
        if pr["state"] != "MERGED":
            inspect_workspace(receipt)
            verify_files(Path(receipt["worktree"]), receipt["files"])
            require(remote_head(receipt, receipt["branch"]) == receipt["publish_sha"], "remote head race before merge")
            if not pr.get("autoMergeRequest"):
                gh(receipt, "pr", "merge", str(pr["number"]), "--auto", "--merge", "--match-head-commit", receipt["publish_sha"])
            pr = json.loads(gh(receipt, "pr", "view", str(pr["number"]), "--json", PR_FIELDS))
            validate_pr(receipt, pr)
            if pr["state"] != "MERGED":
                return result("PENDING")
        receipt["merge"] = pr
        atomic_json(path, receipt)
        cleanup(receipt, path, pr, args.writers_stopped)
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
    allocation.add_argument("--worktree")
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
        parser.error("allocate, complete or clean-scratch is required")
    try:
        result = (allocate(args) if args.action == "allocate" else
                  clean_scratch_command(args) if args.action == "clean-scratch" else complete(args))
        print(json.dumps(result, sort_keys=True))
        return 0
    except (CompletionError, OSError, ValueError, KeyError, TypeError, IndexError, SystemExit) as exc:
        result = {"status": "BLOCKED", "reason": str(exc)}
        if args.action in {"complete", "clean-scratch"}:
            result["receipt"] = str(Path(args.receipt).absolute())
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
def save(): p.write_text(json.dumps(d), encoding="utf-8")
def remote(ref):
    r = subprocess.run([os.environ['REAL_GIT'], '--git-dir', d['bare'], 'rev-parse', '--verify', ref], capture_output=True, text=True, encoding="utf-8")
    return r.stdout.strip() if r.returncode == 0 else None
if a[:2] == ['repo', 'view']:
    assert a[2:] == ['github.com/test/project', '--json', 'nameWithOwner,url,defaultBranchRef,mergeCommitAllowed'], 'unsupported gh repo view arguments: '+str(a)
    print(json.dumps({'nameWithOwner':'test/project', 'url':'https://github.com/test/project', 'defaultBranchRef':{'name':'main'}, 'mergeCommitAllowed':d.get('merge_allowed',True)}))
elif a[:2] == ['pr', 'list']:
    assert '--repo' in a and a[a.index('--repo')+1] == 'github.com/test/project'
    print(json.dumps([d['pr']] if d.get('pr') else []))
elif a[:2] == ['pr', 'create']:
    d['creates'] = d.get('creates',0)+1
    assert not d.get('pr'), 'duplicate PR'
    head = a[a.index('--head')+1]; base = a[a.index('--base')+1]
    d['pr'] = {'number':1,'url':'https://github.com/test/project/pull/1','headRefName':head,'baseRefName':base,'headRefOid':remote('refs/heads/'+head),'headRepository':{'name':'project','owner':{'login':'test'}}, 'headRepositoryOwner':{'login':'test'},'isCrossRepository':False,'state':'OPEN','mergedAt':None,'mergeCommit':None,'autoMergeRequest':None}
    save()
    print(d['pr']['url'])
    if d.pop('interrupt_create',False): save(); sys.exit(1)
elif a[:2] == ['pr', 'view']:
    print(json.dumps(d['pr']))
elif a[:2] == ['pr', 'merge']:
    assert '--admin' not in a and '--delete-branch' not in a
    assert '--auto' in a and '--merge' in a and '--match-head-commit' in a
    sha = a[a.index('--match-head-commit')+1]
    assert sha == remote('refs/heads/'+d['pr']['headRefName'])
    d['merges'] = d.get('merges',0)+1
    if not d.get('auto_allowed',True) and d.get('pending'):
        save(); print('repository disallows auto merge',file=sys.stderr); sys.exit(1)
    if d.get('pending'):
        d['pr']['autoMergeRequest'] = {'enabledAt':'now'}
    else:
        g = [os.environ['REAL_GIT'],'--git-dir',d['bare']]
        base = remote('refs/heads/main')
        tree = subprocess.check_output(g+['rev-parse',sha+'^{tree}'],text=True, encoding="utf-8").strip()
        merge = subprocess.check_output(g+['commit-tree',tree,'-p',base,'-p',sha,'-m','merge fixture'],text=True, encoding="utf-8").strip()
        subprocess.check_call(g+['update-ref','refs/heads/main',merge,base])
        d['pr'].update(state='MERGED',mergedAt='now',mergeCommit={'oid':merge})
    save()
    if d.pop('interrupt_merge',False): save(); sys.exit(1)
else:
    raise SystemExit('unexpected gh arguments: '+str(a))
'''

GIT_WRAPPER = r'''#!/usr/bin/env python3
import json, os, pathlib, subprocess, sys
a = sys.argv[1:]
p = pathlib.Path(os.environ['FIXTURE_GH']); d = json.loads(p.read_text(encoding="utf-8"))
if 'push' in a and any(x.startswith('--force-with-lease=') for x in a) and d.pop('remote_delete_race',False):
    subprocess.check_call([os.environ['REAL_GIT'],'--git-dir',d['bare'],'update-ref','refs/heads/'+d['pr']['headRefName'],d['race_sha']])
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
        for name, body in (("gh", FAKE_GH), ("git", GIT_WRAPPER)):
            path = self.bin / name
            path.write_text(body, encoding="utf-8")
            path.chmod(0o755)
        self.env["PATH"] = str(self.bin) + os.pathsep + os.environ["PATH"]
        self.run_cmd(["git", "init", "--bare", "--initial-branch=main", str(self.bare)])
        self.run_cmd(["git", "init", "--initial-branch=main", str(self.work)])
        (self.work / ".gitignore").write_text(".devlyn/\nignored/\n", encoding="utf-8")
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

    def allocate(self, linked=False):
        args = ["allocate", "--repo", self.work, "--task", "fixture", "--branch", "task/fixture", "--repository", "test/project", "--base", "main"]
        if linked:
            args += ["--worktree", self.root / "linked"]
        result, _ = self.cli(*args)
        self.receipt = Path(result["receipt"])
        self.task = Path(result["worktree"])
        return result

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
        result, _ = self.cli("complete", "--receipt", self.receipt, "--acceptance", self.acceptance, "--writers-stopped")
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

    def accept(self, pipeline=False, queue=False, spec_expected=None, spec_name="spec.md"):
        if spec_expected is not None:
            (self.task / spec_name).write_text("# Fixture\nProduct contains accepted bytes.\n", encoding="utf-8")
            (self.task / "spec.expected.json").write_text(json.dumps(spec_expected), encoding="utf-8")
            self.g("add", spec_name, "spec.expected.json", work=self.task)
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
        if pipeline:
            a = {"kind": "pipeline", "task": "fixture", "source_sha": self.sha, "run_id": "fixture-run"}
            archive = evidence / "runs" / a["run_id"]
            archive.mkdir(parents=True)
            self.archive = archive
            report = "<!-- devlyn:final-report run_id=fixture-run -->\nFixture completed.\n"
            (archive / "final-report.md").write_text(report, encoding="utf-8")
            phases = {n: {"started_at": "2026-09-10T00:00:00Z", "completed_at": "2026-09-10T00:00:01Z", "verdict": "PASS"}
                      for n in ("plan", "implement", "build_gate", "cleanup", "verify", "final_report")}
            phases["cleanup"]["post_sha"] = self.sha
            phases["final_report"].update(output_sha256=hashlib.sha256(report.encode()).hexdigest(), artifacts={"log_file": ".devlyn/final-report.md"})
            criteria = "# Fixture acceptance\nProduct contains accepted bytes.\n"
            (archive / "criteria.generated.md").write_text(criteria, encoding="utf-8")
            source = {"type": "generated", "criteria_path": ".devlyn/criteria.generated.md", "criteria_sha256": hashlib.sha256(criteria.encode()).hexdigest()}
            self.state = {"run_id": a["run_id"], "mode": "free-form", "source": source, "phases": phases, "process_evidence": None}
            if spec_expected is not None:
                self.state["mode"] = "spec"
                self.state["source"] = {"type": "spec", "spec_path": spec_name, "spec_sha256": hashlib.sha256((self.task / spec_name).read_bytes()).hexdigest()}
            (archive / "pipeline.state.json").write_text(json.dumps(self.state), encoding="utf-8")
            (archive / "finish-gate.summary.json").write_text(json.dumps({"mode": self.state["mode"], "exit": 0, "offenders": 0, "checked": 1}), encoding="utf-8")
            (archive / "verify-merge.summary.json").write_text(json.dumps({"verdict": "PASS"}), encoding="utf-8")
        if queue:
            (self.task / "queue.md").write_text("- [x] fixture\n", encoding="utf-8")
            self.g("add", "queue.md", work=self.task)
            self.g("commit", "-m", "terminal queue", work=self.task)
            a["queue"] = {"commit": self.g("rev-parse", "HEAD", work=self.task), "file": "queue.md"}
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
        self.assertEqual(json.loads(self.data.read_text(encoding="utf-8"))["pushs"], 1)

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

    def test_in_place_retains_ignored_data(self):
        self.allocate(); self.accept()
        (self.task / "ignored").mkdir()
        (self.task / "ignored" / "user.txt").write_text("retain me", encoding="utf-8")
        result, _ = self.complete("--writers-stopped")
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(self.g("branch", "--show-current"), "main")
        self.assertEqual((self.task / "ignored/user.txt").read_text(encoding="utf-8"), "retain me")
        self.assertEqual(self.g("branch", "--list", "task/fixture"), "")
        self.assertEqual(self.g("ls-remote", "origin", "refs/heads/task/fixture"), "")
        again, _ = self.complete("--writers-stopped", acceptance=False)
        self.assertEqual(again["status"], "COMPLETE")

    def test_linked_custody_and_interrupted_removal(self):
        self.allocate(linked=True); self.accept(pipeline=True)
        # Direct evidence unrelated to the pipeline is unknown ignored content.
        (self.task / ".devlyn/checks.txt").unlink()
        self.configure(interrupt_remove=True)
        result, r = self.complete("--writers-stopped", success=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(self.task.exists())
        saved = json.loads(self.receipt.read_text(encoding="utf-8"))
        recovered = self.receipt.parent / "custody" / ".devlyn/runs/fixture-run/final-report.md"
        self.assertEqual(hashlib.sha256(recovered.read_bytes()).hexdigest(), saved["files"][".devlyn/runs/fixture-run/final-report.md"]["sha256"])
        result, _ = self.complete("--writers-stopped", acceptance=False)
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(self.g("show", saved["recovery_ref"]+":product"), "accepted")

    def test_reject_acceptance_and_policy_before_push(self):
        self.allocate(); self.accept(pipeline=True)
        original = json.loads(json.dumps(self.state))
        for case in ("failed", "verify-only", "blocked", "unfinished", "digest", "source"):
            state = json.loads(json.dumps(original))
            if case == "failed": state["phases"]["verify"]["verdict"] = "NEEDS_WORK"
            if case == "verify-only": state["mode"] = "verify-only"
            if case == "blocked": state["phases"]["implement"]["verdict"] = "BLOCKED"
            if case == "unfinished": state["phases"]["verify"]["completed_at"] = None
            if case == "digest": state["phases"]["final_report"]["output_sha256"] = "0"*64
            if case == "source": state["phases"]["cleanup"]["post_sha"] = self.g("rev-parse", "main")
            (self.archive / "pipeline.state.json").write_text(json.dumps(state), encoding="utf-8")
            with self.subTest(case=case):
                _, r = self.complete(success=False)
                self.assertNotEqual(r.returncode, 0)
                self.assertEqual(self.g("ls-remote", "origin", "refs/heads/task/fixture"), "")
        (self.archive / "pipeline.state.json").write_text(json.dumps(original), encoding="utf-8")
        for value in ("typo", "", " auto"):
            self.g("config", "--local", "devlyn.completionMode", value)
            _, r = self.complete("--mode", "pr", success=False)
            self.assertNotEqual(r.returncode, 0)
        result, _ = self.complete("--local-only")
        self.assertEqual(result["status"], "LOCAL_ONLY")
        self.assertEqual(json.loads(self.data.read_text(encoding="utf-8")).get("creates", 0), 0)

    def test_queue_only_and_unverified_descendant(self):
        self.allocate(); self.accept(pipeline=True, queue=True)
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
        for effect in ("push", "create", "merge"):
            self.configure(**{"interrupt_"+effect: True})
            _, r = self.complete("--writers-stopped", success=False)
            self.assertNotEqual(r.returncode, 0)
        result, _ = self.complete("--writers-stopped")
        self.assertEqual(result["status"], "COMPLETE")
        d = json.loads(self.data.read_text(encoding="utf-8"))
        self.assertEqual((d["pushs"], d["creates"], d["merges"]), (1, 1, 1))

    def test_retains_unknown_dirty_locked_and_active_tree(self):
        self.allocate(linked=True); self.accept()
        for case in ("ignored", "dirty", "untracked", "locked", "cwd", "no-yield"):
            path = self.task / ("ignored/unknown" if case == "ignored" else "product" if case == "dirty" else "unknown")
            if case in {"ignored", "dirty", "untracked"}:
                path.parent.mkdir(exist_ok=True); path.write_text("do not delete", encoding="utf-8")
            if case == "locked": self.g("worktree", "lock", str(self.task))
            with self.subTest(case=case):
                _, r = self.complete(*([] if case == "no-yield" else ["--writers-stopped"]), cwd=self.task if case == "cwd" else None, success=False)
                self.assertNotEqual(r.returncode, 0)
                self.assertTrue(self.task.exists())
                self.assertNotEqual(self.g("branch", "--list", "task/fixture"), "")
            if case in {"ignored", "untracked"}: path.unlink()
            if case == "dirty": path.write_text("accepted\n", encoding="utf-8")
            if case == "locked": self.g("worktree", "unlock", str(self.task))

    def test_no_adoption_and_remote_head_race(self):
        _, r = self.cli("allocate", "--repo", self.work, "--task", "foreign", "--branch", "main", "--repository", "test/project", "--base", "main", success=False)
        self.assertNotEqual(r.returncode, 0)
        self.allocate(); self.accept()
        self.complete("--mode", "pr")
        self.run_cmd(["git", "--git-dir", str(self.bare), "update-ref", "refs/heads/task/fixture", self.g("rev-parse", "main")])
        _, r = self.complete(success=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(json.loads(self.data.read_text(encoding="utf-8")).get("merges",0), 0)

    def test_concurrent_completions(self):
        self.allocate(); self.accept(); self.configure(pending=True)
        args = [sys.executable, str(Path(__file__).resolve()), "complete", "--receipt", str(self.receipt), "--acceptance", str(self.acceptance)]
        procs = [subprocess.Popen(args, cwd=self.root, env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8") for _ in range(2)]
        for proc in procs:
            out, err = proc.communicate(timeout=30)
            self.assertEqual(proc.returncode, 0, out+err)
        d = json.loads(self.data.read_text(encoding="utf-8"))
        self.assertEqual((d["pushs"], d["creates"], d["merges"]), (1,1,1))

    def test_custody_failure_and_evidence_tamper(self):
        self.allocate(linked=True); self.accept()
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
        self.allocate(linked=True); self.accept()
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"], cwd=self.task)
        try:
            _, r = self.complete("--writers-stopped", success=False)
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
        _, r = self.complete("--writers-stopped", success=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.g("ls-remote", "origin", "refs/heads/task/fixture").split()[0], race)
        self.assertNotEqual(self.g("branch", "--list", "task/fixture"), "")

    def test_policy_and_local_only_persist(self):
        self.allocate(); self.accept()
        self.configure(merge_allowed=False)
        _, r = self.complete(success=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(json.loads(self.data.read_text(encoding="utf-8")).get("pushs",0), 0)
        self.complete("--mode", "pr")
        result, _ = self.complete()
        self.assertEqual(result["status"], "PR")
        self.configure(merge_allowed=True, auto_allowed=False, pending=True)
        _, r = self.complete("--mode", "auto", success=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("disallows auto merge", json.loads(r.stdout)["reason"])
        result, _ = self.complete("--no-push")
        self.assertEqual(result["status"], "LOCAL_ONLY")
        result, _ = self.complete(acceptance=False)
        self.assertEqual(result["status"], "LOCAL_ONLY")

    def test_queue_commit_cannot_hide_product_changes(self):
        self.allocate(); self.accept(pipeline=True, queue=True)
        (self.task / "product").write_text("unverified extra\n", encoding="utf-8")
        self.g("add", "product", work=self.task)
        self.g("commit", "--amend", "--no-edit", work=self.task)
        a = json.loads(self.acceptance.read_text(encoding="utf-8"))
        a["queue"]["commit"] = self.g("rev-parse", "HEAD", work=self.task)
        self.acceptance.write_text(json.dumps(a), encoding="utf-8")
        _, r = self.complete(success=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(json.loads(self.data.read_text(encoding="utf-8")).get("pushs",0), 0)

    def test_pipeline_sealed_process_evidence(self):
        self.allocate(); self.accept(pipeline=True)
        evidence_module = shared("process-evidence")
        obligation = {"id": "actual-check", "phase": "verify", "argv": [sys.executable, "-c", "print('fixture passed')"], "exit_code": 0, "stdout_contains": ["fixture passed"], "timeout_sec": 10}
        relative = ".devlyn/process-evidence/fixture-run/verify/round-0/manifest.json"
        evidence_module["capture_process"](self.task, self.task / relative, "fixture-run", "verify", 0, obligation)
        carrier = evidence_module["validate_manifest"](self.task, relative, "fixture-run", "verify", 0, [obligation])
        results = {"commands": evidence_module["bound_carrier_summary_commands"](self.task, carrier), "process_evidence": carrier}
        self.state["phases"]["verify"]["round"] = 0
        self.state["process_evidence"] = [carrier]
        (self.archive / "pipeline.state.json").write_text(json.dumps(self.state), encoding="utf-8")
        (self.archive / "spec-verify.results.json").write_text(json.dumps(results), encoding="utf-8")
        shutil.move(str(self.task / ".devlyn/process-evidence"), str(self.archive / "process-evidence"))
        stdout = self.archive / carrier["streams"][0]["stdout"]["path"].removeprefix(".devlyn/")
        before = stdout.read_bytes()
        stdout.write_text("tampered", encoding="utf-8")
        _, r = self.complete(success=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(json.loads(self.data.read_text(encoding="utf-8")).get("pushs",0), 0)
        stdout.write_bytes(before)
        result, _ = self.complete("--mode", "pr")
        self.assertEqual(result["status"], "PR")

    def test_in_place_resume_does_not_overwrite_ignored_collision(self):
        self.allocate(); self.accept()
        user_file = self.task / "ignored/user.txt"
        user_file.parent.mkdir()
        user_file.write_text("retained user data", encoding="utf-8")
        self.configure(interrupt_delete=True)
        _, r = self.complete("--writers-stopped", success=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.g("branch", "--show-current"), "main")
        other = self.root / "advance"
        self.run_cmd(["git", "clone", str(self.bare), str(other)])
        (other / "ignored").mkdir()
        (other / "ignored/user.txt").write_text("new upstream tracked file", encoding="utf-8")
        self.g("add", "-f", "ignored/user.txt", work=other)
        self.g("commit", "-m", "upstream collision", work=other)
        self.g("push", "origin", "main", work=other)
        _, r = self.complete("--writers-stopped", acceptance=False, success=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(user_file.read_text(encoding="utf-8"), "retained user data")
        self.assertNotEqual(self.g("branch", "--list", "task/fixture"), "")

    def test_replaced_tree_and_unsafe_custody(self):
        self.allocate(linked=True); self.accept()
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

    def test_spec_source_and_report_binding(self):
        self.allocate(); self.accept(pipeline=True, spec_expected={"verification_commands": []})
        report = self.archive / "final-report.md"
        original = report.read_bytes()
        report.write_text("<!-- devlyn:final-report run_id=another-run -->\nBody\n", encoding="utf-8")
        self.state["phases"]["final_report"]["output_sha256"] = hashlib.sha256(report.read_bytes()).hexdigest()
        (self.archive / "pipeline.state.json").write_text(json.dumps(self.state), encoding="utf-8")
        _, r = self.complete(success=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(json.loads(self.data.read_text(encoding="utf-8")).get("pushs",0), 0)
        report.write_bytes(original)
        self.state["phases"]["final_report"]["output_sha256"] = hashlib.sha256(original).hexdigest()
        (self.archive / "pipeline.state.json").write_text(json.dumps(self.state), encoding="utf-8")
        result, _ = self.complete("--mode", "pr")
        self.assertEqual(result["status"], "PR")

    def test_missing_required_process_evidence(self):
        expected = {"process_evidence": [{"id": "red-first", "phase": "implement", "argv": [sys.executable, "-c", "print('red')"], "exit_code": 0, "timeout_sec": 10}]}
        self.allocate(); self.accept(pipeline=True, spec_expected=expected)
        _, r = self.complete(success=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("implement process evidence", json.loads(r.stdout)["reason"])
        self.assertEqual(json.loads(self.data.read_text(encoding="utf-8")).get("pushs",0), 0)

    def test_named_spec_custody(self):
        self.allocate(); self.accept(pipeline=True, spec_expected={"pure_design": True}, spec_name="X.md")
        result, _ = self.complete("--mode", "pr")
        self.assertEqual(result["status"], "PR")
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertIn("spec.expected.json", receipt["files"])
        self.assertEqual((self.receipt.parent / "custody/spec.expected.json").read_bytes(), (self.task / "spec.expected.json").read_bytes())

    def test_named_spec_missing_required_process_evidence(self):
        expected = {"process_evidence": [{"id": "red-first", "phase": "implement", "argv": [sys.executable, "-c", "print('red')"], "exit_code": 0, "timeout_sec": 10}]}
        self.allocate(); self.accept(pipeline=True, spec_expected=expected, spec_name="X.md")
        _, r = self.complete(success=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("implement process evidence", json.loads(r.stdout)["reason"])
        self.assertEqual(json.loads(self.data.read_text(encoding="utf-8")).get("pushs",0), 0)


if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).with_name("platform-support.py")))["configure_utf8"]()
    sys.exit(main())
