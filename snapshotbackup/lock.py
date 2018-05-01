from os import remove
from os.path import dirname, join


_lockfilename = '.sync_lock'


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


class Lock(object):
    """lockfile as context manager

    :raise LockedError: when lockfile already exists
    :raise LockPathError: when lockfile cannot be created (missing dir)

    >>> import tempfile
    >>> from os.path import join
    >>> from snapshotbackup import Lock, LockedError
    >>> with tempfile.TemporaryDirectory() as path:
    ...     with Lock(path):
    ...         pass
    >>> with tempfile.TemporaryDirectory() as path:
    ...     with Lock(path):
    ...         try:
    ...             with Lock(path):
    ...                 pass
    ...         except LockedError as e:
    ...             print(e)
    LockedError: ...
    >>> with tempfile.TemporaryDirectory() as path:
    ...     with Lock(join(path, 'nope')):
    ...         pass
    Traceback (most recent call last):
    snapshotbackup.lock.LockPathError: ...
    """

    _lockfile: str
    """full path to the lockfile"""

    def __init__(self, path):
        """initialize lock

        :param path str: path where lockfile shall be created
        """
        self._lockfile = join(path, _lockfilename)

    def __enter__(self):
        """enter locked context

        :raise LockedError: when already locked
        :raise LockPathError: when path of lockfile is not found
        :raise OSError: others may occur
        """
        try:
            open(self._lockfile, 'r').close()
            raise LockedError(self._lockfile)
        except FileNotFoundError as e:
            pass

        try:
            open(self._lockfile, 'w').close()
        except FileNotFoundError as e:
            raise LockPathError(dirname(self._lockfile))

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """exit locked context, lockfile will be removed"""
        remove(self._lockfile)
