import argparse
import configparser
import logging
import os
import signal
import sys
from os import makedirs
from os.path import join as path_join
from pkg_resources import get_distribution
from setuptools_scm import get_version as get_scm_version

from .backupdir import BackupDir
from .config import parse_config
from .exceptions import BackupDirError, CommandNotFoundError, LockedError, LockPathError, SyncFailedError, \
    TimestampParseError
from .shell import delete_subvolume, make_snapshot, rsync

try:
    __version__ = get_scm_version()
except LookupError as e:
    __version__ = get_distribution(__name__).version

logger = logging.getLogger()


def make_backup(config, silent=False):
    """make a backup for given configuration.

    :return None:
    """
    logger.debug(f'make backup w/ config `{config}`')
    vol = BackupDir(config['backups'], assert_syncdir=True)
    with vol.lock():
        rsync(config['source'], vol.sync_dir, exclude=config['ignore'], silent=silent)
    make_snapshot(vol.sync_dir, vol.new_snapshot_path(), silent=silent)


def list_backups(config):
    """list all backups for given configuration.

    :return None:
    """
    logger.debug(f'list backups w/ config `{config}`')
    vol = BackupDir(config['backups'])
    for backup in vol.get_backups(config['retain_all_after'], config['retain_daily_after']):
        retain_all = backup.is_inside_retain_all_interval
        retain_daily = backup.is_inside_retain_daily_interval
        print(f'{backup.name}'
              f'\t{"retain_all" if retain_all else "retain_daily" if retain_daily else "        "}'
              f'\t{"weekly" if backup.is_weekly else "daily" if backup.is_daily else ""}'
              f'\t{"purge candidate" if backup.purge else ""}')


def purge_backups(config, silent=False):
    """delete all backups for given configuration which are not held by retention policy.

    :return None:
    """
    logger.debug(f'purge backups w/ config `{config}`')
    vol = BackupDir(config['backups'])
    backups = vol.get_backups(config['retain_all_after'], config['retain_daily_after'])
    purges = [backup for backup in backups if backup.purge]
    for purge in purges:
        delete_subvolume(path_join(purge.path, purge.name), silent=silent)


def setup_path(config, silent=False):
    """setup backup path for given configuration.

    :return None:
    """
    logger.debug(f'setup paths w/ config `{config}`')
    makedirs(config['backups'], exist_ok=True)


def _parse_args():
    """argument definitions. return parsed args.

    :return: :class:`argparse.Namespace`
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['setup', 's', 'backup', 'b', 'list', 'l', 'purge', 'p'],
                        help='setup backup path (`mkdir -p`), make backup, list backups'
                             ' or purge backups not held by retention policy')
    parser.add_argument('name',
                        help='section name in config file')
    parser.add_argument('-c', '--config', type=open, metavar='filename',
                        help='use given config file')
    parser.add_argument('-s', '--silent', action='store_true',
                        help='suppress output on stdout')
    parser.add_argument('-d', '--debug', action='count', default=0,
                        help='lower logging threshold, may be used twice')
    parser.add_argument('-v', '--version', action='version', version=f'%(prog)s {__version__}',
                        help='print version number and exit')
    return parser.parse_args()


def _init_logger(log_level=0):
    """increase log level.

    :param int log_level: `0` - warning, `1` - info, `2` - debug
    :return None:
    """
    if log_level == 0:
        level = logging.WARNING
    elif log_level == 1:
        level = logging.INFO
    else:
        level = logging.DEBUG
    logging.basicConfig(level=level)


def _exit(error_message=None):
    """log and exit.

    :param str error_message: will be logged. changes exit status to `1`.
    :exit 0: success
    :exit 1: error
    """
    if error_message is None:
        logger.info(f'exit without errors')
        sys.exit()
    logger.error(f'exit with error: {error_message}')
    sys.exit(1)


def _main(configfile, configsection, action, silent=False):  # noqa: C901
    """perform given action on given config/configsection.
    expected errors are logged.

    :param configfile:
    :param configsection:
    :param action:
    :param silent:
    :exit 1: in case of error
    :return None:
    """
    try:
        config = parse_config(configsection, file=configfile)
    except FileNotFoundError as e:
        _exit(f'configuration file `{e.filename}` not found')
    except configparser.NoSectionError as e:
        _exit(f'no configuration for `{e.section}` found')
    except TimestampParseError as e:
        _exit(e)

    try:
        if action in ['s', 'setup']:
            setup_path(config, silent=silent)
        elif action in ['b', 'backup']:
            make_backup(config, silent=silent)
        elif action in ['l', 'list']:
            list_backups(config)
        elif action in ['p', 'purge']:
            purge_backups(config, silent=silent)
    except (BackupDirError, LockPathError) as e:
        _exit(e)
    except CommandNotFoundError as e:
        _exit(f'command `{e.command}` not found, mayhap missing software?')
    except LockedError as e:
        _exit(f'sync folder is locked, aborting. try again later or delete `{e.lockfile}`')
    except SyncFailedError as e:
        _exit(f'backup interrupted or failed, `{e.target}` may be in an inconsistent state')


def _signal_handler(signal, _):
    """handle registered signals, probably just `SIGTERM`."""
    _exit(f'got signal {signal}')


def main():
    """command line entry point.

    - parse arguments
    - init logger
    - call `_main`
    - handle `SIGTERM` and `KeyboardInterrupt`
    - log unhandled exceptions

    :exit 0: success
    :exit 1: interruption
    :exit 2: argument error
    """
    try:
        signal.signal(signal.SIGTERM, _signal_handler)
        args = _parse_args()
        _init_logger(log_level=args.debug)
        logger.info(f'backup {args.name} start w/ pid `{os.getpid()}`')
        _main(configfile=args.config, configsection=args.name, action=args.action, silent=args.silent)
    except KeyboardInterrupt:
        _exit('keyboard interrupt')
    except Exception as e:
        logger.exception(e)
        _exit('uncaught exception')
    _exit()
