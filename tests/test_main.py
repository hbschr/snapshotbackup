import argparse
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


def test_yes_no_prompt():
    with patch('builtins.input', return_value='y'):
        assert snapshotbackup._yes_no_prompt('message') is True
    with patch('builtins.input', return_value='yes'):
        assert snapshotbackup._yes_no_prompt('message') is True
    with patch('builtins.input', return_value='Y'):
        assert snapshotbackup._yes_no_prompt('message') is True
    with patch('builtins.input', return_value='YES'):
        assert snapshotbackup._yes_no_prompt('message') is True
    with patch('builtins.input'):
        assert snapshotbackup._yes_no_prompt('message') is False
    with patch('builtins.input', return_value=''):
        assert snapshotbackup._yes_no_prompt('message') is False
    with patch('builtins.input', return_value='n'):
        assert snapshotbackup._yes_no_prompt('message') is False
    with patch('builtins.input', return_value='no'):
        assert snapshotbackup._yes_no_prompt('message') is False


def test_list_backups():
    mocked_worker = MagicMock()
    mocked_worker.get_backups.return_value = [MagicMock(), MagicMock()]
    list_backups(mocked_worker)
    mocked_worker.get_backups.assert_called_once()


class TestApp(object):

    app: snapshotbackup.CliApp

    def setup(self):
        self.app = snapshotbackup.CliApp()
        self.app.args = argparse.Namespace()

    @patch('snapshotbackup._yes_prompt')
    @patch('snapshotbackup._yes_no_prompt')
    def test_delete_backup_prompt(self, mocked_yes_no, mocked_yes):
        self.app.args.yes = False
        self.app.delete_backup_prompt('message')
        mocked_yes.assert_not_called()
        mocked_yes_no.assert_called_once()

    @patch('snapshotbackup._yes_prompt')
    @patch('snapshotbackup._yes_no_prompt')
    def test_delete_backup_prompt_yes(self, mocked_yes_no, mocked_yes):
        self.app.args.yes = True
        self.app.delete_backup_prompt('message')
        mocked_yes.assert_called_once()
        mocked_yes_no.assert_not_called()


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
