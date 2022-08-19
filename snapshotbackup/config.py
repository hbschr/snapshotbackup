import configparser
import csv
import os
from pathlib import Path

from xdg import (XDG_CONFIG_DIRS, XDG_CONFIG_HOME)

from snapshotbackup.exceptions import ConfigFileNotFound
from .timestamps import parse_human_readable_relative_dates


_config_filename = 'snapshotbackup.ini'
_config_basepaths = (XDG_CONFIG_HOME, *XDG_CONFIG_DIRS, Path('/etc'))
_defaults = {
    'ignore': '',
    'retain_all': '1 day',
    'retain_daily': '1 month',
    'decay': '1 year',
    'autodecay': '',
    'autoprune': '',
}


def _get_config_file(filepath=None):
    """check if config file exists in fs. if `filepath` is not given search xdg config paths and `/etc` for a file
    named :data:`_config_filename`.

    :param filepath:
    :return Path: path to config file or None
    :raise snapshotbackup.exceptions.ConfigFileNotFound: when config file cannot be found
    """
    if filepath:
        if os.path.isfile(filepath):
            return filepath
        raise ConfigFileNotFound(filepath)

    _config_files = (_path / _config_filename for _path in _config_basepaths)
    for _filepath in _config_files:
        if os.path.isfile(_filepath):
            return _filepath
    raise ConfigFileNotFound(_config_files)


def _parse_bool(line):
    """parse a string input to boolean.

    :param str line:
    :return bool:

    >>> from snapshotbackup.config import _parse_bool
    >>> _parse_bool('true') and _parse_bool('True') and _parse_bool('1')
    True
    >>> _parse_bool('') or _parse_bool('0') or _parse_bool('foo')
    False
    """
    return line in ('true', 'True', '1')


def _parse_ignore(line):
    """get a line of comma seperated values and return items.

    :param str line: section in ini file to use
    :return tuple:

    >>> from snapshotbackup.config import _parse_ignore
    >>> _parse_ignore('item1')
    ('item1',)
    >>> _parse_ignore('item1,item2')
    ('item1', 'item2')
    >>> _parse_ignore('item1, item2')
    ('item1', 'item2')
    >>> _parse_ignore('string with whitespaces')
    ('string with whitespaces',)
    >>> _parse_ignore('"double quoted string with , comma"')
    ('double quoted string with , comma',)
    >>> _parse_ignore('42')
    ('42',)
    >>> len(_parse_ignore(r'string with escaped \\, comma')) == 1
    False
    >>> len(_parse_ignore("'single quoted string with , comma'")) == 1
    False
    >>> _parse_ignore('item1\\nitem2')
    Traceback (most recent call last):
    _csv.Error: ...
    """
    # mimic multiple lines w/ list
    parser = csv.reader([line])
    return tuple(item.strip() for row in parser for item in row)


def parse_config(filepath, section):
    """parse ini file and return dictionary for given section

    :param str filepath: path to config file
    :param str section: section in ini file to use
    :return dict:
    :raise configparser.NoSectionError: when given `section` is not found
    :raise snapshotbackup.exceptions.ConfigFileNotFound: when config file cannot be found
    """
    config = configparser.ConfigParser(defaults=_defaults)
    config.read(_get_config_file(filepath))
    if not config.has_section(section):
        raise configparser.NoSectionError(section)
    return {
        'source': config[section]['source'],
        'backups': config[section]['backups'],
        'ignore': _parse_ignore(config[section]['ignore']),
        'retain_all_after': parse_human_readable_relative_dates(config[section]['retain_all']),
        'retain_daily_after': parse_human_readable_relative_dates(config[section]['retain_daily']),
        'decay_before': parse_human_readable_relative_dates(config[section]['decay']),
        'autodecay': _parse_bool(config[section]['autodecay']),
        'autoprune': _parse_bool(config[section]['autoprune']),
    }
