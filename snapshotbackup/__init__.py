import configparser
import importlib
import logging
import os
import sys
from csboilerplate import cli_app
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


def _exit(app, error_message=None):
    """log and exit.

    >>> from unittest.mock import Mock
    >>> from snapshotbackup import _exit
    >>> app = Mock()
    >>> app.config = {'notify_remote': None}
    >>> _exit(app)
    Traceback (most recent call last):
    SystemExit
    >>> try:
    ...     _exit(app)
    ... except SystemExit as e:
    ...     assert e.code is None
    >>> try:
    ...     _exit(app, 'xxx')
    ... except SystemExit as e:
    ...     assert e.code == 1

    :param str error_message: will be logged. changes exit status to `1`.
    :exit 0: success
    :exit 1: error
    """
    if error_message is None:
        logger.info(f'pid `{os.getpid()}` exit without errors')
        sys.exit()
    send_notification(__name__, f'backup failed with error:\n{error_message}', error=True,
                      notify_remote=app.config['notify_remote'])
    logger.error(f'pid `{os.getpid()}` exit with error: {error_message}')
    sys.exit(1)


@cli_app(name=__name__, exit_handler=_exit)  # noqa: C901
def main(app):
    try:
        handlers = [importlib.import_module('systemd.journal').JournalHandler(SYSLOG_IDENTIFIER=app.name)] \
            if app.args.silent else None
        app.logging_config(log_level=app.args.debug, handlers=handlers,
                           log_levels=[logging.WARNING, logging.INFO, logging.DEBUG, DEBUG_SHELL])
    except ModuleNotFoundError as e:
        app.exit(f'dependency for optional feature not found, missing module: {e.name}')
    except IndexError:
        app.exit('debugging doesn\'t go that far, remove one `-d`')
    logger.info(f'start `{app.args.name}` w/ pid `{os.getpid()}`')

    configsection = app.args.name
    try:
        app.config = parse_config(configsection, filepath=app.args.config)
    except FileNotFoundError as e:
        app.exit(f'configuration file `{e.filename}` not found')
    except configparser.NoSectionError as e:
        app.exit(f'no configuration for `{e.section}` found')
    except TimestampParseError as e:
        app.exit(e)

    _config = app.config
    try:
        if app.args.action in ['s', 'setup']:
            setup_path(_config['backups'])
        elif app.args.action in ['b', 'backup']:
            make_backup(app.args.source or _config['source'], _config['backups'], _config['ignore'], app.args.progress)
            send_notification(__name__, f'backup `{configsection}` finished', notify_remote=_config['notify_remote'])
        elif app.args.action in ['l', 'list']:
            list_backups(_config['backups'], _config['retain_all_after'], _config['retain_daily_after'])
        elif app.args.action in ['p', 'purge']:
            purge_backups(_config['backups'], _config['retain_all_after'], _config['retain_daily_after'])
    except BackupDirError as e:
        app.exit(e)
    except CommandNotFoundError as e:
        app.exit(f'command `{e.command}` not found, mayhap missing software?')
    except LockedError as e:
        app.exit(f'sync folder is locked, aborting. try again later or delete `{e.lockfile}`')
    except SyncFailedError as e:
        app.exit(f'backup interrupted or failed, `{e.target}` may be in an inconsistent state')


main.argparser.add_argument('action', choices=['setup', 's', 'backup', 'b', 'list', 'l', 'purge', 'p'],
                            help='setup backup path (`mkdir -p`), make backup, list backups '
                            'or purge backups not held by retention policy')
main.argparser.add_argument('name', help='section name in config file')
main.argparser.add_argument('-c', '--config', metavar='CONFIGFILE', help='use given config file')
main.argparser.add_argument('-d', '--debug', action='count', default=0,
                            help='lower logging threshold, may be used thrice')
main.argparser.add_argument('-p', '--progress', action='store_true', help='print progress on stdout')
main.argparser.add_argument('-s', '--silent', action='store_true',
                            help='silent mode: log to journald instead of stdout (install with extra `journald`, e.g. '
                                 '`pip install snapshotbackup[journald]`)')
main.argparser.add_argument('--source', help='use given path as source for backup')
main.argparser.add_argument('-v', '--version', action='version', version=f'%(prog)s {__version__}',
                            help='print version number and exit')
