#!/usr/bin/env python3
"""Start a new worktree's build directory warm, from a built checkout (task-completion.md).

Of the common build tools only Cargo keeps a large cache inside each checkout that a new
worktree starts without: pnpm, bun, npm, Go and uv share content-addressed caches machine-wide,
Turborepo shares the main worktree's cache, and the path-keyed caches of Vite, Gradle, Xcode and
Flutter would miss after a copy. For a Cargo workspace whose default target directory is absent
and ignored, this clones the dev-profile layouts of the anchor's (else another registered
worktree's) built target directory into private staging, sharing its blocks (APFS clonefile,
Linux reflink; never a copy), removes what must not carry over, and moves the result into place:

- every unit of the recipient's path packages: Cargo judges their freshness by mtime against the
  other tree's sources;
- every unit of a package the recipient does not use: nothing classified it;
- each build-script run whose kept results point into the donor where Cargo does not rewrite
  them: on reuse Cargo rewrites a script's own OUT_DIR in its directives, not paths elsewhere
  (aws-lc-rs's `cargo:include` into aws-lc-sys) nor inside the text it wrote (tauri's permission
  lists);
- every unit of a package whose sources or generated Rust plainly compile OUT_DIR in (rather
  than through include!/include_str!/include_bytes!): Cargo never recompiles that path
  (fingerprint/dep_info.rs). This is a best-effort reading of the source, not a proof;
- incremental caches.

Cargo rebuilds what it then finds missing, and everything that depends on it. A path that
survives inside compiled output (a proc-macro's install name, debug maps, a native library or
a crate that compiled a path in where the reading above does not see it) still names the
donor's files: when the donor rebuilds or removes them, the recipient can change behavior
without a warning. That is why a workspace opts in, with `[workspace.metadata.devlyn]
warm-build-dirs = true` in its Cargo.toml, once its dependencies do not use such paths.

The donor is only read: its dev build lock is taken from an existing lock file opened read-only,
without waiting, while the layouts are cloned. The whole operation has a time limit. Every skip
is reported with its reason; the target directory then stays absent and the first build is an
ordinary cold one.

  warm-build-dirs.py <worktree> [--from <checkout>]
  warm-build-dirs.py --self-test
"""
from __future__ import annotations

import argparse
import contextlib
import ctypes
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest
import uuid

PROFILE_DIR = "debug"
BUDGET_SECONDS = 300
CARGO_ENTRIES = {".fingerprint", "build", "deps", "examples", ".cargo-lock"}
UNIT = re.compile(r"^(?P<name>.+)-(?P<hash>[0-9a-f]{16})(?:\.[^/]*)?$")
SNIFF_BYTES = 8192  # a NUL among the first bytes marks a binary file
# Conservative on purpose. Every string literal that spells OUT_DIR, escapes included, counts as
# a compiled-in path, and only the plain include!(concat!(env!("OUT_DIR"), ...)) forms, which
# embed contents, offset one each; an env!/option_env! whose argument is not a literal counts too.
_SPACE = r"(?:\s|//[^\n]*|/\*[\s\S]*?\*/)*"
# Every quote may start a literal (a lookahead, so candidates overlap); its escapes are decoded.
STRING_CANDIDATE = re.compile(r'(?="((?:[^"\\]|\\[\s\S])*?)")')
ESCAPE = re.compile(r'\\(?:x([0-9a-fA-F]{2})|u\{([0-9a-fA-F_]+)\}|\n\s*|(.))')
NONLITERAL_ENV = re.compile(rf'(?<![A-Za-z0-9_])(?:option_)?env{_SPACE}!{_SPACE}[(\[{{]{_SPACE}(?!r?#*")')
INCLUDED_OUT_DIR = re.compile(
    r'(?<![A-Za-z0-9_])include(?:_str|_bytes)?\s*!\s*\(\s*concat\s*!\s*\(\s*env\s*!\s*\(\s*"OUT_DIR"\s*\)')
REDIRECTS = ("CARGO_TARGET_DIR", "CARGO_BUILD_TARGET_DIR", "CARGO_BUILD_BUILD_DIR")
RUSTC_ENV = re.compile(r"^cargo::?rustc-env=[^=]+=")
# Runs in a child so the time limit can stop a long clone; argv: source, target.
CLONE_CHILD = """import ctypes, os, sys
if ctypes.CDLL(None, use_errno=True).clonefile(os.fsencode(sys.argv[1]), os.fsencode(sys.argv[2]), 1) != 0:
    sys.exit(os.strerror(ctypes.get_errno()))
"""


class Skip(Exception):
    """An expected reason not to warm; the build starts cold."""


class Unsafe(Exception):
    """A safety check failed; nothing was published and the donor was not written."""


def entry(tool, status, **fields):
    return {"tool": tool, "status": status, **fields}


class Deadline:
    def __init__(self, seconds):
        self.seconds = seconds
        self.end = time.monotonic() + seconds

    def left(self):
        remaining = self.end - time.monotonic()
        if remaining <= 0:
            raise TimeUp(f"warming took longer than {self.seconds} s")
        return remaining


class TimeUp(Skip):
    """The time limit ran out; staging is left in scratch for its cleanup."""


def run(argv, *, cwd, deadline, env=None):
    try:
        result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True,
                                encoding="utf-8", timeout=deadline.left())
    except subprocess.TimeoutExpired as exc:
        raise TimeUp(f"{' '.join(map(str, argv[:3]))} timed out") from exc
    if result.returncode != 0:
        raise Skip(f"{' '.join(map(str, argv[:3]))} failed: {(result.stderr or result.stdout).strip()[-400:]}")
    return result.stdout


