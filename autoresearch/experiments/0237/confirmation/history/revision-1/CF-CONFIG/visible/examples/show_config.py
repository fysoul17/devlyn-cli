"""Supervisor-style caller; run from the repository root."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from beacon import ConfigManager, ConfigError

manager = ConfigManager(Path(__file__).parent / 'config' / 'app.json')
try:
    current = manager.reload()
except ConfigError as exc:
    print(f'reload rejected: {exc}', file=sys.stderr)
    raise SystemExit(1)
print(json.dumps({'generation': current.generation, 'settings': current.values}, sort_keys=True))
