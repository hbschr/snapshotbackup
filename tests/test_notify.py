from unittest.mock import patch

from snapshotbackup.notify import send_notification, _ok_icon, _error_icon


def test_plain():
    with patch('snapshotbackup.notify._run') as patched_run:
        send_notification('title', 'message with whitespace')
        patched_run.assert_called_once()
        assert 'title' in patched_run.call_args[0]
        assert 'message with whitespace' in patched_run.call_args[0]


def test_remote():
    with patch('snapshotbackup.notify._run') as patched_run:
        send_notification('title', 'message with whitespace', notify_remote='test@host')
        patched_run.assert_called_once()
        assert patched_run.call_args[0][0] == 'ssh'
        assert patched_run.call_args[0][1] == 'test@host'
        assert 'title' in patched_run.call_args[0][2]
        assert '\'message with whitespace\'' in patched_run.call_args[0][2]


def test_icon():
    with patch('snapshotbackup.notify._run') as patched_run:
        send_notification('title', 'message with whitespace')
        patched_run.assert_called_once()
        assert '-i' in patched_run.call_args[0]
        assert _ok_icon in patched_run.call_args[0]
    with patch('snapshotbackup.notify._run') as patched_run:
        send_notification('title', 'message with whitespace', error=True)
        patched_run.assert_called_once()
        assert '-i' in patched_run.call_args[0]
        assert _error_icon in patched_run.call_args[0]
