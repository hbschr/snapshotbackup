class Error(Exception):
    """Base class for `snapshotbackup` exceptions."""

    def __init__(self, msg=''):
        self.message = msg
        Exception.__init__(self, msg)

    def __str__(self):
        return self.message


class BackupDirError(Error):
    """backup directory is no directory. run setup.

    >>> raise BackupDirError('/test')
    Traceback (most recent call last):
    snapshotbackup.exceptions.BackupDirError: ...
    """
    dir: str

    def __init__(self, dir):
        super().__init__(f'BackupDirError: `{dir}`')
        self.dir = dir


class CommandNotFoundError(Exception):
    """127 - command not found"""
    command: str

    def __init__(self, command):
        self.command = command

    def __str__(self):
        return f'Command not found: `{self.command}`'


class LockedError(Exception):
    lockfile: str

    def __init__(self, lockfile):
        self.lockfile = lockfile

    def __str__(self):
        return f'LockedError: cannot lock, `{self.lockfile}` already exists'


class LockPathError(Exception):
    path: str

    def __init__(self, path):
        self.path = path

    def __str__(self):
        return f'LockPathError: cannot create lock, `{self.path}` not found'


class TimestampParseError(Exception):
    def __init__(self, message, error=None):
        super().__init__(message)
        self.error = error

    def __str__(self):
        return f'TimestampParseError: {self.error}'


class SyncFailedError(Exception):
    """sync interrupted"""
    target: str

    def __init__(self, target):
        self.target = target

    def __str__(self):
        return f'Sync interrupted: `{self.target}`'
