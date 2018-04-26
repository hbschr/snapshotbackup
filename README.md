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

[data1]
source = /path/to/data1
backups = /backups/data1

[data2]
source = /path/to/data2
backups = /backups/data2
ignore = /.cache
```


usage
--

```
./command_line -c config.ini setup data1
./command_line -c config.ini backup data1
./command_line -c config.ini list data1
./command_line -c config.ini purge data1
```


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
