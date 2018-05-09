import logging
import subprocess

from .exceptions import CommandNotFoundError, SyncFailedError

DEBUG_SHELL = 5
"""custom logging level for subprocess output"""

logging.addLevelName(DEBUG_SHELL, 'DEBUG_SHELL')
logger = logging.getLogger(__name__)


def _shell(*args, show_output=False):
    """wrapper around `subprocess.run`: executes given command in a consistent way in this project.

    :param args: command arguments
    :type args: tuple of str
    :param bool show_output: if `True` shell output will be shown on `stdout` and `stderr`
    :raise CommandNotFoundError: if command cannot be found
    :raise subprocess.CalledProcessError: if process exits with a non-zero exit code
    :return: None

    >>> from snapshotbackup.shell import _shell
    >>> _shell('true')
    >>> _shell('true', show_output=True)
    >>> _shell('false')
    Traceback (most recent call last):
    subprocess.CalledProcessError: ...
    >>> _shell('false', show_output=True)
    Traceback (most recent call last):
    subprocess.CalledProcessError: ...
    >>> _shell('not-a-command-whae5roo')
    Traceback (most recent call last):
    snapshotbackup.exceptions.CommandNotFoundError: ...
    >>> _shell('not-a-command-whae5roo', show_output=True)
    Traceback (most recent call last):
    snapshotbackup.exceptions.CommandNotFoundError: ...
    """
    try:
        if show_output:
            subprocess.run(args, check=True)
        else:
            completed_process = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logger.log(DEBUG_SHELL, f'stdout: {completed_process.stdout.decode("utf-8")}')
            logger.log(DEBUG_SHELL, f'stderr: {completed_process.stderr.decode("utf-8")}')
            completed_process.check_returncode()
    except FileNotFoundError as e:
        logger.debug(f'raise `CommandNotFoundError` after catching `{e}`')
        raise CommandNotFoundError(e.filename)


def rsync(source, target, exclude='', progress=False):
    """run `rsync` for given `source` and `target`.

    :param str source: path to read from
    :param str target: path to write to
    :param str exclude: paths to exclude
    :param bool progress: show some progress information
    :raise SyncFailedError: when sync is interrupted
    :return: None
    """
    logger.info(f'sync `{source}` to `{target}`')
    try:
        _shell('rsync', '-azv', '--delete', f'--exclude={exclude}', f'{source}/', target, show_output=progress)
    except subprocess.CalledProcessError as e:
        logger.debug(f'raise `SyncFailedError` after catching `{e}`')
        raise SyncFailedError(target)


def create_subvolume(path):
    """create a subvolume in filesystem for given `path`.

    :param str path: filesystem path
    :return: None
    """
    logger.info(f'create subvolume `{path}`')
    _shell('btrfs', 'subvolume', 'create', path)


def delete_subvolume(path):
    """delete subvolume in filesystem at given `path`.

    :param str path: filesystem path
    :return: None
    """
    logger.info(f'delete subvolume `{path}`')
    _shell('sudo', 'btrfs', 'subvolume', 'delete', path)


def make_snapshot(source, target, readonly=True):
    """make a readonly filesystem snapshot for `source` at `target`.

    :param str source: filesystem path
    :param str target: filesystem path
    :param bool readonly: if `True` snapshot will not be writable
    :return: None
    """
    logger.info(f'snapshot subvolume `{source}` as `{target}`')
    args = 'btrfs', 'subvolume', 'snapshot', '-r' if readonly else None, source, target
    _shell(*[_a for _a in args if _a is not None])


def is_btrfs(path):
    """check if given path is on a btrfs filesystem.

    :return: bool
    """
    try:
        _shell('btrfs', 'filesystem', 'df', path)
        return True
    except subprocess.CalledProcessError:
        return False


def btrfs_sync(path):
    """force a sync of the filesystem at path. that's like a btrfs-aware `sync`.

    :return: None
    """
    _shell('btrfs', 'filesystem', 'sync', path)
