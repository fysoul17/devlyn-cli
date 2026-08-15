"""Run the visible parser smoke checks."""

import pathlib
import runpy


if __name__ == "__main__":
    runpy.run_path(str(pathlib.Path(__file__).with_name("parser_preview_test.py")), run_name="__main__")
