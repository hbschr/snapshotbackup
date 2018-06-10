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
from .subprocess import rsync, DEBUG_SHELL

__version__ = get_distribution(__name__).version
logger = logging.getLogger(__name__)


def make_backup(source_dir, backup_dir, ignore, progress=False, checksum=False, dry_run=False):
    """make a backup for given configuration.

    :param str source_dir:
    :param str backup_dir:
    :param str ignore:
    :param bool progress:
    :param bool checksum:
    :param bool dry_run:
    :return: None
    """
    logger.info(f'make backup, source_dir={source_dir}, backup_dir={backup_dir}, ignore={ignore}, progress={progress}')
    vol = BackupDir(backup_dir, assert_syncdir=True)
    with vol.lock():
        if dry_run:
            print(f'dry run, no changes will be made on disk, this is what rsync would do:')
        rsync(source_dir, vol.sync_path, exclude=ignore, checksum=checksum, progress=progress, dry_run=dry_run)
        if dry_run:
            print(f'dry run, no changes were made on disk')
        else:
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
              f'\t{"prune candidate" if backup.prune else ""}')


def prune_backups(backup_dir, retain_all_after, retain_daily_after):
    """delete all backups for given configuration which are not held by retention policy.

    :param str backup_dir:
    :param datetime.datetime retain_all_after:
    :param datetime.datetime retain_daily_after:
    :return: None
    """
    logger.info(f'prune backups, backup_dir={backup_dir}, retain_all_after={retain_all_after},'
                f'retain_daily_after={retain_daily_after}')
    vol = BackupDir(backup_dir)
    backups = vol.get_backups(retain_all_after=retain_all_after, retain_daily_after=retain_daily_after)
    for to_be_pruned in [_b for _b in backups if _b.prune]:
        print(f'prune {to_be_pruned.name}')
        to_be_pruned.delete()


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
    >>> app.name = 'application_name'
    >>> app.args.name = 'backup_name'
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
        logger.info(f'`{app.args.name}` exit without errors')
        sys.exit()
    send_notification(app.name, f'backup `{app.args.name}` failed with error:\n{error_message}', error=True,
                      notify_remote=app.config['notify_remote'])
    logger.error(f'`{app.args.name}` exit with error: {error_message}')
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

    try:
        app.config = parse_config(app.args.name, filepath=app.args.config)
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
            make_backup(app.args.source or _config['source'], _config['backups'], _config['ignore'],
                        progress=app.args.progress, checksum=app.args.checksum, dry_run=app.args.dry_run)
            if not app.args.dry_run:
                send_notification(app.name, f'backup `{app.args.name}` finished',
                                  notify_remote=_config['notify_remote'])
        elif app.args.action in ['l', 'list']:
            list_backups(_config['backups'], _config['retain_all_after'], _config['retain_daily_after'])
        elif app.args.action in ['p', 'prune']:
            prune_backups(_config['backups'], _config['retain_all_after'], _config['retain_daily_after'])
    except BackupDirError as e:
        app.exit(e)
    except CommandNotFoundError as e:
        app.exit(f'command `{e.command}` not found, mayhap missing software?')
    except LockedError as e:
        app.exit(f'sync folder is locked, aborting. try again later or delete `{e.lockfile}`')
    except SyncFailedError as e:
        app.exit(f'backup interrupted or failed, `{e.target}` may be in an inconsistent state')


main.argparser.add_argument('action', choices=['setup', 's', 'backup', 'b', 'list', 'l', 'prune', 'p'],
                            help='setup backup path (`mkdir -p`), make backup, list backups '
                                 'or prune backups not held by retention policy')
main.argparser.add_argument('name', help='section name in config file')
main.argparser.add_argument('-c', '--config', metavar='CONFIGFILE', help='use given config file')
main.argparser.add_argument('-d', '--debug', action='count', default=0,
                            help='lower logging threshold, may be used thrice')
main.argparser.add_argument('-p', '--progress', action='store_true', help='print progress on stdout')
main.argparser.add_argument('-s', '--silent', action='store_true',
                            help='silent mode: log errors, warnings and `--debug` to journald instead of stdout '
                                 '(extra dependencies needed, install with `pip install snapshotbackup[journald]`)')
main.argparser.add_argument('--checksum', action='store_true',
                            help='detect changes by checksum instead of file size and modification time, '
                                 'increases disk load significantly (triggers `rsync --checksum`)')
main.argparser.add_argument('--dry-run', action='store_true',
                            help='pass `--dry-run` to rsync and display rsync output, no changes are made on disk')
main.argparser.add_argument('--source', help='use given path as source for backup, replaces `source` from config file')
main.argparser.add_argument('-v', '--version', action='version', version=f'%(prog)s {__version__}',
                            help='print version number and exit')
