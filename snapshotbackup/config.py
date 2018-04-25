import configparser
from datetime import timedelta
import sys


from .timestamps import get_timestamp


def parse_config(file, name):
    config = configparser.ConfigParser()
    config.read_file(file)
    if not config.has_section(name):
        sys.exit(f'no configuration for `{name}` found')
    return {
        'source': config.get(name, 'source'),
        'backups': config.get(name, 'backups'),
        'ignore': config.get(name, 'ignore'),
        'now': get_timestamp(),
        'retain_all': timedelta(hours=24),
        'retain_daily': timedelta(days=31),
    }
