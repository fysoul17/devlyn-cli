# 0266 amendment 2: the copy of a cell's /tmp leaves special files out and can hold any directory, and a cleared teardown STOP is recovered and run again (2026-11-14)

This is a dated amendment to [DESIGN.md](DESIGN.md) "Operations", which takes 0265's "Faults" rule
([../0265/DESIGN.md](../0265/DESIGN.md)). It changes two operations: how a cell's `/tmp` volume is copied into the
cell, and what becomes of a registered slot whose teardown failed once an amendment has cleared its latch. DESIGN.md
and [registration.md](registration.md) are unchanged.

## What happened

Times are KST on 2026-11-14, from `output/driver-claude.log`, the two `output/driver-status-*.json` files, and c069's
verdict and folder in the runtime root. The diagnostic containers are the orchestrator's; the runtime root does not
keep them.

- The Codex lane is complete: 64 of 64, `complete` at 03:56:05.
- The Claude lane ended at 04:49:11 with a harm latch on `c069-D4-claude-B-r1`, its 69th slot and its first D4 row:
  `STOP teardown failed`. 133 of 176 slots have a verdict (64 Codex, 69 Claude). 43 Claude slots remain: 15 D4, 14
  B5 and 14 D3.
- c069's owner ended `EXITED_0`, usage `COMPLETE`, identity `MATCH`. The teardown removed the owner's container and
  the credential copy. Then the copy of the cell's `/tmp` volume into `c069-D4-claude-B-r1/tmp` failed:
  `tar: ./exp/tmp79kh78r5/fifo_noperm: Cannot mkfifo: Permission denied`, and the same for `exp/tmp9f3tfxi1`. The
  session had written its own experiment, `/tmp/exp/e.py`, on `click.File` (D4 is the click task). It ran it twice,
  and each run made a FIFO of mode 0200 (beside a file of mode 0200, a dangling link and a looping link).
- Cause, shown at 04:51 by two diagnostic containers on the pinned image: on Docker Desktop's host mount, `mkfifo`
  works for a FIFO of mode 644 and fails with "Permission denied" for one of mode 0200, as c069's are. The node
  appears on the host all the same. The volume `devlyn-0233-tmp-0924ac2f014e4cf99266f7df8a55a52a` holds 1196
  entries; the two FIFOs are its only entries that are not a regular file, a directory or a symlink. The partial copy
  on the host has 1196 paths (its root counted), both half-made FIFO nodes among them.
- The copy is `preserve_tmp` in `0233/cell.py` (`tar -C /src -cf - . | tar -C /dst -xpf -`), unchanged since 0233's
  registration. It is reached through `0265/cell.py` (`preserve_tmp = legacy.preserve_tmp`, called in `run()`'s
  teardown) and through `driver.py`'s `prove_docker_teardown` (`cell.cell_run.preserve_tmp`). Every test of it
  replaces it with a fake; none runs its body.
- The teardown was not proved, so `run_cell.py` graded nothing: `stop_evidence(proved=False)` wrote
  `scope_violations: null` and `scope_error: not taken: the teardown is not proved`. There is no `checks.json`, no
  snapshot and no assessment. The volume was not removed: its removal comes after the copy.
- The frozen design has no rule for a registered slot after a STOP that is not redispatched has its latch cleared.
  Only screen slots have one: the slot is passed and reads as an unknown. In code a cleared registered STOP ends the
  lane again (`terminal()` raises `Stopped`, with no new latch). Left so, this one slot makes the final verdict
  NOT_FINISHED (`decide.py`: a slot without a final verdict is a missing input of G1, G2 and G3), and an attempt
  archived without a scope result leaves G2 NOT_FINISHED.
- The design's one rule for a failed teardown is the proven Docker loss (0265 DESIGN "Faults",
  [0257 amendment 3](../0257/amendment-3.md)). The teardown is ended and proved (`driver.py` `recover()`:
  `prove_docker_teardown`, sealed again, `stop_evidence`), the attempt is archived (`.stop-N`) and its slot is
  dispatched again. Until now `recover()` is reached only when the teardown error names the Docker daemon
  (`docker_fault`).

