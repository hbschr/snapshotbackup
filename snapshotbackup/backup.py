from datetime import datetime
from os import walk
from os.path import isdir

from .exceptions import BackupDirError
from .timestamps import is_same_day, is_same_week, is_timestamp, parse_timestamp


def _get_dirs(path):
    """get list of directories in `path` which can be parsed as timestamps.

    :param path str:
    :return list: backups available in `path`
    :raise BackupDirError: if `path` is no directory

    >>> import tempfile
    >>> from os.path import join
    >>> from snapshotbackup.backup import _get_dirs
    >>> _get_dirs('/tmp')
    [...]
    >>> with tempfile.TemporaryDirectory() as path:
    ...     _get_dirs(join(path, 'nope'))
    Traceback (most recent call last):
    snapshotbackup.exceptions.BackupDirError: ...
    """
    if not isdir(path):
        raise BackupDirError(path)
    for root, dirs, files in walk(path):
        return [dir for dir in dirs if is_timestamp(dir)]
    return []


def load_backups(config):
    """get list of backups for given `config`

    :param config dict:
    :return list: list of `Backup`
    """
    path = config['backups']
    retain_all_after = config['retain_all_after']
    retain_daily_after = config['retain_daily_after']
    dirs = _get_dirs(path)
    backups = []
    for dir in reversed(dirs):
        if len(backups) == 0:
            backups.insert(0, Backup(dir, path, retain_all_after, retain_daily_after))
        else:
            backups.insert(0, Backup(dir, path, retain_all_after, retain_daily_after, next=backups[0]))
    return backups


class Backup(object):
    """Used as a container for all metadata attached to a finished backup.

    >>> from snapshotbackup.backup import Backup
    >>> from datetime import datetime
    >>> retain_all = datetime(1970, 3, 1)
    >>> retain_daily = datetime(1970, 2, 1)
    >>> b4 = Backup('1970-04-02', '/tmp', retain_all, retain_daily)
    >>> b3 = Backup('1970-03-02', '/tmp', retain_all, retain_daily, next=b4)
    >>> b2 = Backup('1970-02-02', '/tmp', retain_all, retain_daily, next=b3)
    >>> b1 = Backup('1970-01-02', '/tmp', retain_all, retain_daily, next=b2)
    >>> b0 = Backup('1970-01-01', '/tmp', retain_all, retain_daily, next=b1)
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

    path: str
    """basepath this backup resides in"""

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

    def __init__(self, name: str, path: str, retain_all_after: datetime, retain_daily_after: datetime, next=None):
        """initialize a backup object.

        :param name str: name of this backup, also a iso timestamp
        :param path str: path where this backup resides
        :param retain_all datetime: backup will not be purged if it is after this timestamp
        :param retain_daily datetime: backup will not be purged if it is after this timestamp and a daily
        :param next Backup: successive backup object
        """
        self.name = name
        self.path = path
        self.datetime = parse_timestamp(name)
        self.is_inside_retain_all_interval = self._is_after(retain_all_after)
        self.is_inside_retain_daily_interval = self._is_after(retain_daily_after)
        if not next:
            self.is_last = True
        else:
            self.is_daily = not is_same_day(self.datetime, next.datetime)
            self.is_weekly = not is_same_week(self.datetime, next.datetime)
            self.purge = not self._retain()

    def _is_after(self, timestamp):
        """check if given timestamp if after the completion time of this backup.

        :param timestamp datetime:
        :return bool:
        """
        return self.datetime > timestamp

    def _retain(self):
        """check if this backup should be retained by retention policy.

        :return bool:
        """
        if self.is_inside_retain_all_interval:
            return True
        if self.is_inside_retain_daily_interval:
            return self.is_daily
        return self.is_weekly
