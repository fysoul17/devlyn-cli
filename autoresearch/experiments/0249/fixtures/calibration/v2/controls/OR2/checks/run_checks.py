import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(Path(__file__).parent), pattern="test_*.py"))
print(json.dumps({"public_passed": result.wasSuccessful(), "tests": result.testsRun}))
raise SystemExit(0 if result.wasSuccessful() else 1)
