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


def _delete_volume_prompt_approve(name):
    """

    :param name:
    :return bool:

    >>> from snapshotbackup import _delete_volume_prompt_approve
    >>> _delete_volume_prompt_approve('name')
    delete name
    True
    """
    print(f'delete {name}')
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
                                              'delete', 'clean'],
                           help='setup backup path (`mkdir -p`), make backup, list backups, prune backups not '
                                'held by retention policy, decay old backups, delete all backups or clean backup '
                                'directory')
    argparser.add_argument('name', help='section name in config file')
    argparser.add_argument('-c', '--config', metavar='CONFIGFILE', default='/etc/snapshotbackup.ini',
                           help='use given config file')
    argparser.add_argument('-d', '--debug', action='count', default=0, help='lower logging threshold, may be used '
                                                                            'thrice')
    argparser.add_argument('--delete', action='store_true', help='together w/ `delete` this will delete all backups')
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

    config: dict
    """parsed config file"""

    name: str
    """name of this app"""

    def __call__(self, name=sys.argv[0]):
        """entry point for this `CliApp`.

        :param str name:
        :return: None
        :exit: always calls :func:`snapshotbackup.CliApp.exit`
        """
        signal.signal(signal.SIGTERM, lambda signal, frame: self.exit('Terminated'))
        self.name = name
        self.args = _get_argument_parser().parse_args()
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

    def _configure_logger(self):
        """

        :return: None
        :exit: calls :func:`snapshotbackup.CliApp.exit` in case of error

        >>> from unittest.mock import Mock
        >>> from snapshotbackup import CliApp
        >>> app = Mock()
        >>> CliApp._configure_logger(app)
        >>> app.exit.assert_called_once()
        >>> app = Mock()
        >>> app.args.silent = False
        >>> app.args.debug = 1
        >>> CliApp._configure_logger(app)
        >>> app.exit.assert_not_called()
        >>> app = Mock()
        >>> app.args.silent = False
        >>> app.args.debug = 10
        >>> CliApp._configure_logger(app)
        >>> app.exit.assert_called_once()
        """
        try:
            handlers = [importlib.import_module('systemd.journal').JournalHandler(SYSLOG_IDENTIFIER=self.name)] \
                if self.args.silent else None
            level = (logging.WARNING, logging.INFO, logging.DEBUG, DEBUG_SHELL)[self.args.debug]
            logging.basicConfig(handlers=handlers, level=level)
        except ModuleNotFoundError as e:
            self.exit(f'dependency for optional feature not found, missing module: {e.name}')
        except IndexError:
            self.exit('debugging doesn\'t go that far, remove one `-d`')

    def _parse_config(self):
        """populate `self.config`. make sure to call this first before relying on proper `self.config`.

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
                    send_notification(self.name, f'backup `{self.args.name}` finished',
                                      notify_remote=_config['notify_remote'])
            elif self.args.action in ['l', 'list']:
                list_backups(worker)
            elif self.args.action in ['d', 'decay']:
                worker.decay_backups(_delete_volume_prompt_approve)
            elif self.args.action in ['p', 'prune']:
                worker.prune_backups(_delete_volume_prompt_approve)
            elif self.args.action in ['delete']:
                if self.args.delete:
                    worker.destroy_volume(_delete_volume_prompt_approve)
                else:
                    self.exit('to delete all backups you must also give argument `--delete`')
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
        send_notification(self.name, f'backup `{self.args.name}` failed with error:\n{error_message}', error=True,
                          notify_remote=self.config['notify_remote'] if hasattr(self, 'config') else False)
        logger.error(f'`{self.args.name}` exit with error: {error_message}')
        sys.exit(1)
