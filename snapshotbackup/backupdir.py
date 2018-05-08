import os
from os.path import abspath, isdir, join

from .backup import Backup
from .exceptions import BackupDirError, LockedError, LockPathError
from .shell import create_subvolume, is_btrfs, make_snapshot
from .timestamps import get_timestamp, is_timestamp, earliest_time

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

    path: str
    """absolute path to backup dir"""

    sync_path: str
    """absolute path to sync dir"""

    def __init__(self, dir, assert_syncdir=False, assert_writable=False, silent=False):
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
        self.path = abspath(dir)
        self.sync_path = join(self.path, _sync_dir)
        self._silent = silent

        if not isdir(self.path):
            raise BackupDirError(f'not a directory {self.path}', self.path)

        if (assert_writable or assert_syncdir) and not os.access(self.path, os.W_OK):
            raise BackupDirError(f'not writable {self.path}', self.path)

        if not is_btrfs(self.path):
            raise BackupDirError(f'not a btrfs {self.path}', self.path)

        if assert_syncdir and not isdir(self.sync_path):
            try:
                _last = self.get_backups().pop()
                make_snapshot(_last.path, self.sync_path, readonly=False, silent=self._silent)
            except IndexError:
                create_subvolume(self.sync_path, silent=True)

    def lock(self):
        """lock sync dir.

        :return object: a :class:`snapshotbackup.lock.Lock` context
        """
        return Lock(self.path)

    def snapshot_sync(self):
        """make a snapshot of sync dir.

        :return: None
        """
        target_path = join(self.path, get_timestamp().isoformat())
        make_snapshot(self.sync_path, target_path, silent=self._silent)

    def get_backups(self, retain_all_after=earliest_time, retain_daily_after=earliest_time):
        """create list of all backups in this backup dir.

        :param datetime.datetime retain_all_after:
        :param datetime.datetime retain_daily_after:
        :return: list of backups in this backup directory
        :rtype: [snapshotbackup.backup.Backup]
        """
        for root, dirs, files in os.walk(self.path):
            dirs = [dir for dir in dirs if is_timestamp(dir)]
            break

        backups = []
        for backup in reversed(dirs):
            if len(backups) == 0:
                backups.insert(0, Backup(backup, self, retain_all_after, retain_daily_after))
            else:
                backups.insert(0, Backup(backup, self, retain_all_after, retain_daily_after, next=backups[
                    0]))
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
    _dir: str
    """full path to directory"""

    _lockfile: str
    """full path to the lockfile"""

    def __init__(self, dir):
        """initialize lock

        :param str dir: path where lockfile shall be created
        """
        self._dir = abspath(dir)
        self._lockfile = join(self._dir, _sync_lockfile)

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
            raise LockPathError(self._dir)

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """exit locked context, lockfile will be removed"""
        os.remove(self._lockfile)
