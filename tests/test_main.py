import argparse
import pytest
from unittest.mock import MagicMock, Mock, patch

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

    @patch('importlib.import_module')
    def test_get_journald_handler(self, mocked_systemd_journal):
        handler = self.app._get_journald_handler()
        assert handler._mock_name == mocked_systemd_journal.JournalHandler()._mock_name

    @patch('importlib.import_module', side_effect=ModuleNotFoundError('message'))
    def test_get_journald_handler_fail(self, _):
        with pytest.raises(ModuleNotFoundError):
            self.app._get_journald_handler()

    @patch('logging.basicConfig')
    def test_configure_logger(self, mocked_basic_config):
        self.app.args.debug = 0
        self.app.args.silent = False
        self.app._configure_logger()
        mocked_basic_config.assert_called_once()
        _, kwargs = mocked_basic_config.call_args
        assert isinstance(kwargs.get('handlers'), list) and len(kwargs.get('handlers')) == 0

    @patch('logging.basicConfig')
    def test_configure_logger_journald(self, mocked_basic_config):
        self.app.args.debug = 0
        self.app.args.silent = True
        self.app._get_journald_handler = Mock()
        self.app._configure_logger()
        mocked_basic_config.assert_called_once()
        _, kwargs = mocked_basic_config.call_args
        assert isinstance(kwargs.get('handlers'), list) and len(kwargs.get('handlers')) == 1
        assert kwargs.get('handlers')[0] == self.app._get_journald_handler()

    def test_configure_logger_import_fail(self):
        self.app.args.debug = 0
        self.app.args.silent = True
        self.app._get_journald_handler = Mock(side_effect=ModuleNotFoundError('message'))
        self.app.exit = Mock()
        self.app._configure_logger()
        self.app.exit.assert_called_once()

    def test_configure_logger_debug_level_fail(self):
        self.app.args.debug = 10
        self.app.args.silent = False
        self.app.exit = Mock()
        self.app._configure_logger()
        self.app.exit.assert_called_once()

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
