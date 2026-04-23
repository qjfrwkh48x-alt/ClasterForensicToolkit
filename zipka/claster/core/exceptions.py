"""
Custom exception hierarchy for the Claster Forensic Toolkit.
All exceptions should inherit from ClasterError to allow unified handling.
"""

class ClasterError(Exception):
    """Base class for all Claster exceptions."""
    def __init__(self, message: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self):
        if self.details:
            return f"{self.message} (Details: {self.details})"
        return self.message

class ClasterCoreError(ClasterError):
    """Exceptions raised by the core module."""
    pass

class ConfigurationError(ClasterCoreError):
    """Raised when configuration is invalid or missing."""
    pass

class DatabaseError(ClasterCoreError):
    """Raised when database operations fail."""
    pass

class FileSystemError(ClasterCoreError):
    """Raised when file system operations fail (e.g., permissions, I/O)."""
    pass

class HashingError(ClasterCoreError):
    """Raised when hashing fails."""
    pass

class PrivilegeError(ClasterCoreError):
    """Raised when insufficient privileges for an operation."""
    pass

class EventLogError(ClasterCoreError):
    """Raised when parsing Windows Event Logs fails."""
    pass

class PluginError(ClasterCoreError):
    """Raised when plugin loading or execution fails."""
    pass