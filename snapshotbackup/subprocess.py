import logging
import os
import subprocess

from .exceptions import BtrfsSyncError, CommandNotFoundError, SourceNotReachableError, SyncFailedError

DEBUG_SHELL = 5
"""custom logging level for subprocess output"""

logging.addLevelName(DEBUG_SHELL, 'DEBUG_SHELL')
logger = logging.getLogger(__name__)


def run(*args, show_output=False):
    """wrapper around python's `subprocess`: executes given command in a consistent way in this project.

    :param args: command arguments
    :type args: tuple of str
    :param bool show_output: if `True` shell output will be shown on `stdout` and `stderr`
    :raise CommandNotFoundError: if command cannot be found
    :raise subprocess.CalledProcessError: if process exits with a non-zero exit code
    :return: None

    >>> from snapshotbackup.subprocess import run
    >>> run('true')
    >>> run('true', show_output=True)
    >>> run('echo', 'test')
    >>> run('echo', 'test', show_output=True)
    test
    >>> run('false')
    Traceback (most recent call last):
    subprocess.CalledProcessError: ...
    >>> run('not-a-command-whae5roo')
    Traceback (most recent call last):
    snapshotbackup.exceptions.CommandNotFoundError: ...
    """
    logger.log(DEBUG_SHELL, f'run {args}, show_output={show_output}')
    args = tuple(_a for _a in args if _a is not None)
    try:
        with subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='utf-8') as process:
            while process.poll() is None:
                line = process.stdout.readline().rstrip()
                if line:
                    logger.log(DEBUG_SHELL, f'subprocess: {line}')
                    if show_output:
                        print(line)
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, args)
    except FileNotFoundError as e:
        logger.debug(f'raise `CommandNotFoundError` after catching `{e}`')
        raise CommandNotFoundError(e.filename) from e


def is_reachable(path):
    """test if `path` can be reached.

    :param path: can be a local or remote path
    :return: bool
    """
    args = []
    if '@' in path:
        host, path = path.split(':', 1)
        args = ['ssh', host]
    args.extend(['ls', path])
    try:
        run(*args)
    except subprocess.CalledProcessError as e:
        raise SourceNotReachableError(path) from e


def rsync(source, target, exclude=(), checksum=False, progress=False, dry_run=False):
    """run `rsync` for given `source` and `target`.

    :param str source: path to read from
    :param str target: path to write to
    :param str exclude: paths to exclude
    :param bool progress: show some progress information
    :raise SyncFailedError: when sync is interrupted
    :return: None
    """
    logger.debug(f'sync `{source}` to `{target}`')
    args = ['rsync', '--human-readable', '--itemize-changes', '--stats']
    args.extend(['-azv', '--sparse', '--delete', '--delete-excluded'])
    args.extend([f'--exclude={path}' for path in exclude])
    args.extend([f'{source}/', target])
    if checksum:
        args.append('--checksum')
    if dry_run:
        args.append('--dry-run')
        print(f'dry run, no changes will be made on disk, this is what rsync would do:')
    try:
        run(*args, show_output=progress or dry_run)
        btrfs_sync(target)
    except subprocess.CalledProcessError as e:
        logger.debug(f'raise `SyncFailedError` after catching `{e}`')
        raise SyncFailedError(target, e.returncode) from e
    if dry_run:
        print(f'dry run, no changes were made on disk')


def create_subvolume(path):
    """create a subvolume in filesystem for given `path`.

    :param str path: filesystem path
    :return: None
    """
    logger.debug(f'create subvolume `{path}`')
    run('btrfs', 'subvolume', 'create', path)
    btrfs_sync(path)


def delete_subvolume(path):
    """delete subvolume in filesystem at given `path`.

    :param str path: filesystem path
    :return: None
    """
    logger.info(f'delete subvolume `{path}`')
    run('sudo', 'btrfs', 'subvolume', 'delete', path)
    btrfs_sync(os.path.dirname(path))


def make_snapshot(source, target, readonly=True):
    """make a readonly filesystem snapshot for `source` at `target`.

    :param str source: filesystem path
    :param str target: filesystem path
    :param bool readonly: if `True` snapshot will not be writable
    :return: None
    """
    logger.debug(f'create snapshot `{target}`')
    args = 'btrfs', 'subvolume', 'snapshot', '-r' if readonly else None, source, target
    run(*args)
    btrfs_sync(target)


def is_btrfs(path):
    """check if given path is on a btrfs filesystem.

    :return: bool
    """
    try:
        run('btrfs', 'filesystem', 'df', path)
        return True
    except subprocess.CalledProcessError:
        return False


def btrfs_sync(path):
    """force a sync of the filesystem at path. that's like a btrfs-aware `sync`.

    :raise BtrfsSyncError: when sync failed
    :return: None
    """
    try:
        run('btrfs', 'filesystem', 'sync', path)
    except subprocess.CalledProcessError as e:
        raise BtrfsSyncError(path) from e
