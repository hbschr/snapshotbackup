#!/usr/bin/env python3

import argparse
import logging
import sys

from btrfsbackup import make_backup, purge_backups
from btrfsbackup.config import parse_config
from btrfsbackup.backup import load_backups


logger = logging.getLogger()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', type=open, required=True, metavar='filename',
                        help='use given config file')
    parser.add_argument('name',
                        help='section name in config file')
    parser.add_argument('-b', '--backup', action='store_true',
                        help='make backup')
    parser.add_argument('-l', '--list', action='store_true',
                        help='list backups')
    parser.add_argument('-p', '--purge', action='store_true',
                        help='purge backups not held by retention policy')
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help='increase verbosity, may be used twice')
    args = parser.parse_args()

    config = _load_config(args.config, args.name)
    _init_logger(args.verbose)

    if args.backup:
        logger.debug(f'make backup w/ config `{config}`')
        return make_backup(config)
    elif args.list:
        logger.debug(f'list backups w/ config `{config}`')
        return list_backups(config)
    elif args.purge:
        logger.debug(f'purge backups w/ config `{config}`')
        return purge_backups(config)

    print('missing argument, either `-b`, `-l` or `-p` is mandatory.', file=sys.stderr)
    parser.print_help()
    return False


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
    logger.debug('btrfsbackup start')
    success = main()
    logger.debug('btrfsbackup finished with `{}`'.format(success))
    sys.exit(not success)   # invert bool for UNIX