def git(work, *args, deadline):
    return run(["git", "-C", str(work), *args], cwd=work, deadline=deadline).removesuffix("\n")


def without_redirects():
    return {key: value for key, value in os.environ.items() if key not in REDIRECTS}


def metadata(work, deadline, *, env=None, deps=False):
    argv = ["cargo", "metadata", "--format-version", "1", "--frozen", *([] if deps else ["--no-deps"])]
    found = json.loads(run(argv, cwd=work, deadline=deadline, env=env))
    if "build_directory" not in found:
        raise Skip("this Cargo does not report its build directory (Cargo 1.91 or later needed)")
    return found


def open_beneath(root, parts):
    """A descriptor for root/parts, reached without following any link below root."""
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in parts:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
    except OSError:
        os.close(fd)
        raise
    return fd


def no_symlink_between(root, path):
    current = root
    for part in path.relative_to(root).parts:
        current = current / part
        if current.is_symlink():
            return False
    return True


def destination(work, deadline, stack):
    """The worktree's own Cargo target directory and a descriptor for its parent, when it can be warmed."""
    found = metadata(work, deadline)
    if ((found.get("metadata") or {}).get("devlyn") or {}).get("warm-build-dirs") is not True:
        raise Skip("not enabled: the workspace's Cargo.toml has no [workspace.metadata.devlyn] warm-build-dirs = true")
    if any(key in os.environ for key in REDIRECTS) and metadata(work, deadline, env=without_redirects()) != found:
        raise Skip("the target directory comes from this environment, which later commands may not share")
    target = Path(found["target_directory"])
    if Path(found["build_directory"]) != target:
        raise Skip("a separate Cargo build-dir is configured")
    if not target.is_absolute() or not target.is_relative_to(work) or target == work:
        raise Skip(f"{target} is not inside the worktree")
    relative = target.relative_to(work)
    if relative.parts[0] in {".git", ".devlyn"} or ".." in relative.parts:
        raise Skip(f"{relative} is reserved")
    try:
        parent = stack.enter_context(contextlib.closing(_Fd(open_beneath(work, relative.parts[:-1]))))
    except OSError as exc:
        raise Skip(f"{relative.parent} cannot be reached without a link: {exc.strerror}") from exc
    if os.path.lexists(target):
        raise Skip(f"{relative} already exists")
    if git(work, "ls-files", "--", str(relative), deadline=deadline):
        raise Skip(f"{relative} holds tracked files")
    try:
        # The trailing slash names a directory, which directory-only rules such as `target/` need.
        git(work, "check-ignore", "-q", "--", f"{relative}/", deadline=deadline)
    except TimeUp:
        raise
    except Skip as exc:
        raise Skip(f"{relative} is not ignored by Git") from exc
    return target, relative, parent


class _Fd:
    def __init__(self, fd):
        self.fd = fd

    def close(self):
        os.close(self.fd)


def donors(work, anchor, relative, deadline):
    """Built targets at the same place in the anchor, then the other worktrees, newest first."""
    others = []
    for line in git(work, "worktree", "list", "--porcelain", deadline=deadline).splitlines():
        if line.startswith("worktree "):
            checkout = Path(line[len("worktree "):]).resolve()
            if checkout not in {work, anchor}:
                others.append(checkout)
    found = []
    for checkout in [anchor, *others]:
        donor = checkout / relative
        layout = donor / PROFILE_DIR
        if not (no_symlink_between(checkout, donor) and (layout / ".fingerprint").is_dir() and not layout.is_symlink()):
            continue
        if donor.is_relative_to(work) or work.is_relative_to(donor):
            continue
        found.append((checkout, donor, (layout / ".fingerprint").stat().st_mtime))
    first = [item for item in found if item[0] == anchor]
    return first + sorted((item for item in found if item[0] != anchor), key=lambda item: -item[2])


@contextlib.contextmanager
def read_lock(donor):
    """The donor's dev build lock, held only if free now, through a read-only descriptor."""
    import fcntl
    path = donor / PROFILE_DIR / ".cargo-lock"
    try:
        # O_NONBLOCK: a FIFO in its place must not stall the open.
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError as exc:
        raise Skip(f"{path} cannot be opened: {exc.strerror}") from exc
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise Skip(f"{path} is not a regular file")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise Skip(f"a build is using {donor}") from exc
        yield fd, path
    finally:
        os.close(fd)


def same_file(fd, path):
    held, current = os.fstat(fd), os.lstat(path)
    return (held.st_dev, held.st_ino) == (current.st_dev, current.st_ino)


def layouts(target):
    """The dev-profile layouts under a target directory, host first, relative."""
    found = [Path(PROFILE_DIR)] if (target / PROFILE_DIR / ".fingerprint").is_dir() else []
    for kind in sorted(p for p in target.iterdir() if p.is_dir() and not p.is_symlink() and p.name != PROFILE_DIR):
        if (kind / PROFILE_DIR / ".fingerprint").is_dir() and not (kind / PROFILE_DIR).is_symlink():
            found.append(Path(kind.name, PROFILE_DIR))
    return found


def clone(source, target, deadline):
    """Share source's blocks at target (never copy them), within the time limit."""
    target.parent.mkdir(parents=True, exist_ok=True)
    argv = ([sys.executable, "-c", CLONE_CHILD, str(source), str(target)] if sys.platform == "darwin"
            else ["cp", "-a", "--reflink=always", "--", str(source), str(target)])
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=deadline.left())
    except subprocess.TimeoutExpired as exc:
        raise TimeUp(f"cloning {source} timed out") from exc
    if result.returncode != 0:
        raise Skip(f"this filesystem cannot clone {source}: {result.stderr.strip()[-200:]}")


