"""Custom exceptions for the generation pipeline."""


class PauseGeneration(Exception):
    """Raised when the generation should pause (all providers failed for a phase).

    Carries the session snapshot so the API layer can serialize it for resume.
    """

    def __init__(
        self, reason: str, phase_number: int, phase_name: str,
        session_snapshot: dict | None = None,
    ):
        self.reason = reason
        self.phase_number = phase_number
        self.phase_name = phase_name
        self.session_snapshot = session_snapshot or {}
        super().__init__(reason)


class NexusRateLimitError(Exception):
    pass


class NexusServerError(Exception):
    pass


class NexusExhaustedError(Exception):
    """All retry attempts for a Nexus API call failed."""
    pass
