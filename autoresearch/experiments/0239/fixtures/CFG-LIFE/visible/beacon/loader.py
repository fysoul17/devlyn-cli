from .document import read_document
from .errors import ConfigError
from .merge import merge
from .model import Resolved
from .paths import canonical

class Loader:
    def __init__(self):
        self._cache = {}

    def load(self, path):
        seen = set()
        dependencies = set()

        def visit(path, chain):
            dependencies.add(path)
            if path in self._cache:
                cached = self._cache[path]
                dependencies.update(cached.dependencies)
                return cached.values
            if path in seen:
                raise ConfigError(path, chain, 'include cycle')
            seen.add(path)
            includes, local = read_document(path, chain)
            values = {}
            for include in includes:
                child = canonical(include, path.parent)
                values = merge(values, visit(child, chain + (child,)))
            values = merge(values, local)
            self._cache[path] = Resolved(values, tuple(sorted(dependencies, key=str)))
            return values

        root = canonical(path)
        values = visit(root, (root,))
        return Resolved(values, tuple(sorted(dependencies, key=str)))