def publish(staging_parent, staging_name, target_parent, target_name):
    """Move staging into the checked parent only if nothing exists there."""
    names = os.fsencode(staging_name), os.fsencode(target_name)
    if sys.platform == "darwin":
        rename = ctypes.CDLL(None, use_errno=True).renameatx_np
        rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        failed = rename(staging_parent, names[0], target_parent, names[1], 0x4) != 0  # RENAME_EXCL
    else:
        rename = ctypes.CDLL(None, use_errno=True).renameat2
        rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        failed = rename(staging_parent, names[0], target_parent, names[1], 1) != 0  # RENAME_NOREPLACE
    if failed:
        raise Skip(f"cannot publish {target_name}: {os.strerror(ctypes.get_errno())}")


def check_clone(staging, deadline):
    """No Git data, no special file, and no link that leads out of the clone."""
    for directory, dirs, files in os.walk(staging):
        deadline.left()
        for name in dirs + files:
            path = Path(directory, name)
            mode = path.lstat().st_mode
            if name.casefold() == ".git":
                raise Unsafe(f"{path} is Git data")
            if stat.S_ISLNK(mode):
                if not Path(os.path.realpath(path)).is_relative_to(staging):
                    raise Unsafe(f"{path} links out of the clone")
            elif not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
                raise Unsafe(f"{path} is not a regular file or directory")


def mentions(data, roots):
    """Whether bytes name a path at or below any root (not a sibling such as `<root>.other`)."""
    return any(re.search(re.escape(os.fsencode(root)) + rb"(?![A-Za-z0-9._-])", data) for root in roots)


def is_text(path):
    """Whether a regular file (never a link or special file) holds no NUL in its first bytes."""
    if not stat.S_ISREG(path.lstat().st_mode):
        return False
    with open(path, "rb") as stream:
        return b"\0" not in stream.read(SNIFF_BYTES)


def foreign_runs(staging, layout, roots, deadline):
    """Hashes of build-script runs whose kept results name a donor root Cargo does not rewrite."""
    found = set()
    for run_dir in (staging / layout / "build").iterdir():
        deadline.left()
        root_output = run_dir / "root-output"
        if not root_output.is_file():
            continue  # the compiled build script, not a run of it
        old_out = os.fsdecode(root_output.read_bytes())
        # <old target>/<layout>/build/<unit>/out
        tail = (*layout.parts, "build", run_dir.name, "out")
        if not Path(old_out).is_absolute() or Path(old_out).parts[-len(tail):] != tail:
            raise Unsafe(f"{root_output} does not name this run's OUT_DIR")
        needles = {*roots, str(Path(old_out).parents[len(tail) - 1])}
        output = run_dir / "output"
        lines = output.read_text(errors="replace").splitlines() if output.is_file() else []
        # A variable the script hands to rustc is compiled in as it is, own OUT_DIR included.
        exported = [line.split("=", 2)[2] for line in lines if RUSTC_ENV.match(line)]
        foreign = mentions(os.fsencode("\n".join(exported)), {*needles, old_out}) or mentions(
            os.fsencode("\n".join(lines).replace(old_out, "")), needles)
        for directory, _, files in os.walk(run_dir / "out") if not foreign else ():
            deadline.left()
            for name in files:
                path = Path(directory, name)
                deadline.left()
                if is_text(path):
                    data = path.read_bytes()
                    foreign = mentions(data, needles) or (name.endswith(".rs") and compiles_path(data.decode(errors="replace")))
                if foreign:
                    break
            if foreign:
                break
        if foreign:
            found.add(UNIT.match(run_dir.name)["hash"])
    return found


def decoded(literal):
    def one(match):
        byte, code, other = match.groups()
        if byte or code:
            return chr(int((byte or code).replace("_", ""), 16))
        return "" if other is None else other  # a continuation, or an escaped character
    return ESCAPE.sub(one, literal)


def compiles_path(text):
    """Whether Rust source may compile its OUT_DIR in other than through an include macro."""
    literals = sum(decoded(match) == "OUT_DIR" for match in STRING_CANDIDATE.findall(text))
    return literals > len(INCLUDED_OUT_DIR.findall(text)) or NONLITERAL_ENV.search(text) is not None


def compiles_out_dir(package, deadline):
    """Whether the package's library sources compile its OUT_DIR in."""
    root = Path(package["manifest_path"]).parent
    for directory, dirs, files in os.walk(root):
        deadline.left()
        dirs[:] = [d for d in dirs if d not in {"target", "tests", "benches", "examples", ".git"}]
        for name in files:
            if name.endswith(".rs") and not (Path(directory) == root and name == "build.rs"):
                if compiles_path(Path(directory, name).read_text(encoding="utf-8", errors="replace")):
                    return True
    return False


def remove(item, deadline):
    """Delete a file or a whole directory without following links, within the time limit."""
    deadline.left()
    if not item.is_dir() or item.is_symlink():
        item.unlink()
        return
    for directory, dirs, files in os.walk(item, topdown=False):
        for name in files:
            deadline.left()
            os.unlink(os.path.join(directory, name))
        for name in dirs:
            deadline.left()
            path = os.path.join(directory, name)
            os.unlink(path) if os.path.islink(path) else os.rmdir(path)
    deadline.left()
    os.rmdir(item)


