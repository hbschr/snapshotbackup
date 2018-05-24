import configparser


from .timestamps import parse_human_readable_relative_dates


_default_filepath = '/etc/snapshotbackup.ini'

_defaults = {
    'retain_all': '1 day',
    'retain_daily': '1 month',
    'ignore': '',
    'notify_remote': None,
}


def parse_config(section, filepath=None):
    """parse ini file and return dictionary for given section

    :param str section: section in ini file to use
    :param str filepath: path to config file
    :return dict:
    :raise FileNotFoundError: when config file cannot be found
    :raise configparser.NoSectionError: when given `section` is not found
    """
    config = configparser.ConfigParser(defaults=_defaults)
    config.read(filepath or _default_filepath)
    if not config.has_section(section):
        raise configparser.NoSectionError(section)
    return {
        'source': config[section]['source'],
        'backups': config[section]['backups'],
        'ignore': config[section]['ignore'],
        'retain_all_after': parse_human_readable_relative_dates(config[section]['retain_all']),
        'retain_daily_after': parse_human_readable_relative_dates(config[section]['retain_daily']),
        'notify_remote': config[section]['notify_remote'],
    }
