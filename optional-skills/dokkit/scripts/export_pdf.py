#!/usr/bin/env python3
"""Export a document to PDF using LibreOffice.

Usage:
    python export_pdf.py <input_file> <output.pdf>

Requires:
    LibreOffice installed and 'soffice' in PATH.
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def find_soffice() -> str:
    """Find the LibreOffice soffice executable."""
    # Check PATH
    soffice = shutil.which("soffice")
    if soffice:
        return soffice

    # Common locations
    candidates = [
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        "/usr/bin/soffice",
        "/usr/local/bin/soffice",
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    ]
    for path in candidates:
        if Path(path).exists():
            return path

    return ""


def export_pdf(input_file: str, output_file: str) -> str:
    """Convert a document to PDF using LibreOffice."""
    soffice = find_soffice()
    if not soffice:
        print("Error: LibreOffice not found. Install it or add 'soffice' to PATH.",
              file=sys.stderr)
        sys.exit(1)

    input_path = Path(input_file).resolve()
    output_path = Path(output_file).resolve()

    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    # Use a temp directory for LibreOffice output
    with tempfile.TemporaryDirectory() as tmpdir:
        cmd = [
            soffice,
            "--headless",
            "--convert-to", "pdf",
            "--outdir", tmpdir,
            str(input_path),
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            print("Error: LibreOffice conversion timed out", file=sys.stderr)
            sys.exit(1)

        if result.returncode != 0:
            print(f"Error: LibreOffice conversion failed: {result.stderr}", file=sys.stderr)
            sys.exit(1)

        # Find the generated PDF
        pdf_files = list(Path(tmpdir).glob("*.pdf"))
        if not pdf_files:
            print("Error: No PDF file generated", file=sys.stderr)
            sys.exit(1)

        # Move to output location
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(pdf_files[0]), str(output_path))

    size = output_path.stat().st_size
    print(f"Exported: {output_path} ({size:,} bytes)", file=sys.stderr)
    return str(output_path)


def main():
    if len(sys.argv) != 3:
        print("Usage: python export_pdf.py <input_file> <output.pdf>", file=sys.stderr)
        sys.exit(1)

    export_pdf(sys.argv[1], sys.argv[2])


if __name__ == "__main__":
    main()