def remove_units(staging, layout, hashes, deadline):
    for sub in (".fingerprint", "build", "deps", "examples"):
        directory = staging / layout / sub
        for item in directory.iterdir() if directory.is_dir() else ():
            match = UNIT.match(item.name)
            if match and match["hash"] in hashes:
                remove(item, deadline)


def remove_unclassified(staging, layout, deadline):
    """Final artifacts Cargo places beside the unit directories carry no unit to classify them by."""
    for item in (staging / layout).iterdir():
        if item.name not in CARGO_ENTRIES:
            remove(item, deadline)
    for sub in ("deps", "examples"):
        directory = staging / layout / sub
        for item in directory.iterdir() if directory.is_dir() else ():
            if not UNIT.match(item.name):
                remove(item, deadline)


def sanitize(work, staging, found, roots, deadline):
    for layout in found:
        remove_unclassified(staging, layout, deadline)
    env = {**without_redirects(), "CARGO_TARGET_DIR": str(staging)}
    resolved = metadata(work, deadline, env=env, deps=True)
    if not (Path(resolved["target_directory"]).resolve() == Path(resolved["build_directory"]).resolve() == staging.resolve()):
        raise Unsafe("Cargo does not resolve the staging directory as both target and build directory")
    names = {package["name"] for package in resolved["packages"]}
    path_packages = sorted({package["name"] for package in resolved["packages"] if package["source"] is None})
    out_dir_packages = sorted({package["name"] for package in resolved["packages"] if package["source"] is not None
                               and any("custom-build" in t["kind"] for t in package["targets"])
                               and compiles_out_dir(package, deadline)})
    removed = set()
    for layout in found:
        orphans = {m["hash"] for item in (staging / layout / ".fingerprint").iterdir()
                   if (m := UNIT.match(item.name)) and m["name"] not in names}
        foreign = foreign_runs(staging, layout, roots, deadline)
        removed |= {m["name"] for item in (staging / layout / ".fingerprint").iterdir()
                    if (m := UNIT.match(item.name)) and m["hash"] in orphans | foreign}
        remove_units(staging, layout, orphans | foreign, deadline)
    clean = path_packages + out_dir_packages
    if clean:
        base = ["cargo", "clean", "--frozen", "--target-dir", str(staging), "--profile", "dev"]
        for name in clean:
            base += ["-p", name]
        run(base, cwd=work, deadline=deadline, env=env)  # Without --target only the host layout's outputs go.
        triples = [arg for layout in found[1:] for arg in ("--target", layout.parts[0])]
        if triples:
            run([*base, *triples], cwd=work, deadline=deadline, env=env)
    return sorted(removed | set(clean))


def warm_cargo(work, anchor, staging_root, deadline):
    if not (work / "Cargo.toml").is_file():
        return None
    if sys.platform not in {"darwin", "linux"}:
        return entry("cargo", "skipped", reason=f"cloning is unsupported on {sys.platform}")
    started = time.monotonic()
    with contextlib.ExitStack() as stack:
        staging = None
        try:
            if shutil.which("cargo") is None:
                raise Skip("cargo is not on PATH")
            target, relative, parent = destination(work, deadline, stack)
            candidates = donors(work, anchor, relative, deadline)
            if not candidates:
                raise Skip(f"no built {relative} in this repository's checkouts")
            if os.stat(staging_root).st_dev != os.fstat(parent.fd).st_dev:
                raise Skip("the staging and target directories are on different volumes")
            root = stack.enter_context(contextlib.closing(_Fd(os.open(staging_root, os.O_RDONLY | os.O_DIRECTORY))))
            busy = []
            for checkout, donor, _ in candidates:
                if os.stat(donor).st_dev != os.stat(staging_root).st_dev:
                    busy.append(f"{donor} is on another volume")
                    continue
                name = f".warm-cargo-{uuid.uuid4().hex}"
                try:
                    with read_lock(donor) as (fd, lock):
                        identity = os.stat(donor / PROFILE_DIR)
                        found = layouts(donor)
                        os.mkdir(name, dir_fd=root.fd)
                        staging = staging_root / name
                        for layout in found:
                            clone(donor / layout, staging / layout, deadline)
                        after = os.stat(donor / PROFILE_DIR)
                        if (identity.st_dev, identity.st_ino) != (after.st_dev, after.st_ino) or not same_file(fd, lock):
                            raise Unsafe(f"{donor} was replaced while it was cloned")
                except TimeUp:
                    raise
                except Skip as exc:
                    busy.append(str(exc))
                    if staging is not None:
                        remove(staging, deadline)
                        staging = None
                    continue
                check_clone(staging, deadline)
                if (donor / "CACHEDIR.TAG").is_file():
                    (staging / "CACHEDIR.TAG").write_bytes((donor / "CACHEDIR.TAG").read_bytes())
                removed = sanitize(work, staging, found, [str(donor), str(checkout)], deadline)
                deadline.left()
                try:
                    reached = open_beneath(work, relative.parts[:-1])
                except OSError as exc:
                    raise Unsafe(f"{relative.parent} changed while warming: {exc.strerror}") from exc
                try:
                    held, now = os.fstat(parent.fd), os.fstat(reached)
                    if (held.st_dev, held.st_ino) != (now.st_dev, now.st_ino):
                        raise Unsafe(f"{relative.parent} changed while warming")
                finally:
                    os.close(reached)
                publish(root.fd, name, parent.fd, relative.name)
                staging = None
                return entry("cargo", "seeded", path=str(target), donor=str(donor),
                             removed=removed, seconds=round(time.monotonic() - started, 1))
            raise Skip("; ".join(busy))
        except Skip as exc:
            result = entry("cargo", "skipped", reason=str(exc))
        except Unsafe as exc:
            result = entry("cargo", "failed", reason=str(exc))
        except FileNotFoundError as exc:
            result = entry("cargo", "skipped", reason=f"{exc.filename} disappeared while warming")
        except Exception as exc:  # Reported, never raised: allocation goes on cold.
            result = entry("cargo", "failed", reason=f"{type(exc).__name__}: {exc}")
        if staging is not None and os.path.lexists(staging):
            try:
                remove(staging, deadline)
            except TimeUp:
                # Removing a large partial clone would outlast the limit; scratch cleanup owns it.
                result["residue"] = str(staging)
        return result


