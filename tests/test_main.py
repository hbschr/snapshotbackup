import pytest
import signal
from unittest.mock import MagicMock, Mock, patch

import snapshotbackup
from snapshotbackup import list_backups


class Test_main(object):

    @pytest.fixture(autouse=True)
    def reset_sigterm_handler(self):
        signal.signal(signal.SIGTERM, signal.SIG_DFL)

    @patch('snapshotbackup.CliApp')
    def test_main(self, mocked_App):
        assert 'main' in dir(snapshotbackup)
        assert callable(snapshotbackup.main)
        snapshotbackup.main()
        mocked_App.assert_called_once()
        mocked_App().assert_called_once()

    @patch('signal.signal')
    @patch('snapshotbackup.CliApp')
    def test_main_signal_handler(self, mocked_App, mocked_signal):
        snapshotbackup.main()
        mocked_signal.assert_called_once()
        args, _ = mocked_signal.call_args
        assert len(args) == 2
        _signal, _handler = args
        assert _signal == signal.SIGTERM
        assert callable(_handler)
        _handler('signal', 'frame')
        mocked_App().abort.assert_called_once()

    @patch('snapshotbackup.CliApp', return_value=Mock(side_effect=KeyboardInterrupt()))
    def test_main_keyboard_interrupt(self, mockedApp):
        snapshotbackup.main()
        mockedApp().abort.assert_called_once()

    @patch('snapshotbackup.logger')
    @patch('snapshotbackup.CliApp', return_value=Mock(side_effect=Exception('error')))
    def test_main_catchall_exceptions(self, mockedApp, mocked_logger):
        snapshotbackup.main()
        mocked_logger.exception.assert_called_once()
        mockedApp().abort.assert_called_once()


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
        self.app._configure_logger(0, False)
        mocked_basic_config.assert_called_once()
        _, kwargs = mocked_basic_config.call_args
        assert kwargs.get('handlers') is None

    @patch('logging.basicConfig')
    def test_configure_logger_journald(self, mocked_basic_config):
        self.app._get_journald_handler = Mock()
        self.app._configure_logger(0, True)
        mocked_basic_config.assert_called_once()
        _, kwargs = mocked_basic_config.call_args
        assert isinstance(kwargs.get('handlers'), list) and len(kwargs.get('handlers')) == 1
        assert kwargs.get('handlers')[0] == self.app._get_journald_handler()

    def test_configure_logger_import_fail(self):
        self.app._get_journald_handler = Mock(side_effect=ModuleNotFoundError('message'))
        self.app.abort = Mock()
        self.app._configure_logger(0, True)
        self.app.abort.assert_called_once()

    def test_configure_logger_debug_level_fail(self):
        self.app.abort = Mock()
        self.app._configure_logger(10, False)
        self.app.abort.assert_called_once()

    def test_delete_backup_prompt(self):
        self.app.delete_prompt = Mock()
        self.app.delete_backup_prompt('name')
        self.app.delete_prompt.assert_called_once()
        args, _ = self.app.delete_prompt.call_args
        assert args[0].startswith('delete')
        assert args[0].endswith('name')


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
