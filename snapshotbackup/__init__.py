import logging
from os.path import join as path_join
import subprocess
import sys


from .backup import load_backups
from .filesystem import create_subvolume, delete_subvolume, make_snapshot, rsync
from .timestamps import get_timestamp


logger = logging.getLogger()


def make_backup(config):
    sync_target = f'{config["backups"]}/{config["sync_dir"]}'
    logger.info(f'syncing `{config["source"]}` to `{sync_target}`')
    try:
        rsync(config['source'], sync_target, config['ignore'])
    except subprocess.CalledProcessError as e:
        logger.error(e)
        sys.exit(f'backup interrupted or failed, `{sync_target}` may be in an inconsistent state')
    timestamp = get_timestamp().isoformat()
    snapshot_target = f'{config["backups"]}/{timestamp}'
    logger.info(f'snapshotting `{sync_target}` to `{snapshot_target}`')
    make_snapshot(sync_target, snapshot_target, True)


def purge_backups(config):
    backups = load_backups(config)
    purges = [backup for backup in backups if backup.purge]
    for purge in purges:
        logger.info(f'purging `{purge.name}` in path `{purge.path}`')
        delete_subvolume(path_join(purge.path, purge.name))


def setup_paths(config):
    sync_target = f'{config["backups"]}/{config["sync_dir"]}'
    logger.info(f'create subvolume `{sync_target}`')
    create_subvolume(sync_target)
