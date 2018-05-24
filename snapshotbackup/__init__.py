import argparse
import configparser
import importlib
import logging
import os
import signal
import sys
from pkg_resources import get_distribution

from .notify import send_notification
from .backupdir import BackupDir
from .config import parse_config
from .exceptions import BackupDirError, CommandNotFoundError, LockedError, SyncFailedError, TimestampParseError
from .subprocess import delete_subvolume, rsync, DEBUG_SHELL

__version__ = get_distribution(__name__).version

logger = logging.getLogger(__name__)


def make_backup(source_dir, backup_dir, ignore, progress):
    """make a backup for given configuration.

    :param str source_dir:
    :param str backup_dir:
    :param str ignore:
    :param bool progress:
    :return: None
    """
    logger.info(f'make backup, source_dir={source_dir}, backup_dir={backup_dir}, ignore={ignore}, progress={progress}')
    vol = BackupDir(backup_dir, assert_syncdir=True)
    with vol.lock():
        rsync(source_dir, vol.sync_path, exclude=ignore, progress=progress)
        vol.snapshot_sync()


def list_backups(backup_dir, retain_all_after, retain_daily_after):
    """list all backups for given configuration.

    :param str backup_dir:
    :param datetime.datetime retain_all_after:
    :param datetime.datetime retain_daily_after:
    :return: None
    """
    logger.info(f'list backups, backup_dir={backup_dir}, retain_all_after={retain_all_after}, '
                f'retain_daily_after={retain_daily_after}')
    vol = BackupDir(backup_dir)
    for backup in vol.get_backups(retain_all_after=retain_all_after, retain_daily_after=retain_daily_after):
        retain_all = backup.is_inside_retain_all_interval
        retain_daily = backup.is_inside_retain_daily_interval
        print(f'{backup.name}'
              f'\t{"retain_all" if retain_all else "retain_daily" if retain_daily else "        "}'
              f'\t{"weekly" if backup.is_weekly else "daily" if backup.is_daily else ""}'
              f'\t{"purge candidate" if backup.purge else ""}')


def purge_backups(backup_dir, retain_all_after, retain_daily_after):
    """delete all backups for given configuration which are not held by retention policy.

    :param str backup_dir:
    :param datetime.datetime retain_all_after:
    :param datetime.datetime retain_daily_after:
    :return: None
    """
    logger.info(f'purge backups, backup_dir={backup_dir}, retain_all_after={retain_all_after},'
                f'retain_daily_after={retain_daily_after}')
    vol = BackupDir(backup_dir)
    backups = vol.get_backups(retain_all_after=retain_all_after, retain_daily_after=retain_daily_after)
    for purge in [_b for _b in backups if _b.purge]:
        print(f'purge {purge.name}')
        delete_subvolume(purge.path)


def setup_path(path):
    """assert given path exists.

    >>> import os.path, tempfile
    >>> from snapshotbackup import setup_path
    >>> with tempfile.TemporaryDirectory() as path:
    ...     newdir = os.path.join(path, 'long', 'path')
    ...     setup_path(newdir)
    ...     os.path.isdir(newdir)
    True

    :param str path:
    :return: None
    """
    logger.info(f'setup path `{path}`')
    os.makedirs(path, exist_ok=True)


def _init_logger(log_level=0, silent=False):
    """increase log level.

    >>> from snapshotbackup import _init_logger
    >>> _init_logger(0)
    >>> _init_logger(1)
    >>> _init_logger(2)
    >>> _init_logger(3)

    :param int log_level: `0` - warning, `1` - info, `2` - debug, `3` - debug w/ shell output
    :return: None
    """
    if log_level == 0:
        level = logging.WARNING
    elif log_level == 1:
        level = logging.INFO
    elif log_level == 2:
        level = logging.DEBUG
    else:
        level = DEBUG_SHELL
    handlers = [importlib.import_module('systemd.journal').JournalHandler(SYSLOG_IDENTIFIER=__name__)] \
        if silent else None
    logging.basicConfig(level=level, handlers=handlers)


