from subprocess import PIPE, Popen


def _shell(*args):
    """
    >>> from btrfsbackup.filesystem import _shell
    >>> isinstance(_shell('true'), bool)
    True
    >>> _shell('true')
    True
    >>> _shell('false')
    False
    >>> _shell('not-a-command-whae5roo') != ''
    Traceback (most recent call last):
      ...
    FileNotFoundError: ...
    """
    try:
        process = Popen(args, stdout=PIPE, stderr=PIPE)
        output, error = process.communicate()
        returncode = process.returncode
    except OSError as e:
        raise e

    return True if returncode == 0 else False
    # todo: throw custom error object `shellerror` w/ contains `output` and/or `error`
    # raise error.decode('utf-8') if (error != b'') else output.decode('utf-8')


def rsync(source, target, exclude=''):
    """todo"""
    return _shell('rsync', '-azv', '--delete', f'--exclude={exclude}', f'{source}/', target)


def make_snapshot(source, target, readonly=False):
    return _shell('btrfs', 'subvolume', 'snapshot', '-r' if readonly else '', source, target)
