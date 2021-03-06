from unittest.mock import patch

from snapshotbackup.exceptions import CommandNotFoundError
from snapshotbackup.notify import send_notification, _ok_icon, _error_icon


@patch('snapshotbackup.notify.run')
def test_plain(patched_run):
    send_notification('title', 'message with whitespace')
    patched_run.assert_called_once()
    args, _ = patched_run.call_args
    assert 'title' in args
    assert 'message with whitespace' in args


@patch('snapshotbackup.notify.run')
def test_remote(patched_run):
    send_notification('title', 'message with whitespace', notify_remote='test@host')
    patched_run.assert_called_once()
    args, _ = patched_run.call_args
    assert args[0] == 'ssh'
    assert args[1] == 'test@host'
    assert 'title' in args[2]
    assert '\'message with whitespace\'' in args[2]


@patch('snapshotbackup.notify.run', side_effect=CommandNotFoundError('no_command'))
@patch('snapshotbackup.notify.logger.warning')
def test_command_not_found(patched_logger, patched_run):
    send_notification('title', 'message with whitespace')
    patched_run.assert_called_once()
    patched_logger.assert_called_once()


def test_icon():
    with patch('snapshotbackup.notify.run') as patched_run:
        send_notification('title', 'message with whitespace')
        patched_run.assert_called_once()
        args, _ = patched_run.call_args
        assert '-i' in args
        assert _ok_icon in args
    with patch('snapshotbackup.notify.run') as patched_run:
        send_notification('title', 'message with whitespace', error=True)
        patched_run.assert_called_once()
        args, _ = patched_run.call_args
        assert '-i' in args
        assert _error_icon in args
