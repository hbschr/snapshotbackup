import argparse
import configparser
import importlib
import logging
import os
import signal
import sys

from pkg_resources import get_distribution

from .notify import send_notification
from .worker import Worker
from .config import parse_config
from .exceptions import BackupDirError, BackupDirNotFoundError, CommandNotFoundError, LockedError, \
    SourceNotReachableError, SyncFailedError, TimestampParseError
from .subprocess import DEBUG_SHELL

__version__ = get_distribution(__name__).version
logger = logging.getLogger(__name__)


def _yes_no_prompt(message):
    """prints message, waits for user input and returns `True` if prompt was answered w/ "yes" or "y".

    :param str message:
    :return bool:
    """
    return input(f'{message} [y/N] ').lower() in ('y', 'yes')


def _yes_prompt(message):
    """prints message, exits w/ `True`.

    :param str message:
    :return bool: True

    >>> from snapshotbackup import _yes_prompt
    >>> _yes_prompt('message')
    message
    True
    """
    print(message)
    return True


def list_backups(worker):
    """list all backups for given configuration.

    :param Worker worker:
    :return: None
    """
    logger.info(f'list backups, {worker}')
    for backup in worker.get_backups():
        retain_all = backup.is_retain_all
        retain_daily = backup.is_retain_daily
        print(f'{backup.name}'
              f'\t{"retain_all" if retain_all else "retain_daily" if retain_daily else "        "}'
              f'\t{"weekly" if backup.is_weekly else "daily" if backup.is_daily else ""}'
              f'\t{"prune candidate" if backup.prune else ""}'
              f'\t{"decay candidate" if backup.decay else ""}')


def _get_argument_parser():
    """

    :return argparse.ArgumentParser:

    >>> import argparse
    >>> from snapshotbackup import _get_argument_parser
    >>> assert isinstance(_get_argument_parser(), argparse.ArgumentParser)
    """
    argparser = argparse.ArgumentParser()
    argparser.add_argument('action', choices=['setup', 's', 'backup', 'b', 'list', 'l', 'prune', 'p', 'decay', 'd',
                                              'destroy', 'clean'],
                           help='setup backup path (`mkdir -p`), make backup, list backups, prune backups not '
                                'held by retention policy, decay old backups, destroy all backups or clean backup '
                                'directory')
    argparser.add_argument('name', help='section name in config file')
    argparser.add_argument('-c', '--config', metavar='CONFIGFILE', default='/etc/snapshotbackup.ini',
                           help='use given config file')
    argparser.add_argument('-d', '--debug', action='count', default=0, help='lower logging threshold, may be used '
                                                                            'thrice')
    argparser.add_argument('-p', '--progress', action='store_true', help='print progress on stdout')
    argparser.add_argument('-s', '--silent', action='store_true',
                           help='silent mode: log errors, warnings and `--debug` to journald instead of stdout '
                                '(extra dependencies needed, install with `pip install snapshotbackup[journald]`)')
    argparser.add_argument('--checksum', action='store_true',
                           help='detect changes by checksum instead of file size and modification time, '
                                'increases disk load significantly (triggers `rsync --checksum`)')
    argparser.add_argument('--dry-run', action='store_true', help='pass `--dry-run` to rsync and display rsync '
                                                                  'output, no changes are made on disk')
    argparser.add_argument('--source', help='use given path as source for backup, replaces `source` from config file')
    argparser.add_argument('--yes', action='store_true', help='say yes to each question, allows non-interactive '
                                                              'deletion (prune, decay, destroy)')
    argparser.add_argument('-v', '--version', action='version', version=f'%(prog)s {__version__}',
                           help='print version number and exit')
    return argparser


def main():
    """entry function for setuptools' `console_scripts` entry point.
    it initializes and runs :class:`snapshotbackup.CliApp`.

    :return: None
    """
    app = CliApp()
    app()