The proof of the first version of the copy (special files left out, directories copied as before), run by the
orchestrator on the pinned image from 05:23 to 05:35 on scratch volumes (GNU tar 1.35, findutils 4.10.0), showed that
the copy, old and new, also fails on a directory whose mode denies its owner and on a read-only directory that holds
a file. So the change covers directories too. No cell had met that case. What was measured on Docker Desktop's host
mount, written by root in a container:

- `mkdir -m <mode>` fails with "Permission denied" for 000, 100, 200, 300 and 111 and works for 400, 500, 600, 700
  and 555: a directory is refused when its mode has no owner read bit. `mkfifo -m` fails for 000, 200, 400 and 444
  and works for 600 and 644. In every failing case the node appears on the host all the same.
- GNU tar run by root creates a directory with its recorded mode at once (it adds owner write and search only when
  it is not root). So the old copy fails on a directory of mode 000 ("Cannot mkdir: Permission denied") and on a
  read-only directory that holds a file (mode 555: "Cannot open: Permission denied", since the host directory has no
  write bit when the file is to be made).
- A directory that exists already is not created by tar: tar sets its recorded mode and time once its members are
  done, and the mount keeps a 555 directory usable on the host (host mode 755, the recorded mode in an attribute).
  For a recorded mode without owner search (000, 600) the host directory ends without the search bit, the host user
  cannot read what is inside, and `seal_after_teardown` could not hash it.
- A regular file of any mode (000, 200, 444) is copied and stays readable on the host, as before.

## The change

### 1. The copy leaves special files out, can hold any directory, and lists what it changed (0266 only)

`0233/cell.py` and `0265/cell.py` stay byte for byte, so the `imported` hashes in every cell's `seal.json` stay the
same. `run_cell.py` defines its own `preserve_tmp(volume, dest, image)` and sets it in its loaded copy of
`0265/cell.py` right after the modules load, the way `0265/check.py` replaces `base.in_image`. `0265/cell.py`'s
`run()` and `driver.py`'s recovery look the name up at call time, so both use it. It does four things:

1. If `dest` holds anything, it empties it first and keeps `dest` itself and its mode. A copy that failed before
   left its part there: half-made FIFO nodes, and directories the host user may not be able to enter. Each
   directory is given owner read, write and search before it is entered, and a symlink is removed, never followed.
   The volume still holds everything.
