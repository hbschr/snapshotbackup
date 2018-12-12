import os
import tempfile
from unittest.mock import patch, Mock

from snapshotbackup.volume import BtrfsVolume
from snapshotbackup.worker import Worker


def test_worker_volume():
    with tempfile.TemporaryDirectory() as path:
        assert isinstance(Worker(path).volume, BtrfsVolume)


@patch('os.path.isdir')
@patch('snapshotbackup.worker.BtrfsVolume')
def test_worker_assert_syncdir_noop(_, __):
    worker = Worker('/path')
    worker._assert_syncdir()
    worker.volume.assure_writable.assert_called_once()
    worker.volume.create_subvolume.assert_not_called()
    worker.volume.make_snapshot.assert_not_called()


@patch('snapshotbackup.worker.BtrfsVolume')
def test_worker_assert_syncdir_create(_):
    worker = Worker('/path')
    worker.get_backups = Mock(return_value=[])
    worker._assert_syncdir()
    worker.volume.create_subvolume.assert_called_once()
    worker.volume.make_snapshot.assert_not_called()


# fixme: not tested if recovered from last backup
@patch('snapshotbackup.worker.BtrfsVolume')
def test_worker_assert_syncdir_recover(_):
    worker = Worker('/path')
    worker.get_backups = Mock()
    worker._assert_syncdir()
    worker.volume.create_subvolume.assert_not_called()
    worker.volume.make_snapshot.assert_called_once()


@patch('snapshotbackup.worker.BtrfsVolume')
@patch('snapshotbackup.worker.is_reachable')
@patch('snapshotbackup.worker.rsync')
def test_worker_make_backup(mocked_rsync, mocked_reachable, _):
    worker = Worker('/path')
    worker._assert_syncdir = Mock()
    worker.make_backup('source', ('ignore',))
    mocked_reachable.assert_called_once()
    mocked_rsync.assert_called_once()
    worker._assert_syncdir.assert_called_once()
    worker.volume.lock.assert_called_once()
    worker.volume.make_snapshot.assert_called_once()


@patch('snapshotbackup.worker.BtrfsVolume')
@patch('snapshotbackup.worker.is_reachable')
@patch('snapshotbackup.worker.rsync')
def test_worker_make_backup_dry_run(mocked_rsync, mocked_reachable, _):
    worker = Worker('/path')
    worker._assert_syncdir = Mock()
    worker.make_backup('source', ('ignore',), dry_run=True)
    mocked_reachable.assert_called_once()
    mocked_rsync.assert_called_once()
    _, kwargs = mocked_rsync.call_args
    assert kwargs.get('dry_run') is True
    worker._assert_syncdir.assert_called_once()
    worker.volume.lock.assert_called_once()
    worker.volume.make_snapshot.assert_not_called()


@patch('snapshotbackup.worker.BtrfsVolume')
@patch('snapshotbackup.worker.is_reachable')
@patch('snapshotbackup.worker.rsync')
def test_worker_make_backup_autodecay(_, __, ___):
    worker = Worker('/path')
    worker._assert_syncdir = Mock()
    worker.decay_backups = Mock()
    worker.prune_backups = Mock()
    worker.make_backup('source', ('ignore',), autodecay=True)
    worker.decay_backups.assert_called_once()
    worker.prune_backups.assert_not_called()


@patch('snapshotbackup.worker.BtrfsVolume')
@patch('snapshotbackup.worker.is_reachable')
@patch('snapshotbackup.worker.rsync')
def test_worker_make_backup_autoprune(_, __, ___):
    worker = Worker('/path')
    worker._assert_syncdir = Mock()
    worker.decay_backups = Mock()
    worker.prune_backups = Mock()
    worker.make_backup('source', ('ignore',), autoprune=True)
    worker.decay_backups.assert_not_called()
    worker.prune_backups.assert_called_once()


@patch('snapshotbackup.worker.BtrfsVolume')
def test_worker_get_backups(_):
    with tempfile.TemporaryDirectory() as path:
        worker = Worker(path)
        worker.volume.path = path
        worker.volume.sync_path = os.path.join(path, 'sync')
        # make sure sync dir is ignored
        os.mkdir(worker.volume.sync_path)
        assert len(worker.get_backups()) == 0
        worker.volume.assure_path.assert_called_once()
        os.mkdir(os.path.join(path, '1989-11-10T00+00'))
        assert len(worker.get_backups()) == 1
        os.mkdir(os.path.join(path, '1989-11-09T00+00'))
        assert len(worker.get_backups()) == 2


@patch('snapshotbackup.worker.BtrfsVolume')
def test_worker_decay_backups_empty_list(_):
    worker = Worker('/path')
    worker.get_backups = Mock(return_value=[])
    worker.decay_backups(lambda x: True)
    worker.get_backups.assert_called_once()
    worker.volume.assure_writable.assert_called_once()
    worker.volume.delete_subvolume.assert_not_called()


