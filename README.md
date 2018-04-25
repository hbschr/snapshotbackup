what
==

performs incremental backups with `rsync` onto a `btrfs` filesystem.
finished backups are retained as read-only snapshots.


retention policy
--

- all backups not older than `retain_all`
- daily backups not older than `retain_daily`
- weekly backups forever
- the latest backup is always preserved


example `config.ini`
--

```
[DEFAULT]
# retain_all = '1 day'
# retain_daily = '1 month'

[disc1]
source = /path/to/disc1
backups = /backups/disc1

[disc2]
source = /path/to/disc2
backups = /backups/disc2
ignore = /.cache
```


setup
--

- make sure that `backups` is on a `btrfs` filesystem
- create a subvolume `current` inside `backups` w/ `btrfs subvolume create {backups}/current`


dev env
==

```
virtualenv .env -p python3
. .env/bin/activate
pip install -r requirements.txt
```


demo
==

doesn't work as is, some `sudo`s are missing.

```
fallocate -l 1G test.iso
mkfs.btrfs test.iso
sudo mount -o loop test.iso mnt/
mkdir mnt/source
mkdir mnt/backups
btrfs subvolume create mnt/backups/current
```
