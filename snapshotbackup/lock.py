from os import remove
from os.path import join


_lockfilename = '.sync_lock'


class LockError(Exception):
    lockfile: str

    def __init__(self, lockfile):
        self.lockfile = lockfile
        self.message = f'cannot lock, `{self.lockfile}` already exists'

    def __str__(self):
        return f'LockError: {self.message}'


class Lock(object):
    """lockfile as context manager

    :raise LockError: when lockfile already exists

    >>> import tempfile
    >>> from snapshotbackup import Lock, LockError
    >>> with tempfile.TemporaryDirectory() as path:
    ...     with Lock(path):
    ...         pass
    >>> with tempfile.TemporaryDirectory() as path:
    ...     with Lock(path):
    ...         try:
    ...             with Lock(path):
    ...                 pass
    ...         except LockError as e:
    ...             print(e)
    LockError: ...
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

        :raise LockError: when already locked
        """
        if self._is_locked():
            raise LockError(self._lockfile)
        open(self._lockfile, 'w').close()

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """exit locked context, lockfile will be removed"""
        remove(self._lockfile)

    def _is_locked(self):
        """checks if lockfile already exists

        :return bool:
        """
        try:
            open(self._lockfile, 'r').close()
            return True
        except FileNotFoundError as e:
            return False
