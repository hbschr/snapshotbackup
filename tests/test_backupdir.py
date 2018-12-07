import os
import pytest
import tempfile
from datetime import datetime
from unittest.mock import patch

from snapshotbackup.backupdir import Backup, BackupDir
from snapshotbackup.volume import BtrfsVolume


# backup dir

@patch('snapshotbackup.volume.is_btrfs', return_value=True)
def test_backupdir_volume(_):
    with tempfile.TemporaryDirectory() as path:
        assert isinstance(BackupDir(path).volume, BtrfsVolume)


@patch('snapshotbackup.backupdir.BtrfsVolume')
def test_backupdir_assert_writable_default(mocked_volume):
    with tempfile.TemporaryDirectory() as path:
        BackupDir(path)
        mocked_volume.assert_called_once()
        _, kwargs = mocked_volume.call_args
        assert kwargs.get('assert_writable') is False


@patch('snapshotbackup.backupdir.BtrfsVolume')
def test_backupdir_assert_writable_true(mocked_volume):
    with tempfile.TemporaryDirectory() as path:
        BackupDir(path, assert_writable=True)
        _, kwargs = mocked_volume.call_args
        assert kwargs.get('assert_writable') is True


@patch('os.walk')
@patch('snapshotbackup.backupdir.BtrfsVolume')
def test_backupdir_assert_writable_implied_by_assert_syncdir(mocked_volume, _):
    with tempfile.TemporaryDirectory() as path:
        BackupDir(path, assert_syncdir=True)
        _, kwargs = mocked_volume.call_args
        assert kwargs.get('assert_writable') is True


@patch('os.walk', return_value=[(None, (), None)])
@patch('snapshotbackup.backupdir.BtrfsVolume')
def test_backupdir_create_empty_sync(_, __):
    with tempfile.TemporaryDirectory() as path:
        worker = BackupDir(path, assert_syncdir=True)
    worker.volume.create_subvolume.assert_called_once()
    worker.volume.make_snapshot.assert_not_called()


# creation of `Backup` wants a valid volume.path
@pytest.mark.skip
@patch('snapshotbackup.backupdir.is_btrfs', return_value=True)
@patch('snapshotbackup.backupdir.create_subvolume')
@patch('snapshotbackup.backupdir.make_snapshot')
def test_backupdir_recover_sync_from_latest(mocked_make_snapshot, mocked_create_subvolume, _):
    with tempfile.TemporaryDirectory() as path:
        os.mkdir(os.path.join(path, '1989-11-10T00+00'))
        os.mkdir(os.path.join(path, '1989-11-09T00+00'))
        BackupDir(path, assert_syncdir=True)
    mocked_create_subvolume.assert_not_called()
    mocked_make_snapshot.assert_called_once()
    args, _ = mocked_make_snapshot.call_args
    assert '1989-11-10T00+00' in args[0]


@patch('snapshotbackup.backupdir.BtrfsVolume')
def test_backupdir_delete_subvolume(_):
    with tempfile.TemporaryDirectory() as path:
        worker = BackupDir(path)
        worker.volume.sync_path = os.path.join(path, 'sync')
        os.mkdir(worker.volume.sync_path)
        worker.delete_syncdir()
    worker.volume.delete_subvolume.assert_called_once()


@patch('snapshotbackup.backupdir.BtrfsVolume')
def test_backupdir_delete_subvolume_noop(_):
    with tempfile.TemporaryDirectory() as path:
        worker = BackupDir(path)
        worker.volume.sync_path = os.path.join(path, 'sync')
        worker.delete_syncdir()
    worker.volume.delete_subvolume.assert_not_called()


@patch('snapshotbackup.backupdir.BtrfsVolume')
def test_backupdir_get_backups(_):
    with tempfile.TemporaryDirectory() as path:
        worker = BackupDir(path)
        worker.volume.path = path
        worker.volume.sync_path = os.path.join(path, 'sync')
        # make sure sync dir is ignored
        os.mkdir(worker.volume.sync_path)
        assert len(worker.get_backups()) == 0
        os.mkdir(os.path.join(path, '1989-11-10T00+00'))
        assert len(worker.get_backups()) == 1
        os.mkdir(os.path.join(path, '1989-11-09T00+00'))
        assert len(worker.get_backups()) == 2


@patch('snapshotbackup.backupdir.BtrfsVolume')
def test_backupdir_snapshot(_):
    with tempfile.TemporaryDirectory() as path:
        worker = BackupDir(path)
        worker.snapshot_sync()
    worker.volume.make_snapshot.assert_called_once()


# backup

@patch('snapshotbackup.backupdir.delete_subvolume')
def test_backup_delete(mocked_delete_subvolume):
    retain_all = datetime(1970, 3, 1)
    retain_daily = datetime(1970, 2, 1)
    decay = datetime(1970, 1, 1)
    backup = Backup('1970-01-01', '/tmp', retain_all, retain_daily, decay)
    backup.delete()
    mocked_delete_subvolume.assert_called_once()
