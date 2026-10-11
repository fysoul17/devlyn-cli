"""A local worker integration example. Run from the repository root."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from parcel import Store, enqueue, process_one

with Store(':memory:') as store:
    enqueue(store, 'document-17', {'destination': 'archive', 'bytes': 128}, 0)
    result = process_one(store, 'demo-worker', print, lambda: 1)
    print(result.state)
