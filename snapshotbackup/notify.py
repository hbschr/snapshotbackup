import logging
import shlex

from .exceptions import CommandNotFoundError
from .subprocess import run


_notify_send = 'notify-send'
_ssh = 'ssh'
_ok_icon = 'ok'
_error_icon = 'error'

logger = logging.getLogger(__name__)


def send_notification(title, message, error=False, notify_remote=None):
    """send desktop notification via `libnotify` to local or remote host.
    uses shell command `notify-send` since i'm unaware of any python dbus implementation that supports sending to remote
    hosts.

    :param str title:
    :param str message:
    :param bool error: if error-icon should be shown, otherwise ok-icon is used
    :param str notify_remote: if given `notify-send` will be executed on remote machine via `ssh`
    :return: None
    """
    args = [_notify_send, title, message, '-i', f'{_error_icon if error else _ok_icon}']
    if notify_remote:
        args = [_ssh, notify_remote, ' '.join([shlex.quote(_a) for _a in args])]
    try:
        run(*args)
    except CommandNotFoundError as e:
        logger.warning(f'{e}, could not send notification "{title} {message}"')
