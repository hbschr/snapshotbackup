isofile := btrfs.img
isosize := 500M
mnt_dir := backups
script  := ../dev.py
opts    :=

help:
	@echo 'no user-friendly help here, please consult `demo/Makefile` and `demo/config.ini` and have fun!'

setup:
	mkdir $(mnt_dir)
	fallocate -l $(isosize) $(isofile)
	mkfs.btrfs $(isofile)
	sudo mount -o loop $(isofile) $(mnt_dir)
	sudo chmod a+w $(mnt_dir)
	$(script) $(opts) -c config.ini setup demo

backup:
	$(script) $(opts) -c config.ini backup demo

list:
	$(script) $(opts) -c config.ini list demo

purge:
	$(script) $(opts) -c config.ini purge demo

.IGNORE: clean
clean:
	sudo umount $(mnt_dir)
	rmdir $(mnt_dir)
	rm $(isofile)
