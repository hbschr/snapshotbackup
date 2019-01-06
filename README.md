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
pip install snapshotbackup[ci]          # install ci related dependencies
pip install snapshotbackup[dev]         # install dev dependencies
pip install snapshotbackup[journald]    # enable logging to journald with `--silent`
```


example `config.ini`
--

```ini
[DEFAULT]
; retain_all = '1 day'
; retain_daily = '1 month'
; decay = '1 year'

[data1]
source = /path/to/data1
backups = /backups/data1

[data2]
source = /path/to/data2
backups = /backups/data2
ignore = /.cache
retain_all = '1 week'
; '1', 'true' or 'True' for `True`, everything else is `False`
autodecay = 1
autoprune = true
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
snapshotbackup decay data1
```


retention policy
--

`prune` will preserve:
-   all backups not older than `retain_all`
-   daily backups not older than `retain_daily`
-   weekly backups forever (see `decay`)
-   the latest backup is always preserved

`decay` removes all backups older than configured `decay`.


notification
--

when running via cron or using `notify_remote` you may need to add
`DBUS_SESSION_BUS_ADDRESS` to execution environment, e.g.
`DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus snapshotbackup backup data1`


automatization
--

when using advanced installation methods and `cron` make sure `PATH` is
properly setup, f.e.

```
PATH=/usr/local/bin:/bin:/usr/bin:/home/foo/.local/bin
01 * * * * DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus snapshotbackup backup home -s
```

to allow non-interactive deletions configure `sudo` to allow your user "foo"
to use some btrfs commands without password.

```sudoers
foo ALL=(ALL) NOPASSWD: /usr/bin/btrfs subvolume list *
foo ALL=(ALL) NOPASSWD: /usr/bin/btrfs subvolume delete *
```


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
make -f makefile.demo setup
make -f makefile.demo backup
make -f makefile.demo list
make -f makefile.demo prune
make -f makefile.demo decay
make -f makefile.demo clean
```

please read `makefile.demo` and `demo/config.ini` to understand what's happening.


build
--

```commandline
./setup.py bdist_wheel
```


that's all
==

not enough documentation? well, erm.., intended audience are developers.
that's what you get for hobby projects ;-)