2. It runs one copy container, as before (`docker run --rm --network none --user 0`, the volume read-only at `/src`,
   `dest` at `/dst`, `--entrypoint bash`, the pinned image, a 600 s timeout). It reads the output as bytes, since a
   name need not be UTF-8. The command:
   ```
   set -o pipefail; cd /src && find . \( -type p -o -type s -o -type b -o -type c \) -printf 'left_out\0%y\0%m\0%p\0' && find . -type d ! -perm -u+x -printf 'made_searchable\0%y\0%m\0%p\0' && find . -type d -print0 | (cd /dst && xargs -0 -r mkdir -p --) && find . ! \( -type p -o -type s -o -type b -o -type c \) -print0 | tar --null --no-unquote --verbatim-files-from --no-recursion -T - -cf - | tar -C /dst -xpf - && find . -type d ! -perm -u+x -print0 | (cd /dst && xargs -0 -r chmod u+x --)
   ```
   In words: (1) list the FIFOs, sockets and device nodes, which are left out; (2) list the directories whose mode
   has no owner search bit; (3) make every directory in `dest` first, with the default mode, so that tar never
   creates one with a mode the mount refuses and can write into read-only ones; (4) copy everything that is not a
   special file, as before (the extract side is unchanged; tar then sets each directory's recorded mode and time, and
   the root entry `.` is a member, so `dest` keeps the volume root's mode); (5) give the directories of (2) the owner
   search bit in `dest`, parents first, so that the host can read the evidence inside.
3. The output is NUL-separated records of four fields: kind (`left_out` or `made_searchable`), type letter, octal
   mode, path. They go to `run/tmp-copy.json` beside `dest`: `{"left_out": [{"type", "mode", "path"}, ...],
   "made_searchable": [{"mode", "path"}, ...]}`, written only when a list is not empty. When both are empty, no such
   file exists. `seal_after_teardown` runs after the teardown in both callers and seals it with `run/`.
4. Then it removes the volume, as before. Any failure raises as before: `0265/cell.py` records `teardown: FAILED`,
   and the recovery stops both lanes. A failure before the removal leaves the volume as it was; a failure of the
   removal itself leaves the copy done and the volume in place.

What differs from the volume in the copy: the special files are absent and listed, and the listed directories have
the owner search bit added. Everything else is as the old copy gave it: on an ordinary volume (610 entries, a git
repository, read-only files, hard links, symlinks, set times) the old copy and this one gave identical trees (type,
mode, owner, link count, size, modification time, path and link target of every entry).

Special files are left out because the host mount refuses some of them. Nothing reads them, with one exception that
changes. `seal_after_teardown` hashes regular files only. But when no receipt binds an accepted commit, the locator
(`0265/locate.py`) copies each tree it compares (the anchor and each linked worktree) path by path as Git lists
them, a file with `shutil.copy2`, which refuses a FIFO. So a tracked path that is a FIFO in a linked worktree under
`/tmp` was a locator STOP under the old copy, when the mount had accepted the FIFO. Now a tracked path that is a
special file is absent from the copy, and the locator skips it as a file the session deleted (`copy_tree`), both
when it compares the trees and in the graded tree. No cell of the two lanes has had a `locator:` STOP: such a STOP
latches both lanes, and neither lane's status file holds a latch but c069's or a cleared one.

Directories are made first because the mount refuses to create one whose mode has no owner read bit, and tar run as
root creates each with its recorded mode at once. The owner search bit is added at the end because the seal cannot
read what a directory without it holds.

### 2. A registered slot's cleared teardown STOP is recovered, archived and run again (`driver.py`)

A STOP whose reason starts with `teardown failed: ` on a registered slot (not a screen slot), once an amendment has
cleared its latch, is ended as a proven Docker loss is: `recover()` proves the teardown (containers gone, the volume
preserved by the copy and removed, both proved gone, and the attempt's credential copy already gone from scratch),
seals the cell again and calls `stop_evidence`, which replaces the old `scope_error` with the attempt's tree and
scope result. The attempt is archived as `.stop-N` and the slot is dispatched again. A recovery that cannot be
proved stops both lanes and keeps the volume, as before. The rule reads a SMOKE row as it reads a registered slot;
SMOKE ended before the screen and is not run again.

Nothing else changes. A teardown STOP that no amendment cleared latches both lanes as before: there is no automatic
redispatch, also not for a repeat on the same slot. A screen slot's cleared STOP is passed as before, and no screen
cell is run again. The lane regrades or runs again some STOPs by itself, whether or not a latch was cleared: an
assessor fault; a slot's first launch fault, memory kill or shared account fault; a Docker loss. A cleared STOP on
a registered slot that is none of these and not a failed teardown ends its lane without a new latch, as before.

## Why the slot is run again and not graded

The design grades no attempt whose teardown failed. Its one rule for a failed teardown, a proven Docker loss, proves
the teardown, archives the attempt and runs the slot again. A memory kill, which also follows from what a session
did, is run again once in the same way. The archived attempt is read as the design's rule for attempts says: its
owner input is charged (G3), its tree and scope result enter the harm readings (G2), and D4's witnesses run on it.

What this costs: the first attempt's completion is never read. So one D4 result of arm B is replaced by a fresh run
because of what its session did in `/tmp`. From this amendment on, a session that makes such files, or directories
the mount refuses, is graded like any other, in either arm.

## What does not change

- Every decision rule and every verdict reading.
- The grading path: `stop_evidence`, the checks, the assessors, the witnesses, the probe, the judges, `decide.py`.
- The caps.
- The screen's rule: a screen slot's cleared STOP, a failed teardown among them, is passed and reads as an unknown;
  no screen cell is run again.
- A teardown STOP still latches both lanes and needs an amendment before its slot is recovered. A Docker loss is
  still recovered without one, and its proof now also needs the attempt's credential copy already gone from scratch:
  a copy left there stopped the rerun at its setup before, and stops the recovery now.
- `0233/cell.py` and `0265/cell.py`.

## What can still fail

Each of these is a STOP, as before: `teardown: FAILED` in a cell, or both lanes stopped in a recovery. A failure
before the volume's removal leaves the volume as it was; a failure of the removal itself leaves the copy done and the
volume in place.

- A name the host cannot hold.
- Two names that differ only in letter case (the host's file system ignores case).
- A full disk.
- The copy's 600 s timeout. It ends the Docker client, not necessarily the copy container; a container still on the
  volume makes the recovery's proof fail, which stops both lanes, as with the old copy.
- Docker lost during the copy (a Docker loss, recovered without an amendment as before).

The recovery is not safe against the lane's own death inside it (operator step 7).

## What was known of the outcomes

When the change was decided and written, 133 verdicts existed. The orchestrator had opened none of the registered
verdicts except c069's STOP (its status, reason and teardown fields, and the owner, usage and identity fields quoted
in "What happened"). From the lane logs it knew only that the other 132 cells returned rc 0 (a final verdict). The
screen's decision `GO(K2)` and its event counts were known. No witness, probe, harm check, judge or `decide.py` had
run on the registered cells. c069's arm and task are in its name. Writing this file read c069's verdict and folder
in full and no other cell's. The change does not depend on any outcome and applies to every arm alike.

## Which cells ran under which rule

c001-c068 and the Codex lane's 64 cells ran under the old copy. c069's first attempt failed under it and is
recovered by the new one; the archived attempt keeps its old `seal.json`, and the lane's log names the recovery
(`docker_teardown_proven`). Every cell dispatched from the restart on carries the new `run_cell.py` and `driver.py`
in its `seal.json` (`apparatus` and `source_commit`). Cells before this amendment may hold FIFOs in `tmp/` (the old
copy kept those the host accepted); later cells hold none and list them in `run/tmp-copy.json`, with each directory
that was given the owner search bit.

## Qualification

DESIGN "Apparatus": "Qualification re-runs what a change touches".

- Q1 unit tests, 0266's and 0265's: `test_cell.py` covers the copy (its command's five steps, bytes output, both
  kinds of record in `run/tmp-copy.json`, a stale list removed, a failed copy's part removed first with directories
  of mode 000 and links out of `dest` among it, a failed copy keeping the volume, and the function 0265's `cell.py`
  and the recovery now call); `test_driver.py` covers the driver rule (a cleared teardown STOP recovered, archived
  and run again at the restart; one no amendment cleared latching, also a repeat after a recovery; a screen slot's
  passed; a recovery that cannot be proved stopping both lanes); `test_integration.py` rehearses the whole path once
  (step 10).
- The copy's proof on the pinned image: the opt-in test `CopyProof` in `test_cell.py`, in two parts. Each fills a
  scratch volume as the cell's user, copies it into a folder under `$R/scratch` and lists both sides through a root
  container.
  (run and recorded by the orchestrator under "Applied")
  - The ordinary volume (a git repository, files of mode 000, 200, 400, 444, 600, 644 and 755, folders of mode 700
    and 750, a hard-link pair, links, set times): the old copy (0233's, its volume kept) and the real `preserve_tmp`
    give identical trees (type, mode, owner, link count, size, modification time, path and link target of every
    entry, and every regular file's sha256), and no `run/tmp-copy.json`. The old copy also shows what the mount
    itself makes of each mode (a 444 file was read back as 400 once); where that differs from the volume's mode, the
    special volume is held to what the old copy gives.
  - The special volume (FIFOs of mode 0200, 0644, 000 and 0600, the last inside nested mode-000 directories; a
    socket; files of mode 0200, 000 and 444; directories of mode 555 and 600 with a file and an empty one of mode 300;
    a dangling and a looping link and a link to the mode-000 directory; a hard-link pair; the names `-dash`, `-T`,
    `--null`, `back\slash`, `new<newline>line`, `a space` and a directory `-dirdash`): the copy exits clean; the
    records name exactly the special files and the directories without owner search, with their modes; every other
    entry has the volume's type, size and path, and every regular file its sha256; modes are equal except that the
    listed directories gain exactly the owner search bit; the hard link is kept; the host user opens every regular
    file; no FIFO or socket is on the host; the volume is gone.
- Not repeated:
  - Q2 seal: it pins the packages and their session text and is written once. The change touches neither.
  - Q5 controls: the witnesses and probes are `results/operator/judge.py`, which the change does not touch, and
    `q5-controls.json` pins no apparatus code. README says the controls "are run again on a new commit and replace
    `q5-controls.json`" (lines 19-20), right after "move it aside before repeating the step on another commit" for
    the seal and the screen decision. Those lines speak of the steps before SMOKE, run again when the run is
    registered on another commit (the run worktree is moved to the registration commit before the screen, lines
    14-16). They are not a rule for an amendment after SMOKE.
  - Q6 judge calibration: the judges, their rule, prompt and descriptions are unchanged.
  - Q7 SMOKE: a model run before the screen that qualifies the launch, the forms and the assertions, none of which
    the change touches. Every later cell's verdict still records its own teardown.
  - Q3, Q4 and Q8: as DESIGN "Qualification" says; the change touches none of them.

## Operator steps

1. No lane is alive: the Claude lane ended on the latch, and the Codex lane is complete.
2. Move the run worktree (`~/.local/share/nx01/0266-run`) to the merge commit of this amendment.
3. The copy's proof (Docker, no model):
   `NX01_0266_COPY_PROOF=$R/runtime-smoke.json nice -n 10 python3 -m pytest -q $X/test_cell.py -k CopyProof`
4. While c069's verdict is unchanged, release its latch:
   `python3 $X/driver.py --clear-latch $X/amendment-2.md $R/runtime-claude.json`
5. Start the Claude lane with README step 14.
6. Check that the lane logged `docker_teardown_proven` for c069 with `tmp: preserved`; that
   `verdict-c069-D4-claude-B-r1.stop-1.json` has a scope result (`scope_violations` a list, no `scope_error`); that
   `c069-D4-claude-B-r1.stop-1/run/tmp-copy.json` lists the two FIFOs under `left_out`; and that the volume is gone
   (`docker volume ls -q --filter name=^devlyn-0233-tmp-0924ac2f014e4cf99266f7df8a55a52a$` prints nothing).
7. A lane that dies inside the recovery or before the archive is complete (between `docker_teardown_proven` and the
   slot's next `run` event) is not started again by clearing the latch a second time: a second recovery can find a
   snapshot the first one made and archive the attempt without a scope result, and a death between the two renames
   leaves a verdict without its folder. That state is resolved by a further amendment. Both edges exist for a Docker
   loss today; this amendment does not change them.

## Reported in RESULT.md

- c069's first attempt (archived as `stop-1`, with its recovery and its scope result) and its rerun.
- The number of cells with `run/tmp-copy.json` (special files left out or directories made searchable), archived
  attempts included: `ls $R/output/*/run/tmp-copy.json 2>/dev/null | wc -l`
- The Claude lane's lost time: from the latch at 04:49:11 to the restart's first dispatch.

## Reviews

(written by the orchestrator after the review)

## Applied

(written by the orchestrator)
