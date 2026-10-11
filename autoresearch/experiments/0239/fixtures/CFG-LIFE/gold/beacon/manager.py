from copy import deepcopy
from .loader import Loader
from .model import Snapshot

class ConfigManager:
    def __init__(self, path, loader=None):
        self.path = path
        self.loader = loader if loader is not None else Loader()
        self._current = None

    @property
    def current(self):
        return deepcopy(self._current)

    def reload(self):
        resolved = self.loader.load(self.path)
        generation = 1 if self._current is None else self._current.generation
        if self._current is not None and resolved.values != self._current.values:
            generation += 1
        self._current = Snapshot(generation, deepcopy(resolved.values), resolved.dependencies)
        return self.current
