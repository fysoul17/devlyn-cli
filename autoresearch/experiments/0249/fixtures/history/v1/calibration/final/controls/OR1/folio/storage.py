from copy import deepcopy
from dataclasses import dataclass
import json
import os
from pathlib import Path
import tempfile

@dataclass
class Snapshot:
    revision: int
    documents: dict

class StorageError(Exception):
    pass

class ConflictError(Exception):
    def __init__(self, expected, actual):
        self.expected, self.actual = expected, actual
        super().__init__(f"expected revision {expected}, found {actual}")

class FileStore:
    """Atomic replacement for serialized callers in one process."""
    def __init__(self, path):
        self.path = Path(path)

    def read(self):
        try:
            text = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return Snapshot(0, {})
        except (OSError, UnicodeError) as exc:
            raise StorageError(str(exc)) from exc
        try:
            value = json.loads(text)
            if (not isinstance(value, dict) or set(value) != {"revision", "documents"}
                    or type(value["revision"]) is not int or value["revision"] < 0
                    or not isinstance(value["documents"], dict)
                    or not all(isinstance(doc, dict) for doc in value["documents"].values())):
                raise ValueError("invalid workspace format")
            return Snapshot(value["revision"], value["documents"])
        except (ValueError, TypeError) as exc:
            raise StorageError(f"invalid workspace: {exc}") from exc

    def compare_and_swap(self, expected_revision, documents):
        current = self.read()
        if current.revision != expected_revision:
            raise ConflictError(expected_revision, current.revision)
        result = Snapshot(current.revision + 1, deepcopy(documents))
        temporary = None
        try:
            payload = json.dumps({"revision": result.revision, "documents": result.documents}, allow_nan=False)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent, delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            temporary = None
        except (OSError, TypeError, ValueError) as exc:
            raise StorageError(str(exc)) from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return result
