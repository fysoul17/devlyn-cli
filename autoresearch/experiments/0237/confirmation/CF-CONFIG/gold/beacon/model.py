from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Resolved:
    values: dict
    dependencies: tuple[Path, ...]

@dataclass(frozen=True)
class Snapshot:
    generation: int
    values: dict
    dependencies: tuple[Path, ...]
