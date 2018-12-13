import os
import pytest
import subprocess
from unittest.mock import patch

import snapshotbackup.subprocess


def test_mock_without_decorator():
    with patch('subprocess.run', return_value='hallo'):
        assert subprocess.run('xxx') is 'hallo'


@patch('subprocess.run', return_value='hallo')
def test_mock_with_decorator(_):
    assert subprocess.run('xxx') is 'hallo'


def test_run_true():
    assert snapshotbackup.subprocess.run('true') is None


def test_run_false():
    with pytest.raises(subprocess.CalledProcessError):
        snapshotbackup.subprocess.run('false')


@patch('subprocess.run')
def test_run_silent(_):
    snapshotbackup.subprocess.run('example')
    args, kwargs = subprocess.run.call_args
    assert args[0] == ('example',)
    assert 'stdout' in kwargs and kwargs['stdout'] == subprocess.PIPE
    assert 'stderr' in kwargs and kwargs['stderr'] == subprocess.PIPE


@patch('subprocess.run')
def test_run_not_silent(_):
    snapshotbackup.subprocess.run('example', show_output=True)
    args, kwargs = subprocess.run.call_args
    assert args[0] == ('example',)
    assert 'stdout' not in kwargs
    assert 'stderr' not in kwargs


def test_is_reachable(tmpdir):
    snapshotbackup.subprocess.is_reachable(str(tmpdir))


@patch('snapshotbackup.subprocess.run')
def test_is_reachable_ssh(mocked_run):
    snapshotbackup.subprocess.is_reachable('user@host:path')
    mocked_run.assert_called_once()
    args, _ = mocked_run.call_args
    assert args[0] == 'ssh'
    assert args[1] == 'user@host'


def test_is_reachable_error(tmpdir):
    path = os.path.join(tmpdir, 'nope')
    with pytest.raises(snapshotbackup.exceptions.SourceNotReachableError) as excinfo:
        snapshotbackup.subprocess.is_reachable(path)
    assert excinfo.value.path == path


@patch('subprocess.run')
def test_rsync_success(_):
    snapshotbackup.subprocess.rsync('source', 'target')
    assert subprocess.run.call_count == 2


@patch('subprocess.run', side_effect=subprocess.CalledProcessError(42, 'command'))
def test_rsync_interrupted(_):
    with pytest.raises(snapshotbackup.exceptions.SyncFailedError) as excinfo:
        snapshotbackup.subprocess.rsync('source', 'target')
    assert excinfo.value.target == 'target'
    assert excinfo.value.errno == 42
    subprocess.run.assert_called_once()


@patch('subprocess.run')
def test_rsync_checksum(_):
    snapshotbackup.subprocess.rsync('source', 'target', checksum=True)
    args, kwargs = subprocess.run.call_args_list[0]
    assert '--checksum' in args[0]


@patch('subprocess.run')
def test_rsync_dry_run(_):
    snapshotbackup.subprocess.rsync('source', 'target', dry_run=True)
    args, kwargs = subprocess.run.call_args_list[0]
    assert '--dry-run' in args[0]


@patch('subprocess.run')
def test_create_subvolume(_):
    snapshotbackup.subprocess.create_subvolume('path')
    assert subprocess.run.call_count == 2


@patch('subprocess.run')
def test_delete_subvolume(_):
    snapshotbackup.subprocess.delete_subvolume('is_btrfs')
    assert subprocess.run.call_count == 2


@patch('subprocess.run')
def test_make_snapshot(_):
    snapshotbackup.subprocess.make_snapshot('source', 'target')
    assert subprocess.run.call_count == 2
    args, _ = subprocess.run.call_args_list[0]
    assert '-r' in args[0]


@patch('subprocess.run')
def test_make_snapshot_writable(_):
    snapshotbackup.subprocess.make_snapshot('source', 'target', readonly=False)
    assert subprocess.run.call_count == 2
    args, _ = subprocess.run.call_args_list[0]
    assert '-r' not in args[0]


@patch('subprocess.run')
def test_is_btrfs(_):
    assert snapshotbackup.subprocess.is_btrfs('path') is True
    subprocess.run.assert_called_once()


@patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, 'command'))
def test_is_not_btrfs(_):
    assert snapshotbackup.subprocess.is_btrfs('path') is False
    subprocess.run.assert_called_once()


@patch('subprocess.run')
def test_btrfs_sync(_):
    snapshotbackup.subprocess.btrfs_sync('path')
    subprocess.run.assert_called_once()


@patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, 'command'))
def test_btrfs_sync_failed(_):
    with pytest.raises(snapshotbackup.exceptions.BtrfsSyncError) as excinfo:
        snapshotbackup.subprocess.btrfs_sync('path')
    assert excinfo.value.path == 'path'
    subprocess.run.assert_called_once()
