import os
from datetime import datetime

from .subprocess import delete_subvolume
from .timestamps import earliest_time, get_timestamp, is_same_day, is_same_week, is_timestamp, parse_timestamp
from .volume import BtrfsVolume


class Worker(object):
    """a backup dir contains all snapshots and a sync dir.
    the directory must be reachable via file system and has to be on a btrfs filesystem.
    all checks from :func:`BtrfsVolume.init` are performed.

    optional this class provides a sync dir (btrfs subvolume) which can be locked.
    """

    volume: BtrfsVolume
    """instance of :class:`snapshotbackup.volume.BtrfsVolume`"""

    def __init__(self, dir, assert_syncdir=False, assert_writable=False):
        """checks some general assumptions about `dir` (see :func:`BtrfsVolume.__init__`) and create sync dir when
        not yet present.

        not implemented: check if sync dir is btrfs subvolume.

        :param str dir:
        :param bool assert_syncdir: if `True` syncdir will be created if needed, also implies `assert_writable`
        :param bool assert_writable: if `True` write access for current process will be checked
        :raise Error: see :func:`BtrfsVolume.__init__`
        """
        self.volume = BtrfsVolume(dir, assert_writable=assert_writable or assert_syncdir)

        if assert_syncdir and not os.path.isdir(self.volume.sync_path):
            try:
                _last = self.get_backups().pop()
                self.volume.make_snapshot(_last.name, self.volume.sync_path, readonly=False)
            except IndexError:
                self.volume.create_subvolume(self.volume.sync_path)

    def delete_syncdir(self):
        """deletes sync dir when found, otherwise nothing.

        :return: None
        """
        if os.path.isdir(self.volume.sync_path):
            self.volume.delete_subvolume(self.volume.sync_path)

    def get_backups(self, retain_all_after=earliest_time, retain_daily_after=earliest_time, decay_before=earliest_time):
        """create list of all backups in this backup dir.

        :param datetime.datetime retain_all_after:
        :param datetime.datetime retain_daily_after:
        :return: list of backups in this backup directory
        :rtype: [snapshotbackup.backup.Backup]
        """
        dirs = []
        for _root, _dirs, _files in os.walk(self.volume.path):
            dirs = [_dir for _dir in _dirs if is_timestamp(_dir)]
            break

        dirs.sort()
        backups = []
        for _index, _dir in enumerate(dirs):
            previous = backups[len(backups) - 1] if len(backups) > 0 else None
            backups.append(Backup(_dir, self.volume.path, retain_all_after, retain_daily_after, decay_before,
                                  previous=previous, is_last=_index == len(dirs)))
        return backups

    def snapshot_sync(self):
        """make a snapshot of sync dir.

        :return: None
        """
        self.volume.make_snapshot(self.volume.sync_path, get_timestamp().isoformat())


class Backup(object):
    """Used as a container for all metadata attached to a finished backup.

    >>> from datetime import datetime
    >>> from snapshotbackup.worker import Backup
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
