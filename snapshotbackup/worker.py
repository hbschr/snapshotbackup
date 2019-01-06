import logging
import os
from datetime import datetime

from .subprocess import is_reachable, rsync
from .timestamps import earliest_time, get_human_readable_timedelta, get_timestamp, is_same_day, is_same_week, \
    is_timestamp, parse_timestamp
from .volume import BtrfsVolume

logger = logging.getLogger(__name__)


class Worker(object):
    """a worker provides the basic functionality regarding backups (make, list, decay, prune, ...).
    the worker delegates low-level file system interaction to :class:`snapshotbackup.volume.BtrfsVolume`.
    the volume contains all snapshots (backups) and a sync dir.
    the volume must be reachable via file system and has to be on a btrfs filesystem.
    """

    decay_before: datetime
    """threshold: backups older than this may decay"""

    retain_all_after: datetime
    """threshold: backups younger than this are not pruned"""

    retain_daily_after: datetime
    """threshold: daily backups younger than this are not pruned"""

    volume: BtrfsVolume
    """instance of :class:`snapshotbackup.volume.BtrfsVolume`"""

    def __init__(self, path, retain_all_after=earliest_time, retain_daily_after=earliest_time,
                 decay_before=earliest_time):
        """populate `self.volume` with a new :class:`snapshotbackup.volume.BtrfsVolume` instance.

        :param str path:
        :param datetime.datetime retain_all_after:
        :param datetime.datetime retain_daily_after:
        :param datetime.datetime decay_before:
        :raise Error: see :func:`BtrfsVolume.__init__`
        """
        self.volume = BtrfsVolume(path)
        self.decay_before = decay_before
        self.retain_all_after = retain_all_after
        self.retain_daily_after = retain_daily_after

    def __repr__(self):
        return f'Worker(path={self.volume.path}, decay_before={self.decay_before}), ' \
               f'retain_all_after={self.retain_all_after}, retain_daily_after={self.retain_daily_after})'

    def _assert_syncdir(self):
        """assert existence of syncdir, create if not present.

        not implemented: check if sync dir is btrfs subvolume.

        :return: None
        """
        self.volume.assure_writable()
        if not os.path.isdir(self.volume.sync_path):
            _last = self.get_last()
            if _last:
                self.volume.make_snapshot(_last.name, self.volume.sync_path, readonly=False)
            else:
                self.volume.create_subvolume(self.volume.sync_path)

    def setup(self):
        """

        :return: None
        """
        self.volume.setup()

    def make_backup(self, source_dir, ignore, autodecay=False, autoprune=False, checksum=False, dry_run=False,
                    progress=False):
        """make a backup from given source.

        :param str source_dir:
        :param tuple ignore:
        :param bool autodecay:
        :param bool autoprune:
        :param bool checksum:
        :param bool dry_run:
        :param bool progress:
        :return: None
        """
        logger.info(f'make backup, source_dir={source_dir}, ignore={ignore}, autodecay={autodecay}, '
                    f'autoprune={autoprune}, checksum={checksum}, dry_run={dry_run}, progress={progress}, {self}')
        is_reachable(source_dir)
        self._assert_syncdir()
        with self.volume.lock():
            rsync(source_dir, self.volume.sync_path, exclude=ignore, checksum=checksum, progress=progress,
                  dry_run=dry_run)
            if not dry_run:
                self.volume.make_snapshot(self.volume.sync_path, get_timestamp().isoformat())
        if autodecay:
            self.decay_backups(lambda x: True)
        if autoprune:
            self.prune_backups(lambda x: True)

    def get_backups(self):
        """create list of all backups in this backup dir.

        :return: list of backups in this volume
        :rtype: [snapshotbackup.backup.Backup]
        """
        self.volume.assure_path()
        dirs = []
        for _root, _dirs, _files in os.walk(self.volume.path):
            dirs = [_dir for _dir in _dirs if is_timestamp(_dir)]
            break

        dirs.sort()
        backups = []
        for _index, _dir in enumerate(dirs):
            previous = backups[len(backups) - 1] if len(backups) > 0 else None
            backups.append(Backup(_dir, self.retain_all_after, self.retain_daily_after, self.decay_before,
                                  previous=previous, is_last=_index == len(dirs)))
        return backups

    def get_last(self):
        """returns latest backup of this volume

        :return: latest backup or None
        :rtype: snapshotbackup.backup.Backup
        """
        _list = self.get_backups()
        if len(_list) == 0:
            return None
        return _list.pop()

    def delete_syncdir(self):
        """deletes sync dir when found, otherwise nothing.

        :return: None
        """
        logger.info(f'delete sync dir, {self}')
        self.volume.assure_writable()
        if os.path.isdir(self.volume.sync_path):
            self.volume.delete_subvolume(self.volume.sync_path)

    def destroy_volume(self, prompt):
        """deletes all backups and the volume path. i repeat: deletes all data!

        :return: None
        """
        logger.warning(f'delete all backups, {self}')
        self.delete_syncdir()
        for backup in self.get_backups():
            if prompt(backup):
                self.volume.delete_subvolume(backup.name)
        os.rmdir(self.volume.path)

    def decay_backups(self, prompt):
        """delete all backups which are older than `decay` retention policy.

        :param callable prompt: will be called for each deletion, must return `True` to authenticate.
        :return: None
        """
        logger.info(f'decay backups, {self}')
        self.volume.assure_writable()
        for to_decay in [_b for _b in self.get_backups() if _b.decay]:
            if prompt(to_decay):
                self.volume.delete_subvolume(to_decay.name)

    def prune_backups(self, prompt):
        """delete all backups which are not held by `retain_*` retention policy.

        :param callable prompt: will be called for each deletion, must return `True` to authenticate.
        :return: None
        """
        logger.info(f'prune backups, {self}')
        self.volume.assure_writable()
        for to_be_pruned in [_b for _b in self.get_backups() if _b.prune]:
            if prompt(to_be_pruned):
                self.volume.delete_subvolume(to_be_pruned.name)


