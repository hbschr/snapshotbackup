import configparser


from .timestamps import parse_human_readable_relative_dates


_defaults = {
    'retain_all': '1 day',
    'retain_daily': '1 month',
    'ignore': '',
}


def parse_config(filename, section):
    """parse ini file and return dictionary for given section

    :param filename str: config file path
    :param section str: section in ini file to use
    :return dict:
    :raise configparser.NoSectionError: when given `section` is not found
    """
    config = configparser.ConfigParser(defaults=_defaults)
    config.read_file(filename)
    if not config.has_section(section):
        raise configparser.NoSectionError(section)
    return {
        'source': config[section]['source'],
        'backups': config[section]['backups'],
        'ignore': config[section]['ignore'],
        'retain_all_after': parse_human_readable_relative_dates(config.get(section, 'retain_all')),
        'retain_daily_after': parse_human_readable_relative_dates(config.get(section, 'retain_daily')),
    }
