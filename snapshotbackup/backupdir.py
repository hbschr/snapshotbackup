import os
from os.path import abspath, dirname, isdir, join

from .backup import Backup
from .exceptions import BackupDirError, LockedError, LockPathError
from .shell import create_subvolume, is_btrfs
from .timestamps import get_timestamp, is_timestamp

_sync_dir = '.sync'
_sync_lockfile = '.sync_lock'


class BackupDir(object):
    """a backup dir contains all snapshots and a sync dir.
    the directory must be reachable via file system and has to be on a btrfs filesystem.

    optional this class provides a sync dir (btrfs subvolume) which can be locked. for more checks consult
    :func:`__init__`.

    >>> import tempfile
    >>> from os.path import join
    >>> from snapshotbackup.backupdir import BackupDir
    >>> with tempfile.TemporaryDirectory() as path:
    ...     BackupDir(join(path, 'nope')).get_backups()
    Traceback (most recent call last):
    snapshotbackup.exceptions.BackupDirError: ...
    """

    dir: str
    """absolute path to backup dir"""

    sync_dir: str
    """absolute path to sync dir"""

    def __init__(self, dir, assert_syncdir=False, assert_writable=False):
        """check that `path`

        - exists
        - is on a btrfs filesystem.
        - is writable (optional)
        - has sync dir, create if needed (optional)
        - ... which is btrfs subvolume (not implemented).

        :param str dir:
        :param bool assert_syncdir: if true syncdir will be checked and created if needed, also checks `writable`
        :param bool assert_writable bool: if true write access for current process will be checked
        :raise BackupDirError: error with meaningful message
        """
        self.dir = abspath(dir)
        self.sync_dir = join(self.dir, _sync_dir)

        if not isdir(self.dir):
            raise BackupDirError(f'not a directory {self.dir}', self.dir)

        if (assert_writable or assert_syncdir) and not os.access(self.dir, os.W_OK):
            raise BackupDirError(f'not writable {self.dir}', self.dir)

        if not is_btrfs(self.dir):
            raise BackupDirError(f'not a btrfs {self.dir}', self.dir)

        if assert_syncdir and not isdir(self.sync_dir):
            # FIXME: create snapshot from last backup if possible
            create_subvolume(self.sync_dir, silent=True)

    def lock(self):
        """lock sync dir.

        :return object: a :class:`snapshotbackup.lock.Lock` context
        """
        return Lock(self.dir)

    def new_snapshot_path(self):
        """create snapshot path with current timestamp.

        :return str:
        """
        timestamp = get_timestamp().isoformat()
        return join(self.dir, timestamp)

    def get_backups(self, retain_all_after, retain_daily_after):
        """create list of all backups in this backup dir.

        :param datetime.datetime retain_all_after:
        :param datetime.datetime retain_daily_after:
        :return: list of backups in this backup directory
        :rtype: [snapshotbackup.backup.Backup]
        """
        for root, dirs, files in os.walk(self.dir):
            dirs = [dir for dir in dirs if is_timestamp(dir)]
            break

        backups = []
        for dir in reversed(dirs):
            if len(backups) == 0:
                backups.insert(0, Backup(dir, self.dir, retain_all_after, retain_daily_after))
            else:
                backups.insert(0, Backup(dir, self.dir, retain_all_after, retain_daily_after, next=backups[0]))
        return backups


class Lock(object):
    """lockfile as context manager

    :raise LockedError: when lockfile already exists
    :raise LockPathError: when lockfile cannot be created (missing dir)

    >>> import tempfile
    >>> from os.path import join
    >>> from snapshotbackup.backupdir import Lock
    >>> with tempfile.TemporaryDirectory() as path:
    ...     with Lock(path):
    ...         pass
    >>> with tempfile.TemporaryDirectory() as path:
    ...     with Lock(path):
    ...         with Lock(path):
    ...             pass
    Traceback (most recent call last):
    snapshotbackup.exceptions.LockedError: ...
    >>> with tempfile.TemporaryDirectory() as path:
    ...     with Lock(join(path, 'nope')):
    ...         pass
    Traceback (most recent call last):
    snapshotbackup.exceptions.LockPathError: ...
    """

    _lockfile: str
    """full path to the lockfile"""

    def __init__(self, path):
        """initialize lock

        :param str path: path where lockfile shall be created
        """
        self._lockfile = join(path, _sync_lockfile)

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
        os.remove(self._lockfile)
