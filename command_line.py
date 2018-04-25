#!/usr/bin/env python3

import argparse
import logging
import sys

from snapshotbackup import make_backup, purge_backups
from snapshotbackup.config import parse_config
from snapshotbackup.backup import load_backups


logger = logging.getLogger()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['backup', 'b', 'list', 'l', 'purge', 'p'],
                        help='make backup, list backups or purge backups not held by retention policy')
    parser.add_argument('name',
                        help='section name in config file')
    parser.add_argument('-c', '--config', type=open, required=True, metavar='filename',
                        help='use given config file')
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help='increase verbosity, may be used twice')
    args = parser.parse_args()

    config = _load_config(args.config, args.name)
    _init_logger(args.verbose)

    if args.action in ['l', 'list']:
        logger.debug(f'list backups w/ config `{config}`')
        return list_backups(config)
    elif args.action in ['b', 'backup']:
        logger.debug(f'make backup w/ config `{config}`')
        return make_backup(config)
    elif args.action in ['p', 'purge']:
        logger.debug(f'purge backups w/ config `{config}`')
        return purge_backups(config)


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
        print(backup)
    return True


if __name__ == '__main__':
    logger.debug('snapshotbackup start')
    success = main()
    logger.debug('snapshotbackup finished with `{}`'.format(success))
    sys.exit(not success)   # invert bool for UNIX
