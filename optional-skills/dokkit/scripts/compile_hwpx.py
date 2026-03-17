#!/usr/bin/env python3
"""Compile an HWPX document from its unpacked working directory.

Usage:
    python compile_hwpx.py <work_dir> <output.hwpx> [--reference <original.hwpx>]

Critical: mimetype must be the first file in the ZIP and stored uncompressed.
When --reference is given, preserves the original ZIP's file ordering and
per-file compression types (STORED vs DEFLATED). New files not present in the
reference are appended at the end with DEFLATED compression.
"""

import os
import sys
import zipfile
from pathlib import Path


def compile_hwpx(work_dir: str, output_path: str, reference_zip: str | None = None) -> str:
    """Repackage an HWPX from its unpacked working directory."""
    work = Path(work_dir)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    # Collect all files in work_dir (excluding mimetype and .bak)
    all_work_files: set[str] = set()
    for root, dirs, files in os.walk(work):
        for f in files:
            if f == "mimetype" or f.endswith(".bak"):
                continue
            fpath = os.path.join(root, f)
            arcname = os.path.relpath(fpath, work).replace(os.sep, "/")
            all_work_files.add(arcname)

    if reference_zip:
        _compile_with_reference(work, out, reference_zip, all_work_files)
    else:
        _compile_default(work, out, all_work_files)

    # Validate
    with zipfile.ZipFile(out, 'r') as zf:
        names = zf.namelist()
        if names and names[0] != "mimetype":
            print("Warning: mimetype is not the first entry in the archive", file=sys.stderr)

    size = out.stat().st_size
    print(f"Compiled: {out} ({size:,} bytes)", file=sys.stderr)
    return str(out)


def _compile_with_reference(work: Path, out: Path, reference_zip: str, all_work_files: set[str]) -> None:
    """Compile preserving the reference ZIP's file order and compression types."""
    ref_zip = zipfile.ZipFile(reference_zip)
    ref_entries = [(info.filename, info.compress_type) for info in ref_zip.infolist()]

    added: set[str] = set()
    with zipfile.ZipFile(out, 'w') as zf:
        # 1. mimetype first, stored
        mimetype_path = work / "mimetype"
        if mimetype_path.exists():
            zf.write(str(mimetype_path), "mimetype", compress_type=zipfile.ZIP_STORED)
            added.add("mimetype")

        # 2. Files from reference in original order with original compression
        for filename, compress_type in ref_entries:
            if filename == "mimetype":
                continue
            file_path = work / filename
            if file_path.exists():
                zf.write(str(file_path), filename, compress_type=compress_type)
            else:
                # Fall back to original content
                data = ref_zip.read(filename)
                info = zipfile.ZipInfo(filename)
                info.compress_type = compress_type
                zf.writestr(info, data)
            added.add(filename)

        # 3. New files not in reference (BinData images etc.)
        for arcname in sorted(all_work_files - added):
            file_path = work / arcname
            zf.write(str(file_path), arcname, compress_type=zipfile.ZIP_DEFLATED)

    ref_zip.close()


def _compile_default(work: Path, out: Path, all_work_files: set[str]) -> None:
    """Compile with default ordering (mimetype first, rest alphabetical, all deflated)."""
    with zipfile.ZipFile(out, 'w') as zf:
        # mimetype MUST be first and uncompressed
        mimetype_path = work / "mimetype"
        if mimetype_path.exists():
            zf.write(str(mimetype_path), "mimetype", compress_type=zipfile.ZIP_STORED)
        else:
            print("Warning: mimetype file not found", file=sys.stderr)

        # All other files with compression
        for root, dirs, files in os.walk(work):
            dirs.sort()
            for file in sorted(files):
                if file == "mimetype" or file.endswith(".bak"):
                    continue
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, work)
                zf.write(file_path, arcname, compress_type=zipfile.ZIP_DEFLATED)


def main():
    if len(sys.argv) < 3:
        print("Usage: python compile_hwpx.py <work_dir> <output.hwpx> [--reference <original.hwpx>]",
              file=sys.stderr)
        sys.exit(1)

    work_dir = sys.argv[1]
    output_path = sys.argv[2]
    reference_zip = None

    if "--reference" in sys.argv:
        idx = sys.argv.index("--reference")
        if idx + 1 < len(sys.argv):
            reference_zip = sys.argv[idx + 1]
        else:
            print("Error: --reference requires a path argument", file=sys.stderr)
            sys.exit(1)

    if not Path(work_dir).is_dir():
        print(f"Error: Not a directory: {work_dir}", file=sys.stderr)
        sys.exit(1)

    compile_hwpx(work_dir, output_path, reference_zip)


if __name__ == "__main__":
    main()
