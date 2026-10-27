All three round-2 findings are resolved:

- **Two-app/path-alias:** request errors, invalid stored JSON, thrown exceptions, unhandled rejections and cleanup failures return **2**. Missing acknowledged items return **1**; complete writes return **0**.
- **File-shape witness:** accepts a first positional file parameter followed by options or rest parameters, including defaults. Exported `app` retains precedence.
- **blind.py:** excludes bare `set` in the specified command forms while retaining results for `set -e`, `set -o pipefail` and `set -euo pipefail`.

No new HIGH or MEDIUM findings in the reviewed scope.

Write-free verification passed: 16 exit-mapping controls, 25 file-shape tests, 17 transcript controls and all seven pinned witness hashes. README notes match the fixes. Full suites were not rerun; the supplied totals remain user-reported. No files edited.

VERDICT: SHIP
