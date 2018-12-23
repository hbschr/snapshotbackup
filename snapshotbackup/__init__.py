import argparse
import configparser
import importlib
import logging
import os
import signal
import sys

from abc import ABC, abstractmethod
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
    """prints message, returns `True`.

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
    setups process logic (signal handling, logging of uncaught exceptions) and
    initializes and runs :class:`snapshotbackup.CliApp`.

    :return: None
    """
    app = CliApp()
    signal.signal(signal.SIGTERM, lambda signal, frame: app.abort('Terminated'))
    try:
        app()
    except KeyboardInterrupt:
        app.abort('KeyboardInterrupt')
    except Exception as e:
        logger.exception(e)
        app.abort('uncaught exception')


class BaseApp(ABC):
    """base application provides low level app logic like logger and config file handling.
    this is an abstract class, :func:`snapshotbackup.BaseApp.abort` has to implemented in subclass.
    """

    name: str = __name__
    """name of this app"""

    def __init__(self, name=__name__):
        """initialize an base app instance.

        :param str name: name of this app instance
        """
        self.name = name
        super().__init__()

    def _get_journald_handler(self):
        """get logging handler for `journald`.

        :raise ModuleNotFoundError: when module `systemd.journal` couldn't be imported
        :return logging.Handler:
        """
        systemd_journal = importlib.import_module('systemd.journal')
        return systemd_journal.JournalHandler(SYSLOG_IDENTIFIER=self.name)

    def _configure_logger(self, level, journald):
        """configures python logger, aware of custom logging levels.

        :param int level: logging level, 0 `warning`, 1 `info`, 2 `debug`, 3 `debug_shell`
        :param bool journald: redirects log from `stdout` to `journald`
        :return: None
        :exit: calls :func:`snapshotbackup.BaseApp.abort` in case of error
        """
        try:
            handlers = None
            if journald:
                handlers = [self._get_journald_handler()]
            level = (logging.WARNING, logging.INFO, logging.DEBUG, DEBUG_SHELL)[level]
            logging.basicConfig(handlers=handlers, level=level)
        except ModuleNotFoundError as e:
            self.abort(f'dependency for optional feature not found, missing module: {e.name}')
        except IndexError:
            self.abort('debugging doesn\'t go that far, remove one `-d`')

    def _get_config(self, filepath, section):
        """populate `self.config`. make sure to call this first before relying on `self.config`.

        :param str filepath: path to config file
        :param str section: section in ini file to use
        :return dict:
        :exit: calls :func:`snapshotbackup.BaseApp.abort` in case of error
        """
        try:
            return parse_config(filepath, section)
        except FileNotFoundError as e:
            self.abort(f'configuration file `{e.filename}` not found')
        except configparser.NoSectionError as e:
            self.abort(f'no configuration for `{e.section}` found')
        except TimestampParseError as e:
            self.abort(e)

    @abstractmethod
    def abort(self, error_message):
        """aborts execution of app with an error message.

        :param str error_message:
        :return: None
        """
        pass


class CliApp(BaseApp):
    """main cli application, provides job handling."""

    args: argparse.Namespace
    """parsed command line arguments"""

    config: dict = {}
    """parsed config file"""

    def __call__(self, args=sys.argv[1:]):
        """entry point for this `CliApp`.

        :param list args:
        :return: None
        :exit: calls :func:`snapshotbackup.CliApp.abort` in case of error
        """
        self.args = _get_argument_parser().parse_args(args=args)
        self._configure_logger(self.args.debug, self.args.silent)
        self.config = self._get_config(self.args.config, self.args.name)
        try:
            self._main(self.args.action)
        except SourceNotReachableError as e:
            self.abort(f'source dir `{e.path}` not found, is it mounted?')
        except BackupDirNotFoundError as e:
            self.abort(f'backup dir `{e.path}` not found, did you run setup and is it mounted?')
        except BackupDirError as e:
            self.abort(e)
        except CommandNotFoundError as e:
            self.abort(f'command `{e.command}` not found, mayhap missing software?')
        except LockedError as e:
            self.abort(f'sync folder is locked, aborting. try again later or delete `{e.lockfile}`')
        except SyncFailedError as e:
            self.abort(f'backup interrupted or failed, `{e.target}` may be in an inconsistent state '
                       f'(rsync error {e.errno}, {e.error_message})')

    def notify(self, message, error=False):
        """display message via libnotify.

        :param str message:
        :param bool error:
        :return: None
        """
        send_notification(self.name, message, error=error, notify_remote=self.config.get('notify_remote'))

    def abort(self, error_message):
        """log, notify and exit.

        >>> from unittest.mock import Mock
        >>> from snapshotbackup import CliApp
        >>> app = CliApp()
        >>> app.name = 'application_name'
        >>> app.args = Mock()
        >>> app.args.name = 'backup_name'
        >>> app.config = {'notify_remote': None}
        >>> try:
        ...     app.abort('xxx')
        ... except SystemExit as e:
        ...     assert e.code == 1

        :param str error_message: will be logged and notified
        :return: this function never returns, it always exits
        :exit 1: error
        """
        self.notify(f'backup `{self.args.name}` failed with error:\n{error_message}', error=True)
        logger.error(f'`{self.args.name}` exit with error: {error_message}')
        sys.exit(1)

    def _main(self, action):
        """dispatch backup volume actions.

        :param str action: which command to execute, f.e. `backup`, `list`, `prune`, ...
        :return: None
        :raise NotImplementedError: in case of unknown action
        """
        logger.info(f'start `{self.args.name}` w/ pid `{os.getpid()}`')
        _config = self.config
        worker = Worker(_config['backups'], retain_all_after=_config['retain_all_after'],
                        retain_daily_after=_config['retain_daily_after'], decay_before=_config['decay_before'])
        if action in ['s', 'setup']:
            worker.setup()
        elif action in ['b', 'backup']:
            worker.make_backup(self.args.source or _config['source'], _config['ignore'],
                               autodecay=_config['autodecay'], autoprune=_config['autoprune'],
                               checksum=self.args.checksum, dry_run=self.args.dry_run, progress=self.args.progress)
            if not self.args.dry_run:
                self.notify(f'backup `{self.args.name}` finished')
        elif action in ['l', 'list']:
            list_backups(worker)
        elif action in ['d', 'decay']:
            worker.decay_backups(self.delete_backup_prompt)
        elif action in ['p', 'prune']:
            worker.prune_backups(self.delete_backup_prompt)
        elif action in ['destroy']:
            worker.destroy_volume(self.delete_backup_prompt)
        elif action in ['clean']:
            worker.delete_syncdir()
        else:
            raise NotImplementedError(f'unknown command `{action}`')
        logger.info(f'`{self.args.name}` exit without errors')

    def delete_backup_prompt(self, backup_name):
        """

        :param snapshotbackup.worker.Backup backup_name:
        :return bool:
        """
        return (_yes_prompt if self.args.yes else _yes_no_prompt)(f'delete {backup_name}')
