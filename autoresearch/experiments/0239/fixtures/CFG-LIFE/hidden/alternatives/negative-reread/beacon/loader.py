from copy import deepcopy
from .document import read_document
from .errors import ConfigError
from .merge import merge
from .model import Resolved
from .paths import canonical

class Loader:
    def load(self, path):
        dependencies = set()

        def visit(path, chain):
            dependencies.add(path)
            if path in chain[:-1]:
                raise ConfigError(path, chain, 'include cycle')
            includes, local = read_document(path, chain)
            values = {}
            for include in includes:
                child = canonical(include, path.parent)
                values = merge(values, visit(child, chain + (child,)))
            values = merge(values, local)
            return values

        root = canonical(path)
        values = visit(root, (root,))
        return Resolved(deepcopy(values), tuple(sorted(dependencies, key=str)))
