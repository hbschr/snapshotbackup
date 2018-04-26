from subprocess import run


def _shell(*args):
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
    run(args, check=True)


def rsync(source, target, exclude=''):
    _shell('rsync', '-azv', '--delete', f'--exclude={exclude}', f'{source}/', target)


def create_subvolume(path):
    _shell('btrfs', 'subvolume', 'create', path)


def delete_subvolume(path):
    _shell('sudo', 'btrfs', 'subvolume', 'delete', path)


def make_snapshot(source, target, readonly=False):
    _shell('btrfs', 'subvolume', 'snapshot', '-r' if readonly else '', source, target)