@patch('snapshotbackup.worker.BtrfsVolume')
def test_worker_decay_backups_nothing_to_do(_):
    worker = Worker('/path')
    mocked_backup = Mock()
    mocked_backup.decay = False
    worker.get_backups = Mock(return_value=[mocked_backup])
    worker.decay_backups(lambda x: True)
    worker.volume.delete_subvolume.assert_not_called()


@patch('snapshotbackup.worker.BtrfsVolume')
def test_worker_decay_backups_approved(_):
    worker = Worker('/path')
    mocked_backup = Mock()
    worker.get_backups = Mock(return_value=[mocked_backup])
    worker.decay_backups(lambda x: True)
    worker.volume.delete_subvolume.assert_called_once()
    args, _ = worker.volume.delete_subvolume.call_args
    assert args[0] == mocked_backup.name


@patch('snapshotbackup.worker.BtrfsVolume')
def test_worker_decay_backups_rejected(_):
    worker = Worker('/path')
    mocked_backup = Mock()
    worker.get_backups = Mock(return_value=[mocked_backup])
    worker.decay_backups(lambda x: False)
    worker.volume.delete_subvolume.assert_not_called()


@patch('snapshotbackup.worker.BtrfsVolume')
def test_worker_decay_backups_filters_list(_):
    worker = Worker('/path')
    mocked_backup_1 = Mock()
    mocked_backup_2 = Mock()
    mocked_backup_2.decay = False
    worker.get_backups = Mock(return_value=[mocked_backup_1, mocked_backup_2])
    worker.decay_backups(lambda x: True)
    worker.volume.delete_subvolume.assert_called_once()


@patch('snapshotbackup.worker.BtrfsVolume')
def test_worker_prune_backups_empty_list(_):
    worker = Worker('/path')
    worker.get_backups = Mock(return_value=[])
    worker.prune_backups(lambda x: True)
    worker.get_backups.assert_called_once()
    worker.volume.assure_writable.assert_called_once()
    worker.volume.delete_subvolume.assert_not_called()


@patch('snapshotbackup.worker.BtrfsVolume')
def test_worker_prune_backups_nothing_to_do(_):
    worker = Worker('/path')
    mocked_backup = Mock()
    mocked_backup.prune = False
    worker.get_backups = Mock(return_value=[mocked_backup])
    worker.prune_backups(lambda x: True)
    worker.volume.delete_subvolume.assert_not_called()


@patch('snapshotbackup.worker.BtrfsVolume')
def test_worker_prune_backups_approved(_):
    worker = Worker('/path')
    mocked_backup = Mock()
    worker.get_backups = Mock(return_value=[mocked_backup])
    worker.prune_backups(lambda x: True)
    worker.volume.delete_subvolume.assert_called_once()
    args, _ = worker.volume.delete_subvolume.call_args
    assert args[0] == mocked_backup.name


@patch('snapshotbackup.worker.BtrfsVolume')
def test_worker_prune_backups_rejected(_):
    worker = Worker('/path')
    mocked_backup = Mock()
    worker.get_backups = Mock(return_value=[mocked_backup])
    worker.prune_backups(lambda x: False)
    worker.volume.delete_subvolume.assert_not_called()


@patch('snapshotbackup.worker.BtrfsVolume')
def test_worker_prune_backups_filters_list(_):
    worker = Worker('/path')
    mocked_backup_1 = Mock()
    mocked_backup_2 = Mock()
    mocked_backup_2.prune = False
    worker.get_backups = Mock(return_value=[mocked_backup_1, mocked_backup_2])
    worker.prune_backups(lambda x: True)
    worker.volume.delete_subvolume.assert_called_once()


@patch('os.path.isdir')
@patch('snapshotbackup.worker.BtrfsVolume')
def test_worker_delete_syncdir(_, __):
    worker = Worker('/path')
    worker.delete_syncdir()
    worker.volume.assure_writable.assert_called_once()
    worker.volume.delete_subvolume.assert_called_once()


@patch('os.path.isdir', return_value=False)
@patch('snapshotbackup.worker.BtrfsVolume')
def test_worker_delete_syncdir_noop(_, __):
    worker = Worker('/path')
    worker.delete_syncdir()
    worker.volume.delete_subvolume.assert_not_called()


@patch('snapshotbackup.worker.BtrfsVolume')
@patch('os.rmdir')
def test_worker_destroy_volume(mocked_rmdir, _):
    worker = Worker('/path')
    mocked_backup = Mock()
    worker.get_backups = Mock(return_value=[mocked_backup])
    worker.destroy_volume(lambda x: True)
    worker.volume.delete_subvolume.assert_called_once()
    args, _ = worker.volume.delete_subvolume.call_args
    assert args[0] == mocked_backup.name
    mocked_rmdir.assert_called_once()


@patch('snapshotbackup.worker.BtrfsVolume')
@patch('os.rmdir')
def test_worker_destroy_volume_rejected(mocked_rmdir, _):
    worker = Worker('/path')
    mocked_backup = Mock()
    worker.get_backups = Mock(return_value=[mocked_backup])
    worker.destroy_volume(lambda x: False)
    worker.volume.delete_subvolume.assert_not_called()
