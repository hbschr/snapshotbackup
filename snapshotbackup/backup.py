from datetime import datetime

from os.path import join

from .timestamps import is_same_day, is_same_week, parse_timestamp


class Backup(object):
    """Used as a container for all metadata attached to a finished backup.

    >>> from datetime import datetime
    >>> from snapshotbackup.backup import Backup
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

        :param str name: name of this backup, also a iso timestamp
        :param BackupDir vol: backup directory this backup lives in
        :param datetime.datetime retain_all: backup will not be purged if it is after this timestamp
        :param datetime.datetime retain_daily: backup will not be purged if it is after this timestamp and a daily
        :param Backup next: successive backup object
        :raise TimestampParseError: when `name` is not valid iso string
        """
        self.name = name
        self.datetime = parse_timestamp(name)
        self.vol = vol
        self.path = join(self.vol.path, self.name)
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
