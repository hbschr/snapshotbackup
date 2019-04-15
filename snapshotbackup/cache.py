import configparser
import os
from xdg import (XDG_CACHE_HOME)

from snapshotbackup.exceptions import TimestampParseError
from snapshotbackup.timestamps import parse_timestamp

_CACHE_DIR = XDG_CACHE_HOME / 'snapshotbackup'
_STAT_FILE = _CACHE_DIR / 'statistic.ini'


def _get_stats_parser():
    """return configparser object and preload it with current statistics from fs.

    :return configparser.ConfigParser:
    """
    parser = configparser.ConfigParser()
    parser.read(_STAT_FILE)
    return parser


def get_last_run(backup_name):
    """get datetime of last run for given backup name from cache file.

    :param str backup_name:
    :return: timestamp of last backup run or None
    """
    parser = _get_stats_parser()
    try:
        return parse_timestamp(parser.get(backup_name, 'last_run'))
    except (configparser.NoSectionError, configparser.NoOptionError, TimestampParseError):
        return None


def set_last_run(backup_name, value):
    """persist datetime of last run for given backup name in cache file.

    :param str backup_name:
    :param datetime.datetime value:
    :return: None
    """
    parser = _get_stats_parser()
    if not parser.has_section(backup_name):
        parser.add_section(backup_name)
    parser.set(backup_name, 'last_run', str(value))
    os.makedirs(_CACHE_DIR, exist_ok=True)
    parser.write(open(_STAT_FILE, 'w'))
