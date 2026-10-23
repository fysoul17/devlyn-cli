Small operational fix in autoresearch/experiments/0257/driver.py (devlyn-cli). Work only under autoresearch/experiments/0257/. Do not commit; no Docker, models, credentials or runtime files.

Observed failure (twice, 2026-10-23): the host disk dipped below 1 GB, Docker Desktop's daemon went down, and `Driver.image()` ran `subprocess.run(['docker','load','-i',tarball], check=True)`, which raised CalledProcessError and killed the driver (rc=1). Docker came back by itself within minutes, but the run stayed stopped. No cell was running either time (preflight was already refusing on the 8 GB disk floor).

Fix: an unavailable Docker daemon is a hold, not a crash. In `image()`, when `docker load` fails, log `hold` with reason `docker load failed: <first line of stderr>` and return False (the run loop already sleeps 60 s and retries). Keep raising on 'image identity mismatch after docker load' (a real apparatus failure). Do not add other machinery. Add one focused test in test_apparatus.py (docker load fails → ready returns False with that hold event, driver keeps running). Update README.md's driver row only if it lists hold reasons. No amendment file is needed: holds are operations (DESIGN §Operations), not a protocol change. Mention it in the commit-ready summary.

Run `python3 -m pytest -q autoresearch/experiments/0257` and report the count.
