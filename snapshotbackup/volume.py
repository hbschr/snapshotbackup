import logging
import os

from .exceptions import BackupDirError, BackupDirNotFoundError, LockedError
from .subprocess import create_subvolume, delete_subvolume, is_btrfs, make_snapshot

logger = logging.getLogger(__name__)

_sync_dir = '.sync'
_sync_lockfile = '.sync_lock'


class BaseVolume(object):
    """some basic tools for backup volumes."""

    path: str
    """absolute path to this volume"""

    sync_path: str
    """absolute path to this volume's sync dir"""

    def __init__(self, path):
        """

        :param str path:
        """
        self.path = os.path.abspath(path)
        self.sync_path = self._path_join(_sync_dir)

    def _path_join(self, path):
        """get path relative to this volume.

        :param str path: relative or absolute path, see :func:`os.path.join`
        :raise RuntimeError: when resulting path is not inside this volume
        :return str: absolute path

        >>> from snapshotbackup.volume import BaseVolume
        >>> vol = BaseVolume('/foo/bar')
        >>> vol._path_join('baz')
        '/foo/bar/baz'
        >>> vol._path_join('/foo/bar/baz')
        '/foo/bar/baz'
        >>> vol._path_join('/elsewhere/baz')
        Traceback (most recent call last):
        RuntimeError: ...
        >>> vol._path_join('../bar/baz')
        '/foo/bar/baz'
        >>> vol._path_join('../elsewhere/baz')
        Traceback (most recent call last):
        RuntimeError: ...
        """
        joined_path = os.path.normpath(os.path.join(self.path, path))
        if not os.path.commonpath((self.path, joined_path)) == self.path:
            raise RuntimeError(f'invalid path, join {self.path} with {path}')
        return joined_path

    def assure_path(self):
        """assert this volume's path exists and is dir.

        :raise BackupDirNotFoundError: when this volume's path doesn't exist
        :raise BackupDirError: when this volume's path isn't a directory
        :return: None

        >>> import os, tempfile
        >>> from snapshotbackup.volume import BaseVolume
        >>> with tempfile.TemporaryDirectory() as path:
        ...     BaseVolume(path).assure_path()
        ...     BaseVolume(os.path.join(path, 'nope')).assure_path()
        Traceback (most recent call last):
        snapshotbackup.exceptions.BackupDirNotFoundError: ...
        >>> with tempfile.TemporaryDirectory() as path:
        ...     not_a_dir = os.path.join(path, 'not_a_dir')
        ...     open(not_a_dir, 'w').close()
        ...     BaseVolume(not_a_dir).assure_path()
        Traceback (most recent call last):
        snapshotbackup.exceptions.BackupDirError: not a directory ...
        """
        if not os.path.exists(self.path):
            raise BackupDirNotFoundError(self.path)
        if not os.path.isdir(self.path):
            raise BackupDirError(f'not a directory {self.path}', self.path)

    def assure_writable(self):
        """assert write access on this volume. checks from :func:`assure_path` are also performed.

        :raise BackupDirError: when write access on volume is not given
        :return: None

        >>> import os, stat, tempfile
        >>> from unittest.mock import Mock
        >>> from snapshotbackup.volume import BaseVolume
        >>> with tempfile.TemporaryDirectory() as path:
        ...     BaseVolume(path).assure_writable()
        ...     os.chmod(path, stat.S_IRUSR)
        ...     BaseVolume(path).assure_writable()
        Traceback (most recent call last):
        snapshotbackup.exceptions.BackupDirError: not writable ...
        >>> with tempfile.TemporaryDirectory() as path:
        ...     vol = BaseVolume(path)
        ...     vol.assure_path = Mock()
        ...     vol.assure_writable()
        ...     vol.assure_path.assert_called_once()
        """
        self.assure_path()
        if not os.access(self.path, os.W_OK):
            raise BackupDirError(f'not writable {self.path}', self.path)

    def lock(self):
        """lock sync dir.

        :return object: a :class:`snapshotbackup.volume.Lock` context

        >>> import tempfile
        >>> from snapshotbackup.volume import BaseVolume
        >>> with tempfile.TemporaryDirectory() as path:
        ...     vol = BaseVolume(path)
        ...     with vol.lock():
        ...         with vol.lock():
        ...             pass
        Traceback (most recent call last):
        snapshotbackup.exceptions.LockedError: ...
        """
        return Lock(self._path_join(_sync_lockfile))

    def setup(self):
        """create directory for this volume, do nothing if directory already exists.

        :return: None

        >>> import tempfile
        >>> from snapshotbackup.volume import BaseVolume
        >>> with tempfile.TemporaryDirectory() as path:
        ...     vol = BaseVolume(os.path.join(path, 'long', 'path'))
        ...     assert not os.path.isdir(vol.path)
        ...     vol.setup()
        ...     assert os.path.isdir(vol.path)
        >>> with tempfile.TemporaryDirectory() as path:
        ...     BaseVolume(path).setup()
        """
        os.makedirs(self.path, exist_ok=True)


