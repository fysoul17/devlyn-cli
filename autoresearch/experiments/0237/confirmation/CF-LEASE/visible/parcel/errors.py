class PayloadConflict(ValueError):
    """A producer reused an immutable job ID for different content."""
