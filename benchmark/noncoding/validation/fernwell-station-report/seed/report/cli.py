"""Print the Fernwell station report.

    python3 -m report.cli               # text, the default
    python3 -m report.cli --format text
"""

import argparse
import sys

from report.loader import load_summaries
from report.renderer_text import render_text


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="report", description="Summarise bike-share trips per station."
    )
    parser.add_argument(
        "--format",
        default="text",
        choices=["text"],
        help="output format (default: text)",
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    rows = load_summaries()
    sys.stdout.write(render_text(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
