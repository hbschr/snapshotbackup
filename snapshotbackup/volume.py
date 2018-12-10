import os

from .exceptions import BackupDirError, BackupDirNotFoundError, LockedError
from .subprocess import create_subvolume, delete_subvolume, is_btrfs, make_snapshot

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
        if not joined_path.startswith(self.path):
            raise RuntimeError(f'invalid path, join {self.path} with {path}')
        return joined_path

    def assure_writable(self):
        """assert write access on this volume.

        :raise BackupDirError: when write access on volume is not given
        :return: None

        >>> import os, stat, tempfile
        >>> from snapshotbackup.volume import BaseVolume
        >>> with tempfile.TemporaryDirectory() as path:
        ...     BaseVolume(path).assure_writable()
        ...     os.chmod(path, stat.S_IRUSR)
        ...     BaseVolume(path).assure_writable()
        Traceback (most recent call last):
        snapshotbackup.exceptions.BackupDirError: not writable ...
        """
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
        return Lock(self.path)


class BtrfsVolume(BaseVolume):
    """represents a path on a btrfs volume.
    provides functions to interact with btrfs relative to given base dir.
    """

    def __init__(self, path):
        """check that `base_path` exists, is dir, and is on a btrfs filesystem.

        :param str path:
        :raise BackupDirNotFoundError: backup dir not found
        :raise BackupDirError: general error with meaningful message

        >>> import os.path, tempfile
        >>> from snapshotbackup.volume import BtrfsVolume
        >>> with tempfile.TemporaryDirectory() as path:
        ...     BtrfsVolume(os.path.join(path, 'nope'))
        Traceback (most recent call last):
        snapshotbackup.exceptions.BackupDirNotFoundError: ...
        >>> with tempfile.TemporaryDirectory() as path:
        ...     not_a_dir = os.path.join(path, 'file')
        ...     open(not_a_dir, 'w').close()
        ...     BtrfsVolume(not_a_dir)
        Traceback (most recent call last):
        snapshotbackup.exceptions.BackupDirError: not a directory ...
        """
        super().__init__(path)

        if not os.path.exists(self.path):
            raise BackupDirNotFoundError(self.path)

        if not os.path.isdir(self.path):
            raise BackupDirError(f'not a directory {self.path}', self.path)

        if not is_btrfs(self.path):
            raise BackupDirError(f'not a btrfs {self.path}', self.path)

    def create_subvolume(self, name):
        """create subvolume `name` in this volume.

        :param str name:
        :return: None
        """
        create_subvolume(self._path_join(name))

    def delete_subvolume(self, name):
        """delete subvolume `name` in this volume.

        :param str name:
        :return: None
        """
        delete_subvolume(self._path_join(name))

    def make_snapshot(self, source, target, readonly=True):
        """make snapshot `target` in this volume from `source` in this volume.

        :param str source:
        :param str target:
        :param bool readonly: snapshot will be readonly
        :return: None
        """
        make_snapshot(self._path_join(source), self._path_join(target), readonly=readonly)


class Lock(object):
    """lockfile as context manager.

    :raise LockedError: when lockfile already exists
    :raise FileNotFoundError: when lockfile cannot be created (missing dir)
    :raise OSError: others may occur

    >>> import tempfile
    >>> import os.path
    >>> from snapshotbackup.volume import Lock
    >>> with tempfile.TemporaryDirectory() as path:
    ...     with Lock(path):
    ...         pass
    >>> with tempfile.TemporaryDirectory() as path:
    ...     with Lock(path):
    ...         pass
    ...     with Lock(path):
    ...         pass
    >>> with tempfile.TemporaryDirectory() as path:
    ...     with Lock(path):
    ...         with Lock(path):
    ...             pass
    Traceback (most recent call last):
    snapshotbackup.exceptions.LockedError: ...
    >>> with tempfile.TemporaryDirectory() as path:
    ...     with Lock(os.path.join(path, 'nope')):
    ...         pass
    Traceback (most recent call last):
    FileNotFoundError: ...
    """
    _dir: str
    """full path to directory"""

    _lockfile: str
    """full path to the lockfile"""

    def __init__(self, dir):
        """initialize lock

        :param str dir: path where lockfile shall be created
        """
        self._dir = os.path.abspath(dir)
        self._lockfile = os.path.join(self._dir, _sync_lockfile)

    def __enter__(self):
        """enter locked context: create lockfile or throw error"""
        if os.path.isfile(self._lockfile):
            raise LockedError(self._lockfile)
        open(self._lockfile, 'w').close()

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """exit locked context: remove lockfile"""
        os.remove(self._lockfile)
