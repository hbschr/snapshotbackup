from subprocess import PIPE, Popen


def shell(*args):
    """
    >>> from btrfsbackup.yaks import shell
    >>> isinstance(shell('ls'), str)
    True
    >>> shell('echo', '-n', 'test')
    'test'
    >>> shell('python3', '-c', 'import sys; print("error", file=sys.stderr, end="")')
    'error'
    >>> shell('not-a-command-whae5roo') != ''
    True
    """
    try:
        process = Popen(args, stdout=PIPE, stderr=PIPE)
        output, error = process.communicate()
    except OSError as e:
        return str(e)
    return output.decode('utf-8') if (output != b'') else error.decode('utf-8')


if __name__ == '__main__':
    print(shell('uname', '-a'))