def _exit(error_message=None):
    """log and exit.

    >>> from snapshotbackup import _exit
    >>> _exit()
    Traceback (most recent call last):
    SystemExit
    >>> try:
    ...     _exit()
    ... except SystemExit as e:
    ...     assert e.code is None
    >>> try:
    ...     _exit('xxx')
    ... except SystemExit as e:
    ...     assert e.code == 1

    :param str error_message: will be logged. changes exit status to `1`.
    :exit 0: success
    :exit 1: error
    """
    if error_message is None:
        logger.info(f'pid `{os.getpid()}` exit without errors')
        sys.exit()
    logger.error(f'pid `{os.getpid()}` exit with error: {error_message}')
    sys.exit(1)


def _main(configfile, configsection, action, source, progress):  # noqa: C901
    """perform given action on given config/configsection.
    expected errors are logged.

    :param configfile:
    :param str configsection:
    :param str action:
    :param str source:
    :param bool progress:
    :exit 1: in case of error
    :return: None
    """
    try:
        config = parse_config(configsection, filepath=configfile)
    except FileNotFoundError as e:
        _exit(f'configuration file `{e.filename}` not found')
    except configparser.NoSectionError as e:
        _exit(f'no configuration for `{e.section}` found')
    except TimestampParseError as e:
        _exit(e)

    try:
        if action in ['s', 'setup']:
            setup_path(config['backups'])
        elif action in ['b', 'backup']:
            make_backup(config['source'] if source is None else source, config['backups'], config['ignore'], progress)
            send_notification(__name__, f'backup `{configsection}` finished', notify_remote=config['notify_remote'])
        elif action in ['l', 'list']:
            list_backups(config['backups'], config['retain_all_after'], config['retain_daily_after'])
        elif action in ['p', 'purge']:
            purge_backups(config['backups'], config['retain_all_after'], config['retain_daily_after'])
    except BackupDirError as e:
        _exit(e)
    except CommandNotFoundError as e:
        _exit(f'command `{e.command}` not found, mayhap missing software?')
    except LockedError as e:
        _exit(f'sync folder is locked, aborting. try again later or delete `{e.lockfile}`')
    except SyncFailedError as e:
        _exit(f'backup interrupted or failed, `{e.target}` may be in an inconsistent state')


def _parse_args():
    """argument definitions. return parsed args.

    >>> from snapshotbackup import _parse_args
    >>> try:
    ...     _parse_args()
    ... except SystemExit as e:
    ...     e.code
    2

    :exit 2: argument error
    :return: :class:`argparse.Namespace`
    """
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['setup', 's', 'backup', 'b', 'list', 'l', 'purge', 'p'],
                   help='setup backup path (`mkdir -p`), make backup, list backups '
                        'or purge backups not held by retention policy')
    p.add_argument('name', help='section name in config file')
    p.add_argument('-c', '--config', metavar='CONFIGFILE', help='use given config file')
    p.add_argument('-d', '--debug', action='count', default=0, help='lower logging threshold, may be used thrice')
    p.add_argument('-p', '--progress', action='store_true', help='print progress on stdout')
    p.add_argument('-s', '--silent', action='store_true', help='silent mode: log to journald instead of stdout '
                                                               '(install with extra `journald`, e.g. `pip install '
                                                               'snapshotbackup[journald]`)')
    p.add_argument('--source', help='use given path as source for backup')
    p.add_argument('-v', '--version', action='version', version=f'%(prog)s {__version__}', help='print version number '
                                                                                                'and exit')
    return p.parse_args()


def _signal_handler(signal, _):
    """handle registered signals, probably just `SIGTERM`.

    >>> from snapshotbackup import _signal_handler
    >>> try:
    ...     _signal_handler('signal', 'frame')
    ... except SystemExit as e:
    ...     e.code
    1

    :exit 1:
    """
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
        _init_logger(log_level=args.debug, silent=args.silent)
        logger.info(f'start `{args.name}` w/ pid `{os.getpid()}`')
        _main(configfile=args.config, configsection=args.name, action=args.action, source=args.source,
              progress=args.progress)
    except KeyboardInterrupt:
        _exit('keyboard interrupt')
    except Exception as e:
        logger.exception(e)
        _exit('uncaught exception')
    _exit()
