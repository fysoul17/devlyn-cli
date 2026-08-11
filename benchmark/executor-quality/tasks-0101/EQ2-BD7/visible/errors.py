class UnknownFlagError(LookupError):
    def __init__(self, flag_key: str, environment: str) -> None:
        super().__init__(f"Unknown flag {flag_key!r} in {environment!r}")
        self.flag_key = flag_key
        self.environment = environment
