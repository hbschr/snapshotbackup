what
==

performs incremental backups with `rsync` onto a `btrfs` filesystem.
finished backups are retained as read-only snapshots.


usage
==

install
--

```commandline
pip install snapshotbackup
pip install snapshotbackup[journald]    # enable logging to journald with `--silent`
```


example `config.ini`
--

```ini
[DEFAULT]
; retain_all = '1 day'
; retain_daily = '1 month'

[data1]
source = /path/to/data1
backups = /backups/data1

[data2]
source = /path/to/data2
backups = /backups/data2
ignore = /.cache
retain_all = '1 week'
notify_remote = user@host
```


actions
--

the setup-step can be skipped if configured backup directory already exists.

```commandline
snapshotbackup setup data1
snapshotbackup backup data1
snapshotbackup list data1
snapshotbackup prune data1
```


prune retention policy
--

- all backups not older than `retain_all`
- daily backups not older than `retain_daily`
- weekly backups forever (*)
- the latest backup is always preserved

(*) yes, forever. if the backup disc is full you have to manually delete the
oldest snapshots.


notification
--

when running via cron or using `notify_remote` you may need to add
`DBUS_SESSION_BUS_ADDRESS` to execution environment, e.g.
`DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus snapshotbackup backup data1`


dev env
==

```commandline
virtualenv .env -p python3
. .env/bin/activate
pip install -r requirements.txt
pip install -e .                    # or pip install -e .[journald]
```


demo
--

if you don't have a `btrfs` filesystem at hand checkout the demo folder.
it creates a `btrfs` image file and mounts it as loopback device.

*DISCLAIMER*: i'm not sure if btrfs loopback files are safe in every environment. use at your own risk.

```commandline
make -f Makefile.demo setup
make -f Makefile.demo backup
make -f Makefile.demo list
make -f Makefile.demo prune
make -f Makefile.demo clean
```

please read `Makefile.demo` and `demo/config.ini` to understand what's happening.


build
--

```commandline
./setup.py bdist_wheel
```


that's all
==

not enough documentation? well, erm.., intended audience are developers.
that's what you get for hobby projects ;-)
