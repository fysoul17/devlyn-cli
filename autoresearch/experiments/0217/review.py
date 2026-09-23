"""Request one independent Fable review of /work. Takes no arguments; help or unknown arguments never dispatch."""
import argparse
import runpy

argparse.ArgumentParser(description=__doc__).parse_args()
runpy.run_path('/control/review-0210.py', run_name='__main__')
