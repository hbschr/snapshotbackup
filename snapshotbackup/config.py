import configparser
import csv


from .timestamps import parse_human_readable_relative_dates


_defaults = {
    'ignore': '',
    'retain_all': '1 day',
    'retain_daily': '1 month',
    'decay': '1 year',
    'autodecay': '',
    'autoprune': '',
    'silent_fail_threshold': '3 days',
    'notify_remote': '',
}


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
    >>> len(_parse_ignore('string with escaped \\, comma')) == 1
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
    :raise FileNotFoundError: when config file cannot be found
    :raise configparser.NoSectionError: when given `section` is not found
    """
    config = configparser.ConfigParser(defaults=_defaults)
    config.read(filepath)
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
        'silent_fail_threshold': parse_human_readable_relative_dates(config[section]['silent_fail_threshold']),
        'notify_remote': config[section]['notify_remote'] or None,
    }
