import snapshotbackup
from unittest.mock import patch, MagicMock


def test_main():
    assert 'main' in dir(snapshotbackup)


@patch('snapshotbackup.rsync')
def test_make_backup_plain(mocked_rsync):
    mocked_backupdir_instance = MagicMock()
    with patch('snapshotbackup.BackupDir', return_value=mocked_backupdir_instance):
        snapshotbackup.make_backup('source', 'target', 'ignore')
        mocked_rsync.assert_called_once()
        mocked_backupdir_instance.lock.assert_called_once()
        mocked_backupdir_instance.snapshot_sync.assert_called_once()


@patch('snapshotbackup.rsync')
def test_make_backup_dry_run(mocked_rsync):
    mocked_backupdir_instance = MagicMock()
    with patch('snapshotbackup.BackupDir', return_value=mocked_backupdir_instance):
        snapshotbackup.make_backup('source', 'target', 'ignore', dry_run=True)
        mocked_rsync.assert_called_once()
        mocked_backupdir_instance.lock.assert_called_once()
        mocked_backupdir_instance.snapshot_sync.assert_not_called()
