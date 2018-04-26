#!/usr/bin/env python3

import argparse
import logging
import sys

from snapshotbackup import make_backup, purge_backups
from snapshotbackup.config import parse_config
from snapshotbackup.backup import load_backups


logger = logging.getLogger()


def main():
    args = _parse_args()
    config = _load_config(args.config, args.name)
    _init_logger(args.verbose)

    try:
        if args.action in ['l', 'list']:
            logger.debug(f'list backups w/ config `{config}`')
            list_backups(config)
        elif args.action in ['b', 'backup']:
            logger.debug(f'make backup w/ config `{config}`')
            make_backup(config)
        elif args.action in ['p', 'purge']:
            logger.debug(f'purge backups w/ config `{config}`')
            purge_backups(config)
    except FileNotFoundError as e:
        logger.error(f'file `{e.filename}` not found, maybe missing software?')
        return False
    else:
        return True


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['backup', 'b', 'list', 'l', 'purge', 'p'],
                        help='make backup, list backups or purge backups not held by retention policy')
    parser.add_argument('name',
                        help='section name in config file')
    parser.add_argument('-c', '--config', type=open, required=True, metavar='filename',
                        help='use given config file')
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help='increase verbosity, may be used twice')
    return parser.parse_args()


def _init_logger(verbosity):
    if verbosity == 0:
        level = logging.WARNING
    elif verbosity == 1:
        level = logging.INFO
    else:
        level = logging.DEBUG
    logging.basicConfig(level=level)


def _load_config(file, section):
    logger.debug(f'parse config file `{file}`, section `{section}`')
    return parse_config(file, section)


def list_backups(config):
    backups = load_backups(config)
    for backup in backups:
        retain_all = backup.is_inside_retain_all_interval
        retain_daily = backup.is_inside_retain_daily_interval
        print(f'{backup.name}'
              f'\t{"retain_all" if retain_all else "retain_daily" if retain_daily else "        "}'
              f'\t{"weekly" if backup.is_weekly else "daily" if backup.is_daily else ""}'
              f'\t{"purge candidate" if backup.purge else ""}')


if __name__ == '__main__':
    logger.debug('snapshotbackup start')
    success = main()
    logger.debug(f'snapshotbackup finished with `{success}`')
    sys.exit(not success)   # invert bool for UNIX
