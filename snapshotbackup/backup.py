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
    dirs = _get_dirs(config['backups'])
    backups = []
    for dir in reversed(dirs):
        if len(backups) == 0:
            backups.insert(0, Backup(dir, config))
        else:
            backups.insert(0, Backup(dir, config, backups[0]))
    return backups


class Backup(object):
    name: str
    config: dict
    datetime: datetime
    retain: bool
    is_daily: bool = False
    is_weekly: bool = False
    is_last: bool = False

    def __init__(self, name: str, config: dict, next=None):
        self.name = name
        self.config = config
        self.datetime = parse_timestamp(name)
        if not next:
            self.is_last = True
        else:
            self.is_daily = not is_same_day(self.datetime, next.datetime)
            self.is_weekly = not is_same_week(self.datetime, next.datetime)
        self.retain = self.is_last or self._retain()

    def __str__(self) -> str:
        return '{}\t{}\t{}\t{}\t{}'.format(self.name,
                                           'daily' if self.is_daily else '',
                                           'weekly' if self.is_weekly else '',
                                           'last' if self.is_last else '',
                                           'retain' if self.retain else '')

    def _is_after(self, timestamp):
        return self.datetime > timestamp

    def _retain(self):
        now = self.config['now']
        retain_all = self.config['retain_all']
        retain_daily = self.config['retain_daily']

        if self._is_after(now - retain_all):
            return True

        if self._is_after(now - retain_daily):
            return self.is_daily

        return self.is_weekly
