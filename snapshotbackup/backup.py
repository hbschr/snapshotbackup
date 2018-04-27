from datetime import datetime
from os import walk


from .timestamps import is_same_day, is_same_week, is_timestamp, parse_timestamp


def _get_dirs(path):
    """get list of directories in `path` which can be parsed as timestamps.

    :param path str:
    :return list: backups available in `path`

    >>> from snapshotbackup.backup import _get_dirs
    >>> _get_dirs('/tmp')
    [...]
    """
    for root, dirs, files in walk(path):
        return [dir for dir in dirs if is_timestamp(dir)]


def load_backups(config):
    """get list of backups for given `config`

    :param config dict:
    :return list: list of `Backup`
    """
    path = config['backups']
    dirs = _get_dirs(path)
    backups = []
    for dir in reversed(dirs):
        if len(backups) == 0:
            backups.insert(0, Backup(dir, path, config))
        else:
            backups.insert(0, Backup(dir, path, config, backups[0]))
    return backups


class Backup(object):
    """Used as a container for all metadata attached to a finished backup.

    """

    name: str
    """name, coincidently also the iso timestamp string"""

    path: str
    """basepath this backup resides in"""

    config: dict
    """copy of config dictionary"""

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

    def __init__(self, name: str, path: str, config: dict, next=None):
        """initialize a backup object.

        :param name str: name of this backup, also a iso timestamp
        :param path str: path where this backup resides
        :param config dict: config object for this backup
        :param next Backup: successive backup object
        """
        self.name = name
        self.path = path
        self.config = config
        self.datetime = parse_timestamp(name)
        self.is_inside_retain_all_interval = self._is_after(config['retain_all_after'])
        self.is_inside_retain_daily_interval = self._is_after(config['retain_daily_after'])
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
