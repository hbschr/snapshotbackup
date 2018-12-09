from unittest.mock import patch, MagicMock

import snapshotbackup


def test_main():
    assert 'main' in dir(snapshotbackup)


@patch('snapshotbackup.is_reachable')
@patch('snapshotbackup.rsync')
def test_make_backup_plain(mocked_rsync, _):
    mocked_volume = MagicMock()
    mocked_worker_instance = MagicMock()
    mocked_worker_instance.volume = mocked_volume
    with patch('snapshotbackup.Worker', return_value=mocked_worker_instance):
        snapshotbackup.make_backup('source', 'target', ('ignore',))
        mocked_rsync.assert_called_once()
        mocked_volume.lock.assert_called_once()
        mocked_worker_instance.snapshot_sync.assert_called_once()


@patch('snapshotbackup.is_reachable')
@patch('snapshotbackup.rsync')
def test_make_backup_dry_run(mocked_rsync, _):
    mocked_volume = MagicMock()
    mocked_worker_instance = MagicMock()
    mocked_worker_instance.volume = mocked_volume
    with patch('snapshotbackup.Worker', return_value=mocked_worker_instance):
        snapshotbackup.make_backup('source', 'target', ('ignore',), dry_run=True)
        mocked_rsync.assert_called_once()
        mocked_volume.lock.assert_called_once()
        mocked_worker_instance.snapshot_sync.assert_not_called()


def test_list_backups():
    mocked_worker_instance = MagicMock()
    mocked_worker_instance.get_backups.return_value = [MagicMock(), MagicMock()]
    with patch('snapshotbackup.Worker', return_value=mocked_worker_instance):
        snapshotbackup.list_backups('dir', 'retain_all_after', 'retain_daily_after', 'decay_before')
        mocked_worker_instance.get_backups.assert_called_once()


def test_prune_backups():
    mocked_worker_instance = MagicMock()
    mocked_backup_instance_old = MagicMock()
    mocked_backup_instance_old.prune = True
    mocked_backup_instance_new = MagicMock()
    mocked_backup_instance_new.prune = False
    mocked_worker_instance.get_backups.return_value = [mocked_backup_instance_old, mocked_backup_instance_new]
    with patch('snapshotbackup.Worker', return_value=mocked_worker_instance):
        snapshotbackup.prune_backups('dir', 'retain_all_after', 'retain_daily_after', 'decay_before')
        mocked_worker_instance.get_backups.assert_called_once()
        mocked_backup_instance_old.delete.assert_called_once()
        mocked_backup_instance_new.delete.assert_not_called()


def test_decay_backups():
    mocked_worker_instance = MagicMock()
    mocked_backup_instance_old = MagicMock()
    mocked_backup_instance_old.decay = True
    mocked_backup_instance_new = MagicMock()
    mocked_backup_instance_new.decay = False
    mocked_worker_instance.get_backups.return_value = [mocked_backup_instance_old, mocked_backup_instance_new]
    with patch('snapshotbackup.Worker', return_value=mocked_worker_instance):
        snapshotbackup.decay_backups('dir', 'retain_all_after', 'retain_daily_after', 'decay_before')
        mocked_worker_instance.get_backups.assert_called_once()
        mocked_backup_instance_old.delete.assert_called_once()
        mocked_backup_instance_new.delete.assert_not_called()


@patch('os.rmdir')
@patch('snapshotbackup.subprocess.delete_subvolume')
def test_delete_backups(mocked_delete_subvolume, mocked_rmdir):
    mocked_backup_instance = MagicMock()
    mocked_worker_instance = MagicMock()
    mocked_worker_instance.get_backups.return_value = [mocked_backup_instance]
    with patch('snapshotbackup.Worker', return_value=mocked_worker_instance):
        snapshotbackup.delete_backups('dir')
    # no sync dir provided
    mocked_delete_subvolume.not_called()
    mocked_backup_instance.delete.assert_called_once()
    mocked_rmdir.assert_called_once()


@patch('snapshotbackup.subprocess.delete_subvolume')
def test_delete_sync_dir(mocked_delete_subvolume):
    mocked_worker_instance = MagicMock()
    with patch('snapshotbackup.Worker', return_value=mocked_worker_instance):
        snapshotbackup.delete_syncdir('dir')
    # no sync dir provided
    mocked_delete_subvolume.not_called()
