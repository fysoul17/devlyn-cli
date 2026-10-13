"""Parse a nonnegative result limit."""
import argparse


def parse_limit(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int)
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit < 0:
        parser.error("--limit must be nonnegative")
    return args.limit or 10
