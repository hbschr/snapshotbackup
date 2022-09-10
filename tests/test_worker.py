import os
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, Mock

from snapshotbackup.exceptions import SyncFailedError
from snapshotbackup.volume import BtrfsVolume
from snapshotbackup.worker import Backup, Worker


def test_worker_volume(tmpdir):
    assert isinstance(Worker(tmpdir).volume, BtrfsVolume)


@patch('os.path.isdir')
@patch('snapshotbackup.worker.BtrfsVolume')
def test_worker_assert_syncdir_noop(_, __, tmpdir):
    worker = Worker(tmpdir)
    worker._assert_syncdir()
    worker.volume.assure_writable.assert_called_once()
    worker.volume.create_subvolume.assert_not_called()
    worker.volume.make_snapshot.assert_not_called()


@patch('snapshotbackup.worker.BtrfsVolume')
def test_worker_assert_syncdir_create(_, tmpdir):
    worker = Worker(tmpdir)
    worker.get_last = Mock(return_value=None)
    worker._assert_syncdir()
    worker.volume.create_subvolume.assert_called_once()
    worker.volume.make_snapshot.assert_not_called()


# fixme: not tested if recovered from last backup
@patch('snapshotbackup.worker.BtrfsVolume')
def test_worker_assert_syncdir_recover(_, tmpdir):
    worker = Worker(tmpdir)
    worker.get_last = Mock(return_value=Mock())
    worker._assert_syncdir()
    worker.volume.create_subvolume.assert_not_called()
    worker.volume.make_snapshot.assert_called_once()
    _, kwargs = worker.volume.make_snapshot.call_args
    assert kwargs.get('readonly') is False


@patch('snapshotbackup.worker.BtrfsVolume')
def test_worker_setup(_):
    worker = Worker('/path')
    worker.setup()
    worker.volume.setup.assert_called_once()


@patch('snapshotbackup.worker.BtrfsVolume')
@patch('snapshotbackup.worker.is_reachable')
@patch('snapshotbackup.worker.rsync')
def test_worker_make_backup(mocked_rsync, mocked_reachable, _):
    worker = Worker('/path')
    worker._assert_syncdir = Mock()
    timestamp = worker.make_backup('source', ('ignore',))
    mocked_reachable.assert_called_once()
    mocked_rsync.assert_called_once()
    worker._assert_syncdir.assert_called_once()
    worker.volume.lock.assert_called_once()
    worker.volume.make_snapshot.assert_called_once()
    assert isinstance(timestamp, str)


@patch('snapshotbackup.worker.is_reachable')
@patch('snapshotbackup.worker.rsync', side_effect=SyncFailedError('target', 1))
def test_worker_make_backup_failed(_, __, tmpdir):
    worker = Worker(tmpdir)
    worker._assert_syncdir = Mock()
    with pytest.raises(SyncFailedError):
        worker.make_backup('source', ('ignore',))


@patch('snapshotbackup.worker.BtrfsVolume')
@patch('snapshotbackup.worker.is_reachable')
@patch('snapshotbackup.worker.rsync')
def test_worker_make_backup_dry_run(mocked_rsync, mocked_reachable, _):
    worker = Worker('/path')
    worker._assert_syncdir = Mock()
    timestamp = worker.make_backup('source', ('ignore',), dry_run=True)
    mocked_reachable.assert_called_once()
    mocked_rsync.assert_called_once()
    _, kwargs = mocked_rsync.call_args
    assert kwargs.get('dry_run') is True
    worker._assert_syncdir.assert_called_once()
    worker.volume.lock.assert_called_once()
    worker.volume.make_snapshot.assert_not_called()
    assert timestamp is None


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
    args, _ = worker.decay_backups.call_args
    assert args[0]('backup') is True
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
    args, _ = worker.prune_backups.call_args
    assert args[0]('backup') is True


@pytest.mark.parametrize('config', (
    {
        '1970-01-02T00+00': True,
        '1970-01-01T00+00': False,
    },
))
@patch('snapshotbackup.worker.BtrfsVolume')
def test_worker_get_backups_count_and_order(_, tmpdir, config):
    worker = Worker(tmpdir)
    worker.volume.path = tmpdir

    assert len(worker.get_backups()) == 0
    worker.volume.assure_path.assert_called_once()

    for index, name in enumerate(config.keys()):
        os.mkdir(os.path.join(tmpdir, name))
        assert len(worker.get_backups()) == index + 1

    for backup in worker.get_backups():
        assert backup.is_last == config[backup.name]


@pytest.mark.parametrize('config', (
    {
        '1970-01-01T01+00': True,
        '1970-01-01T15+00': False,
    },
    {
        '1970-01-01T01+00': True,
        '1970-01-01T02+00': True,
    },
))
@patch('snapshotbackup.worker.BtrfsVolume')
def test_worker_get_backups_decay(_, tmpdir, config):
    decay_before = datetime(1970, 1, 1, 10, tzinfo=timezone.utc)

    worker = Worker(tmpdir, decay_before=decay_before)
    worker.volume.path = tmpdir

    for name in config.keys():
        os.mkdir(os.path.join(tmpdir, name))

    for backup in worker.get_backups():
        assert backup.decay == config[backup.name]


