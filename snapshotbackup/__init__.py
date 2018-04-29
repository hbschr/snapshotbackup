import argparse
import logging
import os
from os import makedirs
from os.path import join as path_join
import signal
import subprocess
import sys


from .backup import load_backups
from .config import parse_config
from .lock import Lock, LockedError, LockPathError
from .shell import create_subvolume, delete_subvolume, make_snapshot, rsync
from .timestamps import get_timestamp


logger = logging.getLogger()
_sync_dir = '.sync'


def make_backup(config, silent=False):
    """make a backup for given configuration."""
    sync_target = f'{config["backups"]}/{_sync_dir}'
    logger.info(f'syncing `{config["source"]}` to `{sync_target}`')
    try:
        with Lock(config['backups']):
            rsync(config['source'], sync_target, exclude=config['ignore'], silent=silent)
    except subprocess.CalledProcessError as e:
        logger.error(e)
        sys.exit(f'backup interrupted or failed, `{sync_target}` may be in an inconsistent state')
    except LockedError as e:
        logger.warning(e)
        sys.exit(f'sync folder is locked, aborting. try again later or delete `{e.lockfile}`')
    timestamp = get_timestamp().isoformat()
    snapshot_target = f'{config["backups"]}/{timestamp}'
    logger.info(f'snapshotting `{sync_target}` to `{snapshot_target}`')
    make_snapshot(sync_target, snapshot_target, silent=silent)


def list_backups(config):
    backups = load_backups(config)
    for backup in backups:
        retain_all = backup.is_inside_retain_all_interval
        retain_daily = backup.is_inside_retain_daily_interval
        print(f'{backup.name}'
              f'\t{"retain_all" if retain_all else "retain_daily" if retain_daily else "        "}'
              f'\t{"weekly" if backup.is_weekly else "daily" if backup.is_daily else ""}'
              f'\t{"purge candidate" if backup.purge else ""}')


def purge_backups(config, silent=False):
    """delete all backups for given configuration which are not held by retention policy."""
    backups = load_backups(config)
    purges = [backup for backup in backups if backup.purge]
    for purge in purges:
        logger.info(f'purging `{purge.name}` in path `{purge.path}`')
        delete_subvolume(path_join(purge.path, purge.name), silent=silent)


def setup_paths(config, silent=False):
    """setup backup paths for given configuration."""
    makedirs(config['backups'], exist_ok=True)
    sync_target = f'{config["backups"]}/{config["sync_dir"]}'
    logger.info(f'create subvolume `{sync_target}`')
    create_subvolume(sync_target, silent=silent)


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


def _main_switch(args): # noqa: C901
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
    except NotADirectoryError as e:
        logger.error(f'not a directory: `{e}`')
    except FileNotFoundError as e:
        logger.error(f'file `{e.filename}` not found, maybe missing software?')
    except LockPathError as e:
        logger.error(e)
    else:
        return True


def main():
    try:
        signal.signal(signal.SIGTERM, _signal_handler)
        args = _parse_args()
        _init_logger(args.verbose)
        logger.info(f'snapshotbackup start w/ pid `{os.getpid()}`')
        success = _main_switch(args)
        logger.info(f'snapshotbackup finished with `{success}`')
        sys.exit(not success)  # invert bool for UNIX
    except KeyboardInterrupt:
        sys.exit('keyboard interrupt, exit')
