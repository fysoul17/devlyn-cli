import json

def encode(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)

def decode(value: str) -> object:
    return json.loads(value)