@pytest.mark.parametrize('config', (
    {
        '1970-01-01T00+00': True,
        '1970-01-01T01+00': False,
        '1970-01-02T00+00': True,
        '1970-01-02T23:59+00': False,
    },
))
@patch('snapshotbackup.worker.BtrfsVolume')
def test_worker_get_backups_daily(_, tmpdir, config):
    worker = Worker(tmpdir)
    worker.volume.path = tmpdir

    for name in config.keys():
        os.mkdir(os.path.join(tmpdir, name))

    for backup in worker.get_backups():
        assert backup.is_daily == config[backup.name]


@pytest.mark.parametrize('config', (
    {
        '1970-01-01T00+00': True,
        '1970-01-04T00+00': False,
        '1970-01-11T00+00': True,
        '1970-01-11T23:59+00': False,
    },
))
@patch('snapshotbackup.worker.BtrfsVolume')
def test_worker_get_backups_weekly(_, tmpdir, config):
    worker = Worker(tmpdir)
    worker.volume.path = tmpdir

    for name in config.keys():
        os.mkdir(os.path.join(tmpdir, name))

    for backup in worker.get_backups():
        assert backup.is_weekly == config[backup.name]


@pytest.mark.parametrize('config', (
    {
        '1970-01-01T00+00': False,
        '1970-01-02T00+00': True,
        '1970-01-05T00+00': False,
        '1970-01-06T00+00': False,  # last is prune-protected
    },
))
@patch('snapshotbackup.worker.BtrfsVolume')
def test_worker_get_backups_prune_weekly(_, tmpdir, config):
    retain_all_after = datetime(2000, 1, 1, tzinfo=timezone.utc)
    retain_daily_after = datetime(2000, 1, 1, tzinfo=timezone.utc)

    worker = Worker(tmpdir, retain_all_after=retain_all_after, retain_daily_after=retain_daily_after)
    worker.volume.path = tmpdir

    for name in config.keys():
        os.mkdir(os.path.join(tmpdir, name))

    for backup in worker.get_backups():
        assert backup.prune == config[backup.name]


@pytest.mark.parametrize('config', (
    {
        '1970-01-05T00+00': False,
        '1970-01-06T00+00': True,
        '1970-01-08T00+00': False,
        '1970-01-09T00+00': False,
        '1970-01-09T01+00': False,  # last is prune-protected
    },
))
@patch('snapshotbackup.worker.BtrfsVolume')
def test_worker_get_backups_prune_daily(_, tmpdir, config):
    retain_all_after = datetime(2000, 1, 1, tzinfo=timezone.utc)
    retain_daily_after = datetime(1970, 1, 7, tzinfo=timezone.utc)

    worker = Worker(tmpdir, retain_all_after=retain_all_after, retain_daily_after=retain_daily_after)
    worker.volume.path = tmpdir

    for name in config.keys():
        os.mkdir(os.path.join(tmpdir, name))

    for backup in worker.get_backups():
        assert backup.prune == config[backup.name]


@pytest.mark.parametrize('config', (
    {
        '1970-01-01T00+00': False,
        '1970-01-01T05+00': True,
        '1970-01-01T15+00': False,
        '1970-01-01T20+00': False,  # last is prune-protected
    },
    {
        '1970-01-01T00+00': False,
        '1970-01-01T05+00': False,  # last is prune-protected
    },
))
@patch('snapshotbackup.worker.BtrfsVolume')
def test_worker_get_backups_prune_retain_all(_, tmpdir, config):
    retain_all_after = datetime(1970, 1, 1, 12, tzinfo=timezone.utc)
    retain_daily_after = datetime(2000, 1, 1, tzinfo=timezone.utc)

    worker = Worker(tmpdir, retain_all_after=retain_all_after, retain_daily_after=retain_daily_after)
    worker.volume.path = tmpdir

    for name in config.keys():
        os.mkdir(os.path.join(tmpdir, name))

    for backup in worker.get_backups():
        assert backup.prune == config[backup.name]


@patch('os.walk')
def test_worker_get_backups_missing_branch(_, tmpdir):
    worker = Worker(tmpdir)
    assert len(worker.get_backups()) == 0


@patch('snapshotbackup.worker.BtrfsVolume')
def test_worker_get_last(_, tmpdir):
    worker = Worker(tmpdir)
    worker.volume.path = tmpdir
    assert worker.get_last() is None
    os.mkdir(os.path.join(tmpdir, '1989-11-09T00+00'))
    last = worker.get_last()
    assert isinstance(last, Backup)
    assert last.name == '1989-11-09T00+00'


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


@patch('snapshotbackup.worker.BtrfsVolume')
def test_worker_delete_syncdir_noop(_, tmpdir):
    worker = Worker(tmpdir)
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
