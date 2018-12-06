import os
from datetime import datetime

from .exceptions import BackupDirError, BackupDirNotFoundError, LockedError
from .subprocess import create_subvolume, delete_subvolume, is_btrfs, make_snapshot
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
    snapshotbackup.exceptions.BackupDirNotFoundError: ...
    >>> with tempfile.TemporaryDirectory() as path:
    ...     not_a_dir = os.path.join(path, 'file')
    ...     open(not_a_dir, 'w').close()
    ...     BackupDir(not_a_dir)
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
        :raise BackupDirNotFoundError: backup dir not found
        :raise BackupDirError: general error with meaningful message
        """
        self.path = os.path.abspath(dir)
        self.sync_path = os.path.join(self.path, _sync_dir)

        if not os.path.exists(self.path):
            raise BackupDirNotFoundError(self.path)

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

    def get_backups(self, retain_all_after=earliest_time, retain_daily_after=earliest_time, decay_before=earliest_time):
        """create list of all backups in this backup dir.

        :param datetime.datetime retain_all_after:
        :param datetime.datetime retain_daily_after:
        :return: list of backups in this backup directory
        :rtype: [snapshotbackup.backup.Backup]
        """
        dirs = []
        for _root, _dirs, _files in os.walk(self.path):
            dirs = [_dir for _dir in _dirs if is_timestamp(_dir)]
            break

        dirs.sort()
        backups = []
        for _index, _dir in enumerate(dirs):
            previous = backups[len(backups) - 1] if len(backups) > 0 else None
            backups.append(Backup(_dir, self.path, retain_all_after, retain_daily_after, decay_before,
                                  previous=previous, is_last=_index == len(dirs)))
        return backups


class Backup(object):
    """Used as a container for all metadata attached to a finished backup.

    >>> from datetime import datetime
    >>> from snapshotbackup.backupdir import Backup
    >>> retain_all = datetime(1970, 3, 1)
    >>> retain_daily = datetime(1970, 2, 1)
    >>> decay = datetime(1970, 1, 1, 1)
    >>> b0 = Backup('1970-01-01', '/tmp', retain_all, retain_daily, decay)
    >>> b1 = Backup('1970-01-02', '/tmp', retain_all, retain_daily, decay, previous=b0)
    >>> b2 = Backup('1970-02-02', '/tmp', retain_all, retain_daily, decay, previous=b1)
    >>> b3 = Backup('1970-03-02', '/tmp', retain_all, retain_daily, decay, previous=b2)
    >>> b4 = Backup('1970-04-02', '/tmp', retain_all, retain_daily, decay, previous=b3, is_last = True)
    >>> b0.is_last or b1.is_last or b2.is_last or b3.is_last
    False
    >>> b4.is_last
    True
    >>> b0.prune
    False
    >>> b0.is_weekly
    True
    >>> b1.prune
    True
    >>> b1.is_weekly
    False
    >>> b2.prune
    False
    >>> b2.is_daily
    True
    >>> b2.is_inside_retain_daily_interval
    True
    >>> b3.prune
    False
    >>> b3.is_daily
    True
    >>> b3.is_inside_retain_all_interval
    True
    >>> b0.decay
    True
    >>> b1.decay or b2.decay or b3.decay or b4.decay
    False
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

    decay: bool = False
    """if this backup may decay"""

    prune: bool = False
    """if this backup should be pruned by retention policy"""

    def __init__(self, name, basedir, retain_all_after, retain_daily_after, decay_before, previous=None, is_last=False):
        """initialize a backup object.

        :param str name: name of this backup, also an iso timestamp
        :param str basedir: backup directory this backup lives in
        :param datetime.datetime retain_all: backup will not be pruned if it is after this timestamp
        :param datetime.datetime retain_daily: backup will not be pruned if it is after this timestamp and a daily
        :param Backup next: successive backup object
        :raise TimestampParseError: when `name` is not valid iso string
        """
        self.name = name
        self.datetime = parse_timestamp(name)
        self.path = os.path.join(basedir, self.name)
        self.decay = self._is_before(decay_before)
        self.is_inside_retain_all_interval = self._is_after_or_equal(retain_all_after)
        self.is_inside_retain_daily_interval = self._is_after_or_equal(retain_daily_after)
        self.is_last = is_last
        if not previous:
            self.is_daily = True
            self.is_weekly = True
        else:
            self.is_daily = not is_same_day(previous.datetime, self.datetime)
            self.is_weekly = not is_same_week(previous.datetime, self.datetime)
        self.prune = not self._retain()

    def _is_before(self, timestamp):
        """check if this backup completed before given timestamp.

        :param datetime.datetime timestamp:
        :return bool:
        """
        return timestamp > self.datetime

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
        if self.is_last:
            return True
        if self.is_inside_retain_all_interval:
            return True
        if self.is_inside_retain_daily_interval:
            return self.is_daily
        return self.is_weekly

    def delete(self):
        """delete this backup"""
        delete_subvolume(self.path)


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
