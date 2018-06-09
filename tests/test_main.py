from unittest.mock import patch, MagicMock

import snapshotbackup


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


def test_list_backups():
    mocked_backupdir_instance = MagicMock()
    mocked_backupdir_instance.get_backups.return_value = [MagicMock(), MagicMock()]
    with patch('snapshotbackup.BackupDir', return_value=mocked_backupdir_instance):
        snapshotbackup.list_backups('dir', 'retain_all_after', 'retain_daily_after')
        mocked_backupdir_instance.get_backups.assert_called_once()


def test_prune_backups():
    mocked_backupdir_instance = MagicMock()
    mocked_backup_instance_old = MagicMock()
    mocked_backup_instance_old.prune = True
    mocked_backup_instance_new = MagicMock()
    mocked_backup_instance_new.prune = False
    mocked_backupdir_instance.get_backups.return_value = [mocked_backup_instance_old, mocked_backup_instance_new]
    with patch('snapshotbackup.BackupDir', return_value=mocked_backupdir_instance):
        snapshotbackup.prune_backups('dir', 'retain_all_after', 'retain_daily_after')
        mocked_backupdir_instance.get_backups.assert_called_once()
        mocked_backup_instance_old.delete.assert_called_once()
        mocked_backup_instance_new.delete.assert_not_called()
