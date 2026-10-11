class ConfigError(ValueError):
    def __init__(self, path, chain, reason):
        self.path = path
        self.chain = tuple(chain)
        self.reason = reason
        super().__init__(f"{reason}: {' -> '.join(str(item) for item in self.chain)}")
