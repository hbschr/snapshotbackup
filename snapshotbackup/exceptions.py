class Error(Exception):
    """Base class for `snapshotbackup` exceptions."""

    def __init__(self, message):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return self.message


class BackupDirError(Error):
    """backup directory related error with meaningful message.

    >>> from snapshotbackup.exceptions import BackupDirError
    >>> raise BackupDirError('something wrong with /test', '/test')
    Traceback (most recent call last):
    snapshotbackup.exceptions.BackupDirError: ...
    """
    path: str

    def __init__(self, message, path):
        super().__init__(message)
        self.path = path


class CommandNotFoundError(Error):
    """127 - command not found"""
    command: str

    def __init__(self, command):
        super().__init__(f'Command not found: {command}')
        self.command = command


class LockedError(Error):
    lockfile: str

    def __init__(self, lockfile):
        super().__init__(f'cannot lock, `{lockfile}` already exists')
        self.lockfile = lockfile


class LockPathError(Error):
    path: str

    def __init__(self, path):
        super().__init__(f'cannot create lock, `{path}` not found')
        self.path = path


class TimestampParseError(Error):
    error: Exception

    def __init__(self, message, error=None):
        """wrapper for several timestamp parsing related errors.

        :param str message: string representation of this error
        :param Exception error: error thrown from imported timestamp parser
        """
        super().__init__(message)
        self.error = error


class SyncFailedError(Error):
    """sync interrupted"""
    target: str

    def __init__(self, target):
        super().__init__(f'Sync interrupted: `{target}`')
        self.target = target
