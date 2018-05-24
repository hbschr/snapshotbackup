import os
from datetime import datetime

from .exceptions import BackupDirError, LockedError
from .subprocess import create_subvolume, is_btrfs, make_snapshot
from .timestamps import earliest_time, get_timestamp, is_same_day, is_same_week, is_timestamp, parse_timestamp

_sync_dir = '.sync'
_sync_lockfile = '.sync_lock'


class BackupDir(object):
    """a backup dir contains all snapshots and a sync dir.
    the directory must be reachable via file system and has to be on a btrfs filesystem.

    optional this class provides a sync dir (btrfs subvolume) which can be locked.
    for more details about checks consult :func:`__init__`.

    >>> import os, os.path, stat, tempfile
    >>> from snapshotbackup.backupdir import BackupDir
    >>> with tempfile.TemporaryDirectory() as path:
    ...     BackupDir(os.path.join(path, 'nope'))
    Traceback (most recent call last):
    snapshotbackup.exceptions.BackupDirError: not a directory ...
    >>> with tempfile.TemporaryDirectory() as path:
    ...     os.chmod(path, stat.S_IRUSR)
    ...     BackupDir(path, assert_writable=True)
    Traceback (most recent call last):
    snapshotbackup.exceptions.BackupDirError: not writable ...
    """

    path: str
    """absolute path to backup dir"""

    sync_path: str
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
        self.path = os.path.abspath(dir)
        self.sync_path = os.path.join(self.path, _sync_dir)

        if not os.path.isdir(self.path):
            raise BackupDirError(f'not a directory {self.path}', self.path)

        if (assert_writable or assert_syncdir) and not os.access(self.path, os.W_OK):
            raise BackupDirError(f'not writable {self.path}', self.path)

        if not is_btrfs(self.path):
            raise BackupDirError(f'not a btrfs {self.path}', self.path)

        if assert_syncdir and not os.path.isdir(self.sync_path):
            try:
                _last = self.get_backups().pop()
                make_snapshot(_last.path, self.sync_path, readonly=False)
            except IndexError:
                create_subvolume(self.sync_path)

    def lock(self):
        """lock sync dir.

        :return object: a :class:`snapshotbackup.backupdir.Lock` context
        """
        return Lock(self.path)

    def snapshot_sync(self):
        """make a snapshot of sync dir.

        :return: None
        """
        target_path = os.path.join(self.path, get_timestamp().isoformat())
        make_snapshot(self.sync_path, target_path)

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

        dirs.sort()
        backups = []
        for backup in reversed(dirs):
            if len(backups) == 0:
                backups.insert(0, Backup(backup, self, retain_all_after, retain_daily_after))
            else:
                backups.insert(0, Backup(backup, self, retain_all_after, retain_daily_after, next=backups[
                    0]))
        return backups


class Backup(object):
    """Used as a container for all metadata attached to a finished backup.

    >>> from datetime import datetime
    >>> from snapshotbackup.backupdir import Backup
    >>> mock_vol = type('BackupDir', (object,), {'path': '/tmp'})
    >>> retain_all = datetime(1970, 3, 1)
    >>> retain_daily = datetime(1970, 2, 1)
    >>> b4 = Backup('1970-04-02', mock_vol, retain_all, retain_daily)
    >>> b3 = Backup('1970-03-02', mock_vol, retain_all, retain_daily, next=b4)
    >>> b2 = Backup('1970-02-02', mock_vol, retain_all, retain_daily, next=b3)
    >>> b1 = Backup('1970-01-02', mock_vol, retain_all, retain_daily, next=b2)
    >>> b0 = Backup('1970-01-01', mock_vol, retain_all, retain_daily, next=b1)
    >>> b0.purge
    True
    >>> b0.is_weekly
    False
    >>> b1.purge
    False
    >>> b1.is_weekly
    True
    >>> b2.purge
    False
    >>> b2.is_daily
    True
    >>> b2.is_inside_retain_daily_interval
    True
    >>> b3.purge
    False
    >>> b3.is_daily
    True
    >>> b3.is_inside_retain_all_interval
    True
    """

    name: str
    """name, coincidently also the iso timestamp string"""

    vol = None
    """backup dir where this backup resides in"""

    path: str
    """full path to this backup"""

    datetime: datetime
    """when this backup was finished"""

    is_last: bool = False
    """if this backup is the latest one"""

    is_daily: bool = False
    """if this backup is the last in its day"""

    is_weekly: bool = False
    """if this backup is the last in its week"""

    is_inside_retain_all_interval: bool
    """if this backup is inside the `retain_all` time interval"""

    is_inside_retain_daily_interval: bool
    """if this backup is inside the `retain_daily` time interval"""

    purge: bool = False
    """if this backup should be purged by retention policy"""

    def __init__(self, name, vol, retain_all_after, retain_daily_after, next=None):
        """initialize a backup object.

        :param str name: name of this backup, also an iso timestamp
        :param BackupDir vol: backup directory this backup lives in
        :param datetime.datetime retain_all: backup will not be purged if it is after this timestamp
        :param datetime.datetime retain_daily: backup will not be purged if it is after this timestamp and a daily
        :param Backup next: successive backup object
        :raise TimestampParseError: when `name` is not valid iso string
        """
        self.name = name
        self.datetime = parse_timestamp(name)
        self.vol = vol
        self.path = os.path.join(self.vol.path, self.name)
        self.is_inside_retain_all_interval = self._is_after_or_equal(retain_all_after)
        self.is_inside_retain_daily_interval = self._is_after_or_equal(retain_daily_after)
        if not next:
            self.is_last = True
        else:
            self.is_daily = not is_same_day(self.datetime, next.datetime)
            self.is_weekly = not is_same_week(self.datetime, next.datetime)
            self.purge = not self._retain()

    def _is_after_or_equal(self, timestamp):
        """check if this backup completed after given timestamp.

        :param datetime.datetime timestamp:
        :return bool:
        """
        return timestamp <= self.datetime

    def _retain(self):
        """check if this backup should be retained by retention policy.

        :return bool:
        """
        if self.is_inside_retain_all_interval:
            return True
        if self.is_inside_retain_daily_interval:
            return self.is_daily
        return self.is_weekly


class Lock(object):
    """lockfile as context manager

    :raise LockedError: when lockfile already exists
    :raise FileNotFoundError: when lockfile cannot be created (missing dir)
    :raise OSError: others may occur

    >>> import tempfile
    >>> import os.path
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
        try:
            open(self._lockfile, 'r').close()
            raise LockedError(self._lockfile)
        except FileNotFoundError:
            open(self._lockfile, 'w').close()

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """exit locked context: remove lockfile"""
        os.remove(self._lockfile)