def warm(work, anchor, staging_root, *, budget=BUDGET_SECONDS):
    """Warm every eligible build directory of a new worktree; never raises for a tool's failure."""
    work, anchor, staging_root = Path(work).resolve(), Path(anchor).resolve(), Path(staging_root).resolve()
    results = []
    for tool, warmer in (("cargo", warm_cargo),):
        try:
            result = warmer(work, anchor, staging_root, Deadline(budget))
        except Exception as exc:  # Optional warming reports any failure; allocation goes on cold.
            result = entry(tool, "failed", reason=f"{type(exc).__name__}: {exc}")
        if result is not None:
            results.append(result)
            print(f"warm-build-dirs: {tool} {result['status']}: {result.get('path') or result.get('reason')}", file=sys.stderr)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("worktree", nargs="?", type=Path)
    parser.add_argument("--from", dest="anchor", type=Path, help="the checkout to warm from first (default: the main worktree)")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if args.worktree is None:
        parser.error("a worktree is required")
    work = args.worktree.resolve()
    anchor = args.anchor.resolve() if args.anchor else None
    if anchor is None:
        listing = subprocess.run(["git", "-C", str(work), "worktree", "list", "--porcelain"],
                                 capture_output=True, text=True, check=True).stdout
        anchor = Path(listing.splitlines()[0].removeprefix("worktree ")).resolve()
    common = subprocess.run(["git", "-C", str(work), "rev-parse", "--path-format=absolute", "--git-common-dir"],
                            capture_output=True, text=True, check=True).stdout.strip()
    staging_root = Path(tempfile.mkdtemp(prefix=".warm-build-dirs-", dir=common))
    results = warm(work, anchor, staging_root)
    if not any(result.get("residue") for result in results):
        staging_root.rmdir()
    print(json.dumps(results, sort_keys=True))
    return 0


def self_test():
    result = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(WarmTests))
    if result.wasSuccessful():
        print(f"warm-build-dirs self-test: PASS ({result.testsRun} isolated tests)")
    return 0 if result.wasSuccessful() else 1


# Fixtures use real Git and a fake `cargo` on PATH that answers `metadata` from a JSON file
# and performs `clean -p` on the layout as Cargo names it; a filesystem without cloning
# copies instead, in tests only, so every rule still runs there.
FAKE_CARGO = r"""#!/usr/bin/env python3
import json, os, pathlib, shutil, sys, time
argv = sys.argv[1:]
fixture = json.loads(pathlib.Path(os.environ["FAKE_CARGO"]).read_text())
with open(os.environ["FAKE_CARGO_LOG"], "a") as log:
    log.write(json.dumps(argv) + "\n")
time.sleep(fixture.get("sleep", 0))
target = pathlib.Path(os.environ.get("CARGO_TARGET_DIR") or os.getcwd() + "/" + fixture.get("target", "target"))
if argv[0] == "metadata":
    found = {"target_directory": str(target), "packages": fixture["packages"] if "--no-deps" not in argv else [],
             "metadata": fixture.get("workspace_metadata", {"devlyn": {"warm-build-dirs": True}})}
    if not fixture.get("old_cargo"):
        found["build_directory"] = fixture.get("build_directory", str(target))
    print(json.dumps(found))
elif argv[0] == "clean":
    directory = pathlib.Path(argv[argv.index("--target-dir") + 1])
    names = [argv[i + 1] for i, a in enumerate(argv) if a == "-p"]
    triples = [argv[i + 1] for i, a in enumerate(argv) if a == "--target"]
    for layout in [directory / t / "debug" for t in triples] or [directory / "debug"]:
        for name in names:
            for sub in (".fingerprint", "build", "deps"):
                for item in (layout / sub).glob("*"):
                    stem = item.name.split(".")[0].removeprefix("lib")
                    if stem.rsplit("-", 1)[0].replace("_", "-") == name:
                        shutil.rmtree(item) if item.is_dir() else item.unlink()
    if fixture.get("swap") and not os.path.islink("build"):
        os.rename("build", "build-moved")
        os.symlink(fixture["swap"], "build")
    if fixture.get("race"):
        (pathlib.Path(os.getcwd()) / "target").mkdir(exist_ok=True)
"""


