"""Eval Cal Node error types."""


class CalNodeError(Exception):
    """Base exception for Eval Cal Node."""
    pass


class SchemaValidationError(CalNodeError):
    """Raised when data fails schema validation."""
    pass


class RecordIdMismatchError(CalNodeError):
    """Raised when computed record_id does not match input."""
    pass


class DuplicateRecordError(CalNodeError):
    """Raised when a record with the same record_id already exists."""
    pass


class ConfigError(CalNodeError):
    """Raised when config loading or validation fails."""
    pass


class RevisionError(CalNodeError):
    """Raised when record revision is incompatible with node revision."""
    pass
