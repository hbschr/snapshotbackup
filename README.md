what
==

performs incremental backups with `rsync` onto a `btrfs` filesystem.
finished backups are retained as read-only snapshots.


retention policy
--

- all backups not older than `retain_all`
- daily backups not older than `retain_daily`
- weekly backups forever (*)
- the latest backup is always preserved

(*) yes, forever. if the backup disc is full you have to manually delete the oldest snapshots.


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
retain_all = '1 week'
```


usage
--

```
snapshotbackup -c config.ini setup data1
snapshotbackup -c config.ini backup data1
snapshotbackup -c config.ini list data1
snapshotbackup -c config.ini purge data1
```


demo
==

if you don't have a `btrfs` filesystem at hand checkout the demo folder.
it creates a `btrfs` image file and mounts it as loopback device.

**DISCLAIMER**: i'm not sure if btrfs loopback files are safe in every environment. use at your own risk.

```
make -C demo setup
make -C demo backup
make -C demo list
make -C demo purge
make -C demo clean
```

please read `demo/Makefile` and `demo/config.ini` to understand what's happening.


dev env
==

```
virtualenv .env -p python3
. .env/bin/activate
pip install -r requirements.txt
```

use `./dev.py` instead of `snapshotbackup`.


that's all
==

not enough documentation? well, erm.., intended audience are developers.
that's what you get for hobby projects ;-)
