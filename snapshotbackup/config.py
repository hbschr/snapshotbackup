import configparser
import sys


from .timestamps import parse_human_readable_relative_dates


_defaults = {
    'retain_all': '1 day',
    'retain_daily': '1 month',
    'ignore': '',
    'sync_dir': 'current',
}


def parse_config(file, name):
    config = configparser.ConfigParser(defaults=_defaults)
    config.read_file(file)
    if not config.has_section(name):
        sys.exit(f'no configuration for `{name}` found')
    return {
        'source': config[name]['source'],
        'backups': config[name]['backups'],
        'ignore': config[name]['ignore'],
        'sync_dir': config[name]['sync_dir'],
        'retain_all_after': parse_human_readable_relative_dates(config.get(name, 'retain_all')),
        'retain_daily_after': parse_human_readable_relative_dates(config.get(name, 'retain_daily')),
    }
