"""Domain-oriented errors raised across ports without binding to infrastructure."""


class PersistencyUnavailableError(RuntimeError):
    """Raised when persistence cannot complete (migration, outage, misconfiguration)."""
