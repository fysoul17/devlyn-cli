"""Use rp-d1's offline sealed-evidence reevaluator with the rp-d2 slot census."""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('summary_rpd2_reevaluate', HERE / 'summarize.py')
summary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(summary)
legacy = summary.runner.load('reevaluate_rpd1_rpd2', summary.runner.PRIOR / 'reevaluate.py')
legacy.summary = summary
reevaluate, census, main = legacy.reevaluate, legacy.census, legacy.main


if __name__ == '__main__':
    raise SystemExit(main())
