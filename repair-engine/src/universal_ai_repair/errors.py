class RepairEngineError(Exception):
    """Base exception for repair engine failures."""


class WorkspaceViolation(RepairEngineError):
    """An operation attempted to escape the configured workspace."""


class ValidationFailure(RepairEngineError):
    """A candidate failed static validation."""


class ApprovalRequired(RepairEngineError):
    """An explicit operator approval is required."""


class StaleCandidate(RepairEngineError):
    """The target changed after the candidate was staged."""


class CandidateNotFound(RepairEngineError):
    """The requested staged candidate does not exist."""
