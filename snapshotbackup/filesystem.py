from subprocess import PIPE, run


def _shell(*args, silent=False):
    """
    >>> from snapshotbackup.filesystem import _shell
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
    _shell('rsync', '-azv', '--delete', f'--exclude={exclude}', f'{source}/', target, silent=silent)


def create_subvolume(path, silent=False):
    _shell('btrfs', 'subvolume', 'create', path, silent=silent)


def delete_subvolume(path, silent=False):
    _shell('sudo', 'btrfs', 'subvolume', 'delete', path, silent=silent)


def make_snapshot(source, target, silent=False):
    _shell('btrfs', 'subvolume', 'snapshot', '-r', source, target, silent=silent)
