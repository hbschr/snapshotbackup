import os
import pytest
import tempfile
from datetime import datetime
from unittest.mock import patch

import snapshotbackup.backupdir
from snapshotbackup.exceptions import BackupDirError


@patch('snapshotbackup.backupdir.is_btrfs', return_value=False)
def test_backupdir_no_btrfs(mock_is_btrfs):
    with tempfile.TemporaryDirectory() as path:
        with pytest.raises(snapshotbackup.exceptions.BackupDirError):
            snapshotbackup.backupdir.BackupDir(path)
        mock_is_btrfs.assert_called_once()
        try:
            snapshotbackup.backupdir.BackupDir(path)
        except BackupDirError as e:
            assert e.message.startswith('not a btrfs')


@patch('snapshotbackup.backupdir.is_btrfs', return_value=True)
def test_backupdir_btrfs(mock_is_btrfs):
    with tempfile.TemporaryDirectory() as path:
        snapshotbackup.backupdir.BackupDir(path)
    mock_is_btrfs.assert_called_once()


@patch('snapshotbackup.backupdir.is_btrfs', return_value=True)
@patch('snapshotbackup.backupdir.create_subvolume')
@patch('snapshotbackup.backupdir.make_snapshot')
def test_backupdir_create_empty_sync(mock_make_snapshot, mock_create_subvolume, mock_is_btrfs):
    with tempfile.TemporaryDirectory() as path:
        snapshotbackup.backupdir.BackupDir(path, assert_syncdir=True)
    mock_is_btrfs.assert_called_once()
    mock_create_subvolume.assert_called_once()
    mock_make_snapshot.assert_not_called()


@patch('snapshotbackup.backupdir.is_btrfs', return_value=True)
@patch('snapshotbackup.backupdir.create_subvolume')
@patch('snapshotbackup.backupdir.make_snapshot')
def test_backupdir_recover_sync(mock_make_snapshot, mock_create_subvolume, mock_is_btrfs):
    with tempfile.TemporaryDirectory() as path:
        os.mkdir(os.path.join(path, '1989-11-09T00+00'))
        snapshotbackup.backupdir.BackupDir(path, assert_syncdir=True)
    mock_is_btrfs.assert_called_once()
    mock_create_subvolume.assert_not_called()
    mock_make_snapshot.assert_called_once()


@patch('snapshotbackup.backupdir.is_btrfs', return_value=True)
@patch('snapshotbackup.backupdir.create_subvolume')
@patch('snapshotbackup.backupdir.make_snapshot')
def test_backupdir_recover_sync_from_latest(mock_make_snapshot, mock_create_subvolume, mock_is_btrfs):
    with tempfile.TemporaryDirectory() as path:
        os.mkdir(os.path.join(path, '1989-11-10T00+00'))
        os.mkdir(os.path.join(path, '1989-11-09T00+00'))
        snapshotbackup.backupdir.BackupDir(path, assert_syncdir=True)
    mock_is_btrfs.assert_called_once()
    mock_create_subvolume.assert_not_called()
    mock_make_snapshot.assert_called_once()
    assert '1989-11-10T00+00' in mock_make_snapshot.call_args[0][0]


@patch('snapshotbackup.backupdir.is_btrfs', return_value=True)
def test_backupdir_get_backups(_):
    with tempfile.TemporaryDirectory() as path:
        vol = snapshotbackup.backupdir.BackupDir(path)
        os.mkdir(os.path.join(path, snapshotbackup.backupdir._sync_dir))
        assert len(vol.get_backups()) == 0
        os.mkdir(os.path.join(path, '1989-11-10T00+00'))
        assert len(vol.get_backups()) == 1
        os.mkdir(os.path.join(path, '1989-11-09T00+00'))
        assert len(vol.get_backups()) == 2


@patch('snapshotbackup.backupdir.is_btrfs', return_value=True)
@patch('os.path.isdir', return_value=True)
def test_backupdir_get_backups_missing_branch(_, __):
    """when `os.walk` doesn't iterate, can't happen since i checked `isdir` in constructor, but branch coverage
    complains"""
    with tempfile.TemporaryDirectory() as path:
        vol = snapshotbackup.backupdir.BackupDir(os.path.join(path, 'nope'))
        assert len(vol.get_backups()) == 0


@patch('snapshotbackup.backupdir.is_btrfs', return_value=True)
@patch('snapshotbackup.backupdir.create_subvolume')
@patch('snapshotbackup.backupdir.make_snapshot')
def test_backupdir_lock(_, __, ___):
    with tempfile.TemporaryDirectory() as path:
        vol = snapshotbackup.backupdir.BackupDir(path, assert_syncdir=True)
        with vol.lock():
            with pytest.raises(snapshotbackup.exceptions.LockedError):
                with vol.lock():
                    pass


@patch('snapshotbackup.backupdir.is_btrfs', return_value=True)
@patch('snapshotbackup.backupdir.create_subvolume')
@patch('snapshotbackup.backupdir.make_snapshot')
def test_backupdir_snapshot(mock_make_snapshot, _, __):
    with tempfile.TemporaryDirectory() as path:
        vol = snapshotbackup.backupdir.BackupDir(path, assert_syncdir=True)
        vol.snapshot_sync()
    mock_make_snapshot.assert_called_once()


@patch('snapshotbackup.backupdir.delete_subvolume')
def test_backup_delete(mocked_delete_subvolume):
    retain_all = datetime(1970, 3, 1)
    retain_daily = datetime(1970, 2, 1)
    backup = snapshotbackup.backupdir.Backup('1970-01-01', '/tmp', retain_all, retain_daily)
    backup.delete()
    mocked_delete_subvolume.assert_called_once()
