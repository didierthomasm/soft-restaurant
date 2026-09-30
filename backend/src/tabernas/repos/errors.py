class NotFoundError(LookupError):
    """Requested record does not exist. The API maps it to 404."""


class ConflictError(RuntimeError):
    """Record clashes with existing data (duplicates, overlapping ranges). Maps to 409."""
