#!/usr/bin/env python3
"""Bring a commit into the owner's branch using only a protected fast-forward.

Merge policy is honored while preparing a commit with merge-tree/commit-tree, before
landing. Clearing mergeOptions and selecting ort at landing prevents configuration
from turning that fast-forward into a destructive merge; it does not bypass policy.
pre-merge-commit is not run: its contract requires the merged index and worktree,
which would require writing the owner's checkout before the commit. Message hooks
see the pre-merge checkout, with no MERGE_HEAD. post-merge runs natively at landing.
Hooks are trusted programs and can themselves change the checkout. Concurrency
protection detects HEAD/branch drift before landing; it is not a transaction.

  bring-in.py --repo <checkout> --branch <branch> --target <rev> [--ff-only]
  bring-in.py --self-test
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import os
from pathlib import Path
import re
import runpy
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


class Refused(Exception):
    """An explicit refusal, leaving the caller to fix the reported cause."""


def diagnostic(data):
    if data:
        sys.stderr.write(data.decode("utf-8", errors="replace"))


class Git:
    def __init__(self, repo):
        self.repo = Path(repo).resolve()

    def run(self, *args, data=None, check=True, env=None):
        result = subprocess.run(["git", "-C", str(self.repo), *map(str, args)],
                                input=data, capture_output=True, env=env)
        diagnostic(result.stderr)
        if check and result.returncode:
            command = next(str(arg) for i, arg in enumerate(args)
                           if arg != "-c" and not str(arg).startswith("--config-env=")
                           and (i == 0 or args[i - 1] != "-c"))
            raise Refused(f"git {command} failed (exit {result.returncode}).")
        return result

    def text(self, *args):
        return self.run(*args).stdout.decode("utf-8", errors="surrogateescape").removesuffix("\n")

    def config(self, key, kind=None):
        result = self.run("config", *(["--type=" + kind] if kind else []), "--get", key, check=False)
        if result.returncode == 1:
            return None
        if result.returncode:
            raise Refused(f"Cannot read {key}; unset it or run the merge yourself.")
        return result.stdout.decode("utf-8", errors="surrogateescape").removesuffix("\n")

    def path(self, name):
        return self.repo / self.text("rev-parse", "--git-path", name)

    def ancestor(self, old, new):
        result = self.run("merge-base", "--is-ancestor", old, new, check=False)
        if result.returncode not in (0, 1):
            raise Refused("Cannot determine commit ancestry.")
        return result.returncode == 0

    def snapshot(self, branch):
        head_ref = self.run("symbolic-ref", "-q", "HEAD", check=False).stdout
        head = self.run("rev-parse", "--verify", "HEAD").stdout
        tip = self.run("rev-parse", "--verify", "refs/heads/" + branch).stdout
        # Staged entries, not raw index bytes: Git may refresh cached stat data without changing them.
        return head_ref, head, tip, self.run("ls-files", "--stage", "-z").stdout


def merge_tokens(value):
    """Git alias.c split_cmdline quoting (backslash escapes even inside double quotes).

    shlex's POSIX mode retains some double-quoted backslashes that Git removes.
    Git also retains empty arguments at the boundaries of whitespace.
    """
    tokens, word, quote, i = [], "", "", 0
    while i < len(value):
        char = value[i]
        if not quote and char in " \t\n\r\v\f":
            tokens.append(word)
            word = ""
            while i + 1 < len(value) and value[i + 1] in " \t\n\r\v\f":
                i += 1
        elif not quote and char in "\"'":
            quote = char
        elif quote and char == quote:
            quote = ""
        else:
            if char == "\\" and quote != "'":
                i += 1
                if i == len(value):
                    raise Refused("trailing backslash")
                char = value[i]
            word += char
        i += 1
    if quote:
        raise Refused("unclosed quote")
    return tokens + [word] if value else []


@dataclass
class Policy:
    ff: str = "true"
    verify: bool = False
    sign: str | None = None
    log: list[str] = field(default_factory=list)
    options: list[str] = field(default_factory=list)
    option_source: str = "branch.<name>.mergeOptions"
    strategies: list[tuple[str, str]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def read_policy(git, branch, ff_only):
    policy = Policy(option_source=f"branch.{branch}.mergeOptions")
    ff = git.config("merge.ff")
    policy.ff = "only" if ff == "only" else (git.config("merge.ff", "bool") or "true")
    policy.verify = git.config("merge.verifySignatures", "bool") == "true"
    policy.sign = "" if git.config("commit.gpgSign", "bool") == "true" else None
    setting = policy.option_source
    try:
        tokens = merge_tokens(git.config(setting) or "")
    except Refused as exc:
        raise Refused(f"{setting}: {exc}; unset it or run the merge yourself.") from exc
    strategies = []
    irrelevant = {"--no-edit", "--commit", "-q", "--quiet", "-v", "--verbose", "--stat", "-n", "--no-stat",
                  "--summary", "--no-summary", "--progress", "--no-progress", "--autostash", "--no-autostash",
                  "--rerere-autoupdate", "--no-rerere-autoupdate"}
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token in ("--ff", "--no-ff", "--ff-only"):
            policy.ff = {"--ff": "true", "--no-ff": "false", "--ff-only": "only"}[token]
        elif token in ("--verify-signatures", "--no-verify-signatures"):
            policy.verify = token == "--verify-signatures"
        elif token == "--no-gpg-sign":
            policy.sign = None
        elif token.startswith("-S") or token == "--gpg-sign" or token.startswith("--gpg-sign="):
            policy.sign = token[2:] if token.startswith("-S") else token.partition("=")[2]
        elif token in ("--log", "--no-log") or re.fullmatch(r"--log=\d+", token):
            policy.log = [token]
        elif token in ("-s", "--strategy", "-X", "--strategy-option") or token.startswith(("-s", "-X", "--strategy=", "--strategy-option=")):
            strategy = token.startswith(("-s", "--strategy=")) or token == "--strategy"
            if token in ("-s", "--strategy", "-X", "--strategy-option"):
                i += 1
                if i == len(tokens):
                    policy.errors.append(f"{setting}: missing value for {token!r}")
                    break
                value = tokens[i]
            else:
                value = token.partition("=")[2] if token.startswith("--") else token[2:]
            if strategy:
                strategies.append((setting, value))
            else:
                policy.options += ["-X", value]
        elif token not in irrelevant:
            policy.errors.append(f"{setting}: unsupported token {token!r}")
        i += 1
    # Explicit strategies replace pull.twohead, just as in git merge.
    twohead = git.config("pull.twohead")
    if not strategies and twohead is not None:
        strategies = [("pull.twohead", item) for item in twohead.split(" ")]
    policy.strategies = strategies
    if ff_only:
        policy.ff = "only"
    return policy


def verify_target(git, target):
    # merge defaults to marginal trust; verify-commit otherwise defaults to undefined.
    options = ["-c", "gpg.minTrustLevel=marginal"] if git.config("gpg.minTrustLevel") is None else []
    if git.run(*options, "verify-commit", target, check=False).returncode:
        raise Refused(f"Target {target} does not have a good signature with the required trust.")


def merge_name(git, target, commit):
    # Git builtin/merge.c merge_name uses the spelling supplied by the caller.
    ref = git.text("rev-parse", "--symbolic-full-name", "--verify", "--end-of-options", target)
    for prefix, kind in (("refs/heads/", "branch"), ("refs/remotes/", "remote-tracking branch"), ("refs/tags/", "tag")):
        if ref.startswith(prefix):
            return f"{commit}\t\t{kind} '{target}' of .\n".encode("utf-8", errors="surrogateescape")
    if re.fullmatch(r"[0-9a-fA-F]{4,64}", target):
        return f"{commit}\t\tcommit '{target}'\n".encode("ascii")
    raise Refused(f"Cannot reproduce Git's merge message for target {target!r}; use a branch or commit ID, or run the merge yourself.")


def parse_git_version(version):
    match = re.match(r"git version (\d+)\.(\d+)(?:\.\d+)?\b", version)
    if not match:
        raise Refused(f"Cannot determine Git version from {version!r}; update Git or merge it yourself.")
    return tuple(map(int, match.groups()))


def check_git_version(version):
    if parse_git_version(version) < (2, 31):
        raise Refused(f"Bringing in a branch needs Git 2.31 or newer (found {version}). Update Git, or merge it yourself.")


def check_preparation(policy, version):
    if policy.errors:
        raise Refused("; ".join(policy.errors) + "; unset the setting or run the merge yourself.")
    number = parse_git_version(version)
    if number < (2, 38):
        raise Refused(f"Preparing a merge commit needs Git 2.38 or newer (found {version}). Update Git, or merge it yourself.")
    if policy.options and number < (2, 43):
        raise Refused(f"{policy.option_source}: -X needs Git 2.43 or newer (found {version}); update Git, or unset the setting.")
    for source, strategy in policy.strategies:
        if strategy not in ("ort", "recursive") or (strategy == "recursive" and number < (2, 50)):
            raise Refused(f"{source}: unsupported strategy {strategy!r} with {version}; unset the setting or run the merge yourself.")


def prepare(git, args, policy, head, target):
    check_preparation(policy, git.text("--version"))
    cleanup = git.config("commit.cleanup")
    if cleanup not in (None, "default", "whitespace", "scissors", "strip", "verbatim"):
        raise Refused(f"Unsupported commit.cleanup {cleanup!r}; unset it or run the merge yourself.")
    name = merge_name(git, args.target, target)
    if policy.verify:
        verify_target(git, target)
    merged = git.run("merge-tree", "--write-tree", "--name-only", "--no-messages", *policy.options, head, target, check=False)
    if merged.returncode == 1:
        paths = merged.stdout.decode("utf-8", errors="replace").splitlines()[1:]
        directory = git.repo.parent / (git.repo.name + "-bring-in-resolution")
        rerun = ["python3", str(Path(__file__).resolve()), "--repo", str(git.repo), "--branch", args.branch, "--target", "<resolved-commit>"]
        if args.ff_only:
            rerun.append("--ff-only")
        raise Refused("Merge conflicts: " + ", ".join(paths) + "\nResolve outside this checkout (choose an absent directory):\n" +
                      shlex.join(["git", "-C", str(git.repo), "worktree", "add", "--detach", str(directory), head]) + "\n" +
                      shlex.join(["cd", str(directory)]) + "\n" + shlex.join(["git", "merge", args.target]) +
                      "\n# Resolve the conflicts, then:\ngit add -- <resolved-paths>\ngit commit\ngit rev-parse HEAD\n# Use that commit ID below:\n" + shlex.join(rerun))
    if merged.returncode:
        raise Refused(f"git merge-tree failed (exit {merged.returncode}).")
    tree = merged.stdout.splitlines()[0].decode("ascii")
    message = git.run("fmt-merge-msg", "--into-name", args.branch, *policy.log, data=name).stdout
    # fmt-merge-msg always credits people; native merge --no-edit does not. Credits
    # occur before the sole shortlog heading. Descriptions (which may contain comment
    # lines of their own) occur after it and must remain byte-for-byte intact.
    title, heading, log = message.partition(b"\n* ")
    if heading:
        comment = git.config("core.commentString") or git.config("core.commentChar") or "#"
        prefix = ("#" if comment == "auto" else comment).encode("utf-8", errors="surrogateescape")
        title = b"\n".join(line for line in title.split(b"\n")
                            if not line.startswith((prefix + b" By ", prefix + b" Via ")))
        message = title + heading + log
    temp_root = Path(tempfile.gettempdir()).resolve()
    top = Path(git.text("rev-parse", "--show-toplevel")).resolve()
    if temp_root == top or top in temp_root.parents:
        raise Refused("TMPDIR is inside the checkout; set it to a directory outside the checkout and run again.")
    with tempfile.TemporaryDirectory(prefix="devlyn-bring-in-", dir=temp_root) as directory:
        path = Path(directory) / "message"
        path.write_bytes(message[:-1] if message.endswith(b"\n") else message)
        env = dict(os.environ, GIT_EDITOR=":")
        git.run("hook", "run", "--ignore-missing", "prepare-commit-msg", "--", path, "merge", env=env)
        git.run("hook", "run", "--ignore-missing", "commit-msg", "--", path, env=env)
        # Native no-editor merge cleans once, after both message hooks.
        if cleanup != "verbatim":
            path.write_bytes(git.run("stripspace", *(["--strip-comments"] if cleanup == "strip" else []),
                                     data=path.read_bytes()).stdout)
        if not path.read_bytes():
            raise Refused("Empty merge message; fix the message hook and run again.")
        return git.text("commit-tree", tree, "-p", head, "-p", target, "-F", str(path),
                        *(["-S" + policy.sign] if policy.sign is not None else []))


def bring_in(args):
    git = Git(args.repo)
    before = None
    try:
        check_git_version(git.text("--version"))
        if git.text("rev-parse", "--is-inside-work-tree") != "true":
            raise Refused(f"{git.repo} is not a work tree.")
        git.repo = Path(git.text("rev-parse", "--show-toplevel")).resolve()
        expected = "refs/heads/" + args.branch
        if git.run("symbolic-ref", "-q", "HEAD", check=False).stdout.rstrip(b"\n") != os.fsencode(expected):
            raise Refused(f"Expected checked-out branch {args.branch}; HEAD is detached or on another branch. Never switch to force bring-in.")
        for name in ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge", "rebase-apply"):
            if git.path(name).exists():
                raise Refused(f"{name} exists; finish or abort the in-progress operation before bring-in.")
        head = git.text("rev-parse", "--verify", "HEAD")
        target = git.text("rev-parse", "--verify", "--end-of-options", args.target + "^{commit}")
        before = git.snapshot(args.branch)
        if target == head or git.ancestor(target, head):
            print(f"{args.branch} is already up to date at {head}.")
            return 0
        policy = read_policy(git, args.branch, args.ff_only)
        if policy.ff != "only" and git.text("cat-file", "-t", args.target) == "tag":
            raise Refused(f"Annotated-tag target {args.target!r} needs a mergetag; run the merge yourself.")
        fast_forward = git.ancestor(head, target)
        if policy.ff == "only" and not fast_forward:
            raise Refused(f"{args.branch} has commits of its own; retain and report the delivered result, or run the merge yourself.")
        prepared = not fast_forward or policy.ff == "false"
        commit = prepare(git, args, policy, head, target) if prepared else target
        if (git.run("symbolic-ref", "-q", "HEAD", check=False).stdout.rstrip(b"\n") != os.fsencode(expected)
                or git.text("rev-parse", "HEAD") != head):
            raise Refused(f"{args.branch} moved while preparing; run again.")
        verify = "--verify-signatures" if policy.verify and not prepared else "--no-verify-signatures"
        git.run(f"--config-env=branch.{args.branch}.mergeOptions=DEVLYN_BRING_IN_EMPTY",
                "merge", "--ff-only", "--no-overwrite-ignore", "--no-autostash", "-s", "ort", verify, commit,
                env=dict(os.environ, DEVLYN_BRING_IN_EMPTY=""))
        if (git.text("symbolic-ref", "-q", "HEAD") != expected or git.text("rev-parse", "HEAD") != commit
                or git.text("rev-parse", "--verify", expected) != commit):
            raise Refused("Landing returned success but the branch or HEAD differs from the prepared commit; inspect the checkout before retrying.")
        print(f"{args.branch} {'merged' if prepared else 'fast-forwarded'} to {commit}.")
        return 0
    except (Refused, OSError) as exc:
        print(str(exc), file=sys.stderr)
        if before is not None:
            try:
                unchanged = (git.snapshot(args.branch) == before and before[:3] ==
                             (os.fsencode(expected) + b"\n", head.encode("ascii") + b"\n", head.encode("ascii") + b"\n"))
            except (Refused, OSError) as check_error:
                print(f"Cannot verify unchanged state: {check_error}", file=sys.stderr)
                unchanged = False
            if unchanged:
                print(f"Not brought in: {args.branch} is still at {head} and its staged entries are unchanged. Fix what Git reported above "
                      "(move files that are in the way aside), then run the same command again.", file=sys.stderr)
            else:
                print("HEAD, branch or index changed; inspect the checkout before retrying.", file=sys.stderr)
        return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path)
    parser.add_argument("--branch")
    parser.add_argument("--target")
    parser.add_argument("--ff-only", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(BringInTests)
        return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1
    if not all((args.repo, args.branch, args.target)):
        parser.error("--repo, --branch and --target are required")
    return bring_in(args)


class BringInTests(unittest.TestCase):
    """Prediction: preparation never writes the anchor; protected landing refuses all collisions.

    Before: true merges ignored --no-overwrite-ignore, and configuration could turn
    even --ff-only into a merge that overwrote files or discarded delivered content.
    """
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bring in ✓ 한글 ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root / "owner checkout"
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith("GIT_")}
        self.env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=str(self.root / "no-global"),
                        GIT_AUTHOR_NAME="Fixture", GIT_AUTHOR_EMAIL="fixture@example.invalid",
                        GIT_COMMITTER_NAME="Fixture", GIT_COMMITTER_EMAIL="fixture@example.invalid",
                        LC_ALL="C", GIT_EDITOR=":", GIT_MERGE_AUTOEDIT="no")
        self.g("init", "-q", "--initial-branch=main", str(self.repo), repo=self.root)
        self.commit("base", "base\n")
        self.base = self.g("rev-parse", "HEAD").strip()
        self.g("checkout", "-qb", "topic")
        self.commit("delivered", "delivered\n")
        self.target = self.g("rev-parse", "HEAD").strip()
        self.g("checkout", "-q", "main")

    def g(self, *args, repo=None):
        result = subprocess.run(["git", "-C", str(repo or self.repo), *map(str, args)], env=self.env, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))
        return result.stdout

    def commit(self, name, content):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode("utf-8"))
        self.g("add", "--", name)
        self.g("commit", "-qm", "add " + name)

    def diverge(self):
        self.commit("owner", "owner\n")
        return self.g("rev-parse", "HEAD").strip()

    def state(self):
        return (self.g("rev-parse", "HEAD"), self.g("symbolic-ref", "HEAD"),
                self.g("rev-parse", "main"), self.g("ls-files", "--stage", "-z"))

    def cli(self, *extra, target="topic", branch="main", code=0):
        result = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--repo", str(self.repo),
                                 "--branch", branch, "--target", target, *extra], env=self.env, capture_output=True)
        self.assertEqual(result.returncode, code, (result.stdout + result.stderr).decode("utf-8", errors="replace"))
        if code == 0:
            self.assertEqual(len(result.stdout.splitlines()), 1)
        return result

    def refused(self, *extra, target="topic", phrase=b"Not brought in"):
        before = self.state()
        result = self.cli(*extra, target=target, code=1)
        self.assertEqual(self.state(), before)
        self.assertIn(phrase, result.stderr)
        self.assertFalse((self.repo / ".git/MERGE_HEAD").exists())
        return result

    def hook(self, name, body):
        path = self.repo / ".git/hooks" / name
        path.write_bytes(("#!/bin/sh\n" + body).encode("utf-8"))
        path.chmod(0o755)

    def test_fast_forward_and_paths_with_spaces(self):
        self.cli()
        self.assertEqual(self.g("rev-parse", "HEAD").strip(), self.target)
        self.assertEqual((self.repo / "delivered").read_bytes(), b"delivered\n")

    def test_equals_branch_fast_forwards_despite_ours(self):
        # Prediction: '=' in a branch name cannot keep -s ours active at landing.
        self.g("branch", "-m", "feature=x")
        self.g("config", "branch.feature=x.mergeOptions", "-s ours")
        self.cli(branch="feature=x")
        self.assertEqual(self.g("rev-parse", "HEAD").strip(), self.target)
        self.assertEqual((self.repo / "delivered").read_bytes(), b"delivered\n")
        self.assertEqual(self.g("show", "-s", "--format=%P", "HEAD").strip(), self.base)

    def test_refusal_reports_only_verified_state_after_hook_changes_file(self):
        # Prediction: unchanged refs/index do not imply unchanged working files.
        self.diverge()
        self.hook("commit-msg", 'printf "hook bytes\\n" > base\nexit 1\n')
        result = self.refused(phrase=b"Not brought in: main is still at ")
        self.assertIn(b"and its staged entries are unchanged. Fix what Git reported above", result.stderr)
        self.assertEqual((self.repo / "base").read_bytes(), b"hook bytes\n")

    def test_fast_forward_collisions(self):
        for content in (b"owner bytes\n", b"delivered\n"):
            with self.subTest(content=content):
                (self.repo / ".git/info/exclude").write_bytes(b"delivered\n")
                (self.repo / "delivered").write_bytes(content)
                result = self.refused()
                self.assertIn(b"git merge failed", result.stderr)
                self.assertEqual((self.repo / "delivered").read_bytes(), content)

    def test_diverged_collisions(self):
        self.diverge()
        for content in (b"owner bytes\n", b"delivered\n"):
            with self.subTest(content=content):
                (self.repo / ".git/info/exclude").write_bytes(b"delivered\n")
                (self.repo / "delivered").write_bytes(content)
                self.refused()
                self.assertEqual((self.repo / "delivered").read_bytes(), content)

    def test_directory_to_file_collision(self):
        self.commit("d/tracked", "original tracked child\n")
        self.g("branch", "-f", "topic", "HEAD")
        self.g("checkout", "-q", "topic")
        self.g("rm", "d/tracked")
        self.commit("d", "delivered file\n")
        self.g("checkout", "-q", "main")
        self.diverge()
        (self.repo / ".git/info/exclude").write_bytes(b"d/secret\n")
        (self.repo / "d/secret").write_bytes(b"owner secret\x00")
        self.refused()
        self.assertEqual((self.repo / "d/secret").read_bytes(), b"owner secret\x00")
        self.assertEqual((self.repo / "d/tracked").read_bytes(), b"original tracked child\n")

    def native_message(self, target, *options):
        with tempfile.TemporaryDirectory(prefix="native copy ", dir=self.root) as directory:
            clone = Path(directory) / "repo"
            shutil.copytree(self.repo, clone)
            self.g("merge", "--no-edit", *options, target, repo=clone)
            return self.g("cat-file", "commit", "HEAD", repo=clone).split(b"\n\n", 1)[1]

    def message(self):
        return self.g("cat-file", "commit", "HEAD").split(b"\n\n", 1)[1]

    def test_merge_message_and_parents_equal_native(self):
        head = self.diverge()
        self.g("update-ref", "refs/remotes/origin/topic", self.target.decode())
        self.g("tag", "lightweight", "topic")
        for target in ("topic", "refs/heads/topic", "origin/topic", "lightweight", self.target.decode()):
            for log in ("false", "true"):
                with self.subTest(target=target, log=log):
                    self.g("config", "merge.log", log)
                    expected = self.native_message(target)
                    self.cli(target=target)
                    self.assertEqual(self.g("show", "-s", "--format=%P", "HEAD").strip(), head + b" " + self.target)
                    self.assertEqual(self.message(), expected)
                    self.g("reset", "--hard", head.decode())

    def test_merge_log_with_another_author_and_log_options(self):
        # Prediction: fmt-merge-msg and native no-edit merge agree even when the author differs.
        # Before: equal-author fixtures alone cannot expose automatic author credit or log-option differences.
        self.g("checkout", "-q", "topic")
        self.g("commit", "--amend", "--author=Contributor <contributor@example.invalid>", "-m", "contributed work")
        self.g("checkout", "-q", "main")
        head = self.diverge()
        self.g("config", "merge.log", "true")
        self.g("config", "merge.branchdesc", "true")
        self.g("config", "branch.topic.description", "# By a description, not a credit\nkeep this\n")
        self.g("config", "core.commentChar", ";")
        for options in ("--no-edit", "--no-log", "--log=1", "--no-log --log"):
            with self.subTest(options=options):
                self.g("config", "branch.main.mergeOptions", options)
                expected = self.native_message("topic")
                self.cli()
                self.assertEqual(self.message(), expected)
                self.g("reset", "--hard", head.decode())

    def test_conflict(self):
        self.g("checkout", "-q", "topic")
        self.commit("base", "topic change\n")
        self.g("checkout", "-q", "main")
        self.commit("base", "owner change\n")
        nested = self.repo / "nested"
        nested.mkdir()
        result = self.refused("--repo", str(nested), phrase=b"Merge conflicts: base")
        self.assertIn(os.fsencode(self.repo.parent / (self.repo.name + "-bring-in-resolution")), result.stderr)
        self.assertIn(b"worktree add --detach", result.stderr)
        self.assertIn(b"--target '<resolved-commit>'", result.stderr)

    def test_up_to_date(self):
        before = self.state()
        self.assertIn(b"already up to date", self.cli(target="main").stdout)
        self.assertEqual(self.state(), before)
        self.diverge()
        before = self.state()
        self.assertIn(b"already up to date", self.cli(target=self.base.decode()).stdout)
        self.assertEqual(self.state(), before)

    def test_detached_and_other_branch(self):
        self.cli(branch="other", code=1)
        self.assertEqual(self.g("symbolic-ref", "HEAD"), b"refs/heads/main\n")
        self.g("checkout", "-q", "--detach")
        self.assertIn(b"detached", self.cli(code=1).stderr)
        self.assertEqual(self.g("rev-parse", "HEAD").strip(), self.base)

    def test_in_progress_operations(self):
        for name in ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge", "rebase-apply"):
            with self.subTest(name=name):
                path = self.repo / ".git" / name
                if name.startswith("rebase-"):
                    path.mkdir()
                else:
                    path.write_bytes(self.target + b"\n")
                before = self.state()
                self.assertIn(name.encode(), self.cli(code=1).stderr)
                self.assertEqual(self.state(), before)
                path.rmdir() if path.is_dir() else path.unlink()

    def test_unsupported_options_and_strategy(self):
        self.diverge()
        for value in ("-s ours", "--squash", "--overwrite-ignore", "--no-commit", "--edit", "--signoff", "--cleanup=verbatim", "-s subtree"):
            with self.subTest(value=value):
                self.g("config", "branch.main.mergeOptions", value)
                self.refused(phrase=b"branch.main.mergeOptions")

    def test_strategy_option_and_quoting(self):
        # Prediction: -X is honored from 2.43 onward and explicitly refused on older Git.
        self.g("checkout", "-q", "topic")
        self.commit("base", "base  \n")
        self.g("checkout", "-q", "main")
        self.commit("base", "owner change\n")
        self.g("config", "branch.main.mergeOptions", '-s ort -X "ignore-space-change"')
        self.assertEqual(merge_tokens(r'''-X "a\b" 'c\d' a\ b'''), ["-X", "ab", "c\\d", "a b"])
        if parse_git_version(self.g("--version").decode()) < (2, 43):
            self.refused(phrase=b"branch.main.mergeOptions: -X needs Git 2.43 or newer")
            return
        expected = self.native_message("topic")
        self.cli()
        self.assertEqual((self.repo / "base").read_bytes(), b"owner change\n")
        self.assertEqual(self.message(), expected)

    def test_fast_forward_cannot_be_hijacked(self):
        for setting, value in (("pull.twohead", "ours"), ("branch.main.mergeOptions", "-s ours"),
                               ("branch.main.mergeOptions", "-s subtree"), ("branch.main.mergeOptions", "--squash")):
            with self.subTest(setting=setting, value=value):
                self.g("config", setting, value)
                self.cli()
                self.assertEqual(self.g("rev-parse", "HEAD").strip(), self.target)
                self.g("reset", "--hard", self.base.decode())
                (self.repo / ".git/info/exclude").write_bytes(b"delivered\n")
                (self.repo / "delivered").write_bytes(b"owner\n")
                self.refused()
                self.assertEqual((self.repo / "delivered").read_bytes(), b"owner\n")
                (self.repo / "delivered").unlink()
                self.g("config", "--unset", setting)
        self.diverge()
        self.g("config", "pull.twohead", "ours")
        self.refused(phrase=b"pull.twohead")
        self.g("config", "branch.main.mergeOptions", "-s ort")
        self.cli()  # The explicit supported strategy overrides pull.twohead.

    def test_ff_policy(self):
        self.g("config", "merge.ff", "false")
        expected = self.native_message("topic")
        self.cli()
        self.assertEqual(self.g("show", "-s", "--format=%P", "HEAD").strip(), self.base + b" " + self.target)
        self.assertEqual(self.message(), expected)
        self.g("reset", "--hard", self.base.decode())
        self.cli("--ff-only")
        self.assertEqual(self.g("rev-parse", "HEAD").strip(), self.target)
        self.g("reset", "--hard", self.base.decode())
        self.diverge()
        self.g("config", "merge.ff", "only")
        self.refused(phrase=b"main has commits of its own")
        self.g("config", "merge.ff", "true")
        self.refused("--ff-only", phrase=b"main has commits of its own")
        self.g("config", "branch.main.mergeOptions", "--no-ff --ff --ff-only")
        self.refused(phrase=b"main has commits of its own")

    def test_signing_failure(self):
        self.diverge()
        program = self.root / "fail-sign"
        program.write_bytes(b"#!/bin/sh\nexit 1\n")
        program.chmod(0o755)
        self.g("config", "commit.gpgSign", "true")
        self.g("config", "gpg.program", str(program))
        self.refused()
        self.g("config", "branch.main.mergeOptions", "--no-gpg-sign")
        self.cli()

    def test_unsigned_target_verification(self):
        # Prediction: an unsigned divergent target refuses even with signature display enabled.
        self.g("config", "merge.verifySignatures", "true")
        self.refused()
        self.diverge()
        for show in ("false", "true"):
            self.g("config", "log.showSignature", show)
            result = self.refused(phrase=self.target)
            self.assertNotIn(b"Traceback", result.stderr)
        self.g("config", "branch.main.mergeOptions", "--no-verify-signatures")
        self.cli()

    def test_verification_uses_native_verifier_and_trust_default(self):
        # Prediction: Git verifies signatures with marginal default and configured case intact.
        git = Git(self.repo)
        for minimum, options in ((None, ("-c", "gpg.minTrustLevel=marginal")), ("FULLY", ())):
            with self.subTest(minimum=minimum), patch.object(git, "config", return_value=minimum), \
                    patch.object(git, "run", return_value=subprocess.CompletedProcess([], 0, b"", b"")) as run:
                verify_target(git, "target-id")
                run.assert_called_once_with(*options, "verify-commit", "target-id", check=False)
                run.return_value.returncode = 1
                with self.assertRaisesRegex(Refused, "target-id"):
                    verify_target(git, "target-id")

    def test_cleanup_modes_match_native_after_commit_msg(self):
        # Prediction: cleanup happens once after commit-msg, honoring commit.cleanup and commentChar.
        head = self.diverge()
        for mode in ("default", "whitespace", "scissors", "strip", "verbatim"):
            for comment in ("#", ";"):
                with self.subTest(mode=mode, comment=comment):
                    self.g("reset", "--hard", head.decode())
                    self.g("config", "commit.cleanup", mode)
                    self.g("config", "core.commentChar", comment)
                    self.hook("commit-msg", f'printf "\\n{comment} comment  \\n\\n" >> "$1"\n')
                    expected = self.native_message("topic")
                    self.cli()
                    self.assertEqual(self.message(), expected)
                    if mode == "strip":
                        self.assertNotIn(b"comment", self.message())

    def test_commit_msg_sees_prepare_hook_whitespace_and_refuses_like_native(self):
        # Prediction: commit-msg sees trailing whitespace from prepare-commit-msg before cleanup.
        self.diverge()
        self.hook("prepare-commit-msg", 'printf "\\ntrailing  \\n" >> "$1"\n')
        self.hook("commit-msg", 'if grep -q "[[:blank:]]$" "$1"; then exit 1; fi\n')
        with tempfile.TemporaryDirectory(prefix="native hook copy ", dir=self.root) as directory:
            clone = Path(directory) / "repo"
            shutil.copytree(self.repo, clone)
            result = subprocess.run(["git", "-C", str(clone), "merge", "--no-edit", "topic"],
                                    env=self.env, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
        self.refused()

    def test_invalid_cleanup_refuses_before_hooks(self):
        # Prediction: an invalid cleanup mode refuses without invoking any message hook.
        self.diverge()
        self.g("config", "commit.cleanup", "invalid")
        self.hook("prepare-commit-msg", "touch hook-ran\n")
        self.refused(phrase=b"commit.cleanup")
        self.assertFalse((self.repo / "hook-ran").exists())

    def test_hooks_and_native_cleanup(self):
        self.diverge()
        self.hook("commit-msg", "exit 1\n")
        self.refused()
        self.hook("prepare-commit-msg", 'printf "\\n# kept comment  \\n\\n" >> "$1"\n')
        self.hook("commit-msg", 'printf "\\nHook edit  \\n\\n" >> "$1"\n')
        expected = self.native_message("topic")
        self.hook("pre-merge-commit", "exit 1\n")  # Its incompatible contract must not run.
        self.hook("post-merge", 'printf "%s" "$1" > post-merge-ran\n')
        self.cli()
        self.assertEqual(self.message(), expected)
        self.assertIn(b"Hook edit\n", self.message())
        self.assertEqual((self.repo / "post-merge-ran").read_bytes(), b"0")

    def test_hook_drift_is_not_rolled_back(self):
        self.diverge()
        self.hook("prepare-commit-msg", 'if test "$2" = merge; then git -c core.hooksPath=/dev/null commit --allow-empty -qm "hook commit"; fi\n')
        result = self.cli(code=1)
        self.assertIn(b"moved while preparing", result.stderr)
        self.assertIn(b"HEAD, branch or index changed; inspect the checkout before retrying.", result.stderr)
        self.assertEqual(self.g("show", "-s", "--format=%s", "HEAD"), b"hook commit\n")
        self.assertFalse((self.repo / "delivered").exists())

    def test_annotated_tag_and_revision_expression_refused(self):
        self.diverge()
        self.g("tag", "-am", "tag message", "annotated", "topic")
        self.refused(target="annotated", phrase=b"mergetag")
        self.refused(target="topic~0", phrase=b"Cannot reproduce Git's merge message")

    def test_annotated_tag_fast_forward_requires_ff_only(self):
        # Prediction: an annotated tag needs a mergetag unless effective ff mode is only.
        self.g("tag", "-am", "tag message", "annotated", "topic")
        self.refused(target="annotated", phrase=b"mergetag")
        for options in (("--ff-only",), ()):
            with self.subTest(options=options):
                if not options:
                    self.g("config", "merge.ff", "only")
                expected = self.native_message("annotated", *options)
                self.cli(*options, target="annotated")
                self.assertEqual(self.g("rev-parse", "HEAD").strip(), self.target)
                self.assertEqual(self.message(), expected)
                self.assertEqual((self.repo / "delivered").read_bytes(), b"delivered\n")
                self.g("reset", "--hard", self.base.decode())

    def test_recursive_preparation_requires_git_250(self):
        # Prediction: recursive refuses before 2.50, when it became an alias for ort.
        for source in ("branch.main.mergeOptions", "pull.twohead"):
            self.g("config", source, "-s recursive" if source.startswith("branch.") else "recursive")
            policy = read_policy(Git(self.repo), "main", False)
            for version in ("git version 2.43.0", "git version 2.49.9"):
                with self.subTest(source=source, version=version):
                    with self.assertRaises(Refused) as refused:
                        check_preparation(policy, version)
                    self.assertIn(source, str(refused.exception))
                    self.assertIn(version, str(refused.exception))
            check_preparation(policy, "git version 2.50.0")
            self.g("config", "--unset", source)

    def test_preparation_feature_floors(self):
        # Prediction: plain preparation needs 2.38; only configured -X raises that to 2.43.
        for ff in ("true", "false"):
            with self.subTest(ff=ff):
                with self.assertRaisesRegex(Refused, r"Preparing a merge commit needs Git 2.38 or newer \(found git version 2.37.0\)"):
                    check_preparation(Policy(ff=ff), "git version 2.37.0")
        check_preparation(Policy(), "git version 2.38.0")
        check_preparation(Policy(), "git version 2.39.5")
        policy = Policy(options=["-X", "ours"], option_source="branch.main.mergeOptions")
        with self.assertRaisesRegex(Refused, r"branch.main.mergeOptions: -X needs Git 2.43 or newer \(found git version 2.39.5\)"):
            check_preparation(policy, "git version 2.39.5")
        check_preparation(policy, "git version 2.43.0")

    def test_rename_settings_match_native_merge(self):
        # Prediction: on the same Git, both fixtures conflict like native merge or land its tree.
        for fixture in ("file", "directory"):
            self.g("reset", "--hard", self.base.decode())
            self.commit("original/file", "original content\n")
            self.g("branch", "-f", "topic", "HEAD")
            self.g("checkout", "-q", "topic")
            self.g("mv", "original/file" if fixture == "file" else "original", "renamed")
            self.g("commit", "-qm", "rename " + fixture)
            self.g("checkout", "-q", "main")
            self.commit("original/file" if fixture == "file" else "original/new", "owner content\n")
            head = self.g("rev-parse", "HEAD").strip().decode()
            for setting in ("merge.renames", "merge.directoryRenames"):
                with self.subTest(fixture=fixture, setting=setting):
                    self.g("reset", "--hard", head)
                    self.g("config", setting, "false")
                    with tempfile.TemporaryDirectory(prefix="native rename copy ", dir=self.root) as directory:
                        twin = Path(directory) / "repo"
                        shutil.copytree(self.repo, twin)
                        native = subprocess.run(["git", "-C", str(twin), "merge", "--no-edit", "topic"],
                                                env=self.env, capture_output=True)
                        self.assertIn(native.returncode, (0, 1),
                                      (native.stdout + native.stderr).decode("utf-8", errors="replace"))
                        if native.returncode == 1:
                            self.assertTrue(self.g("ls-files", "--unmerged", repo=twin))
                            self.refused(phrase=b"Merge conflicts:")
                        else:
                            self.cli()
                            self.assertEqual(self.g("rev-parse", "HEAD^{tree}"),
                                             self.g("rev-parse", "HEAD^{tree}", repo=twin))
                    self.g("config", "--unset", setting)

    def test_git_version_suffixes_and_early_floor(self):
        # Prediction: vendor suffixes parse; Git 2.30 refuses before any repository work.
        for version, expected in (("git version 2.50.1 (Apple Git-155)", (2, 50)),
                                  ("git version 2.47.1.windows.1", (2, 47)),
                                  ("git version 2.31.0", (2, 31))):
            with self.subTest(version=version):
                self.assertEqual(parse_git_version(version), expected)
                check_git_version(version)
        with self.assertRaisesRegex(Refused, r"needs Git 2.31 or newer \(found git version 2.30.9\)"):
            check_git_version("git version 2.30.9")
        with patch.object(Git, "text", return_value="git version 2.30.9") as text, \
                patch("sys.stderr"):
            self.assertEqual(bring_in(argparse.Namespace(repo=self.repo)), 1)
            text.assert_called_once_with("--version")


if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).with_name("platform-support.py")))["configure_utf8"]()
    sys.exit(main())