class Backup(object):
    """Used as a container for all metadata attached to a finished backup.

    >>> from datetime import datetime
    >>> from snapshotbackup.worker import Backup
    >>> retain_all = datetime(1970, 3, 1)
    >>> retain_daily = datetime(1970, 2, 1)
    >>> decay = datetime(1970, 1, 1, 1)
    >>> b0 = Backup('1970-01-01', retain_all, retain_daily, decay)
    >>> b1 = Backup('1970-01-02', retain_all, retain_daily, decay, previous=b0)
    >>> b2 = Backup('1970-02-02', retain_all, retain_daily, decay, previous=b1)
    >>> b3 = Backup('1970-03-02', retain_all, retain_daily, decay, previous=b2)
    >>> b4 = Backup('1970-04-02', retain_all, retain_daily, decay, previous=b3, is_last = True)
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
    >>> b2.is_retain_daily
    True
    >>> b3.prune
    False
    >>> b3.is_daily
    True
    >>> b3.is_retain_all
    True
    >>> b0.decay
    True
    >>> b1.decay or b2.decay or b3.decay or b4.decay
    False
    """

    name: str
    """name, coincidently also the iso timestamp string"""

    datetime: datetime
    """when this backup was finished"""

    is_last: bool = False
    """if this backup is the latest one"""

    is_daily: bool = False
    """if this backup is the last in its day"""

    is_weekly: bool = False
    """if this backup is the last in its week"""

    is_retain_all: bool
    """if this backup is inside the `retain_all` time interval"""

    is_retain_daily: bool
    """if this backup is inside the `retain_daily` time interval"""

    decay: bool = False
    """if this backup may decay"""

    prune: bool = False
    """if this backup should be pruned by retention policy"""

    def __init__(self, name, retain_all_after, retain_daily_after, decay_before, previous=None, is_last=False):
        """initialize a backup object.

        :param str name: name of this backup, also an iso timestamp
        :param datetime.datetime retain_all_after: backup will not be pruned if it is after this timestamp
        :param datetime.datetime retain_daily_after: backup will not be pruned if it is after this timestamp and a daily
        :param datetime.datetime decay_before: backup will not decay if it is before this timestamp
        :param Backup previous: previous backup object
        :param bool is_last: if this is the last backup
        :raise TimestampParseError: when `name` is not valid iso string
        """
        self.name = name
        self.datetime = parse_timestamp(name)
        self.decay = self.is_before(decay_before)
        self.is_retain_all = self.is_after_or_equal(retain_all_after)
        self.is_retain_daily = self.is_after_or_equal(retain_daily_after)
        self.is_last = is_last
        if not previous:
            self.is_daily = True
            self.is_weekly = True
        else:
            self.is_daily = not is_same_day(previous.datetime, self.datetime)
            self.is_weekly = not is_same_week(previous.datetime, self.datetime)
        self.prune = not self._retain()

    def __repr__(self):
        attributes = ', '.join((f'{_a}={getattr(self, _a)}' for _a in ('name', 'decay', 'prune', 'is_daily',
                                                                       'is_weekly', 'is_last',
                                                                       'is_retain_all',
                                                                       'is_retain_daily')))
        return f'Backup({attributes})'

    def __str__(self):
        """return human readable string representation for this backup.

        :return str:

        >>> from snapshotbackup.timestamps import earliest_time
        >>> from snapshotbackup.worker import Backup
        >>> backup = Backup('1970-01-01T00:00:00+00', earliest_time, earliest_time, earliest_time)
        >>> str(backup)
        'Backup 1970-01-01 00:00:00+00:00 (... ago)'
        """
        iso = self.datetime.isoformat(sep=' ')
        ago = get_human_readable_timedelta(get_timestamp() - self.datetime)
        return f'Backup {iso} ({ago} ago)'

    def is_before(self, timestamp):
        """check if this backup completed before given timestamp.

        :param datetime.datetime timestamp:
        :return bool:
        """
        return timestamp > self.datetime

    def is_after_or_equal(self, timestamp):
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
        if self.is_retain_all:
            return True
        if self.is_retain_daily:
            return self.is_daily
        return self.is_weekly
