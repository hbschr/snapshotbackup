import os.path
import pytest
import subprocess
from unittest.mock import patch

import snapshotbackup.subprocess


def test_run_true():
    assert snapshotbackup.subprocess.run('true') is None


def test_run_false():
    with pytest.raises(subprocess.CalledProcessError):
        snapshotbackup.subprocess.run('false')


def test_run_silent(capsys):
    snapshotbackup.subprocess.run('echo', 'test')
    out, _ = capsys.readouterr()
    assert out == ''


def test_run_not_silent(capsys):
    snapshotbackup.subprocess.run('echo', 'test', show_output=True)
    out, _ = capsys.readouterr()
    assert out == 'test\n'


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


@patch('snapshotbackup.subprocess.run')
def test_rsync_success(mocked_run):
    snapshotbackup.subprocess.rsync('source', 'target')
    assert mocked_run.call_count == 2


@patch('snapshotbackup.subprocess.run', side_effect=subprocess.CalledProcessError(42, 'command'))
def test_rsync_interrupted(mocked_run):
    with pytest.raises(snapshotbackup.exceptions.SyncFailedError) as excinfo:
        snapshotbackup.subprocess.rsync('source', 'target')
    assert excinfo.value.target == 'target'
    assert excinfo.value.errno == 42
    mocked_run.assert_called_once()


@patch('snapshotbackup.subprocess.run')
def test_rsync_checksum(mocked_run):
    snapshotbackup.subprocess.rsync('source', 'target', checksum=True)
    args, kwargs = mocked_run.call_args_list[0]
    assert '--checksum' in args


@patch('snapshotbackup.subprocess.run')
def test_rsync_dry_run(mocked_run):
    snapshotbackup.subprocess.rsync('source', 'target', dry_run=True)
    args, kwargs = mocked_run.call_args_list[0]
    assert '--dry-run' in args


@patch('snapshotbackup.subprocess.run')
def test_create_subvolume(mocked_run):
    snapshotbackup.subprocess.create_subvolume('path')
    assert mocked_run.call_count == 2


@patch('snapshotbackup.subprocess.run')
def test_delete_subvolume(mocked_run):
    snapshotbackup.subprocess.delete_subvolume('is_btrfs')
    assert mocked_run.call_count == 2


@patch('snapshotbackup.subprocess.run')
def test_make_snapshot(mocked_run):
    snapshotbackup.subprocess.make_snapshot('source', 'target')
    assert mocked_run.call_count == 2
    args, _ = mocked_run.call_args_list[0]
    assert '-r' in args


@patch('snapshotbackup.subprocess.run')
def test_make_snapshot_writable(mocked_run):
    snapshotbackup.subprocess.make_snapshot('source', 'target', readonly=False)
    assert mocked_run.call_count == 2
    args, _ = mocked_run.call_args_list[0]
    assert '-r' not in args


@patch('snapshotbackup.subprocess.run')
def test_is_btrfs(mocked_run):
    assert snapshotbackup.subprocess.is_btrfs('path') is True
    mocked_run.assert_called_once()


@patch('snapshotbackup.subprocess.run', side_effect=subprocess.CalledProcessError(1, 'command'))
def test_is_not_btrfs(mocked_run):
    assert snapshotbackup.subprocess.is_btrfs('path') is False
    mocked_run.assert_called_once()


@patch('snapshotbackup.subprocess.run')
def test_btrfs_sync(mocked_run):
    snapshotbackup.subprocess.btrfs_sync('path')
    mocked_run.assert_called_once()


@patch('snapshotbackup.subprocess.run', side_effect=subprocess.CalledProcessError(1, 'command'))
def test_btrfs_sync_failed(mocked_run):
    with pytest.raises(snapshotbackup.exceptions.BtrfsSyncError) as excinfo:
        snapshotbackup.subprocess.btrfs_sync('path')
    assert excinfo.value.path == 'path'
    mocked_run.assert_called_once()
