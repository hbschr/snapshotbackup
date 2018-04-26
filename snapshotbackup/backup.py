from datetime import datetime
from os import walk


from .timestamps import is_same_day, is_same_week, is_timestamp, parse_timestamp


def _get_dirs(path):
    """

    :param path:
    :return list: backups available in `path`

    >>> from snapshotbackup.backup import _get_dirs
    >>> _get_dirs('/tmp')
    [...]
    """
    for root, dirs, files in walk(path):
        return [dir for dir in dirs if is_timestamp(dir)]


def load_backups(config):
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
    name: str
    path: str
    config: dict
    datetime: datetime
    is_last: bool = False
    is_daily: bool = False
    is_weekly: bool = False
    is_inside_retain_all_interval: bool
    is_inside_retain_daily_interval: bool
    purge: bool = False

    def __init__(self, name: str, path: str, config: dict, next=None):
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
        return self.datetime > timestamp

    def _retain(self):
        if self.is_inside_retain_all_interval:
            return True
        if self.is_inside_retain_daily_interval:
            return self.is_daily
        return self.is_weekly