# decorators break doctests
# def instance(constructor):
#     return constructor()
#
#
# @instance
class CliApp(object):
    """

    """

    args: argparse.Namespace
    """parsed command line arguments"""

    config: dict = {}
    """parsed config file"""

    name: str = __name__
    """name of this app"""

    def __call__(self, name=__name__, args=sys.argv[1:]):
        """entry point for this `CliApp`.

        :param str name:
        :param list args:
        :return: None
        :exit: always calls :func:`snapshotbackup.CliApp.exit`
        """
        signal.signal(signal.SIGTERM, lambda signal, frame: self.exit('Terminated'))
        self.name = name
        self.args = _get_argument_parser().parse_args(args=args)
        try:
            self._configure_logger()
            logger.info(f'start `{self.args.name}` w/ pid `{os.getpid()}`')
            self._parse_config()
            self._main()
        except KeyboardInterrupt:
            self.exit('KeyboardInterrupt')
        except Exception as e:
            logger.exception(e)
            self.exit('uncaught exception')
        self.exit()

    def _get_journald_handler(self):
        """get logging handler for `journald`.

        :raise ModuleNotFoundError: when module `systemd.journal` couldn't be imported
        :return logging.Handler:
        """
        systemd_journal = importlib.import_module('systemd.journal')
        return systemd_journal.JournalHandler(SYSLOG_IDENTIFIER=self.name)

    def _configure_logger(self):
        """

        :return: None
        :exit: calls :func:`snapshotbackup.CliApp.exit` in case of error
        """
        try:
            handlers = []
            if self.args.silent:
                handlers.append(self._get_journald_handler())
            level = (logging.WARNING, logging.INFO, logging.DEBUG, DEBUG_SHELL)[self.args.debug]
            logging.basicConfig(handlers=handlers, level=level)
        except ModuleNotFoundError as e:
            self.exit(f'dependency for optional feature not found, missing module: {e.name}')
        except IndexError:
            self.exit('debugging doesn\'t go that far, remove one `-d`')

    def _parse_config(self):
        """populate `self.config`. make sure to call this first before relying on `self.config`.

        :return: None
        :exit: calls :func:`snapshotbackup.CliApp.exit` in case of error
        """
        try:
            self.config = parse_config(self.args.name, filepath=self.args.config)
        except FileNotFoundError as e:
            self.exit(f'configuration file `{e.filename}` not found')
        except configparser.NoSectionError as e:
            self.exit(f'no configuration for `{e.section}` found')
        except TimestampParseError as e:
            self.exit(e)

    def notify(self, message, error=False):
        """display message via libnotify.

        :param str message:
        :param bool error:
        :return: None
        """
        send_notification(self.name, message, error=error, notify_remote=self.config.get('notify_remote'))

    def exit(self, error_message=None):
        """log and exit.

        >>> from unittest.mock import Mock
        >>> from snapshotbackup import CliApp
        >>> app = CliApp()
        >>> app.name = 'application_name'
        >>> app.args = Mock()
        >>> app.args.name = 'backup_name'
        >>> app.config = {'notify_remote': None}
        >>> app.exit()
        Traceback (most recent call last):
        SystemExit
        >>> try:
        ...     app.exit()
        ... except SystemExit as e:
        ...     assert e.code is None
        >>> try:
        ...     app.exit('xxx')
        ... except SystemExit as e:
        ...     assert e.code == 1

        :param str error_message: will be logged. changes exit status to `1`.
        :return: this function never returns, it always exits
        :exit 0: success
        :exit 1: error
        """
        if error_message is None:
            logger.info(f'`{self.args.name}` exit without errors')
            sys.exit()
        self.notify(f'backup `{self.args.name}` failed with error:\n{error_message}', error=True)
        logger.error(f'`{self.args.name}` exit with error: {error_message}')
        sys.exit(1)

    def _main(self):  # noqa: C901
        """

        :return: None
        :exit: calls :func:`snapshotbackup.CliApp.exit` in case of error
        """
        _config = self.config
        try:
            worker = Worker(_config['backups'], retain_all_after=_config['retain_all_after'],
                            retain_daily_after=_config['retain_daily_after'], decay_before=_config['decay_before'])
            if self.args.action in ['s', 'setup']:
                worker.setup()
            elif self.args.action in ['b', 'backup']:
                worker.make_backup(self.args.source or _config['source'], _config['ignore'],
                                   autodecay=_config['autodecay'], autoprune=_config['autoprune'],
                                   checksum=self.args.checksum, dry_run=self.args.dry_run, progress=self.args.progress)
                if not self.args.dry_run:
                    self.notify(f'backup `{self.args.name}` finished')
            elif self.args.action in ['l', 'list']:
                list_backups(worker)
            elif self.args.action in ['d', 'decay']:
                worker.decay_backups(self.delete_backup_prompt)
            elif self.args.action in ['p', 'prune']:
                worker.prune_backups(self.delete_backup_prompt)
            elif self.args.action in ['destroy']:
                worker.destroy_volume(self.delete_backup_prompt)
            elif self.args.action in ['clean']:
                worker.delete_syncdir()
            else:
                self.exit(f'unknown command `{self.args.action}`')
        except SourceNotReachableError as e:
            self.exit(f'source dir `{e.path}` not found, is it mounted?')
        except BackupDirNotFoundError as e:
            self.exit(f'backup dir `{e.path}` not found, did you run setup and is it mounted?')
        except BackupDirError as e:
            self.exit(e)
        except CommandNotFoundError as e:
            self.exit(f'command `{e.command}` not found, mayhap missing software?')
        except LockedError as e:
            self.exit(f'sync folder is locked, aborting. try again later or delete `{e.lockfile}`')
        except SyncFailedError as e:
            self.exit(f'backup interrupted or failed, `{e.target}` may be in an inconsistent state '
                      f'(rsync error {e.errno}, {e.error_message})')

    def delete_backup_prompt(self, backup_name):
        """

        :param snapshotbackup.worker.Backup backup_name:
        :return bool:
        """
        return (_yes_prompt if self.args.yes else _yes_no_prompt)(f'delete {backup_name}')
