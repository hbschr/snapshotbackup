from unittest.mock import MagicMock

import snapshotbackup
from snapshotbackup import list_backups


def test_main():
    assert 'main' in dir(snapshotbackup)


def test_list_backups():
    mocked_worker = MagicMock()
    mocked_worker.get_backups.return_value = [MagicMock(), MagicMock()]
    list_backups(mocked_worker)
    mocked_worker.get_backups.assert_called_once()
