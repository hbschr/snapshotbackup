import logging
from os.path import join as path_join
import sys


from .backup import load_backups
from .filesystem import delete_subvolume, make_snapshot, rsync
from .timestamps import get_timestamp


logger = logging.getLogger()
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
        logger.info(f'purging `{purge.name}` in path `{purge.path}`')
        delete_subvolume(path_join(purge.path, purge.name))
