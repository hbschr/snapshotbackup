import pytest
from unittest.mock import patch
import subprocess

import snapshotbackup.subprocess


def test_mock_without_decorator():
    with patch('subprocess.run', return_value='hallo'):
        assert subprocess.run('xxx') is 'hallo'


@patch('subprocess.run', return_value='hallo')
def test_mock_with_decorator(_):
    assert subprocess.run('xxx') is 'hallo'


def test_run_true():
    assert snapshotbackup.subprocess._run('true') is None


def test_run_false():
    with pytest.raises(subprocess.CalledProcessError):
        snapshotbackup.subprocess._run('false')


@patch('subprocess.run')
def test_run_silent(_):
    snapshotbackup.subprocess._run('example')
    subprocess.run.assert_called_once_with(('example',), stderr=subprocess.PIPE, stdout=subprocess.PIPE)


@patch('subprocess.run')
def test_run_not_silent(_):
    snapshotbackup.subprocess._run('example', show_output=True)
    subprocess.run.assert_called_once_with(('example',), check=True)


@patch('subprocess.run')
def test_rsync_success(_):
    snapshotbackup.subprocess.rsync('source', 'target')
    assert subprocess.run.call_count == 2


@patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, 'command'))
def test_rsync_interrupted(_):
    with pytest.raises(snapshotbackup.exceptions.SyncFailedError):
        snapshotbackup.subprocess.rsync('source', 'target')
    subprocess.run.assert_called_once()


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
    assert '-r' in subprocess.run.call_args_list[0][0][0]


@patch('subprocess.run')
def test_make_snapshot_writable(_):
    snapshotbackup.subprocess.make_snapshot('source', 'target', readonly=False)
    assert subprocess.run.call_count == 2
    assert '-r' not in subprocess.run.call_args_list[0][0][0]


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
