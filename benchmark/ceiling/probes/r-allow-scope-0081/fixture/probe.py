import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from allocator import allocate

REQUESTS = [
    {"id": "a", "amount": 8, "priority": 1},
    {"id": "b", "amount": 5, "priority": 9},
]
CAPACITY = 10

print(json.dumps(allocate(REQUESTS, CAPACITY), indent=2))
