import sys


from .backup import load_backups
from .filesystem import make_snapshot, rsync
from .timestamps import get_timestamp


sync_dir = 'current'


def make_backup(config):
    sync_target = '{}/{}'.format(config['backups'], sync_dir)
    if rsync(config['source'], sync_target, config['ignore']):
        timestamp = get_timestamp().isoformat()
        snapshot_target = '{}/{}'.format(config['backups'], timestamp)
        return make_snapshot(sync_target, snapshot_target, True)
    else:
        sys.exit('backup interrupted, `{}` may be inconsistent'.format(sync_target))


def purge_backups(config):
    backups = load_backups(config)
    purges = [backup for backup in backups if not backup.retain]
    for purge in purges:
        print(purge)