class BtrfsVolume(BaseVolume):
    """represents a path on a btrfs volume.
    provides functions to interact with btrfs relative to given base dir.
    """

    def _assure_btrfs(self):
        """assert this volume is on a btrfs filesystem.

        :raise BackupDirError: general error with meaningful message
        :return: None
        """
        if not is_btrfs(self.path):
            raise BackupDirError(f'not a btrfs {self.path}', self.path)

    def create_subvolume(self, name):
        """create subvolume `name` in this volume.

        :param str name:
        :return: None
        """
        self._assure_btrfs()
        create_subvolume(self._path_join(name))

    def delete_subvolume(self, name):
        """delete subvolume `name` in this volume.

        :param str name:
        :return: None
        """
        self._assure_btrfs()
        delete_subvolume(self._path_join(name))

    def make_snapshot(self, source, target, readonly=True):
        """make snapshot `target` in this volume from `source` in this volume.

        :param str source:
        :param str target:
        :param bool readonly: snapshot will be readonly
        :return: None
        """
        self._assure_btrfs()
        make_snapshot(self._path_join(source), self._path_join(target), readonly=readonly)


class Lock(object):
    """lockfile as context manager.

    :raise LockedError: when lockfile already exists
    :raise FileNotFoundError: when lockfile cannot be created (missing dir) or lockfile couldn't be removed
    :raise OSError: others may occur

    >>> import tempfile
    >>> import os
    >>> from snapshotbackup.volume import Lock
    >>> with tempfile.TemporaryDirectory() as path:
    ...     with Lock(os.path.join(path, 'lock')):
    ...         pass
    ...     with Lock(os.path.join(path, 'lock')):
    ...         pass
    >>> with tempfile.TemporaryDirectory() as path:
    ...     with Lock(os.path.join(path, 'lock')):
    ...         with Lock(os.path.join(path, 'lock')):
    ...             pass
    Traceback (most recent call last):
    snapshotbackup.exceptions.LockedError: ...
    >>> with tempfile.TemporaryDirectory() as path:
    ...     with Lock(os.path.join(path, 'nope', 'lock')):
    ...         pass
    Traceback (most recent call last):
    FileNotFoundError: ...
    >>> with tempfile.TemporaryDirectory() as path:
    ...     with Lock(os.path.join(path, 'lock')):
    ...         os.remove(os.path.join(path, 'lock'))
    Traceback (most recent call last):
    FileNotFoundError: ...
    """

    _lockfile: str
    """full path to the lockfile"""

    def __init__(self, lockfile):
        """initialize lock

        :param str lockfile: path to lockfile
        """
        self._lockfile = os.path.abspath(lockfile)

    def __enter__(self):
        """enter locked context: create lockfile or throw error"""
        if os.path.isfile(self._lockfile):
            raise LockedError(self._lockfile)
        open(self._lockfile, 'w').close()

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """exit locked context: remove lockfile"""
        os.remove(self._lockfile)
