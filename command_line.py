#!/usr/bin/env python3

import argparse
import logging
import os
import signal
import sys

from snapshotbackup import list_backups, make_backup, purge_backups, setup_paths
from snapshotbackup.config import parse_config
from snapshotbackup.lock import LockPathError


logger = logging.getLogger()


def main(args):     # noqa: C901
    config = _load_config(args.config, args.name)
    try:
        if args.action in ['s', 'setup']:
            logger.debug(f'setup paths w/ config `{config}`')
            setup_paths(config, silent=args.silent)
        elif args.action in ['b', 'backup']:
            logger.debug(f'make backup w/ config `{config}`')
            make_backup(config, silent=args.silent)
        elif args.action in ['l', 'list']:
            logger.debug(f'list backups w/ config `{config}`')
            list_backups(config)
        elif args.action in ['p', 'purge']:
            logger.debug(f'purge backups w/ config `{config}`')
            purge_backups(config, silent=args.silent)
    except FileNotFoundError as e:
        logger.error(f'file `{e.filename}` not found, maybe missing software?')
    except LockPathError as e:
        logger.error(e)
    else:
        return True


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['setup', 's', 'backup', 'b', 'list', 'l', 'purge', 'p'],
                        help='setup backup paths, make backup, list backups'
                             ' or purge backups not held by retention policy')
    parser.add_argument('name',
                        help='section name in config file')
    parser.add_argument('-c', '--config', type=open, required=True, metavar='filename',
                        help='use given config file')
    parser.add_argument('-s', '--silent', action='store_true',
                        help='suppress output on stdout')
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


def _signal_handler(signal, frame):
    sys.exit(f'got signal `{signal}`, exit')


if __name__ == '__main__':
    try:
        signal.signal(signal.SIGTERM, _signal_handler)
        args = _parse_args()
        _init_logger(args.verbose)
        logger.info(f'snapshotbackup start w/ pid `{os.getpid()}`')
        success = main(args)
        logger.info(f'snapshotbackup finished with `{success}`')
        sys.exit(not success)  # invert bool for UNIX
    except KeyboardInterrupt:
        sys.exit('keyboard interrupt, exit')
