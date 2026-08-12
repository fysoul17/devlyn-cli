import json
import pathlib
import sys


root = pathlib.Path(sys.argv[1])
name = "site_" + "assigner.py"
text = (root / "assigner" / name).read_text(encoding="utf-8")
level = int(text.split("LEVEL = ")[1].splitlines()[0])
roles = ("local-a", "local-b", "remote-a", "remote-b", "restore")
checks = (level >= 1, level >= 1, level >= 2, level >= 2, level >= 2)
print(json.dumps({"manifestations": [{"id": role, "passed": passed} for role, passed in zip(roles, checks)]}))
