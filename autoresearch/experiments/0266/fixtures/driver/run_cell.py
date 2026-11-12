"""Fake 0266 run_cell for test_driver.py: only what driver.py uses, with no Docker, keychain or network.
The values are the common brief's contract; test_driver.py checks the real run_cell.py against them."""
import hashlib
import json
from pathlib import Path
import types
import urllib.request  # noqa: F401  driver.credential reaches the profile endpoint through cell.urllib

MIN_TOKEN_SECONDS = 2700 + 900
HEADROOM_BYTES = 16 * 2**30
base = types.SimpleNamespace(fingerprint=lambda value: hashlib.sha256(value.encode()).hexdigest()[:12])


def selected(runtime):
    """prepare.selected's contract: the registered C's candidate from a GO screen decision, else ValueError."""
    path = Path(runtime['output']).parent / 'screen-decision.json'
    decision = json.loads(path.read_text()) if path.is_file() else {}
    if decision.get('decision') != 'GO':
        raise ValueError(f'the screen decision is {decision.get("decision")}, not GO with a candidate: no registered run')
    return decision['candidate']


prepare = types.SimpleNamespace(selected=selected)


def claude_limits(runtime, access_token=None):
    raise AssertionError('a driver test must fake the usage endpoint')


def image_identity(runtime):
    return True


def run(runtime_path, name, task, column, config, *, expected_account=None):
    raise AssertionError('a driver test must fake the cell')


def regrade(runtime_path, name, *, expected_account=None):
    raise AssertionError('a driver test must fake the regrade')
