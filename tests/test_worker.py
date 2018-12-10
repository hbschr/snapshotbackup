import os
import tempfile
from datetime import datetime
from unittest.mock import patch, Mock

from snapshotbackup.volume import BtrfsVolume
from snapshotbackup.worker import Backup, Worker


# worker

@patch('snapshotbackup.volume.is_btrfs', return_value=True)
def test_worker_volume(_):
    with tempfile.TemporaryDirectory() as path:
        assert isinstance(Worker(path).volume, BtrfsVolume)


@patch('os.path.isdir')
@patch('snapshotbackup.worker.BtrfsVolume')
def test_worker_assert_syncdir_writable(_, __):
    worker = Worker('/path')
    worker._assert_syncdir()
    worker.volume.assure_writable.assert_called_once()


@patch('os.path.isdir')
@patch('snapshotbackup.worker.BtrfsVolume')
def test_worker_assert_syncdir_noop(_, __):
    worker = Worker('/path')
    worker._assert_syncdir()
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


@patch('os.walk')
@patch('snapshotbackup.worker.BtrfsVolume')
def test_worker_assert_syncdir_called_from_constructor(_, __):
    worker = Worker('/path', assert_syncdir=True)
    worker.volume.create_subvolume.assert_called_once()
    worker.volume.make_snapshot.assert_not_called()


@patch('os.path.isdir')
@patch('snapshotbackup.worker.BtrfsVolume')
def test_worker_delete_subvolume(_, __):
    worker = Worker('/path')
    worker.delete_syncdir()
    worker.volume.delete_subvolume.assert_called_once()


@patch('os.path.isdir', return_value=False)
@patch('snapshotbackup.worker.BtrfsVolume')
def test_worker_delete_subvolume_noop(_, __):
    worker = Worker('/path')
    worker.delete_syncdir()
    worker.volume.delete_subvolume.assert_not_called()


@patch('snapshotbackup.worker.BtrfsVolume')
def test_worker_get_backups(_):
    with tempfile.TemporaryDirectory() as path:
        worker = Worker(path)
        worker.volume.path = path
        worker.volume.sync_path = os.path.join(path, 'sync')
        # make sure sync dir is ignored
        os.mkdir(worker.volume.sync_path)
        assert len(worker.get_backups()) == 0
        os.mkdir(os.path.join(path, '1989-11-10T00+00'))
        assert len(worker.get_backups()) == 1
        os.mkdir(os.path.join(path, '1989-11-09T00+00'))
        assert len(worker.get_backups()) == 2


@patch('snapshotbackup.worker.BtrfsVolume')
def test_worker_snapshot(_):
    worker = Worker('/path')
    worker.snapshot_sync()
    worker.volume.make_snapshot.assert_called_once()


# backup

@patch('snapshotbackup.worker.delete_subvolume')
def test_backup_delete(mocked_delete_subvolume):
    retain_all = datetime(1970, 3, 1)
    retain_daily = datetime(1970, 2, 1)
    decay = datetime(1970, 1, 1)
    backup = Backup('1970-01-01', '/tmp', retain_all, retain_daily, decay)
    backup.delete()
    mocked_delete_subvolume.assert_called_once()
