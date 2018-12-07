import os
import pytest
import stat
import tempfile
from unittest.mock import patch

from snapshotbackup.exceptions import BackupDirError, BackupDirNotFoundError
from snapshotbackup.volume import BtrfsVolume


@patch('snapshotbackup.volume.is_btrfs', return_value=True)
def test_btrfs_volume(mocked_is_btrfs):
    with tempfile.TemporaryDirectory() as path:
        BtrfsVolume(path)
    mocked_is_btrfs.assert_called_once()


def test_btrfs_volume_no_path():
    with tempfile.TemporaryDirectory() as path:
        with pytest.raises(BackupDirNotFoundError):
            BtrfsVolume(os.path.join(path, 'nope'))


def test_btrfs_volume_no_dir():
    with tempfile.TemporaryDirectory() as path:
        not_a_dir = os.path.join(path, 'file')
        open(not_a_dir, 'w').close()
        with pytest.raises(BackupDirError) as excinfo:
            BtrfsVolume(not_a_dir)
        assert excinfo.value.message.startswith('not a directory')


def test_btrfs_volume_not_writable():
    with tempfile.TemporaryDirectory() as path:
        os.chmod(path, stat.S_IRUSR)
        with pytest.raises(BackupDirError) as excinfo:
            BtrfsVolume(path, assert_writable=True)
        assert excinfo.value.message.startswith('not writable')


@patch('snapshotbackup.volume.is_btrfs', return_value=False)
def test_btrfs_volume_no_btrfs(mocked_is_btrfs):
    with tempfile.TemporaryDirectory() as path:
        with pytest.raises(BackupDirError) as excinfo:
            BtrfsVolume(path)
        mocked_is_btrfs.assert_called_once()
        assert str(excinfo.value).startswith('not a btrfs')


@patch('snapshotbackup.volume.is_btrfs', return_value=True)
@patch('snapshotbackup.volume.create_subvolume', return_value=True)
def test_btrfs_volume_create_subvolume(mocked_create, _):
    with tempfile.TemporaryDirectory() as path:
        BtrfsVolume(path).create_subvolume('name')
        mocked_create.assert_called_once()
        args, _ = mocked_create.call_args
        assert args[0] == os.path.join(path, 'name')


@patch('snapshotbackup.volume.is_btrfs', return_value=True)
@patch('snapshotbackup.volume.delete_subvolume', return_value=True)
def test_btrfs_volume_delete_subvolume(mocked_delete, _):
    with tempfile.TemporaryDirectory() as path:
        BtrfsVolume(path).delete_subvolume('name')
        mocked_delete.assert_called_once()
        args, _ = mocked_delete.call_args
        assert args[0] == os.path.join(path, 'name')


@patch('snapshotbackup.volume.is_btrfs', return_value=True)
@patch('snapshotbackup.volume.make_snapshot', return_value=True)
def test_btrfs_volume_make_snapshot_readonly(mocked_snapshot, _):
    with tempfile.TemporaryDirectory() as path:
        BtrfsVolume(path).make_snapshot('source', 'target')
        mocked_snapshot.assert_called_once()
        args, kwargs = mocked_snapshot.call_args
        assert args[0] == os.path.join(path, 'source')
        assert args[1] == os.path.join(path, 'target')
        assert kwargs.get('readonly') is True


@patch('snapshotbackup.volume.is_btrfs', return_value=True)
@patch('snapshotbackup.volume.make_snapshot', return_value=True)
def test_btrfs_volume_make_snapshot_writable(mocked_snapshot, _):
    with tempfile.TemporaryDirectory() as path:
        BtrfsVolume(path).make_snapshot('source', 'target', readonly=False)
        mocked_snapshot.assert_called_once()
        args, kwargs = mocked_snapshot.call_args
        assert args[0] == os.path.join(path, 'source')
        assert args[1] == os.path.join(path, 'target')
        assert kwargs.get('readonly') is False
