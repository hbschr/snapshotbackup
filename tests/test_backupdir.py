import os
import pytest
import tempfile
from datetime import datetime
from unittest.mock import patch

from snapshotbackup.backupdir import Backup, BackupDir
from snapshotbackup.exceptions import BackupDirError, LockedError


@patch('snapshotbackup.backupdir.is_btrfs', return_value=False)
def test_backupdir_no_btrfs(mocked_is_btrfs):
    with tempfile.TemporaryDirectory() as path:
        with pytest.raises(BackupDirError) as excinfo:
            BackupDir(path)
        mocked_is_btrfs.assert_called_once()
        assert str(excinfo.value).startswith('not a btrfs')


@patch('snapshotbackup.backupdir.is_btrfs', return_value=True)
def test_backupdir_btrfs(mocked_is_btrfs):
    with tempfile.TemporaryDirectory() as path:
        BackupDir(path)
    mocked_is_btrfs.assert_called_once()


@patch('snapshotbackup.backupdir.is_btrfs', return_value=True)
@patch('snapshotbackup.backupdir.create_subvolume')
@patch('snapshotbackup.backupdir.make_snapshot')
def test_backupdir_create_empty_sync(mocked_make_snapshot, mocked_create_subvolume, _):
    with tempfile.TemporaryDirectory() as path:
        BackupDir(path, assert_syncdir=True)
    mocked_create_subvolume.assert_called_once()
    mocked_make_snapshot.assert_not_called()


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


@patch('snapshotbackup.backupdir.is_btrfs', return_value=True)
def test_backupdir_get_backups(_):
    with tempfile.TemporaryDirectory() as path:
        vol = BackupDir(path)
        # make sure sync dir is ignored
        os.mkdir(vol.sync_path)
        assert len(vol.get_backups()) == 0
        os.mkdir(os.path.join(path, '1989-11-10T00+00'))
        assert len(vol.get_backups()) == 1
        os.mkdir(os.path.join(path, '1989-11-09T00+00'))
        assert len(vol.get_backups()) == 2


@patch('snapshotbackup.backupdir.is_btrfs', return_value=True)
@patch('os.path.isdir', return_value=True)
@patch('os.path.exists', return_value=True)
def test_backupdir_get_backups_missing_branch(_, __, ___):
    """when `os.walk` doesn't iterate, can't happen since i checked `isdir` in constructor, but branch coverage
    complains"""
    with tempfile.TemporaryDirectory() as path:
        vol = BackupDir(os.path.join(path, 'nope'))
        assert len(vol.get_backups()) == 0


@patch('snapshotbackup.backupdir.is_btrfs', return_value=True)
def test_backupdir_lock(_):
    with tempfile.TemporaryDirectory() as path:
        vol = BackupDir(path)
        with vol.lock():
            with pytest.raises(LockedError):
                with vol.lock():
                    pass


@patch('snapshotbackup.backupdir.is_btrfs', return_value=True)
@patch('snapshotbackup.backupdir.make_snapshot')
def test_backupdir_snapshot(mocked_make_snapshot, _):
    with tempfile.TemporaryDirectory() as path:
        BackupDir(path).snapshot_sync()
    mocked_make_snapshot.assert_called_once()


@patch('snapshotbackup.backupdir.delete_subvolume')
def test_backup_delete(mocked_delete_subvolume):
    retain_all = datetime(1970, 3, 1)
    retain_daily = datetime(1970, 2, 1)
    decay = datetime(1970, 1, 1)
    backup = Backup('1970-01-01', '/tmp', retain_all, retain_daily, decay)
    backup.delete()
    mocked_delete_subvolume.assert_called_once()
