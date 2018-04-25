import configparser
import sys


from .timestamps import parse_human_readable_relative_dates


_defaults = {
    'retain_all': '1 day',
    'retain_daily': '1 month',
    'ignore': '',
}


def parse_config(file, name):
    config = configparser.ConfigParser(defaults=_defaults)
    config.read_file(file)
    if not config.has_section(name):
        sys.exit(f'no configuration for `{name}` found')
    return {
        'source': config.get(name, 'source'),
        'backups': config.get(name, 'backups'),
        'ignore': config.get(name, 'ignore'),
        'retain_all_after': parse_human_readable_relative_dates(config.get(name, 'retain_all')),
        'retain_daily_after': parse_human_readable_relative_dates(config.get(name, 'retain_daily')),
    }
