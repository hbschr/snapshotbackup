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
    """127 - command not found

    >>> from snapshotbackup.exceptions import CommandNotFoundError
    >>> raise CommandNotFoundError('rsync')
    Traceback (most recent call last):
    snapshotbackup.exceptions.CommandNotFoundError: ...
    """
    command: str

    def __init__(self, command):
        super().__init__(f'Command not found: {command}')
        self.command = command


class LockedError(Error):
    """already locked.

    >>> from snapshotbackup.exceptions import LockedError
    >>> raise LockedError('/path/to/lockfile')
    Traceback (most recent call last):
    snapshotbackup.exceptions.LockedError: ...
    """
    lockfile: str

    def __init__(self, lockfile):
        super().__init__(f'cannot lock, `{lockfile}` already exists')
        self.lockfile = lockfile


class TimestampParseError(Error):
    """wrapper for several timestamp parsing related errors.

    >>> from snapshotbackup.exceptions import TimestampParseError
    >>> raise TimestampParseError('meaningful mesage', error='original exception')
    Traceback (most recent call last):
    snapshotbackup.exceptions.TimestampParseError: ...
    """
    error: Exception

    def __init__(self, message, error=None):
        """

        :param str message: string representation of this error
        :param Exception error: error thrown from imported timestamp parser
        """
        super().__init__(message)
        self.error = error


class SyncFailedError(Error):
    """sync interrupted.

    >>> from snapshotbackup.exceptions import SyncFailedError
    >>> raise SyncFailedError('/path/to/sync target')
    Traceback (most recent call last):
    snapshotbackup.exceptions.SyncFailedError: ...
    """
    target: str

    def __init__(self, target):
        super().__init__(f'Sync interrupted: `{target}`')
        self.target = target
