from subprocess import PIPE, run


def _shell(*args, silent=False):
    """wrapper around `subprocess.run`: executes given command in a consistent way in this project.

    :param args: command arguments
    :type args: tuple of str
    :param silent bool: suppress output on `stdout`
    :raise subprocess.CalledProcessError: if process exits with a non-zero exit code
    :raise FileNotFoundError: if command cannot be found

    >>> from snapshotbackup.shell import _shell
    >>> _shell('true')
    >>> _shell('false')
    Traceback (most recent call last):
      ...
    subprocess.CalledProcessError: ...
    >>> _shell('not-a-command-whae5roo') != ''
    Traceback (most recent call last):
      ...
    FileNotFoundError: ...
    """
    run(args, check=True, stdout=PIPE if silent else None)


def rsync(source, target, exclude='', silent=False):
    """run `rsync` for given `source` and `target`.

    :param source str: path to read from
    :param target str: path to write to
    :param exclude str: paths to exclude
    :param silent bool: suppress output on `stdout`
    """
    _shell('rsync', '-azv', '--delete', f'--exclude={exclude}', f'{source}/', target, silent=silent)


def create_subvolume(path, silent=False):
    """create a subvolume in filesystem for given `path`.

    :param path str: filesystem path
    :param silent bool: suppress output on `stdout`
    """
    _shell('btrfs', 'subvolume', 'create', path, silent=silent)


def delete_subvolume(path, silent=False):
    """delete subvolume in filesystem at given `path`.

    :param path str: filesystem path
    :param silent bool: suppress output on `stdout`
    """
    _shell('sudo', 'btrfs', 'subvolume', 'delete', path, silent=silent)


def make_snapshot(source, target, silent=False):
    """make a readonly filesystem snapshot for `source` at `target`.

    :param source str: filesystem path
    :param target str: filesystem path
    :param silent bool: suppress output on `stdout`
    """
    _shell('btrfs', 'subvolume', 'snapshot', '-r', source, target, silent=silent)
