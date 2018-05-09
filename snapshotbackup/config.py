import configparser


from .timestamps import parse_human_readable_relative_dates


_default_path = '/etc/snapshotbackup.ini'

_defaults = {
    'retain_all': '1 day',
    'retain_daily': '1 month',
    'ignore': '',
}


def parse_config(section, file=None):
    """parse ini file and return dictionary for given section

    :param io.TextIOBase file: config file
    :param str section: section in ini file to use
    :return dict:
    :raise FileNotFoundError: when config file cannot be found
    :raise configparser.NoSectionError: when given `section` is not found
    """
    if not file:
        file = open(_default_path)
    config = configparser.ConfigParser(defaults=_defaults)
    config.read_file(file)
    if not config.has_section(section):
        raise configparser.NoSectionError(section)
    return {
        'source': config[section]['source'],
        'backups': config[section]['backups'],
        'ignore': config[section]['ignore'],
        'retain_all_after': parse_human_readable_relative_dates(config.get(section, 'retain_all')),
        'retain_daily_after': parse_human_readable_relative_dates(config.get(section, 'retain_daily')),
    }