class WarmTests(unittest.TestCase):
    def setUp(self):
        # Imported here: unittest.mock imports asyncio, which a caller simulating Windows cannot load.
        from unittest import mock
        temporary = tempfile.TemporaryDirectory(prefix="warm-build-dirs-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.anchor, self.work = self.root / "anchor", self.root / "work"
        self.staging = self.root / "scratch"
        self.staging.mkdir()
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        (bin_dir / "cargo").write_text(FAKE_CARGO)
        (bin_dir / "cargo").chmod(0o755)
        self.fixture, self.log = self.root / "fixture.json", self.root / "cargo.log"
        self.environment = mock.patch.dict(os.environ, {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}", "FAKE_CARGO": str(self.fixture),
            "FAKE_CARGO_LOG": str(self.log), "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        for key in REDIRECTS:
            os.environ.pop(key, None)
        self.anchor.mkdir()
        self.git(self.anchor, "init", "-q", "-b", "main")
        (self.anchor / "Cargo.toml").write_text("[workspace]\n")
        (self.anchor / ".gitignore").write_text("target/\n/build/target/\n")
        self.git(self.anchor, "add", "-A")
        self.git(self.anchor, "commit", "-q", "-m", "init")
        self.git(self.anchor, "worktree", "add", "-q", "-b", "task", str(self.work))
        self.write_fixture()
        self.donor = self.anchor / "target"
        self.build_donor()
        probe = self.root / "probe"
        probe.mkdir()
        (probe / "file").write_bytes(b"x" * 65536)
        self.native_clone = True
        try:
            if os.name == "nt":
                raise Skip("no clone primitive")
            clone(probe, self.root / "probe-clone", Deadline(30))
            self.native_clone = (self.root / "probe-clone" / "file").read_bytes() == b"x" * 65536
        except (Skip, OSError):
            self.native_clone = False
        if not self.native_clone:
            # A plain copy that keeps links and special files, as a clone would; tests only.
            patch = mock.patch(f"{__name__}.clone", lambda source, target, deadline: subprocess.run(
                ["cp", "-a", "--", str(source), str(target)], check=True))
            patch.start()
            self.addCleanup(patch.stop)

    def git(self, work, *args):
        return subprocess.run(["git", "-C", str(work), *args], check=True, capture_output=True, text=True).stdout

    def write_fixture(self, **extra):
        packages = [
            {"name": "app", "source": None, "manifest_path": str(self.work / "Cargo.toml"), "targets": [{"kind": ["lib"]}]},
            {"name": "serde", "source": "registry", "manifest_path": str(self.root / "registry/serde/Cargo.toml"), "targets": [{"kind": ["lib"]}]},
            {"name": "ring", "source": "registry", "manifest_path": str(self.root / "registry/ring/Cargo.toml"), "targets": [{"kind": ["lib"]}, {"kind": ["custom-build"]}]},
            {"name": "tauri", "source": "registry", "manifest_path": str(self.root / "registry/tauri/Cargo.toml"), "targets": [{"kind": ["lib"]}, {"kind": ["custom-build"]}]},
            {"name": "aws-lc-rs", "source": "registry", "manifest_path": str(self.root / "registry/aws-lc-rs/Cargo.toml"), "targets": [{"kind": ["lib"]}, {"kind": ["custom-build"]}]},
            {"name": "baked", "source": "registry", "manifest_path": str(self.root / "registry/baked/Cargo.toml"), "targets": [{"kind": ["lib"]}, {"kind": ["custom-build"]}]},
            {"name": "exporter", "source": "registry", "manifest_path": str(self.root / "registry/exporter/Cargo.toml"), "targets": [{"kind": ["lib"]}, {"kind": ["custom-build"]}]},
            {"name": "generator", "source": "registry", "manifest_path": str(self.root / "registry/generator/Cargo.toml"), "targets": [{"kind": ["lib"]}, {"kind": ["custom-build"]}]},
        ]
        for package in packages[1:]:
            source = Path(package["manifest_path"]).parent / "src"
            source.mkdir(parents=True, exist_ok=True)
            (source / "lib.rs").write_text('include!(concat!(\n  env!("OUT_DIR"), "/gen.rs"));\n' if package["name"] != "baked"
                                           else 'pub const DIR: &str = env!(/* why */ "OUT_DIR");\n')
        self.fixture.write_text(json.dumps({"packages": packages, **extra}))

    def unit(self, layout, sub, name, digest, files=None):
        directory = self.donor / layout / sub / f"{name}-{digest}"
        directory.mkdir(parents=True, exist_ok=True)
        for relative, data in (files or {"stamp": b"x"}).items():
            (directory / relative).parent.mkdir(parents=True, exist_ok=True)
            (directory / relative).write_bytes(data)

    def run_unit(self, layout, name, digest, output, out_files):
        old_out = f"{self.donor}/{layout}/build/{name}-{digest}/out"
        self.unit(layout, ".fingerprint", name, digest)
        self.unit(layout, "build", name, digest, {"root-output": old_out.encode(), "output": output(old_out).encode(),
                                                  **{f"out/{k}": v(old_out) for k, v in out_files.items()}})

    def build_donor(self):
        for layout in ("debug", "x86_64-pc-windows-msvc/debug"):
            deps = self.donor / layout / "deps"
            deps.mkdir(parents=True)
            for name, digest in (("serde", "1" * 16), ("app", "2" * 16), ("gone", "7" * 16), ("baked", "8" * 16)):
                self.unit(layout, ".fingerprint", name, digest)
                (deps / f"lib{name}-{digest}.rlib").write_bytes(b"rlib")
            (self.donor / layout / ".cargo-lock").write_bytes(b"")
            (self.donor / layout / "incremental" / "app-x").mkdir(parents=True)
            # Final artifacts Cargo puts beside the unit directories, here of the unused `gone`.
            (self.donor / layout / "old-tool").write_bytes(b"bin")
            (self.donor / layout / "examples").mkdir()
            (self.donor / layout / "examples" / "old-example").write_bytes(b"bin")
            self.run_unit(layout, "ring", "4" * 16, lambda out: f"cargo:rustc-link-search=native={out}\n",
                          {"libring.a": lambda out: b"\0\x01" + out.encode()})
            self.run_unit(layout, "tauri", "3" * 16, lambda out: f"cargo:rustc-link-search=native={out}\n",
                          {"permission-files": lambda out: f'["{out}/app_hide.toml"]'.encode()})
            self.run_unit(layout, "aws-lc-rs", "5" * 16,
                          lambda out: f"cargo:include={self.donor}/{layout}/build/aws-lc-sys-{'6' * 16}/out/include\n", {})
            # A variable handed to rustc that carries the script's own OUT_DIR is compiled in as is.
            self.run_unit(layout, "exporter", "9" * 16, lambda out: f"cargo:rustc-env=DEBUG_OUTPUT_DIR={out}\n", {})
            # Generated Rust that compiles its OUT_DIR in names no donor path in its text.
            self.run_unit(layout, "generator", "a" * 16, lambda out: f"cargo:rustc-link-search=native={out}\n",
                          {"gen.rs": lambda out: b'pub const DIR: &str = env!("OUT\\x5fDIR");\n'})
        (self.donor / "CACHEDIR.TAG").write_bytes(b"Signature: 8a477f597d28d172789f06886806bc55\n")

    def snapshot(self, root):
        return {str(p.relative_to(root)): (p.lstat().st_size, p.lstat().st_mtime_ns, p.lstat().st_mode)
                for p in sorted(root.rglob("*"))}

    def warm(self, **kwargs):
        return warm(self.work, self.anchor, self.staging, **kwargs)

    def assert_nothing_left(self):
        self.assertEqual([], list(self.staging.iterdir()))
        self.assertEqual("", self.git(self.work, "status", "--porcelain", "--untracked-files=all"))

    @unittest.skipIf(os.name == "nt", "warming is POSIX-only")
    def test_seeds_only_what_carries_over_and_never_writes_the_donor(self):
        before = self.snapshot(self.donor)
        [result] = self.warm()
        self.assertEqual("seeded", result["status"], result)
        target = self.work / "target"
        for layout in ("debug", "x86_64-pc-windows-msvc/debug"):
            kept = {p.name for p in (target / layout / ".fingerprint").iterdir()}
            self.assertEqual({f"serde-{'1' * 16}", f"ring-{'4' * 16}"}, kept, layout)
            self.assertEqual({".fingerprint", "build", "deps", "examples", ".cargo-lock"}, {p.name for p in (target / layout).iterdir()})
            self.assertEqual([], list((target / layout / "examples").iterdir()))
            self.assertTrue((target / layout / "build" / f"ring-{'4' * 16}" / "out" / "libring.a").exists())
        self.assertEqual(["app", "aws-lc-rs", "baked", "exporter", "generator", "gone", "tauri"], result["removed"])
        self.assertEqual(str(self.donor), result["donor"])
        self.assertEqual(before, self.snapshot(self.donor))
        self.assert_nothing_left()

    @unittest.skipIf(os.name == "nt", "warming is POSIX-only")
    def test_a_busy_donor_is_skipped_without_waiting(self):
        import fcntl
        with open(self.donor / "debug" / ".cargo-lock", "rb") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            [result] = self.warm()
        self.assertEqual("skipped", result["status"])
        self.assertIn("a build is using", result["reason"])
        self.assertFalse((self.work / "target").exists())
        self.assert_nothing_left()

    @unittest.skipIf(os.name == "nt", "warming is POSIX-only")
    def test_ineligible_destinations_are_skipped_with_their_reason(self):
        cases = {
            "already exists": lambda: (self.work / "target").mkdir(),
            "not ignored": lambda: (self.work / ".gitignore").write_text(""),
            "not enabled": lambda: self.write_fixture(workspace_metadata=None),
            "separate Cargo build-dir": lambda: self.write_fixture(build_directory=str(self.root / "elsewhere")),
            "build directory (Cargo 1.91": lambda: self.write_fixture(old_cargo=True),
            "comes from this environment": lambda: os.environ.__setitem__("CARGO_TARGET_DIR", str(self.root / "t")),
            "no built target": lambda: shutil.rmtree(self.donor),
        }
        for reason, arrange in cases.items():
            with self.subTest(reason):
                self.setUp()
                arrange()
                [result] = self.warm()
                self.assertEqual("skipped", result["status"], result)
                self.assertIn(reason, result["reason"])
                self.assertEqual([], list(self.staging.iterdir()))

    @unittest.skipIf(os.name == "nt", "warming is POSIX-only")
    def test_a_clone_with_git_data_or_a_link_out_is_refused(self):
        for name, arrange in {
            "links out": lambda: (self.donor / "debug" / "build" / "link").symlink_to(self.root),
            "Git data": lambda: (self.donor / "debug" / "deps" / ".git").mkdir(),
        }.items():
            with self.subTest(name):
                self.setUp()
                arrange()
                before = self.snapshot(self.donor)
                [result] = self.warm()
                self.assertEqual("failed", result["status"], result)
                self.assertIn(name, result["reason"])
                self.assertFalse(os.path.lexists(self.work / "target"))
                self.assertEqual(before, self.snapshot(self.donor))
                self.assertEqual([], list(self.staging.iterdir()))

    @unittest.skipIf(os.name == "nt", "warming is POSIX-only")
    def test_running_out_of_time_publishes_nothing(self):
        self.write_fixture(sleep=2)
        [result] = self.warm(budget=1)
        self.assertEqual("skipped", result["status"])
        self.assertIn("timed out", result["reason"])
        self.assertFalse((self.work / "target").exists())
        self.assertEqual([], list(self.staging.iterdir()))

    @unittest.skipIf(os.name == "nt", "warming is POSIX-only")
    def test_a_target_that_appears_meanwhile_is_never_replaced(self):
        self.write_fixture(race=True)
        [result] = self.warm()
        self.assertEqual("skipped", result["status"])
        self.assertIn("cannot publish", result["reason"])
        self.assertEqual([], list((self.work / "target").iterdir()))
        self.assertEqual([], list(self.staging.iterdir()))

    @unittest.skipIf(os.name == "nt", "warming is POSIX-only")
    def test_a_parent_replaced_while_warming_receives_nothing(self):
        (self.anchor / "build").mkdir()
        self.donor = self.anchor / "build" / "target"
        (self.anchor / "target").rename(self.donor)
        (self.work / "build").mkdir()
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        self.write_fixture(target="build/target", swap=str(elsewhere))
        [result] = self.warm()
        self.assertEqual("failed", result["status"], result)
        self.assertIn("changed while warming", result["reason"])
        self.assertEqual([], list(elsewhere.iterdir()))
        self.assertFalse((self.work / "build-moved" / "target").exists())
        self.assertEqual([], list(self.staging.iterdir()))

    @unittest.skipIf(os.name == "nt", "warming is POSIX-only")
    def test_a_special_file_is_never_read(self):
        os.mkfifo(self.donor / "debug" / "build" / f"tauri-{'3' * 16}" / "out" / "pipe")
        [result] = self.warm(budget=20)
        self.assertEqual("failed", result["status"], result)
        self.assertIn("not a regular file or directory", result["reason"])
        self.assertFalse((self.work / "target").exists())
        self.assertEqual([], list(self.staging.iterdir()))

    @unittest.skipIf(os.name == "nt", "warming is POSIX-only")
    def test_a_malformed_build_record_fails_explicitly(self):
        (self.donor / "debug" / "build" / f"tauri-{'3' * 16}" / "root-output").write_bytes(b"")
        [result] = self.warm()
        self.assertEqual("failed", result["status"], result)
        self.assertIn("does not name this run's OUT_DIR", result["reason"])
        self.assertFalse((self.work / "target").exists())
        self.assertEqual([], list(self.staging.iterdir()))

    @unittest.skipIf(os.name == "nt", "warming is POSIX-only")
    def test_allocation_warms_its_worktree_and_records_the_outcome(self):
        tree = self.root / "allocated"
        head = self.git(self.anchor, "rev-parse", "HEAD").strip()
        completed = subprocess.run([sys.executable, str(Path(__file__).with_name("task-complete.py")), "allocate",
                                    "--repo", str(self.anchor), "--task", "warm", "--branch", "warm-allocation",
                                    "--worktree", str(tree), "--local-base", head], capture_output=True, text=True)
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        result = json.loads(completed.stdout)
        [warmed] = result["build_dirs"]
        if self.native_clone:
            self.assertEqual(("seeded", str(tree / "target")), (warmed["status"], warmed.get("path")), warmed)
        else:  # The child cannot use the fixture's copy; a filesystem without cloning must skip.
            self.assertEqual("skipped", warmed["status"], warmed)
            self.assertIn("cannot clone", warmed["reason"])
        self.assertEqual(result["build_dirs"], json.loads(Path(result["receipt"]).read_text())["build_dirs"])
        self.assertEqual("", self.git(tree, "status", "--porcelain", "--untracked-files=all"))
        self.assertEqual([], list(Path(result["scratch"]).iterdir()))

    def test_compiled_in_out_dir_is_recognized_in_every_spelling(self):
        compiled = ['env!("OUT_DIR")', 'env!("OUT_DIR", "missing")', 'env ! ( "OUT_DIR" )', 'std::env!(r"OUT_DIR")',
                    'option_env!("OUT_DIR")', 'myinclude!(concat!(env!("OUT_DIR"), "/a.rs"))', 'env![ "OUT_DIR" ]',
                    'env/**/!("OUT_DIR")', 'env!(/* why */ "OUT_DIR")', 'env!("OUT\\x5fDIR")', 'env!("\\u{4f}UT_DIR")',
                    'use std::env as e; e!("OUT_DIR")', 'env!(concat!("OUT", "_DIR"))', 'env!(// note\n"OUT_DIR")',
                    'env!("\\u{4_f}UT_DIR")', 'env!("OUT_\\\n      DIR")', 'let a = \'"\'; env!("OUT_DIR")',
                    'include!(concat!(env!(/* c */ "OUT_DIR"), "/a.rs"))']
        for text in compiled:
            self.assertTrue(compiles_path(text), text)
        for text in ['include!(concat!(env!("OUT_DIR"), "/a.rs"));', 'include_bytes!(concat!(\n  env!("OUT_DIR"),\n "/b"))',
                     'env!("OUT_DIRS")', 'env!("CARGO_PKG_NAME")', 'let s = "OUT_DIR_NAME";']:
            self.assertFalse(compiles_path(text), text)

    def test_no_cargo_workspace_or_an_unsupported_platform_does_nothing(self):
        (self.work / "Cargo.toml").unlink()
        self.assertEqual([], self.warm())
        (self.work / "Cargo.toml").write_text("[workspace]\n")
        from unittest import mock
        with mock.patch.object(sys, "platform", "win32"):
            [result] = self.warm()
        self.assertEqual(("skipped", "cloning is unsupported on win32"), (result["status"], result["reason"]))
        self.assertFalse(self.log.exists())


if __name__ == "__main__":
    sys.exit(main())
