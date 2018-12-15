from unittest.mock import MagicMock, patch

import snapshotbackup
from snapshotbackup import list_backups


def test_main():
    assert 'main' in dir(snapshotbackup)
    assert callable(snapshotbackup.main)
    with patch('snapshotbackup.CliApp') as mockedApp:
        snapshotbackup.main()
    mockedApp.assert_called_once()
    mockedApp().assert_called_once()


def test_list_backups():
    mocked_worker = MagicMock()
    mocked_worker.get_backups.return_value = [MagicMock(), MagicMock()]
    list_backups(mocked_worker)
    mocked_worker.get_backups.assert_called_once()


@patch('snapshotbackup.send_notification')
def test_notify(mocked_notify):
    snapshotbackup.CliApp().notify('message')
    mocked_notify.assert_called_once()
    args, kwargs = mocked_notify.call_args
    assert args[1] == 'message'
    assert kwargs.get('error') is False
    assert kwargs.get('notify_remote') is None


@patch('snapshotbackup.send_notification')
def test_notify_error(mocked_notify):
    snapshotbackup.CliApp().notify('message', error=True)
    mocked_notify.assert_called_once()
    args, kwargs = mocked_notify.call_args
    assert args[1] == 'message'
    assert kwargs.get('error') is True
    assert kwargs.get('notify_remote') is None


@patch('snapshotbackup.send_notification')
def test_notify_remote(mocked_notify):
    app = snapshotbackup.CliApp()
    app.config = {'notify_remote': 'remote'}
    app.notify('message')
    mocked_notify.assert_called_once()
    args, kwargs = mocked_notify.call_args
    assert args[1] == 'message'
    assert kwargs.get('error') is False
    assert kwargs.get('notify_remote') == 'remote'
