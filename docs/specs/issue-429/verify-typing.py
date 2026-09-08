"""Require a precise Pyright rejection while valid serializer calls remain clean."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SOURCE = (Path.cwd() / "src").resolve()
assert (SOURCE / "itsdangerous" / "__init__.py").is_file()
VALID = """from itsdangerous import URLSafeSerializer, URLSafeTimedSerializer

plain = URLSafeSerializer("SECRET")
plain_token = plain.dumps("value", salt="other")
plain.loads(plain_token)
plain.loads(plain_token, salt="other")
plain.loads_unsafe(plain_token, salt="other")
timed = URLSafeTimedSerializer("SECRET")
timed_token = timed.dumps("value", salt="other")
timed.loads(timed_token)
timed.loads(timed_token, max_age=60, salt="other")
timed.loads(timed_token, max_age=60, return_timestamp=True, salt="other")
timed.loads_unsafe(timed_token, max_age=60, salt="other")
"""
INVALID = """from itsdangerous import URLSafeSerializer
serializer = URLSafeSerializer("SECRET")
signed = serializer.dumps("value")
serializer.loads(signed, max_age=-1)
"""


def main():
    with tempfile.TemporaryDirectory(prefix="itsdangerous-issue-429-") as temporary:
        directory = Path(temporary)
        valid = directory / "valid.py"
        invalid = directory / "invalid.py"
        valid.write_text(VALID, encoding="utf-8")
        invalid.write_text(INVALID, encoding="utf-8")
        config = directory / "pyrightconfig.json"
        version = f"{sys.version_info.major}.{sys.version_info.minor}"
        config.write_text(
            json.dumps(
                {
                    "include": [valid.name, invalid.name],
                    "extraPaths": [str(SOURCE)],
                    "typeCheckingMode": "standard",
                    "pythonVersion": version,
                }
            ),
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pyright",
                "--pythonpath",
                sys.executable,
                "--project",
                str(config),
                "--outputjson",
            ],
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
        print(result.stdout, end="")
        print(result.stderr, end="", file=sys.stderr)
        report = json.loads(result.stdout)
        diagnostics = report["generalDiagnostics"]
        if result.returncode != 1 or len(diagnostics) != 1:
            raise SystemExit("Expected exactly one error on the invalid max_age call.")
        error = diagnostics[0]
        location = error["range"]
        keyword_column = INVALID.splitlines()[3].index("max_age")
        if not (
            Path(error["file"]).resolve() == invalid.resolve()
            and error["severity"] == "error"
            and error.get("rule") == "reportCallIssue"
            and location["start"]["line"] == location["end"]["line"] == 3
            and location["start"]["character"] <= keyword_column
            and location["end"]["character"] >= keyword_column + len("max_age")
            and "max_age" in error["message"]
        ):
            raise SystemExit(
                "The diagnostic does not identify the invalid max_age keyword."
            )
        print("Typing contract passed: invalid max_age rejected; valid calls clean.")


if __name__ == "__main__":
    main()
