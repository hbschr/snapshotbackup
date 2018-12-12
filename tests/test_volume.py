import os
import pytest
import tempfile
from unittest.mock import patch

from snapshotbackup.exceptions import BackupDirError
from snapshotbackup.volume import BtrfsVolume


def test_btrfs_volume():
    with tempfile.TemporaryDirectory() as path:
        BtrfsVolume(path)


@patch('snapshotbackup.volume.is_btrfs')
def test_btrfs_volume_assure_btrfs(mocked_is_btrfs):
    with tempfile.TemporaryDirectory() as path:
        BtrfsVolume(path)._assure_btrfs()
        mocked_is_btrfs.assert_called_once()


@patch('snapshotbackup.volume.is_btrfs', return_value=False)
def test_btrfs_volume_assure_btrfs_fail(mocked_is_btrfs):
    with tempfile.TemporaryDirectory() as path:
        with pytest.raises(BackupDirError) as excinfo:
            BtrfsVolume(path)._assure_btrfs()
        mocked_is_btrfs.assert_called_once()
        assert str(excinfo.value).startswith('not a btrfs')


@patch('snapshotbackup.volume.is_btrfs')
@patch('snapshotbackup.volume.create_subvolume')
def test_btrfs_volume_create_subvolume(mocked_create, mocked_is_btrfs):
    with tempfile.TemporaryDirectory() as path:
        BtrfsVolume(path).create_subvolume('name')
        mocked_is_btrfs.assert_called_once()
        mocked_create.assert_called_once()
        args, _ = mocked_create.call_args
        assert args[0] == os.path.join(path, 'name')


@patch('snapshotbackup.volume.is_btrfs')
@patch('snapshotbackup.volume.delete_subvolume')
def test_btrfs_volume_delete_subvolume(mocked_delete, mocked_is_btrfs):
    with tempfile.TemporaryDirectory() as path:
        BtrfsVolume(path).delete_subvolume('name')
        mocked_is_btrfs.assert_called_once()
        mocked_delete.assert_called_once()
        args, _ = mocked_delete.call_args
        assert args[0] == os.path.join(path, 'name')


@patch('snapshotbackup.volume.is_btrfs')
@patch('snapshotbackup.volume.make_snapshot')
def test_btrfs_volume_make_snapshot_readonly(mocked_snapshot, mocked_is_btrfs):
    with tempfile.TemporaryDirectory() as path:
        BtrfsVolume(path).make_snapshot('source', 'target')
        mocked_is_btrfs.assert_called_once()
        mocked_snapshot.assert_called_once()
        args, kwargs = mocked_snapshot.call_args
        assert args[0] == os.path.join(path, 'source')
        assert args[1] == os.path.join(path, 'target')
        assert kwargs.get('readonly') is True


@patch('snapshotbackup.volume.is_btrfs')
@patch('snapshotbackup.volume.make_snapshot')
def test_btrfs_volume_make_snapshot_writable(mocked_snapshot, mocked_is_btrfs):
    with tempfile.TemporaryDirectory() as path:
        BtrfsVolume(path).make_snapshot('source', 'target', readonly=False)
        mocked_is_btrfs.assert_called_once()
        mocked_snapshot.assert_called_once()
        args, kwargs = mocked_snapshot.call_args
        assert args[0] == os.path.join(path, 'source')
        assert args[1] == os.path.join(path, 'target')
        assert kwargs.get('readonly') is False
